# FG-E — Reconciliation Snapshot Consistency

## Task

- Date: 2026-09-09
- Branch: `fix/fg-e-reconciliation-snapshot-consistency`
- Task Base / Accepted Main: `5388e848d5396f232f05818ac53add3b511e7d2d`
- Scope: N02 only — make all database facts in one G4 Reconciliation Report come from one coherent PostgreSQL snapshot.
- Out of Scope: schema/migration, execution accounting redesign, Control/Recovery semantics or transaction boundaries, Repair Engine, automatic repair, Risk Gate, Position Protection, G2 Runtime, N01, G6, Redis/Kafka/Celery, and global isolation changes.

## Root Cause

Before this change, `g4.reconciliation.reconcile()` called `execution.reconciliation()` with its own G3 session and then opened another G4 session. PostgreSQL `READ COMMITTED` could produce different snapshots for those sessions and for each statement within them.

## Changes

- `PaperExecutionService.reconciliation()` now accepts an optional caller-owned session. Standalone use opens a read-only `REPEATABLE READ` transaction; G4 can supply its encompassing session.
- `g4.reconciliation.reconcile()` opens one read-only `REPEATABLE READ` transaction, passes that session to G3 accounting reconciliation, and reads G4 plans/orders/positions/trades/accounts/runtime-control in the same snapshot.
- Added a real PostgreSQL concurrent regression: after the G3 portion has read its snapshot, a separate transaction commits `ACTIVE → REPLACED` for the referenced plan. The in-flight report remains the coherent pre-commit report; a fresh report sees the committed invalid plan/order relationship.
- No schema, migration, DB lock graph, SystemControlService / RecoveryManager boundary, Control/Recovery behavior, or G3 accounting calculation changed.

## Verification

- `py -3.14 -m pytest tests/test_group4.py -q -k 'reconciliation_uses_one_repeatable_read_snapshot_across_g3_and_g4' -ra` → `1 passed, 73 deselected`.
- `py -3.14 -m pytest tests/test_group3.py -q -ra` → `12 passed`.
- `py -3.14 -m pytest tests/test_group4.py -q -ra` → `74 passed in 65.37s`.
- `py -3.14 -m pytest tests -q -ra` → `151 passed, 1 warning in 169.12s`; warning is existing FastAPI/Starlette TestClient deprecation.
- `py -3.14 -m ruff check src tests` → PASS.
- `py -3.14 -m compileall -q src tests` → PASS.
- `alembic current` / `alembic heads` → `20260905_0004 (head)` / `20260905_0004 (head)`.
- `git diff --check` → PASS (Windows LF→CRLF informational warnings only).

## Status

`IMPLEMENTED / WAITING REVIEW` — no human Acceptance was claimed and `main` was not updated.
