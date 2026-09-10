# N01-G4-INV-01 — Protection vs Limit Fill Concurrency Investigation

> Task：`N01-G4-INV-01｜Protection vs Limit Fill Concurrency Investigation`
> Finding：`N01-G4-F01`
> 类型：**READ / REPRODUCE / INSTRUMENT / CLASSIFY**（Phase 1 Investigation Only）
> Production Code Changed：**NO**
> 结论：**Case B — Test Interleaving / Witness Defect**（production invariant 正确）
> 日期：2026-09-11

---

## 1. Finding

`backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`
在 load 后的 full-suite 上下文中偶发失败：

```text
FAILED backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen
>   assert order.status == OrderStatus.CANCELLED and position.quantity == 0
E   AssertionError: assert ('FILLED' == <OrderStatus....: 'CANCELLED'>  ... - CANCELLED  + FILLED)
backend\tests\test_group4.py:1709
```

（原文另见 `dev_log/2026-09-10-n01-val-fix-02-n01b-postgres-activity-evidence.md` 第 235–254 行。）

**本窗口已定位根因并确定性复现该断言失败**（详见 §8）。它不是并发 Fill、不是旧数据/错误查询、
不是跨测试污染，而是**测试断言自身读取了一个非唯一/无序的结果集**。

---

## 2. Accepted Baseline（CIP-02，实测读取）

| 项 | 值 | 来源 |
|---|---|---|
| Accepted Main | `e0dab188e55c32b7607c18a66644d25449dc2236` | `git ls-remote origin refs/heads/main` |
| FIX-01 | `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2`（`fix/n01-val-postgres-lifecycle-evidence`，REVIEW PASS，未 merge） | `git ls-remote` |
| FIX-02 | `14f387ac88af1ecd377fcd181c90b109ee361754`（`fix/n01-val-n01b-postgres-activity-evidence`，REVIEW PASS，未 merge） | `git ls-remote` |
| 调查 Branch | `investigate/n01-g4-protection-limit-fill-race` @ `14f387a` | 新建独立 clean worktree |
| 调查 Worktree | `E:\Documents\MarketPulse-AI-n01-g4-inv`（`git status --porcelain` 为空） | — |

未触碰：`main`、`67b0cb5`、`14f387a` 均保持不变；未 closeout FIX-01/FIX-02；未 merge；未开 N01-C。

沙箱环境提示（与既有记忆一致）：新建分支 ref 会被沙箱吞掉，需用 Write 直写
`.git/refs/heads/investigate/<branch>` 后再 `git worktree add`。

---

## 3. Reproduction Matrix

| # | 上下文 | 次数 | 结果 | 证据 |
|---|---|---|---|---|
| R1 | isolated（单 node id） | 20 + 4（早期单跑） | **24/24 PASS**，1.81–1.96 s | `E:\Temp\n01_g4_inv\isolated_20.txt` |
| R2 | 整个 `backend/tests/test_group4.py`（含其全部前置测试，文件顺序） | 1 | **77 passed**，83.13 s | `E:\Temp\n01_g4_inv\group4_file_run1.txt` |
| R3 | preceding Group4 tests + failing test | 由 R2 覆盖（同文件同顺序） | **PASS** | 同上 |
| R4 | full backend suite | 2 | **173 passed**（233.12 s / 239.33 s） | `full_suite_run1.txt` / `full_suite_run2.txt` |
| R5 | **确定性复现该断言失败**（D6 forced-order） | 3 | **3/3 `TEST_1709_WOULD_FAIL = true`** | `E:\Temp\n01_g4_inv\d6_forced_snapshot.txt` |

预算遵守：isolated ≤20 → 实际 20；group4 contextual ≤10 → 实际 1（+ D5/D6 诊断）；
full-suite ≤4 → 实际 2。R2/R3/R4 未捕获 flake（与历史 1 次/多轮的基数一致），
但 R5 已**确定性地**复现同一断言失败，无需靠次数碰运气。

---

## 4. Deterministic Interleaving Evidence

利用仓库**既有** tests-only seam（未新增 production hook）：
`PositionProtectionService.after_risk_reducing_orders_lock`、
`PaperExecutionService.before_order_lock`。
诊断脚本：`scripts/n01_g4_inv_race_diagnostic.py`（investigation-only，不在 `backend/tests`，
不被 `pytest` 默认 collection 采集）。

