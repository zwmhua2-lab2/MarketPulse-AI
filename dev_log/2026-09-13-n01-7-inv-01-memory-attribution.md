# N01-7-INV-01｜Memory Attribution + Validation Gate Correction

> 批次：`N01-7-INV-01` —— **诊断 / 验证门修正窗口**，**非** N01-7 Acceptance。
> 分支：`n01-7-inv-01-memory-attribution`，自 `6b882c9709137300d7bc271e7ddf9172742dd435` 新建。
> 日期：2026-09-13
> Task Position：`N01-7 = BLOCKED / INVESTIGATION REQUIRED`；`N01-7-MEM-01 = RSS GROWTH OBSERVATION CONFIRMED / ROOT CAUSE UNRESOLVED`；`N01-7-VAL-01 = DEDUPE VALIDATION GATE DEFECT CONFIRMED`；F01 live witness = `PASS / LONG_LIVED_PROTECTION_WITNESSED`。
> 归因分类结论：见 §11。

本窗口**不改生产代码**（`backend/src/`、`backend/alembic/`、`backend/tests/` 全程 READ/DIAGNOSTIC ONLY），
不 merge `main`，不产生 PASS/FAIL 验收结论。

---

## 1. Repository Truth（CIP-01 / CIP-02 / CIP-03）

任务开始前从 Git 实时读取，不采信任务描述中的静态 SHA：

| 项目 | 实测值 | 来源 |
| --- | --- | --- |
| `origin/main` | `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` | `git ls-remote` |
| `origin/n01-7-2h-runtime-soak-after-f01` | `6b882c9709137300d7bc271e7ddf9172742dd435` | `git ls-remote` |
| 本窗口 Task Base／新建分支起点 | `6b882c97…` | `git rev-parse HEAD`（worktree `E:/Documents/MarketPulse-AI-n01-7-inv-01`） |
| 冻结的 N01-7 证据 worktree | `E:/Documents/MarketPulse-AI-n01-7-soak` @ `6b882c97…` | 只读，本窗口**未触碰** |
| Alembic head（任务自有实例） | `20260912_0006` | `alembic upgrade head` 实测 |
| Baseline drift | **无** | CIP-03：`origin/main` 与任务书导航一致 |
| Context drift | **无** | 已重读 `AGENTS.md` / `PROJECT_STATE.md` / `AI_CONTEXT.md` / N01-7 2h devlog |

主 worktree `E:/Documents/MarketPulse AI` HEAD = `d47313a`（`prb-01-product-requirements-baseline`），工作树干净。

**环境隔离**：本窗口新建任务专属 disposable 容器 `marketpulse-inv01-pg`
（`postgres:16-alpine` @ `127.0.0.1:5435`）；worktree 内 gitignored `.env` 指向 5435。
**共享主库 `127.0.0.1:5432/marketpulse` 全程未被迁移或写入**（容器 `marketpulse-postgres` Up 未受影响）。

---

## 2. 原始 2h Finding（本次任务的唯一首要问题）

来源：`dev_log/2026-09-13-n01-7-2h-runtime-soak.md`（**本窗口未改写该文件**）。
Run #2：`active 7200.369 s`、wall `7216.351 s`、`717` 样本、`61-of-62` checks 通过。

| 项目 | 值 |
| --- | --- |
| baseline RSS | `114.723 MB` |
| peak／final RSS | `134.508 MB`（**final == peak**） |
| 总增长 | **`+19.785 MB`（`+17.3%`）** |
| 整体斜率 | **`+9.066 MB/h`** |
| 8 窗口末值 | `116.371 → 117.875 → 121.141 → 124.477 → 126.816 → 128.992 → 131.863 → 134.508` |
| 窗口均值严格递增 | **`true`（8/8）** |
| 分段斜率 | `0–1800s +3.269` → `1800–3600s +12.826` → `3600–5400s +8.788` → `5400–7200s +8.710` MB/h |
| 归一化事件数 | `56741` |
| `connection_attempts` / `reconnects` | `1` / `0` |
| `stale_periods` | `[]` |

已排除项（原窗口结论）：非峰值读取伪影；生产 dedupe 结构（pipeline `_trade_dedupe` 于 ≈`4004 s` 触顶
`8192` 后停止增长，而 RSS 其后仍以 ≈`8.7 MB/h` 上升）；`InMemoryG2Repository` 累积 list（生产不走该路径）。

遗留三个 finding：
- **F-1（阻断）**：RSS 持续单调增长，约 `15–16 MB` 未归因 ⇒ 归因未完成。
- **F-2**：`dedupe_long_run_turnover` 被挂在从不饱和的 `EventRuntime._dedupe` 上，结构上不可观测。
- **F-3**：`RSS_GROWTH_ALERT_FRACTION = 0.25` 阈值过宽，不覆盖 §21 定性判据。

---

## 3. N01-7-VAL-01 修正（次目标）

**允许修改范围**：仅 `scripts/verify_n01_7_runtime_soak.py`（validation-only）。
**未修改任何已验收 pytest 文件**。

### 3.1 修正内容

`_dedupe_analysis()` 整体重写，不再要求 `EventRuntime._dedupe` 饱和，改为以
`ScannerPipeline._trade_dedupe` 为周转语义载体（`turnover_basis = "scanner_pipeline_trade_dedupe"`）。

