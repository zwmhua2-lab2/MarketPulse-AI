# N01-7 — 2-hour Medium Runtime Soak（结果：BLOCKED / FIX REQUIRED）

- Date: 2026-09-13
- Task: N01-7｜2-hour Medium Runtime Soak（validation-only）
- Repository: `zwmhua2-lab2/MarketPulse-AI`
- Branch: `n01-7-2h-runtime-soak-after-f01`（base `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`）
- Worktree: `E:\Documents\MarketPulse-AI-n01-7-soak`
- **Status: `N01-7 = BLOCKED / FIX REQUIRED`**（**未**自行 Acceptance；**未** merge `main`；**未**启动 N01-8）

---

## 1. Task / Scope / Out of Scope

**Goal**：用真实 OKX 公共行情（BTC-USDT + ETH-USDT SPOT）+ 独立 disposable PostgreSQL，
让**已验收的生产运行时组件**在验证 harness 内**单次连续**运行 ≥7200 s，并验证市场数据连续性、
EventRuntime 生命周期稳定、队列/worker/inflight 健康、dedupe 长时周转、PostgreSQL 会话生命周期、
内存/资源长时行为、Paper 安全连续性、持久保护快照跨 TradePlan TTL 存活、reconciliation / 经济
不变量、受控关停与清理；期间通过**正式路径**完成一笔受控 `LIVE_PAPER` SPOT LONG 生命周期。

**允许修改（本任务新增物）**：
- 新增 `scripts/verify_n01_7_runtime_soak.py`（validation-only 薄层）
- 新增本 devlog；最小同步 `PROJECT_STATE.md` / `AI_CONTEXT.md`

**Out of Scope（明确不做）**：不是 Integrated Runtime Host；不是 FastAPI 7x24；不是 daemon/部署；
不降低 scanner 阈值；不接入 AI；不触碰 Live Trading / OKX 私有端点 / API key / 真实资金；
不改 production code / schema / migration / 已验收测试。

---

## 2. Repository Truth（CIP-01 / 02 / 03）

| 项 | 实测值 | 来源 |
|---|---|---|
| `origin/main`（远端真值） | `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` | Bash `git ls-remote` |
| 交叉核验 | 同上 | `gh api repos/zwmhua2-lab2/MarketPulse-AI/git/ref/heads/main` |
| 本地 `main` / 开工 HEAD | 同上 | `git rev-parse` |
| SHA Delta | **无**（== 任务书导航 SHA） | —— |
| 陈旧分支 `n01-7-2h-runtime-soak`（`af81414`） | **未删、未 reset、未复用** | 只读确认 |

无 Runtime / G3 / G4 / migration 漂移 ⇒ 无 `STOP / CONTEXT DRIFT`。

> 说明：任务书建议 worktree 为 `E:\Documents\MarketPulse-AI-n01-7`，该路径存在一个**更早被放弃、
> 未在 git 注册**的 N01-7 检出（含基于 `af81414` 的 1296 行黑盒包装脚本）。按「不覆盖不明工作」
> 原则另开新路径 `E:\Documents\MarketPulse-AI-n01-7-soak`，原目录保持原样。

---

## 3. Harness 拓扑（复用已验收 N01-6 harness）

`scripts/verify_n01_7_runtime_soak.py`（1556 行）**导入**已验收 `scripts/verify_n01_6_runtime_smoke.py`
（`import verify_n01_6_runtime_smoke as n6`），**未复制、未修改**其 ~1300 行。

**Harness 完整性**：`git hash-object scripts/verify_n01_6_runtime_smoke.py`
= `94853dd747d0e800397b5f6fd743b82e42944e01`（与已验收版本**逐字节一致**，全程未变）。

```
OKXLiveProvider(public WS, 直连)                       # 真实，无 key
   │  NormalizedTrade / NormalizedBookTicker           # BTC-USDT + ETH-USDT SPOT
   ▼
ScannerPipeline ──▶ OpportunityScanner(accepted default ScannerConfig)
   ▼
EventRuntime(accepted defaults: 4 workers / queue 2048 / dedupe 8192 / worker_exception_cap 128)
   ▼
PostgresG2Repository ──▶ 真实 disposable PostgreSQL（任务专属容器）
   │
   └─ SafetyRuntime ─▶ PositionProtectionService / SystemRiskGate / PaperExecutionService
```

薄层新增职责仅限于：2h 时长控制、8×15min 进度窗口采集、N01-7 专属分析、F01 长寿命保护见证、
最终验收报告。**未**降低任何阈值、**未**覆盖任何已验收常量。

