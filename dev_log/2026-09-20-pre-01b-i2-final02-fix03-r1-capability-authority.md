# 2026-09-20 PRE-01B-I2 FINAL-02 FIX-03-R1 — Latest-Main Capability Authority

## Task and lineage

- Task: `PRE-01B-I2-RESUME-01-C3-FINAL-02-FIX-03-R1`.
- Protocol: `v1.4.3 / ACCEPTED`; remote main =
  `cabd07b3acc064851f5cf73b9baed834ed599b28`.
- Latest Accepted Main base = `f09245ab346495f60556a7eba49980d947a4781f`.
- Old common base = `df02073521140e7ae599e03f2e04190b6a5ae590`.
- Immutable failed FIX-02 evidence = `2b8761addd004d5713c6dc09f9bc9ad2bee80a3e`.
- Candidate branch = `pre-01b-i2-final02-fix03-r1-latest-main-capability`.

## Baseline reconstruction

- `df020735... → f09245...` is exactly six accepted UI-RD01 commits: `a2f8951`,
  `fc0febf`, `58e02d0`, `764cdb2`, `5377537`, `f09245a`.
- Current-main drift paths = 21: `AI_CONTEXT.md`, `PROJECT_STATE.md`, Product Read
  `context.py`, `cursor.py`, `market_scanner.py`, `models.py`, `opportunities.py`,
  `system.py`, `edge/aggregation_snapshot.py`, `runtime_host.py`, Product Read tests,
  eight UI-RD01 dev logs, and `frontend/src/api/generated.ts`.
- Old FIX-02 paths = 34. Exact overlap = `AI_CONTEXT.md`, `PROJECT_STATE.md`, and
  `backend/src/marketpulse/runtime_host.py`; main-only = 18, FIX-02-only = 31.
- Reconstruction used a three-way content patch from `df020735... → 2b8761...` onto
  `f09245...`. Non-overlap paths were carried unchanged. The two state files preserve all
  accepted UI-RD01 records and only add the current PRE-01B-I2 FIX-03-R1 state. RuntimeHost
  retains the latest Product Read runtime snapshot behavior while retaining PRE-I2 composition.

## Capability-authority remediation

- `RestartRecoveryCapability` and `LiveAttemptCapability` no longer have public usable
  constructors. `HostAdvisoryAuthorityIssuer` is RuntimeHost-root-bound, and each issued
  capability carries an issuer-held credential instead of caller-supplied issuer/proof fields.
- Restart admission checks issuer/root validity on every `require_active()` and
  `admit_owner_session()` call. Startup completion closes restart issuance; lock loss and
  singleton release revoke all local capability credentials.
- Live capability validates exact Host lifetime, Invocation, Attempt, issued credential and
  cancellation receipt before resolving to RuntimeHost's actual owner-session operation.
  Wrong Invocation/Attempt, stale root, revocation and failed owner proof fail closed before
  lifecycle mutation. Recovery cannot obtain a live capability.
- The final admission order remains Evidence → Invocation → Attempt → capability/local checks
  → `SingletonOwnerSessionGate` → `pg_stat_clear_snapshot()` → FINAL OWNER-SESSION PROOF →
  transaction admission → lifecycle mutation. No table, schema, fence, signature, owner
  identity, Provider, Gate or Live activation was added.

## Verification

- Focused capability contracts: `56 passed in 1.40s`.
- Real RuntimeHost owner-proof/revocation regression: `1 passed, 1 warning in 4.22s`.
- SE-02B durable lifecycle regression on isolated PostgreSQL `127.0.0.1:5450`:
  `55 passed in 131.26s`.
- RuntimeHost + restart recovery + resource lifecycle: `65 passed, 1 warning in 144.62s`.
- Latest-main Product Read regression: `54 passed, 18 warnings in 41.25s`.
  Its disposable databases ran on `:5450`; a repository-external temporary Alembic adapter
  made each migration use the test's explicit disposable URL rather than the process-level
  admin URL. No repository code or shared `:5432` database was changed.
- Fresh collection: `845 tests collected in 2.83s`.
- Full backend on isolated PostgreSQL: `845 passed, 21 warnings in 963.73s (0:16:03)`;
  Completed = 845, Missing = 0, Unexpected = 0, Failures = 0.
- Schema verifier: `60/60 PASS`; Alembic `heads` / `current` = `20260917_0010 (head)`.
- `ruff check`, `compileall`, `git diff --check`, and conflict-marker scan = PASS.

## Non-claims and remaining work

- PRE-01B-I2 remains `IMPLEMENTING`; FIX-03-R1 is `IMPLEMENTED / READY FOR INDEPENDENT
  RE-REVIEW`; P1-01/P1-02 are `REMEDIATED / AWAITING INDEPENDENT RE-REVIEW`.
- Independent Re-Review, Human Acceptance, PRE-01B-I2 acceptance and main integration have
  not occurred. Real AI, Gate A/B/C, live G2→G3 and Live remain unactivated.
