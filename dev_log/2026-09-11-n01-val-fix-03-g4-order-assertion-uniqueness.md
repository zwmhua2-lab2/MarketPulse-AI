# N01-VAL-FIX-03 — G4 Protection / Limit-Fill Assertion Uniqueness

- Date: 2026-09-11
- Type: tests-only validation fix（`Production Code Changed = NO`）
- Status: `VALIDATED / AWAITING REVIEW`
- Branch: `fix/n01-val-g4-order-assertion-uniqueness`
- Isolated worktree: `E:\Documents\MarketPulse-AI-n01-val-fix-03`

## 1. Requirement / Scope

修复 `N01-G4-F01`：目标测试用**非唯一的 `plan_id` 谓词**读取 pending order，再用
`Session.scalar()` 取其状态作为断言证据。

- Task Base（硬约束）= `14f387ac88af1ecd377fcd181c90b109ee361754`
  （= N01-VAL-FIX-02 已评审 commit；其 parent = `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2`，
  再 parent = Accepted Main `e0dab188e55c32b7607c18a66644d25449dc2236`）。
- **未**基于 `201d9a8604f8e02c3bb35c262c9755834f899548`（investigation evidence branch）开发；
  该分支及其 `scripts/n01_g4_inv_race_diagnostic.py` 保留为独立 Evidence Branch，未复制、未
  cherry-pick 到本 branch。
- 预期主线：`e0dab188 → 67b0cb5 → 14f387a → N01-VAL-FIX-03 → Final Closeout`。

## 2. Repository Truth（preflight 实测）

| 项 | 实测值 |
|---|---|
| Accepted Main（`git ls-remote origin refs/heads/main`） | `e0dab188e55c32b7607c18a66644d25449dc2236` |
| Task Base | `14f387ac88af1ecd377fcd181c90b109ee361754` |
| Task Base parent | `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2` |
| Task Base parent-parent | `e0dab188e55c32b7607c18a66644d25449dc2236` |
| Investigation evidence commit | `201d9a8604f8e02c3bb35c262c9755834f899548`（未使用） |
| Fix #3 worktree HEAD（preflight） | `14f387ac88af1ecd377fcd181c90b109ee361754`（clean） |

### 2.1 Git ref 事故与恢复（环境，非产品）

本机既有实测坑：在沙箱内 `git worktree add <path> <existing-branch>` 会**吞掉**
`.git/refs/heads/<ns>/` 整个 loose-ref 目录。本次创建 FIX-03 worktree 时该现象复现，
连带丢失 `fix/n01-val-postgres-lifecycle-evidence` 与
`fix/n01-val-n01b-postgres-activity-evidence` 两个 loose ref。

- 恢复依据（权威）：远端 `git ls-remote origin "refs/heads/fix/*"` →
  `fix/n01-val-postgres-lifecycle-evidence = 67b0cb5e03bd…`、
  `fix/n01-val-n01b-postgres-activity-evidence = 14f387ac88…`；
  并用 `.git/worktrees/MarketPulse-AI-n01-val-fix-0{1,2,3}/logs/HEAD` reflog 交叉核对。
- 恢复手段：直接用 Write 工具写回三个 loose-ref 文件（40 位 SHA + 换行），随后
  `git rev-parse` 三个 branch 名称全部解析正确，各 worktree 工作树仍为 clean。
- **无内容丢失**：commit 对象、远端 branch 均未受影响；仅本地 ref 文件被重建。

## 3. Finding — N01-G4-F01

目标测试：

`backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`

分类：**Case B — Test Assertion Scope / Ambiguous Read Defect**。未确认 production
concurrency defect。

### 3.1 Old Assertion（Task Base `14f387a`，line 1683–1685）

```python
order = await session.scalar(
    select(PaperOrderRecord).where(PaperOrderRecord.plan_id == pending_plan.plan_id)
)
...
assert order.status == OrderStatus.CANCELLED and position.quantity == 0  # line 1709
```

该 query 在 protective exit 之后可能命中**两行**，两者合法共享同一个 `plan_id`：

| order | side | order_type | status |
|---|---|---|---|
| pending LIMIT BUY | BUY | LIMIT | CANCELLED |
| protective exit | SELL | MARKET | FILLED |

