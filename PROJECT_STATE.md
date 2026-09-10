# MarketPulse AI Project State

## Current Group

N01-B — OKX Reconnect / Freshness + Paper Safety Continuity — ACCEPTED / COMPLETE

N01-A — Deterministic Runtime + Resource Lifecycle — ACCEPTED / COMPLETE

N01 overall — NOT ACCEPTED（N01-5 / N01-6 / N01-7 / N01-8 与 Integrated Runtime Host 仍 `NOT STARTED`）

## GitHub Repository

- GitHub Repository Full Name: `zwmhua2-lab2/MarketPulse-AI`
- GitHub Repository URL: https://github.com/zwmhua2-lab2/MarketPulse-AI
- Visibility: `PRIVATE`
- Default Branch: `main`
- Accepted Main Source: Git `main` / `origin/main` — read actual SHA at task preflight（CIP-02）
- Current Development Status: `N01-B ACCEPTED / COMPLETE`（Final Acceptance Closeout completed）

## Branch / Source

- Current Accepted Branch: `main`
- Current Group Branch: `n01-b-okx-paper-safety-continuity`（N01-B accepted historical branch；Final Acceptance Closeout fast-forward 收编至 `main`）
- Last Accepted Group Branch: `n01-a-runtime-resource-lifecycle`（历史证据，保留未删）；更早 `g5-deterministic-replay-foundation`
- Accepted Main Source: Git `main` / `origin/main` — read actual SHA at task preflight（CIP-02）
- G5-1 Implementation Acceptance Basis: `34da62a0cc9dbe95b95faadb770fbd06179a6975`
- Migration Head: `20260905_0004`（`alembic current/heads` 一致）
- Real AI Provider Status: `DEFERRED`（`OPENAI_API_KEY=MISSING`；测试用 deterministic Fake Provider）

## Completed

- 空工作区 Git 初始化。
- Foundation、Provider boundary、标准化模型、Universe 初版实现已建立。
- Backend/Frontend、PostgreSQL Docker、Alembic migration cycle、Auth、OpenAPI/type generation 已真实验证。
- OKX Spot/Swap REST identity、Trade/BBO/Kline WebSocket、OI/Funding、freshness、重连与 Universe 已真实验证。
- Group 1 已完成人工 Acceptance Review #1，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 2 已完成人工 Acceptance Review #2，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 3 已完成人工 Acceptance Review #3，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- G3 Post-Acceptance Fix 与 Fix2 已人工验收，`PASS WITH NON-BLOCKING NOTES`。
- FG-A — G3 Execution Authority & Freshness：`ACCEPTED / COMPLETE`（accepted implementation
  `a9c2cd64bea0c6cc43b1ef8ad890e4db5353b801`；C04 accepted unblocker
  `d574e242f3aa7c26658ed6cc780fd8f744dbf503`；isolated Final Gate PASS）。
- C04 — Alembic Replay Test Isolation Fix：`ACCEPTED / COMPLETE`；无 production Alembic
  behavior 或 migration revision 修改。
- FG-B — Protection Concurrency：`ACCEPTED / COMPLETE`（accepted implementation
  `1c292b28e8e453b3c2e349b6b3b4f76c542341b1`；F03 / F06 = `ACCEPTED / FIXED`；
  FG-C = `NOT STARTED`）。
- FG-C — Safety Recovery Validity：`ACCEPTED / COMPLETE`（accepted implementation
  `39388acdd313d631e887a3d1786352bbee51caca`；F04 / F05 / C01 = `ACCEPTED / FIXED`；
  Acceptance Fix #2 已验证 C01 Case G 的 OPEN-position 三方保护生命周期与 F05 Case 2/3/4
  crash-boundary durable 证据；`state_version` 仅作为 risk-increasing freshness authority，
  不参与 open-position protection lifetime）。
- FG-E — Reconciliation Snapshot Consistency：`ACCEPTED / COMPLETE`（Human Acceptance
  confirmed；accepted implementation `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`；N02-1～N02-14
  evidence PASS；无 schema/migration 或 Control/Recovery/execution-accounting semantic change）。
- N01-FIX-01 — G2 EventRuntime Lifecycle Safety：`ACCEPTED / COMPLETE`（Task Base
  `d47313a1cb41996410606fe92b286a5046ed4fce`；accepted implementation
  `fc234b99dcbbd4f8dc2059a415b1b44d9f7f0a2b`；R01/R02/R03 与 PostgreSQL durable duplicate
  TOCTOU 已修复；无 schema/migration、Runtime Host、G3–G5 或业务语义修改）。
- N01-A — Deterministic Runtime + Resource Lifecycle：`ACCEPTED / COMPLETE`（Task Base /
  verified `origin/main` = `bc635787eafdf88fdc8e5810109452b5e394a076`；仅新增 deterministic
  validation；20 个 disposable PostgreSQL lifecycle、queue/backpressure、finite worker、同标的串行、
  BTC/ETH 并行、dedupe/retry/cancellation、task/queue/inflight/retention/session 证据均通过；无
  `backend/src`、schema/migration、Runtime Host、OKX 或 long-soak 改动）。
