# PRE-01B-I2-AUTH-D01｜Recovery Authority Amendment

```text
Task: PRE-01B-I2-AUTH-D01-AMEND-01-R3-PERSIST
Status: CANDIDATE / PENDING INDEPENDENT RE-REVIEW
Task type: DOCS / DESIGN CANDIDATE FIX + STATE SYNC ONLY
Human R1 Decision: CONFIRMED — 2026-09-19
Human R3 Design Confirmation: CONFIRMED — 2026-09-20
R2 Independent Re-Review: FAIL — R3 REQUIRED
Independent Review Findings: R2IR-P1-01; R1IR-P1-01 / R1IR-P1-02 and IR-P3-01 / IR-P3-02 remain closed
R3 Candidate State: IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW
Formal Human Acceptance: NOT PERFORMED
Implementation Authorization: NOT GRANTED
```

## 1. Purpose and authority boundary

This is a narrowly scoped amendment to the human-accepted
`PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md` (D2).  It records the
human-confirmed recovery-authority rulings discovered as an executable authority gap
during PRE-01B-I2 `FINAL-02`.  It does not rewrite, replace, or otherwise alter the
accepted D2 artifact.

This amendment does not activate Gate A, authorize implementation by itself, change
schema, or resume PRE-01B-I2 FIX-02.  It does not supersede unrelated D2 semantics.
In particular, the following remain unchanged: the nine no-terminal-producing-Attempt
pairs, canonical lock order, winner precedence, and `PROCESS_LOST` / `ABANDONED`
business semantics.

## 2. Confirmed decisions

| Decision | Human ruling | Amendment meaning |
|---|---|---|
| DF-01 | APPROVED | Narrow DISABLED provider-free startup recovery exception |
| DF-02 | APPROVED WITH TRANSACTION-ADMISSION AUTHORITY | Canonical row locks → exact Host capability / applicable non-mutating predicates → FINAL OWNER-SESSION PROOF on the existing dedicated singleton-owner session → transaction admission |
| D1–D7 | CONFIRMED | Subject to the exact DF-01 / DF-02 rulings in this amendment |

## 3. DF-01 — DISABLED provider-free recovery exception

When `advisory_activation_level = DISABLED`, the existing `RuntimeHost` MAY construct
and execute one narrowly scoped, provider-free, startup-only `AdvisoryRecoveryCore` for
the sole purpose of classifying or recovering already-durable Advisory state.  This is
the explicit narrow exception to D2 wording which otherwise prohibits additional
Advisory SQL in DISABLED mode and requires ordinary Advisory SQL to pass through the
active Advisory Fence.

The exception is limited to bounded, serial startup recovery.  Its owner is the
existing `RuntimeHost`; its DB authority is the existing Host-owned primary DB/session
authority.  It may read Evidence, Decision Snapshot, Invocation, Attempt, and durable
G2 state required by the accepted stale matrix.  It may write only state, lifecycle, and
final transitions already authorized by accepted D2 recovery semantics.

It MUST NOT construct `AdvisoryIngress`, an active queue, worker, Real AI provider or
client, active `AdvisoryAdmissionWriter`, `G3Workflow`, `TradePlan`, Risk authority,
Execution authority, or economic-action capability.  Pack B is not required merely to
perform this DISABLED provider-free startup recovery.  Gate A remains `DISABLED / NOT
ACTIVATED`; DISABLED startup recovery does not construct active dispatch.

## 4. DF-02 — transaction-admission ownership authority

The existing `RuntimeHost` dedicated PostgreSQL connection that owns the existing
PostgreSQL SESSION advisory singleton lock remains the unique cross-process Host
ownership authority. No second advisory lock or lock identity, owner connection, durable
fencing row/table/column, ownership service, RuntimeHost, engine, session factory, or
distributed lease system is introduced.

