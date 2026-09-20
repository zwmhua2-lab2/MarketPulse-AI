# 2026-09-19 PRE-01B-I2 Resume-01 — Advisory Durable Slice — v5 → v6 Integration

## Task

- Task: `PRE-01B-I2-RESUME-01-INTEGRATE-06-RESUME-01`.
- Protocol: `v1.4.1 / ACCEPTED`.
- Protocol Remote Main: `e273adee6347e5be14e0678055d93e7253487283` (`zwmhua2-lab2/ai-dev-protocol`).
- Current Accepted Main: `e5476b46d0d84f0bb4e495e9dc806a6adaa390c7`.
- Current Integration: `v6` (branch `pre-01b-i2-resume-01-integrated-v6`).
- Repair content authority: `dbb91c3d55a722b4c0659fc99e9fbfb490da03b8` (`integrated-v5`, immutable).
- State: `IMPLEMENTING`; Implementation Completion Marker = `NOT READY`; Ready For
  Independent Review = `NO`; Human Acceptance = `NOT PERFORMED`.

## Resume history

- `PRE-01B-I2-RESUME-01-INTEGRATE-06` (first attempt): `BLOCKED BEFORE MUTATION` --
  the attempt resolved the Global Protocol SHA against an unrelated repository and
  stopped before any repository mutation. Zero repository mutations were made; the
  `v6` branch / worktree was not created; no commit was made and no ref was moved.
- `PRE-01B-I2-RESUME-01-INTEGRATE-06-RESUME-01`: `RESUMED` using the correct canonical
  Global Protocol source -- repository `zwmhua2-lab2/ai-dev-protocol`, remote
  `https://github.com/zwmhua2-lab2/ai-dev-protocol.git`, branch `main` at
  `e273adee6347e5be14e0678055d93e7253487283`, Protocol `v1.4.1 / ACCEPTED`.
- Retained from the v5 checkpoint (unchanged by v6): full combined backend suite
  `787 passed / 0 failed / exit 0`; PRE-I2 schema verifier `60/60 PASS`;
  `P1-01 = CLOSED`; `P1-02 = CLOSED`.
- v6 fidelity: v6 was rebuilt from latest accepted main
  `e5476b46d0d84f0bb4e495e9dc806a6adaa390c7`; the same three authorized commits were
  cherry-picked in order (`3 / 3`, zero conflicts, zero manual semantic resolution);
  pre-repair compatibility against `04b8adc` was `7 / 7 MATCH` for the seven repair
  paths and post-restore fidelity against `dbb91c3` was `7 / 7 EXACT`.
  `git diff dbb91c3 HEAD -- backend scripts/verify_pre_01b_i2_advisory_schema.py` is
  empty, so the retained evidence applies to v6 by exact content identity; the full
  backend suite was deliberately not re-executed.
- Latest-main UI-RD01 truth (`AI_CONTEXT.md`, `DECISIONS.md`,
  `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md` and both
  `dev_log/2026-09-19-ui-rd01-i02-requirements*.md`) remains byte-identical to current
  `main`; no PRE-I2 modification was applied to it.
- `FINAL-02 Self Review` = `PENDING`; the task remains `IMPLEMENTING`.

## Scope and boundaries

- Preserve the verified FIX-01 WIP immutably; rebuild a clean integrated-v5 from latest
  accepted main; carry forward only the approved three-commit PRE-I2 chain; reapply only
  the verified repair code/test content; reconcile PRE-I2 documentation to latest-main
  truth; verify and create this repair checkpoint.
- No change to `main`, integrated-v4, `AI_CONTEXT.md`, `DECISIONS.md`, frontend,
  Product model/test, migrations beyond the carried PRE-I2 `20260917_0010`, DB models,
  contracts, Provider/AI/Gate/Live activation, or PRE-I2 business semantics.

## Integration evidence

- WIP was preserved without a content edit on
  `pre-01b-i2-final02-fix01-wip-preservation` at `9ce9fecd2a76a8ef286361a40c43c27b3235f6e3`,
  parent `454e21024b8de433ee21926723c428cbe823f981`; its nine paths were the permitted
  seven repair code/test paths plus `PROJECT_STATE.md` and this dev_log.
- Clean `pre-01b-i2-resume-01-integrated-v5` was based at `08b6c5d`; the approved
  three commits were cherry-picked in order with zero conflicts. The existing PRE-I2
  30-path content matched integrated-v4 exactly before repair application.
- Each of the seven re-applied repair blobs matched the preservation commit exactly.
  P1-01 remains the canonical Evidence → Invocation → Attempt lock ordering with real
  supersede/finalizer concurrency coverage. P1-02 remains queue-only
  `post_commit_offer`, no DB work in queue offer, bounded terminalization under
  Advisory capacity A, and no consumption of Protection reserve R.
