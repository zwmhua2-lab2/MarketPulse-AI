# UI-V1-D01-AMEND-01｜Post-Freeze Amendment

## 1. Status and Authority

- Amendment ID: `UI-V1-D01-AMEND-01`.
- Status: **`ACCEPTED / FROZEN`**.
- Human Acceptance: `CONFIRMED` before this repository-persistence task.
- This artifact is the formal post-freeze amendment to the accepted artifacts
  `UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md` and
  `UI-RD01-Product-Read-API-Formal-Design.md`.
- `UI-V1-D01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`.
- `UI-RD01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`.

The original frozen artifacts retain their historical `ACCEPTED / FROZEN` identity. This
artifact is additive and is the authority for the six amendments below. Contract acceptance
does **not** mean implementation remediation is complete.

## 2. CR-01 P1 — Typed Readiness Coherence

Classification: `FOUNDATION FIX CONTRACT`.

`GET /api/v1/ready` has a formal typed HTTP contract. A valid typed readiness body contains at
least `ready: boolean` and a typed `reasons` collection. Existing accepted fields such as
`status`, `run_mode`, `host_state`, `evaluated_at`, and `local_only`, when included in the DTO,
retain their existing backend meaning. If both `ready` and `status` (or other discriminants) are
present, they must be semantically consistent.

The only legal verdict combinations are:

| HTTP status | Valid typed body | Verdict |
| --- | --- | --- |
| `200` | `ready = true` | `READY` |
| `503` | `ready = false` | `NOT_READY` |

The following are protocol violations: `200 + ready=false`, `503 + ready=true`, a missing
`ready` discriminant, a non-boolean `ready`, malformed typed readiness body, or any status/body
semantic contradiction. A protocol violation must not become `READY`, `NOT_READY`, or
`NetworkError`; it must enter existing `UnexpectedResponse` or the same Foundation-owned
protocol-interpretation category.

A future Foundation fix must give both the `200` and `503` responses formal OpenAPI response
schemas and preserve the chain `FastAPI typed response → OpenAPI → generated.ts`. It must not
introduce a handwritten frontend duplicate-authority DTO. `503` remains neither network failure
nor generic backend failure, and readiness remains distinct from Risk Admission: the frontend
must not infer `risk_admission_open` from it.

Disposition: `CR-01 Contract Amendment = ACCEPTED`; Foundation implementation remediation is
`REQUIRED / NOT STARTED` and is not implemented by this task.

## 3. CR-02 P1 — Session Generation / Request Ownership

Classification: `FOUNDATION FIX CONTRACT`.

The frontend Auth Session Boundary must own a `session_generation`: a local-only, ephemeral,
non-persistent, non-auth-authority identity used only for request ownership and stale-response
fencing. It must not be written to `sessionStorage` or `localStorage`, sent to the backend,
decoded from a token, used to replace backend auth authority, or used to introduce refresh-token
behavior.

Every protected request captures immutable `request_session_generation` at actual dispatch. A
protected `401` whose request generation equals `current_session_generation` is an authoritative
current-session `401`: it invalidates the current session, clears the current token and
authenticated Query cache, and enters the Login boundary. A protected `401` whose request
generation differs is a stale-session `401`: its originating request may or shall surface
`UnauthorizedError`, but it must not clear the current new token, clear the new-session
authenticated cache, log out the new session, or redirect that new session to Login.

A new generation identity is required at successful sign-in, sign-out/current-session
invalidation, and a new AuthSessionBoundary lifetime. `POST /api/v1/auth/login` returning `401`
continues to mean invalid credentials; it is not protected-session invalidation.

Disposition: `CR-02 Contract Amendment = ACCEPTED`; Foundation implementation remediation is
`REQUIRED / NOT STARTED` and is not implemented by this task.

## 4. CR-03 P1 — Current Canonical Evidence vs Decision-Bound Evidence

Classification: `UI-RD01 CONTRACT AMENDMENT`.

`OpportunityTraceRead` formally distinguishes `current_canonical_evidence` from
`decision_bound_evidence`.

