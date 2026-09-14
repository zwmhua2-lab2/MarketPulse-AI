# PRE-01A Context Pack

## 1. Repository Snapshot

### FACT — Git

| ItemRepository Truth          |                                                                    |
| ----------------------------- | ------------------------------------------------------------------ |
| Current branch                | `prb-01-product-requirements-baseline`                             |
| Current `HEAD`                | `d47313a1cb41996410606fe92b286a5046ed4fce`                         |
| Local `main`                  | `dd78a979d128dee385c7a8ddc2254a53366af714`                         |
| Local `origin/main`           | `dd78a979d128dee385c7a8ddc2254a53366af714`                         |
| GitHub `main`                 | `dd78a979d128dee385c7a8ddc2254a53366af714`，由只读 `git ls-remote` 核实  |
| GitHub current branch         | `d47313a1cb41996410606fe92b286a5046ed4fce`                         |
| Relationship                  | Current `HEAD` 是 `main` 的祖先；`main` 领先 49 commits；当前分支没有独有 commit   |
| Accepted Truth                | GitHub `main@dd78a97`                                              |
| Current branch classification | `ACCEPTED TRUTH — HISTORICAL / STALE SNAPSHOT`，不是最新 Accepted Truth |

### FACT — Working Tree

工作树不是 clean：

- 20 个 tracked modified files；
- 5 个 tracked deleted files；
- 21 个 untracked files；
- 涉及 G2/G3/G4 source、G2–G5 tests、历史 dev logs、`.workbuddy/` 和 `scripts/_g54_selfreview.py`。

全部标记为：

```
PREEXISTING DELTA
```

本次未读取这些未提交内容作为 Accepted Truth，也未修改、清理或恢复它们。

### FACT — Accepted / Candidate State

`main:PROJECT_STATE.md:5-35,49-84` 证明：

```
ACCEPTED TRUTH
- SE-02A Contracts + Additive Persistence
- SE-02B Opportunity Capture + Attribution
- SE-ARCH-FIX-01 Stable Evidence Anchor
- SE-ARCH-FIX-02 Outcome Revision Chain Scope
- G1–G5 accepted components
- N01-A / N01-B / N01-C / N01-6 / N01-7-F01 / N01-7

NOT ACCEPTED / NOT AVAILABLE AS CURRENT CAPABILITY
- SE-02C Forward Outcome Calculator = BLOCKED / NOT STARTED
- SE-02D Family Aggregation / Expectancy = NOT STARTED
- N01-8 = NOT STARTED
- Integrated Runtime Host = NOT STARTED
- N01 overall = NOT ACCEPTED
- Real AI Provider = DEFERRED / NOT VERIFIED
```

以下 SE-02C-related tips 不属于 `main`：

- `be3aa6c`
- `2f98682`
- `7bb3835`

分类：

```
CANDIDATE / IN-PROGRESS
```

分支名、提交内容或 Worker 报告不能覆盖 `main` 的 `BLOCKED / NOT STARTED` 状态。

### UNKNOWN

由于 `DO NOT DISTURB`：

- 未检查当前 Runtime 进程；
- 未读取 Runtime environment 或 `.env`；
- 未连接 PostgreSQL；
- 未核对当前运行数据库的实际 migration head 或 Edge 表数据；
- 未重新运行任何测试或 smoke。

因此运行中 Runtime、实际数据库内容和当前 API key 状态均为 `UNKNOWN`。`OPENAI_API_KEY=MISSING` 是 Accepted 项目记录中的最后已验收状态，不是本轮环境探测结果。

---

## 2. Current Trading Decision Flow

### FACT — 已实现组件流

Accepted source 实际定义：

```
Normalized Market Data
    ↓
RollingFeatureEngine
    ↓
OpportunityScanner
    ↓
MarketEvent
    ↓
SymbolStateManager
    ↓
StrategyEngine
    ↓
StrategyCandidate + SETUP state
    ↓
[可选 Edge Capture]
Formal BREAKOUT_RETEST Opportunity + immutable EvidenceRevision
```