- N01-A Final Acceptance Closeout：`ACCEPTED / COMPLETE`；N01-A-F01/F02 = `CLOSED / PASS`；accepted
  validation lineage = `6321efb` → `facac1f` → `d67ffc2`；Final Closeout commit documented below。
- N01-B — OKX Reconnect / Freshness + Paper Safety Continuity：`ACCEPTED / COMPLETE`
  （Independent Review `PASS`；Human Acceptance `CONFIRMED`；Task Base / verified
  `refs/heads/main` = `a48673404abe256d0adb07c8139b129a54b4e7ce`；accepted validation lineage =
  `fc168c1` → `26688a2`；`N01-3 = ACCEPTED`、`N01-4 = ACCEPTED`）。真实 OKX SPOT metadata、真实
  `bbo-tbt` / `trades`、BTC-USDT 与 ETH-USDT 受控真实重连、FRESH → CONTROLLED STALE → FRESH 边界、
  `LIVE_PAPER` paper safety continuity（disposable PostgreSQL）均已真实验证；`Production code
  changed = NO`（`backend/src` / `backend/alembic` diff 为空）。Final Gate 重跑全绿：focused
  `3 passed`、G2 `30` / G3 `16` / G4 `77`、full backend `171 passed` ×2、Ruff / compileall /
  `git diff --check` PASS。详见 `dev_log/2026-09-10-n01-b-okx-paper-safety-continuity.md`
  「Final Acceptance Closeout」。
- N01-VAL-FIX-01 — PostgreSQL Lifecycle Evidence Stability：`VALIDATED / AWAITING REVIEW`
  （Task Base / verified `refs/heads/main` = `e0dab188e55c32b7607c18a66644d25449dc2236`；
  branch `fix/n01-val-postgres-lifecycle-evidence`）。Finding `N01-VAL-F01` 已在当前 accepted
  `main` 上复现（40 次文件级执行中 2 次），并**证伪**"连接泄漏 / 服务端关闭可见窗口"假设：
  捕获到的多余 `pg_stat_activity` 行是 `backend_type='autovacuum worker'`、`usename=null`、
  `application_name=''` 的**服务端维护进程**（`last_query='autovacuum: ANALYZE
  pg_catalog.pg_class'`），不是任何 harness 连接。lifecycle gate 改为：每 cycle 唯一
  `application_name` 归属 + 按 `backend_type` 拆分 client/server + 有界最终条件等待
  （`client_sessions == 0`，hard deadline 1.0 s，实测最长关闭可见时间 8.3 ms）；新增注入泄漏
  负向对照（可检出、可安全释放）。`Production code changed = NO`。详见
  `dev_log/2026-09-10-n01-val-fix-01-postgres-lifecycle-stability.md`。
- N01-VAL-FIX-02 — N01-B PostgreSQL Activity Evidence Stability：`VALIDATED / AWAITING REVIEW`
  （Task Base = `N01-VAL-FIX-01` 已评审 commit `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2`，
  其 parent = Accepted Main `e0dab188e55c32b7607c18a66644d25449dc2236`；branch
  `fix/n01-val-n01b-postgres-activity-evidence`）。Finding `N01-VAL-F02`：N01-B 两个
  PostgreSQL 测试用 `datname`-only 聚合（`SELECT count(*) ... FROM pg_stat_activity WHERE
  datname = ...`）与 `activity_after == baseline` 证明 client connection cleanup，属错误
  ownership model。修复：每个测试唯一 `application_name` 归属（`marketpulse-n01-b-owned-*`）
  + observer 连接 primary 库不污染被测库 + 按 `backend_type` 拆分 client/server +
  有界最终条件等待（`client_sessions == 0`，hard deadline 1.0 s，尺度沿用 FIX-01 实测
  ≤8.3 ms）+ 极小注入泄漏负向对照；未引入 `baseline + 1` 容差，未用 sleep/retry 伪造清理证明。
  历史 8 次 full-suite 中的 1 次 `test_n01_b_freshness_boundary_...` 失败**无 traceback**，
  本窗口 12 次文件级 + 1 次 full suite 有界复现**未再捕获**，故明确记录为
  `single historical full-suite failure not independently recaptured`；Fix 依据为源码缺陷 +
  FIX-01 的既有捕获证据。`Production code changed = NO`。详见
  `dev_log/2026-09-10-n01-val-fix-02-n01b-postgres-activity-evidence.md`。
