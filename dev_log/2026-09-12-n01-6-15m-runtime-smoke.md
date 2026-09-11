# N01-6 — 15-minute Short Runtime Smoke

- Date: 2026-09-12
- Task: N01-6｜15-minute Short Runtime Smoke（validation-only）
- Branch: `n01-6-15m-runtime-smoke`
- Worktree: `E:\Documents\MarketPulse-AI-n01-6`
- Status: `VALIDATED / AWAITING REVIEW`（**未**自行 Acceptance；**未** merge `main`）

## 1. Task / Scope / Out of Scope

**Goal**：用真实 OKX 公共行情 + 真实 disposable PostgreSQL，让**已验收的生产运行时组件**连续运行
≥900 s，并证明该期间市场数据、运行时健康、队列/背压、内存、PostgreSQL 生命周期、reconciliation
与经济不变量、关停清理全部成立；期间通过**正式路径**完成一笔受控 `LIVE_PAPER` SPOT LONG 生命周期
并在关停前平仓。

**允许修改（本任务唯一新增物）**：
- 新增 `scripts/verify_n01_6_runtime_smoke.py`（validation-only harness）
- 新增本 devlog
- 最小同步 `PROJECT_STATE.md` / `AI_CONTEXT.md`

**Out of Scope（明确不做）**：
- **不是** Integrated Runtime Host；**不是** FastAPI 7x24 runtime；**不是** daemon/service；**不是**部署；
  **不是** 7x24 acceptance。
- N01-7 2h soak / N01-8 12h soak / restart-recovery（N01-C 已覆盖，本任务不重复）。
- 不降低 scanner 阈值；不接入 AI（无 paid model、无 provider 依赖）；不触碰 Live Trading /
  OKX 私有端点 / OKX API key / 真实资金。
- 不修改任何 production code / schema / migration / 已验收测试。

**Production Code Policy**：本任务为 `Production Code Frozen`。实测 `git diff ab4bf29..HEAD --
backend/src backend/alembic` 为空，`Production Code Changed = NO`。

## 2. Repository Truth（CIP-02 / CIP-03）

| 项 | 实测值 | 来源 |
|---|---|---|
| Accepted Main / Task Base SHA | `ab4bf297dff42a673d8dbf204dee8e4c0574aff9` | `git ls-remote origin refs/heads/main` + `git rev-parse main` |
| 本地 HEAD（开工） | `ab4bf297dff42a673d8dbf204dee8e4c0574aff9` | `git rev-parse HEAD` in worktree |
| SHA Delta | **无**（Current HEAD == Task Base） | —— |
| Alembic heads | `20260911_0005`（单 head） | `alembic heads` |
| Python | `py -3.14` → `C:\Users\hua\AppData\Local\Programs\Python\Python314\python.exe` | 解释器合同（见 §13） |
| Worktree 创建 | `git worktree add -b n01-6-15m-runtime-smoke … ab4bf29…`（exit=0，status 干净） | `n01_6_wt.txt` |

Preflight 期间观察到主工作区（`E:\Documents\MarketPulse AI`）当时检出在
`prb-01-product-requirements-baseline`；`main` / `origin/main` 与 `ls-remote` 三者一致指向
`ab4bf29…`。本任务所有改动均发生在 N01-6 独立 worktree 内，未触碰主工作区工作树。

## 3. Harness 拓扑（真正走已验收路径）

`scripts/verify_n01_6_runtime_smoke.py`（1309 行，显式 opt-in 验证脚本；**不进 pytest 默认集合**）。

```
OKXLiveProvider(public WS)                     # 真实，无 key
   │  NormalizedTrade / NormalizedBookTicker   # BTC-USDT + ETH-USDT SPOT
   ▼
ScannerPipeline ──▶ OpportunityScanner(accepted default ScannerConfig)
   ▼
EventRuntime(accepted default capacities: 4 workers / queue 2048 / dedupe 8192)
   ▼
PostgresG2Repository ──▶ 真实 disposable PostgreSQL
   │
   └─ SafetyRuntime ─▶ PositionProtectionService / SystemRiskGate / PaperExecutionService
                        (reevaluation_enabled=False —— 与已验收 N01-B harness 一致)
```

- **重点**：每一条 normalized trade **与** normalized book ticker 都进入上述已验收路径，不是伪队列。
- `SmokeHarness(LivePaperHarness)` 继承已验收 N01-B harness，仅做两处**验证侧**适配：
  1. `__post_init__` 增加 per-instrument `self.quotes: dict[str, BestBidAsk]`，覆盖
     `execution.bbo_for`（原因见 §4 缺陷 A）；
  2. `persist_controlled_long()` 把 plan 持久化与 execute 拆开，使 "persist → risk-gate → execute"
     三段可分别取证。