关键边界：

- `OpportunityScanner` 只生成 market facts，不输出交易方向。
  Evidence：`main:backend/src/marketpulse/g2/scanner.py:24-41`
- `StrategyEngine` 生成并行、可解释的 candidates，不执行、不修改状态。
  Evidence：`main:backend/src/marketpulse/g2/strategy.py:15-32`
- Formal Edge Opportunity 仅在 `APPLIED → SETUP`、`BREAKOUT`、适用且 `BULLISH` 的 `BREAKOUT_RETEST` candidate 与全部 G2 identities/version 一致时成立。AI、Risk、Trade 和 reference-data availability 都不是 Opportunity admission 条件。
  Evidence：`main:backend/src/marketpulse/edge/capture.py:871-977`
- G2 facts 与正式 Opportunity Evidence 在启用 capture 时同一 PostgreSQL transaction 提交；Edge integrity failure 会回滚 G2 facts。
  Evidence：`main:backend/src/marketpulse/g2/repository.py:393-456`

### FACT — Opportunity 到 G3 的真实断点

Accepted live path 中不存在自动的：

```
G2 Opportunity
→ G3 DecisionSnapshot
→ G3Workflow.process_setup()
```

`G3Workflow` 是可调用组件，但源码明确声明尚未接入 G2 runtime：

- `main:backend/src/marketpulse/g3/service.py:448-470`

非测试生产源码中的 `process_setup()` 调用点只存在于 G5 Replay：

- `main:backend/src/marketpulse/g5/replay.py:620-659`
- `main:backend/src/marketpulse/g5/replay.py:796-926`

因此当前实际状态是：

```
Live / continuous accepted runtime:
G2 Opportunity
→ [NO ACCEPTED INTEGRATED HOST HANDOFF]
→ G3 component exists but is not continuously wired

Deterministic Replay:
G2 SETUP
→ DecisionSnapshot
→ recorded AI provider
→ validated decision
→ TradePlan
→ caller-created ExecutionIntent
→ SystemRiskGate
→ PaperExecution
```

G5 Replay 使用 Recorded/Fake provider，不是 Real AI。

N01 runtime smoke 也没有证明 Opportunity→AI 链：其脚本直接构造 `TradePlan` 和 `ExecutionIntent`，再调用 Paper Execution。
Evidence：`main:scripts/verify_n01_6_runtime_smoke.py:280-323`

### FACT — Decision、Plan、Risk、Execution

```
DecisionSnapshot
    ↓
AIProvider.analyze()
    ↓
AIAnalysis
    ↓
DecisionValidator + stale state_version check
    ↓
VALID / INVALID / STALE
    ↓
TradePlanManager.from_analysis()
    ↓
TradePlan or no plan
    ↓
[ExecutionIntent 由 caller 创建]
    ↓
SystemRiskGate + capacity + execution-time validation
    ↓
Paper Order / Fill
    ↓
Account + Position + Trade + Ledger + Outbox
```

- Trade Decision 的 advisory 内容由 AI provider 输出。
- 程序决定该输出是否 `VALID`、`INVALID_*` 或 `STALE_DECISION`。
- `WAIT`、`SHORT_BIAS` 或无效输出不会生成可执行 LONG plan。
- Trade Plan 由程序化 `TradePlanManager` 从有效 `LONG_BIAS` 分析生成，并对 notional 做确定性 cap。
- `G3Workflow.process_setup()` 本身不创建或执行 `ExecutionIntent`；Intent 由上层 caller 创建。
- 风险增加动作可被 `SystemRiskGate`、capacity policy 或 execution revalidation 拒绝。
- `PaperExecutionService` 才能生成 Order、Fill 并修改经济事实。

---

## 3. Authority Map

### FACT

