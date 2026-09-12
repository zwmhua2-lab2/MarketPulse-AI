# SE-02B-FIX-01｜Acceptance Blockers Fix

> 专项 **SE｜Strategy & Trading Edge**，SE-02B 的专项执行窗口：关闭 Independent Acceptance Review
> 发现的 **4 个 P0 Acceptance Blocker + 1 个 P1 cross-fact consistency 补强**。
> 状态：`IMPLEMENTED / VERIFIED / READY FOR INDEPENDENT RE-REVIEW`（**未**自行 Acceptance，
> **未** merge `main`，**未**开始 SE-02C）。
> branch：`se-02b-opportunity-capture-attribution`；worktree：`E:\Documents\MarketPulse-AI-se-02b`。
> 统一解释器 `py -3.14`；`PYTHONPATH=backend/src`；PostgreSQL = Docker `marketpulse-postgres`。

---

## 1. Repository Truth（动作前实测）

| 项 | 实测值 |
|---|---|
| Reviewed HEAD（Fix 的 parent） | `f261766767fff5f8f3d472c1711aeb9bc951d619` |
| Fix commit | `7e86757b0fbea8c5b2af70f05ce9471fde0b498f` |
| Diff Range（reviewed → fix） | `f261766..7e86757` |
| branch | `se-02b-opportunity-capture-attribution`（未 merge `main`、未 force push、未 rebase） |
| Task Base / Accepted Main | `af81414160248c97f59a63b31fe615ea8ae14bbe` |
| Drift（CIP-03） | **无**：`git rev-parse HEAD` == reviewed `f261766`，工作树仅含本 Fix 的 6 个文件 |
| Migration Head | `20260911_0005`（**本 Fix 未新增 / 未修改任何 migration**） |
| `git diff --check` | rc = 0（仅 LF→CRLF 提示，无空白错误） |

**外部窗口观察（非本 Fix 所致，如实记录）**：主库 `alembic_version` 曾读到 `20260912_0006`。
取证：该 revision 文件 `20260912_0006_position_protection_snapshot.py` 存在于**另一 worktree**
`E:\Documents\MarketPulse-AI-n01-7-f01-wt2`（branch `fix/n01-7-f01-durable-protection-snapshot`），
其 parent = 本任务 Task Base `af81414`；内容为 `positions` 表 5 个可空列 + 3 个 CHECK，纯 additive。
与本 branch 的 `down_revision` 链无关，本 branch 的 `alembic heads` 实测仍为**单 head** `20260911_0005`。

---

## 2. Scope

| 项 | 内容 |
|---|---|
| 允许修改 | `backend/src/marketpulse/edge/{capture,attribution}.py`、`g2/repository.py`、`g3/service.py`、`backend/tests/test_se_02b_*.py`、`dev_log/`、`PROJECT_STATE.md` |
| Out of Scope（未触碰） | SE-02C / SE-02D、forward outcome、MFE/MAE、cost model、expectancy、KEEP/DOWNWEIGHT/KILL、L2/L3、UI、Dashboard、Real AI、OKX real orders、Live Trading、`backend/alembic/`、`edge/{models,identity,hashing,repository}.py`（SE-02A 冻结契约）、G4/G5、Frontend、`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md` |

未做任何顺手重构／优化；G2/G3/G4 既有语义与接口契约除批准点外未变。

---

## 3. Fixes by Finding

### P0-1｜Reference BBO causal / identity correctness

**Root cause**：`ReferenceQuote` 不携带市场身份（instrument / market type / quality / tradability），
`classify_reference` 只做「形状 + 年龄」判定 ⇒（a）别的 symbol 的 BBO 可被当作本 Opportunity 的
reference；（b）quote 晚于 evidence 锚点（future lookahead）会被当作「新鲜」；
（c）`EdgeCaptureContext` 是 run 级对象，把 quote 放在 context 里会让**一次报价沿用给之后所有
Opportunity**（构造函数/上下文级常量）。

**Fix**：

- `ReferenceQuote` 增补 `instrument_id` / `market_type` / `data_quality` / `tradable`（upstream
  不存在的字段不伪造，均由调用方显式提供）；