---

## 4. 环境与隔离（§7 / §8 / §9）

| 项 | 值 |
|---|---|
| Run mode | `LIVE_PAPER` |
| 品种 / 类型 | BTC-USDT、ETH-USDT，`SPOT` |
| OKX 端点 | `GET /api/v5/public/instruments`、`WS /ws/v5/public`（`trades`×{BTC,ETH} + `bbo-tbt`×{BTC,ETH}） |
| WS URL | `wss://ws.okx.com:8443/ws/v5/public`（**直连**） |
| API key / 私有端点 | `false` / `false`（**未使用**） |
| Disposable PostgreSQL | 任务专属容器 `marketpulse-n01-7-pg`（`postgres:16-alpine`）@ `127.0.0.1:5434` |
| 库名 | `marketpulse_n01_7_557c5788d42f`（前缀 `marketpulse_n01_7_` + uuid12） |
| 迁移 | `alembic upgrade head` → `20260912_0006`（= 已验收唯一的 migration head） |
| 归属标识 | owned `application_name=marketpulse-n01-7-runtime`；observer `marketpulse-n01-7-observer` |
| Runtime DSN | 经 **gitignored `.env`** 锚定到 5434（实测 `runtime_dsn` = `127.0.0.1:5434/marketpulse`） |

**两项 validation-only 环境适配（已获用户明确批准，非产品改动）**：
1. **OKX REST 传输**：沙箱内 OKX REST 直连已失效；**仅**那一次 metadata 查询经本机既有用户代理
   `http://127.0.0.1:10808`（`elapsed 3.448 s`）；公共 WebSocket **保持直连**。**未**写入任何系统代理设置。
2. **PG 拓扑**：任务书 §8（任务专属 disposable PG，绝不动 5432）与 §9（记录共享主库状态）在字面上
   互相冲突（N01-6 harness 的 observer engine 会连 `Settings().database_url`）。经用户选择
   **独立容器**，使 runtime DSN 永不等于共享主库。

---

## 5. Run #1 中止 —— 验证侧 harness 缺陷（§26-B）

第一次正式运行在 **1928.658 s（≈32 min）** 处中止，`active_duration_seconds=0.0`：

```
mode: ACCEPTANCE   result: FAIL
in-scenario failure:
  AttributeError: '_EntryPlanView' object has no attribute 'side'
  verify_n01_7_runtime_soak.py:508  ->  g3/service.py:627 (生产路径读 plan.side)
```

**根因（验证侧，非产品缺陷）**：薄层的 `_EntryPlanView` 只暴露了「witness 想当然需要的字段」，
缺 `side`；而生产 `execute` 路径会读 `plan.side`（`g3/service.py:627`）、`plan.entry_zone`、
`plan.order_type` ⇒ 属**结构性**不完整。崩溃帧 = 508 ⇒ 该帧之前的 418–507 行（position 读取、
`load_valid_long_active_plan`、`_db_state`、`protection.evaluate`、`risk_gate.check`）**全部已成功执行**。

**正面副产物**：plan **确实真实过期**（`plan_expires_at 18:23:25.758573Z`、
`expiry_crossed_elapsed 1861.455 s`），崩溃时已有 `post_expiry_position_samples=7`
/ `post_expiry_samples_with_protection=7` —— F01 现象本身正在被正确观察。

**修复（validation-only，Production Code Frozen 未破）**：
1. **删除 `_EntryPlanView`**，改用生产域加载器 `load_active_plan()`（`g4/planning.py:254`，**不带 TTL 过滤**）
   取回**真实 `TradePlan`** ⇒ 由构造消除字段缺失类缺陷。
2. 新增 `PLAN_FIELDS_READ_BY_EXECUTION` **具名 fail-fast 守卫** + `WITNESS_HARNESS_ERROR` 分类
   ⇒ 同类问题显式报错，不再把整个 2h 运行丢弃。
3. **健全性修正**：`MARKET_PATH_F01_KEYS` 的「市场路径豁免」现**仅在
   `f01_position_still_open_after_expiry is not True`**（行情提前平仓）时生效。修正前「持仓仍在
   但保护快照丢失」会被误判为 `VALIDATION INCOMPLETE DUE TO MARKET PATH` 而漏掉真实产品缺陷。

**修复的验证依据（如实标注强度）**：
- 结构性（已实测）：`TradePlan.model_fields` 20 字段完整包含执行路径所需 5 项
  （`plan_id`/`instrument_id`/`side`/`entry_zone`/`order_type`）。
