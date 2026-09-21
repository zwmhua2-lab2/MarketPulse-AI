# UI-RD01-I03｜交易审计读取 Product Read 实施需求

## Artifact Status

Requirement ID:

`UI-RD01-I03-REQ-04`

Status:

`ACCEPTED / FROZEN`

Human Freeze:

`CONFIRMED — 2026-09-21`

Independent Requirement Re-Review:

`PASS WITH NON-BLOCKING FINDING — READY FOR HUMAN FREEZE`

Accepted Limited Amendment:

`UI-RD01-I03-PLA-01 = ACCEPTED`

Remaining Finding:

`R04-P2-01 = NON-BLOCKING / REMAINS`

Implementation Authorization:

`NOT GRANTED`

Implementation Status:

`UI-RD01-I03 = NOT STARTED`

Protocol Baseline:

`v1.4.4 / ACCEPTED`

Repository Baseline at Human Freeze:

`f7715f58f9da6fa57426b1df31a23692ac6a41a1`

Parent Design:

`UI-RD01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`

This Requirement Freeze does not itself execute, start, or authorize `UI-RD01-I03`. `UI-RD01-I03` requires its own separate Formal Task; this persistence task creates none.

---

## A0. Authority

Requirement:

`UI-RD01-I03-REQ-04`

Human Freeze:

`CONFIRMED — 2026-09-21`

Independent Review:

`PASS WITH NON-BLOCKING FINDING — READY FOR HUMAN FREEZE`

Limited Amendment:

`UI-RD01-I03-PLA-01 = ACCEPTED`

Known Finding:

`R04-P2-01 = NON-BLOCKING / REMAINS`

Implementation:

`NOT STARTED / NOT AUTHORIZED`

Earlier I03 drafts are design history only.

---

## A1. Limited Amendment — UI-RD01-I03-PLA-01

Accepted with Human Freeze.

Parent UI-RD01 Trading timeline originally defined:

* `occurred_at DESC`
* `entity_kind DESC`
* `entity_id DESC`

I03 replaces only its Trading timeline third key with:

* `occurred_at DESC`
* `entity_kind DESC`
* `timeline_event_id DESC`

Reason:

`entity_id` remains business identity, while one business entity can legitimately produce multiple timeline events, including equal-time events.

The Amendment:

* applies only to TradingAuditRead;
* does not alter Scanner, Opportunity, Incident or Edge ordering;
* does not change business IDs;
* does not add schema/persistence;
* does not create historical-as-of semantics.

---

## A2. Product Purpose

Implement:

`GET /api/v1/product/trading-audit`

Read-only.

It answers：

`系统如何处理经济动作，现在资金 / 仓位怎样？`

Strict separation:

`Risk Accepted != Execution Intent != Paper Order != Fill != Position`

Only durable Fill proves Paper Economic Action.

---

## A3. Scope

One Human Acceptance Batch:

* TradingAuditRead endpoint
* Account
* Current Positions
* Position Protection
* Current ACTIVE Plans
* Current OPEN Orders
* Pending Intent capability state
* Typed Trading Timeline
* Initial Intent rejection classification
* Deferred Risk / Execution refusals
* Order cancellation evidence
* Traceability
* Economic integrity validation
* run_mode ownership classification
* stable PostgreSQL read snapshot
* Product HTTP failures
* OpenAPI
* generated.ts
* verification

---

## A4. Out of Scope

Do not introduce/redesign:

* Trading Engine
* Risk Engine
* Execution Engine
* Position state machine
* Protection Engine
* Ledger/accounting semantics
* mutation controls
* pending-intent persistence
* partial fills
* exchange orders
* Account Equity
* Unrealized PnL
* portfolio valuation
* Trade lifetime total PnL
* Replay selector
* historical revision-as-of
* Real AI activation
* PRE-01B-I2
* live G2→G3
* Gate A/B/C
* Live Trading
* new schema
* new migration
* new index without separate approval

---

## A5. Endpoint / Authentication

Exactly:

`GET /api/v1/product/trading-audit`

No I03 detail routes.

Existing authenticated Product session boundary applies.

Authentication occurs before Product-data existence is observable.

Invalid session:

`401`

---

## A6. Query Contract

Exactly:

* `limit`
* `cursor`
* `instrument_id`

`limit`:

* default = 100
* min = 1
* max = 500

`instrument_id`:

* optional
* 1..64 chars
* exact durable identity

No case normalization, aliases, new regex grammar.

Valid absent identity:

`200`

matching projected collections = `EMPTY`

Not supported:

* range
* start
* end
* status
* side
* order_type
* entity_kind
* trade_id
* run_mode selector
* source selector

---