- N01-VAL-FIX-03 — G4 Protection / Limit-Fill Assertion Uniqueness：`VALIDATED / AWAITING REVIEW`
  （Task Base = `14f387ac88af1ecd377fcd181c90b109ee361754`，即 N01-VAL-FIX-02 已评审 commit；
  branch `fix/n01-val-g4-order-assertion-uniqueness`）。Finding `N01-G4-F01`（Classification =
  Case B — Test Assertion Scope / Ambiguous Read Defect，**未**确认 production concurrency defect）：
  `test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen` 用非唯一谓词
  `PaperOrderRecord.plan_id == <pending plan>` + `Session.scalar()` 读取 pending BUY 状态；protective
  exit SELL 与 pending LIMIT BUY 合法共享同一 `plan_id`（`persist_trade_plan` REPLACE 旧 ACTIVE plan ⇒
  待成交 BUY plan 为唯一 ACTIVE ⇒ `_close_position_in` 以该 plan_id 建 SELL），`Result.scalar()`
  多行时静默返回首行、query 无 `ORDER BY` ⇒ 行序依赖物理堆序，负载相关。修复：pending BUY 改用
  唯一 identity `order_id`（以 `plan_id + side=BUY + order_type=LIMIT` 唯一谓词取得一次，断言
  `len == 1` 后一律 `session.get(PaperOrderRecord, order_id)`），并强化为 exact pending BUY
  (`side/order_type/status= CANCELLED/reserved_cash == 0`) + protective SELL (`side=SELL/status=FILLED`)
  + `protection.cancelled_order_ids` + `position.quantity == 0` + `fills == []` + 仅原始 BUY entry fill +
  reconciliation PASS；并发 witness（`after_risk_reducing_orders_lock` / `assert not fill.done()`）
  完整保留；**未**用 `ORDER BY` / `LIMIT 1` 规避。同构 tests-only ambiguity 一并最小修正
  `test_stop_loss_cancels_pending_add`（read 发生在 protective exit 之后），其余 13 处 `plan_id` 读取
  经审计为 Safe（读取窗口内该 plan 下只可能有一笔）未改。验证：目标测试 20/20；`test_group4.py`
  `77 passed` ×2；FIX-01 `6 passed`、N01-B `4 passed`、G2 `30`、G3 `16`；full backend
  `173 passed` ×2（**带 DB 客户端会话监控**，全程无外来写者）；Ruff / compileall /
  `git diff --check` PASS。`Production code changed = NO`。详见
  `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md`。
- Group 4（持仓安全与恢复）已实现：Position Protection（SL/TP/Protective Exit/幂等）、Position Re-evaluation（HOLD/ADD/REDUCE/CLOSE/CANCEL_ADD/UPDATE_STOP/UPDATE_TP/UPDATE_INVALIDATION/REPLACE_PLAN）、System Safety State、Control（Pause/Resume/Emergency Stop/Emergency Recovery/Symbol Block/Manual Close/Safe Mode）、Recovery Manager（PostgreSQL SoT + Restart Recovery + Reconciliation Gate + Plan/Order Revalidation + EXECUTION_GAP）、Health Registry 与 Incident Manager。

## In Progress

- 无进行中的 Acceptance Group。**N01-B 已 `ACCEPTED / COMPLETE`**（见 Completed）；下一门
  N01-5 Restart / Recovery / Reconciliation（N01-C）**尚未开窗**。
- `N01-VAL-FIX-01 = REVIEW PASS / CLOSEOUT BLOCKED BY F02`：validation infrastructure fix，只改
  `backend/tests/test_n01_runtime_resource_lifecycle.py`；其 Final Closeout 因新增 validation
  finding `N01-VAL-F02` 而**暂停执行**（未建 closeout commit、未推进 `main`）。既**不构成**
  N01-C 开窗，也**不改变** `N01-A` / `N01-B` 的 `ACCEPTED` 结论。
- `N01-VAL-FIX-02 = VALIDATED / AWAITING REVIEW`：继续修 N01-B PostgreSQL activity evidence
  ownership model，只改 `backend/tests/test_n01_okx_paper_safety.py`（+ dev_log / 状态文档）；
  **未** merge `main`、**未** closeout `N01-VAL-FIX-01`、**未**开始 `N01-C`。
- `N01-VAL-FIX-03 = VALIDATED / AWAITING REVIEW`：tests-only 修 `N01-G4-F01`（G4 protection /
  limit-fill 断言用非唯一 `plan_id` 读 pending order），只改 `backend/tests/test_group4.py`
  （+ dev_log / 状态文档）；**未** merge `main`、**未** closeout FIX-01 / FIX-02 / FIX-03、
  **未**开始 `N01-C`。`N01-G4-INV-01 = REVIEW PASS / Case B`。
- N01 Continuous Runtime / Soak 本身仍 `NOT ACCEPTED`；不得由 N01-B 验收推断 N01 整体验收。
- N01-5 Restart / Recovery / Reconciliation、N01-6 15m Runtime Smoke、N01-7 2h Soak、N01-8 12h
  Soak 与 Integrated Runtime Host 仍 `NOT STARTED`，须另开窗口并按各自批准的门执行。

## Blocked

- 无阻塞。

## Current Architecture Baseline

