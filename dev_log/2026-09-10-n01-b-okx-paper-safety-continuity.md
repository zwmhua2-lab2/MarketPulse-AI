# N01-B — OKX Reconnect / Freshness + Paper Safety Continuity

## Result

`VALIDATED / AWAITING REVIEW`。本记录只说明 validation implementation 与真实验证已完成；
**不构成** Independent Review 或 Human Acceptance，未推进 `main`。

- N01-3 — OKX Reconnect / Freshness：`VALIDATED`
- N01-4 — Paper Safety Continuity：`VALIDATED`
- N01-B overall：`VALIDATED / AWAITING REVIEW`
- N01 overall / Continuous Runtime / 7×24：**未证明、未验收**

## Repository Truth / Workspace Isolation

- Verified Accepted Main / Task Base：`origin/main = a48673404abe256d0adb07c8139b129a54b4e7ce`
  （以 `git ls-remote origin refs/heads/main` 为权威远端真值读取；本地分支 `main` 同 SHA）。
- Branch：`n01-b-okx-paper-safety-continuity`。
- Validation Commit：`fc168c10bec1237c8a795d11a67d1e89783a2bff`（validation artifacts）。
- Isolated clean worktree：`E:\Documents\MarketPulse-AI-n01-b`；开工前 `git status` 为空、
  `HEAD == a4867340…`。
- 历史脏工作树 `prb-01-product-requirements-baseline`（`E:\Documents\MarketPulse AI`，HEAD
  `d47313a1…`，含大量未提交修改）**未被 reset / restore / stash / clean / overwrite**。

### SHA Delta Check（CIP-03）

`git fetch --prune origin` 前 `git rev-parse origin/main` = `a4867340…`；fetch 后变为
`8d4e8305088485095df241fb41111980179f6105`。已查证：

- 权威远端真值 `git ls-remote origin refs/heads/main` = `a48673404abe256d0adb07c8139b129a54b4e7ce`。
- `8d4e830` 是 `a486734` 的 **祖先**（`git merge-base --is-ancestor` = YES），即 N01-A 合并
  **之前** 的旧 main 值。
- 本地无 `.git/refs/remotes/origin/` 目录，该值来自陈旧 `packed-refs`（第 47 行）；`fetch`
  未刷新该 packed-ref（本机 sandbox 已知 ref 事务不落盘现象）。

结论：**本地 ref 陈旧，不是远端基线漂移，也不是他人提交**。Task Base 安全，未执行任何
reset / rebase / overwrite。

## Scope

- Allowed and changed：
  - `backend/tests/test_n01_okx_paper_safety.py`（新增）
  - `scripts/verify_n01_b_okx_paper_safety.py`（新增）
  - 本 dev_log、`PROJECT_STATE.md`、`AI_CONTEXT.md` 的最小当前态同步
- **Production code changed = NO**：`git diff a4867340..HEAD -- backend/src backend/alembic`
  为空；无 schema、migration、Runtime Host、G3/G4/G5 业务语义、reconnect 实现修改。
- Out of Scope（未进入）：N01-5 Restart / Recovery / Reconciliation、N01-6 15m Runtime Smoke、
  N01-7 2h Soak、N01-8 12h Soak、Integrated Runtime Host。
- `DECISIONS.md`、`PRODUCT_REQUIREMENTS.md` 未修改：本任务没有产品或架构决策变化。

## Environment Finding（环境，非产品缺陷）

`www.okx.com` / 公网访问在本机 sandbox 下受两个**环境**因素影响：

1. sandbox 注入 `HTTP_PROXY=http://127.0.0.1:61157`，对 OKX 返回
   `502 CONNECT tunnel failed`（`api.github.com` 经同一代理可 200，说明代理本身可用，只是
   不能到达 OKX）。
2. 本地 DNS 对 `www.okx.com` 返回 `awscn.okpool.top → 169.254.0.2`（链路本地黑洞地址）。

