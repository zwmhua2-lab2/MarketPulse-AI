# PRE-01B-D2-CLAR-01-FIX-02｜Retry-Gap Terminal Provenance Fix

## Task

Fix exactly `PRE01B-D2-CLAR01-FIX01-RR-P1-01`: freeze one unambiguous terminal-provenance
contract for the interval in which historical Attempts exist but the next/current Attempt has not
yet been durably created.

Task type: `CLARIFICATION FIX / DOCS ONLY`.

## Scope

- Freeze `final_attempt_id` as the exact durable Attempt whose lifecycle/result directly produced
  the authoritative terminal result.
- Separate zero Attempt history, retry gap, and current terminal-producing Attempt.
- Apply retry-gap semantics to deadline, supersede, opportunity/market stale, binding, activation,
  config, DB capacity, queue/re-dispatch and shutdown terminals.
- Synchronize D2 §14, §15, §17, §18, §19, §20.1 and §27 plus directly dependent wording.
- Preserve the FIX-01 nine-pair closed set and CLAR-01 F-01/F-02 identity requirements.

## Out of Scope

- No implementation, test, migration, schema, Runtime, config, service, database or provider change.
- No PRE-01B-I2 resume; no migration 0010, model, vocabulary or identity edit.
- No new table, durable column, trigger, CHECK subquery, terminal reason or fake Attempt.
- No retry-budget, SAVEPOINT, DB-fence, reserve, provider-adapter, experiment, RuntimeHost,
  DISABLED-epoch, Gate A/B/C or PRE-01A causal-boundary redesign.
- No `PROJECT_STATE.md`, `AI_CONTEXT.md`, `DECISIONS.md`, `PRODUCT_REQUIREMENTS.md`, PRE-01A-D1,
  PRE-01B-D1, prior clarification/fix dev log, `.workbuddy`, memory, skill or daily-log change.
- No Independent Re-Review, Human Acceptance, main merge or PRE-01B-I2 activation.

## Repository Truth

- Protocol: `v1.1.0 / ACCEPTED`.
- Protocol remote `main`: `a80c55b7451f77883d8b0713a228f0d9bebf7d22` after live fetch.
- Project remote `main`: `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` after live fetch.
- Reviewed FIX-01 candidate/branch:
  `design/pre-01b-d2-clar-01-fix-01-noattempt-completeness@e408ef7d14213aa5a6ff2cad37dc04b1a65810fd`.
- Verified FIX-01 parent: `f583e096d3a9ed33dcce97b6581b8c336a57d671`.
- I2 foundation checkpoint: `b0b89a8919303bbbd34b4e7c685282e95e0c73ed`.
- FIX-02 branch:
  `design/pre-01b-d2-clar-01-fix-02-retry-gap-provenance`, created from exact `e408ef7...`.
- Root checkout contained unrelated pre-existing dirty changes. Work used a new isolated external
  worktree; no root file was reset, stashed, cleaned, overwritten or attributed to this task.

### Main Drift Classification

The live `main` pin matched the task dispatch pin. Independent `git log` / `git diff --name-status`
from the last accepted PRE-01B-D2 closeout base `547095f...` to `2c95cc2...` showed only UI-V1
design/dev-log/state-document drift. The targeted PRE-01A/PRE-01B/advisory/migration semantic paths
had no diff. The clarification lineage therefore remains on immutable `e408ef7...`; no rebase or
main merge was performed.

## Reviewed FIX-01 Candidate

FIX-01 correctly preserved nine exact NULL-final-Attempt pairs and used Attempt-start commit as the
first-dispatch boundary. Its wording nevertheless collapsed two non-equivalent facts:

- the Invocation has any historical Attempt;
- the current terminal condition was directly produced by a current Attempt.

The lifecycle permits `ACTIVE -> RETRY_PENDING -> FINAL` before another Attempt is inserted, so the
collapse could falsely link a historical Attempt as terminal provenance.

## Re-Review Finding

`PRE01B-D2-CLAR01-FIX01-RR-P1-01` — retry-gap terminal provenance was undefined.

## Root Cause

FIX-01 defined the provenance boundary using total durable Attempt existence. That works for a first
dispatch but fails after a retryable Attempt has completed: an old Attempt exists while the new
deadline/stale/capacity/shutdown predicate arises before the next Attempt-start commit.

## Three Provenance States

1. **Zero Attempt History** — no Attempt row ever committed.
2. **Retry Gap** — historical Attempt rows exist, but no new/current Attempt committed for the
   terminalizing dispatch/retry cycle.
3. **Current Terminal-Producing Attempt Exists** — the current cycle's Attempt-start transaction
   committed and that Attempt's lifecycle/result directly produces the terminal outcome.

States 1 and 2 have no terminal-producing Attempt. State 3 has one exact current Attempt.

## `final_attempt_id` Semantic Freeze

`final_attempt_id` references only the durable Attempt whose lifecycle/result directly produced the
authoritative terminal result. It is not the latest historical Attempt and not any earlier Attempt in
the Invocation. States 1 and 2 require NULL; State 3 requires the exact same-Invocation current
Attempt. Historical rows remain immutable audit. No Attempt is fabricated for provenance.

## Retry-Gap Rules

### Deadline

`Attempt #1 -> RETRY_PENDING -> no Attempt #2 -> deadline` uses
`STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER`, NULL final Attempt/Decision, no new provider
call, and preserves Attempt #1. After Attempt #2 start commit, the mapping is
`STALE_DECISION / DEADLINE_EXPIRED` with `final_attempt_id=Attempt #2`.

### Supersede