## A7. Runtime Boundary

Current Host owns request `run_mode`.

No user selector.

Existing values:

* LIVE_PAPER
* REPLAY
* TEST

Replay/Test must not masquerade as LIVE_PAPER.

---

## A8. Stable Snapshot

Every active request uses one:

`REPEATABLE READ / READ ONLY`

PostgreSQL transaction covering all required durable:

* Account
* TradePlan
* Decision
* ExecutionIntent
* PaperOrder
* Fill
* Position
* Trade
* Ledger
* PositionEvent
* Outbox cancellation evidence
* Edge attribution

Materialize all coupled facts before transaction end.

This is per-request consistency only.

---

## A9. Host Absent

After authentication:

* HTTP 200
* ReadSurfaceClass = A
* OperationalAvailability = NOT_ACTIVATED
* ProjectionState = UNAVAILABLE
* ReadFailureReason = null
* data = null
* next_cursor = null

Not EMPTY, SOURCE_UNAVAILABLE or CAPABILITY_NOT_INTEGRATED.

---

## A10. Parent Response

`TradingAuditReadResponse`

contains:

* meta: ProjectionMetaDTO
* operational_context: OperationalContextDTO
* data: TradingAuditDataDTO | null

Data:

* account
* positions
* active_plans
* open_orders
* pending_intents
* timeline

---

## A11. Successful Parent Meta

Active successful read:

* read_surface_class = A
* operational_availability = ACTIVE
* projection_state = FRESH
* read_failure_reason = null
* is_partial = false
* observed_at = null

`meta.snapshot_at` is authoritative database snapshot time.

`meta.next_cursor` is opaque cursor or null.

Legal nested states such as:

* CAPABILITY_NOT_INTEGRATED
* PARTIAL
* NOT_PROVABLE
* NO_PROVABLE_RECORD
* NOT_OCCURRED

do not change parent `is_partial` to true.

No normal I03 section-local partial-200 path.

Untrustworthy whole economic projection:

`503`

---

## A12. Operational Context

Active TradingAudit:

* run_mode = Host current run_mode
* runtime_instance_id = Host current instance_id
* host_state = Host current state
* operational_provenance = Host current run_mode value
* context_snapshot_at = context acquisition time

Operational context does not manufacture historical-row provenance.

---

## A13. Nested DTOs

* account: `TraceNodeDTO[TradingAccountDTO]`
* positions: `TradingCollectionDTO[TradingPositionDTO]`
* active_plans: `TradingCollectionDTO[TradingPlanDTO]`
* open_orders: `TradingCollectionDTO[TradingOpenOrderDTO]`
* pending_intents: `TradingPendingIntentCapabilityDTO`
* timeline: `TradingTimelinePageDTO`

`TradingCollectionDTO[T]`:

* state: ProjectionState
* items: list[T] | null

Legal:

* FRESH + non-empty list
* EMPTY + []
* CAPABILITY_NOT_INTEGRATED + null

---

## A14. TradingTimelinePageDTO

Fields:

* state: ProjectionState
* items: list[TradingTimelineItem]
* timeline_upper_bound: datetime

Non-empty:

`FRESH + items`

Zero timeline rows:

`EMPTY + []`

`timeline_upper_bound` remains present.

Pagination cursor only appears in:

`meta.next_cursor`

---

## A15. Account

TradingAccountDTO:

* account_id
* cash_balance
* reserved_cash
* available_cash
* realized_pnl
* updated_at

`available_cash = cash_balance - reserved_cash`

No:

* equity
* unrealized_pnl
* portfolio_value
* buying_power

---

## A16. Legal Empty Workspace

If current run_mode has no:

* Account
* ExecutionIntent
* PaperOrder
* Fill
* Position
* Trade
* Ledger

then:

* HTTP 200
* account.state = NO_PROVABLE_RECORD
* account.data = null
* account.evidence_basis = null

Account-dependent reconciliation is not evaluated for this truly empty workspace.

---

## A17. Missing Account With Economic Facts

Account absent while dependent economic facts exist:

`503 SNAPSHOT_FAILED`

Never zero-fill.

---

## A18. Position

TradingPositionDTO:

* position_id
* instrument_id
* state
* quantity
* average_cost
* trade_id | null
* updated_at
* protection

State:

* quantity > 0 → OPEN
* quantity == 0 → FLAT
* quantity < 0 → SNAPSHOT_FAILED

No Product-specific position-state tolerance.

Do not expose:

* side
* position_version
* PositionRecord.realized_pnl

---

## A19. Protection DTO

TradingPositionProtectionDTO:

* state
* authority

States:

* NOT_REQUIRED
* PROTECTED
* UNPROTECTED
* UNKNOWN