- 新增 `matches(instrument_id, market_type)`；`classify_reference` 顺序为
  `None → REFERENCE_MISSING`、身份不匹配 → `REFERENCE_STALE`、形状不合格 → `REFERENCE_STALE`、
  因果不合格 → `REFERENCE_STALE`、否则 `OK`；**非 OK 一律返回 `None` 作 quote**（metrics 写 NULL，禁 0 占位、禁伪造）；
- `_is_causally_available`：`0 <= at - received_at <= max_age`（future quote 必然被拒）；
- `EdgeCaptureContext` **移除** `reference_quote` 字段；quote 改为 **per-persist** 经
  `PostgresG2Repository(reference_quote_for=...)` 有界访问器注入（每 persist 读取一次，
  不跨境复用；访问器要求 in-process 无 I/O，因为它运行在 G2 事务内）；
- `RUNTIME_CAPTURE_PAYLOAD_VERSION`：`se02b-runtime-capture-v1 → v2`，`reference_data` 记录
  被拒 quote 自身身份事实以便审计（`status` / `bid` / `ask` / `received_at` / `instrument_id` /
  `market_type` / `data_quality` / `tradable`）。

**未接管 market data subsystem**：无新组件、无新表、无新 migration；quote 仍由调用方（上游）
持有并通过最小 DI 传入。

### P0-2｜evidence_at causal anchor

**Root cause**：evidence 的时间锚点未明确区分「事件收到时刻」与「机会可被知晓时刻」。

**Fix**：`evidence_at = qualifying_candidate.created_at`（`detected_at = event.event_time`、
`created_at = event.received_time` 保持不变，**未**修改 SE-02A 的 `created_at` 契约）；
reference freshness 相对 `evidence_at` 判定，future horizon（SE-02C）亦从此锚点起算。

### P0-3｜AI Family explicit selection

**Root cause**：`family_is_selected` 在 `selected_strategy_ids` 为空时回退到
`snapshot_strategy_ids`；且 `process_setup` 对「其他 family 的 LONG plan」也会归因 `PLAN_CREATED`。

**Fix**：

- 删除 snapshot 回退（`family_is_selected(*, selected_strategy_ids)` 仅认显式列表）；
  `AI_ACCEPTED_LONG` 仅在 `DecisionStatus == VALID` AND `direction == LONG_BIAS` AND
  列表**显式包含** `BREAKOUT_RETEST` 时产生 —— 空列表 + snapshot 含该 family ⇒
  `AI_NOT_SELECTED_THIS_FAMILY`；
- `G3Workflow.process_setup`：仅当显式选中本 family 时以 attribution 写 plan；
  否则**原样**调用 `persist_trade_plan(self.sessions, plan)`（plan 照常落库，只是不归因本 Opportunity）；
- `record_ai_decision` 移除 `snapshot_strategy_ids` 参数；
- **未改变 G3 业务语义**：`persist_trade_plan` 本身、plan 的创建条件与落库行为均未变。

### P0-4｜Deferred LIMIT order attribution

**Root cause**：`process_open_orders()` 用**单一外部传入 recorder** 绑定整批 OPEN orders ⇒
一个批次内多个 order 会被归因到同一 Opportunity；且进程重启后内存 recorder 不存在 ⇒ 延迟成交无法归属。

**Fix**：

- `process_open_orders(..., *, order_link_resolver: OrderLinkResolver | None = None)`
  取代原 `attribution` 参数；新增 `_deferred_order_attribution(session, order_id, *, resolver)`
  **逐单**解析；
- 新增 `link_for_durable_order(session, order_id)`：以 durable 事实
  `edge_attribution_events(subject_type=EXECUTION, event_type=ORDER_OPEN, subject_id=order_id)`
  → 唯一 `(opportunity_id, evidence_id)` → 校验 `edge_opportunity_evidence` 中该 revision 存在
  ⇒ 返回 `OpportunityLink`，否则返回 `None`（**绝不**猜测、**绝不**回落到别的 Opportunity）；
