# PRE-01B-I1-FIX-01 — Runtime Host 生命周期阻塞修复（Implementation 记录）

- **日期**：2026-09-15
- **Task ID**：PRE-01B-I1-FIX-01
- **Task Base SHA**：`b66e17d34173156b3797b664dbe09625511a0a11`（执行前 `git rev-parse HEAD` 实测）
- **Accepted Main SHA**：`f887981d18fd7fc696d99cde702d0fec3e72a16c`（`git ls-remote origin refs/heads/main` 实测；窗口内未移动，与本轮 docs/state-only drift 一致）
- **Worktree**：`E:/Documents/MarketPulse-AI-pre-01b-i1-fix-01`
- **Branch**：`pre-01b-i1-fix-01-runtime-host-lifecycle`
- **状态**：`IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`
  （**未** Human Accept、**未** merge `main`、**未** 做 latest-main reconciliation、**未** 开始下一批）

上游判定：PRE-01B-I1 的 Independent Review 为 `FAIL — FIX REQUIRED`，Human Acceptance 为 `NOT READY`。
本轮的**唯一目标**是把下列 blocker 全部关闭，并交出可进入 Independent Re-Review 的候选。

---

## 1. 必须关闭的 blocker（来自任务书 §2 / §7–§15）

| 编号 | 问题 | 本轮要求 |
| --- | --- | --- |
| P1-01 | Singleton connection 常驻 transaction | 保留 session-level advisory lock + 连接生命周期 = Host 生命周期；每次 lock/liveness SQL 后 transaction 必须结束；READY 期间 `idle in transaction = 0` 且 fence 仍持 |
| P1-02 | Critical child failure 无 external process / lifespan failure signal | fatal result 成为 **lifespan owned** 的 lifecycle result，**在 Runtime 运行期间**被 lifespan 观察（不得要求人工 shutdown）；外部 supervisor 能看到异常终止；不得 in-process restart / generic supervisor / WinSW / `os._exit` |
| P1-03 | Cleanup exception 被吞并错误报告 CLEAN | `DatabaseResources.dispose()` 仅在 `engine.dispose()` 成功后置 `disposed=True`；cleanup 每步独立尝试，失败进 `shutdown_failures`；mandatory failure → 终端 `STOP_FAILED` 并传播给 lifespan |
| P1-04 | `stop()` cancellation 可绕过 final disposal | cancellation 到达时：mark cancellation → 关 risk admission → 进入 bounded shielded final cleanup → 尝试所有 mandatory disposal → **建立 truthful terminal state** → 才传播；不得提前 re-raise、不得伪装 clean `STOPPED` |
| P2-01 | Injected-engine cancellation seam checkout leak | 与 P1-04 一并关闭；shield 落在各 session 使用处 |
| P2-03 | Host unbounded retention | `_state_history` / `_scanner_error_samples` 改成底层存储有界（不得只切 telemetry slice） |
| P2-04 | Legacy DB wrapper ownership leak | 不得保留「只返回 factory、owner 丢失」的 helper |
| P2-05 | Enabled Host 必须至少配置 BTC-USDT + ETH-USDT | 缺任一即 fail |
| P2-02 | 历史 process finding（上一轮 Implementation Worker 改过 memory/skill） | 本轮**只记录**为本进程审计发现：`REMAINS`，**ZERO CHANGE to memory/skills** |

## 2. Scope

**Allowed Changes（§5）**——实际改动恰好落在其中 5 个文件：

```
backend/src/marketpulse/runtime_host.py
backend/src/marketpulse/api/app.py
backend/src/marketpulse/db/session.py
backend/tests/test_runtime_host.py
scripts/verify_pre_01b_runtime_host.py
dev_log/                                    （本文件）
```

**Forbidden（§6）已核对为 ZERO CHANGE**：`PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md`、`backend/src/marketpulse/g2|g3|g4/**`、`edge/**`、`db/models.py`、`alembic/**`、`frontend/**`、`docs/design/**`、`.workbuddy/memory|skills`；无 migration / schema 变更。

`git diff --name-only` 实测（还原变异探针后）：

```
backend/src/marketpulse/api/app.py
backend/src/marketpulse/db/session.py
backend/src/marketpulse/runtime_host.py
backend/tests/test_runtime_host.py
scripts/verify_pre_01b_runtime_host.py
```

`git status --porcelain --untracked-files=all` = 5 条（无临时文件残留）。

