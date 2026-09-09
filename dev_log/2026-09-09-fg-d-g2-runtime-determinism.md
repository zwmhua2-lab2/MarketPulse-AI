# FG-D — G2 Runtime Determinism & Failure Atomicity

## Task

Close one G2 runtime-correctness batch:

- F07 — lifecycle normalization order must not depend on set iteration.
- F09 — `SymbolStateManager.expire()` must be reached and durably persisted by runtime input.
- F10 — duplicate `NormalizedTrade` must not mutate Rolling state before dedupe.
- F11 — EventRuntime state/dedupe memory must not commit before persistence succeeds.

## Repository Truth

- Accepted Main / Task Base: `4859c8f70a484353d598f80fc2e0c2658cc50864`.
- Branch: `fix/fg-d-g2-runtime-determinism`.
- Isolated clean worktree: `E:\Documents\MarketPulse AI.fg-d-g2-runtime-determinism`.
- `origin/main` was fetched and verified at the Task Base before worktree creation.
- The original `E:\Documents\MarketPulse AI` unborn/staged workspace was not modified.

## Scope

- Modified only G2 runtime/state-machine/timeline/rolling code, G2 tests, and required state
  records.
- No schema or migration, G2 scanner/strategy business semantics, G3/G4, G5 canonical replay
  contract, background scheduler, Event UoW redesign, provider, Live, UI, or external service
  state change.

## Implementation

### F07 — Stable lifecycle normalization

`ScannerPipeline.ingest()` now sorts active lifecycle types absent from the current detector output
by `EventType.value` before creating normalization events. The order no longer inherits Python set
iteration and therefore remains stable in replay traces and durable timelines.

### F09 — Input-driven TTL reachability

`EventRuntime.expire()` runs under the existing per-instrument lock and uses a prepare/persist/
commit flow. `ScannerPipeline.ingest()` invokes it using the existing injected Clock before current
scanner processing. A TTL expiry creates the existing G2 event, timeline, state transition, and
observation atomically through the existing repository. No background task or scheduler was added.

### F10 — NormalizedTrade dedupe before Rolling

`ScannerPipeline` keys a normalized trade by exchange, instrument, market type, and trade ID before
Rolling ingestion. Its Rolling update is performed on an isolated working copy and committed only
when the input finishes successfully, so a duplicate trade cannot grow the rolling window.

### F11 — Persistence-first EventRuntime commit

`SymbolStateManager` now supports prepare/commit transitions. EventRuntime builds state, timeline,
and candidate facts from a copy, persists them through the existing repository boundary, and commits
in-memory state only after `persist()` returns true. The durable-rejection path returns no
transition and leaves state/dedupe uncommitted. In-flight same-ID publishers share the same future;
the durable dedupe set is updated only after success and is cleared on failure for a retry.

`SignalLifecycle` likewise has preview/commit operations so pipeline lifecycle memory is not
advanced when its runtime publish fails.

## Tests Added

- Stable lifecycle normalization order by `EventType.value`.
- Runtime-reachable TTL creates persisted `g2.state_ttl` event/timeline/transition and reaches IDLE.
- Duplicate `NormalizedTrade` leaves its Rolling trade deque at one item.
- Injected persistence exception leaves EventRuntime IDLE/not-deduped and permits a successful retry.
- `persist() -> False` leaves EventRuntime IDLE/not-deduped, returns no transition, and permits a
  successful retry.
- Concurrent same-ID publishers share one failing persistence attempt, then a later retry persists.

## Verification

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q` → `15 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_1_replay.py -q` → `9 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_2_trading_replay.py -q` → `7 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_3_determinism.py -q` → `5 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_4_evaluation.py -q` → `10 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` → `139 passed, 1 warning`.
  The warning is the existing FastAPI/Starlette TestClient/httpx deprecation.
- `py -3.14 -m ruff check backend/src/marketpulse/g2 backend/tests/test_group2.py` → PASS.
- `py -3.14 -m compileall -q backend/src backend/tests` → PASS.

## Result

`IMPLEMENTED / WAITING REVIEW`.

No human Acceptance was claimed, no commit was created, and `main` was not changed.

## Evidence

- `E:\Temp\marketpulse-fg-d\g5-4.txt`
- `E:\Temp\marketpulse-fg-d\backend-full-final.txt`
