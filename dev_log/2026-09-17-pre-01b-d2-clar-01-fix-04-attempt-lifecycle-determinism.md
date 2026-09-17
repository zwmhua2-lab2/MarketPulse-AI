# PRE-01B-D2-CLAR-01-FIX-04｜Attempt Lifecycle Determinism

## Task

Resolve exactly `PRE01B-D2-CLAR01-FIX03-RR-P1-01`: freeze one deterministic and mechanically
testable rule for selecting `PROCESS_LOST` versus `ABANDONED` in the PRE-01B-I2 V1 Attempt
lifecycle.

Task type: `CLARIFICATION FIX / DOCS ONLY`.

## Scope

- Freeze the exact `PROCESS_LOST` and `ABANDONED` predicates and their mutual exclusivity.
- Synchronize restart/process-loss recovery, live shutdown cancellation, crash-before-commit,
  provider-returned-but-uncommitted, retry allowed/exhausted, external terminal precedence,
  `final_attempt_id`, atomicity and future exact-state tests.
- Update only D2 §14 / §15 / §18 / §20 / §27 directly dependent normative wording.
- Record the unaccepted FIX-04 candidate state minimally in `PROJECT_STATE.md`.

## Out of Scope

- No backend, frontend, test, script, migration, schema, config, deployment, Runtime, service,
  database or provider change.
- No PRE-01A-D1, PRE-01B-D1, prior clarification dev log, `DECISIONS.md`, `AI_CONTEXT.md`,
  `PRODUCT_REQUIREMENTS.md`, foundation, `.workbuddy`, memory, skill or daily-log change.
- No new Attempt state, `DecisionStatus`, reason literal, retry budget, queue/SAVEPOINT/fence/
  Protection/arm-identity change.
- No PRE-01B-I2 resume, Gate A/B/C activation, Production/Live/provider call, main merge,
  Independent Re-Review or Human Acceptance.

## Repository Truth

- Protocol: `v1.2.0 / ACCEPTED`.
- Protocol remote `main`: `373a4d8f1c5bcf2bdef33ed1e49bd57f0c49473b`.
- Project remote `main`: `de0f8d83c4a917f3fa801e1ef5c703cd9d9a5a84`.
- Reviewed FIX-03 candidate: `7fd0e93ffb746bf6330961dcfed5127ffca9975e`.
- Expected and actual FIX-03 parent: `bb7c8933796ebee302a8cd2af909f50859ceebc5`.
- Foundation checkpoint: `b0b89a8919303bbbd34b4e7c685282e95e0c73ed`.
- Branch: `design/pre-01b-d2-clar-01-fix-04-attempt-lifecycle`.
- The root checkout contained unrelated pre-existing dirty changes. Work used a new isolated
  worktree and did not reset, stash, clean, overwrite or attribute those changes.

## Main Delta Check

`merge-base(7fd0e93, de0f8d8) = 547095f`. The candidate side contains only the CLAR-01 → FIX-01
→ FIX-02 → FIX-03 clarification lineage; the current-main side contains later UI-V1/UI-F01
changes. The drift is orthogonal to this PRE-01B-D2 clarification. No rebase or main merge occurred.

## Finding Evidence

FIX-03 used active interchangeable wording such as `PROCESS_LOST / ABANDONED` in §14, §15,
§18, §20 and §27. It therefore allowed the same durable `ACTIVE + STARTED + no durable
completion` facts to select either Attempt state during restart, and it incorrectly allowed
`ABANDONED` to participate in generic retry exhaustion.

## Frozen Predicates

### PROCESS_LOST

`PROCESS_LOST` is the only legal Attempt state when newly authoritative startup/restart recovery
finds an existing durable Invocation `ACTIVE`, its current Attempt durably `STARTED`, no durable
Attempt completion / authoritative finalizer result / Invocation `FINAL`, and the previous owning
runtime/process can no longer provide authoritative completion. Provider network failure need not be
proved. A provider result that existed only in old-process memory remains uncommitted and is not
reconstructed.

### ABANDONED