处置：真实 OKX 验证脚本在**自身进程内**清空 `HTTP(S)_PROXY` 环境变量后再构造 client
（`okx_live.py` 的 httpx / websockets 默认信任 env proxy）。清空后：

- `GET https://www.okx.com/api/v5/public/instruments?instType=SPOT` → `200`，连续 3 次
  一致返回 `1416` 个 SPOT instrument。
- `wss://ws.okx.com:8443/ws/v5/public` 真实握手成功并收到 `subscribe` ack（`connId`
  见证据）。

这**只是验证环境的旁路**，不是产品代理配置；未修改任何 production code，未降低任何 AC，
未用 fake server 替代真实 OKX。

## N01-3 — Real OKX Reconnect / Freshness

### Real OSK metadata（AC-B03）

| Instrument | market_type | tradable | tick_size | lot_size |
|---|---|---|---|---|
| BTC-USDT | SPOT | true | 0.1 | 1e-08 |
| ETH-USDT | SPOT | true | 0.01 | 1e-06 |

### Real WebSocket handshake / channels

- 真实握手：`wss://ws.okx.com:8443/ws/v5/public`，`subscribe` ack 覆盖
  BTC-USDT + ETH-USDT，`connId = 55a5360e`。
- `trades` 真实归一化事件：BTC-USDT `trade_id=1055363413`、`price=77766.6`、
  `side=buy`；ETH-USDT `trade_id=873387661`、`price=2458.38`、`side=sell`；
  两者 `market_type = SPOT`、`source = okx.websocket.trade`。
- `bbo-tbt` 真实归一化事件：见下方 reconnect 证据；`source = okx.websocket.bbo-tbt`，
  `data_quality = FRESH`，`bid > 0`、`ask > 0`、`ask >= bid`，`received_time` 为 tz-aware。
- 所有事件均断言 `market_type = SPOT` 且 `instrument_id` 正确；SPOT / SWAP 未混用同一 instrument
  identity。

### Controlled real reconnect（AC-B06 / AC-B07）

复用 Accepted Provider 既有 `disconnect_after_events`：

```text
real OKX connection #1 -> receive real BBO -> controlled local disconnect
-> production reconnect loop -> real OKX connection #2 -> post-reconnect real BBO
```

| Run | Instrument | attempts after 1st event | reconnects after 1st event | connection_attempts | reconnects | first bid | post-reconnect bid |
|---|---|---|---|---|---|---|---|
| run3 | BTC-USDT | 1 | 0 | 2 | 1 | 77725.3 | 77711.4 |
| run3 | ETH-USDT | 1 | 0 | 2 | 1 | 2456.76 | 2456.76 |
| run4 | BTC-USDT | 1 | 0 | 2 | 1 | 77712.4 | 77712.4 |
| run4 | ETH-USDT | 1 | 0 | 2 | 1 | 2456.76 | 2456.76 |

`connection_attempts >= 2`、`reconnects >= 1`、post-reconnect 真实事件均已收到。
`connection_attempts == 2` 与事件只可能在 `_receive_once()` 的 `websockets.connect`
上下文内被 yield，可证明第二个事件来自**第二条真实连接**，不是同连接重放。
BTC 与 ETH 分别做 bounded reconnect validation，不依赖市场流量概率。

### Freshness boundary（AC-B08 / AC-B10 / AC-B11 / AC-B15）

三段 evidence 来源明确区分：

| 段 | 来源 | 证据 |
|---|---|---|
| Fresh #1 | **真实 OKX BBO** | BTC bid=77712.4 / ask=77712.5，使用时 age = 0.273s（< 5s TTL） |
| Stale | **CONTROLLED STALE INJECTION**（非 OKX 事实） | 保留同一 `instrument_id` / bid / ask，仅把 `received_at` 推后 30s（远超 5s TTL）；**未**把 `data_quality` 改成 STALE，以真实走 production TTL 路径 |
| Fresh #2 | **真实 post-reconnect OKX BBO** | BTC bid=77712.4（第二条真实连接），使用时 age = 7.4e-05s |

