# PRE-01B-I1｜Integrated Runtime Host Core Implementation — Candidate Delivery

## Task

- Type：IMPLEMENTATION / VERIFICATION / CANDIDATE DELIVERY（**非** Human Acceptance）。
- Goal：实现 Accepted Design `PRE-01B-D1` 的 First Implementation Batch ——
  **Integrated Runtime Host / Host Core V1**：唯一 production composition owner、
  FastAPI `lifespan` 唯一 activation boundary、显式 DB ownership、duplicate-Host fence、
  process-local market-state boundary、11 步确定性 startup、AnyIO 结构化并发、
  safety/scanner 隔离、诚实 readiness、有界 shutdown、P2 有界遥测。
- 本任务**不**实现：Real AI、G2→G3 live advisory handoff、`SE-02D`、Live Trading、
  OS/service deployment、12h soak。
- 本任务**不**执行 Human Acceptance、**不** merge `main`、**不** fast-forward `main`。

## Repository Truth Preflight（实时读取）

- Task Base = Accepted Main at dispatch = `9e0553f5dee3fcb4a2dad0b672280657235656aa`。
- `git rev-parse HEAD` = `9e0553f5…`、branch = `pre-01b-i1-runtime-host-core`
  ⇒ 与 Task Base 一致，**无 SHA drift**。
- 实时读取远端真值：`origin/main` = `f887981d18fd7fc696d99cde702d0fec3e72a16c`。
  Delta 相对 Task Base = 1 commit、fast-forward、**docs/state-only**
  （`AI_CONTEXT.md` / `DECISIONS.md` / `PROJECT_STATE.md` + 4 个 `docs/**` 文档，
  1524 insertions，`backend/` / `frontend/` / `scripts/` **零改动**）。
  ⇒ 未触碰 Runtime Host、FastAPI、DB lifecycle、G2/G3/G4、Recovery、Reconciliation、
  OKX provider、config 或 accepted PRE-01B semantics
  ⇒ **Baseline Drift = NON-MATERIAL（docs/state-only）**，非 `BASELINE MISMATCH`，可继续。
- 未执行任何 reset / rebase / 覆盖未知修改。

## Scope Delivered

唯一新增 production composition owner：`backend/src/marketpulse/runtime_host.py`。

- **Runtime ownership**：`RuntimeHost` 负责 resource construction、startup FSM、
  structured concurrency、failure propagation、readiness、graceful shutdown、
  resource disposal、bounded telemetry snapshot。
- **FastAPI lifecycle**：`api/app.py` 的 `lifespan` 是 `RuntimeHost` 唯一 activation
  boundary；`app.state.host` 对 request handler 只读；module import 不启动 runtime；
  普通 request 不创建 runtime resource；Host **不是** process supervisor
  （不重启自身 child、不重启进程）。
- **DB ownership**：`db/session.py` 引入 `DatabaseResources`
  （owned `AsyncEngine` + 由其派生的 `async_sessionmaker`，`dispose()` 幂等），
  Host 真正持有并释放 engine；无 request-scoped engine；
  `create_session_factory` 保留为向后兼容 wrapper。
- **Duplicate Host fence**：PostgreSQL session advisory lock
  （`pg_try_advisory_lock`，namespace `runtime_advisory_lock_namespace` = `0x4D50`），
  绑定 dedicated connection lifetime，duplicate Host **fail closed**；
  lock connection loss = Host-fatal；**无** schema / migration。
- **Market-state boundary**：process-local `LiveMarketState`
  （latest BBO、market freshness、read-only telemetry）；
  ephemeral observation **≠** durable business authority。
- **Startup**：config validation → DB engine/session ownership → singleton lock →
  dependency construction → recovery-only public OKX market ingress →
  active-risk fresh BBO availability → Recovery → startup reconciliation →
  EventRuntime / safety / scanner / heartbeat / periodic reconciliation →
  normal ingress routing → readiness；Recovery precedes new risk admission；
  recovery-only warm-up 事件**不**回放给 Scanner、**不**制造 Opportunity /
  economic fact、**不**伪造历史 Fill。
