# MarketPulse AI Project State

## Current Group

Acceptance Group 2 — Derived Features + Scanner + Timeline + Event Runtime + Symbol State Machine + Strategy

## Completed

- 空工作区 Git 初始化。
- Foundation、Provider boundary、标准化模型、Universe 初版实现已建立。
- Backend/Frontend、PostgreSQL Docker、Alembic migration cycle、Auth、OpenAPI/type generation 已真实验证。
- OKX Spot/Swap REST identity、Trade/BBO/Kline WebSocket、OI/Funding、freshness、重连与 Universe 已真实验证。
- Group 1 已完成人工 Acceptance Review #1，正式结果为 `PASS WITH NON-BLOCKING NOTES`。

## In Progress

- G2 前置：对齐已接受的 Group 1 Git baseline；随后开始 Group 2。

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

## Known Issues

- OKX Liquidation context 当前保留 boundary，并按真实 Provider 能力标记 `UNAVAILABLE`/`null`，未伪造数据。
- Acceptance criterion 19（重连后的持久业务记录去重）在 Group 1 无业务记录持久化对象，当前 `NOT VERIFIED`，留待后续具备记录层后验证。
- FastAPI TestClient 产生上游 deprecation warning；不影响测试结果，后续可随依赖升级处理。

## Acceptance Record

- Group 1 = `ACCEPTED`。
- Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- 人工 Acceptance Review #1 已完成。
- AC #19 = `DEFERRED TO GROUP 2`；这不是 Group 1 FAIL，也不要求在 Group 1 提前实现 G2 功能。
