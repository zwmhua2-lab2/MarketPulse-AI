# MarketPulse AI Project State

## Current Group

SE-02A — Contracts + Additive Persistence — ACCEPTED / COMPLETE

SE-02B — Opportunity Capture + Attribution — ACCEPTED / COMPLETE

SE-02C — Forward Outcome Calculator — NOT STARTED

SE-02D — Family Aggregation / Expectancy — NOT STARTED

N01-C — Restart / Recovery / Reconciliation — ACCEPTED / COMPLETE

N01-A — Deterministic Runtime + Resource Lifecycle — ACCEPTED / COMPLETE

N01-6 — 15-minute Short Runtime Smoke — ACCEPTED / COMPLETE

N01-7-F01 — Durable Protection Snapshot（N01-7 前置 Fix）— ACCEPTED / COMPLETE

N01 overall — NOT ACCEPTED（`N01-7-F01 = ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance
Confirmed + Final Main Integration）；`N01-7 = NOT STARTED / READY TO RESUME`；N01-8 与
Integrated Runtime Host 仍 `NOT STARTED`；N01-6 的验收不得推断 Continuous Runtime / soak /
7x24 / Integrated Runtime Host）

## GitHub Repository

- GitHub Repository Full Name: `zwmhua2-lab2/MarketPulse-AI`
- GitHub Repository URL: https://github.com/zwmhua2-lab2/MarketPulse-AI
- Visibility: `PRIVATE`
- Default Branch: `main`
- Accepted Main Source: Git `main` / `origin/main` — read actual SHA at task preflight（CIP-02）
- Current Development Status: `SE-02B ACCEPTED / COMPLETE`（2026-09-12 Human Acceptance &
  Final Acceptance Closeout，已 fast-forward only 收编 `main`）；`SE-02A ACCEPTED / COMPLETE`；
  `N01-7-F01 ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance Confirmed + Final Main
  Integration，已 fast-forward only 收编 `main`）；`N01-C ACCEPTED / COMPLETE`；
  `N01-6 ACCEPTED / COMPLETE`；N01-A / N01-B 与
  `N01-VAL-FIX-01/02/03` 均维持已验收结论，N01 overall 仍未验收；
  `SE-02C / SE-02D = NOT STARTED`

## Branch / Source

- Current Accepted Branch: `main`
- Current Group Branch: `n01-c-restart-recovery-reconciliation`（N01-C accepted validation
  lineage；仅 fast-forward 收编至 `main`，历史分支保留）；最近新增 SE-02A accepted lineage
  `se-02a-final-integration-refresh`、N01-6 accepted lineage `n01-6-15m-runtime-smoke` 与
  SE-02B accepted lineage `se-02b-opportunity-capture-attribution`
  （三者均仅 fast-forward 收编至 `main`，历史分支保留）
- Last Accepted Group Branch: `n01-c-restart-recovery-reconciliation`（历史证据，保留未删）；更早 `n01-a-runtime-resource-lifecycle`、`n01-b-okx-paper-safety-continuity`
- Accepted Main Source: Git `main` / `origin/main` — read actual SHA at task preflight（CIP-02）
- G5-1 Implementation Acceptance Basis: `34da62a0cc9dbe95b95faadb770fbd06179a6975`
- Migration Head: `20260912_0006`（SE-02A `20260911_0005` Edge evidence + F01
  `20260912_0006` Position Protection Snapshot；`alembic heads` 实测单 head）
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
- N01-C — Restart / Recovery / Reconciliation：`ACCEPTED / COMPLETE`（Independent Review =
  `PASS / READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED`；Task Base / verified
  remote `main` = `6cc4c36e11c380f638872598e4766a4436d0d255`；branch
  `n01-c-restart-recovery-reconciliation`；isolated worktree
  `E:\Documents\MarketPulse-AI-n01-c`）。新增离网 deterministic cross-process validation：每个
  disposable PostgreSQL scenario 以 Process A durable `LIVE_PAPER` BTC-USDT LONG / plan /
  pending BUY / old heartbeat 后完全退出，再由 fresh Process B 从 PostgreSQL重建 RecoveryManager。
  覆盖 EXECUTION_GAP、official detector-only reconciliation、valid/invalid recovered BUY、HOLD /
  current-BBO SL exit、SAFE_MODE、PAUSED operator intent、BBO failure fail-closed、second-recovery
  economic idempotency，以及 client ownership cleanup / database drop。Final Gate：focused `6 passed`、
  lifecycle `6`、N01-B `4`、G2 `30`、G3 `16`、G4 `77`、full backend `179 passed, 1 warning`
  （exclusive writer evidence）；Ruff / compileall / diff-check PASS。`Production Code Changed = NO`。
  仅 fast-forward 收编至 `main`；不构成 N01 overall 或 N01-6/7/8 / Integrated Runtime Host 结论。详见
  `dev_log/2026-09-11-n01-c-restart-recovery-reconciliation.md`。
