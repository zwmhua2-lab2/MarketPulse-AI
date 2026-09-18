# UI-RD01-I02｜市场扫描与机会追踪 Product Read 实施需求

## Artifact Status

Document ID:

`UI-RD01-I02-REQ-01`

Status:

`CANDIDATE / PENDING INDEPENDENT REVIEW`

Human Content Confirmation:

`CONFIRMED — 2026-09-19`

Implementation Authorization:

`NOT GRANTED`

Protocol Baseline:

`v1.4.0 / ACCEPTED`

Repository Baseline at Requirement Confirmation:

`08b6c5d6eebb5339756378ace80cb97d504ee25d`

Parent Design:

`UI-RD01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`

Implementation Status:

`UI-RD01-I02 = NOT STARTED / NOT AUTHORIZED`

---

## 1. Purpose

This requirement converts the already-frozen UI-RD01 Product Read Contract, Post-Freeze Amendment, and current Repository Truth into executable requirements for `UI-RD01-I02`.

It does not redesign UI-RD01 and does not alter frozen product semantics.

The Acceptance Batch contains:

* MarketScannerRead
* Opportunity Collection
* OpportunityTraceRead
* Frozen Range Contract
* Frozen Provenance Contract
* Keyset Cursor Contract
* TraceNodeState Contract
* CR-03 Current Canonical Evidence vs Decision-Bound Evidence
* CR-05 NOT_REACHED vs NOT_YET_DUE
* OpenAPI / generated.ts integration

Formal Product UI is out of scope.

---

## 2. Source of Truth

Priority:

1. `docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md`
2. `docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md`
3. `DECISIONS.md`
4. current Accepted Source / DB Schema / Tests
5. this Implementation Requirement

This requirement MUST NOT override a higher-priority Frozen Contract.

If implementation discovers a real Contract Conflict:

`STOP / REPORT`

The executor MUST NOT redesign it.

---

## 3. Repository Reality

### Scanner Durable Truth

Authority:

`MarketEventRecord`

Relevant facts include:

* event_id
* symbol
* instrument_id
* market_type
* event_type
* event_time
* received_time
* source
* strength
* priority
* state_version
* config_version
* payload

Product Scanner Event MUST NOT expose arbitrary `payload`.

### Strategy Candidate

Authority:

`StrategyCandidateRecord`

It holds:

* candidate_id
* strategy_id
* strategy_version
* instrument_id
* symbol
* event_id
* state_version
* config_version
* created_at

Therefore:

`Market Event → Strategy Candidate`

has an exact durable identity relation through:

`StrategyCandidateRecord.event_id`

### Opportunity Durable Truth

The current repository has no independent `OpportunityRecord`.

Opportunity durable authority is represented through the revision chain of:

`EdgeOpportunityEvidenceRecord`

It includes:

* opportunity_id
* evidence_id
* candidate_id
* family_id
* family_version
* instrument_id
* market_type
* evidence_revision
* evidence_contract_version
* evidence_hash
* feature_snapshot_hash
* supersedes_evidence_id
* detected_at
* evidence_at
* expires_at
* source_type
* source_identity
* source_manifest_id
* reference_data_status
* immutable evidence payload
* immutable feature snapshot payload

I02 MUST NOT create a new Opportunity table merely for Product API convenience.

Opportunity Collection MUST be projected by folding the `EdgeOpportunityEvidenceRecord` revision chain to a canonical Opportunity view.

### Forward Outcome

Authority:

`EdgeForwardOutcomeRecord`

Revision scope:

`(opportunity_id, evidence_id, horizon)`

Accepted horizons:

* 30s
* 5m
* 15m
* 1h

There is no durable `PENDING` row.

Before maturity, pending state is derived from authoritative backend:

* snapshot as_of
* evidence_at
* due_at
* horizon

### Attribution / Decision Link

Authority:

`EdgeAttributionEventRecord`

It persists:

* subject_type
* subject_id
* event_type
* opportunity_id
* evidence_id
* occurred_at
* recorded_at

For AI attribution:

`subject_id = decision_id`

This may prove a durable Decision → Opportunity/Evidence relation.

However:

`DecisionSnapshotRecord`

and

`AIDecisionRecord`

do not themselves contain Opportunity/Evidence binding.

They MUST NOT be used alone to guess historical Decision-bound Evidence.

### Current Market

RuntimeHost owns:

`LiveMarketState`

containing current `BestBidAsk` facts:

* instrument_id
* bid
* ask
* received_at
* tradable
* data_quality

RuntimeHost also owns current freshness/age authority.

Product API MUST NOT expose mutable `LiveMarketState` itself.

---

## 4. Acceptance Batch Structure

`UI-RD01-I02` remains one Human Acceptance Batch.

Execution is split serially into:

### I02-A

Market Scanner Read

Endpoint:

`GET /api/v1/product/market-scanner`

### I02-B

Opportunity Read

Endpoints:

`GET /api/v1/product/opportunities`

`GET /api/v1/product/opportunities/{opportunity_id}`

Execution:

`I02-A → I02-B`

I02-A completion is only an internal checkpoint.

Only after I02-A + I02-B complete, verify, independently review, and receive Human Acceptance may:

`UI-RD01-I02 = ACCEPTED / COMPLETE`

---

## 5. Shared Product Read Contract

I02 MUST reuse I01 accepted contracts:

* ReadSurfaceClass
* OperationalAvailability
* ProjectionState
* TraceNodeState
* ReadFailureReason
* OperationalContextDTO
* ProjectionMetaDTO
* RangeContextDTO
* FreshnessDTO
* SourceContextDTO
* TraceNodeDTO
* ProductReadContext
* authenticated Product API boundary

A parallel second state system MUST NOT be created.

---

## 6. Authentication Boundary

All I02 Product endpoints use the existing authenticated session dependency.

Unauthenticated:

`401`

Host disabled MUST NOT bypass authentication.

Product Read authorization grants no:

* mutation
* recovery
* repair
* risk action
* trading action
* activation

---

## 7. Frozen Range Contract

Supported values:

* 15m
* 30m
* 1h
* 4h
* 6h
* 24h
* 7d
* 30d
* custom

Default:

`1h`

### Preset

Backend freezes `effective_end` once when the first request begins.

Then:

`effective_start = effective_end - duration`

Response exposes:

* requested_range
* effective_start
* effective_end
* time_authority_field

Every subsequent cursor page inherits the same effective range.

The window MUST NOT slide with current time during pagination.

### Custom

`range=custom`

requires both:

* start
* end

They MUST be:

* timezone-aware
* UTC-normalized
* start < end

Missing one or invalid order:

`422`

Non-custom range with start/end:

`422`

---

## 8. Time Authority

Scanner:

`event_time ∈ [effective_start, effective_end)`

Opportunity:

`detected_at ∈ [effective_start, effective_end)`

Forward Outcome maturity derives from:

* evidence_at
* due_at
* horizon
* authoritative snapshot as_of

Forward Outcome is not truncated by the Opportunity list range after the Opportunity identity has been selected.

---

## 9. Pagination

Default:

`limit = 100`

Valid:

`1..500`

Use opaque, versioned keyset cursors.

No page-number/offset pagination.

Scanner sort:

`(event_time DESC, event_id DESC)`

Opportunity sort:

`(detected_at DESC, opportunity_id DESC)`

Cursor MUST bind:

* endpoint
* effective_start
* effective_end
* filters
* provenance
* sort tuple
* cursor version

Request/cursor validation MUST occur before source-availability short-circuit.

Malformed cursor remains:

`422`

even if DB/session is unavailable.

Cursor/range mismatch:

`422`

Cursor/filter mismatch:

`422`

Cursor/provenance mismatch:

`422`

---

## 10. Provenance

Operational MarketScanner:

`FORWARD_PAPER`

Operational Opportunity default:

`FORWARD_PAPER`

Allowed explicit Opportunity provenance:

* FORWARD_PAPER
* HISTORICAL_REPLAY

No implicit:

FORWARD_PAPER unavailable
→ HISTORICAL_REPLAY fallback

Every Opportunity projection MUST explicitly carry:

* source_type
* source_identity

When Forward truth cannot be provided, represent actual Product/capability state.

Do not fabricate data or silently substitute Replay.

---

## 11. I02-A MarketScannerRead

Endpoint:

`GET /api/v1/product/market-scanner`

Response contains two distinct authorities:

1. Current Market
2. Scanner Event History

They MUST NOT be presented as one global ACID snapshot.

---

## 12. Current Market Snapshot

I02-A MUST add a narrow, sanitized, immutable, non-owning Product market snapshot accessor.

Expected responsibility:

`RuntimeHost.product_market_snapshot()`

exposed through:

`ProductReadContext.market_snapshot()`

Exact symbol naming may be minimally adjusted for repository consistency, but ownership semantics MUST remain unchanged.

Product API MUST NOT:

* expose LiveMarketState references
* mutate LiveMarketState
* construct a provider
* construct a second market cache
* construct a second RuntimeHost
* pretend DB history is a current quote

Minimum current quote facts:

* instrument_id
* bid | null
* ask | null
* received_at | null
* tradable
* data_quality
* age_seconds | null
* snapshot_at

`data_quality` comes from RuntimeHost freshness authority.

Frontend MUST NOT recompute freshness.

Configured/required instrument with no current quote MUST NOT be represented as zero prices.

---

## 13. Scanner Event DTO

Allowed Product fields:

* event_id
* instrument_id
* symbol
* market_type
* event_type
* event_time
* received_time
* strength
* priority
* state_version
* config_version
* producer_source
* runtime_binding_status

`producer_source = MarketEventRecord.source`

`runtime_binding_status = NOT_RECORDED`

Forbidden historical Event fields:

* raw payload
* run_mode
* runtime_instance_id
* current runtime data_quality

Current quote quality belongs to Current Market only.

---

## 14. Scanner Consistency / Partial Failure

Current Market uses a runtime-memory snapshot.

Scanner history uses a stable DB read/page snapshot.

Each exposes its own source/snapshot metadata.

If current market is available while Scanner DB source fails, legal behavior is:

* HTTP 200
* is_partial = true
* Scanner section = UNAVAILABLE
* read_failure_reason = SOURCE_UNAVAILABLE

Equivalent section-local semantics apply in the opposite direction when safe and representable.

If the entire projection cannot form trustworthy output:

`503`

---

## 15. Scanner Empty

Successful authoritative DB query with zero events:

`ProjectionState = EMPTY`

with typed empty collection.

It is NOT:

* UNAVAILABLE
* CAPABILITY_NOT_INTEGRATED

---

## 16. I02-B Opportunity Collection

Endpoint:

`GET /api/v1/product/opportunities`

There is no independent Opportunity row.

The collection MUST derive logical Opportunities from:

`EdgeOpportunityEvidenceRecord`

grouped by:

`opportunity_id`

with accepted revision-chain validation and canonical-head selection.

---

## 17. Revision Folding Reuse

Accepted revision semantics already exist in:

`marketpulse.edge.aggregation_snapshot`

including:

* Evidence reconstruction validation
* full visible revision-chain validation
* canonical Evidence head selection
* Outcome revision validation
* canonical Outcome selection
* fail-closed integrity behavior

I02 MUST NOT create a second, slightly different folding algorithm.

Allowed implementation patterns:

* reuse existing accepted primitive
* minimally extract a shared primitive
* add a Product-specific adapter

Any extraction MUST preserve existing SE-02D semantics and regression.

Product API dependency MUST NOT be pushed into the Edge domain.

---

## 18. Canonical Opportunity Authority