- Current Canonical Evidence is the current authoritative read snapshot's backend-selected
  canonical Evidence head, used for current Opportunity evidence, the current Forward Outcome
  branch, and current snapshot/research context.
- Decision-Bound Evidence is the exact Evidence identity that a historical Decision or Decision
  Invocation actually bound at creation/admission. When durable facts prove it, the binding must
  use exact `opportunity_id`, `evidence_id`, `evidence_revision`, `evidence_hash`, and
  `feature_snapshot_hash`.

If Decision `D1` bound revision 1 and revision 2 later became the current canonical head,
`current_canonical_evidence` is revision 2 while `D1.decision_bound_evidence` remains revision
1. A historical Decision must never be backfilled with the current canonical head. If legacy
durable facts cannot prove the exact binding, the response must use frozen absence semantics such
as `NO_PROVABLE_RECORD`; it must not guess from time proximity, instrument, payload similarity,
or the current canonical head.

`PRE-01B-I2` remains `NOT STARTED / NOT ACTIVATED`: this contract freezes future exact-binding
semantics and does not describe future AdvisoryIngress live binding as currently live capability.
Disposition: `CR-03 Contract Amendment = ACCEPTED`; current implementation remediation is
`NOT APPLICABLE YET`; future relevant OpportunityTraceRead implementation must comply. This does
not claim that OpportunityTraceRead is already implemented.

## 5. CR-04 P1 — Full Edge Product Query Bounded Resource Boundary

Classification: `UI-RD01 CONTRACT AMENDMENT`.

Future `EdgeAggregateRead` must acquire bounded full Edge query admission before expensive
DB/session/query work starts, and hold it until the aggregate request's authoritative result or
failure is complete. The covered pipeline is:

```text
bounded Edge Query admission
→ borrow Host-owned async DB resource
→ REPEATABLE READ / READ ONLY stable snapshot
→ DB row acquisition → record rehydration → revision-chain validation
→ cross-integrity validation → canonical folding
→ revision-aware manifest construction → immutable CurrentSnapshotProjection materialization
→ end transaction / return DB resource
→ bounded CPU admission → off-main-event-loop pure aggregate_projection()
→ exact AggregationResult → typed Product DTO adapter → release full-query admission
```

DB transaction/connection resources must be released before CPU-heavy aggregation. No
`AsyncSession`, connection, lazy ORM object, or provider may be passed to or accessed in the CPU
thread. CPU aggregation remains off the main async event loop with bounded CPU admission and
bounded worker/task usage.

Normal completion, validation failure, snapshot failure, timeout, request cancellation, CPU
failure, and DTO adapter failure must all release query admission, CPU admission, and DB/session
resources correctly. The implementation must not silently truncate rows or populations, drop
revisions, or return a partial aggregate as complete; if workload exceeds the accepted Product
query budget it must fail closed / `UNAVAILABLE`. This amendment freezes no numeric concurrency,
queue, timeout, memory, or latency values, and authorizes no Celery, Redis, Kafka, separate
worker service, daemon, scheduler, persistence, or materialized aggregate.

Disposition: `CR-04 Contract Amendment = ACCEPTED`; current implementation remediation is
`NOT APPLICABLE YET`; future EdgeAggregateRead implementation must comply. This does not start or
claim an Edge endpoint.

## 6. CR-05 P2 — NOT_REACHED vs NOT_YET_DUE

Classification: `UI-RD01 CONTRACT AMENDMENT`.

`TraceNodeState` is amended to:

```text
PRESENT | NOT_OCCURRED | NOT_REACHED | NOT_YET_DUE |
NO_PROVABLE_RECORD | CAPABILITY_NOT_INTEGRATED
```

`NOT_REACHED` is solely causal/structural: the upstream causal chain really ended before the
node, so that node was never reached. `NOT_YET_DUE` is solely temporal: the node is in legal
causal scope but authoritative backend `as_of` / `due_at` / horizon facts have not matured. For
example, evidence at `T0` with a five-minute Forward horizon is `NOT_YET_DUE` when authoritative
`as_of < T0 + 5m`, not `NOT_REACHED`.

