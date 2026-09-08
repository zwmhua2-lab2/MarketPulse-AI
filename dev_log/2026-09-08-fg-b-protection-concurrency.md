# FG-B — Protection Concurrency

## Task

FG-B addresses F03 (same-symbol protective BBO blocked by slow AI re-evaluation) and F06
(G4/G3 risk-reducing settlement lock-order inversion).

## Requirement

- Protection never waits for AI.
- A symbol has at most one active AI re-evaluation authority; BBO burst traffic must not create
  queued or detached AI tasks.
- Slow responses remain proposal-only and fail closed when their snapshot is stale.
- All G4 protection, manual-close and AI REDUCE/CLOSE paths must share G3's canonical PostgreSQL
  risk-reducing settlement order.

## Scope

- G4 `SafetyRuntime`, `PositionProtectionService`, and AI risk-reducing stale-authority locking.
- FG-B PostgreSQL concurrency regressions in `backend/tests/test_group4.py`.
- This log and the implementation status in `PROJECT_STATE.md`.

## Out of Scope

F04/F05/F07/F09/F10/F11, C01, N01/N02/N03; schema/migration; recovery/emergency redesign;
G2 changes; G5 behavior changes; provider redesign; Live/contract/short trading; middleware,
Redis, Celery, Kafka, and runtime activation.

## Repository Truth

- Accepted Main / Task Base / remote `origin/main`: `352bbb68a8b7051ea398da45b46914d5e0ad49b5`.
- FG-B branch: `fix/fg-b-protection-concurrency`.
- Isolated worktree: `E:\Documents\MarketPulse AI.fg-b-protection-concurrency`.
- Old `fix/fg-a-g3-execution-authority` worktree and its tracked/untracked state were preserved
  untouched under the explicit resume authorization.
- No migration or schema change was made.

## Root Cause F03

`SafetyRuntime.on_market_data()` held its per-symbol asyncio lock across
`await reevaluation.evaluate(...)`. Provider latency therefore prevented a later same-symbol BBO
from reaching SL/TP protection or limit-fill safety.

## Root Cause F06

G4 `_close_position_in()` locked the target `PositionRecord` before calling G3
`execute_risk_reducing_exit()`. G3 already locks `AccountRecord` and then the position set.
Two cross-symbol exits could therefore form `Position → Account` versus `Account → Position`.

## Canonical Lock Order

Risk-reducing settlement is:

`RuntimeControl (AI authority path only) → AccountRecord → PositionRecord(s) → Plan/Order/audit writes`

G3 already used `AccountRecord → PositionRecord(s)`. FG-B makes G4 protection/manual close take
the Account fence before its target Position lock. AI REDUCE/CLOSE acquires the same Account fence
before stale-authority validation locks `PositionRecord`.

## Implementation

- `SafetyRuntime` claims a per-`(run_mode, instrument_id)` in-flight AI authority while inside
  the protection serialization lock, then releases that lock before awaiting the provider.
- The initiating `on_market_data()` coroutine owns and awaits the re-evaluation; this is not a
  `create_task()` path. Later BBOs run protection/limit-fill normally and coalesce their AI work
  while authority is active. Replay therefore retains lifecycle-owned deterministic completion.
- Existing G4 post-provider stale checks remain unchanged. A close during the provider wait makes
  the frozen position lifecycle stale, so the response records `STALE_DECISION` and has no action.
- `PositionProtectionService` now acquires `AccountRecord FOR UPDATE` before `PositionRecord FOR
  UPDATE`; its test-only barrier seam is unset in production.
- G3 settlement and paper accounting semantics are unchanged.

## Files Changed

- `backend/src/marketpulse/g4/orchestrator.py`
- `backend/src/marketpulse/g4/protection.py`
- `backend/src/marketpulse/g4/reevaluation.py`
- `backend/tests/test_group4.py`
- `PROJECT_STATE.md`
- `dev_log/2026-09-08-fg-b-protection-concurrency.md`

## Business Behavior

The priority remains `Protection → Limit Fill → Reevaluation`. SL/TP still trigger from Fresh Best
Bid and settle at Best Bid minus existing slippage. AI remains advisory and stale decisions fail
closed. No economic, pause, emergency, recovery, or plan semantics changed.

## Concurrency Design

The per-symbol lock serializes only the critical BBO safety sequence. The in-flight set is claimed
under that same lock, bounding a symbol to one provider call without an unbounded task queue. The
provider wait is performed by the original caller, and `finally` always releases the authority.

## Verification

- Baseline G3+G4 before modification: `61 passed`.
- FG-B targeted real PostgreSQL concurrency tests: `6 passed`.
- G3 + G4 targeted suites: `67 passed`.
- G5-2 + G5-3 + G5-4: `22 passed` (7 + 5 + 10).
- Full backend: `115 passed, 1 warning in 143.01s`.

## PostgreSQL Evidence

