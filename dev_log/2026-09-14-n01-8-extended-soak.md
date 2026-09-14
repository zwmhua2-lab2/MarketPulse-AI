# N01-8｜12-hour Extended Runtime Soak

- Date: 2026-09-14
- Task: **N01-8｜12-hour Extended Runtime Soak**（Validation / Soak / Evidence Task）
- 本文件当前状态：**Phase A–E 已执行完成**；
  **Phase E 正式 ≥12h Run = `PASS`（99/99 checks True，total active 44401.217 s，4 相位 / 3 fresh-process restart / 12 reconnect / 6 STALE→FRESH / 24 checkpoint）**；
  **Memory 冻结 AND 门：`finding = false`，但 total-growth 支越线 77.711 > 64，已归因于 trim-peak 口径 × 3 次进程重启，watch item 未关闭**；
  🚩 **Baseline drift = YES（`dd78a979 → b77c8033`，命中 `g2/**`）⇒ 结论仅覆盖 Task Base，交 Independent Review 裁定**；
  Phase F/G 收尾中。
- Window Status: **`PHASE E PASS / BASELINE DRIFT CLASSIFIED / MEMORY P2 OPEN`**
- 允许结果（本窗口自评）：**`VALIDATED / READY FOR INDEPENDENT REVIEW`**（附 §43 baseline-drift 边界；**非** ACCEPTED / **非** Human Accepted）
- Branch: `n01-8-12h-extended-soak`
- Worktree: `E:\Documents\MarketPulse-AI-n01-8`（本窗口唯一作业 worktree；
  根 worktree `E:\Documents\MarketPulse AI` 全程未触碰 —— 其已知 dirty，停在
  `prb-01-product-requirements-baseline`）

---

## 1. Task

在已 Human Accepted 的 N01-7 / N01-7-R01 基础上，验证当前 Accepted Runtime 组件在
**真实 OKX Public Market Data + Paper + PostgreSQL** 下能否连续稳定运行 **>= 12 小时**，
并重点关闭 / 进一步分类 N01-7 遗留的 **Memory P2 Watch Item**
（`N01-7-R01-RR-P2-01`）。

这不是「能不能跑 12 小时不崩」的问句，而是要回答 §3 的六个问题：

1. Runtime resources 是否长期有界；
2. reconnect / stale / recovery 多轮后是否累积；
3. PostgreSQL connection / transaction lifecycle 是否长期稳定；
4. durable economic facts 是否始终自洽；
5. restart / reconciliation 是否长期可靠；
6. **Memory 是否在 bounded retention 饱和后趋于平台**。

## 2. Requirement

- 单一轮全新 Acceptance Run，**active runtime >= 43200 s（12h）**；不得 2h + 10h 拼接。
- 允许**任务书批准的 fresh-process restart**，但 supervisor 必须维持**同一正式 Acceptance timeline**。
- 真实 OKX 公共行情：至少 `BTC-USDT` SPOT + `ETH-USDT` SPOT；**禁止** private API / API key / Live funds。
- Mode = `LIVE_PAPER`。
- 继承 Memory 冻结契约（**不得修改 threshold**）：
  `RSS growth > 64 MiB` **AND** `second-half slope > 5 MiB/h` 同时成立才算 Finding。
- 必须**新增**长期 retention saturation 分析（见 §18）。
- Production Code 默认冻结；发现 product defect ⇒ `STOP / REPORT`，不得顺手修。

## 3. Scope

1. 复用已 Accepted 的 N01-6 / N01-7 / N01-7-R01 harness 基础设施；
2. 只做 **validation-only 最小适配**（新 harness 文件 + 12h schedule + retention 分析 + 环境身份）；
3. 运行 12h 正式 Acceptance Run，采集时间序列遥测与 checkpoint 证据；
4. 建立 N01-8 dev_log / evidence package；
5. 给出 `VALIDATED / READY FOR INDEPENDENT REVIEW` 或
   `BLOCKED / FINDING CONFIRMED` 或 `INVALIDATED BY ENVIRONMENT`。

## 4. Out of Scope（一行不改 / 一物不建）

- `backend/src/**`、`backend/alembic/**`、`backend/tests/**`、`frontend/**`（Production Code Frozen）；
- Runtime Host implementation、新功能开发、架构重构、Real AI、Live Trading；
- `SE-02C` / `SE-02D` / `G6` / `Integrated Runtime Host`；
- `PRODUCT_REQUIREMENTS.md` / `DECISIONS.md` / `pyproject.toml` / `docker-compose.yml`；
- 其它窗口的容器 / worktree / DB（**不得**删除或清理）；
- N01-7 既有 evidence（`E:/Temp/n01-7-r01/`、`E:/Temp/n01-7-medium/`，只读保留）。

---

## 5. Repository Truth（CIP-01/02/03，本窗口实测）

| 项 | 实测值 | 结论 |
|---|---|---|
| `git ls-remote origin refs/heads/main` | `dd78a979d128dee385c7a8ddc2254a53366af714` | 远端真值 |
| `git rev-parse main` | `dd78a979d128dee385c7a8ddc2254a53366af714` | 与远端一致 ✅ |
| `git rev-parse origin/main` | `dd78a979d128dee385c7a8ddc2254a53366af714` | 与远端一致 ✅ |
| 导航 Accepted Main（窗口提示词） | `dd78a979d128dee385c7a8ddc2254a53366af714` | **与实测一致**（无 SHA drift）✅ |
| 根 worktree `E:\Documents\MarketPulse AI` | branch `prb-01-product-requirements-baseline` @ `d47313a1…`，**dirty**（production 文件 `M` + dev_log `D` + `?? .workbuddy/`） | **不触碰**（他人窗口状态）⚠️ |
| N01-7-R01 closeout worktree `E:\Documents\MarketPulse-AI-n01-7-r01` | `dd78a97`，clean | 只读、未修改 ✅ |
| Migration head（N01-8 worktree 实测） | **`20260913_0009`（单 head）** | ✅ |
| Migration lineage（实测） | `0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 → 0009`（linear，9） | ✅ |
| `N01-7-R01-RR-P2-01` | `OPEN / P2 / NON-BLOCKING`（留给 N01-8） | 必须继承 ✅ |
| `N01 overall` | `NOT ACCEPTED` | 不得由 N01-8 推导 |
| `Integrated Runtime Host` | `NOT STARTED` | 不在本窗口 claim 边界 |

**Accepted Main = `dd78a979d128dee385c7a8ddc2254a53366af714`（= origin/main = 导航 SHA）。**

## 6. Task Base（Phase 2 起冻结）

| 项 | 值 |
|---|---|
| **Accepted Main / Task Base SHA（Phase 2 冻结）** | `dd78a979d128dee385c7a8ddc2254a53366af714` |
| Branch | `n01-8-12h-extended-soak` |
| Worktree | `E:\Documents\MarketPulse-AI-n01-8` |
| Worktree HEAD / 洁净度（实测） | `dd78a97` / `git status --porcelain` 为空 ✅ |
| Migration Head | `20260913_0009`（单 head） |

> Phase 2 启动前与结束后各做一次 `git ls-remote origin refs/heads/main`；drift 只记录、不自动重跑（§21）。

## 7. Harness Reuse（§2「必须先判断当前 N01-7 harness 是否已足够」）

### 7.1 实测的 harness 资产

| 文件 | 行数 | 角色 |
|---|---|---|
| `scripts/verify_n01_6_runtime_smoke.py` | 1309 | **接受基线**：单进程 runtime smoke；提供 `SmokeHarness` / `OKXLiveProvider` / `EventRuntime` / `ScannerPipeline` / `PostgresG2Repository` / `_disposable_postgres_database` / `_ownership_activity` / `_consume` / `_controlled_entry` / `_controlled_close` / `_okx_metadata`（**import，不复制、不修改**） |
| `scripts/verify_n01_7_runtime_soak.py` | 1915 | **观察 helper**：`_db_state` / `_f01_witness` / `_dedupe_analysis` / `_memory_analysis` / `_shared_primary_snapshot` / `_slope_per_hour` / `_proc_resources` 依赖 |
| `scripts/verify_n01_7_medium_soak.py` | 2547 | **正式 2h Acceptance 主 harness**：supervisor + 多 phase 子进程 + `_ControlledStream` + `_controlled_reconnect` + `_stale_fresh_cycle` + `_schedule` + `_checkpoint` + Witness A/B/C + `_memory_condition` + `_aggregate` + `_emit` |

### 7.2 判断结论

**当前 N01-7 harness「不足以」直接支持 12h，但其 runtime substrate 与 supervisor 机制「足够且应复用」。**

可直接复用（**零改动**）的部分：

- 全部 runtime 组件构造与生产路径（经由 `verify_n01_6_runtime_smoke` 的 import 契约）；
- `_ControlledStream`（reconnect = 真正关闭 async generator ⇒ 退出 `websockets.connect` ⇒ 真实重连；
  stall = 扣留**投递**，不是伪造数据）；
- `_controlled_reconnect` / `_stale_fresh_cycle` / `_checkpoint` 的**判据**（age > 生产 freshness TTL、
  fail-closed、protection facts 保全、no fabricated fill、recovery、reconciliation ok）；
- `_run_child` / `_child_command`（fresh OS 进程 + stdout 落盘 + timeout 收割）；
- `_proc_resources()`（psutil handles / inet sockets / asyncio tasks）；
- `_memory_condition()` 的**冻结 AND 契约**（`64.0 MiB` / `5.0 MiB/h`，**不改**）。