Authority:

TradingProtectionAuthorityDTO:

* plan_id
* plan_version
* stop_loss
* take_profit
* updated_at

---

## A20. Protection Mapping

Five durable Position protection fields:

* protection_plan_id
* protection_plan_version
* protection_stop_loss
* protection_take_profit
* protection_updated_at

FLAT + all null:

* NOT_REQUIRED
* authority = null

FLAT + any populated:

`503 SNAPSHOT_FAILED`

OPEN + all null:

* UNPROTECTED
* authority = null

OPEN + all non-null and valid:

* PROTECTED
* authority = exact durable Position authority

Valid includes:

* plan_id non-empty
* plan_version >= 1
* finite stop_loss/take_profit
* stop_loss < take_profit
* valid updated_at

OPEN + malformed/incomplete/non-classifiable:

* UNKNOWN
* authority = null

Never Plan-backfill protection.

Known Finding:

`R04-P2-01`

This Product validity classification is intentionally more conservative than the current Runtime reader for a hypothetical `protection_plan_id=""`.

`UNKNOWN` does not mean Runtime Protection has been disabled.

---

## A21. Active Plans

Include every durable:

`status == ACTIVE`

including TTL-expired rows.

Order:

* instrument_id ASC
* plan_id ASC

---

## A22. TradingPlanDTO

Fields:

* plan_id
* snapshot_id
* decision_id
* instrument_id
* symbol
* plan_version
* status
* created_at
* expires_at
* ttl_expired
* order_type
* side
* entry_zone
* stop_loss
* take_profit
* intended_notional
* invalidation | null
* decision

`decision = TraceNodeDTO[TradingDecisionDTO]`

`ttl_expired = request meta.snapshot_at >= expires_at`

---

## A23. Active Plan Integrity

Every ACTIVE Plan is rehydrated through accepted typed `TradePlan`.

Validate row/payload identity including applicable:

* plan_id
* snapshot_id
* decision_id
* instrument_id
* run_mode
* state_version
* plan_version
* created_at
* expires_at

plus typed business fields.

Invalid schema / identity / impossible ACTIVE representation:

`503 SNAPSHOT_FAILED`

Do not silently omit.

Do not expose raw payload.

---

## A24. Plan TTL vs Protection

`Plan TTL = risk-increasing freshness`

`Position durable protection snapshot = protection-lifetime authority`

TTL-expired ACTIVE is legal.

TTL expiry does not remove durable Position protection.

New ACTIVE Plan does not automatically replace it.

---

## A25. TradingDecisionDTO

Fields:

* decision_id
* snapshot_id
* status
* model
* created_at
* opportunity_binding

`opportunity_binding = TraceNodeDTO[TradingOpportunityBindingDTO]`

Binding:

* opportunity_id
* evidence_id
* evidence_revision
* evidence_hash
* feature_snapshot_hash

Never raw prompt/response/provider error.

---

## A26. Decision Binding

`current canonical Evidence != historical Decision-bound Evidence`

No exact historical binding:

`NO_PROVABLE_RECORD`

Explicit durable binding/reference that is missing, cross-opportunity, conflicting or identity-invalid:

`503 SNAPSHOT_FAILED`

Never substitute current canonical Evidence.

Latest-main additive direct Advisory bindings may serve as exact durable evidence when applicable.

If multiple explicit durable sources prove incompatible identities:

`503 SNAPSHOT_FAILED`

No silent source precedence may hide an explicit contradiction.

---

## A27. Open Orders

Only:

`status == OPEN`

DTO:

* order_id
* intent_id
* plan_id | null
* instrument_id
* side
* order_type
* quantity
* limit_price | null
* reserved_cash
* reserved_quantity
* created_at

Order:

* created_at DESC
* order_id DESC

OPEN means waiting for possible Fill only.

---

## A28. Pending Intents

TradingPendingIntentCapabilityDTO:

* state: ProjectionState
* items: null

Always V1:

* CAPABILITY_NOT_INTEGRATED
* items = null

Never `EMPTY + []`.

No new persistence.

---

## A29. Timeline Common Shape

Every item:

* timeline_event_id
* entity_kind
* entity_id
* event_type
* occurred_at
* traceability

`entity_id` = business identity.

`timeline_event_id` = stable unique Product timeline-event identity.

No arbitrary dict/raw payload.

---

## A30. Timeline Kinds

* PLAN
* RISK
* EXECUTION
* INTENT
* ORDER
* FILL
* LEDGER
* TRADE_OPEN
* TRADE_CLOSE
* POSITION_EVENT

---

## A31. Timeline Event Identity

PLAN_CREATED:

* entity_id = plan_id
* timeline_event_id = `plan:create:{plan_id}`

RISK_ACCEPTED / RISK_REJECTED:

* entity_id = intent_id
* timeline_event_id = `attribution:{attribution_event_id}`

EXECUTION_REJECTED:

* entity_id = intent_id
* timeline_event_id = `attribution:{attribution_event_id}`

INTENT_EXECUTED / INTENT_REJECTED:

* entity_id = intent_id
* timeline_event_id = `intent:{intent_id}`

ORDER_CREATED:

* entity_id = order_id
* timeline_event_id = `order:create:{order_id}`

ORDER_CANCELLED:

* entity_id = order_id
* timeline_event_id = `outbox:{outbox_id}`

FILL_OCCURRED:

* entity_id = fill_id
* timeline_event_id = `fill:{fill_id}`

SETTLEMENT_RECORDED:

* entity_id = entry_id
* timeline_event_id = `ledger:{entry_id}`

TRADE_OPEN:

* entity_id = trade_id
* timeline_event_id = `trade:open:{trade_id}`

TRADE_CLOSE:

* entity_id = trade_id
* timeline_event_id = `trade:close:{trade_id}`

Position Event:

* entity_id = event_id
* timeline_event_id = `position-event:{event_id}`

Stable across requests.

---

## A32. Trading Cursor

Accepted PLA-01 ordering:

* occurred_at DESC
* entity_kind DESC
* timeline_event_id DESC

Cursor binds:

* version
* endpoint
* run_mode
* instrument_id filter
* timeline_upper_bound
* occurred_at
* entity_kind
* timeline_event_id

Wrong scope/malformed:

`422`

---

## A33. timeline_upper_bound

First page:

`timeline_upper_bound = PostgreSQL database time`

Include:

`occurred_at <= timeline_upper_bound`

Later pages reuse it.

It prevents later event-time facts from entering the sequence.

It does not prevent later-committed backdated rows.

No cross-request historical MVCC claim.

---

## A34. Timeline Union

Concrete members:

* TradingPlanTimelineItemDTO
* TradingRiskTimelineItemDTO
* TradingExecutionTimelineItemDTO
* TradingIntentTimelineItemDTO
* TradingOrderCreatedTimelineItemDTO
* TradingOrderCancelledTimelineItemDTO
* TradingFillTimelineItemDTO
* TradingLedgerTimelineItemDTO
* TradingTradeOpenTimelineItemDTO
* TradingTradeCloseTimelineItemDTO
* TradingPositionEventTimelineItemDTO

---

## A35. PLAN_CREATED

Fields:

* plan_id
* snapshot_id
* decision_id
* instrument_id
* symbol
* plan_version
* created_at
* expires_at

No current mutable Plan status.

---

## A36. RISK Timeline

Fields:

* attribution_event_id
* intent_id
* plan_id | null
* order_id | null
* authority | null
* reason | null
* opportunity_id | null
* evidence_id | null

RISK_REJECTED:

* authority required
* reason required

RISK_ACCEPTED:

* authority = null
* reason = null

unless exact accepted durable facts prove otherwise.

Do not invent.

---

## A37. EXECUTION_REJECTED

Fields:

* attribution_event_id
* intent_id
* plan_id | null
* reason
* opportunity_id | null
* evidence_id | null

No Risk authority field.

---

## A38. INTENT Timeline

Fields:

* intent_id
* plan_id | null
* instrument_id
* status
* reason | null
* created_at
* initial_rejection

`initial_rejection = TraceNodeDTO[TradingIntentRejectionDTO]`

---

## A39. Initial Rejection DTO

Fields:

* kind: RISK | EXECUTION
* attribution_event_id
* authority | null
* reason
* occurred_at

EXECUTED Intent:

* state = NOT_OCCURRED
* data = null
* evidence_basis = durable_intent_status

Exact rejected classification:

* state = PRESENT
* data = typed rejection
* evidence_basis = exact_edge_attribution

Unprovable rejected classification:

* state = NO_PROVABLE_RECORD
* data = null
* evidence_basis = null

No reason-text inference.

---

## A40. Initial Rejection Matching

Exact classification matches:

* subject_id == intent_id
* payload.intent_id == intent_id
* payload.plan_id == durable intent.plan_id
* payload.reason == durable intent.reason
* occurred_at == durable intent.created_at

Risk:

* RISK_REJECTED
* authority required

Execution:

* EXECUTION_REJECTED
* authority = null

Incompatible exact classification:

`503 SNAPSHOT_FAILED`

---

## A41. Deferred Fill Refusals

An EXECUTED Intent may later have its OPEN LIMIT fill attempt refused.