**明确声明：Stale 段不是「OKX 真的发送了陈旧数据」，而是受控 aging。** Fresh #2 未被任何
fabricated quote 替代。

## N01-4 — Paper Safety Continuity

`RunMode.LIVE_PAPER` + 真实 PostgreSQL（disposable）+ 真实 OKX 公共 BBO；无 Live Trading、
无真实交易所下单、无 private OKX API、无 OKX API Key。

- Paper 直连链：`TradePlan` → `ExecutionIntent` → `PaperExecutionService.execute`（经
  `SystemRiskGate`）→ Paper order / fill；**未**直接 INSERT Position 伪造开仓。
- 初始 account：`initial_balance = 10_000.0`，`accounts = 1`。
- 开仓后 position quantity = `0.0012853407532970203`，`stop_loss = 69985.26`，
  `take_profit = 85537.54`。
- AI 依赖 = 无：`reevaluation_enabled=False`，未新增 Multi-AI fallback。

| 阶段 | Health CORE_MARKET_DATA | Incident | Protection reason | Risk Gate (risk-increasing) |
|---|---|---|---|---|
| Fresh #1（真实） | HEALTHY | — | HOLD | admitted = True / reason = None |
| Controlled stale | UNAVAILABLE | `CORE_DATA_STALE` = OPEN | `CORE_MARKET_DATA_STALE` | blocked，reason = `RUNTIME_STATE_DATA_DEGRADED` |
| Fresh #2（真实 post-reconnect） | HEALTHY | `CORE_DATA_STALE` = RESOLVED | HOLD | admitted = True / reason = None |

Stale 期间进一步证据：

- `SystemRiskGate.check` = `(False, "RUNTIME_STATE_DATA_DEGRADED")`；同时经**真实 G3 事务内
  准入路径**再试一笔 BUY：`intent status = REJECTED`、`reason = RUNTIME_STATE_DATA_DEGRADED`
  —— machine-readable rejection reason 来自 production 准入路径本身，未绕过 Risk Gate。
- 重复 stale 事件（network duplication）再送入 2 次（`SafetyRuntime` + 直接
  `PositionProtection.evaluate`）：position quantity / average_cost / trade_id 全部不变，
  经济事实计数不变。
- **风险降低语义（§20）**：`SystemRiskGate.evaluate(..., side=SELL)` 返回 `None`（不被
  Pause / Safe Mode / stale 禁止）；但 `PositionProtection.manual_close(..., stale)` 返回
  `CORE_MARKET_DATA_STALE` 且 `triggered = False`、`sell_fill_count = 0`。即：**不因 stale
  永久禁止风险降低动作，但保护性成交仍要求可执行的 fresh BBO，绝不 fabricate**。
- 无 fabricated Fill / fake exit / 由 stale quote 导致的 quantity mutation。

### Protection continuity（AC-B17）

- stale 前 position 已存在（quantity > 0）。
- stale 阶段未 fabricate exit（`sell_fill_count = 0`）。
- 真实 post-reconnect fresh BBO 送达 `PositionProtection`，评估的是**同一 durable
  position / 同一 ACTIVE plan**；真实市价未触发 SL/TP → `HOLD`（合法，未修改真实市场价格）。
- 确定性 SL 引擎在 freshness 状态转换后仍可执行：由 deterministic focused test
  （明确标记 `CONTROLLED FRESH BBO`，见下）证明；该证据**不替代**真实 post-reconnect fresh
  BBO 的 freshness recovery evidence。

### ETH-USDT 无持仓 safety path（可选，成本低）

- `protection` reason = `NO_POSITION`；无持仓期间 risk gate。
- stale 阶段 reason 由 `PLAN_MISSING` 变为 `RUNTIME_STATE_DATA_DEGRADED`（数据条件成为 blocker）；
  恢复后回到 `PLAN_MISSING` —— 说明 stale 已不再是 blocker，剩余原因仅为「确实没有 ACTIVE plan」，
  符合 fail-closed 语义。

## Economic Fact Counts

`LIVE_PAPER`，disposable PostgreSQL：