## 3. 修复前的机制取证（先取证，再改代码）

**P1-02 是本轮唯一需要"发明机制"的项**，因此先做实证，不靠推理：

1. 读 `uvicorn/lifespan/on.py` / `server.py` 源码：`LifespanOn.main` 里 `error_occurred=True` **不会**置 `should_exit`，即"运行期 lifespan 抛异常"本身并不停止服务器。
2. 真实 uvicorn 进程 4 组对照实验（`E:/Documents/pre-01b-i1-fix-01-evidence/uvicorn_probe_app{,2,3}.py`）：
   - lifespan 自行 unwound（无需人工 shutdown）后，进程 **继续存活**（30 s 仍在）；
   - `SIGINT` → 退出码 `0`；**`SIGTERM` → 进程自退出，`returncode = 3`（非零）**。
   - 结论：唯一"运行期让进程以非零退出码结束"的机制是向 OS 请求 `SIGTERM`，与已接受契约 D1 §505–516「RuntimeHost owns … deterministic exit signal；a future service wrapper watches its exit code；nonzero process signal」一致。
3. 因此采用：**detached failure-cleanup task → 发布 `HostTerminalResult`；lifespan 用 task group own 该 result → `request_process_stop(SIGTERM)` + cancel scope**。不发明 repo-local supervisor。
4. `request_process_stop` 在 `SIGTERM` 未映射（如独立 `py -3.14` 直跑）时**安全拒绝**并记 `runtime_host_process_stop_unmapped`，不误杀进程（实测进程存活）。

**P2-01 的泄漏缝合点**：探针确认 shield 放在 `AsyncSession.close()` / `__aexit__` 上无效，必须放在 Host 自己的 session 使用处；且只有**仍持有 open transaction** 的 session 在 `close()` 时才持有池连接 —— 这正是 `_load_active_risk_instruments`（`async with self._sessions() as session:` 后直接 `scalars()`，无 `begin()`/`commit()`）的形态。

## 4. 逐条修复

### 4.1 P1-01 — 让 fence 连接不再常驻 transaction（`runtime_host.py`）

- `_acquire_singleton_lock`：`pg_try_advisory_lock` 之后立刻 `await self._lock_connection.commit()`。
  session 级 advisory lock **不是** transaction-scoped，commit 之后 fence 仍持（只有显式 unlock 或断连才结束）。
- `_singleton_connection_alive`：`SELECT 1` 之后同样 `await connection.commit()`，使 liveness 探针不留下 open transaction。
- 结果：fence 连接在两次心跳之间停在 `idle`；锁仍持。

### 4.2 P1-02 — fatal result 成为 lifespan owned 的 lifecycle fact

`runtime_host.py`：

- 新增冻结 dataclass `HostTerminalResult(reason, state, shutdown_failures)`，加入 `__all__`。
- 新增 `_terminal_result` / `_terminal_event`（`anyio.Event`）、只读属性 `terminal_result`、`wait_for_terminal_result()`、`_publish_terminal_result()`（仅发布一次）。
- `_supervise` 的 failure 分支：`asyncio.create_task(self.stop())` → `asyncio.create_task(self._failure_cleanup())`；
  `_failure_cleanup()` 先 `await self.stop()`（有界清理既有实现），**成功返回后**才 `_publish_terminal_result()`。
  ⇒ 观察者永远不会拿到"跑在 disposal 前面"的结果；`_supervise` 自己已 unwound，故不自我死锁。
  顺序停止（lifespan/operator 主动 `stop()`）**永不**发布该结果 ⇒ "runtime died" 与 "we were asked to shut down" 可区分。

`api/app.py`：

- 新增 `request_process_stop(reason)`（上述 SIGTERM 机制，未映射则拒绝并记录）。
- 重写 `lifespan`：启用时构造 → `start()` → `anyio.create_task_group()` 内 `start_soon(own_runtime_failure)`；
  `own_runtime_failure` `await host.wait_for_terminal_result()` → 写 `app.state.runtime_failure` → `logger.critical("runtime_host_fatal")` → `request_process_stop(failure.reason)` → cancel scope（即使 ASGI 调用方从不发 shutdown，run phase 也会直接结束）。
  `finally` 中 `with anyio.CancelScope(shield=True): await host.stop()`；fatal → `raise RuntimeError(f"runtime_host_fatal:{reason}")`；终端 `STOP_FAILED` → `raise RuntimeError("runtime_host_stop_failed")`（不得被报成 clean stop）。