| 结构 | 记录字段 |
| --- | --- |
| `runtime_dedupe` | `size` / `capacity` / `saturated` / `size_within_capacity_all_samples` |
| `trade_dedupe` | `capacity` / `size_first` / `size_last` / `size_max` / `size_min` / `reached_capacity` / `saturated_sample_count` / `saturation_elapsed_seconds` / `saturation_at` / `oldest_key_at_first_saturation` / `oldest_key_last` / `oldest_key_changes_while_saturated` / `trade_events_at_first_saturation` / `trade_events_after_first_saturation` / `size_within_capacity_all_samples` |

有效周转见证的三条件（AND）：

1. `trade_dedupe_reached_capacity` —— 达容量；
2. `trade_dedupe_fifo_head_changed_while_saturated` —— FIFO head 在饱和后变化；
3. `trade_dedupe_kept_accepting_after_saturation` —— 新 trade 事件持续被接受。

`EventRuntime._dedupe` 仍**保留**容量校验（`runtime_dedupe_within_capacity_all_samples`），
并新增独立检查 `dedupe_within_capacity_all_samples`（两者 AND），仅**不再**要求其饱和。

### 3.2 修正的强证据：在冻结的 2h 原始 717 样本上重算（只读）

对 `E:/Temp/n01-7-soak/acceptance_raw.json` 用修正后逻辑重跑，**未重跑任何运行时**：

| 项目 | 旧（缺陷）检查 | 修正后 |
| --- | --- | --- |
| `turnover_observed` | **`false`** | **`true`** |
| `dedupe_reached_capacity` | `false` | `true` |
| `dedupe_saturated_sample_count` | `0` | `318` |
| trade_dedupe 容量 | — | `8192` |
| trade_dedupe 首次饱和 | — | `4004.031 s` |
| 首饱和 oldest key | — | `["OKX","ETH-USDT","SPOT","874442166"]` |
| 末次 oldest key | — | `["OKX","BTC-USDT","SPOT","1056377417"]` |
| FIFO head 饱和后变化次数 | — | **`316`** |
| 首饱和后 trade 事件数 | — | **`6793`** |
| 全程 `size <= capacity` | — | `true` |
| `runtime_dedupe` | `4 → 4924`（容量 8192，**未饱和**） | 同（仅保留容量校验） |

⇒ §20 的实质语义在 2h 运行中**已被正面观测**，旧判据只是挂错了结构。

### 3.3 确定性自检（新增 `--self-check`）

合成样本（`_SELF_CHECK_CAPACITY = 4`）覆盖四种序列，断言判据真有牙齿：

| 合成序列 | 期望 | 实测 | 说明 |
| --- | --- | --- | --- |
| `saturated_and_rotating` | `True` | `True` | 达容量 + FIFO head 变化 + 持续接受 |
| `saturated_not_rotating` | `False` | `False` | **旧模型会答 True** 的回归守卫 |
| `never_saturated` | `False` | `False` | 结构上不可观测 |
| `saturated_no_further_trades` | `False` | `False` | 无新事件 ⇒ 不可证明周转 |

`python scripts/verify_n01_7_runtime_soak.py --self-check` → `exit 0`，`passed = true`。

### 3.4 静态门（validation-only 文件）

`ruff check` = 0 issues；`ruff format --check` = already formatted；`compileall` = exit 0。

---

## 4. 诊断拓扑与方法学边界

### 4.1 新增 harness

`scripts/verify_n01_7_memory_attribution.py`（validation-only，**诊断用**）。

- **强制复用**：`import verify_n01_6_runtime_smoke as n6`，不复制任何运行时实现；仅通过
  `n6.DATABASE_PREFIX` / `n6.OWNED_APPLICATION` / `n6.OBSERVER_APPLICATION` 重绑定所有权域
  （`marketpulse_n01_7_inv01_` / `marketpulse-n01-7-inv01-runtime`）。
- 声明边界：`is_n01_7_acceptance = false`、`counts_toward_7200s = false`、`counts_toward_n01_7 = false`；
  不产生 PASS/FAIL；不得被描述为修复。
- 检查点顺序严格分层：**轻量探针先**（memory / gc / structures / harness_retention / async / db ⇒ 干净 RSS 序列）
  → **tracemalloc 快照 + diff** → **对象普查**（重，且自报其 RSS 成本）。

### 4.2 工作负载（与已验收运行同核心）

real OKX public `BTC-USDT` + `ETH-USDT` SPOT（`trades` + `bbo-tbt`）× 生产
`ScannerPipeline` / `EventRuntime`（4 workers / queue 2048 / dedupe 8192）× task-owned disposable PostgreSQL ×
`LIVE_PAPER` / No Real AI / No Live Trading。网络：OKX **REST metadata 经本机用户代理
`http://127.0.0.1:10808`（仅进程内 env，不改系统代理）**，WebSocket **直连**。

### 4.3 ⚠️ 方法学边界：tracemalloc 是侵入性探针（本窗口实测发现）

这是本窗口最重要的方法学事实，**必须在读任何 RSS 斜率之前先声明**。

| 运行 | 时长 | `tracemalloc` | RSS 增长 | RSS 斜率 | `traced_current` 增长 |
| --- | --- | --- | --- | --- | --- |
| 原 2h soak（§2） | `7200 s` | **关闭** | `+19.785 MB` | **`+9.066 MB/h`** | 未测 |
| dry_run3 | `180 s` | 开启 | `+61.63 MB` | ≈`+1246 MB/h` | `+3.68 MB` |
| dry_run4 | `90 s` | 开启 | `+62.50 MB` | ≈`+2500 MB/h` | `+3.05 MB` |

