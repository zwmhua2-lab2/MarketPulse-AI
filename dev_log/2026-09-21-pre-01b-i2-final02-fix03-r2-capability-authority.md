# 2026-09-21 PRE-01B-I2 FINAL-02 FIX-03-R2 - Capability Authority

## Task and lineage

- Task: `PRE-01B-I2-RESUME-01-C3-FINAL-02-FIX-03-R2`.
- Accepted main = `f09245ab346495f60556a7eba49980d947a4781f` and immutable reviewed R1 candidate =
  `36cfc1fed88e2981dd2fa226eae0e8d122baa51c`, both re-fetched and verified before R2 branch creation.
- Candidate branch: `pre-01b-i2-final02-fix03-r2-capability-authority` from the exact R1 candidate.
- Scope: only `PREI2-IR-P1-01` and `PREI2-IR-P1-02`; no schema, migration, second singleton
  mechanism, activation, frontend, D2/R3 design, or R1 branch change.

## Remediation

- P1-02: `HostAdvisoryAuthorityIssuer` now records a frozen credential-to-issuance binding with the
  exact Host lifetime, Invocation, Attempt, and positive cancellation receipt. `LiveAttemptCapability`
  retains only an issuer-controlled credential; capability-facing identity assignment is rejected.
  `matches()` and owner-session admission resolve authority from issuer-owned issuance state, not from
  mutable capability fields.
- P1-01: a FINAL owner-session proof result other than `True` now calls the same local authority-loss
  path as transport uncertainty: `_lock_lost = True`, `SINGLETON_LOCK = UNAVAILABLE`, and
  `revoke_all()` before returning. A later positive proof cannot restore an old capability.
- The accepted final order remains Evidence -> Invocation -> Attempt -> local capability checks ->
  `SingletonOwnerSessionGate` -> `pg_stat_clear_snapshot()` -> FINAL OWNER-SESSION PROOF -> admitted
  transaction -> lifecycle mutation. No distributed authority was added.

## Focused adverse evidence

- `test_live_capability_identity_is_issuer_owned_immutable_and_revocable` proves Host A / Invocation A /
  Attempt A / Receipt A is valid; public rebinding assignment is rejected; B Invocation/Attempt cannot
  match; issuer state remains A; and revocation invalidates both representations.
- `test_host_capabilities_use_the_real_owner_proof_and_cleanup_revokes_them` uses the real RuntimeHost
  owner-proof path with a normal-commit definitive `False` seam. It asserts admission false,
  `_lock_lost`, unavailable singleton health, capability revocation, and that restoring a later-valid
  connection cannot re-admit the same old capability. Restart capability issuance is already closed in
  the started lifecycle phase; existing non-forgeability and recovery/live separation regressions pass.

## Verification

- Isolated PostgreSQL: temporary non-volume PostgreSQL 16 at `127.0.0.1:5450`; shared `:5432` was not
  used by verification.
- Focused capability contracts: `57 passed in 1.62s`.
- Focused real RuntimeHost definitive-False regression: `1 passed, 1 warning in 4.38s`.
- RuntimeHost suite: `53 passed, 1 warning in 97.46s`.
- SE-02B opportunity/lifecycle suite: `55 passed in 144.47s`.
- Fresh collection: `846 tests collected in 4.59s`.
- Full backend: `846 passed, 20 warnings in 995.38s (0:16:35)`; Completed = 846, Missing = 0,
  Unexpected = 0, Failures = 0.
- Alembic head/current: `20260917_0010 (head)`; PRE-I2 schema verifier: `60/60 PASS`.
- `ruff check`, `compileall`, `git diff --check`, and conflict-marker scan: PASS.
- Full-suite migration isolation used a repository-external, process-local adapter so disposable child
  migrations use each test's explicit URL while normal Settings I/O remains on isolated `:5450`; no
  repository code/configuration or shared database was altered for this adapter.
- Accepted D2 blob = `d08d7feebec4c0b8d74b550a75d161659709cd70` unchanged; accepted R3 blob =
  `b91a6f7772e7894aeb9d801ea7dc62aa57a4ba40` unchanged.

## State

- `PRE-01B-I2 = IMPLEMENTING`.
- `FIX-03-R2 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`.
- `PREI2-IR-P1-01 = REMEDIATED / AWAITING INDEPENDENT RE-REVIEW`.
- `PREI2-IR-P1-02 = REMEDIATED / AWAITING INDEPENDENT RE-REVIEW`.
- Independent Re-Review and Human Acceptance are not performed. Main remains unchanged; Real AI,
  Gate A/B/C, live G2->G3, Live and Live Trading remain inactive.