For one `opportunity_id`:

rev1 → rev2

current Opportunity collection returns one logical Opportunity whose current canonical Evidence is rev2.

It MUST NOT return two logical Opportunities merely because two revisions exist.

---

## 19. Opportunity Collection DTO

Minimum typed facts:

* opportunity_id
* candidate_id
* family_id
* family_version
* instrument_id
* market_type
* detected_at
* evidence_at
* expires_at
* source_type
* source_identity
* evidence_contract_version
* current_canonical_evidence identity

Current canonical Evidence identity includes at least:

* evidence_id
* evidence_revision
* evidence_hash
* feature_snapshot_hash

Product response MUST NOT pass through arbitrary raw:

* evidence_payload
* feature_snapshot_payload

If future UI requires a field, expose it explicitly as typed allowlist data.

---

## 20. Opportunity Range

Collection authority:

`detected_at`

Canonical correction/revision MUST NOT create a new logical Opportunity time solely because a new Evidence revision was written.

---

## 21. Opportunity Detail

Endpoint:

`GET /api/v1/product/opportunities/{opportunity_id}`

All coupled durable trace reads MUST be formed within one explicit:

`REPEATABLE READ / READ ONLY`

stable DB snapshot.

At minimum the snapshot may need:

* Evidence revisions
* Forward Outcome revisions
* Strategy Candidate
* Market Event
* Attribution lineage
* related AI Decision facts when provable

Final immutable Product DTO is built after the stable durable read has been materialized.

---

## 22. Canonical Trace

Logical trace:

Market Event
→ Strategy Candidate
→ Opportunity
→ Current Canonical Evidence

Then parallel branches:

Forward Outcome

and:

Trading Decision

Forward Outcome is NOT a prerequisite for Trading Decision.

---

## 23. TraceNodeState

Use exactly the accepted six values:

* PRESENT
* NOT_OCCURRED
* NOT_REACHED
* NOT_YET_DUE
* NO_PROVABLE_RECORD
* CAPABILITY_NOT_INTEGRATED

Nested causal absence MUST NOT be represented by `ProjectionState.UNAVAILABLE`.

UNAVAILABLE is a read/source/snapshot failure state.

---

## 24. Exact Event / Candidate Relation

Evidence holds:

`candidate_id`

StrategyCandidateRecord holds:

`event_id`

Therefore exact durable linkage is:

Evidence
→ StrategyCandidateRecord(candidate_id)
→ MarketEventRecord(event_id)

MUST NOT infer relation from:

* timestamp proximity
* instrument equality
* event type
* payload similarity

If exact durable record cannot be proven:

use frozen absence semantics rather than guessing.

---

## 25. CR-03 Activation

When I02-B implementation begins:

`CR-03 = ACTIVE IMPLEMENTATION REQUIREMENT`

OpportunityTraceRead MUST distinguish:

`current_canonical_evidence`

from:

`decision_bound_evidence`

---

## 26. Current Canonical Evidence

Current Canonical Evidence comes from the current authoritative stable DB snapshot canonical Evidence head.

Example:

rev1 → rev2

Current canonical:

rev2

---

## 27. Decision-Bound Evidence

Decision-Bound Evidence is the exact Evidence revision historically bound to that Decision.

If Decision D1 bound rev1 and later rev2 becomes canonical:

* current_canonical_evidence = rev2
* D1.decision_bound_evidence = rev1

Historical Decision binding MUST NOT move to the current canonical head.

---

## 28. Current Durable Decision Binding Reality

`DecisionSnapshotRecord` and `AIDecisionRecord` themselves do not contain:

* opportunity_id
* evidence_id
* evidence_revision
* evidence_hash
* feature_snapshot_hash

They cannot independently prove the exact binding.

`EdgeAttributionEventRecord` can persist:

* subject_type = AI
* subject_id = decision_id
* opportunity_id
* evidence_id

Only when durable attribution lineage is:

1. unique
2. non-conflicting
3. subject_id exactly identifies the target decision
4. opportunity_id exactly identifies the target Opportunity
5. evidence_id exactly references a durable Evidence row belonging to that Opportunity

may Product Read classify that exact Evidence as:

`decision_bound_evidence = PRESENT`

The exact Evidence row then supplies:

* evidence_revision
* evidence_hash
* feature_snapshot_hash

---

## 29. Unprovable Decision Binding

Forbidden:

current canonical rev2
+
historical Decision with no exact durable Evidence binding
→ assume rev2

Forbidden inference sources:

* timing proximity
* instrument match
* payload similarity
* current canonical head

If exact durable binding cannot be proven:

`decision_bound_evidence.state = NO_PROVABLE_RECORD`

If durable causal truth proves AI was not reached:

`NOT_REACHED`

If the relevant capability is not currently integrated:

`CAPABILITY_NOT_INTEGRATED`

Classification MUST follow actual authority, not generic null.

---

## 30. PRE-01B-I2 Boundary

PRE-01B-I2 remains:

`NOT STARTED / NOT ACTIVATED`

I02 MUST NOT claim that it activates:

* AdvisoryIngress
* live exact Decision invocation pipeline
* live G2→G3
* Real AI

I02 only reads currently provable durable facts.

---

## 31. Forward Outcome Branch

Each detail projection MUST treat the accepted horizons independently:

* 30s
* 5m
* 15m
* 1h

No cross-horizon substitution or pooling.

Recommended semantic shape:

`forward_outcomes[horizon] = TraceNodeDTO`

Exact DTO representation remains an implementation detail so long as the frozen semantics remain explicit and typed.

---

## 32. CR-05 NOT_YET_DUE

There is no durable PENDING Forward Outcome row.

Backend maturity authority uses:

* snapshot as_of
* evidence_at
* horizon
* due_at

When:

`as_of < due_at`

the node state is:

`NOT_YET_DUE`

It MUST NOT be:

* NOT_REACHED
* NOT_OCCURRED
* UNAVAILABLE

Browser clock has no maturity authority.

---

## 33. Due But No Outcome

When:

`as_of >= due_at`

and there is no terminal Forward Outcome row:

the result MUST NOT remain `NOT_YET_DUE`.

Classification must reflect actual accepted capability/causal truth.

If current automatic production is not consumably integrated:

`CAPABILITY_NOT_INTEGRATED`

when that classification is supported by current authority.

Do not disguise an already-due missing result as temporal immaturity.

---

## 34. Forward Outcome Revisions

For exact scope:

`(opportunity_id, evidence_id, horizon)`

rev1 → rev2

current branch result is canonical rev2.

Revision-chain corruption MUST fail closed.

Implementation MUST NOT simply choose max(revision) while skipping integrity validation.

---

## 35. Decision Branch

Only durable, provable Decision facts may be exposed.

Product API MUST NOT expose:

* raw_prompt
* raw_response
* provider secret
* raw internal error text
* arbitrary Decision payload

A typed allowlist may include only facts actually supported by current durable authority, such as:

* decision_id | null
* durable Decision status
* attribution event type
* decision_bound_evidence
* trace node state

Unsupported fields MUST NOT be invented.

---

## 36. Stable Snapshot

The coupled durable relation set used for Opportunity detail MUST come from the same stable read transaction:

* current Evidence head
* exact historical Decision-bound Evidence
* Forward Outcome revisions
* Strategy Candidate
* Market Event
* Attribution lineage
* Decision row

Forbidden:

query Evidence in transaction A
→ close transaction
→ query Decision in transaction B
→ present them as one authoritative trace snapshot

---

## 37. Snapshot as_of

DB snapshot authority SHOULD reuse the already accepted PostgreSQL:

`statement_timestamp()`

semantics.

Python `datetime.now()` MUST NOT masquerade as the authoritative DB snapshot time.

---

## 38. Detail 404