- **Structured concurrency**：AnyIO `TaskGroup` / `CancelScope`；
  critical Host child 意外退出 ⇒ fail Host ⇒ cancel sibling ⇒ bounded cleanup ⇒
  external process failure signal；**无** in-process infinite restart loop、
  **无** catch-all-and-continue supervisor。
- **Safety / Scanner isolation**：每个 instrument 一条有界 safety lane，
  market update 先 safety admission/process、后 scanner admission；
  scanner 满时按 accepted contract 拒绝/降级，**不**阻塞 Protection；
  safety lane 满 ⇒ 立即关闭 risk admission + health `UNAVAILABLE` +
  `SafetyQueueOverflowError`（fail closed，**不**静默丢弃/合并 safety BBO）。
- **Readiness**：`HostLifecycleState`（Host 生命周期事实）与 durable G4 `SystemState`
  严格区分；`/api/v1/live`（liveness，恒 200 语义）、`/api/v1/ready`
  （conjunction，未满足返回 503）、`/api/v1/health`（诚实 DEGRADED / FAIL_CLOSED）、
  `/api/v1/runtime`（既有鉴权边界内的详细遥测）四者不互相冒充。
- **Reconciliation**：startup / periodic / final-shutdown 三段，
  **复用既有 detector semantics**，仅检测、绝不修复经济事实；
  mismatch 走 accepted G4 fail-closed path。
- **Shutdown**：close risk-increasing admission → stop new ingress →
  drain/terminate safety → drain scanner（有界）→ stop EventRuntime →
  stop Host loops → final detector-only reconciliation → close provider →
  release singleton lock → dispose engine；所有等待有界；
  **无** `queue.join()` 永久等待；cleanup failure **不**报告为 clean stop。
- **Telemetry**：bounded current snapshot + monotonic counters / high-water；
  覆盖 RSS、Host task count/names、EventRuntime worker state、
  safety/scanner/EventRuntime queue size/capacity/high-water、overflow/reject counters、
  bounded retention sizes、provider reconnect/status/fresh timestamps、
  socket/handle aggregate、SQLAlchemy pool state、singleton connection presence、
  Host lifecycle timestamps、reconciliation/heartbeat timestamps/results。
  `psutil` 已 direct declare（`backend/requirements.txt`）；probe 不可用报 `UNAVAILABLE`，
  **不**伪造 0。**未**构建 metrics platform、**未**保留 unbounded time series、
  **未**宣称 Memory P2 resolved。

## Carry-In F-01（durable `state_version` authority）

`PASS`。`RuntimeHost._durable_state_version_for(instrument_id)` 直接读
**durable G2 symbol-state authority**：

- durable source = `symbol_states.state_version`（PostgreSQL），
  经 Host 持有的 `PostgresG2Repository.get_state(instrument_id)` 读取
  （`runtime_host.py` `_durable_state_version_for`）；
  无 durable row 时返回 accepted `SymbolStateRecord` 默认值 `0`。
- 该 accessor 注入 accepted `PaperExecutionService`
  （构造参数 `state_version_for=self._durable_state_version_for`）。
- Host **未**创建 counter、**未**从 quote / `LiveMarketState` 派生、
  **未**在内存中递增任何并行 `state_version` authority。

## Carry-In F-02（safety queue capacity sizing）

`INITIAL DEFAULT = 64`（`runtime_safety_queue_capacity`，**可配置**，非不可变常量）。

- 暴露面：`BoundedLane` 提供 `capacity` / `size` / `high_water` /
  `overflow_count` / `rejected_count`。
- 公网 OKX 5 分钟真实运行观测（见下）：
  `safety_queue_high_water = {BTC-USDT: 17, ETH-USDT: 16}`、capacity 均为 `64`
  ⇒ 峰值利用率约 `26.6%` / `25.0%`；`safety_overflow = 0`、safety lane `rejected = 0`。
  `scanner_queue_high_water = 192`、capacity `2048` ⇒ 约 `9.4%`；`scanner_rejected = 0`。