⇒ 开启 tracemalloc 后 RSS 斜率比关闭时高 **两个数量级**，且两次干跑的 RSS 形状高度一致：
**前 ≈45 s 急剧上升 ≈`+27 MB`，随后快速衰减并趋于平台**（dry_run3 分段：`45→90 s +27.0`、
`90→135 s +7.1`、`135→180 s +5.2 MB`）。

对比原 2h soak 的形状：**首个 900 s 窗口增量仅 `+1.504 MB`（全程最小），随后稳定在
≈`+2.4–3.3 MB / 900 s`** —— 与「前段 warmup、后段平台」的形状**相反**。

**结论（方法学）**：

1. 本诊断的 **RSS / USS / private 斜率受 tracemalloc 前段 warmup 严重污染，不得作为归因依据**，
   也不得与 2h 的 `+9.066 MB/h` 直接相减。
2. 归因依据改为：`traced_current` 斜率、owner 分组 live bytes 斜率、定向对象计数、
   有界结构尺寸、以及**稳态段**（剔除前 300 s warmup）的形状。
3. `tracemalloc.get_tracemalloc_memory()`（probe 自身开销）已显式纳入每个检查点：
   dry_run4 实测 `4.94 → 9.10 MB`（`+4.16 MB`）—— **不足以**解释 `+62.5 MB` 的 RSS 缺口，
   故不能把全部缺口归给探针；剩余部分即本窗口要回答的问题。

### 4.4 测量纪律

- §12：60 分钟测量期间**未**执行任何 `gc.collect()` / 缓存清理 / allocator trim / dedupe 清空 / samples 清空。
- 仅在全部测量采集完成后执行**一次**诊断性 `gc.collect()`，记录 RSS / traced / 对象数 before-after，
  且在报告中**明确声明它不是修复**。
- §10：对象普查只用 `gc.get_objects()` + stdlib，**未引入任何外部依赖**。

---

## 5. 60 分钟诊断运行身份

| 项目 | 值 |
| --- | --- |
| 模式 | `DIAGNOSTIC`（`--seconds 3600`，`MAX_DIAGNOSTIC_ACTIVE_SECONDS = 3600`） |
| 检查点 | `5`（baseline + 4 个窗口四等分） |
| 采样间隔 | `10 s` |
| `tracemalloc` frames | `25` |
| disposable DB | `127.0.0.1:5435`（任务自有容器 `marketpulse-inv01-pg`） |
| 并发干扰核验 | 启动前实测 5435 仅有本窗口 `psql` 探针会话；**无**并发 pytest（早前 06:24:42 启动的全量 pytest 已结束） |

**干跑门（harness 就绪证据）**：`dry_run4` = `result: DIAGNOSTIC_OK`、`failures: []`、**18/18 checks 全 `true`**，
包含 `checkpoints_captured`、`baseline_captured_before_activity`、`active_duration_observed`、
`worker_exceptions_zero`、`no_harness_event_errors`。

> 干跑期间修复的自身缺陷（均为 harness 缺陷，非产品缺陷）：
> (a) baseline 检查点在 active 时钟启动前读取 `active_started_monotonic` ⇒ `KeyError`；
> (b) 误将 `g3.TradePlanManager._active` 当作 `harness.plans`（实为 `g4.planning.PlanManager`）的属性 ⇒ `AttributeError`；
> (c) `checkpoints_captured` 判据 off-by-one（`CHECKPOINT_COUNT - 1`），已修正为 `CHECKPOINT_COUNT`；
> (d) `# noqa: E402` 触发 `RUF100`（本项目未启用 E402）。

---

## 6. 运行身份（实测）

| 项目 | 值 |
| --- | --- |
| `result` | **`DIAGNOSTIC_OK`**（`failures = []`、`failure = None`） |
| checks | **18/18 全 `true`** |
| `active_duration_seconds` | `3641.73`（请求 `3600`） |
| `wall_clock_seconds` | `3667.197` |
| `started_at` / `finished_at` | `2026-09-12T22:34:56Z` / `2026-09-12T23:36:03Z` |
| 归一化事件 | `12365`（BTC trades `982` / bbos `3606`；ETH trades `929` / bbos `6848`） |
| 事件率 | `3.435 events/s`（对照：2h soak `7.881 events/s`） |
| `stale_periods` / `health_transitions` | `[]` / `1` |
| OKX `connection_attempts` / `reconnects` | **`26` / `25`**（对照：2h soak `1` / `0`） |
| `max_inter_arrival_gap_s` | BTC `47.413` / ETH `43.731` |
| 受控 entry | **成功**（BTC SPOT，real ask `77200.2` + slippage，`risk_gate.admitted = true`） |
| `leftover_n01_7_inv01_databases` | `0` |
| `harness_errors` / `sampler_errors` | `[]` / `[]` |
| shutdown | `queue 0` / `inflight 0` / `workers 0` / `worker_exceptions 0` / `errors []` |
| harness 脚本哈希（sha1） | `verify_n01_7_memory_attribution.py` = `b4bd7a00b068a9fab82a39892f7338a8f626c728`（`62731` B） |
| 哈希有效性 | 文件 mtime `06:30:55` **早于**运行启动 `06:34:56` ⇒ 运行证据与提交脚本一致 |
| 原始证据 | `E:/Temp/n01_7_inv_01/attribution_raw.json`（`803869` B）、`attribution_analysis.txt` |