- N01-VAL-FIX-01 — PostgreSQL Lifecycle Evidence Stability：`ACCEPTED / COMPLETE`
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
- N01-VAL-FIX-02 — N01-B PostgreSQL Activity Evidence Stability：`ACCEPTED / COMPLETE`
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
- N01-VAL-FIX-03 — G4 Protection / Limit-Fill Assertion Uniqueness：`ACCEPTED / COMPLETE`
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
- N01 验证修复 Consolidated Final Acceptance Closeout：`ACCEPTED / COMPLETE`（2026-09-11；
  Independent Review = `PASS`；Human Acceptance = `CONFIRMED`）。N01-VAL-FIX-01 / FIX-02 / FIX-03
  的最终收尾门在本窗口重新执行：lifecycle `6 passed`、N01-B `4 passed`、G2 `30`、G3 `16`、
  G4 `77`、目标并发测试连续 `10/10`、full backend `173 passed` ×2（**带进程 + `pg_stat_activity`
  客户端会话采样 exclusivity 证据，全程无外来写者**）；Ruff / compileall / `git diff --check`
  （工作树 + range）PASS；`Production code changed = NO`。三个 Fix 的 devlog 均已追加
  `Consolidated Final Acceptance Closeout` 章节。accepted lineage（仅 fast-forward）：
  `e0dab188 → 67b0cb5 → 14f387a → 13049a0 → Consolidated Closeout Commit`；investigation branch
  `investigate/n01-g4-protection-limit-fill-race`（`201d9a8`）**保留、不 merge**。
- Group 4（持仓安全与恢复）已实现：Position Protection（SL/TP/Protective Exit/幂等）、Position Re-evaluation（HOLD/ADD/REDUCE/CLOSE/CANCEL_ADD/UPDATE_STOP/UPDATE_TP/UPDATE_INVALIDATION/REPLACE_PLAN）、System Safety State、Control（Pause/Resume/Emergency Stop/Emergency Recovery/Symbol Block/Manual Close/Safe Mode）、Recovery Manager（PostgreSQL SoT + Restart Recovery + Reconciliation Gate + Plan/Order Revalidation + EXECUTION_GAP）、Health Registry 与 Incident Manager。
- SE-02A｜Contracts + Additive Persistence：`ACCEPTED / COMPLETE`（2026-09-11/12；专项
  SE｜Strategy & Trading Edge 的第一个 Implementation Acceptance Batch；Independent Review =
  `PASS`；Human Acceptance = `CONFIRMED`）。只落地 Edge domain contracts 与 4 张 additive Edge 表
  + Alembic `20260911_0005`；**未**接 runtime capture、**未**实现 forward outcome calculator、
  **未**修改 G2/G3/G4/G5 业务语义。Final Acceptance Closeout 为 docs-only；accepted lineage
  （仅 fast-forward）：`b3ac21b → 2e7bf6a → 134aec5 → Final Closeout Commit`。
  Closeout 阶段 `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO`
  / `Contract changed = NO`。详见 `dev_log/2026-09-11-se-02a-edge-contracts-persistence.md`
  与本文「SE-02A Result」。