- 常量：`ACCEPTED_FRESHNESS_TTL_SECONDS=5.0`（生产 TTL，**未降低**）、`ACCEPTED_SLIPPAGE_BPS=5`
  （`PaperExecutionService` 默认，**未覆盖**）、`CONTROL_NOTIONAL_USD=100.0`、
  `STOP_LOSS_FACTOR=0.95`、`TAKE_PROFIT_FACTOR=1.05`、`DEFAULT_ACTIVE_SECONDS=900`、
  `DEFAULT_SAMPLE_INTERVAL_SECONDS=5.0`。
- 网络环境（环境事实，非产品事实）：沙箱注入 `HTTP_PROXY/HTTPS_PROXY` 指向本地代理且访问 OKX 失败；
  harness 在构造任何 client 之前**仅对本进程**清除 `HTTP_PROXY/HTTPS_PROXY/ALL_PROXY`（含小写）
  与 `NO_PROXY`。**未**修改任何产品配置、机器或系统代理设置。

## 4. 开发期自检（PROBE）与两次真实缺陷

本 harness 为真实网络 + 真实数据库脚本，开发期用 `--seconds 45/60` 做自检；捕获两个真实问题：

**缺陷 A（harness 侧，已修）** — Probe 2 在 `execute_risk_reducing_exit` 抛
`RuntimeError: harness_has_no_quote:BTC-USDT`。根因：已验收 `LivePaperHarness` 只有**单槽**
`self.quote`，而本任务同时喂 **两条** instrument 流，BBO 交错时 BTC 槽被 ETH 覆盖。修法：
`SmokeHarness` 增加 per-instrument quote 表 + `publish_quote()`，`bbo_for` 按 `instrument_id` 取值；
**未改生产代码**（生产 `bbo_for` 由调用方注入，属既有设计）。

**缺陷 B（harness 侧，已修）** — Probe 1 抛
`AttributeError: 'TradeRecord' object has no attribute 'quantity'`。根因：已验收 `TradeRecord`
无 `quantity/entry_price/exit_price` 字段。修法：`_trade()` 只读真实存在的字段
（`trade_id/instrument_id/status/exit_reason/opened_at/closed_at`），并新增 `_fill_facts()`
join `FillRecord + PaperOrderRecord` 形成 durable 成交证据（side/price/quantity/fee）。

两次均为**验证脚本自身**缺陷，不构成产品缺陷，也不改变任何已验收结论。

## 5. Claim Boundary（明示，不得越界）

本 harness 是**在验证 harness 内连续运行已验收生产运行时组件**。即使 PASS：
- `Integrated Runtime Host` 仍 = `NOT STARTED`；
- `N01-7` / `N01-8` 仍 = `NOT STARTED`；
- `N01 overall` 仍 = `NOT ACCEPTED`。

`mode=ACCEPTANCE` 仅在 `active ≥ 900 s` 时成立；短跑自检一律 `mode=PROBE`、`result=PROBE_OK`。

## 6. Disposable PostgreSQL

- 库名：`marketpulse_n01_6_05c4a7071a16`（`DATABASE_PREFIX=marketpulse_n01_6_` + uuid12）。
- 迁移：`alembic upgrade head` → `20260911_0005`；用 `DATABASE_URL` 环境变量显式锚定
  （`backend/alembic/env.py` 优先读 `DATABASE_URL`，避免误升级 primary）。
- 归属标识：owned `application_name=marketpulse-n01-6-owned-runtime`，observer
  `marketpulse-n01-6-observer`；所有会话观测按 `backend_type='client backend'` 拆分。
- 结束：drop 后 `pg_database LIKE 'marketpulse_n01_6_%'` 计数 = **0**（`RESIDUE 0`）。
- **primary 未被升级**：`_primary_alembic_version()` before = after = `20260905_0004`。

## 7. 真实 OKX / BTC / ETH 证据

| 项 | 实测 |
|---|---|
| 端点 | `GET /api/v5/public/instruments`、`WS /ws/v5/public trades`、`WS /ws/v5/public bbo-tbt` |
| WS URL | `wss://ws.okx.com:8443/ws/v5/public` |
| 订阅 | `trades`×{BTC,ETH} + `bbo-tbt`×{BTC,ETH}（SPOT） |
| metadata | BTC-USDT `SPOT/tradable/tick=0.1/lot=1e-08`；ETH-USDT `SPOT/tradable/tick=0.01/lot=1e-06` |
| connection_attempts / reconnects | `1` / `0` |
| api_key_used / private_endpoint_used | `false` / `false` |
| normalized 事件总数 | **24540** |
| BTC-USDT | trades `2376`、bbos `8203`、最大到达间隔 `2.319 s` |
| ETH-USDT | trades `2883`、bbos `11078`、最大到达间隔 `3.263 s` |
| fresh 证据 | `stale_periods = []`；health transition 仅 1 次 `null → HEALTHY`（ETH，接通瞬间）；BTC/ETH `data_quality` 全程 `FRESH`、`last_fresh` 全程 `True` |