- 等价性：修复后第 508 行调用形态与**每次运行都成功**的 `_controlled_entry → execute_intent(real_plan)` 一致。
- **未做**（如实声明）：未对「过期 plan → 闸门 `PLAN_EXPIRED`」做独立端到端预跑 —— 任何 ≤300 s 的
  PROBE 都无法复现（plan TTL 固定 30 min 且不可修改已验收 harness）。该行为由 Run #2 本身作为端到端验证。

Run #1 产物已归档为 `aborted_run1_{raw.json,stdout.txt,launch.txt}`（保留为 harness 缺陷证据）。
按 §26-B，修复后正式 7200 s **从零重启** ⇒ Run #2 为本任务正式运行。

---

## 6. Run #2 Run Identity

| 项 | 值 |
|---|---|
| 类别 | **ACCEPTANCE**（`--seconds 7200 --sample-interval 10`） |
| 进程启动 | `2026-09-12T17:52:15.254553+00:00` |
| active 起点 / 终点 | `17:52:25.698190` / `19:52:26.066734` |
| **active 连续运行** | **`7200.369 s`**（≥7200 ✔，**单次连续、无重启、无拼接**） |
| wall clock | `7216.351 s` |
| 采样 | `717` 样本（10 s 间隔），8 窗口各 `89–91` 样本（覆盖完整） |
| 残留 | `leftover_n01_7_databases = 0` |

---

## 7. 市场数据连续性（§12）

| 项 | BTC-USDT | ETH-USDT |
|---|---|---|
| trades | `6389` | `8774` |
| bbos | `17626` | `23952` |
| first / last received | `17:52:20.990` / `19:52:25.987` | `17:52:20.919` / `19:52:26.034` |
| 最大到达间隔 | `14.160 s` | `7.887 s` |

- 归一化事件总数 **`56741`**；`connection_attempts=1`、`reconnects=0`（**单次建连全程无重连**）。
- `stale_periods = []`、`max_stale_period_seconds = 0.0`；`health_transitions` 仅 1 次
  `null → HEALTHY`（ETH 接通瞬间）。
- 8 个窗口 `btc_fresh_all` / `eth_fresh_all` **全为 True**，`btc_data_quality` 全程 `FRESH`。
- 每窗口 trades/bbos 增量全部 > 0 ⇒ **8/8 窗口市场数据连续**（`market_data_continuity_all_windows = true`）。
- 生产 fresh TTL `5.0 s`（**未降低**）；存在 `max_inter_arrival_gap 14.16 s` 但未触发 STALE 判定
  （TTL 由 harness 侧 freshness 观察窗口计算，非单事件间隔）。
- **未**做任何人为断连 / 丢包 / 注入 stale / 强制重连。

---

## 8. 8 × 15 分钟进度窗口（§11）

| w | elapsed first→last | btcTr | btcBBO | ethTr | ethBBO | qMax | ifMax | ddSz | rssLast | pgOwnMax | posLast | exp | prot | sys | inc | recon | btcMaxAge |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | 0.06→895.5 | 1077 | 2379 | 687 | 2633 | 0 | 1 | 430 | 116.371 | 2 | 0.0012949… | False | True | RUNNING | 0 | True | 3.649 |
| 2 | 905.5→1790.8 | 974 | 2456 | 1208 | 3020 | 0 | 1 | 1148 | 117.875 | 2 | 0.0012949… | False | True | RUNNING | 0 | True | 4.355 |
| 3 | 1800.8→2696.2 | 663 | 2317 | 1034 | 2998 | 0 | 1 | 1742 | 121.141 | 3 | 0.0012949… | **True** | True | RUNNING | 0 | True | 7.945 |
| 4 | 2706.3→3591.5 | 496 | 1743 | 697 | 2508 | 0 | 1 | 2294 | 124.477 | 3 | 0.0012949… | True | True | RUNNING | 0 | True | 6.601 |
| 5 | 3601.6→4496.9 | 744 | 1982 | 1803 | 3833 | 0 | 1 | 2977 | 126.816 | 3 | 0.0012949… | True | True | RUNNING | 0 | True | 8.528 |
| 6 | 4507.0→5392.2 | 700 | 1783 | 1206 | 2853 | 0 | 1 | 3616 | 128.992 | 3 | 0.0012949… | True | True | RUNNING | 0 | True | 6.964 |
| 7 | 5402.2→6297.7 | 898 | 2196 | 782 | 2477 | 0 | 1 | 4191 | 131.863 | 3 | 0.0012949… | True | True | RUNNING | 0 | True | 7.048 |
| 8 | 6307.7→7193.0 | 774 | 2563 | 1149 | 3362 | 0 | 1→0 | 4924 | 134.508 | 3 | 0.0012949… | True | True | RUNNING | 0 | (None) | 2.725 |

