# FG-C — Safety Recovery Validity

## Task

FG-C closes three safety-authority / durable-state / protection-validity defects:

- F04 — Emergency authority: the emergency latch must not be bypassed by Pause / Resume.
- F05 — Durable Safe Mode: SAFE_MODE must survive a crash at any point in recovery.
- C01 — Protection Plan Validity: Recovery / Resume / Protection must share one open-position
  protection-plan validity contract.

## Requirement

The three findings form one minimal, complete safety-acceptance unit
(`Emergency authority + Durable Safe Mode + Protection Plan Validity`) that must close together.

## Scope

- `backend/src/marketpulse/g4/control.py`
- `backend/src/marketpulse/g4/recovery.py`
- `backend/src/marketpulse/g4/protection.py`
- `backend/tests/test_group4.py`
- `PROJECT_STATE.md`
- This dev log

## Out of Scope

F07/F09/F10/F11 (FG-D), N02 (FG-E), F03/F06 redesign, N01 Continuous Runtime,
N03 Real AI Provider, G2 Event UoW, reconciliation snapshot redesign, execution accounting
redesign, Redis/Kafka/Celery/worker infra, Live/Contract/Short, UI, strategy changes,
auto Close All, Emergency Stop semantics redesign, and schema/migration remain unchanged.

## Repository Truth

- Accepted Main / Task Base: `8d4e8305088485095df241fb41111980179f6105` (verified against live
  `origin/main` at preflight).
- Fix branch: `fix/fg-c-safety-recovery-validity`.
- Isolated worktree: `E:\Documents\MarketPulse AI.fg-c-safety-recovery-validity`.
- FG-A / FG-B are both ancestors of the base (`a9c2cd6` / `1c292b2`), confirming the base already
  contains the accepted G3 execution-authority and protection-concurrency fixes.
- No migration or schema change.

## Root Cause F04

`SystemControlService.pause()` did not inspect `operator_state`. It transitioned straight to
`PAUSED / PAUSED`, so an operator `pause()` issued while in `EMERGENCY_STOP` silently downgraded
the emergency latch. A subsequent `resume()` only checks `operator_state == EMERGENCY_STOP`, which
is now `PAUSED`, so the resume gate passed and the runtime returned to `RUNNING` — bypassing the
emergency authority entirely. `resume()` already refused under emergency; `pause()` was
asymmetric and did not.

## Root Cause F05

`RecoveryManager.recover()` read the pre-restart `system_state` into an in-memory variable, then
immediately persisted transient `STARTING` and `RECOVERING` transitions that overwrote a durable
`SAFE_MODE`. A single recovery attempt still landed in `SAFE_MODE` (because the in-memory
`pre_system_state` still held the old value), but if the process crashed after `RECOVERING` was
persisted, the next recovery read `system_state == RECOVERING` and lost the `SAFE_MODE` latch,
silently promoting to a non-safe final state.

## Root Cause C01

`PositionProtectionService.evaluate()` and `_close_position_in()` loaded the active plan with
`load_active_plan()` (uniqueness + payload parse + identity only), while the resume / safe-mode
gate used `load_valid_long_active_plan()` (which additionally enforces the shared business
validity contract: valid entry zone, finite SL/TP, `stop_loss < take_profit`). A protection path
could therefore trust an invalid plan (e.g. `stop_loss >= take_profit`) that the resume gate would
reject as unprotected, so the two paths disagreed on whether an OPEN LONG was protected.

## Implementation

- `control.py::pause()` now refuses when `operator_state == EMERGENCY_STOP`, returning
  `emergency_stop_requires_recovery`, symmetric with `resume()`. Only `emergency_recovery()` clears
  the emergency latch.
- `recovery.py::recover()` latches `SAFE_MODE` into the durable `RuntimeControlRecord.payload`
  (`safe_mode_latch`) before any transient transition, and normalizes the in-memory pre-state so
  `_final_state()` still sees `SAFE_MODE`. The latch is read back on any later recovery attempt,
  so a crash after `STARTING` / `RECOVERING` cannot erase it.
- `control.py::safe_mode_recovery()` removes the `safe_mode_latch` payload key when it
  successfully clears `SAFE_MODE`, so a later recovery does not wrongly re-latch.
- `protection.py::evaluate()` and `_close_position_in()` now use
  `load_valid_long_active_plan(session, run_mode, instrument_id, now=now)`, unifying protection
  with the resume gate's valid-plan contract.

## Business Behavior

Emergency authority, the SAFE_MODE durability guarantee, and the protection-plan validity contract
now agree across recovery / resume / protection. Risk-reducing exits, SL/TP trigger semantics,
plan replacement, and reconciliation behavior are unchanged. No accounting or schema semantics
changed.

## Tests

- New `test_fg_c_pause_refused_under_emergency_stop` proves pause is refused under emergency and
  the latch stays `EMERGENCY_STOP`; resume remains blocked.
- New `test_fg_c_safe_mode_survives_recovery_crash_and_second_recovery` persists `SAFE_MODE`, runs
  one recovery, overwrites the durable state to `RECOVERING` (simulated crash), then runs a second
  recovery and asserts it still lands in `SAFE_MODE`.
- New `test_fg_c_protection_fails_closed_on_invalid_protection_plan` opens a LONG whose active plan
  has `stop_loss >= take_profit` and asserts protection treats it as `POSITION_UNPROTECTED`
  instead of triggering an exit from an untrusted plan.

## Regression

- G4 targeted: `61 passed` (58 existing + 3 new).
- G3 targeted: `12 passed`.
- G5-1 `9 passed`; G5-2 `7 passed`; G5-3 `5 passed`; G5-4 `10 passed` (run serially; the G5 suites
  share one primary PostgreSQL database and must not run concurrently with G3/G4).
- `ruff check` on all changed files: PASS.
- `compileall -q backend/src backend/tests`: PASS.
- `git diff --check`: PASS.
- Alembic `current` / `heads`: both `20260905_0004 (head)`; no migration added.

## Result

FG-C IMPLEMENTED / WAITING REVIEW

## Remaining

Human acceptance review. No merge to `main` until Acceptance PASS.

## Known Risks

The `safe_mode_latch` lives in the existing JSON `payload` column (no schema change). It is
cleared only on a successful `safe_mode_recovery()`; `emergency_recovery()` does not touch it, and
`recover()` re-latches whenever it sees `system_state == SAFE_MODE` or a present latch, which is
idempotent.

## Evidence

- `pytest backend/tests/test_group4.py -q` → `61 passed`.
- `pytest backend/tests/test_group3.py -q` → `12 passed`.
- `pytest backend/tests/test_group5_1_replay.py ... test_group5_4_evaluation.py -q` → `31 passed`.
- `ruff check` / `compileall` / `git diff --check` / Alembic current+heads → PASS (see above).