## 8. 15 分钟时间线（active window）

| 项 | 值 |
|---|---|
| started | `2026-09-11T17:09:19.436836+00:00` |
| finished | `2026-09-11T17:24:19.579544+00:00` |
| **active 连续运行** | **900.143 s**（≥900 ✔） |
| wall clock | `909.746 s` |
| sample 数 / 覆盖 | `179`（elapsed `0.089 → 895.333 s`，5 s 间隔） |
| position>0 覆盖 | 166/179 样本（首个 index 13，末个 index 178） |

## 9. 受控 Paper 生命周期（正式路径）

Entry（`_controlled_entry`，三段可分别取证：persist → risk-gate → execute）：

| 项 | 值 |
|---|---|
| entry BBO | BTC-USDT bid `77793.7` / ask `77793.8`，`FRESH`，`tradable`，使用年龄 `0.166 s` |
| risk gate | `admitted=true`，`reason=null` |
| plan | `plan_7d212f0ce53054e676a6e30c`，BUY / MARKET / notional `100.0`，SL `73904.015` / TP `81683.385` |
| order / fill | `order_4df12f7a…` / `fill_4df12f7a…`，BUY MARKET FILLED @ **`77832.6969`**，qty `0.0012848070795809725`，fee `0.1` |
| 成交价校验 | ask `77793.8 × (1 + 5 bps) = 77832.6969` ✔（真实 ask + 已验收 slippage） |
| position | `pos_6dbdb97a…`，qty `0.0012848070795809725`，avg_cost `77832.6969`，trade `trade_67f14f69…` |
| account after entry | cash `9899.9`，reserved `0.0`，realized `0.0` |
| duplicate intent | 再次提交同 intent → `EXECUTED / duplicate_intent`，**reuse 同一 order_id**，counts 未变（幂等见证） |

Close（`_controlled_close`，`manual_close` on 最后一笔真实 fresh BTC BBO）：

| 项 | 值 |
|---|---|
| close BBO | BTC-USDT bid `77838.6` / ask `77838.7`，`FRESH`，使用年龄 `0.723 s` |
| closed_by / exit_reason | `controlled_manual_close` / `MANUAL_CLOSE` |
| order / fill | `order_6859010576…` / `fill_6859010576…`，SELL MARKET FILLED @ **`77799.6807`**，fee `0.09995758…` |
| 成交价校验 | bid `77838.6 × (1 − 5 bps) = 77799.6807` ✔（风险降低动作按 Fresh Best Bid − slippage） |
| cancelled orders | `[]`（无 pending OPEN BUY 需取消） |
| trade final | `trade_67f14f69…`，`CLOSED / MANUAL_CLOSE`，opened `17:10:19.506494` → closed `17:24:19.583370` |
| position final | qty `0.0`，avg_cost `0.0`，`open_buys_final=0` |

**经济不变量（durable facts）**：

| 项 | 值 |
|---|---|
| counts final | orders `2`、fills `2`、positions `1`、trades `1`、accounts `1`、ledger_entries `2` |
| cash final | `9999.757622971947` |
| reserved_cash final | `0.0` |
| realized_pnl final | `-0.14237702805333946` |
| 一致性复核 | `9899.9 + 77799.6807×0.0012848 − 0.09996 = 9999.7576` ✔ 与 durable cash 吻合 |
| SELL fill ids | 恰好 `1` 条：`fill_6859010576…`（无重复 exit fill） |
| 生命周期唯一性 | 恰好 1 条 trade、1 个 position、2 个 fill，无重复 fact |

## 10. Runtime 指标 / 队列 / 背压 / 内存

| 指标 | 观测 |
|---|---|
| worker_count | 恒 `4`（全部 179 样本） |
| queue_capacity / dedupe_capacity | `2048` / `8192`（已验收默认） |
| queue_high_water | **`0`**（队列从未积压） |
| inflight_high_water | `1`（>1 样本数 = 0） |
| dedupe_max | `4250`（< cap 8192；FIFO 未触顶），first `16` → last `4250` |
| worker_exceptions | 恒 `0`（cap 128） |
| system_state / operator_state | 全程 `RUNNING` / `NORMAL` |
| RSS | start `111.582 MB`，p50 `113.129 MB`，**peak `114.758 MB`**，end `114.086 MB`（峰值相对 start +3.18 MB，无单调增长趋势） |

