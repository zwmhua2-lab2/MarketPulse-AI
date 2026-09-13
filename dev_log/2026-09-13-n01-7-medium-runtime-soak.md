# N01-7 — 2-hour Medium Runtime Soak（结果：VALIDATED / READY FOR INDEPENDENT REVIEW）

| 项 | 值 |
|---|---|
| Task | `N01-7｜2-hour Medium Runtime Soak` |
| 类型 | Validation / Soak / Evidence Only（非 Design Gate，非功能实现） |
| Branch | `n01-7-medium-runtime-soak` |
| Worktree | `E:\Documents\MarketPulse-AI-n01-7-ms` |
| Accepted Main SHA (Task Base) | `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` |
| 本批次 HEAD | `ece1f7cb0eff4efd8f4ad498234cd2bdb45f6b92` |
| Harness（新增） | `scripts/verify_n01_7_medium_soak.py` blob `febcfd70c1bfe1b20a6cbd456eb734dca9162419` |
| 复用（只读） | `scripts/verify_n01_6_runtime_smoke.py` blob `94853dd747d0e800397b5f6fd743b82e42944e01`；`scripts/verify_n01_7_runtime_soak.py` blob `ed0afd1cdb3b57719e587ce03400fb84a86a1e2c` |
| Migration head | `20260912_0006`（single head）— **这是 Task Base `71abb07` 的 head**；⚠️ 运行结束后实测远端 `main` 已推进至 `20260913_0008`，见 §26 |
| 隔离实例 | 任务专属容器 `marketpulse-n01-7-ms-pg`（`postgres:16-alpine`，PG 16.15）@ `127.0.0.1:5434` |
| 运行窗口（UTC） | `2026-09-13T06:12:05.733437Z` → `2026-09-13T08:14:21.037607Z`（`wall_clock 7335.304 s`，单次连续，无拼接） |

**声明边界**：即便本批次 PASS，也只能证明「已验收的 production runtime 组件在一个 N01 validation harness 内、含一次 fresh-process restart 连续稳定运行 ≥ 2 小时」。它**不是** Integrated Runtime Host、**不是** FastAPI 7×24 运行时、**不是**部署、**不是** N01-8、**不是** N01 整体验收、**不是**实盘交易。

---

## 1. Task / Scope / Out of Scope

### 1.1 In Scope（本批次实际执行）
- 用真实 OKX Public Market Data（`BTC-USDT` + `ETH-USDT` SPOT）+ 一次性 PostgreSQL + 当前已 Accepted 的 production runtime 组件，在 `LIVE_PAPER` 下单次连续运行，`active` 合计 ≥ 7200 s。
- 新增 telemetry、受控重连、受控 STALE→FRESH、fresh-process restart driver、reconciliation checkpoints、protection snapshot evidence。
- 产出 `dev_log/2026-09-13-n01-7-medium-runtime-soak.md`，最小同步 `PROJECT_STATE.md` / `AI_CONTEXT.md`。

### 1.2 Out of Scope（未做、也不得做）
- 未修改任何 production 语义：Scanner / Strategy / Risk / Execution / Protection / Recovery / Reconciliation 行为一律未动。
- 未做 N01-8、未做 Integrated Runtime Host、未启动 N03、未做 SE-02C/02D、未做 G6。
- 未做 Human Acceptance、未把本分支 merge 进 `main`、未宣布 N01 ACCEPTED。
- 未"发现问题→顺手修→接着跑→宣布 PASS"：production 侧只观察、只取证。

### 1.3 Change Boundary（实际落盘）
- 新增：`scripts/verify_n01_7_medium_soak.py`。
- 新增：`dev_log/2026-09-13-n01-7-medium-runtime-soak.md`（本文件）。
- 未改动：`backend/src/**`、`backend/alembic/**`、`backend/tests/**`、`frontend/**`、`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md`。
- 验证：`git diff --stat 71abb07 HEAD -- backend/src backend/alembic backend/tests frontend` = 空；
  `git diff --stat 71abb07 <worktree> -- <同上>` = 空（含未提交状态）。

---

## 2. Repository Truth（CIP-01 / CIP-02 / CIP-03）

执行前从仓库实时读取，不依赖任务书静态描述。

| 事实 | 实时读取值 |
|---|---|
| `git rev-parse main` / `origin/main` / `git ls-remote origin refs/heads/main` | `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` |
| Task Base SHA（任务书导航值） | `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` |
| Delta | **无 baseline drift**（三个来源一致） |

### 2.1 仓库真值与任务书文本的冲突（按 CIP-01 以仓库为准）

任务书称 `N01-7 = NOT STARTED`。实时读取仓库后确认**不成立**：

| 分支 | tip | 远端 | 内容 |
|---|---|---|---|
| `n01-7-2h-runtime-soak-after-f01` | `6b882c9` | 存在 | 首次 N01-7 2h soak：真实 `active 7200.369 s`、62 检查 61 通过、`F01 = LONG_LIVED_PROTECTION_WITNESSED`；结论 `BLOCKED / FIX REQUIRED` |
| `n01-7-inv-01-memory-attribution` | `0a34c72` | 存在 | 修 `N01-7-INV-01`（F-2 check 设计缺陷）+ 内存归因诊断（分类 `C`） |

两条分支**均未 merge 到 `main`**。`PROJECT_STATE.md:22`（`N01-7 = NOT STARTED / READY TO RESUME`）与 `AI_CONTEXT.md:111`（`N01 = NOT STARTED`）均与仓库真值冲突，属文档滞后；本次**不修改**这两处历史描述以外的内容，仅在本次交付范围内最小同步。

### 2.2 本轮定位（与既有两条分支的关系）
- 既有 2h soak **未做**受控重连（`reconnects=0`）、**未做** STALE 注入、**未做** fresh-process restart、**无** socket/handle telemetry、**无** §16 规定的多点 checkpoint。
- 本轮按任务书 §14/§15/§16/§17 补齐上述能力，并把 §19 的 F01 三条见证（A/B/C）做成可审计证据。

---

## 3. Harness 拓扑（复用已验收 N01-6 harness，不复制其代码）

```
verify_n01_7_medium_soak.py --mode acceptance            ← supervisor 进程
  │  · 持有一次性库上下文（n6._disposable_postgres_database）
  │  · 迁移后记录 alembic head；前后读共享主库只读指纹
  │  · 串行拉起两个**独立 OS 进程**（subprocess.Popen，sys.executable）
  │
  ├─ child #1  --mode phase --phase first   → phase_first_raw.json   (+ .progress.jsonl)
  └─ child #2  --mode phase --phase second  → phase_second_raw.json  (+ .progress.jsonl)
```

关键点：

1. **两个 phase 是两个独立 OS 进程**，`--prior-active-seconds` 把 phase first 的实测 active 时长带给 phase second，累加后判定 §12；`fresh_process_restart_performed` 以两个 pid 不同为证。
2. `import verify_n01_6_runtime_smoke as n6`（blob `94853dd7…`，与 `71abb07` / `0a34c72` 三处**逐字节一致**）：复用其代理清理、`backend/src` + `backend/tests` 入 path、`SmokeHarness` / `OKXLiveProvider` / `_consume` / `_controlled_entry` / `_controlled_close` / `_ownership_activity` / `_disposable_postgres_database` / `_wait_for_owned_client_cleanup` 等已验收基座。
3. `import verify_n01_7_runtime_soak as soak`（blob `ed0afd1c…`，与 `0a34c72` 逐字节一致）：复用 `_shared_primary_snapshot` / `_alembic_version` / `_db_state` / `_f01_witness` / `_slope_per_hour` / `_age` / `TASK_OWNED_DATABASE_PORT` / `N01_7_OWNED_APPLICATION`。**只读复用，未改动一行**。
4. `_ControlledStream`：在已验收 provider stream 之上加一层包装。
   - 受控重连 = 请求后 `break`（generator 关闭 → `websockets.connect` 退出 → 真实 WebSocket 断开），`finally` 中 `aclose()`，再重新 `provider.stream(...)`。**transport 本身未改**。
   - 受控 stall = `set_stale(True)` 后继续消费但**不投递**，只计数并记住被扣留事件。
5. 采集面：每次采样记录 queue/inflight/worker/dedupe/trade_dedupe/pg 会话（owned/other/idle-in-tx）/RSS/socket/handle/asyncio task 数，并**增量写 JSONL**（`*.progress.jsonl`），使中途崩溃也留下真实时间序列。
6. 运行时进程**不加载 `tracemalloc`**，也不做对象普查 —— 依 `N01-7-INV-01` 的方法学结论，`tracemalloc` 是侵入性探针（同负载下 RSS 斜率可被抬高两个数量级），不得与测量同窗口。

---

## 4. 环境与隔离（§10 P-01~P-05）

### 4.1 P-01 Repository Truth
见 §2。

### 4.2 P-02 Isolated Worktree
`E:\Documents\MarketPulse-AI-n01-7-ms`，branch `n01-7-medium-runtime-soak`，base `71abb07`。历史 worktree（`-soak` / `-inv-01`）保持**只读**。

### 4.3 P-03 Disposable PostgreSQL（隔离实测）

