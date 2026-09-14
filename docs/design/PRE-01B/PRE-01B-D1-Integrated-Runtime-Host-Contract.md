# PRE-01B-D1 Integrated Runtime Host Contract

## Artifact Status

```text
Artifact: PRE-01B-D1 Integrated Runtime Host Contract
Status: ACCEPTED / COMPLETE
Human Acceptance: CONFIRMED — 2026-09-15
Human-Accepted reviewed candidate: 80cb2babe9f55b3a3b1dc2d3b7913a405607ac22
Independent Review: PASS WITH NON-BLOCKING FINDINGS
P0 / P1: NONE
Task type: FORMAL DESIGN / ARCHITECTURE CONTRACT / DOCS ONLY
Implementation authorized by this artifact: NO
Runtime activation authorized by this artifact: NO
```

本文件冻结 `MarketPulse Integrated Runtime Host V1` 的 Candidate Architecture Contract。它不把
Candidate 写成 Accepted，不实现或启动 Runtime，不修改任何已验收交易、风险、恢复、对账、会计或
AI 语义。

## Repository Truth

### 实时基线

| 项目 | 实时事实 |
|---|---|
| Global Protocol repository | `zwmhua2-lab2/ai-dev-protocol` |
| Global Protocol remote `main` | `e92fcc381baaf314a6c0f5687b1353ac6c06a748` |
| Protocol Version / Status | `1.0.0` / `ACCEPTED` |
| Project repository | `zwmhua2-lab2/MarketPulse-AI` |
| Project remote `main` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| Project local `main` / `origin/main` | both `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| Task dispatch navigation SHA | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| Baseline drift | `NO` |
| Candidate branch | `design/pre-01b-d1-runtime-host-contract` |

任务开始时根工作区位于历史 branch 且有大量既存修改。本设计在基于 verified `main` 的独立 clean
worktree 中完成；未 reset、rebase、覆盖或归因根工作区修改。

### 当前实现事实

- `FastAPI` app 没有 `lifespan`，模块导入时创建独立 `GlobalRuntimeState`，不拥有交易 Runtime。
- `db/session.py::create_session_factory()` 丢失 engine handle，当前无 production engine dispose owner。
- `EventRuntime` 已有 bounded `PriorityQueue`、finite workers、per-instrument serialization、
  `start()` / `stop()` 和 bounded dedupe / worker exception retention。
- `ScannerPipeline` 会等待 `EventRuntime.publish()`；若与保护链共用同一消费循环，G2 backpressure
  会延迟下一条 protective BBO。
- `SafetyRuntime.on_market_data()` 已冻结为同 instrument 内 protection → open-order processing，AI
  reevaluation 在 critical section 外，且 inflight coalescing 已存在。
- `RecoveryManager.recover()` 只从 PostgreSQL 恢复，并在 recovery 内执行 reconciliation、active
  symbol fresh-BBO 检查、plan/order revalidation 与 protection restore；因此 active risk 存在时，
  recovery 前必须已有只读 live BBO warm-up。
- `OKXLiveProvider.stream()` 已实现 cancellation-safe indefinite reconnect；Host 仍需拥有 stream
  lifetime，并用 freshness 而非“task still alive”判定 readiness。
- `G3Workflow` 主要由 Replay 路径构造；live Opportunity → G3 未接受、未激活。
- `BoundedAITaskQueue` 有 production 定义，但无正式 live consumer lifecycle，且不满足
  PRE-01A-D1 的完整 durable invocation/deadline contract。
- N01 overall = `ACCEPTED / COMPLETE`；Integrated Runtime Host = `NOT STARTED`；N01-7-R01-RR-P2-01
  = `REMAINS / NON-BLOCKING`。

## Problem Statement

当前已有组件能在测试/Replay/验证 harness 中组合，但 production 不存在唯一 composition root。由此
无法证明：只有一个 Runtime、engine 一定释放、child task 有 owner、恢复先于新增风险、HTTP alive
不冒充 trading ready、shutdown 有界、失败会一致地 fail closed。

V1 需要补的是一个最小 lifecycle/ownership 层，而不是第二套交易系统、通用工作流引擎或进程
supervisor。

## Accepted Inputs / Invariants

以下输入保持原义，不由本设计重写：

1. Paper Trading only；Spot Paper LONG only；Live Trading disabled。
2. AI = advisory；deterministic Risk Engine / `SystemRiskGate` = authoritative。
3. Protection / risk-reducing action 不得等待 AI；AI 失败不得移除既有 SL/TP。
4. PostgreSQL = restart/recovery durable source of truth；Recovery 不从 memory 猜测。
5. Reconciliation = detector, not repair；No fabricated historical fills。
6. Operator Intent 与 System Derived State 分离；Host state 不替代或重定义 G4 durable state。
7. `TradePlan.invalidation` 仍是 advisory text；`stop_loss` 仍是唯一 machine-enforceable hard
   price invalidation。
8. PRE-01A-D1 的 `decision_deadline_at` 是 future Real AI invocation 的 absolute deadline；本设计
   不新增 Real AI business timeout 数值。
9. Real AI provider implementation/activation、SE-02D、Live、schema/migration、策略/Scanner/Risk/
   accounting semantic change 全部不在本任务。
10. Memory P2 watch item 保持 `REMAINS / NON-BLOCKING`，不得以新增 telemetry 宣称 resolved。

## Research Evidence Used

### Repository evidence

- `docs/research/PRE-01B/PRE-01B-Runtime-Host-Research-Verdict.md`：Research Verdict / Design Input。
- `docs/research/PRE-01B/PRE-01B-IRH-Reference-Research-Evidence.md`：Worker research evidence；未直接
  升级为 Architecture Decision。
- `backend/src/marketpulse/api/app.py`、`runtime.py`、`db/session.py`、`g2/runtime.py`、
  `g3/service.py`、`g4/orchestrator.py`、`g4/recovery.py`、`market_data/okx_live.py`：本窗口复核。
- N01 harness：只作为 wiring / validation evidence，不复制为 production Host。
- PRE-01A-D1 Accepted Contract：只继承 AI authority、deadline、identity 与 activation gate 边界。

### External evidence and adjudication

- FastAPI official lifespan documentation：`lifespan` 是 app-scoped startup/shutdown resource
  boundary；采用。
- Starlette lifespan semantics：serving 前完成 startup、teardown 位于 application lifespan；采用其
  lifecycle placement，不把它当 process supervisor。
- AnyIO official task-group semantics：structured child ownership、sibling cancellation、
  `TaskGroup.start()` readiness handshake、cancel scope；采用为唯一 Host structured-concurrency model。
- Uvicorn：继续作为 ASGI server/signal boundary；不承担 trading child restart policy。
- Hummingbot / Freqtrade / NautilusTrader：仅学习 single owner、ordered cleanup、transient-vs-terminal
  classification、dispose-before-rebuild；不复制其 framework 或代码。
- WinSW：仅作为 Windows future process-supervision candidate；不进入 V1 Host Core。

结论：现有 FastAPI/Starlette/AnyIO/Uvicorn + accepted MarketPulse components 足够；不需要 Kafka、
Redis、Celery、Kubernetes、LangGraph、generic workflow engine 或新 trading framework。

## Goals

- 一个 app-scoped、可测试、唯一的 `RuntimeHost` owner。
- 确定的 construct/start/recover/ready/stop/dispose 顺序。
- protection lane 与 scanner/advisory backpressure 隔离。
- 明确 transient、degraded、fail-closed 与 fatal failure。
- 单进程/单 Runtime enforcement 与外部 supervisor 边界。
- 最小可观测 lifecycle/resource surface。
- 为下一 Implementation Batch 冻结一个可独立验收的小 vertical slice。

## Non-Goals

- Live Trading、short execution、SE-02D、Real AI provider implementation/activation。
- live Opportunity → G3 handoff implementation。
- G3/G4/Scanner/Risk/accounting/recovery/reconciliation business semantic redesign。
- schema/migration、UI redesign、multi-provider fallback、model voting、Agent Runtime。
- Kafka、Redis、Celery、Kubernetes、microservices、new trading framework。
- repo 内 process restart/backoff supervisor、WinSW packaging、Docker mandatory deployment。
- 12-hour soak、Memory P2 closure或完整 observability platform。

## V1 Architecture Decision

```text
Placement                    = Option B
Composition owner            = RuntimeHost object
Lifecycle anchor             = FastAPI lifespan
Structured concurrency       = AnyIO TaskGroup / CancelScope only
Process model                = one OS process / one Uvicorn worker / reload off
Duplicate-host fence         = PostgreSQL session advisory lock + process policy
Process restart              = external OS/service layer
G2 -> G3 live handoff        = DEFERRED
Real AI                      = NOT CONSTRUCTED / NOT ACTIVATED
Periodic reconciliation      = INCLUDED
OS/service wrapper           = FUTURE DEPLOYMENT TASK
```

`RuntimeHost` is the only production composition root. FastAPI lifespan creates exactly one Host, enters
`host.lifecycle()`, publishes a read-only host reference via `app.state`, yields to requests, then exits the Host
lifecycle. Route handlers never create long-lived engines, providers, queues or workers.

Host lifecycle is explicit and idempotency-strict:

- `CREATED -> ... -> READY/DEGRADED/FAIL_CLOSED -> STOPPING -> STOPPED`
- second `start`/second lifecycle entry is an invariant violation；不得 silent double-start。
- `stop()` / context exit may be invoked again only as cleanup and must not double-dispose resources。
- a new Host may start in the same process only after the prior Host reaches `STOPPED` and releases DB lock,
  provider, tasks and engine。

## Process Model

### Frozen V1 policy

- Single OS process。
- Uvicorn `workers = 1`。
- `reload = false` whenever Integrated Runtime Host is enabled。
- `runtime_host_enabled = false` by default；implementation does not equal activation。
- Enabled production Host requires explicit `RUN_MODE=LIVE_PAPER`, `LOCAL_ONLY=true`, approved disposable/
  non-Production DB for acceptance, and configured `BTC-USDT` / `ETH-USDT` SPOT subscription set。
- `TEST` constructs Host only through injected test dependencies；it must not construct real OKX or Real AI。

### Enforced duplicate fence

`RuntimeHost` acquires a dedicated PostgreSQL connection and `pg_try_advisory_lock()` on a stable namespace +
`run_mode` key before any market ingress. It holds that session lock for the Host lifetime. Failure to acquire is
fatal startup (`DUPLICATE_RUNTIME_HOST`)；it must not wait and must not start a second Runtime. Connection loss is a
fatal Host invariant because the cross-process fence is gone. The lock is released explicitly during shutdown and
implicitly by PostgreSQL on process death。

This lock is defense-in-depth, not a replacement for `workers=1` / reload-off deployment policy, and requires no
schema/migration。

## Host Placement

### Selected: Option B — independent `RuntimeHost`, owned by FastAPI lifespan

Why：

- separates MarketPulse composition policy from ASGI glue while preserving first-party lifecycle timing；
- unit/integration tests can enter Host without starting a server；
- one object can expose ownership, state, readiness and deterministic disposal；
- FastAPI routes receive the same Host reference via `app.state`, avoiding a second module global；
- fits one developer and the Modular Monolith。

### Not selected

| Option | Verdict | Reason |
|---|---|---|
| A. Lifespan directly composes every component | Rejected for V1 | low code count but turns `api/app.py` into a large untestable composition script and obscures ownership/state transitions |
| C. Separate trading process | Deferred | stronger isolation but adds IPC, dual health/deployment, duplicated configuration and coordination with no current requirement evidence |
| Hand-written process supervisor | Rejected | duplicates Uvicorn/OS responsibilities and conflicts with minimum sufficient solution |

## Component Ownership Matrix

| Component | Creator | Owner | Start Phase | Ready Condition | Failure Domain | Stop Phase | Dispose Responsibility | Durable Authority | Host Dependency |
|---|---|---|---|---|---|---|---|---|---|
| SQLAlchemy AsyncEngine | `RuntimeHost.build` | RuntimeHost | STARTING | `SELECT 1` succeeds | fatal DB domain | last resource | RuntimeHost `engine.dispose()` | PostgreSQL | root |
| Session Factory | RuntimeHost from owned engine | RuntimeHost | STARTING | engine healthy | DB domain | after all DB users | released with engine | none; factory only | engine |
| Host advisory-lock connection | RuntimeHost | RuntimeHost | ACQUIRING_SINGLETON | lock acquired and connection alive | fatal singleton/DB | after all children, before engine dispose | unlock + close | PostgreSQL session lock | engine |
| `GlobalRuntimeState` / Host state | RuntimeHost | RuntimeHost | CREATED | timestamps/health initialized | Host invariant | terminal snapshot/log | RuntimeHost | in-memory observation only | clock |
| `LiveMarketState` latest BBO accessors | RuntimeHost | RuntimeHost | RECOVERY_INGRESS | required instruments have usable fresh BBO | market-data degradation | after safety drain | clear references | none; never recovery authority | provider/clock |
| `OKXLiveProvider` + stream | RuntimeHost | RuntimeHost | RECOVERY_INGRESS | metadata valid + stream task live + fresh BBO | transient reconnect/stale; unexpected termination fatal | stop ingress first | cancel/aclose stream | exchange facts, not economic authority | settings/task group |
| Per-instrument safety ingress lanes | RuntimeHost | RuntimeHost | RECOVERY_INGRESS (closed gate), STARTING_RUNTIME (open gate) | one finite worker each, queue below capacity | overflow fatal | close then drain first | RuntimeHost | none | provider/SafetyRuntime |
| Scanner ingress lane | RuntimeHost | RuntimeHost | STARTING_RUNTIME | finite worker live | overload isolated/degraded | close/drain after safety | RuntimeHost | none | provider/ScannerPipeline |
| `OpportunityScanner` | RuntimeHost | RuntimeHost | construct | constructed with accepted config | scanner domain | no active stop | drop reference | none | clock/config |
| `PostgresG2Repository` | RuntimeHost | RuntimeHost | construct | session factory available | DB/G2 domain | after EventRuntime | drop reference | PostgreSQL G2 facts | sessions |
| `EventRuntime` | RuntimeHost | RuntimeHost | after recovery | exact configured finite workers live | event-local exception or fatal worker exit | after scanner ingress drain | `EventRuntime.stop()` under deadline | PostgreSQL via repository | G2 repository |
| `ScannerPipeline` | RuntimeHost | RuntimeHost | after recovery | scanner consumer live | isolated scanner lane | before EventRuntime stop | drop bounded in-memory state | PostgreSQL via EventRuntime | scanner/EventRuntime |
| G3 `PaperExecutionService` | RuntimeHost | RuntimeHost | construct before recovery | injected BBO/state accessors + risk gate | execution/safety critical | after final reconciliation | no independent resource | PostgreSQL economic facts | sessions/market state |
| G4 state/incidents/risk/protection/plan/control services | RuntimeHost | RuntimeHost | construct before recovery | accepted dependency graph complete | safety critical | after final reconciliation | no independent resource | PostgreSQL | sessions/execution/health |
| `SafetyRuntime` | RuntimeHost | RuntimeHost | construct before recovery; lane opens after recovery | per-instrument worker live; protection enabled | safety critical | safety ingress close/drain | clear locks/references | delegates to PostgreSQL services | execution/protection |
| Position AI reevaluation | RuntimeHost | RuntimeHost | disabled | `reevaluation_enabled=false` | not active | n/a | none | none | SafetyRuntime |
| `RecoveryManager` | RuntimeHost | RuntimeHost | RECOVERING once/start | returns report and final durable state | logical fail-closed or fatal exception | no periodic task | drop reference | PostgreSQL | market state/G4 services |
| Periodic reconciliation loop | RuntimeHost task group | RuntimeHost | after recovery | first startup reconciliation already complete; loop live | fail-closed on mismatch; DB exception fatal | stop before final reconciliation | task group | detector reads PostgreSQL | sessions/execution/control |
| Heartbeat loop | RuntimeHost task group | RuntimeHost | after recovery | first heartbeat committed | DB exception fatal | before final reconciliation | task group | `runtime_control.heartbeat_at` | state service |
| G3 live advisory handoff/AI queue | none in V1 | none | DEFERRED | n/a | n/a | n/a | n/a | future PRE-01A durable facts | explicit future batch |
| OS/service supervisor | external | OS/service layer | outside process | process policy | process domain | OS stop | external | service config/logs | RuntimeHost exit signal |

`SystemRiskGate` remains the only risk-increasing authority；Host owns its lifecycle but never bypasses or replaces it。

## Dependency Graph

```text
FastAPI lifespan
  -> RuntimeHost
      -> Settings + Clock + GlobalRuntimeState
      -> AsyncEngine -> SessionFactory -> Host advisory-lock connection
      -> LiveMarketState <---------------- OKX recovery ingress
      -> G4 services
           -> PaperExecutionService -> bbo_for / state_version_for
           -> SystemRiskGate
           -> PositionProtectionService
           -> SafetyRuntime (Real AI reevaluation disabled)
           -> RecoveryManager -> reconcile(detector)
      -> G2 PostgresRepository -> EventRuntime -> ScannerPipeline
      -> AnyIO TaskGroup
           -> OKX stream driver
           -> finite per-instrument safety workers
           -> one scanner ingress worker
           -> EventRuntime worker monitor
           -> heartbeat loop
           -> periodic reconciliation loop
           -> telemetry sampler