> `active_duration` 比请求多 `41.73 s`：最后一个窗口检查点在 `3600 s` 触发后，循环才 break，之后依次执行
> trace 快照收尾、`rss_end_before_gc_probe` 采样。**这不是延长测量窗口**，最后的测量点仍在 `3600 s`。

### ⚠️ 本次运行的负载可比性警告

本次与 2h soak 的**环境不可比**：事件率 `0.436×`、且出现 **25 次 WebSocket 重连**（2h 为 0 次）。
`permessage_deflate.py` 与 `sslproto.py` 在 q1/q2/q3 持续出现在 top-delta 中（`+0.61/+1.84/+0.92 MB` 与
`+0.51/+1.52/+0.76 MB`），即重连的 Python 层痕迹。**任何跨运行比较都必须带着这个差异读。**

---

## 7. RSS / USS / private 趋势

| 检查点 | 时刻 | `rss_mb` | `uss_mb` | `private_mb` | `wset_mb` |
| --- | --- | --- | --- | --- | --- |
| baseline | `0 s` | `132.895` | `111.492` | `115.078` | `132.895` |
| window_quarter_1 | `900.353 s` | `156.176` | `132.641` | `138.637` | `156.176` |
| window_quarter_2 | `1800.339 s` | `183.875` | `160.656` | `167.113` | `183.875` |
| window_quarter_3 | `2700.524 s` | `194.910` | `171.070` | `180.203` | `194.910` |
| window_quarter_4 | `3600.665 s` | `198.715` | `174.637` | `185.262` | `198.715` |
| **总增长** | | **`+65.820`** | **`+63.145`** | **`+70.184`** | `+65.820` |

| 分段 | RSS 增量 | `traced_current` 增量 |
| --- | --- | --- |
| `0 → 900 s` | **`+23.281`** | `+4.105` |
| `900 → 1800 s` | **`+27.699`** | `+3.006` |
| `1800 → 2700 s` | `+11.035` | `+2.230` |
| `2700 → 3600 s` | **`+3.805`** | **`-0.400`** |

| 斜率（MB/h） | RSS | USS | private | `traced_current` | `traced_peak` | `tracemalloc_self` |
| --- | --- | --- | --- | --- | --- | --- |
| 全窗口 `0–3600 s` | `68.139` | `65.876` | `72.761` | `9.245` | `12.960` | `4.604` |
| 稳态 `≥900 s` | `55.453` | `54.553` | `61.177` | **`6.694`** | `12.392` | `3.251` |

**要点**：RSS/private/USS 三者同幅增长（`+65.8/+70.2/+63.1 MB`）⇒ 是真私有内存，不是共享页/映射伪影。
但 RSS 增量**逐段衰减**（`+23.3 → +27.7 → +11.0 → +3.8`），而 2h soak 是「起步最缓、随后稳定」
（`+1.504 → +3.266 → +3.336 → +2.339 → +2.176 → +2.871 → +2.645`）—— **两者形状相反**。
`traced_current` 最后一段为 **负值**，即 Python 活堆在窗口末段**已回落**。

---

## 8. tracemalloc 趋势与 owner 归因

| 检查点 | `traced_current_mb` | `traced_peak_mb` | `tracemalloc_self_mb` | `python_allocated_blocks` |
| --- | --- | --- | --- | --- |
| baseline | `8.165` | `10.926` | `4.941` | `849744` |
| q1 | `12.270` | `12.534` | `6.761` | `1275088` |
| q2 | `15.276` | `21.068` | `9.154` | `1398903` |
| q3 | `17.506` | `21.068` | `9.338` | `1419261` |
| q4 | `17.106` | `22.862` | `9.409` | `1428824` |
| 总增长 | `+8.941` | `+11.936` | `+4.468` | `+579080` |

### 8.1 owner 分组（live **Python** bytes，MB）

| 分组 | first | final | delta | slope/h | 4 等分均值递增 | 4 等分均值 |
| --- | --- | --- | --- | --- | --- | --- |
| `stdlib` | `0.599` | `5.473` | **`+4.874`** | `5.257` | **true** | `0.599 → 2.292 → 4.673 → 5.581` |
| `websocket_http_stack` | `2.398` | `4.188` | `+1.790` | `1.993` | **true** | `2.398 → 3.105 → 3.538 → 4.349` |
| `sqlalchemy_asyncpg` | `1.338` | `2.542` | `+1.203` | `0.980` | true | `1.338 → 2.504 → 2.524 → 2.545` |
| `validation_scripts` | `0.009` | `0.462` | `+0.453` | `0.474` | true | `0.009 → 0.053 → 0.202 → 0.397` |
| `production_backend_src` | `0.375` | `0.703` | **`+0.329`** | `0.319` | true | `0.375 → 0.548 → 0.574 → 0.696` |
| `interpreter_frozen` | `2.162` | `2.326` | `+0.163` | `0.130` | false | 平台 |
| `other_third_party` | `1.348` | `1.407` | `+0.059` | `0.036` | false | 平台 |
| `accepted_test_modules` | `0.004` | `0.005` | `+0.001` | `0.001` | false | 平台 |
| `unclassified` | `0.000` | `0.000` | `0.000` | `0.000` | false | — |
| **合计** | | | **`+8.872`** | | | |