| DomainCurrent AuthorityPersistenceEvidence |                                                                                                                   |                                                                                                                   |                                                                    |
| ------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| Opportunity                                | G2 `OpportunityScanner` + `SymbolStateManager`；正式 Edge Opportunity 由 `edge.capture.qualifies()` 判定                | `market_events`、timeline、state、transition、candidate、derived observation；启用 capture 后写 `edge_opportunity_evidence` | `g2/scanner.py:24-41`; `edge/capture.py:871-977`                   |
| AI Analyst                                 | `AIProvider` / `PositionReviewProvider` 仅提供 advisory output；程序验证结果                                                | `decision_snapshots`、`ai_decisions`                                                                               | `g3/provider.py:12-15`; `g4/provider.py:44-47`                     |
| Trade Decision                             | AI 输出 `AIAnalysis.direction`；`DecisionService` 与 `DecisionValidator` 决定有效性和 stale 状态                              | `ai_decisions` 保存 status、model、prompt/schema version、response、error                                               | `g3/service.py:355-445`                                            |
| Trade Plan                                 | `TradePlanManager.from_analysis()` 和 G4 `PlanManager`                                                             | `trade_plans`、`trade_plan_scenarios`                                                                              | `g3/service.py:248-352`; `g4/planning.py:63-252`                   |
| Risk                                       | G4 `SystemRiskGate` 对 BUY/ADD/OPEN BUY fill 拥有最终 policy veto；Execution capacity policy 也可拒绝                       | 拒绝写入 intent/Edge attribution；runtime control、incidents、symbol controls 持久化                                        | `g4/risk_gate.py:18-138`; `g3/service.py:627-654,748-785`          |
| Execution                                  | `PaperExecutionService`；只接受程序化 Plan/Intent 并做 action-time validation                                              | intents、orders、fills、outbox                                                                                       | `g3/service.py:569-852,1408-1834`                                  |
| Balance                                    | `PaperExecutionService` 在锁定 Account 的 settlement/cancel transaction 内修改                                           | `accounts`、`ledger_entries`                                                                                       | `g3/service.py:1213-1341`                                          |
| Fill                                       | `PaperExecutionService._settle_order()`；AI/provider 无创建权                                                          | `fills`；每 order/intent 唯一                                                                                         | `g3/service.py:1213-1325`; `db/models.py:222-230`                  |
| Position                                   | `PaperExecutionService` settlement；G4 validated re-evaluation 可通过该路径 ADD/REDUCE/CLOSE                             | `positions`、`trades`、`position_events`                                                                            | `g3/service.py:1243-1310`; `g4/reevaluation.py:763-1046`           |
| Ledger                                     | `PaperExecutionService._settle_order()` 与 Fill 同一 transaction                                                     | `ledger_entries`，每 Fill 唯一                                                                                        | `g3/service.py:1326-1341`; `db/models.py:316-325`                  |
| Protection                                 | OPEN Position 行上的 durable protection snapshot 是唯一 lifetime authority；`PositionProtectionService` 用 fresh BBO 判定触发 | protection fields on `positions`、position events、incidents、exit Order/Fill                                        | `g3/protection_snapshot.py:1-37,69-126`; `g4/protection.py:44-164` |
| Recovery                                   | `RecoveryManager`；只从 PostgreSQL 重建，验证 BBO/plan/order/capacity，取消无效风险增加订单并恢复保护                                     | runtime control、incidents、order cancellation及其 reservation change；RecoveryReport 本身为返回值                           | `g4/recovery.py:52-321`                                            |
| Reconciliation                             | G3/G4 reconciliation functions；严格为 detector，不是 repair authority                                                   | 本身返回 report；读取 durable accounting/control/protection facts，不修复它们                                                  | `g4/reconciliation.py:27-42,101-257`                               |

### FACT — Risk Veto 限定