**背压判定**：队列高水位 = 0 且 inflight 高水位 = 1 ⇒ 15 分钟真实双品种行情下**未出现背压**，
已验收有界优先队列 + 有限 worker pool 在 24,540 事件负载下保持排空。

## 11. PostgreSQL 生命周期 / 隔离证据

| 项 | 值 |
|---|---|
| baseline client sessions | `0`（client/owned/other/server 全 0） |
| max owned client sessions | `2`（runtime 池 + observer） |
| **max other(client) sessions** | **`0`**（全程无外来写者） |
| max idle_in_transaction | `1`（36/179 样本非零，瞬时） |
| cleanup | `released=true`，`released_seconds=0.057399`，`polls=1`，final client sessions `0`，`idle_in_transaction` `0`，`foreign_rows=[]` |

**Exclusivity（回归门窗口）**：`n01_6_proc_scan.ps1` 于 regression 前/后各扫一次，均仅见 2 个
**无关**的 crypto-MCP `python.exe`（`crypto-derivatives-free-mcp/.venv` 启动，`matches_validation=no`），
无任何 validation/ pytest 进程存活。

**回归窗口 PG 会话连续采样（补充证据）**：`n01_6_pg_monitor.ps1` 于 `01:26:00 → 01:40:59`
连续采样 **171** 次（5 s 间隔；输出 `E:/Temp/n01_6_pg_during_regression.txt`），覆盖 focused 与
full backend 两个门。采样到的会话**全部可归属到本批自身**，未出现仓库外标识：

| 观测对象 | 说明 |
|---|---|
| `marketpulse:psql:active` | 监控脚本自身查询 `pg_stat_activity` 的连接（每样本出现） |
| `marketpulse:<empty>:active` | 本批 pytest 在 **primary** 库上的连接（本仓库套件 `application_name` 为空，属已知事实） |
| `marketpulse_g53_run_a_*` / `marketpulse_g54_*` / `marketpulse_n01_b_*`（含 `marketpulse-n01-b-owned-freshness`）/ `marketpulse_se02a_*` | 本批 pytest 的 disposable 测试库；前缀全部属本仓库测试模块命名，出现区间 `01:27:51 → 01:30:24` **完全落在** full backend 运行窗口（≈`01:25:45 → 01:30:33`）内 |
| `marketpulse:marketpulse-n01-vf01-observer:idle` | 本批 N01-VAL-FIX-01 测试模块的 observer 连接 |

未观测到任何**仓库外** `application_name`、任何非本仓库前缀的 disposable 库，也无并发第二个套件
的痕迹（若有并发 full suite，按已知并发签名必然互坏，而本门在同一窗口内干净 `267 passed`）。

**局限（如实记录）**：两次进程扫描位于窗口**两端**（`01:24:46` / `01:30:44`），因此「恰好起止于
两次扫描之间」的外部会话无法仅凭进程证据排除；但 DB 级连续采样 + 前缀归属 + 本门 267/267 干净
通过三者一致，未发现任何外部写者迹象。该局限不改变本门结论，仅界定其证据强度。

## 12. Reconnaissance / Shutdown / 资源清理

Reconciliation（关停前，12 不变量）：

```
ok = true, diagnostics = []
reserved_cash_matches_open_buys / sell_reservations_within_positions /
position_quantities_match_fills / available_cash_non_negative /
fills_have_one_ledger_entry / filled_orders_match_fills / active_plan_unique /
open_order_plan_valid / emergency_no_risk_increasing_open_buy /
closed_position_no_stale_intent / account_position_state_valid /
runtime_control_consistent  —— 全部 true
details: open_orders=0, open_buys=0, positions=1, trades=1,
          active_plans={BTC-USDT:1}, invalid_open_orders=[], impossible_states=[],
          runtime_control={operator_state:NORMAL, system_state:RUNNING, issues:[]}
```

Shutdown：

| 项 | 值 |
|---|---|
| queue_final / inflight_final | `0` / `0` |
| workers_final | `0`（worker tasks 全空） |
| worker_exceptions_final | `0` |
| background_tasks | 仅瞬时 `Task-23::Connection.keepalive` / `Task-95763::async_generator_athrow`，**remaining_pending_tasks=[]** |
| shutdown errors | `[]`（无 shutdown 异常） |
| detached runtime tasks | `0` |