| 项 | 实测 |
|---|---|
| 容器 | `marketpulse-n01-7-ms-pg`，`postgres:16-alpine`，`Up`，`RestartCount=0`，`StartedAt 2026-09-13T05:46:27Z` |
| 端口绑定 | `127.0.0.1:5434->5432/tcp`（**仅本机回环**） |
| 一次性库命名 | `marketpulse_n01_7_<uuid12>`（每次运行新库；本批次运行 = `marketpulse_n01_7_9372d796b4f1`） |
| 显式 DSN | 由 `n6._disposable_postgres_database()` 上下文生成并**显式**传给两个 child（`--database-url`），不依赖环境推断 |
| 被测 client `application_name` | `marketpulse-n01-7-runtime`（`soak.N01_7_OWNED_APPLICATION`） |
| Observer `application_name` | `marketpulse-n01-7-observer`（`n6.OBSERVER_APPLICATION`），与被测 client **分离** |
| 迁移作用域 | 只作用于该一次性库；`alembic heads` = `20260912_0006 (head)`，单 head |
| 共享主库 | `marketpulse-postgres` @ `127.0.0.1:5432`，**只做 before/after 只读快照**（revision / protection 列 / 是否出现 N01-7 owned 会话） |
| 任务结束 | 一次性库由上下文管理器 drop；`_n01_6_leftover_databases()` 复核残留 |

**绝对禁止项已遵守**：未使用 primary MarketPulse DB（5432）作为被测库；未使用其他窗口的 SE DB；未为 PASS 修改任何系统级网络/代理配置。

### 4.4 P-04 Environment（实测）

| 项 | 值 |
|---|---|
| OS | `Windows-11-10.0.26200-SP0` |
| Python | `3.14.2 (tags/v3.14.2:df79316, Dec 5 2025) [MSC v.1944 64 bit (AMD64)]`（`py -3.14`，与全项目测试门一致） |
| PostgreSQL | `PostgreSQL 16.15 on x86_64-pc-linux-musl`（`postgres:16-alpine`） |
| psutil | 可用（`psutil_available = True`；socket/handle 采集依赖它） |
| OKX WebSocket | `wss://ws.okx.com:8443` **直连**可达（测试订阅回执正常） |
| OKX REST（metadata） | 沙箱内直连失效，经**本机既有用户代理** `http://127.0.0.1:10808` 可达（每 phase 仅 1 次，实测 ≈3.24 s，返回 `BTC-USDT`/`ETH-USDT`） |
| 代理处置 | 仅为**本进程**清空沙箱 `HTTP(S)_PROXY`/`ALL_PROXY`（含小写）；REST 走本机既有用户代理；WS 直连。**未写入任何机器/系统代理配置** |
| 未使用 | 未为本次 PASS 修改系统网络、代理、防火墙或 hosts |

> 环境限制（如实记录，非产品结论）：本 workspace 的 Bash 工具缺 coreutils（`ls`/`head`/`tail`/`wc`/`date`/`sleep`/`dirname` 不可用），所有枚举/统计改由 `py -3.14` 完成；PowerShell stdout 偶被吞，凡核验一律落盘后复核。这些只影响操作手段，不影响被测运行时与证据真实性。

### 4.5 P-05 Mandatory Preflight 结果

| 检查 | 结果 |
|---|---|
| `Settings().database_url` 归属 | `postgresql+asyncpg://127.0.0.1:5434/marketpulse`（**指向任务专属实例**，非共享主库） |
| `alembic heads` | `20260912_0006 (head)`（single head） |
| 一次性库残留（运行前） | `0` |
| 共享主库 before 指纹 | revision `20260905_0004`，`protection_columns = []`，N01-7 owned 会话 `0` |
| 端到端可达 | OKX WS 直连 OK；OKX REST 经本机用户代理 OK |

---

## 5. Harness 验证历史（§12：短跑只能是 PROBE）

正式 2h Run 之前先做 PROBE 以剔除 harness 自身缺陷。**PROBE 不构成 Acceptance**，其时长**不**计入 2h Clock。

| # | 结果 | 关键现象 | 分类 |
|---|---|---|---|
| PROBE#1 | FAIL | `_CleanupObservation` 字段名误用（`released_seconds` → 实为 `elapsed_seconds`） | CASE B（harness） |
| PROBE#2 | 部分通过 | phase `second` 完整跑通且 `OK`（recovery / reconnect / stale / checkpoint / F01-after-restart / controlled close 全部取得正面真实证据）；phase `first` 以 `KeyError: 'plan_version'` 早退 —— 我先前误信 `plan` 视图含 `plan_version`，实读 `verify_n01_6_runtime_smoke.py:694-703` 确认**不含** | CASE B（harness） |
| PROBE#3 | **PROBE_OK** | 两 phase 均 `OK`、`active 150.1 / 150.4 s`、双 pid、`restart_gap 5.708 s`、`failures: []`。但**暴露关键缺陷**：`stale_cycles_health_unavailable = False`、`stale_cycles_risk_increasing_fail_closed = False` | CASE B（harness，见 F-1） |
| PROBE#4 | FAIL | `TypeError: '>' not supported between 'str' and 'datetime.datetime'` —— `feed["last_bbo_received"]` 存的是 `.isoformat()` **字符串**（`verify_n01_6_runtime_smoke.py:392`），我按 datetime 比较 | CASE B（harness） |
| PROBE#5 | FAIL | `TypeError: 'asyncio.locks.Lock' object does not support the context manager protocol` —— `with feed["lock"]:` 应为 `async with` | CASE B（harness） |
| PROBE#6 | **PROBE_OK** | 两 phase `OK`、`active 150.008 / 150.105 s`、`restart_gap 5.463 s`、68 检查 60 通过、`failures: []`（余 8 项 False 全属 PROBE 固有，见下）。**stale 修复验证通过** | PROBE 通过 |

PROBE#6 中 8 项 False 及其性质（全部属"短跑无法满足"，已登记于 `PROBE_SCOPE_KEYS`，故不计入 PROBE 失败）：

| 项 | 原因 |
|---|---|
| `active_total_ge_7200` | 300 s 短跑 |
| `checkpoints_cover_required_points` / `checkpoint_coverage_complete` | probe 标签集与时间带不同 |
| `reconnects_ge_5` | probe 仅 4 次 |
| `f01_plan_ttl_expired_while_position_open` 等 4 项 | **probe 模式按设计跳过 F01 见证**（TTL=30 min，短跑无法自然过期） |

### 5.1 本批次在 harness 侧发现并修复的问题（全部 CASE B，未触碰 production）

| 编号 | 问题 | 证据 | 修复 |
|---|---|---|---|
| **H-1** | **STALE 注入不成立**：取 `controlled.last_withheld[BTC]` = **最新**一条被扣留事件（收到于停顿末尾），实测 `age_seconds = 1.594 / 0.393`，**远小于 5.0 s TTL**。故 `health` 仍 `HEALTHY`、`fresh_flag=True`、`risk_gate_during_stall.admitted=True`；此前观察到的 `execute_intent REJECTED` 只是报价龄跨过 2.0 s 阈值的时序偶然 | PROBE#2 / PROBE#3 的 `stale_cycles` 记录 | 改为投递**停顿前最后一条被真正投递的报价**（`feed["latest_bbo"][BTC]`，在 `set_stale(True)` **之前**抓取），60 s 后投递 → 龄 ≈60 s ≫ TTL |
| **H-2** | 重连"新事件"见证过弱：只要求总事件计数 +1，可能由断线前已到达的事件满足 | PROBE#3 `events_delta = 1` | 改要求**最新 BBO 收据时间严格晚于断线请求时刻** |
| **H-3** | §23 socket/handle gate 只用"每次重连前后差"：每次泄漏 +1 也可蒙过 | 代码审查 | 改为「首/末次重连之间的区间差」**AND**「各 phase 序列净增长」双视图 |
| **H-4** | `no_python_memory_carried_over` 直接复述 pid 不同 = 同义反复 | 代码审查 | 增要求 phase second 在自己进程内完成 warm-up 且 recovery 非空、且 phase first 已结束 |
| **H-5** | `_run_child` 超时会抛 `TimeoutExpired` 炸掉 supervisor，丢证据 | 代码审查 | 超时即 terminate→kill→reap 并记录 `timed_out` |
| **H-6** | 子进程非零退出码不影响裁决（写在报告后崩溃仍可能 PASS） | 代码审查 | 新增 `phase_processes_clean` 检查并把 `phase_process_errors` 纳入 `blocking` |
| **H-7** | `_main_phase` 无兜底：`_phase_scenario` 之外抛错则不产报告 | PROBE#4/#5 均验证了 `_phase_scenario` 内兜底有效；仍补外层 | 外层 try/except 必产报告（含 traceback） |
| **H-8** | 长跑中途崩溃会丢掉整段真实时间序列 | 设计审查 | 每样本增量写 `*.progress.jsonl`（**每 phase 启动时清空**，避免跨 run 混样） |
| **H-9** | §16 checkpoint 只校验标签集合，不校验落点时刻 | 任务书 §16 | 增按 `absolute_elapsed_seconds` 的四段时间带覆盖校验 |
| **H-10** | `feed` 收据标记是 ISO 字符串却被当 datetime 比较 | PROBE#4 | 新增 `_as_datetime()` 统一解析 |
| **H-11** | 同一文件并行编辑会丢失更新（本机环境行为），且已两次踩中类型误用 | 本次实操 | 改为**单次确定性 patch 脚本**（Python 读全文 → `count(old)==1` 断言 → 一次写盘），每步后跑静态门 |

**统计**：PROBE#3 之前 harness 缺陷 2 处（#1/#2）；PROBE#3 暴露 1 处关键缺陷（H-1）；补丁 5 引入 2 处类型/协议回归（H-10/H-11 对应），由 PROBE#4/#5 立刻捕获并修复。**未有任何一处改动落到 production 代码**。

> 因为 harness 修复发生在**正式 2h Run 之前**，依 §12 不存在"修复后拼接时间"的问题：本批次 2h Clock 完全来自下文这一次连续运行。

## 6. Run Identity 与裁决

