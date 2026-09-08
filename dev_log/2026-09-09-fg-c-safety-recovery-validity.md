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
- `backend/src/marketpulse/g4/planning.py`
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

## Acceptance Fix #1 — Review Correction

Independent Acceptance Review ruled FG-C = `CHANGES_REQUIRED / NOT ACCEPTED`:

- F04 = PASS (no further change).
- F05 = design correct, but required deterministic crash-boundary evidence (completed below).
- C01 = FAIL / BLOCKER: the canonical contract did not yet settle the SymbolStateStore
  state-version relationship.

The first Acceptance Fix #1 draft added:

```
current SymbolStateStore.state_version == plan.state_version
```

as an open-position protection-plan validity condition. **This requirement is revoked.**

Real G2→G3→G4 evidence proved that `SymbolStateStore.state_version` advances under normal market
evolution after a plan is created (measured `plan=3, store=4`). Strict equality therefore disabled
SL/TP protection on every position once the symbol state advanced — breaking the G5-2 stop exit,
G5-3 CLOSED/STOP_LOSS, and G5-4 evaluation suites — and violated the Accepted Safety Semantics
that risk-reducing protection must remain continuously effective.

### Final Authority Boundary

- **`state_version` freshness** remains a *risk-increasing* authority only: BUY / ADD, pending
  risk-increasing orders, fill-time revalidation, recovery order revalidation, stale proposal
  authority, and `block_symbol` invalidation of risk-increasing authority. The existing
  `recovery.py::_plan_issues()` `state_version_stale` order-revalidation semantics are preserved.
- **Open Position Protection Validity** must NOT depend on `state_version`. The canonical
  protection contract shared by recovery / resume / protection is:

  1. exactly one ACTIVE plan
  2. durable row / serialized payload identity agree
  3. run_mode / instrument scope agree
  4. TTL valid
  5. entry zone finite / valid
  6. stop_loss finite
  7. take_profit finite
  8. stop_loss < take_profit
  9. TradePlan schema / business validation PASS

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
- `planning.py::load_valid_long_active_plan()` documents the canonical protection contract (9
  conditions, no state-version equality). The temporary SymbolStateStore strict-equality check
  added in the rejected draft is removed.

## Business Behavior

Emergency authority, the SAFE_MODE durability guarantee, and the protection-plan validity contract
now agree across recovery / resume / protection. `SymbolStateStore.state_version` is treated as a
risk-increasing freshness authority only; normal symbol-state version advancement never invalidates
an open position's SL/TP protection. Risk-reducing exits, SL/TP trigger semantics, plan
replacement, and reconciliation behavior are unchanged. No accounting or schema semantics changed.

## Tests

### F04 (preserved)

- `test_fg_c_pause_refused_under_emergency_stop` — pause refused under emergency, resume blocked,
  latch stays `EMERGENCY_STOP`.

### F05 Crash-Boundary Matrix (6 cases, real durable interruption via monkeypatched transition)

Each case runs the real `RuntimeControlRecord` / `RecoveryManager`, never just `_final_state()`.

1. `test_fg_c_f05_case1_safe_mode_persisted_restart_lands_safe_mode` — SAFE_MODE persisted →
   restart → still SAFE_MODE.
2. `test_fg_c_f05_case2_crash_after_latch_before_starting` — latch durable commit → injected crash
   before STARTING → fresh manager → SAFE_MODE.
3. `test_fg_c_f05_case3_crash_after_starting` — STARTING durable commit → crash → fresh → SAFE_MODE.
4. `test_fg_c_f05_case4_crash_after_recovering` — RECOVERING durable commit → crash → fresh →
   SAFE_MODE.
5. `test_fg_c_f05_case5_successful_recovery_lands_safe_mode_then_restart` — successful recovery
   lands SAFE_MODE → restart → still SAFE_MODE.
6. `test_fg_c_f05_case6_safe_mode_recovery_clears_latch_no_stale_relatch` — `safe_mode_recovery()`
   → PAUSED → latch cleared → restart does NOT re-latch from stale payload.

### C01 Matrix (8 cases, real PostgreSQL durable rows)

Three-way conclusion (Recovery / Resume / Protection) verified per case:

- A `test_fg_c_c01_case_a_valid_all_three_valid` — valid plan → all VALID.
- B `test_fg_c_c01_case_b_expired_all_three_invalid` — expired → all INVALID.
- C `test_fg_c_c01_case_c_corrupt_payload_identity_all_three_invalid` — corrupt payload identity →
  all INVALID.
- D `test_fg_c_c01_case_d_invalid_entry_zone_all_three_invalid` — invalid entry zone → all INVALID.
- E `test_fg_c_c01_case_e_invalid_stop_take_profit_all_three_invalid` — invalid SL/TP → all INVALID.
- F `test_fg_c_c01_case_f_no_active_plan_fail_closed` — no unique ACTIVE plan → all fail closed.
- G `test_fg_c_c01_case_g_natural_state_version_advance_still_valid` — natural SymbolStateStore
  version advancement (plan=7, store=8) → protection still VALID, resume gate still VALID, recovery
  does NOT land POSITION_UNPROTECTED.
- H `test_fg_c_c01_case_h_stale_risk_increasing_buy_rejected` — stale risk-increasing BUY authority
  (plan=7, store=8) still cancelled by recovery order revalidation, while the open position's
  protection stays valid. This is a separate contract, not merged into protection validity.

`test_symbol_block_blocks_only_that_symbol` retains its original semantics: SOL BUY/ADD blocked,
BTC unaffected, SOL protection/SL still allowed.

## Acceptance Fix #2 — Remaining Verification Gaps

### Review Findings and Exact Correction

