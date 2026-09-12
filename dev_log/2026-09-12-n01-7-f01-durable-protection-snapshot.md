# N01-7-F01 — Durable OPEN-Position Protection Snapshot

- Date: 2026-09-12
- Task: N01-7-F01｜durable OPEN-position protection snapshot（Candidate A）
- Branch: `fix/n01-7-f01-durable-protection-snapshot`
- Worktree: `E:\Documents\MarketPulse-AI-n01-7-f01-wt2`（重建于本批，见 §9）
- Status: `IMPLEMENTED / AWAITING REVIEW`（**未**自行 Acceptance；**未** merge `main`）

## 1. Task / Scope / Out of Scope

**Goal**：让一个 OPEN LONG 的 stop-loss / take-profit 保护权威**独立于**其来源 TradePlan 的 TTL 存活——在 G3 结算时把 SL/TP 原子固化到 `positions` 行，G4 的 protection / resume / recovery / reevaluation / reconciliation 统一从该 snapshot 读回。TradePlan TTL 仍继续约束 risk-increasing 新鲜度（BUY / ADD / pending limit fill），但不再终止既有持仓的保护。

**Approved contract change（Candidate A，来自 N01-7-F01 设计门）**：

```text
TradePlan TTL controls risk-increasing freshness only.

A valid protection snapshot, atomically attached to the current OPEN Position,
remains authoritative until:
1. an approved successor protection snapshot is durably committed, or
2. the Position becomes flat.

OPEN Position with missing/corrupt protection snapshot
→ cancel risk-increasing BUY → POSITION_UNPROTECTED → SAFE_MODE / Resume refused
→ explicit risk-reducing manual close remains available
```

**Frozen acceptance contract（保护层级合法性）**：仅当「SL/TP 有限 且 `stop_loss < take_profit`」才接受；**无 positivity 规则**（有序的非正价格对合法）。该规则与 `plan_business_errors` 完全一致，避免「计划层接受、持仓层判无保护」的跨层翻转。

**允许修改**：`backend/src/marketpulse/{db,g3,g4,g5}` 与新增 migration、`backend/tests/test_group4.py`（F01 用例 + Case B 契约更新）、`backend/tests/test_se_02a_edge_persistence.py`（HEAD_REVISION 推进）、本 devlog。

**Out of Scope**：N01-7 实际重跑、N01-8、Integrated Runtime Host、Real AI、Live Trading、策略优化、自动强平政策、新 Position subsystem。

## 2. Repository Truth（CIP-02 / CIP-03）

| 项 | 实测值 | 来源 |
|---|---|---|
| Accepted Main / Task Base SHA | `af81414160248c97f59a63b31fe615ea8ae14bbe` | `git ls-remote origin refs/heads/main` + `git rev-parse main` |
| 开工 HEAD | `af81414…`（== main，**无基线漂移**） | `git rev-parse HEAD` |
| Migration heads | `20260912_0006`（单 head） | `alembic heads` |
| Python | `py -3.14` → `C:\Users\hua\AppData\Local\Programs\Python\Python314\python.exe` | 解释器合同 |
| 全量测试 | `290 passed, 1 warning` | `pytest backend/tests -q -p no:randomly`（`PYTHONPATH=backend/src`） |

## 3. Implementation

### 3.1 Schema（additive migration `20260912_0006`）

`backend/alembic/versions/20260912_0006_position_protection_snapshot.py`（`down_revision = 20260911_0005`）：
- 5 个 nullable `positions` 列：`protection_plan_id` / `protection_plan_version` / `protection_stop_loss` / `protection_take_profit` / `protection_updated_at`。
- 3 个 CHECK：`ck_positions_protection_complete`（全 NULL 或全 NOT NULL）、`ck_positions_protection_version_positive`（`>= 1`）、`ck_positions_protection_prices`（有限 + `stop_loss < take_profit`）。
- 有限性用 `x < 'Infinity'::float8` / `x > '-Infinity'::float8` 表达（拒绝 NaN/±Inf）。

### 3.2 共享契约 `g3/protection_snapshot.py`

`authority_from_plan` / `read_position_protection` / `apply_position_protection` / `clear_position_protection`。写侧在 G3 经济事务内，故模块置于 g3（依赖方向 `g4 → g3`，放 g4 会形成环）。`authority_from_plan` 用 try/except 返回 None（fail closed，永不抛）。