关停断言：`queue_drained` / `inflight_empty` / `runtime_workers_stopped` /
`no_detached_runtime_tasks` / `shutdown_no_errors` 全部 true。

## 13. 解释器合同

所有 pytest/脚本门均以 **`py -3.14`**（`C:\Users\hua\AppData\Local\Programs\Python\Python314\python.exe`）
执行；依赖齐备（pytest 8.4.2 / SQLAlchemy 2.0.52 / asyncpg / alembic）。**未**使用
`E:/Documents/MarketPulse AI/.venv/Scripts/python.exe`（Windows venv 重定向启动器会导致
`Popen([sys.executable]).pid != os.getpid()`，属调用方式伪影，会使 N01-C 的 pid 断言必然失败）。
本任务不涉及该断言，但为保持与其他 N01 门一致，统一使用 `py -3.14`。

## 14. Acceptance 证据汇总（机器可读）

harness 输出 `checks`（**37 项**，全部 `true` ⇒ `failures=[]`、`result=PASS`、`mode=ACCEPTANCE`）：

- **入口/行情**：`initial_real_data_both_symbols`、`entry_bbo_fresh`、`entry_symbol_is_btc_spot`
- **风险/执行**：`entry_risk_gate_admits`、`entry_executed`、`entry_exactly_one_buy`、
  `entry_fill_at_real_ask_plus_slippage`、`entry_duplicate_intent_idempotent`
- **时长/生命周期**：`active_duration_ge_900`、`controlled_entry_performed`、`close_bbo_fresh`、
  `close_executed`、`close_position_flat`、`close_no_open_buys`、
  `close_fill_at_real_bid_minus_slippage`
- **关停/运行时**：`queue_drained`、`inflight_empty`、`runtime_workers_stopped`、
  `worker_exceptions_zero`、`no_detached_runtime_tasks`、`shutdown_no_errors`
- **Reconciliation/经济**：`reconciliation_ok`、`final_position_flat`、`final_no_open_buy`、
  `final_exactly_one_exit_fill`、`final_single_trade_lifecycle`、`final_no_duplicate_facts`、
  `final_reserved_cash_zero`、`final_cash_non_negative`
- **PostgreSQL/隔离**：`pg_owned_clients_zero`、`pg_idle_in_transaction_zero`、
  `pg_no_foreign_client_sessions`、`retention_within_capacity`、`primary_database_not_migrated`、
  `disposable_database_residue_zero`
- **harness 自身**：`no_harness_event_errors`

> 说明：本窗口未持有任务书 AC 编号（`N01-6-xx`）原文，故**不臆造编号**；上表 `checks` 键即
> harness 的机器可读验收映射，覆盖任务书 §「市场数据 / 运行时健康 / 队列 / 背压 / 内存 /
> PostgreSQL / reconciliation / shutdown / paper lifecycle / 经济不变量 / reconnect-stale /
> 资源生命周期」全部证据类别。

**观测到的既有非确定性**：`max_inter_arrival_gap_seconds` BTC `2.319 s`、ETH `3.263 s` 均
小于生产 fresh TTL `5.0 s`，且 `stale_periods=[]` ⇒ 15 分钟内未发生 STALE 判定。

## 15. Reconnect / STALE 证据

| 项 | 观测 |
|---|---|
| connection_attempts | `1`（单次建连，全程无重连） |
| reconnects | `0` |
| 最大事件到达间隔 | BTC `2.319 s` / ETH `3.263 s`（均 < 生产 TTL `5.0 s`） |
| stale_periods | `[]`（15 分钟内未触发 STALE 判定） |
| health_transitions | 仅 1 次 `null → HEALTHY`（ETH 接通瞬间），此后无降级 |
| data_quality（BTC/ETH） | 179 样本全程 `FRESH`；`last_fresh` 全程 `True` |

说明：本门**未**覆盖重连/断线恢复（属 N01-C / N01-7 范畴），故其结论仅限「15 分钟内单连接
连续稳定、未出现 stale」，不外推至重连行为。

## 16. Regression Gate

| 门 | 命令 | 结果 |
|---|---|---|
| Focused（N01 三模块） | `py -3.14 -m pytest backend/tests/test_n01_runtime_resource_lifecycle.py backend/tests/test_n01_okx_paper_safety.py backend/tests/test_n01_restart_recovery.py` | **`16 passed`** in 50.10 s（= 6 + 4 + 6） |
| Collect-only | `pytest --collect-only -q backend/tests` | `267 tests collected`（baseline 一致） |
| Full backend | `py -3.14 -m pytest backend/tests` | **`267 passed, 1 warning`** in 268.28 s（warning = 既有 FastAPI/Starlette `httpx` deprecation，非本任务引入） |

