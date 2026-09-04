# Approved Decisions

- Group 1 使用 Modular Monolith。
- Backend/Frontend 本地运行，PostgreSQL 使用 Docker，默认监听 `127.0.0.1`。
- Market data 采用 Raw Adapter → Normalized Data 边界。
- `SPOT` 与 `SWAP` 是严格不同的 market type；衍生品上下文通过明确关联提供。
- Hot Score 仅用于 Universe/Priority，不进入 Buy/Sell 逻辑。
- G3 采用单一可配置 Primary AI Provider 边界；V1 没有自动 model fallback、投票或多模型 reviewer。AI 仅输出分析建议，Paper execution 只能由程序化 Trade Plan/Execution Intent 驱动。
- G3 V1 仅支持 Spot Paper 的 LONG 风险计划；`SHORT_BIAS` 只保留分析记录，绝不产生 Short Execution。