### 4.3 P1-03 — cleanup 不吞异常、dispose 说真话

`db/session.py`：

- `DatabaseResources.dispose()`：只有 `await engine.dispose()` **返回后**才置 `disposed=True`；失败保持 `False`（幂等：二次调用是 no-op）。
- 删除 `create_session_factory` / `get_db`（P2-04）。

`runtime_host.py`：

- `_record_cleanup_failure(label, exc)` → `shutdown_failures` 追加 `f"{label}:{type(exc).__name__}"`（不吞、不抛）。
- `_attempt_cleanup(label, action)` → 每步独立 `try/except`，失败记录后**继续下一步**。
- `_release_singleton_lock`：unlock / connection close / lock-engine dispose 逐步 `try/except` + 记录（原先 `contextlib.suppress`）。
- `_close_stream`：失败改为 `_record_cleanup_failure("provider_close_failed", exc)`。
- `_dispose_resources` 重写为 provider / singleton / engine 三步独立尝试；engine 侧区分 `engine_dispose_failed:<Type>`（抛错）与 `engine_dispose_incomplete`（返回了但 `disposed` 仍为 `False` —— 以 truthful flag 为准，不以调用乐观为准）。
- 终端：`escalated = _shutdown_escalated or bool(_shutdown_failures)` → `STOP_FAILED`，否则 `STOPPED`。

### 4.4 P1-04 — cancellation 不得绕过 final disposal 与 truthful terminal state（`runtime_host.py`）

- `_shutdown` 新增 `cancelled: BaseException | None`：graceful 段 `except` 中 `CancelledError` **不再 `raise`**，改为 `cancelled = exc` + 记 `shutdown_cancelled` + `_shutdown_escalated = True`。
- **shielded final region 内**依次执行：`_force_children_down()` → 有界 `_dispose_resources()` → **建立 truthful terminal state（`_stopped_at` / `_stop_completed` / `STOPPED|STOP_FAILED` / telemetry）**；region 退出后 `if cancelled is not None: raise cancelled`。
  - 把 step 11 放进 shield 是刻意的：否则"在 shielded 区被延迟的 cancellation"会在 shield 退出时先于终端状态建立而抛出，留下停在 `STOPPING` 的 Host。
- 新增 `_force_children_down(budget)`：置 `_loops_stop` / `_supervisor_stop_requested`，有界 join supervisor；仍未收敛才 `cancel()`（escalation 记录在案）；`children_live` 仍非空 → 追加 `host_children_remained:<names>`（去重）。
  - 正常路径 supervisor 已 done 且 children 为空 ⇒ **纯 no-op**（对既有 476 项回归零影响）。
  - 对"cancellation 打断 graceful 段"与"graceful 段耗尽 deadline"两条路径，保证 `stop()` 返回后不留任何 Host-owned 子任务。

### 4.5 P2-01 — shield 落在 session 使用处

`_load_active_risk_instruments`、`_heartbeat_loop` 的 DB 段、`_reconciliation_loop` 的 DB 段均包 `with anyio.CancelScope(shield=True)`，并把"为什么"写进注释（兄弟/anyio cancellation 落在 `AsyncSession.close()` 会丢 checkout）。

### 4.6 P2-03 — 底层存储有界

- 常量 `STATE_HISTORY_MAXLEN = 64`、`SCANNER_ERROR_SAMPLE_MAXLEN = 16`。
- `_state_history` / `_scanner_error_samples` 改为 `deque(maxlen=...)`；telemetry 取 `list(...)[:8]`（读路径切片只是展示，界在存储上）。

### 4.7 P2-05 — V1 activation contract

- 常量 `V1_REQUIRED_INSTRUMENTS = ("BTC-USDT", "ETH-USDT")`。
- `_validate_configuration`：`missing = sorted(set(V1_REQUIRED_INSTRUMENTS) - set(self.instruments))` 非空 → `HostConfigurationError("V1_REQUIRED_INSTRUMENTS_MISSING:" + ",".join(missing))`（在任何资源打开之前 fail closed；额外品种仍允许）。

### 4.8 §5 附录：验证脚本（`scripts/verify_pre_01b_runtime_host.py`）