两次门均在**独占写者窗口**内执行（进程扫描 + PG 客户端会话采样双证据，见 §11）。

## 17. Static Gate

| 门 | 结果 |
|---|---|
| `ruff check backend/src backend/tests scripts` | `All checks passed!`（rc=0） |
| `python -m compileall` | rc=0 |
| `git diff --check`（worktree） | rc=0 |
| `git diff ab4bf29..HEAD -- backend/src backend/alembic` | **空** ⇒ `Production Code Changed = NO` |
| `git status --porcelain` | 仅 `?? scripts/verify_n01_6_runtime_smoke.py`（新增验证脚本 + 本 devlog + 两个状态文件同步） |

## 18. Findings

1. **F1（harness）**：已验收 `LivePaperHarness` 单槽 `self.quote` 在多品种并发喂入下会被覆盖，
   导致风险降低退出路径取不到指定 instrument 报价。**验证侧**已按 instrument 分离取值；
   生产 `bbo_for` 由调用方注入属既有设计，**无需**（也不应）改动。→ 供 N01-7/8 复用 harness 时注意。
2. **F2（环境）**：沙箱注入 `HTTP(S)_PROXY` 使真实 OKX 访问失败；仅在本验证进程内清除即可恢复
   直连（`ws.okx.com:8443` 可直连）。属环境事实，非产品缺陷。
3. **F3（环境）**：本 workspace 的 Bash 工具缺 coreutils（`ls/grep/wc/head` 不可用），且
   PowerShell stdout 常被吞；所有核验一律落盘为文件后以 Read 复核。
4. **无产品缺陷**：15 分钟连续运行未暴露任何 production defect。

## 19. Production Code Changed

`NO`（实测 `git diff ab4bf29..HEAD -- backend/src backend/alembic` 为空）。
`Tests Changed = NO`（已验收测试文件未改动）。`Schema / Migration Changed = NO`（唯一 head 仍
`20260911_0005`，primary 仍 `20260905_0004`）。

## 20. Remaining / Blockers

- **Remaining**：等人工 Review。`N01-7`（2h soak）、`N01-8`（12h soak）、`Integrated Runtime Host`
  仍 = `NOT STARTED`，须另开窗口按各自批准的门执行。
- **Blockers**：无。
- 本任务**不**构成 `N01 overall` 验收，也**不**推断 `N01-6 = ACCEPTED`（该结论属人工 Acceptance）。

## 21. Context For N01-7 / N01-8

- 可直接复用 `SmokeHarness` 与 `_disposable_postgres_database()`（`DATABASE_URL` 显式锚定 +
  唯一 `application_name` 归属 + `backend_type='client backend'` 观测）。
- 长跑前务必确认：单槽 `self.quote` 已替换为 per-instrument 取值（F1）；进程内清除沙箱代理（F2）。
- 采样器（每 5 s 记录 queue/inflight/dedupe/RSS/PG/position）在 900 s 内 179 样本无泄漏；
  2h / 12h 建议直接沿用并关注 RSS 趋势与 dedupe FIFO 触顶（cap 8192，本次峰值 4250）。
- 长跑独占窗口证据：`n01_6_proc_scan.ps1` + `n01_6_pg_monitor.ps1` 可直接复用。

## 22. 证据文件清单（E:/Temp，本窗口）

`n01_6_preflight.txt`、`n01_6_alembic.txt`、`n01_6_wt.txt`、`n01_6_probe1..3.json`、
`n01_6_acceptance.json`（900 s 正式门原始输出）、`n01_6_acc_summary.txt`、`n01_6_acc_econ.txt`、
`n01_6_sample_agg.txt`、`n01_6_focused.txt`、`n01_6_collect_raw.txt`、`n01_6_collect.txt`、
`n01_6_full_backend.txt`、`n01_6_static_final.txt`、`n01_6_proc_before/after_regression.txt`、
`n01_6_pre_smoke_db.txt`、`n01_6_post_regression_db.txt`、`n01_6_heads.txt`、`n01_6_midrun*.txt`、
`n01_6_pg_during_regression.txt`（回归窗口 171 样本 PG 会话采样）、
`n01_6_pg_monitor.ps1`、`n01_6_proc_scan.ps1`。

### Closeout 窗口追加（`n01_6_cl_*`）

`n01_6_cl_preflight.txt`（§2 drift guard + §3 integrity）、`n01_6_cl_proc_before.txt` /
`n01_6_cl_proc_after.txt`（回归前后进程扫描）、`n01_6_cl_pg_before.txt` / `n01_6_cl_pg_after.txt`
（PG 快照）、`n01_6_cl_pg_regression.txt`（回归窗口 114 样本连续 PG 采样）、
`n01_6_cl_focused.txt`、`n01_6_cl_collect.txt`、`n01_6_cl_full.txt`、`n01_6_cl_static.txt`。

