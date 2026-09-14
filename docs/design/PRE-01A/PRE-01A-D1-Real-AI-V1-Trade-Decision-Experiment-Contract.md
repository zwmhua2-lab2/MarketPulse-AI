# PRE-01A-D1 | Real AI V1 Trade Decision Experiment Contract

## 1. Status / Inputs / Repository Baseline

### 1.1 Artifact status

| Classification | Item | Value |
|---|---|---|
| **DESIGN DECISION** | Artifact status | `CANDIDATE DESIGN / PENDING HUMAN REVIEW` |
| **DESIGN DECISION** | Task type | `DESIGN FIX / DOC-ONLY` |
| **DESIGN DECISION** | V1 placement | `C. Trade Decision` only |
| **DESIGN DECISION** | Implementation authority | None |
| **DESIGN DECISION** | Activation authority | None |

本文件在 Human Acceptance 之前不是 Accepted Design，不授权实现、migration、Runtime Host、provider/model 选择、真实 provider 调用、Paper Economic activation 或 Live Trading。

### 1.2 Repository baseline

| Classification | Fact | Evidence |
|---|---|---|
| **FACT** | Global Protocol | `zwmhua2-lab2/ai-dev-protocol` `main@e92fcc381baaf314a6c0f5687b1353ac6c06a748`; Protocol `1.0.0 / ACCEPTED` |
| **FACT** | MarketPulse remote | `https://github.com/zwmhua2-lab2/MarketPulse-AI.git` |
| **FACT** | Current Accepted main / Task Base | `origin/main@b77c80333b85d6e3f1095ac7da9b13e9bf08163a`，2026-09-14 实时 fetch 后读取 |
| **FACT** | Research branch pinned tip | `research/pre-01a@e087caed7eed58ed2c5138084b43dda0807eec58`，与实时 remote tip 一致 |
| **FACT** | Research ancestry | `e087cae` 的 parent chain 直接建立在 `b77c803` 上；Research 只比 Accepted main 多两个 docs-only commits |
| **FACT** | Design branch base | `design/pre-01a-d1-real-ai-v1-contract` 从 `origin/main@b77c803` 创建 |
| **FACT** | Root worktree | 原 root checkout 存在大量 unrelated dirty changes；本任务未读取其内容作为 Accepted Truth，也未修改、stash、reset、clean 或提交它们 |

### 1.3 Inputs and precedence

| Classification | Input | Role |
|---|---|---|
| **FACT** | `AGENTS.md`, `AI_CONTEXT.md`, `PROJECT_STATE.md`, `PRODUCT_REQUIREMENTS.md`, `DECISIONS.md` at `b77c803` | Current accepted project truth and boundary |
| **FACT** | G2/G3/G4/G5/Edge source, schema, tests and relevant `dev_log` at `b77c803` | Current implementation facts |
| **FACT** | `docs/research/PRE-01A/PRE-01A-Real-AI-Research-Verdict.md` at `e087cae` | Final research verdict, evidence input only |
| **FACT** | External Evidence Pack at `e087cae` | External reference evidence, not project decision |
| **FACT** | Context Pack at `e087cae` | Historical snapshot only |
| **DESIGN DECISION** | Precedence | Current Accepted main > accepted project docs/contracts > Final Research Verdict > External Evidence Pack > Context Pack > inference |

### 1.4 Confirmed preconditions and drift

| Classification | Precondition | Verdict |
|---|---|---|
| **FACT** | Real AI V1 First Placement | `C. Trade Decision` |
| **FACT** | `SE-02C Forward Outcome Calculator` | `ACCEPTED / COMPLETE` |
| **FACT** | `SE-02D Family Aggregation / Expectancy` | `NOT STARTED` |
| **FACT** | live Opportunity -> G3 integrated handoff | `NOT ACCEPTED / NOT ACTIVE`; `G3Workflow` remains an explicit unwired entry |
| **FACT** | Integrated Runtime Host | `NOT STARTED` |
| **FACT** | Real AI provider runtime evidence | Not present; Accepted project record remains `DEFERRED / NOT VERIFIED` |
| **FACT** | Historical drift | Context Pack said `SE-02C = BLOCKED / NOT STARTED`; current main supersedes it with `ACCEPTED / COMPLETE` |

## 2. Problem Statement

**FACT** — Current MarketPulse already has a provider-neutral `AIProvider`, frozen `DecisionSnapshot`, `AIAnalysis`, `DecisionValidator`, deterministic `TradePlanManager`, `SystemRiskGate`, Paper Execution, durable Position Protection, Recovery/Reconciliation, attribution primitives, deterministic Replay and accepted per-opportunity Forward Outcome.

**FACT** — Current MarketPulse does not yet have a live Opportunity-to-G3 handoff, Real AI runtime evidence, explicit experiment/arm/pair identity, provider-attempt provenance, an accepted without-AI baseline, or accepted SE-02D Expectancy aggregation.

**DESIGN DECISION** — Real AI V1 must answer a narrow causal question:

```text
For the same formally admitted Opportunity and the same immutable Evidence,
does Real AI improve LONG participation / selection quality
relative to participating LONG in every eligible Opportunity,
without changing downstream deterministic authority?
```

**DESIGN DECISION** — The V1 causal treatment variable in the paired SE-02C evaluation is only `PARTICIPATE_LONG` versus `NO_LONG`. This experiment can prove only **Real-AI Trade-Decision selection / participation edge**. It cannot attribute edge to AI `entry_zone`, `stop_loss`, `take_profit`, `suggested_position_pct`, `probe`, the full `AIAnalysis` package, or actual executed trades.

**DESIGN DECISION** — Provider connectivity, schema-valid output, a profitable sample, or high Win Rate cannot answer that question by itself.

## 3. Scope / Out of Scope

### 3.1 Scope

| Classification | In scope |
|---|---|
| **DESIGN DECISION** | Trade Decision authority boundary |
| **DESIGN DECISION** | Real AI input/output and structured-output/refusal contract |
| **DESIGN DECISION** | Failure, retry, deadline, freshness, late and duplicate semantics |
| **DESIGN DECISION** | Provider capability and provider/model provenance contract |
| **DESIGN DECISION** | with-AI versus without-AI experiment identity, arms and pairing |
| **DESIGN DECISION** | Evaluation metric classification |
| **DESIGN DECISION** | Provider Shadow, Paper Economic and Edge Evidence activation gates |

### 3.2 Out of scope

| Classification | Out of scope |
|---|---|
| **DESIGN DECISION** | Runtime Host architecture or technology selection |
| **DESIGN DECISION** | Provider or model selection |
| **DESIGN DECISION** | DB schema/migration design or implementation |
| **DESIGN DECISION** | Source, test, config, Runtime, Docker or PostgreSQL changes |
| **DESIGN DECISION** | SE-02D implementation or metric aggregation implementation |
| **DESIGN DECISION** | live G2-to-G3 handoff implementation |
| **DESIGN DECISION** | Scanner, Opportunity, Evidence, TradePlan, Risk, Execution, Protection, Recovery, Reconciliation, Ledger or Replay redesign |
| **DESIGN DECISION** | Position Re-evaluation placement, Agent Runtime, tools, autonomous planning, multi-provider fallback or model voting |

## 4. Frozen V1 Placement

**DESIGN DECISION** — Real AI V1 has exactly one placement: `C. Trade Decision`.

```text
Immutable Opportunity Evidence
        +
Frozen Decision Input Binding
        |
        v
Real AI advisory Trade Decision
        |
        v
Deterministic validation and existing authority chain
```

**DESIGN DECISION** — V1 does not use AI to qualify Opportunities, create a different TradePlan algorithm, change Risk policy, choose Execution behavior, or re-evaluate an open Position.