`Session.scalar()`（SQLAlchemy 2.0.52 / `Result.scalar()`）在多行时**不抛**
`MultipleResultsFound`（`raise_for_second_row=False`），而是静默返回**第一行**。该 query 是
Seq Scan 且**无 `ORDER BY`** ⇒ 行序即物理堆序（受历史负载 / FSM / autovacuum 影响）
⇒ 断言结果与负载相关。

## 4. Root Cause（源码层独立复核）

1. `persist_trade_plan()`（`g3/service.py:283`）把同 `(run_mode, instrument_id)` 下既有
   `PlanStatus.ACTIVE` 行整批改为 `PlanStatus.REPLACED`，再插入新 plan 为 `ACTIVE`。
   ⇒ `open_position()` 后 `open_limit_buy()` ⇒ 该 symbol 的**唯一 ACTIVE plan = 待成交 LIMIT BUY 的 plan**。
2. `protection.evaluate()`（`g4/protection.py:77`）在 `_close_position_in()` 内以
   `load_valid_long_active_plan()` 取 ACTIVE plan（`:280`）并令 `plan_id = plan.plan_id`（`:281`），
   随后 `_cancel_risk_increasing()` 取消 risk-increasing BUY（`:286`），并调用
   `execute_risk_reducing_exit(plan_id=plan_id, ...)`（`:333`）。
3. `_risk_reducing_exit_once()`（`g3/service.py:945`）以
   `side=OrderSide.SELL, order_type=OrderType.MARKET, plan_id=<active plan id>` 建单并 SETTLE。
   ⇒ **protective SELL 与 pending LIMIT BUY 共享 `plan_id`**。
4. 结论：`plan_id` 在该时点**不是**唯一 order identity；用它作 pending BUY 的状态证据在
   语义上就是错的，与「行序是否稳定」无关。

（同一根因链已由 N01-G4-INV-01 以 PostgreSQL lock evidence 独立证明并通过 Review；
本窗口按 CIP-07/CIP-08 重新从源码复核，不采信其结论文本。）

## 5. Exact Test Fix

### 5.1 New Identity

pending BUY 以其**唯一稳定 identity = `order_id`** 读取。在一次显式唯一条件下取得该
`order_id`（此时该 plan 下只有这一笔 LIMIT BUY），之后**所有**断言一律走 `order_id`。

```python
pending_order_ids = list(
    (
        await session.scalars(
            select(PaperOrderRecord.order_id).where(
                PaperOrderRecord.plan_id == pending_plan.plan_id,
                PaperOrderRecord.side == OrderSide.BUY,
                PaperOrderRecord.order_type == OrderType.LIMIT,
            )
        )
    ).all()
)
assert len(pending_order_ids) == 1     # 显式证明唯一性，而不是假设唯一
pending_order_id = pending_order_ids[0]
```

- 采用 `.scalars().all()` + `len == 1`，**显式**证明唯一性，而不是再次依赖 `scalar()` 的
  静默首行语义。
- 读取按 `order_id`：

```python
pending_order = await session.get(PaperOrderRecord, pending_order_id)   # PK 读取
protective_sell = await session.scalar(
    select(PaperOrderRecord).where(
        PaperOrderRecord.plan_id == pending_plan.plan_id,
        PaperOrderRecord.side == OrderSide.SELL,
        PaperOrderRecord.order_type == OrderType.MARKET,
    )
)
```

- 同一文件中已有同型先例（`test_fg_b_protection_vs_cancel_...` 与
  `test_fg_b_ai_close_claims_pending_buy_order_before_account` 以
  `PaperOrderRecord.order_id == pending.order_id` 复读），本次沿用该既有模式，未新造 helper、
  未改 `open_limit_buy()` 签名。

### 5.2 New Assertions

```python
assert protection.triggered and fills == []
assert protection.cancelled_order_ids == [pending_order.order_id]

assert pending_order.side == OrderSide.BUY          # exact pending BUY
assert pending_order.order_type == OrderType.LIMIT
assert pending_order.status == OrderStatus.CANCELLED
assert pending_order.reserved_cash == 0

assert protective_sell is not None                  # protective SELL
assert protective_sell.side == OrderSide.SELL
assert protective_sell.status == OrderStatus.FILLED

assert position.quantity == 0
assert len(buy_fills) == 1                          # 仅原始 entry fill
assert buy_fills[0].order_id != pending_order.order_id
assert report.ok
```