- Python/FastAPI/asyncio backend；React/TypeScript/Vite frontend；PostgreSQL via Docker；SQLAlchemy/Alembic。
- Raw Adapter → Normalized Data → 后续 Derived Features。
- 默认 `LOCAL_ONLY=true`，默认 `RUN_MODE=TEST`。
- OKX Spot 与 Swap 使用不同 `market_type` 和 `instrument_id`。
- G4 增加：System/Operator State 分离；统一 Risk Gate；PostgreSQL 为 Restart Recovery 唯一事实源；Protective Exit 一律以当前 Fresh Best Bid − slippage 成交（Stop/TP 仅触发价）；Position Event 追加审计；Trade.exit_reason。

## Current Runtime Facts

- G2 Event Runtime 使用有界 asyncio 优先队列与有限 worker pool；同 `instrument_id` 串行。
- G3 不可变 Decision Snapshot、Provider-neutral AI boundary、Account Row Lock 事务内写 Order/Fill/Position/Account/Ledger/Outbox。
- G4 运行时：SL/TP 不经 AI Queue；同 Symbol 串行（asyncio lock + DB row lock）；Risk Gate 锁定 runtime_control 行后决定风险增加动作是否放行；EMERGENCY_STOP 原子取消 OPEN BUY 并释放 Reservation（≠ Close All）；SAFE_MODE 锁存需显式恢复 → PAUSED → 人工 Resume。
- G4 stale core data（N01-B verified）：`CORE_MARKET_DATA = UNAVAILABLE`，`CORE_DATA_STALE`
  incident OPEN，风险增加 BUY 经 `SystemRiskGate` fail-closed（`RUNTIME_STATE_DATA_DEGRADED`，
  standalone 与 G3 事务内一致）；SELL 风险降低**不**因 stale 被禁止，但保护性成交仍要求
  executable fresh BBO，stale 下不 fabricate fill；fresh 恢复后 health HEALTHY 且
  `CORE_DATA_STALE` 按既有语义 RESOLVED。

## Known Issues

- 原「Pre-existing flaky test」（`N01-G4-F01`）**根因已定位并已修（待评审）**：
  `backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`
  在负载下的 full-suite 上下文中可能失败（`assert order.status == OrderStatus.CANCELLED ... got
  FILLED`，`test_group4.py:1709`）。分类 = **Case B — Test Assertion Scope / Ambiguous Read
  Defect**（**非** production concurrency defect）：pending LIMIT BUY 与 protective exit SELL
  合法共享同一 `plan_id`，而断言用非唯一 `plan_id` 谓词 + `Session.scalar()`（多行静默取首行）+
  无 `ORDER BY`，故结果依赖物理堆序。N01-G4-INV-01 已以 PostgreSQL lock evidence 确证；N01-VAL-FIX-03
  改为按唯一 `order_id` 读取并强化断言，`N01-VAL-FIX-03 = VALIDATED / AWAITING REVIEW`（目标测试
  20/20、full backend 监控下 `173 passed` ×2）。修复**尚未** merge `main`，故该现象在 Accepted
  Main `e0dab188` 上仍然存在。证据见
  `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md`。
- **环境级风险（out-of-scope，未修）**：本仓库全量套件使用**单一共享 PostgreSQL 数据库**，且
  `Harness.clean()` 会整表清空 `RunMode.REPLAY` 行 ⇒ **任何两个并发会话在全量套件层面必然互相
  破坏**（观测签名：`open_position()` 得到 `PLAN_REPLACED`，因另一写者替换了同
  `(run_mode, instrument_id)` 的 ACTIVE plan）。N01-VAL-FIX-03 的 full-suite 门首次尝试即被另一
  WorkBuddy 会话通过 Bash 发起的 `pytest backend/tests` 污染（`10 failed, 163 passed`），
  已在带 DB 客户端会话监控的条件下重跑取得 2 次连续 `173 passed`。建议后续另开窗口评估
  （例如按会话隔离数据库或加互斥），不在本 Fix Scope 内。
- 真实 AI Provider 集成 = `DEFERRED`（`OPENAI_API_KEY=MISSING`）。Position Re-evaluation contract 以 deterministic Fake Provider 验证，未伪造真实 AI 结果。
- Real OKX Paper Protection / Restart Recovery smoke 已用真实 BTC-USDT BBO 完成（`LIVE_PAPER`，无 Live 下单）。
- FastAPI TestClient 上游 deprecation warning 仍存在（2 处，不影响结果）。

## Group 4 Result

- G4 PostgreSQL 场景测试（`test_group4.py`）覆盖 A–U、失败注入、Post-Review Fix #1–#4 回归：`45 passed`。
- 全量 `pytest backend/tests`：`72 passed`，1 个既有 FastAPI/Starlette deprecation warning。
- `ruff check backend/src backend/tests scripts` / `compileall` / `git diff --check`：PASS。
- `alembic current` / `alembic heads`：`20260905_0004 (head)`。
- Restart smoke（`scripts/g4_verify_runtime.py setup/recover`）：两进程 PostgreSQL 重建 → `RUNNING`、`active_symbols=['BTC-USDT']`、`reconciliation_ok=True`。

### Post-Review Fix #1