> 窗口 8 的 `recon = None` 属正常：只在 7 个窗口边界执行 reconcile，最终 reconcile 在循环外单列
> （见 §13），`reconciliation_ok_all_windows` 将其视为 OK。
> 窗口 8 `ifMax=0` 属瞬时计数未被 10 s 采样命中（全程 `inflight_high_water = 1`）。

---

## 9. Runtime 健康 / 队列 / worker（§19）

| 指标 | 观测 |
|---|---|
| worker_count | **恒 4**（8/8 窗口） |
| workers_alive_min | **4**（8/8 窗口，无 worker 异常退出） |
| worker_exceptions | **0**（上限 128，8/8 窗口） |
| queue_capacity | `2048`（已验收默认，**未降级**） |
| **queue_high_water** | **`0`**（8/8 窗口 max 均为 0 ⇒ 全程未积压） |
| inflight_high_water | `1` |
| runtime_errors（harness 侧 feed["errors"]） | `0`（8/8 窗口） |
| system_state / operator_state | 全程 `RUNNING` / `NORMAL` |
| open_incidents | 全程 `0`（8/8 窗口） |

**判定**：56,741 真实事件负载下队列始终排空、inflight 高水位 1、worker 零异常 ⇒ 已验收有界优先队列 +
有限 worker pool 在 2h 尺度上保持健康，**未出现背压**。

---

## 10. Dedupe（§20）

| 结构 | 容量 | first → last | max | 是否触顶 | 触顶后行为 |
|---|---|---|---|---|---|
| `ScannerPipeline._trade_dedupe`（pipeline，按 `(exchange, instrument, market_type, trade_id)`） | `8192` | 2 → **8192** | **8192** | **是**（窗口 5 起） | 窗口 5–8 持续保持 8192，同时 btcTr/ethTr 增量在窗口 6/7/8 仍分别 `700/898/774`、`1206/782/1149` ⇒ **触顶后仍持续接收新事件**（FIFO 淘汰 + 重新接受），`dedupe_kept_accepting_after_saturation = true` |
| `EventRuntime._dedupe`（runtime，按已发布事件 key） | `8192` | 4 → **4924** | `4924` | **否** | 2h 内未达容量 ⇒ 结构上不会发生淘汰 |

- `dedupe_within_capacity_all_samples = true`（两结构全程未越界）。
- 生产源码核实为**有界正确**：`ScannerPipeline._remember_trade`（`g2/runtime.py:374-379`）严格执行
  「达容量先 `popleft()` 淘汰再 `add()`」。
- **未**做任何人为清空 dedupe 以美化指标。
- ⚠️ **本项自动检查 `dedupe_long_run_turnover = false` 属检查设计缺陷，见 §16 F-2。**

---

## 11. 内存 / 资源长时行为（§21）—— **NEW FINDING，本批次阻断项**

`_rss_mb()` = `psutil.Process().memory_info().rss`（**当前 RSS**，非峰值）⇒ 下列趋势**非测量伪影**。

| 指标 | 值 |
|---|---|
| baseline（首样本） | `114.723 MB` |
| min / median | `114.562 MB` / `122.887 MB` |
| **peak** | **`134.508 MB`** |
| **final** | **`134.508 MB`**（= peak，**关停时仍在上升**） |
| 总增长 | **+`19.785 MB`（+`17.3%`，相对 baseline）** |
| 整体斜率 | **+`9.066 MB/h`** |
| 8 窗口末值 | `116.371 → 117.875 → 121.141 → 124.477 → 126.816 → 128.992 → 131.863 → 134.508` |
| **窗口均值严格递增** | **`true`**（8/8） |
| 分段斜率 | `0–1800s +3.269` → `1800–3600s +12.826` → `3600–5400s +8.788` → `5400–7200s +8.710` MB/h |

**归因尝试（未完成，如实声明）**：
- 生产去重结构已核实**有界**（pipeline `_trade_dedupe` 在窗口 5 已触顶并保持 8192；runtime `_dedupe` 仅 4924）。
  **关键**：trade-dedupe 在 ≈4500 s 已停止增长，而 RSS 在其后仍以 ≈8.7 MB/h 上升 ⇒ 增长**不能**由 dedupe 解释。