| 项 | 值 |
|---|---|
| `task` / `mode` | `N01-7` / `ACCEPTANCE` |
| `result` | **`PASS`**（`failures = []`） |
| 一次性库 | `marketpulse_n01_7_9372d796b4f1` @ `postgresql+asyncpg://127.0.0.1:5434` |
| `migration_head_observed` | `20260912_0006` |
| `started_at`（UTC） | `2026-09-13T06:12:05.733437+00:00` |
| `finished_at`（UTC） | `2026-09-13T08:14:21.037607+00:00` |
| `wall_clock_seconds` | `7335.304` |
| `phase_first_active_seconds` | `3600.166`（`06:12:14.039` → `07:12:14.205`） |
| `phase_second_active_seconds` | `3720.414`（`07:12:19.728` → `08:14:20.142`） |
| **`total_active_seconds`** | **`7320.580` ≥ 7200**（§12 达标，余量 `+120.580 s`） |
| `phase_first_pid` / `phase_second_pid` | `29320` / `30332`（**两个不同 OS 进程**） |
| `restart_gap_seconds` | `5.523` |

**Check 汇总**：顶层 `checks` 共 **68 项，全部 `true`**；`failures` / `harness_errors` / `shutdown_errors` / `phase_failures` / `phase_process_errors` **均为 `[]`**。

两 phase 各自报告的 `checks`（phase 内 33 项）与 `result: OK` 亦全绿。

> ⚠️ 依 §7，Worker **不自行写 ACCEPTED**。本条 `PASS` 是 harness 裁决，仅支持 `VALIDATED / READY FOR INDEPENDENT REVIEW`。

---

## 7. 市场数据连续性（真实 OKX Public 流，§11）

两 phase 合计消费 **81 120** 条 normalized 事件（`31128 + 49992`），全部来自真实 OKX SPOT 公共流，无合成数据。

| 指标 | phase first | phase second |
|---|---|---|
| `connection_attempts` | 4（初始 1 + 受控 3） | 3（初始 1 + 受控 2） |
| `provider_reconnects`（自发性） | **0** | **0** |
| trades `BTC-USDT` / `ETH-USDT` | `3443` / `4396` | `4882` / `13526` |
| BBOs `BTC-USDT` / `ETH-USDT` | `10225` / `13064` | `10927` / `20657` |
| `total_normalized_events` | `31128` | `49992` |
| 首条 `BTC` / `ETH` | `06:12:12.023656` / `06:12:12.105533` | `07:12:19.730459` / `07:12:20.825573` |
| 末条 `BTC` / `ETH` | `07:12:12.191136` / `07:12:14.001169` | `08:14:18.882170` / `08:14:16.560461` |
| `max_inter_arrival_gap` `BTC` / `ETH` | `61.166 s` / `61.638 s` | `60.802 s` / `60.250 s` |
| `health_transitions` | 1（`null → HEALTHY` @ `06:12:12.053360`） | 1（`null → HEALTHY` @ `07:12:19.760793`） |
| `stale_periods`（provider 自发 stale） | `[]` | `[]` |

**如实标注**：`max_inter_arrival_gap ≈ 60–62 s` **不是网络异常**，而是本 harness 注入 60 s 投递停顿（§15 STALE 周期：`stall_seconds 60.009` / `60.013`）造成的直接后果。`stale_periods = []` 说明 **provider 自身从未自发判 stale**，所有 stale 都来自受控注入；`provider_reconnects = 0` 说明 5 次断线**全部**是本 harness 请求的，无自发性重连掩盖。

`health_transitions` 每 phase 仅 1 条（→ `HEALTHY`）也说明：除受控停顿窗口外，全时段 `CORE_MARKET_DATA = HEALTHY`。

---

## 8. 采样序列（15 分钟分桶，共 730 样本）

每 10 s 采样一次，两 phase 共 `730` 样本；按绝对时间分 15 分钟桶：

| 窗口 | 区间 | n | btc_bbos | eth_bbos | q_max | inflight_max | w_exc | dedupe_max | trade_max | pg_own_max | pg_other_max | sockets | handles | rss(MiB) | tasks |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0–15 min | 91 | 1660 | 1915 | 0 | 1 | 0 | 448 | 1075 | 3 | 0 | [4,6] | 185–197 | 113.13–119.82 | 9 |
| 1 | 15–30 | 89 | 3491 | 3848 | 0 | 1 | 0 | 887 | 2083 | 3 | 0 | [6] | 185 | 115.80–117.36 | 9 |
| 2 | 30–45 | 90 | 6632 | 8793 | 0 | 1 | 0 | 2117 | 5215 | 3 | 0 | [6] | 185 | 116.65–120.74 | 9 |
| 3 | 45–60 | 89 | 10213 | 13043 | 0 | 1 | 0 | 3065 | 7832 | 3 | 0 | [6] | 185 | 119.34–126.08 | 9 |
| 4 | 60–75 | 91 | 1890 | 2150 | 0 | 1 | 0 | 474 | 1134 | 2 | 0 | [5,6] | 184–196 | 114.46–119.09 | 9 |
| 5 | 75–90 | 89 | 4486 | 7468 | 0 | 1 | 0 | 2842 | 6384 | 2 | 0 | [5] | 184 | 118.30–119.79 | 9 |
| 6 | 90–105 | 90 | 7893 | 15153 | 0 | 1 | 0 | 5969 | 8192 | 2 | 0 | [5] | 184 | 117.35–119.78 | 9 |
| 7 | 105–120 | 89 | 10352 | 19971 | 0 | 1 | 0 | 7535 | 8192 | 2 | 0 | [5] | 184 | 118.17–125.03 | 9 |
| 8 | 120–122 min | 12 | 10915 | 20652 | 0 | 1 | 0 | 7793 | 8192 | 2 | 0 | [5] | 184 | 125.17 | 8 |

（`btc_bbos`/`eth_bbos` 为**该桶末**的累计值；窗口 4 起点下滑 = phase first 结束、phase second 新进程计数归零，是 §17 fresh-process restart 在 telemetry 上的正常反映。）

分桶结论：
- `q_max = 0`、`inflight_max = 1`、`w_exc = 0` **贯穿全部 8 个窗口**，无背压堆积、无 worker 异常。
- `pg_other_max = 0` **贯穿全时段** → 隔离期内没有任何非本任务 client 会话混入（§24）。
- `sockets` 稳定在 `4–6`、`handles` 稳定在 `184–197`、`tasks` 稳定在 `8–9`（`n01_owned_task_count` 恒定 `4`）。

分布统计（730 样本）：`rss_mb` min `113.133` / mean `118.762` / max `126.078` / last `121.266`；`handles` min `184` / mean `184.921` / max `197`；`sockets` min `4` / mean `5.492` / max `6`；`asyncio_tasks_total` min `7` / max `9`；`n01_owned_task_count` 全程恒为 `4`。

---

## 9. 队列 / backpressure / worker（§20）

| 检查 | 证据 | 结果 |
|---|---|---|
| `queue_within_capacity` | 全 730 样本 `queue_size ≤ queue_capacity(2048)`，`q_max = 0` | ✅ |
| `worker_count_stable` | 全程 `worker_count = 4`（`workers_alive = 4`） | ✅ |
| `worker_exceptions_zero` | `worker_exceptions = 0`，容量 `128` | ✅ |
| `inflight_empty`（settle 点） | 5 次重连 settle 与 2 次 stale cycle 后 `inflight = 0` | ✅ |
| `final_queue_empty` | 两 phase `queue_final = 0` | ✅ |
| `final_inflight_empty` | 两 phase `inflight_final = 0` | ✅ |
| `final_no_owned_tasks` | 两 phase `workers_final = 0`、`worker_tasks_final = []`、`n01_owned_task_count` 归零 | ✅ |
| `no_detached_runtime_tasks` | `background_tasks.remaining_pending_tasks = []`（`grace 5.0 s`） | ✅ |

队列容量 `2048`，实测峰值 `0`；即在整个 2h 窗口内**连一次性瞬时堆积都没有出现**。事件尽速 drain（`settle` 点在断线后 ~26 s 处 `queue_size = 0`）。

---

## 10. Dedupe / 有界结构

| 结构 | 容量 | 实测峰值 | 判据 |
|---|---|---|---|
| `dedupe_size`（BBO/Trade 去重） | `8192` | `7793`（窗口 8） | `dedupe_within_capacity = true` |
| `trade_dedupe_size` | `8192` | `8192`（**饱和**，窗口 6 起） | 同上，`≤` 容量 |

`trade_dedupe` 在窗口 6（90–105 min）达到容量上限 8192 后**保持饱和而非越过**，属 `_trade_dedupe` FIFO 容量语义（与 `N01-7-INV-01` 对周转语义的修正一致）：饱和后仍表现为**有界**，`dedupe_within_capacity = true` 全程成立。**未观察到无界增长**。

---

## 11. 内存验收（§21）— 含一处必须显式说明的边界

harness 采用任务书 §21 的 **AND** 判据：`total_growth > 64 MiB` **AND** `second_half_trend > 5 MiB/h` 才构成 Finding。

| 项 | 值 |
|---|---|
| 采样点 | `657` |
| `warmup_baseline_mib` | `118.023` |
| `peak_mib` | `126.078` |
| `final_mib` | `121.266` |
| **`total_growth_mib`** | **`8.055`**（阈值 `64.0`，**远未触及**） |
| **`second_half_trend_mib_per_hour`** | **`5.255`**（阈值 `5.0`，**已越过**） |
| `overall_trend_mib_per_hour` | `2.045` |
| `finding` | **`false`**（`memory_within_approved_condition = true`） |