`SystemRiskGate` 对 G4-wired 风险增加路径拥有 veto；但 `PaperExecutionService.risk_gate` 构造参数允许为 `None`，用于保留 standalone G3 行为：

- `main:backend/src/marketpulse/g3/service.py:520-548`

已知 G5 Replay 和 G4/N01 harness 会注入 `SystemRiskGate`。由于 Integrated Runtime Host 未实现，当前不存在可审计的生产 host wiring，据此不能把任意独立 `PaperExecutionService` 实例推断为已接入 Gate。

---

## 4. Existing AI Boundary

### FACT — G3 Initial Decision Boundary

Contract：

```
AIProvider.analyze(
    snapshot: DecisionSnapshot,
    prompt: str,
) -> AIAnalysis
```

输入 `DecisionSnapshot` 包含：

- instrument / run mode / state / state\_version；
- frozen market context 与 BBO；
- rolling features / structure / derivatives；
- 最近 timeline；
- applicable Strategy contexts；
- account、position、open-order 等 trading context。

输出 `AIAnalysis` 包含：

- `LONG_BIAS` / `SHORT_BIAS` / `WAIT`；
- trends；
- entry zone；
- stop loss / take profit；
- invalidation；
- confidence；
- suggested position percentage；
- reason/evidence；
- main plan / backup scenarios；
- explicit `selected_strategy_ids`。

Authority：

- Provider 只接收 frozen snapshot 和 prompt，没有 repository、Risk 或 Execution handle。
- Prompt 明确禁止 tool use 和直接交易。
- `DecisionValidator` 检查 `SETUP`、Fresh BBO、LONG 必需字段与价格关系。
- provider 返回后再检查 `state_version`。
- 只有 `VALID + LONG_BIAS` 才可能生成 plan。
- `SHORT_BIAS` 只持久化分析，不产生 Short Execution。
- Plan notional 由程序以 equity、single-order cap 和 AI suggestion 的较小值生成。

Evidence：

- `main:backend/src/marketpulse/g3/models.py:106-175`
- `main:backend/src/marketpulse/g3/provider.py:12-65`
- `main:backend/src/marketpulse/g3/service.py:92-214,248-300,355-493`

Persistence：

- frozen `DecisionSnapshotRecord.payload`
- `AIDecisionRecord`：
  - `snapshot_id`
  - `state_version`
  - config/prompt/schema versions
  - `model`
  - status
  - raw prompt
  - raw response
  - error
  - timestamp
- `TradePlanRecord` 通过 `snapshot_id`、`decision_id` 关联决策。

### FACT — G4 Position Review Boundary

Contract：

```
PositionReviewProvider.review(
    snapshot: DecisionSnapshot,
    prompt: str,
) -> PositionReevaluation
```

允许的 advisory actions：

```
HOLD
ADD
REDUCE
CLOSE
CANCEL_ADD
UPDATE_STOP
UPDATE_TP
UPDATE_INVALIDATION
REPLACE_PLAN
```

但程序拥有实际 action authority：

- timeout/provider error/invalid business output → `HOLD`、零经济副作用；
- action 前重新取得 BBO；
- provider 后重验 state version、active plan/version、position/trade lifecycle；
- mutation transaction 内再次锁定并重验；
- `ADD` 再经过 `SystemRiskGate` 和 Execution；
- `REDUCE/CLOSE` 通过程序化 risk-reducing exit；
- Plan update 经过 schema/business validation 和 expected-current CAS；
- 既有 SL/TP 不因 AI 失败、延迟或不可用而失效。

Evidence：

- `main:backend/src/marketpulse/g4/provider.py:18-98`
- `main:backend/src/marketpulse/g4/reevaluation.py:118-322,358-529,763-1046`
- `main:backend/src/marketpulse/g4/protection.py:44-49`
- `main:DECISIONS.md:14-18`

### FACT — AI Persistence Limitations

