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

## Acceptance Fix #1 — Complete N02 Snapshot Evidence

### Formal Review Input

- Formal Review result: `CHANGES_REQUIRED / NOT ACCEPTED`.
- Production implementation was assessed as correct, but Review identified multiple incomplete evidence categories. Acceptance Fix #1 was scoped to the real production G4 → G3 `REPEATABLE READ` / `READ ONLY` transaction-state gap only.

### Scope and Change

- Tests and documentation only. No production source was modified.
- The existing real PostgreSQL concurrent snapshot regression now intercepts the actual `g4.reconciliation.reconcile()` call to `execution.reconciliation(..., session=session)`.
- Before it invokes the original G3 reconciliation using that exact session, it runs `SHOW transaction_isolation` and `SHOW transaction_read_only` through the supplied session and asserts `("repeatable read", "on")`.
- The existing concurrent `ACTIVE → REPLACED` plan-commit proof remains: the in-flight report retains the coherent pre-commit snapshot, and a fresh report observes the committed invalid plan/order relationship.

### Verification

- Targeted state evidence: `py -3.14 -m pytest tests/test_group4.py -q -k 'reconciliation_uses_one_repeatable_read_snapshot_across_g3_and_g4' -ra` → `1 passed, 73 deselected`.
- G4 regression: `py -3.14 -m pytest tests/test_group4.py -q -ra` → `74 passed in 69.41s`.
- Full backend: `py -3.14 -m pytest tests -q -ra` → `151 passed, 1 warning in 186.46s`; warning is existing FastAPI/Starlette TestClient deprecation.
- `py -3.14 -m ruff check tests/test_group4.py` and `py -3.14 -m compileall -q tests` → PASS.

### Status

`IMPLEMENTED / WAITING REVIEW` — Formal Review remains `CHANGES_REQUIRED / NOT ACCEPTED` until a reviewer accepts this evidence. `main` was not updated.

## Acceptance Fix #2 — Remaining N02 Evidence

### Corrected Review State

- Acceptance Fix #1 closed only the real G4 transaction-state evidence gap.
- Remaining acceptance evidence after Fix #1: account/order torn-read race; standalone G3 RR/RO; standalone G3 torn-read race; true durable corruption detection; transaction identity and failure cleanup evidence.

### Explicit G4 → G3 Transaction Identity Evidence

- The real G4 supplied session records `id(session)` and `id(session.get_transaction())` immediately before invoking G3 reconciliation.
- The production `PaperExecutionService.reconciliation()` path is then allowed to call its actual `_reconciliation_once()` implementation; that method records the same two identities from the session it actually receives.
- The test asserts the two identity tuples are identical, in addition to the existing `SHOW transaction_isolation = repeatable read`, `SHOW transaction_read_only = on`, and concurrent plan-race snapshot assertions.
- Test seams are restored in `finally`, including when the concurrent report path raises.

### Verification

- Targeted identity evidence: `py -3.14 -m pytest tests/test_group4.py -q -k 'reconciliation_uses_one_repeatable_read_snapshot_across_g3_and_g4' -ra` → `1 passed, 73 deselected`.
- G4 regression: `py -3.14 -m pytest tests/test_group4.py -q -ra` → `74 passed in 70.78s`.
- `py -3.14 -m ruff check tests/test_group4.py`, `py -3.14 -m compileall -q tests`, and `git diff --check` → PASS.

### Status

`CHANGES_REQUIRED / NOT ACCEPTED` — this Fix closes G4→G3 same-transaction identity evidence only. Remaining N02 evidence needs an explicit acceptance contract before new tests are added; `main` was not updated.
