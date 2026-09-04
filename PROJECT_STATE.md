# MarketPulse AI Project State

## Current Group

Acceptance Group 3 — AI Decision + Trade Plan + Paper Execution + Account + Position + Ledger

## Completed

- 空工作区 Git 初始化。
- Foundation、Provider boundary、标准化模型、Universe 初版实现已建立。
- Backend/Frontend、PostgreSQL Docker、Alembic migration cycle、Auth、OpenAPI/type generation 已真实验证。
- OKX Spot/Swap REST identity、Trade/BBO/Kline WebSocket、OI/Funding、freshness、重连与 Universe 已真实验证。
- Group 1 已完成人工 Acceptance Review #1，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 2 已完成人工 Acceptance Review #2，正式结果为 `PASS WITH NON-BLOCKING NOTES`。

## In Progress

- 无；Group 3 已通过人工 Acceptance Review #3（`PASS WITH NON-BLOCKING NOTES`），已建立 G3 Accepted Baseline；未进入 G4 / G5。

## Blocked

- 无影响 Group 1 完成的阻塞。

## Current Architecture Baseline

- Python/FastAPI/asyncio backend；React/TypeScript/Vite frontend；PostgreSQL via Docker；SQLAlchemy/Alembic。
- Raw Adapter → Normalized Data → 后续 Derived Features。
- 默认 `LOCAL_ONLY=true`，默认 `RUN_MODE=TEST`。
- OKX Spot 与 Swap 使用不同 `market_type` 和 `instrument_id`；Swap 的衍生上下文不得当作 Spot Instrument。

## Current Runtime Facts

- 初始现场为空目录，Git 已初始化。
- 未加载 Live Trading Secret，未执行交易动作。
- G2 使用内存增量 Rolling State；PostgreSQL 仅保存 Derived Observation、Market Event、Append-style Signal Timeline、Symbol State、State Transition 与 Strategy Candidate。
- G2 Event Runtime 使用有界 asyncio 优先队列（默认 2048）与有限 worker pool（默认 4）；同 `instrument_id` 串行、不同标的可并行。
- G3 使用不可变 Decision Snapshot、Provider-neutral AI boundary、一次调用最多一次 retry、版本防陈旧守卫与有界 AI Queue。AI 不拥有订单、仓位、账户或账本写权限。
- G3 仅 Paper Spot：Order/Fill/Position/Account/Ledger/Outbox 在同一 PostgreSQL transaction 中更新；账户行锁保护跨标的现金竞争。

## Known Issues

- OKX Liquidation context 当前保留 boundary，并按真实 Provider 能力标记 `UNAVAILABLE`/`null`，未伪造数据。
- FastAPI TestClient 产生上游 deprecation warning；不影响测试结果，后续可随依赖升级处理。
- Liquidation Provider 仍按真实能力明确为 `UNAVAILABLE`；未引入第三方 Liquidation 系统。
- G2 不包含 AI Decision、Trade Plan、Order、Fill、Position、Account、Ledger、Dashboard 或任何 Live Trading。
- 真实 OpenAI Provider Contract Smoke = `NOT VERIFIED`：本地 `OPENAI_API_KEY` 为 `MISSING`。测试使用 deterministic Fake Provider；真实 OKX BBO 已作为 TEST Paper execution-time context 验证。
- G3 不包含 Live、Short Execution、Contract、Leverage、SL/TP P0 Runtime、Recovery、Emergency Stop、Dashboard、Replay Engine、Performance、Batch AI Review 或 WeCom。
- 真实 AI Provider（Real AI Provider）集成验证 = `DEFERRED`：当前仅以 deterministic Fake Provider 完成自动测试；真实 OpenAI Provider Contract Smoke = `NOT VERIFIED`（本地 `OPENAI_API_KEY` 为 `MISSING`）。
- G3 Basic Reconciliation（Reserved Cash / Reserved Asset / Position Quantity / Available Cash）已以 G3 PostgreSQL 场景测试补验，结果 `PASS`。
- 长时间真实市场运行与自然特殊行情覆盖延后至后续 Runtime / `LIVE_PAPER` Soak；不构成 G2 Fail。

## Group 2 Current Result

- Rolling Feature Engine、Structure Analyzer、Opportunity Scanner、Market Event、Signal Timeline、Event Runtime、Symbol State Machine 与四类 Strategy Candidate 已实现。
- State Machine 仅实现 `IDLE`、`DETECTED`、`WATCHING`、`SETUP` 及必要退回；预留未来状态优先级，不实现 Group 3/4 业务。
- G1 AC #19 已以真实 OKX reconnect smoke + 可控重复业务 Event persistence fixture 补验；结果见 G2 开发日志。
- Group 2 = `ACCEPTED`；Acceptance Result = `PASS WITH NON-BLOCKING NOTES`；人工 Acceptance Review #2 已完成。

## Acceptance Record

- Group 1 = `ACCEPTED`。
- Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- 人工 Acceptance Review #1 已完成。
- AC #19 = `DEFERRED TO GROUP 2`；这不是 Group 1 FAIL，也不要求在 Group 1 提前实现 G2 功能。
- G1 AC #19 = `PASS / CLOSED`。
- Group 2 = `ACCEPTED`。
- Group 2 Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- 人工 Acceptance Review #2 已完成。
- Group 3 = `ACCEPTED`。
- Group 3 Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- 人工 Acceptance Review #3 已完成。
- Real AI Provider Integration = `DEFERRED`。
- G3 Basic Reconciliation = `PASS`。
- 当前未进入 G4 / G5。