- **Sizing Evidence 结论**：在本次 5 分钟、2 instrument、单 Uvicorn worker、
  `run_mode=LIVE_PAPER` 的运行条件下，`64` **未**出现压力，
  且**没有**证据表明需要修改 Accepted Architecture Contract。
  这**不**等于"64 已被证明为长期充分"；更长窗口 / 更高并发下的 sizing
  仍留给 Implementation Acceptance 裁决。

## Files Changed

新增：

1. `backend/src/marketpulse/runtime_host.py`（2199 行）
2. `backend/tests/test_runtime_host.py`（1059 行，35 tests）
3. `scripts/verify_pre_01b_runtime_host.py`（689 行）

修改（6 个，共 +388 / -20）：

4. `backend/requirements.txt`（+`anyio>=4.4,<5`、+`psutil>=6,<8`）
5. `backend/src/marketpulse/api/app.py`（lifespan + 4 个 system surface + `create_app`）
6. `backend/src/marketpulse/config.py`（`runtime_host_*` 设置与 instrument 解析）
7. `backend/src/marketpulse/db/session.py`（`DatabaseResources` / `create_database_resources`）
8. `backend/src/marketpulse/g2/runtime.py`（read-only telemetry accessor）
9. `backend/src/marketpulse/runtime.py`（`HostLifecycleState` / `HostReadinessStatus` /
   `HostReadinessReport` / readiness reason codes）

任务状态文档：

10. `PROJECT_STATE.md`（+42 行，仅 branch-local 状态）
11. `dev_log/2026-09-15-pre-01b-i1-runtime-host-core.md`（本文件）

除上述路径外**无**任何其他变更。`Migration = NO`、`Schema = NO`、
`G3 Production = NO`、`G4 Production = NO`、`Edge Production = NO`、
`Frontend = NO`、`Deployment = NO`、`.workbuddy / memory / skills = ZERO CHANGE`。

## Verification

### 静态门

- `ruff check backend/src backend/tests scripts`：`All checks passed`。
  说明：本环境 ruff `0.16.6` 启用 413 条规则（含 `BLE001` / `RUF100` / `ASYNC115` /
  `PLR0124` / `RUF012` / `PYI034` / `PLW1510` / `S110`）。
  交付前先确认**未改动**的 `backend/src/marketpulse/{g3,edge,g4}` 在该门下
  `All checks passed`，再把自己新增/修改的 41 项违规全部清零。
- `py -3.14 -m compileall`（全部改动文件）：`EXIT=0`。
- `git diff --check`：clean（曾出现 `g2/runtime.py` EOF 多余空行，已修）。

