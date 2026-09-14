Status:
RESEARCH EVIDENCE INPUT / NOT ACCEPTED ARCHITECTURE

Source Task:
IRH-PRE-01

Source Model:
deepseek-v4.1-flash

Source Local Artifact:
E:\Temp\IRH-PRE-01-Reference-Research-Report.md

Source SHA-256: 809d2389276a66019c1cb4f6bb5186202d7d723760cdb49382a20f97d5ec4eda

Synced From Accepted Main: 1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b

Worker claims are Evidence Input and require Design / Review adjudication.

---
# IRH-PRE-01 Reference Research Report

Integrated Runtime Host — Reference Research / Repository Reality Audit / Reuse & Gap Mapping

- Task Type: READ_ONLY / AUDIT / REFERENCE RESEARCH
- Evidence Input only. **No** formal Architecture Decision. **No** Integrated Runtime Host implementation.
- Executed: 2026-09-15 (session time 2026-09-15 00:17 GMT+8)
- Evidence anchor: worktree `E:\Documents\MarketPulse-AI-n01-overall-final-closeout` @ `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` (clean)
- Tooling note (Facility, not a finding): the sandbox Git Bash lacks `grep/head/sed/wc/ls/cat/mkdir`; all file content was read via the Read/Grep tools, all git refs via `git ls-remote` / `git rev-parse`, and GitHub file content via authenticated `gh api`. This does not affect any conclusion below.

---

## Repository Truth

### Global Protocol (external, canonical)

| Item | Value | How obtained |
|---|---|---|
| Repository | `zwmhua2-lab2/ai-dev-protocol` (PRIVATE, default branch `main`) | `gh api repos/zwmhua2-lab2/ai-dev-protocol` |
| Real-time remote truth | `refs/heads/main` = `e92fcc381baaf314a6c0f5687b1353ac6c06a748` | `git ls-remote https://github.com/zwmhua2-lab2/ai-dev-protocol.git refs/heads/main` |
| Tag | `protocol-v1.0.0` | `gh api .../tags` |
| File inventory | `AI_BOOTSTRAP.md` (1583 B), `AI_DEVELOPMENT_PROTOCOL.md` (29854 B), `CHANGELOG.md` (494 B), `PROJECT_REGISTRY.md` (2152 B), `README.md` (2508 B) | `gh api .../git/trees/main?recursive=1` |

### MarketPulse (this project)

| Item | Value | How obtained |
|---|---|---|
| Repository | `zwmhua2-lab2/MarketPulse-AI` (PRIVATE, default branch `main`) | `gh api repos/zwmhua2-lab2/MarketPulse-AI` |
| Remote truth `refs/heads/main` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` | `git ls-remote origin refs/heads/main` |
| Remote `HEAD` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` | `git ls-remote origin HEAD` |
| Local `main` ref | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` | `git rev-parse main` |
| Navigation value in task card | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` | — |
| Session cwd worktree | `E:\Documents\MarketPulse AI` @ `d47313a1` on branch `prb-01-product-requirements-baseline` — **NOT main, and DIRTY** (20 modified / 5 deleted under `backend/**` + `dev_log/**`, plus untracked `.workbuddy/` and `scripts/_g54_selfreview.py`) | `git rev-parse HEAD`, `git branch --show-current`, `git status --porcelain` |
| **Evidence anchor used** | `E:\Documents\MarketPulse-AI-n01-overall-final-closeout` @ `1e7eeb2a`, `git status --porcelain` empty | `git worktree list`, Read |
| Migration head | single head `20260913_0009` (9 revisions `20260904_0001` … `20260913_0009`) | `git ls-tree HEAD backend/alembic/versions/` |

**Baseline verdict: NO `BASELINE MISMATCH`.** remote `main` == local `main` == navigation value == evidence-anchor worktree HEAD.

The session cwd was **not** used as the truth anchor. It is checked out on the historical branch `prb-01-product-requirements-baseline` (`d47313a1`) and is additionally **dirty** with pre-existing local modifications. Read it and the evidence chain would be polluted. Therefore **every** file read, grep and grep-path in this report targeted the clean `1e7eeb2a` worktree (`E:\Documents\MarketPulse-AI-n01-overall-final-closeout`); no evidence was taken from the session cwd. (This matches the known environment hazard recorded in project memory: the session cwd may sit on a stale, dirty branch.) The pre-existing dirt is **not** attributable to this task — this task performed no writes anywhere inside any repository (see Close-Out below).

---

## Global Protocol Verification

**Status: VERIFIED (real time, not from memory).**

| Check | Required by task | Actual |
|---|---|---|
| `AI_BOOTSTRAP.md` read | yes | read in full |
| `AI_DEVELOPMENT_PROTOCOL.md` read | yes | read in full (§0–§45 + Appendix A/B) |
| `PROJECT_REGISTRY.md` read | yes | read in full |
| Protocol Version | `1.0.0` | `AI_BOOTSTRAP.md` → "Protocol Version: 1.0.0"; `AI_DEVELOPMENT_PROTOCOL.md` line 3 → "Protocol Version: 1.0.0" |
| Protocol Status | `ACCEPTED` | `AI_BOOTSTRAP.md` → "Protocol Status: ACCEPTED"; protocol doc line 5-6 → "Status: ACCEPTED"; `CHANGELOG.md` → `[1.0.0] - 2026-09-14`, Status ACCEPTED, "Human Acceptance: CONFIRMED — 2026-09-14" |
| MarketPulse repository resolution | must come from registry, not memory | `PROJECT_REGISTRY.md` → `MarketPulse AI` → `zwmhua2-lab2/MarketPulse-AI` → Context Entry `AGENTS.md`（Project Overlay + 强制入口）+ `AI_CONTEXT.md` → Status `ACTIVE`. **No repository address was taken from memory.** |
| Registry confirmation evidence | — | Registry itself records the confirmation method: local `git remote -v` → `origin https://github.com/zwmhua2-lab2/MarketPulse-AI.git`; `gh repo list`; `git ls-tree --name-only HEAD` for Context Entry existence. Independently re-confirmed here: `git remote -v` and root tree listing both match. |

Additional protocol facts relevant to this task:

- The protocol is **project-agnostic by construction**: §0 forbids project-specific content; Project Overlay lives in `AGENTS.md`. The IRH decision must therefore land in the *project* overlay / `DECISIONS.md`, **not** in the global protocol.
- §13 "Ecosystem Reuse First, Build Last" and §14 "Reference First Design" are the governing rules for this exact task, and both require traceable sources.
- §38 "Research Report = Evidence Input": this report **must not** be treated as an Architecture Decision.
- §18 READ_ONLY semantics list: code / tests / docs / config / DB / Git state-refs / runtime state. Isolated runtime or temp DB would require separate explicit authorisation.
- `AI_BOOTSTRAP.md` "ChatGPT Web acknowledgement"（`靓仔`）is explicitly scoped: "该要求属于 ChatGPT 使用入口行为，**不得扩展成所有 Coding Agent 的通用输出要求**." It is therefore **not** applied to this coding-agent window.
- Fail-closed codes (§45 / bootstrap "Fail Closed"): `RULE BASELINE NOT VERIFIED` / `PROJECT CONTEXT NOT VERIFIED` / `CONTEXT INCOMPLETE` / `BASELINE MISMATCH` — **none triggered**.

---

## Current Runtime Ownership Map

Scope-of-truth: `backend/src/marketpulse/**` at `1e7eeb2a`. "Production" = importable from `marketpulse.*`; "Harness" = only reachable from `backend/tests/**` or `scripts/**`.

| Component | Source | Production / Harness | Creator | Owner | Start Boundary | Stop Boundary | Failure Boundary | Persistent State Dependency | Host Relevance |
|---|---|---|---|---|---|---|---|---|---|
| FastAPI `app` | `api/app.py:18` | Production | module import (`app = FastAPI(...)`) | module global | process import | **none defined** | none | none | **HOST TARGET**: currently has no `lifespan`, owns no runtime resource |
| `runtime_state` (`GlobalRuntimeState`) | `api/app.py:15`, `runtime.py:32-37` | Production | module import, singleton | module global | import | none | none | none | Should be the health/state surface; today **not shared** with any G4 component |
| `HealthRegistry` | `runtime.py:10-29` | Production | caller-supplied | whoever constructs it | n/a | n/a | n/a | none | The real production health object is constructed per-composition (harness/tests/replay); the app's copy is a second, disconnected one |
| `supervised_worker()` | `runtime.py:39-47` | Production (helper) | — | caller | n/a | n/a | **isolates worker exception → writes `health.set(name,"FAILED")`, does NOT cancel runtime** | none | **Strong evidence for the desired supervision semantic**: fail-isolate + report, not fail-stop. Currently unused by any composition |
| `OKXLiveProvider` | `market_data/okx_live.py:17-114` | Production | caller (`api/market.py:14,21`; harness; scripts) | caller | none (stateless object) | none | internal: `stream()` catches all `Exception`, increments `reconnects`, sleeps `reconnect_delay`, loops forever; `CancelledError` re-raised | counters `connection_attempts`, `reconnects`, `_instruments` | Host must own lifetime/cancellation; must expose `reconnects` / connection state |
| `EventRuntime` | `g2/runtime.py:79-316` | Production | caller | caller | `start()` creates N worker tasks (`g2-event-worker-{i}`) | `stop()` posts N sentinels → `queue.join()` → `gather(...)` → clears `_workers` | worker catches `Exception` → `worker_exceptions` deque (cap 128) + sets future exception; `CancelledError` propagates | none (in-memory); `_pending_capture_anchors` lives on the repository | **Host must start/stop it and observe `queue.qsize()`, `len(_inflight)`, `len(_workers)`, `len(worker_exceptions)`, `len(_dedupe)`** |
| `ScannerPipeline` | `g2/runtime.py:319-478` | Production | caller | caller | none (driven per `ingest()`) | none | exceptions propagate to the driver | in-process `_trade_dedupe` (cap 8192), `_btc_returns`, `lifecycle`, `rolling` | Driven by the Host's market-data loop; optional `forward_admission_authority` / `forward_path_recorder` are opt-in wiring |
| `OpportunityScanner` | `g2/scanner.py` | Production | caller | caller | none | none | pure function | none | Config-version source for events |
| `PostgresG2Repository` | `g2/repository.py:121-459` | Production | caller (`session_factory` injected) | caller | none | none | `CaptureAdmissionRejected` / `CaptureAdmissionOverloaded` / `CaptureAnchorOrphan` raise and fail-closed the persist transaction | PostgreSQL + in-process `_pending_capture_anchors` (cap 2048) | Host must supply and dispose the session factory; the bounded anchor dict is a P2 observation candidate |
| DB engine / session factory | `db/session.py:8-16` | Production but **UNUSED** | — | **nobody** | none | **none** | n/a | PostgreSQL | **Central gap**: `create_session_factory()` / `get_db()` are referenced nowhere else in the repo (verified by repo-wide grep). No production engine, no `dispose()` boundary, no pooled client |
| `SystemStateService` | `g4/state.py:47-215` | Production | caller | caller | none | none | n/a (DB errors propagate) | `runtime_control` row (`operator_state`, `system_state`, `runtime_version`, `heartbeat_at`) | Host must drive `ensure()` / `heartbeat()`; `heartbeat_at` is the durable liveness fact used by execution-gap detection |
| `IncidentManager` | `g4/incidents.py:17-186` | Production | caller | caller | none | none | n/a | `incidents` table; idempotent per `(type, run_mode, instrument)` | Read/written by most safety paths; `blocking()` is the admission input |
| `SystemRiskGate` | `g4/risk_gate.py` | Production | caller | caller | none | none | denies (never raises) | `runtime_control` + symbol control + plan facts | Request-scoped authority; Host must not own or bypass |
| `PositionProtectionService` | `g4/protection.py` | Production | caller | caller | none | none | per-symbol locks | `positions.protection_*` snapshot (sole protection-lifetime authority) | Invoked by `SafetyRuntime` per fresh BBO |
| `PaperExecutionService` | `g3/service.py:520+` | Production | caller, with **injected accessors** `bbo_for` / `state_version_for` | caller | none | none | fail-closed on stale BBO | ledger/orders/fills/account | **Its two accessors are the production market-data handoff that does not exist today** (see Gap Map) |
| `SafetyRuntime` | `g4/orchestrator.py:16-119` | Production | caller | caller | none (driven per `on_market_data`) | none | per-instrument `asyncio.Lock`; `_reevaluation_inflight` set; `_mark_freshness` publishes `CORE_MARKET_DATA` health | none | **The production glue** the Host must call once per normalized BBO frame |
| `PositionReevaluationService` | `g4/reevaluation.py:118+` | Production | caller | caller | none; **caller-awaited**, deliberately not a detached task (see comment at `orchestrator.py:82-83`) | none | provider timeout / error → fail-closed HOLD + `AI_REEVALUATION_FAILED` incident | snapshots / AI decisions / position events | Optionally disabled in V1 (`reevaluation_enabled=False`); Host must decide the enabling policy |
| `SystemControlService` | `g4/control.py:45-586` | Production | caller | caller | none | none | returns `ControlOutcome`, never raises | `runtime_control` + orders + incidents | Operator plane (pause/resume/emergency/safe-mode/block). Invoked by API/operator, not by a tick loop |
| `RecoveryManager` | `g4/recovery.py:52-528` | Production | caller | caller | invoked once per process start | n/a | provider failure degrades via `health.set(...)`, never crashes; reconciliation failure → SAFE_MODE latch | PostgreSQL only (explicitly "never from memory") | **This is the startup gate the Host must own**: `STARTING → RECOVERING → final_state` |
| `reconcile()` | `g4/reconciliation.py:27-257` | Production | module function | caller | n/a | n/a | n/a | one `REPEATABLE READ / READ ONLY` PostgreSQL snapshot | Detector-only. Called by recovery, resume gate, checkpoints |
| `ForwardOutcomeService` / `ForwardPathRecorder` | `edge/forward_service.py`, `edge/forward.py` | Production, opt-in via `ScannerPipeline` | caller | caller | none | none | fail-closed (`INSUFFICIENT_DATA`/`INVALID`) | edge tables + advisory xact lock | Ingress hook; already an accepted live-ingress participant |
| `UniverseProvider` / `build_live_universe` | `universe/service.py`, `market_data/universe_provider.py` | Production, API-only | request handler | FastAPI request | per-request | per-request | HTTP error | none | Request-scoped only; **not** a Host responsibility |
| `ReplayTradingRunner` composition | `g5/replay.py:526-595` | Production (offline) | `ReplayTradingRunner` | the runner's own async scope | `await runtime.start()` then per-frame loop | `finally: primary.dispose() / replay.dispose()` | deterministic | replay workspace DB | **The only production composition root that exists** — and it is a *replay* lifecycle (ReplayClock-driven, worker_count=1), not a live host. Useful as a wiring reference, not as a Host |