- 初始 G3 decision 保存 prompt、response、model 与错误。
- G4 re-evaluation 保存 snapshot、response、model 与错误，但 `_persist_decision()` 写入 `raw_prompt=""`。
- `ai_decisions` 没有独立的 provider identity、provider response/request ID、latency、token、cost 或 experiment-arm 字段。
- Edge attribution 可以通过 `decision_id` 关联 AI decision，但需 caller 显式传入 `EdgeAttributionRecorder`。
- Real OpenAI adapter 已实现；Real AI activation/verification 没有 Accepted evidence。

---

## 5. Evidence / Attribution Readiness

| CapabilityStatusFACT              |               |                                                                                                                                                                 |
| --------------------------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| opportunity identity              | `READY`       | `opportunity_id` 由 family/version/instrument/candidate 确定性派生；正式 capture 已 Accepted                                                                              |
| evidence snapshot                 | `READY`       | 完整 event、transition、timeline、SETUP state、candidate、feature snapshot、reference/provenance 被 immutable/hash/versioned 保存；仅在 capture 启用且 Forward admission 合法时产生   |
| decision provenance               | `PARTIAL`     | DecisionSnapshot、AI decision、plan 和 Edge attribution primitives 已存在；但 live integrated handoff 不存在，attribution recorder 是可选注入，G4 prompt 不完整保存                    |
| forward outcome                   | `PARTIAL`     | `ForwardOutcomeContract`、`edge_forward_outcomes` 与 append-only writer 已存在；但 Accepted Calculator 不存在，当前系统不会计算/产生 horizon outcome                                 |
| family attribution                | `READY`       | 当前唯一获准 family 是 `BREAKOUT_RETEST`；AI 必须显式选择对应 `selected_strategy_ids` 才记 `AI_ACCEPTED_LONG`；Risk/Execution/Economic lineage 可继承相同 opportunity/evidence identity |
| model attribution                 | `PARTIAL`     | `AIDecisionRecord.model` 可经 `decision_id` 连接到 attribution event；但无 provider identity、provider request、latency/cost或实验 arm，且没有 Real AI 样本证明                      |
| without-AI vs with-AI attribution | `NOT PRESENT` | 没有 treatment/control assignment、AI-disabled decision provenance、paired baseline identity 或可比较的已计算 forward outcomes                                              |

### FACT — 已具备的 Attribution Chain Primitive

在 caller 正确注入 recorder 时，Accepted source 可记录：

```
Opportunity / Evidence
→ AI reached / accepted / wait / invalid / provider error / stale
→ Plan created / not created
→ Risk accepted / rejected with exact authority and reason
→ Execution rejected / order open / cancelled / filled
→ Trade opened / closed
→ Actual economic result with Fill + Ledger
```

Evidence：

- `main:backend/src/marketpulse/edge/attribution.py:61-87,191-302,306-577`
- `main:backend/src/marketpulse/g3/service.py:400-445,303-352,627-685,1213-1396`
- Static accepted tests include:
  - `test_accepted_ai_through_fill_links_the_whole_lineage_to_one_opportunity`
  - `test_closed_trade_records_the_actual_economic_result_linkage`
  - `test_deferred_open_orders_resolve_each_order_to_its_own_opportunity`

### FACT — 当前仍不能证明 Edge

G5 `ReplayEvaluationReport` 已能从 durable Replay workspace 确定性计算：

- event/decision/plan/order/fill/trade counts；
- filled notional；
- fees；
- ledger cash delta；
- account realized PnL；
- final balance/reservation；
- position/trade closure state。

它不是 per-opportunity forward outcome calculator，也不提供：

```
MFE
MAE
forward returns
Expectancy
R-Multiple
Drawdown
family aggregation
without-AI vs with-AI comparison
```

Evidence：

- `main:backend/src/marketpulse/g5/evaluation.py:1-10,45-127,130-303`
- `main:PROJECT_STATE.md:356-361`
- `main:PRODUCT_REQUIREMENTS.md:300-325`