| 阶段 | orders | fills | positions | trades | accounts | ledger_entries |
|---|---|---|---|---|---|---|
| pre-reconnect（开仓后） | 1 | 1 | 1 | 1 | 1 | 1 |
| post-recovery | 1 | 1 | 1 | 1 | 1 | 1 |
| final（含 ETH safety path 后） | 1 | 1 | 1 | 1 | 1 | 1 |

- reconnect / duplicate network event / stale → fresh transition 均**未**产生 duplicate Fill、
  duplicate protective exit 或 duplicate Account/Ledger mutation。
- 未要求行情 Event ID 全局唯一；验证目标是 network duplication 不转化为 duplicate economic action。
- Final reconciliation：`ok = True`，`diagnostics = []`。

## PostgreSQL / Resource Cleanup

- 使用独立 disposable database（`marketpulse_n01_b_<12hex>`）：`CREATE DATABASE` →
  `alembic upgrade head` → validation workload → `DROP DATABASE`。
- 用户真实 `marketpulse` 数据库中的经济事实未被清理或写入（仅只读 `pg_stat_activity` /
  `pg_database` 查询）。
- 运行后 disposable DB activity：`{'sessions': 0, 'idle_in_transaction': 0}`。
- `pg_database LIKE 'marketpulse_n01_b_%'` 残留数 = `0`。
- Harness 自己持有 `AsyncEngine` / `SessionFactory` / runtime 对象，结束 `await engine.dispose()`。
- 真实 stream 结束显式 `await stream.aclose()`，`inspect.getasyncgenstate(stream) == "AGEN_CLOSED"`。
- Background task 收敛证据（run4）：`observed_transient_tasks =
  ['Task-68::Connection.keepalive', 'Task-87::async_generator_athrow']`、
  `remaining_pending_tasks = []`（bounded grace 内全部终止）。无 detached 无限后台 stream、
  无 EventRuntime-owned task leak、无 unclosed AsyncEngine。

## Findings

### N01-B-V01 —（VALIDATION HARNESS，非 production defect）

- **现象**：真实 OKX 脚本第 2 次运行失败于 `assert pending_tasks == set()`（run2，
  `E:\Temp\marketpulse-n01-b\n01-b-real-okx-run2-20260910-202557.stderr.txt`）。
- **Reproduction**：真实 `bbo-tbt` 受控重连后立即 `await stream.aclose()`，立刻断言无 pending task。
- **Root Cause（已验证）**：`aclose()` 后 `websockets` 内部 `Connection.keepalive`
  task（每连接一个，`ping_interval=20`）的取消要到下一个 event-loop turn 才被观察到，
  实测 0.5s 内自行终止。属库内部瞬态，**不是泄漏**。
- **Classification**：validation harness 断言的时序假设错误，不是产品缺陷。
- **Fix（仅 validation 侧）**：改为对**具体 task 对象**做有界等待（`asyncio.wait(tasks,
  timeout=5.0)`）后断言 `remaining_pending_tasks == []`，并记录
  `observed_transient_tasks`。无 polling / retry loop，未修改 production code，未降低 AC。
- **Status**：`CLOSED`（run3 / run4 均通过）。

### N01-B-E01 —（外部环境，见上「Environment Finding」）

sandbox 注入代理无法隧道到 OKX + 本地 DNS 黑洞。分类：
`EXTERNAL ENVIRONMENT LIMITATION`，非产品缺陷。清理代理 env 后真实 OKX 可达。

无其他 production finding。本任务**未**发现需要 `N01-B-FIX-xx` 的 production defect。

## Acceptance Criteria