- 生产侧存在**每事件 copy-on-write churn**：`ScannerPipeline.ingest` 每事件 `self.rolling.copy()`
  （`g2/runtime.py:309`）并在末尾 `self.rolling.commit(working_rolling)`（`:365`）。属**功能设计**（复制→变更→提交），
  非活集合泄漏；但 56,741 次/2h 的整引擎复制构成高频大对象分配，**可能**经分配器碎片推高 RSS。**仅为假设，未证明**。
- 本 harness 自身保留线性增长的 `samples` 列表：`717 × ≈1722 B（JSON）≈ 1.23 MB` JSON，
  折算 Python 内存约 **3–4 MB** ⇒ 至多解释约 20% 的增长。
- **结论**：约 **15–16 MB 增长未获归因** ⇒ 依 §21「clear sustained monotonic growth → NEW FINDING，
  STOP acceptance」，本项**阻断本批次**。

> 透明度说明（F-3）：自动检查 `rss_no_unbounded_growth = true` 是因为我在事前声明的阈值
> `RSS_GROWTH_ALERT_FRACTION = 0.25` 未被触发（窗口均值增长比例 `0.1254 < 0.25`）。该阈值检查
> **过宽**，未覆盖 §21 的定性判据（持续单调上升）。**不**以该自动检查的 `true` 作为通过依据。
> 一个诊断参考：总增长 / 总事件 ≈ `0.35 KB/event`。

---

## 12. PostgreSQL 会话生命周期与隔离（§9 / §22）

| 项 | 值 |
|---|---|
| baseline client sessions | `0`（owned/other/server/idle-in-txn 全 0） |
| max owned client sessions | `3` |
| **max other client sessions** | **`0`**（8/8 窗口，**全程无外来写者**） |
| max idle_in_transaction | `1`（8/8 窗口恒为 1，**无累积**） |
| cleanup | `released=true`，`released_seconds=0.056238`，`polls=1`，最终 client sessions `0`，idle-in-txn `0`，`foreign_rows=[]` |

**共享主库隔离（§9）**：

| 项 | before | after |
|---|---|---|
| Alembic revision | `20260905_0004` | `20260905_0004`（**未迁移**） |
| protection columns | `[]` | `[]`（**未变**） |
| N01-7 归属会话可见数 | `0` | `0` |

- `runtime_connected_to_shared_primary = false`（`runtime_dsn` 实测指向 `5434`）。
- 独立后台采样器连续覆盖（60 s 间隔，含 Run #1 窗口）：`shared_primary_sessions_during_run.txt`
  （`START 01:16:20`）全程 `n017_sessions=0`；`shared_primary_sessions_detail.txt`（`START 01:18:57`）
  明细**仅**采样器自身只读探测 `psql|client backend|1`。
- **诚实局限**：该采样器脚本内附带的明细查询存在 SQL 缺陷
  （`aggregate functions are not allowed in GROUP BY`），故 `_during_run` 文件附带 ERROR 行；主计数可用，
  明细由第二个采样器覆盖。**未**由此判断共享主库的写活动归因（不属本任务 Scope）。

---

## 13. 受控 Paper 生命周期（§13 / §17）

**Entry**（`_controlled_entry`：persist → risk-gate → execute 三段可分别取证）：

| 项 | 值 |
|---|---|
| entry BBO | bid `77184.5` / ask `77184.6`，`FRESH`，`tradable`，使用年龄 `0.162 s` |
| risk gate | `admitted=true`，`reason=null` |
| plan | `plan_7d212f0ce53054e676a6e30c`，BUY / MARKET / notional `100.0`，entry_zone `[69466.14, 84903.06]`，SL `73325.275` / TP `81043.725`，`expires_at 18:23:25.758573Z` |
| order / fill | `order_4df12f7a…` / `fill_4df12f7a…`，BUY MARKET FILLED @ **`77223.1923`**，qty `0.0012949477614382435`，fee `0.1` |
| 成交价校验 | ask `77184.6 × (1 + 5 bps) = 77223.1923` ✔（真实 ask + 已验收 slippage，**未覆盖**） |
| position | `pos_6dbdb97a…`，qty `0.0012949477614382435`，avg_cost `77223.1923`，trade `trade_67f14f69…` |
| duplicate intent | 同 intent 再提交 → `EXECUTED / duplicate_intent`，**reuse 同一 order_id**，counts 未变（幂等见证） |