- P0-1：AI 重估值在 provider 返回后、dispatch 前重验 DB 的 state_version / active plan(plan_id+version) / position lifecycle，变化判 STALE，记 `AIDecisionRecord.status=STALE_DECISION` + `PositionEvent(AI_REEVALUATION)`，返回 HOLD 零副作用。
- P0-2：Recovery 捕获重启前 `system_state` 锁存 SAFE_MODE；未解决 blocking incident 不得进入 RUNNING。
- P0-3：Recovery `_revalidate` 严格 §33（TTL / state_version / entry / stop-invalidation / BBO freshness），final state 非 RUNNING（SAFE_MODE/EMERGENCY_STOP/ERROR）取消残留 OPEN BUY 并释放 Reservation。
- P1-1：Recovery 与 Orchestrator 的 BBO 新鲜度判断加入 `DataQuality.FRESH`。
- P1-2：`active_symbols` 仅来自 OPEN Order / quantity>0 Position / ACTIVE Plan。
- P1-3：Reconciliation 不变量 #10 增测 closed lifecycle 后残留的风险增加 BUY（`BUY_AFTER_CLOSED_LIFECYCLE`）。

### Post-Review Fix #2

- P0-1 Recovery §33：OPEN BUY 在恢复事务内重验 current Fresh Best Ask、entry zone、stop breach、persisted symbol block 与 G3 cash/capacity；失效订单原子 cancel 并释放 Reservation，不 retroactive fill。
- P0-2 AI TOCTOU：provider 后使用 action-time clock 与重新获取的 executable BBO；最终 stale facts（state_version、expected active plan/version、position/trade lifecycle）在 PostgreSQL 行锁事务内校验并保持到 mutation commit。
- `PlanManager.replace()` 改为 expected-current conditional update；旧 plan 非当前 ACTIVE 时返回 stale，保留 `uq_trade_plans_one_active`，不再 replace symbol 下所有 ACTIVE plan。
- P1 Recovery BBO failure：OPEN Position 的 exception/missing/unusable BBO 持久化 `CORE_DATA_STALE` Incident，Health 标记 UNAVAILABLE，恢复落在非 RUNNING。
- 修复 SAFE_MODE recovery 的 blocking-incident 可达性：仅在 health/reconciliation 与 position protection durable facts 通过后，于同一控制事务 resolve 并落到 PAUSED。
- 新增 8 个真实 PostgreSQL 回归测试；真实 AI Provider 因 `OPENAI_API_KEY=MISSING` 为 `DEFERRED / NOT VERIFIED`。

### Post-Review Fix #3

- `load_active_plan()` 现只在恰好一条 ACTIVE row、payload 可由 `TradePlan.model_validate` 加载，且 payload 与 durable row 的 plan identity / run_mode / instrument / version / status / timestamps 一致时返回计划；否则 fail closed。
- 共用的 plan business validation 检查 entry-zone、SL/TP 与当前 LONG `average_cost` 的保护关系（`stop_loss < average_cost < take_profit`）；Safe Mode Recovery 与普通 Resume 都以此证明 OPEN Position 真实受保护，不能以 raw/corrupt row 或错误 RESOLVED Incident 放行。
- `safe_mode_recovery()` 仅在 durable protection、reconciliation、health 与 fresh core-data gate 均通过后，resolve blocking incident 并落到 `PAUSED`；随后 manual Resume 才可进入 `RUNNING`。
- 新增 4 个真实 PostgreSQL 回归：corrupt payload / payload identity mismatch 拒绝、可解析但 LONG protection relationship 非法拒绝、修复为有效 plan 后恢复到 `PAUSED` 并 resolve incident、错误手工 resolve Incident 后 Resume 仍拒绝直至有效保护和健康条件恢复。
- PENDING PRODUCT DECISION：V1 是否正式定义 `TradePlan.invalidation` 为 AI/human-readable advisory text，而 `stop_loss` 为唯一 machine-enforceable hard invalidation；本轮保持冻结现状，未开发自然语言 invalidation parser。

### Post-Review Fix #4

- OPEN LONG durable protection 不再要求 `stop_loss < average_cost < take_profit`；利润锁定止损（例如 cost=100、stop=110、TP=140）在 Fresh bid=120 时是有效保护。
- 保持 fail-closed：ACTIVE row 必须唯一、payload 可解析且身份一致、TTL 有效、entry zone 合法、SL/TP 有限且 `stop_loss < take_profit`。
- 新增 PostgreSQL 回归覆盖利润锁定止损的 Safe Mode Recovery → `PAUSED`、随后 manual Resume → `RUNNING`，以及 `stop_loss >= take_profit` 仍拒绝；corrupt payload、identity mismatch、expired、duplicate ACTIVE 行为不变。
- 本次验证：G4 `45 passed`、G3 `10 passed`、全量 `72 passed, 1 warning`；Ruff、compileall、`git diff --check`、Alembic current/heads 与 paper-only Restart Smoke 均通过。

## Group 5-0 Result

