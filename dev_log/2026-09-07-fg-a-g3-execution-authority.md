# 2026-09-07 FG-A — G3 Execution Authority & Freshness

## Task

FG-A fixes the G3 OPEN LIMIT final settlement qualification boundary:

- F01 — Cancel / Fill stale ORM authority.
- F02 — Clock / BBO captured before database lock waits.

## Requirement

Only a still-valid, current and durable OPEN LIMIT order may settle. PostgreSQL Order/Plan,
Reservation, action-time market facts, state/capacity and settlement must form one final
legality boundary.

## Scope

- `PaperExecutionService` OPEN LIMIT processing and direct final-qualification helpers.
- The direct G4 orchestrator call site, so runtime does not pass its candidate-time clock into
  settlement.
- Real PostgreSQL G3 regressions for F01/F02.
- This dev log and the minimum branch-state record required by repository policy.

## Out of Scope

F03–F11, C01, N01–N04, schema/migration, G2 runtime correctness, G4 protection architecture,
Emergency/Safe Mode, reconciliation repair, providers, continuous runtime, G6, Live trading and
all external exchange/private API work remain unchanged.

## Preflight

- Accepted base: `36401b26478a9892dc2ca0490f5c21ff24663636`.
- `HEAD`, local `main`, and live `origin/main` were all that SHA before branch creation.
- Fix branch: `fix/fg-a-g3-execution-authority`.
- Pre-existing untracked protected items only: `.workbuddy/` and `scripts/_g54_selfreview.py`.
- Alembic `current` / `heads`: `20260905_0004 (head)`; no migration added.

## Root Cause F01

`_process_open_order()` first loaded an unlocked preview in an SQLAlchemy Session, then issued
`SELECT ... FOR UPDATE` in that same identity map. Without an explicit refresh, the locked query
could return the already materialized pre-Cancel object, including stale `status`, reservation,
plan ID or quantity.

## Root Cause F02

`process_open_orders()` forwarded its candidate event's `now` and BBO through Order/Plan/Account/
Position lock waits to settlement. The final Plan TTL, freshness, entry/stop, price and capacity
checks could therefore use facts from before the actual mutation window.

## Implementation

- Locked Order, Plan, Account and Position reads use `populate_existing=True` with `FOR UPDATE`;
  the durable locked Order is the only mutation authority.
- Candidate BBO now only finds candidate OPEN LIMIT orders. The final path obtains current BBOs,
  state version and Clock after acquiring the existing DB lock set, then repeats Runtime Gate,
  BBO freshness/instrument, Plan/TTL/state, Entry/Stop, capacity/reservation and limit eligibility
  immediately before `_settle_order()`.
- Current BBO/state lookups are bounded to 250ms and fail closed. The execution interface is
  documented as an upstream-owned in-process latest-market-state accessor; no exchange/network
  I/O was added to the execution service.
- G4 `SafetyRuntime` no longer supplies its candidate event timestamp to `process_open_orders()`.

## Files Changed

- `backend/src/marketpulse/g3/service.py`
- `backend/src/marketpulse/g4/orchestrator.py`
- `backend/tests/test_group3.py`
- `backend/tests/test_group4.py`
- `PROJECT_STATE.md`
- `dev_log/2026-09-07-fg-a-g3-execution-authority.md`

## Transaction Boundary

The final OPEN LIMIT path stays in one PostgreSQL transaction. It retains the existing atomic
Order + Account + Position + Fill + Trade + Ledger + Outbox settlement. A Cancel that commits
before the locked Order reload is observed as `CANCELLED` and cannot enter `_settle_order()`;
Cancel and Fill each consume the reservation only on their own terminal path.

## Lock Order Before / After

| Path | Before | After |
| --- | --- | --- |
| G4 risk-increasing LIMIT Fill | `RuntimeControl → Order → Plan → Account → Positions` | unchanged |
| Cancel | `Order → Account` | unchanged |

Action-time current-state access occurs only after the above final lock set is acquired. It is a
bounded local latest-state lookup (250ms); a timeout or failure fails closed and produces no
settlement. No unbounded external network await was introduced under a DB lock.

## Action-Time Validation Boundary

