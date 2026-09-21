# 2026-09-21 PRE-01B-I2 FINAL-02 FIX-03-R3 - Binding Integrity

## Task and scope

- Task: `PRE-01B-I2-RESUME-01-C3-FINAL-02-FIX-03-R3`.
- Accepted main was re-fetched as `f09245ab346495f60556a7eba49980d947a4781f`; immutable R2 task
  base was re-fetched as `b1ae41c1c49467e3955ab67fe0e1edb8054a9f46`.
- Candidate branch: `pre-01b-i2-final02-fix03-r3-binding-integrity`, created in an isolated
  worktree from that exact R2 SHA. R2 and main were not modified.
- Scope: only `PREI2-IR-P1-02` binding integrity, with the required P1-01 non-regression. No
  schema, migration, RuntimeHost ownership redesign, second fence, design artifact, frontend,
  activation, provider, Gate, live G2→G3, or main change.

## Remediation

- Removed the caller-reachable credential-to-issuance dictionary from
  `HostAdvisoryAuthorityIssuer`. The issuer creates one frozen `_LiveAttemptIssuance`; the issued
  `LiveAttemptCapability` retains that frozen value in an immutable slot. `matches()` resolves
  Host lifetime, Invocation, Attempt, and positive cancellation receipt from that immutable
  issuance rather than any mutable issuer registry.
- Added `test_live_capability_binding_cannot_be_redirected_through_reachable_issuer_state`. It
  scans caller-reachable credential-keyed issuer dictionaries, attempts the prior replacement
  operation with lifecycle identity D, proves no such path exists, preserves C-only matching,
  rejects direct issuance-slot reassignment, and proves revocation invalidates C.
- The new regression failed on the unmodified R2 implementation because its issuer exposed one
  credential-keyed issuance dictionary; it passes on R3. P1-01 definitive-False behavior and the
  accepted owner-session authority order were not changed.

## Verification

- Isolated PostgreSQL only: temporary PostgreSQL 16 at `127.0.0.1:5450`; shared `:5432` was not
  used or modified.
- New R3 negative regression on R2: `1 failed` (caller-reachable replacement dictionary found).
- Capability contracts: `58 passed in 1.38s`.
- P1-01 real RuntimeHost definitive-False regression: `1 passed, 1 warning in 4.76s`.
- RuntimeHost relevant suite: `53 passed, 1 warning in 75.61s`.
- SE-02B opportunity/lifecycle suite: `55 passed in 116.66s`.
- Alembic `heads` and `current`: `20260917_0010 (head)`.
- PRE-I2 schema verifier: `60/60 PASS`.
- Fresh collection: `847 tests collected in 1.72s`.
- Full backend: `847 passed, 20 warnings in 851.33s (0:14:11)`; Completed = 847, Missing = 0,
  Unexpected = 0, Failures = 0.
- Full-suite fixture migration isolation used a repository-external, process-local pytest adapter:
  it temporarily masks inherited `DATABASE_URL` only while Alembic evaluates a fixture's explicit
  Config URL. The adapter is outside the repository; source, configuration, and shared database
  were not modified.
- `ruff check`, `compileall`, `git diff --check`, exact conflict-marker scan, and forbidden-path
  audit: PASS.
- Accepted D2 blob = `d08d7feebec4c0b8d74b550a75d161659709cd70` unchanged; accepted R3 blob =
  `b91a6f7772e7894aeb9d801ea7dc62aa57a4ba40` unchanged.

## State

- `PRE-01B-I2 = IMPLEMENTING`.
- `FIX-03-R3 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`.
- `PREI2-IR-P1-01 = CLOSED / PASS`.
- `PREI2-IR-P1-02 = REMEDIATED / AWAITING INDEPENDENT RE-REVIEW`.
- Independent Re-Review and Human Acceptance are not performed. Main remains unchanged; Recovery
  / Live separation remains intact; Real AI, Gate A/B/C, live G2→G3, Live and Live Trading remain
  inactive.