**⚠️ 必须显式记录，不得掩盖**：`second_half_trend = 5.255 MiB/h` **已越过 5.0 MiB/h 阈值**。本批次判 `finding = false` 的**唯一**原因是 AND 判据的另一支（`total_growth 8.055 MiB ≪ 64 MiB`）未成立。即：**按本批次已批准判据不构成 Finding，但斜率是真实的正值**，与 `N01-7-INV-01` 的 `C｜ALLOCATOR_OR_NATIVE_RETENTION_LIKELY` 方向一致。

四个独立视角（皆为正斜率）：

| 视角 | 斜率/增量 |
|---|---|
| 全程（两 phase 合并） | `+2.045 MiB/h` |
| phase first 后段 | `+17.88 MiB/h` |
| phase second 后段 | `+10.785 MiB/h` |
| 外部监视器 private bytes | `+11.4 MiB`（PID 29320）/ `+23.7 MiB`（PID 30332） |

**进程外独立监视器**（`external_monitor.py`，**不加载 `tracemalloc`**，无侵入探针，符合 `N01-7-INV-01` 方法学）：

| PID | rss 起→终（峰值） | private 起→终 | uss 起→终 |
|---|---|---|---|
| `29320`（phase first） | `117.777 → 121.516`（peak `125.902`） | `99.941 → 111.387` | 见 `external_monitor.jsonl` |
| `30332`（phase second） | `102.695 → 121.383`（peak `125.137`） | `85.309 → 108.992` | 见 `external_monitor.jsonl` |

外部视角印证：**CPU/RSS 数值均处于百 MiB 量级、无失控**，但两个进程的 private bytes 均呈持续正增长 —— 与 harness 内测量方向一致。

**结论**：`memory_within_approved_condition = true`（AC 满足）；但 §21 的 5.0 MiB/h 支已越线，这是一个**必须交给 Independent Review 判断的开放问题**，不是本批次可以自行宣称"内存无问题"的结论。

---

## 12. PostgreSQL 生命周期与隔离（§10 P-03 / §24）

### 12.1 会话归属（禁止 datname-only 计数）

- 被测 client `application_name = marketpulse-n01-7-runtime`（`soak.N01_7_OWNED_APPLICATION`）
- Observer `application_name = marketpulse-n01-7-observer`，**与被测 client 分离**
- 查询口径：`pg_stat_activity` 加 `AND backend_type = 'client backend'`，按 `application_name` 归属

| 检查 | 证据 | 结果 |
|---|---|---|
| `pg_no_foreign_client_sessions` | 两 phase `cleanup.foreign_rows = []` | ✅ |
| `pg_other_sessions_zero_all_samples` | 全 730 样本 `pg_other_client_sessions = 0` | ✅ |
| `pg_idle_in_transaction_zero` | `final_idle_in_transaction = 0` | ✅ |
| `pg_owned_clients_zero` | phase first `final_client_sessions = 0`/`final_server_sessions = 0`；phase second 同 | ✅ |

运行期 `pg_owned_client_sessions` 稳定在 `1–3`（pool `checkedout` 有界），**无泄漏、无 idle-in-transaction 长事务**。

### 12.2 隔离实测

| 项 | before | after |
|---|---|---|
| 共享主库 revision（`127.0.0.1:5432`） | `20260905_0004` | **`20260905_0004`**（未变） |
| `protection_columns` | `[]` | `[]` |
| 可见的 N01-7 owned 会话 | `0` | `0` |
| 主库 `client_sessions_by_application` | `[{"marketpulse-shared-primary-observer", 1}]` | 同 |

- `leftover_databases = 0` → `disposable_database_residue_zero = true`
- `shared_primary_unchanged = true`、`shared_primary_no_owned_sessions = true`
- `single_migration_head = true`（`alembic heads` = `20260912_0006 (head)`，单 head）
- `runtime_dsn_points_at_task_owned_instance = true`（DSN 指向 `127.0.0.1:5434/marketpulse_n01_7_9372d796b4f1`）

**P-03 绝对禁止项复核**：未使用 primary MarketPulse DB 作为被测库；未使用其他窗口的 SE DB；迁移只作用于一次性库；**未为 PASS 修改任何系统级网络/代理配置**（`proxy_note` 已记录：仅为本进程清空沙箱代理环境变量，REST 走本机既有用户代理 `http://127.0.0.1:10808`，WS 直连，未写入任何机器级代理配置）。

---

## 13. 受控 Paper 生命周期（§18 LIVE_PAPER SPOT LONG witness）

单笔 `BTC-USDT` SPOT LONG，全链路证据：

| 阶段 | 证据 |
|---|---|
| **ENTRY** | `entry_quote` `bid 77310.4 / ask 77310.5`、`data_quality FRESH`、`age_seconds_at_use 0.192`；`risk_gate {admitted: true}`；`plan_7d212f0ce53054e676a6e30c`（`BUY` / `MARKET` / `intended_notional 100.0` / `stop 73444.88` / `tp 81175.92`）；`order_4df12f7a…` / `fill_4df12f7a…`；`position pos_6dbdb97a…` `qty 0.0012928389415086728` @ `77349.15525`；填价 = `ask + slippage`；`fee 0.1` |
| **幂等** | `duplicate_intent` → `{status: EXECUTED, reason: duplicate_intent, counts_unchanged: true}`（`entry_duplicate_intent_idempotent = true`） |
| **LONG-RUN** | 持仓跨 TTL（`expires_at 06:43:15.106`）持续 OPEN，`open_position_unprotected_incidents = 0` 全程 |
| **RECONNECT** | 5 次受控重连期间持仓与 protection 快照不变（见 §14） |
| **STALE** | 2 次停顿期间 `no_economic_fact_during_stall = true`、`protection_facts_preserved = true`（见 §15） |
| **FRESH** | 两次停顿结束后 `health_status HEALTHY`、`protection_reason HOLD`、`fresh_recovered = true` |
| **RESTART** | phase second 新进程从 PostgreSQL 恢复该持仓与快照（见 §17） |
| **CLOSE** | `controlled_manual_close` @ `08:14:20.167`；`close_quote bid 77066.6 / ask 77066.7`、`age 1.373`；`order/fill_1e84c93b…`；`SELL FILLED @ 77028.0667`、`qty 0.0012928389415086728`、`fee 0.09958488421888746`；`position_after_close_quantity = 0.0`；`exit_reason = MANUAL_CLOSE` |

经济终态：`cash_balance 9999.385299334668`、`reserved_cash 0.0`、`realized_pnl -0.5147006653314238`。

`fill_4df12f7a…`（BUY）与 `fill_1e84c93b…`（SELL）数量严格相等、价格不同 —— 人工平仓的**真实价差亏损** `-0.5147` 由 `fee 0.1 + 0.0996` 与价格差解释（`77349.15525 → 77028.0667`），非账面构造。**未出现任何非本交易产生的额外 fill**。

---

## 14. 受控重连（§14，目标 ≥5 次，实测 5 次）

每次由 harness 请求 `break`（generator 关闭 → 真实 WebSocket 断开）→ 重新 `provider.stream(...)`。

| # | phase | 时刻（UTC） | phase elapsed | `disconnect_observed` | `reconnects_performed` | `provider_reconnects` | `disconnect_requested_at` → `newest_bbo_after` | 严格更晚 | `events_delta` | socket Δ | handle Δ | recon |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | first | `06:17:14.160` | 300.1 s | ✅ | 1 | 0 | `06:17:14.161407` → `06:17:15.928569` | ✅ (+1.767 s) | 7 | 0 | 0 | ✅ |
| 2 | first | `06:32:14.239` | 1200.2 s | ✅ | 2 | 0 | `06:32:14.240475` → `06:32:14.647665` | ✅ (+0.407 s) | 1 | 0 | 0 | ✅ |
| 3 | first | `06:52:14.111` | 2400.1 s | ✅ | 3 | 0 | `06:52:14.112999` → `06:52:14.137436` | ✅ (+0.024 s) | 1 | 0 | 0 | ✅ |
| 4 | second | `07:22:20.113` | 600.4 s | ✅ | 1 | 0 | `07:22:20.114663` → `07:22:20.182033` | ✅ (+0.067 s) | 1 | 0 | 0 | ✅ |
| 5 | second | `07:52:19.934` | 2400.2 s | ✅ | 2 | 0 | `07:52:19.935947` → `07:52:20.466054` | ✅ (+0.530 s) | 1 | 0 | 0 | ✅ |

每次 settle（断线后 ~26 s）：`queue 0/2048`、`inflight 0`、`workers 4`、`worker_exceptions 0`、`system_state RUNNING`、`operator_state NORMAL`、`reconciliation_ok = true`、`diagnostics = []`。`dedupe`/`trade_dedupe` 在 settle 点分别为 `189/546`、`584/1401`、`1547/3493`、`306/705`、`4868/8192` —— **重连不导致去重结构越界**。

对照 check：`reconnects_ge_5 = true`、`controlled_reconnects_recovered_fresh = true`、`reconnect_reconciliation_ok = true`。

**结论**：5 次全部满足「`CONNECTED` → 受控断开 → 重连 → 收到 `FRESH` 事件」；`provider_reconnects` 全程 `0` 证明断线确由本 harness 触发而非 provider 自发；**无永久 socket/task 泄漏**（Δ=0）、**无重复污染**（`duplicate_intent` 幂等、settle 后 recon OK）、**无经济重复**。

---

## 15. 受控 STALE → FRESH（§15，目标 ≥2 次，实测 2 次）

注入方式（经 H-1 修复后）：取**停顿前最后一条真正被投递的报价**，`set_stale(True)` 后 60 s 内只消费不投递。

