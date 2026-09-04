# MarketPulse AI 工作纪律

- Architecture Frozen：Backend 使用 Python + FastAPI，Frontend 使用 React + TypeScript + Vite，采用 Modular Monolith。
- 本项目严格按已批准的 Acceptance Group 执行，不扩大 Scope，不自行改变业务规则或架构。
- 开始工作前检查 `PROJECT_STATE.md`、相关 `dev_log` 与当前 Git 状态。
- 测试和真实验证必须实际执行；证据不足时标记 `NOT VERIFIED`，不得伪造 PASS。
- Backend 默认只监听 `127.0.0.1`，Secret 不进入 Git、不进入 Frontend、不通过 API 返回。
- Group 1 不实现 Scanner、Strategy、AI、Order、Position、Ledger、Replay、Dashboard 或 Live Trading。
- 完成每个 Group 后维护 `PROJECT_STATE.md`、`DECISIONS.md` 和 `dev_log`。

## GitHub Review 工作流

### Group 开发完成但尚未人工验收
Codex / Agent 应：
1. 完成 Implementation（实现）。
2. 完成自动测试 / 真实验证。
3. Self Review（自审）。
4. 修复自身发现。
5. Regression（回归）。
6. Commit 到当前 Group branch。
7. Push 当前 Group branch 到 GitHub。
8. 返回 branch、commit SHA、Completion Report。
9. 停止，不自行 merge `main`。
Reviewer 可直接从 GitHub 读取真实源码、状态文件与测试相关内容。

### 人工验收 PASS 后
回原 Group 窗口：
1. 同步 `PROJECT_STATE.md`。
2. 同步当前 `dev_log`。
3. 执行必要 Final Regression。
4. 创建 Acceptance / Baseline Commit。
5. 更新 `main` 到最新 Accepted Baseline。
6. Push `main`。
7. 保留 Group branch 作为历史证据。

### 原则
- `main` = 最新人工验收通过代码。
- Group branch = 当前开发 / 等待验收代码。
- 未经人工 Acceptance PASS，不得自行把 Group 未验收实现推进 `main`。

