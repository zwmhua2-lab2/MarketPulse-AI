# UI-RD01-I02-FIX-03｜Opportunity Read Re-Review Final Blockers

## Result

`UI-RD01-I02-FIX-03 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`.

Parent `UI-RD01-I02 task_state = REVIEW`. Human Acceptance and main integration are
`NOT PERFORMED`. This task does not start Independent Re-Review, Human Acceptance, I03, I04,
or I05.

## Scope

- Closed only `RR2-P1-01 / F1` and `RR2-P2-01 / F4`.
- Production change: `backend/src/marketpulse/api/product/opportunities.py`.
- Regression change: `backend/tests/test_product_opportunities.py`.
- No schema, migration, index, DTO contract, cursor contract, aggregation/folding implementation,
  Forward logic, attribution writer, RuntimeHost, `DECISIONS.md`, frozen requirement/design, or
  PRE-01B change.

## Finding Closure

### RR2-P1-01 / F1 — Logical Root Query Authority

- A rooted Opportunity is selected only by its revision-1 `detected_at`; range and descending
  cursor predicates are applied to that root before its complete chain is loaded.
- A non-revision-1 row is a malformed sentinel only when a correlated `NOT EXISTS` confirms that
  no revision-1 row exists for the same `opportunity_id`.
- Therefore a later correction cannot make a rooted Opportunity enter a range or cross a cursor.
  When a root is relevant, all revisions still load and corruption fails closed as
  `503 SNAPSHOT_FAILED`.
- Regressions cover root outside/later inside, cursor root outside/later inside, root inside/later
  corrupt outside, a truly rootless malformed chain, legal Forward-to-Replay canonical projection,
  and the existing provenance-heavy pagination coverage.

### RR2-P2-01 / F4 — Source Error Boundary

- Source classification now occurs at the Opportunity-local durable-source transaction and actual
  source awaits (`_begin_snapshot`, `scalars`, `get`, and source context enter/exit), not around
  the whole collection/trace Product execution path.
- SQLAlchemy source errors, asyncpg connection/auth errors, `TimeoutError`, and `OSError` retain
  `503 SOURCE_UNAVAILABLE` only when raised by those source operations.
- Product DTO mapping after successful materialization is outside that boundary: injected
  `TimeoutError("product-timeout-secret")` and `OSError("product-oserror-secret")` both return
  sanitized `500` with correlation ID. No injected secret is returned.
- Both endpoints retain the source timeout, invalid-password, connection-refused, SQLAlchemy
  source failure, `SnapshotIntegrityError`, mapper runtime-error, and sanitization controls.

## Verification

- Environment: task-owned PostgreSQL `marketpulse-ui-rd01-i02-fix03-pg` on `127.0.0.1:54134`;
  worktree-local ignored `.env`; process `DATABASE_URL` unset; `PYTHONPATH=backend/src`.
- Alembic disposable URL: `current = heads = 20260913_0009`.
- Focused opportunities regression: `14 passed, 5 warnings in 26.54s`, exit `0`.
- Required targeted backend regression:
  `backend/tests/test_product_opportunities.py`, `test_product_market_scanner.py`,
  `test_product_system.py`, `test_runtime_host.py`, and
  `test_se_02d_aggregation_snapshot.py` => `167 passed, 20 warnings in 104.81s`, exit `0`.
- Full backend: `PYTHONPATH=backend/src; py -3.14 -m pytest -q backend/tests` =>
  `757 passed, 0 failed, 0 errors, 0 skipped, 20 warnings in 797.26s`, exit `0`.
- Ruff on modified source/test and `compileall`: pass.
- OpenAPI generate and drift: pass; `frontend/src/api/generated.ts` has no content change.
  Frontend typecheck: pass; `test:run`: `7 files / 57 tests` pass; build: pass.
- `git diff --check`: pass before documentation sync. Fresh remote verification before delivery is
  required and performed during final Git gate.

## State / Remaining Boundary

- F2, F3, F5, R1, R2, R4, I02-A, stable snapshot, CR-03, and CR-05 are preserved by the
  targeted and full regression gates; this task does not redesign I02.
- `I03/I04/I05 = NOT STARTED`; Real AI, Gate, Live, and PRE-01B state are unchanged.
- Independent Re-Review and Human Acceptance remain required. No acceptance claim is made here.

## Execution Timing

- Estimated Run Duration: `00:25:00–00:45:00`.
- Execution Started At: `2026-09-20T14:06:08.2011837+08:00`.
- Completed At: `2026-09-20T14:35:46.7019257+08:00`.
- Run Duration: `00:29:38`.
- Estimate Delta: `-00:15:22 vs upper bound`.