**交叉验证**：owner 分组合计 `+8.872 MB` 与 `traced_current` 实测增量 `+8.941 MB`
**在 `0.07 MB` 内吻合** ⇒ 分类器无遗漏组，Python 活堆已被完整分解。

**`production_backend_src` 仅 `+0.329 MB / 3600 s = 0.319 MB/h`** —— 生产代码自身的 Python 活对象
增长在 60 分钟内可忽略。

---

## 9. Top allocation deltas（每个检查点相对前一检查点）

| 检查点 | #1 | #2 | #3 |
| --- | --- | --- | --- |
| q1 | `stdlib/copy.py` **`+0.757 MB`** `cnt+3682` | `websockets/extensions/permessage_deflate.py` `+0.614` `cnt+22` | `stdlib/asyncio/sslproto.py` `+0.505` `cnt+30` |
| q2 | `permessage_deflate.py` **`+1.841`** `cnt+66` | `sslproto.py` `+1.515` `cnt+90` | `stdlib/tracemalloc.py` `+0.864` `cnt+8188` |
| q3 | `permessage_deflate.py` `+0.922` `cnt+49` | `sslproto.py` `+0.757` `cnt+46` | `tracemalloc.py` `+0.598` `cnt+4688` |
| q4 | `validation_scripts/verify_n01_7_memory_attribution.py` `+0.124` `cnt+1470` | `tracemalloc.py` `+0.028` `cnt+396` | `stdlib/json/decoder.py` `+0.016` `cnt+340` |

- `copy.py`（q1）对应 §13 关注的 `rolling.copy()` / `deepcopy` 路径 —— 但它是**流量**，**未**形成活对象存量
  （`production_backend_src` 仅 `+0.329 MB`，`g2/runtime.py` 相关 delta 仅 KB 级）。
- `permessage_deflate.py` / `sslproto.py` 反复出现在 q1–q3 ⇒ **25 次 WebSocket 重连**的痕迹。
- `tracemalloc.py` 的 `cnt+8188/4688/396` ⇒ **探针自身**。
- q4 三个 top 项合计仅 `~0.17 MB`，且 `traced_current` 该段为**负** ⇒ 窗口末段无实质新增。

---

## 10. Live object counts（同一检查点定向普查）

| 类型 | t=0 | t=900 | t=1800 | t=2700 | t=3600 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| `NormalizedTrade` | 0 | 480 | 480 | 240 | 240 | **有界** |
| `NormalizedBookTicker` | 0 | 120 | 120 | 61 | 61 | **有界** |
| `FeatureSnapshot` | 0 | 6 | 5 | 5 | 5 | **有界** |
| `MarketEvent` | 0 | 6 | 7 | 7 | 6 | **有界** |
| `SymbolStateRecord` | 0 | 6 | 6 | 6 | 6 | **有界** |
| `TradePlan` | 0 | 0 | 0 | 0 | 0 | 无累积 |
| `PositionRecord` | 0 | 0 | 0 | 0 | 0 | 无累积 |
| `Task` | 5 | 8 | 10 | 9 | 11 | 有界（波动） |
| `Future` | 5 | 15 | 18 | 17 | 21 | 有界（波动） |
| `TimerHandle` | 0 | 5 | 7 | 6 | 8 | 有界（波动） |
| `Lock` | 6 | 8 | 8 | 8 | 8 | **恒定** |
| `dict` | 24002 | 26672 | 26935 | 26890 | 27118 | 有界 |
| `list` | 6551 | 7691 | 7819 | 7924 | 8034 | 有界 |
| `set` | 4529 | 5433 | 5440 | 5140 | 5140 | 有界 |
| **`tuple`** | **82190** | **169968** | **210603** | **228758** | **236954** | 增长 ⇒ **探针伪影（见 §13）** |
| `deque` | 353 | 363 | 365 | 360 | 362 | 有界 |
| `coroutine` | 10 | 26 | 28 | 26 | 22 | 有界 |
| `generator` / `async_generator` | 2 / 0 | 5 / 3 | 6 / 4 | 6 / 4 | 7 / 5 | 有界 |

**关键**：**生产域类型全部有界**（无一单调增长）。唯一显著单调增长的类别是 `tuple`，
而 §13 的实验证明它来自 `tracemalloc` 探针。

---

## 11. Rolling-state 与有界结构尺寸