**DESIGN DECISION** — Real AI may still produce the complete accepted `AIAnalysis` package, and every field remains subject to its validation, provenance and authority rules. For Provider Shadow / paired SE-02C causal evaluation, however, the treatment variable is reduced to the validated decision to `PARTICIPATE_LONG` or `NO_LONG`; effects of entry, stop, target, sizing and probe fields are outside the V1 causal claim. The downstream `TradePlanManager` algorithm remains unchanged.

## 5. Authority Contract

### 5.1 Frozen authority chain

**FACT** — The accepted responsibility chain is:

```text
AI
-> AIAnalysis
-> DecisionValidator
-> TradePlanManager
-> SystemRiskGate
-> PaperExecution
-> Account / Fill / Position / Ledger
```

**DESIGN DECISION** — Real AI remains advisory. Deterministic code remains authoritative.

| Classification | Domain | Authority |
|---|---|---|
| **DESIGN DECISION** | Repository mutation | Real AI has none |
| **DESIGN DECISION** | Opportunity admission and Evidence revision | Existing deterministic Edge/G2 contracts only |
| **DESIGN DECISION** | Trade Decision proposal | Real AI may propose `AIAnalysis`; it cannot self-validate |
| **DESIGN DECISION** | TradePlan creation | Existing deterministic `TradePlanManager` only |
| **DESIGN DECISION** | Risk limits and risk-increasing admission | Existing deterministic limits and `SystemRiskGate` only |
| **DESIGN DECISION** | Order, Fill and execution | `PaperExecutionService` only |
| **DESIGN DECISION** | Balance, Position, PnL and Ledger | Existing atomic accounting path only |
| **DESIGN DECISION** | Protection | Durable protection snapshot on the OPEN Position plus existing protection service only |
| **DESIGN DECISION** | Recovery | Existing PostgreSQL-backed Recovery only |
| **DESIGN DECISION** | Reconciliation | Existing detector-only Reconciliation only |

### 5.2 Risk-direction invariant

**DESIGN DECISION** — `AI failure -> no new risk-increasing economic action`.

**DESIGN DECISION** — AI failure does not stop deterministic runtime. Existing Position Protection, stop enforcement, cancellation and risk-reducing exits must continue without a successful AI call.

**DESIGN DECISION** — `SystemRiskGate` must be structurally present on every Real-AI-authoritative risk-increasing execution path. The accepted standalone `risk_gate=None` compatibility seam is not eligible for Paper Economic Activation.

## 6. Input Binding Contract

### 6.1 What market state is being answered

**DESIGN DECISION** — One Real AI result answers exactly one immutable `DecisionInputBinding`; it must not be reusable for a different opportunity, evidence revision, snapshot, state, configuration, prompt, schema, instrument or market type.

| Classification | Binding field | V1 requirement | Current readiness |
|---|---|---|---|
| **DESIGN DECISION** | `opportunity_id` | MUST bind | Edge READY; absent from current `DecisionSnapshot` |
| **DESIGN DECISION** | `evidence_id` | MUST bind | Edge READY; absent from current `DecisionSnapshot` |
| **DESIGN DECISION** | `evidence_revision` | MUST bind | Edge READY; absent from current `DecisionSnapshot` |
| **DESIGN DECISION** | `evidence_hash` | MUST bind | Edge READY; absent from current `DecisionSnapshot` |
| **DESIGN DECISION** | `snapshot_id` | MUST bind | Present |
| **DESIGN DECISION** | `snapshot_version` | MUST bind | Present |
| **DESIGN DECISION** | `snapshot_payload_hash` | MUST bind | `NEW CONTRACT REQUIRED`; current snapshot has no content hash |
| **DESIGN DECISION** | `state_version` | MUST bind | Present |
| **DESIGN DECISION** | `config_version` | MUST bind | Present |
| **DESIGN DECISION** | `prompt_version` | MUST bind | Present on decision record, not snapshot |
| **DESIGN DECISION** | `schema_version` | MUST bind | Present on decision record, not snapshot |
| **DESIGN DECISION** | `family_id` | MUST bind | Edge READY; absent from current `DecisionSnapshot` |
| **DESIGN DECISION** | `family_version` | MUST bind | Edge READY; absent from current `DecisionSnapshot` |
| **DESIGN DECISION** | `instrument_id` | MUST bind | Present |
| **DESIGN DECISION** | `market_type` | MUST bind | Evidence/feature READY; absent as a top-level current snapshot field |
| **DESIGN DECISION** | `decision_requested_at` | MUST bind as timezone-aware request fact | `NEW CONTRACT REQUIRED` |
| **DESIGN DECISION** | `decision_deadline_at` | MUST bind as absolute deadline | `NEW CONTRACT REQUIRED` |

### 6.2 Minimal binding mechanism

**DESIGN DECISION** — Future implementation must construct a canonical, versioned `input_binding_digest` over all MUST-bind fields and the frozen snapshot payload before provider invocation.

**DESIGN DECISION** — A client-owned `decision_invocation_id` must bind the local call, all attempts, provider request identities and the final decision record to that digest. The model/provider is never allowed to choose or rewrite these identities.

**DESIGN DECISION** — If a structured response echoes a binding digest, deterministic code must require exact equality; an echo is only a misrouting check and never the identity authority.

**DESIGN DECISION** — Before plan creation and again at the existing action-time authority boundaries, deterministic code must verify the current durable state against the binding. Any mismatch is stale and has zero risk-increasing side effects.

### 6.3 Logical final-decision identity

**DESIGN DECISION** — One client-owned `decision_invocation_id` maps to **exactly one logical final AI decision identity**. Attempt 1, attempt 2 and every permitted retry belong to that same invocation. Each attempt has its own unique attempt identity, provider request identity when available, timestamps, outcome and attempt provenance, but attempts do not become independent final decisions.

**DESIGN DECISION** — The invocation's logical final identity exists independently of retry attempts. When the invocation terminalizes, its atomic invocation-result claim is won exactly once by one durable final result—either the accepted valid result or the terminal failure result. A valid winner is the only result eligible to become actionable. Losing, duplicate or late completions may be retained as attempt audit evidence, but cannot create or replace a second final decision, plan or economic action.

**DESIGN DECISION** — `same snapshot_id + same configured model` is insufficient to identify a future Real AI experiment decision. The durable final identity and its unambiguous one-to-one invocation linkage must be collision-free across the following bound values:

```text
decision_invocation_id
+ experiment_id
+ pair_id
+ arm_id
+ input_binding_digest
+ prompt_version
+ schema_version
+ configured treatment version
```

Changing any listed value creates a distinct logical invocation/final-decision lineage. A final result from another experiment, pair or arm must never be reused, linked or overwritten as the result of the new invocation.

**DESIGN DECISION** — D1 freezes this logical contract but does not choose a DB schema or migration. Future implementation must independently prove one of two compatible physical approaches:

1. version or redefine durable `decision_id` so it is invocation-aware and collision-free; or
2. preserve legacy `decision_id` only where compatible and introduce a separate durable invocation-aware final-decision identity with an unambiguous one-to-one linkage.

Under either approach, different experiments/invocations cannot collide onto one AI decision record, and retries cannot create multiple actionable final decisions.

## 7. Output / Structured Schema Contract

### 7.1 Current `AIAnalysis` field verdict

