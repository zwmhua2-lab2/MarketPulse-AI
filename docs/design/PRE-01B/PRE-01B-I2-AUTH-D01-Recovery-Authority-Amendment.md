# PRE-01B-I2-AUTH-D01｜Recovery Authority Amendment

```text
Task: PRE-01B-I2-AUTH-D01-AMEND-01-PERSIST
Status: CANDIDATE / PENDING INDEPENDENT REVIEW
Task type: DOCS / DESIGN PERSISTENCE + STATE SYNC ONLY
Human Content Confirmation: CONFIRMED — 2026-09-19
Independent Review: NOT PERFORMED
Formal Human Acceptance: NOT PERFORMED
Implementation Authorization: NOT GRANTED BY THIS TASK
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
| DF-02 | APPROVED WITH TRANSACTION-ADMISSION AUTHORITY | Final host capability validation admits a lifecycle transaction after canonical row locks |
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

The system does not require loss of the singleton session lock to retroactively revoke
commit ability of every transaction already admitted on another primary DB connection.
No durable owner/fencing schema is introduced.

The canonical ownership linearization point is:

```text
acquire applicable canonical PostgreSQL row locks
  Evidence → Invocation → Attempt
→ final validation of the Host-issued authority capability
→ first lifecycle mutation
```

If final capability validation fails, no lifecycle mutation may be written and the
transaction fails closed / rolls back.  If it succeeds, the winner-fenced transaction is
admitted for that exact lifecycle transition.  Subsequent singleton loss does not
retroactively revoke that already-admitted transaction.

Exactly-one-winner correctness remains owned by PostgreSQL row serialization plus the
Invocation final winner fence, not by Python object identity, a one-time liveness probe,
or a process-local lock alone.  If an admitted old-owner transaction commits before a
new-owner recovery transaction obtains the same rows, the new owner observes the durable
FINAL state and creates no second winner.  If it rolls back, the new owner may obtain the
rows and apply the normal `PROCESS_LOST` recovery tree.

### Singleton-loss consequence

Once singleton ownership is lost, the old `RuntimeHost` must immediately fail closed,
stop issuing new live-owner capabilities and cancellation receipts, refuse lifecycle
transactions not yet admitted by final capability validation, and enter the existing D1
fatal/failure lifecycle.  Already-admitted transactions may commit or roll back according
to PostgreSQL outcome.  No new work may be admitted after authority loss.

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

One Host-issued process-local `LiveAttemptCapability` is frozen.  It is tied to the exact
RuntimeHost lifetime/generation, Invocation, Attempt, and live provider-task/cancellation
ownership.  Only the current RuntimeHost authority issuer may create it; Recovery MUST
NOT obtain one.

`ABANDONED` requires a valid current capability, Host shutdown in progress, a positive
cancellation-completion receipt, the exact Attempt still current `STARTED`, Invocation
still `ACTIVE`, and final capability validation after canonical locks and before mutation.
Only then may one transaction atomically commit exact Attempt `ABANDONED`, Invocation
`FINAL`, `INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT`, the exact
`final_attempt_id`, and `final_decision_id = NULL`.  Stale generation, wrong Attempt, or
revoked authority fails closed.

## 8. D4 — RestartRecoveryCapability

One startup-only `RestartRecoveryCapability`, issued by the same RuntimeHost ownership
root as live authority, is frozen.  It is issued only after primary DB availability,
existing RuntimeHost singleton acquisition, entry into startup/recovery phase, and before
normal Advisory dispatch runs.  It permits `PROCESS_LOST` classification and provider-free
Advisory restart recovery only; it does not permit `ABANDONED`.

It is revoked when Advisory startup recovery completes, singleton authority is lost, the
Host fails/stops, or normal lifecycle exits recovery.  No second durable ownership
mechanism is created.

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

For `ACTIVE + STARTED`, recovery validates `RestartRecoveryCapability`, locks
`Evidence → Invocation → Attempt`, rechecks existing final/winner, classifies the exact
current STARTED Attempt `PROCESS_LOST`, evaluates external authority before retry policy,
and atomically produces exactly one external FINAL, `RETRY_PENDING`, or
`INVALID_SCHEMA / RETRY_EXHAUSTED`.  No provider response, usage, cost, or `AIDecision`
may be reconstructed from process memory.

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
new durable owner identity / second config authority / second RuntimeHost /
second engine-session factory: ZERO
Real AI: NOT ACTIVATED
Gate A: NOT ACTIVATED
Gate B: NOT ACTIVATED
Gate C: NOT PASSED
live G2→G3: NOT ACTIVE
Live: NOT AUTHORIZED
```

## 14. Non-authorization

This candidate has not received Independent Review or Formal Human Acceptance.  It does
not make PRE-01B-I2 ready for independent review, complete, or implementation-authorized.
It does not resume FIX-02, create authority classes, change recovery behavior, call a
provider, create configuration defaults, run economic actions, or activate any Gate.
