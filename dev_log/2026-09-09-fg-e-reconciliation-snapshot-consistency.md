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

### Account / Order Torn-Read Race

- A normal production path creates one OPEN LIMIT BUY with `Account.reserved_cash = Order.reserved_cash = X`.
- The test pauses the actual G3 accounting path immediately before its first `PaperOrderRecord` query, after the account query completed.
- A separate real PostgreSQL writer transaction commits `Account.reserved_cash = 0`, `Order.status = CANCELLED`, and zeroed order reservations. The report task remains incomplete until the paused order query is released.
- The in-flight report remains coherent T0: `open_orders = 1`, `open_buys = 1`, `reserved_cash_matches_open_buys = True`, and no `reserved_cash_mismatch` diagnostic. A fresh report is coherent T1: zero open orders/buys and the same invariant remains true. Fresh durable DB reads confirm zero account reservation and the cancelled order.
- Verification: `py -3.14 -m pytest tests/test_group4.py -q -k 'reconciliation_account_order_cancellation_race_uses_one_snapshot' -ra` → `1 passed, 74 deselected`; G4 regression → `75 passed in 66.60s`.

### Current Status

`CHANGES_REQUIRED / NOT ACCEPTED` — Acceptance Fix #2 has now closed G4→G3 transaction identity and account/order torn-read evidence. Standalone G3 RR/RO, standalone G3 torn-read race, true durable corruption detection, and failure cleanup evidence remain pending their acceptance contracts. `main` was not updated.

## Acceptance Fix #2 — Standalone G3 Remaining Evidence (B/C/D/E)

### Scope

- Tests and evidence documentation only. No file under `backend/src` was modified.
- Each test invokes `PaperExecutionService.reconciliation(RunMode.REPLAY)` without a caller-supplied session and uses real PostgreSQL transactions. Concurrency is controlled with `asyncio.Event`; the writer uses a distinct `AsyncSession` and commits before the paused read is released.

### Evidence Added

- **B — real owned transaction state:** immediately inside the production standalone reconciliation callback, `SHOW transaction_isolation` and `SHOW transaction_read_only` return `repeatable read` and `on`. The captured session identity is the owned session factory result, and its transaction is closed when that session exits.
- **C — account/order torn-read race:** a normal OPEN LIMIT BUY first establishes matching account/order cash reservations. Reconciliation pauses after its account read and before the order read; a distinct writer commits account reservation release and cancellation/zeroed order reservations. The in-flight report stays incomplete while the writer is already committed, then remains a coherent pre-commit snapshot with no `reserved_cash_mismatch`. A fresh report is coherent after the commit, and fresh durable reads confirm the cancellation and zero reservations.
- **D — true durable corruption:** a writer changes only `Account.reserved_cash`, leaving the OPEN order reservation durable. A new standalone report returns `ok=False`, `reserved_cash_matches_open_buys=False`, and `reserved_cash_mismatch`; fresh DB reads prove the mismatch is durable and reconciliation did not repair it.
- **E — failure cleanup:** after a real read, an injected exception leaves the standalone-owned transaction inactive and the session non-transactional at context exit. A subsequent independent reconciliation succeeds.
- All monkey-patched test seams are restored in `finally`.

### Verification

- `py -3.14 -m pytest tests/test_group3.py -q -k 'standalone_reconciliation' -ra` → `4 passed, 12 deselected in 2.76s`.
- `py -3.14 -m pytest tests/test_group3.py -q -ra` → `16 passed in 15.23s`.
- `py -3.14 -m pytest tests/test_group4.py -q -ra` → `75 passed in 66.44s`.
- `py -3.14 -m pytest tests -q -ra` → `156 passed, 1 warning in 171.36s`; the warning is the existing FastAPI/Starlette `TestClient` deprecation.
- `py -3.14 -m ruff check src tests`, `py -3.14 -m compileall -q src tests`, and `git diff --check` → PASS.
- `py -3.14 -m alembic current` and `py -3.14 -m alembic heads` → `20260905_0004 (head)`.

### Status

`CHANGES_REQUIRED / NOT ACCEPTED` — Acceptance Fix #1 closed only real G4 transaction-state evidence. Acceptance Fix #2 now supplies the remaining G4 identity/account-order and standalone G3 B/C/D/E evidence, but no human or independent reviewer Acceptance is claimed. `main` was not updated.

## Acceptance Fix #3 — Final N02 Evidence

### Scope

- Tests and evidence documentation only. No `backend/src`, schema, migration, Runtime, Control, or Recovery source was modified.
- The tests use the production `g4.reconciliation.reconcile()` path through `Harness.reconcile()` and distinct real PostgreSQL sessions for writers.

### G4 Durable Corruption Propagation