---

## Validation Harness vs Production Boundary

Harness inventory and classification (n01-6 → n01-7 → n01-8 lineage):

| Harness artifact | Location | Class | Why it must not become the Host |
|---|---|---|---|
| `LivePaperHarness` | `backend/tests/test_n01_okx_paper_safety.py:154+` (imported by scripts via `sys.path`) | **VALIDATION-HARNESS-ONLY** | Constructs the whole G3/G4 graph with a `DeterministicFakePositionReviewProvider`, a `RuntimeError("harness_has_no_quote:...")` `bbo_for`, `state_version_for → constant`, and a single-slot `self.quote`. A test double, not a runtime |
| `SmokeHarness` | `scripts/verify_n01_6_runtime_smoke.py:247-330` | **VALIDATION-HARNESS-ONLY** | Subclass that monkey-patches `self.execution.bbo_for = bbo_for` (`:274`) and splits plan-persist / gate-check / execute purely to produce §13 gate evidence |
| `_consume()` market consumer | `scripts/verify_n01_6_runtime_smoke.py:366+` | **VALIDATION-HARNESS-ONLY** | The only implementation of "market events → ScannerPipeline + SafetyRuntime" in the repo. Production has no equivalent |
| `_ControlledStream` | `scripts/verify_n01_7_medium_soak.py:328+` | **VALIDATION-HARNESS-ONLY** | Synthetic disconnect / STALE→FRESH injection |
| `_checkpoint`, `_final_assertions`, `_memory_condition`, `_aggregate` | `verify_n01_7_medium_soak.py:301`, `:2427`, … | **VALIDATION-HARNESS-ONLY** | Acceptance-verification logic, not runtime logic |
| `_ownership_activity`, `_wait_for_owned_client_cleanup` | `test_n01_okx_paper_safety.py` (imported at `verify_n01_6:113-115`) | **VALIDATION-HARNESS-ONLY** | PostgreSQL client-session attribution (needed because the *host* does not yet own sessions) |
| `_settle_background_tasks` | `verify_n01_6` (`:1003`) | **VALIDATION-HARNESS-ONLY** | Global `asyncio.all_tasks()` leak probe — a substitute for a real supervisor |
| Disposable DB create/drop + `alembic upgrade head` | `verify_n01_6:549-615` | **VALIDATION-HARNESS-ONLY** | Environment provisioning |
| Detached supervisor | `scripts/n01_8_detach.py`, `n01_8_detach_probe.py` | **VALIDATION-HARNESS-ONLY** | External process-launch machinery for a 12 h run across 4 fresh processes; the accepted N01-8 finding `N01-8-IR-P3-03` records that it produced no independent exit-code artifact |
| `_okx_rest_proxy()` | `verify_n01_7_runtime_soak.py` (used at `verify_n01_8:369`) | **VALIDATION-HARNESS-ONLY (environment)** | Works around a *sandbox* proxy limitation; explicitly not a product concern (cf. `N01-B-E01`) |

### Lifecycle logic in the harness that directly implies a production Host gap

**n01-6 / n01-8 open sequence** (`verify_n01_6:807-831`, `verify_n01_8:356-407`):

```
engine            = _smoke_engine(database_url)          # engine ownership
observer          = _observer_engine()                   # second engine, observation only
sessions          = async_sessionmaker(engine, expire_on_commit=False)
harness           = SmokeHarness(sessions); await harness.boot()   # state ensure + RUNNING + account bootstrap
runtime           = EventRuntime(PostgresG2Repository(sessions))
pipeline          = ScannerPipeline(OpportunityScanner(), runtime)
await runtime.start()                                     # worker tasks
stream            = provider.stream(CHANNELS)             # no host-owned cancellation token
consumer          = asyncio.create_task(_consume(stream, pipeline, harness, feed), name="…-market-consumer")
```

**n01-8 fresh-process restart sequence** (`verify_n01_8:409-459`) — the strongest single piece of evidence:

```
await harness.state_service.ensure(RUN_MODE)
# warm-up: pull real events until both instruments have a live BBO, events counted and DISCARDED
manager  = RecoveryManager(sessions, state_service, incidents, health, protection, execution,
                           _reconcile_for_recovery, clock=…, gap_threshold=10s)
recovery = await manager.recover(RUN_MODE, bbo_for=_bbo_for, now=…)
# … then and only then:  await runtime.start()   (:519)
```

⇒ Production has **no** notion of "warm-up → recovery gate → runtime start", and **no** notion of "recovery owns the RUNNING transition".

**n01-8 / n01-6 shutdown sequence** (`verify_n01_6:938-951`, `verify_n01_8:726-741`):

```
consumer.cancel(); await asyncio.gather(consumer, return_exceptions=True)
controlled.stop(); await stream.aclose()
await runtime.stop()
sampler.cancel(); await asyncio.gather(sampler, return_exceptions=True)
# then: queue_final / inflight_final / workers_final / worker_exceptions_final / worker_tasks_final probes
# then: engine.dispose(); observer.dispose()
# then: _wait_for_owned_client_cleanup(...)   → pg client_sessions == 0
```

This ordering — **stop ingress → close stream → drain/stop runtime → stop observers → dispose engines → prove zero owned PG clients** — is exactly the Host lifecycle that does not exist in production. The same ordering appears in the two `finally:` blocks (`verify_n01_6:1044-1095`, `verify_n01_8:802-820`), i.e. it is *deliberately* built twice inside validation code because there is no single owner.

**Explicitly forbidden use:** neither `LivePaperHarness` nor any `verify_n01_*` script may be promoted, subclassed, or imported as a Runtime Host. The accepted boundary already says this in-repo: `AI_CONTEXT.md:627` — "两者均**不是**产品入口，不得被当作 Runtime Host 或 Smoke 使用."

---

## Runtime Host Gap Map

### A. ALREADY PRODUCTION + ACCEPTED

All components in the Ownership Map marked "Production". Evidence: N01 overall ACCEPTED / COMPLETE (`dev_log/2026-09-14-n01-overall-final-acceptance-closeout.md`), with the Accepted Claim Boundary explicitly stated as "accepted production runtime components 在 validation harness + real PostgreSQL + real OKX public market data + Paper boundary 下通过 runtime validation".

| Item | Source symbol | Current owner | Missing boundary | Why the Host needs it |
|---|---|---|---|---|
| `EventRuntime` | `g2/runtime.py:79` | caller | start/stop owner | It has `start()`/`stop()` but nobody calls them in production |
| `ScannerPipeline` | `g2/runtime.py:319` | caller | driver | Needs a market-data pump |
| `SafetyRuntime` | `g4/orchestrator.py:16` | caller | per-frame driver | Needs the same pump, on BBO frames |
| `PostgresG2Repository` | `g2/repository.py:121` | caller | session factory supplier | Injected factory must be owned and disposed |
| `OKXLiveProvider` | `market_data/okx_live.py:17` | caller | lifetime + cancellation | Infinite generator with no owner = no shutdown |
| `RecoveryManager` | `g4/recovery.py:52` | caller | startup phase | Must run exactly once at process start |
| `SystemControlService` | `g4/control.py:45` | caller | invocation plane | Operator actions need a live target |
| `reconcile()` | `g4/reconciliation.py:27` | caller | schedule | Startup gate **and** periodic checkpoint |
| `PaperExecutionService`, `SystemRiskGate`, `PositionProtectionService`, `IncidentManager`, `SystemStateService`, `PositionReevaluationService` | see map | caller | composition | No composition exists |

### B. PRODUCTION COMPONENT / NOT INTEGRATED

| Item | Source | Evidence | Current owner | Missing boundary |
|---|---|---|---|---|
| FastAPI `app` runtime wiring | `api/app.py:1-36` | 36 lines; no `lifespan`; no `startup`/`shutdown`; imports only auth + market routers | module | whole lifecycle |
| `GlobalRuntimeState` | `api/app.py:15` | instantiated at import; health set once to `"HEALTHY"`; exposed only via `/api/v1/health` and `/api/v1/runtime` | module | it is **not** the `HealthRegistry` handed to G4 services ⇒ two disconnected health surfaces |
| DB engine / session factory | `db/session.py:8-16` | repo-wide grep: `create_session_factory` and `get_db` appear **only** in their own definition file. `get_db` is not used by any route | **nobody** | engine ownership, pool policy, `dispose()` |
| `main.py` | `main.py:1-7` | `uvicorn.run("marketpulse.api.app:app", host=…, port=…, reload=False)`; no lifespan configuration, no runtime startup | module | process entry has no runtime phase |
| `supervised_worker()` | `runtime.py:39` | defined, unused | — | the intended supervision primitive has no host to own it |
| `UniverseProvider` (for runtime use) | `api/market.py:14,21` | only used inside request handlers to build an ad-hoc provider per call | request | per-request provider construction is fine for API; the *runtime* universe/watchlist selection has no owner |

### C. VALIDATION-HARNESS-ONLY

Enumerated in the previous section. Summary of classes: harness composition (`LivePaperHarness`, `SmokeHarness`), market pump (`_consume`), perturbation (`_ControlledStream`), evidence probes (`_ownership_activity`, `_settle_background_tasks`, `_wait_for_owned_client_cleanup`, `_checkpoint`, `_memory_condition`), environment provisioning (disposable DB, detached supervisor, REST proxy shim).

### D. MISSING HOST RESPONSIBILITY

Each row: what is missing, the evidence that it is missing, and why the Host needs it.