| Classification | Current field | Verdict | V1 semantics |
|---|---|---|---|
| **DESIGN DECISION** | `direction` | `KEEP + VALIDATE DETERMINISTICALLY` | `LONG_BIAS`, `WAIT`, `SHORT_BIAS`; only validated `LONG_BIAS` can reach plan creation |
| **DESIGN DECISION** | `trends` | `KEEP / ADVISORY` | Explanation only; no direct economic authority |
| **DESIGN DECISION** | `confidence` | `KEEP / RESTRICT` | Calibration/diagnostics only; must not set risk limits, bypass gates or rank execution priority |
| **DESIGN DECISION** | `entry_zone` | `KEEP + VALIDATE DETERMINISTICALLY` | Suggestion within the Trade Decision package; not an order |
| **DESIGN DECISION** | `stop_loss` | `KEEP + VALIDATE DETERMINISTICALLY` | Suggested hard-price input; existing deterministic plan/protection contracts remain authority |
| **DESIGN DECISION** | `take_profit` | `KEEP + VALIDATE DETERMINISTICALLY` | Suggested target input; not a Fill or exit command |
| **DESIGN DECISION** | `invalidation` | `KEEP / RESTRICT` | Human-readable advisory text only; Runtime must not parse it as executable logic |
| **DESIGN DECISION** | `reason` / `trends` / `main_plan` / `backup_scenarios` | `KEEP / ADVISORY` | Explanation only; backup scenarios remain non-executable |
| **DESIGN DECISION** | `supporting_evidence` / `risk_evidence` | `KEEP + VALIDATE DETERMINISTICALLY` | Every referenced fact must resolve to the bound Evidence/Snapshot allow-list; invented/unsupported facts invalidate the result |
| **DESIGN DECISION** | `selected_strategy_ids` | `KEEP + VALIDATE DETERMINISTICALLY` | Must be a subset of strategies in the bound snapshot; family attribution requires explicit selection |
| **DESIGN DECISION** | `suggested_position_pct` | `KEEP / RESTRICT + VALIDATE` | Suggestion only; finite `[0,1]`; deterministic sizing cap and Risk authority dominate |
| **DESIGN DECISION** | `probe` | `KEEP / RESTRICT + VALIDATE` | Cannot bypass plan, capacity, gate, execution or accounting checks |
| **DESIGN DECISION** | Any `ADD/REDUCE/CLOSE/UPDATE_*/REPLACE_PLAN` suggestion | `REMOVE FROM V1 AUTHORITY` | Belongs to Position Re-evaluation placement E, not C |

**DESIGN DECISION** — In Spot Long V1, `SHORT_BIAS` means bearish/no-long analysis. It is valid analysis but produces no executable short plan, short intent or short order.

### 7.2 Provider-native Structured Output

**DESIGN DECISION** — Provider-native strict structured output is **REQUIRED** for Real AI V1 Provider Shadow Activation and later gates. A provider/model combination that cannot enforce the approved schema is ineligible for V1 activation.

**DESIGN DECISION** — The schema layer is limited to shape, type, required fields, enum values and provider-supported structural constraints. It cannot establish evidence truth, state freshness, numeric relationships, Spot Long rules, risk policy or authority.

**DESIGN DECISION** — Deterministic business validation remains mandatory after provider-native validation and before any plan/action. Structured output never replaces `DecisionValidator`.

**DESIGN DECISION** — Tools/function execution must be disabled. V1 output is one bounded data object or a provider-native refusal/incomplete branch, never a tool call.

### 7.3 Required deterministic business validation

| Classification | Validation |
|---|---|
| **DESIGN DECISION** | Exact `input_binding_digest` / invocation association |
| **DESIGN DECISION** | Durable opportunity/evidence identity, revision and hash integrity |
| **DESIGN DECISION** | Current `state_version`, snapshot identity/version and freshness |
| **DESIGN DECISION** | Instrument and SPOT market identity |
| **DESIGN DECISION** | `SETUP` and accepted family/strategy membership |
| **DESIGN DECISION** | Required LONG fields and finite numeric values |
| **DESIGN DECISION** | `stop_loss < entry_zone.lower <= entry_zone.upper < take_profit` |
| **DESIGN DECISION** | Evidence references are supported by the bound immutable input |
| **DESIGN DECISION** | Spot Long-only and no executable `SHORT_BIAS` |
| **DESIGN DECISION** | Position sizing caps, capacity and all existing risk rules |
| **DESIGN DECISION** | Result arrived before deadline and won the invocation result race |

## 8. Failure Contract

### 8.1 Existing status vocabulary

**FACT** — Current `DecisionStatus` is exactly `RECEIVED`, `VALID`, `INVALID_SCHEMA`, `INVALID_BUSINESS`, `STALE_DECISION`, `CAPACITY_BLOCKED`.

**DESIGN DECISION** — Research labels such as `REFUSED`, `LATE`, `UNSUPPORTED_EVIDENCE` and `DUPLICATE_SUPPRESSED` are not accepted DB statuses and must not be silently introduced as enums.

**DESIGN DECISION** — V1 keeps the existing economic-decision status vocabulary and adds a logically separate, versioned diagnostic `error_category`/attempt history in the future implementation contract. This is `NEW CONTRACT REQUIRED`, not a migration design in D1.

**DESIGN DECISION** — `RECEIVED` is non-terminal invocation state. `CAPACITY_BLOCKED` is a downstream capacity outcome, not an AI/provider failure.

### 8.2 Failure mapping and economic semantics

| Classification | Failure | Existing terminal status mapping | Diagnostic category | Retry class | Economic result |
|---|---|---|---|---|---|
| **DESIGN DECISION** | timeout | `INVALID_SCHEMA` when no complete decision exists | `TIMEOUT` | Transport-conditional | No new risk |
| **DESIGN DECISION** | provider unavailable | `INVALID_SCHEMA` | `PROVIDER_UNAVAILABLE` | Transport-conditional | No new risk |
| **DESIGN DECISION** | transport failure | `INVALID_SCHEMA` | `TRANSPORT_FAILURE` | Transport-conditional | No new risk |
| **DESIGN DECISION** | refusal | `INVALID_SCHEMA` | `REFUSAL` | Non-retryable | No new risk |
| **DESIGN DECISION** | malformed JSON | `INVALID_SCHEMA` | `MALFORMED_OUTPUT` | Validation-conditional | No new risk |
| **DESIGN DECISION** | schema failure | `INVALID_SCHEMA` | `SCHEMA_FAILURE` | Validation-conditional | No new risk |
| **DESIGN DECISION** | business validation failure | `INVALID_BUSINESS` | exact validator reasons | Conditional only for explicitly repairable output | No new risk |
| **DESIGN DECISION** | hallucinated / unsupported evidence | `INVALID_BUSINESS` | `UNSUPPORTED_EVIDENCE` | Non-retryable | No new risk |
| **DESIGN DECISION** | invalid numeric relation | `INVALID_BUSINESS` | `INVALID_NUMERIC_RELATION` | Validation-conditional | No new risk |
| **DESIGN DECISION** | stale `state_version` or binding | `STALE_DECISION` | `STALE_BINDING` | Non-retryable | No new risk; zero mutation |
| **DESIGN DECISION** | late result | `STALE_DECISION` | `LATE_RESULT` | Non-retryable | Audit only; no action |
| **DESIGN DECISION** | duplicate result | Preserve the already accepted terminal status | `DUPLICATE_SUPPRESSED` | Non-retryable | Attempt audit only; no second final decision or duplicate action |
| **DESIGN DECISION** | partial/incomplete result | `INVALID_SCHEMA` | `PARTIAL_RESULT` | Validation-conditional only when provider marks it repairable | No new risk |
| **DESIGN DECISION** | retry exhaustion | Status of the final failure class | `RETRY_EXHAUSTED` plus full attempt history | Non-retryable | No new risk |

**DESIGN DECISION** — Failure precedence for action authority is: duplicate winner check -> absolute deadline/late check -> binding/stale check -> provider/refusal/completeness/schema -> business validation -> `VALID`. Diagnostics may retain multiple observed reasons even though the terminal status is singular.

**DESIGN DECISION** — Missing latency, token usage or provider cost is `UNKNOWN/NULL`, never zero.

## 9. Retry / Deadline Contract

### 9.1 Separate retry budgets

**DESIGN DECISION** — Transport retry and validation retry are separate counters with separate reason classes, but both consume one joint absolute deadline, joint maximum-attempt budget and joint cost budget.

