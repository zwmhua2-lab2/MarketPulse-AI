# AI_CONTEXT — MarketPulse AI 上下文入口

> 本文件是 AI 开发工作的**上下文入口（Context Index）**，不是项目 Spec 的复制。
> 任何新的 AI / Codex 窗口应先读本文件建立上下文，再按下方 Source of Truth 顺序读取真实事实。
> 本文件是入口和索引，**不是**比代码或已批准决策更高的事实源。

## 1. Project Identity

| 字段 | 值 |
|---|---|
| Project | MarketPulse AI（BTC/ETH 量化纸面交易终端，Modular Monolith） |
| Current Acceptance Group | G5-1 ACCEPTED（Deterministic Replay Foundation） |
| Accepted Main SHA | `82faf76cde1ddb99e15c6c524709df446ff8c78f` |
| Current State | `G5-1 ACCEPTED / READY FOR G5-2 DESIGN` |
| Last Accepted Group | G5-1（Deterministic Replay Foundation） |

- G1–G4 acceptance 状态：`ACCEPTED` / `ACCEPTED` / `ACCEPTED` / `ACCEPTED`。
- G5-0 acceptance 状态：`ACCEPTED`（G5 feature implementation = NOT STARTED）。

## 2. Source of Truth（事实源优先级，从高到低）

1. 当前真实代码 / schema / migrations / tests
2. `PROJECT_STATE.md`
3. `DECISIONS.md`
4. 已批准的当前 Group Spec / Acceptance Contract
5. `dev_log/` / acceptance evidence
6. `AI_CONTEXT.md`（本文件）
7. 聊天记录 / AI 历史回答

**核心原则：聊天内容不能覆盖 repository truth。** 旧聊天、模型记忆、人工转述只能作为导航信息，不能直接作为实现依据。

## 3. Frozen Architecture / Invariants（G5 不得静默修改）

以下边界已从当前 accepted repository 核实，G5 实现不得静默改变：

1. **Paper Trading only**；不启用 Live Trading。
2. **AI 为 advisory（建议层）**：AI 仅输出分析建议；Paper execution 只能由程序化 Trade Plan / Execution Intent 驱动，AI 不得直接绕过 Risk / Execution。
3. **Risk Engine 保持 authoritative**：所有风险增加动作（BUY / ADD / OPEN BUY Limit Fill）必须经过唯一程序化 `SystemRiskGate`；SELL 风险降低动作不受此限。
4. **责任边界不得被 G5 静默重构**：
   `Market Data → Scanner → Candidate/Watchlist → AI Analyst → Trade Plan → Risk Engine → Execution → Position Manager → Ledger`。
5. **SPOT / SWAP 语义不得混淆**：二者是严格不同的 market type，使用不同 `market_type` / `instrument_id`。
6. **当前 Spot Paper 能力边界不得扩大**：V1 仅支持 Spot Paper 的 LONG 风险计划；`SHORT_BIAS` 只保留分析记录，绝不产生 Short Execution。
7. **G4 Position Safety / Recovery 语义不得被回归破坏**：Operator Intent 与 System Derived State 分离；PostgreSQL 为 Restart Recovery 唯一事实源；SL/TP 为 Trigger Price；Protective Exit 一律以 Fresh Best Bid − slippage 成交；不伪造停机期间历史 Fill。
8. **`TradePlan.invalidation` = advisory text**（AI/human-readable，非 machine-executable condition；Runtime 不得解析其自然语言）。
9. **`stop_loss` = 唯一 machine-enforceable hard invalidation**。
10. **架构冻结**：Python/FastAPI/asyncio backend + React/TypeScript/Vite frontend + PostgreSQL（Docker）；Modular Monolith；默认 `LOCAL_ONLY=true`、`RUN_MODE=TEST`、监听 `127.0.0.1`；Secret 不进入 Git / Frontend / API 返回。

> 若后续仓库事实已明确改变上述任一边界：以仓库事实为准并报告差异，不把本文件文本当成高于 repository truth 的事实源。

## 4. Current Group Boundary

| 字段 | 值 |
|---|---|
| Current Group | G5-1 |
| Previous accepted boundary | G4 |

- G4 **没有**提前实现完整 Replay / ReplayClock Engine。
- 仓库中仅存在：`Clock` Protocol 的 `ReplayClock` 实现（`backend/src/marketpulse/clock.py`）与 `RunMode.REPLAY` 枚举（`config.py`）——这是既有 Clock 边界，**不是**完整回放引擎。
- 完整 Replay 工作从 G5 才允许开始。
- **G5-0 本身仍然禁止实现 Replay。**

## 5. Required Context Pack（每个任务开始前必须建立）

每个执行任务开始前必须知道：

- Group / Task / Acceptance Batch
- Accepted Main SHA + Task Base SHA
- Current Branch
- Current Scope / Out of Scope
- 已批准的 Spec / Acceptance Contract
- 相关 frozen decisions（见 `DECISIONS.md`）
- 相关架构 invariants（见本文件第 3 节）
- 必需 source files / docs
- Acceptance Criteria

**禁止依赖**：「上一个聊天应该知道」「前一个 AI 说已经做了」「我记得这个功能是……」。

## 6. Next Step Entry（下一步工作入口）

- G5-0 `ACCEPTED`：`AI_CONTEXT.md` 为上下文入口；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- G5-1 `ACCEPTED`：Deterministic Replay Foundation 已验收，implementation acceptance basis = `34da62a0cc9dbe95b95faadb770fbd06179a6975`。
- 下一步 = G5-2 Trading Replay Integration DESIGN（G5-2 = `NOT STARTED`，须另行授权，不得提前定义或实现）。
- 具体 In Progress / Blocked 状态见 `PROJECT_STATE.md`。