- `_session_attribution` 增加第三会话（observer）侧的 `state` + `state_change` 采集，用 **`clock_timestamp()`**（不是 `now()`）算 dwell，并给出 `singleton_fence.{states,max_idle_seconds,max_idle_in_transaction_seconds}`。
- 采样增加 `singleton_lock_held`（从 `pg_locks` 读 fence backend 是否仍持 advisory lock）；window summary 增加 fence 两个 dwell 最大值、held 采样数，以及 `host_owned_idle_in_transaction_max_dwell`。
- 修正被 P1-01 推翻的旧注释（原文写"advisory-lock 连接预期常驻 open transaction"）。
- 新增 pass 条件（21 → 22 条）：`singleton_fence_parks_in_idle`、`singleton_fence_never_dwells_in_transaction`、`singleton_fence_held_for_the_whole_window`、`v1_instruments_covered`、`host_owned_idle_in_transaction_is_transient`。

> 说明 1（为何用 dwell 而非"某次采样是否等于 idle in transaction"）：session 在"语句返回 → COMMIT 到达"之间存在物理上的极短 `idle in transaction` 窗口；用"dwell 上限"既决定性又不引入 flaky 判据（修复前该项会是整个观测窗长）。本轮实际采用的 4 个量化阈值：fence `max_idle_seconds > 1.0`（必须真的停在 idle）、fence `max_idle_in_transaction_seconds < 2.0`、pooled `max_host_owned_idle_in_transaction_seconds < 5.0`、`singleton_lock_held_samples == len(samples)`（整窗逐采样持锁，不允许"某一刻恰好没采到"）。
>
> 说明 2（为何必须 `clock_timestamp()`）：`now()` 返回**当前事务的开始时刻**。observer 自己也在一个（可能显式开启的）事务里做 SELECT，用 `now() - state_change` 去量别人，会得到负数或极大偏差 —— 首跑就实测到 −0.006 s。`clock_timestamp()` 取真实墙钟，才是可用的 dwell 计量。

## 5. 验证证据

### 5.1 静态门

- `py -3.14 -m ruff check backend/src backend/tests scripts` → `All checks passed!`（exit 0）
- `py -3.14 -m compileall -q backend/src/marketpulse scripts/verify_pre_01b_runtime_host.py` → exit 0
- `git diff --check` → clean

### 5.2 确定性门（§17）：`backend/tests/test_runtime_host.py`

**51 passed，1 warning（唯一的 warning 是第三方 `StarletteDeprecationWarning`）**；修复前存在的 `SAWarning: non-checked-in connection` 已 **完全消失**（P2-01 的直接证据）。

原有 35 项**未删未弱**；新增 16 项（含 parametrize 展开）：