### Focused RuntimeHost tests

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_runtime_host.py -q`
  ⇒ **`35 passed`, 1 warning, 39.04 s**。
- 覆盖：Host FSM legal/illegal transition、double start 拒绝、stop 幂等 +
  engine dispose、injected engine 不被 Host dispose、startup 次序与 conjunction、
  recovery-only warm-up **不**回放给 scanner、safety 先于 scanner、
  feed gap 关闭 readiness 与 fresh feed 恢复、durable SAFE_MODE 不 ready、
  duplicate Host 被 advisory lock 拒绝、bounded lane capacity/high-water/counters、
  safety lane overflow fatal 不丢帧、scanner overload 降级不阻塞 safety、
  critical child 退出 fatal、cancelled startup 仍有界清理、
  Real AI provider 从不构造、AI disabled sentinel fail closed、
  4 个 API surface 互不冒充、lifespan disabled 时行为。

### Regression（§19）

隔离姿势：新建**独立 disposable PostgreSQL 实例**
`marketpulse-pre-01b-i1-regr-pg`（`postgres:16-alpine`，`127.0.0.1:5444`，
其主库名恰为 `marketpulse`），经 `alembic upgrade head`
迁到 `20260913_0009`（30 表），仅用 gitignored `.env` 覆盖 `DATABASE_URL`。
共享 5432 主库 `marketpulse` **全程未使用、未迁移、未写入**
（前后 revision 均 `20260905_0004`，会话数 0）。

- 全量 backend 套件（`pytest backend/tests -q`，未导出 `DATABASE_URL`）：
  **`460 passed`, 2 warnings, 656.63 s (10:56), EXIT=0**。
  其中已包含 task-relevant 的 G2 / G3 / G4 回归
  （`test_group2.py` / `test_group3.py` / `test_group4.py` /
  `test_group5_1..5_4`）、DB / session lifecycle 回归
  （`test_n01_runtime_resource_lifecycle.py`、
  `test_n01_okx_paper_safety.py`、`test_n01_restart_recovery.py`）
  与 SE-02A/B/C 套件。
- 2 warnings 均**与本次改动无关**且非新增：
  `StarletteDeprecationWarning`（fastapi/starlette testclient 与 httpx），
  以及 `alembic/versions/20260911_0005_edge_evidence_foundation.py:29` 的
  `SAWarning`（disposable 库拆除期 GC 回收未归还连接；
  该文件属 §16 禁改路径，未触碰）。
- **已排除的环境伪失败（证据保留）**：首次全量运行时，隔离库使用
  **不同库名**（`marketpulse_pre01bi1_regr`）于共享 5432 服务器，产生
  **恰好 1 个失败**：
  `test_group5_2_trading_replay.py::test_real_postgres_replay_g2_to_g4_stop_exit_is_isolated_and_historical`，
  断言 `result.primary_database == "marketpulse"` 而实际为隔离库名。
  该断言只比较**已配置 primary 数据库的名称**（同一测试另用
  `primary_counts_after == primary_counts_before` 证明 replay **不**修改 primary），
  与实现语义无关。改用主库名同为 `marketpulse` 的独立实例后即 `460 passed`。
  ⇒ 判定为**隔离方式造成的环境伪失败**，非产品回归。

### Disposable PostgreSQL Validation（§20）

- 独立实例、从零 `alembic upgrade head`，运行前确认
  `current == head == 20260913_0009`。
- 运行证据：one Host only；duplicate independent Host 被 lock 拒绝；
  restart 从 durable PostgreSQL 重建（无 in-memory authority 复用）；
  **无**重复 economic fact；pool / session ownership 有界；
  stop 后**无** idle-in-transaction 泄漏；Host-owned sessions = 0。

### Public OKX 5-Minute Runtime Validation（§21）

`PYTHONPATH=backend/src py -3.14 scripts/verify_pre_01b_runtime_host.py --minutes 5`
（仅 public market data；无 credential、无 trading API、无 private endpoint、
无 Real AI key；instrument 仅 `BTC-USDT` / `ETH-USDT`）。

**结果：`PASS`，17/17 §22 pass conditions 全为 `true`，`failed conditions = []`。**

| 项 | 观测值 |
| --- | --- |
| 运行窗口 | `304.238 s`（≥ 5 分钟连续），60 samples @ 5 s |
| startup | 4.485 s 达 `READY`；state history 严格 11 步次序 |
| ready fraction | `1.0`；`states_seen = [READY]`、`readiness_statuses = [READY]` |
| live children | 8：`eventruntime_monitor` / `heartbeat` / `provider_stream` / `reconciliation` / `safety:BTC-USDT` / `safety:ETH-USDT` / `scanner` / `telemetry` |
| provider | `LIVE`，`connection_attempts = 1`，`reconnects = 0` |
| market frames | `4015`（trade frames `1997`） |
| ingress → safety | `4005` admitted，safety processed `4003` |
| scanner | processed `5999`，rejected `0` |
| safety high-water | BTC `17` / ETH `16`（capacity `64`），overflow `0` |
| scanner high-water | `192`（capacity `2048`） |
| periodic reconciliation | 全程 `OK` |
| RSS | `113.461 MB` → `119.266 MB` |
| max host-owned sessions | `5`（singleton `1` + non-singleton `4`） |
| shutdown | `0.452 s` 达 `STOPPED`，`shutdown_failures = []`，`shutdown_escalated = false` |
| post-stop orphans | `orphan_tasks = []`、EventRuntime live workers `0`、inflight `0` |
| post-stop DB | Host-owned sessions `0`、idle-in-transaction `0`、owned engine `disposed = true`、lock engine `disposed = true` |
| post-stop provider | `provider_status = STOPPED`、provider socket connections `0` |
| economic facts | 9 张经济表 before / after 全 `0` |
| duplicate fence | `duplicate_refused = true`（`DuplicateRuntimeHostError`），第二个 Host `STOPPED` 且未持有 singleton connection |
| Real AI | `ai_sentinel = true`；`safety_reevaluation.enabled = false`、`inflight = 0` |
| 停止时 readiness | 诚实 `FAIL_CLOSED`，reasons = `HOST_NOT_READY` / `RISK_ADMISSION_CLOSED` / `SINGLETON_LOCK_NOT_HELD` / `DB_UNAVAILABLE` / `PROVIDER_STREAM_DOWN` / `MARKET_DATA_STALE` / `WORKER_UNAVAILABLE` |

- 未刻意开仓；未发生 intentional economic Position。
- 5 分钟窗口内**未**发生自然网络断连（按 §21，受控 reconnect / stale 行为
  由确定性测试覆盖）。

### 计数类结论的独立交叉核对

- `scanner_processed (5999) <= ingress_forwarded_to_safety (4005) + trade_frames (1997) = 6002`：
  仅用于证明 scanner **只**被 post-admission 路径喂入
  （recovery-only warm-up BBO 结构性排除），**不**表示 scanner 只吃 BBO。
- `safety_processed (4003) <= ingress_forwarded (4005)`；
  `safety_overflow = 0` 与 lane `overflow = 0` 一致；
  `scanner_rejected = 0` 与 lane `rejected = 0` 一致。

## Environment / Tooling Notes

- **ruff `0.16.6`**（`py -3.14 -m ruff`），无 user-level / extra config，
  `Settings path` = 仓库根 `pyproject.toml`；启用规则集为 413 条。
- **ASYNC115 修复的语义等价性（有据）**：`_close_stream()` 的 shielded 收敛循环由
  `await anyio.sleep(0)` 改为 `await anyio.lowlevel.checkpoint()`。
  在本项目使用的 asyncio 后端（anyio `4.14.2`）上
  `anyio.lowlevel.checkpoint()` = `checkpoint_if_cancelled()` +
  `cancel_shielded_checkpoint()`，而 asyncio backend 的 `checkpoint()` 实现即
  `await sleep(0)`；且外层为 `CancelScope(shield=True)` ⇒
  `checkpoint_if_cancelled()` 在 shield 处 `break`、不抛取消
  ⇒ 与 `anyio.sleep(0)` **等价**。**无**行为变化。
- `PLR0124`：`_positive_finite` 的 `number == number and number not in (±inf)`
  改为 `math.isfinite(number)`（等价，可读性更好）。
- `PLR1730` / `RUF012` / `PYI034` / `F401` / `I001` / `UP035` / `B018` /
  `PLW1510` / `S110` / `RUF100` 修复均为**纯静态**（`max()`、`ClassVar`、`Self`、
  去未用 import、import 排序、显式 `check=False`、合并 noqa）。
  自动修复曾把 7 处解释性理由注释连同无用的 `# noqa: BLE001` 一起删除，
  已按原意**以普通注释形式恢复**（理由文本保留，指令不保留）。