When that exact dedicated owner connection acquires the existing singleton lock, the Host
authority issuer records from that same connection the exact existing advisory-lock
identity, PostgreSQL backend PID, `pg_stat_activity.backend_start`, and Host
lifetime/generation correlation. Authoritative PostgreSQL backend identity remains
**PID + `backend_start`**; PID alone is insufficient and Host generation is process-local
correlation only.

### Owner-session synchronization gate

One minimal process-local `SingletonOwnerSessionGate` serializes use of that existing
dedicated owner connection for FINAL owner-session admission proof, singleton liveness
probe, explicit `pg_advisory_unlock()`, and singleton connection close/disposal. The gate
is coordination only: it is not singleton ownership authority, a fencing token, durable
state, distributed lock, or winner authority.

### Canonical lifecycle admission order

Every lifecycle transaction requiring `LiveAttemptCapability` or
`RestartRecoveryCapability` MUST retain canonical durable row locks throughout this
sequence:

```text
PRIMARY LIFECYCLE TRANSACTION
canonical durable row locks: Evidence → Invocation → Attempt
→ exact Host capability / local-binding validation
→ applicable existing non-mutating lifecycle predicates

OWNER SINGLETON SESSION
→ enter SingletonOwnerSessionGate
→ verify Host has not already closed new admission due to shutdown / fatal ownership loss
→ SELECT pg_stat_clear_snapshot()
→ FINAL OWNER-SESSION PROOF on the exact dedicated owner session
→ successful FINAL proof = TRANSACTION ADMITTED = ownership linearization point
→ leave SingletonOwnerSessionGate

PRIMARY LIFECYCLE TRANSACTION
→ first lifecycle mutation
```

No lifecycle mutation is authorized before successful FINAL proof. There MUST NOT be
another authority-bearing validation between that proof and the first lifecycle mutation.

### FINAL OWNER-SESSION PROOF

The sole final ownership authority executes on the exact existing dedicated PostgreSQL
connection that owns the singleton session advisory lock, never on the ordinary lifecycle
primary connection. Immediately before the proof, that same owner session MUST execute
`SELECT pg_stat_clear_snapshot();`. Then one FINAL owner-session proof statement MUST
establish together:

- `pg_backend_pid()` equals the recorded singleton backend PID;
- fresh `pg_stat_activity.backend_start` equals the recorded `backend_start`;
- `pg_locks` shows the exact existing RuntimeHost session advisory singleton lock;
- `locktype = advisory`, `pid = pg_backend_pid()`, `granted = true`, and
  `mode = ExclusiveLock`;
- exact existing two-integer lock identity, `objsubid = 2`, and database identity match;
  and
- the result is unique and unambiguous.

Previously cached observations cannot grant authority. `_lock_held`, `_lock_lost`,
heartbeat timestamp, prior `SELECT 1`, Python object identity, Host generation boolean,
test-fixture boolean, and a primary-connection `pg_locks` observation may only be local
correlation, telemetry, or preflight evidence. There is exactly one final ownership
authority: `FINAL OWNER-SESSION PROOF`.

### Loss, response uncertainty, and shutdown serialization

If the owner session disconnects, dies, is terminated, invalidated, replaced/reconnected,
cannot reset the statistics snapshot or execute final proof, reports PID or
`backend_start` mismatch, no longer holds the exact advisory lock, or returns ambiguous
evidence before successful final proof, the result is `NOT ADMITTED`, `NO LIFECYCLE
MUTATION`, rollback / fail closed. A replacement backend never inherits old authority.

If PostgreSQL may have executed final proof but caller response is uncertain because of a
connection, driver, or transport failure, authority is `NOT PROVEN ADMITTED`: no
lifecycle mutation, rollback / fail closed, and no reconstruction from elapsed time,
local flags, heartbeat, prior catalog observation, or Host state.

Shutdown closes new admission before releasing singleton ownership and uses the same
owner-session gate. A proof that wins the gate first admits its transaction; later unlock
or close is loss after admission and does not retrospectively revoke it. If admission is
closed first, or shutdown unlocks/closes first, a later lifecycle path has no successful
final proof and must be not admitted, make no mutation, and fail closed. Liveness may
continue only through the same gate as telemetry / early failure detection, never as
lifecycle admission authority.