| 新测试 | 关闭 | 断言要点 |
| --- | --- | --- |
| `test_the_fence_connection_is_never_idle_in_transaction` | P1-01 | 从**另一个**会话读 `pg_stat_activity`：fence backend 存在、`state == idle`、无 `idle in transaction`，且 `pg_locks` 仍显示该 backend 持有 advisory lock（= commit 没释放 fence） |
| `test_a_fatal_child_failure_publishes_a_settled_terminal_result_during_the_run` | P1-02(Host 半) | 不做任何外部 shutdown / 不手工 `stop()`，`wait_for_terminal_result()` 在运行期返回；返回时 `state` 已 `STOPPED`、`shutdown_failures == ()`、锁已释放、`children_live == ()`、无 orphan task |
| `test_the_lifespan_owns_the_fatal_result_and_requests_the_process_stop` | P1-02(lifespan 半) | 真实 `RuntimeHost`（TEST 模式注入依赖）+ 真实 `lifespan`：fatal 在 run phase 被观察 → `app.state.runtime_failure` → **请求 `SIGTERM`**（记录而非真发）→ lifespan 抛 `RuntimeError("runtime_host_fatal:…")`；末端锁已释放、`shutdown_failures == []`、注入 engine 已 dispose |
| `test_an_engine_dispose_failure_is_reported_and_never_called_stopped` | P1-03 | `dispose()` 抛错 → `engine_dispose_failed:RuntimeError` ∈ failures、`state == STOP_FAILED`、`owned.disposed is False` |
| `test_a_disposal_that_lies_about_succeeding_is_reported` | P1-03 | `dispose()` 静默返回但未置位 → `engine_dispose_incomplete`、`STOP_FAILED` |
| `test_one_broken_cleanup_step_never_stops_the_others` | P1-03 | `singleton_release_failed:RuntimeError` 记录在案，**其后** engine 仍被 dispose（步骤独立） |
| `test_a_cancelled_stop_still_disposes_everything_and_stays_truthful` | P1-04 | `stop()` 任务被 cancel → 仍抛 `CancelledError`，但 `shutdown_cancelled` 记录、`state == STOP_FAILED`、`_stop_completed is True`、锁与连接已释放、`children_live == ()`、provider stream 已关、无 orphan task、二次 `stop()` 为 no-op |
| `test_an_injected_engine_keeps_its_checkout_baseline_under_sibling_cancellation` | P2-01 | 用 gated `AsyncSession.close()`（仅 open transaction 时阻塞）把"取消落在 session 退出内"变成确定性事件：兄弟失败已发生（health `safety_lane_failure`、safety child 已消失）时，被 shield 保护的持有者**仍存活**且连接仍 checked out；释放后 `pool.checkedout() == 0`、无 orphan、**零 `SAWarning`** |
| `test_a_scanner_error_storm_cannot_grow_host_retention` | P2-03 | 24 种不同异常类型制造风暴（> 3× bound）→ `len(_scanner_error_samples) == 16`、telemetry slice ≤ 8、`maxlen` 正确、Host 仍 non-failed（per-event isolation） |
| `test_host_retention_storage_is_bounded_by_construction` | P2-03 | 直接写 3× bound 进两个 deque → 长度恒定在 maxlen，末尾元素是最后一次写入（界在存储） |
| `test_database_resources_dispose_is_truthful_and_idempotent` | P1-03 / P2-04 | 成功 → `disposed=True` 且只 dispose 一次；失败 → 抛错且 `disposed is False` |
| `test_the_legacy_factory_only_helpers_are_gone_and_unreferenced` | P2-04 | `db.session` 无 `create_session_factory`/`get_db`，且 `backend/src/**/*.py` 全仓零引用 |
| `test_an_enabled_host_must_cover_both_v1_instruments`（3 组 parametrize） | P2-05 | 仅 BTC / 仅 ETH / 两者皆缺 → `V1_REQUIRED_INSTRUMENTS_MISSING:<missing>`，且 Host 停在 `CREATED` |
| `test_additional_instruments_beyond_the_v1_pair_remain_allowed` | P2-05 | BTC+ETH+SOL 全部订阅并各自起 safety worker（契约是下限，不是固定清单） |

### 5.3 测试"有牙齿"证明（变异探针，非提交内容）

`E:/Documents/pre-01b-i1-fix-01-evidence/mutation_check_p2_01.py`：临时把 `_load_active_risk_instruments` / `_heartbeat_loop` / `_reconciliation_loop` 的 `shield=True` 改为 `False`，只跑 P2-01 测试，然后按字节还原：

```
site load_active_risk: occurrences=1
site heartbeat: occurrences=1
site reconciliation: occurrences=1
mutated sha256: 2b6b29966435a6c9ed5dc4e9128477672cd76b4dbaf3194732576c5b860064b2
---- pytest exit: 1        （FAILED test_an_injected_engine_keeps_its_checkout_baseline_…）
restored sha256: 41e2bc1345883b4f715f4455083add8ca2b62ad0f22b71ecb335bb3036d3084b
byte_exact_restore: True
```

⇒ 该测试对"shield 是否存在"是**决定性**的（有 shield → PASS；去掉 shield → FAIL），不是恒真断言。

### 5.4 回归（§18）

按**独占**原则串行执行（运行前后均确认 5446 容器无外来 writer；primary `marketpulse@5446` 已实测在 head `20260913_0009`）：

| 批次 | 内容 | 结果 |
| --- | --- | --- |
| focused | `test_runtime_host.py` | **51 passed** |
| A | `test_group1` + `test_auth` + `test_group2` + `test_group3` + `test_n01_runtime_resource_lifecycle` | **61 passed** |
| B | `test_group4` | **105 passed** |
| C | `test_group5_1..5_4` + `test_n01_restart_recovery` + `test_n01_okx_paper_safety` + `test_se_02a_*` + `test_se_02b_*` + `test_se_02c_*` | **259 passed** |

合计 **476 passed / 0 failed**，覆盖 `backend/tests` **全部 20 个测试文件**（= 本机可执行的 backend 全量套件）。

### 5.5 真实链路（§19 / §20）