- N01-6｜15-minute Short Runtime Smoke：`ACCEPTED / COMPLETE`（Task Base / Accepted Main
  = `ab4bf297dff42a673d8dbf204dee8e4c0574aff9`；branch `n01-6-15m-runtime-smoke`；isolated worktree
  `E:\Documents\MarketPulse-AI-n01-6`；Independent Review = `PASS`；post-review docs-only
  Incremental Re-Review（`db3a0dc..3f591a7`）= `PASS`；Human Acceptance = `CONFIRMED`；
  Reviewed HEAD = `3f591a7694bf9e03dda53708a92c048dcea75fb3`）。以真实 OKX 公共行情（BTC-USDT +
  ETH-USDT SPOT，`trades` + `bbo-tbt`）+ 真实 disposable PostgreSQL（`marketpulse_n01_6_05c4a7071a16`，
  drop 后残留 0）让**已验收生产运行时组件**（`ScannerPipeline → OpportunityScanner → EventRuntime →
  PostgresG2Repository` + `SafetyRuntime`/`PositionProtectionService`/`SystemRiskGate`）连续运行
  **`900.143 s`**；normalized 事件 `24540`；queue 高水位 `0`、inflight 高水位 `1`、dedupe 峰值
  `4250`（cap 8192）、worker_exceptions `0`；RSS 峰值 `114.758 MB`（+3.18 MB）；max other client
  sessions `0`；`stale_periods=[]`；通过正式路径完成一笔受控 `LIVE_PAPER` BTC-USDT SPOT LONG 并
  在关停前 `MANUAL_CLOSE` 平仓（entry ask `77793.8` + 5 bps = `77832.6969`；exit bid `77838.6` −
  5 bps = `77799.6807`；trade `CLOSED`；cash `9999.7576`；reserved `0`）；reconciliation 12/12
  invariants PASS。Final Acceptance Closeout 复验门：focused `16 passed`、collect `267`、
  full backend `267 passed, 1 warning`（连续 PG 会话采样 114 样本 + 前后进程扫描，无外来写者）；
  Ruff `All checks passed!` / compileall rc=0 / `git diff --check`（工作树 + `ab4bf29..HEAD`）rc=0。
  Closeout 四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Harness changed = NO` / `Migration changed = NO`。accepted lineage（仅 fast-forward）：
  `ab4bf29 → db3a0dc → 3f591a7 → Final Closeout Commit`；evidence branch
  `n01-6-15m-runtime-smoke` 保留。详见
  `dev_log/2026-09-12-n01-6-15m-runtime-smoke.md`。

- SE-02B｜Opportunity Capture + Attribution：`ACCEPTED / COMPLETE`（2026-09-12 Human Acceptance &
  Final Acceptance Closeout；Independent Review = `PASS`；Human Acceptance = `CONFIRMED`；
  Human-Accepted reviewed tip = `6ce0c9214f552c0173e1f925315102506c3e9078`；branch
  `se-02b-opportunity-capture-attribution`；isolated worktree `E:\Documents\MarketPulse-AI-se-02b`；
  Task Base / Accepted Main before = `af81414160248c97f59a63b31fe615ea8ae14bbe`）。落地
  ① G2 SETUP Opportunity Capture（与 durable G2 facts **同一 PostgreSQL 事务**、atomic /
  fail-closed、immutable / append-only，遵循 SE-02A identity + hash + revision 契约）与
  ② Attribution（`Opportunity → AI → Plan → Risk → Execution → Economic Result`；append-only；
  exact authority / reason；显式 AI family selection；deferred LIMIT per-order restart-safe 归因）；
  新增 `backend/src/marketpulse/edge/capture.py` / `edge/attribution.py`，对 `g2/repository.py` /
  `g3/service.py` 仅做纯增量接线。**无新 migration**（head 仍 `20260911_0005`）。
  Acceptance blocker 由 SE-02B-FIX-01（P0-2 / P0-3 / P0-4 + P1）与 SE-02B-FIX-02
  （P0-1 Reference Quote Quality & Provenance，payload `se02b-runtime-capture-v2 → v3`）闭合后
  Independent Review = `PASS`。accepted lineage（仅 fast-forward）：
  `af81414 → f261766 → 7e86757 → b8a5fe3 → 0b8a275 → 6ce0c92 → Final Closeout Commit`。
  Closeout 阶段四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Contract changed = NO`。
  ⚠️ 本验收**不**构成 SE-02C / SE-02D / Forward Outcome Calculator / MFE-MAE / expectancy /
  Real AI Edge / Live / N01-7 / N01-8 / Integrated Runtime Host 的任何进度。
  详见 `dev_log/2026-09-12-se-02b-final-acceptance-closeout.md` 与本文「SE-02B Result」。

