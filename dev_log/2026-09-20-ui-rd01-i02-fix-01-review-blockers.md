# UI-RD01-I02-FIX-01｜Opportunity Read Review Blockers Fix

## Result

`UI-RD01-I02-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`。Parent
`UI-RD01-I02` formal task_state = `REVIEW`。本任务未开始 independent re-review，未作 Human
Acceptance 或 `ACCEPTED` 结论。

## Scope and Git Evidence

- Fix Base / immutable reviewed candidate: `9ee1fc7253555ad2d7bc3ea1be97017d0700b148` on
  `ui-rd01-i02-b-opportunity-read`.
- Fix branch: `ui-rd01-i02-fix-01-review-blockers`.
- `origin/main` pre-delivery: `e5476b46d0d84f0bb4e495e9dc806a6adaa390c7`.
- No schema, migration, index, package manifest, frozen Requirement, frozen Design, Amendment,
  `DECISIONS.md`, Edge accepted folding authority, I03–I05, PRE-01B-I2, activation, provider,
  Gate, Live, or main change.

## Finding Closure

| Finding | Closure evidence |
|---|---|
| R1 | Collection and detail fold the complete visible Evidence revision chain before source-type projection. Regression proves a legal FORWARD→REPLAY chain projects only its canonical source while preserving a Decision exact binding to its historical evidence; malformed cross-provenance chain returns `SNAPSHOT_FAILED`, not a truncated projection. |
| R2 | A durable Decision without one provable exact Evidence binding is represented by `NO_PROVABLE_RECORD`; null historical references remain non-fabricated. Non-null missing/cross-opportunity/conflicting exact bindings remain fail-closed snapshot integrity errors. |
| R3 | Session/SQLAlchemy acquisition errors return sanitized `503 SOURCE_UNAVAILABLE`; `SnapshotIntegrityError` returns `503 SNAPSHOT_FAILED`; other internal exceptions return sanitized `500` with a correlation ID. Regressions assert secret-bearing exception strings do not leak. |
| R4 | Forward trace node maturity derives its due boundary from the accepted `marketpulse.edge.forward.forward_due_at` authority for every horizon. Regression covers primitive reuse and before/equal/after boundary behavior. |

## Verification Environment Recovery

- Root cause of the prior invalid full-suite run: `backend/alembic/env.py` gives process
  `DATABASE_URL` precedence over the Alembic Config URL. A fixture-created disposable database can
  therefore remain empty while a different process-level database reaches head.
- Corrected parent process: `DATABASE_URL=None`; `PYTHONPATH=backend/src`; worktree-local ignored
  `.env` supplied `Settings().database_url = postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:54132/marketpulse`.
- Task-owned Docker PostgreSQL: host `127.0.0.1`, port `54132`, primary database `marketpulse`,
  tmpfs-only data and no shared volume.
- Programmatic primary migration: `20260913_0009 (head)`; `ai_decisions`, `decision_snapshots`,
  `trade_plans`, and `edge_opportunity_evidence` existed in that exact database.
- Disposable probe: `marketpulse_i02_fix_probe_db4a6ed27d34`, explicit Alembic URL, head
  `20260913_0009`, `ai_decisions` and `edge_opportunity_evidence` present, then task-owned probe
  dropped.

## Verification

| Command / check | Actual result |
|---|---|
| `PYTHONPATH=backend/src; DATABASE_URL` absent; `py -3.14 -m pytest -q backend/tests` | `754 passed, 20 warnings in 618.78s (0:10:18)`; exit `0`. |
| `PYTHONPATH=backend/src; DATABASE_URL` absent; targeted Opportunity/Product/RuntimeHost/SE-02D suite | `164 passed, 20 warnings in 68.49s`; exit `0`. |
| `PYTHONPATH=backend/src; py -3.14 -m ruff check` on changed source/test | `All checks passed!` |
| `npm --prefix frontend run generate:api` / `check:api-drift` / `typecheck` | pass |
| `npm --prefix frontend run test:run` | `7 files / 57 tests passed` |
| `npm --prefix frontend run build` | pass |
| `git diff --check` and allowed-path audit | pass; generated API file content diff = zero and was index-refreshed only |

## Actual Changes

- `backend/src/marketpulse/api/product/opportunities.py`
- `backend/tests/test_product_opportunities.py`
- `PROJECT_STATE.md`
- `AI_CONTEXT.md`
- this dev log

## State Boundary

- Parent task_state = `REVIEW`.
- Human Acceptance = `NOT PERFORMED`.
- main integration = `NOT PERFORMED`.
- I03/I04/I05 = `NOT STARTED`.

## Timing

- Estimated Run Duration: `00:15:00–00:30:00`.
- Execution Started At: `2026-09-20T07:21:11.9536958+08:00`.
- Verification Completed At: `2026-09-20T07:52:57.6808709+08:00`.
- Verification Duration: `00:31:45`.
- Estimate Delta: `+00:01:45 vs upper bound`.

## Remaining

Only independent re-review is pending. This record does not authorize re-review, Human Acceptance,
main integration, or any later I02/I03 work.

## Formal Task Final Timing

The existing `Verification Completed At` and `Verification Duration` fields above are a verification
checkpoint, not the Formal Task final completion timing.

- Estimated Run Duration: `00:15:00–00:30:00`.
- Execution Started At: `2026-09-20T07:21:11.9536958+08:00`.
- Completed At: `2026-09-20T07:55:19.1111016+08:00`.
- Run Duration: `00:34:07`.
- Estimate Delta: `+00:04:07 vs upper bound`.
