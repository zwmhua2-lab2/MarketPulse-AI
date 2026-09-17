# PRE-01B-D2-CLAR-01-FIX-03｜Process-Lost No-Retry Terminal Closure

## Task

Fix exactly `PRE01B-D2-CLAR01-FIX02-RR-P1-01`: freeze the complete durable outcome when a
current Attempt was durably `STARTED`, process/provider completion authority is lost, recovery
classifies it as `PROCESS_LOST` / `ABANDONED`, and no replacement Attempt is authorized.

Task type: `CLARIFICATION FIX / DOCS ONLY`.

## Scope

- Freeze process-loss recovery authority and durable-only provider-result semantics.
- Separate retry allowed, retry unavailable solely by retry policy, and higher-precedence external
  terminal predicates.
- Freeze exact Invocation terminal status/reason and `final_attempt_id` / `final_decision_id`.
- Harmonize completed-Attempt and process-lost-Attempt retry exhaustion.
- Synchronize D2 §14, §15, §18, §20 and §27 plus directly dependent wording.
- Preserve FIX-02 retry-gap provenance and its nine exact NULL-final-Attempt pairs.

## Out of Scope

- No implementation, migration, schema, test, Runtime, config, service, database or provider change.
- No PRE-01B-I2 resume and no migration `20260917_0010_advisory_ingress_core.py` edit.
- No new table, column, trigger, CHECK subquery, Attempt state, DecisionStatus or reason literal.
- No retry-budget values, Pack-B numbers, SAVEPOINT, DB-fence, Protection reserve, provider-adapter,
  arm identity, experiment, RuntimeHost or Gate A/B/C redesign.
- No Real AI/provider call, Production/Live activation, main merge, Independent Re-Review or Human
  Acceptance.
- No `PROJECT_STATE.md`, `AI_CONTEXT.md`, `DECISIONS.md`, `PRODUCT_REQUIREMENTS.md`, PRE-01A-D1,
  PRE-01B-D1, prior clarification/fix dev log, foundation, `.workbuddy`, memory, skills or daily-log
  change.

## Repository Truth

- Protocol: `v1.1.0 / ACCEPTED`.
- Protocol remote `main`: `a80c55b7451f77883d8b0713a228f0d9bebf7d22` (live `git ls-remote`).
- Project remote `main`: `de0f8d83c4a917f3fa801e1ef5c703cd9d9a5a84` (live `git ls-remote`).
- Reviewed FIX-02 candidate/branch:
  `design/pre-01b-d2-clar-01-fix-02-retry-gap-provenance@bb7c8933796ebee302a8cd2af909f50859ceebc5`.
- Verified FIX-02 parent: `e408ef7d14213aa5a6ff2cad37dc04b1a65810fd`.
- I2 foundation checkpoint: `b0b89a8919303bbbd34b4e7c685282e95e0c73ed`.
- FIX-03 branch:
  `design/pre-01b-d2-clar-01-fix-03-process-lost-terminal`, created from exact `bb7c893...`.
- Root checkout contained unrelated pre-existing dirty changes. Work used a new isolated external
  worktree; no root file was reset, stashed, cleaned, overwritten or attributed to this task.

## Main Drift Classification

Live project remote `main` exactly matched the dispatch pin `de0f8d83...`; therefore there was no
post-dispatch main drift to classify. The existing clarification lineage remains based on immutable
`bb7c893...`; no rebase or main merge was performed. The branch-local delta from accepted main
contains the clarification lineage itself and is not treated as main drift.

## Reviewed FIX-02 Candidate

FIX-02 correctly distinguished zero Attempt history, retry gap and current terminal-producing
Attempt for external terminal predicates. It also preserved the nine exact NULL-final-Attempt pairs
and prohibited linking the latest historical Attempt merely because it exists.

Its recovery sentence remained incomplete:

```text
ACTIVE + STARTED with no completion
-> PROCESS_LOST / ABANDONED
-> create a next Attempt only if joint budget + deadline permit
```

It did not define the Invocation result when retry was unavailable solely because the accepted retry
policy had no remaining safe capacity.

## Re-Review Finding

`PRE01B-D2-CLAR01-FIX02-RR-P1-01` — process-lost/no-retry terminal provenance and Invocation
closure were undefined.

## Root Cause

FIX-02 fully modeled an external predicate arising in a retry gap, but treated process loss only as
historical Attempt audit plus an optional retry. It omitted the distinct causal case in which the lost
Attempt consumes the last retry authority and no higher-precedence external predicate exists. That
omission allowed an Invocation to remain indefinitely `ACTIVE` / `RETRY_PENDING` solely because a
replacement Attempt could not be authorized.

## Durable Authority

Only durably committed PostgreSQL facts participate in recovery authority. A provider response that
may have existed in process memory before crash, but whose finalizer transaction did not commit, is
not a durable provider result.

