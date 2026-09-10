# AI_CONTEXT — MarketPulse AI 上下文入口

> 本文件是 AI 开发工作的**上下文入口（Context Index）**，不是项目 Spec 的复制。
> 任何新的 AI / Codex 窗口应先读本文件建立上下文，再按下方 Source of Truth 顺序读取真实事实。
> 本文件是入口和索引，**不是**比代码或已批准决策更高的事实源。
> **产品级长期需求基线见 [`PRODUCT_REQUIREMENTS.md`](./PRODUCT_REQUIREMENTS.md)**（Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction）。本文件（AI_CONTEXT）是其下的上下文入口索引，不重复其产品级内容；若二者冲突，以 `PRODUCT_REQUIREMENTS.md` 的产品级定位与 `DECISIONS.md` 的已批准冻结为准。

## 1. Project Identity

| 字段 | 值 |
|---|---|
| Project | MarketPulse AI（BTC/ETH 量化纸面交易终端，Modular Monolith） |
| Current Acceptance Group | N01-B — OKX Reconnect / Freshness + Paper Safety Continuity — ACCEPTED / COMPLETE |
| Accepted Main Source | Git `main` / `origin/main`；须在任务 preflight 按 CIP-02 实时读取，不以文档静态 SHA 为准 |
| Current State | `N01-B = ACCEPTED / COMPLETE`（N01-A 亦为 `ACCEPTED / COMPLETE`；**N01 overall 仍 `NOT ACCEPTED`**） |
| Last Accepted Group | N01-B — OKX Reconnect / Freshness + Paper Safety Continuity |
| Current Group Branch | `n01-b-okx-paper-safety-continuity`（accepted historical branch；Final Acceptance Closeout 已 fast-forward 收编至 `main`；下一 Group branch 尚未建立） |

- G1–G4 acceptance 状态：`ACCEPTED` / `ACCEPTED` / `ACCEPTED` / `ACCEPTED`。
- G5-0 / G5-1 / G5-2 / G5-3 / G5-4 acceptance 状态：`ACCEPTED`。
- G5 overall = `ACCEPTED / COMPLETE`。

## 2. Source of Truth（事实源优先级，从高到低）

1. 当前真实代码 / schema / migrations / tests
2. `PROJECT_STATE.md`
3. `DECISIONS.md`
4. `PRODUCT_REQUIREMENTS.md`（产品级长期需求基线：Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction；不覆盖 `DECISIONS.md` 的已批准冻结，也不改变本列表的 repository truth 优先级）
5. 已批准的当前 Group Spec / Acceptance Contract
6. `dev_log/` / acceptance evidence
7. `AI_CONTEXT.md`（本文件）
8. 聊天记录 / AI 历史回答

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
| Current Group | N01-B — OKX Reconnect / Freshness + Paper Safety Continuity — `ACCEPTED / COMPLETE` |
| Last accepted subgroup | N01-B — OKX Reconnect / Freshness + Paper Safety Continuity (`ACCEPTED / COMPLETE`)；前一门 N01-A 亦 `ACCEPTED / COMPLETE` |
| Next Group Design | `NOT STARTED`（须另开窗口） |
| Next Group name/number | N01-5 Restart / Recovery / Reconciliation（N01-C）— not started |

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

### N01-5 Restart / Recovery / Reconciliation（N01-C）— NEXT GATE / NOT STARTED

- 状态：`NOT STARTED`，**尚未开窗、尚未批准 Spec**。
- 入口基线：`main` = N01-B accepted lineage 末端（须在 preflight 按 CIP-02 用
  `git ls-remote origin refs/heads/main` 实时读取，不以本文档静态 SHA 为准）。
- 上游已验收前提：N01-A（Deterministic Runtime + Resource Lifecycle）、N01-B（OKX Reconnect /
  Freshness + Paper Safety Continuity）。
- 不得由 N01-B 验收推断：N01 overall 验收、Continuous Runtime、N01-6 15m Smoke、N01-7 2h Soak、
  N01-8 12h Soak、Integrated Runtime Host。
- 开窗前需先批准该门的 Requirement / Scope / Out of Scope / Acceptance Criteria；不得沿用
  N01-B 的 harness 直接充当 N01-5 证据。

### N01-B OKX Reconnect / Freshness + Paper Safety Continuity

- Task Base / verified remote `refs/heads/main` = `a48673404abe256d0adb07c8139b129a54b4e7ce`；
  branch = `n01-b-okx-paper-safety-continuity`；accepted validation lineage =
  `fc168c1` → `26688a2`；isolated worktree = `E:\Documents\MarketPulse-AI-n01-b`。
- `N01-B = ACCEPTED / COMPLETE`（Independent Review `PASS`；Human Acceptance `CONFIRMED`；
  `N01-3 = ACCEPTED`、`N01-4 = ACCEPTED`；accepted lineage 已 fast-forward 至 `main`）。
  N01-3 真实 OKX SPOT metadata / 真实 `bbo-tbt` + `trades` / BTC-USDT 与 ETH-USDT 受控真实重连 /
  FRESH → CONTROLLED STALE → FRESH 三段边界；N01-4 `LIVE_PAPER` paper safety continuity
  （disposable PostgreSQL）：stale 下 `CORE_MARKET_DATA = UNAVAILABLE` + `CORE_DATA_STALE`
  incident，risk-increasing BUY 经 `SystemRiskGate` fail-closed（`RUNTIME_STATE_DATA_DEGRADED`），
  无 fabricated Fill / exit / position mutation，SELL 风险降低语义保持不被 stale 禁止但要求
  executable fresh BBO；post-reconnect real fresh BBO 恢复 HEALTHY 并 RESOLVE incident；
  final reconciliation PASS。