## 23. 状态（验证窗口结束时）

`N01-6 = VALIDATED / AWAITING REVIEW`（该时点）；`N01 overall = NOT ACCEPTED`；
`N01-7 / N01-8 / Integrated Runtime Host = NOT STARTED`。
→ 该状态已在 §24 Final Acceptance Closeout 中更新。

---

# 24. Final Acceptance Closeout

- Date: 2026-09-12
- 任务：`N01-6｜Final Acceptance Closeout`（docs-only Acceptance Closeout + fast-forward `main`）
- 本窗口**未**重新运行 900 s Smoke（不制造第二套 acceptance evidence），**未**启动 N01-7 / N01-8 /
  Integrated Runtime Host。

## 24.1 Review / Acceptance 记录

| 项 | 值 |
|---|---|
| Original N01-6 Review | `PASS` |
| Post-review docs-only Incremental Re-Review（`db3a0dc..3f591a7`） | **`PASS`**（devlog-only） |
| Human Acceptance | **`CONFIRMED`** |
| Reviewed HEAD | **`3f591a7694bf9e03dda53708a92c048dcea75fb3`** |
| Independent Review 结论 | `PASS / READY FOR HUMAN ACCEPTANCE` |

> 背景（如实记录）：`db3a0dc` 为原始验证 implementation/evidence commit；`3f591a7` 为其上的
> **post-review docs-only** 增量（仅 `dev_log/2026-09-12-n01-6-15m-runtime-smoke.md`，+20/−1），
> 内容是 §11「回归窗口 PG 会话连续采样」证据。该增量经独立 Incremental Re-Review = `PASS` 后，
> 本 Closeout 以 `3f591a7` 作为 Reviewed HEAD。（历史：首次收尾任务曾 pin `db3a0dc`，因分支 tip
> 已前移而按 §3 `STOP / RE-REVIEW REQUIRED` 停止，未产生 closeout commit；补齐复审后重发本任务。）

## 24.2 Preflight / Drift Guard（实测）

| 检查 | 实测 | 判定 |
|---|---|---|
| `git status --porcelain` | 空 | ✅ |
| `remote main`（`ls-remote`）= Accepted Main | `ab4bf297dff42a673d8dbf204dee8e4c0574aff9` | ✅ 无 drift |
| `git rev-parse HEAD` = Reviewed HEAD | `3f591a7694bf9e03dda53708a92c048dcea75fb3` | ✅ |
| `merge-base --is-ancestor ab4bf29 3f591a7` | exit `0` | ✅ |
| `merge-base --is-ancestor ab4bf29 db3a0dc` | exit `0` | ✅ |
| HEAD 的 parent | `db3a0dc` | ✅ lineage `ab4bf29 → db3a0dc → 3f591a7` |

## 24.3 Review Head Integrity / Harness Integrity

| 检查 | 实测 |
|---|---|
| `git diff --name-status db3a0dc..3f591a7` | **仅** `M dev_log/2026-09-12-n01-6-15m-runtime-smoke.md` |
| 同上，受限 `backend/src` / `backend/tests` / `backend/alembic` / `scripts/verify_n01_6_runtime_smoke.py` / `PROJECT_STATE.md` / `AI_CONTEXT.md` | **空**（0 命中） |
| `git diff db3a0dc..3f591a7 -- scripts/verify_n01_6_runtime_smoke.py` | **空** ⇒ harness 与 reviewed commit 完全一致 |

Harness 契约静态确认（全部在位）：`DEFAULT_ACTIVE_SECONDS = 900.0`（L126）；
`PUBLIC_WS_URL = wss://ws.okx.com:8443/ws/v5/public`（L135）；通道 `trades` × {BTC, ETH} +
`bbo-tbt` × {BTC, ETH}（L142-145）；`MarketType.SPOT` 断言（L626）；`ScannerPipeline`（L86/820）、
`OpportunityScanner`（L87/820）、`EventRuntime`（L86/819）、`PostgresG2Repository`（L85/819）；
`RunMode.LIVE_PAPER`（L118）；正式路径 `persist_trade_plan`（L101/310）+ `manual_close`（L754，
`controlled_manual_close`）/ 风险闸门 + position + ledger；`DATABASE_PREFIX = "marketpulse_n01_6_"` +
残留查询（L148/557/570）；机器可读 FAIL 闸（L1300 `report["result"] = "FAIL"`）。

## 24.4 Test Environment Exclusivity