`ABANDONED` is legal only while the currently authoritative live RuntimeHost still owns the
`ACTIVE + STARTED` Attempt, deliberate shutdown cancellation/cleanup has been positively observed,
and one winner-fenced transaction atomically commits the exact Attempt as `ABANDONED` plus the
Invocation final `INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT`, with
`final_attempt_id` referencing that Attempt. V1 has no other `ABANDONED` emitter.

## Mutual Exclusivity / Crash Boundary

Previous owner authority gone ⇒ restart/recovery ⇒ `PROCESS_LOST` only. Current live owner remains
authoritative and durable shutdown cancellation transaction commits ⇒ `ABANDONED` only. If
cancellation completes only in memory and the transaction rolls back or the process is lost before
commit, durable state remains `ACTIVE + STARTED`; restart must classify `PROCESS_LOST` and must not
reconstruct `ABANDONED`.

## Recovery / Provenance

- `PROCESS_LOST` + higher-precedence external terminal ⇒ lost Attempt is historical audit;
  existing FIX-02 retry-gap exact pair wins; `final_attempt_id=NULL`.
- `PROCESS_LOST` + retry authorized ⇒ same Invocation `RETRY_PENDING`; no FINAL; next Attempt only
  through normal Attempt-start.
- `PROCESS_LOST` + retry unavailable ⇒ `FINAL + INVALID_SCHEMA / RETRY_EXHAUSTED`;
  `final_attempt_id` references the exact `PROCESS_LOST` Attempt; `final_decision_id=NULL`.
- `ABANDONED` is shutdown-specific and never maps to `RETRY_EXHAUSTED`.
- Neither lifecycle classification may be committed free-standing; rollback leaves the prior durable
  state, normally `ACTIVE + STARTED`.

## Files Changed

Exactly three repository paths:

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-04-attempt-lifecycle-determinism.md`
3. `PROJECT_STATE.md`

## Verification

- Realtime protocol/project/main/candidate refs and exact parent checked.
- Main SHA delta classified from actual graph and paths.
- Whole-artifact lifecycle token scan performed across the complete D2 candidate.
- §14 / §15 / §18 / §20 / §27 synchronized to exact predicates and future expected-state tests.
- `git diff --check`: PASS (exit 0; Windows LF-to-CRLF notices only, no whitespace error).
- Conflict-marker scan: PASS (no matches).
- Exact allowed-path audit: PASS (only the three authorized paths changed).
- Tests: `ZERO CHANGE / NOT RUN BY DOCS-ONLY TASK`.
- Production / Runtime / Migration / Schema / Config: `ZERO`.

## Result

`PRE-01B-D2-CLAR-01-FIX-04 = FIX CANDIDATE DESIGN`.

Formal Task State: `IMPLEMENTING`.

Handoff Marker after candidate commit/push: `READY FOR INDEPENDENT RE-REVIEW`.

Human Acceptance: `NOT PERFORMED`.

Finding disposition: `CLAIMED CLOSED` pending Independent Re-Review.

## Remaining

Independent Re-Review only. PRE-01B-I2 remains not resumed and unauthorized by this task.

## Risks

The accepted PRE-01B-D2 on `main` remains authoritative until this candidate is independently
reviewed and Human-accepted. FIX-04 does not authorize application or migration changes.

## Context For Next AI

- Verify the exact durable predicates independently; do not rely on this worker claim.
- Confirm restart never emits `ABANDONED`, and live shutdown never emits `PROCESS_LOST` before
  ownership is actually lost.
- Confirm the crash-before-commit fixture leaves no durable `ABANDONED` and restarts as
  `PROCESS_LOST`.
- Confirm existing FIX-02/FIX-03 provenance and retry-exhaustion semantics remain intact.

## Evidence

- D2 §14.2, §15, §18, §20.2 and §27.
- Reviewed FIX-03 commit `7fd0e93ffb746bf6330961dcfed5127ffca9975e`.
- FIX-03 dev log:
  `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-03-process-lost-no-retry-terminal.md`.