| 项 | cycle 1（phase first） | cycle 2（phase second） |
|---|---|---|
| 时刻（UTC） | `06:27:14.395`（elapsed 900.4 s） | `07:32:19.860`（elapsed 1200.1 s） |
| `stall_seconds` | `60.009` | `60.013` |
| `withheld_events`（本 cycle） | `356` | `1312` |
| stale 报价来源 | `last_quote_delivered_before_the_stall` | 同 |
| `bid` / `ask` | `77291.3` / `77291.4` | `77111.4` / `77111.5` |
| `age_seconds` | **`60.466`** | **`60.049`** |
| `stale_quote_age_exceeds_ttl` | ✅（`> 5.0 s`） | ✅ |
| `health_status`（stall 中） | **`UNAVAILABLE`** | **`UNAVAILABLE`** |
| `fresh_flag` | `false` | `false` |
| `protection_reason` | `CORE_MARKET_DATA_STALE` | `CORE_MARKET_DATA_STALE` |
| `protection_triggered` / `protection_fill_id` | `false` / `null` | `false` / `null` |
| `risk_gate_before_stall` | `{admitted: true, reason: null}` | `{admitted: false, reason: PLAN_EXPIRED}` |
| `risk_gate_during_stall` | `{admitted: false, reason: RUNTIME_STATE_DATA_DEGRADED}` | 同 |
| `execute_intent_during_stall` | `{REJECTED, RUNTIME_STATE_DATA_DEGRADED}` | 同 |
| protection 快照（stall 中） | `plan_7d212f0ce53054e676a6e30c v1 stop 73444.88 tp 81175.92`，`present: true` | 同 |
| `open_position_unprotected_incidents` | `0` | `0` |
| `counts_before` == `counts_after_stall` | ✅（1/1/1/1/1/1） | ✅ |
| `no_economic_fact_during_stall` | ✅ | ✅ |
| `protection_facts_preserved` | ✅ | ✅ |
| `fresh_recovered` | ✅（`HEALTHY` / `HOLD` / `triggered: false`） | ✅ |
| `reconciliation_ok` | ✅ `diagnostics: []` | ✅ `diagnostics: []` |

**关键语义证据**：cycle 1 在 stall 中 `risk_gate_before_stall.admitted = true`，而 stall 中转为 `false / RUNTIME_STATE_DATA_DEGRADED` —— 这是「risk-increasing 在数据降级期 fail closed」的**同一进程内前后对照**（不是两个不同进程的对比）。`stale_cycles_risk_increasing_fail_closed = true`。

**如实标注（重要边界）**：cycle 2 的 `risk_gate_before_stall` 已是 `PLAN_EXPIRED`（TTL 早已过期），因此它的 fail-closed 结论**不能独立证明** stale 的因果 —— 真正承载该因果的是 **cycle 1**（前 `true` → 中 `false`，原因为 `RUNTIME_STATE_DATA_DEGRADED` 而非 `PLAN_EXPIRED`）。cycle 2 的价值在于：**TTL 过期后再次经历数据降级，durable protection 快照仍完整且 `open_position_unprotected_incidents = 0`**。两者互补，不重复。

另：H-1 修复前（PROBE#3）该注入的 `age_seconds` 仅 `1.594 / 0.393 s`，**不足以越过 5.0 s TTL**，那时观察到的 fail-closed 是时序偶然。修复后 cycle 1 的 `before=true → during=false` 才是真实证据。**这是 harness 缺陷（CASE B）在正式 Run 之前被发现并修正的记录，不是 production 缺陷。**

---

## 16. Reconciliation Checkpoints（§16，目标 ≥7，实测 7）

| # | label | phase | 绝对时刻 | 绝对 elapsed | `ok` | invariants | diagnostics |
|---|---|---|---|---|---|---|---|
| 1 | `start` | first | `06:12:14.199` | `0.1 s` | ✅ | 13/13 | `[]` |
| 2 | `abs_30m` | first | `06:42:14.222` | `1800.2 s` | ✅ | 13/13 | `[]` |
| 3 | `before_restart` | first | `07:11:14.114` | `3540.1 s` | ✅ | 13/13 | `[]` |
| 4 | `final_before_stop` | first | `07:12:14.220` | `3600.2 s` | ✅ | 13/13 | `[]` |
| 5 | `after_restart` | second | `07:12:19.9` | `3600.3 s` | ✅ | 13/13 | `[]` |
| 6 | `abs_90m` | second | `07:41:20.0` | `5340.3 s` | ✅ | 13/13 | `[]` |
| 7 | `final` | second | `08:14:20.6` | `7320.9 s` | ✅ | 13/13 | `[]` |

13 条不变量在每个 checkpoint 全 `true`：`reserved_cash_matches_open_buys`、`sell_reservations_within_positions`、`position_quantities_match_fills`、`available_cash_non_negative`、`fills_have_one_ledger_entry`、`filled_orders_match_fills`、`active_plan_unique`、`open_order_plan_valid`、`emergency_no_risk_increasing_open_buy`、`closed_position_no_stale_intent`、`account_position_state_valid`、`runtime_control_consistent`、**`open_position_protection_survives_plan_ttl`**。

`checkpoints_cover_required_points = true`（四段时间带 start `0–300 s` / ~30 min `1500–2100` / ~60 min `3300–3900` / ~90 min `5100–5700` 全部命中，且含 `before_restart` 与 `after_restart`）、`all_checkpoints_ok = true`、`checkpoint_coverage_complete = true`。

**零失败、零 retry、零隐藏**：7/7 一次通过，无 `diagnostics`。

### 16.1 断点续接的正确性

`after_restart`（绝对 `3600.3 s`）紧接 `before_restart`（`3540.1 s`）与 `final_before_stop`（`3600.2 s`），说明 restart 后**同一逻辑时间轴连续**、无时间窗丢失：`execution_gap.downtime_seconds = 3608.195931`（= 从 `last_heartbeat 06:12:11.360` 到 `recovery_time 07:12:19.556` 的真实停机跨度）。

---

## 17. Fresh-process Restart（§17）

| 证据 | 值 |
|---|---|
| phase first pid → phase second pid | `29320` → `30332`（**不同 OS 进程**） |
| phase first `active_finished_at` | `2026-09-13T07:12:14.204837+00:00` |
| phase first `process_exited_at` | `2026-09-13T07:12:14.475076+00:00` |
| phase second `process_started_at` | `2026-09-13T07:12:15.605038+00:00` |
| phase second `active_started_at` | `2026-09-13T07:12:19.727581+00:00` |
| `restart_gap_seconds` | `5.523` |
| `prior_active_seconds`（传给 phase second） | `3600.1658749000053` |

phase second 是**全新解释器进程**，不继承任何 Python 对象；唯一状态来源是 PostgreSQL。

`no_python_memory_carried_over = true` 的构成（H-4 加固后，非同义反复）：
1. `fresh_process_restart_performed = true`（两 pid 不同）
2. phase second `warmup.events_discarded = 2`（>0，证明它在**自己进程内**完成了冷启动 warm-up）；`warmup.seconds = 0.572`
3. phase second `recovery` 非空
4. `first_active_finished_at (07:12:14.205) < second_active_started_at (07:12:19.728)`

**Recovery 报告**（`seconds = 0.146`）：

15 步全绿：`STARTING → RECOVERING → LOAD_RUNTIME_CONTROL → LOAD_ACCOUNT → LOAD_OPEN_ORDERS → LOAD_POSITIONS → LOAD_ACTIVE_PLANS → LOAD_SYMBOL_STATES → FIND_ACTIVE_SYMBOLS → FETCH_FRESH_MARKET_DATA → EXECUTION_GAP_RECORDED → RECONCILIATION → REVALIDATE_PLANS_ORDERS → RESTORE_POSITION_PROTECTION → FINAL_STATE:RUNNING`

| 项 | 值 |
|---|---|
| `ok` / `reason` | `true` / `null` |
| `final_system_state` / `operator_state` | `RUNNING` / `NORMAL` |
| `reconciliation.ok` / `diagnostics` | `true` / `[]`（13 条不变量全 true，含 `open_position_protection_survives_plan_ttl`） |
| `active_symbols` | `["BTC-USDT"]` |
| `details.open_orders` / `open_buys` / `positions` / `trades` | `0` / `0` / `1` / `1` |
| `plan_revalidation` | `plan_7d212f0ce53054e676a6e30c` `status ACTIVE`、**`valid: false`**、`issues: ["expired", "state_version_stale"]` |
| `protection` | `triggered false` / `trigger NONE` / `reason HOLD` / 无 fill |
| `execution_gap` | `downtime_seconds 3608.195931`、`affected_instruments ["BTC-USDT"]`、`active_risk.open_positions ["BTC-USDT"]` |

对照 check：`recovery_ok`、`recovery_final_state_running`、`recovery_position_recovered`、`recovery_protection_snapshot_recovered`、`no_fabricated_fill_across_restart` 全 `true`。

**`no_fabricated_fill_across_restart` 的证据**：phase first `counts_at_stop = {1,1,1,1,1,1}`；phase second `recovered_counts` 与之**完全相等**（`1/1/1/1/1/1`）→ restart **没有凭空产生任何 fill / order / ledger entry**。

> **禁止冒充项已遵守**：phase second 是独立 OS 进程（`subprocess.Popen(sys.executable)`），**不是** same-process object reset。

---

## 18. N01-7-F01 三条见证（§19）

TradePlan TTL 实测 = **30 分钟**（`expires_at 06:43:15.106501` = `06:13:15.106` + 30 min）。`expiry_crossed_at = 06:43:15.967562`，`expiry_crossed_elapsed_seconds = 1861.929`。

### 18.1 Witness A — TTL 过期但持仓 OPEN，durable protection snapshot 仍在且可执行（phase first）