Recovery must not reconstruct that response, infer validity, create `AIDecision`, guess provider
winner status or turn unknown response/usage/cost into zero. Durable `STARTED` plus no committed
completion/finalizer result is treated as a lost Attempt.

## Process-Lost Attempt State

The exact existing Attempt remains the provenance row. Recovery uses the already-frozen appropriate
`PROCESS_LOST` / `ABANDONED` lifecycle state; it creates no synthetic Attempt merely to represent
process loss. Attempt identity and all previously committed request/provider/audit facts remain
immutable. Unknown response/usage/cost remains `NULL/UNKNOWN`.

## Recovery Precedence

After identifying the lost Attempt, recovery evaluates in this exact order:

1. existing winner/final;
2. absolute deadline, Evidence supersede, Opportunity/market stale, binding invalid,
   activation/config mismatch, applicable shutdown and other accepted external authority;
3. joint retry-policy eligibility;
4. normal replacement Attempt creation.

Recovery uses the existing `Evidence -> Invocation -> Attempt` lock order and atomically commits the
lost Attempt classification together with exactly one of: external FINAL, `RETRY_PENDING`, or
retry-policy-exhausted FINAL. It must not commit an intermediate `ACTIVE + lost Attempt` combination;
a failed recovery transaction leaves the original durable `ACTIVE + STARTED` state for retry.

If step 2 wins, the external predicate is the terminal authority. The lost Attempt is historical
audit only and FIX-02 retry-gap provenance applies: exact existing terminal pair,
`final_attempt_id=NULL`, `final_decision_id=NULL`.

## Retry Allowed

When no higher-precedence external terminal is true and the joint attempt/deadline/cost policy permits
retry, recovery preserves the lost Attempt as audit and moves the same Invocation to `RETRY_PENDING`.
It retains the same immutable input, provider/model and absolute deadline. A replacement Attempt is
created only by the normal later Attempt-start transaction; no final result is written during recovery.

## Retry Disallowed

When no higher-precedence external terminal is true and retry policy forbids a next Attempt because
of max attempts, cost/token budget, usage/cost uncertainty fail-closed, or another accepted retry
budget, the lost Attempt itself is terminal-producing. Its lifecycle failure plus exhausted retry
authority directly causes the Invocation final.

This is not a retry-gap NULL-origin terminal and does not require a fake replacement Attempt.

## Exact Terminal Mapping

```text
Invocation state = FINAL
final_status = INVALID_SCHEMA
final_reason_code = RETRY_EXHAUSTED
final_attempt_id = exact PROCESS_LOST / ABANDONED Attempt
final_decision_id = NULL
```

No `AIDecision` is created. No new reason literal is introduced.

`INVALID_SCHEMA` is used because process loss produced no durably accepted normalized AI decision;
therefore the result cannot be `VALID` or `INVALID_BUSINESS`. It is `STALE_DECISION` only when an
exact higher-precedence stale/deadline predicate wins, and `CAPACITY_BLOCKED` only when an exact
capacity predicate wins.

## final_attempt_id Ownership

For process-loss/no-retry, the exact lost Attempt is linked because its own durable lifecycle plus
inability to authorize a replacement directly causes FINAL. This preserves FIX-02's causal rule:

- latest historical Attempt alone is never sufficient provenance;
- an external retry-gap terminal leaves the lost Attempt unlinked;
- retry-policy exhaustion caused by the lost Attempt requires that exact Attempt.

## Retry Exhaustion Harmonization

Two Attempt-origin forms remain coherent:

1. completed-Attempt exhaustion — a durable provider/validation failure exhausts policy and that
   completed Attempt is terminal-producing;
2. process-lost-Attempt exhaustion — no durable provider completion exists, but the lost lifecycle
   consumes the last safe retry authority and that lost Attempt is terminal-producing.

Both use `RETRY_EXHAUSTED`, require an exact `final_attempt_id` and remain outside the nine NULL pair
set. The process-lost form is fixed to `INVALID_SCHEMA` and `final_decision_id=NULL`.

## Deadline/Stale Precedence

If restart occurs after the absolute deadline, deadline wins before retry-policy exhaustion:

```text
STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER
final_attempt_id = NULL
```

The lost Attempt remains historical audit. The same precedence model applies to supersede,
Opportunity/market stale, binding invalid and activation/config mismatch under their already-frozen
exact pairs.

## Shutdown

If shutdown is the external authority and no replacement Attempt has begun, recovery uses
`INVALID_SCHEMA / SHUTDOWN_BEFORE_PROVIDER` with NULL final Attempt; the lost Attempt remains audit.