External OS/service supervisor -> one Uvicorn process -> FastAPI lifespan
```

Critical path ordering for every live BBO is：

```text
OKX normalized BBO
  -> update LiveMarketState
  -> enqueue exact BBO to that instrument's bounded safety lane (must succeed)
  -> scanner lane try-send (may reject under overload; never blocks safety)

safety worker -> accepted SafetyRuntime
              -> protection
              -> open-order processing
              -> (AI reevaluation disabled)
```

Scanner processing cannot occupy, await or fill the safety lane。No Host path is
`market event -> AI -> protection`。

## Startup State Machine

### Host states

```text
CREATED
  -> STARTING
  -> ACQUIRING_SINGLETON
  -> RECOVERY_INGRESS
  -> RECOVERING
  -> STARTING_RUNTIME
  -> WAITING_FOR_READINESS
  -> READY | DEGRADED | FAIL_CLOSED

any unexpected critical exception -> FAILED -> bounded cleanup
READY/DEGRADED/FAIL_CLOSED -> STOPPING -> STOPPED | STOP_FAILED
```

Host states are in-memory lifecycle facts and must not add aliases to G4 `SystemState`。Readiness derives from both
Host state and current durable G4 state。

### Deterministic startup order

`startup_timeout_seconds = 60` (positive finite setting; one absolute monotonic startup deadline)：

1. Validate explicit enable gate、`LIVE_PAPER`、local-only、BTC/ETH SPOT subscriptions、one-worker/no-reload
   operational contract；Real AI config is not read or instantiated。
2. Construct owned engine/session factory; set unique redacted `application_name`; execute bounded DB connectivity
   probe。
3. Acquire dedicated PostgreSQL advisory-lock connection；duplicate or lost lock fails startup。
4. Construct one `GlobalRuntimeState`、`LiveMarketState`、accepted G2/G3-execution/G4 service graph、
   `RecoveryManager` and bounded lanes。Long-lived resources remain closed。
5. Fetch OKX public SPOT metadata and verify configured instruments/tradability。Start one provider stream task in
   `RECOVERY_INGRESS` mode：only update latest market state and freshness telemetry；do not call Scanner、AI or risk-
   increasing path。
6. Load durable active symbols。For each active-risk symbol, wait for a current usable BBO within the shared startup
   deadline。No synthetic/stale quote may satisfy this gate。
7. Call `RecoveryManager.recover()` exactly once using Host-owned `bbo_for`。It performs durable recovery、startup
   reconciliation、plan/order revalidation and protection restore with accepted semantics。
8. Start `EventRuntime` once。Start finite safety workers、scanner worker、EventRuntime monitor、heartbeat、periodic
   reconciliation and telemetry sampler inside the one AnyIO task group。
9. Atomically switch stream routing from recovery-only to runtime ingress。No buffered warm-up frame is replayed as a
   new G2 event；future fresh frames flow normally。
10. Evaluate readiness。Only if all Ready Conditions below hold may Host transition to `READY`。A durable PAUSED/
    SAFE_MODE/EMERGENCY state starts protective runtime but remains non-ready/fail-closed。
11. Only after the lifespan startup block completes may FastAPI serve requests。

Runtime MUST NOT become READY before DB singleton fencing、recovery、startup reconciliation、freshness、finite worker
startup and durable state gates all pass。

## Readiness Contract

### Definitions

| Surface | Meaning | HTTP contract |
|---|---|---|
| Liveness | ASGI process/event loop and Host control task are alive; says nothing about trading readiness | `/api/v1/live`: `200` while alive |
| Readiness | all risk-increasing prerequisites currently safe | `/api/v1/ready`: `200` only when `ready=true`, otherwise `503` |
| Degraded | Host alive; noncritical subsystem impaired; no claim of full readiness | health payload status `DEGRADED`; readiness normally `503` |
| Fail-Closed | Host keeps diagnostics/protection where possible, but rejects all new risk-increasing work | readiness `503`, explicit safe reason codes |

API process alive is never equivalent to Runtime READY。

### READY is a conjunction

All are required：

- Host state `READY` and enable gate true。
- advisory lock connection alive and held。
- DB health `HEALTHY`；latest heartbeat committed。
- Recovery completed in this process and durable `system_state=RUNNING` with `operator_state=NORMAL`。
- startup reconciliation `ok=true`；no unresolved blocking incident。
- OKX stream child alive；every configured/active-risk instrument has tradable `DataQuality.FRESH` BBO no older than
  accepted 5 seconds。
- all safety workers、scanner worker、EventRuntime workers、reconciliation and heartbeat tasks live。
- no safety queue overflow、no fatal EventRuntime worker exit、no Host invariant violation。
- risk gate's existing blocking health set is healthy。

Provider reconnect or any stale required instrument changes Host to `DEGRADED/FAIL_CLOSED` and readiness to 503；
freshness recovery may return Host to READY only after all conjuncts are re-evaluated。It must not clear durable
SAFE_MODE/incidents automatically。

Recovery incomplete means no risk-increasing work。Recovery logical failure keeps the API/protective lane available when
possible but reports `FAIL_CLOSED`。DB-unavailable startup cannot complete lifespan and is fatal。

Health responses may expose only stable reason codes、component status、safe counters/timestamps and redacted Runtime
identity。They must not expose DB DSN、credentials、API keys、raw prompts/responses、exception messages or external
account data。

## Failure Classification Matrix

| Failure | Isolate / Retry | Degrade / Fail Closed | Fail Host / External restart |
|---|---|---|---|
| Expected transient provider disconnect | isolate inside existing `OKXLiveProvider.stream()`; reconnect with its bounded delay; no Host child restart loop | immediately freshness-watch; stale required symbol => readiness 503 and reject new risk | no, unless stream task exits/violates contract |
| Market data STALE / unusable | keep stream/reconnect and protection lane alive; accept later fresh BBO | `CORE_MARKET_DATA=UNAVAILABLE`, fail closed for new risk; no stale protection/execution fact | no automatic restart |
| EventRuntime per-event `Exception` | existing worker records bounded exception and completes publisher future exceptionally | scanner lane degraded; affected event creates no downstream risk; repeated overload remains visible | no, unless worker task exits |
| EventRuntime worker unexpected exit | no in-process worker restart | close risk admission | yes; critical monitor fails Host, external process restart/recovery required |
| DB unavailable at startup | no blind business retry inside Host startup | no READY, no risk | yes; lifespan startup fails after bounded probe |
| DB unavailable/lost singleton connection at runtime | do not retry ambiguous economic operations; set DB unavailable | fail closed immediately | yes; cancel Host and rely on restart/recovery |
| Recovery logical `ok=false` / durable SAFE_MODE or PAUSED | no repair; keep market/protection/API if construction is valid | `FAIL_CLOSED`; readiness 503; Human recovery/resume contract remains authoritative | no automatic process restart |
| Recovery unexpected exception | best-effort accepted safe-mode/error reporting; no partial admission | fail closed | yes after bounded cleanup |
| Startup reconciliation mismatch | RecoveryManager opens/retains accepted incident/state semantics | SAFE_MODE/FAIL_CLOSED; detector only | no automatic restart; Human correction required |
| Periodic reconciliation mismatch | call accepted `SystemControlService.enter_safe_mode()` once/idempotently; keep detector reports | FAIL_CLOSED; never auto-repair/auto-resume | no, unless DB/critical task itself fails |
| AI advisory timeout/failure | no active G2→G3 AI in V1；future invocation isolates/cancels against one absolute deadline | AI auxiliary degraded; result cannot add risk; protection continues | no |
| Protection / execution safety unexpected exception | no ambiguous automatic economic retry | execution unavailable; fail closed | yes; external restart/recovery required |
| Host internal invariant / duplicate Host / queue contract breach | no retry in same Host | close risk admission | yes；deterministic nonzero failure signal |
| Shutdown step failure | continue best-effort later independent cleanup steps and aggregate errors | terminal `STOP_FAILED` | process exits nonzero after resource cleanup attempt |

No category uses generic “catch and continue”。Business-denial outcomes are not exceptions and retain existing
semantics。

## G2 → G3 Live Handoff Decision

```text
Decision: DEFERRED from Integrated Runtime Host V1 / first Implementation Batch
```

Reason：

- Runtime Host is complete and independently useful when it owns DB、recovery、protection、live market ingress、G2
  Scanner、health and shutdown；这些是 lifecycle correctness，而不是 AI activation。
- Current live handoff lacks PRE-01A-D1 required durable invocation/pair/arm/input-binding identity、absolute deadline、
  retry provenance and collision-free final-decision fence。Wiring current `G3Workflow`/`BoundedAITaskQueue` would
  silently create an unaccepted activation path。
- Keeping it out makes the first slice small and proves Protection/runtime safety before provider cost/latency is added。

Explicit future boundary：a separately approved implementation batch may add one Host-owned `AdvisoryIngress` after
the exact persisted SETUP/Opportunity boundary。That batch must define producer/consumer identity、bounded queue、
reject/coalesce policy、absolute deadline propagation、durable duplicate/late-result fence、shutdown/cancellation、
stale Opportunity handling and AI failure semantics, and must satisfy PRE-01A-D1 Gate A prerequisites。It must not
modify the safety lane or make protection await advisory work。

No G2→G3 queue、consumer、DecisionService、Real AI provider or plan creation is constructed by Host Core V1。

## AI Deadline / Cancellation Contract

Host Core V1 has no active AI task and therefore invents no AI timeout number。The future advisory batch must carry the
same immutable UTC `decision_deadline_at` from producer to every attempt。At each boundary it computes remaining time
from the accepted clock and maps that remaining duration once into the AnyIO monotonic cancel scope (`fail_after` /
equivalent)。Retries share the original deadline；they do not reset it。

Required future semantics：

- expired at enqueue/dequeue => reject as expired, zero new risk；
- cancellation/timeout => cancel provider I/O, record the approved attempt/final provenance, zero new risk；
- completion after deadline => retain only allowed audit evidence and fail the durable late-result fence；
- shutdown closes advisory admission first and cancels unfinished advisory work；
- provider cancellation cannot cancel or block protection/safety tasks；
- numeric decision timeout remains `NEEDS HUMAN DECISION / PROVIDER ACTIVATION INPUT` under PRE-01A-D1。

## Backpressure Contract

| Queue/lane | V1 capacity authority/default | Producer behavior when full | Consumer / priority | Shutdown |
|---|---|---|---|---|
| per-instrument safety lane | `Settings.runtime_safety_queue_capacity = 64` | `send_nowait`; full is fatal safety overload, close risk admission and fail Host; never drop/coalesce a protective BBO | exactly one FIFO worker per configured instrument | close ingress, drain within shared deadline |
| scanner ingress lane | `Settings.runtime_scanner_queue_capacity = 2048` | `send_nowait`; reject newest input, increment rejection counter, mark degraded; never block safety/provider driver | one FIFO scanner worker | close, bounded drain; cancel remainder on deadline |
| existing `EventRuntime.queue` | accepted `queue_capacity = 2048` | only scanner worker may await it；cannot block safety lane | existing priority + 4 finite workers | existing `stop()` under Host deadline |
| future G3 advisory queue | none | DEFERRED | none | none |

All capacities must be positive finite values validated before acquisition。The Host may make these operational values
configurable but must not silently substitute unbounded queues。Changing capacities does not change overload semantics
and requires targeted validation。

Safety-lane fullness is fatal rather than lossy because dropping/coalescing an intermediate BBO could erase a real
protective threshold crossing。Scanner fullness may reject because missing a new opportunity is fail-closed and cannot
increase economic risk。

## Protection Isolation Contract

1. `SafetyRuntime` accepted ordering remains unchanged：protection → open-order processing → optional reevaluation。
2. One safety worker per instrument preserves order；no scanner/AI lock is acquired。
3. Market driver updates latest BBO, enqueues safety first, then attempts scanner enqueue。
4. Scanner overload or future AI overload cannot block/enqueue into/cancel safety lane。
5. Real AI reevaluation is disabled in the first Host implementation；no fake provider result is treated as production
   evidence。
6. If reevaluation is later authorized, existing critical-section exit + inflight coalescing remains mandatory and the
   provider await stays outside protection lock。
7. Stale/missing/invalid data cannot authorize new risk；fresh risk-reducing path remains available whenever accepted
   execution prerequisites are available。

## Recovery / Reconciliation Contract

- Host constructs `RecoveryManager` once and invokes `recover()` once per process start before risk admission。
- PostgreSQL remains the only durable source；warm-up BBO is current external evidence, not recovered economic state。
- Warm-up frames are not replayed into Scanner and do not fabricate historical fills/events。
- Recovery's internal reconciliation remains detector-only；Host does not interpret diagnostics into repairs。
- Recovery non-running final state is honored。Host may keep protection/API alive but readiness stays false and risk
  admission closed。
- Periodic reconciliation is INCLUDED at `runtime_reconciliation_interval_seconds = 60`。A mismatch invokes accepted
  safe-mode/incident service; it never edits accounting facts or auto-clears the latch。
- Periodic success after a mismatch does not auto-resume。Existing Human safe-mode recovery/resume gate remains required。
- Final reconciliation runs after ingress/queues/workers stop and before DB disposal, if the shared shutdown contract
  still permits DB access。Mismatch is reported and latched; no repair occurs。
- No Host restart path reuses in-memory Queue、dedupe、quote or task facts。A new process repeats durable recovery and
  receives only new live frames。

## Graceful Shutdown Contract

### Deadlines

- graceful phase：one absolute monotonic `shutdown_grace_seconds = 30`。
- escalation cleanup reserve：`shutdown_dispose_seconds = 5` in a shielded cancel scope for provider close、advisory
  unlock/connection close and engine dispose。
- deployment `timeout_graceful_shutdown` must be at least 40 seconds；otherwise server timeout would undercut Host
  cleanup contract。

### Deterministic order

1. Atomically set Host `STOPPING`；close all risk-increasing admission and reject new work。
2. Close/cancel new advisory work（none in Host Core V1）。
3. Stop new market ingress：close stream routing and cancel/aclose provider stream after no further enqueue can occur。
4. Close safety send ends and drain already accepted per-instrument BBOs first within the shared deadline。
5. Close scanner send end；drain accepted scanner items, then call accepted `EventRuntime.stop()` so its queue/futures
   reach terminal state。
6. Stop heartbeat、periodic reconciliation、telemetry and monitors；normal tasks must acknowledge completion。
7. Verify no Host-owned task/worker remains；cancel stragglers at grace expiry。Cancellation is escalation, not success。
8. Run final detector-only reconciliation if DB and remaining deadline permit；mismatch latches/report safe mode, never
   repairs facts。
9. Close/aclose provider resources and clear market-state references。
10. Release advisory lock and close its connection；dispose engine last。
11. Record terminal `STOPPED` only when all required cleanup succeeds；otherwise `STOP_FAILED`, aggregate sanitized
    failures and return a nonzero process signal。

No background task may wait forever。A normal stop proves all queues drained、EventRuntime workers zero、Host task set
empty、provider socket closed、pool checked-out zero and engine disposed。

## Process Supervisor Boundary

`RuntimeHost` owns only in-process construction、readiness、failure propagation、graceful shutdown and deterministic
exit signal。It does not restart its own critical child after unexpected termination and does not restart the process。

External OS/service layer owns：auto-start、boot integration、crash restart、restart delay/backoff、process log
handling and OS stop signal。Uvicorn maps the signal into ASGI lifespan shutdown；a future service wrapper watches its
exit code。

WinSW classification：`FUTURE DEPLOYMENT TASK`，not V1 required，not part of first Implementation Acceptance Batch。
No repo-local supervisor is built。Docker is not mandatory。

## Memory P2 Observation Contract

The Host exposes a read-only, bounded current snapshot and lifecycle counters；it does not build a metrics platform。

Minimum snapshot：

- process RSS bytes/MiB；
- event-loop task count and Host-owned task names/count；
- EventRuntime configured/live/done worker counts；
- safety/scanner/EventRuntime queue size + capacity + high-water mark + rejected/overflow counters；
- EventRuntime inflight、dedupe size/capacity、worker-exception size/capacity；
- Scanner trade dedupe and other explicitly bounded retention size/capacity；
- SafetyRuntime reevaluation inflight（zero/disabled in first slice）；
- provider connection attempts/reconnects、stream status、last event/fresh BBO timestamps；
- process TCP socket count and Windows handle count（aggregate only）；
- SQLAlchemy pool checked-in/checked-out/overflow plus dedicated singleton-lock connection；
- Host monotonic uptime、state、created/start/recovery-ready/degraded/stop timestamps；
- latest reconciliation/heartbeat timestamps and sanitized result codes。

`psutil` is the minimal cross-platform process RSS/socket/handle probe and must be declared as a direct production
dependency if imported by production code；absence/probe failure reports `UNAVAILABLE`, never zero。DB ownership
acceptance additionally uses an external observer connection to verify `application_name` attribution and final zero
owned sessions；the production endpoint does not need a second permanent observer engine。

Telemetry retains only current snapshot + monotonic counters/high-water marks；no unbounded time series in Host memory。
This surface enables future observation of `N01-7-R01-RR-P2-01` but explicitly leaves it
`REMAINS / NON-BLOCKING`。

## Security / Secret Boundary

- Host is enabled only explicitly and remains local-only in V1；listen `127.0.0.1`。
- Settings/SecretStr values are consumed only at composition boundary；no secret enters Frontend、health、logs or
  exception payloads。
- DB telemetry exposes counts and redacted host instance ID only, never DSN/user/password/query text。
- Provider telemetry exposes public endpoint category/counters, not credentials or raw frames。
- Real AI provider/API key is never constructed/read by Host Core V1。
- `/api/v1/live` and `/api/v1/ready` expose minimal safe facts；detailed runtime telemetry remains behind existing
  authenticated `/api/v1/runtime` boundary。
- Host-owned objects stay in `app.state` and are not serialized or returned directly。

## Implementation Vertical Slice

### First batch: Host Core only

Expected production files to add/modify exactly：

| File | Change |
|---|---|
| `backend/src/marketpulse/runtime_host.py` | add RuntimeHost, host FSM, dependency composition, singleton fence, market-state store, bounded lanes, loops, readiness, shutdown and telemetry snapshot |
| `backend/src/marketpulse/api/app.py` | add app factory/lifespan, app.state Host access, honest live/ready/runtime responses; remove import-time Runtime ownership |
| `backend/src/marketpulse/runtime.py` | extend existing runtime/health data contracts without duplicating G4 business state |
| `backend/src/marketpulse/db/session.py` | return an explicit engine + session-factory resource bundle so Host can dispose the engine |
| `backend/src/marketpulse/g2/runtime.py` | add read-only public telemetry/worker-state access needed by Host; do not change G2 business/state-machine semantics |
| `backend/src/marketpulse/config.py` | explicit enable gate, instruments, finite capacities/intervals/deadlines; defaults keep Host disabled |
| `backend/requirements.txt` | declare direct AnyIO and psutil dependencies used by production Host |

Expected tests/validation artifact：

- add `backend/tests/test_runtime_host.py` for injected/fake unit + PostgreSQL integration tests；
- add `scripts/verify_pre_01b_runtime_host.py` for short explicit disposable-DB + public OKX validation；
- no schema/migration、G3 provider、G4 semantic、Frontend or state-doc change in implementation commit itself except
  the separately required minimal dev log/status workflow for that future batch。

### Included

- Host Core、FastAPI lifecycle、DB ownership/disposal、recovery、SafetyRuntime、G2 scanner runtime、periodic
  reconciliation、health/readiness、bounded shutdown、P2 hooks。
- real public OKX is required only for the short acceptance validation script；not for deterministic test suite。
- disposable PostgreSQL upgraded to current head is required for integration/runtime validation；shared primary is not
  mutated。

### Explicitly excluded from same batch

- OS/service wrapper / WinSW。
- G2→G3 live handoff、`BoundedAITaskQueue` consumer、Real AI provider/activation。
- SE-02D、Forward Outcome evaluator scheduler、new edge/scanner/risk/accounting semantics。
- 12-hour soak and Memory P2 verdict closure。

This is one independent vertical slice：real market facts → Host-owned protection + G2 path → durable PostgreSQL,
with startup/recovery/readiness/shutdown proven；it does not bundle Deployment + AI + SE-02D + long soak。

## Verification Plan

### Unit / deterministic integration

- FSM legal/illegal transitions；double-start rejected；double-stop cleanup idempotent。
- engine/factory/lock ownership；duplicate process/session lock fails before ingress。
- exact startup ordering, recovery-only warm-up, no warm-up replay。
- readiness conjunction and 200/503 API behavior for STARTING/READY/STALE/SAFE_MODE/DB-down/reconnect。
- safety lane precedes scanner enqueue；scanner full does not delay safety；safety full is fatal, not lossy。
- EventRuntime per-event error isolation vs unexpected worker exit fatal behavior。
- provider disconnect/reconnect and stale→fresh transitions using controlled fake stream。
- recovery failure、reconciliation mismatch、DB failure、singleton connection loss。
- normal and forced shutdown at every startup/runtime phase；no orphan tasks/futures/sockets/connections。
- Real AI/provider constructors and G2→G3 consumer call count = 0。
- accepted G2/G3/G4 targeted regression；no business/state-machine/accounting semantic change。

### Real PostgreSQL integration

- task-owned disposable DB only；Alembic `current=head` before run。
- one Host at a time across independent engine/session attempts。
- restart reconstructs from PostgreSQL, not in-memory quote/queue/dedupe；no duplicate economic facts。
- observer proves application-name attribution, bounded pool usage, no idle-in-transaction leak and zero Host-owned
  sessions after stop/failure。
- reconciliation remains detector-only and mismatch latches safe mode without repair。

### Short real-runtime validation

- explicit, non-default enablement；BTC-USDT/ETH-USDT public OKX metadata + trades + BBO；no API key。
- minimum 5 continuous minutes after READY on disposable DB；record startup/recovery/readiness/telemetry/shutdown。
- no Real AI、no Live Trading、no fabricated Fill；no new economic position is intentionally opened。
- controlled provider reconnect and STALE behavior remain deterministic integration tests；natural disconnect is not
  required to occur in the 5-minute real window。
- normal shutdown must leave zero Host tasks/workers/inflight/owned PG sessions and no provider socket。

### Not required in first batch

- 12-hour N01 rerun、long soak、Memory slope verdict、WinSW/service restart、Real AI/provider contract test、SE-02D。

## Acceptance Criteria

Future Implementation is acceptable only with independent evidence for all items：

1. Exactly one Host owns every long-lived resource；no request-scoped engine/provider/runtime。
2. remote/local accepted baseline and implementation scope match the approved batch。
3. one process/one worker/reload-off plus PostgreSQL singleton lock prevent duplicate Runtime instances。
4. startup ordering matches this contract；active-risk fresh BBO warm-up precedes Recovery, and no warm-up event is
   replayed into Scanner。
5. PostgreSQL connectivity、Recovery、startup reconciliation、durable state、freshness and finite workers all gate
   READY。
6. API liveness does not imply readiness；STALE/reconnect/SAFE_MODE/DB failure return honest 503 readiness and reason。
7. normal shutdown follows dependency order and finishes within 30+5 seconds；escalation is reported, not called clean。
8. child failures match the matrix；unexpected critical worker/safety/DB/invariant failure fails Host and produces an
   external-restart signal。
9. transient provider disconnect reconnects without duplicate Host；STALE fails closed and fresh data can restore only
   nondurable readiness conditions。
10. risk-increasing work is impossible before successful Recovery and whenever any readiness blocker exists。
11. no duplicate event/intent/order/Fill/Position/Ledger/economic fact after retry/reconnect/restart。
12. Protection remains independent of Scanner/AI and processes before any risk-increasing downstream handoff。
13. every queue/retention/task/worker set is bounded；scanner overload cannot block protection；safety BBO is never
    silently dropped/coalesced。
14. DB pool and singleton connection are closed on normal/failure/cancelled startup；observer sees zero owned sessions。
15. no orphan AnyIO/asyncio task、EventRuntime worker/future、WebSocket or HTTP client after stop。
16. periodic/final reconciliation remains detector-only；failure enters/retains fail-closed safe state without repair。
17. Memory P2 telemetry includes all fields in this contract and remains observation-only；watch item stays open。
18. FastAPI lifespan is the only Host activation boundary；module import and ordinary request handling create no Runtime。
19. G2→G3 live handoff/Real AI call count is zero；no provider key required/read。
20. current accepted G2/G3/G4 semantics and targeted regressions are preserved。
21. real OKX short validation and real disposable PostgreSQL validation produce complete start-to-dispose evidence；
    unavailable evidence is `NOT VERIFIED`, never inferred PASS。
22. production code、test、config、migration and docs delta stays within the future approved Implementation Scope；
    no main merge before independent review + Human Acceptance。

## Deferred Items

- G2 Opportunity → G3 bounded/durable live advisory handoff。
- PRE-01A-D1 Gate A Real AI provider Shadow activation and exact timeout/cost/retry values。
- SE-02D aggregation/Expectancy and Gate C edge evidence。
- Forward Outcome evaluator periodic scheduler（accepted services remain callable; Host Core does not schedule it）。
- WinSW/service packaging、restart/backoff/log policy。
- 12-hour Host soak and any future Memory P2 closure verdict。
- separate trading/API processes、multi-provider、Live Trading。

Deferred means explicitly outside the first acceptance batch, not silently implemented or accepted。

## Risks

| Risk | Treatment |
|---|---|
| Recovery requires fresh BBO before Runtime fully starts | recovery-only live ingress; no scanner/economic replay |
| Scanner await can block a shared consumer | separate bounded scanner lane; safety lane never awaits scanner |
| safety queue overload could lose a trigger | never drop/coalesce; fail Host and recover durably |
| current DB factory hides engine | explicit Host-owned resource bundle and disposal tests |
| current API module global reports false health | lifespan app.state Host and separate live/ready semantics |
| AnyIO direct use may otherwise rely on transitive dependency | declare AnyIO directly in production requirements |
| process singleton enforced only by deployment convention | add PostgreSQL session advisory lock and connection-loss fatal check |
| periodic reconciliation could become a repair engine | call detector + accepted safe-mode service only; no fact mutation repair |
| exact Real AI latency/cost is unknown | G2→G3/AI deferred; absolute semantics retained, numeric timeout not invented |
| P2 telemetry itself could retain data | current snapshot + counters/high-water only; no in-memory time series |
| external supervisor may restart-loop on durable corruption | Host stays diagnostic fail-closed for logical recovery mismatch; WinSW policy deferred |

Implementation-blocking architecture ambiguity for Host Core V1：`NONE`。Deferred items require their own approved
contracts and do not block Host Core implementation。

## Candidate Design Verdict

```text
Host Placement = Option B: RuntimeHost owned by FastAPI lifespan
In-Process Concurrency = AnyIO TaskGroup / CancelScope
Process Model = single process, Uvicorn workers=1, reload off
Duplicate Fence = PostgreSQL session advisory lock
Supervisor = external OS/service boundary; WinSW future task
Startup = recovery-only live BBO -> Recovery/Reconciliation -> bounded Runtime -> readiness gate
Protection = dedicated bounded non-lossy lanes, independent of Scanner/AI
G2 -> G3 live handoff = DEFERRED
Real AI = NOT CONSTRUCTED / NOT ACTIVATED
Periodic Reconciliation = INCLUDED, detector-only + accepted fail-closed transition
Memory P2 = telemetry boundary added; finding REMAINS / NON-BLOCKING
Unnecessary Infrastructure = NONE
Implementation Blocking Unknowns = NONE
Artifact Status = ACCEPTED / COMPLETE
Task Status = ACCEPTED / COMPLETE (Human Acceptance 2026-09-15)
```

本 verdict 为设计时点记录；Human Acceptance 见文末「Acceptance Record」（2026-09-15：`PRE-01B-D1 = ACCEPTED / COMPLETE`）。本 Acceptance 仅接受 Formal Design，不授权 Implementation、Runtime activation、SE-02D、Real AI 或 Live。

## Acceptance Record

```text
Artifact: PRE-01B-D1 Integrated Runtime Host Contract
Status: ACCEPTED / COMPLETE
Task type: FORMAL DESIGN / ARCHITECTURE CONTRACT / DOCS ONLY
Human Acceptance: CONFIRMED — 2026-09-15
Human-Accepted reviewed candidate: 80cb2babe9f55b3a3b1dc2d3b7913a405607ac22
Independent Review: PASS WITH NON-BLOCKING FINDINGS
P0: NONE
P1: NONE
Closeout branch: pre-01b-d1-final-acceptance-closeout
Main integration: FAST-FORWARD ONLY
Integrated Runtime Host Implementation: NOT STARTED
```

本 Acceptance **仅** 接受本文件所冻结的
`Integrated Runtime Host V1` Formal Design。它 **不** 证明、
**不** 授权：Runtime Host Implementation、runtime validation、
Real AI activation、G2→G3 activation、`SE-02D`、Live Trading、
profitability / edge。

协议版本说明：本文档 `Repository Truth` 记录的是
**设计时点**的 Global Protocol 快照（v1.0.0 / `e92fcc38…`）；
本次 Human Acceptance 执行时点的实际 accepted protocol 为
**v1.1.0**（remote `main` = tag `protocol-v1.1.0` =
`07e2df83266d4ecdea46caff5c61f000937b8913`）。该差异属协议仓库
自身的版本推进，**不** 改变、**不** 影响本设计
任何架构语义。

### Implementation Carry-Ins

以下两项 **必须** 带入 `Integrated Runtime Host` 的
Implementation 窗口；它们 **不** 表示本设计存在缺陷
或未被接受：

- **F-01**：`state_version_for` 的实现 **必须** 显式绑定
  已接受的 durable state/version authority；`RuntimeHost` /
  `LiveMarketState` **不得** 另造一套并行 `state_version` authority。
- **F-02**：safety queue capacity `64` 只是 **初始可配置默认值**；
  Implementation Acceptance **必须** 用 queue high-water / runtime evidence 验证其
  sizing。它 **不是** 免证据的永久架构常量。

`F-03` .. `F-08` = P3 / NON-BLOCKING 历史 review findings；**不** 为其单独开
Fix batch。

### 收口编辑边界

本次 closeout 对本文件只做了状态级最小同步：
上方 `Artifact Status` 块、`Candidate Design Verdict` 的 `Artifact Status` /
`Task Status` 两行、以及 verdict 末句的 supersession 指向。718 行
设计正文（Problem Statement / Accepted Inputs / Architecture Contract / Invariants /
Risks 等）**逐字未改**，架构语义保持原样。