### D1 — 见证有效性（hook 是否真的持有行锁）

```text
D1 locked_rows      = [{"order_id":"order_05c6d38…","status":"OPEN","side":"BUY","reserved_cash":20.02}]
D1 backend_pid      = 24233
D1 locks_while_held = [relation RowShareLock on paper_orders, granted, pid 24233, state "idle in transaction",
                       transactionid ExclusiveLock, granted, xid 163503, pid 24233, state "idle in transaction"]
D1 probe_while_held = BLOCKED LockNotAvailableError: canceling statement due to lock timeout
D1 final_status     = ["CANCELLED", 0.0]
```

结论：hook 触发时 `_lock_risk_increasing_orders` 确实命中了该 pending BUY，且保护事务真的
持有其行锁（独立连接以 `lock_timeout=400ms` 做 `SELECT … FOR UPDATE` 被阻塞）。
→ **在本测试场景下见证是有效的**，不是「hook 空触发」。

### D2 — 取消提交后 fill 路径的可见性（stale ORM 探针）

把 fill 路径卡在它自己的 `SELECT … FOR UPDATE` **之前**（`before_order_lock`），让 protection
完整跑完并提交 CANCELLED，再放行 fill：

```text
D2 fill_at_before_order_lock        = true
D2 locks_before_release             = protection (pid 14993, xid 159246) + fill (pid 14994, xid 159247) 同时持锁
D2 committed_status_before_release  = "CANCELLED"
D2 cancelled_order_ids              = ["order_068b14039422b21d9a12905d"]
D2 fill_returned                    = []          ← fill 路径没有成交
D2 final_status                     = ["CANCELLED", 0.0]
D2 reconcile_ok                     = true
```

20 次基础场景重复（D3）：`repeats=20, violations=0`。

结论：**「保护先声明行锁 → fill 后到」这一顺序是安全的**。fill 路径在获得锁后用
`.execution_options(populate_existing=True).with_for_update()` 重新读取到了已提交的 CANCELLED，
并返回 `None`；不存在「锁后使用 stale ORM 状态」的成交路径。

---

## 5. PostgreSQL Lock Evidence

- 保护事务：`pg_stat_activity.state = "idle in transaction"`，`pg_locks` 中
  `relation RowShareLock @ paper_orders` + `transactionid ExclusiveLock (xid 163503)`（D1）。
- 独立 observer 连接 `SELECT … FOR UPDATE` 该 order 行 → `LockNotAvailableError`（D1）⇒ 他人持有该行锁。
- D2 同时刻存在两个 XID（保护 159246 / fill 159247），随后保护提交、fill 读取 CANCELLED。
- 说明：即使保护与 fill 事务**同时持锁**，也**没有死锁**（见 §9 锁序分析），保护先释放后 fill 才继续。

（首次 D1 的 `for update` 探针因 SQLAlchemy autobegin 报 `InvalidRequestError`，已修正后复跑，得上述 BLOCKED 证据。）

---

## 6. Failure Snapshot（§9 全部字段）

确定性失败态（D6 `force`）：

```json
{
 "orders_sharing_plan_id_by_ctid": [
   {"ctid":"(0,61)","order_id":"order_addbcb…","side":"SELL","order_type":"MARKET","status":"FILLED",
    "reserved_cash":0.0,"quantity":0.49975012,"limit_price":null},
   {"ctid":"(0,62)","order_id":"order_256a41…","side":"BUY","order_type":"LIMIT","status":"CANCELLED",
    "reserved_cash":0.0,"quantity":0.21052631,"limit_price":95.0}
 ],
 "pending_order": {order_id order_256a41…, plan_id plan_215304…, side BUY, type LIMIT,
                   status CANCELLED, reserved_cash 0.0},
 "positions": [{position_id pos_5e57fa…, quantity 0.0, trade_id trade_882cf1…, realized_pnl -10.5789}],
 "protection": {triggered true, cancelled_order_ids [order_256a41…],
                exit_order_id order_addbcb…, sell_fill_id fill_addbcb…, reason null},
 "fill_task_returned": [],
 "buy_fills":  [{fill_b28309…, order_b28309…, BUY, price 100.05, qty 0.49975012, fee 0.05}],
 "sell_fills": [{fill_addbcb…, order_addbcb…, SELL, price 78.9605, qty 0.49975012, fee 0.03946052}],
 "ledger": [{BUY_FILL, cash_delta -50.05}, {SELL_FILL, cash_delta +39.4211}],
 "trades": [{trade_882cf1…, status CLOSED, exit_reason STOP_LOSS}],
 "position_events": [SL_TRIGGERED, CLOSE]（payload 均含 cancelled_order_ids [order_256a41…]）,
 "reconciliation": {"ok": true, "diagnostics": []}
}
```