If shutdown previously cancelled the current ACTIVE Attempt and that shutdown terminalization was
durably committed, the existing
`INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT` mapping and exact current Attempt provenance
remain unchanged. An uncommitted cancellation final is never reconstructed after restart.

## Provider-Returned-Uncommitted

When provider may have returned in memory but the process dies before the finalizer transaction
commits, durable DB truth is still `STARTED`, with no normalized result, no `AIDecision` and no
Invocation final. Recovery applies the same process-loss decision tree. Any later duplicate/late
delivery must pass the FINAL winner fence and is audit-only.

## DB CHECK Impact

The nine-pair NULL-final-Attempt CHECK remains unchanged. Process-loss/no-retry is not in that set:

```text
state = FINAL
final_status = INVALID_SCHEMA
final_reason_code = RETRY_EXHAUSTED
final_attempt_id IS NOT NULL
final_decision_id IS NULL
```

The existing same-Invocation composite FK is the required provenance fence. No table, column,
trigger, subquery or second migration is required by this clarification.

## Section Synchronization

- §14.2 now names process-lost-Attempt exhaustion, exact mapping, provenance, `INVALID_SCHEMA`
  rationale and the two legitimate retry-exhaustion forms.
- §15 now freezes durable-only recovery, provider-return-uncommitted handling, precedence, retry
  allowed and retry unavailable closure, plus exactly-one-final fencing.
- §18 now contains explicit process-lost retry-allowed / retry-unavailable rows and the external
  terminal precedence rule.
- §20 now aligns shutdown/restart rows with the same decision tree and preserves the committed active-
  Attempt shutdown mapping.
- §27 now requires targeted durable fixtures for all process-loss branches, precedence, provenance,
  provider-return-uncommitted ambiguity and concurrent recovery.

## Acceptance Tests

Future I2 tests must cover:

- process lost + retry allowed;
- process lost + max-attempt exhausted;
- process lost + cost/token budget exhausted;
- process lost + usage/cost unknown makes retry unsafe;
- process lost + deadline already expired;
- process lost + superseded/stale/binding/activation/config mismatch;
- provider returned in memory + finalizer uncommitted;
- negative external-terminal provenance and positive retry-exhaustion provenance;
- concurrent/duplicate recovery exactly-one-final.

## Files Changed

Exactly two repository paths:

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-03-process-lost-no-retry-terminal.md`

## Verification

- Realtime protocol/project refs and FIX-02/foundation lineage verified.
- PRE-01A-D1, PRE-01B-D1, PRE-01B-D2 at `bb7c893...` and all three clarification/fix dev logs
  read before modification.
- Foundation vocabulary/model/migration evidence inspected read-only at `b0b89a8...`; it already
  contains `PROCESS_LOST`, `ABANDONED`, `RETRY_EXHAUSTED`, `INVALID_SCHEMA` and same-Invocation
  Attempt provenance constraints.
- Whole-artifact required-token scan and §14/§15/§18/§20/§27 consistency review completed.
- Exact delta, `git diff --check`, conflict-marker scan, previous-candidate/foundation/main and
  forbidden-path checks are recorded in the completion evidence.
- Tests: `ZERO` by task contract; no test code changed or executed.
- Production/Runtime/Migration/Schema/Config/State docs: `ZERO`.

## Result

`PRE-01B-D2-CLAR-01-FIX-03 = FIX CANDIDATE DESIGN`.

Status: `READY FOR INDEPENDENT RE-REVIEW` after verification, commit and push. This is not Human
Acceptance and does not amend the Human-Accepted D2 on `main`.

Finding disposition: `PRE01B-D2-CLAR01-FIX02-RR-P1-01 = CLAIMED CLOSED`, subject to Independent
Re-Review.

## Remaining

- Independent Re-Review only.
- Human Acceptance only after a future passing re-review and explicit human confirmation.
- PRE-01B-I2 remains not resumed and unauthorized by this task.

## Context For Next AI

- Review recovery precedence before retry-policy exhaustion.
- Verify external terminal authority leaves the lost Attempt unlinked, while retry-policy exhaustion
  requires that exact lost Attempt.
- Verify provider-return-without-finalizer is treated only from durable DB facts.
- Verify the nine NULL-Attempt pairs and FIX-02 retry-gap semantics remain unchanged.
- Original Human-Accepted PRE-01B-D2 on `main` remains authoritative until this candidate passes
  Independent Re-Review and Human Acceptance.

## Evidence Pointers

- D2: top FIX-03 candidate record, §14.2, §15, §18, §20.2 and §27.
- FIX-02 candidate: `bb7c8933796ebee302a8cd2af909f50859ceebc5`.
- FIX-02 dev log:
  `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-02-retry-gap-terminal-provenance.md`.
- I2 foundation checkpoint `b0b89a8...`: vocabulary, ORM model and migration 0010 were read-only;
  no foundation file changed.