Evidence supersede in a retry gap uses
`STALE_DECISION / EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` with NULL final Attempt. After the current
Attempt exists it uses `EVIDENCE_SUPERSEDED` with that Attempt's provenance.

### Stale

Opportunity eligibility or market freshness loss in a retry gap uses
`STALE_DECISION / OPPORTUNITY_STALE_BEFORE_PROVIDER`. Historical Attempts remain audit only.

### Binding

Binding invalidity in a retry gap uses
`STALE_DECISION / BINDING_INVALID_BEFORE_PROVIDER`. A historical Attempt is never linked merely to
avoid NULL.

### Config

Actual disablement uses `ACTIVATION_DISABLED_BEFORE_PROVIDER`; enabled-but-incompatible frozen
experiment/config uses `EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER`. Both carry NULL final Attempt
when they arise before the current retry Attempt is created.

### Capacity

DB capacity unavailable before the next retry Attempt exists uses
`CAPACITY_BLOCKED / ADVISORY_DB_CAPACITY_UNAVAILABLE`, NULL final Attempt/Decision and zero new
provider calls for that retry cycle. Historical Attempt/provider calls may exist.

### Queue

The existing bounded `AdvisoryIngress` queue is the single process-local dispatch mechanism for
initial dispatch, retry continuation and recovery re-dispatch. A `RETRY_PENDING` re-offer rejected by
REJECT NEWEST uses `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` with NULL final Attempt. The same
frozen ref/queue is reused; no second dispatch path is introduced.

### Shutdown

Shutdown in a retry gap uses `INVALID_SCHEMA / SHUTDOWN_BEFORE_PROVIDER` with NULL final Attempt.
Shutdown after the current Attempt exists uses `SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT` and requires that
current Attempt's provenance.

## Retry Exhaustion Non-Regression

True exhaustion remains Attempt-origin. If the last completed Attempt result causes the joint retry
policy to stop, that last Attempt is the terminal-producing Attempt and remains required with
`RETRY_EXHAUSTED`. Only a new external terminal condition after entering `RETRY_PENDING` and before
the next Attempt creation is retry gap.

## Section Synchronization

- §14 defines the three states, current-cycle durable boundary, nine-pair authority and no-fabrication rule.
- §15 applies retry-gap semantics during restart and preserves historical Attempt history.
- §16 makes retry/recovery re-offer through the existing bounded queue explicit.
- §17 applies the same before/after-current-Attempt boundary to first and retry dispatch.
- §18 distinguishes no current terminal-producing Attempt from a current committed Attempt for all
  relevant failures and preserves retry exhaustion.
- §19 renames/redefines its columns by terminal-producing provenance rather than total row count.
- §20 / §20.1 freeze shutdown and DB-capacity retry-gap behavior.
- §27 requires zero-history, retry-gap, current-Attempt, negative-linkage and no-fabrication proofs.

## DB CHECK Implementability

For FINAL Invocation, `final_attempt_id IS NULL` iff the exact `(final_status, final_reason_code)` is
one of the existing nine pairs. The CHECK does not assert zero historical Attempt rows; historical
rows remain separately queryable. This permits retry-gap NULL provenance without subqueries, triggers,
new columns or fake Attempts. Future I2 tests must prove acceptance with historical rows and rejection
of a non-nine-pair NULL final Attempt.

## Files Changed

Exactly two paths:

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-02-retry-gap-terminal-provenance.md`

## Verification

- Live protocol/project refs and FIX-01/foundation lineage verified.
- Full required-token artifact scan and section-consistency review performed.
- Nine-pair set preserved; no reason literal, table, column, trigger or CHECK subquery added.
- `git diff --check`: PASS (exit 0; Windows LF-to-CRLF notice only, no whitespace error).
- Conflict-marker scan: PASS (no marker found; `rg` exit 1).
- Exact pre-commit delta from `e408ef7...`: PASS — one modified design document and this one
  newly added dev log; no other path changed.
- Tests: `ZERO` by task contract; no test code changed or executed.
- Production/Runtime/Migration/Schema/Config/State docs: `ZERO`.

## Result

`PRE-01B-D2-CLAR-01-FIX-02 = FIX CANDIDATE DESIGN`.

Status: `READY FOR INDEPENDENT RE-REVIEW` after verification, commit and push. This is not Human
Acceptance and does not amend the Human-Accepted D2 on `main`.

## Remaining

- Independent Re-Review only.
- Human Acceptance only after a future passing re-review and explicit human confirmation.
- PRE-01B-I2 remains not resumed and unauthorized by this task.

## Context For Next AI

- Review provenance by current terminal-producing Attempt, never by total historical Attempt count.
- Verify every retry-gap path leaves Attempt #1 immutable, creates no Attempt #2 and writes NULL
  `final_attempt_id` with one of the unchanged nine exact pairs.
- Verify current-Attempt contrast cases link exact Attempt #2.
- Review queue retry/recovery publication as the existing bounded ref path, not a new architecture.
- Original Human-Accepted PRE-01B-D2 on `main` remains authoritative until this candidate passes
  Independent Re-Review and Human Acceptance.

## Evidence Pointers

- D2: §10, §14, §15, §16, §17, §18, §19, §20.1 and §27.
- FIX-01 candidate: `e408ef7...`.
- FIX-01 dev log:
  `dev_log/2026-09-17-pre-01b-d2-clar-01-fix-01-noattempt-terminal-completeness.md`.
- I2 foundation read-only evidence at `b0b89a8...`: vocabulary, identity, ORM model and migration
  0010; no foundation file changed.