1. **C01 Case G did not keep the position OPEN for all three authorities.** Its prior
   below-stop BBO intentionally triggered SL before Resume and fresh-manager Recovery ran, so the
   latter two checks did not prove the required open-position protection lifetime contract.
   Case G now uses a fresh non-triggering BBO (`bid=99`, `ask=100`) after normal
   `SymbolStateStore.state_version` advancement (`7 -> 8`). It asserts protection returns
   `HOLD` (not `POSITION_UNPROTECTED`), the position/trade are still OPEN before Resume, Resume is
   accepted, a fresh `RecoveryManager` lands `RUNNING`, and the same position/trade remain OPEN
   afterward. The separate Case H still proves stale risk-increasing BUY cancellation.

2. **F05 Cases 2/3/4 swallowed simulated crashes without proving their boundary.** Each case now
   uses a precise `pytest.raises(RuntimeError, match=...)` assertion, so it fails if the hook is
   never reached. Before invoking fresh-manager recovery it reads the durable
   `RuntimeControlRecord` and asserts the required intermediate state and persisted
   `safe_mode_latch`.

### Final C01 Matrix

| Case | Durable condition | Protection | Resume | Fresh Recovery | OPEN position proof |
| --- | --- | --- | --- | --- | --- |
| A | valid ACTIVE plan | HOLD | accepted | RUNNING | valid-path contract |
| B | expired plan | fail closed | refused | non-RUNNING | not applicable |
| C | corrupt payload identity | fail closed | refused | non-RUNNING | not applicable |
| D | invalid entry zone | fail closed | refused | non-RUNNING | not applicable |
| E | invalid `stop_loss/take_profit` | fail closed | refused | non-RUNNING | not applicable |
| F | no valid ACTIVE plan | fail closed | refused | non-RUNNING | not applicable |
| G | normal store `state_version 7 -> 8` | HOLD | accepted | RUNNING | asserted before Resume and after Recovery |
| H | stale risk-increasing BUY (`7 -> 8`) | protection remains valid | not the authority under test | RUNNING | stale BUY cancelled; existing OPEN position retained |

### Final F05 Crash-Boundary Matrix

| Case | Asserted injected boundary | Durable state before fresh recovery | Fresh recovery |
| --- | --- | --- | --- |
| 1 | persisted SAFE_MODE restart | SAFE_MODE | SAFE_MODE |
| 2 | after `safe_mode_latch`, before STARTING | `system_state=SAFE_MODE`, `safe_mode_latch=true` | SAFE_MODE |
| 3 | after STARTING commit | `system_state=STARTING`, `safe_mode_latch=true` | SAFE_MODE |
| 4 | after RECOVERING commit | `system_state=RECOVERING`, `safe_mode_latch=true` | SAFE_MODE |
| 5 | successful SAFE_MODE recovery restart | SAFE_MODE | SAFE_MODE |
| 6 | successful `safe_mode_recovery()` | latch absent after PAUSED transition | no stale re-latch |

No production authority, schema, migration, F07/F09/F10/F11/N02, FG-D, or G5 behavior changed.

## Regression

- FG-C targeted: `15 passed` (1 F04 + 6 F05 + 8 C01).
- G4 full: `73 passed`.
- G3: `12 passed`.
- G5-1/G5-2/G5-3/G5-4 (serial): `31 passed`.
- Full backend: `133 passed, 1 warning` (pre-existing FastAPI/Starlette deprecation).
- `ruff check backend/src backend/tests scripts`: PASS.
- `compileall`: PASS.
- `git diff --check`: PASS.
- Alembic `current` / `heads`: both `20260905_0004 (head)`; no migration.

## Result

FG-C ACCEPTED / COMPLETE

## Remaining

No implementation or Acceptance Fix remains. FG-D / FG-E = `NOT STARTED`.

## Known Risks

The `safe_mode_latch` lives in the existing JSON `payload` column (no schema change). It is
cleared only on a successful `safe_mode_recovery()`; `emergency_recovery()` does not touch it, and
`recover()` re-latches whenever it sees `system_state == SAFE_MODE` or a present latch, which is
idempotent.

## Evidence

- `pytest backend/tests/test_group4.py -q` → `73 passed`.
- `pytest backend/tests/test_group3.py -q` → `12 passed`.
- `pytest backend/tests/test_group5_1_replay.py ... test_group5_4_evaluation.py -q` → `31 passed`.
- `pytest backend/tests -q` → `133 passed, 1 warning`.
- `ruff check backend/src backend/tests scripts` → `All checks passed!`.
- `py -3.14 -m compileall -q backend/src` → PASS.
- `git diff --check` → PASS (Git emitted only the existing LF-to-CRLF working-copy warning).
- `cd backend; PYTHONPATH=src; py -3.14 -m alembic current` / `heads` → both
  `20260905_0004 (head)`.

## Final Acceptance Record

- Formal acceptance: FG-C Acceptance Fix #2 = `PASS`；F04 / F05 / C01 = `ACCEPTED / FIXED`。
- Accepted implementation: `39388acdd313d631e887a3d1786352bbee51caca`。
- Closeout Final Regression（2026-09-09，在 accepted SHA 39388ac 的隔离 worktree 重跑）：
  FG-C targeted `15 passed`；full backend `133 passed`（closeout 重跑 `2 warnings`，既有
  FastAPI/Starlette deprecation，数量随收集环境在 1–2 间波动）；ruff、`compileall`、
  `git diff --check` PASS；Alembic `current` / `heads` = `20260905_0004 (head)`。
- `main` 已 fast-forward 收编 FG-C；`fix/fg-c-safety-recovery-validity` 保留为历史证据。