观测时刻 `06:44:16.028`（过期后 `f01_elapsed_seconds = 1921.989`，延迟 `POST_EXPIRY_WITNESS_DELAY_SECONDS = 60.0`）。

| 事实 | 值 |
|---|---|
| plan 视图 | `plan_7d212f0ce53054e676a6e30c` `v1` `side BUY`、`expires_at 06:43:15.106501`、**`expired_at_observation: true`** |
| **`load_valid_long_active_plan`** | **`null`** → 过期 plan 已**不再作为 risk-increasing 合法授权** |
| 持仓 | `position_quantity 0.0012928389415086728`（**仍 OPEN**）、`average_cost 77349.15525`、`trade_id trade_67f14f69be1bfd9761ac5273` |
| **durable protection snapshot** | `protection: {plan_7d212f0ce53054e676a6e30c, v1, stop 73444.88, tp 81175.92, updated_at 06:13:15.136164, present: true}` |
| `authority`（protection service 解析结果） | `{plan_7d212f0ce53054e676a6e30c, v1, stop 73444.88, tp 81175.92}` |
| `evaluate` | `{triggered: false, reason: HOLD, trigger: NONE}`（**可执行、且正确判定不需动作**） |
| `open_position_unprotected_incidents` | **`0`** |
| `risk_gate_after_expiry` | `{admitted: false, reason: PLAN_EXPIRED}` |
| `probe`（risk-increasing 探测） | `{status: REJECTED, reason: PLAN_EXPIRED}` |
| plan 记录本身 | `plan_status ACTIVE`、`active_plan_count 1`（**未被删除**，但**已失去 risk-increasing 授权**） |
| `economic_counts` before/after | `1/1/1/1/1/1` **完全相等** |

对应 check（phase 内）：`f01_plan_expired_observed`、`f01_plan_no_longer_risk_increasing_valid`、`f01_position_still_open_after_expiry`、`f01_protection_snapshot_complete_after_expiry`、`f01_snapshot_matches_originating_plan`、`f01_protection_service_uses_snapshot_after_expiry`、`f01_no_position_unprotected_incident`、`f01_runtime_not_safe_mode`（`operator_state NORMAL` / `system_state RUNNING`）、`f01_expired_plan_blocks_risk_increasing`、`f01_no_economic_fact_from_probe` —— **全部 `true`**。

### 18.2 Witness B — 新 ACTIVE TradePlan 不得仅因 ACTIVE 自动替换 protection authority

证据来自 `f01_after_restart`（`08:14:20.142`，phase second）：`authority` 与 `durable_active_plan` **同为** `plan_7d212f0ce53054e676a6e30c v1`，而 `durable_active_plan.expired = true`。

即：即便 plan 记录状态仍为 `ACTIVE` 且仍被 `LOAD_ACTIVE_PLANS` 载入，protection authority **仍然**来自 durable Position snapshot（同 id/version/stop/tp），**没有**被"再次看到 ACTIVE plan"这一事实所替换或重新授权。`risk_gate` 侧同时对同一 plan 判 `PLAN_EXPIRED`（Witness A）—— authority 与 risk-increasing 授权**分离**，符合 F01 契约。

### 18.3 Witness C — Restart 后 authority 来源仍是 durable Position snapshot

| check | 值 | 说明 |
|---|---|---|
| `f01_protection_authority_after_restart` | `true` | 重启后仍可解析出 authority |
| `f01_authority_identity_matches_durable_plan` | `true` | `authority` 与 `durable_active_plan` 的 `plan_id`/`plan_version` 一致 |
| `f01_protection_service_resolves_snapshot_after_restart` | `true` | 解析路径为 durable snapshot |
| `f01_no_unprotected_incident` | `true` | `open_position_unprotected_incidents = 0` |

`f01_after_restart.state` 显示：`protection.present = true`、`stop 73444.88` / `tp 81175.92`（与 phase first 快照**逐字段相同**，`protection_updated_at` 仍为原始的 `06:13:15.136164` —— 说明是**恢复而非重建**）、`position_quantity 0.0012928389415086728`、`plan_expired true`、`evaluate {HOLD}`。

顶层 check（§19 三条）：`f01_plan_ttl_expired_while_position_open`、`f01_durable_snapshot_present_after_ttl`、`f01_snapshot_matches_originating_plan` —— 全 `true`。

**F01 结论**：A / B / C 三条见证**全部成立且互不重叠**（A 在 phase first 证明 TTL≠protection-lifetime；B/C 在 phase second 证明 authority 不随 ACTIVE 状态或进程重启漂移）。

---

## 19. 经济不变量（§25）

| 检查 | 证据 | 结果 |
|---|---|---|
| `final_position_flat` | `position_final.quantity = 0.0` | ✅ |
| `final_no_open_buy` | `open_buys_final = 0` | ✅ |
| `final_exactly_one_exit_fill` | `sell_fills = ["fill_1e84c93b8bfae0091b72ae10"]`（恰好 1） | ✅ |
| `final_single_trade_lifecycle` | `trade_final` `status CLOSED`、`opened_at 06:13:15.136164` → `closed_at 08:14:20.167018`，全程**单一** `trade_id` | ✅ |
| `final_no_duplicate_facts` | `counts_final = {orders 2, fills 2, positions 1, trades 1, accounts 1, ledger_entries 2}`（2 单 : 2 成 : 2 账 ⇒ 无重复事实） | ✅ |
| `final_reserved_cash_zero` | `reserved_cash = 0.0` | ✅ |
| `final_cash_non_negative` | `cash_balance = 9999.385299334668 ≥ 0` | ✅ |
| `final_protection_snapshot_cleared_when_flat` | `position_final.protection_present = false`、`protection_plan_id = null` | ✅ |
| `reconciliation_ok`（final） | `true`、`diagnostics: []`、13/13 不变量 | ✅ |
| `no_fabricated_fill_across_restart` | first `counts_at_stop` == second `recovered_counts` | ✅ |
| 账实相符 | `2 fills × 1 ledger_entry = 2`；`fee 0.1 + 0.09958488421888746` 均已入账；`realized_pnl -0.5147006653314238` | ✅ |

**关键点**：持仓**跨 TTL 过期 + 跨进程重启**存活 2 小时后被**人工平仓**收尾，全程只产生 2 笔 fill，`ledger_entries == fills`。`position_final` 同时证明 **flat 后 protection snapshot 被正确清除**（未残留哑保护）。

---

## 20. 资源生命周期：socket / handle gate（§23）与长驻容器（§22）

### 20.1 §23 socket / handle（双视图，H-3 加固后）

| 指标 | 值 |
|---|---|
| `socket_band_delta_across_reconnects`（首/末次重连之间） | **`-1`** |
| `socket_net_growth_first_phase` | `+2` |
| `socket_net_growth_second_phase` | **`-1`** |
| `socket_series` first/last/max（730 样本） | `4` / `5` / `6` |
| `handle_band_delta_across_reconnects` | **`-1`** |
| `handle_net_growth_first_phase` | **`-9`** |
| `handle_net_growth_second_phase` | **`-11`** |
| `handle_series` first/last/max | `194` / `184` / `197` |
| 容差 | `max_permanent_socket_delta = 2`、`max_permanent_handle_delta = 16` |

`5` 次重连后 socket/handle **未累积**（两个 phase 净增长均 ≤ 0，区间差为负），远在容差内。`sockets_not_accumulating = true`、`handles_not_accumulating = true`。

样本级佐证：窗口 0 的 `handles 185–197`、`sockets [4,6]` 是启动期抖动；自窗口 5 起稳定为 `handles 184` / `sockets 5`，保持至结束。

### 20.2 §22 Long-lived container bound

任务专属容器 `marketpulse-n01-7-ms-pg`（`postgres:16-alpine`，PG `16.15`）：

| 项 | 值 |
|---|---|
| `StartedAt` | `2026-09-13T05:46:27Z`（早于运行窗口 `06:12:05`） |
| `RestartCount` | **`0`** |
| 端口 | `127.0.0.1:5434->5432/tcp`（仅回环） |
| 运行窗口内状态 | 连续 `Up`，**无重启、无替换、无镜像漂移** |
| 运行结束后查询 | `Up 2 hours`（同一容器实例） |

即：2h soak 全程由**同一个长驻容器实例**承载，容器本身不是变量。

---

## 21. 最终关停与残留（§26）

| 项 | phase first | phase second |
|---|---|---|
| `queue_final` | `0` | `0` |
| `inflight_final` | `0` | `0` |
| `workers_final` | `0` | `0` |
| `worker_tasks_final` | `[]` | `[]` |
| `worker_exceptions_final` | `0` | `0` |
| `background_tasks.remaining_pending_tasks` | `[]` | `[]` |
| `cleanup.released` | `true` | `true` |
| `cleanup.elapsed_seconds` / `polls` | `0.055` / `1` | `0.047` / `1` |
| `cleanup.first_client_sessions` / `final_client_sessions` | `0` / `0` | `0` / `0` |
| `cleanup.final_server_sessions` / `final_idle_in_transaction` | `0` / `0` | `0` / `0` |
| `cleanup.foreign_rows` / `transients` | `[]` / `0` | `[]` / `0` |
| `errors` | `[]` | `[]` |

顶层：`shutdown_no_errors = true`、`no_detached_runtime_tasks = true`、`phase_processes_clean = true`（`phase_process_errors = []`）、`disposable_database_residue_zero = true`、`shared_primary_unchanged = true`。

**残留 = 0**：`leftover_databases = 0`；共享主库 revision 前后恒 `20260905_0004`、`protection_columns` 恒 `[]`、N01-7 owned 会话恒 `0`。

### 21.1 实例清理（任务结束后，实测）

运行结束、证据抽取完毕后再执行 teardown，以保留**运行期容器连续性**证据（§22）与**清理动作**证据。