| 证据 | 结果 |
|---|---|
| 进程扫描（回归前 `01:58:09` / 回归后 `02:04:30`） | 仅 **2** 个无关 `python.exe`（`crypto-derivatives-free-mcp/.venv` 启动，`matches_validation=no`）；无 validation / pytest / soak 进程 |
| PG 快照（前 / 后） | 仅监控自身 `marketpulse:psql:active` |
| 回归窗口连续采样 `n01_6_cl_pg_regression.txt` | **114** 样本（`01:58:18 → 02:08:16`，5 s 间隔，**完整覆盖** focused + full backend 两个门） |

114 样本中出现的会话**全部归属本批自身**：监控自身 `marketpulse:psql`；本批 pytest 的 primary 库
连接（`marketpulse:<empty>`，本仓库套件 `application_name` 为空）；本批 disposable 测试库
`marketpulse_n01_a_*` / `marketpulse_n01_c_*`（含仓库内定义的 `marketpulse-n01-c-owned-process-b-*`）/
`marketpulse_g52_*` / `marketpulse_g53_run_a_*` / `marketpulse_g54_*`（metrics/run_b/run_c/corrupt/
txn/missing_order/bad_side）/ `marketpulse_se02a_*`（evidence_*/bbo_backstop/outcome_*/migration）。
**未观测到任何仓库外 `application_name`、非本仓库前缀 disposable 库或 `py.exe` 启动器会话。**

**局限（如实记录）**：连续采样间隔为 5 s，理论上「在两次采样之间连上又断开」的外部 client 会话
可被漏采；前后进程扫描亦只能界定窗口两端。结论基于三项一致证据（连续采样 + 前缀归属 + 本门
`267 passed` 干净通过）——未发现任何外来写者迹象，但不等同于形式化互斥证明。

## 24.5 Final Gate（Closeout 最小充分复验）

统一解释器 `py -3.14`；`PYTHONPATH=backend/src`；cwd = worktree。

| 门 | 命令 | 结果 |
|---|---|---|
| Focused N01 | 三模块（`test_n01_runtime_resource_lifecycle.py` + `test_n01_okx_paper_safety.py` + `test_n01_restart_recovery.py`） | **`16 passed`**（50.77 s） |
| Collect | `pytest backend/tests --collect-only -q` | **`267 tests collected`**（1.65 s） |
| Full backend | `pytest backend/tests -q` | **`267 passed, 1 warning`**（274.80 s） |
| Ruff | `ruff check backend/src backend/tests scripts` | `All checks passed!`（rc=0） |
| compileall | `compileall -q backend/src backend/tests scripts` | rc=0 |
| `git diff --check`（worktree） | —— | rc=0 |
| `git diff --check ab4bf29..HEAD` | —— | rc=0 |

warning = 既有 FastAPI/Starlette `httpx` deprecation（非本任务引入）。clean 环境下**无任何 FAIL**。

## 24.6 Closeout Diff / 四项不变

Closeout commit 仅含：

```text
PROJECT_STATE.md
AI_CONTEXT.md
dev_log/2026-09-12-n01-6-15m-runtime-smoke.md
```

```text
Production Changed = NO
Tests Changed      = NO
Harness Changed    = NO
Migration Changed  = NO
```

## 24.7 Accepted lineage / Accepted Main before-after

```text
Accepted Main before = ab4bf297dff42a673d8dbf204dee8e4c0574aff9
  → db3a0dc（original validation implementation/evidence）
  → 3f591a7（post-review docs-only evidence，Reviewed HEAD）
  → Final Closeout Commit（本 commit）
```

- Main Integration = **fast-forward only**（无 rebase / squash / force push / history rewrite）。
- `n01-6-15m-runtime-smoke` evidence branch **保留未删**；`db3a0dc` 与 `3f591a7` 均在 main 历史中。

## 24.8 Claim Boundary（不得越界）

N01-6 = `ACCEPTED / COMPLETE` **不等于**：

```text
Continuous Runtime fully accepted
2-hour soak passed
12-hour soak passed
7x24 Runtime proven
Integrated Runtime Host complete
```

`N01 overall` 仍 = `NOT ACCEPTED`；`N01-7` / `N01-8` / `Integrated Runtime Host` 仍 = `NOT STARTED`。

## 24.9 最终状态

`N01-6 = ACCEPTED / COMPLETE`；`N01 overall = NOT ACCEPTED`；
`N01-7 / N01-8 / Integrated Runtime Host = NOT STARTED`；
`Accepted Main after = Final Closeout Commit`。下一步 = N01-7｜2-hour Medium Runtime Soak（本窗口未启动）。