| Classification | Retry type | Retryable | Non-retryable |
|---|---|---|---|
| **DESIGN DECISION** | Transport | Provider-classified transient timeout, connection interruption, rate limit or transient server unavailable, only while deadline/cost remains | refusal, authentication/permission, invalid request/schema capability, permanent provider/model error |
| **DESIGN DECISION** | Validation | malformed/schema/partial or numeric relation only when the validator explicitly marks the failure repairable and a corrected response can still arrive in time | unsupported evidence, authority violation, stale/late result, duplicate, invalid binding, non-repairable product-rule failure |

**DESIGN DECISION** — Every retry uses the same provider, same configured model identity, same immutable input binding, same experiment arm and same pair. No automatic provider/model fallback and no voting are permitted.

**DESIGN DECISION** — An absolute `decision_deadline_at` is fixed before attempt 1. Per-attempt timeout cannot extend it. A retry starts only if a conservative remaining-time check proves it can finish before the deadline.

**DESIGN DECISION** — The first fully valid result that wins the invocation's atomic result claim before the deadline is the only actionable result. If no valid result wins, terminalization records one terminal failure result under the same logical final identity. All later completions are audit-only duplicate/late attempt results and cannot replace the claimed final result.

**DESIGN DECISION** — Cancellation is best-effort transport cleanup, not an authority boundary. A response arriving after cancellation still undergoes deadline, duplicate and stale checks and cannot act.

### 9.2 Numeric settings

| Classification | Setting | Candidate range | Status |
|---|---|---|---|
| **OPEN QUESTION** | Joint total attempts including first attempt | `1..3` | `NEEDS HUMAN DECISION` |
| **OPEN QUESTION** | Transport retries | `0..2`, within joint cap | `NEEDS HUMAN DECISION` |
| **OPEN QUESTION** | Validation retries | `0..1`, within joint cap | `NEEDS HUMAN DECISION` |
| **OPEN QUESTION** | Per-attempt timeout and absolute decision deadline | Must be measured from Provider Shadow latency and current market freshness budgets | `NEEDS HUMAN DECISION` |
| **OPEN QUESTION** | Per-decision token/cost ceiling | Positive bounded values; retry stops if usage cannot be safely measured | `NEEDS HUMAN DECISION` |

**INFERENCE** — The smallest defensible starting candidate is two total attempts (first attempt plus at most one retry), but repository/runtime evidence is insufficient to freeze this as an accepted value.

## 10. Freshness / Stale / Late / Duplicate Contract

**DESIGN DECISION** — Freshness has three independent gates:

1. input facts were fresh/valid when the immutable binding was created;
2. result arrived before the absolute decision deadline;
3. durable state/evidence/plan/action-time facts still match at each existing authority boundary.

**DESIGN DECISION** — Passing an earlier gate never waives a later gate.

**DESIGN DECISION** — A changed `state_version`, evidence revision/hash, snapshot digest, configuration, instrument/market identity or expired deadline makes the result stale for risk-increasing action. It is persisted for audit with zero plan/account/position/ledger/protection mutation.

**DESIGN DECISION** — `pair_id` does not change merely because one attempt retries. A new evidence revision, new snapshot binding, new configured experiment definition, or new decision deadline creates a new unit/invocation and may not reuse the old result.

**DESIGN DECISION** — Duplicate detection is based on explicit invocation/experiment/pair/arm identities and an atomic accepted-result claim, never symbol plus timestamp. A late or duplicate provider completion may preserve attempt audit evidence, but must not create a second final decision, plan, intent, order, Fill, Position or attribution chain, and must not reuse a final result across experiment/pair/arm boundaries.

## 11. Provider Capability Boundary

### 11.1 Required capabilities

| Classification | Capability | V1 requirement |
|---|---|---|
| **DESIGN DECISION** | Single Primary Provider | REQUIRED |
| **DESIGN DECISION** | Provider-native strict structured output for the approved schema | REQUIRED |
| **DESIGN DECISION** | Explicit refusal and incomplete/partial response detection | REQUIRED |
| **DESIGN DECISION** | Bounded request timeout and best-effort cancellation | REQUIRED |
| **DESIGN DECISION** | Client request identity and provider request/response identity | REQUIRED |
| **DESIGN DECISION** | Configured and provider-reported model identity | REQUIRED |
| **DESIGN DECISION** | Typed/classifiable transport and provider errors | REQUIRED |
| **DESIGN DECISION** | Input/output/total usage reporting, with unknown represented as NULL | REQUIRED capability; actual missing report must fail the cost-controlled retry decision closed |
| **DESIGN DECISION** | No tools, no autonomous loop | REQUIRED boundary |
| **DESIGN DECISION** | Streaming | `NOT NEEDED V1` |
| **DESIGN DECISION** | Automatic fallback, router or model voting | FORBIDDEN |

### 11.2 Abstraction boundary

**DESIGN DECISION** — Reuse and minimally adapt the current lightweight `AIProvider` boundary. Do not add LiteLLM Router, Agent Runtime, LangGraph, multi-provider abstraction or a generic orchestration framework.

**DESIGN DECISION** — Provider-specific parsing, refusal, request IDs, usage and error classification belong inside the provider adapter. Business validation, binding, freshness and authority remain provider-neutral application responsibilities.

## 12. Provenance Contract

### 12.1 Current readiness

**FACT** — Current `ai_decisions` stores `decision_id`, `snapshot_id`, run/state/config/prompt/schema versions, `model`, status, raw rendered prompt, normalized response/error and creation time.

**FACT** — It does not separately store provider identity, provider request/response ID, attempt sequence/retry reason, request/response times, latency, token usage, cost, experiment/arm/pair identity, or a snapshot payload hash.

**DESIGN DECISION** — Current provenance readiness is `PARTIAL`.

### 12.2 V1 classification

| Classification | Provenance item | Verdict | Notes |
|---|---|---|---|
| **DESIGN DECISION** | provider identity | `MUST HAVE` | Stable adapter/provider identifier |
| **DESIGN DECISION** | configured model identity | `MUST HAVE` | Exact configured value |
| **DESIGN DECISION** | provider-reported model/version/deployment identity | `MUST HAVE` when available; otherwise explicit `UNKNOWN` | Model drift must be detectable/stratifiable |
| **DESIGN DECISION** | client invocation/request ID | `MUST HAVE` | Binds all attempts |
| **DESIGN DECISION** | provider request/response ID | `MUST HAVE` when returned; otherwise explicit `UNKNOWN` | Never synthesize a provider ID |
| **DESIGN DECISION** | attempt number | `MUST HAVE` | Starts at 1; unique within invocation |
| **DESIGN DECISION** | retry type/reason and prior-attempt link | `MUST HAVE` | Transport versus validation retained |
| **DESIGN DECISION** | request started/finished and response received timestamps | `MUST HAVE` | Timezone-aware |
| **DESIGN DECISION** | latency | `MUST HAVE` | Derived from monotonic measurement; wall timestamps retained for audit |
| **DESIGN DECISION** | input binding digest and versions | `MUST HAVE` | Includes opportunity/evidence/snapshot/state/config |
| **DESIGN DECISION** | prompt version / schema version | `MUST HAVE` | Existing fields retained |
| **DESIGN DECISION** | rendered prompt | `MUST HAVE` | Existing redaction rule retained; secrets forbidden |
| **DESIGN DECISION** | normalized structured output and digest | `MUST HAVE` | Accepted or rejected normalized result |
| **DESIGN DECISION** | provider outcome/status and exact error categories | `MUST HAVE` | Includes refusal/incomplete/late/duplicate diagnostics |
| **DESIGN DECISION** | input/output/total token usage | `MUST HAVE` when reported; otherwise NULL + unavailable reason | Missing is not zero |
| **DESIGN DECISION** | experiment identity / arm identity / pair identity | `MUST HAVE` | No post-hoc pairing |
| **DESIGN DECISION** | raw provider request envelope | `SHOULD HAVE` | Redacted; authorization/secret headers never stored |
| **DESIGN DECISION** | raw provider response envelope | `SHOULD HAVE` | Redacted, retention-bounded; refusal/incomplete metadata preserved |
| **DESIGN DECISION** | provider monetary cost | `SHOULD HAVE` | Store provider-reported cost if available or computed cost with pricing-version provenance; otherwise NULL |
| **DESIGN DECISION** | SDK/library version | `SHOULD HAVE` | Useful for reproducibility without becoming authority |
| **DESIGN DECISION** | full HTTP headers/body duplication beyond audit need | `NOT NEEDED V1` | Avoid secrets and unbounded storage |
| **DESIGN DECISION** | chain-of-thought / hidden reasoning | `NOT NEEDED V1` | Never required or stored |