The FG-B cross-symbol test holds BTC's actual `AccountRecord FOR UPDATE` with a deterministic
barrier, starts ETH protective close, proves ETH cannot complete before that account fence is
released, then proves both transactions complete within the bounded wait with both Positions and
Trades closed plus two SELL Fill/Ledger pairs. The mixed test repeats the interleaving with BTC
protection concurrent with ETH AI REDUCE.

## Exactly-once Evidence

Slow-AI SL asserts exactly one SELL Order, Fill, Ledger and CLOSE PositionEvent; the slow response
is persisted as `STALE_DECISION`. Concurrent same-symbol SL/TP BBOs produce exactly one SELL Fill,
zero final position quantity, and a reconciled account. Existing duplicate-protection coverage
also remains in G4 regression.

## Replay Regression

No background task is created. The initiating caller awaits the provider and replay invokes that
caller per BBO, so no re-evaluation can outlive Replay's event lifecycle. G5-2/G5-3/G5-4 all pass.

## Self-Check

- No schema/Alembic revision change.
- No G3 accounting mutation or lock-order weakening.
- `ruff check backend/src backend/tests scripts`: PASS.
- `compileall -q backend/src backend/tests`: PASS.
- `git diff --check`: PASS (Windows LF→CRLF warnings only; exit 0).
- Alembic `current` / `heads`: both `20260905_0004 (head)`.
- No protected FG-A worktree contents were modified.

## Result

FG-B IMPLEMENTATION COMPLETE — WAITING ACCEPTANCE

## Remaining

Human / independent source acceptance and branch push remain required. FG-C is not started.

## Known Risks

The account-first settlement fence serializes risk-reducing exits within an account by design. This
is the required deadlock-safety tradeoff; no throughput redesign was introduced.

## Context For Next AI

Review `SafetyRuntime`'s lock release before the caller-owned provider await, the in-flight claim
and `finally` release, and the Account-before-Position order in both G4 protection and AI
REDUCE/CLOSE stale authority. Confirm test barriers exercise actual PostgreSQL row locks.

## Evidence

- `E:\Temp\marketpulse-fg-b\fg-b-targeted-rerun.txt`
- `E:\Temp\marketpulse-fg-b\g3-g4-after.txt`
- `E:\Temp\marketpulse-fg-b\g5-after.txt`
- `E:\Temp\marketpulse-fg-b\backend-full-after.txt`

## Acceptance Fix #1 — Order / Account Lock Consistency

### Account ↔ Order Root Cause

The original FG-B account-first protection fence made `_close_position_in()` acquire
`AccountRecord → PositionRecord`, then cancel pending BUYs through G3 `cancel_order()`.
That cancellation locks `PaperOrderRecord → AccountRecord`; meanwhile G3 limit-fill uses
`RuntimeControl → Order → Plan → Account → Positions`. A protective close and concurrent Cancel
or Limit Fill could therefore form `Account → Order` against `Order → Account`.

### Final Canonical Lock Order

`RuntimeControl` (AI authority only) → risk-increasing `PaperOrderRecord` rows ordered by
`created_at, order_id` → active Plan (AI authority stale check only) → `AccountRecord` →
`PositionRecord(s)` → cancellation / settlement audit writes.

Protection locks all cancellable same-symbol OPEN BUYs before Account, passes that durable locked
set to cancellation, then calls unchanged G3 risk-reducing settlement. AI REDUCE/CLOSE acquires
the same order set before its Account/Position stale-authority locks. G3 Cancel and LIMIT fill
already start from Order, so no G3 transaction-architecture change was required.

### Protection vs Cancel Evidence

Real PostgreSQL barrier test holds Protection after it has locked the pending BUY Order, starts a
concurrent `cancel_order()`, proves Cancel waits on Order, then releases both. The BUY is
`CANCELLED` exactly once, reservation is zero once, and one protective SELL Fill/Ledger/closed
Trade remains with reconciliation PASS.

### Protection vs Limit Fill Evidence

Real PostgreSQL barrier test overlaps SL protection with the actual G3 `process_open_orders()`
LIMIT-fill path while the BUY is price-eligible. Limit fill waits on the same Order; after
Protection cancels it, no stale BUY Fill occurs and the closed Position is not reopened.

### AI REDUCE/CLOSE Evidence

The AI CLOSE caller-owned transaction claims the pending BUY Order before Account. A concurrent
Cancel waits on that Order, then the AI close completes once, cancels the BUY once, and leaves the
Position flat with reconciliation PASS. Existing mixed Protection/AI REDUCE coverage remains in
the FG-B suite.

### Acceptance Fix #1 Verification

- FG-B concurrency tests: `10 passed`.
- G1–G4: PASS (included in full backend).
- G5-1: `9 passed`; G5-2: `7 passed`; G5-3: `5 passed`; G5-4: `10 passed`.
- Full backend: `118 passed, 1 warning` (existing FastAPI/Starlette TestClient deprecation).

### Known Risk

The canonical order intentionally serializes conflicting risk-reducing exit/cancellation work on
the same pending BUY Order and Account. This is a deadlock-safety fence, not a throughput redesign.

### Acceptance Fix #1 Result

FG-B ACCEPTANCE FIX #1 COMPLETE — WAITING ACCEPTANCE
