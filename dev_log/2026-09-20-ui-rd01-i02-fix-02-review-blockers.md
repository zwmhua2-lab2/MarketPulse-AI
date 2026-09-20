# UI-RD01-I02-FIX-02-R1｜Opportunity Read Re-Review Findings Fix

## Result

`UI-RD01-I02-FIX-02-R1 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`.
Parent `UI-RD01-I02` formal task_state remains `REVIEW`. Human Acceptance and main integration
were not performed.

## Baseline Reconciliation

- Previous I02 accepted-main base: `e5476b46d0d84f0bb4e495e9dc806a6adaa390c7`.
- Current task base: `df02073521140e7ae599e03f2e04190b6a5ae590`, five commits ahead and zero behind.
- The drift is limited to PRE-01B docs/state/design paths; it does not touch I02 production, tests,
  frontend API, schema, migration, or index.
- A new direct-descendant worktree/branch used content-level carry-forward only. All 15 named
  Fix-01 blobs matched before FIX-02 edits; the 12 paths not intentionally changed by FIX-02 still
  match exactly. Current-main PRE-01B paths and `DECISIONS.md` remain byte-identical.

## Finding Closure

| Finding | Closure evidence |
| --- | --- |
| F1 | Collection derives scoped logical IDs from revision-1 `detected_at`, effective range/cursor, and requested-provenance presence before loading and folding only their complete revision chains. Adverse cases prove unrelated out-of-range and Replay-only corruption do not poison Forward, in-scope corruption returns `SNAPSHOT_FAILED`, legal Forward→Replay projects only canonical Replay, and pre-provenance rows do not cause pagination omission. |
| F2 | Each Decision attribution group validates exactly one event semantic and one non-null exact evidence identity. Equivalent exact/null rows remain legal; differing event semantics or evidence IDs fail closed. |
| F3 | Opportunity/evidence/event/exact-binding integrity is validated before missing `AIDecisionRecord` filtering. A consistent missing Decision stays `NO_PROVABLE_RECORD`; conflicting missing Decision lineage returns `SNAPSHOT_FAILED`. |
| F4 | The Opportunity-local finite classifier covers SQLAlchemy errors plus evidenced `TimeoutError`, connection OS errors, and asyncpg connection/auth errors. Real asyncpg timeout and `InvalidPasswordError` probes return `503 SOURCE_UNAVAILABLE` from both endpoints; mapper RuntimeError remains sanitized `500`. |
| F5 | Fix-01 now retains its verification checkpoint and appends the requested Formal Task final timing without rewriting historical timestamps. |

## Verification

- Isolated task-owned PostgreSQL: `127.0.0.1:54133`, database `marketpulse`, tmpfs container;
  process `DATABASE_URL` unset, worktree-local ignored `.env`, `PYTHONPATH=backend/src`.
- Primary Alembic head: `20260913_0009`; `edge_opportunity_evidence` and `ai_decisions` confirmed.
- Real F4 exception evidence: timeout top-level `builtins.TimeoutError`, cause/context
  `asyncio.exceptions.CancelledError`; auth top-level `asyncpg.exceptions.InvalidPasswordError`,
  no cause/context. Collection and Detail each returned `503 SOURCE_UNAVAILABLE`; response bodies
  did not expose the injected password.
- Focused F1/F2/F3/F4 and required target regression: `166 passed, 20 warnings in 68.63s`, exit 0.
- Full backend: `PYTHONPATH=backend/src; py -3.14 -m pytest -q backend/tests` →
  `756 passed, 0 failed, 0 errors, 0 skipped, 20 warnings in 608.01s`, exit 0.
- Ruff on modified Opportunity source/test: pass. OpenAPI generate/drift, frontend typecheck,
  `test:run` (`7 files / 57 tests`), and build: pass. Generated API blob remains identical to Fix-01.
- `git diff --check`: pass. Schema, migration, index, package manifests, frozen requirements/design,
  PRE-01B artifacts, and `DECISIONS.md`: zero change.

## Remaining / Boundary

- Parent task_state = `REVIEW`; Human Acceptance = `NOT PERFORMED`; main integration =
  `NOT PERFORMED`; I03/I04/I05 = `NOT STARTED`.
- This record does not start Independent Re-Review or authorize Human Acceptance, main integration,
  activation, or Live work.

## Execution Timing

- Estimated Run Duration: `00:40:00–01:05:00`.
- Execution Started At: `2026-09-20T09:07:19.0498436+08:00` (isolated task worktree creation).
- Completed At: `2026-09-20T09:33:00.5577546+08:00`.
- Run Duration: `00:25:42`.
- Estimate Delta: `-00:14:18 vs lower bound`.