| # | Missing responsibility | Evidence it is missing | Why the Host needs it |
|---|---|---|---|
| D1 | **Composition root** for the live graph (state service → incidents → risk gate → execution (+accessors) → protection → plans → reevaluation → safety → G2 runtime/repository → scanner pipeline → market provider) | The graph is assembled in `g5/replay.py:526-595` (replay), `test_n01_okx_paper_safety.py:160-214` (test), `test_group4.py:128-180` (test), `verify_n01_6:816-821` (script). Nothing under `api/` or `main.py` assembles any of it | Without one root, there is no single place to start, stop, or reason about the live system |
| D2 | **Engine / sessionmaker ownership + dispose boundary** | `db/session.py` is dead code; every composition builds its own engine (`verify_n01_6:808`, `g5/replay.py:480-481` with `NullPool`) | A live process must own exactly one engine, bound the pool, and dispose on shutdown (the accepted N01 evidence already asserts `pg_owned_clients_zero`) |
| D3 | **Production market-data accessors** `bbo_for(instrument_id)` → `BestBidAsk` and `state_version_for(instrument_id)` → `int` | `PaperExecutionService.__init__` requires both (`g3/service.py:523-534`); the harness supplies fakes (`test_n01_okx_paper_safety.py:169-175`: `RuntimeError` stub and constant `STATE_VERSION`); `SmokeHarness` monkey-patches `execution.bbo_for` (`verify_n01_6:274`); replay uses `ReplayMarketState().bbo_for` (`g5/replay.py:551`) | These are the latest-market-state handoff between the market feed and the execution/protection paths. Today the live value of a quote is only ever held by a harness dictionary; production has no owner of "latest BBO per instrument" |
| D4 | **Task supervision / failure policy** | `EventRuntime` records worker exceptions but never restarts a worker or fails the process (`g2/runtime.py:191-194`); `supervised_worker` (`runtime.py:39`) is unused; the harness instead probes global `asyncio.all_tasks()` (`verify_n01_6:956-960`) | "Who notices a child crash, and what happens next" is currently answered only by an external script |
| D5 | **Startup ordering incl. recovery gate and readiness** | `verify_n01_8:409-519` shows warm-up → `RecoveryManager.recover()` → `runtime.start()`. `api/app.py` has none of it; uvicorn starts serving immediately on import | Serving before recovery completes would let API/operator actions observe a non-recovered runtime |
| D6 | **Shutdown ordering** | See previous section. `api/app.py` has no shutdown; `EventRuntime.stop()` exists but is unreachable in production | Deterministic drain + zero-leak shutdown is an accepted requirement, currently satisfied only inside validation scripts |
| D7 | **Signal / process termination handling** | `main.py` uses bare `uvicorn.run(...)`; uvicorn's own `handle_exit` only sets `should_exit`, and the app's lifespan is a no-op | Without a lifespan, SIGINT/SIGTERM produce *no* runtime shutdown sequence at all |
| D8 | **Observability surface for the open P2 memory watch** | The metrics that the frozen P2 condition consumes (`rss_mb`, `absolute_elapsed_seconds`, sockets, handles, worker/queue/inflight/retention counts, PG client sessions) are collected *only* by harness sampling code (`verify_n01_6:848-897`, `verify_n01_7_medium_soak.py:2427-2462`) | The accepted closeout names the Integrated Runtime Host as the future observation boundary (see Memory P2 section) |
| D9 | **Duplicate/conflicting health ownership** | `api/app.py:16` writes `runtime_state.health`; G4 services take an injected `HealthRegistry` | Two health objects would silently diverge; admission control reads the injected one |

### E. OUT OF SCOPE (must not be pulled in by this research)

Live trading; Real AI runtime activation (`NOT STARTED / NOT ACTIVATED`); `SE-02D`; `N03`/`G6`; frontend runtime; SWAP runtime; any change to risk/safety/business semantics; any production DB schema change; `N01-9` (must not be created).

---

## External Reference Sources

All sources are traceable. "Exact module / file" is given verbatim.

### R1 — FastAPI lifespan