Intent remains EXECUTED.

Each refusal is independent:

* RISK_REJECTED
* EXECUTION_REJECTED

Multiple later refusals on the same Intent are legal.

---

## A42. ORDER_CREATED

Fields:

* order_id
* intent_id
* plan_id | null
* instrument_id
* side
* order_type
* quantity
* limit_price | null
* created_at

No future mutable status.

---

## A43. ORDER_CANCELLED

Authority:

* `OutboxRecord.event_type == ORDER_CANCELLED`
* `aggregate_id == order_id`

validated against exact Order.

Fields:

* order_id
* instrument_id
* cancelled_at

Do not infer cancellation from disappearance or no Fill.

---

## A44. Missing Cancellation Evidence

Durable Order is CANCELLED but exact cancellation-time fact absent:

* do not fabricate ORDER_CANCELLED
* do not fabricate cancelled_at

The ORDER_CREATED item's current-request traceability includes:

`ORDER_CANCELLATION_EVENT`

---

## A45. Fill DTO

Fields:

* fill_id
* order_id
* intent_id
* instrument_id
* side
* price
* quantity
* fee
* created_at

Instrument/side come from exact Order.

Fill without Order:

`503 SNAPSHOT_FAILED`

---

## A46. Ledger DTO

Fields:

* entry_id
* fill_id
* instrument_id
* entry_type
* cash_delta
* fee
* settlement_realized_pnl
* created_at

Allowlisted payload only.

No raw Ledger payload.

Settlement realized PnL is settlement-only.

---

## A47. TRADE_OPEN

Fields:

* trade_id
* instrument_id
* opened_at

No close/current-state backfill.

---

## A48. TRADE_CLOSE

Fields:

* trade_id
* instrument_id
* closed_at
* exit_reason | null

No lifetime total PnL.

---

## A49. PositionEvent

Whitelist:

* SL_TRIGGERED
* TP_TRIGGERED
* AI_REEVALUATION
* ADD
* REDUCE
* CLOSE
* MANUAL_CLOSE
* PLAN_UPDATED
* PLAN_REPLACED
* CANCEL_ADD
* RISK_BLOCKED

Exclude:

* PROTECTION_EVALUATED
* RECOVERY
* SYMBOL_BLOCK
* EMERGENCY_ACTION

Fields:

* event_id
* instrument_id
* position_id | null
* plan_id | null
* order_id | null
* fill_id | null
* created_at

No raw payload.

---

## A50. Economic Roles

* BUY = RISK_INCREASING
* SELL = RISK_REDUCING

Risk-reducing SELL does not require new Risk Admission.

---

## A51. No-Plan SELL

Internal:

`plan_id = ""`

maps to Product null only when stable snapshot proves:

* Intent.plan_id == ""
* Intent.status == EXECUTED
* exact Order
* same intent_id
* plan_id == ""
* side == SELL
* order_type == MARKET
* status == FILLED
* exact Fill
* exact Ledger
* coherent run_mode/instrument

Otherwise:

`503 SNAPSHOT_FAILED`

---

## A52. Traceability DTO

Status:

* COMPLETE
* PARTIAL
* NOT_PROVABLE

missing_links:

* DECISION
* OPPORTUNITY_BINDING
* PLAN
* INTENT
* ORDER
* FILL
* LEDGER
* RISK_ATTRIBUTION
* REJECTION_CLASSIFICATION
* ORDER_CANCELLATION_EVENT

Every event must have an explicit matrix row.

---

## A53. Traceability Algorithm

1. Validate primary fact.
2. Apply exact matrix.
3. Apply strong economic integrity.
4. Evaluate remaining lineage.

All applicable links proven:

* COMPLETE
* missing_links=[]

Some proven, some genuinely unprovable:

`PARTIAL`

Primary fact authoritative but no meaningful applicable external lineage:

`NOT_PROVABLE`

Explicitly empty applicable set:

* COMPLETE
* []

---

## A54. PLAN_CREATED Traceability

Required:

* DECISION
* OPPORTUNITY_BINDING

Bad explicit reference → SNAPSHOT_FAILED.

Historical absence → PARTIAL/NOT_PROVABLE according to remaining proof.

---

## A55. INTENT_REJECTED

Required:

* PLAN
* DECISION
* OPPORTUNITY_BINDING
* REJECTION_CLASSIFICATION

No-plan rejected Intent:

`SNAPSHOT_FAILED`

---

## A56. INTENT_EXECUTED BUY

Exact Order is strong invariant.

Missing Order:

`SNAPSHOT_FAILED`

Trace:

* ORDER
* PLAN
* DECISION
* OPPORTUNITY_BINDING
* RISK_ATTRIBUTION