- N01-7-F01｜Durable Protection Snapshot（N01-7 前置 Fix）：`ACCEPTED / COMPLETE`（2026-09-13
  Human Acceptance = `CONFIRMED`（人工原文「确认 N01-7-F01 Human Acceptance，并执行 Final Main
  Integration」）+ Final Main Integration）。Reviewed candidate =
  `7c0ea7dd88c55fff301bfeef795088f44313c7d8`（branch `n01-7-f01-latest-main-integration`）；
  integration merge = `ddf39f2`（true merge：parent1 = 最新 main `1579707`，parent2 = 已复审
  F01 源 `c0ce0af`；`Reviewed Source Preserved = YES`）；Final Independent Review = `PASS`；
  R2 Independent Re-Review = `PASS`；Integration Review = `PASS`；
  E1 Writer Attribution = `FOREIGN WRITER CONFIRMED`；原始 shared-primary 指纹门
  = `INVALIDATED BY ENVIRONMENT / NON-BLOCKING`（**非** product failure）。
  既有验证据（**未**重跑）：F01 migration gate `PASS`、集成定向 `271 passed`、full backend
  `341 passed, 1 warning`、ruff / compileall / `git diff --check` `PASS`。
  Final Acceptance Closeout 为 docs/state-only：`Production code changed = NO` /
  `Tests changed = NO` / `Migration changed = NO`；`alembic heads` 单 head `20260912_0006`；
  accepted lineage 仅 fast-forward（`ddf39f2 → 7c0ea7d → Final Acceptance Closeout Commit`）。
  ⚠️ 本验收**不**构成 N01-7 2h soak / N01-8 / Integrated Runtime Host / Continuous Runtime /
  7×24 / Real AI Edge / Live 的任何进度；`N01 overall` 仍 `NOT ACCEPTED`。详见
  `dev_log/2026-09-13-n01-7-f01-final-acceptance-closeout.md` 与
  `dev_log/2026-09-12-n01-7-f01-latest-main-integration.md`。

## In Progress

- **SE-02C｜Forward Outcome Calculator = `NOT STARTED`**（forward outcome 仍未计算：无 MFE / MAE /
  无 forward returns；horizon `30s` / `5m` / `15m` / `1h` 的 calculation 尚未实现）。
- **SE-02D｜Family Aggregation / Expectancy = `NOT STARTED`**（family aggregation、expectancy、
  KEEP / DOWNWEIGHT / KILL 均未实现）。
- 两项均须另开窗口并经批准的门执行；本窗口 **不** 自动开始 SE-02C。
- **SE-02B 已关闭**：`ACCEPTED / COMPLETE` 并已 fast-forward only 收编 `main`（见 Completed、
  Acceptance Record 与「SE-02B Result」）；其 3 个历史状态项
  （`IMPLEMENTED / WAITING HUMAN ACCEPTANCE`、SE-02B-FIX-01 / FIX-02
  `READY FOR INDEPENDENT RE-REVIEW`）已由本次 Final Acceptance Closeout 取代。
- **SE-02A｜Contracts + Additive Persistence 已完成验收收尾
  （`ACCEPTED / COMPLETE`；见 Completed 与本文「SE-02A Result」）**。其 reviewed implementation
  source = branch `se-02a-contracts-additive-persistence` @ `0c206c9`；最终收编经 refresh
  integration branch `se-02a-final-integration-refresh`（`b3ac21b → 2e7bf6a → 134aec5 →
  Final Closeout Commit`，仅 fast-forward）。SE-02C / SE-02D / Forward Outcome Calculator /
  Real AI Edge / Live 仍 **NOT STARTED**；runtime opportunity capture 已由 SE-02B 落地
  （`ACCEPTED / COMPLETE`，见上）。
- **N01-7-F01｜Durable Protection Snapshot（N01-7 前置 Fix）= `ACCEPTED / COMPLETE`**
  （2026-09-13 Human Acceptance = `CONFIRMED` + Final Main Integration；branch
  `n01-7-f01-latest-main-integration`；integration merge commit `ddf39f2` = 最新 main `1579707` ×
  已复审 F01 源 `c0ce0af`，true merge、`Reviewed Source Preserved = YES`；已 fast-forward only
  收编 `main`；见 Completed、Acceptance Record 与
  `dev_log/2026-09-13-n01-7-f01-final-acceptance-closeout.md`）。
- **`N01-7 = NOT STARTED / READY TO RESUME`**（2-hour Medium Runtime Soak 尚未启动；
  重启前须做一次全新 Repository Truth rebuild，并以实时 `origin/main` 为 Accepted Main）。
