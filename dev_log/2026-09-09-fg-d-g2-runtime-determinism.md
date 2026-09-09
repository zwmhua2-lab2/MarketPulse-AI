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

No human Acceptance was claimed and `main` was not changed. Repository truth correction: the
initial FG-D implementation was committed as `6388eac4ebed56f112b35276b576c9d63c9a56bd`, and
Acceptance Fix #1 was committed as `cd43be75b175645b62763fcb58938ac7bd7cf7b3`.

## Evidence

- `E:\Temp\marketpulse-fg-d\g5-4.txt`
- `E:\Temp\marketpulse-fg-d\backend-full-final.txt`

## Acceptance Fix #1 — Bounded Trade Dedupe & Missing Acceptance Evidence

### Review Result / Boundary

Independent review marked the original FG-D `CHANGES_REQUIRED / NOT ACCEPTED`: F10 was an
unbounded `set`; F07/F09/F11 production looked correct but lacked prescribed evidence. This fix
changes only F10 production code. F07/F09/F11 production semantics remain frozen.

### F10 — Bounded FIFO Cache

- `ScannerPipeline.trade_dedupe_capacity` defaults to `8192`, globally per Pipeline instance.
- Identity remains `(exchange, instrument_id, market_type, trade_id)`.
- The cache uses FIFO arrival order. A duplicate hit returns `[]`, clears
  `last_detected_events`, and does not refresh FIFO position or mutate Rolling, BTC returns,
  lifecycle, EventRuntime, repository, or `last_features`.
- New identity insertion happens only after successful frame completion. At capacity, the oldest
  distinct identity is evicted; an evicted identity is intentionally processed as new input.
- No database table, configuration source, Redis, schema, migration, scheduler, or F07/F09/F11
  production change was added.

### F07 Acceptance Evidence

`test_f07_normalization_trace_is_hash_seed_independent_in_subprocesses` starts independent
`sys.executable` processes at `PYTHONHASHSEED=1`, `2`, and `777`. Each real Pipeline creates three
active lifecycle types and processes one empty-detector frame. The canonical JSON includes required
normalized event types/IDs, timeline IDs, transition IDs/to-states, and state versions.

All three SHA-256 values are identical:

| Seed | Canonical JSON SHA-256 |
| --- | --- |
| 1 | `84e50a9fb5832f117d2529e454b14895d4bb020bb85751d07de32c5857c5e5f6` |
| 2 | `84e50a9fb5832f117d2529e454b14895d4bb020bb85751d07de32c5857c5e5f6` |
| 777 | `84e50a9fb5832f117d2529e454b14895d4bb020bb85751d07de32c5857c5e5f6` |

### F09 Acceptance Evidence

Real Pipeline/Runtime paths establish both `IDLE → DETECTED → WATCHING` and
`IDLE → DETECTED → SETUP`; no test calls `state_manager.expire()` directly. Evidence covers TTL
deadline from committed event time plus configured TTL, equality expiry, one-microsecond-before
non-expiry, durable event/timeline/transition/state/cooldown facts, and two fresh ReplayClock runs
with identical TTL IDs/times/state versions/final state.

### F11 Acceptance Evidence

Evidence covers injected raise then retry versus a clean deterministic runtime (full canonical
SymbolState/MarketEvent/Timeline/Transition/Candidate equality), a true durable duplicate through
a fresh Runtime over the same repository, and two concurrent same-ID callers sharing one failed
persist attempt. The checks prove no speculative state/version/dedupe/in-flight/repository facts
remain before retry and that retry persists exactly once. Existing same-symbol priority serialization
continues to pass.

### Cross-Finding Regression

Two fresh deterministic runs execute `Trade A → activation → Trade B → duplicate A → exact TTL
boundary → valid Trade C`. They prove duplicate A leaves Rolling and durable facts unchanged, TTL
runs first exactly once, C processes from the expired state without a double version increment, and
the final Rolling/repository/state truth is identical across runs.

### Verification

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q` → `24 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` → `148 passed, 1 warning`.
  The warning is the existing FastAPI/Starlette TestClient/httpx deprecation.
- `py -3.14 -m ruff check backend/src backend/tests scripts` → PASS.
- `py -3.14 -m compileall -q backend/src backend/tests` → PASS.
- `git diff --check` → PASS.

### Result

`FG-D ACCEPTANCE FIX #1 COMPLETE — WAITING ACCEPTANCE`.

No human Acceptance was claimed, no merge to `main` occurred, and branch history remains pending
review.

### Fix #1 Evidence

- `E:\Temp\marketpulse-fg-d-fix1\backend-full-final.txt`

## Acceptance Fix #2 — Close Final F10 Evidence

### Boundary

This tests/docs-only fix adds the final F10 acceptance evidence. Production source, including
`backend/src`, is unchanged from Fix #1. F07, F09, F11, F10 cache semantics, and the G5 canonical
replay contract remain frozen. No schema or migration changed.

### Real Scanner Business Equivalence

`test_f10_real_scanner_duplicate_trade_is_business_equivalent_to_omission` uses fresh, independent
`RollingFeatureEngine`, `OpportunityScanner`, `ScannerPipeline`, `EventRuntime`, and
`InMemoryG2Repository` instances for each run; it does not stub `scanner.scan`.

- Run A processes `Trade A → duplicate Trade A → Trade B`.
- Run B processes `Trade A → Trade B`.
- At the duplicate frame, the test asserts `[]`, `last_detected_events == ()`, unchanged persisted
  MarketEvents/SignalTimeline/StateTransitions/StrategyCandidates/SymbolState, and unchanged
  committed rolling trades.
- The final `FeatureSnapshot`, rolling trades, repository business truth, SymbolState, and
  state version are equal between the independent runs.

### Replay Duplicate Evidence

`test_replay_duplicate_trade_is_business_equivalent_to_omission` uses the formal
`ReplayG2Runner` path with fresh runner/runtime/repository instances.

- Source A is `Trade A → duplicate Trade A → Trade B`; Source B is `Trade A → Trade B`.
- The duplicate ReplayFrame has no detected event IDs and no trace events, proving it adds no
  MarketEvent, Timeline, StateTransition, or StrategyCandidate.
- Final canonical G2 repository business truth, final SymbolState/state version, and the canonical
  business-event ID sequence are equal. Raw frame count and input ordinals are intentionally not
  compared.

### Verification

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q` → `25 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_1_replay.py -q` → `10 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_2_trading_replay.py -q` → `7 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_3_determinism.py -q` → `5 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group5_4_evaluation.py -q` → `10 passed`.
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` → `150 passed, 1 warning`.
  The warning is the existing FastAPI/Starlette TestClient/httpx deprecation.
- `py -3.14 -m ruff check backend/src backend/tests scripts` → PASS.
- `py -3.14 -m compileall -q backend/src backend/tests` → PASS.
- `git diff --check` → PASS.
- `git diff cd43be75b175645b62763fcb58938ac7bd7cf7b3 -- backend/src` → EMPTY.
- No schema/migration diff exists relative to Fix #1; Alembic was not rerun because no production
  source or migration changed.

### Result

`FG-D ACCEPTANCE FIX #2 COMPLETE — WAITING ACCEPTANCE`.

No human Acceptance was claimed, no merge to `main` occurred, and FG-E was not started.

### Fix #2 Evidence

- `E:\Temp\marketpulse-fg-d-fix2\g5-4.txt`
- `E:\Temp\marketpulse-fg-d-fix2\backend-full.txt`