- Reference: FastAPI
- Official docs: `https://fastapi.tiangolo.com/advanced/events/`
- Exact section: "Lifespan Events" → "Lifespan" / "Lifespan function" / "Async Context Manager" / "Alternative Events (deprecated)" / "Technical Details" / "Sub Applications"
- Problem solved: one app-scoped startup/shutdown hook that runs *once* before requests and *once* after they finish
- Lifecycle model: `async def lifespan(app)` decorated with `@asynccontextmanager`, passed as `FastAPI(lifespan=...)`; code before `yield` = startup, after `yield` = shutdown
- Failure model: not specified in this page (covered by uvicorn's `LifespanOn`)
- Shutdown model: runs "after the application finishes handling requests"
- Dependency ownership: "very useful for setting up **resources** that you need to use for the whole app, and that are **shared** among requests, and/or that you need to **clean up** afterwards. For example, a database connection pool, or loading a shared machine learning model."
- Complexity: minimal (one function)
- License: FastAPI is MIT (unmodified use)
- Maintenance / maturity: official, first-party
- MarketPulse applicability: **high** — this is the sanctioned app-scoped resource owner. Exact quote to note: "If you provide a `lifespan` parameter, `startup` and `shutdown` event handlers will no longer be called. It's all `lifespan` or all events, not both." Also: "🚨 Keep in mind that these lifespan events (startup and shutdown) will only be executed for the main application, not for Sub Applications - Mounts."

### R2 — Starlette lifespan + lifespan state

- Reference: Starlette
- Official docs: `https://starlette.dev/lifespan/` (also linked from the FastAPI page)
- Exact sections: "Lifespan", "Lifespan State", "Accessing State", "Running lifespan in tests"
- Problem solved: app-scoped resource bring-up/tear-down plus a typed state bag shared with handlers
- Lifecycle model: `@contextlib.asynccontextmanager async def lifespan(app): async with some_async_resource(): yield {"http_client": client}`; state is yielded as a mapping
- Failure model: not stated on this page
- Shutdown model: **"The lifespan teardown will run once all connections have been closed, and any in-process background tasks have completed."** and **"Starlette will not start serving any incoming requests until the lifespan has been run."**
- Dependency ownership: the state bag; and the page explicitly recommends **"Consider using `anyio.create_task_group()` for managing asynchronous tasks."**
- State semantics: "The `state` received on the requests is a **shallow** copy of the state received on the lifespan handler." Requests read it as `request.state.x` (attribute) or `request.state["x"]` (dict, since Starlette 0.52.0)
- Complexity: minimal
- License: BSD-3-Clause (verified from `pyproject.toml` → `license = "BSD-3-Clause"`)
- Maintenance / maturity: official, first-party
- MarketPulse applicability: **high** — supplies both the `try/finally`-equivalent ordering guarantee and the "background tasks must finish before teardown" statement, plus a first-party pointer to AnyIO task groups

### R3 — Uvicorn lifespan protocol + graceful shutdown (source level)

- Reference: Uvicorn
- Sources: `https://raw.githubusercontent.com/encode/uvicorn/master/uvicorn/lifespan/on.py`; `https://raw.githubusercontent.com/encode/uvicorn/master/uvicorn/server.py`; `https://raw.githubusercontent.com/encode/uvicorn/master/uvicorn/config.py`; `https://raw.githubusercontent.com/encode/uvicorn/master/docs/settings.md`
- Exact symbols: `uvicorn.lifespan.on.LifespanOn.startup/shutdown/main/send/receive`; `uvicorn.server.Server.serve/_serve/startup/main_loop/on_tick/shutdown/_wait_tasks_to_complete/capture_signals/handle_exit`; `uvicorn.config.Config` (`lifespan`, `timeout_graceful_shutdown`); `LifespanType = Literal["auto","on","off"]`
- Problem solved: the ASGI lifespan protocol and orderly process termination
- Lifecycle model (verbatim behaviour):
  - `Server.startup()` → `await self.lifespan.startup()`; **`if self.lifespan.should_exit: sys.exit(STARTUP_FAILURE)`** — a failed startup is fatal for the process.
  - `LifespanOn.startup()` → creates a `main()` task, sends `{"type": "lifespan.startup"}`, awaits `startup_event`; on failure logs "Application startup failed. Exiting." and sets `should_exit = True`.
  - `Config.lifespan` default `"auto"`; `LIFESPAN` map: `auto`/`on` → `LifespanOn`, `off` → `LifespanOff`. Under `auto`, an app whose lifespan protocol appears unsupported is tolerated with an info log ("ASGI 'lifespan' protocol appears unsupported."); under `on` it is an error.
  - `LifespanOn.state` is a dict passed into the lifespan scope and then handed to every HTTP protocol instance as `app_state` (`Server.startup()` → `create_protocol(... app_state=self.lifespan.state ...)`).
- Shutdown model (`Server.shutdown()`, in order, verbatim): stop accepting new connections (`server.close()`); "Request shutdown on all existing connections" (`connection.shutdown()`); `await asyncio.sleep(0.1)`; `await asyncio.wait_for(self._wait_tasks_to_complete(), timeout=self.config.timeout_graceful_shutdown)`; on `TimeoutError` → "Cancel %s running task(s), timeout graceful shutdown exceeded" and cancel each remaining task; **then** `if not self.force_exit: await self.lifespan.shutdown()`.
- Failure model / signals: `HANDLED_SIGNALS = (SIGINT, SIGTERM)` plus `SIGBREAK` on win32; `capture_signals()` installs `handle_exit` and restores the previous handlers afterwards; `handle_exit` sets `should_exit = True`, and a second SIGINT sets `force_exit = True`.
- Dependency ownership: uvicorn owns the socket, connection set and background-task set (`ServerState.tasks`); the *application* owns whatever the lifespan creates.
- Complexity: already present — MarketPulse already depends on `uvicorn[standard]` and already runs through this code path
- License: BSD-3-Clause (unmodified runtime dependency; no code copying needed)
- Maintenance / maturity: official, very mature
- MarketPulse applicability: **high / already-in-effect**. Two facts matter for design: (i) `lifespan="auto"` + no app lifespan ⇒ today MarketPulse has **no** startup/shutdown hook being called at all; (ii) uvicorn's graceful shutdown waits for connections and tasks *before* the lifespan shutdown, and `timeout_graceful_shutdown` defaults to `None` (i.e. **unbounded**) — a design-relevant hazard for a 7×24 process.

### R4 — asyncio TaskGroup / Runner

- Reference: CPython standard library
- Official docs: `https://docs.python.org/3/library/asyncio-task.html` (`asyncio.TaskGroup`, `asyncio.timeout`) and `https://docs.python.org/3/library/asyncio-runner.html`
- Exact statements (TaskGroup, added 3.11): "All tasks are awaited when the context manager exits."; "The first time any of the tasks belonging to the group fails with an exception other than `asyncio.CancelledError`, **the remaining tasks in the group are cancelled**. **No further tasks can then be added to the group.**"; "Once all tasks have finished, if any tasks have failed with an exception other than `asyncio.CancelledError`, those exceptions are combined in an `ExceptionGroup` or `BaseExceptionGroup` … which is then raised."; "Task groups preserve the cancellation count reported by `asyncio.Task.cancelling()`."
- `asyncio.run` / `Runner`: "Execute *coro* in an asyncio event loop and return the result." — "taking care of managing the asyncio event loop, *finalizing asynchronous generators*, and closing the executor"; "The executor is given a timeout duration of 5 minutes to shutdown."; `Runner.close()` → "Finalize asynchronous generators, shutdown default executor, close the event loop". SIGINT handling: the custom handler cancels the main task so `try/finally` cleanup runs, and `KeyboardInterrupt` is re-raised afterwards.
- Problem solved: deterministic fan-out/fan-in with cancellation propagation and aggregated failure reporting
- Failure model: first non-cancellation failure cancels siblings; all failures surface as an exception group
- Shutdown model: the `async with` block cannot exit until every child has finished
- Dependency ownership: none (stdlib)
- Complexity: low, but with the caveats in R5
- License: PSF (stdlib)
- Maintenance / maturity: stdlib since 3.11; project targets `py314` (`pyproject.toml` → `target-version = "py314"`)
- MarketPulse applicability: **medium** — the failure semantics are what a host wants, but the API is narrow (see R5)

### R5 — AnyIO task groups + structured concurrency rationale

- Reference: AnyIO
- Official docs: `https://anyio.readthedocs.io/en/stable/tasks.html` and `.../why.html`
- Exact statements: "A task group is an asynchronous context manager that makes sure that all its child tasks are finished one way or another after the context block is exited. If a child task, or the code in the enclosed context block raises an exception, all child tasks are cancelled."; "In practice this means that a special exception, `ExceptionGroup` (or `BaseExceptionGroup`) is raised which contains both exception objects."
- Design-rationale page (`why.html`), verbatim: "First and foremost, the `asyncio.TaskGroup` class does not offer any way to cancel, or even list all of the contained tasks…"; "…`asyncio.TaskGroup` still does not provide any such mechanism [waiting for readiness], leaving users to devise their own, often error-prone methods to achieve this."; "An AnyIO task group contains its own cancel scope which can be used to cancel all the child tasks, regardless of where they were launched from."
- **Dependency availability (verified):** `https://raw.githubusercontent.com/encode/starlette/master/pyproject.toml` → `dependencies = ["anyio>=4.0.0,<5", "typing_extensions>=4.10.0; python_version < '3.13'"]`. AnyIO is therefore **already a required transitive dependency** of the installed FastAPI/Starlette stack — no new dependency would be introduced.
- Problem solved: structured concurrency with cancellable-but-not-obscured task trees and readiness signalling
- Failure model: sibling cancellation + exception group, plus explicit cancel scopes
- Shutdown model: cannot leave the `async with` block until all children exit; a cancelled cancel scope also cancels subsequently-spawned children
- Dependency ownership: none beyond the task group
- License: MIT
- Maintenance / maturity: mature, actively maintained; recommended by Starlette's own docs for managing async tasks
- MarketPulse applicability: **high** — it is the lowest-cost way to get "all children stopped, failure not lost" without inventing a supervisor

### R6 — NautilusTrader (kernel / TradingNode)

- Reference: NautilusTrader (`nautechsystems/nautilus_trader`)
- Sources: official docs `https://nautilustrader.io/docs/latest/concepts/architecture/`; official API reference `https://nautilustrader.io/docs/python-api-nightly/system.html`; license `https://api.github.com/repos/nautechsystems/nautilus_trader/license` (**LGPL-3.0**); third-party line-level cross-reference `https://deepwiki.com/nautechsystems/nautilus_trader/7.1-tradingnode-architecture`
- Exact symbols (official API reference): `NautilusKernel.start()`, `await start_async()`, `stop()`, `await stop_async()`, `dispose()`, `cancel_all_tasks()`, `is_running()`; `TradingNode.build() / run() / run_async() / stop() / stop_async() / dispose()`. Third-party line references (not independently verified): `nautilus_trader/live/node.py` build ~252-261, run_async ~303-341, stop_async ~362-376, dispose ~409-473
- Problem solved: one kernel shared by backtest / sandbox / live, with explicit node lifecycle and graceful shutdown
- Lifecycle model: `TradingNode` wraps `NautilusKernel`; `build()` instantiates data/exec clients via `TradingNodeBuilder`; `run_async()` starts the kernel, then gathers engine queue tasks (and optionally an external streaming task); `stop_async()` cancels streaming, stops the kernel, waits for disconnection; `dispose()` is documented as idempotent ("Calling this method multiple times has the same effect as calling it once")
- Failure model: crash-only design; official docs state "**Crash-only design**" as an architectural technique; `stop_async()` "After a specified delay the internal Trader residual state will be checked"
- Shutdown model: signal handlers for SIGTERM/SIGINT/SIGABRT invoke the async shutdown path; the Rust `LiveNode` tracks an explicit FSM `Idle → Starting → Running → ShuttingDown → Stopped`
- Dependency ownership: the kernel owns cache / portfolio / engines / trader / clock / message bus; "The kernel owns the shared trading core"
- Complexity: **very high** — Rust core + Python facade, multi-crate workspace, message bus, event store, adapters
- License constraint: **LGPL-3.0** — copying source into this project is not appropriate; pattern study only
- Maintenance / maturity: very mature, production-grade
- MarketPulse applicability: **pattern only**, and only three patterns transfer: (i) one explicit lifecycle owner; (ii) an explicit lifecycle FSM; (iii) engine queues drained as a bounded set of tasks gathered by the node. Explicitly **not** transferable: message bus, service partitioning, Rust core, "one node per process" global-state design. Official docs also record a directly relevant constraint: **"Running multiple `LiveNode` or `BacktestNode` instances concurrently in the same process is not supported because their runtime state is not isolated"** — "Sequential execution … is supported when each node is disposed before the next one starts."

### R7 — Hummingbot (TradingCore / stop path, source level)

- Reference: Hummingbot (`hummingbot/hummingbot`), Apache-2.0
- Sources: `https://raw.githubusercontent.com/hummingbot/hummingbot/master/hummingbot/client/hummingbot_application.py`; `.../hummingbot/core/trading_core.py`; `.../hummingbot/client/command/stop_command.py`; license `https://api.github.com/repos/hummingbot/hummingbot/license` (**Apache-2.0**)
- Exact symbols: `HummingbotApplication.__init__ / main_application() / run() / run_headless()`; `TradingCore.start_clock() / stop_clock() / start_strategy() / stop_strategy() / remove_connector() / shutdown() / get_status()`; `StopCommand.stop() / stop_loop()`
- Problem solved: a long-running live trading process with a CLI/headless control plane and an explicitly ordered teardown
- Lifecycle model: `HummingbotApplication` is a process singleton (`_main_app`); it delegates all trading concerns to `TradingCore`; the headless entry point is `while True: await asyncio.sleep(1)` with `finally: await self.trading_core.shutdown()`
- **Shutdown model (verbatim ordering from `stop_loop`)**: (1) V2 strategy `on_stop()`; (2) `stop_strategy()`; (3) `cancel_outstanding_orders()` unless skipped; (4) `remove_connector(name)` in a `try/except Exception` loop "Error stopping connector {name}"; (5) `stop_clock()`; (6) `markets_recorder.stop()`; (7) clear strategy references. `TradingCore.shutdown()` performs the same steps and returns a bool
- Failure model: per-connector teardown errors are caught and logged so the rest of the shutdown proceeds; clock task cancellation catches `asyncio.CancelledError`; clock ownership is `self._clock_task = asyncio.create_task(self._run_clock())` with `stop_clock()` cancelling and awaiting it
- Dependency ownership: `TradingCore` owns connector manager, clock, strategy, notifiers, kill switch, markets recorder, metrics collectors; note the clock itself owns its iterators (`clock.add_iterator` / `remove_iterator` for connectors, strategy, metrics)
- Complexity: medium; the design is CLI-centric with a large command mixin hierarchy
- License constraint: Apache-2.0 — permissive, but direct copying still imports a large CLI/strategy architecture
- Maintenance / maturity: mature, actively maintained
- MarketPulse applicability: **pattern only**. Highest-value transferable pattern: **a single ordered teardown with per-step error containment**, i.e. "one failure in shutdown must not abort the remaining steps". MarketPulse's harness `finally:` blocks already do this by hand (`shutdown_errors.append(...)` then continue).

### R8 — Freqtrade (Worker loop, source level)

- Reference: Freqtrade (`freqtrade/freqtrade`), GPL-3.0
- Sources: `https://raw.githubusercontent.com/freqtrade/freqtrade/develop/freqtrade/worker.py`; license `https://api.github.com/repos/freqtrade/freqtrade/license` (**GPL-3.0**)
- Exact symbols: `Worker.__init__ / _init / run / _worker / _throttle / _process_stopped / _process_running / _reconfigure / exit`; `FreqtradeBot.startup() / process() / cleanup() / check_for_open_trades()`
- Problem solved: a supervised, restart-aware, single-process bot loop with an explicit state machine and systemd integration
- Lifecycle model: `Worker.run()` is `while True: state = self._worker(old_state=state)`; state transitions drive `freqtrade.startup()` (on entering RUNNING/PAUSED) and `check_for_open_trades()` (on STOPPED); `_throttle()` sleeps to align to the next candle
- Failure model (verbatim behaviour): `_process_running()` catches `TemporaryError` → warn + sleep `RETRY_TIMEOUT` (retry, keep running); catches `OperationalException` → notify, log exception, and **set `self.freqtrade.state = State.STOPPED`** (stop trading but keep the process alive). Systemd integration via `sdnotify`: `READY=1` after init, `WATCHDOG=1\nSTATUS=…` every iteration, `RELOADING=1`/`READY=1` around config reload, `STOPPING=1` on exit
- Shutdown model: `exit()` → `_notify("STOPPING=1")`, notify status, `freqtrade.cleanup()`. `_reconfigure()` → `cleanup()` then `_init(True)` — i.e. **cleanup-then-rebuild in place**
- Dependency ownership: `Worker` owns the `FreqtradeBot`; config reload replaces the whole bot instance
- Complexity: medium, and heavily coupled to `Configuration`/RPC/systemd
- License constraint: **GPL-3.0** — code copying is not permissible here; pattern study only
- Maintenance / maturity: very mature
- MarketPulse applicability: **pattern only**. Two transferable ideas: (i) **distinguish transient vs terminal failures** and choose "retry" vs "degrade to stopped while staying alive"; (ii) external supervisor liveness signalling (sd_notify) as the model for "who observes the process".

### R9 — Rejected infrastructure references (recorded for completeness)

Redis / Celery / Kafka / Kubernetes / Docker supervisor / systemd — **not researched as candidates**: `DECISIONS.md:31` records that PRE-01A-D1 (Accepted) explicitly "不选型、不设计 asyncio TaskGroup / Docker supervisor / systemd / Celery / Redis / Kafka / Kubernetes"; `PRODUCT_REQUIREMENTS.md` §12 lists Microservices/Kafka/Redis/Celery/Kubernetes as explicit non-goals "不因为长期目标而自动要求". They are re-examined in "Known Solution Check" and "Rejected / Unnecessary Complexity".

---

## Reference Comparison Matrix

| Ref | Lifecycle model | Failure model | Shutdown model | Dependency ownership | Complexity | License | Maturity | MarketPulse fit |
|---|---|---|---|---|---|---|---|---|
| FastAPI lifespan (R1) | one app-scoped async CM; before/after `yield` | delegated to server | after requests finish | app-owned shared resources | very low | MIT (no copy needed) | official | **adopt as the host anchor** |
| Starlette lifespan + state (R2) | as R1 + typed state bag to handlers | delegated | **teardown only after connections closed and in-process background tasks finish** | state bag | very low | BSD-3 | official | **adopt**; note it nudges toward AnyIO task groups |
| Uvicorn (R3) | `LifespanOn` startup/shutdown over ASGI lifespan | startup failure ⇒ `should_exit` ⇒ `sys.exit(STARTUP_FAILURE)`; `lifespan="auto"` tolerates a missing lifespan | connections → tasks → `lifespan.shutdown()`; `timeout_graceful_shutdown` default `None` = **unbounded** | server owns sockets/connections/tasks | already installed | BSD-3 | very mature | **already in effect**; must be configured/knowingly relied on |
| asyncio TaskGroup (R4) | `async with` fan-out/fan-in | first non-cancel failure cancels siblings; `ExceptionGroup` | block cannot exit until all children finish | none | low | PSF | stdlib 3.11+ | usable, but narrow API |
| AnyIO task group (R5) | asyncio plus cancel scope + readiness + handle | sibling cancellation + exception group; explicit cancel scopes | same as asyncio, plus later-spawned children inherit cancellation | none | low | MIT | mature; **already a transitive dep** | **preferred** among the two |
| NautilusTrader (R6) | Kernel + Node with explicit phases; builder for clients | crash-only design; residual-state check on stop | signal-driven async shutdown; Rust FSM `Idle→…→Stopped`; idempotent `dispose()` | kernel owns cache/portfolio/engines/trader/clock/bus | very high | **LGPL-3.0** | very mature | pattern only (single owner, FSM, bounded task set) |
| Hummingbot (R7) | singleton app → `TradingCore`; stepwise start | per-step shutdown error containment | **ordered teardown**, error-contained per connector | core owns connectors/clock/strategy/recorder | medium | Apache-2.0 | mature | pattern only (ordered, error-contained teardown) |
| Freqtrade (R8) | state machine + throttled loop; `Worker` owns bot | transient → retry; terminal → degrade to STOPPED and stay alive | `exit()` → notify + `cleanup()`; reconfigure = cleanup + rebuild | worker owns bot | medium | **GPL-3.0** | very mature | pattern only (transient vs terminal split; liveness signalling) |

---

## Reuse Classification

Allowed classes only. "Why" is mandatory.

| Item | Class | Why |
|---|---|---|
| FastAPI `lifespan=` parameter | **INTEGRATE** | First-party API on an already-installed dependency; it is the sanctioned app-scoped resource owner. No wrapper is needed; wrapping would add a layer with no benefit |
| Starlette lifespan state bag (`yield {...}` → `request.state`) | **INTEGRATE** | First-party; gives the API layer read-only access to host-owned objects without a second global |
| Uvicorn lifespan + graceful-shutdown machinery | **DIRECT REUSE** | Already the running server; no code change required. The only decision is *what* the app-level lifespan does and whether `timeout_graceful_shutdown` should be set |
| AnyIO `create_task_group()` | **INTEGRATE** | Already a transitive dependency (`starlette` → `anyio>=4.0.0,<5`), so zero dependency cost; provides cancel scopes, sibling cancellation, exception groups and readiness signalling. Starlette's own docs recommend it |
| AnyIO `TaskGroup.start(..., return_handle=True)` | **INTEGRATE** | same as above; gives a cancellable handle per subsystem |
| `asyncio.TaskGroup` | **LEARN / PATTERN ONLY** | Semantics are right but the API cannot cancel or enumerate children and cannot signal readiness (AnyIO's own documented critique). Serve the same guarantee via AnyIO instead of adding a second concurrency primitive |
| `asyncio.Runner` / `asyncio.run` shutdown semantics | **LEARN / PATTERN ONLY** | Relevant only if the host ever owns its own `asyncio.run` entry point; under uvicorn it does not |
| Uvicorn `handle_exit` / `capture_signals` | **DIRECT REUSE** | Signal handling is already provided; the host must not install competing handlers |
| NautilusTrader kernel/node architecture | **LEARN / PATTERN ONLY** | LGPL-3.0 forbids convenient source reuse; and its scope (message bus, Rust core, multi-crate workspace, one-node-per-process globals) is enormously disproportionate to a single-process paper-trading modular monolith |
| NautilusTrader explicit lifecycle FSM (`Idle/Starting/Running/ShuttingDown/Stopped`) | **LEARN / PATTERN ONLY** | The *pattern* maps cleanly onto MarketPulse's existing persisted `SystemState`/`OperatorState`; the code does not |
| Hummingbot `TradingCore.shutdown()` ordered teardown | **LEARN / PATTERN ONLY** | Apache-2.0 permits copying, but the code is entangled with a CLI/connector/strategy hierarchy MarketPulse does not have. The transferable part is the *ordering + per-step error containment*, which is a handful of lines |
| Freqtrade `Worker` transient-vs-terminal failure split | **LEARN / PATTERN ONLY** | GPL-3.0; also built around candle throttling and RPC, neither of which MarketPulse needs |
| Freqtrade `sd_notify` liveness signalling | **LEARN / PATTERN ONLY** | Useful as a *conceptual* external-observer model. MarketPulse runs an in-process host for V1 and should not add a process supervisor (see Rejected Complexity) |
| MarketPulse's own `EventRuntime.start()/stop()` | **DIRECT REUSE** | Already the accepted bounded-queue/worker lifecycle; the host calls it, it does not reimplement it |
| MarketPulse's own `RecoveryManager` | **DIRECT REUSE** | Already the accepted startup gate; the host invokes it once at process start and honours its `final_system_state` |
| MarketPulse's own `SafetyRuntime` / `ScannerPipeline` / `reconcile()` | **DIRECT REUSE** | Already the accepted runtime seams; the host only needs to pump and schedule them |
| MarketPulse's own `supervised_worker()` (`runtime.py:39`) | **ADAPT** | The semantic ("isolate one worker exception and report it without cancelling the runtime") is already the project's chosen policy. It takes a bare `HealthRegistry` and writes `<name> FAILED`; a host would want to extend it with retry/restart policy and richer telemetry — an adaptation, not a rewrite |
| MarketPulse's `db/session.py` factory | **ADAPT** | The shape (`create_async_engine(pool_pre_ping=True)` + `async_sessionmaker(expire_on_commit=False)`) is correct and reusable; what must change is *ownership* (module-level, single instance, explicit `dispose()`) and pool policy |
| `LivePaperHarness` / `SmokeHarness` / `_consume` / `_ControlledStream` / harness probes | **REJECT** | Test doubles and perturbation tools. `AI_CONTEXT.md:627` already states they must not be used as a Runtime Host or Smoke. Copying `_consume` would import an evidence script's private contract into production |
| Celery / Redis / Kafka / message broker | **REJECT** | No real requirement evidence; explicitly a non-goal (`PRODUCT_REQUIREMENTS.md` §12); single process, single user, in-process queues already bounded and accepted |
| Kubernetes / external scheduler / custom supervisor framework / microservices | **REJECT** | Same as above; plus `DECISIONS.md:31` records that D1 did not select them and left the boundary open — this research finds no requirement that would now justify them |
| New persistence layer / new DB tables for host state | **REJECT** | PostgreSQL is already the accepted sole restart-recovery source of truth; `runtime_control` already carries `system_state` + `heartbeat_at` |
| Docker/`docker-compose.yml` as the runtime supervisor | **REJECT for V1** | `docker-compose.yml` currently contains **only** the `postgres` service. Adding a supervisor service changes the operational boundary and is not needed to run one local paper process |

---

## Known Solution Check

**Q1. Which Runtime Host problems are already mature, generic problems?**
All of them. Enumerated against the Gap Map: app-scoped resource ownership (D1, D2); orderly startup with a readiness gate (D5); ordered, error-contained shutdown (D6); signal-driven termination (D7); structured task fan-out with cancellation propagation and failure aggregation (D4); bounded graceful-shutdown timeouts (D6/R3); child-failure observation and reporting (D4). None of D1–D9 is a novel problem. What is *not* generic is only the MarketPulse-specific composition (which component is started in which order, and which facts constitute readiness).

**Q2. Which official frameworks already solve them?**
FastAPI `lifespan` (R1) solves app-scoped ownership and startup/shutdown timing. Starlette (R2) adds the "teardown after connections and background tasks complete" guarantee and the state bag. Uvicorn (R3) solves signal handling, process-level startup failure semantics, and ordered graceful shutdown with a timeout knob. AnyIO task groups (R5) solve structured fan-out, cancellation propagation, failure aggregation and readiness signalling — and are already installed. Together these four cover every missing responsibility in the Gap Map except the MarketPulse-specific *content* of each phase.

**Q3. What is genuinely MarketPulse-specific?**
Five things, and only five:
1. **Which component is started in which order** — state service/incidents first (they are dependencies of almost everything), then execution/protection/plans/reevaluation/safety, then G2 runtime/repository/scanner, then the market feed.
2. **What "ready" means** — per the accepted evidence: durable state ensured, a genuine fresh BBO for each instrument in scope, `RecoveryManager.recover()` completed, and only then `EventRuntime.start()` + ingress (`verify_n01_8:409-519`).
3. **The production implementation of the latest-market-state accessors** (`bbo_for`, `state_version_for`) — currently only fakes and monkey-patches exist.
4. **The failure policy per subsystem** — MarketPulse's accepted semantics are "fail-closed on risk, keep protection working, isolate worker exceptions, degrade state rather than crash" (`supervised_worker`; `SafetyRuntime`; `RecoveryManager`'s `health.set(...)` on provider failure; SAFE_MODE latch). Which subsystem failure may fail the whole host vs must be isolated is a MarketPulse decision, not a framework one.
5. **The observability surface required by the open P2 memory watch** — the specific series that the frozen N01 memory condition consumes.

**Q4. Can we adopt "mature lifecycle infrastructure + MarketPulse-specific composition" instead of building a Runtime Framework?**
**Yes — and the evidence strongly favours it.** Uvicorn is already providing the process/lifespan machinery; FastAPI/Starlette already provide the app-scoped hook and the state bag; AnyIO is already installed and provides the concurrency guarantees. What remains is a composition root plus an explicit lifecycle ordering plus a small observability surface. The Gap Map's D1–D9 contain no item that requires a new framework. Note the asymmetric cost: a self-built supervisor would have to re-derive signal handling, graceful-shutdown ordering, startup-failure semantics and task aggregation — all of which are already present and battle-tested in the current dependency set.

**Q5. Does the current real requirement need Redis / Celery / Kafka / message broker / microservice / external scheduler / custom supervisor framework / Kubernetes / a new persistence layer?**

**No evidence of need was found in the repository. Marked NOT REQUIRED (V1).** Basis:

| Candidate | Verdict | Evidence |
|---|---|---|
| Redis | **NOT REQUIRED** | `PRODUCT_REQUIREMENTS.md` §12 non-goal; sole durable source of truth is already PostgreSQL; no cross-process coordination requirement exists (the only cross-process concern, same-scope evaluator coordination, is already solved with a PostgreSQL advisory transaction lock per `DECISIONS.md:23`) |
| Celery | **NOT REQUIRED** | No distributed task requirement; `EventRuntime` already provides a bounded in-process queue with finite workers and accepted lifecycle |
| Kafka | **NOT REQUIRED** | §12 non-goal; single process, single user, no fan-out across services |
| message broker | **NOT REQUIRED** | Same; in-process `asyncio.PriorityQueue` is already the accepted bus |
| microservice split | **NOT REQUIRED** | `DECISIONS.md:3` Modular Monolith; §12 non-goal |
| external scheduler | **NOT REQUIRED for V1** | The only schedules are periodic reconciliation checkpoints and a re-evaluation cadence gate (`MeaningfulEventGate`), both in-process. (An OS-level scheduler is a legitimate *deployment* option to study in the placement section, but it is not required by any evidence) |
| custom supervisor framework | **NOT REQUIRED** | Nothing in D1–D9 is unsolved by the existing stack; a custom supervisor would duplicate uvicorn + AnyIO |
| Kubernetes | **NOT REQUIRED** | §12 non-goal; single local process |
| new persistence layer | **NOT REQUIRED** | PostgreSQL already the sole restart-recovery truth; `runtime_control` already persists `system_state` + `heartbeat_at` |

---

## Host Placement Evidence

Evidence only. **No final architecture is decided here.**

### Option A — FastAPI `lifespan` directly owns runtime components

- **Supporting evidence:** first-party sanctioned mechanism (R1, R2). Starlette guarantees "will not start serving any incoming requests until the lifespan has been run" and "lifespan teardown will run once all connections have been closed, and any in-process background tasks have completed". Uvicorn enforces startup failure as fatal (`sys.exit(STARTUP_FAILURE)`) and runs lifespan shutdown after connection/task drain (R3). Zero new dependencies. Zero new processes. Starlette's state bag lets handlers read host objects.
- **Risks:** (i) single failure domain — a fatal runtime error and the API die together (though this is already true today, since there is no runtime at all); (ii) no meaningful restart isolation — an unrecoverable runtime bug takes the API down; (iii) `verify_n01_8` shows restarts are how the accepted evidence exercises recovery, and Option A has no natural in-process restart story; (iv) a long/wedged shutdown blocks the process, and uvicorn's `timeout_graceful_shutdown` defaults to `None` (unbounded); (v) the module-level `runtime_state = GlobalRuntimeState(...)` in `api/app.py:15` would become an ambiguous second owner unless removed or re-pointed at the lifespan-created state.
- **MarketPulse fit:** high for a local single-user paper runtime. `LOCAL_ONLY=true`, `127.0.0.1`, one process, one operator (`PRODUCT_REQUIREMENTS.md` §7). Closest to today's deployment (`main.py` → uvicorn → `api.app:app`).
- **Complexity:** lowest of the four.
- **Operational implications:** one process to start/stop; runtime logs interleave with access logs; restarting the API restarts the runtime.
- **Open questions:** does "API up but runtime not ready" need to be externally distinguishable? Is serving-before-recovery acceptable if `/health` reports it? Must `timeout_graceful_shutdown` be set?

### Option B — Independent `RuntimeHost` object, started/stopped by FastAPI `lifespan`

- **Supporting evidence:** keeps a single explicit owner (the pattern NautilusTrader and Hummingbot both use: a kernel/core object with `start`/`stop`), while still using the first-party hook for timing. The object is unit-testable without a server (R7/R8 both test their core independently). Starlette's state bag lets the API read host state. Reuses `EventRuntime.start/stop`, `RecoveryManager.recover`, `SafetyRuntime`, `reconcile` unchanged. `supervised_worker` and `HealthRegistry` already model "isolate and report" from inside such an object.
- **Risks:** (i) still shares the process failure domain with the API; (ii) two shutdown drivers (uvicorn's graceful shutdown and the host's own ordering) must be reconciled into one deterministic sequence, otherwise ordering is ambiguous — this is a real design hazard, not a generic one; (iii) more moving parts than A; (iv) the object's lifetime is still tied to the API, so "runtime survives API restart" is not achieved.
- **MarketPulse fit:** high. Matches the accepted component boundaries exactly (the host adds ownership, not new abstractions), and keeps the accepted harness shutdown ordering expressible verbatim.
- **Complexity:** low–medium.
- **Operational implications:** as A, plus a clear seam for tests and future observability.
- **Open questions:** who owns engine/sessionmaker — the host or `api/app.py`? Does the host expose the state bag, or does the API hold a reference? How is "readiness" surfaced (health endpoint, or serve-gate)?

### Option C — Independent runtime process; API process separate

- **Supporting evidence:** NautilusTrader's documented constraint that concurrent nodes in one process are unsafe (R6) is the general argument for process isolation; Freqtrade's supervisor + sd_notify model (R8) shows the external-observer pattern. Gives true restart isolation, and lets the runtime keep running while the API restarts.
- **Risks:** (i) requires a **second durable coordination surface** — today the only cross-process facts are the PostgreSQL rows; operator actions (`SystemControlService`) would have to be routed cross-process or duplicated; (ii) `api/app.py` would no longer be the runtime's owner, so `GlobalRuntimeState.health` and any live status the API reports must be re-sourced (DB read or IPC); (iii) doubles the operational surface (two processes, two logs, two failure modes) for a single-user local paper system; (iv) a restart story requires a supervisor — which Q5 marks NOT REQUIRED; (v) the accepted `N01-8` supervisor is explicitly a *validation* artifact (`scripts/n01_8_detach.py`) and must not be promoted; (vi) `N01-8-IR-P3-03` already records an unresolved evidence gap around supervisor exit codes — the same gap would move into production.
- **MarketPulse fit:** medium. Justifiable only if a real requirement appears for "unattended 7×24 runtime independent of the UI/API". `PRODUCT_REQUIREMENTS.md` §11 lists "Continuous Runtime Validation" as a future direction, but no accepted requirement currently demands process separation.
- **Complexity:** highest.
- **Operational implications:** two processes to manage; needs an explicit supervisor choice (which Q5 does not justify today); observability must span processes.
- **Open questions:** is API-independent runtime uptime a stated requirement? Would operator control move to the DB (it already is durable) or need new IPC? Who supervises whom?

### Option D — Other patterns found during research (added per task §13)

Only one additional pattern is evidenced by the research: **NautilusTrader's "sequential node with explicit dispose"** (R6: "Sequential execution of multiple nodes is supported when each node is disposed before the next one starts"). As applied to Option B/C this is a *refinement* rather than a distinct option: it argues that whatever owns the runtime must have an idempotent `dispose()`-equivalent that fully releases engines/tasks so that a restart is safe. Its evidence value is in the *stop* design, not the placement choice. No third empirically-supported placement pattern was found; a hybrid (runtime started by lifespan, but with an explicit readiness gate before serving) is a composition of A and B, not a new option.

---

## Lifecycle / Failure Evidence

Evidence and trade-offs only. **No answer is frozen here.**

**1. When one Runtime child task crashes, who is responsible for noticing?**
Evidence: (a) `EventRuntime._worker` catches every `Exception`, appends to `worker_exceptions` (cap 128) and sets the publisher's future exception — so the *publisher* notices, and the failure does not kill the runtime (`g2/runtime.py:191-194`). (b) `supervised_worker()` documents the intended policy: "Isolate one worker exception and report it without cancelling the runtime" (`runtime.py:40`). (c) `PositionReevaluationService._call_provider` converts provider failure into a fail-closed HOLD plus an `AI_REEVALUATION_FAILED` incident rather than raising (`reevaluation.py:305-322`). (d) Official structured-concurrency evidence says the opposite of (a)/(b): a task group observes children itself and cannot lose a failure (R4, R5). (e) The validation harness substituted a global `asyncio.all_tasks()` sweep for a real observer (`verify_n01_6:956-960`). Trade-off: an explicit owner must notice (reliable, but needs a defined policy) vs. a task group noticing implicitly (unlosable, but then the group decides the blast radius).

**2. Should a child failure fail the whole host / isolate the subsystem / restart the child?**
Mature patterns found: three distinct policies exist in real systems. Freqtrade splits **transient** (retry, keep running) from **terminal** (log, degrade to `STOPPED`, keep the process alive) (R8). NautilusTrader is **crash-only** at the process level and keeps running children but checks "Trader residual state" on stop (R6). AnyIO/asyncio task groups **cancel siblings and raise an exception group**, i.e. fail the enclosing scope unless the scope is explicitly isolated (R4, R5). MarketPulse's accepted semantics already lean toward isolation-with-degradation: `health.set(..., "FAILED")`; `CORE_MARKET_DATA → UNAVAILABLE` + `CORE_DATA_STALE` incident instead of raising; risk-increasing actions fail closed while protection keeps working (`DECISIONS.md:11-13`). Trade-off: isolation preserves protection availability but can hide a systemic failure; fail-fast is safer to reason about but would stop protection.

**3. How to distinguish an OKX disconnect from a Host failure?**
Evidence: a disconnect is *internal* to `OKXLiveProvider.stream()` — it catches `Exception`, increments `reconnects`, logs `okx_stream_disconnected`, sleeps and reconnects (`okx_live.py:105-114`). The provider therefore presents a disconnect as **temporary stream silence, not an exception**. Downstream, `SafetyRuntime._mark_freshness` ages quotes out: freshness = `tradable and data_quality is FRESH and (now - received_at) <= 5.0 s` (`orchestrator.py:108-119`), and staleness is expressed as `CORE_MARKET_DATA = UNAVAILABLE` + a `CORE_DATA_STALE` incident, with risk-increasing BUY blocked (`RUNTIME_STATE_DATA_DEGRADED`) while SELL still requires an executable fresh BBO. Trade-off: the accepted mechanism makes a disconnect a *data-quality* fact, which means a *host* failure must be distinguished by something other than data staleness — the host needs its own liveness signal (e.g. "is the consumer task alive", "is the provider's reconnect counter advancing"). Note that `reconnects` / `connection_attempts` are counters on the provider instance and are not currently exposed anywhere in production.

**4. How does an `EventRuntime` worker failure surface upward?**
Evidence: it does **not** currently surface upward in production. `worker_exceptions` is a bounded `deque` (`g2/runtime.py:111`), and the only reader in the repo is the validation sampler (`verify_n01_6:867`). The accepted gate `worker_exceptions_zero` is asserted only by validation code. Trade-off: keeping it as a bounded diagnostic deque avoids one bad event poisoning the system; but without a host that reads it, a persistent worker failure is invisible until someone inspects memory.

**5. How should shutdown establish dependency ordering?**
Evidence: two independent, converging orderings.
- Harness (MarketPulse, accepted): stop ingress → close stream → `runtime.stop()` (drain queue, join, gather workers) → stop observers → dispose engines → prove zero owned PG clients (`verify_n01_6:938-951`, `verify_n01_8:726-741`).
- Hummingbot (production system): strategy `on_stop` → stop strategy → cancel outstanding orders → remove connectors (error-contained per connector) → stop clock → stop recorder → clear refs (R7).
Both are **producer-first, resource-last**. Trade-off found in evidence: Starlette says teardown waits for "in-process background tasks" (R2) — which means a long-lived runtime task must be explicitly cancelled *by* the app before teardown can complete; and uvicorn cancels remaining tasks only if `timeout_graceful_shutdown` is set (R3), otherwise the wait is unbounded. Operational implication, not a decision: the host's stop sequence must terminate its own tasks rather than rely on the server to reap them.

**6. Who should own the DB engine / sessionmaker?**
Evidence: today **nobody** in production — `db/session.py` is unreferenced. Every composition builds its own engine: `verify_n01_6:808` (`_smoke_engine(database_url)`), `g5/replay.py:480-481` (`create_async_engine(..., poolclass=NullPool)` with explicit `dispose()` in `finally`), plus a *second* engine purely for observation (`_observer_engine()`). `PostgresG2Repository` and all G4 services accept an injected `async_sessionmaker` and are engine-agnostic, so ownership is a free choice at the composition root. Trade-off: a single owned engine gives one pool, one `dispose()` boundary and one place to reason about connection counts (which the accepted evidence already asserts: `pg_owned_clients_zero`, `pg_no_foreign_client_sessions`); per-request engines (as `get_db` does) would make that guarantee unprovable. NautilusTrader's analogue is that the kernel owns the shared infrastructure (R6).

**7. In which lifecycle phase should recovery run?**
Evidence: `verify_n01_8:409-519` places it strictly between "durable state ensured + live BBO available" and "runtime started", and the comment records that "PostgreSQL recovery owns the RUNNING transition (never forced)". `RecoveryManager.recover()` itself walks `STARTING → RECOVERING → … → final_state` and explicitly refuses to promote silently: `_final_state()` returns `EMERGENCY_STOP` if the operator latched it, `SAFE_MODE` if the SAFE_MODE latch or reconciliation failure or blocking incidents, `PAUSED` if operator/pre-state paused, `ERROR` on DATABASE/EXECUTION health, `DATA_DEGRADED` if not all quotes fresh, else `RUNNING` (`recovery.py:489-525`). Trade-off: running recovery during startup delays readiness but guarantees no risk-increasing action occurs pre-recovery; running it lazily would allow serving (and therefore possibly acting) against unrecovered state.

**8. Is reconciliation a startup gate, a periodic service, or an explicit command — and how do these compose?**
Evidence: it is **all three already**, and composition is already specified:
- startup gate: `RecoveryManager.recover()` awaits `self.reconcile(run_mode)` and latches SAFE_MODE + `ACCOUNT_INTEGRITY_ERROR` on failure (`recovery.py:250-296`);
- admission gate: `SystemControlService._resume_gate` calls `self.reconcile(run_mode)` before allowing a resume (`control.py:142-144`);
- periodic: `N01-8` emitted 24/24 reconciliation checkpoints through `ms._checkpoint(...)` (`verify_n01_8:605-652`), i.e. the *cadence* exists today only inside the validation harness.
`reconcile()` is detector-only by contract ("Detector only. Never repairs ledger, position, cash or reservation.") and reads one `REPEATABLE READ / READ ONLY` snapshot. Trade-off: a detection-only reconciler can be called freely but never fixes anything, so the host must define what happens on a recurring failure (the accepted answer so far is the SAFE_MODE latch).

**9. May FastAPI serving begin before runtime readiness?**
Evidence: Starlette will not serve until the lifespan has run (R2), so "serving" in the strict sense is already gated on the lifespan completing — which means *if* recovery is awaited inside the lifespan, the API is readiness-gated for free. Uvicorn additionally treats a lifespan startup failure as fatal (`sys.exit(STARTUP_FAILURE)`, R3). But if recovery were started-but-not-awaited (a background task), serving would begin immediately. Also relevant: today the API is *ungated* simply because no lifespan exists. Trade-off: awaiting recovery inside lifespan is the simplest correct behaviour and costs startup latency; a deferred gate keeps the API responsive but requires an explicit readiness surface and honest `/health` semantics. A separate question the evidence raises: the current `/api/v1/health` unconditionally reports the app-level `runtime_state.health`, which is set once at import to `"HEALTHY"` (`api/app.py:16`) — i.e. today's health endpoint cannot express "runtime not ready".

**10. How should shutdown guarantee: stop accepting new risk-increasing work → cancel/finish workers → close market streams → reconcile/flush where appropriate → close DB resources?**
Evidence, and the gaps in it:
- *stop accepting new risk-increasing work*: the mechanism exists (`SystemRiskGate` + `operator_state`/`system_state`), but nothing in the current shutdown path uses it — the harness simply stops the feed. A host could either set a non-running state before draining, or rely on "no new events after the feed stops".
- *cancel/finish workers*: `EventRuntime.stop()` drains rather than cancels (sentinels with priority 101 → `queue.join()` → `gather`) — i.e. **finish, not cancel**; this is deliberate and accepted.
- *close market streams*: `stream.aclose()` on the async generator, preceded by `consumer.cancel()` (`verify_n01_6:939-945`). `OKXLiveProvider` has no `close()`/`aclose()` of its own; cancellation of the consumer is the only stop mechanism.
- *reconcile/flush where appropriate*: the harness runs a **final reconciliation** *after* the runtime stops and asserts economics (`verify_n01_6:968-1001`, `verify_n01_8:759-765` via `ms._final_assertions`). NautilusTrader's `stop_async()` similarly checks residual state after a delay (R6).
- *close DB resources*: `await engine.dispose()` then `_wait_for_owned_client_cleanup(...)` proving `client_sessions == 0` and `idle_in_transaction == 0` (`verify_n01_6:1010-1019`).
- Trade-off / hazard found: the accepted ordering reconciles *after* stopping, which is only meaningful if nothing can still mutate durable state; the host must therefore be able to prove quiescence, which is why the zero-owned-clients probe exists.

---

## Memory P2 Observation Inputs

Finding identity preserved verbatim. **Nothing is modified here.**

`N01-7-R01-RR-P2-01` — Memory Operational Watch / Bounded Retention Growth
- Status: **REMAINS**. Severity: **P2 / NON-BLOCKING**.
- Frozen AND contract (thresholds **unchanged**): `RSS growth > 64 MiB` **AND** second-half slope `> 5 MiB/hour`.
- Observed at N01-8: `RSS growth = 77.711 MiB`; second-half slope = `−0.639369 MiB/hour` ⇒ Formal Finding = `FALSE`.
- Forbidden phrasings (must not appear): `memory resolved` / `memory is fine` / `memory problem closed` / `no memory concern`.
- Future observation surface explicitly named: **`Integrated Runtime Host`** + longer unattended Paper operation. `N01-9` must **not** be created.

**This research modifies nothing**: no threshold change, no finding closure, no severity change, no `N01-9`.

### What the future Host must expose, derived from the frozen condition's own inputs

Source of truth for the required series is the accepted evaluation code, not an opinion.

| Required observation | Exact source of the current definition | Why the Host must expose it |
|---|---|---|
| **Per-sample `rss_mb` paired with an elapsed-time axis** | `ms._memory_condition` reads `item["absolute_elapsed_seconds"]` and `item["rss_mb"]` (`verify_n01_7_medium_soak.py:2430-2435`); `rss_mb` from `_rss_mb()` = `psutil`/`Process.memory_info().rss` (`verify_n01_6:181`) | Without a host-owned, monotonically-timestamped RSS series, the warm-up-trimmed peak-growth and second-half-slope statistics cannot be computed at all |
| Warm-up-trimmed peak growth (MiB) | `ms._memory_condition`: `warmup_index = max(1, int(len(rss)*0.1))`, `total_growth_mib = peak - baseline` | The condition's first AND branch |
| Second-half slope (MiB/h) | `ms._memory_condition` → `soak._slope_per_hour(trimmed[half:])` | The condition's second AND branch |
| Sample cadence + series continuity | harness sampler loop (`verify_n01_6:882-900`) | A gap in the series changes the slope |
| `task_counts` — workers, pending tasks | `len(runtime._workers)`, `worker_tasks_final` via `asyncio.all_tasks()` name filter (`verify_n01_6:866,956-960`) | "no unexplained synchronized resource growth" |
| `worker_exceptions` count | `len(runtime.worker_exceptions)` (`verify_n01_6:867`) | `worker_exceptions_zero` is an accepted gate |
| `queue` depth / `inflight` | `runtime.queue.qsize()`, `len(runtime._inflight)` (`verify_n01_6:864-865`) | queue-drained / inflight-empty shutdown gates |
| `retained collections` (dedupe, capture anchors) | `len(runtime._dedupe)` + `runtime._dedupe_capacity` (`verify_n01_6:868-869`); `PostgresG2Repository._pending_capture_anchors` (cap 2048, `g2/repository.py:148-149`); trade-dedupe saturation analysis (N01-8 AC-16/AC-17) | `retention_within_capacity` + retention saturation analysis |
| **sockets** | N01-8 `sockets_not_accumulating` ("socket permanent delta <= 2 (or classified)") | AC-13 |
| **handles** | N01-8 `handles_not_accumulating` ("handle delta <= 16 (or classified)"); `_proc_resources` is the harness provider | AC-14 |
| **DB sessions** | `owned_client_sessions` / `other_client_sessions` / `idle_in_transaction` from `_ownership_activity` (`verify_n01_6:849-874`); `pg_owned_clients_zero` / `pg_idle_in_transaction_zero` / `pg_no_foreign_client_sessions` | AC-12 |
| **lifecycle timestamps** | `system_state` / `operator_state` from `_runtime_state(sessions)`; `runtime_control.heartbeat_at`; `RuntimeControlRecord.updated_at` (`g4/state.py:201-215`); N01-8 phase `process_started_at` / `pid` | Liveness + restart/execution-gap detection |
| Provider reconnect / stream liveness | `OKXLiveProvider.reconnects` / `connection_attempts` (counters exist but are unexposed); N01-8 `reconnects_ge_12` | Distinguishing disconnect (supported) from host failure |
| Tracked-set stability (no unexplained synchronized growth) | N01-8 `worker_count_stable` | AC-18 |

Note (fact, not a proposal): every one of these inputs is currently produced **only** by validation-harness sampling code. The frozen condition consumes `rss_mb` + `absolute_elapsed_seconds`; the rest are the accepted AC-11…AC-18 resource gates. The task requires only that the Host *be able to expose* them — it does not require a specific mechanism, and this report deliberately does not choose one.

---

## MarketPulse Reusable Parts

1. **The whole accepted component graph** — `SystemStateService`, `IncidentManager`, `SystemRiskGate`, `PaperExecutionService`, `PositionProtectionService`, `PlanManager`, `PositionReevaluationService`, `SafetyRuntime`, `EventRuntime`, `ScannerPipeline`, `OpportunityScanner`, `PostgresG2Repository` (+ SE-02B capture, SE-ARCH-FIX-01 anchor, SE-02C forward path), `RecoveryManager`, `SystemControlService`, `reconcile()`. Every one already takes injected `sessions` / accessors and is engine- and process-agnostic. The Graph in `g5/replay.py:526-595` is a *working production-assembled* reference for the exact constructor arguments.
2. **A near-complete lifecycle ordering already exists in validated form** — `verify_n01_8:356-407` (open) and `:409-519` (restart: ensure → warm-up → recovery → runtime start) and `:726-741`/`:802-820` (shutdown). These are *evidenced orderings*, already accepted, that a host can implement rather than invent.
3. **`supervised_worker()` + `HealthRegistry`** (`runtime.py:10-47`) — the project's own supervision primitive and health surface, including the admission-control helpers `blocking()` / `all_healthy()` consumed by `SystemRiskGate` paths.
4. **`db/session.py`'s engine construction shape** — `create_async_engine(settings.database_url, pool_pre_ping=True)` + `async_sessionmaker(..., expire_on_commit=False)`; only ownership/pool policy needs deciding.
5. **`RecoveryManager._final_state()`** (`recovery.py:489-525`) — the accepted, already-tested mapping from operator intent + durable latch + reconciliation + freshness + incidents + health onto the next `SystemState`. A host does not need its own readiness judgement.
6. **`runtimacy`-adjacent accepted facts already persisted in PostgreSQL** — `runtime_control.system_state`, `operator_state`, `runtime_version`, `heartbeat_at`, plus the `outbox` `SYSTEM_STATE_CHANGED` events (`g4/state.py:168-188`). A host can be observable through existing durable facts rather than new ones.
7. **Version/refs**: `pyproject.toml` targets `py314`; `requirements.txt` already declares `fastapi>=0.116,<1`, `uvicorn[standard]>=0.35,<1`, `sqlalchemy[asyncio]>=2.0.43,<3`, `websockets>=15,<16`. No dependency addition is required for Options A/B.
8. **Existing test infrastructure for the composition** — `test_group4.py:128-180` and `test_n01_okx_paper_safety.py:160-214` show the accepted component graph can be built against a disposable DB in-process; a host is therefore testable without a live feed.

---

## MarketPulse Custom Minimum

The smallest set of genuinely new work, derived strictly from the Gap Map, with no framework-building:

1. **One composition root for the live graph.** Construct the accepted components once, in dependency order. ~1 module.
2. **An owned engine + sessionmaker** with an explicit `dispose()` boundary (currently `db/session.py` is unreachable and every caller makes its own engine). Reuse the existing construction shape; decide pool policy.
3. **A production implementation of the two accessors** `bbo_for(instrument_id) -> BestBidAsk` and `state_version_for(instrument_id) -> int`, backed by the host's own latest-market-state/state-version, replacing the harness fakes and the `execution.bbo_for` monkey-patch. This is the single largest genuinely new piece of *logic*, and it is small.
4. **A lifecycle sequence** with explicit phases — an `ensure/start` path that mirrors the validated ordering (state ensure → fresh-BBO warm-up → `RecoveryManager.recover()` → `EventRuntime.start()` → ingress), and a `stop` path that mirrors the validated ordering (stop ingress → close stream → `runtime.stop()` → stop observers → dispose engines → prove zero owned PG clients), with per-step error containment.
5. **A supervision policy** — an explicit, written answer per subsystem to Lifecycle Question 2 (fail whole host / isolate / restart), plus reading `EventRuntime.worker_exceptions` and the provider's reconnect counters so that a failure is actually observed. `supervised_worker` is the starting point; an ADAPT, not a rewrite.
6. **A readiness surface** — something other than today's import-time `"HEALTHY"` that can distinguish "API up" from "runtime ready/recovered", and can report the persisted `system_state`.
7. **An exposure path for the P2 observation inputs** listed in the previous section (exposure only; no threshold or finding change).

Explicitly **not** in the custom minimum: any new abstraction layer over FastAPI/uvicorn/AnyIO; any message bus; any queue beyond the accepted `EventRuntime`; any new table; any new process; any health/state model beyond the existing `HealthRegistry` + `runtime_control`; any change to `system_state`/`operator_state` semantics.

---

## Rejected / Unnecessary Complexity

| Rejected | Class | Why (evidence) |
|---|---|---|
| Custom supervisor framework / hand-rolled task-group replacement | REJECT | Every missing responsibility is already solved by uvicorn (R3) + FastAPI/Starlette lifespan (R1, R2) + AnyIO (R5). §8 Minimum Sufficient Solution / §12 No Overdevelopment forbid building what exists |
| Redis / Celery / Kafka / message broker | REJECT / NOT REQUIRED | `PRODUCT_REQUIREMENTS.md` §12 non-goal; single process; `EventRuntime` is already the accepted bounded bus; the only cross-process coordination need is already met by a PostgreSQL advisory transaction lock (`DECISIONS.md:23`) |
| Microservices / service split | REJECT | `DECISIONS.md:3` Modular Monolith; §12 non-goal |
| Kubernetes / external scheduler / Docker-based supervisor / systemd unit | REJECT for V1 | No requirement evidence (Q5); `docker-compose.yml` currently holds only PostgreSQL; `DECISIONS.md:31` records D1 did not select these and this research finds no new requirement |
| New persistence layer / new host-state tables | REJECT | PostgreSQL is already the sole restart-recovery truth; `runtime_control` already persists `system_state` + `heartbeat_at` + `runtime_version`; adding tables would create a second truth |
| Promoting `LivePaperHarness` / `SmokeHarness` / `_consume` | REJECT | Test doubles; `AI_CONTEXT.md:627` explicitly forbids using them as a Runtime Host or Smoke; they carry fake accessors and monkey-patches |
| Promoting `scripts/n01_8_detach.py` as the production supervisor | REJECT | Validation-only artifact; the accepted `N01-8-IR-P3-03` already records that no independent supervisor exit-code artifact exists — i.e. it is not a validated supervisor |
| Adopting NautilusTrader's kernel/message-bus architecture | REJECT | LGPL-3.0 + massive scope mismatch (Rust core, multi-crate, one-node-per-process global state) versus one local paper process |
| Copying Freqtrade code | REJECT | GPL-3.0 |
| `asyncio.TaskGroup` as an additional concurrency primitive | REJECT | Its semantics are already obtainable through AnyIO, which is already installed; using both would add a second, subtly different cancellation model |
| In-process restart/supervisor loop (a self-restarting host) | REJECT for V1 | Restart is already the accepted mechanism exercised by N01-8 at the *process* level; an in-process restart loop would introduce a state-reset problem that no evidence requires solving |
| New observability stack (metrics server, exporter, tracing) | REJECT for V1 | The P2 inputs need exposure, not a new stack; §8/§43 forbid ceremonial infrastructure |

---

## Open Questions For Formal Design

These must be adjudicated by the Formal Design step. Each is stated with the evidence that makes it a decision rather than a lookup.

1. **Placement**: Option A, B, or C — and if A/B, how is the API's second state surface (`api/app.py:15` module-level `GlobalRuntimeState`) reconciled with the injected `HealthRegistry` that G4 services actually read (Gap D9)?
2. **Readiness semantics**: is FastAPI serving allowed before runtime readiness? If not, is recovery awaited inside the lifespan (Starlette's own guarantee then makes readiness free) or deferred behind a readiness gate? What must `/api/v1/health` report so that "runtime not ready" is distinguishable from "API down"?
3. **Recovery phase placement**: is `RecoveryManager.recover()` mandatory inside the host startup path, and what happens if it lands on `DATA_DEGRADED` / `PAUSED` / `SAFE_MODE` — does the host still start the G2 runtime and ingress, and does the API still serve?
4. **Failure policy per subsystem** (Lifecycle Q2): for each of {market-data stream, G2 EventRuntime worker, `ScannerPipeline.ingest`, `SafetyRuntime.on_market_data`, `PositionReevaluationService`, periodic reconciliation, DB connectivity, API request path} — fail whole host, isolate, or restart? Which failures must fail closed on risk but keep protection running?
5. **Supervision mechanism**: AnyIO task group vs explicit task ownership + `supervised_worker`. Does the answer differ per subsystem (e.g. group for the core loops, isolated for the AI review)? Must `EventRuntime.worker_exceptions` be actively consumed (and at what cadence), or is a counter enough?
6. **DB ownership**: who owns the engine/sessionmaker (host vs `api/app.py`), what pool class/policy, and does the API share the same engine as the runtime? What is the evidence obligation at shutdown (the accepted gates are `pg_owned_clients_zero`, `idle_in_transaction_zero`, `pg_no_foreign_client_sessions`)?
7. **Shutdown**: exact responsibility ordering; whether the host must first move to a non-running state (using the existing `SystemStateService`) before draining, or whether "feed stopped" is sufficient; whether a bounded shutdown timeout should be introduced and how it relates to uvicorn's `timeout_graceful_shutdown` (default `None` = unbounded, R3); and whether final reconciliation runs before or after `EventRuntime.stop()`.
8. **Reconciliation composition**: which of {startup gate, admission gate, periodic checkpoint} the host owns, at what cadence, and what the host does on a recurring reconciliation failure beyond the existing SAFE_MODE latch.
9. **Quiescence proof**: what evidence the host itself provides that nothing can still mutate durable state at shutdown (today that proof is `_settle_background_tasks` + `_wait_for_owned_client_cleanup`, both harness-only).
10. **Market-data accessor ownership**: where the latest BBO per instrument lives, how `state_version_for` is derived, and how the host reports provider health (`reconnects` / `connection_attempts` are today unexposed) so that "disconnect" and "host failure" separate cleanly (Lifecycle Q3).
11. **Re-evaluation policy**: `SafetyRuntime(reevaluation_enabled=...)` is a first-class switch (harness sets `False`). Does the live host enable it, and if so, does that require a provider implementation (`PositionReviewProvider`) that does not exist in production?
12. **Observability surface**: which concrete mechanism exposes the P2 inputs (in-process sampling by the host, a status endpoint, an existing durable fact, or a log series), while explicitly *not* changing the frozen thresholds.
13. **`GlobalRuntimeState` / `HealthRegistry` ownership**: should there be exactly one health object per process, and who sets/clears `CORE_MARKET_DATA`?
14. **Restart semantics**: whether the host defines a *deployment-level* restart procedure (process restart + recovery, as N01-8 validated) or an *in-process* restart, and what must be true for a restart to be safe (NautilusTrader's "dispose before next start" is the analogous evidence).
15. **Scope boundary for the IRH batch itself**: what the acceptance criteria must prove (e.g. a bounded unattended run of the real host with the accepted harness *not* involved, plus the P2 exposure) and what is explicitly deferred (`SE-02D`, Real AI activation, Live, `N03`/`G6`).

---

## Evidence Gaps

Reported honestly. Each is marked with impact on the verdict.

| # | Gap | Impact |
|---|---|---|
| G1 | **NautilusTrader was not read at raw-source level.** `raw.githubusercontent.com` and `api.github.com/contents` for `nautilus_trader/live/node.py` and `nautilus_trader/system/kernel.py` returned 404 (the repository has been restructured to `python/nautilus_trader/` + `crates/`). Evidence for R6 is the **official** API reference (`nautilustrader.io/docs/python-api-nightly/system.html`, exact members `start_async`/`stop_async`/`dispose`/`cancel_all_tasks`) and the **official** architecture guide, plus third-party line-level cross-references (DeepWiki) that were **not** independently verified. | **Non-blocking.** The task requires at least 2 mature trading runtimes at source level; R7 (Hummingbot) and R8 (Freqtrade) are full raw-source reads. R6's conclusions are architectural patterns corroborated by two independent official sources, and no NautilusTrader *code* is proposed for reuse (LGPL-3.0 ⇒ pattern-only). If Formal Design wants line-level Nautilus citations, it should re-fetch from the restructured paths. |
| G2 | FastAPI/Starlette/Uvicorn docs were fetched as of the live web on 2026-09-15; the local installed versions may differ. `requirements.txt` pins `fastapi>=0.116,<1` / `uvicorn[standard]>=0.35,<1` — ranges, not exact versions. | **Non-blocking for design.** A pin-level re-verification (installed `fastapi` / `starlette` / `uvicorn` / `anyio` versions) belongs to the implementation window. Note the one behaviour that is version-sensitive in this report: `Starlette` dict-style `request.state["x"]` was introduced in 0.52.0. |
| G3 | No runtime execution was performed (strictly forbidden). All lifecycle claims are read from source and from accepted `dev_log` evidence, not from a live host. | **Non-blocking** — this task is explicitly evidence-input research; execution belongs to a later, separately authorised window. |
| G4 | The per-subsystem failure policy for `ScannerPipeline` / `SafetyRuntime` has not been enumerated line-by-line against every exception type; the report cites the accepted semantics (`DECISIONS.md`, `supervised_worker`) rather than a complete exception matrix. | **Non-blocking** — but it is precisely Open Question 4, so Formal Design must resolve it rather than assume it. |
| G5 | The exact N01-8 raw evidence files live outside the repository (accepted as such: `AICONTEXT`/dev_log reference external evidence paths). Counts such as `99/99 checks` and `24/24 checkpoints` are taken from the accepted closeout documents, not re-derived here. | **Non-blocking** — those are accepted facts with an accepted provenance chain; re-derivation would be a re-verification task, out of this scope. |
| G6 | `frontend/` (1561 files) was not inspected; it has no bearing on the runtime host. | **Non-blocking**, disclosed for completeness. |

---

## Research Verdict

# READY FOR FORMAL DESIGN

Justification (against the Acceptance Criteria):

- AC-01/AC-02: global protocol and project truth verified in real time; no fail-closed condition triggered.
- AC-03: Integrated Runtime Host = `NOT STARTED` confirmed from repository truth; N01 overall = `ACCEPTED / COMPLETE`; the Accepted Claim Boundary explicitly excludes a production Integrated Runtime Host.
- AC-04/05/06: ownership map, harness-vs-production boundary and gap map complete, all with file/line-level evidence.
- AC-07…AC-11: FastAPI/Starlette, Uvicorn (including raw `lifespan/on.py`, `server.py`, `config.py`), asyncio/AnyIO, and 2 trading runtimes read at raw-source level (Hummingbot, Freqtrade) plus a third at official-docs level (NautilusTrader); every reference carries a specific traceable source.
- AC-12…AC-15: reuse classification, reusable parts, custom minimum and the NOT-REQUIRED list are all evidence-linked.
- AC-16/17: four placement options and ten lifecycle/failure questions answered with evidence and trade-offs, no decision frozen.
- AC-18: the P2 observation requirement is mapped to the frozen condition's own inputs, and the finding is untouched.
- AC-19: zero mutation of repository / Git / DB / runtime / local AI tooling (see the close-out section below).
- AC-20: no formal architecture decision is stated. Every option is presented as evidence.
- AC-21: the next Design AI can enter Formal Design directly; Section "Open Questions For Formal Design" is the intended input list, and no further wide research sweep is required. Evidence gaps G1–G6 are disclosed and none blocks design.

---

# Close-Out — READ_ONLY Compliance

## Result
IRH-PRE-01 research report produced as Evidence Input. Verdict: `READY FOR FORMAL DESIGN`. No architecture decision, no implementation, no `N01-9`, no `SE-02D`, no Live, no Real AI activation.

## Changes
**NONE inside any repository.** Verified: no file under `E:\Documents\MarketPulse AI` or `E:\Documents\MarketPulse-AI-*` was created, modified or deleted; no branch, worktree, commit, push or ref update; no PostgreSQL start; no FastAPI start; no OKX runtime; no soak; no prototype host; no Docker action; no change to production code / tests / docs / config / DB / Git state / runtime state / local project memory / `.workbuddy` memory / skills / agent rules.

Note on pre-existing state: the session cwd (`E:\Documents\MarketPulse AI`) was **already dirty before this task began** (20 modified + 5 deleted tracked files, plus untracked `.workbuddy/` and `scripts/_g54_selfreview.py`). This task neither created nor touched any of those; local uncommitted work was preserved exactly as found. The evidence anchor worktree remained byte-identical and clean throughout.

The only write performed was the report file itself, deliberately placed **outside** all repositories (matching the project's existing precedent of non-repository evidence at `E:/Temp/...`):
`E:\Temp\IRH-PRE-01-Reference-Research-Report.md`

## Verification
- Reference reads: `git ls-remote origin refs/heads/main` == `git rev-parse main` == navigation value == anchor worktree HEAD (`1e7eeb2a`); anchor worktree `git status --porcelain` empty.
- Session cwd (`d47313a1`, branch `prb-01-product-requirements-baseline`) inspected, confirmed **not** `main` and **dirty** (pre-existing local modifications), and therefore **not** used as a truth anchor for any evidence in this report.
- Post-task re-verification: anchor worktree `git status --porcelain` **empty**, HEAD still `1e7eeb2a`; worktree count unchanged (24). The session cwd's dirty set is unchanged in kind and is pre-existing, not produced by this task.
- Repository truth read from the anchor worktree: `AGENTS.md`, `AI_CONTEXT.md`, `PROJECT_STATE.md`, `PRODUCT_REQUIREMENTS.md`, `DECISIONS.md`, `dev_log/2026-09-14-n01-overall-final-acceptance-closeout.md`.
- Source read: `api/app.py`, `api/auth.py`, `api/market.py`, `main.py`, `runtime.py`, `config.py`, `clock.py`, `db/session.py`, `g2/runtime.py`, `g2/repository.py`, `market_data/okx_live.py`, `market_data/base.py`, `g3/service.py` (index), `g4/orchestrator.py`, `g4/control.py`, `g4/recovery.py`, `g4/reevaluation.py`, `g4/incidents.py`, `g4/state.py`, `g4/reconciliation.py`, `g5/replay.py` (composition).
- Harness read: `verify_n01_6_runtime_smoke.py`, `verify_n01_7_medium_soak.py` (memory condition), `verify_n01_8_extended_soak.py`, `backend/tests/test_n01_okx_paper_safety.py` (`LivePaperHarness`).
- Protocol read: `AI_BOOTSTRAP.md`, `AI_DEVELOPMENT_PROTOCOL.md`, `PROJECT_REGISTRY.md`, `CHANGELOG.md` (via authenticated GitHub API on the real-time `main`).
- **Not executed** (and explicitly marked as not executed): any runtime, any test suite, any migration, any soak, any container, any network call to OKX. Therefore no PASS/FAIL runtime claim is made anywhere in this report.

## Remaining / Blockers
No blockers. Six disclosed evidence gaps (G1–G6); none blocks Formal Design. G1 (NautilusTrader source-level access, caused by the upstream repository restructure) is the only one that would need a fresh fetch if line-level Nautilus citations are wanted.

## Evidence
- `E:\Temp\IRH-PRE-01-Reference-Research-Report.md` (this report; outside all repositories)
- Protocol repo real-time truth: `git ls-remote https://github.com/zwmhua2-lab2/ai-dev-protocol.git refs/heads/main` → `e92fcc381baaf314a6c0f5687b1353ac6c06a748`
- Project real-time truth: `git ls-remote origin refs/heads/main` → `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`
- Evidence anchor worktree: `E:\Documents\MarketPulse-AI-n01-overall-final-closeout` @ `1e7eeb2a` (clean)
- External sources: FastAPI `advanced/events/`; Starlette `lifespan/`; uvicorn `lifespan/on.py`, `server.py`, `config.py`, `docs/settings.md`; CPython `asyncio-task.html`, `asyncio-runner.html`; AnyIO `tasks.html`, `why.html`, plus Starlette `pyproject.toml` (proving `anyio>=4.0.0,<5` is a hard dependency); Hummingbot `hummingbot_application.py`, `core/trading_core.py`, `client/command/stop_command.py` (Apache-2.0); Freqtrade `freqtrade/worker.py` (GPL-3.0); NautilusTrader official architecture + API reference, license endpoint (LGPL-3.0)

**STOP.** No Formal Architecture Freeze, no Runtime Host implementation, no `SE-02D`, no Real AI implementation, no Live, no repository modification, no local AI memory/skill modification. Return this report to the overall progress window; the Design AI decides whether to proceed to `IRH Formal Design / Scope Freeze`.