- G5-0（Repository Context + Context Isolation Protocol）已完成。
- 落地 `AI_CONTEXT.md`（上下文入口 / Context Index）；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- Accepted Main SHA = `c366d078e86d2ee5637c81a88cc7773686646556`（当前 main HEAD）；G4 implementation acceptance basis = `534dfad0f072553f18b8b687c20a48bf9914ee14`（G4 源码）。
- 无业务代码 / schema / API / UI / Runtime 修改；未实现 Replay / ReplayClock Engine。
- 状态：`G5-0 ACCEPTED`；G5 feature implementation 尚未开始（NOT STARTED）。

## Acceptance Record

- Group 1 = `ACCEPTED`；Group 2 = `ACCEPTED`；Group 3 = `ACCEPTED`；Group 4 = `ACCEPTED`。
- G3 Post-Acceptance Fix = `ACCEPTED`。
- FG-A — G3 Execution Authority & Freshness = `ACCEPTED / COMPLETE`（implementation
  `a9c2cd64bea0c6cc43b1ef8ad890e4db5353b801`；C04
  `d574e242f3aa7c26658ed6cc780fd8f744dbf503`；isolated Final Gate PASS）。
- C04 — Alembic Replay Test Isolation Fix = `ACCEPTED / COMPLETE`。
- Group 5-0 = `ACCEPTED`（G5 feature implementation NOT STARTED）。
- Group 5-3 = `ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Implementation Acceptance Basis = `f4c07333600f605cbcc5e34b591659feb1b1f318`；Review Fix #1 = VERIFIED）。
- G5-4 = `ACCEPTED`（Formal Acceptance Closeout 2026-09-06；Production Implementation Basis = `8678b2927a2d029ac0767e49acc9e0732c329bfa`；Self Review Fix #1 Evidence = `fe610c1f23457ff11f2d5c8654e9de0aec4ff289`）。
- G5 overall = `ACCEPTED / COMPLETE`。
- FG-E / N02 = `ACCEPTED / COMPLETE`（Human Acceptance confirmed；accepted implementation
  `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`；N02-1～N02-14 evidence PASS；Final Acceptance
  Closeout 已将 accepted lineage fast-forward 至 `main`）。

## Group 5-1 Result

- G5-1（Deterministic Replay Foundation）实现：已验证 ordered normalized input，以 `received_time` 推进 `ReplayClock`，并复用既有 G2 Rolling → Scanner → Lifecycle → State Machine → Strategy → EventRuntime 链路。
- 每次 replay 使用全新的 `InMemoryG2Repository`；未修改 PostgreSQL schema，未向 PostgreSQL G2 tables 写入 replay 数据。
- `OpportunityScanner`、`ScannerPipeline` 与 `StrategyEngine` 允许注入 Clock，默认仍使用 `SystemClock`；Replay business timestamps 使用同一个 `ReplayClock`。
- 新增 G5-1 定向测试，覆盖 received-time clock、稳定同时间顺序、回退 fail-fast、三种 Normalized event、双跑 canonical trace、历史 timestamp、真实 G2 非空链路与 processing timeline 变化。
- 验证：G5-1 `9 passed`；G1/G2 `15 passed`；G3 `10 passed`；G4 `45 passed`；full backend `81 passed, 1 warning`；Ruff、compileall、`git diff --check` 通过。
- 状态：`G5-1 IMPLEMENTED / WAITING REVIEW`（未自行 Acceptance，未 merge `main`）。

## Group 5-2 Result

- G5-2（Trading Replay Integration）实现：独立 PostgreSQL Replay workspace、`RunMode.REPLAY`、`ReplayWorkspaceGuard`、`ReplayMarketState` 与 Recorded G3/G4 provider；复用 Postgres G2、G3 Decision/Plan/Paper Execution、G4 Risk Gate/Safety/Protection/Re-evaluation。
- Replay Workspace Guard 真实比较 primary/replay `current_database()`、验证 `alembic_version=20260905_0004`，并对关键 G2/G3/G4 business tables 的残留数据 fail closed；runner 在前后比较 primary row counts。
- Replay business timestamps 通过 `ReplayClock` 注入 G3 Snapshot/Decision/Plan/Execution 与既有 G4 path；G4 默认随机 review snapshot ID 保持不变，Replay path 单独注入稳定 ID factory 以严格匹配 recorded review。
- 定向真实 PostgreSQL 集成覆盖 primary identity/dirty workspace 拒绝、未来 BBO 不可见、G3 缺失 record fail-closed、真实 Kline G2 SETUP 完成后才进入 G3、已有 Position 的 BookTicker G2→G4 且不触发 G3、最近 20 条 Timeline 的截断/正序、真实 G2 SETUP→G3→Risk→BUY Fill→G4 HOLD→SL protective SELL→closed Trade/Ledger、G2/G3/G4 历史业务时间及 outbound HTTP construction guard。
- 验证：G5-2 `7 passed`；full backend `88 passed, 1 warning`；Ruff、compileall、`git diff --check` 通过；Alembic current/heads=`20260905_0004 (head)`。
- Schema migration：未新增；Live、OKX、真实 AI、Performance Analytics、G5-3：未实现/未调用。
- 状态：`G5-2 ACCEPTED`（人工 Acceptance 正式确认；Implementation Acceptance Basis = `2a7d0c858c70f21215a090ee3b583d341cfd84b4`）。
- Acceptance Closeout（2026-09-06）：Reviewer Result = `ACCEPTED`；Review Fix #1 = `VERIFIED`。详见 `dev_log/2026-09-06-group5-2.md`「Formal Acceptance Record」。
- 当前 Accepted Baseline：以 Git `main` / `origin/main` 为准（CIP-02 preflight 实时读取），不以本文静态 SHA 为准。

### Group 4 Acceptance

- Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- G4 implementation acceptance basis = `534dfad0f072553f18b8b687c20a48bf9914ee14`。
- Position Safety + Recovery 已正式 `ACCEPTED`。
- Real AI Provider = `DEFERRED / NOT VERIFIED`（原因：`OPENAI_API_KEY` 缺失，无 `.env`；测试用 deterministic Fake Provider）。此项 non-blocking。
- Current next state = `G5 initialized / G5-0 complete`（G5 feature implementation not started）。

## Group 5-3 Result

- G5-3（End-to-End Determinism）实现：新增 `g5/canonical.py`（22 表 canonical durable workspace snapshot + SHA-256 digest + 诊断 diff）、`ReplayTradingResult.workspace_digest` 增补；三独立 PostgreSQL workspace（Run A/B/C）证明 `snapshot(A)==snapshot(B)`、`Digest(A)==Digest(B)`、`Digest(A)!=Digest(C)`（C 变异 protective-stop bid 89→88），经济差异定位到 `fills.fee` 与 SELL fill price。
- 本批同时按 Reviewer 授权对已验收 G4 做最小确定性修正：SignalTimeline `event_time DESC, timeline_id DESC LIMIT 20`（reversed 后 `event_time ASC, timeline_id ASC`）、OPEN orders `created_at ASC, order_id ASC`；并修正 G5-2 fixture t6 review 触发器为 `state_version_changed`、加固 recorded G4 HOLD 消费断言。
- 验证：G5-3 `3 passed`、G5-2 `7 passed`、G4 `46 passed`、full backend `92 passed, 2 warnings`；Ruff / compileall / `git diff --check` 通过；Alembic primary 与 disposable replay `current`/`heads` = `20260905_0004`；PYTHONHASHSEED 0/12345 跨进程 digest 一致。
- 审计残留已关闭（Review Fix #1 = VERIFIED）：
  - Review Fix #1 已解决三处 Replay-reachable OPEN BUY cancellation ordering（`g4/protection.py`、`g4/reevaluation.py`、`g4/planning.py`）；
  - 三处均使用 `ORDER BY created_at ASC, order_id ASC`；
  - canonical representation collision（typed value→string 折叠）已以无歧义类型标记编码解决；
  - 无 remaining G5-3 determinism blocker。
- Schema migration：未新增；Live、OKX、真实 AI、Performance Analytics、G5-4：未实现/未调用。
- 状态：`G5-3 ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Implementation Acceptance Basis = `f4c07333600f605cbcc5e34b591659feb1b1f318`；Review Fix #1 = VERIFIED）。详见 `dev_log/2026-09-06-group5-3.md`「Formal Acceptance Record」。