- **沙箱出网**：本开发沙箱注入的 `HTTP_PROXY/HTTPS_PROXY` 指向一个对 OKX 失败的
  本地代理端口；按已接受先例（`scripts/verify_n01_6_runtime_smoke.py`）
  在**进程内**清空这些变量即可同时打通 OKX REST（`200` / `code=0`）与 WS（`bbo-tbt`）。
  验证脚本的 `apply_proxy()` 默认走 `cleared_environment`，**未**修改任何机器 /
  系统代理设置。
- **共享 primary DB**：`127.0.0.1:5432/marketpulse` 当前 revision 为
  `20260905_0004`（**旧于** head `20260913_0009`，24 表）。
  该库在本任务中**未**被迁移、**未**被写入、**未**被用于验证。

## Known Findings

- **P0**：`NONE`。
- **P1**：`NONE`。
- **P2（新，NON-BLOCKING，未修）**：focused 套件中的
  `SAWarning: non-checked-in connection`。已定位为**测试态伪影**：
  在 `test_provider_stream_task_exit_is_fatal` 导致 TaskGroup 取消 sibling 时，
  兄弟任务正于 `AsyncSession.close()` 的 asyncpg `terminate()` 中被取消，
  连接未能归还池；该连接属于测试 harness 注入的 engine，
  pytest session 末 `gc_collect_harder` 才回收。
  Host **自持 engine** 的生产形态独立复现结果：
  `checked_out = 0` / `disposed = True` / `shutdown_failures = []`
  ⇒ §22 生产路径成立。
  **未修复**：修复需要在 G3/G4 `_apply` / `on_market_data` 内增加 `await` 点或
  `suppress(CancelledError)`，属 §16 禁止的 scope 扩张；**留给 Review 裁决**。
  另注：全量套件中同类 `SAWarning` 出现在
  `alembic/versions/20260911_0005_edge_evidence_foundation.py`（§16 禁改路径）。