**OPEN QUESTION** — Raw provider envelope retention duration/size and access policy require Human Decision before implementation.

## 13. Experiment Unit / Arm / Pairing Contract

### 13.1 Experiment identity

**DESIGN DECISION** — `experiment_id` identifies one predeclared, versioned experiment definition: placement, baseline policy/version, configured treatment contract/version, prompt version, schema version, provider/model eligibility rule, input-binding version, horizons, metric definitions and activation mode. Changing any of those creates a new `experiment_id` and a distinct invocation/final-decision lineage.

**DESIGN DECISION** — One experiment unit is:

```text
Same opportunity_id
+ same evidence_id / evidence_revision / evidence_hash
+ same frozen DecisionInputBinding / snapshot_payload_hash
+ same experiment_id
```

**DESIGN DECISION** — `pair_id` is deterministically derived from the experiment identity and exact unit identity. It is not derived from symbol plus timestamp.

**DESIGN DECISION** — Each pair has exactly two arm identities:

```text
WITHOUT_AI_BASELINE
REAL_AI_TREATMENT
```

**DESIGN DECISION** — Each arm result must link directly to `experiment_id`, `pair_id`, `arm_id`, the same Opportunity/Evidence binding and its own decision/result provenance. Missing or failed arm results remain explicit; they are never deleted from the denominator.

**DESIGN DECISION** — Replaying the same `snapshot_id` with the same configured model under a different `experiment_id`, prompt/schema version or configured treatment version must be durably representable without primary-key or logical-identity collision. Different experiment lineages cannot overwrite one another.

### 13.2 Assignment

**DESIGN DECISION** — Arm economic authority, if any, is declared before provider invocation and before outcomes are known. Assignment cannot change because of AI failure, refusal, latency, result quality or observed market outcome.

**DESIGN DECISION** — The experiment must report coverage counters: eligible units, paired units, missing baseline, missing treatment, invalid/refused/stale/late treatment, complete/insufficient/invalid forward outcomes and excluded units by predeclared reason.

## 14. Baseline Contract

### 14.1 Candidate comparison

| Classification | Candidate | Represents without AI? | Same Opportunity/Evidence? | Replayable? | New confounder / verdict |
|---|---|---|---|---|---|
| **FACT** | A. Existing G2 strategy/candidate logic | It is deterministic market/strategy evidence, not a complete Trade Decision or executable plan | Yes | Yes | Cannot by itself supply stop/target/sizing |
| **INFERENCE** | B. New deterministic fixed trade policy | Potentially | Could | Could | Would invent a second strategy/business policy; not authorized |
| **FACT** | C. Recorded/Fake provider behavior | No; it is an AI-shaped test/replay response | Yes when keyed correctly | Yes | Calling it without-AI would be false attribution |
| **FACT** | D. Formal accepted Opportunity admission plus SE-02C outcome | Yes for the decision-selection question; no model participates | Yes, by exact identity | Yes | Reuses accepted facts; cannot claim symmetric TradePlan/execution PnL |

### 14.2 Recommended baseline

**DESIGN DECISION — WITHOUT-AI SELECTION BENCHMARK** — `ALL_ELIGIBLE_LONG_SHADOW_V1`:

1. For every formally admitted `BREAKOUT_RETEST` Opportunity with the exact immutable Evidence and eligible SPOT/LONG context, the without-AI baseline decision is **participate LONG**.
2. The baseline is deterministic and uses only the accepted Opportunity admission fact; it does not call any provider.
3. Its outcome is the already accepted SE-02C per-opportunity Forward Outcome for predeclared horizons.
4. It is shadow-only in V1 and creates no TradePlan, intent, order, Fill, Position, balance or Ledger mutation.
5. Missing/stale reference evidence and `INSUFFICIENT_DATA`/`INVALID` outcomes remain explicit and are not silently dropped.

**INFERENCE** — This is the minimum interpretable comparison for “did AI selection improve over taking every already-qualified opportunity?” It neither invents stop/target rules nor pretends Recorded/Fake AI is non-AI.

**DESIGN DECISION** — This baseline answers only: among the exact same formally qualified Opportunities, does Real AI improve participation/selection quality relative to participating LONG in every eligible Opportunity? It has no baseline TradePlan, entry, stop, target, sizing or Paper execution. Therefore it supports selection/participation edge only and cannot prove full-package or executed-trade economic superiority.

## 15. Treatment Contract

**DESIGN DECISION** — `REAL_AI_TREATMENT` may produce the complete `AIAnalysis` package for the bound unit, but the Provider Shadow / SE-02C paired causal treatment variable is only `PARTICIPATE_LONG` versus `NO_LONG`.

**DESIGN DECISION** — Opportunity qualification, Evidence identity/revision/hash and the accepted SE-02C outcome/cost semantics are identical across the selection comparison. Any later Gate B Paper activation keeps the Accepted main TradePlan algorithm, sizing cap, Risk policy, Execution algorithm, Protection, Position Re-evaluation, Recovery, Reconciliation and accounting unchanged; that downstream safety invariant does not turn the shadow baseline into a symmetric executable strategy.

**DESIGN DECISION** — Treatment participation semantics for decision-quality evaluation are:

| Classification | Treatment result | Participation |
|---|---|---|
| **DESIGN DECISION** | `VALID + LONG_BIAS` with the bound family explicitly selected | `PARTICIPATE_LONG` |
| **DESIGN DECISION** | `VALID + WAIT` | `NO_LONG` |
| **DESIGN DECISION** | `VALID + SHORT_BIAS` | `NO_LONG`; bearish analysis cannot execute short |
| **DESIGN DECISION** | invalid/refused/provider-failed/stale/late/duplicate-loser | `NO_LONG`; failure remains in operational denominator |

**DESIGN DECISION** — AI confidence is never used to remove samples after the fact. Any confidence threshold must be predeclared as a new treatment version/experiment identity.

**DESIGN DECISION** — AI `entry_zone`, `stop_loss`, `take_profit`, `suggested_position_pct` and `probe` may be persisted, validated, linked to provenance and used for diagnostics. Their effects are not included in the SE-02C selection-edge causal claim.

## 16. Economic Authority Per Pair

### 16.1 V1 choice

**DESIGN DECISION** — V1 uses **one authoritative arm plus one shadow counterfactual**. It does not use two isolated paper-economic arms.

| Classification | Phase | Authoritative economic arm | Shadow arm |
|---|---|---|---|
| **DESIGN DECISION** | Provider Shadow | Existing accepted runtime behavior only; Real AI has zero new-action authority | Both experiment decisions/outcomes are observational |
| **DESIGN DECISION** | Paper Economic Activation | Exactly one predeclared arm, expected to be `REAL_AI_TREATMENT` only after Gate B Human approval | `ALL_ELIGIBLE_LONG_SHADOW_V1` remains outcome-only |