`protection.cancelled_order_ids` 直接使用 `ProtectionOutcome` 既有字段
（`g4/models.py:228`）——**未**新增 production API。`protective_sell` 的 SELL/FILLED 断言与
pending BUY 的 BUY/LIMIT/CANCELLED 断言**并列存在**，使两种 order 不再可能被互相误认。

### 5.3 未做的（Forbidden Fixes 遵守情况）

- **未**加 `ORDER BY` / `LIMIT 1` 去"稳定"原 query。
- **未**用 `plan_id + 任意排序` 替代 `order_id`。
- **未**改动 `g3/service.py`、`g4/protection.py`、schema、production locking、
  transaction ordering。
- **未**因根因是 assertion scope 而删除并发 witness：`after_risk_reducing_orders_lock` /
  `orders_locked` / `release` / `assert not fill.done()` 全部原样保留。

## 6. Targeted Repository Audit（只读）

搜索面：`backend/tests/` 内 `PaperOrderRecord.plan_id`（15 处，全部位于 `test_group4.py`）
与 `session.scalar(...)`。

### 6.1 Ambiguous（本 Fix 一并最小修正）

| 行（Task Base） | 测试 | 判定依据 |
|---|---|---|
| 1684 | `test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen` | 本 Finding；read 发生在 protective exit 之后 ⇒ 2 行同 `plan_id` |
| 714 | `test_stop_loss_cancels_pending_add` | **与 Finding 完全同构**：read 发生在 `protection.evaluate()` **之后**，protective SELL 与 pending BUY 共享 `plan_id`，同样 `session.scalar()` + `assert add_order_after.status == CANCELLED` |

714 的最小修正：在 protective exit **之前**的那次读取处捕获 `add_order.order_id`
（并把该次 acquisition 收紧为 `plan_id + side=BUY + order_type=LIMIT` 的唯一谓词），
之后一律用 `session.get(PaperOrderRecord, add_order_id)` 复读。断言集合不变。

### 6.2 Safe（不改）

其余 13 处（705 / 758 / 1291 / 1566 / 1722 / 2105 / 2113 / 2263 / 2354 / 2435 / 2543 /
2636 / 3765）：读取窗口内该 `plan_id` 下**只可能有一笔** order，逐一核对如下——

- 705 / 758 / 1566 / 1722 / 2105：读取发生在任何 protective exit **之前**。
- 1291：`emergency_stop()` 为 cancel-only（**非** close-all），不创建 SELL order。
- 2113 / 2543 / 2636 / 3765：读取在 `RecoveryManager.recover()` 之后；这些场景中 recovery 的
  `protection.evaluate()` 未触发退出（无 position 或 SL/TP 未 breach），不产生共享 `plan_id` 的 SELL。
- 2263 / 2354 / 2435：紧接 `open_limit_buy()` 之后读取，尚未发生 protective exit。

以上 13 处属**潜在**（latent）歧义而非当前缺陷，**未**修改（CIP-05 Scope Isolation）。
另核 `select(PaperOrderRecord)` 的其余用法（`test_group3.py` / `test_group4.py`）均为
`order_id` / `intent_id` 唯一谓词或 `.scalars().all()` 集合读取，无单行假设，不改。

**未发现**涉及 production semantics 或范围较大的问题，故无 STOP/REPORT 触发项。

## 7. Concurrency Invariant Evidence

并发 witness 保留：Protection 取得 risk-increasing BUY row lock 后，Fill path 必须等待，
并最终看到 `CANCELLED`。

```python
h.protection.after_risk_reducing_orders_lock = hold_after_orders
close = asyncio.create_task(h.protection.evaluate(...))
await orders_locked.wait()
fill = asyncio.create_task(h.execution.process_open_orders(...))
await asyncio.sleep(0)
assert not fill.done()
release.set()
protection, fills = await asyncio.wait_for(asyncio.gather(close, fill), timeout=5)
```

`fills == []`（fill path 未产生 BUY fill）作为该 witness 的结果断言保留。
hook 的真实锁语义由 N01-G4-INV-01 的 PostgreSQL lock evidence 独立证明，本次不重构该部分。

## 8. Verification

全部命令在 `E:\Documents\MarketPulse-AI-n01-val-fix-03`（clean worktree @ `14f387a`）执行；
`PYTHONPATH=backend/src`、`py -3.14`（Windows）、PostgreSQL = Docker `marketpulse-postgres`。