| 步骤 | 实测 |
|---|---|
| 清理前库列表（`pg_database LIKE 'marketpulse%'`） | 仅 `marketpulse`（容器默认库）—— **无 `marketpulse_n01_7_*` 残留** |
| 清理前 N01-7 专属 client 会话 | `0` |
| 清理前容器 inspect | `running \| RestartCount=0 \| StartedAt 2026-09-13T05:46:27.067Z` |
| 容器挂载 | 1 个匿名卷 `839460baf0120aebe49f9e69174351e5fe6b60e1def315fdc1125df482e1ffe4` → `/var/lib/postgresql/data` |
| 清理动作 | `docker rm -f -v marketpulse-n01-7-ms-pg` → `rc=0` |
| 清理后容器 | `[]`（无 `marketpulse-n01-7` 前缀容器） |
| 清理后**卷** | `[]`（**带 `-v` 已移除该匿名卷，无孤儿卷残留**） |
| 未受影响的其他容器 | `marketpulse-se-fix-02-pg`（另一窗口）、`marketpulse-postgres`（共享主库 `5432`）——**均未触碰** |

**归因唯一性**：被删匿名卷经 `docker inspect` 确认**仅**挂载于本任务专属容器，非其他窗口容器共享，故不存在误删风险（对照本机环境坑：「多窗口并行下无法唯一归因的匿名卷勿盲删」）。


---

## 22. 静态门

| 门 | 命令 | 结果 |
|---|---|---|
| Lint | `ruff check scripts/verify_n01_7_medium_soak.py` | `All checks passed!` |
| Format | `ruff format --check scripts/verify_n01_7_medium_soak.py` | `1 file already formatted` |
| Compile | `py -3.14 -m compileall scripts/verify_n01_7_medium_soak.py` | `rc = 0` |
| Production freeze | `git diff --stat 71abb07 HEAD -- backend/src backend/alembic backend/tests frontend` | **空** |
| Production freeze（含未提交） | `git status --porcelain -- backend/src backend/alembic backend/tests frontend` | **空** |
| 判据 | `production_code_unchanged = true`（`code_evidence.production_frozen = true`） | ✅ |

`code_evidence` 实测值：`base_sha 71abb07…`、`head_sha ece1f7cb…`、`branch n01-7-medium-runtime-soak`、`production_diff_stat ""`、`production_status_porcelain ""`。

---

## 23. 验收标准映射（§27 AC-01~AC-13）

> **说明（不做臆测）**：任务书 §27 的 AC 编号逐条原文属**外部输入**，不在本仓库可读范围内，因此**本文不重述其条文字面**。下表按任务书**各节的明确量化要求**给出本批次的可取证结论与证据锚点；AC 编号与本文事实的逐条对齐，由 Independent Review 依任务书原文确认。

| 任务书要求 | 量化门 | 实测 | 证据锚点 | 结论 |
|---|---|---|---|---|
| §12 Acceptance Duration | `active ≥ 7200 s` | `7320.580 s` | §6；`active_total_ge_7200` | ✅ |
| §14 Controlled Reconnect | `≥ 5` 次，各含 fresh 见证 | `5` 次，全部 `disconnect_observed` + `strictly_newer` | §14；`reconnects_ge_5`、`controlled_reconnects_recovered_fresh` | ✅ |
| §15 Stale → Fresh | `≥ 2` 次，各含 fail-closed + 恢复 | `2` 次，`age 60.466/60.049 s`、`UNAVAILABLE`、`RUNTIME_STATE_DATA_DEGRADED`、`fresh_recovered` | §15；6 项 `stale_cycles_*` 全 true | ✅ |
| §16 Reconciliation Checkpoints | `≥ 7`，全部 `ok` | `7`，7/7 `ok=true`、13/13 不变量 | §16；`all_checkpoints_ok`、`checkpoints_cover_required_points` | ✅ |
| §17 Fresh-process Restart | 1 次，无 Python 记忆 | pid `29320 → 30332`，`warmup 2 discarded`，`recovery 0.146 s` | §17；`fresh_process_restart_performed`、`no_python_memory_carried_over` | ✅ |
| §18 Paper Position Witness | 1 笔 SPOT LONG 全链路 | ENTRY→LONG-RUN→RECONNECT→STALE→FRESH→RESTART→CLOSE | §13；`entry_*`、`final_*` 系列 | ✅ |
| §19 F01 Witness A/B/C | 三条互不重叠 | A（phase first）+ B/C（phase second） | §18；`f01_*` 7 项顶层 + 10 项 phase 内 | ✅ |
| §20 Queue / Backpressure | `q ≤ maxsize`、worker 有界、final 归零 | `q_max 0/2048`、`workers 4`、final `0/0/0` | §9；`queue_within_capacity`、`final_queue_empty`、`final_inflight_empty` | ✅ |
| §21 Memory | AND 判据（`>64 MiB` **AND** `>5 MiB/h`） | `8.055 MiB` / `5.255 MiB/h` → `finding false` | §11；`memory_within_approved_condition`、`memory_series_present` | ⚠️ **满足已批准判据，但斜率支越线，见 §11** |
| §22 Long-lived Container | 有界、不漂移 | `RestartCount 0`、连续 `Up` | §20.2 | ✅ |
| §23 Socket / Handle Gate | 重连后不累积 | `band_delta -1`、净增长 `≤ 0` | §20.1；`sockets_not_accumulating`、`handles_not_accumulating` | ✅ |
| §24 PostgreSQL Gate | 归属分离、无 foreign、无残留 | `pg_other_max 0`、`foreign_rows []`、`leftover 0` | §12；4 项 `pg_*` 全 true | ✅ |
| §25 Economic Invariants | 单一交易生命周期、flat 后清快照 | `2 fills / 1 trade / ledger 2`、`protection cleared` | §19；`final_*` 9 项全 true | ✅ |
| §26 Final Shutdown | 队列/inflight/task 归零、无错 | 两 phase 全 `0`／`[]`／`[]` | §21；`shutdown_no_errors`、`phase_processes_clean` | ✅ |
| §29 Change Boundary | 只改允许文件 | 仅新增 harness + 本 devlog | §22；`production_code_unchanged` | ✅ |

**顶层 68/68 checks 全 `true`**；上表逐节核对**未发现任何一项不满足已批准量化门**。

---

## 24. Failure Classification 与开放问题（§28 / §21 边界）

### 24.1 分类

| 类别 | 本次判定 | 依据 |
|---|---|---|
| **CASE A — PRODUCT DEFECT** | **无** | 68/68 checks 全绿；`failures = []`；未出现任何 production 行为异常 |
| **CASE B — HARNESS DEFECT** | **有，共 11 项（H-1~H-11），全部在正式 Run 之前修复** | §5.1。修复仅落于 `scripts/verify_n01_7_medium_soak.py`，**零 production 改动**；因修复早于正式 Run，2h Clock 完全来自单次连续运行，**不涉拼接** |
| **CASE C — ENVIRONMENT INVALIDATED** | **无** | OKX WS 直连正常、REST 经本机既有代理正常、一次性 PG 正常、隔离实测干净；未修改任何系统级配置 |

### 24.2 必须交给 Independent Review 的开放问题（不作 PASS 结论）

1. **§21 内存斜率支越线**（最高优先级）：`second_half_trend = 5.255 MiB/h > 5.0`，仅因 AND 判据另一支（`8.055 ≪ 64 MiB`）未成立而判 `finding = false`。四个独立视角（§11）均显示持续正斜率，方向与 `N01-7-INV-01` 的 `C｜ALLOCATOR_OR_NATIVE_RETENTION_LIKELY` 一致。**本批次按已批准判据不构成 Finding，但"2h 长跑是否存在缓慢保留"这一问题仍未闭合。**
2. **`trade_dedupe` 在窗口 6 起饱和至 `8192`**：表现为有界而非越界，符合 FIFO 容量语义；但饱和状态持续约 45 分钟，Review 需确认这与 `N01-7-INV-01` 的周转语义修正一致、且不影响去重正确性（本次 `duplicate_intent` 幂等、`reconciliation_ok` 全程成立可作为辅证）。
3. **STALE 因果的单点承载**：cycle 2 因 `PLAN_EXPIRED` 前置，其 fail-closed 证据不能独立成立，因果由 cycle 1 单独承载（§15 已详述）。若 Review 要求"两次独立因果"，则当前设计只提供 1 次 —— **属可观测性局限，非产品异常**。
4. **文档滞后**：`PROJECT_STATE.md:22` / `AI_CONTEXT.md:111` 对 `N01-7` 的描述与仓库中既有两条分支（`6b882c9` / `0a34c72`）冲突。本次仅作最小同步，**未改写历史描述**。

### 24.3 三条候选分支的关系（供 Review 决策）

| 分支 | tip | 状态 | 关系 |
|---|---|---|---|
| `n01-7-2h-runtime-soak-after-f01` | `6b882c9` | 未 merge | 首次 2h soak（`active 7200.369 s`），结论 `BLOCKED / FIX REQUIRED` |
| `n01-7-inv-01-memory-attribution` | `0a34c72` | 未 merge | 修 F-2 + 内存归因分类 `C` |
| **`n01-7-medium-runtime-soak`（本次）** | `ece1f7cb` | 未 merge | 补齐 §14/§15/§16/§17 能力 + F01 A/B/C 见证；base = `71abb07`（**不含**前两条） |

> ⚠️ 本次分支 **不含** 前两条分支的提交（base 直接取 accepted main `71abb07`）。三者如何收敛属 Review / 人工决策事项，**Worker 不自行 merge**。

---

## 25. Result / Remaining / Evidence