- **`N01-8 = NOT STARTED`**；**`Integrated Runtime Host = NOT STARTED`**。
- **N01-A / N01-B / N01-C / N01-6 / N01-7-F01 均已 `ACCEPTED / COMPLETE`**（见 Completed）；
  N01 overall 仍未验收，也不由任何单门 N01 验收推断。
- N01 Continuous Runtime / Soak 本身仍 `NOT ACCEPTED`；不得由 N01-B / N01-6 验收推断 N01 整体验收。
- N01-6 15m Runtime Smoke 已完成 Final Acceptance Closeout 并 `ACCEPTED / COMPLETE`（见 Completed 与
  `dev_log/2026-09-12-n01-6-15m-runtime-smoke.md`）。N01-7 2h Soak、N01-8 12h Soak 与
  Integrated Runtime Host 仍 `NOT STARTED`，须另开窗口并按各自批准的门执行。

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

- 原「Pre-existing flaky test」（`N01-G4-F01`）**根因已定位、已修复、已验收、已收入 `main`**：
  `backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`
  在负载下的 full-suite 上下文中可能失败（`assert order.status == OrderStatus.CANCELLED ... got
  FILLED`，`test_group4.py:1709`）。分类 = **Case B — Test Assertion Scope / Ambiguous Read
  Defect**（**非** production concurrency defect）：pending LIMIT BUY 与 protective exit SELL
  合法共享同一 `plan_id`，而断言用非唯一 `plan_id` 谓词 + `Session.scalar()`（多行静默取首行）+
  无 `ORDER BY`，故结果依赖物理堆序。N01-G4-INV-01 已以 PostgreSQL lock evidence 确证；N01-VAL-FIX-03
  改为按唯一 `order_id` 读取并强化断言，`N01-VAL-FIX-03 = ACCEPTED / COMPLETE`（目标测试 20/20 + 收尾门连续 10/10、full backend
  监控下 `173 passed` ×2），并已随 Consolidated Final Acceptance Closeout fast-forward 收入
  `main`。证据见
  `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md`。
- **环境级约束（`KNOWN TEST-ENVIRONMENT CONSTRAINT` / NON-PRODUCTION / NON-BLOCKING）**：本仓库
  全量套件使用**单一共享 PostgreSQL 数据库**，且
  `Harness.clean()` 会整表清空 `RunMode.REPLAY` 行 ⇒ **任何两个并发会话在全量套件层面必然互相
  破坏**（观测签名：`open_position()` 得到 `PLAN_REPLACED`，因另一写者替换了同
  `(run_mode, instrument_id)` 的 ACTIVE plan）。N01-VAL-FIX-03 的 full-suite 门首次尝试即被另一
  WorkBuddy 会话通过 Bash 发起的 `pytest backend/tests` 污染（`10 failed, 163 passed`），
  在 N01-VAL-FIX-03 与 Consolidated Closeout 中均以「进程扫描 + `pg_stat_activity` 客户端会话
  采样」建立 exclusivity 证据后才采信；运行期间若监测到外来 writer，该 run 标记
  `INVALIDATED BY ENVIRONMENT` 并在恢复 exclusivity 后重跑（不「重试至通过」）。建议后续另开
  窗口评估（例如按会话隔离数据库或加互斥），**不在**本次 Scope 内。
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
- N01-6｜15-minute Short Runtime Smoke = `ACCEPTED / COMPLETE`（2026-09-12；Independent Review =
  `PASS`；post-review docs-only Incremental Re-Review `db3a0dc..3f591a7` = `PASS`；Human
  Acceptance = `CONFIRMED`；Reviewed HEAD = `3f591a7694bf9e03dda53708a92c048dcea75fb3`；
  accepted lineage 仅 fast-forward：`ab4bf29 → db3a0dc → 3f591a7 → Final Closeout Commit`）。
  Closeout 期间 `Production code changed = NO` / `Tests changed = NO` / `Harness changed = NO` /
  `Migration changed = NO`。**不得**由本验收推断 2h soak / 12h soak / Continuous Runtime 全量验收 /
  7×24 Runtime / Integrated Runtime Host。
- SE-02B｜Opportunity Capture + Attribution = `ACCEPTED / COMPLETE`（2026-09-12；Independent Review =
  `PASS`；Human Acceptance = `CONFIRMED`；Human-Accepted reviewed tip = `6ce0c92…`；accepted lineage
  仅 fast-forward：`af81414 → f261766 → 7e86757 → b8a5fe3 → 0b8a275 → 6ce0c92 → Final Closeout
  Commit`）。Closeout 期间 `Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Contract changed = NO`。**不得**由本验收推断 SE-02C / SE-02D /
  Forward Outcome Calculator / MFE-MAE / expectancy / Real AI Edge / Live / N01-7 / N01-8 /
  Integrated Runtime Host。