**解读**：这是「经济事实完全正确、但断言读到 FILLED」的现场。
- `pending_order.status = CANCELLED`、`reserved_cash = 0`、`position.quantity = 0`、
  `buy_fills = 1`（仅入场）、`SELL_FILL` 1 笔、trade CLOSED/STOP_LOSS、reconcile ok。
- 两笔订单共享同一 `plan_id`：pending LIMIT BUY（CANCELLED）与 protective SELL（FILLED）。
- 失败态下 **SELL 的物理行位置 `(0,61)` 早于 BUY 的 `(0,62)`**。
- 真实并发 Fill ✗、旧数据/错误查询 ✗、跨测试污染 ✗（见 §7）。

---

## 7. Test Isolation Audit

`Harness.boot()` → `Harness.clean()` 后、场景启动前的共享 DB 事实（D5）：

```text
fact_counts_by_run_mode:
  after_boot_before_scenario: orders {TEST:1, LIVE_PAPER:2}, positions {TEST:1, LIVE_PAPER:1},
                              trades {LIVE_PAPER:1, TEST:1}, accounts {TEST:1, REPLAY:1, LIVE_PAPER:1},
                              plans {LIVE_PAPER:1}, fills {TEST:1, LIVE_PAPER:2}, ledger {}
                              runtime_controls 1, symbol_controls 0, incidents 0, outbox 1, pos_events 0
  scenario_setup:             orders {REPLAY:2, …}  ← 恰为该场景自己创建的 2 笔订单
client_backends: 仅本进程 observer，无外来 client backend
```

- **REPLAY 经济事实在场景开始时为 0**：无残留 OPEN order / plan / Position / Trade / Account。
- 非 REPLAY（`LIVE_PAPER`/`TEST`）存在残留，但不在本场景的 `run_mode` 作用域内，不参与本断言。
- 无外来 client backend、无遗留未提交事务、无遗留后台任务（每个测试各自 `asyncio.run` 独立事件循环）。

⇒ **不是 TEST ISOLATION DEFECT（非 Case A）。** 断言读到的 FILLED 行是**本测试自己创建的**
protective SELL 订单。

---

## 8. Root Cause（本窗口定位）

### 8.1 两笔订单共享同一 `plan_id`

1. `open_position` 持久化 plan A（MARKET）；`open_limit_buy` 持久化 plan B（LIMIT）。
   `persist_trade_plan` 会把同 `(run_mode, instrument_id)` 的旧 `ACTIVE` plan 置为 `REPLACED`
   （`backend/src/marketpulse/g3/service.py:283-294`）。
   ⇒ 场景中 **plan B 是唯一 `ACTIVE` plan**。
2. 保护退出时 `load_valid_long_active_plan`（要求「恰好 1 个 ACTIVE plan」，
   `backend/src/marketpulse/g4/planning.py:216-233`）返回 **plan B**；
   `_close_position_in` 取 `plan_id = plan.plan_id`（`g4/protection.py:280-281, 335`）。
3. `_risk_reducing_exit_once` 落库 protective SELL 订单时写入 `plan_id=plan_id`
   （`g3/service.py:1000`），并被 `_settle_order` 置为 `FILLED`（`g3/service.py:1118`）。

⇒ **protective SELL 与 pending LIMIT BUY 共享 `plan_id`。** 实测确认：

```text
plan_62e12473a90e2695223f9342 | 2 | BUY:CANCELLED,SELL:FILLED
```

