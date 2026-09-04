# MarketPulse AI Project State

## Current Group

Acceptance Group 4 — Position Safety + Recovery

## GitHub Repository

- GitHub Repository Full Name: `zwmhua2-lab2/MarketPulse-AI`
- GitHub Repository URL: https://github.com/zwmhua2-lab2/MarketPulse-AI
- Visibility: `PRIVATE`
- Default Branch: `main`
- Latest Accepted Source Commit: `ab70a72b80be3a4529835b8a3dced773a7f2e986`
- Current Development Status: `G4 IMPLEMENTED / WAITING REVIEW`

## Branch / Source

- Branch: `g4-position-safety-recovery`
- Base main SHA: `15dd0f1ebdf9c8f79af81ba1aab5078bf0f99844`
- Migration Head: `20260905_0004`（`alembic current/heads` 一致）
- Real AI Provider Status: `DEFERRED`（`OPENAI_API_KEY=MISSING`；测试用 deterministic Fake Provider）

## Completed

- 空工作区 Git 初始化。
- Foundation、Provider boundary、标准化模型、Universe 初版实现已建立。
- Backend/Frontend、PostgreSQL Docker、Alembic migration cycle、Auth、OpenAPI/type generation 已真实验证。
- OKX Spot/Swap REST identity、Trade/BBO/Kline WebSocket、OI/Funding、freshness、重连与 Universe 已真实验证。
- Group 1 已完成人工 Acceptance Review #1，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 2 已完成人工 Acceptance Review #2，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 3 已完成人工 Acceptance Review #3，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- G3 Post-Acceptance Fix 与 Fix2 已人工验收，`PASS WITH NON-BLOCKING NOTES`。
- Group 4（持仓安全与恢复）已实现：Position Protection（SL/TP/Protective Exit/幂等）、Position Re-evaluation（HOLD/ADD/REDUCE/CLOSE/CANCEL_ADD/UPDATE_STOP/UPDATE_TP/UPDATE_INVALIDATION/REPLACE_PLAN）、System Safety State、Control（Pause/Resume/Emergency Stop/Emergency Recovery/Symbol Block/Manual Close/Safe Mode）、Recovery Manager（PostgreSQL SoT + Restart Recovery + Reconciliation Gate + Plan/Order Revalidation + EXECUTION_GAP）、Health Registry 与 Incident Manager。

## In Progress

- G4 已实现并完成真实 PostgreSQL 验证，等待人工 Acceptance。

## Blocked

- 无阻塞。

## Current Architecture Baseline

- Python/FastAPI/asyncio backend；React/TypeScript/Vite frontend；PostgreSQL via Docker；SQLAlchemy/Alembic。
- Raw Adapter → Normalized Data → 后续 Derived Features。
- 默认 `LOCAL_ONLY=true`，默认 `RUN_MODE=TEST`。
- OKX Spot 与 Swap 使用不同 `market_type` 和 `instrument_id`。
- G4 增加：System/Operator State 分离；统一 Risk Gate；PostgreSQL 为 Restart Recovery 唯一事实源；Protective Exit 一律以当前 Fresh Best Bid − slippage 成交（Stop/TP 仅触发价）；Position Event 追加审计；Trade.exit_reason。

## Current Runtime Facts

- G2 Event Runtime 使用有界 asyncio 优先队列与有限 worker pool；同 `instrument_id` 串行。
- G3 不可变 Decision Snapshot、Provider-neutral AI boundary、Account Row Lock 事务内写 Order/Fill/Position/Account/Ledger/Outbox。
- G4 运行时：SL/TP 不经 AI Queue；同 Symbol 串行（asyncio lock + DB row lock）；Risk Gate 锁定 runtime_control 行后决定风险增加动作是否放行；EMERGENCY_STOP 原子取消 OPEN BUY 并释放 Reservation（≠ Close All）；SAFE_MODE 锁存需显式恢复 → PAUSED → 人工 Resume。

## Known Issues

- 真实 AI Provider 集成 = `DEFERRED`（`OPENAI_API_KEY=MISSING`）。Position Re-evaluation contract 以 deterministic Fake Provider 验证，未伪造真实 AI 结果。
- Real OKX Paper Protection / Restart Recovery smoke 已用真实 BTC-USDT BBO 完成（`LIVE_PAPER`，无 Live 下单）。
- FastAPI TestClient 上游 deprecation warning 仍存在（2 处，不影响结果）。

## Group 4 Result

- G4 PostgreSQL 场景测试（`test_group4.py`）覆盖 A–U 全部验收场景 + 失败注入：`24 passed`。
- 全量 `pytest backend/tests`：`51 passed`（G1 1 + G2 5 + G3 21 + G4 24）。
- `ruff check backend/src backend/tests scripts` / `compileall` / `git diff --check`：PASS。
- `alembic current` / `alembic heads`：`20260905_0004 (head)`。

## Acceptance Record

- Group 1 = `ACCEPTED`；Group 2 = `ACCEPTED`；Group 3 = `ACCEPTED`。
- G3 Post-Acceptance Fix = `ACCEPTED`。
- Group 4 = 待人工 Acceptance（当前 `G4 IMPLEMENTED / WAITING REVIEW`）。