---

## A57. INTENT_EXECUTED SELL With Plan

Strong:

`ORDER`

Trace:

* ORDER
* PLAN
* DECISION
* OPPORTUNITY_BINDING

No new Risk requirement.

---

## A58. INTENT_EXECUTED SELL Without Plan

Prove accepted no-plan bundle first.

Trace requirement:

`ORDER`

Not applicable:

* PLAN
* DECISION
* OPPORTUNITY_BINDING
* RISK_ATTRIBUTION

---

## A59. ORDER_CREATED BUY

Required:

* INTENT
* PLAN
* DECISION
* OPPORTUNITY_BINDING
* RISK_ATTRIBUTION

If current Order is CANCELLED:

`ORDER_CANCELLATION_EVENT`

also applies.

No Fill requirement.

---

## A60. ORDER_CREATED SELL With Plan

Required:

* INTENT
* PLAN
* DECISION
* OPPORTUNITY_BINDING

If CANCELLED:

`ORDER_CANCELLATION_EVENT`

also applies.

---

## A61. ORDER_CREATED SELL Without Plan

Required:

`INTENT`

No-plan bundle must be valid.

---

## A62. ORDER_CANCELLED

Required:

* ORDER
* INTENT

Then inherit Order BUY / SELL-with-plan ancestry.

Empty-plan CANCELLED Order:

`SNAPSHOT_FAILED`

---

## A63. Initial RISK Event

Initial RISK_ACCEPTED / RISK_REJECTED requires:

* INTENT
* PLAN
* DECISION
* OPPORTUNITY_BINDING

Risk event proves its own Risk classification.

---

## A64. Deferred RISK_REJECTED

Required:

* INTENT
* ORDER
* PLAN
* DECISION
* OPPORTUNITY_BINDING

Intent may remain EXECUTED.

---

## A65. Initial EXECUTION_REJECTED

Required:

* INTENT
* PLAN
* DECISION
* OPPORTUNITY_BINDING

No Risk attribution required.

---

## A66. Deferred EXECUTION_REJECTED

Required:

* INTENT
* ORDER
* PLAN
* DECISION
* OPPORTUNITY_BINDING

No Risk attribution required.

---

## A67. Fill BUY

Strong:

* ORDER
* INTENT
* LEDGER

Trace:

* PLAN
* DECISION
* OPPORTUNITY_BINDING
* RISK_ATTRIBUTION

---

## A68. Fill SELL With Plan

Strong:

* ORDER
* INTENT
* LEDGER

Trace:

* PLAN
* DECISION
* OPPORTUNITY_BINDING

---

## A69. Fill SELL Without Plan

Strong:

* ORDER
* INTENT
* LEDGER

No Plan/Decision/Opportunity/Risk requirement.

---

## A70. Ledger

Strong:

* FILL
* ORDER
* INTENT

Then inherit exact Fill BUY / SELL-with-plan / SELL-no-plan trace row.

---

## A71. TRADE_OPEN Trace

First require exact opening Fill.

Unprovable:

`missing_links = [FILL]`

Do not infer conditional ancestry.

When proven, opening Fill must be BUY or SNAPSHOT_FAILED.

Then require:

* ORDER
* INTENT
* LEDGER
* PLAN
* DECISION
* OPPORTUNITY_BINDING
* RISK_ATTRIBUTION

No nearest timestamp inference.

---

## A72. TRADE_CLOSE Trace

First require exact closing Fill.

Unprovable:

`missing_links = [FILL]`

Do not decide Plan applicability until Fill is known.

Closing Fill must be SELL or SNAPSHOT_FAILED.

Always require:

* ORDER
* INTENT
* LEDGER

SELL with real Plan additionally:

* PLAN
* DECISION
* OPPORTUNITY_BINDING

Accepted no-plan SELL:

`Plan ancestry NOT APPLICABLE`

No new Risk Admission.

---

## A73. PositionEvent Trace

Only explicit non-null:

* plan_id
* order_id
* fill_id

become applicable.

All null:

* COMPLETE
* missing_links=[]

---

## A74. Strong Economic Validation

Reuse accepted G3 reconciliation/accounting semantics for complete current run_mode.

At minimum:

1. Account.reserved_cash equals all OPEN BUY reserved_cash within accepted tolerance.
2. OPEN SELL reserved_quantity per instrument <= Position quantity within accepted tolerance.
3. Position quantities match complete BUY-minus-SELL Fill population.
4. available_cash = cash_balance - reserved_cash.
5. available_cash non-negative within accepted tolerance.
6. Every Fill has exactly one Ledger entry.
7. Every Ledger resolves to exact Fill.
8. Every FILLED Order has exactly one Fill.
9. Fill quantity matches FILLED Order quantity within accepted tolerance.
10. Fill.intent_id matches Order.intent_id.