### 8.2 测试按 `plan_id` 读取「pending order」，且 `scalar()` 对多行静默取首行

`backend/tests/test_group4.py:1682-1685`：

```python
order = await session.scalar(
    select(PaperOrderRecord).where(PaperOrderRecord.plan_id == pending_plan.plan_id)
)
```

- 该查询**没有** `order_id` / `side` / `order_type` 限定，也没有 `ORDER BY` ⇒ 命中 **2 行**。
- SQLAlchemy **2.0.52** 的 `Result.scalar()`：

  ```python
  return self._only_one_row(raise_for_second_row=False, raise_for_none=False, scalar=True)
  ```
  文档字符串原文：**"No validation is performed to test if additional rows remain."**
  ⇒ 多行时**不抛 `MultipleResultsFound`**，直接返回**第一行**。

- 该查询计划为 **Seq Scan**（`explain`: `Seq Scan on paper_orders / Filter: (plan_id)::text = …`）
  ⇒ 行序 = **物理堆序**（受 `clean()` 后的 FSM 复用、历史更新产生的死元组、autovacuum 等影响）
  ⇒ **这就是「只在 loaded full-suite 上下文偶发」的原因**。

### 8.3 失败与通过的分野

- 物理顺序为 BUY(CANCELLED) 在前 → 断言读到 CANCELLED → **PASS**（R1/R2/R4，以及 D6 自然序）。
- 物理顺序为 SELL(FILLED) 在前 → 断言读到 FILLED → **line 1709 FAIL**，而 line 1708
  （`protection.triggered and fills == []`）仍然通过（fill 路径确实返回 `[]`）
  ⇒ **与历史 traceback 完全一致**。

### 8.4 确定性复现（D6）

| 条件 | 命中顺序（按 ctid） | 原样查询返回 | `TEST_1709_WOULD_FAIL` | 不变量 |
|---|---|---|---|---|
| 自然堆序 | BUY(0,33) → SELL(0,35) | **BUY / CANCELLED** | false | 全部满足 |
| 自然堆序 | BUY(0,38) → SELL(0,40) | BUY / CANCELLED | false | 全部满足 |
| 自然堆序 | BUY(0,43) → SELL(0,45) | BUY / CANCELLED | false | 全部满足 |
| `order_by(side desc)`（只改排序，不改数据） | — | **SELL / FILLED** | true | 全部满足 |
| forced（一次逻辑中性写入把已取消 BUY 的活元组移到堆后方） | **SELL(0,61) → BUY(0,62)** | **SELL / FILLED** | **true ×3/3** | 全部满足 |

（`order_by(side desc)` 与 forced 两种方式都证明：**读取结果只由行序决定，与不变量无关**。
forced 这一次不改任何 status，只是把已取消 BUY 的新元组版本排到 SELL 之后。）

---

## 9. Production Concurrency Audit

静态核查两条路径（未修改 production）：

```text
Protection (_close_position_in):
  SELECT OPEN BUY … FOR UPDATE          (Order)
  → hook(after_risk_reducing_orders_lock)
  → Account FOR UPDATE
  → Position FOR UPDATE
  → cancel BUY (cancel_order, 同一事务/同一 session)
  → protective SELL (execute_risk_reducing_exit, 同一 session)
  → COMMIT

Fill (_process_open_order):
  preview OPEN BUY (无锁)
  → RiskGate (RuntimeControl FOR UPDATE)
  → before_order_lock
  → SELECT BUY … FOR UPDATE populate_existing
  → refresh order; if status != OPEN: return None
  → Plan / Account / Positions FOR UPDATE
  → 二次 RiskGate / freshness / plan guard / eligibility
  → _settle_order
```

- 锁序：Protection 为 `Order → Account → Position`；Fill 为
  `RuntimeControl → Order → Plan → Account → Positions`。两者**无环**（protection 不取
  RuntimeControl），故不构成死锁；亦无 AbortedTransaction/DeadlockDetected 现象。
- 未发现任何可在 protection 已持有行锁后成交该 BUY 的路径；
  未发现获得锁后使用 stale ORM 状态的分支（`populate_existing=True` + D2 实证）。