- 逐条拒绝路径接入 `_record_deferred_refusal(...)`：
  `SystemRiskGate` / `CapacityPolicy` → `RISK_REJECTED` + 精确 `authority` + 精确 `reason`；
  其余（`LIMIT_PRICE_MISSING` / `ACTION_TIME_BBO_UNAVAILABLE` / `ACTION_TIME_STATE_UNAVAILABLE` /
  `CORE_MARKET_DATA_STALE` / `CORE_POSITION_MARK_STALE` / `PLAN_MISSING` / `PLAN_EXPIRED` /
  `PLAN_NOT_ACTIVE` / `STATE_VERSION_CHANGED` / `PLAN_ORDER_MISMATCH` / `BUY_STOP_LOSS_BREACHED` /
  `BUY_PRICE_OUTSIDE_ENTRY_ZONE` / `SELL_RESERVATION_EXCEEDS_POSITION` …）→ `EXECUTION_REJECTED`；
- `ORDER_OPEN` 仍是「被准入」的证据而非成交；成功成交 → `BUY_FILLED` + exact Opportunity，
  仅首次开仓同时记 `TRADE_OPEN`；
- 拒绝事实的 `occurred_at` 使用**真正做决定的时钟**：pre-lock 准入预览用 `candidate_now`，
  action-time 守卫用 `action_now`（settlement 时间戳不冒充决策时间）；
- **restart-safe**：归因只读 durable facts，不依赖任何内存状态。

**Migration**：**NO new migration**。durable `ORDER_OPEN` attribution 事实天然提供了
restart-safe 的 linkage 锚点，现有 schema 已足够，故**未**触发 Minimal Schema Proposal，
`alembic head` 保持 `20260911_0005`。

### P1｜cross-fact consistency（negative admission matrix）

`qualifies()` 内 `_candidate_agrees()` 补齐五项一致：`candidate.symbol == event.symbol`、
`timeline.symbol == event.symbol`、`timeline.config_version == event.config_version`、
`timeline.signal_type == event.event_type`、`state.symbol == event.symbol`。
口径：G2 durable facts **照常落库**，只是**不得**被接纳为本 Opportunity 的 evidence（evidence rows = 0）。

---

## 4. 保留的既有正确行为（未回归）

同事务 G2 facts + evidence（无独立提交点）；conflict 全回滚（pre-staged / post-staged 两场景）；
同 rev 同 hash `IDEMPOTENT`、异 hash `EdgeEvidenceConflict` fail closed；append-only 无 UPDATE；
缺失 / 陈旧 BBO **不删** Opportunity（样本永在）；Risk 与 Execution 分类互不混淆；
`ORDER_OPEN != 成交`；EOB 与 forward outcome 分离（SE-02C 未触碰）；
`capture=None` / `attribution=None` 保持 legacy 行为（有专门回归测试）。

---

## 5. Adverse Tests（新增 / 更新）

`backend/tests/test_se_02b_opportunity_capture.py`（14 个，原 11）：

| 用例 | 断言 |
|---|---|
| `future`（`received_at = evidence_at + 1s`） | `REFERENCE_STALE`（future 不可当新鲜） |
| `wrong_instrument`（`ETH-USDT` quote 投给 `BTC-USDT`） | `REFERENCE_STALE`，metrics 全 NULL |
| `wrong_market_type`（`SWAP` vs `SPOT`） | `REFERENCE_STALE` |
| `stale` / `missing` / `untradable` / `crossed` / `non_positive` / `non_finite` | 各自 `REFERENCE_STALE` / `REFERENCE_MISSING` |
| `test_capture_payload_keeps_the_v2_reference_identity_facts` | v2 payload + 被拒 quote 身份可审计且 metrics NULL（非 0） |
| `test_each_opportunity_is_evidenced_only_by_its_own_reference_quote` | 同一 repository、BTC/ETH 各自用自己 quote；无 quotes 的 SOL ⇒ `REFERENCE_MISSING`（**不继承**他人 BBO） |
| `test_evidence_horizon_is_anchored_on_the_candidate_not_the_event_receipt` | 构造 `event_time < received_time < candidate.created_at`，断言 `detected_at` / `created_at` / `evidence_at` 三值分离，且以「事件收到时刻」为锚会被接受的 quote 实际被判 `REFERENCE_STALE` |
| negative admission matrix（13 → 18 项） | 新增 `candidate_symbol_mismatch` / `timeline_symbol_mismatch` / `timeline_config_version_mismatch` / `timeline_signal_type_mismatch` / `state_symbol_mismatch`，全部 `evidence rows == 0` 且 G2 照常落库 |