### G5-3 Review Fix #1（Reviewer = CORRECTION REQUIRED）

- P0-1：三处 Replay 可达取消 OPEN BUY 路径补 `ORDER BY created_at ASC, order_id ASC`（`g4/protection.py::_cancel_risk_increasing`、`g4/reevaluation.py::_cancel_adds`、`g4/planning.py::cancel_stale_risk_increasing`），仅确定性排序，不改取消资格/订单语义/reservation 释放/G4 业务规则/Risk。新增 3 个 PostgreSQL 回归验证持久化 `PositionEventRecord.payload["cancelled_order_ids"]` 稳定排序。
- P0-2：`g5/canonical.py::canonicalize_value` 从「typed value 折叠 string」改为无歧义类型标记编码（`["null"]`/`["bool",v]`/`["int",v]`/`["str",v]`/`["float",hex]`/`["decimal",str]`/`["datetime",UTC ISO]`/`["enum",...]`/`["object",[[k,v]...]]`/`["array",[...]]`），`first_snapshot_difference` 感知 tagged 结构保持语义 path，主键列值保持原始可哈希标量。新增碰撞回归（float vs 相同 hex 文本、Decimal vs 相同串、datetime vs 相同 ISO 文本、`["float",...]` vs 真实 float、shape-like-marker object vs 真实值）。无 schema 变更。
- 验证：G5-3 `5 passed`、G4 `49 passed`、G5-2 `7 passed`、全量 `97 passed, 2 warnings`；Ruff/compileall/`git diff --check` 通过；Alembic primary=`20260905_0004 (head)`；DigestA=`487c96806b7666ab565f26f2796a42ec689d82eec36b68e799d090dea18b4694`、DigestC=`171c2ff9dafe836744997ab4f5f621c1f4d09c5c2c9c7e18e16a772a2f13ab97`（A==B、A!=C）；recorded G4 HOLD 真实消费（`model=replay-recorded-g4`、`error=None`）；PYTHONHASHSEED 0/12345 跨进程 digest 一致。
- 状态：Review Fix #1 = `VERIFIED`；G5-3 已随 2026-09-06 Formal Acceptance Closeout 整体 `ACCEPTED`（见上）。