- 额外护栏：`_limit_fill_plan_guard`（`g3/service.py:1404-1407`）在 `ask <= plan.stop_loss` 时返回
  `BUY_STOP_LOSS_BREACHED`；本场景 `ask=80 <= stop_loss=80` ⇒ 即便走到该步也不会成交。
- D2 实证：取消提交后 fill 路径返回 `None`/`[]`，最终 CANCELLED，`reconciliation.ok = true`。

⇒ **production no-reopen invariant 保持正确。**

---

## 10. Classification

### 结论：**Case B — Test Interleaving / Witness Defect**

- **不是 Case A**：REPLAY 事实在场景前为 0，无残留/共享状态、无外来 backend（§7）。
- **不是 Case C**：无任何 production 路径可违反 no-reopen invariant；该「FILLED」行是
  **protective SELL 订单自身的正常 FILLED**，pending BUY 实际为 CANCELLED（§6/§9）。
- **不是 Case D**：根因已定位（§8）并**确定性复现**了同一断言失败（R5）。

精确表述：这是**测试侧「断言读取范围」缺陷** —— 断言自称读取「pending BUY」，实际读取了一个
**非唯一且无序**的结果集（两行共享 `plan_id`），并依赖 `Session.scalar()` 的「静默取首行」语义。

下一步：`N01-VAL-FIX-03`。

---

## 11. Recommended Fix Boundary

**仅限测试代码**；不得修改 production（`g3/service.py`、`g4/protection.py` 均不得动）。

最小修复（`backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`）：
在 `open_limit_buy` 之后、改变 quotes 之前，读取并保存 **pending BUY 的 `order_id`**，
断言时按 `order_id` 唯一读取，例如：

```python
async with SESSIONS() as session:
    pending_order_id = await session.scalar(
        select(PaperOrderRecord.order_id).where(
            PaperOrderRecord.plan_id == pending_plan.plan_id,
            PaperOrderRecord.side == OrderSide.BUY,
            PaperOrderRecord.order_type == OrderType.LIMIT,
        )
    )
…
order = await session.scalar(
    select(PaperOrderRecord).where(PaperOrderRecord.order_id == pending_order_id)
)
```

要点：
1. 必须让「pending BUY」的读取**唯一化**（`order_id` 或至少
   `plan_id + side=BUY + order_type=LIMIT`）；仅加 `ORDER BY` 不足以消除歧义。
2. 同样的读取模式建议做一次**仓库级审计**：凡是「按 `plan_id` 读 `paper_orders`」或依赖
   `Session.scalar()` 唯一性的地方，都需确认其谓词确实唯一（本文件 line 1683 是一例）。
3. 建议在测试作者规范中记录：**SQLAlchemy `Result.scalar()` 对多行静默取首行，不做校验**
   （`raise_for_second_row=False`），因此「断言依赖 `scalar()` 唯一性」是危险模式。

---

## 12. Production Code Changed

**NO。** `git diff 14f387a..HEAD -- backend/src backend/alembic` 为空；
未修改 `g3/service.py`、`g4/protection.py`、schema/migration、OKX provider、G2/G3/G4/G5 语义；
未 closeout FIX-01/FIX-02、未 merge、未开 N01-C。

## 13. Files Changed

- `dev_log/2026-09-11-n01-g4-protection-limit-fill-investigation.md`（本文件，新增）
- `scripts/n01_g4_inv_race_diagnostic.py`（新增；investigation-only 诊断脚本，
  不在 `backend/tests`，不被 pytest 默认采集；仅使用既有 test 行为与只读 observer 连接）
- 仓库外原始证据（`E:\Temp\n01_g4_inv\`）：`isolated_20.txt`、`group4_file_run1.txt`、
  `full_suite_run1.txt`、`full_suite_run2.txt`、`d1_witness.txt`、`d2_post_cancel.txt`、
  `d3_base_20.txt`、`d5_isolation.txt`、`d6_forced_snapshot.txt`

未修改：`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md`、`PROJECT_STATE.md`、`AI_CONTEXT.md`、
`backend/tests/test_group4.py`。

## 14. Final Recommendation

`INVESTIGATION COMPLETE — Case B — READY FOR INDEPENDENT REVIEW`
后续请另开 `N01-VAL-FIX-03`（tests-only），boundary 见 §11。