`backend/tests/test_se_02b_attribution.py`（31 个，原 26）：

| 用例 | 断言 |
|---|---|
| `test_family_selection_requires_an_explicit_ai_selection` | 仅显式列表计入（**无** snapshot 通道） |
| `test_missing_explicit_family_selection_is_not_an_ai_acceptance` | 空列表 + snapshot 含 BREAKOUT_RETEST ⇒ `AI_NOT_SELECTED_THIS_FAMILY`；plan 仍存在（plans = 1） |
| `test_a_long_plan_for_another_family_is_never_attributed_to_this_opportunity` | 其他 family 的 LONG plan ⇒ **无** `PLAN_CREATED`；plan 仍存在 |
| `test_deferred_open_orders_resolve_each_order_to_its_own_opportunity` | 同一 instrument 两个 OPEN order（两个不同 Opportunity，同一批次处理）：各自延迟事实只挂自己的 opportunity/evidence（`all_linked_to_own_opportunity`、`opportunity_ids` / `evidence_ids` 单元素）；一个成交（`BUY_FILLED` + `TRADE_OPEN`）一个执行校验拒绝（`PLAN_NOT_ACTIVE`）；`TRADE_OPEN` 恰 1 次且归属成交方；**restart-safe**：全新 engine/pool 仅凭 durable facts 解析出同一 linkage；从未开过的 order ⇒ `None` |
| `test_deferred_fill_blocked_by_the_system_risk_gate_keeps_its_authority_and_reason` | `RISK_REJECTED` + `authority = SystemRiskGate` + 精确 reason + 精确 `plan_id`；无 `EXECUTION_REJECTED` / `BUY_FILLED`；order 仍 OPEN、fills = 0 |
| `test_deferred_fill_blocked_by_capacity_keeps_its_own_distinct_authority` | `RISK_REJECTED` + `authority = CapacityPolicy` + `reason = CAPACITY_BLOCKED`，且 **≠** gate authority；fills = 0 |
| `test_deferred_execution_validation_refusal_is_never_a_risk_refusal` | `PLAN_EXPIRED` ⇒ `EXECUTION_REJECTED`，**无** `RISK_REJECTED`；fills = 0 |

全部使用**真实 disposable PostgreSQL**（`CREATE DATABASE marketpulse_se02b_*` →
`alembic upgrade head` → workload → `DROP DATABASE`），未用内存库替代。

**测试自身修复（构造缺陷，非产品缺陷，如实记录）**：

1. helper 初版按「quote 自身 instrument」建映射，导致错配 quote 根本没被投递给 capture，
   掩盖了 P0-1 的 identity 检查 ⇒ 改为按 **event 的 instrument** 显式投递；
2. `_captured_opportunity` 原先 `.one()` 无谓词，双 Opportunity 场景触发
   `MultipleResultsFound` ⇒ 改为按 `candidate_id` **唯一谓词**读取；
3. 延迟成交场景初版用 `ask = 100.5 > limit_price = 99.0`，未满足
   `_process_open_order` 的 `eligible(ask <= limit_price)` ⇒ 静默不成交（`return None`），
   经诊断脚本定位后改为 `ask = 99.0`；
4. 双 Opportunity 场景初版两次 `_accepted_plan` 产生**相同** `snapshot_id`
   （snapshot 身份 = instrument / state_version / config / time，**不含** candidate）⇒
   `ai_decisions` 主键冲突；为 helper 增加可选 `snapshot_at`（默认不变）以错开时刻；
5. 延迟阶段断言初版对**全表** `event_types` 做相等比较，混入了同场景的 AI / PLAN 行 ⇒
   改为只比较「延迟结算阶段可产生的事实」（`_deferred_event_types` / `_order_lineage`）。

---

## 6. Verification（真实执行）