- N01-7-F01｜Durable Protection Snapshot（N01-7 前置 Fix）= `ACCEPTED / COMPLETE`（2026-09-13；
  Human Acceptance = `CONFIRMED`（人工原文「确认 N01-7-F01 Human Acceptance，并执行 Final Main
  Integration」）；Final Independent Review = `PASS`；R2 Independent Re-Review = `PASS`；
  Integration Review = `PASS`；Reviewed candidate = `7c0ea7d…`；integration merge = `ddf39f2…`
  （true merge：`1579707` × `c0ce0af`，`Reviewed Source Preserved = YES`）；accepted lineage 仅
  fast-forward：`ddf39f2 → 7c0ea7d → Final Acceptance Closeout Commit`）。Closeout 期间
  `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO`；
  E1 = `FOREIGN WRITER CONFIRMED`（原始 shared-primary 指纹门 `INVALIDATED BY ENVIRONMENT /
  NON-BLOCKING`）。**不得**由本验收推断 N01-7 2h soak / N01-8 / Integrated Runtime Host /
  Continuous Runtime / 7×24 / Real AI Edge / Live；`N01 overall` 仍 `NOT ACCEPTED`。

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

## SE-02A Result

- 任务：SE-02A｜Contracts + Additive Persistence（专项 SE｜Strategy & Trading Edge 的第一个
  Implementation Acceptance Batch）。
- **reviewed implementation source** = branch `se-02a-contracts-additive-persistence` @
  `0c206c9c598c735d8f708db6603c02fc4d5a3fa3`（Task Base / verified Accepted Main at authoring
  time = `e0dab188e55c32b7607c18a66644d25449dc2236`）。
- **historical integration candidate**（仅作 evidence / 对照，**不**作为本次 implementation source）
  = branch `se-02a-final-integration` @ `9998e1b`（建于旧 `main` `6cc4c36`）。
- **此次 refresh integration** = branch `se-02a-final-integration-refresh`，以最新 Accepted Main
  `b3ac21b` 为基，merge reviewed source `0c206c9`（保留正常 lineage；未 rebase / 未 squash /
  未 rewrite reviewed source）。
- 新增 `backend/src/marketpulse/edge/`（`hashing.py` / `identity.py` / `models.py` /
  `repository.py`）：Opportunity / Evidence Revision / Evidence Source & Status / Forward Horizon
  （仅 `30s` / `5m` / `15m` / `1h`）/ Outcome contract types / Attribution 的 domain contracts；
  identity 采用任务规定公式；canonical hashing 复用 G5 `canonicalize_value`，未引入第二套 serializer。
- 新增 4 张 additive Edge 表与 Alembic revision `20260911_0005`
  （`edge_opportunity_evidence` / `edge_bbo_observations` / `edge_forward_outcomes` /
  `edge_attribution_events`），含 Edge 专属 index 与约束（UNIQUE、复合 supersedes FK、
  frozen family / horizon / status CHECK）。
- 语义与 immutability：同 revision 同 hash 幂等；同 revision 不同 hash `EdgeEvidenceConflict`
  fail closed；`revision > 1` 必须 supersedes 恰为 `R-1` 的同 opportunity revision，跨机会 /
  悬空 / 跳号一律拒绝；`calculation_digest` 与 `outcome_record_hash` 分离，Replay 与 Forward Paper
  provenance 不同可共享同一 calculation digest。
- 边界：**未接 runtime capture**（`SE-02B` 未开始）、**未实现 forward outcome calculator**
  （`SE-02C` 未开始）、未实现 family aggregation / expectancy（`SE-02D`）；未修改 G2/G3/G4/G5
  既有表 semantics、Risk、Execution、State Machine、G3 accounting semantics。
- 唯一 G5 改动：`g5/replay.py` 的 `schema_head` 常量
  `20260905_0004 → 20260911_0005`（migration head 派生事实，本批新 revision 使其必然过期，
  属阻塞当前 AC 的最小修复；guard 行为未变）。