### 25.1 Result

**`VALIDATED / READY FOR INDEPENDENT REVIEW`**

- 正式 2h Acceptance Run：`result PASS`，**68/68 checks 全 `true`**，`failures / harness_errors / shutdown_errors / phase_failures / phase_process_errors` 全为 `[]`。
- `total_active_seconds = 7320.580 ≥ 7200`，**单次连续运行**（无拼接）。
- 隔离干净：一次性库残留 `0`、共享主库前后完全未变、容器 `RestartCount 0`。
- **Production Code Frozen 成立**：对 `backend/src` / `backend/alembic` / `backend/tests` / `frontend` 的 diff 为空（含未提交状态）。
- ⚠️ **适用范围限定**：以上结论针对 **Task Base `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`**。运行结束后实测远端 `main` 已推进至 `fc619242c99a794a2eb2b87ee02b8b72aa782f05`（含 `g2/runtime.py`、`g2/repository.py`、`db/models.py` 与 migration `0007/0008` 变更）→ 见 **§26 Baseline Delta**。本批次**不主张**结论可平移至当前 `main`。

### 25.2 Remaining / Blockers

| 项 | 状态 |
|---|---|
| 🔴 **BASELINE DELTA（§1，最高优先级）** | 远端 `main` 已由 `71abb07` 推进至 **`fc619242`**，命中 §1 触发区（**G2** + **DB schema** + migration head `20260912_0006 → 20260913_0008`）。本批次结论**仅覆盖 Task Base `71abb07`**；能否平移至当前 `main` 须由 Review 判定。详见 **§26** |
| **§21 内存斜率支越线（5.255 MiB/h）** | **未闭合**，已如实记录（§11 / §24.2）。按已批准 AND 判据不构成 Finding，需 Independent Review 判断是否需要后续 INV/FIX 批次 |
| `trade_dedupe` 长时饱和 | 有界，但饱和窗口 ~45 min，需 Review 确认语义 |
| STALE 独立因果次数 = 1 | 可观测性局限，非产品异常 |
| 三条 N01-7 分支收敛 | 需 Review / 人工决策，Worker 不自行 merge |
| **N01-7 状态** | **不得由本 Worker 宣布 ACCEPTED**（§7 / §32） |

**未发现 CASE A（Product Defect）**，因此本批次**不是** `BLOCKED / FINDING CONFIRMED`。

### 25.3 Evidence

| 文件 | 内容 |
|---|---|
| `E:/Temp/n01-7-medium/acceptance_raw.json` | 正式 Run 完整 JSON（含 730 samples / 68 checks / run_identity / code_evidence） |
| `E:/Temp/n01-7-medium/acceptance_stdout.txt` | 正式 Run 进程 stdout |
| `E:/Temp/n01-7-medium/acceptance_analysis.txt` | 全证据表抽取（37 923 B） |
| `E:/Temp/n01-7-medium/analysis2.txt` / `analysis3.txt` / `analysis4.txt` | 本次辅助抽取（分桶 / phase second / 重连·checkpoint·code_evidence） |
| `E:/Temp/n01-7-medium/n01-7-medium-logs/phase_first_raw.json` | phase first 完整报告 |
| `E:/Temp/n01-7-medium/n01-7-medium-logs/phase_second_raw.json` | phase second 完整报告 |
| `E:/Temp/n01-7-medium/n01-7-medium-logs/{phase_first,phase_second}.progress.jsonl` | 增量时间序列（每 phase 启动前清空，无跨 run 混样） |
| `E:/Temp/n01-7-medium/external_monitor.jsonl` | 进程外独立 RSS/private/USS 监视（348 行，**无 tracemalloc**） |
| `E:/Temp/n01-7-medium/probe{3,4,5,6}_raw.json` | PROBE 记录（§5） |
| `E:/Temp/n01-7-medium/patch{5,6,7}.py` | 确定性补丁脚本（H-1/H-10/H-11 相关） |
| `E:/Temp/n01-7-medium/pgcheck.py` / `freeze_facts.json` / `preflight.json` / `harness_sha.txt` | 隔离核验与冻结事实 |

**仓库内交付物**：`scripts/verify_n01_7_medium_soak.py`（blob `febcfd70c1bfe1b20a6cbd456eb734dca9162419`）、`dev_log/2026-09-13-n01-7-medium-runtime-soak.md`（本文件）。

## 26. Baseline Delta（§1）— **必须由 Review 处理**

### 26.1 事实

本批次 **Preflight 时**（§2 实测）：`main` / `origin/main` / `ls-remote` 三者一致 = `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` → 当时**无 baseline drift**，运行全程基于该 base。

**运行结束后**（推送本分支前复验 `git ls-remote origin refs/heads/main`）：远端 `main` 已推进至 **`fc619242c99a794a2eb2b87ee02b8b72aa782f05`**。

即：**main 的推进发生在本批次 2h 运行窗口（`06:12:05Z → 08:14:21Z`）期间/之后，不在运行之前，也不由本批次造成。**

### 26.2 `71abb07..fc619242` 的实际内容

6 个 commit（含 1 个 merge `513689a`）：

```
fc61924 docs(edge): accept stable evidence anchor
1e2738b fix(edge): close re-review blockers for the stable evidence anchor
5ba78af docs(edge): bound the integration isolation evidence
513689a merge(edge): integrate stable anchor review fix onto latest main   ← merge commit
bdb1af2 fix(edge): close stable anchor review findings
5105375 fix(edge): add stable evidence capture anchor
```

`git diff --stat 71abb07 fc619242`：17 文件、`+4100 / -104`。

| 区域 | 差异 | **是否属 §1 的 STOP 触发区** |
|---|---|---|
| `backend/src/marketpulse/g2/repository.py` | `+376` | 🔴 **是（G2）** |
| `backend/src/marketpulse/g2/runtime.py` | `+90` | 🔴 **是（G2）** |
| `backend/src/marketpulse/db/models.py` | `+83` | 🔴 **是（DB schema 相关）** |
| `backend/alembic/versions/20260913_0007_capture_anchor.py` | 新增 `+59` | 🔴 **是（DB schema / migration）** |
| `backend/alembic/versions/20260913_0008_capture_anchor_review_fix.py` | 新增 `+132` | 🔴 **是（DB schema / migration）** |
| `backend/src/marketpulse/edge/{capture,hashing,repository}.py` | `+594/+40/+214` | 属 SE 区域；本项目结论不覆盖 |
| `backend/src/marketpulse/g5/replay.py` | `+11` | 涉及 `schema_head` 常量 |
| `backend/tests/test_se_02{a,b}_*.py` | `+252/+48/+993` | 测试侧 |
| `frontend/**` | 无差异 | — |
| `AI_CONTEXT.md` / `PROJECT_STATE.md` / `DECISIONS.md` | 文档 | — |

**Migration head 变化**：`20260912_0006` → **`20260913_0008`**（`20260913_0007_capture_anchor` → `20260913_0008_capture_anchor_review_fix`）。

### 26.3 对本批次结论的影响（如实界定）

| 项 | 判定 |
|---|---|
| 本批次 2h 运行证据是否自洽 | ✅ **是**。运行期间 `HEAD = ece1f7cb`（parent `9ee13a7` → `71abb07`）、migration head 实测 `20260912_0006`、production tree = `71abb07`。所有 68 项 check 是对**那个 tree**的真实测量 |
| 结论是否覆盖当前 `main`（`fc619242`） | ❌ **不覆盖**。`g2/runtime.py` 与 `g2/repository.py` 正位于本批次实测的 G2 事件运行时路径上；`db/models.py` 与 migration `0007/0008` 改变了 schema head |
| 是否属 `CASE A PRODUCT DEFECT` | ❌ 否。无任何产品缺陷证据 |
| 是否属 `CASE C ENVIRONMENT INVALIDATED` | ❌ 否。运行环境有效、证据有效 |
| 性质 | **BASELINE DELTA（基线漂移）**，依 §1 属 `STOP / REPORT BASELINE DELTA` |
| 是否由本 Worker 擅自处理 | ❌ **否**。未 rebase、未 reset、未把结论改写、未改 production |

**因此**：本批次给出 `VALIDATED / READY FOR INDEPENDENT REVIEW`，其**适用范围明确限定为 Task Base `71abb07`**。是否可将结论平移至当前 `main fc619242`，须由 Independent Review 判断（重点：`g2/runtime.py`、`g2/repository.py`、`db/models.py`、migration `0007/0008` 是否影响本批次验证的 `ScannerPipeline → EventRuntime → G3/G4 → Recovery/Reconciliation` 链路）。

### 26.4 连带影响（供 Review 参考，非本批次 Scope）

1. `scripts/verify_n01_7_f01_r1_migration_gate.py` 仍钉死 head `20260912_0006`（`RRF-03` 已登记为 DEFER）→ 在当前 `main`（head `20260913_0008`）上运行该 accepted 门脚本会 `AssertionError`。**本次未修改该脚本**（它是 accepted 证据）。
2. 本分支上的 `PROJECT_STATE.md` / `AI_CONTEXT.md` 是基于 `71abb07` 版本的最小编辑；`main` 上这两个文件已被 `71abb07..fc619242` 改动（`102` / `58` 行）→ **若未来合并本分支，这两个文件会冲突**，属预期，收敛方式由 Review / 人工决策。
3. 本批次**未**对 `fc619242` 做任何验证，**未**运行任何 pytest，**未**对新 migration 做 upgrade/downgrade。

---

### 25.4 STOP

依 §32：**执行到此停止**。不自行 Human Acceptance、不 merge `main`、不启动 N01-8、不宣布 N01 ACCEPTED、不开发 Integrated Runtime Host、不修改任何 production defect。
