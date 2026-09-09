# AI_CONTEXT — MarketPulse AI 上下文入口

> 本文件是 AI 开发工作的**上下文入口（Context Index）**，不是项目 Spec 的复制。
> 任何新的 AI / Codex 窗口应先读本文件建立上下文，再按下方 Source of Truth 顺序读取真实事实。
> 本文件是入口和索引，**不是**比代码或已批准决策更高的事实源。

## 1. Project Identity

| 字段 | 值 |
|---|---|
| Project | MarketPulse AI（BTC/ETH 量化纸面交易终端，Modular Monolith） |
| Current Acceptance Group | Acceptance Group 5 — ACCEPTED / COMPLETE |
| Accepted Main Source | Git `main` / `origin/main`；须在任务 preflight 按 CIP-02 实时读取，不以文档静态 SHA 为准 |
| Current State | `G5 ACCEPTED / COMPLETE` |
| Last Accepted Group | Acceptance Group 5（Deterministic Replay，G5-0～G5-4） |
| Current Group Branch | NONE / main accepted baseline（Group 5 已 closeout） |

- G1–G4 acceptance 状态：`ACCEPTED` / `ACCEPTED` / `ACCEPTED` / `ACCEPTED`。
- G5-0 / G5-1 / G5-2 / G5-3 / G5-4 acceptance 状态：`ACCEPTED`。
- G5 overall = `ACCEPTED / COMPLETE`。

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
| Current Group | Acceptance Group 5 — `ACCEPTED / COMPLETE` |
| Last accepted subgroup | G5-4 — `ACCEPTED`（2026-09-06 Formal Acceptance Closeout） |
| Next Group Design | `NOT STARTED` |
| Next Group name/number | `NOT YET APPROVED` |

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

### FG-D Remediation（Current）

- FG-D Acceptance Fix #1 — `COMPLETE / WAITING ACCEPTANCE`；branch
  `fix/fg-d-g2-runtime-determinism`，Task Base / current accepted main =
  `4859c8f70a484353d598f80fc2e0c2658cc50864`。
- Fix #1 仅将 F10 无界 Trade dedupe 改为全 Pipeline `8192` entries FIFO cache；F07/F09/F11
  仅增加 acceptance evidence。无 schema/migration、F07/F09/F11 production semantics、G2
  business semantics、G5 canonical replay contract、G3/G4/Live 修改；未自行 Acceptance 或 merge。

- G5-0 `ACCEPTED`：`AI_CONTEXT.md` 为上下文入口；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- G5-1 `ACCEPTED`：Deterministic Replay Foundation 已验收，implementation acceptance basis = `34da62a0cc9dbe95b95faadb770fbd06179a6975`。
- G5-2 Trading Replay Integration = `ACCEPTED`（Implementation Acceptance Basis = `2a7d0c858c70f21215a090ee3b583d341cfd84b4`；详见 `dev_log/2026-09-06-group5-2.md`「Formal Acceptance Record」）。
- G5-3 End-to-End Determinism = `ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Implementation Acceptance Basis = `f4c07333600f605cbcc5e34b591659feb1b1f318`；Review Fix #1 = VERIFIED；详见 `dev_log/2026-09-06-group5-3.md`「Formal Acceptance Record」）。
- G5-4 Deterministic Replay Evaluation = `ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Production Implementation Basis = `8678b2927a2d029ac0767e49acc9e0732c329bfa`；Self Review Fix #1 Evidence = `fe610c1f23457ff11f2d5c8654e9de0aec4ff289`；branch `g5-replay-evaluation` = historical accepted branch；详见 `dev_log/2026-09-06-group5-4.md`）。
  - 关键事实源：`backend/src/marketpulse/g5/evaluation.py`（新增）、`backend/src/marketpulse/g5/replay.py`（additive `evaluation` 字段与评估步骤）、`backend/src/marketpulse/g5/canonical.py`（未修改）。
  - G5-4 冻结边界：不持久化 Evaluation Report、不引入 `replay_run_id` / `backtest_id`、不新增 schema、
    不修改 G3 accounting semantics、不做 MFE/MAE/drawdown/equity curve/win rate/expectancy/R-multiple/Sharpe/Sortino/profit factor。
- G5 overall = `ACCEPTED / COMPLETE`（G5-4 已于 2026-09-06 Formal Acceptance Closeout）。Next Group Design = `NOT STARTED`；Next Group name/number = `NOT YET APPROVED`。
- 具体 In Progress / Blocked 状态见 `PROJECT_STATE.md`。