**Position 跨越 TTL 全程保持 OPEN**：`position_quantity` 自 entry 起至关停前恒为
`0.0012949477614382435`（`position_present_samples = 710/717`；未在途中被刷新 TTL、**未**周期性重建 plan）。

**Exit**（§17：风险降低路径，真实 fresh BTC BBO + 已验收 slippage）：

| 项 | 值 |
|---|---|
| close BBO | bid `77117.0` / ask `77117.1`，`FRESH`，使用年龄 `0.156 s` |
| closed_by / exit_reason | `controlled_manual_close` / `MANUAL_CLOSE` |
| order / fill | `order_c3ab78fa…` / `fill_c3ab78fa…`，SELL MARKET FILLED @ **`77078.4415`**，fee `0.09981255…` |
| 成交价校验 | bid `77117.0 × (1 − 5 bps) = 77078.4415` ✔ |
| cancelled orders | `[]` |
| position after close | qty **`0.0`** |

**未**使用 `UPDATE position quantity = 0`、**未**伪造 fill、**未**放宽保护位。

---

## 14. N01-7-F01 长寿命保护见证（§14）—— `LONG_LIVED_PROTECTION_WITNESSED`

| 项 | 值 |
|---|---|
| 分类 | **`LONG_LIVED_PROTECTION_WITNESSED`** |
| `market_path_early_exit` | `false`（持仓确实仍在） |
| plan 真实过期 | `expires_at 18:23:25.758573Z`，`expiry_crossed_at 18:23:26.888854Z`，`expiry_crossed_elapsed_seconds 1861.191` |
| 见证时刻 | `observed_at_elapsed_seconds 1921.532`（过期后 +60 s） |
| **过期后仍持仓采样** | **`531` 个（≈88.5 分钟）** |
| **其中携带完整保护快照** | **`531` 个（100%）** |

见证证据（对真实、未修改的生产路径观察）：

| 断言 | 实测 | 结论 |
|---|---|---|
| (A) TradePlan 真实过期 | `expired_at_observation = true` | ✔ |
| (A′) TTL 仍封锁其风险增量权限 | `load_valid_long_active_plan = null` | ✔ |
| (B) 持久快照完整 | `protection_plan_id=plan_7d212f0ce53054e676a6e30c`、`protection_plan_version=1`、`protection_stop_loss=73325.275`、`protection_take_profit=81043.725`、`protection_updated_at=17:53:25.797983Z`、`present=true` | ✔ |
| (B′) 快照身份 == 起源 plan | `authority.plan_id/plan_version/stop_loss/take_profit` 与 plan 全等 | ✔ |
| (C) 保护服务仍使用该快照 | 真实 fresh BBO 上 `protected.evaluate` → `triggered=false`、`reason="HOLD"`、`trigger="NONE"` | ✔ |
| (D) 未因 TTL 过期而失保护 | `open_position_unprotected_incidents=0`；`system_state=RUNNING`、`operator_state=NORMAL`；无非预期 SAFE_MODE / Resume 拒绝 | ✔ |
| (E) 过期 plan 仍被封锁 | `risk_gate.check` → `admitted=false`、`reason="PLAN_EXPIRED"`；`execute_intent` → `REJECTED / PLAN_EXPIRED`；经济计数 before == after（`orders/fills/positions/trades/accounts/ledger` 全不变） | ✔ |

⇒ **「TTL 仅管风险增量新鲜度；durable protection snapshot = Position 唯一 protection-lifetime authority」**
在 2h 尺度上被真实见证。**未**通过禁用 SL/TP、**未**通过加宽保护位、**未**通过直接写库造持仓来"证明"。

---

## 15. Reconciliation / 经济不变量（§18 / §23）

`reconcile()`（detector only，`REPEATABLE READ, READ ONLY`，**未做任何自动修复**）：

| 项 | 值 |
|---|---|
| 最终 `ok` | **`true`** |
| `diagnostics` | `[]` |
| 13 项不变量 | 全 `true`（含 `open_position_protection_survives_plan_ttl`，`ttl_unprotected_positions: []`） |
| 7 个窗口边界 | `ok = true` × 7（`diagnostics = []`） |
| `open_orders` / `open_buys` | `0` / `0` |
| `active_plans` | `{BTC-USDT: 1}` |
| `impossible_states` / `invalid_open_orders` | `[]` / `[]` |

经济不变量（durable facts）：