No new accounting formula/tolerance.

---

## A75. Validation Population

Strong economic validation is over:

`entire current run_mode economic workspace`

not timeline page, instrument-filtered UI rows, or returned subset.

Instrument filter never narrows global Account reconciliation.

---

## A76. No Join-Hidden Orphans

Acquisition must detect:

* Fill without Order
* Ledger without Fill
* FILLED Order without Fill

Inner joins must not hide the inconsistency before validation.

---

## A77. run_mode Ownership

Economic rows without direct run_mode:

* PROVEN_CURRENT
* PROVEN_OTHER
* CONFLICTING_SCOPE
* UNSCOPED

Fill anchors:

* Fill.order_id → PaperOrder.run_mode
* Fill.intent_id → ExecutionIntent.run_mode

Ledger anchors:

* Ledger.account_id → Account.run_mode
* Ledger.fill_id → exact Fill ownership

All anchors current → PROVEN_CURRENT.

All anchors one other mode → PROVEN_OTHER.

Disagree → CONFLICTING_SCOPE.

No anchor → UNSCOPED.

---

## A78. Ownership Failure

* PROVEN_CURRENT → validate current run
* PROVEN_OTHER → exclude current projection/accounting
* CONFLICTING_SCOPE → 503 SNAPSHOT_FAILED
* UNSCOPED → 503 SNAPSHOT_FAILED

Unscoped economic facts are intentionally global blockers for active TradingAudit.

---

## A79. Audit Rows Without run_mode

Attribution / ORDER_CANCELLED Outbox only project when exact referenced business objects prove current-run ownership.

Unprovable ownership:

* do not assign
* do not guess

Absence may become trace gap.

It does not alone trigger global orphan-economic failure.

---

## A80. Economic Integrity Overrides Traceability

Examples:

* Fill without Order
* Fill without exactly one Ledger
* Ledger without Fill
* FILLED Order without Fill
* EXECUTED Intent without Order
* Position/Fill mismatch
* Account reservation mismatch
* OPEN SELL reservation exceeds Position
* impossible negative economic state
* CONFLICTING_SCOPE
* UNSCOPED

return:

`503 SNAPSHOT_FAILED`

Never PARTIAL/NOT_PROVABLE.

---

## A81. Economic Result Boundary

Allowed:

* Account.realized_pnl
* Fill fee
* Ledger cash_delta
* settlement_realized_pnl
* Trade lifecycle timestamps
* exit_reason

Forbidden:

* Account Equity
* Unrealized PnL
* Position.realized_pnl as Trade PnL
* Trade lifetime total PnL
* Forward Outcome as economic result

No `trades[]` aggregate in I03 V1.

---

## A82. HTTP Semantics

200:

* success
* empty
* legal trace absence
* capability not integrated
* Host not activated

401:

* auth

422:

* invalid query/cursor

503 SOURCE_UNAVAILABLE:

* active source/session/DB acquisition failure

503 SNAPSHOT_FAILED:

* snapshot failure
* economic contradiction
* bad explicit lineage
* conflicting or unscoped economic ownership

500:

* unclassified sanitized internal error

Reuse shared Product error DTOs.

---

## A83. Security

Never return:

* SQL
* SQL params
* DSN
* traceback
* exception text
* secrets
* tokens
* credentials
* raw ORM
* raw Plan payload
* raw PositionEvent payload
* raw Ledger payload
* raw AI prompt
* raw AI response

---

## A84. Current-State Ordering

positions:

`instrument_id ASC`

active_plans:

* instrument_id ASC
* plan_id ASC

open_orders:

* created_at DESC
* order_id DESC

---

## A85. Global Timeline Merge

Timeline page is the true global first `limit` items under A32 ordering.

Do not arbitrarily fetch a small N from each source and claim global completeness unless mathematically sufficient.

---

## A86. OpenAPI / Frontend Types

Same I03 batch includes:

* explicit Pydantic DTOs
* OpenAPI
* generated.ts regeneration
* `npm run generate:api`
* `npm run check:api-drift`
* frontend typecheck
* frontend tests
* frontend build

No hand-edited `generated.ts`.

No frontend duplicate authority DTOs.

---

## A87. Schema / Migration / Index

Default:

* Schema = ZERO CHANGE
* Migration = ZERO CHANGE
* Index = ZERO CHANGE

If real PostgreSQL evidence shows an index is required:

`STOP`

Separate Index Proposal + Human decision.

---

## A88. Performance Fixtures

A. Legal empty workspace.

