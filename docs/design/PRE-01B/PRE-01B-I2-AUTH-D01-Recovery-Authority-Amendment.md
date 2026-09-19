# PRE-01B-I2-AUTH-D01｜Recovery Authority Amendment

```text
Task: PRE-01B-I2-AUTH-D01-AMEND-01-R2-PERSIST
Status: CANDIDATE / PENDING INDEPENDENT RE-REVIEW
Task type: DOCS / DESIGN CANDIDATE FIX + STATE SYNC ONLY
Human R1 Decision: CONFIRMED — 2026-09-19
R1 Independent Re-Review: FAIL — R2 REQUIRED
Independent Review Findings: R1IR-P1-01 / R1IR-P1-02; IR-P3-01 / IR-P3-02 remain closed by R1
R2 Candidate State: IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW
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
| DF-02 | APPROVED WITH TRANSACTION-ADMISSION AUTHORITY | Canonical row locks → exact Host capability / applicable non-mutating predicates → statistics snapshot reset → FINAL FRESH PostgreSQL singleton ownership proof → transaction admission |
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

The existing `RuntimeHost` PostgreSQL session advisory singleton lock remains the only
cross-process Host singleton fence. No new database row, column, migration, second
singleton lock, durable owner identity, ownership service, engine, or session factory is
introduced.

When RuntimeHost successfully acquires that existing singleton advisory lock, the Host
authority issuer conceptually records:

- the exact existing singleton advisory-lock identity, preserving the existing namespace
  and run-mode-derived key semantics;
- the PostgreSQL singleton backend PID;
- that backend's `pg_stat_activity.backend_start`;
- Host lifetime/generation correlation.

The authoritative PostgreSQL backend identity is **PID + `backend_start`**. PID alone is
insufficient because a later PostgreSQL backend may reuse a PID. Host generation remains
process-local correlation and is not a substitute for PostgreSQL ownership proof.
If an old owner has PID `P` and `backend_start = S1`, then exits and a new backend reuses
PID `P` with `backend_start = S2`, `S2 != S1` MUST make the FINAL FRESH proof fail; a
cached historical `S1` cannot satisfy final ownership proof.

### Canonical PostgreSQL ownership proof

Every lifecycle transaction requiring `LiveAttemptCapability` or
`RestartRecoveryCapability` MUST use this transaction-admission sequence:

```text
canonical durable row locks
  Evidence → Invocation → Attempt