- **P2（既有，REMAINS）**：`N01-7-R01-RR-P2-01`（memory growth watch）
  = **REMAINS / NON-BLOCKING**，本任务**未**关闭、**未**宣称 resolved。
  本次 5 分钟窗口 RSS `113.461 MB → 119.266 MB` **不构成**该 finding 的闭合证据
  （窗口远短于 N01-8 的 12h，且 N01-8 已冻结 AND 门 `finding=false`）。
- **P3**：`NONE`（本次）。

## Remaining / Out of Scope

- `PRE-01B-I1` = `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`
  （**未** `ACCEPTED`、**未** `COMPLETE`）。
- `main` = `UNCHANGED`（本任务**未** merge、**未** fast-forward、**未** push `main`）。
- Human Acceptance = `NOT PERFORMED`。
- Real AI runtime activation = `NOT STARTED / NOT ACTIVATED`；
  Real AI provider constructor call count = `0`。
- G2→G3 live integrated handoff = `NOT ACCEPTED / NOT ACTIVE`；live call count = `0`。
- `SE-02D` = `NOT STARTED`；Live Trading = `DISABLED`；WinSW / OS service = `NOT STARTED`；
  12h Host soak = `NOT STARTED`。
- `PRE-01B-D1` = `ACCEPTED / COMPLETE`（Formal Design），未受本任务影响。
- 本候选**不**证明：Runtime Host production acceptance、Real AI、
  G2→G3 activation、`SE-02D`、Live Trading、profitability / edge。

## Context for Next AI

- 候选 branch `pre-01b-i1-runtime-host-core`，Task Base `9e0553f5`；
  candidate commit SHA 以该分支 tip 与 Completion Report 为准
  （Git ref 是权威事实；不把 commit 自身 SHA 写入其内容，避免 self-referential commit）。
- 本任务**未**解锁任何下游。下一步**必须**是 Independent Review；
  未经 Human Acceptance **不得**推进 `main`；收尾一个 batch **不**自动解锁下游。
- 复现验证的推荐姿势：先起独立 disposable PostgreSQL 实例
  （主库名须为 `marketpulse`），迁到 head，再以 gitignored `.env` 仅覆盖
  `DATABASE_URL`；**不要**把共享 5432 主库当作验证目标。
- 公网 OKX 验证前须在进程内清空代理变量（见 Environment / Tooling Notes）。

## Evidence Pointers

- 5 分钟公网 OKX 运行证据：
  `E:/Documents/pre-01b-i1-evidence/pre-01b-i1-5min.json`（含 17 条 pass conditions、
  60 个 telemetry sample、startup / shutdown state history、post-stop 清理快照）。
- 全量回归：`E:/Documents/pre-01b-i1-evidence/pytest_full2.txt`（460 passed）；
  环境伪失败对照：`E:/Documents/pre-01b-i1-evidence/pytest_full.txt`（1 failed）。
- 聚焦测试：`E:/Documents/pre-01b-i1-evidence/pytest_focused.txt`（35 passed）。
- 静态门：`E:/Documents/pre-01b-i1-evidence/ruff_fix2.txt`（All checks passed）、
  `compile.txt`。
- 诊断与探针原始件（**已移出仓库**，不属于候选提交）：
  `E:/Documents/pre-01b-i1-evidence/diag/`。