B. Representative mixed workspace with at least:

* 2 instruments
* OPEN + FLAT Positions
* ACTIVE Plans
* OPEN Order
* FILLED Order
* CANCELLED Order
* Risk rejection
* Execution rejection
* Fill/Ledger settlement
* Trade open/close
* PositionEvent history

C. History-heavy isolated PostgreSQL:

* > = 5,000 Orders
* > = 5,000 Fills
* > = 5,000 Ledger entries
* > = 5,000 PositionEvents

plus sufficient lineage objects.

Verification workload, not production SLA.

---

## A89. Performance Gate

Structural PASS requires:

* no N+1 DB queries
* no query-per-row loop
* no provider/network I/O
* no silent truncation
* no weakened integrity validation
* resources released on success/failure/cancellation

Report:

* SQL statement count
* major query row counts
* rows materialized
* timeline limit+1 behavior
* global validation population sizes
* request duration
* DB transaction hold duration
* representative memory evidence
* dominant EXPLAIN plans
* cancellation cleanup

No invented millisecond SLA.

Performance receives explicit Human disposition later.

---

## A90. Required Tests

Mandatory categories:

* authentication / availability
* account / empty workspace
* multi-instrument global reconciliation
* OPEN / FLAT Position
* all four Protection classifications
* ACTIVE Plan TTL
* ACTIVE Plan corruption
* pending_intents capability
* initial Risk rejection
* initial Execution rejection
* deferred Risk refusal
* deferred Execution refusal
* multiple deferred refusals
* OPEN Order without Fill
* ORDER_CANCELLED exact evidence
* cancelled Order missing cancellation evidence
* Fill / Order / Ledger integrity
* accepted no-plan SELL
* invalid empty-plan shapes
* Decision exact historical binding
* no-record vs explicit bad Evidence
* TRADE_OPEN exact/missing Fill
* TRADE_CLOSE exact/missing Fill
* cursor scope
* equal-time event pagination
* stable snapshot concurrency
* run_mode orphan ownership
* SOURCE_UNAVAILABLE
* SNAPSHOT_FAILED
* sanitized 500
* no raw payload
* Forward Outcome not Economic Result
* no mutation

Specific adverse cases include:

Same ORDER + same timestamp:

* ORDER_CREATED
* ORDER_CANCELLED
* limit=1
* both exactly once across pages

Also:

* same Intent + equal-time multiple attribution events: no collision
* instrument_id=BTC does not narrow global Account validation
* orphan Fill not hidden by join
* orphan Ledger not hidden by join
* concurrent mutation after snapshot creation does not create mixed-state response

---

## A91. Acceptance Boundary

I03 is ready for Human Acceptance only after proving all frozen semantics, including:

* endpoint/auth/query exact
* PLA-01 ordering
* Host absent behavior
* active success meta
* stable request snapshot
* empty workspace distinction
* global reconciliation population
* OPEN SELL reservation invariant
* orphan detection
* run_mode ownership
* Position state
* Protection mapping
* Plan TTL separation
* ACTIVE Plan fail-closed
* Fill-only economic proof
* initial-vs-deferred rejection
* Risk-vs-Execution distinction
* Order cancellation evidence
* pending_intents capability gap
* no-plan SELL
* timeline DTO completeness
* timeline_event_id uniqueness
* traceability matrix completeness
* Decision binding integrity
* cursor scope
* no cross-request MVCC claim
* typed DTOs
* sanitization
* no unauthorized PnL
* OpenAPI/generated synchronization
* zero schema/migration/index unless separately approved
* performance evidence
* resource cleanup
* zero mutation
* zero unrelated activation progress

---

## A92. STOP Conditions

STOP if implementation requires:

* new schema
* new migration
* new persistence
* new index
* new Product endpoint
* new economic state
* new Risk semantics
* new Position authority
* new Order lifecycle semantics
* new pending-intent producer
* TradeEconomicSummary
* partial fills
* exchange orders
* mutation API

---

## A93. Human Decision Boundary

Human Freeze accepts together:

* `UI-RD01-I03-REQ-04`
* `UI-RD01-I03-PLA-01`

One Requirement freeze; not separate implementation batches.

---

## A94. Open Decisions

`NONE INTENTIONALLY DELEGATED TO IMPLEMENTATION`

Executor can choose only non-semantic implementation organization.

---

## A95. Frozen State

* `UI-RD01-I03-REQ-04 = ACCEPTED / FROZEN`
* `UI-RD01-I03-PLA-01 = ACCEPTED`
* `R04-P2-01 = REMAINS / NON-BLOCKING`
* `UI-RD01-I03 implementation = NOT STARTED / NOT AUTHORIZED`