**DESIGN DECISION** — If the authoritative AI arm fails, the result is no new risk. The baseline must not be promoted to an automatic fallback.

**DESIGN DECISION** — The non-authoritative arm may consume immutable evidence and SE-02C outcomes but cannot write economic state.

**DESIGN DECISION** — Gate B may allow the separately Human-approved Real AI arm to use the complete validated `AIAnalysis` package for Paper economic action. That activation/safety evidence is not proof that the full package has economic edge and cannot use Gate C's selection benchmark to claim entry, stop, target or sizing superiority.

**INFERENCE** — Two paper-economic arms would require isolated accounts, duplicate plan/execution/accounting state and new attribution/reconciliation semantics. That does not solve a current Real AI V1 gap because SE-02C already supplies a same-evidence shadow outcome. It fails the over-engineering test.

## 17. Metrics Contract

### 17.1 Metric classes

| Classification | Metric | Category | Readiness / rule |
|---|---|---|---|
| **DESIGN DECISION** | Selection Expectancy by arm and delta | `REQUIRED TO DECLARE SELECTION EDGE` | `NOT AVAILABLE YET`; requires accepted SE-02D over LONG/NO-LONG participation |
| **DESIGN DECISION** | Cost-adjusted Forward Return by predeclared horizon | `REQUIRED TO DECLARE SELECTION EDGE` | READY from SE-02C per eligible unit; aggregation pending SE-02D |
| **DESIGN DECISION** | Executable LONG / reference Forward Return | `REQUIRED TO DECLARE SELECTION EDGE` | READY from SE-02C only as the common per-opportunity LONG counterfactual outcome |
| **DESIGN DECISION** | R-Multiple | `REQUIRED FOR A FUTURE FULL-PACKAGE / EXECUTED-TRADE CLAIM` | `NOT AVAILABLE YET`; outside Gate C V1 selection claim |
| **DESIGN DECISION** | Drawdown / tail loss distribution | `REQUIRED FOR A FUTURE DEPLOYABLE ECONOMIC CLAIM` | `NOT AVAILABLE YET`; outside Gate C V1 selection claim |
| **DESIGN DECISION** | Trade Frequency / participation rate | `REQUIRED TO DECLARE SELECTION EDGE` | PARTIAL; pair/arm aggregation missing |
| **DESIGN DECISION** | Missed Opportunities / avoided losses | `REQUIRED TO DECLARE SELECTION EDGE` | SE-02C outcomes READY; pair/arm aggregation missing |
| **DESIGN DECISION** | Fixed counterfactual cost | `REQUIRED TO DECLARE SELECTION EDGE` | SE-02C fixed cost model READY; no actual execution-cost claim |
| **DESIGN DECISION** | Actual fees/slippage | `REQUIRED FOR A FUTURE EXECUTED-TRADE CLAIM` | Accepted symmetric economic comparison contract absent; outside Gate C V1 selection claim |
| **DESIGN DECISION** | Market regime/family stratification | `REQUIRED TO DECLARE SELECTION EDGE` | `NOT AVAILABLE YET` as accepted aggregation; do not hide regime concentration |
| **DESIGN DECISION** | MFE / MAE | `REQUIRED FOR DIAGNOSTICS` | READY per unit from SE-02C |
| **DESIGN DECISION** | Win Rate | `REQUIRED FOR DIAGNOSTICS` | Not sufficient alone; aggregation contract pending |
| **DESIGN DECISION** | AI latency, p50/p95/p99 and deadline miss rate | `REQUIRED FOR DIAGNOSTICS` and activation | Provenance missing; must be measured in Shadow |
| **DESIGN DECISION** | AI token usage and cost | `REQUIRED FOR DIAGNOSTICS`; required in net benefit decision | Provenance missing; unknown is not zero |
| **DESIGN DECISION** | Failure rate | `REQUIRED FOR DIAGNOSTICS` and activation | Must include all eligible units |
| **DESIGN DECISION** | Refusal rate | `REQUIRED FOR DIAGNOSTICS` and activation | Separate diagnostic category |
| **DESIGN DECISION** | Schema failure rate | `REQUIRED FOR DIAGNOSTICS` and activation | Separate diagnostic category |
| **DESIGN DECISION** | Stale/late/duplicate rates | `REQUIRED FOR DIAGNOSTICS` and activation | Separate categories; duplicate losers cannot inflate sample count |
| **DESIGN DECISION** | Sharpe/Sortino/profit factor/optimization ranking | `OPTIONAL LATER` | Not needed for V1 decision contract |

### 17.2 Edge-claim discipline

**DESIGN DECISION** — Win Rate alone cannot prove AI edge.

**DESIGN DECISION** — A V1 selection-edge declaration must use predeclared horizons, sample inclusion/exclusion, baseline/treatment versions, LONG/NO-LONG semantics, metric formulas, uncertainty method, sample sufficiency and pass thresholds. Post-hoc selection of profitable horizon/regime/model is forbidden.

**DESIGN DECISION** — Operational failures count against the treatment and remain in the experiment denominator. Provider cost and failure-induced missed opportunities must not be omitted from the net conclusion.

**DESIGN DECISION** — No metric in this section may attribute observed selection results to AI entry, stop, target, sizing, probe, full-package or executed-trade effects. Proving any such effect requires a separately Human-accepted symmetric economic comparison contract in which baseline and treatment have comparable economic semantics. D1 does not design that future contract.

**OPEN QUESTION** — Exact primary horizon, minimum sample size, statistical uncertainty method, materiality threshold, acceptable tail-risk bound and regime sufficiency are `NEEDS HUMAN DECISION` after SE-02D design evidence exists.

## 18. SE-02C / SE-02D Boundary

### 18.1 SE-02C provides

| Classification | Accepted evidence |
|---|---|
| **FACT** | Exact scope `(opportunity_id, evidence_id, horizon)` with immutable revision-1 normal outcome |
| **FACT** | Horizons `30s / 5m / 15m / 1h` |
| **FACT** | Stable Capture Anchor reference and complete causal Forward BBO path |
| **FACT** | MFE, MAE, reference return, executable LONG return and cost-adjusted Forward Return |
| **FACT** | `COMPLETE / INSUFFICIENT_DATA / INVALID` terminal semantics |
| **FACT** | Replay/Forward provenance separation, deterministic concurrency and stable read snapshot |

### 18.2 SE-02D must provide later

| Classification | Missing evidence contract |
|---|---|
| **FACT** | Family/arm aggregation and Expectancy are not implemented or accepted |
| **DESIGN DECISION** | D1 does not implement or pre-accept SE-02D |
| **DESIGN DECISION** | Gate C cannot pass until an independently approved SE-02D contract can aggregate the explicit pairs/arms without post-hoc joins |

**DESIGN DECISION** — D1 does not duplicate SE-02C calculation and does not redefine its cost model, horizon identity, revision chain, completeness or immutable outcome semantics.

**DESIGN DECISION** — In D1, SE-02C supplies only the common per-opportunity outcome used to compare `PARTICIPATE_LONG` with `NO_LONG`. It does not supply baseline plan, stop, target, sizing or execution semantics and therefore cannot prove full-package/economic execution edge.

## 19. Activation Gates

### 19.1 Gate A — Provider Shadow Activation

**DESIGN DECISION** — Gate A permits real provider calls and durable experiment/provenance recording only. Real AI results have zero new risk-increasing economic authority.

All items are required:

| Classification | Prerequisite |
|---|---|
| **DESIGN DECISION** | Human-Accepted D1 design plus separately accepted implementation |
| **DESIGN DECISION** | Exact input binding and experiment/arm/pair identity implemented and independently reviewed |
| **DESIGN DECISION** | Provider-native strict schema, refusal/incomplete handling and deterministic business validation verified with the selected provider/model |
| **DESIGN DECISION** | Bounded retry/deadline/cost values approved and enforced; no fallback/voting |
| **DESIGN DECISION** | Complete minimum provenance and explicit UNKNOWN semantics verified |
| **DESIGN DECISION** | Secret/redaction/storage/retention controls verified |
| **DESIGN DECISION** | AI failure isolation proves deterministic runtime, existing protection, cancel and risk-reducing exits continue |
| **DESIGN DECISION** | Approved bounded invocation host/lifecycle exists; continuous live Shadow additionally requires accepted Opportunity-to-G3 handoff |
| **DESIGN DECISION** | Production and Live remain disabled unless separately authorized |

### 19.2 Gate B — Paper Economic Activation

**DESIGN DECISION** — Gate B permits exactly one predeclared arm per pair to create Paper economic action. It does not declare AI edge.

**DESIGN DECISION** — Gate B is an activation/safety gate. Even when a Human-approved Real AI arm uses the complete validated `AIAnalysis` package, Gate B evidence is not causal proof that the full package—or its entry, stop, target or sizing fields—has economic edge.

All items are required:

| Classification | Prerequisite |
|---|---|
| **DESIGN DECISION** | Gate A passed with a Human-approved minimum Shadow observation window and operational thresholds |
| **DESIGN DECISION** | Separate Human approval explicitly names the authoritative arm and activation version |
| **DESIGN DECISION** | Every authoritative path uses current deterministic `DecisionValidator`, `TradePlanManager`, structurally present `SystemRiskGate`, Paper Execution and existing accounting/protection authority |
| **DESIGN DECISION** | Action-time state/evidence/plan/market freshness revalidation and atomic duplicate fencing independently verified |
| **DESIGN DECISION** | Failure/refusal/stale/late/duplicate result produces no new risk and never activates baseline fallback |
| **DESIGN DECISION** | Recovery/Reconciliation/Protection remain provider-independent and verified |
| **DESIGN DECISION** | Paper only, Spot Long only; Live and short execution remain forbidden |

### 19.3 Gate C — Real AI Trade-Decision Selection Edge Evidence

**DESIGN DECISION** — Gate C V1 is an evidence verdict for **Real AI Trade-Decision selection / participation edge only**. Passing provider or Paper activation gates does not pass Gate C.

All items are required:

| Classification | Prerequisite |
|---|---|
| **DESIGN DECISION** | Accepted SE-02D aggregation/Expectancy contract |
| **DESIGN DECISION** | Complete explicit pair/arm identity and predeclared sample rules |
| **DESIGN DECISION** | Human-approved primary horizon, sample sufficiency, uncertainty method, materiality threshold and tail/regime criteria |
| **DESIGN DECISION** | Treatment selection Expectancy materially exceeds the `ALL_ELIGIBLE_LONG_SHADOW_V1` selection benchmark after the accepted SE-02C fixed counterfactual costs, with no hidden failure exclusions |
| **DESIGN DECISION** | Participation frequency, missed opportunities, avoided losses, outcome distribution/tail, regime concentration, latency, failure and provider cost are reported |
| **DESIGN DECISION** | Results are reproducible from immutable Evidence, decision provenance and accepted outcomes |
| **DESIGN DECISION** | Independent review plus explicit Human verdict |

**DESIGN DECISION** — Gate C does not prove AI entry/stop/target/sizing superiority, full `AIAnalysis` package economic edge or actual executed-trade edge. Those claims require a separately accepted symmetric economic comparison contract; D1 neither designs nor authorizes one.

**DESIGN DECISION** — Gate C does not authorize Live Trading. Live remains a separate future gate requiring Edge + Safety + Runtime evidence.

## 20. Runtime Host Dependency Boundary

### 20.1 Host requirements

| Classification | Required property |
|---|---|
| **DESIGN DECISION** | Bounded invocation with absolute deadline and cancellation |
| **DESIGN DECISION** | Supervised lifecycle and failure isolation |
| **DESIGN DECISION** | Durable invocation/attempt/result provenance before any action |
| **DESIGN DECISION** | Explicit Opportunity-to-G3 handoff preserving exact identities |
| **DESIGN DECISION** | Backpressure/bounded queue behavior that does not block protection |
| **DESIGN DECISION** | Restart-safe duplicate/late-result fencing |

### 20.2 Excluded host choices

**DESIGN DECISION** — D1 does not select or design `asyncio TaskGroup`, Docker supervisor, systemd, Celery, Redis, Kafka, Kubernetes or any other host technology.

**DESIGN DECISION** — Host implementation and activation remain separate tasks. This document specifies only the properties Real AI requires from that future boundary.

## 21. Over-engineering Exclusions

### 21.1 Added-contract gap trace

| Classification | Added logical contract | Current real gap solved | Why the existing field is insufficient |
|---|---|---|---|
| **DESIGN DECISION** | `snapshot_payload_hash` / `input_binding_digest` | Prevent one result from being applied to another market/evidence state | Current `snapshot_id` derivation does not content-hash the frozen payload and the snapshot lacks Opportunity/Evidence identity |
| **DESIGN DECISION** | Invocation-aware durable final-decision identity + `decision_invocation_id` + attempt identity | Bound experiment lineage, retries, cancellation, late completion and exactly one final winner | Current `decision_id(snapshot_id, model)` can collide across experiments/versions and does not identify an invocation or individual attempts |
| **DESIGN DECISION** | Separate `error_category` + attempt history | Preserve refusal/transport/schema/business/late diagnostics without inventing DB statuses | Current singular `status`/`error` cannot express the required failure provenance |
| **DESIGN DECISION** | `experiment_id` / `pair_id` / `arm_id` | Explicit same-unit with/without-AI attribution | Current schema has no experiment or arm identity; symbol/time joins are unsafe |
| **DESIGN DECISION** | `ALL_ELIGIBLE_LONG_SHADOW_V1` | Provide a genuine without-AI baseline without a second strategy/execution engine | G2 candidates are not a complete decision policy; Fake/Recorded providers are still AI-shaped inputs |

### 21.2 Excluded complexity

| Classification | Exclusion | Current real gap solved? | Verdict |
|---|---|---|---|
| **DESIGN DECISION** | LiteLLM Router / automatic fallback | No; conflicts with Single Primary Provider and confounds attribution | Exclude |
| **DESIGN DECISION** | Multi-provider/model voting | No; changes treatment and attribution | Exclude |
| **DESIGN DECISION** | Agent Runtime / tool loop / autonomous planning | No; V1 is one bounded advisory call | Exclude |
| **DESIGN DECISION** | LangGraph/checkpointer runtime | No; Host is separate and current call is not a graph | Exclude |
| **DESIGN DECISION** | Langfuse as required platform | No; identity shape can be implemented minimally in the monolith | Exclude initially |
| **DESIGN DECISION** | Third-party structured-output wrapper stack | No; provider-native schema + existing Pydantic + deterministic validation is sufficient | Exclude initially |
| **DESIGN DECISION** | New trading framework | No; G2-G5 authority chain already exists | Exclude |
| **DESIGN DECISION** | Two isolated paper-economic accounts/arms | No; SE-02C supplies shadow outcome | Exclude V1 |
| **DESIGN DECISION** | New baseline strategy with invented stop/target/sizing | No accepted evidence supports it | Exclude |
| **DESIGN DECISION** | New DecisionStatus enum family in D1 | No; existing status plus separate diagnostics is sufficient | Exclude from D1 |
| **DESIGN DECISION** | DB migration/schema design | Logical gaps are identified, but physical persistence is a future implementation design | Exclude from D1 |

## 22. Human Decisions Required

