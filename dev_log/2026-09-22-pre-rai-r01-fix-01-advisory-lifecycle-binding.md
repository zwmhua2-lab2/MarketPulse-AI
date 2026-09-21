# PRE-RAI-R01-FIX-01｜生命周期与绑定修复

## Task / Scope

- Task ID: `PRE-RAI-R01-FIX-01`.
- Base / remote `main` at start and revalidation: `d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b`.
- Candidate branch and isolated worktree: `pre-rai-r01-fix-01-advisory-lifecycle-binding`.
- Scope: P1-01 locked-row freshness, P1-02 durable Attempt lifecycle eligibility, P1-03
  canonical binding/current-authority integrity, and deterministic regressions only.
- Zero change: schema, migration, `DECISIONS.md`, accepted design, RuntimeHost ownership, activation,
  provider, Gate A/B/C, live behavior, economic semantics, dependencies, and original dirty worktree.

## Local Implementation

- `AdvisoryAttemptStarter` locks Evidence → Invocation → latest Attempt with
  `populate_existing=True`; only durable `ADMITTED` and `RETRY_PENDING` states can mint a new Attempt.
- `AdvisoryFinalizer` reloads locked lifecycle rows, admits completion only for the newest exact
  `STARTED` Attempt of an `ACTIVE` Invocation, and preserves first FINAL winner facts.
- `AdvisoryPredicateEvaluator` recomputes existing canonical snapshot payload hash, snapshot identity,
  and input-binding digest; current authority now exactly compares epoch, experiment digest and deadline
  policy in addition to the existing durable fields.

## Complete Verification Evidence

- New P1 nodes: `test_pre_rai_p1_01_preloaded_stale_identity_cannot_replace_first_winner`,
  `test_pre_rai_p1_02_start_gate_rejects_active_and_final_but_permits_retry`,
  `test_pre_rai_p1_02_historical_attempt_cannot_complete_while_current_attempt_is_active`,
  `test_pre_rai_p1_02_process_lost_attempt_cannot_regain_completion_authority`, and five parameter
  cases of `test_pre_rai_p1_03_binding_and_current_authority_mismatches_fail_closed`: `9 passed in
  21.11s`.
- Advisory identity plus Gate-A fail-closed node:
  `backend/tests/test_pre_01b_i2_advisory_identity.py` and
  `test_gate_a_setting_fails_closed_without_a_separately_authorized_activation_pack`: `59 passed,
  1 warning in 1.61s`, exit `0`.
- PRE-I2 schema verifier: `60/60 PASS`; Alembic `heads` and `current`:
  `20260917_0010 (head)`; Ruff, compileall and `git diff --check`: exit `0`; conflict markers: `0`.
- Fresh full collection on task DB: `856 tests collected in 3.31s`.

## R1 Corrected Isolation Verification

- R1 used a task-only PostgreSQL 16 container with no shared volume, host port `55432`, primary database
  exactly `marketpulse`, and a worktree-local gitignored `.env` pointing Settings to that primary.
- Before collection and full pytest, parent `DATABASE_URL = None`; `Settings().database_url` =
  `postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:55432/marketpulse`. Alembic upgrade/current
  ran in a separate child process only; pytest received no `DATABASE_URL` environment variable.
- R1 reran the nine new P1 nodes: `9 passed in 23.85s`; advisory identity plus Gate-A fail-closed:
  `59 passed, 1 warning in 1.61s`; full SE-02B opportunity/advisory lifecycle suite:
  `64 passed in 158.76s`, exit `0`.
- Schema verifier: `60/60 PASS`; Alembic head/current: `20260917_0010 (head)`; Ruff, compileall,
  diff check and conflict-marker scan: pass. Fresh collection: `856 collected in 1.88s`.
- Full backend command: `py -3.14 -m pytest backend/tests -q`; `856 passed, 21 warnings in 954.07s
  (0:15:54)`, failed `0`, errors `0`, skipped `0`, xfailed `0`, exit `0`.

## State / Git

- Formal task_state: `IMPLEMENTING`; R1 handoff state: `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`.
- Candidate branch remains `pre-rai-r01-fix-01-advisory-lifecycle-binding`; candidate SHA is recorded
  by the final push report. `main` remains unchanged.
- R1 Timing: Estimated `00:20:00-00:35:00`; Execution Started At `2026-09-22T05:29:22.8104221+08:00`;
  Completed At `NOT AVAILABLE` until post-cleanup/push revalidation; Run Duration / Estimate Delta
  `NOT VERIFIED`.
