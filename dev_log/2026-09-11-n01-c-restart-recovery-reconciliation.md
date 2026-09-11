# N01-C — Restart / Recovery / Reconciliation

## Result

`N01-C = ACCEPTED / COMPLETE`。

本批仅新增 deterministic validation，未修改 production code、schema、migration、Runtime Host 或 provider。它不构成 N01 overall acceptance，亦不进入 N01-6/7/8、Integrated Runtime Host 或 G6。

## Repository Truth

- Task Base / verified `main` / `origin/main` / `origin refs/heads/main`：`6cc4c36e11c380f638872598e4766a4436d0d255`。
- Isolated worktree：`E:\Documents\MarketPulse-AI-n01-c`。
- Branch：`n01-c-restart-recovery-reconciliation`。
- Pre-existing dirty worktree `E:\Documents\MarketPulse AI` 未 reset / clean / stash / restore / overwrite。

## Changes

- `backend/tests/test_n01_restart_recovery.py`
  - parent test creates and migrates one disposable real PostgreSQL database per scenario;
  - Process A and Process B use `subprocess.Popen` to create two fresh Python processes;
  - only database URL and named deterministic scenario cross the boundary; no Harness, ORM object, health registry, runtime cache or quote object is transferred;
  - child engines use `NullPool`, dispose before exit, and parent checks zero client sessions / zero idle-in-transaction before database drop.
- `PROJECT_STATE.md`、`AI_CONTEXT.md`：minimal N01-C status synchronization only.

## Process Boundary and Durable Continuity

The final focused run recorded the following independently reaped child pairs (both exit code `0`):

| scenario | Process A PID | Process B PID |
|---|---:|---:|
| healthy | 8876 | 13040 |
| invalid_buy | 21196 | 3064 |
| stop | 22720 | 16824 |
| safe_mode | 16780 | 5168 |
| paused | 11940 | 7228 |
| bbo_failure | 23900 | 13744 |

For every scenario, Process A committed a `LIVE_PAPER` BTC-USDT account, LONG position, active plan and a heartbeat at `2026-09-11T11:55:00+00:00`, then exited. Process B constructed fresh engine/session/services from PostgreSQL and asserted its pre-recovery economic snapshot exactly equals Process A's committed snapshot.

## Recovery Evidence

- `EXECUTION_GAP` uses the durable Process A heartbeat; recovery time is Process B's controlled time, downtime exceeds the 10-second threshold, active risk includes BTC-USDT position (and pending BUY where present).
- Recovery invokes the formal `reconcile()` path. Its before/after snapshots are identical at the reconciliation boundary, proving detector-only behavior; the production function sets `REPEATABLE READ, READ ONLY`.
- Healthy recovered BUY remains `OPEN` without a restart-generated Fill. Invalid recovered BUY (fresh Process B ask outside entry zone) is cancelled with reservation released; no Fill/Ledger is fabricated.
- HOLD restoration keeps the position open. Stop breach uses Process B deterministic fresh BBO `79/80`; durable SELL Fill is `79 * (1 - 5 / 10000) = 78.9605`, proving current-BBO execution rather than a historical downtime stop-price Fill.
- Durable `SAFE_MODE` remains `SAFE_MODE` and cancels the risk-increasing pending BUY without filling it. Durable `PAUSED` operator intent remains `PAUSED`; current reconciliation semantics sees transient `RECOVERING` plus PAUSED intent as inconsistent and therefore fails closed to `SAFE_MODE`, never `RUNNING`.
- BBO-provider failure creates `CORE_DATA_STALE` and lands `DATA_DEGRADED`, not `RUNNING`, with no fabricated Fill.
- A second recovery of every same durable state has unchanged economic counts (orders, fills, positions, trades, accounts, ledger).

## PostgreSQL Resource Cleanup

Every disposable `marketpulse_n01_c_*` database was migrated with Alembic, observed after both child processes exited, required to have zero client sessions and zero `idle in transaction`, then dropped. Final leftover count was `0`.

## Verification

All commands used `PYTHONPATH=backend/src` and `py -3.14` from this isolated worktree.

| Gate | Result |
|---|---|
| N01-C cross-process test | `6 passed` (final evidence run: 47.19s) |
| N01-A lifecycle | `6 passed` |
| N01-B focused | `4 passed` |
| G2 | `30 passed` |
| G3 | `16 passed` |
| full backend run 1 | `179 passed, 1 warning` (255.18s) |
| full backend run 2 | `179 passed, 1 warning` (244.11s) |
| Ruff | PASS |
| compileall | PASS |
| `git diff --check` | PASS |

Full-suite exclusivity was checked before and during both accepted runs: no foreign pytest writer and no foreign client backend on the shared `marketpulse` database. A prior N01-B focused run that observed another active disposable N01-B database, and a G4-only run with pre-existing shared REPLAY residue, were marked invalid environment evidence and not used for any conclusion; both final full runs passed under restored exclusivity.

## Claim Boundary

`Production Code Changed = NO`.

This is restart/recovery/reconciliation validation only. It does not claim 15-minute, 2-hour, 12-hour, Continuous Runtime, Integrated Runtime Host, real AI, Live Trading, private OKX, or soak acceptance.

## Final Acceptance Closeout

- Independent Review = `PASS / READY FOR HUMAN ACCEPTANCE`。
- Human Acceptance = `CONFIRMED`。
- Final Gate preflight reconfirmed reviewed branch HEAD =
  `fba8b8a11893cc875bfe08b7e16c3c965d827df8` with no review-head drift; local `main`,
  `origin/main`, and `refs/heads/main` were all Task Base
  `6cc4c36e11c380f638872598e4766a4436d0d255` before fast-forward integration.
- Final Gate re-executed under exclusive PostgreSQL-writer evidence: N01-C `6 passed` (47.65s),
  N01-A lifecycle `6 passed`, N01-B `4 passed`, G2 `30 passed`, G3 `16 passed`, G4 `77 passed`,
  full backend `179 passed, 1 warning` (303.59s), Ruff / compileall / worktree-and-range
  `git diff --check` PASS. The single warning is the existing FastAPI/Starlette TestClient deprecation.
- Resource closeout rechecked: Process A/B child processes = 0, owned PostgreSQL client sessions = 0,
  `idle in transaction` = 0, and disposable `marketpulse_n01_c_*` databases = 0.
- Production boundary rechecked relative to Acceptance Base: `backend/src` diff = empty;
  `backend/alembic` diff = empty; `Production Code Changed = NO`.
- Decision: `N01-C = ACCEPTED / COMPLETE`; `N01 overall = NOT ACCEPTED`.
  `N01-6 = NOT STARTED`; `N01-7 = NOT STARTED`; `N01-8 = NOT STARTED`; Integrated Runtime Host =
  `NOT STARTED`. This closeout does not authorize or begin any of them.

## Recommendation

`ACCEPTED / COMPLETE` — fast-forward-only integration to `main` is authorized by this closeout.