**必须做的 validation-only 适配（缺口表）**：

| # | 缺口 | 现状（N01-7） | N01-8 需要 | 类别 |
|---|---|---|---|---|
| G1 | 时长 | `ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS = 7200.0` | `43200.0` | validation-only |
| G2 | Supervisor phase 数 | **硬编码 2 个** phase（`first`/`second`，`_supervisor` 内两次 `_run_child`） | **N 个** phase，列表驱动（≥3 次 fresh-process restart） | validation-only |
| G3 | Schedule 时间轴 | 每 phase 硬编码 4～6 项（`_schedule`） | 12h 全局 schedule 表（12 reconnect / 6 stale / 3 restart / 每小时 checkpoint） | validation-only |
| G4 | Checkpoint 覆盖 | 7 个（start / abs_30m / abs_90m / before_restart / after_restart / …） | 全 timeline 覆盖：每小时 + 每次 restart 前后 + 每次 reconnect 后 + 每次 stale 恢复后 | validation-only |
| G5 | **Retention saturation 分析** | **无**（只有 window means + overall slope + dedupe 饱和计数） | §18 全套（见下） | **新增（核心）** |
| G6 | Rolling slope | 无 | 滚动窗（30 min 窗均 + trailing K 窗斜率）时间序列 | 新增 |
| G7 | GC / allocation（非侵入式） | 无 | `gc.get_count()` / `gc.get_stats()`（cheap，无 tracemalloc） | 新增 |
| G8 | 资源趋势（tasks/sockets/handles/DB sessions）与 reconnect/stale 次数的关系 | 只有 first/last/max + band delta | 时间序列 + 与事件计数的联合趋势 | 新增 |
| G9 | 环境身份 | `TASK_BASE_SHA=8a29306…`、`DEFAULT_RAW_OUT=E:/Temp/n01-7-r01/…`、`n01-7-r01-logs`、5434、`n01-7-r01` app 域 | N01-8 域名/端口/路径/Task Base | validation-only |
| G10 | 资源 band 门 | `MAX_PERMANENT_SOCKET_DELTA=2` / `HANDLE_DELTA=16`（按 2h/5 reconnect 校准） | **保持冻结**；若 12h/12 reconnect 触发，按 §15 分类处理（见 §26-R3） | 决策项 |

> **复用铁律（沿用 N01-7 / N01-7-R01）**：`verify_n01_6_runtime_smoke.py` **import，不复制、不修改**；
> 新 harness 只做「加一层」，不重写 ~1300 行 runtime 构造。

### 7.3 计划产物（Phase 2 创建）

- `scripts/verify_n01_8_extended_soak.py`（新，validation-only；以 `verify_n01_7_medium_soak.py`
  为模板逐项适配 G1–G10，import 既有 harness）
- 不改动任何既有 harness 文件（N01-7 / N01-7-R01 的 accepted 证据不得被改写）。

## 8. Environment（实测）

| 项 | 实测值 |
|---|---|
| 解释器 | `py -3.14` = Python **3.14.2**（psutil **7.2.2** / SQLAlchemy **2.0.52** / websockets **15.0.1**） |
| 现行接受基线解释器约定 | `py -3.14`（`.venv/Scripts/python.exe` 有 fork 伪影；linked worktree 无 venv） |
| OKX WS | 直连（清空 proxy env）；`ws.okx.com:8443` |
| OKX REST metadata | 沙箱内需经本机用户代理 `http://127.0.0.1:10808`（**仅**该一次调用；WS 直连；不写系统代理） |
| Docker 镜像 | `postgres:16-alpine` 已在本地 ✅ |
| 磁盘 | `E:` 剩余 **29.8 GiB**（12h progress JSONL + 日志预计 << 1 GiB；非阻塞） |

## 9. Database Isolation（选择结果）