| # | 验证项 | 结果 |
|---|---|---|
| 1 | 目标测试单独执行 | `1 passed` |
| 2 | 目标测试重复 **20/20** | `20 passed / 0 failed` |
| 3 | `test_group4.py` run1 / run2 | `77 passed` / `77 passed` |
| 4 | `test_n01_runtime_resource_lifecycle.py`（FIX-01） | `6 passed` |
| 5 | `test_n01_okx_paper_safety.py`（N01-B） | `4 passed` |
| 6 | `test_group2.py` | `30 passed` |
| 7 | `test_group3.py` | `16 passed` |
| 8 | full backend run3（带 DB 会话监控） | `173 passed` |
| 9 | full backend run4（带 DB 会话监控） | `173 passed` |
| 10 | `py -3.14 -m ruff check backend/src backend/tests scripts` | `All checks passed!` |
| 11 | `py -3.14 -m compileall -q backend/src backend/tests` | rc=0 |
| 12 | `git diff --check`（worktree） | rc=0 |

### 8.1 Full-suite 环境干扰事故（必须准确记录）

本窗口的 full-suite 门**首次尝试即被外部进程污染**，前后共 3 次观测：

| 尝试 | 时间 | 结果 | 归因 |
|---|---|---|---|
| `full_run1` | 01:37–01:41 | `173 passed` | 无并发监控，**不作为验收证据** |
| `full_run2` | 01:41 | 被 SIGTERM，日志截断（当日志中已出现 5 个 `F`，位置映射为 `test_group4.py` 的 #25 / #28–#31） | 无完整 traceback（被中断），不可用 |
| `full_run2b` | 01:52–01:56 | `10 failed, 163 passed`（**traceback 已保存**） | 见下 |
| `full_run3` | 01:59–02:02 | `173 passed` | 监控下无外来写者 ⇒ 采信 |
| `full_run4` | 02:03–02:07 | `173 passed` | 监控下无外来写者 ⇒ 采信 |

`full_run2b` 的 10 个失败全部是 `open_position()` 内
`assert result.status is IntentStatus.EXECUTED` 得到 `PLAN_REPLACED`
（9 个在 `test_group3.py`：`test_scenarios_f_j_capacity_and_cross_symbol_account_lock`、
`test_limit_buy_lifecycle_duplicate_cancel_and_settlement_rollback`、
`test_pending_buy_exposure_fee_reservation_equity_marks_and_reconciliation`、
`test_limit_fill_time_plan_state_and_buy_invalidation_guards`、
`test_fg_a_cancel_wins_authoritative_order_reload_and_reservation_isolation`、
`test_fg_a_action_time_clock_bbo_and_plan_guards_after_controlled_order_lock_wait`、
`test_standalone_reconciliation_uses_real_repeatable_read_read_only_transaction`、
`test_standalone_reconciliation_account_order_cancellation_race_uses_one_snapshot`、
`test_standalone_reconciliation_failure_cleans_up_owned_read_only_transaction`；
1 个在 `test_group4.py::test_stop_loss_and_take_profit_protective_exit`）。

**根因 = 并发外来写者，不是本 Fix 的代码变更。** 证据：

1. 进程取证：`E:\Documents\MarketPulse AI\.venv\Scripts\python.exe -m pytest backend/tests
   -q --tb=short` 两个进程（PID 32384 redirector stub / PID 33620 实际解释器），
   `CreationDate = 2026-09-11 01:52:01`，父进程 = `bash.exe -c "__codebuddy_payload=…"`
   （即**另一个 WorkBuddy/CodeBuddy 会话窗口**通过 Bash 工具发起），与 `full_run2b`
   （01:52:00–01:56:15）**完全重叠**。
2. 症状签名：`PLAN_REPLACED` 只可能由**另一个进程**在本进程 `persist_trade_plan()` 与
   `execute()` 之间替换同 `(run_mode, instrument_id)` 的 ACTIVE plan 造成；
   `Harness.clean()` 又会整表清空 `RunMode.REPLAY` 行 ⇒ 两个 full suite 同库并发必然互相破坏。
3. 交叉对照：同一 branch 上 `test_group4.py` 单独 `77 passed ×2`、G2 `30`、G3 `16`、
   N01-B `4`、lifecycle `6` 全绿；run3 / run4 在同一 branch、同一 DB 上均 `173 passed`。