| 项 | 值 |
|---|---|
| counts final | orders `2`、fills `2`、positions `1`、trades `1`、accounts `1`、ledger_entries `2` |
| cash final | `9999.612742720297` |
| reserved_cash final | `0.0` |
| realized_pnl final | `-0.2872572797019612` |
| 一致性复核 | `9899.9 + 77078.4415×0.0012949477614382435 − 0.0998125552755736 = 9999.6128` ✔ |
| SELL fill ids | 恰好 `1` 条（无重复 exit fill） |
| 生命周期唯一性 | 恰好 1 trade、1 position、2 fills，无重复 fact |
| 持仓已平 | qty `0.0`、`open_buys_final = 0` |
| 平仓后快照已清 | `protection_present = false`、`protection_plan_id = null` |

---

## 16. 关停 / 残留（§24）

| 项 | 值 |
|---|---|
| queue_final / inflight_final | `0` / `0` |
| workers_final / worker_tasks_final | `0` / `[]` |
| worker_exceptions_final | `0` |
| background_tasks | 仅瞬时 `Task-198503::async_generator_athrow`、`Task-28::Connection.keepalive`；`remaining_pending_tasks = []` |
| shutdown errors | `[]` |
| detached runtime tasks | `0` |
| owned client sessions（终态） | `0` |
| disposable DB 残留 | `0`（`leftover_n01_7_databases = 0`） |
| 任务归属进程/会话残留 | 无 |

关停断言全 true：`queue_drained` / `inflight_empty` / `runtime_workers_stopped` /
`no_detached_runtime_tasks` / `shutdown_no_errors` / `pg_owned_clients_zero` /
`pg_idle_in_transaction_zero` / `disposable_database_residue_zero`。

---

## 17. Findings

### F-1（Runtime / 内存；**阻断项**，归因未完成）
2h 连续运行出现**持续单调的 RSS 增长**：8/8 窗口均值严格递增
（`116.887 → 131.545 MB`），整体 **+9.066 MB/h**，总 **+19.785 MB（+17.3%）**，
**final RSS = peak（关停时仍在上升）**。已排除：测量伪影（读当前 RSS 非峰值）、
生产去重结构（pipeline trade-dedupe 在 ≈4500 s 触顶后停止增长，而 RSS 仍以 ≈8.7 MB/h 上升）、
本 harness 自身 `samples` 列表（仅约 3–4 MB）。**约 15–16 MB 增长未获归因**。
候选假设（**未证明**）：`ScannerPipeline.ingest` 每事件 `rolling.copy()` 的 copy-on-write
分配 churn（`g2/runtime.py:309`/`:365`）经分配器碎片推高 RSS。
⇒ 依 §21 **NEW FINDING / STOP acceptance**。**未**做任何 GC hack、**未**修改生产代码。
**建议**：另开 memory-attribution 窗口，用 `tracemalloc` / 对象计数在 30–60 min 内定位增长生产者，
再决定是「有界碎片」还是「真实累加器」。

### F-2（Validation harness，§26-B）
`dedupe_long_run_turnover` 被实现在 `EventRuntime._dedupe` 上，而该结构在本负载下 2h 内**只到
4924/8192、从不饱和** ⇒ 周转**结构性不可观测**，检查恒为 false。**真正承载 §20 语义**的
`ScannerPipeline._trade_dedupe` 已触顶 8192 并从窗口 5 起保持，同时持续接收新事件
（窗口 6/7/8 trade 增量仍为正）⇒ §20 的实质要求**已被正面观测**。
⇒ 属检查设计缺陷，**非产品缺陷**；但按 §26-B，修复后正式 7200 s 须**从零重启**，
故本批次不以「改检查后重跑」来取得 PASS。

### F-3（Validation harness，透明度）
`RSS_GROWTH_ALERT_FRACTION = 0.25`（事前声明的阈值）使 `rss_no_unbounded_growth` 判为 true，
未能覆盖 §21 的定性判据。**不**以该自动检查作为内存项通过依据。

### F-4（环境，非产品）
- 沙箱内 OKX REST 直连失效 ⇒ 仅 metadata 一次经本机用户代理；WS 直连。属环境事实。
- 本 workspace Bash 工具缺 coreutils（`ls/head/wc/date/dirname` 不可用）且 PowerShell stdout 常被吞
  ⇒ 所有核验落盘后以 Read 复核。`docker exec` 需经 PowerShell 工具调用。