- Validation-only 产物：`backend/tests/test_n01_okx_paper_safety.py`（离网 deterministic）
  与 `scripts/verify_n01_b_okx_paper_safety.py`（真实 OKX，需显式执行）。两者均**不是**产品
  入口，不得被当作 Runtime Host 或 Smoke 使用。
- `Production code changed = NO`；无 schema / migration / Runtime Host / G3–G5 业务语义修改。
- 环境提示：本机 sandbox 注入的 `HTTP(S)_PROXY` 无法隧道到 OKX（502），本地 DNS 对
  `www.okx.com` 返回链路本地黑洞；真实 OKX 脚本在自身进程内清空 proxy env 后可正常验证。
  该现象属环境（`N01-B-E01`），不是产品缺陷，也未修改任何 production code。
- Final Gate Observation（非阻塞）：N01-A 既有测试
  `test_n01_twenty_real_postgres_lifecycles_...` 在 `engine.dispose()` 后立即断言
  PostgreSQL `sessions == baseline`，存在极短服务端回收窗口的偶发时序抖动（当日 5 次执行中 1 次；
  单独 3/3、全量 2/2 PASS）。属测试侧时序，非连接泄漏，无 production impact。

### N01-A Deterministic Runtime + Resource Lifecycle

- Task Base / verified `origin/main` = `bc635787eafdf88fdc8e5810109452b5e394a076`；branch =
  `n01-a-runtime-resource-lifecycle`。
- `N01-A = ACCEPTED / COMPLETE`：N01-A-F01 的 deterministic
  same-instrument queue-get / persist-boundary witness 保留；N01-A-F02 恢复每 cycle / final activity
  strict baseline equality；F01/F02 = `CLOSED / PASS`；其余 validation-only test 覆盖 bounded queue/backpressure、
  finite worker、同 `instrument_id` 串行、BTC/ETH bounded parallelism、recent/evicted/concurrent
  duplicate、failure retry、cancellation、20 个 real PostgreSQL lifecycle、task/queue/inflight/retained
  collection/session evidence。`backend/src` / schema / migration / Runtime Host 均未修改。
- R01 / R02 / R03 与 PostgreSQL durable duplicate TOCTOU 在 verified Accepted Main 上保持关闭。
  未执行真实 OKX reconnect 或 15m / 2h / 12h Soak；N01 Continuous Runtime / Soak 仍未证明、未验收。
  N01-B 未由本 Closeout 提前开始。（Historical N01-A closeout statement; N01-B 后续已单独开窗，
  经 Independent Review `PASS` + Human Acceptance 后为 `ACCEPTED / COMPLETE`，见第 6 节。）

### FG-E Reconciliation Snapshot Consistency

- FG-A、FG-B、FG-C、FG-D = `ACCEPTED / COMPLETE`；FG-A～FG-E Fix Program = `COMPLETE`。
- FG-D — G2 Runtime Determinism & Failure Atomicity：F07、F09、F10、F11 =
  `ACCEPTED / FIXED`；Accepted Implementation =
  `b08c2ea1eef4e2780a98b68dfaa2d5954af7d42b`。
- FG-E = `ACCEPTED / COMPLETE`；N02 = `ACCEPTED / FIXED`：Human Acceptance confirmed；accepted implementation
  `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`。G4 `reconcile()` 在同一 read-only
  `REPEATABLE READ` PostgreSQL transaction 内调用 G3 accounting，并加载 G4 extended
  facts；standalone G3 reconciliation 也使用自己的同类只读 snapshot。真实 PostgreSQL
  并发回归已验证报告不会跨 `ACTIVE → REPLACED` plan commit 撕裂。未改 schema、migration、
  SystemControlService / RecoveryManager transaction boundary 或 G3 accounting semantics。
  Initial Formal Review = `CHANGES_REQUIRED / NOT ACCEPTED`（historical; superseded by
  Acceptance Fix #1/#2/#3, Independent Review PASS and Human Acceptance）。Acceptance Fix #1 仅关闭 real G4
  transaction-state evidence：production G4 → G3 session 参数路径内断言
  `transaction_isolation=repeatable read` 与 `transaction_read_only=on`。其余 acceptance
  evidence 包括 account/order torn-read race、standalone G3 RR/RO、standalone G3 torn-read
  race、true durable corruption detection，以及 transaction identity / failure cleanup
  evidence。Acceptance Fix #2 已补 G4→G3 same-session/same-transaction identity、G4
  account/order torn-read race，以及 standalone G3 RR/RO、account/order torn-read race、
  true durable corruption detection、failure cleanup evidence。Acceptance Fix #3 已验证 G4
  durable corruption detector-only propagation，以及 actual G4 outer transaction 的 failure
  cleanup、immediate independent writer 与同生命周期 fresh reconciliation。N02-1～N02-14
  evidence 已完成，N02-1～N02-14 = PASS；Final Acceptance Closeout 已将 accepted lineage
  fast-forward 至 `main`。FG-E historical branch 保留为证据。
- N01-A = `ACCEPTED / COMPLETE`；N01-B = `ACCEPTED / COMPLETE`（见第 6 节）；N01 overall = `NOT ACCEPTED`；N03 = `DEFERRED`，G6 = `NOT STARTED`。
- C02 / C03 = `UNMAPPED / NOT AUDITABLE`；repository 中无法恢复原始 finding，需原始
  master audit source 后才能重新分类；不属于当前已证明的 P0/P1 blocker。

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