### New-owner race and preserved local capability role

An old transaction already admitted by FINAL OWNER-SESSION PROOF retains the canonical
durable rows. A new RuntimeHost therefore serializes behind `Evidence → Invocation →
Attempt`; after old commit it re-reads the FINAL/lifecycle result and creates no second
winner, and after old rollback it evaluates normal `PROCESS_LOST` recovery. Exactly-one
winner remains PostgreSQL durable row serialization plus the Invocation final winner
fence; FINAL OWNER-SESSION PROOF is not a second winner authority.

`LiveAttemptCapability` and `RestartRecoveryCapability` remain mandatory and exact for
their Host lifetime/generation, phase, Invocation, and Attempt where applicable, but are
not singleton ownership proof. Any ownership-proof failure is fail closed and alone MUST
NOT become `PROCESS_LOST`, `ABANDONED`, or another semantic terminal.

### R2 observer-side proof superseded

R2's primary-lifecycle-connection FINAL ownership proof is superseded and MUST NOT
remain a competing final mechanism. `pg_locks + pg_stat_activity` remain part of the
proof only when run from the actual owner session; primary-connection ownership queries
are diagnostic only.

## 5. D1 — CurrentAdvisoryAuthority

One `RuntimeHost`-owned immutable `CurrentAdvisoryAuthority` is frozen.  Its sole source
is existing canonical Settings / activation configuration; no second configuration source
is permitted.  It represents current Host-frozen facts for activation level,
activation/config epoch, experiment definition identity/digest, config version,
configured provider/model binding, prompt/schema/treatment/baseline policy versions, and
already-accepted retry/deadline/resource-policy facts available for the current mode.

In DISABLED mode, activation level is authoritatively DISABLED; missing Pack B values are
not fabricated, and missing active configuration is not inferred from historical
Invocation rows.  Activation disabled and config mismatch remain distinct predicates.  A
future separately authorized `GATE_A_SHADOW` mode uses the same authority carrier; this
amendment does not activate it.

## 6. D2 — AdvisoryPredicateEvaluator

One small provider-free `AdvisoryPredicateEvaluator` is frozen.  It is not a generic
policy engine.  It deterministically evaluates the existing D2 external predicate facts
needed by Attempt Start, Finalizer, and Recovery: deadline, Evidence supersession,
Opportunity eligibility, market freshness, binding integrity, activation disabled,
experiment/config mismatch, and applicable shutdown authority.

It preserves D2 source authorities at minimum as follows:

- deadline: PostgreSQL DB clock plus `Invocation.decision_deadline_at`;
- Evidence supersession: durable higher Evidence revision for the same Opportunity;
- Opportunity eligibility: Evidence expiry plus durable current G2 state/state version;
- market freshness: frozen `Evidence.reference_data_status` plus Decision Snapshot-bound
  market facts;
- binding: Decision Snapshot/payload hash, `input_binding_digest`, Evidence and feature
  hashes, and existing immutable bound identity;
- activation/config: `CurrentAdvisoryAuthority` versus Invocation/Snapshot/seed binding;
- shutdown: RuntimeHost lifecycle plus a valid Host authority capability.

The evaluator returns independently provable predicate facts.  It MUST NOT preselect the
final terminal result for Recovery; the lifecycle component retains D2 precedence
authority.

## 7. D3 — LiveAttemptCapability

One Host-issued process-local `LiveAttemptCapability` is frozen. It is tied to the exact
RuntimeHost lifetime/generation, Invocation, Attempt, and live provider-task/cancellation
ownership. Only the current RuntimeHost authority issuer may create it; Recovery MUST
NOT obtain one.

The capability is mandatory local authority but is not independently sufficient to prove
current singleton ownership.

`ABANDONED` admission requires:

```text
canonical Evidence → Invocation → Attempt row locks
→ valid exact LiveAttemptCapability
→ existing shutdown/cancellation requirements
→ enter SingletonOwnerSessionGate
→ FINAL OWNER-SESSION PROOF
→ TRANSACTION ADMITTED
→ lifecycle mutation
```

Only after the PostgreSQL proof and exact capability validation pass may one transaction
atomically commit exact Attempt `ABANDONED`, Invocation `FINAL`,
`INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT`, the exact `final_attempt_id`, and
`final_decision_id = NULL`. Stale generation, wrong Attempt, revoked authority, or
ownership-proof failure fails closed with no lifecycle mutation. Ownership-proof failure
is not itself an `ABANDONED` predicate.

## 8. D4 — RestartRecoveryCapability

One startup-only `RestartRecoveryCapability`, issued by the same RuntimeHost ownership
root as live authority, is frozen. It is issued only after primary DB availability,
successful acquisition of the existing RuntimeHost singleton lock, recording of the
exact lock identity plus singleton backend PID + `backend_start`, and entry into
startup/recovery phase before normal Advisory dispatch runs.

It permits `PROCESS_LOST` classification and provider-free Advisory restart recovery
only; it does not permit `ABANDONED`. It is mandatory local recovery authority but is
not independently sufficient to prove current singleton ownership.

`PROCESS_LOST` recovery admission requires:

```text
canonical Evidence → Invocation → Attempt row locks
→ valid exact RestartRecoveryCapability
→ existing winner / external-precedence evaluation
→ other applicable existing non-mutating recovery predicates
→ enter SingletonOwnerSessionGate
→ FINAL OWNER-SESSION PROOF
→ TRANSACTION ADMITTED
→ lifecycle mutation
```

Recovery cannot obtain `LiveAttemptCapability`. The RestartRecoveryCapability is revoked
when Advisory startup recovery completes, singleton authority is lost, the Host
fails/stops, or normal lifecycle exits recovery. No second durable ownership mechanism
is created.

## 9. D5 — provider-free recovery composition

Provider-free startup Advisory recovery is explicitly allowed.  With current activation
DISABLED, construct `CurrentAdvisoryAuthority`, `RestartRecoveryCapability`,
`AdvisoryPredicateEvaluator`, `AdvisoryRetryPolicy` access, and provider-free
`AdvisoryRecoveryCore`.  Do not construct a Real AI provider, active queue, Advisory
worker, active admission writer, or active G2→G3 provider dispatch.  DISABLED startup may
classify/terminalize durable Advisory rows but may not re-offer active work to a provider
queue.

## 10. D6 — typed RecoveryInput contract

The insufficient `retry_allowed: bool` is replaced conceptually by a typed
`RecoveryInput` boundary.  Responsibilities remain separate:
`CurrentAdvisoryAuthority`, `RestartRecoveryCapability`, `AdvisoryPredicateEvaluator`,
`AdvisoryRetryPolicy`, and optional `AdvisoryReofferCapability`.

Recovery owns precedence: existing winner → external terminal authority → retry-policy
assessment → post-commit re-offer eligibility.  A caller MUST NOT pass a final terminal
reason, one opaque stale boolean, one opaque authority boolean, or a test-fixture result
pretending to be production authority.

## 11. D7 — startup ordering

The frozen ordering is:

1. validate Host operational configuration;
2. freeze `CurrentAdvisoryAuthority`;
3. construct existing primary DB resources;
4. acquire existing RuntimeHost singleton;
5. establish Host authority issuer / `RestartRecoveryCapability`;
6. construct core services and provider-free `AdvisoryRecoveryCore`;
7. perform existing D1-required market recovery ingress / warm-up where applicable;
8. execute existing core `RecoveryManager`;
9. execute provider-free Advisory durable recovery / classification;
10. only in separately authorized active mode, construct active Advisory queue / worker /
    provider dispatch;
