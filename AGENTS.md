# MarketPulse AI 工作纪律

- Architecture Frozen：Backend 使用 Python + FastAPI，Frontend 使用 React + TypeScript + Vite，采用 Modular Monolith。
- 本项目严格按已批准的 Acceptance Group 执行，不扩大 Scope，不自行改变业务规则或架构。
- 开始工作前检查 `PROJECT_STATE.md`、相关 `dev_log` 与当前 Git 状态。
- 测试和真实验证必须实际执行；证据不足时标记 `NOT VERIFIED`，不得伪造 PASS。
- Backend 默认只监听 `127.0.0.1`，Secret 不进入 Git、不进入 Frontend、不通过 API 返回。
- Group 1 不实现 Scanner、Strategy、AI、Order、Position、Ledger、Replay、Dashboard 或 Live Trading。
- 完成每个 Group 后维护 `PROJECT_STATE.md`、`DECISIONS.md` 和 `dev_log`。