- Acceptance Fix #1（关闭 3 个 contract blocker）：参考报价改为**可选**
  （`reference_bid` / `reference_ask` / `reference_received_at` 可 NULL；`OK` 要求三字段
  非 NULL 且正/有序，`REFERENCE_MISSING` / `REFERENCE_STALE` 要求三者全 NULL 且禁止 0 占位；
  `ReferenceDataReason` 删除，状态收敛为三态）；forward outcome 恢复 Approved 终态
  `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID`（**无 `PENDING` 行**，`calculation_status` 必填）
  与 `ACTIVE` / `EXPIRED` lifecycle；BBO 强制 V1 因果规则 `available_at == received_at`，
  `observation_id` 纳入 `available_at`，同 identity 但 `data_quality` / `tradable` 冲突时
  `EdgeBboObservationConflict` fail closed。migration **就地修正 `20260911_0005`**（无 0006）。
- 历史验证（reviewed source 窗口，base `e0dab188`）：SE-02A contracts **`62 passed`**、
  SE-02A persistence **`26 passed`**（真实 disposable PostgreSQL）、定向 G5-2/G5-3 + G2
  **`62 passed`**、full backend **`259 passed`**（= baseline `171` + 本批 `88`）、
  migration `0004 → upgrade head(0005) → downgrade 0004 → upgrade head(0005)` PASS、
  无残留 disposable DB、primary `marketpulse` 仍为 `20260905_0004`（未被本批升级）。
- 本次 Latest-Main Integration Refresh 的验证结果与其逐条边界见
  `dev_log/2026-09-11-se-02a-edge-contracts-persistence.md` 末尾
  「Latest-Main Final Integration Refresh」章节（含 N01-A/B/C 在 `20260911_0005` integration
  tree 下共同成立的证据）。
- **Final Acceptance Closeout（2026-09-11/12，docs-only）**：Independent Review = `PASS`；
  Human Acceptance = `CONFIRMED`。在 reviewed refresh HEAD `134aec5` 之上创建 docs-only
  closeout commit（仅 `PROJECT_STATE.md` / `AI_CONTEXT.md` / SE-02A dev_log），随后
  **fast-forward only** 将 `main` 从 `b3ac21b` 收编 `2e7bf6a → 134aec5 → Final Closeout Commit`
  （无 rebase / squash / force / history rewrite）。Closeout 最小充分复验：SE-02A focused `88 passed`
  （62 + 26）、N01-C focused `6 passed`（规范解释器 `py -3.14`）、full backend `267 passed`
  （独占窗口）、`alembic heads` 单 head `20260911_0005` 且 `g5/replay.py::schema_head` 同值、
  Ruff `All checks passed!` / compileall rc=0 / `git diff --check`（工作树 + `b3ac21b..HEAD`）rc=0。
- **Accepted Main before** = `b3ac21b89e11490a0760f560bc099b9acf91ff48`；
  **Accepted Main after** = Final Closeout Commit（`main` 已 fast-forward，仅 fast-forward）。
- Closeout 阶段四项不变：`Production code changed = NO`、`Tests changed = NO`、
  `Migration changed = NO`、`Contract changed = NO`。
- 状态：`ACCEPTED / COMPLETE`（SE-02B / SE-02C / SE-02D / runtime capture / Real AI / Live
  仍未开始，不在本批 claim 边界内）。
- 备注（Repository Truth 差异）：仓库中不存在 SE-02 设计 / approved contract 文档，本批契约依据
  为任务书与既有仓库约定；本批自行确定的契约决策已在上述 dev_log §3 逐条列出。
- 备注（主库）：本地 `marketpulse` 主库仍在 `20260905_0004`，本批**未**对其执行 migration
  （避免未经授权修改外部系统状态）；如需与 head 一致，由 Operator 执行 `alembic upgrade head`。
- 备注（基线漂移，CIP-03，非本批所致）：本 branch 的 Task Base（Accepted Main）为 `b3ac21b`
  （N01-C 已验收收尾）；此前 SE-02A 作者期的 `e0dab188` / `6cc4c36` 均已为其祖先。

## SE-02B Result

- 任务：SE-02B｜Opportunity Capture + Attribution（专项 SE｜Strategy & Trading Edge 的第二个
  Implementation Acceptance Batch）。
- **Human-Accepted reviewed branch tip** = `6ce0c9214f552c0173e1f925315102506c3e9078`
  （branch `se-02b-opportunity-capture-attribution`）。