- §19 disposable PostgreSQL：确定性套件全部运行在一次性库（`marketpulse_pre_01b_i1_*`，用完即 drop）；`idle in transaction`、duplicate fence、critical child cleanup、dispose truthfulness、cancelled cleanup、injected pool baseline、stop 后 sessions/checkedout = 0 均有上述断言或脚本判据。
- §20 公共 OKX ≥5 min 重跑：

- 脚本：`scripts/verify_pre_01b_runtime_host.py`（blob `188f7ffd43a108a2f8a4aa6f9c1c223073af8fb4`）
- 命令：`py -3.14 scripts/verify_pre_01b_runtime_host.py --minutes 5 --sample-seconds 5 --output <out>.json`
  （在 worktree 内执行；`Settings()` 读 cwd 的 `.env` 指向 primary `marketpulse@127.0.0.1:5446`，脚本自行建 disposable 库再 drop；`--proxy` 默认清空沙箱代理变量并显式指向 `127.0.0.1:10808`）
- 证据文件：`E:/Documents/pre-01b-i1-fix-01-evidence/verify_fix01_okx_5min_final.json`（仓库外，未纳入仓库资产）
- 观测窗口：`2026-09-15T05:24:11Z → 05:29:24Z` = **313.7 s**（真实墙钟，≥5 min）
- **`result = PASS`**；`pass_conditions` = **22 / 22 全 `true`**（FALSE 集合为空）

| 判据 | 观测值 | 结论 |
| --- | --- | --- |
| `singleton_fence_parks_in_idle` | fence 采样状态集合 = `{"idle"}`；`singleton_fence_max_idle_seconds = 2.083994` | PASS |
| `singleton_fence_never_dwells_in_transaction` | `singleton_fence_max_idle_in_transaction_seconds = **0.0**`（整窗 60 次采样全为 0） | PASS |
| `singleton_fence_held_for_the_whole_window` | `singleton_lock_held_samples = 60 / 60`；启动期 `duplicate_refused = True`（`DuplicateRuntimeHostError`，第二个 Host 停在 `STOPPED`、`singleton_connection_present = False`） | PASS |
| `host_owned_idle_in_transaction_is_transient` | `max_host_owned_idle_in_transaction_seconds = **0.001391**`（1.4 ms）。注：`max_host_owned_idle_in_transaction = 3` 是"瞬时并发计数"（heartbeat / reconciliation / risk-load 三个非 singleton 会话恰在语句返回→COMMIT 之间），dwell 才是判据；**fence 自身 0.0 s** | PASS |
| `v1_instruments_covered` | `instruments = ["BTC-USDT", "ETH-USDT"]` | PASS |
| `ready_fraction`（附加） | `1.0`，`states_seen = {"READY"}`，`readiness_statuses_seen = {"READY"}` | PASS |
| `shutdown_without_escalation` / `shutdown_failures_empty` | `shutdown = STOPPED`（**0.463 s**）、`shutdown_failures = []`、`shutdown_escalated = False` | PASS |
| `host_owned_tasks_zero` | `post_stop.orphan_tasks = []` | PASS |
| `db_checked_out_zero` / `engine_disposed` / `lock_engine_disposed` | `owned_engine_checkedout = 0` / `owned_engine_disposed = True` / `lock_engine_disposed = True` | PASS |
| `no_idle_in_transaction_after_stop` | `idle_in_transaction_total = 0`、`host_owned_sessions = 0`、`observer_sessions = 0` | PASS |
| `provider_socket_closed` | `sockets.established_tls_to_exchange = 0`、`provider_socket_connections = 0`、`provider_status = STOPPED` | PASS |
| `eventruntime_live_workers_zero` | `eventruntime_live_workers = 0`、`eventruntime_inflight = 0`；`worker_exception_size = 0` | PASS |
| `no_economic_fact_created` | 经济表全 0：`paper_orders / fills / positions / trades / ledger_entries / trade_plans / execution_intents / ai_decisions / decision_snapshots` | PASS |
| `real_ai_never_constructed` | `ai_sentinel = true`；`safety_reevaluation.enabled = false`（`ai_reevaluation_disabled_in_host_core_v1`） | PASS |
| `no_host_invariant_violation` | `host_invariant_violations = 0`、`telemetry_errors = 0`、`scanner_event_errors = 0`、`safety_overflow = 0`、`scanner_rejected = 0` | PASS |