The frontend must not use a browser clock, calculate maturity authority, or convert
`NOT_REACHED` to `NOT_YET_DUE`. Frozen distinctions remain: `NOT_OCCURRED != NOT_REACHED !=
NOT_YET_DUE != NO_PROVABLE_RECORD != UNAVAILABLE != CAPABILITY_NOT_INTEGRATED`. SE-02D semantics
remain: `NOT_YET_DUE != missing` and it does not enter the mature denominator. UI Chinese terms
are `未到达` for causal `NOT_REACHED` and `尚未到期` for temporal `NOT_YET_DUE`.

Disposition: `CR-05 Contract Amendment = ACCEPTED`; current shared Product Read contract
implementation remediation is `REQUIRED / NOT STARTED`. `UI-RD01-I01 = ACCEPTED / COMPLETE`
remains historically accepted: its shared Product Read contract already created
`backend/src/marketpulse/api/product/models.py::TraceNodeState`, but that accepted current enum
lacks `NOT_YET_DUE`. The later post-freeze CR-05 contract therefore requires remediation without
revoking, downgrading, or rewriting I01 historical acceptance. Future OpportunityTraceRead and
trace consumers must also comply.

## 7. CR-06 P2 — EdgeAggregateRead Audit Identity

Classification: `UI-RD01 CONTRACT AMENDMENT`.

Every actually returned selected Edge aggregate result must carry `AggregateAuditIdentity` with
at least `as_of`, `input_fingerprint`, `aggregation_contract_version`,
`selected_population_key`, and `horizon`. It is mapped from one exact `AggregationResult`:

```text
audit.as_of = AggregationResult.as_of
audit.input_fingerprint = AggregationResult.input_fingerprint
audit.aggregation_contract_version = AggregationResult.aggregation_contract_version
audit.selected_population_key ↔ AggregationResult.identity.population_key
audit.horizon = AggregationResult.identity.horizon
```

Expectancy, uncertainty, coverage, evidence sufficiency, sufficiency reasons, tail evidence,
calculability, aggregate status, and audit identity must all come from that same exact immutable
result instance/value. It is forbidden to combine result-A metrics with a result-B fingerprint,
new/current `as_of` with stale metrics, or a request's selected population key with another actual
result. A request echo alone is not aggregate identity authority.

The Product DTO adapter may only project, serialize, and adapt field names/enums. It must not
recompute `input_fingerprint`, mint `as_of`, select another population or horizon, or rerun
aggregate mathematics. When no actual selected aggregate result exists, it must not fabricate an
AggregateAuditIdentity. Available populations and selection requirements may still use frozen
contract semantics. Product UI/Product DTO need not expose the full `input_manifest`; the
existing SE-02D manifest/fingerprint authority remains unchanged and `input_fingerprint` is the
V1 minimum audit reference.

Disposition: `CR-06 Contract Amendment = ACCEPTED`; current implementation remediation is
`NOT APPLICABLE YET`; future EdgeAggregateRead implementation must comply. This does not start or
claim an Edge endpoint.

## 8. Preserved Boundaries and Implementation Status

This amendment closes only `CR-01` through `CR-06`. It neither adds `CR-07+` nor reopens
UI-RD01 R1–R8. The five-page IA, no independent AI page, Read-Only Product Boundary, desktop
direction, SE-02D formulas, Population Key, folding, fingerprint algorithm, and all frozen
Product Read boundaries remain unchanged.

`UI-RD01-I01 = ACCEPTED / COMPLETE` is preserved. It is historically accepted while its existing
shared `TraceNodeState` surface has a new post-freeze CR-05 remediation requirement. `UI-RD01-I02`
through `UI-RD01-I05` remain `NOT STARTED / NOT AUTHORIZED`. `PRE-01B-I2`, Real AI, live G2→G3,
Gate A/B/C, and Live receive no activation or implementation progress from this artifact. This
task makes no production-code, test, schema, migration, index, runtime/configuration, or
dependency change.