| 项 | 选择 | 依据 |
|---|---|---|
| 容器 | **`marketpulse-n01-8-pg`**（`postgres:16-alpine`） | §13：独立 instance |
| 端口 | **`127.0.0.1:5440`** | 实测 5432/5434/5437/5438/**5439** 均 IN USE；5440 free ✅ |
| 显式 `DATABASE_URL` | `postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5440/marketpulse`（写入 worktree 内 gitignored `.env`） | §13 |
| disposable database prefix | **`marketpulse_n01_8_`** | 与 N01-6 / N01-7 / SE 域不重合 |
| owned `application_name` | **`marketpulse-n01-8-runtime`** | 唯一归属 |
| observer `application_name` | **`marketpulse-n01-8-observer`**（连 primary 库，不计入 owned） | separate observer |
| shared primary 观测 | `127.0.0.1:5432/marketpulse`，**只读** before/after 指纹（revision + protection columns + owned sessions） | runtime 全程不连 shared primary |

**不使用**：N01-7-R01 的 5434、SE-02C 的 5438、SE-02C Review 的 **5439**、SE-FIX-02 的 5437、
shared primary 5432（除只读指纹）。

## 10. Formal Timeline（计划；Phase 2 冻结）

| 项 | 计划值 |
|---|---|
| Phases | **4 个 fresh-process phase**（⇒ 3 次 fresh-process restart） |
| 每 phase requested active | `11100.0 s`（3h05m） |
| **`total_active` 目标** | `44400.0 s ≈ 12h20m` ≥ `43200`（留经验边界余量，非「刚好压线」） |
| Estimated wall clock | `≈ 44400 s + 3 × restart_gap + 各 phase 启停开销 ≈ 12.5 h` |
| Sample interval | `10.0 s`（沿用；预计 ~4440 点） |
| 模式 | `--mode acceptance`（单轮全新，不拼接） |
| raw-out | `E:/Temp/n01-8/acceptance_raw.json`（外部，不入 Git） |
| logs | `E:/Temp/n01-8/n01-8-logs/`（每 phase stdout + raw + progress JSONL） |
| 前置 Probe | `--probe`（短窗，覆盖 1 reconnect + 1 stale + 1 restart）；Probe 不满足的 acceptance 项
 按 `PROBE_SCOPE_KEYS` 排除，**不**计入正式判定 |

## 11. Market Data（计划）

- OKX Public：`BTC-USDT` SPOT + `ETH-USDT` SPOT；channels 沿用接受基线的 `trades` + `bbo-tbt`；
- `api_key_used = False`、`private_endpoint_used = False`；
- Run Mode = `LIVE_PAPER`；
- 沿用 `production_ttl_seconds = 5.0`（freshness TTL）作为 stale 判据尺度。

## 12. Reconnects（§7，计划）

- 目标 **12 次真实 transport reconnect**（约每小时 1 次，**分散**到整个 12h timeline；
  避开 stale 窗、checkpoint 与 phase 边界 ±60 s）；
- 每条必须证明：`disconnect_observed`（generator reopen）→ **新连接** →
  `fresh_event_after_reconnect`（新 BBO 收报时间 **严格晚于**断连请求时刻）→ settle →
  `reconciliation_ok = true`；
- 并记录 `socket_delta_vs_before` / `handle_delta_vs_before`，
  用于回答「socket/task/handle/session 是否随 reconnect 次数累积」。

## 13. Stale → FRESH（§8，计划）

- 目标 **6 次**受控 STALE / unavailable 循环（每 2h 一次）；
- 每次：`FRESH → withhold delivery（hold 60 s；投递**停顿前最后一条已投递**报价，
  使其 age > 生产 TTL）→ STALE → fail closed → FRESH recovery`；
- 每次必须证明：`age > 5.0 s` 生产 freshness TTL、risk-increasing **blocked**、
  protection facts **remain available**、**no fabricated Fill**、recovery 可用、reconciliation PASS。

## 14. Fresh-process Restart（§9，计划）

- **3 次**计划内 fresh-process restart（4 phase 之间）；
- 每次必须：**新 OS PID**（记录 `pid` 变化）、`restart_gap_seconds`、
  `no_python_memory_carried_over = true`；
- 经 PostgreSQL durable state 恢复：**Account / Position / Protection authority / Runtime state**；
- 复用已接受的 `RecoveryManager` 15 步恢复链，断言 `recovery_ok` / `final_state_running` /
  `position_recovered` / `protection_snapshot_recovered` / `no_fabricated_fill_across_restart`。

## 15. Reconciliation（§11，计划）

不只 start / final。计划覆盖：

| 类别 | 次数 |
|---|---|
| run start | 1 |
| 每小时定点 `abs_1h … abs_12h` | 12 |
| 每次 restart 前 / 后 | 3 × 2 |
| 每次 reconnect 后 | 12 |
| 每次 stale recovery 后 | 6 |
| final（stop 前） | 1 |

每次断言 `ok = true` 且全部 required invariants PASS（含
`open_position_protection_survives_plan_ttl`）；detector-only，**绝不**修复。

## 16. Resource Telemetry（§12，计划）

必须**保留时间序列**（不是只有 start/final）。逐样本采集：

`RSS`、`worker count`、`asyncio tasks`（总数 + owned）、`queue size / high-water`、`inflight`、
`dedupe size / capacity / FIFO head`、`trade_dedupe size / capacity / FIFO head`、
**`sockets`（inet）**、**`handles`**、**DB owned sessions**、**DB observer sessions**、
`idle-in-transaction`、`worker exceptions`、OKX event counts（per symbol trades/bbos + total）、
`event freshness / age`、`data_quality`、`health_status`、`system_state / operator_state`、
`open incidents`。

> 与 N01-7 相比，N01-8 **新增**：GC 统计、rolling slope、事件计数与资源计数的联合趋势。

## 17. Memory（§4；冻结契约，**不改 threshold**）

| 项 | 值 |
|---|---|
| 冻结门 | `MEMORY_TOTAL_GROWTH_MIB = 64.0` **AND** `MEMORY_SECOND_HALF_TREND_MIB_PER_HOUR = 5.0` |
| 口径定义（沿用接受实现） | warm-up trim（丢前 10% 样本）后的 `peak − baseline`；second-half = trim 后后半段的
  least-squares 斜率（per hour） |
| 继承 watch item | `N01-7-R01-RR-P2-01`（slope `≈16.02 MiB/h` > `5.0`，`growth ≈14.043 MiB ≤ 64` ⇒
  上一 Run `finding = false`） |
| 本窗口纪律 | **禁止**写 `memory resolved` / `memory is fine` / `no memory concern`；
  必须给出 §18 的饱和分析结论 |

## 18. Retention Saturation Analysis（**N01-8 新增，核心**）

对两个有界 retention 结构分别做「size vs time」，并回答 §4 的定性问题：

| 结构 | 语义 | 预期 |
|---|---|---|
| `EventRuntime._dedupe` | published event ids，capacity **8192** | 按接受契约**可能不饱和** ⇒ 只做有界性断言 |
| `ScannerPipeline._trade_dedupe` | `(exchange, instrument_id, market_type, trade_id)`，capacity **8192** | 长 trade stream 下**必然饱和**（按接受工作负载推算约 25 min 内） |

计划产出字段（全部来自 harness 时间序列，**不推测**）：

1. `dedupe_size_vs_time`、`trade_dedupe_size_vs_time`（序列 + 窗均 + 每窗 delta）；
2. `saturation_timestamp` / `saturation_elapsed_seconds`（首次达到 capacity 的样本）；
3. `rss_before_saturation`（warm-up baseline + 饱和前最后窗均值）；
4. `rss_after_saturation`（饱和后各窗均值序列）；
5. **`post_saturation_slope_mib_per_hour`**（饱和点之后所有样本的 least-squares 斜率）；
6. `rolling_slope_mib_per_hour`（30 min 窗均上的 trailing 斜率序列）；
7. `rss_peak_mb` / `rss_final_mb`；
8. `gc_count_generation_0/1/2`、`gc_stats_collections/collected/uncollectable`（`gc.get_count()` /
   `gc.get_stats()`，**非侵入式**，禁用 tracemalloc）；
9. `tasks / sockets / handles / db_owned_sessions / db_observer_sessions` 的同步趋势
   （net growth + 每窗 delta + 与 reconnect/stale 次数的关系）。

**判据（必须显式给出，不得只写「pass」）**：

- 若 retention 到容量上限后 `post_saturation_slope` **明显趋近 0 / 平台** ⇒ 支持
  **bounded retention fill**（而非 unbounded leak）；
- 若 retention 已饱和很久而 RSS **仍持续稳定线性上涨** ⇒ **必须升级 Memory Finding 调查**
  （不得仅以 `total_growth ≤ 64 MiB` 收尾）；
- 最终 `finding` 仍严格按冻结 AND 契约计算，**threshold 不变**；
  但报告必须**同时**给出饱和前后分段斜率，使 §4 的定性问题有独立答案。

## 19. Economic Invariants（计划断言）

`final_position_flat`、`final_no_open_buy`、`final_exactly_one_exit_fill`、
`final_single_trade_lifecycle`、`final_no_duplicate_facts`、`final_reserved_cash_zero`、
`final_cash_non_negative`、`final_protection_snapshot_cleared_when_flat`、`reconciliation_ok`；
且每个 Witness / 判别 / stale / reconnect 探针的
`economic_counts.before == after`（无新 order / fill / position / ledger 行）。

## 20. Protection Authority（§10）

N01-7 已正式证明 Witness A/B/C，**N01-8 不重新设计 Witness B**。本窗口必须证明：

- 长时间运行 / 多轮 reconnect / 多次 restart 后，**Position durable protection snapshot
  仍始终是 protection authority**；
- **不因** active TradePlan / TTL / Recovery 出现 **authority drift**；
- 沿用已接受契约：TradePlan TTL 只控制 risk-increasing freshness，不控制 OPEN Position
  protection lifetime；authority 只允许两种转移（approved successor snapshot 原子提交 /
  Position becomes flat）。

## 21. Baseline Drift（§14）

- Phase 2 启动时冻结 Task Base = `dd78a979d128dee385c7a8ddc2254a53366af714`；
- 12h 运行结束后**重新读取** remote `origin/main`；
- 若发生 drift：**不**自动重跑 12h，只记录 cumulative delta（SHA + commit 列表），
  由 Independent Review 决定 no impact / targeted revalidation / full rerun；
- 建议在 12h active window 内，其它窗口**不要**把 production-changing candidate merge 到 `main`。

## 22. Verification / Acceptance Criteria（Phase 2 判定表）

| AC | 内容 |
|---|---|
| AC-01 | Repository Truth：起止两次 `ls-remote` 记录；单 head `20260913_0009`；`20260912_0006` 为 ancestor；protection 5 列读回存在 |
| AC-02 | **Production Code Changed = NO**（`production_code_unchanged = true` + `PRODUCTION_PATHS` diff 为空） |
| AC-03 | Targeted regression（`pytest backend/tests`）在 N01-8 baseline 上 PASS，并带 DB client-session exclusivity 证据 |
| AC-04 | 短窗 **Probe PASS**（含 1 reconnect + 1 stale + 1 restart），方启动正式 Run |
| AC-05 | Formal **active `total_active >= 43200 s`**，**单轮全新**、未拼接、未复用 N01-7 数据 |
| AC-06 | **>= 12** 次受控 reconnect，逐次 `disconnect_observed` + `fresh_event_after_reconnect` + `reconciliation_ok`；socket/handle 不随次数累积 |
| AC-07 | **>= 6** 次 STALE→FRESH，逐次 age > TTL + risk-increasing fail-closed + protection facts 保全 + no fabricated Fill + recovery + reconciliation PASS |
| AC-08 | **>= 3** 次 fresh-process restart：新 OS PID + durable 恢复（Account / Position / Protection authority / Runtime state）+ `no_python_memory_carried_over = true` |
| AC-09 | Protection authority 全程无 drift（§20）；Witness A/B/C 成立（B 不重新设计） |
| AC-10 | Reconciliation checkpoint **覆盖全 timeline** 且全部 `ok = true`（含 required invariants） |
| AC-11 | 资源时间序列齐备且长期有界（§16；queue/inflight/worker/tasks/sockets/handles/DB sessions） |
| AC-12 | Memory：冻结 AND 门**未改** + §18 饱和分析齐备并给出显式定性结论 |
| AC-13 | 经济不变量全绿、无 duplicate / fabricated economic fact（§19） |
| AC-14 | DB 隔离成立：unique port / db / application_name / separate observer / 显式 `DATABASE_URL`；primary 未变；disposable residue = 0 |
| AC-15 | Baseline drift 检查完成并如实记录（§21） |
| AC-16 | 结果只能是 `VALIDATED / READY FOR INDEPENDENT REVIEW`、`BLOCKED / FINDING CONFIRMED`、`INVALIDATED BY ENVIRONMENT` 三者之一；dev_log 齐备；**不得**自行 Human Accept / merge main / 宣布 N01 overall Accepted / 启动 Integrated Runtime Host |

## 23. Self-Check（Phase 1 已执行）

| # | 检查 | 结果 |
|---|---|---|
| S1 | Accepted Main == origin/main == `ls-remote` == 导航 SHA | ✅ `dd78a97` |
| S2 | 无 `n01-8*` 本地 / 远端分支冲突 | ✅ 均不存在 |
| S3 | 新建 worktree 洁净、HEAD == Task Base | ✅ `dd78a97`，`status` 空 |
| S4 | Migration 单 head + 线性 lineage | ✅ `20260913_0009`，9 个 revision 线性 |
| S5 | harness 三件套在新 worktree 存在 | ✅ |
| S6 | `py -3.14` + psutil 可用（handles/sockets telemetry 前提） | ✅ Python 3.14.2 / psutil 7.2.2 |
| S7 | `postgres:16-alpine` 镜像存在 | ✅ |
| S8 | 端口 `5440` free | ✅ |
| S9 | 未触碰根 worktree / 其它窗口容器 | ✅ |
| S10 | 现有容器清点（collision check） | ✅ 见 §25 |

## 24. Result（Phase 1）

**`PREFLIGHT COMPLETE / RUN NOT STARTED`** —— 无 blocker 阻止启动 12h；
正式 12h Run **尚未启动**，等待人工批准（§2 授权边界）。

## 25. Remaining（Phase 2 待办）与 Collision Check

**现有 worktree（14 个，`git worktree list` 实测）**：
根 `E:\Documents\MarketPulse AI`（d47313a / `prb-01-…`，**dirty**）、
`…se-arch-fix-01`、`…-c04-isolation`、`…n01-7-f01-latest-main-integration`、
`…n01-7-f01-wt2`、`…n01-7-inv-01`、`…n01-7-ms`、`…n01-7-r01`（dd78a97，clean）、
`…n01-7-soak`、`…se-02b`、`…se-02b-closeout-fix-01`（detached）、`…se-02c`、
`…se-arch-fix-01-latest-main-integration`、`…se-arch-fix-02`，
外加本窗口新建 `E:\Documents\MarketPulse-AI-n01-8`（`n01-8-12h-extended-soak` @ dd78a97）。

**现有容器（`docker ps -a` 实测）**：

| 容器 | 端口 | 状态 | 归属 |
|---|---|---|---|
| `marketpulse-postgres` | 5432 | Up 40h (healthy) | shared primary |
| `marketpulse-n01-7-r01-pg` | 5434 | Up 5h | N01-7-R01 遗留（未授权清理，原样保留） |
| `marketpulse-se-fix-02-pg` | 5437 | Up 9h | SE 窗口遗留 |
| `marketpulse-se-02c-pg` | 5438 | Up 2h | SE-02C |
| **`marketpulse-se02c-review-pg`** | **5439** | **Up 25m** | **另一活动窗口** ⚠️ |

> ⚠️ **Collision note**：`marketpulse-se02c-review-pg`（5439，25 分钟前启动）表明**另一个窗口正在活动**。
> 本窗口**不触碰**其容器 / worktree；但因 §14 建议 active window 内避免 `main` 被 merge，
> 需在 Phase 2 启动前向用户确认该窗口是否会在此期间推进 `main`（否则 12h 后可能记录 baseline drift）。

**Phase 2 待办**：

1. 人工批准启动 12h；
2. 创建 `marketpulse-n01-8-pg` @ 5440 + worktree gitignored `.env`（指向 5440）；
3. 编写 `scripts/verify_n01_8_extended_soak.py`（G1–G10 适配）；
4. 跑短窗 Probe（AC-04）→ 通过后启动正式 12h（AC-05）；
5. 采证 / 分析（§16–§18）→ 写 N01-8 dev_log 结果章节 → 给出 §22 三选一结论。

## 26. Known Risks

| # | 风险 | 影响 | 处置 |
|---|---|---|---|
| R1 | **会话/宿主生命周期**：12h 远超单轮对话；supervisor 子进程与宿主会话的关系不明 | 可能中途被杀 ⇒ `INVALIDATED BY ENVIRONMENT` | 采用**真正 detached** 启动（新进程组 + 输出重定向到文件），跨轮以 progress JSONL / raw 文件 re-attach 轮询；启动前先验证 detached 存活 |
| R2 | **另一活动窗口（5439）** 可能在本窗口期间 merge `main` | 12h 后出现 baseline drift | 启动前确认；drift 只记录不重跑（§21） |
| R3 | **socket/handle band 门**（`MAX_PERMANENT_SOCKET_DELTA=2` / `HANDLE_DELTA=16`）按 2h/5 reconnect 校准 | 12h/12 reconnect 下可能被**合法慢漂移**触发 | **保持门冻结**（不移动 goalpost）；若触发，按 §15 分类为 investigation，不自动判 product defect |
| R4 | 根 worktree dirty（`prb-01-…`） | 误操作可能破坏他人窗口 | 全程只在本窗口 worktree 作业 |
| R5 | `E:` 剩余 29.8 GiB | 12h 日志/progress 体量 | 预计 << 1 GiB，非阻塞；Phase 2 前再确认 |
| R6 | OKX REST 依赖本机代理 `127.0.0.1:10808` | REST metadata 拉取失败 ⇒ 无法启动 | Phase 2 前实测代理可用性 |
| R7 | Memory slope 单支越线历史（`5.255 → 16.02`） | 可能出现「RSS 平台化但 slope 仍单支越线」的解读歧义 | §18 强制分段斜率 + 饱和判定，避免只按 AND 门一句话收尾 |

## 27. Evidence（Phase 1）

| 路径 | 内容 |
|---|---|
| `E:\Documents\MarketPulse-AI-n01-8\dev_log\2026-09-14-n01-8-extended-soak.md` | 本文件（preflight） |
| Git | branch `n01-8-12h-extended-soak` @ `dd78a979d128dee385c7a8ddc2254a53366af714` |
| 只读参照（**未**修改） | `E:\Documents\MarketPulse-AI-n01-7-r01\`（`dd78a97`，clean）、`E:/Temp/n01-7-r01/`、`E:/Temp/n01-7-medium/` |
| Phase 2 计划证据路径 | `E:/Temp/n01-8/acceptance_raw.json`、`E:/Temp/n01-8/n01-8-logs/`（外部，不入 Git） |

## 28. Context For Next AI

- 本窗口 Task Base = `dd78a979d128dee385c7a8ddc2254a53366af714`；结论**仅覆盖**该 SHA
  与运行结束时重新读到的 `origin/main`。
- 作业入口：worktree `E:\Documents\MarketPulse-AI-n01-8`；解释器 `py -3.14`；
  `.env` 必须指向 `marketpulse-n01-8-pg` @ `127.0.0.1:5440`（`Settings` 读 **cwd** 的 `.env`，
  `alembic/env.py` 优先读 `os.environ["DATABASE_URL"]`）。
- 复用正主是 `scripts/verify_n01_7_medium_soak.py`（supervisor 版），
  runtime 构造一律经 `scripts/verify_n01_6_runtime_smoke.py` 的 import 契约。
- 冻结不可动：Memory 阈值 `64 MiB` / `5 MiB/h`；TradePlan TTL 与 Position durable protection
  snapshot 的 authority 契约；Production Code。
- **未做**：正式 12h Run、Human Accept、merge main、N01 overall Acceptance、
  Integrated Runtime Host、任何 SE 改动。

---
---

# 第二部分｜Phase A / B / C 执行记录（本轮）

> 本节由 Phase 2 执行窗口追加。前面的 §1–§28 是 Phase 1（Preflight）原文，保留不改。

## 29. Phase A｜Repository Truth Re-Preflight（重新实测，不盲信旧 Preflight）

| 项 | 实测命令 | 实测值 | 结论 |
|---|---|---|---|
| worktree 存在 | `ls E:/Documents/MarketPulse-AI-n01-8` | 存在 | ✅ |
| 当前 branch | `git rev-parse --abbrev-ref HEAD` | `n01-8-12h-extended-soak` | ✅ |
| HEAD | `git rev-parse HEAD` | `dd78a979d128dee385c7a8ddc2254a53366af714` | = Task Base ✅ |
| `git status --porcelain` | — | 仅 `?? dev_log/2026-09-14-n01-8-extended-soak.md` | 洁净（除声明中的 validation 产物）✅ |
| `git ls-remote origin refs/heads/main` | 实时 | `dd78a979d128dee385c7a8ddc2254a53366af714` | **无 drift** ✅ |
| 远端 N01-8 branch | `git ls-remote --heads origin` | **不存在** | 本窗口将首次 push ✅ |
| 生产代码 diff | `git diff --stat dd78a979 -- backend/src backend/alembic frontend` | 空 | ✅ |
| Migration head | lineage 实测 | `20260913_0009`（`0001…0009` 线性 9 个） | 单 head ✅ |
| 根 worktree | `git worktree list` | `E:/Documents/MarketPulse AI` @ `d47313a` `prb-01-…` | **未触碰** ✅ |
| 解释器 | `py -3.14 -c ...` | Python 3.14.2 / psutil 7.2.2 / SQLAlchemy 2.0.52 / websockets 15.0.1 | ✅ |
| 端口占用 | socket probe | 5432/5434/5437/5438 IN USE；**5439 已释放**；**5440 free** | ✅ |
| 容器清点 | `docker ps -a` | `marketpulse-postgres`(5432)、`n01-7-r01-pg`(5434)、`se-fix-02-pg`(5437)、`se-02c-pg`(5438) | 均非本窗口所有，未触碰 ✅（Preflight 时的 `se02c-review-pg`@5439 已消失） |

**结论：AC-PRE-01 PASS。** 导航 SHA 与远端实测一致，无 baseline drift。

## 30. Phase A 补充｜真实依赖连通性

| 项 | 结果 |
|---|---|
| OKX WS 直连 `ws.okx.com:8443` | **OK**（TCP 可连） |
| 本机代理 `127.0.0.1:10808`（仅 OKX REST metadata 用） | **OK** |
| `postgres:16-alpine` 镜像 | 本地存在 ✅ |

## 31. Phase B｜Validation Harness Minimal Adaptation

### 31.1 新增文件（全部 validation-only；已验收脚本零改动）

| 文件 | 行数 | 角色 |
|---|---|---|
| `scripts/verify_n01_8_extended_soak.py` | ~1090 | N01-8 主 harness：role 驱动 N-phase supervisor + 12h schedule + retention 饱和分析 + N-phase 聚合 |
| `scripts/n01_8_detach.py` | ~290 | detached launcher（Task Scheduler 双段式：`task` / `launcher` / `cleanup`） |
| `scripts/n01_8_detach_probe.py` | ~110 | §18 detached survival probe 的合成短负载（不做任何仓库工作） |

**未修改**：`scripts/verify_n01_6_runtime_smoke.py`、`scripts/verify_n01_7_medium_soak.py`、
`scripts/verify_n01_7_runtime_soak.py`、任何 `backend/**`、`frontend/**`、`PRODUCT_REQUIREMENTS.md`。

### 31.2 复用契约（import，不复制）

`verify_n01_8_extended_soak.py` 顶层 import 三个已验收 harness，并**只**通过
`_apply_env_identity()` 改写以下模块属性（不编辑任何已验收文件）：

| 改写项 | N01-7-R01 值 → N01-8 值 |
|---|---|
| `n6.DATABASE_PREFIX` / `soak.N01_7_DATABASE_PREFIX` | `marketpulse_n01_7_r01_` → **`marketpulse_n01_8_`** |
| `n6.OWNED_APPLICATION` / `soak.N01_7_OWNED_APPLICATION` | `marketpulse-n01-7-r01-runtime` → **`marketpulse-n01-8-runtime`** |
| `n6.OBSERVER_APPLICATION` / `soak.N01_7_OBSERVER_APPLICATION` | `…-n01-7-r01-observer` → **`…-n01-8-observer`** |
| `soak.TASK_OWNED_DATABASE_PORT` | `5434` → **`5440`** |
| `ms.TASK_BASE_SHA` | `8a29306…` → **`dd78a979…`** |
| `ms.ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS` | `7200.0` → **`43200.0`** |
| `ms.TARGET_RECONNECTS` / `ms.TARGET_STALE_CYCLES` | `5` / `2` → **`12` / `6`** |
| `ms.PROBE_SCOPE_KEYS` | 追加 5 个 N01-8 项 |
| `ms.WITNESS_B_PLAN_TTL` | `6h` → **`18h`**（见 31.4） |

实测核对（`py -3.14 -c "import verify_n01_8_extended_soak as v8; …"`）全部生效：
`EXPECTED_MIGRATION_HEAD = 20260913_0009`、`TASK_OWNED_PORT = 5440`、
`MEM_THRESH = 64.0 / 5.0`（**未改**）、`POST_EXPIRY_DELAY = 60.0`。

### 31.3 相对 N01-7 的最小 delta（对应任务 §12 A–J）

| # | delta | 落点 |
|---|---|---|
| A | `>=12h total active` | `ACCEPTANCE_MIN_TOTAL_ACTIVE_SECONDS=43200.0`；4×11100 = **44400 s** |
| B | **N-phase supervisor** | 已验收 `ms._phase_scenario` 用 `phase == "first"/"second"` 硬编码 open/close 两态，无法表达"持仓跨 3 次重启保持 OPEN"，故改为 **role 驱动**（`open` / `continue` / `close`），runner 内每一步都调用已验收 helper |
| C | 12h deterministic schedule | `_GLOBAL_SCHEDULE`：实测 12 reconnect / 6 stale / 12 每小时 checkpoint |
| D | 全 timeline reconciliation | start / after_restart×3 / 每小时×12 / reconnect×12 / stale×6 / final_before_stop / final |
| E–H | retention 饱和 + post-saturation + rolling slope + 非侵入 GC | `_retention_analysis` / `_rolling_slopes` / `_gc_telemetry`（**明确不用 tracemalloc**——它是侵入性探针，会自行抬高 RSS 污染长跑序列） |
| I | 资源与事件联合趋势 | `companion_trends`（tasks/workers/queue/inflight/sockets/handles/DB sessions/worker exceptions/event count） |
| J | N01-8 环境身份 | 见 §31.2 |

**N-phase 聚合复用方式**：`_merge_phase_reports()` 把 N 份 phase report 折叠成已验收
`ms._aggregate` 期望的 `(first, second)` 对——`checks` 逐 phase **AND 合并**（任一 phase 的
False 都不可能被掩盖）、事件列表拼接、时长求和、restart 边界字段取**倒数第二个 phase**。
折叠方式写进报告的 `phase_merge` 字段供复核。

### 31.4 明确记录的两处 validation-only 常量变更（供 Reviewer 定向 diff）

1. `WITNESS_B_PLAN_TTL: 6h → 18h`。该常量是 **validation probe 的属性、不是产品契约**（已验收代码原注释即如此声明）。12h 窗口下 6h 的 Plan B 会在最后两次 restart 前过期，使 Witness C 退化成"plan 已过期"这一不同（且更弱）的问题；18h 是保持 witness 语义不变的最小改动。Plan A 仍保留真实产品 30 分钟 TTL 并先过期。
2. `_PROBE_SCHEDULE` 中显式加回 `witness_b` 项——与已验收 N01-7 probe 行为一致（N01-7 亦在 probe schedule 中显式排 `witness_b`）。

### 31.5 Phase B 门

| 门 | 命令 | 结果 |
|---|---|---|
| 编译 | `py -3.14 -m py_compile scripts/verify_n01_8_extended_soak.py` | PASS |
| ruff（项目门） | `py -3.14 -m ruff check backend/src backend/tests scripts` | **All checks passed!** |
| 身份/常量核对 | 见 §31.2 | PASS |

## 32. Phase B｜Database Isolation（实测建立）

| 项 | 实测 |
|---|---|
| 容器 | `marketpulse-n01-8-pg`（`postgres:16-alpine`），`127.0.0.1:5440:5432`，`POSTGRES_USER/PASSWORD/DB=marketpulse` |
| 实例可用 | `SHOW server_version` = **16.15**；实例内 db 列表 = `['marketpulse']` |
| worktree `.env`（gitignored） | **仅一行** `DATABASE_URL=postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5440/marketpulse` |
| `Settings().database_url`（cwd = worktree） | `postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5440/marketpulse` ✅ |

> ⚠️ 关键机制：`n6._disposable_postgres_database()` / `n6._observer_engine()` /
> `n6._n01_6_leftover_databases()` / `n6._alembic_version()` 全部经 **`Settings()`（读 cwd 的 `.env`）**
> 定位实例。因此 worktree 根 `.env` 是隔离的唯一锚点；缺它则 disposable DB 会建到 shared primary 5432。
> `.env` 已被 `.gitignore` 覆盖（`git status --porcelain` 不显示）。
> 运行子进程的 cwd 固定为 `REPOSITORY_ROOT`（`ms._run_child(cwd=REPOSITORY_ROOT)`），所以该锚点对 phase 子进程同样成立。

## 33. Phase C｜Detached Survival Probe（§18）

### 33.1 为什么需要它（实测的逃逸路径矩阵）

12h 远超任何单轮会话。已批准决策 R1 要求使用**真正 detached** supervisor。本沙箱实测结果：

| 机制 | 实测结果 | 判定 |
|---|---|---|
| `Popen(DETACHED_PROCESS｜CREATE_NEW_PROCESS_GROUP)` | 命令返回后子进程**静默被杀**（progress 仅 1–2 行，无 stderr / 无 traceback） | ❌ |
| `+ CREATE_BREAKAWAY_FROM_JOB` | 4 种 flag 组合（含 `CREATE_NO_WINDOW` / `CREATE_NEW_CONSOLE`）**全部同样被杀**，`CreateProcess` 未报 access denied | ❌ |
| WMI `Win32_Process.Create` | 被沙箱安全策略直接拒绝（"equivalent to Start-Process"） | ❌ |
| PowerShell `Start-Process` | 未生效 / 同被拒 | ❌ |
| Bash 工具后台任务（`run_in_background`） | 子进程存活，但归属 agent 进程树 ⇒ **违反 §18.8** | ❌ |
| **Windows Task Scheduler（一次性任务 + `/run`）** | launcher 退出后 **子进程存活、心跳继续增长**；父子链为 `taskeng/svchost → cmd.exe → python.exe`，**不在 agent 进程树内** | ✅ **采用** |

### 33.2 采用机制与边界

`scripts/n01_8_detach.py` 两段式：
1. **`--mode task`（agent 侧）**：写 `detach_spec.json` + `n01_8_task.cmd` → `schtasks /create … /sc ONCE /st 23:59 /f /it` → `schtasks /run` → 有界发现 supervisor PID → 写 `detach_launch.json` 与 `task_query.txt` → 返回（**launcher 进程退出**）。
2. **`--mode launcher`（任务实例内）**：读 spec → `DETACHED_PROCESS｜CREATE_NEW_PROCESS_GROUP` 拉起真实 supervisor，stdout/stderr 落盘 → 记录 `launcher_pid` / `child_pid` / `child_alive_after_2s` / `launcher_exits_at` → 写 `launch.json` → **立即退出**。

> ⚠️ **对宿主状态的改动（已披露、可逆）**：该机制会在本机注册一个名为 `n01-8-*` 的一次性计划任务（`/sc ONCE /st 23:59`，仅由 `/run` 触发）。这是本沙箱中满足"不依赖 Chat/Agent 进程"的唯一可行途径。**收尾时会用 `--mode cleanup` 删除全部 `n01-8-*` 任务**；不使用时不残留。

### 33.3 第一次尝试的失败（保留为证据）

第一次运行 launcher 报 `PermissionError: [Errno 13] … launcher_stdout.txt`：`n01_8_task.cmd` 用 `>>` 持有该文件句柄（无 `FILE_SHARE_WRITE`），launcher 再以 `ab` 打开同一文件即失败。
**修复**：任务侧重定向改为 `task_stdout.txt` / `task_stderr.txt`，launcher 写 supervisor 输出到 `supervisor_stdout.txt` / `supervisor_stderr.txt`；并给 launcher 加 `spawn_error` 兜底，任何失败也必落 `launch.json`。

### 33.4 Probe 结果（实测工件）

run dir `E:/Temp/n01-8/_detach_probe/probe2`：

| 要求 | 证据 | 结果 |
|---|---|---|
| 1 launcher / parent 退出 | `launch.json`: `launcher_pid=32056`，`launcher_exits_at=17:16:34`，`spawn_error=null`；随后该 PID 已不存在（`parent None`） | ✅ |
| 2 child supervisor 仍存活 | `launch.json`: `child_pid=19452`，`child_alive_after_2s=true`；命令返回后再次采样：`alive=True status=running` | ✅ |
| 3 progress JSONL 在 parent exit 后继续增长 | `progress.jsonl`：2 行（launcher 仍在时）→ **73 行**（launcher 已退出后） | ✅ |
| 4 stdout 持久化 | `supervisor_stdout.txt` 存在并持续追加 | ✅ |
| 5 stderr 持久化 | `supervisor_stderr.txt` 存在并持续追加 | ✅ |
| 6 exit status / 完成态可持久读取 | `status.json` 每次采样重写（`state/pid/ppid/seq/elapsed_seconds`）；终态额外写 `final.json` | ✅ |
| 7 新会话可经 PID + 工件重读状态 | 上述所有读取都是**另一个** shell 命令（不同 agent 调用）执行的，未复用启动进程 | ✅ |
| 8 不依赖 Chat/Agent 进程存活 | 父链 `taskeng/svchost → cmd.exe → python.exe`，与 agent 进程树无关 | ✅ |

**结论：Detached Survival Probe = PASS（机制层面）。** 正式 12h 将复用同一 launcher；
Phase D 会再用**真实 supervisor** 走同一路径，作为第二次（真实负载）Detached 证据。

## 34. Phase D｜短运行 Probe

| 项 | 值 |
|---|---|
| 启动方式 | `n01_8_detach.py --mode task --label short-probe`（同一 detached 机制） |
| task name | `n01-8-short-probe` |
| phase plan | `p1_open`(open, 420 s) → `p2_close`(close, 420 s)；⇒ 1 reconnect + 1 STALE→FRESH + 1 fresh-process restart |
| 启动时 `main_before` | `dd78a979…`（= Task Base，无 drift） |

### 34.1 第一轮（修复前）

| 项 | 值 |
|---|---|
| run dir | `E:/Temp/n01-8/probe/` |
| supervisor / phase PID | 23216 / p1_open 28552、p2_close 28328 |
| 结果 | `result=PROBE_OK`，`failures=[]` |
| 早期实测 | `health_status=HEALTHY`；真实 BTC/ETH trades+BBO 均在；`dedupe_capacity=8192`、`trade_dedupe_capacity=8192`、`worker_count=4`、`rss_mb≈113.8`、`btc_fresh=True` |

第一轮已经 `PROBE_OK`，但**我没有把它当作"可以开跑 12 h"的证据**——probe 的 `PROBE_SCOPE_KEYS` 会掩盖一批"短跑结构上不可能满足"的判据。于是对正式运行做了一次定向反虚过审计（§37），并因此发现两个真实 harness defect。

### 34.2 修复后复跑

| 项 | 值 |
|---|---|
| run dir | `E:/Temp/n01-8/probe4/` |
| supervisor PID | 2540（launcher `launch.json.child_pid`=`11396` 为 task wrapper 记录，实际 supervisor 由 `supervisor_status.json` 记录） |
| phase PID | p1_open 17928、p2_close 27772 |
| DB | `marketpulse_n01_8_62d6e5774019` @ `127.0.0.1:5440` |
| migration head | `20260913_0009` |
| wall clock / total active | 862.076 s / **840.608 s**（2×420 s） |
| restart gap | 6.9 s（两 PID 不同，fresh-process 成立） |
| checkpoint 标签（实测） | `start` / `after_restart` / `before_restart` / `final` / `probe_p1_late` / `probe_p2_late` |
| 判据 | **99 checks**；`failures=[]`；⇒ **`result=PROBE_OK`** |
| 两相位 | `p1_open` OK（1 reconnect / 1 stale / 3 checkpoint，`non_true_checks=[]`）；`p2_close` OK（0 / 0 / 3，`non_true_checks=[]`） |
| memory | `finding=false`，`total_growth=1.66 MiB ≤ 64`，`branch_second_half_slope_exceeded=false`（短跑不可外推） |

**Phase D = PASS。** 允许进入 Phase E。


## 35. Self-Check（本轮）

| # | 检查 | 结果 |
|---|---|---|
| S1 | 生产代码 / 迁移 / 已验收测试 / 已验收 harness diff 为空 | ✅（`git diff --stat dd78a979` 空；ruff 门绿） |
| S2 | 根 worktree 与其它窗口资源未被触碰 | ✅ |
| S3 | N01-8 隔离：唯一容器 / 端口 / DB 前缀 / application_name / 显式 `DATABASE_URL` | ✅ |
| S4 | Detached 机制经实测确定，且理解其宿主侧副作用与清理方式 | ✅ |
| S5 | Memory 冻结阈值未被修改（`64.0` / `5.0`，AND） | ✅ |
| S6 | tracemalloc 未被用于长跑 RSS 采样 | ✅（只用 `gc.get_count()/get_stats()`） |

## 37. Phase D 反虚过审计（正式运行预检）与两个 harness defect

probe 通过 ≠ 正式 12h 会通过。`ms.PROBE_SCOPE_KEYS` 会静默掩盖一批判据，因此对**正式运行**单独做了一次穷举审计：把 `ms._aggregate` 定义的全部 **72 个** `checks[...]` 逐条判定是否隐含 N01-7 的「两相位 / 两小时」形状假设。结果发现两个真实缺陷（均属**验证器缺陷**，非产品缺陷；修复只落在 N01-8 validation harness，未触碰任何已验收文件）。

### 37.1 Defect 1｜继承判据硬编码 N01-7 两小时 checkpoint 契约

`verify_n01_7_medium_soak.py::_aggregate` 内：

```python
required_labels = {"start", "abs_30m", "before_restart", "after_restart", "abs_90m", "final"}
checks["checkpoint_coverage_complete"] = required_labels.issubset(labels)
coverage_bands = (("start",0.0,300.0),("~30min",1500.0,2100.0),("~60min",3300.0,3900.0),("~90min",5100.0,5700.0))
checks["checkpoints_cover_required_points"] = bool(
    len(checkpoints) >= 7 and {"before_restart","after_restart"} <= labels
    and all(any(low <= v <= high for v in absolute_times) for _, low, high in coverage_bands))
```

- 这是**已验收代码里的静态契约**，不允许修改。
- 我最初的 N01-8 调度只发 `abs_1h…abs_12h`：缺 `abs_30m` / `abs_90m` / `before_restart`，且覆盖带 `[1500,2100]`、`[5100,5700]` 上没有任何 checkpoint。
- 该判据在 probe 下被 scope 掩盖（probe4 的 non-True 列表里确实有这两项），但**正式运行 `probe=False`，不套 scope ⇒ 必然 FAIL**，且会是"harness 原因"造成的假失败。

**修复（N01-8 侧，等价复现已验收契约的语义）：**

1. `_GLOBAL_SCHEDULE["p1_open"]` 增加 `abs_30m`@1800 s、`abs_90m`@5400 s —— 恰好落在契约命名的两个绝对时刻（绝对 30 min / 90 min）。
2. 相位场景新增 `before_restart` checkpoint：在每个"后面还会 restart"的相位（`open` / `continue`）结束前 60 s 发一次，与 N01-7 的 `before_restart`@3540/3600 位置语义一致。
   - `start` / `after_restart` / `final` **原本就已发出**（相位活跃窗起点的边界 checkpoint + close 相位的 `ms._final_assertions`），本轮实测标签集里可见，无需新增。

### 37.2 Defect 2｜`phase_failures` 只覆盖首末两相位（正式运行的漏报面）

`ms._aggregate` 内：

```python
phase_failures = [item for item in (first.get("failure"), second.get("failure")) if item]
```

折叠后 `first`=p1、`second`=p4，**p2 / p3 的 `failure` 不在其中**。若中间相位以异常失败但其 `checks` 恰好仍全 True，聚合结果可能漏报。

**修复：** 在 N01-8 侧新增三个覆盖**全部相位**的判据（非 probe-scope，正式运行必须为真）：
`no_phase_failures_recorded`、`all_phases_result_ok`、`no_phase_report_build_errors`。
probe4 实测三项均为 `True`。

### 37.3 顺带清理（非 gate 变更）

- 删除一个**同名碰撞的死代码**：我原先把 `checkpoints_cover_required_points` 也放进 extra_checks，但 `ms._aggregate` 已定义同名键，`setdefault` 使其永不生效；已移除（该键本身仍在 `ms.PROBE_SCOPE_KEYS` 中，行为不变）。
- 把 `hourly_checkpoint_coverage_complete` 从 `len(checkpoints) >= 1`（几乎恒真）**强化为** `abs_1h…abs_12h` 标签全覆盖。

### 37.4 另一个被审计过但**判定不改**的点（`worker_count_stable` 停止期竞态）

`worker_count_stable` 要求**每一条**样本 `worker_count==4 and workers_alive==4`；而停止序列是 `await runtime.stop()` 之后才 `sampler.cancel()`（与 N01-7 已验收实现逐字一致）。`g2/runtime.py::stop()` 在 `await asyncio.gather(workers)` 之后**同步** `self._workers.clear()`，紧接着调用方**同步** `cancel()`，两者之间不 yield 事件循环 ⇒ 采样器读到 `worker_count=0` 只存在亚毫秒级调度缝隙，跨 4 个相位仍可忽略且不影响任何断言强度。**结论：保持与已验收实现逐字一致，不引入顺序偏差**，仅在本文档记录该推理。

## 38. 正式调度预检（确定性，不消耗 12 h）

`E:/Temp/n01-8/schedule_preflight.py`（repo 外，不进提交）以固定契约对 `PHASE_PLAN` + `_GLOBAL_SCHEDULE` + 边界 checkpoint 规则做**纯静态推演**，直接套用 `ms._aggregate` 的两个判据公式：

| 结论 | 值 |
|---|---|
| 总 checkpoint | 24 |
| 标签集 | `start, after_restart, abs_30m, abs_1h, abs_90m, abs_2h…abs_12h, before_restart, final_before_stop, final` |
| `checkpoint_coverage_complete` | **True**（必需子集齐全，`missing=[]`） |
| `checkpoints_cover_required_points` | **True** |
| 覆盖带 | `[0,300]→0.5`；`[1500,2100]→1800`；`[3300,3900]→3600`；`[5100,5700]→5400` |
| `hourly_checkpoint_coverage_complete` | **True**（`abs_1h…abs_12h` 齐全） |
| 预期总活跃 | **44421 s ≥ 43200** |
| 判定 | **SCHEDULE_PREFLIGHT: PASS** |

> 说明：预检用固定契约（相位 11100 s、restart gap 7 s）而不是实测值，属**计划层证明**；正式运行的实测值另在 §Phase E 记录，两者必须一致。

## 39. Remaining（本轮之后）

1. **Phase E** 正式 ≥12 h Acceptance Run（`PHASE_PLAN` 4×11100 s，detached 启动）。
2. **Phase F** 证据/分析/dev_log 收尾（AC-01…24 判定；baseline drift 复检；raw 留在 `E:/Temp/n01-8`，Git 仅存摘要/路径/hash）。
3. **Phase G** commit `n01-8-12h-extended-soak`（仅 validation scripts + dev_log + 最小 PROJECT_STATE/AI_CONTEXT）→ push 候选分支。
4. 收尾清理：`schtasks /delete` 删除全部 `n01-8-*` 任务；disposable DB 残留核验 = 0。
5. STOP（不 merge `main`、不做 Human Accept、不宣布 N01 overall ACCEPTED）。

## 40. Phase E｜正式 ≥12h Acceptance Run（已启动）

| 项 | 值 |
|---|---|
| 启动方式 | `n01_8_detach.py --mode task --label formal --run-dir E:/Temp/n01-8/formal`（Task Scheduler detached） |
| task name | `n01-8-formal` |
| supervisor PID | **3716**（`supervisor_status.json` 实测） |
| 启动时刻（UTC） | `2026-09-13T18:09:54.677541+00:00` |
| mode / phase plan | `ACCEPTANCE` / `p1_open(open) → p2_continue(continue) → p3_continue(continue) → p4_close(close)` |
| phase_seconds | **11100.0**（计划总活跃 44400 s ≈ 12 h 20 m；预检实测契约 44421 s） |
| raw-out | `E:/Temp/n01-8/formal/acceptance_raw.json` |
| `main_before` | `dd78a979d128dee385c7a8ddc2254a53366af714` = Task Base（**无 drift**） |
| 隔离 | container `marketpulse-n01-8-pg` / port `5440` / prefix `marketpulse_n01_8_` / app `marketpulse-n01-8-runtime`、`marketpulse-n01-8-observer` |
| 启动后 90 s 健康检查 | `state=RUNNING`、`phases_completed=0`、p1_open 运行中；`elapsed=70.6 s`；真实 BTC 22 / ETH 33 trades；`btc_fresh=True`；`health_status=HEALTHY`；`rss=113.6 MiB`；`worker_count=4`；`pg_owned_client_sessions=3` |

**状态：RUNNING。** 预期完成 ≈ 启动后 12 h 20 m。Phase E 结论、AC-01…24 判定与证据另行追加。

> 运行期间 FREEZE `main`（Task §14）：本窗口不对 production / migration / frontend / 已验收 tests / 已验收 harness 做任何写入；`main` 漂移只在 Phase F 以起止两次 `git ls-remote` 对比判定，不做任何 reset / rebase / 覆盖。

## 41. Phase E｜正式 ≥12h Run 结果

| 项 | 值 |
|---|---|
| 结果 | **`PASS`**，`failures = []`，`phase_process_errors = []` |
| 判据 | **99 checks，全部 `True`，非 True 项 = 0** |
| 4 相位 | 全部 `result=OK`；PID = `3516`(p1_open) / `19892`(p2_continue) / `4660`(p3_continue) / `14372`(p4_close) |
| fresh-process restart | **3 次**（4 个互异 PID，且 `fresh_process_pids_all_distinct=True`） |
| 单相位 active | 11100.188 / 11100.469 / 11100.473 / 11100.088 s |
| **total active** | **44401.217 s（= 12 h 20 m 01 s ≥ 43200 s）** |
| wall clock | 44452.521 s（≈ 12 h 20 m 52 s） |
| restart gap（最后一次） | 12.493 s |
| controlled reconnect | **12**（p1..p4 = 3/3/3/3），全部 `disconnect_observed ∧ fresh_event_after_reconnect ∧ reconciliation_ok` |
| controlled STALE→FRESH | **6**（2/1/2/1），全部 6 项见证：风险门在停顿中 fail-closed、无 economic fact、protection facts 保全、fresh 后恢复、reconciliation OK |
| checkpoint | **24**（7/6/6/5） |
| 唯一时间线 | 单一 disposable DB `marketpulse_n01_8_452d9d31994b` @ `127.0.0.1:5440`；migration head `20260913_0009`（与 accepted lineage 一致，单 head / 9 revision） |
| Witness A / B / C | A：Plan A TTL 到期后持仓仍开 + durable snapshot 在；B：Plan B（`plan_f9c956…` v2）与 Plan A（`plan_7d212f…` v1）id/stop/tp 全异且 Plan B **未被** protection 采纳；C：每次 restart 后 authority 仍 = durable Position snapshot |
| F01 跨 restart 不变量 | p4 restart 实测 `authority.plan_id = plan_7d212f0ce53054e676a6e30c` v1、`stop_loss=73460.65 / take_profit=81193.35`，与 p1 的 `position_snapshot_before_plan_b` **完全一致**；`open_position_unprotected_incidents = 0` |
| 资源 | `sockets` net `0`（max 6）；`handles` net `−11`；`asyncio_tasks_total` net `+1`；`worker_count` 恒 `4`；`queue_size` ≤ 1；`inflight` ≤ 1；`pg_owned_client_sessions` ≤ 3 |
| 有界 retention | `dedupe` / `trade_dedupe` 均触顶 **8192**（首次饱和 14389 s / 4932 s），持续饱和后仍稳定 |
| 残留 | `leftover_databases = 0`；shared primary revision 前后同为 `20260905_0004`、`n01_7_owned_sessions_visible = 0` |
| 生产码 | `production_code_unchanged = True`（`production_diff_stat = ""`、`production_frozen = True`） |

## 42. Memory 判定与解释（**不得**写成 memory resolved）

### 42.1 冻结 AND 门逐支报告（口径 = 接受实现的 warm-up trim 后 `peak − baseline` **AND** 后半段斜率）

| 支 | 实测 | 阈值 | 是否越线 |
|---|---|---|---|
| total growth（trim 后 `peak − baseline`） | **77.711 MiB** | `> 64.0` | 🚩 **是（越线）** |
| second-half trend | **−0.639 MiB/h** | `> 5.0` | 否 |
| **AND 合成** | — | 两支须**同时**成立 | **`finding = false`** |

⇒ 接受门 `memory_within_approved_condition = True`（= `not finding`）。**但这不等于"内存无问题"**：
`branch_total_growth_exceeded = true`，其中一支已越线，属**未闭合的开放问题**。

### 42.2 越线支的机制归因（N01-8 后验量化；**仅解释，不替代冻结门**）

`total_growth` 越线的**不是**单调增长，而是 **warm-up trim 的 `peak − baseline` 口径 × 3 次 fresh-process restart** 造成的**跨进程混淆**。逐相位与 30 min 滚动窗口实测（基于 raw 内 4409 条样本）：

| 证据 | 值 |
|---|---|
| 逐相位 RSS | 每相位 `first ≈ 112.6–114.3` → 早期峰 `114.5–116.3` → 随后稳定 `~38–45`（相位内 min 35.1–36.5） |
| 30 min 窗口均值 | 仅 4 个窗口高：`start=0`(50.71/114.47)、`10800`(50.36/115.28)、`21600`(73.29/116.34)、`32400`(54.78/114.95) —— **恰好是 4 个相位各自的启动窗**；其余 21 个窗口均值 39.2–47.2 |
| 全局峰值位置 | `peak = 116.344 MiB` @ `absolute_elapsed = 22462.7 s`，**位于 p3_continue 的启动瞬态内** |
| `baseline` 位置 | `38.633 MiB` @ 全局 10% trim 点，**位于 p1_open 的已稳定平台内** |
| overall trend | **+0.021 MiB/h**（12.3 h 近乎零） |
| rolling 30 min trailing slope | **−0.075 MiB/h** |
| 逐相位后半段斜率 | p1 **+1.02** / p2 **+3.99** / p3 **−0.56** / p4 **+1.20** MiB/h（最大 3.99，仍 < 5.0） |
| 稳态平台 | 每相位起动后 ~2.5 h 内稳定在 39.2–46.7 MiB，末值 40.66 MiB ≈ trim 起点 38.63 MiB |

⇒ **机制表述**：4 个独立进程各自在启动后进入 ~113–116 MiB 的瞬时状态，随后回落到 ~40 MiB 并长期平台化；`peak − baseline` 因此把「p3 的启动瞬态」减去「p1 的平台」，得到 77.711 MiB —— 这是**口径 × 进程重启次数**的产物，**不是**内存单调增长。这也解释了 N01-7-R01 只跑 1 次 restart、`total_growth` 仅 14.043 MiB 的差异。

### 42.3 与继承 watch item 的关系（**不得宣布关闭**）

- `N01-7-R01-RR-P2-01`（上一轮 `slope ≈ 16.02 MiB/h > 5.0`、`growth ≈ 14.043 ≤ 64`，`finding=false`）：**本窗口不关闭该 watch item**。
- 但本轮提供了实质新材料：**在 6 倍时长（12.3 h vs 2 h）下，后半段斜率 = −0.639 MiB/h（上一轮 +16.02），overall = +0.021 MiB/h，rolling = −0.075 MiB/h** ⇒ 上一轮观察到的上升斜率**未在 12 h 尺度复现**。
- 保留项仍然成立的理由：`total_growth` 支越线（77.711 > 64）虽已归因于口径×重启，但**冻结门不允许改阈值**，且本轮结论**不得**被用作"内存已解决"。
- `operational_memory_interpretation.classification = POST_SATURATION_PLATEAU`（`retention_saturated = true`，饱和后观测 **8974.771 s**，饱和后斜率 `0.854 MiB/h`）—— 与之独立、互不替代。

## 43. Baseline Delta（Task §14；**drift = YES，已分类**）

| 项 | 值 |
|---|---|
| Task Base（Phase 2 冻结） | `dd78a979d128dee385c7a8ddc2254a53366af714` |
| run 开始 remote main | `dd78a979…`（= Task Base） |
| **run 结束 remote main** | **`b77c80333b85d6e3f1095ac7da9b13e9bf08163a`** |
| `drifted` | **`true`** |
| cumulative delta | `dd78a979..b77c8033` = **10 commits**，全部属 SE-02C 系列（`721c488` feat → `7a68bf0`/`be3aa6c` → `51891c7` merge → `7ab1d42` fix(R1/R2/R4) → `2f98682` → `6b08459` fix(SE-02C-FIX-02 stable read snapshot) → `7bb3835` → `b77c803` accept closeout） |
| 是否命中 STOP 触发区 | **是**。`--name-status`：`M backend/src/marketpulse/g2/runtime.py`（**+25**，即在被本 soak 覆盖的 runtime 组件上新增 opt-in `forward_path_recorder` 参数，并在 ingest 路径新增一次 `await self.record_forward_path(market_event)`，无 recorder 时立即返回）、`M backend/src/marketpulse/market_data/models.py`、`M backend/src/marketpulse/market_data/normalizer.py`、`M backend/tests/test_group1.py`，另新增 `edge/forward*.py` 与 2 个 SE-02C 测试文件；`AI_CONTEXT.md` / `PROJECT_STATE.md` / `DECISIONS.md` 亦改 |
| migration head 是否变化 | **否**。`b77c8033` 的 `backend/alembic/versions/` 仍为同样 9 个 revision、无新增文件 ⇒ head 仍 `20260913_0009` |
| 本窗口自身是否改动 production | **否**。`production_code_unchanged = True`；本 worktree HEAD 仍 `dd78a979`，`status --porcelain` 仅有 4 个 N01-8 新增文件 |

**分类与结论界定（按 Task §14：不自动重跑，交 Independent Review 决定）：**

1. 本次 12 h soak 的结论**只覆盖 Task Base `dd78a979`**，**不主张**可平移至当前 `main` `b77c8033`。
2. drift **命中 STOP 触发区（`g2/**`）**，且改动点正是本 soak 所覆盖的 `ScannerPipeline` ingest 路径（虽为 opt-in、无 recorder 时行为不变，但**未经本窗口验证**）⇒ 需 Independent Review 裁定 `no impact` / `targeted revalidation` / `full rerun` 三者之一。
3. **未做**：未 `rebase` / 未 `reset` / 未改写任何既有结论 / 未 merce 任何 candidate / 未触碰其它窗口。
4. **AC-24 证据口径的诚实说明**：`acceptance_criteria` 中 AC-24 的自动 `evidence` 字段是结构性的 `True`（并附 `baseline_drift` 对象），它**只证明起止两次读数都已记录**；AC-24 的实质满足来自**本节**（分类 + 结论界定），不是由代码自动判定的。

## 44. Acceptance Criteria 判定表（AC-01…AC-24，全部由 raw 自动计算）

| AC | 内容 | 结果 |
|---|---|---|
| AC-01 | task base frozen and recorded | ✅ True |
| AC-02 | formal active runtime ≥ 43200 s | ✅ True（44401.217） |
| AC-03 | one coherent timeline (single disposable DB, no stitching) | ✅ True |
| AC-04 | 4 planned phases complete | ✅ True |
| AC-05 | 3 true fresh-process restarts | ✅ True |
| AC-06 | 12 controlled reconnects materially covered | ✅ True |
| AC-07 | 6 controlled STALE→FRESH cycles materially covered | ✅ True |
| AC-08 | periodic reconciliation covers timeline, all PASS | ✅ True（24 checkpoint 全 ok） |
| AC-09 | no duplicate / fabricated economic facts | ✅ True |
| AC-10 | protection authority remains the durable Position snapshot | ✅ True |
| AC-11 | no worker exception requiring failure | ✅ True |
| AC-12 | DB/session lifecycle bounded | ✅ True |
| AC-13 | socket permanent delta ≤ 2 | ✅ True（net 0） |
| AC-14 | handle delta ≤ 16 | ✅ True（net −11） |
| AC-15 | frozen memory AND gate evaluated exactly as accepted | ✅ True（阈值 `64.0`/`5.0` 未改；`finding=false`，逐支见 §42.1） |
| AC-16 | retention saturation analysis complete | ✅ True |
| AC-17 | post-saturation observation window materially long enough | ✅ True（8974.771 s） |
| AC-18 | no unexplained synchronized resource growth | ✅ True |
| AC-19 | primary DB unchanged | ✅ True（`20260905_0004` 前后一致） |
| AC-20 | disposable DB residue = 0 | ✅ True |
| AC-21 | production code unchanged | ✅ True |
| AC-22 | raw evidence complete and internally consistent | ✅ True |
| AC-23 | start/end remote main recorded | ✅ True |
| AC-24 | any baseline drift classified | ✅ True（**drift=YES**，分类见 §43；自动 evidence 为结构性 `True`） |

**24 / 24 True。**

## 45. Evidence（路径 + hash；raw 不入 Git）

| 工件 | 大小 | sha256(前16) |
|---|---|---|
| `E:/Temp/n01-8/formal/acceptance_raw.json` | 27,812,382 | `6afa85dcf84bb765` |
| `.../n01-8-logs/phase_p1_open_raw.json` | 3,264,289 | `770348709f44999e` |
| `.../n01-8-logs/phase_p2_continue_raw.json` | 3,270,079 | `b97fab7faaa3538d` |
| `.../n01-8-logs/phase_p3_continue_raw.json` | 3,271,934 | `69ed2841f445ba31` |
| `.../n01-8-logs/phase_p4_close_raw.json` | 3,269,879 | `6264f7687f9b3427` |
| `.../n01-8-logs/*.progress.jsonl`（4 个） | ≈ 2.44 MB 各 | `4af29dee…`(p4) 等 |
| `E:/Temp/n01-8/formal/supervisor_status.json`、`acceptance_launch.json`、`detach_launch.json` | 小 | — |
| `E:/Temp/n01-8/probe4/acceptance_raw.json`（Phase D 复跑） | 615,331 | — |

Git 只提交 **摘要 + 路径 + hash**，不提交 raw（单文件 27.8 MB）。

## 46. Remaining（Phase E 之后）

1. 🚩 **最高优先级**：Baseline drift `dd78a979 → b77c8033` 命中 `g2/**` STOP 触发区 ⇒ 由 **Independent Review** 裁定 `no impact` / `targeted revalidation` / `full rerun`（§43）。本窗口**不自行**判定为 no impact，也**不**自动重跑。
2. 🚩 `N01-7-R01-RR-P2-01` 继续作为**未闭合 P2 watch item**保留（§42.3）；**禁止**写 memory resolved / memory is fine / no memory concern。
3. 收尾清理：`schtasks /delete` 删除 `n01-8-*` 任务；disposable DB 残留已实测 = 0；容器 `marketpulse-n01-8-pg` @ 5440 与本 worktree 的 gitignored `.env` 为未授权清理项，原样保留并登记。
4. **STOP**：不 merge `main`、不做 Human Accept、不宣布 N01 overall ACCEPTED、不宣布 N01-8 ACCEPTED。