| 结构 | t=0 | t=900 | t=1800 | t=2700 | t=3600 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| `rolling_state_cardinality` | 0 | 2 | 2 | 2 | 2 | **恒定** |
| `rolling_states_estimated_bytes` | 64 | 378 | 378 | 378 | 378 | **恒定** |
| `rolling_states[BTC/ETH].trades` | — | 120 | 120 | 120 | 120 | **满 maxlen 120** |
| `rolling_states[BTC/ETH].books` | — | 30 | 30 | 30 | 30 | **满 maxlen 30** |
| `rolling_states[BTC/ETH].klines` | — | 0 | 0 | 0 | 0 | 空 |
| `trade_dedupe` size | 0 | 557 | 1183 | 1572 | 1911 | 有界（容量 8192，未饱和） |
| `runtime_dedupe` size | 0 | 350 | 665 | 889 | 1044 | 有界（容量 8192） |
| `runtime_inflight` | 0 | 0 | 0 | 0 | 0 | **恒定 0** |
| `runtime_locks` | 0 | 2 | 2 | 2 | 2 | **恒定** |
| `runtime_queue_size` | 0 | 0 | 0 | 0 | 0 | **恒定 0** |
| `worker_exceptions` | 0 | 0 | 0 | 0 | 0 | **恒定 0** |
| `pipeline_lifecycle_active_keys` | 0 | 5 | 5 | 6 | 4 | 有界 |
| `state_manager_records` | 0 | 2 | 2 | 2 | 2 | **恒定** |
| `harness_meaningful_gate_last_keys` | 0 | 0 | 0 | 0 | 0 | **恒定 0** |
| `num_handles` | 186 | 188 | 188 | 188 | 188 | 有界 |
| `num_threads` | 8 | 2 | 2 | 2 | 2 | **下降**（线程池收缩） |

**§13 结论（rolling copy churn）**：`ScannerPipeline.ingest → rolling.copy() → deepcopy(_states) → ingest → commit`
路径在 60 分钟内执行约 `12365` 次（每归一化事件一次），但：
- rolling 状态基数**恒定 2**、估算字节**恒定 378 B**；
- 三个 deque 全部**满且不增长**（120/120、30/30、0）；
- `production_backend_src` live bytes 仅 `+0.329 MB`，`g2/runtime.py` 相关 top-delta 仅 KB 级。

⇒ 该路径产生的是**高频分配/释放流量，不是活对象累积**。按 §13 的禁令，**不**据此推断泄漏；
其可能的**分配器压力**作用见 §12/§14 的分解。

---

## 12. Async / DB / 网络计数

| 指标 | t=0 | t=900 | t=1800 | t=2700 | t=3600 | 判定 |
| --- | --- | --- | --- | --- | --- | --- |
| `task_count` | 5 | 8 | 8 | 8 | 8 | **有界** |
| `pg_owned_client_sessions` | 1 | 1 | 1 | 1 | 1 | **恒定** |
| `pg_other_client_sessions` | 0 | 0 | 0 | 0 | 0 | **恒定 0（无外来写者）** |
| `pg_idle_in_transaction` | 0 | 0 | 0 | 1 | 0 | 无累积 |
| `runtime_engine_pool.checkedout` | 0 | 1 | 1 | 1 | 1 | **恒定** |
| `runtime_engine_pool.size` | 6 | 6 | 6 | 6 | 6 | **恒定** |
| pool `type` | `AsyncAdaptedQueuePool` | 同 | 同 | 同 | 同 | — |

末检查点 task 名单：`Task-11`、`Task-46584`、`g2-event-worker-0..3`、`n01-7-inv-01-market-consumer`、
`n01-7-inv-01-memory-sampler`。匿名 `Task-NNNNN` 每检查点更换（harness 的 `_db_activity` 产生），
计数恒为 1，**不累积**。

⇒ **无 task / Future / asyncpg / SQLAlchemy session / pool 的单调增长**；DB 侧完全有界。
网络侧**无** net count 维度可用，唯一网络相关增长是 `websocket_http_stack` `+1.790 MB`（§8.1）。

### 12.1 Harness 保留量（§11 要求，逐检查点实测）

| 项 | t=0 | t=900 | t=1800 | t=2700 | t=3600 |
| --- | --- | --- | --- | --- | --- |
| `samples_len` / 估算字节 | 0 / 56 | 1 / 1776 | 1 / 1776 | 1 / 1776 | 1 / 1776 |
| `rss_series_len` / 估算字节 | 0 / 56 | 90 / 45612 | 177 / 89802 | 263 / 133174 | 348 / 176176 |
| `checkpoints_len` / 估算字节 | 0 / 56 | 1 / 4084 | 2 / 8088 | 3 / 12092 | 4 / 16096 |
| `feed_errors_len` | 0 | 0 | 0 | 0 | 0 |
| `feed_stale_periods_len` | 0 | 0 | 0 | 0 | 0 |
| 其他 feed 容器 | 0 | ≤2 | ≤2 | ≤2 | ≤2 |

**harness 保留结构合计 `≈ 0.20 MB`**（`rss_series` `0.176` + `checkpoints` `0.016` + `samples` `0.002`）
⇒ 在 `65.82 MB` 的 RSS 增长中占 `0.3%`。**validation 保留结构不是增长主体。**

---

## 13. ⚠️ 探针自身开销的量化（本窗口新增的关键证据）

RSS 增长的主体**不在** Python 活堆。为判定剩余部分里有多少属于**探针**，本窗口做了两项独立量化：

### 13.1 `tracemalloc` 自报开销（每检查点）

| 检查点 | `tracemalloc_self_mb` |
| --- | --- |
| baseline | `4.941` |
| q1 | `6.761` |
| q2 | `9.154` |
| q3 | `9.338` |
| q4 | `9.409` |

⇒ 探针 C 层追踪表 `+4.468 MB`。**不足以**解释 `+65.82 MB`。

### 13.2 单个被持有的 `Snapshot` 的真实成本（独立最小实验）

`E:/Temp/n01_7_inv_01/snapshot_cost_probe.py`：`tracemalloc.start(25)` → 造 2000 次 JSON 分配 →
`take_snapshot()` → 前后定向普查。