If authoritative query confirms the requested Opportunity does not exist in the requested provenance:

`404`

If the source itself cannot be read:

do NOT return 404.

Use source/snapshot failure semantics.

---

## 39. Integrity Failure

Fail closed on at least:

* Evidence revision gap
* duplicate Evidence revision
* incorrect supersedes relation
* cross-Opportunity supersedes
* frozen identity mutation
* Outcome revision gap
* wrong Outcome scope
* conflicting exact attribution
* referenced Evidence missing
* invalid accepted enum reconstruction

Do not silently repair or choose a “best” row.

---

## 40. Error Semantics

Continue frozen UI-RD01 semantics.

200:

* FRESH
* STALE
* EMPTY
* NOT_ACTIVATED
* CAPABILITY_NOT_INTEGRATED
* legal partial result

401:

authentication failure

404:

authoritative detail identity absence

422:

invalid:

* range
* custom time
* limit
* cursor
* filter
* provenance

503 + SOURCE_UNAVAILABLE:

endpoint-wide active source failure

503 + SNAPSHOT_FAILED:

authoritative stable snapshot cannot be formed

500:

sanitized correlation ID only

No internal exception text may escape.

---

## 41. Host Absent

Operational Product endpoint with Host absent:

* ReadSurfaceClass = A
* OperationalAvailability = NOT_ACTIVATED
* ProjectionState = UNAVAILABLE
* ReadFailureReason = null
* HTTP = 200

It MUST NOT be mapped to:

* CAPABILITY_NOT_INTEGRATED
* SOURCE_UNAVAILABLE

---

## 42. Reuse Decisions

Reuse existing:

### Product Read

* ProductReadContext
* accepted Product enums
* Product error response contracts
* authentication dependency
* accepted cursor envelope/version semantics

### Runtime

* RuntimeHost
* LiveMarketState authority
* BestBidAsk
* Host-owned session factory

### Scanner

* MarketEventRecord
* accepted G2 EventType / MarketType semantics

### Opportunity

* EdgeOpportunityEvidenceRecord
* EdgeForwardOutcomeRecord
* EdgeAttributionEventRecord
* StrategyCandidateRecord
* MarketEventRecord

### Revision Folding

* accepted revision semantics in `marketpulse.edge.aggregation_snapshot`

MUST NOT build a second authority for:

* Opportunity identity
* Evidence hashing
* revision semantics
* Forward mathematics
* aggregation mathematics

---

## 43. No New Schema

Default:

* Schema = ZERO CHANGE
* Migration = ZERO CHANGE
* Index = ZERO CHANGE

If current durable truth cannot prove a trace link:

use accepted absence semantics.

Do not add persistence merely to make Product Trace look complete.

If the Frozen Contract truly cannot be implemented with current accepted truth:

STOP / REPORT for design decision.

---

## 44. DTO Boundary

Every Product business response uses explicit typed Pydantic DTOs.

Forbidden:

* dict[str, object] business response
* raw ORM rows
* arbitrary JSON payload passthrough

---

## 45. OpenAPI Boundary

I02-A synchronizes its own endpoint types when implemented.

I02-B synchronizes its own endpoint types when implemented.

Required chain:

Backend DTO
→ OpenAPI
→ generated.ts
→ frontend typecheck

I05 MUST NOT be the first batch that generates I02 types.

`frontend/src/api/generated.ts` is generated, never handwritten.

---

## 46. I02-A Internal Checkpoint

I02-A checkpoint requires:

* MarketScanner endpoint
* Current Market snapshot
* Scanner history
* range
* cursor
* source/partial semantics
* OpenAPI/generated
* focused tests
* regression

Allowed marker:

`I02-A IMPLEMENTED / INTERNAL CHECKPOINT`

It MUST NOT declare:

`UI-RD01-I02 ACCEPTED`

---

## 47. I02-B Completion Marker

After I02-B and the already-complete I02-A both verify:

Formal task_state remains:

`IMPLEMENTING`