- **Task Base / Accepted Main before** = `af81414160248c97f59a63b31fe615ea8ae14bbe`；
  **Accepted Main after** = Final Closeout Commit（`main` 已 fast-forward，仅 fast-forward）。
- **Independent Review（final）** = `PASS`；**Human Acceptance** = `CONFIRMED`。
- 交付能力：
  ① **G2 SETUP Opportunity Capture** — qualifying `BREAKOUT_RETEST` Opportunity Evidence 与 durable
  G2 facts 在**同一 PostgreSQL 事务**内写入；atomic / fail-closed；immutable / append-only；
  遵循已验收 SE-02A identity + hash + revision 契约。
  ② **Attribution** — `Opportunity → AI → Plan → Risk → Execution → Economic Result` 全链
  append-only 归因；exact authority / reason；**显式 AI family selection**
  （`selected_strategy_ids` 必须显式包含 `BREAKOUT_RETEST`，不依赖 snapshot fallback）；
  deferred LIMIT 经 durable `ORDER_OPEN` 事实做 **per-order restart-safe** 归因。
- 主要变更：新增 `backend/src/marketpulse/edge/capture.py`（含 opt-in `EdgeCaptureContext`）与
  `backend/src/marketpulse/edge/attribution.py`；`edge/__init__.py` docstring；
  `backend/src/marketpulse/g2/repository.py` 与 `backend/src/marketpulse/g3/service.py`
  仅做**纯增量**接线（keyword-only 参数 + `None` 守卫，legacy 行为不变）；新增
  `backend/tests/test_se_02b_opportunity_capture.py`（15）与
  `backend/tests/test_se_02b_attribution.py`（31）。
- **无新 migration**：`backend/alembic/` 零改动，head 仍 `20260911_0005`；
  SE-02A 冻结契约文件 `edge/{models,identity,hashing,repository}.py` / `db/models.py` 零 diff。
- Acceptance blocker 闭合链：**SE-02B-FIX-01** 关闭 P0-2（`evidence_at` 因果锚点
  = `candidate.created_at`）、P0-3（显式 AI family selection）、P0-4（deferred LIMIT per-order
  restart-safe 归因）、P1（cross-fact consistency，5 项 + negative admission matrix）；
  P0-1 判 `CHANGES REQUIRED` ⇒ 由 **SE-02B-FIX-02** 终局闭合（`ReferenceDataStatus.OK` 现要求
  `data_quality == FRESH`；不可变 payload 拆为 `supplied_quote`（被拒报价原始输入逐字保留）
  + `accepted_reference`（仅 OK 非空）；payload version `se02b-runtime-capture-v2 → v3`）。
- 验证证据（历史门，均真实执行）：SE-02B `focused 46`（capture 15 + attribution 31）；
  SE-02A 契约 + 持久化 `88`；G2 / G3 / G4 `123`；full backend `313 passed, 1 warning`
  （独占写者窗口 + 进程/PG 会话双证据）；Ruff `All checks passed!` / compileall rc=0 /
  `git diff --check` rc=0；`alembic heads` 单 head `20260911_0005`。
- **Final Acceptance Closeout（2026-09-12，docs-only）**：在 reviewed HEAD `6ce0c92` 之上创建
  docs-only closeout commit（仅 `dev_log/2026-09-12-se-02b-final-acceptance-closeout.md` /
  `PROJECT_STATE.md` / `AI_CONTEXT.md`），随后 **fast-forward only** 收编 `main`
  （无 rebase / squash / cherry-pick / force / history rewrite）。Closeout 最小充分复验：
  `git diff 6ce0c92..HEAD` 仅含上述文档 / 状态文件；`git diff --check` rc=0；
  SE-02B 定向 smoke `46 passed`；`alembic heads` 单 head `20260911_0005`。
- Closeout 阶段四项不变：`Production code changed = NO`、`Tests changed = NO`、
  `Migration changed = NO`、`Contract changed = NO`。
- 边界：**SE-02C / SE-02D = `NOT STARTED`**；Forward Outcome Calculator / MFE-MAE / forward
  returns / family aggregation / expectancy / KEEP-DOWNWEIGHT-KILL / Real AI Edge / Live /
  N01-7 / N01-8 / Integrated Runtime Host 均不在本批 claim 边界内。
- 备注：本批次**未**对共享 primary PostgreSQL 库执行任何 migration / downgrade（保留其它窗口状态）。