## Group 5-4 Result

- G5-4（Deterministic Replay Evaluation）实现：新增 `g5/evaluation.py`（`ReplayEvaluationReport`、
  `ReplayEvaluationError`、`evaluate_replay_workspace(...)`）；`ReplayTradingResult` additive 增补
  `evaluation` 字段；`ReplayTradingRunner.run()` 增补
  `capture workspace → workspace_digest → evaluate durable workspace → verify primary unchanged`。
- Evaluation 只从 Replay PostgreSQL durable facts 读取；所有 float 聚合为 primary-key 排序 +
  `math.fsum()`；读取事务为 `REPEATABLE READ, READ ONLY`；`evaluation_digest` 复用 G5-3
  `canonicalize_value()`，输入排除 `workspace_digest` 与自身。
- 会计语义：`account_realized_pnl`（仅 SELL realized，已扣 SELL fee）、`total_fees`（BUY+SELL fill fee）、
  `ledger_cash_delta`（全部 ledger cash 变动）三项分别报告，未创建 `profit` / `net_profit` 合并字段；
  未修改 G3 settlement semantics。
- 验证：G5-4 `7 passed`；G5-3+G5-2+G5-1 `21 passed`；G1/G2+G3 `25 passed`；G4 `49 passed`；
  全量 `104 passed, 1 warning`；Ruff / compileall / `git diff --check` 通过；
  Alembic primary `current`/`heads` = `20260905_0004 (head)`。
- Determinism：三独立 PostgreSQL workspace A(89)/B(89)/C(88) 证明
  `Evaluation(A)==Evaluation(B)`、`EvaluationDigest(A)==EvaluationDigest(B)`、
  `WorkspaceDigest(A)==WorkspaceDigest(B)`、`EvaluationDigest(A)!=EvaluationDigest(C)`；
  workspace digest 与 G5-3 文档值一致（说明未改变 G5-3 行为）。
- 经济敏感性（A/C）：`sell_filled_notional`、`total_fees`、`ledger_cash_delta`、
  `account_realized_pnl`、`final_cash_balance` 五项均真实变化；A/B/C 生命周期仍合法
  （`closed_trade_count=1`、`open_trade_count=0`、`exit_reason=(('STOP_LOSS', 1),)`）。
- Fail-closed 证据：test-local 篡改 fill fee → `ReplayEvaluationError`
  （`accounting inconsistency: fill fees do not match ledger fees`）。
- Open-position 证据：protective exit 前结束的独立场景 `open_position_count=1`、
  `open_quantity=9.995002498750624`、`open_trade_count=1`、`closed_trade_count=0`、`is_flat=False`。
- 隔离证据：primary counts 前后一致；outbound HTTP client 构造 `0`；Real AI / OKX 调用 `0`。
- Schema migration：未新增；`replay_run_id` / `backtest_id`：未引入；Evaluation Report：未持久化。
- 状态：`G5-4 ACCEPTED`（2026-09-06 Formal Acceptance Closeout；G5 overall = `ACCEPTED / COMPLETE`）。
  详见 `dev_log/2026-09-06-group5-4.md`。

## Product Requirements Baseline（PRB-01）

- 任务：PRB-01 — Establish Stable Product Requirements Baseline（Documentation / Governance Only）。
- 新建根目录 `PRODUCT_REQUIREMENTS.md`：长期产品需求基线（Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction）。
- 同步入口：`AI_CONTEXT.md` 增加 `PRODUCT_REQUIREMENTS.md` 产品基线指针；`AGENTS.md` 开工检查加入 `PRODUCT_REQUIREMENTS.md`。
- 本任务 Scope：仅文档；不修改 Backend / Frontend / Tests / Schema / Migration / 交易行为 / Risk / Scanner / AI Provider / G2–G5 Runtime；不把未来能力写成当前已完成；不静默覆盖 `DECISIONS.md`。
- 状态：`ACCEPTED / COMPLETE`（Independent Re-Review = `PASS / READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED`；Acceptance Fix #1 = `CLOSED`）。
- 分支：`prb-01-product-requirements-baseline`（基于 `main` = `ac3eaf9…`）；Acceptance Fix #1 Commit = `28de04a5b86e84840fb79d0774957f8312b6144e`；Final Acceptance / Baseline Commit = 其后继 commit（SHA 见本任务 dev_log 与 Closeout Report）。
- Accepted Main before = `ac3eaf911b9841f353db53d4ae21e7336af90e37`；Accepted Main after = PRB Final Accepted Commit（`main` 已 fast-forward，仅 fast-forward）。
- Product behavior changed = `NO`；Repository baseline established = `YES`。