- A legal OPEN LIMIT BUY establishes `Account.reserved_cash = Order.reserved_cash = X`, `X > 0`; its baseline G4 report is `ok=True` with `reserved_cash_matches_open_buys=True`.
- A separate committed PostgreSQL transaction changes only `Account.reserved_cash` to `X + 1.0`. Fresh reads confirm the order remains OPEN with reservation `X`, and the difference is greater than reconciliation tolerance.
- A fresh production G4 report is `ok=False`; both its top-level and nested `details["g3"]` reserved-cash invariant are false and diagnostics contain `reserved_cash_mismatch`.
- Fresh DB reads after that report still show the mismatch, proving G4 remains detector-only and performs no repair.

### G4 Failure Cleanup and Immediate Writer

- A legal OPEN LIMIT BUY baseline report passes. The test captures the real G4 caller-owned transaction immediately before G3, confirms `SHOW transaction_isolation = repeatable read` and `SHOW transaction_read_only = on`, then lets the original G3 account read complete.
- The test-only `_reconciliation_once` seam raises `RuntimeError("injected g4 reconciliation failure")` immediately before the original G3 order read. The caller receives that exception and all seams are restored in `finally`.
- After the exception returns, direct lifecycle checks prove `session.in_transaction() is False` and the captured transaction is inactive.
- Without restarting or recreating the Harness, service, database, engine, or session factory, an independent PostgreSQL writer atomically cancels the order and releases account/order reservations under `asyncio.wait_for(..., timeout=2)`.
- Fresh DB reads confirm T1 cancellation and zero reservations. A fresh G4 reconciliation on the same Harness is `ok=True`, has zero open orders/buys, preserves `reserved_cash_matches_open_buys=True`, and has no `reserved_cash_mismatch` diagnostic.

### Final N02 Evidence Matrix

| ID | Evidence | Result |
|---|---|---|
| N02-1 | G4 real REPEATABLE READ | PASS |
| N02-2 | G4 real READ ONLY | PASS |
| N02-3 | G4 → G3 same session | PASS |
| N02-4 | G4 → G3 same transaction | PASS |
| N02-5 | plan ACTIVE → REPLACED snapshot | PASS |
| N02-6 | G4 account/order torn-read | PASS |
| N02-7 | G4 writer non-blocking | PASS |
| N02-8 | fresh G4 report sees T1 | PASS |
| N02-9 | standalone G3 real REPEATABLE READ | PASS |
| N02-10 | standalone G3 real READ ONLY | PASS |
| N02-11 | standalone G3 account/order race | PASS |
| N02-12 | standalone G3 writer non-blocking | PASS |
| N02-13 | durable corruption remains detected | PASS |
| N02-14 | G4 failure cleanup and immediate writer | PASS |

### Verification

- `py -3.14 -m pytest tests/test_group4.py -q -k 'g4_reconciliation_propagates_durable_reserved_cash_corruption or g4_reconciliation_failure_cleans_outer_transaction_for_immediate_writer' -ra` → `2 passed, 75 deselected in 3.30s`.
- `py -3.14 -m pytest tests/test_group3.py -q -ra` → `16 passed in 20.41s`.
- `py -3.14 -m pytest tests/test_group4.py -q -ra` → `77 passed in 88.64s`.
- `py -3.14 -m pytest tests/test_group5_1_replay.py -q -ra` → `10 passed in 1.11s`.
- `py -3.14 -m pytest tests/test_group5_2_trading_replay.py -q -ra` → `7 passed in 23.93s`.
- `py -3.14 -m pytest tests/test_group5_3_determinism.py -q -ra` → `5 passed in 19.14s`.
- `py -3.14 -m pytest tests/test_group5_4_evaluation.py -q -ra` → `10 passed in 66.43s`.
- `py -3.14 -m pytest tests -q -ra` → `158 passed, 1 warning in 211.59s`; the warning is the existing FastAPI/Starlette `TestClient` deprecation.
- `py -3.14 -m ruff check src tests` and `py -3.14 -m compileall -q src tests` → PASS.
- `py -3.14 -m alembic current` and `py -3.14 -m alembic heads` → `20260905_0004 (head)`.

### Status

`FG-E ACCEPTANCE FIX #3 COMPLETE — WAITING ACCEPTANCE` — all N02-1～N02-14 evidence is recorded, but no human or independent reviewer Acceptance is claimed. `main` was not updated.

## Final Acceptance Closeout

### Human Acceptance

- Human decision: `CONFIRMED ACCEPT FG-E`.
- Accepted implementation: `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`.
- Accepted scope: N02 — Reconciliation Snapshot Consistency. N02-1～N02-14 evidence is accepted as recorded above.

### Closeout Record

- This closeout changes documentation only; it does not alter FG-E production behavior, schema, migrations, or transaction semantics.
- Before closeout, `origin/main` was `5388e848d5396f232f05818ac53add3b511e7d2d`; it is an ancestor of the accepted FG-E implementation.
- The accepted FG-E lineage is fast-forwarded to `main`. The FG-E branch is retained as historical acceptance evidence.

### Final Status

`FG-E ACCEPTED / COMPLETE` — Human Acceptance confirmed. Future work remains subject to separate approval; N01 and G6 are not started.
