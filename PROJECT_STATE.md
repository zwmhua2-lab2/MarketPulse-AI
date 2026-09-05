# MarketPulse AI Project State

## Current Group

Acceptance Group 5 — （G5-0 已 ACCEPTED；G5 feature 未开始）

## GitHub Repository

- GitHub Repository Full Name: `zwmhua2-lab2/MarketPulse-AI`
- GitHub Repository URL: https://github.com/zwmhua2-lab2/MarketPulse-AI
- Visibility: `PRIVATE`
- Default Branch: `main`
- Accepted Main SHA: `c366d078e86d2ee5637c81a88cc7773686646556`
- Current Development Status: `G5 initialized / G5-0 complete / G5 feature implementation not started`

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

- G5-0（上下文初始化）已完成：落地 `AI_CONTEXT.md`；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- G5 feature（Replay）实现尚未开始，等待 G5 Acceptance Batch 定义。

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

- G4 PostgreSQL 场景测试（`test_group4.py`）覆盖 A–U、失败注入、Post-Review Fix #1–#4 回归：`45 passed`。
- 全量 `pytest backend/tests`：`72 passed`，1 个既有 FastAPI/Starlette deprecation warning。
- `ruff check backend/src backend/tests scripts` / `compileall` / `git diff --check`：PASS。
- `alembic current` / `alembic heads`：`20260905_0004 (head)`。
- Restart smoke（`scripts/g4_verify_runtime.py setup/recover`）：两进程 PostgreSQL 重建 → `RUNNING`、`active_symbols=['BTC-USDT']`、`reconciliation_ok=True`。

### Post-Review Fix #1

- P0-1：AI 重估值在 provider 返回后、dispatch 前重验 DB 的 state_version / active plan(plan_id+version) / position lifecycle，变化判 STALE，记 `AIDecisionRecord.status=STALE_DECISION` + `PositionEvent(AI_REEVALUATION)`，返回 HOLD 零副作用。
- P0-2：Recovery 捕获重启前 `system_state` 锁存 SAFE_MODE；未解决 blocking incident 不得进入 RUNNING。
- P0-3：Recovery `_revalidate` 严格 §33（TTL / state_version / entry / stop-invalidation / BBO freshness），final state 非 RUNNING（SAFE_MODE/EMERGENCY_STOP/ERROR）取消残留 OPEN BUY 并释放 Reservation。
- P1-1：Recovery 与 Orchestrator 的 BBO 新鲜度判断加入 `DataQuality.FRESH`。
- P1-2：`active_symbols` 仅来自 OPEN Order / quantity>0 Position / ACTIVE Plan。
- P1-3：Reconciliation 不变量 #10 增测 closed lifecycle 后残留的风险增加 BUY（`BUY_AFTER_CLOSED_LIFECYCLE`）。

### Post-Review Fix #2

- P0-1 Recovery §33：OPEN BUY 在恢复事务内重验 current Fresh Best Ask、entry zone、stop breach、persisted symbol block 与 G3 cash/capacity；失效订单原子 cancel 并释放 Reservation，不 retroactive fill。
- P0-2 AI TOCTOU：provider 后使用 action-time clock 与重新获取的 executable BBO；最终 stale facts（state_version、expected active plan/version、position/trade lifecycle）在 PostgreSQL 行锁事务内校验并保持到 mutation commit。
- `PlanManager.replace()` 改为 expected-current conditional update；旧 plan 非当前 ACTIVE 时返回 stale，保留 `uq_trade_plans_one_active`，不再 replace symbol 下所有 ACTIVE plan。
- P1 Recovery BBO failure：OPEN Position 的 exception/missing/unusable BBO 持久化 `CORE_DATA_STALE` Incident，Health 标记 UNAVAILABLE，恢复落在非 RUNNING。
- 修复 SAFE_MODE recovery 的 blocking-incident 可达性：仅在 health/reconciliation 与 position protection durable facts 通过后，于同一控制事务 resolve 并落到 PAUSED。
- 新增 8 个真实 PostgreSQL 回归测试；真实 AI Provider 因 `OPENAI_API_KEY=MISSING` 为 `DEFERRED / NOT VERIFIED`。