**关于 `task` 字段的说明（诚实披露，避免 reviewer 误判为旧轮重放）**：证据 JSON 顶层 `task` 仍为 `"PRE-01B-I1"`（脚本内固有标签，本轮未改）。判据该文件属**本轮新跑**的独立证据为：`git.head = b66e17d34173…`、`git.branch = pre-01b-i1-fix-01-runtime-host-lifecycle`，且 `pass_conditions` 含 `singleton_fence_parks_in_idle` / `singleton_fence_never_dwells_in_transaction` / `host_owned_idle_in_transaction_is_transient` / `singleton_fence_held_for_the_whole_window` / `v1_instruments_covered` 这 5 条**仅在本轮修复后才存在**的判据（上一轮脚本只有 21 条且不含这些）。未改该标签是刻意的：改它会改变脚本 blob，从而必须整轮重跑才能保持"证据 ↔ blob"一致；本轮选择保持证据与已快照 blob 的绑定关系，并把差异写在这里。

**一次被推翻的中间结论（留痕，避免 re-reviewer 重踩）**：首跑（`verify_fix01_okx_5min.json`）的 dwell 用量为 `now() - state_change`，而 `now()` 是**观察会话自己的事务开始时刻**，对 `idle in transaction` 的第三方会话会算出**负数**（实测 −0.006 s），因此该文件不可作为 P1-01 证据。修正为 `clock_timestamp()` 后重跑得到上表（`verify_fix01_okx_5min_final.json`）。修正后原始 pooled dwell 的最大值仍是 0.0014 s 量级 ⇒ 结论未变，变的是计量本身可信了。

## 6. 设计决策与理由（供 reviewer 复核）

1. **不发明进程监督者**：进程级重启/看门狗属外部 supervisor；Host 只提供确定性退出信号（D1 §505–516）。实证（§3）表明运行期唯一非零退出的手段是 `SIGTERM`。
2. **lifespan 用 task group own fatal**，而不是 fire-and-forget 通知：结果被 await、被记录、被用于结束 run phase。
3. **`HostTerminalResult` 在 cleanup 之后才发布**：避免"结果先于其背后的 disposal"这种不可信状态。
4. **step 11 进 shield**：见 4.4 的理由（shield 退出时可能立刻重投递被延迟的 cancellation）。
5. **`_force_children_down` 只在需要时动作**：正常路径纯 no-op；被取消/超时的路径才 escalation，并把 escalation 记录进 `shutdown_failures`（=> `STOP_FAILED`）。
6. **P2-05 放在 `_validate_configuration`**：在任何资源打开前 fail closed，拒绝配置不属于"运行时失败"。
7. 未做、也不允许做：改动 g2/g3/g4/edge、schema/migration、边界行为、经济语义。

## 7. P2-02 — 进程审计发现（本文件仅记录，零改动）

- 事实：PRE-01B-I1 的上一轮 Implementation Worker 在实现过程中修改过 `.workbuddy/memory` 与 `.workbuddy/skills`，而这两处不在任何 batch 的 Allowed Changes 内。
- 本轮处理：**只记录**；本轮对 `.workbuddy/memory/**`、`.workbuddy/skills/**` **ZERO CHANGE**（未读改、未新增、未删除）。
- 状态：`REMAINS AS PROCESS AUDIT FINDING`，需由 Human 决定后续治理动作（例如写入协议层禁用清单）。**不由本轮闭合、不标 resolved。**

## 8. 未验证 / 剩余风险（不推断 PASS）

- 本轮**未**做：Human Acceptance、merge `main`、latest-main reconciliation、下一批（G6 / SE-02D / N03 一律 NOT STARTED）。
- 真实链路的 socket/进程级证据依赖 `psutil`（已确认可用 7.2.2）；若某环境缺 `psutil`，脚本会将该项标 `UNAVAILABLE` 并据此判 FAIL（不伪造）。
- P1-02 的**进程级**"外部 supervisor 看到非零退出码"证据在本机以真实 uvicorn 子进程实测得到（`returncode = 3`），但该实证脚本位于仓库外（`E:/Documents/pre-01b-i1-fix-01-evidence/`），未纳入仓库资产；仓库内的判据是"lifespan 在运行期观察到 fatal 并请求 `SIGTERM`" + 上述外证。
- lifespan 半的测试使用 `RuntimeHost` 依赖注入 seam（TEST 模式本来**要求**注入），被测对象是真实的 `lifespan` + 真实 Host 启动/失败/清理路径；未使用假 Host。

## 9. 完成报告（§23）

见本文件末尾"完成报告"小节与提交信息。

### 9.1 交付标识

