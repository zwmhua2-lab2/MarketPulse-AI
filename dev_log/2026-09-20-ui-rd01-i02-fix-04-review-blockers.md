# UI-RD01-I02-FIX-04｜Opportunity Read Re-Review Blockers

## Result

`UI-RD01-I02-FIX-04 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`.

Parent `UI-RD01-I02 task_state = REVIEW`. Human Acceptance and main integration remain
`NOT PERFORMED`. This task does not start I03, I04, I05, Real AI, Gate, or Live.

## Finding Closure

| Finding | Result | Evidence |
| --- | --- | --- |
| `RR3-P2-01` | CLOSED | Primary body failures retain their original API semantics even when transaction/session cleanup has a source failure; both cleanup exits are attempted. |
| `RR3-P2-02` | CLOSED | Auth and refused-connection probes derive structurally from the effective task-owned `PRIMARY_URL`; no fixed credentials or `54134`/`54135` port dependency remains. |

## RR3-P2-01 — Cleanup Precedence

- `_source_transaction()` now treats an already-raised body exception as primary. It attempts
  transaction exit and session exit independently, logs cleanup failures internally, then
  re-raises the original exception identity. It does not broadly swallow success-path cleanup
  errors: a transaction/session exit failure after successful body execution remains
  `SOURCE_UNAVAILABLE`.
- C1 Product `RuntimeError` + healthy cleanup => sanitized `500`.
- C2 Product `RuntimeError` + cleanup source failure => sanitized `500`.
- C3 Product `TimeoutError` / `OSError` + cleanup source failure => sanitized `500`.
- C4 `SnapshotIntegrityError` + healthy cleanup => `503 SNAPSHOT_FAILED`.
- C5 `SnapshotIntegrityError` + cleanup source failure => `503 SNAPSHOT_FAILED`.
- C6 primary `_OpportunitySourceUnavailableError` + cleanup failure =>
  `503 SOURCE_UNAVAILABLE`.
- C7 successful body + cleanup-only source failure => `503 SOURCE_UNAVAILABLE`.
- C8 `asyncio.CancelledError` + transaction/session cleanup failures preserves cancellation; both
  exits are recorded as attempted.
- A real PostgreSQL `pg_terminate_backend()` case terminates the active source connection before
  a `RuntimeError`; the original runtime error is preserved, the internal cleanup-failure log is
  emitted, and an immediate independent writer completes.

## RR3-P2-02 — Environment-Independent Source Probes

- `_asyncpg_url()` parses effective `PRIMARY_URL` with SQLAlchemy `make_url`, changes only the
  requested structural component, and renders an asyncpg-compatible URL without logging a
  password.
- The auth probe replaces only the parsed password with an invalid test value and asserts that
  the effective rendered URL differs before attempting the real PostgreSQL connection.
- The refused probe binds `127.0.0.1:0`, keeps the returned endpoint reserved without listening,
  substitutes only that port in the parsed source URL, and closes the socket in its context exit.
- Final environment: task-owned PostgreSQL on `127.0.0.1:54755`, database `marketpulse`, with a
  non-default local test role/password. The probe itself selects a new ephemeral refused port.
  Process `DATABASE_URL` was unset for pytest and `PYTHONPATH=backend/src` was used.

## Verification

- Alembic isolated source: `current = heads = 20260913_0009`.
- Focused `backend/tests/test_product_opportunities.py`: `18 passed`, `5 warnings`, exit `0`.
- Required targeted backend set: `171 passed`, `20 warnings`, `105.89s`, exit `0`.
- Full `backend/tests`: `761 passed`, `0 failed`, `0 errors`, `0 skipped`, `20 warnings`,
  `745.64s`, exit `0`.
- Ruff on modified source/tests, `compileall`, and `git diff --check`: pass.
- OpenAPI drift: pass; frontend typecheck: pass; frontend test run: `7 files / 57 tests` pass;
  frontend production build: pass.
- Existing warnings are FastAPI/Starlette TestClient and deprecated 422 constants; no new warning
  category was introduced by this change.

## Scope / Boundary

- Modified production: `backend/src/marketpulse/api/product/opportunities.py` only.
- Modified tests: `backend/tests/test_product_opportunities.py` only.
- No schema, migration, index, DTO/cursor contract, aggregation/folding implementation, forward
  logic, attribution writer, RuntimeHost, frozen requirements/design, `DECISIONS.md`, or
  PRE-01B change.
- F1, F2, F3, F4 original classification, F5, R1, R2, R4, I02-A, stable snapshot, CR-03, and
  CR-05 remain covered by the targeted/full regressions; no acceptance claim is made.

## Execution Timing

- Estimated Run Duration: `00:30:00–00:55:00`.
- Execution Started At: `NOT RECORDED RELIABLY`.
- Verification Completed At: `2026-09-20T19:43:07.9608378+08:00`.
- End-to-end wall-clock duration: `NOT VERIFIED` (the executor did not capture a reliable
  start timestamp); individual focused/targeted/full durations are recorded above.
- Estimate Delta: `NOT VERIFIED`.