| 指标 | 快照前 | 快照后（被持有） | 增量 |
| --- | --- | --- | --- |
| `tuple` 对象数 | 1431 | 17585 | **+16154** |
| 全部 gc 跟踪对象 | — | — | **+16158** |
| `traced_current` | `0.006 MB` | `0.915 MB` | **+0.909 MB** |
| `tracemalloc_self` | `0.004 MB` | `0.746 MB` | **+0.742 MB** |
| `Snapshot` 实例 | 0 | 1 | +1 |

（`Frame` / `Trace` / `Traceback` 的 `type().__name__` 计数为 `0` ⇒ 其帧序列在普查中落入 `tuple` 名类。）

**推论（有实验支撑）**：
`_capture_checkpoint` 的顺序是 memory → gc → structures → retention → async → db → **`take_snapshot()`** → **census**，
且 `snapshot` 局部变量在 census 时**仍存活**（并被 `ctx["latest_snapshot"]` 持有）。因此：
`tracked_objects` 与 `tuple` 的**阶梯式增长（每次检查点约 +3.8 万）是探针伪影**，不是 Python 活对象泄漏。
旁证：`gc probe` 时刻（无检查点构建活动）的 `tracked_objects` 为 `268872`，**低于** q4 的 `372579` 达 `103707`。

### 13.3 `object_census` 自身的 RSS 成本

| 检查点 | census 耗时 (s) | census RSS delta (MB) |
| --- | --- | --- |
| baseline | 2.275 | `+0.820` |
| q1 | 7.444 | `+0.082` |
| q2 | 7.262 | `+2.039` |
| q3 | 8.826 | `+2.024` |
| q4 | 8.585 | `+2.816` |
| **合计** | **34.390** | **`+7.781`** |

⇒ 探针（census 的大临时列表，未被 OS 归还）再贡献 `+7.781 MB`。

### 13.4 探针已识别总量

| 成分 | MB |
| --- | --- |
| `tracemalloc_self`（C 追踪表） | `+4.468` |
| 被持有 `Snapshot` 的 traced 部分（5 次重建，末次驻留；按实验 `0.909 MB/次` 上界估算） | ≤`+4.6` |
| `object_census` 累计 RSS 影响 | `+7.781` |
| **探针已识别小计** | **≈`+17`**（占 RSS 增长 `≈26%`） |

其余 `≈48–52 MB` 属 allocator 高水位/碎片与 native 层（`asyncpg` C 缓冲、OpenSSL、zlib、
25 次重连的 native 资源），**无**任何一项能被证明为**生产代码的活对象累积**。

---

## 14. Post-run GC probe（仅诊断，**不是修复**）

在**全部测量采集完成后**执行**一次** `gc.collect()`：

| 指标 | before | after | delta |
| --- | --- | --- | --- |
| RSS | `208.000 MB` | `194.102 MB` | **`-13.898 MB`** |
| `traced_current` | `13765962 B` | `11220864 B` | `-2545098 B` |
| `tracked_objects` | `268872` | `260630` | `-8242` |
| `gc_collected` | — | `198` | — |

⇒ 有 `13.90 MB` 是**可回收的 Python 垃圾**（含探针构建物）。**该探针不改变任何生产行为，
不得被描述为修复。** 测量期间（`0–3600 s`）**未**执行任何 `gc.collect()` / 清缓存 / trim allocator /
清空 dedupe 或 samples。

---

## 15. Attribution Classification

### **分类 = `C`｜`ALLOCATOR_OR_NATIVE_RETENTION_LIKELY`**

**判据（§15 C）**：RSS / private 实质增长，而 Python traced live heap 与 live 对象数**实质有界**。

| 判据 | 实测 | 结论 |
| --- | --- | --- |
| RSS / private 增长 | RSS `+65.82 MB`、private `+70.18 MB`、USS `+63.14 MB` | ✅ |
| Python traced live heap 有界 | 稳态段（`2700→3600 s`）`traced_current` **`-0.400 MB`** | ✅ |
| live 对象数有界 | 生产域类型（`NormalizedTrade`/`NormalizedBookTicker`/`FeatureSnapshot`/`MarketEvent`/`SymbolStateRecord`/`TradePlan`/`PositionRecord`）**全部有界**；`dict`/`list`/`set`/`deque`/`Lock` 有界 | ✅ |

### 被排除的类别（附证据）

| 类别 | 排除依据 |
| --- | --- |
| **A** `PYTHON_LIVE_HEAP_GROWTH_CONFIRMED` | (a) `traced_current` 与 RSS **不同步**（`+8.94` vs `+65.82`，仅 `13.6%`），且稳态段为**负**；(b) **无**稳定增长的生产 allocation owner（`production_backend_src` 仅 `+0.329 MB/h = 0.319`）或对象族（生产域类型全有界）。A 的两项必要条件均不成立。 |
| **B** `HARNESS_RETENTION_CONFIRMED`（作为主因） | harness 保留结构合计 `≈0.20 MB`（`0.3%`）；`validation_scripts` live bytes `+0.453 MB`。**不构成主因**（探针注入另计，见 §13.4，且不是「保留结构」）。 |
| **D** `PRODUCTION_NATIVE_ACCUMULATION_CONFIRMED` | 无任何被证实的 production / native owner。唯一 native 嫌疑是 25 次 WS 重连，但 **2h soak 在 `reconnects = 0` 时仍有 `+19.785 MB` 增长** ⇒ 重连**不能**作为该增长的成因。 |