| 门 | 命令 | 结果 |
|---|---|---|
| A. SE-02B focused（capture） | `pytest backend/tests/test_se_02b_opportunity_capture.py -q -p no:randomly` | **14 passed**（27.05s） |
| B. SE-02B focused（attribution） | `pytest backend/tests/test_se_02b_attribution.py -q -p no:randomly` | **31 passed** |
| A+B 合集 | 两文件同批 | **45 passed**（61.65s） |
| C. SE-02A 回归 | `test_se_02a_edge_contracts.py` + `test_se_02a_edge_persistence.py` | **88 passed**（含于下方 211） |
| D. G2 / G3 / G4 回归 | `test_group2.py` + `test_group3.py` + `test_group4.py` | **123 passed**（含于下方 211） |
| C+D 合集 | 5 个文件同批 | **211 passed**（153.60s）＝ 88 + 123，与基线逐项一致 |
| E. G5 / N01 | 由 full backend 覆盖 | 见下 |
| F. full backend | `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q -p no:randomly` | **312 passed, 1 warning**（380.72s） |
| G. Ruff | `py -3.14 -m ruff check backend/src backend/tests` | `All checks passed!` |
| G. compileall | `py -3.14 -m compileall -q backend/src/marketpulse/{edge,g2/repository.py,g3/service.py}` + 两个测试文件 | rc = 0 |
| G. `git diff --check` | 工作树 | rc = 0 |
| H. `alembic heads` | `py -3.14 -m alembic -c alembic.ini heads` | **单 head `20260911_0005`** |

**全量门计数对齐**：`312 = 304（SE-02B 原全量）+ 8（本次新增：capture +3、attribution +5）`，
零失败、零 error、无 flaky 迹象。

**并发写者排他性证据（跑前）**：

- 进程扫描（`Get-CimInstance Win32_Process`）：仅 4 个 `python.exe`，全部为
  `crypto-derivatives-free-mcp` MCP 服务，**无任何 pytest 进程**；
- `pg_stat_activity`（`backend_type='client backend'`，从 primary 库采样）：
  `client_backends = [('marketpulse', '', 'active', 1)]`（仅采样连接自身）；
  `leftover_disposable = []`；数据库集合 = `['marketpulse','postgres','template0','template1']`；
- 本 Fix 期间**未**出现需要标记 `INVALIDATED BY ENVIRONMENT` 的运行。

---

## 7. Migration / Database Guard

- **NO new migration**：本 Fix 未新增、未修改任何 `backend/alembic/` 文件；
  `alembic heads` 单 head 仍为 `20260911_0005`；`down_revision` 链未变。
- 主库 `marketpulse` **未**执行任何 migration（避免未经授权修改外部系统状态）。
- 未触发 §8.4 的 Minimal Schema Proposal 条件（现有 schema 足以表达 restart-safe linkage）。

---

## 8. Scope Check

- `git status --porcelain` 于提交前仅 6 项，且全部落在批准 Scope 内：
  `edge/capture.py`、`edge/attribution.py`、`g2/repository.py`、`g3/service.py`、
  `tests/test_se_02b_opportunity_capture.py`、`tests/test_se_02b_attribution.py`；
  无未跟踪临时文件。
- 未修改：`backend/alembic/`、`edge/{models,identity,hashing,repository}.py`、G4/G5、
  Frontend、`DECISIONS.md`（未新增决策 —— 本 Fix 只是纠正已冻结语义）、`PRODUCT_REQUIREMENTS.md`。
- 未 merge `main`、未 force push、未 amend 已 reviewed commit、未 rebase rewrite、未删 branch、
  未开始 SE-02C。

---

## 9. Self Review（16 问）