Immediately before settlement the transaction rechecks: authoritative Order OPEN identity,
Runtime Gate, action Clock, executable BBO identity/tradability/`FRESH`/TTL, authoritative Plan
identity/ACTIVE/TTL, state version, BUY entry zone/stop breach, account reservation, current
capacity and locked Position authority. V1 LIMIT price semantics remain Best Ask / Best Bid and
the limit condition remains unchanged.

## Reservation Invariant

For every OPEN BUY, `Account.reserved_cash == sum(OPEN BUY.reserved_cash)`. Cancel zeros only its
locked Order reservation and decrements the locked Account once; Fill performs the same
consumption only after final qualification, in the settlement transaction. Other OPEN BUY orders
remain untouched.

## Tests

- New F01 real PostgreSQL controlled interleaving: preview → Cancel commit → locked reload;
  proves Cancel wins, zero Fill/Position/Trade/Ledger/Outbox for A, exactly-once reservation and
  independent OPEN reservation for B.
- New F02 real PostgreSQL controlled Order row-lock interleaving with `ReplayClock` and mutable
  current BBO: stale quote, plan expiry, entry exit, stop breach, and legal action-time Fill.
  The legal case asserts the Fill uses the action-time executable price, not the candidate price.

## Regression

- G3 targeted: `12 passed`.
- G4 targeted: `49 passed`.
- G5 Trading Replay: `7 passed`; G5 Determinism: `5 passed`; G5 Evaluation: `10 passed`.
- Full backend suite: `109 passed, 2 warnings` (existing FastAPI/Starlette deprecations).
- `ruff check backend/src/marketpulse/g3 backend/src/marketpulse/g4/orchestrator.py
  backend/tests/test_group3.py`: PASS.
- Repository-wide Ruff command reports only 6 pre-existing violations in protected untracked
  `scripts/_g54_selfreview.py`; this file existed before FG-A and is explicitly forbidden to
  modify, so it is recorded as Existing P2 / not repaired in this scope.
- `compileall -q backend/src backend/tests`: PASS.
- `git diff --check`: PASS (Windows LF→CRLF warnings only; exit 0).
- Alembic `current` / `heads`: both `20260905_0004 (head)`.

## Self Review

1. Locked Order uses `populate_existing=True`; preview identity state cannot authorize mutation.
2. A cancelled locked Order returns before `_settle_order()`.
3. Cancel/Fill reservation changes remain terminal-path-only and transactional.
4. Account-wide reservation isolation is covered by real PostgreSQL regression and reconciliation.
5. Final qualification uses action-time BBO/Clock/state, not caller candidate facts.
6. Runtime gate, Plan TTL/state, Entry/Stop and capacity are all rechecked in the final lock set.
7. Existing RuntimeControl → Order → Plan → Account → Positions order is unchanged.
8. No migration, accounting semantic, G4 protection architecture or Live behavior changed.

## Result

FG-A IMPLEMENTED / WAITING REVIEW

## Remaining

Human source-level review and Acceptance remain required. This implementation does not declare
`ACCEPTED` and does not merge `main`.

## Known Risks

The bounded current-state accessor contract depends on production composition continuing to supply
the already-ingested latest local market state. A future design that requires exchange I/O at this
point needs a separately approved market-data/locking design; it must not replace this bounded
local lookup silently.

## Evidence

- `pytest backend/tests/test_group3.py -q` → `12 passed`.
- `pytest backend/tests/test_group4.py -ra` → `49 passed`.
- `pytest backend/tests/test_group5_2_trading_replay.py -ra` → `7 passed`.
- `pytest backend/tests/test_group5_3_determinism.py -ra` → `5 passed`.
- `pytest backend/tests/test_group5_4_evaluation.py -ra` → `10 passed`.
- `pytest backend/tests -ra` → `109 passed, 2 warnings in 150.32s`.

## Context For Reviewer / Next AI

Review the authoritative reload (`populate_existing=True`) and the final sequence in
`PaperExecutionService._process_open_order()`. Confirm that no candidate-time BBO/Clock reaches
`_settle_order()`, that bounded lookups remain local cache reads, and that only this FG-A scope is
present in the diff.