4. 该外来进程自 01:57 起 CPU 冻结在 15.8 s（10 分钟无进展）→ 僵死，但其 01:52–01:56 的
   活跃窗口与失败窗口完全吻合。

采信证据：`full_run3` / `full_run4` 两次**连续** PASS，且运行期间以每 5 s 采样
`pg_stat_activity`（`backend_type='client backend' AND datname='marketpulse'`）记录客户端会话，
全程最多 2 个（采样器 psql + 被测套件自身），**无第三者写者**。

### 8.2 由此产生的项目级观察（out-of-scope，未修）

本仓库全量套件使用**单一共享 PostgreSQL 数据库**且测试会整表清空 `REPLAY` 行，
因此**任何两个并发会话在全量套件层面必然互相破坏**。建议后续另开窗口评估
（仅记录，不在本 Fix Scope 内，未做任何改动）。

## 9. Production Code Changed

```text
Production Code Changed = NO
```

`git diff --name-only -- backend/src backend/alembic scripts DECISIONS.md PRODUCT_REQUIREMENTS.md`
为空。`scripts/n01_g4_inv_race_diagnostic.py` 未复制、未引入。

## 10. Files Changed

| 文件 | 变更 |
|---|---|
| `backend/tests/test_group4.py` | `+58 / −9`：目标测试改为 `order_id` identity + 强化断言；同构 site `test_stop_loss_cancels_pending_add` 最小修正 |
| `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md` | 新增（本文件） |
| `PROJECT_STATE.md` | 最小状态同步 |
| `AI_CONTEXT.md` | 最小状态同步 |

## 11. Acceptance Criteria（VF03-01 … VF03-18）

| AC | 状态 | 依据 |
|---|---|---|
| VF03-01 failing assertion 不再仅按非唯一 `plan_id` 读取 pending order | PASS | §5.1 |
| VF03-02 exact pending BUY 以 `order_id` 标识 | PASS | §5.1 |
| VF03-03 exact pending BUY `status == CANCELLED` | PASS | §5.2 |
| VF03-04 pending BUY `reserved_cash == 0` | PASS | §5.2 |
| VF03-05 protective SELL `status == FILLED` | PASS | §5.2 |
| VF03-06 `protection.cancelled_order_ids` 含 pending BUY | PASS | §5.2（`== [pending_order.order_id]`） |
| VF03-07 `position.quantity == 0` | PASS | §5.2 |
| VF03-08 并发 fill task 未返回 BUY fill | PASS | §5.2 / §7（`fills == []`） |
| VF03-09 仅存在原始 BUY entry fill | PASS | §5.2（`len(buy_fills) == 1` + `order_id` 不等） |
| VF03-10 reconciliation PASS | PASS | §5.2（`report.ok`） |
| VF03-11 并发 witness 保留 | PASS | §7 |
| VF03-12 targeted test audit 完成 | PASS | §6 |
| VF03-13 未改 production code | PASS | §9 |
| VF03-14 Group4 focused 可重复 PASS | PASS | §8 行 3（`77 passed ×2`） |
| VF03-15 N01-VAL-FIX-01 tests PASS | PASS | §8 行 4（`6 passed`） |
| VF03-16 N01-B tests PASS | PASS | §8 行 5（`4 passed`） |
| VF03-17 full backend **2 consecutive PASS** | PASS（有条件的证据说明） | §8 行 8/9（run3 / run4 监控下 `173 passed`）；§8.1 说明 run1/run2/run2b 为何不可采信 |
| VF03-18 Ruff / compileall / diff-check PASS | PASS | §8 行 10–12 |

## 12. Completion State

```text
N01-G4-INV-01  = REVIEW PASS / Case B
N01-VAL-FIX-03 = VALIDATED / AWAITING REVIEW

N01-A          = ACCEPTED / COMPLETE      （未改变）
N01-B          = ACCEPTED / COMPLETE      （未改变）
N01 overall    = NOT ACCEPTED             （未改变）
N01-C          = NOT STARTED              （未开窗）
```

未 merge `main`、未 closeout `N01-VAL-FIX-01` / `N01-VAL-FIX-02` / `N01-VAL-FIX-03`、
未开始 `N01-C`。