- `ruff format --check` 在**已验收基线**上即有 67 个文件待重排（0 处涉及本任务文件，
  `git diff 71abb07 -- backend/src` 为空可证）⇒ 基线固有，属 Out of Scope，**未**重排。

**无产品功能缺陷被发现**：除 F-1 的内存增长（归因未完成）外，2h 连续运行未暴露任何
市场数据 / 运行时 / 队列 / 经济 / reconciliation / 保护语义层面的产品缺陷。

---

## 18. §28 静态门

统一解释器 `py -3.14`；cwd = worktree。

| 门 | 结果 |
|---|---|
| `ruff check backend/src backend/tests scripts` | `All checks passed!` rc=0 |
| `ruff check scripts/verify_n01_7_runtime_soak.py` | `All checks passed!` rc=0 |
| `ruff format --check scripts/verify_n01_7_runtime_soak.py` | `1 file already formatted` rc=0 |
| `ruff format --check backend/src backend/tests scripts` | rc=1（**基线固有** 67 文件待重排，0 处涉本任务）→ 见 F-4 |
| `compileall -q backend/src backend/tests scripts` | rc=0 |
| `git diff --check` | rc=0 |
| `git status --porcelain` | 仅任务自身新增/修改物 |
| `git diff --stat 71abb07 -- backend/src backend/alembic backend/tests` | **空** |

**Production Code Changed = NO；Migration Changed = NO；Accepted Tests Changed = NO。**
按 §27，**未**重跑大型 full backend 套件（本任务仅新增验证脚本与文档，已验收 harness 逐字节未变，
`main` 无变化）。

---

## 19. Result / Remaining

**Result: `N01-7 = BLOCKED / FIX REQUIRED`**

- 61/62 项检查通过，几乎全部目标（市场数据连续、运行时健康、队列/worker、PG 会话生命周期、
  经济不变量、reconciliation、受控 Paper 生命周期、**F01 长寿命保护见证**、关停与残留、
  共享主库隔离）均取得**正面真实证据**。
- 依 §21，RSS 的持续单调增长构成 **NEW FINDING** ⇒ **不得**写 `VALIDATED`，故本批次判为
  `BLOCKED / FIX REQUIRED`。
- 依 §26-B，`dedupe_long_run_turnover` 的检查设计缺陷须修复；但本批次已被 F-1 阻断，
  不在本窗口"改检查后重跑"以取 PASS。
- 本窗口**未**自行 Acceptance（`N01-7 ≠ ACCEPTED`）；**未** merge / 修改 `main`。

**Remaining / Blockers**

- **Blocker**：F-1 内存增长归因（需独立 memory-attribution 窗口）；F-2 检查设计修复。
- `N01-8`（12h soak）= **NOT STARTED**；`Integrated Runtime Host` = **NOT STARTED**；
  `N01 overall` = **NOT ACCEPTED**。
- 下一位 Reviewer 需独立查看：`acceptance_raw.json`（1.63 MB 原始报告）、
  `aborted_run1_*`（Run #1 harness 缺陷证据）、共享主库采样文件、本 devlog。

---

## 20. 证据文件清单（`E:/Temp/n01-7-soak/`）

`acceptance_raw.json`（Run #2 正式 7200 s 原始报告，1.63 MB）、`acceptance_stdout.txt`、
`acceptance_launch.txt`（`acceptance_exit=1`）、`acceptance_stderr.txt`（空）、
`aborted_run1_raw.json` / `aborted_run1_stdout.txt` / `aborted_run1_launch.txt`（Run #1 中止证据）、
`run_identity.txt`（Repository Truth + Run #1 缺陷 + Run #2 身份 + 代码哈希）、
`static_gate.txt` / `static_gate_scoped.txt` / `static_gate_summary.txt` / `git_gate.txt`、
`fix_static.txt` / `fix_static2.txt` / `fix_verify2.txt` / `fix_contract_check.txt`、
`shared_primary_sessions_during_run.txt` / `shared_primary_sessions_detail.txt`（共享主库 60 s 采样）、
`shared_primary_sampler.ps1` / `shared_primary_detail.ps1`、
`run2_start_check.txt` / `preflight2.txt` / `preflight2_residue.txt` / `midrun_*.txt`、
`acc2_summary.txt`、`summarize.py`（只读解析工具）。

**代码哈希**：
`verify_n01_6_runtime_smoke.py` = `94853dd747d0e800397b5f6fd743b82e42944e01`（未变）；
`verify_n01_7_runtime_soak.py` = `0d823ac8fbac9e29542cef6fa39c39d2d4209cce`。