| AC | 内容 | 结果 | 证据 |
|---|---|---|---|
| AC-B01 | Repository / clean isolated worktree pinned | PASS | `HEAD == a4867340…`，worktree 干净，脏工作树未动 |
| AC-B02 | N01-A remains ACCEPTED / COMPLETE | PASS | `PROJECT_STATE.md` / N01-A dev_log；G2 `30 passed` 未回归 |
| AC-B03 | BTC/ETH real OKX SPOT metadata verified | PASS | SPOT / tradable=true，见 metadata 表 |
| AC-B04 | BTC real WebSocket event received | PASS | BTC `bbo-tbt` + `trades` 真实事件 |
| AC-B05 | ETH real WebSocket event received | PASS | ETH `bbo-tbt` + `trades` 真实事件 |
| AC-B06 | controlled real-OKX reconnect succeeds for BTC | PASS | attempts 2 / reconnects 1 / post-reconnect 真实事件 |
| AC-B07 | controlled real-OKX reconnect succeeds for ETH | PASS | attempts 2 / reconnects 1 / post-reconnect 真实事件 |
| AC-B08 | post-reconnect real fresh BBO obtained | PASS | age = 7.4e-05s（< 5s TTL） |
| AC-B09 | stream cancellation / cleanup leaves no owned pending tasks | PASS | `AGEN_CLOSED`；`remaining_pending_tasks = []` |
| AC-B10 | real fresh BBO marks Core Market Data healthy | PASS | HEALTHY（fresh = True） |
| AC-B11 | controlled stale quote is rejected as stale | PASS | `fresh = False`，protection `CORE_MARKET_DATA_STALE` |
| AC-B12 | stale phase opens/preserves `CORE_DATA_STALE` evidence | PASS | incident OPEN（`CORE_DATA_STALE`） |
| AC-B13 | stale blocks risk-increasing action through SystemRiskGate | PASS | `RUNTIME_STATE_DATA_DEGRADED`（standalone + G3 事务内） |
| AC-B14 | stale creates no fabricated Fill / exit / position mutation | PASS | sell_fill_count 0；quantity / average_cost / trade_id 不变 |
| AC-B15 | post-reconnect real fresh BBO restores healthy data state | PASS | HEALTHY（fresh = True） |
| AC-B16 | stale incident resolves per existing production semantics | PASS | `CORE_DATA_STALE` → RESOLVED |
| AC-B17 | Position Protection remains callable after freshness recovery | PASS | 真实 BBO → HOLD（同一 durable position/plan）；`CONTROLLED FRESH BBO` 确定性用例触发 STOP_LOSS |
| AC-B18 | economic facts remain duplicate-safe | PASS | 计数前后一致；duplicate stale/event 无新增经济动作 |
| AC-B19 | final reconciliation PASS | PASS | `ok = True`，`diagnostics = []` |
| AC-B20 | disposable PostgreSQL / AsyncEngine / tasks cleaned | PASS | 残留 DB 0；activity 0/0；`engine.dispose()`；task drain 空 |
| AC-B21 | production code changed = NO | PASS | `git diff a4867340..HEAD -- backend/src backend/alembic` 为空 |
| AC-B22 | existing G1/G2/G3/G4 relevant regression PASS | PASS | G2 30 / G3 16 / G4 77 passed |
| AC-B23 | full backend regression PASS | PASS | `171 passed, 1 warning` |
| AC-B24 | Ruff / compileall / diff-check PASS | PASS | 见 Verification |

## Verification

```text
PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_n01_okx_paper_safety.py -q -s
  -> 3 passed in 6.46s

py -3.14 scripts/verify_n01_b_okx_paper_safety.py      (真实 OKX，bounded)
  -> run3 EXIT=0 ; run4 EXIT=0（run2 失败见 N01-B-V01，已修复并复跑通过）

PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q
  -> 30 passed in 4.20s
PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group3.py -q
  -> 16 passed in 15.58s
PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group4.py -q
  -> 77 passed in 70.05s
PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q
  -> 171 passed, 1 warning in 189.42s
     （warning = 既有 FastAPI/Starlette TestClient/httpx deprecation）

py -3.14 -m ruff check backend/src backend/tests scripts   -> All checks passed!
py -3.14 -m compileall -q backend/src backend/tests        -> exit 0
git diff --check                                           -> exit 0
```

外部证据文件（仓库外，不进入 Git）：