- Latest-main CR05 product files
  `backend/src/marketpulse/api/product/models.py` and
  `backend/tests/test_product_system.py` remained byte-identical to `08b6c5d`.

## Verification

- Focused repair suite on isolated PostgreSQL `127.0.0.1:5450`:
  `160 passed, 1 warning`, exit `0`, elapsed `00:03:31`.
- Latest-main Product System: `22 passed, 3 warnings`, exit `0`, elapsed
  `00:00:04`.
- PRE-I2 compatibility set (focused PRE-I2, SE-02A, G5-2/3/4 and the seven carried
  fixture/SE files): `361 passed, 1 warning`, exit `0`, elapsed `00:12:10`.
- PRE-I2 schema verifier on isolated PostgreSQL: `60/60 PASS`, exit `0`, elapsed
  `00:00:21`; `alembic upgrade head`, `heads` and `current` each confirmed
  `20260917_0010 (head)`.
- Full combined backend suite: `787 passed, 3 warnings`, exit `0`, elapsed
  `00:16:06`.
- A prior schema-verifier invocation with `DATABASE_URL` inherited into Alembic failed
  because the script's disposable database was not migrated; it is excluded from PASS
  evidence. The rerun used only `PRE_01B_I2_ADMIN_URL=127.0.0.1:5450` as the script
  requires and passed above. No source change was made for that environment correction.

## Safety

- Only the isolated PostgreSQL container at `127.0.0.1:5450` was used.
- Production and shared `127.0.0.1:5432` were not used by verification commands.
- Real Provider calls = `0`; Real AI / Gate A / Gate B / Gate C / live G2→G3 / Live
  were not activated.

## Execution timing

- Execution Started At: `2026-09-19T01:10:25.0179986+08:00`.
- Verification Completed At: `2026-09-19T01:55:32.2730490+08:00`.
- Timing is finalized in the task Result after static verification, remote revalidation,
  checkpoint commit, and push.

## Remaining

- FINAL-02 Self Review and Candidate Handoff only. This checkpoint is not a final candidate
  and does not start Independent Review or Human Acceptance.

## FIX-02 Verification Amendment and Final Self Review

- Task: `PRE-01B-I2-RESUME-01-C3-FINAL-02-FIX-02-VERIFY-AMEND-01`; Protocol =
  `v1.4.3 / ACCEPTED`, protocol remote main =
  `cabd07b3acc064851f5cf73b9baed834ed599b28`; project `origin/main` = task base
  `df02073521140e7ae599e03f2e04190b6a5ae590` before candidate handoff.
- Amendment evidence: the 30-second individual-node limit is superseded; the required
  `test_more_than_fifty_thousand_forward_observations_are_used_in_full` was run in a
  directly observed foreground pytest session with `PYTHONPATH=src` and
  `DATABASE_URL=postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5450/marketpulse`.
  Terminal result = `1 passed in 172.71s (0:02:52)`, exit `0`. No background, detached,
  hidden, or unsupervised process was used. Coverage requirement and test semantics are
  unchanged.
- Final verification: fresh collection = `789 tests collected`; complete backend run in
  the same isolated environment = `789 passed, 4 warnings in 1007.52s (0:16:47)`, exit
  `0`. Completed set reconciles to collection: Missing = `0`, Unexpected = `0`, Failures =
  `0`. Alembic `heads` / `current` = `20260917_0010 (head)`; schema verifier = `60/60
  PASS`; `ruff`, `compileall`, `git diff --check`, conflict-marker scan and forbidden-path
  audit = PASS. The only migration delta is `20260917_0010`.
- Self Review: P1-03 start path evaluates current durable predicates under the canonical
  Evidence → Invocation → Attempt lock order before persisting `STARTED`; P1-04 finalizer
  locks the same lineage and gives current external predicates precedence over a retryable
  provider response; P1-05 recovery consumes typed `RecoveryInput` plus the final
  owner-session proof; P1-06 `ABANDONED` requires an exact live-attempt capability and
  matching host lifetime. R3 uses the existing dedicated PostgreSQL owner session,
  recorded PID + `backend_start`, and its existing advisory lock; each proof commits before
  return, and the tested owner session is not idle in transaction. Before-proof failure is
  fail-closed; post-proof loss does not retrospectively revoke the committed transition.
  P1-01 lock-race and P1-02 queue/resource paths are included in the full regression.
- Scope / activation review: D1, D2 and R3 artifacts are unchanged; no caller
  `retry_allowed: bool`, caller `cancellation_observed: bool`, or boolean-to-capability
  adapter was restored. Real AI, Gate A/B/C, live G2→G3 and Live remain not activated.
  `FIX-02` and `PREI2-SR-P1-03` through `PREI2-SR-P1-06` are
  `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`; parent `PRE-01B-I2` remains
  `IMPLEMENTING`. Candidate commit and branch-only push are the remaining handoff actions;
  Independent Review and Human Acceptance have not been performed.