Completion Marker:

`UI-RD01-I02 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`

Only Independent Review begins the REVIEW state.

---

## 48. I02-A Required Test Matrix

At minimum:

1. unauthenticated = 401
2. Host absent = 200 NOT_ACTIVATED + UNAVAILABLE
3. current quote typed projection
4. fresh quote
5. stale quote
6. missing quote
7. Scanner range uses event_time
8. left boundary inclusive
9. right boundary exclusive
10. default range = 1h
11. all preset ranges
12. valid custom range
13. invalid custom = 422
14. non-custom + start/end = 422
15. keyset ordering
16. equal event_time tied by event_id DESC
17. cursor inherits frozen effective range
18. malformed cursor = 422
19. range/cursor mismatch = 422
20. provenance/cursor mismatch = 422
21. zero Scanner rows = EMPTY
22. Event payload not exposed
23. producer_source present
24. runtime_binding_status = NOT_RECORDED
25. historical row has no runtime_instance_id
26. DB failure + current market available = legal partial
27. no implicit Replay fallback
28. OpenAPI generated contract
29. no second engine/provider/RuntimeHost

---

## 49. I02-B Required Test Matrix

At minimum:

1. unauthenticated = 401
2. Host absent semantics
3. default Opportunity range = 1h
4. detected_at left-inclusive
5. detected_at right-exclusive
6. custom range validation
7. Opportunity keyset ordering
8. same detected_at tied by opportunity_id DESC
9. cursor effective range freeze
10. provenance/cursor binding
11. default source = FORWARD_PAPER
12. HISTORICAL_REPLAY only when explicit
13. Forward absence never silently falls back to Replay
14. rev1 only → rev1 canonical
15. rev1→rev2 → rev2 canonical
16. collection emits one logical Opportunity
17. Evidence chain gap fails closed
18. incorrect supersedes fails closed
19. unknown Opportunity detail = 404
20. exact Market Event linkage
21. exact Strategy Candidate linkage
22. current_canonical_evidence = rev2
23. historical Decision exact binding to rev1 remains rev1
24. Decision binding does not follow current head
25. no exact Decision binding = NO_PROVABLE_RECORD
26. conflicting attribution does not produce guessed binding
27. AI_NOT_REACHED classification
28. PRE-01B-I2 remains not activated
29. 5m before due = NOT_YET_DUE
30. NOT_YET_DUE != NOT_REACHED
31. browser clock is not authority
32. due terminal outcome = PRESENT
33. Outcome rev1→rev2 = canonical rev2
34. Outcome chain corruption fails closed
35. no raw Evidence payload leakage
36. no raw AI prompt/response leakage
37. durable trace relations use one stable snapshot
38. DB statement_timestamp authority
39. OpenAPI/generated contract
40. existing SE-02D folding regressions remain PASS

---

## 50. Regression Boundary

Each I02 subtask performs:

* focused tests
* Ruff relevant scope
* OpenAPI drift
* frontend typecheck
* frontend tests
* frontend build

I02-B completion performs full backend regression.

Known shared PostgreSQL test exclusivity constraints remain applicable.

Concurrent external pytest contamination MUST NOT be misclassified as Product implementation failure.

---

## 51. Scope

UI-RD01-I02 Scope is limited to:

* MarketScannerRead
* Opportunity Collection
* OpportunityTraceRead
* range
* cursor
* provenance
* current Market Product snapshot accessor
* accepted Evidence/Outcome canonical folding consumption
* Decision-bound Evidence trace
* CR-03
* CR-05
* OpenAPI/generated integration
* tests/evidence/state docs

---

## 52. Explicitly Out of Scope

I02 does NOT implement:

* TradingAuditRead
* EdgeAggregateRead
* Product UI pages
* dashboard widgets
* trading actions
* mutation
* repair
* Recovery changes
* Risk changes
* Order changes
* Position changes
* Ledger changes
* Real AI activation
* PRE-01B-I2
* live G2→G3
* Gate A/B/C
* Live authorization
* Live Trading
* schema/migration/index
* materialized Product tables
* caching service
* Redis
* Kafka
* Celery
* Product background scheduler