```text
E:\Temp\marketpulse-n01-b\n01-b-real-okx-20260910-202513.txt          (run1, stdout+stderr 合并)
E:\Temp\marketpulse-n01-b\n01-b-real-okx-run2-20260910-202557.json    (EMPTY, 失败运行)
E:\Temp\marketpulse-n01-b\n01-b-real-okx-run2-20260910-202557.stderr.txt
E:\Temp\marketpulse-n01-b\n01-b-real-okx-run3-20260910-202746.json
E:\Temp\marketpulse-n01-b\n01-b-real-okx-run3-20260910-202746.stderr.txt
E:\Temp\marketpulse-n01-b\n01-b-real-okx-run4-20260910-202818.json
E:\Temp\marketpulse-n01-b\n01-b-real-okx-run4-20260910-202818.stderr.txt
E:\Temp\marketpulse-n01-b\backend-full-20260910-203046.txt
```

脚本 stderr 中的 `okx_stream_disconnected / ConnectionError: verification_disconnect`
Traceback 是**受控本地断开**的 production 日志证据本身（`disconnect_after_events=1`），
不是异常失败。

## Deterministic focused gate（离网）

`backend/tests/test_n01_okx_paper_safety.py`（已纳入 `pytest backend/tests`，不依赖公网）：

- `LOCAL FAKE WS`（`ws://127.0.0.1`，loopback）：受控断开后 reconnect loop 必须建立**第二条**
  连接，且 post-reconnect 事件带第二条连接的 socket 序号（`100_002` vs `100_001`）；
  BTC / ETH 各一例。**明确标记为 LOCAL FAKE WS，不替代 Real OKX Gate。**
- 真实 PostgreSQL（disposable）上的 FRESH → CONTROLLED STALE → FRESH 安全边界：health /
  incident / protection reason / Risk Gate fail-closed / 无经济 mutation / recovery /
  replicate-safe / reconciliation。
- 明确标记 `CONTROLLED FRESH BBO` 的确定性保护触发用例：freshness 状态转换后 SL 引擎仍可执行、
  成交价 = `best_bid × (1 − slippage_bps/10000)`、无 duplicate。

## Claim Boundary

本 Gate 证明：

> Production runtime components 在明确的 N01 validation harness 中，可以跨真实 OKX
> reconnect / stale-fresh boundary 保持安全行为。

**不得**扩大为：

```text
所有 ISP 故障均已证明 / 所有 OKX outage 均已证明
DNS outage 已证明 / 机器 suspend-resume 已证明
7x24 network resilience 已证明 / Continuous Runtime 已证明
FastAPI 正式生产入口已形成完整 7x24 Runtime / Integrated Runtime Host 已存在
```

本任务**不等待**真实 OKX 自己发生故障，也不包含任何 15m / 2h / 12h soak；几十秒级 bounded
网络验证**不**构成 Continuous Runtime proof。

## Known Risks

- 本机 sandbox 的代理 / DNS 环境会阻断 OKX 直连；真实 OKX 验证脚本必须自行清空 env proxy
  才能运行。该脚本在**其他**网络环境下（无侵入代理）同样应可直接运行。此项属环境依赖，非产品缺陷。
- `websockets` 内部 `Connection.keepalive` task 在 `aclose()` 后的极短收敛窗口，已用有界等待
  证明终止；若未来 `websockets` 大版本改变该行为，deterministic test 会立即暴露。
- 真实 BBO 未触发 SL/TP（`HOLD`）属正常结果，未人为修改真实市场价格制造 trigger。

## Production Code Changed

`NO`（`backend/src`、`backend/alembic` diff 为空；无 schema / migration / Runtime Host 修改）。

## Final Recommendation

`READY FOR INDEPENDENT REVIEW`

N01-B = `VALIDATED / AWAITING REVIEW`；不得由本记录声明 `ACCEPTED`、`N01 = ACCEPTED`、
`Continuous Runtime = PROVEN`、`7x24 = PROVEN`。下一步：Independent Review → Human Acceptance；
N01-5 / N01-6 必须另开窗口并按各自批准的门执行。