### 3.3 各层接线

- `g3/service.py`：`_settle_order` 对 BUY 在同事务内 `apply_position_protection`；平仓 `clear_position_protection`；`_limit_fill_plan_guard` 返回 `(reason, plan)` 以便 limit fill 复用已验证 plan 派生权威。
- `g4/planning.py`：新增 `resolve_open_position_protection`（TTL-only carve-out：plan 有效则 plan 优先；否则仅当 plan「expired 且 otherwise-valid」才回落 snapshot）；`PlanManager.replace` 在 `_replace_in` 同事务切换/清除 snapshot（覆盖 UPDATE_STOP / UPDATE_TP / REPLACE_PLAN / ADD）。
- `g4/protection.py`：`evaluate` / `_close_position_in` 读 snapshot；incident reason 改为 `open_position_without_durable_protection`；退出 identity 绑定真实权威。
- `g4/control.py`：resume / safe-mode gate 读 snapshot。
- `g4/reconciliation.py`：新增 invariant #13 `open_position_protection_survives_plan_ttl`。
- `g5/replay.py`：`schema_head` = `20260912_0006`。

## 4. Fix Acceptance Criteria → Evidence

| AC | 含义 | 证据 |
|---|---|---|
| 1 | market/limit BUY fill 同事务建 Position+snapshot | `test_f01_01` / `test_f01_02` |
| 2 | 写入失败 Fill/Position/Account/Ledger/snapshot 全回滚 | `test_f01_22`（新增）+ `test_protective_settlement_failure_rolls_back_atomically` + `test_plan_replace_failure_rolls_back` |
| 3 | 过期后 new BUY/ADD/pending fill 仍拒绝/取消 | G3 `_limit_fill_plan_guard`（`PLAN_EXPIRED` 表驱动用例 `test_group3`）+ Case H stale buy |
| 4 | 过期 plan 下 snapshot 仍给 HOLD/SL/TP | `test_f01_06` / `test_f01_07` / `test_f01_08` |
| 5 | state_version 前进 snapshot 仍有效 | `test_f01_17` + Case G/H |
| 6 | UPDATE_STOP/UPDATE_TP/REPLACE_PLAN 与 snapshot 原子 | `test_f01_18` / `test_f01_19` / `test_f01_22`（`_replace_in` 同事务） |
| 7 | 过期后 restart：fresh→RUNNING/HOLD、below-stop→退出 | `test_f01_10` + N01-C restart-recovery（全绿） |
| 8 | missing/corrupt snapshot → UNPROTECTED/SAFE_MODE/Resume refused/pending cancel | `test_f01_13` / `test_f01_14` / `test_f01_15` / `test_f01_16` / `test_f01_21` + 既有 safe-mode 用例 |
| 9 | 无保护下 manual close 仍可用 fresh BBO | `test_f01_23`（新增） |
| 10 | partial close 保留、full close 清除、重开不复用旧权威 | `test_f01_03` / `test_f01_04` |
| 11 | reconciliation 检测缺失/非法但不把 TTL 本身判无保护 | `test_f01_11` / `test_f01_12` |
| 12 | entry/ADD/replacement/close crash boundary | `test_f01_22` + N01-C 跨进程 restart + 既有 rollback 用例 |
| 13 | alembic/regressions/ruff/compileall/diff-check 全真 PASS | §5 |
| 14 | 无 Real AI / Live Trading / Integrated Runtime Host 依赖 | 结构事实（无新 service/scheduler/provider） |

## 5. Verification（真实验证，全部实际执行）

- **Full backend**：`PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q -p no:randomly` → **290 passed, 1 warning**（0 failed）。
- **F01 子集**：`-k "f01_ or case_b"` → 24 passed（F01-01..F01-23 + Case B）。
- **ruff** `check backend/src backend/tests` → `All checks passed!`；`compileall` → exit 0；`git diff --check` → exit 0。
- **alembic**：`alembic heads` = `20260912_0006`（单 head）；`alembic current` = `20260912_0006`。
- **无 disposable DB 残留**：`pg_database LIKE 'marketpulse_%'` = 0。