### 必须随分类一并声明的边界

1. **`C` 不等同于 Python live-object leak**，也**不**表示已证实生产存在 native 泄漏。
2. 本次 RSS 斜率（`+68.139 MB/h`）**不可**与 2h soak 的 `+9.066 MB/h` 比较：探针介入后斜率抬升
   **两个数量级**（干跑复现：`+62.50 MB / 90 s ≈ +2500 MB/h` 对无探针 2h 的 `+9.066 MB/h`）。
3. 本次**未能复现** 2h 的「缓慢起步 + 稳定线性」形状 ⇒ **对 `N01-7-MEM-01` 的具体载荷，
   归因仍不完整**。本次能确证的是：**该载荷不属于 Python 活对象累积**（A 被排除）。
4. 因此本窗口的 `C` 适用于「本诊断窗口内观测到的 RSS/private 增长机制」，并**据此排除 A**。
   对 2h 现象的最终归因需要一次**不带 tracemalloc 探针**的对照运行（§16 Next action）。
5. §16 处置：`C` ⇒ **报送精确证据给 Reviewer 决定**，本窗口**不**修改任何生产代码。

### 与自动建议的差异（须显式记录）

harness 的 `classification_suggestion` 给出 `E_INCONCLUSIVE`，`inputs` 为
`rss_slope = 68.139`、`traced_current_slope = 9.245`、`tracked_objects_slope = 154562.8`、
`production_owner_slope = 0.319`、`validation_owner_slope = 0.474`。
自动判据等于「RSS 增长 + 生产与 validation owner 组均『有界』⇒ 无法归因」，**与本窗口的人工判定
（`C`）不同**：人工判定使用自动判据未覆盖的证据（稳态段斜率转负、生产域**对象计数**全有界、
探针自报与实验量化、GC probe）。按 harness 自身 note，自动建议**仅供参考**，须人工确认。

> **harness 缺陷记录（不修，保持运行证据可复现）**：`_suggest_classification` 在 `E` 分支未填充
> `rationale` 文本 ⇒ `rationale == []`。仅影响报告可读性，不影响任何测量值。若需补全，应在
> **下一次**运行前修改，届时必须重新绑定脚本哈希。

---

## 16. Evidence / Remaining / Next action

### 16.1 证据清单

| 路径 | 内容 |
| --- | --- |
| `E:/Temp/n01_7_inv_01/attribution_raw.json` | 60 分钟诊断完整原始报告（`803869` B） |
| `E:/Temp/n01_7_inv_01/attribution_analysis.txt` | 分段斜率 / owner / 对象普查 / GC probe 分析输出 |
| `E:/Temp/n01_7_inv_01/snapshot_cost_probe.py` + `snapshot_cost.txt` | 单个 `Snapshot` 成本实验（§13.2） |
| `E:/Temp/n01_7_inv_01/dry_run{1..4}_*.json/txt` | harness 干跑门（`dry_run4` = `DIAGNOSTIC_OK`，18/18） |
| `E:/Temp/n01_7_inv_01/classifier_check_out.txt` / `owner_classifier_check.json` | owner 分类器自检（`all_passed = true`） |
| `E:/Temp/n01_7_inv_01/introspect_out*.txt` / `introspection.json` | 25 条属性路径内省（`missing: []`） |
| `E:/Temp/n01_7_inv_01/prelaunch_check*.txt` | 启动前 PG/容器/并发 pytest 核验 |
| `--self-check` stdout（本文件 §3.3） | 4 个合成序列的确定性自检 |
| 2h 原始样本重算（§3.2） | `turnover_observed` `false → true` |

### 16.2 Remaining / Blockers

| 项目 | 状态 |
| --- | --- |
| `N01-7` | **`BLOCKED / INVESTIGATION REQUIRED`**（未写 VALIDATED） |
| `N01-7-MEM-01` | 观测已确认；**A 类机制被排除**；载荷归因**不完整**（本次未复现 2h 形状）⇒ 需无探针对照 |
| `N01-7-VAL-01` | **修正完成 + 自检通过 + 2h 样本重算确认**，等待 Acceptance |
| F-3（`RSS_GROWTH_ALERT_FRACTION = 0.25` 过宽） | 未处理（属另一批次 Scope） |
| harness `rationale == []` 缺陷 | 已记录，**不修**（保持运行证据可复现） |

### 16.3 Next action（建议给 Reviewer）

1. 复核本窗口的 `C` 分类与排除 A 的证据链。
2. 若需完成 `N01-7-MEM-01` 归因：**另开一个窗口**，用**不启用 `tracemalloc`** 的 60–120 分钟运行
   复现 2h 的 RSS 形状（本次已证明探针会改变被观测现象），并在此复现基础上再决定是否需要
   allocator 级证据（例如 `sys.getallocatedblocks()` / native 工具）。
3. `N01-7-VAL-01` 的修正版 `verify_n01_7_runtime_soak.py` 可与本窗口一并进入独立复审。
4. **不**依据本窗口推进 `main`；`N01-8`、Integrated Runtime Host 维持 `NOT STARTED`；
   `N01 overall = NOT ACCEPTED`。