→ exact Host capability / local binding validation
→ applicable existing non-mutating lifecycle predicates
→ `SELECT pg_stat_clear_snapshot();` on the transaction's existing primary connection
→ FINAL FRESH PostgreSQL singleton ownership proof
→ TRANSACTION ADMITTED
→ first lifecycle mutation
```

Immediately before the FINAL FRESH ownership proof, the lifecycle transaction MUST
successfully execute `SELECT pg_stat_clear_snapshot();` on its existing primary
PostgreSQL connection. The FINAL FRESH proof MUST then be represented as one final
ownership-proof SQL statement using fresh PostgreSQL catalog observation from `pg_locks`
+ `pg_stat_activity`; no previously retrieved or cached `pg_stat_activity`,
`backend_start`, PID/backend identity, heartbeat, or liveness-probe result may satisfy it.

That one final ownership-proof statement MUST establish together:

- the advisory lock exists and is granted;
- the advisory lock identity exactly matches the existing RuntimeHost singleton lock;
- the lock owner PID equals the recorded singleton backend PID;
- fresh `pg_stat_activity.backend_start` for that PID equals the recorded
  `backend_start`; and
- the ownership result is unique and unambiguous.

The implementation may encode the existing two-key advisory lock identity using
PostgreSQL's documented `pg_locks` representation, but MUST NOT create a second lock
identity.

Successful completion of the FINAL FRESH PostgreSQL singleton ownership-proof statement
= `TRANSACTION ADMITTED` = the ownership linearization point. It is the last
authority-bearing gate before lifecycle mutation: there MUST NOT be another authority
validation between successful final fresh proof and admission. Before `TRANSACTION
ADMITTED`, no lifecycle write is authorized. After admission, that exact transaction has
authority for that one lifecycle transition.

Failure of `pg_stat_clear_snapshot()`, the `pg_locks` or `pg_stat_activity` query,
catalog visibility, lock identity/granted-state/PID/`backend_start` matching, or the
unique/unambiguous result MUST produce `NO TRANSACTION ADMISSION`, `NO LIFECYCLE
MUTATION`, and rollback / fail closed.

### Loss before admission

If exact Host capability validation passes but singleton ownership is lost before
successful completion of the FINAL FRESH proof, that final proof MUST fail. The
transaction is not admitted, writes no lifecycle mutation, and rolls back / fails closed.

Rejection is also required for: matching lock absent, lock not granted, wrong lock
identity, PID mismatch, `backend_start` mismatch, PID reuse by a different backend,
catalog-query failure, insufficient catalog visibility, or ambiguous catalog result.
No fallback is permitted.

`_lock_held`, `_lock_lost`, heartbeat, periodic liveness probe, Python object identity,
Host generation boolean, and test-fixture boolean may exist only as local correlation /
telemetry facts. None is singleton ownership authority.

### Loss after admission

The successful FINAL FRESH proof is itself admission. Singleton loss after that point is
loss after admission and does not retrospectively revoke the already-admitted
transaction; it may complete that one lifecycle transition according to PostgreSQL
transaction outcome.

### New-owner race

If a new RuntimeHost acquires singleton ownership while an old already-admitted
lifecycle transaction still owns the same canonical durable rows, new-owner recovery
serializes behind those PostgreSQL row locks.

If the old transaction commits, the new owner re-reads committed state, observes the
authoritative FINAL/lifecycle result, and MUST NOT create a second winner. If the old
transaction rolls back, the new owner may acquire the rows and evaluate normal
`PROCESS_LOST` recovery. Exactly-one winner remains PostgreSQL row serialization plus
the Invocation final winner fence.

### Local capability role and failure semantics

`LiveAttemptCapability` and `RestartRecoveryCapability` remain mandatory. They prove the
correct Host lifetime/generation, phase, Invocation, Attempt where applicable, and
live/recovery authority role, but are not independently sufficient to prove current
singleton ownership.

Required authority is:

```text
exact Host-issued capability validation and applicable predicates before the final proof
AND
FINAL FRESH PostgreSQL singleton ownership proof as the admission event
```

Any inability to prove exact current ownership is FAIL CLOSED. Ownership-proof failure
alone MUST NOT become `SHUTDOWN_BEFORE_PROVIDER`, `ACTIVATION_DISABLED`,
`OPPORTUNITY_STALE`, `BINDING_INVALID`, `PROCESS_LOST`, `ABANDONED`, or another semantic
terminal. Where no exact semantic terminal predicate is independently established,
preserve existing durable state, roll back, and allow a later authoritative owner/restart
to re-evaluate.

Once singleton ownership is lost, the old RuntimeHost stops issuing new live-owner
capabilities and cancellation receipts and refuses lifecycle transactions not already
admitted by the canonical PostgreSQL proof + capability validation. Already-admitted
transactions may commit or roll back according to PostgreSQL outcome.

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
→ `pg_stat_clear_snapshot()`
→ FINAL FRESH PostgreSQL singleton ownership proof
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
→ `pg_stat_clear_snapshot()`
→ FINAL FRESH PostgreSQL singleton ownership proof
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
the statistics snapshot and completes the FINAL FRESH DF-02 PostgreSQL singleton
ownership proof. That successful proof admits the transaction; only then may recovery
atomically apply the already-authorized existing `PROCESS_LOST` / external-precedence /
retry-policy result as exactly one external FINAL, `RETRY_PENDING`, or
`INVALID_SCHEMA / RETRY_EXHAUSTED`. Ownership loss before admission rejects with no
`PROCESS_LOST` mutation. No provider response, usage, cost, or `AIDecision` may be
reconstructed from process memory.

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

This R2 candidate repairs R1 Independent Re-Review findings `R1IR-P1-01`
(PostgreSQL ownership observation freshness incomplete) and `R1IR-P1-02`
(transaction-admission TOCTOU / linearization gap). Each is
`IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`; neither is independently closed before
that review. `IR-P3-01` and `IR-P3-02` remain closed by R1. This candidate has not
received Independent Re-Review or Formal Human Acceptance and is not implementation
authorization.
It does not resume FIX-02, create authority classes, change recovery behavior, call a
provider, create configuration defaults, run economic actions, or activate any Gate.