| Classification | Decision | Why repository evidence is insufficient |
|---|---|---|
| **OPEN QUESTION** | Freeze joint/transport/validation attempt limits within §9.2 candidate ranges | No Real AI latency/failure/cost distribution exists |
| **OPEN QUESTION** | Freeze per-attempt timeout, absolute decision deadline and per-decision token/cost budget | Requires Provider Shadow measurements and market-freshness budget |
| **OPEN QUESTION** | Freeze raw provider envelope retention size/duration/access policy | Security, audit and storage trade-off is not accepted |
| **OPEN QUESTION** | Freeze Gate A Shadow minimum window and operational pass thresholds | No Real AI runtime evidence exists |
| **OPEN QUESTION** | Freeze Gate C selection-edge primary horizon, minimum sample, uncertainty method, materiality/tail/regime thresholds | Depends on future accepted SE-02D design and sample evidence |

**DESIGN DECISION** — The recommended baseline, arm model and authority boundary are not open implementation choices. They remain Candidate Design pending Human review of this document as a whole.

## 23. Acceptance Criteria for Future Implementation

Future implementation is not complete unless independent evidence proves every item:

| Classification | AC |
|---|---|
| **DESIGN DECISION** | AC-01: Real AI placement is only C. Trade Decision |
| **DESIGN DECISION** | AC-02: AI receives no repository/risk/execution/accounting/protection handles |
| **DESIGN DECISION** | AC-03: Exact Opportunity/Evidence/Snapshot/State/Config/Prompt/Schema/treatment-version binding is durable and mismatch tests fail closed |
| **DESIGN DECISION** | AC-04: Provider-native strict schema is used; schema and deterministic business validation are separately tested |
| **DESIGN DECISION** | AC-05: Refusal, timeout, unavailable, malformed, schema, business, unsupported evidence, numeric, stale, late, duplicate, partial and exhaustion paths match §8 |
| **DESIGN DECISION** | AC-06: Transport/validation retries are separate, bounded and share absolute deadline/attempt/cost caps |
| **DESIGN DECISION** | AC-07: No provider/model fallback, voting, tools or autonomous loop exists |
| **DESIGN DECISION** | AC-08: Required provenance is complete; unavailable usage/cost is NULL/UNKNOWN, not zero |
| **DESIGN DECISION** | AC-09: `experiment_id`, `pair_id` and both arm identities are explicit; no symbol/timestamp post-hoc pairing |
| **DESIGN DECISION** | AC-10: Baseline is exactly `ALL_ELIGIBLE_LONG_SHADOW_V1` or a later separately Human-approved contract version |
| **DESIGN DECISION** | AC-11: Real AI may change only the accepted Trade Decision output while downstream algorithms/policies remain unchanged; Provider Shadow / SE-02C treatment is exactly `PARTICIPATE_LONG` versus `NO_LONG`, excluding entry/stop/target/sizing/probe effects from the selection-edge claim |
| **DESIGN DECISION** | AC-12: At most one predeclared arm has Paper economic authority; shadow cannot write economic state or become fallback |
| **DESIGN DECISION** | AC-13: AI failure yields zero new risk while protection, cancel and risk-reducing exit continue |
| **DESIGN DECISION** | AC-14: `SHORT_BIAS` remains analysis/no-long and cannot create short execution |
| **DESIGN DECISION** | AC-15: SystemRiskGate is structurally present on every Real-AI-authoritative risk-increasing path |
| **DESIGN DECISION** | AC-16: Duplicate/late concurrent completions may retain attempt audit evidence but cannot create a second final decision, plan/intent/order/fill/economic attribution or cross-lineage reuse |
| **DESIGN DECISION** | AC-17: SE-02C outcomes are reused without redefining calculator semantics; SE-02D remains a separate acceptance task |
| **DESIGN DECISION** | AC-18: Gate A/B/C are implemented and reviewed as separate gates; no gate implies Live authority |
| **DESIGN DECISION** | AC-19: Real provider contract tests and bounded failure/adverse-case tests use actual selected provider behavior where required; Fake/Recorded evidence is labeled as such |
| **DESIGN DECISION** | AC-20: Production, main and Runtime remain unchanged until their separate authorized gates |
| **DESIGN DECISION** | AC-21: One `decision_invocation_id` has exactly one logical durable final decision; retries share that invocation while every attempt has separate identity and provider-attempt provenance |
| **DESIGN DECISION** | AC-22: Durable final-decision identity is collision-free across `experiment_id`, `pair_id`, `arm_id`, `input_binding_digest`, prompt/schema version and configured treatment version under one-to-one invocation linkage |
| **DESIGN DECISION** | AC-23: Replay of the same snapshot/configured model across experiment, prompt/schema or treatment versions is durably representable without PK/identity collision or lineage overwrite |
| **DESIGN DECISION** | AC-24: Gate B is activation/safety evidence only; Gate C can declare selection/participation edge only, while any full-package or executed-trade claim remains blocked on a separately accepted symmetric economic comparison contract |

## 24. Risks / Unknowns

| Classification | Risk / unknown | Required treatment |
|---|---|---|
| **FACT** | No Real AI provider samples exist | Do not claim latency, cost, failure rate or output quality |
| **FACT** | Current `DecisionSnapshot` is not Opportunity/Evidence-bound and has no payload hash | Gate A blocked until future contract implementation and review |
| **FACT** | Current provider adapter uses JSON object parsing, not provider-native strict schema | Gate A blocked until corrected by a separately authorized implementation |
| **FACT** | Current retry loop does not distinguish transport and validation and has no joint deadline/cost contract | Gate A blocked until corrected by a separately authorized implementation |
| **FACT** | Current `ai_decisions` provenance is partial | Gate A blocked until minimum provenance is implemented |
| **FACT** | live Opportunity-to-G3 handoff and Integrated Runtime Host are absent | Continuous Shadow/Economic activation blocked; D1 does not design the host |
| **FACT** | SE-02D Expectancy/family aggregation is absent | Gate C blocked |
| **INFERENCE** | Model/provider behavior may drift under an alias | Persist exact identities; stratify or exclude unverifiable drift under predeclared rules |
| **INFERENCE** | AI output fields beyond direction can influence Paper behavior after Gate B | Persist/validate them, but exclude their effects from the SE-02C selection-edge causal claim |
| **INFERENCE** | `ALL_ELIGIBLE_LONG_SHADOW_V1` is a selection benchmark, not a symmetric executable strategy | Do not overclaim entry/stop/target/sizing, full-package or executed-trade superiority |
| **FACT** | Current `decision_id(snapshot_id, model)` is not experiment/invocation-aware | Gate A blocked until future implementation proves an allowed collision-free durable identity approach |
| **OPEN QUESTION** | Current Accepted main sample sufficiency across regimes | Must be measured later; calculator readiness is not sample readiness |
| **OPEN QUESTION** | Accepted definitions for R-Multiple, drawdown, actual slippage benchmark and statistical thresholds | Future separately approved design work |

---

## Candidate Design Verdict

```text
Real AI V1 Placement = C. Trade Decision only
AI = Advisory
Deterministic System = Authority
Experiment unit = Same Opportunity + Same immutable Evidence + Same frozen input binding
Baseline = ALL_ELIGIBLE_LONG_SHADOW_V1 (WITHOUT-AI SELECTION BENCHMARK)
Causal treatment = PARTICIPATE_LONG vs NO_LONG
Gate C V1 claim = REAL AI TRADE-DECISION SELECTION / PARTICIPATION EDGE ONLY
Full package / executed-trade edge = NOT PROVEN; REQUIRES A SEPARATELY ACCEPTED SYMMETRIC ECONOMIC COMPARISON CONTRACT
Decision identity = One decision_invocation_id -> exactly one collision-free logical durable final decision
Economic arms = One predeclared authoritative arm + one shadow counterfactual
Provider fallback / model voting = FORBIDDEN
SE-02C = REUSE
SE-02D = REQUIRED BEFORE EDGE DECLARATION / NOT IMPLEMENTED HERE
Status = CANDIDATE DESIGN / PENDING HUMAN REVIEW
```