11. revoke startup `RestartRecoveryCapability` after recovery;
12. start normal runtime workers;
13. open normal ingress/readiness according to existing D1/D2 conditions.

In DISABLED mode, step 9 uses the narrow DF-01 exception and step 10 does not run.

## 12. Recovery state and lifecycle integration

For `ADMITTED`, recovery keeps the same Invocation, Snapshot, original deadline, and
binding; it creates no Attempt during recovery and evaluates external predicates first.
DISABLED mode does not re-offer active dispatch.  If no exact terminal predicate is
established, durable state is preserved and recovery fails closed.

For `RETRY_PENDING`, recovery preserves the same Invocation and historical Attempts,
creates no replacement Attempt during recovery, applies external-predicate precedence then
retry policy, and re-offers only with active queue capability.  Queue-full retry-gap
mapping remains `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` with
`final_attempt_id = NULL` and `final_decision_id = NULL`.

For `ACTIVE + STARTED`, recovery locks `Evidence → Invocation → Attempt`, validates the
exact `RestartRecoveryCapability`, rechecks existing final/winner, evaluates existing
external precedence and other applicable non-mutating recovery predicates, then resets
the statistics snapshot and completes FINAL OWNER-SESSION PROOF through
`SingletonOwnerSessionGate`. That successful proof admits the transaction; only then may
recovery atomically apply the already-authorized existing `PROCESS_LOST` /
external-precedence / retry-policy result as exactly one external FINAL, `RETRY_PENDING`,
or `INVALID_SCHEMA / RETRY_EXHAUSTED`. Ownership loss or uncertain proof response before
admission rejects with no `PROCESS_LOST` mutation. No provider response, usage, cost, or
`AIDecision` may be reconstructed from process memory.

Attempt Start, Finalizer, and Recovery reuse the same minimal predicate evaluator where
their underlying authority is identical.  Attempt Start retains legal source-state and
exact STARTED-Attempt creation; Finalizer retains duplicate → deadline → stale/binding/
config → provider/schema → business → retry/final precedence; Recovery retains existing
winner → external terminal authority → retry policy → later re-offer precedence.

## 13. Failure and unchanged-boundary record

Failure remains fail closed: unavailable current config is not automatically
`ACTIVATION_DISABLED`; G2 query failure is not automatically `OPPORTUNITY_STALE`;
unverifiable binding preserves durable state; DB clock/query/lock failure rolls back;
invalid/revoked capability rejects without guessing a shutdown terminal; terminal commit
failure is not reported as success.  Pack B may be absent while DISABLED for recovery;
absent queue capability prevents re-offer and is not queue rejection.

The following are explicitly unchanged:

```text
canonical lock order: Evidence → Invocation → Attempt
nine no-terminal-producing-Attempt pairs: UNCHANGED
PROCESS_LOST semantics: UNCHANGED
ABANDONED semantics: UNCHANGED
winner final authority: Invocation row + PostgreSQL transaction / constraints
winner precedence and retry semantics: UNCHANGED
schema / migration: ZERO CHANGE
new table / column / migration: ZERO
second singleton lock / second durable owner identity / second ownership service: ZERO
second config authority / second RuntimeHost / second engine-session factory: ZERO
Real AI: NOT ACTIVATED
Gate A: NOT ACTIVATED
Gate B: NOT ACTIVATED
Gate C: NOT PASSED
live G2→G3: NOT ACTIVE
Live: NOT AUTHORIZED
```

## 14. Non-authorization

This R3 candidate repairs R2 Independent Re-Review finding `R2IR-P1-01`
(observer-side `pg_locks` proof cannot itself provide admission linearization). It is
`IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`, not independently closed. `R1IR-P1-01`,
`R1IR-P1-02`, `IR-P3-01`, and `IR-P3-02` remain closed. This candidate has not received
Independent Re-Review or Formal Human Acceptance and is not implementation authorization.
It does not resume FIX-02, create authority classes, change recovery behavior, call a
provider, create configuration defaults, run economic actions, or activate any Gate.