---

## 6. Existing Capabilities / Real Gaps

### EXISTING — FACT

- G1 normalized market-data boundary。
- G2 bounded/deduplicated/per-instrument-serialized runtime。
- Deterministic Scanner market facts、state machine、timeline、parallel StrategyCandidate。
- PostgreSQL G2 fact persistence。
- Opt-in formal `BREAKOUT_RETEST` Opportunity capture。
- Immutable/versioned/hash-bound evidence identity。
- Forward live-ingress admission proof、durable capture anchor、restart-visible orphan classification。
- Provider-neutral G3 AI Analyst contract。
- Real OpenAI adapter class。
- Programmatic schema/business/staleness validation。
- Deterministic Trade Plan generation and persistence。
- `SystemRiskGate`、capacity policy、action-time execution guards。
- Atomic Paper Order/Fill/Account/Position/Trade/Ledger/Outbox settlement。
- G4 Position re-evaluation advisory contract。
- AI-independent durable Position protection。
- PostgreSQL-based Recovery。
- Detector-only Reconciliation。
- G5 deterministic Replay 与 minimal durable evaluation。
- Opportunity→AI→Plan→Risk→Execution→Economic Result attribution primitives。
- Forward Outcome contract、schema、revision-chain integrity 和 append writer。

### REAL GAP — FACT

- Accepted Integrated Runtime Host 不存在。
- Accepted live path 没有自动 `Opportunity → DecisionSnapshot → G3Workflow` handoff。
- `G3Workflow.process_setup()` 不创建 ExecutionIntent；live intent orchestration 未形成 accepted host。
- 没有一个 Accepted continuous runtime 同时启用：
  - Forward Opportunity capture；
  - Real AI；
  - Edge attribution recorder；
  - Risk/Execution；
  - Position/Protection；
  - Forward Outcome。
- Real AI provider activation 与真实 contract/runtime verification 未完成。
- `SE-02C` Forward Outcome Calculator 未实现且仍被 Gate 阻止。
- `SE-02D` family aggregation / Expectancy 未实现。
- 当前没有 without-AI / with-AI treatment identity、paired assignment 或 baseline provenance。
- AI provenance 没有独立 provider identity、request/response ID、latency、token/cost 和 experiment arm。
- 当前没有 Accepted per-opportunity MFE、MAE、forward return、cost-adjusted forward result。
- N01 2-hour soak 是 runtime/safety validation；其交易由 harness 构造 Plan/Intent，不能视为 Real AI Edge evidence。

### UNKNOWN

- 当前 Runtime 是否正在运行、运行何种 commit/configuration。
- 当前 PostgreSQL 是否已经升级到 `20260913_0009`。
- 当前数据库是否存在真实 Forward Opportunity records。
- 当前数据库是否已有任何 AI decision、attribution 或 outcome rows。
- 当前机器是否已有可用 AI credential。
- Real AI 的输出质量、稳定性、延迟、成本和错误率。
- 未提交工作树内容的来源、完成度和接受状态。

---

## 7. Constraints For External Research

### Existing capabilities

Research Worker 必须把以下视为已存在，不得当作空白系统：

- G2 Scanner/state/candidate/persistence；
- Formal Opportunity identity 与 immutable Evidence；
- G3 initial AI contract；
- G4 position-review contract；
- TradePlan/ExecutionIntent/PaperExecution；
- `SystemRiskGate`；
- atomic Account/Fill/Position/Ledger；
- durable position protection；
- Recovery/Reconciliation；
- deterministic Replay；
- attribution event model；
- forward-outcome persistence contract。

### Must preserve

```
AI = advisory
Risk-increasing authority = deterministic SystemRiskGate + programmatic checks
Execution/accounting authority = PaperExecutionService
Protection lifetime authority = durable snapshot on Position
Recovery source of truth = PostgreSQL
Reconciliation = detector, not repair
Paper Trading only
Spot LONG only
SHORT_BIAS = analysis only
```