### Post-Review Fix #3

- `load_active_plan()` 现只在恰好一条 ACTIVE row、payload 可由 `TradePlan.model_validate` 加载，且 payload 与 durable row 的 plan identity / run_mode / instrument / version / status / timestamps 一致时返回计划；否则 fail closed。
- 共用的 plan business validation 检查 entry-zone、SL/TP 与当前 LONG `average_cost` 的保护关系（`stop_loss < average_cost < take_profit`）；Safe Mode Recovery 与普通 Resume 都以此证明 OPEN Position 真实受保护，不能以 raw/corrupt row 或错误 RESOLVED Incident 放行。
- `safe_mode_recovery()` 仅在 durable protection、reconciliation、health 与 fresh core-data gate 均通过后，resolve blocking incident 并落到 `PAUSED`；随后 manual Resume 才可进入 `RUNNING`。
- 新增 4 个真实 PostgreSQL 回归：corrupt payload / payload identity mismatch 拒绝、可解析但 LONG protection relationship 非法拒绝、修复为有效 plan 后恢复到 `PAUSED` 并 resolve incident、错误手工 resolve Incident 后 Resume 仍拒绝直至有效保护和健康条件恢复。
- PENDING PRODUCT DECISION：V1 是否正式定义 `TradePlan.invalidation` 为 AI/human-readable advisory text，而 `stop_loss` 为唯一 machine-enforceable hard invalidation；本轮保持冻结现状，未开发自然语言 invalidation parser。

### Post-Review Fix #4

- OPEN LONG durable protection 不再要求 `stop_loss < average_cost < take_profit`；利润锁定止损（例如 cost=100、stop=110、TP=140）在 Fresh bid=120 时是有效保护。
- 保持 fail-closed：ACTIVE row 必须唯一、payload 可解析且身份一致、TTL 有效、entry zone 合法、SL/TP 有限且 `stop_loss < take_profit`。
- 新增 PostgreSQL 回归覆盖利润锁定止损的 Safe Mode Recovery → `PAUSED`、随后 manual Resume → `RUNNING`，以及 `stop_loss >= take_profit` 仍拒绝；corrupt payload、identity mismatch、expired、duplicate ACTIVE 行为不变。
- 本次验证：G4 `45 passed`、G3 `10 passed`、全量 `72 passed, 1 warning`；Ruff、compileall、`git diff --check`、Alembic current/heads 与 paper-only Restart Smoke 均通过。

## Group 5-0 Result

- G5-0（Repository Context + Context Isolation Protocol）已完成。
- 落地 `AI_CONTEXT.md`（上下文入口 / Context Index）；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- Accepted Main SHA = `c366d078e86d2ee5637c81a88cc7773686646556`（当前 main HEAD）；G4 implementation acceptance basis = `534dfad0f072553f18b8b687c20a48bf9914ee14`（G4 源码）。
- 无业务代码 / schema / API / UI / Runtime 修改；未实现 Replay / ReplayClock Engine。
- 状态：`G5-0 ACCEPTED`；G5 feature implementation 尚未开始（NOT STARTED）。

## Acceptance Record

- Group 1 = `ACCEPTED`；Group 2 = `ACCEPTED`；Group 3 = `ACCEPTED`；Group 4 = `ACCEPTED`。
- G3 Post-Acceptance Fix = `ACCEPTED`。
- Group 5-0 = `ACCEPTED`（G5 feature implementation NOT STARTED）。

### Group 4 Acceptance

- Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- G4 implementation acceptance basis = `534dfad0f072553f18b8b687c20a48bf9914ee14`。
- Position Safety + Recovery 已正式 `ACCEPTED`。
- Real AI Provider = `DEFERRED / NOT VERIFIED`（原因：`OPENAI_API_KEY` 缺失，无 `.env`；测试用 deterministic Fake Provider）。此项 non-blocking。
- Current next state = `G5 initialized / G5-0 complete`（G5 feature implementation not started）。