---

## 53. Acceptance Boundary

I02 may enter Independent Review only after all are true:

### Product Contract

* MarketScannerRead complete
* Opportunity Collection complete
* OpportunityTraceRead complete

### Range

Frozen range semantics complete.

### Provenance

FORWARD_PAPER / HISTORICAL_REPLAY isolation complete.

### Trace

Current canonical Evidence and Decision-bound Evidence remain distinct.

### CR-03

Implemented.

### CR-05

Six-value TraceNodeState consumed correctly.

### Snapshot

Opportunity durable trace uses an explicit stable snapshot.

### Reuse

No second revision-folding authority exists.

### Schema

ZERO CHANGE.

### OpenAPI

I02 slice complete.

### Verification

Focused/relevant/full regression PASS.

---

## 54. Independent Review Focus

Reviewer MUST specifically inspect:

1. current canonical Evidence incorrectly backfilled into historical Decision
2. relation guessed from timestamp/instrument/payload
3. NOT_REACHED / NOT_YET_DUE confusion
4. due-but-no-outcome incorrectly remaining NOT_YET_DUE
5. implicit Forward→Replay fallback
6. cursor effective range drift
7. duplicate revision algorithm
8. durable relation torn across different snapshots
9. arbitrary payload exposure
10. Product API gaining mutation/activation authority

Worker PASS does not constitute Review PASS.

---

## 55. v1.4.0 Execution Characteristics

This requirement does not permanently bind a model SKU.

### I02-A

Characteristics:

* typed HTTP contract
* keyset pagination
* runtime snapshot
* historical DB page
* moderate consistency
* deterministic adverse cases

Risk:

`MEDIUM`

Hidden invariants:

limited/moderate

### I02-B

Characteristics:

* revision chains
* stable transaction snapshot
* current canonical head
* historical exact binding
* causal absence semantics
* temporal maturity semantics
* provenance isolation
* multiple durable authorities

Risk:

`HIGH`

Hidden invariants:

`HIGH`

I02-A and I02-B MUST be separately routed when formal execution tasks are generated.

---

## 56. Escalation Diagnosis

Before increasing Reasoning Level or switching model after a failure, classify evidence into:

1. requirement/Acceptance conflict
2. Repository Truth/baseline problem
3. wrong window/stale context
4. tool/network/auth/environment issue
5. local implementation defect
6. verification/evidence deficiency
7. actual model/reasoning insufficiency

The first six categories are not sufficient proof of Model Capability Failure.

Examples that MUST NOT be “solved” simply by selecting a stronger model:

* PostgreSQL test contention
* network failure
* Codex transport failure
* wrong worktree
* baseline mismatch

---

## 57. Documentation

Implementation batches follow current Protocol documentation discipline.

Maintain:

* dev_log
* PROJECT_STATE
* AI_CONTEXT only when necessary

AI_CONTEXT stays a compact pointer/index.

Do not copy this full requirement into AI_CONTEXT.

---

## 58. Final I02 Completion Definition

Only after Human Acceptance may:

`UI-RD01-I02 = ACCEPTED / COMPLETE`

That means only the Market + Opportunity Product Read slice is accepted.

It does not mean all Product Read implementation is complete.

Remaining:

* I03 TradingAuditRead
* I04 EdgeAggregateRead
* I05 Overall Product Read Acceptance

---

## 59. Post-Freeze Next Step

After this requirement artifact passes Independent Review and Human Freeze:

1. issue `UI-RD01-I02-A｜市场扫描读取`
2. complete I02-A internal checkpoint
3. issue `UI-RD01-I02-B｜机会追踪读取`
4. complete combined I02 implementation
5. Independent Review
6. Human Acceptance
7. Final Acceptance Closeout
8. then begin I03
