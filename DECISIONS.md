# Approved Decisions

- Group 1 使用 Modular Monolith。
- Backend/Frontend 本地运行，PostgreSQL 使用 Docker，默认监听 `127.0.0.1`。
- Market data 采用 Raw Adapter → Normalized Data 边界。
- `SPOT` 与 `SWAP` 是严格不同的 market type；衍生品上下文通过明确关联提供。
- Hot Score 仅用于 Universe/Priority，不进入 Buy/Sell 逻辑。