| 项 | 值 |
| --- | --- |
| Task ID | `PRE-01B-I1-FIX-01` |
| Worktree | `E:/Documents/MarketPulse-AI-pre-01b-i1-fix-01` |
| Branch | `pre-01b-i1-fix-01-runtime-host-lifecycle` |
| Task Base SHA（执行前 `git rev-parse HEAD` 实测） | `b66e17d34173156b3797b664dbe09625511a0a11` |
| Accepted Main SHA（执行前实测；本轮窗口内未移动） | `f887981d18fd7fc696d99cde702d0fec3e72a16c` |
| 状态 | `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW` |

> **关于 commit SHA**：本 dev_log 是本轮 commit 的内容之一，因此文件内**无法**自我引用该 commit 的 SHA（自指）。本轮候选内容的身份由 §9.2 的 **blob SHA** 唯一确定 —— blob 是内容寻址的，任何字节改动都会改变它；commit SHA 还会被提交信息影响，故 blob 是更强的引用。commit SHA 与 push 结果在本轮对外的 §23 回复中给出。

### 9.2 候选内容（`git hash-object` 实测，可在仓库内直接复核）

| 文件 | blob SHA |
| --- | --- |
| `backend/src/marketpulse/runtime_host.py` | `95ba71b4de04266489fba1ad974bf158aa6915fe` |
| `backend/src/marketpulse/api/app.py` | `4a119ed2dab98fc9af6c923731e4c50a41edab6a` |
| `backend/src/marketpulse/db/session.py` | `a634559ea2429d512446b51620f3f8c4e366f14a` |
| `backend/tests/test_runtime_host.py` | `2f15970b9d94f18409133cf514c91f6a9ef15c8c` |
| `scripts/verify_pre_01b_runtime_host.py` | `188f7ffd43a108a2f8a4aa6f9c1c223073af8fb4` |

复核命令：`git hash-object <path>`（逐文件比对）。上表与 `E:/Documents/pre-01b-i1-fix-01-evidence/candidate_blobs.json` 逐条一致。

### 9.3 验证汇总

| 门 | 命令 / 范围 | 结果 |
| --- | --- | --- |
| 静态 | `ruff check backend/src backend/tests scripts`；`compileall`；`git diff --check` | `All checks passed!` / exit 0 / clean |
| 确定性（focus） | `backend/tests/test_runtime_host.py` | **51 passed**（唯一 warning = 第三方 Starlette 弃用警告；修复前存在的 `SAWarning` 已消失） |
| 回归（backend 全量） | 4 批串行独占：`51 / 61 / 105 / 259` | **476 passed / 0 failed**，覆盖 `backend/tests` 全部 20 个文件 |
| 变异（"测试有牙齿"证明） | `mutation_check_p2_01.py`：临时关 3 处 shield → 跑 P2-01 → 按字节还原 | 关 shield ⇒ **FAIL**；`byte_exact_restore: True`（sha256 校验） |
| 真实链路 | OKX 公共 REST + disposable PG，`--minutes 5` | **`result = PASS`，`pass_conditions` 22 / 22 true** |
| Scope | `git diff --name-only`；`.workbuddy/memory` 与 `.workbuddy/skills` 零改动 | 恰好 5 个 allowed 文件；唯一 untracked 是本 dev_log；forbidden 路径 ZERO CHANGE |

### 9.4 显式边界声明（本轮**未**做的事）

- **未** Human Accept、**未** merge / rebase `main`、**未**做 latest-main reconciliation、**未**开始下一批（G6 / SE-02D / N03 一律 `NOT STARTED`）。
- 无 migration、无 schema 变更；`PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md` 未改（按 §6 属 forbidden；状态同步留待 Human Accept 之后的收尾窗口，不在本轮 Scope）。
- P2-02（上一轮 Implementation Worker 曾改动 `.workbuddy/memory` / `.workbuddy/skills`，均不在任何 batch 的 Allowed Changes 内）本轮**只记录、不处理**，状态 `REMAINS AS PROCESS AUDIT FINDING`，见 §7。**不标 resolved。**
- **未**执行任何破坏性清理动作；临时探针与全部证据均在仓库外 `E:/Documents/pre-01b-i1-fix-01-evidence/`，未纳入仓库资产。
- 上游遗留的 `N01-7-R01-RR-P2-01`（slope ≈16.02 MiB/h）等未闭合观察项**本轮未触碰**，状态不变。