### 5.1 自审发现并修复的缺陷（Reconciliation connection leak）

全量回归首次暴露 `test_n01_b_freshness_boundary_blocks_risk_increasing_actions_and_fails_closed` 确定性失败（`cleanup.released=False, elapsed_seconds≈1.08`）。在 `af81414` 基线 worktree 上该测试 4/4 PASS、F01 分支 4/4 FAIL，排除 flake。

根因：`reconciliation.py` 的 invariant #13 循环被放在 `async with sessions() as session, session.begin():` 块**之外**（4-space 缩进），在已关闭的 session 上调用 `load_active_plan`/`load_valid_long_active_plan` → SQLAlchemy 重新 checkout 一条永不归还的连接 → 泄漏一条 client backend，被 N01-B 的 ownership cleanup gate 捕获。

修复：把 invariant #13 的 DB 读取移入既有 REPEATABLE READ 事务内（同 session、同快照），块外只保留对 `invariants`/`diagnostics`/`details` 的报告折叠。修复后 N01-B 通过、全量 290 passed。

## 6. Residual / Known Gaps（不扩大、不隐瞒）

- `g3/service.py` 的 `process_setup` / `persist_trade_plan` 未接入 G2 runtime 的「新 plan while position OPEN」路径：只有 `PlanManager.replace`（reevaluation / ADD）会切换 snapshot。若未来 G2 在持仓存续期间直接创建新 ACTIVE plan（不经 `replace`），snapshot 不会随之更新。此为**已知缺口**，不在本批 Scope；本批不静默扩展。
- 退出 identity：无权威时（unprotected manual close）`plan_id` 仍回退为 `""`（沿用既有语义），未实现设计文档「Execution / Manual-Close Impact」中「至少绑定 position_id/trade_id」的建议——该条不在 14 条 Fix AC 内，留作后续。
- **主库 `marketpulse` 现为 `20260912_0006`**（非 `20260905_0004`）。与 SE-02A 不同，F01 迁移落在核心表 `positions` 上，G2/G3/G4/N01 测试全部经 `marketpulse` 库读写该列，故运行本套件前主库必须先 `alembic upgrade head`。这是 F01 触及核心表的事实性前提，非「未经授权改生产」。

## 7. Git / GitHub Review 工作流

- 遵循 AGENTS.md：commit → push branch → **不 merge main**，返回 branch / commit SHA / report。
- 本 devlog、`DECISIONS.md`（TTL↔protection-lifetime 权威分离决策）、`PROJECT_STATE.md` / `AI_CONTEXT.md` 同步归属：devlog 本批落地；`DECISIONS.md` / `PROJECT_STATE.md` / `AI_CONTEXT.md` 留待**人工验收 PASS 后**窗口同步（CIP-09 / AGENTS.md），避免在未验收时把 contract change 写入 "Approved Decisions"。

## 8. Files Changed

- `backend/alembic/versions/20260912_0006_position_protection_snapshot.py`（新增）
- `backend/src/marketpulse/db/models.py`
- `backend/src/marketpulse/g3/models.py`
- `backend/src/marketpulse/g3/service.py`
- `backend/src/marketpulse/g3/protection_snapshot.py`（新增）
- `backend/src/marketpulse/g4/control.py`
- `backend/src/marketpulse/g4/planning.py`
- `backend/src/marketpulse/g4/protection.py`
- `backend/src/marketpulse/g4/reconciliation.py`
- `backend/src/marketpulse/g5/replay.py`
- `backend/tests/test_group4.py`
- `backend/tests/test_se_02a_edge_persistence.py`

## 9. 环境备注（本批 worktree 重建）

本批进行过程中，一次 `git worktree remove`（清理基线验证用临时 worktree）破坏了原 F01 worktree 的 git 元数据（`.git/worktrees/` 注册丢失），但**工作树文件完好**。已先做文件系统级全量备份（`E:/Temp/f01_files_backup`），随后在 `E:\Documents\MarketPulse-AI-n01-7-f01-wt2` 以 `git worktree add <path> fix/n01-7-f01-durable-protection-snapshot` 重建 clean worktree 并复刻全部 12 个变更文件。`git ls-remote` 确认 `main` 仍 `af81414`，无远端漂移。