| # | 问题 | 结论 |
|---|---|---|
| 1 | 是否引入新的 migration / Edge 持久化？ | **否**；head 仍 `20260911_0005`，`backend/alembic/` 零改动 |
| 2 | 是否新建 Market Data subsystem 或第二套 Edge 写入器？ | **否**；quote 由调用方持有 + 最小 DI；唯一写入者仍是 `append_evidence_revision` / `append_attribution_event` |
| 3 | future quote 是否可能被判为新鲜？ | **否**；`0 <= at - received_at <= max_age`，且以 `evidence_at` 为锚，有定向测试 |
| 4 | 别的 instrument / market type 的 BBO 能否成为本 Opportunity 的 OK evidence？ | **否**；身份不匹配即 `REFERENCE_STALE`，metrics 全 NULL |
| 5 | 是否存在「一次报价沿用给之后所有 Opportunity」的路径？ | **否**；context 已移除 quote，改为 per-persist 有界访问器 |
| 6 | 是否会在非 OK 时写 0 占位 / 伪造 BBO？ | **否**；非 OK 时 `usable_quote = None`，metrics 写 NULL |
| 7 | `evidence_at` 是否被错误地等同于事件收到时刻？ | **否**；`evidence_at = candidate.created_at`，与 `created_at = event.received_time` 分离并各有断言 |
| 8 | 是否偷偷改了 SE-02A 的 `created_at` 契约？ | **否**；`created_at` 仍为 `event.received_time` |
| 9 | 空 `selected_strategy_ids` + snapshot 含本 family 是否会误判为 AI 接受？ | **否**；⇒ `AI_NOT_SELECTED_THIS_FAMILY`，有测试 |
| 10 | 其他 family 的 LONG plan 是否会把 `PLAN_CREATED` 归到本 Opportunity？ | **否**；plan 照常落库但不归因，有测试 |
| 11 | 是否改变了 G3 业务语义？ | **否**；`persist_trade_plan` 与其触发条件未变，只影响是否附加归因 |
| 12 | 是否仍用单一 recorder 绑定整批 OPEN orders？ | **否**；改为逐单 `order_link_resolver` |
| 13 | 延迟成交是否 restart-safe？ | **是**；仅凭 durable `ORDER_OPEN` 事实解析，有「全新 engine + pool」测试 |
| 14 | `ORDER_OPEN` 是否被当作成交？ | **否**；`BUY_FILLED` 只在真实 BUY fill 产生，首次开仓才 `TRADE_OPEN` |
| 15 | Risk 拒绝与 Execution 校验是否仍严格分离？ | **是**；`SystemRiskGate` / `CapacityPolicy` ⇒ `RISK_REJECTED` + 精确 authority/reason，其余 ⇒ `EXECUTION_REJECTED`，各有测试 |
| 16 | `capture=None` / `attribution=None` 的 legacy 行为是否改变？ | **否**；有专门回归测试，且全量门无失败 |

**不确定项：无。** 因此本 Fix 判定为 `READY FOR INDEPENDENT RE-REVIEW`。

---

## 10. Remaining / Blockers

- **无阻塞。**
- 本 Fix **未**自行 Acceptance：`PROJECT_STATE.md` 只写真实状态
  `IMPLEMENTED / VERIFIED / READY FOR INDEPENDENT RE-REVIEW`，**不**写 ACCEPTED / COMPLETE / HUMAN ACCEPTED。
- 交棒 Independent Re-review 时必须继承：
  - 两 order 同 instrument 时，G3 既有语义为「每 instrument 仅一个 ACTIVE plan」，
    因此后建 plan 会使先建 plan 变 `NOT_ACTIVE` ⇒ 延迟阶段一个成交、一个执行校验拒绝。
    这是**产品既有语义**，本 Fix 未改动，测试已按此断言（`PLAN_NOT_ACTIVE`）。
  - `snapshot_id` 不含 candidate，仅由 instrument / state_version / config / time 决定；
    同一 instrument 在同一时刻的两个 Opportunity 会产生同一 decision ⇒ 测试需错开 `snapshot_at`。
  - reference quote 的可用性**永不**参与资格判定：缺失 / 陈旧 / 错配 / future 一律只反映为状态，
    Opportunity 样本始终保留。
- 本 Fix 的验收**不**构成 SE-02C / SE-02D / N01-7 / Integrated Runtime Host 的任何进度。

---

## 11. Review Handoff

| 项 | 值 |
|---|---|
| Branch | `se-02b-opportunity-capture-attribution` |
| Reviewed HEAD（改动前） | `f261766767fff5f8f3d472c1711aeb9bc951d619` |
| Fix commit（本次） | `7e86757b0fbea8c5b2af70f05ce9471fde0b498f` |
| Diff Range | `f261766..7e86757` |
| Migration head | `20260911_0005`（单 head，无新增） |
| Focused 证据 | capture `14 passed`；attribution `31 passed`；合集 `45 passed` |
| Regression 证据 | SE-02A `88`；G2/G3/G4 `123`；合集 `211 passed` |
| Full backend | `312 passed, 1 warning`（独占窗口） |
| 状态 | `IMPLEMENTED / VERIFIED / READY FOR INDEPENDENT RE-REVIEW` |
| 后续 | Independent Re-review（本窗口 STOP，不自行 merge、不开始 SE-02C） |