同时必须保留：

- Scanner 不直接输出 BUY/SELL；
- protection 不等待 AI；
- stale/invalid/provider-failed AI 不产生经济副作用；
- Risk-reducing exit 在 Pause/SafeMode/Emergency 下保持可用；
- `TradePlan.invalidation` 只是 advisory text；
- `stop_loss` 是唯一 machine-enforceable hard price invalidation；
- 单一 Primary Provider 边界，无自动 fallback/voting；
- Modular Monolith；
- SPOT/SWAP identity 隔离；
- accepted identity/hash/revision/anchor/attribution contracts。

### Known gaps

外部研究不得假设已存在：

- Integrated Runtime Host；
- Real AI activation；
- live Opportunity→AI handoff；
- Forward Outcome Calculator；
- Expectancy/family aggregation；
- without-AI vs with-AI experiment assignment；
- AI latency/cost/provider-request provenance。

### Unknowns

外部研究不得把以下写成事实：

- 当前数据库已有足够 Edge 样本；
- Real AI 已经运行；
- Real AI 已产生可归因 PnL；
- 现有 Replay 已证明 Trading Edge；
- N01 soak 已证明 AI Edge；
- SE-02C candidate branch 已被接受。

### Do not redesign

后续研究不能未经批准重新设计或复制：

- Scanner；
- Opportunity identity；
- Evidence revision model；
- Trade Decision schema；
- TradePlan；
- Risk gate；
- Paper accounting；
- Position protection；
- Recovery/Reconciliation；
- Ledger；
- Replay engine；
- Edge attribution contracts。

---

## 8. Conflicts / Unknowns

### CONFLICT 1 — Checked-out branch vs latest Accepted Truth

```
CONFLICT
Current checkout = d47313a historical PRB branch
Latest Accepted GitHub main = dd78a97
```

Evidence：

- `HEAD` 是 `main` 的祖先；
- `main` 领先 49 commits；
- checked-out `PROJECT_STATE.md` 的状态明显早于 `main:PROJECT_STATE.md`；
- current worktree 又含大量未提交变化。

Impact：

- 当前工作树文件不能直接代表 latest Accepted Truth；
- 本 Context Pack 的事实均以 `main@dd78a97` Git blobs 为准。

### CONFLICT 2 — SE-02C branch content vs Accepted state

```
CONFLICT
SE-02C-related branches contain implementation commits
main:PROJECT_STATE.md says SE-02C = BLOCKED / NOT STARTED
```

Impact：

- 这些 branch commits 只能标记为 `CANDIDATE / IN-PROGRESS`；
- Forward Outcome Calculator 不属于当前能力。

### CONFLICT 3 — Product responsibility diagram vs current runtime wiring

```
CONFLICT
PRODUCT_REQUIREMENTS describes the long-term responsibility chain:
Scanner → AI Analyst → Decision → Plan → Risk → Execution

Repository source/state:
Integrated Runtime Host = NOT STARTED
G3Workflow is not connected to live G2 runtime
```

Impact：

- Product responsibility map不能被描述成当前连续运行的 end-to-end host。
- 当前只能确认组件和 Replay/harness 级接线。

### UNKNOWN — Runtime / Database

`DO NOT DISTURB` 禁止验证运行中进程、environment 和 PostgreSQL。因此：

- Runtime commit/config；
- DB migration head；
- durable sample counts；
- AI credential；
- actual Real AI use；

全部保持 `UNKNOWN`。

### Verification Boundary

本轮只执行：

- Git refs/history/diff/status；
- 只读 GitHub `ls-remote`；
- `main` Git object 中的源码、contracts、tests、state 与 dev logs 静态审查。

未执行测试、Runtime、Docker、PostgreSQL 或 provider 调用。工作树在最终复核时与任务开始时状态一致；未修改项目，也未影响 Runtime。