# UI-RD01-I03｜TradingAuditRead Product Read 实现（IMP-01）— Final Closeout / Candidate Commit

> 本文件为 **clean-02 执行线的正式 implementation handoff record**：在保留原 §11 request-level PostgreSQL
> evidence checkpoint 事实的前提下，按 `UI-RD01-I03-IMP-01-BASE-RECONCILE-01-CLOSE-01` 扩写为完整实现交接记录。
> **不**声称 Independent Review PASS、**不**声称 Human Acceptance、**不**声称 `I03 ACCEPTED` / `I03 COMPLETE` /
> `REPOSITORY-INTEGRATED`、**不**声称 Performance Human PASS。

## Task

| 项 | 值 |
| --- | --- |
| Task ID | `UI-RD01-I03-IMP-01-BASE-RECONCILE-01-CLOSE-01` |
| Parent Task | `UI-RD01-I03-IMP-01-BASE-RECONCILE-01` |
| Requirement ID | `UI-RD01-I03-REQ-04`（`ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`） |
| Mode | `FINAL SELF REVIEW / STATE SYNC / CANDIDATE COMMIT / PUSH` |
| Original Task Base | `d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b`（clean-01 绑定） |
| **New Task Base** | `7a023f99ac44ac744e5a9885fd82f8a87ef51a94` |
| Working Branch | `ui-rd01-i03-trading-audit-read-clean-02` |
| Working Tree | `E:/Documents/MarketPulse-AI-ui-rd01-i03-trading-audit-read-clean-02` |
| Frozen Requirement | `docs/design/UI-RD01/UI-RD01-I03-Implementation-Requirements.md` |
| main integration | `NOT PERFORMED` |

## Latest-Main Reconciliation

| 项 | 值 | 判定 |
| --- | --- | --- |
| clean-01 绑定的 Task Base | `d5cffca…` | 已被外部批推进 |
| 推进后 main = clean-02 Task Base | `7a023f99ac44ac744e5a9885fd82f8a87ef51a94` | 一致 |
| 推进性质 | `d5cffca` 是 `7a023f99` 的祖先（纯快进：`6ebf7a6` → `f0e51d9` → `7a023f9`，`fix(advisory)` ×2 + 该批 closeout） | 非分叉 |
| 处置 | clean-01 依其任务卡 STOP；clean-02 以 `7a023f9` 为新 Task Base 重建，clean-01 WIP 逐字节 carry-forward（见下） | `PASS` |
| `origin/main`（resume 读 + 提交前复读） | `7a023f99ac44ac744e5a9885fd82f8a87ef51a94` | 未漂移 |
| 远端候选分支（resume 时） | 不存在（无意外远端工作） | 一致 |

- clean-01 source worktree（`E:/Documents/MarketPulse-AI-ui-rd01-i03-trading-audit-read-clean-01`）**未被修改**：
  HEAD = `d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b`、branch = `ui-rd01-i03-trading-audit-read-clean-01`、
  6 个 WIP 文件 sha256 与该批记录的 source baseline **逐字节一致**（见「Source clean-01 Preservation」）。

## Scope

`GET /api/v1/product/trading-audit`（TradingAuditRead）单 Human Acceptance Batch 的实现、验证与候选提交：

- Account / Current Positions / Position Protection / ACTIVE Plans / OPEN Orders / Pending Intent capability
- Typed Trading Timeline（11 类）+ Traceability（A52/A53 与 A54–A73 矩阵）
- Initial Intent rejection classification / Deferred Risk-Execution refusals / Order cancellation evidence
- Economic integrity validation（A74–A76）/ run_mode ownership（A77–A79）
- Stable PostgreSQL read snapshot（A8）/ Product HTTP failures（A82）/ sanitization（A83）
- OpenAPI + `generated.ts` + 前端校验
- A0–A95 Self Review、state carrier 同步、candidate commit + push（**不** integrate `main`）

## Out of Scope

Trading / Risk / Execution / Position / Protection / Ledger 语义变更；新 schema / migration / index / persistence；
新 Product endpoint；Account Equity / Unrealized PnL / Trade lifetime total PnL；Replay selector；historical
revision-as-of；Real AI 激活；`PRE-01B-I2`；live `G2→G3`；Gate A/B/C；Live Trading；`I04` / `I05`；`main` 整合。
以上全部**未触碰**（见「Zero-Change 证明」）。

## Reuse Decisions

- **复用**既有 `marketpulse.api.product` 包结构与共享 DTO（`ProductReadContext` / `ProjectionMetaDTO` /
  `ProjectionState` / `TraceNodeDTO` / `ProductUnavailableResponse` / `ProductInternalErrorResponse`），
  满足 A82「Reuse shared Product error DTOs」。
- **复用**既有 product router 注册模式：`system.py` 仅 +2 行（import + `include_router`），与
  `market_scanner` / `opportunities` 同构，未引入第二套路由约定。
- **复用**既有 cursor 编码骨架（base64url + `CURSOR_VERSION` + endpoint 绑定），新增
  `TradingAuditCursor` / `encode_trading_audit_cursor` / `decode_trading_audit_cursor`（+81 行），
  **未**引入第二套 cursor 编码。
- **复用**既有前端生成链 `scripts/generate-api.mjs` + `scripts/check-api-drift.mjs`（`openapi-typescript@7.13.0`，
  从 FastAPI app 对象导出，无需 DB）。
- **复用**既有 G3 领域模型（`TradePlan` / `OrderStatus` / `PlanStatus`）与既有 reconciliation 语义，
  **未**新增第二套算法、**未**新增抽象层、**未**新增依赖。

## Final Changed Paths（相对 New Task Base `7a023f99…`）

| 路径 | 状态 | 说明 |
| --- | --- | --- |
| `backend/src/marketpulse/api/product/trading_audit.py` | added（新文件） | 端点 + 投影 + 校验 + traceability |
| `backend/tests/test_product_trading_audit.py` | added（新文件） | focused 契约测试 |
| `backend/src/marketpulse/api/product/cursor.py` | modified `+81` | `TradingAuditCursor` + 编解码 |
| `backend/src/marketpulse/api/product/models.py` | modified `+327` | Trading DTO 家族 |
| `backend/src/marketpulse/api/product/system.py` | modified `+2` | router 注册 |
| `frontend/src/api/generated.ts` | modified `+796` | `generate:api` 生成物 |
| `PROJECT_STATE.md` | modified | I03 实现结果段（docs-only） |
| `AI_CONTEXT.md` | modified | I03 导航指针段（docs-only） |
| `dev_log/2026-09-22-ui-rd01-i03-trading-audit-read.md` | added（本文件） | 正式交接记录 |

`tmp-i03-evidence/**` = 仓库外临时证据，**未** stage、**未** commit（见「Temporary Evidence」）。

## Endpoint / DTO 实现

- 端点：`@router.get("/trading-audit", response_model=TradingAuditReadResponse, responses={401,422,503,500})`，
  `Depends(verify_session)`；**唯一** I03 路由，无 detail route（A5）。
- Query：`limit: int = Query(100, ge=1, le=500)`、`cursor: str | None`、
  `instrument_id: str | None = Query(None, min_length=1, max_length=64)` —— 与 A6 逐字一致；无 case
  normalization / alias / 新 regex（A6）。
- DTO（`models.py`，全部 typed、无 raw payload）：`TradingAccountDTO`、`TradingPositionDTO` +
  `TradingPositionProtectionDTO` / `TradingProtectionAuthorityDTO` / `TradingProtectionState`、
  `TradingPlanDTO`、`TradingDecisionDTO`、`TradingOpportunityBindingDTO`、`TradingOpenOrderDTO`、
  `TradingPendingIntentCapabilityDTO`、`TradingCollectionDTO[T]`、11 个 `Trading*TimelineItemDTO`
  （discriminated union on `event_type`）、`TradingTimelinePageDTO`、`TradingTraceabilityDTO` +
  `TradingTraceabilityStatus` + `TradingTraceMissingLink`、`TradingAuditDataDTO`、`TradingAuditReadResponse`。
- 无 `equity` / `unrealized_pnl` / `portfolio_value` / `buying_power`（A15）；无 `side` / `position_version` /
  `PositionRecord.realized_pnl` 暴露（A18）；无 `trades[]` aggregate（A81）。

## Decision Binding（A25 / A26）

- 复用 `DecisionSnapshotRecord` **历史**绑定字段（`opportunity_id` / `evidence_id` / `evidence_revision` /
  `evidence_hash` / `feature_snapshot_hash`），经 `_historical_binding` 与 `EdgeOpportunityEvidenceRecord`
  逐字段 exact 比对；**从不**用 current canonical Evidence 替换（A26）。
- 全部 5 字段缺失 ⇒ `NO_PROVABLE_RECORD`（`data=null`，`evidence_basis=null`）；**部分**显式缺失 ⇒
  `SNAPSHOT_FAILED`（不做 silent partial 投影）。
- 多条显式 durable 来源（latest-main additive `AdvisoryDecisionInvocationRecord` + `EdgeAttributionEventRecord`
  显式绑定）必须**互相兼容**：identity / snapshot / digest 任一不符，或 attribution 显式绑定与 direct binding
  冲突 ⇒ `SNAPSHOT_FAILED`（无 silent source precedence）。
- 证据：focused 参数化用例覆盖 `missing_snapshot` / `partial_snapshot_binding` / `missing_invocation` /
  `invocation_snapshot_mismatch` / `missing_evidence` / `evidence_hash_mismatch` / `evidence_cross_opportunity` /
  `decision_snapshot_invocation_mismatch` 八类显式引用失败。

## Protection / ACTIVE Plans（A19–A24）

- Protection 由 **Position durable 五字段**（`protection_plan_id` / `_version` / `_stop_loss` / `_take_profit` /
  `_updated_at`）单点分类：`FLAT`+全空 ⇒ `NOT_REQUIRED`；`FLAT`+任一非空 ⇒ `SNAPSHOT_FAILED`；
  `OPEN`+全空 ⇒ `UNPROTECTED`；`OPEN`+全非空且 valid（plan_id 非空 / version ≥ 1 / 有限 SL-TP / SL < TP /
  valid `updated_at`）⇒ `PROTECTED` + exact durable authority；其余 ⇒ `UNKNOWN` + `authority=null`。
  **从不**用 Plan 回填 protection（A20）。`R04-P2-01` 语义（hypothetical `protection_plan_id=""` 更保守）保持。
- ACTIVE Plans：包含全部 `status == ACTIVE`（含 TTL 已过期行），排序 `instrument_id ASC, plan_id ASC`；
  `ttl_expired = request meta.snapshot_at >= expires_at`；每行经 typed `TradePlan` rehydrate 并逐字段比对
  row/payload identity（plan_id / snapshot_id / decision_id / instrument_id / run_mode / state_version /
  plan_version / created_at / expires_at）；invalid schema/identity ⇒ `SNAPSHOT_FAILED`，**不** silent omit，
  **不**暴露 raw payload（A21–A23）。
- TTL 与 protection 生命周期分离：TTL 过期不撤销 durable protection，新 ACTIVE Plan 不自动替换（A24）。

## Traceability（A52 / A53）与 A54–A73 矩阵

- 状态值：`COMPLETE` / `PARTIAL` / `NOT_PROVABLE`；`missing_links` 枚举 = `DECISION` / `OPPORTUNITY_BINDING` /
  `PLAN` / `INTENT` / `ORDER` / `FILL` / `LEDGER` / `RISK_ATTRIBUTION` / `REJECTION_CLASSIFICATION` /
  `ORDER_CANCELLATION_EVENT`（顺序与 A52 一致）。
- 顺序遵循 A53：(1) 校验 primary fact → (2) exact matrix → (3) strong economic integrity → (4) 剩余 lineage。
  `_event_traceability` 先执行 contradictions（order/intent identity、fill/order identity、no-plan bundle、
  trade fill role）再计算 trace gap ⇒ strong integrity **先于** traceability（A80）。
- A54–A73 全部 20 行经**生产投影**入口 `_event_traceability`（`_matrix_links`）驱动，逐行 applicability：
  A54 `PLAN_CREATED`={DECISION,OPPORTUNITY_BINDING}；A55 `INTENT_REJECTED`={PLAN,DECISION,
  OPPORTUNITY_BINDING,REJECTION_CLASSIFICATION}（无 plan 即 `SNAPSHOT_FAILED`）；A56 `INTENT_EXECUTED BUY`
  ={ORDER,PLAN,DECISION,OPPORTUNITY_BINDING,RISK_ATTRIBUTION}；A57 SELL-with-plan 同矩阵减 RISK；A58 SELL
  no-plan={ORDER}，PLAN/DECISION/OPPORTUNITY_BINDING/RISK_ATTRIBUTION 不适用；A59–A61 `ORDER_CREATED`
  BUY/SELL-with-plan/SELL-no-plan（CANCELLED 时加 `ORDER_CANCELLATION_EVENT`）；A62 `ORDER_CANCELLED`
  ={ORDER,INTENT}+继承，empty-plan CANCELLED ⇒ `SNAPSHOT_FAILED`；A63 初始 RISK 与 A65 初始 EXECUTION
  ={INTENT,PLAN,DECISION,OPPORTUNITY_BINDING}（RISK 自证分类）；A64/A66 deferred =同 + `ORDER`；A67/A68/A69
  `FILL` 强引用 {ORDER,INTENT,LEDGER}+按 BUY/SELL-with-plan/SELL-no-plan 追溯；A70 `LEDGER`={FILL,ORDER,INTENT}+
  继承 Fill 行；A71 `TRADE_OPEN`（先证 opening Fill，未证 ⇒ `missing_links=[FILL]`；BUY 否则 `SNAPSHOT_FAILED`）
  +{ORDER,INTENT,LEDGER,PLAN,DECISION,OPPORTUNITY_BINDING,RISK_ATTRIBUTION}；A72 `TRADE_CLOSE`（先证 closing
  Fill；SELL 否则 `SNAPSHOT_FAILED`）+{ORDER,INTENT,LEDGER}，SELL-with-real-Plan 再加 PLAN/DECISION/
  OPPORTUNITY_BINDING，accepted no-plan SELL ⇒ Plan ancestry `NOT APPLICABLE`；A73 `POSITION_EVENT` 仅由显式
  非空 `plan_id`/`order_id`/`fill_id` 决定 applicable，全空 ⇒ `COMPLETE` + `missing_links=[]`。

### Traceability Interpretation Note（**不改实现**，供 Independent Review）

- 生产路径中 `_trace_for(..., proven=∅)` 的 `proven` 集恒为空（实现按「applicable 集合」表达 gap，不从
  durable 事实反推 proven 子集）。因此**可观测**行为为：
  - `applicable == ∅` ⇒ `COMPLETE` / `missing_links=[]`（如 A73 全空、A58 no-plan SELL 的 `FILL`）；
  - `applicable != ∅` ⇒ `NOT_PROVABLE` + 完整 applicable 集合；
  - `PARTIAL` 在当前实现中**不可达**，但 `PARTIAL` 保留在 frozen DTO 枚举中（A52 要求三值齐备）。
- 依任务卡 §4 明确指示（「Do not change implementation merely to make a specific status reachable」），
  本批**未**改动该行为，仅如实记录，供 Independent Review 判断是否需要后续 Batch。

## Timeline / Cancellation / Cursor（A29–A49、A84–A85）

- 11 类 item 的 `timeline_event_id` 与 A31 逐字一致（`plan:create:{id}` / `attribution:{id}` /
  `intent:{id}` / `order:create:{id}` / `outbox:{id}` / `fill:{id}` / `ledger:{id}` / `trade:open:{id}` /
  `trade:close:{id}` / `position-event:{id}`），跨请求稳定；`entity_id` 为业务身份（A29）。
- Initial vs Deferred：`_initial_rejection` 仅当 attribution 的 `subject_id == intent_id`、
  `event_type ∈ {RISK_REJECTED, EXECUTION_REJECTED}` 且 `occurred_at == intent.created_at` 时认定
  initial（A40）；EXECUTED Intent ⇒ `NOT_OCCURRED` + `evidence_basis=durable_intent_status`；无可证记录 ⇒
  `NO_PROVABLE_RECORD`；**从不**按 reason 文本推断（A39）。同一 Intent 多个等时 attribution 事件不碰撞
  （靠 `attribution:{id}` 唯一键）。
- Deferred refusals：EXECUTED Intent 之后可多个独立 RISK_REJECTED / EXECUTION_REJECTED，Intent 保持
  EXECUTED（A41）。
- ORDER_CANCELLED 仅由 `OutboxRecord.event_type == ORDER_CANCELLED` + `aggregate_id == order_id` 且 exact
  Order 得证时投影，**不**由「消失」或「无 Fill」推断（A43）；CANCELLED Order 缺 exact 取消事实时**不**伪造
  事件或 `cancelled_at`，改为在 ORDER_CREATED 的 traceability 上标 `ORDER_CANCELLATION_EVENT`（A44）。
- PositionEvent 白名单 = A49 的 11 值；`PROTECTION_EVALUATED` / `RECOVERY` / `SYMBOL_BLOCK` /
  `EMERGENCY_ACTION` 被排除；无 raw payload。
- Cursor（A32）：绑定 version / endpoint(`trading-audit`) / run_mode / instrument_id filter /
  `timeline_upper_bound` / `occurred_at` / `entity_kind` / `timeline_event_id`；scope 不符或
  malformed（非法 sort tuple / entity_kind 不在 10 类 / 无 tz / `occurred_at > upper`）⇒ `422`。
- 全局 merge（A85）：先物化全部来源 → 按 `occurred_at DESC, entity_kind DESC, timeline_event_id DESC`
  （PLA-01，A1/A32）全局排序 → 再取 `limit + 1` 窗口；等时 `ORDER_CREATED`/`ORDER_CANCELLED` 经
  `timeline_event_id` 区分且逐页各出现一次（focused 用例覆盖）。
- Current-state 排序（A84）：positions `instrument_id ASC`；active_plans `instrument_id ASC, plan_id ASC`；
  open_orders `created_at DESC, order_id DESC`。

## Economic Integrity（A74–A81）

`_validate(...)` 对 **entire current run_mode economic workspace** 执行（A75；instrument filter **不**收窄
global Account reconciliation）：

1. `Account.reserved_cash` == 全部 OPEN BUY `reserved_cash`（tolerance `1e-12`，复用既有 G3 语义，无新容差）
2. 每 instrument 的 OPEN SELL `reserved_quantity` <= Position quantity
3. Position quantity == 完整 BUY-minus-SELL Fill population
4. `available_cash = cash_balance - reserved_cash`
5. `available_cash` 非负
6. 每个 Fill 恰好一个 Ledger（重复 identity ⇒ `duplicate economic identity`）
7. 每个 Ledger 解析到 exact Fill
8. 每个 FILLED Order 恰好一个 Fill
9. Fill quantity == FILLED Order quantity
10. `Fill.intent_id == Order.intent_id`

- A76 无 join-hidden orphan：`fills` / `ledger_entries` **无** `run_mode` 列，故先整表装载再做闭合判定
  （inner join 不会吞掉孤儿）；Fill-without-Order、Ledger-without-Fill、FILLED-Order-without-Fill 均显式触发。
- A77/A78 ownership：`_ownership(anchors, current_run_mode)` → `PROVEN_CURRENT` / `PROVEN_OTHER` /
  `CONFLICTING_SCOPE` / `UNSCOPED`；Fill 锚点 = (Order.run_mode, Intent.run_mode)，Ledger 锚点 =
  (Account.run_mode, exact Fill ownership)；`CONFLICTING_SCOPE` / `UNSCOPED` ⇒ `503 SNAPSHOT_FAILED`
  （故意作为 active TradingAudit 的 global blocker），`PROVEN_OTHER` 被排除出当前投影/会计。
- A79 audit rows without `run_mode`：attribution 仅在 `payload.intent_id` 解析到当前 run_mode Intent 时投影；
  ORDER_CANCELLED outbox 仅在 exact 当前 run_mode Order 存在时投影；不可证 ⇒ 不分配、不猜测，最多成为
  trace gap，**不**单独触发 global orphan failure。
- **CLOSE-01 conformance fix（见「Self-Review Conformance Fix」）**：A80 列表中
  `EXECUTED Intent without Order` 以及 A51/A62 的 empty-plan bundle 判据在本批前**未**实现，本批补齐后
  全部落为 `503 SNAPSHOT_FAILED`，**不再**降级为 `PARTIAL`/`NOT_PROVABLE`。
- A81 结果边界：允许 `Account.realized_pnl` / Fill fee / Ledger `cash_delta` / `settlement_realized_pnl`
  （仅 settlement）/ Trade 生命周期时间戳 / `exit_reason`；无 Equity / Unrealized PnL / Trade lifetime
  total PnL / Forward Outcome as economic result；无 `trades[]` aggregate。

## Stable Snapshot（A8）与 HTTP / Sanitization（A82–A83）

- `_snapshot` 上下文管理器：PostgreSQL 分支执行
  `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ, READ ONLY` 并取 `SELECT statement_timestamp()` 作为
  per-request as_of；全部必需 durable 事实在该事务内物化后事务结束（per-request consistency only，无跨请求
  MVCC 声明，A33）。
- A82：`200`（成功 / empty / 合法 trace absence / capability not integrated / Host not activated）、
  `401`（auth，先于 Product 数据存在性可观测）、`422`（非法 query/cursor）、
  `503 SOURCE_UNAVAILABLE`（source/session/DB 获取失败）、`503 SNAPSHOT_FAILED`（快照失败 / 经济矛盾 /
  非法显式 lineage / conflicting-unscoped ownership）、`500`（未分类且已 sanitize 的内部错误）。
- A83：`ProductInternalErrorResponse(correlation_id=new_id().hex)` —— 不返回 SQL / params / DSN / traceback /
  异常文本 / secret / token / raw ORM / raw Plan 或 PositionEvent 或 Ledger payload / raw AI prompt、response
  （focused 用例 `isdisjoint({"raw_prompt","raw_response","error"})`、`"payload" not in item.model_dump()`）。
- Host absent（A9）：`200` + `ReadSurfaceClass=A` + `NOT_ACTIVATED` + `projection_state=UNAVAILABLE` +
  `read_failure_reason=null` + `data=null` + `next_cursor=null`。

## OpenAPI / generated.ts（A86）

- `generate:api` 为唯一生成路径（`openapi-typescript`，从 FastAPI app 导出，无 DB 依赖）；
  **未**手工编辑 `generated.ts`、**未**在前端复制权威 DTO。
- 本批实测：`node scripts/check-api-drift.mjs` ⇒
  `no OpenAPI drift: /api/v1/live, /api/v1/ready present; generated.ts matches the backend contract`，exit `0`。
- 本批**未**改动任何 DTO / endpoint / OpenAPI 形状（仅 validator 内部逻辑）⇒ `generated.ts` blob 保持
  `50640c81352843c2e5acb88db5f23e447d0ad8bb`（= clean-01 carry-forward 值，未重生成）。
- 前序窗口记录（CIP-07：未在本批独立复核）：contract path/opId/params/responses 齐备、
  `generate:api` 幂等、frontend typecheck / `7 files / 57 tests` / build 通过。

## Request-Level PostgreSQL Evidence（重捕获）

**权威工件**：`tmp-i03-evidence/evidence-20260922-204704.json`
`sha256 = 46773c6f4ff04643d126a8aebc0160a606b1c89b82fe6bd85e39ff68052a80f3`
（harness exit `0`；`harness_errors=[]`；`validation_problems=[]`）

同目录保留同一 harness 的历史捕获：`evidence-20260922-154506.json`（pre-fix bytes，原 §11 checkpoint）、
`evidence-20260922-204505.json`（CLOSE-01 validator fix 后、加入 11.8 前）。三者均为**仓库外**临时证据。

运行命令（cwd = clean-02 worktree 根，以命中隔离 `.env`）：
`PYTHONPATH=backend/src py -3.14 tmp-i03-evidence/evidence_harness.py`
harness 内建 **fail-closed DSN 守卫**：解析端口必须 `== 5450`、库名必须 `marketpulse`，否则在任何 SQL 之前
`SystemExit`。

| 项 | 值 |
| --- | --- |
| isolated 容器 | `marketpulse-ui-rd01-i03-final-verify-pg` / `9af628dc2dac` / `postgres:16-alpine` / `127.0.0.1:5450->5432/tcp` |
| isolated `system_identifier` | `7688238732663410723` |
| isolated `alembic_version` | `20260917_0010`（**等于**仓库单 head；本批未 migrate） |
| shared 5432 | 只读探针；本批**零写入**（未 DDL / DML / migrate / clean / TRUNCATE） |

### 1｜事务属性（§11.1）

| 采样点 | `transaction_isolation` | `transaction_read_only` |
| --- | --- | --- |
| 独立连接事务 | `repeatable read` | `on` |
| **真实请求自己的事务内部**（`_snapshot` 建立后同 session 采样） | `repeatable read` | `on` |

verdict = `PASS`（证据为实际 `SHOW` 输出，非源码字符串）。

### 2｜全局完整性 vs 请求仪器过滤（§11.3）

注入事实：`ETH-USDT` 的 `fill-eth`（durable 双锚点均解析为 `TEST` ⇒ `PROVEN_CURRENT`）缺对应 ledger entry。

| 场景 | durable read | 真实 HTTP 边界 |
| --- | --- | --- |
| BTC 工作区（注入前） | 成功（`active_plans=1`、`open_orders=1`、`positions=1`、`timeline_items=7`） | `200` / `FRESH` / `ACTIVE` |
| 注入后、`instrument_id=BTC-USDT` | `SnapshotError: fill orphan` | **`503` + `read_failure_reason=SNAPSHOT_FAILED`** |
| 注入后、无仪器过滤 | `SnapshotError: fill orphan` | — |
| 移除注入后再次 BTC 读取 | 成功（7 items） | — |

verdict = `PASS`：请求仪器过滤只收窄**呈现**范围，**不**豁免全局经济完整性；越出呈现范围的 ETH 事实仍使
请求整体失败，且由全局 fill/ledger 闭合判据（非 ownership 过滤）触发 ⇒ 过滤无法「藏住」它。

### 3｜确定性并发变更（§11.2）

| 项 | 值 |
| --- | --- |
| entity / field | `accounts.account_id='acc-TEST'` / `cash_balance` |
| pre value | `100000.0` |
| 独立事务 COMMIT | `true`（`commit_error=null`） |
| COMMIT 后直读 DB | `123456.0` |
| **请求观测值** | `100000.0`（= pre） |
| 请求结束后直读 DB | `123456.0` |
| 同步机制 | 注入 `ta._snapshot` 包装器：`BEGIN` + `SET TRANSACTION … REPEATABLE READ, READ ONLY` +
  `SELECT statement_timestamp()`（快照已存在）**之后**暂停请求协程，`threading.Event` 握手；独立事务提交后放行 |

结论 = `PASS`：请求观测到 pre-mutation 值，同时独立事务 COMMIT 成功 ⇒ 一次连贯的 pre-mutation 快照。
**非 sleep-only**：唯一排序依据是 `threading.Event` 标志（10 ms `asyncio.sleep` 仅用于轮询）。

### 4｜资源清理（§11.4）

| 路径 | 结果 | 池（`checkedout` / `checkedin`） | 后续 `SELECT 1` |
| --- | --- | --- | --- |
| 成功 | 请求完成（7 items） | `0` / `1` | `1` |
| 完整性失败（人为孤儿 ledger ⇒ `SnapshotError: unscoped/conflicting ledger`） | 异常抛出；映射 `SNAPSHOT_FAILED` | `0` / `1` | `1` |
| 取消（快照建立后 `task.cancel()`） | `CancelledError` 传播 | `0` / `1` | `1` |

8/8 内建判据全真；`isolated_active_backends=1`（无泄漏连接）⇒ verdict = `PASS`。

### 5｜history-heavy 结构性能（§11.5 / §11.6，A88-C / A89）

| 表 | 实际 DB 计数 | 门槛 |
| --- | --- | --- |
| `paper_orders`（Orders） | **5202** | ≥5000 ✓ |
| `fills`（Fills） | **5201** | ≥5000 ✓ |
| `ledger_entries`（Ledgers） | **5201** | ≥5000 ✓ |
| `position_events`（PositionEvents） | **5200** | ≥5000 ✓ |
| `execution_intents` | 5202 | — |
| `positions` / `accounts` / `trade_plans` | 1 / 1 / 1 | — |

对以上人口执行**真实** TradingAudit read，且完整性校验**全部启用**（`_validate` 未被绕过 / 弱化）：

| 项 | 小人口（40 bulk 行） | 大人口（5200 bulk 行） |
| --- | --- | --- |
| SQL 语句总数 | **16** | **16** |
| distinct statement shapes | 16 | 16 |
| leading keyword | `SET`×1 + `SELECT`×15 | `SET`×1 + `SELECT`×15 |
| 单关系最大语句数 | 2（`accounts`） | 2（`accounts`） |
| 请求时长 | `145.493 ms` | `14000.699 ms` |

- 结构性有界：40 → 5200 行语句数**完全相同**（比值 1.0）；无 query-per-row / 无 N+1；固定投影形状；
  无 provider/network I/O。
- 请求内物化（大人口）：global validation population = `intents 5202 / orders 5202 / fills 5201 /
  ledgers 5201 / positions 1`；`_build_timeline` 候选 = **26,007**；`_project_active_plans` = 1 item。
- timeline window：`limit=100` ⇒ `returned=100`、`next_cursor` 存在、显式 `limit + 1` 窗口 = **101**、
  `silent_truncation=false`（keyset 续读证据，非截断）。
- 事务持有时长（大人口）= `13931.854 ms`；`begin → 快照建立` = `41.213 ms`；事务作用域总时长 = `13973.067 ms`。
- Windows 内存（`psapi.GetProcessMemoryInfo`，**bytes**，`units` 写进证据；working set **不是** RSS，
  **未**使用 `resource.getrusage`）：大人口请求前 working set `119742464`，请求后 `153456640`，
  peak after `230391808`；harness 结束时 `160612352` / peak `231837696`；page faults `36689 → 63056`。
- `EXPLAIN (ANALYZE, BUFFERS)`（先对 6 张关系执行 `ANALYZE` 刷新统计，**仅统计**，无 DDL / schema / index
  变更）：人口级读取为 **Seq Scan**（`paper_orders` 5202 行 / `0.766 ms`；`fills`/`ledger_entries` 各 5201 行；
  `position_events` 5200 行，均在 ~1 ms 内）；有序窗口 = Limit → top-N heapsort；点查走索引
  （`fills_order_id_key` / `ledger_entries_fill_id_key`，`Index Scan`）。
- **未**新增 / 修改 / 删除任何 schema / index；证据**未**显示存在为**正确性**所需的新索引 ⇒ 不触发 A87/A92 的
  `STOP`。人口级 Seq Scan 属性能话题 ⇒ `Performance Human Disposition = PENDING`。
- 本批**不**做延迟 PASS/FAIL 判定，**未**做 profile，**未**定位热点，**未**设置或比较任何自造 SLA 阈值。

### 6｜Legal Empty Workspace（A16 / A88 fixture A）

对 TRUNCATE 后、播种前的**真空** run_mode workspace 执行真实 read + 真实 HTTP：

| 项 | durable read | HTTP |
| --- | --- | --- |
| 结果 | 未抛异常 | `200` |
| `account` | `state=NO_PROVABLE_RECORD`、`data=null` | 同 |
| `positions` / `active_plans` / `open_orders` | `EMPTY` + `[]` | 同 |
| `pending_intents` | `CAPABILITY_NOT_INTEGRATED` + `items=null` | 同 |
| `timeline` | `EMPTY` + `[]` + `timeline_upper_bound` 存在 + 无 cursor | 同 |
| `meta` | — | `FRESH` / `ACTIVE` |

⇒ A14 / A16 / A28 / A11 的 empty-workspace 分支由**真实 PostgreSQL + 真实 HTTP** 证据覆盖。

## Self-Review Conformance Fix（CLOSE-01）

A0–A95 复审在 A51 / A56 / A62 / A80 面发现**未实现**的 frozen fail-closed 判据。按任务卡 §5（unambiguous
defect、required by the Frozen Requirement、inside authorized I03 paths、no new semantic decision）在本批修复，
**仅**落在 `backend/src/marketpulse/api/product/trading_audit.py`（`_validate`）与 focused 测试（+2 个用例，
其中 1 个参数化 4 例）。

| A 节 | 要求 | 修复前实测 | 修复后实测 |
| --- | --- | --- | --- |
| A56 / A80 | EXECUTED Intent 缺 exact Order ⇒ `503 SNAPSHOT_FAILED`，**不**降级为 `PARTIAL`/`NOT_PROVABLE` | 投影成功，`INTENT_EXECUTED` = `NOT_PROVABLE`（`missing_links` 含 `ORDER`） | `SnapshotError: executed intent without order` |
| A51 | `plan_id=""` → Product `null` 仅在 accepted no-plan SELL bundle（Intent `EXECUTED`、`SELL`、`MARKET`、`FILLED`、exact Fill/Ledger）成立时合法，否则 `503` | 空 plan BUY/LIMIT/OPEN 行被投影为 `plan_id=null`（`200`） | `SnapshotError: empty-plan order without accepted no-plan bundle` |
| A62 | Empty-plan CANCELLED Order ⇒ `503 SNAPSHOT_FAILED` | 投影成功（仅 trace gap） | 同上（bundle 判据覆盖 `status != FILLED`） |

**是否改动产品语义**：否。合法 G3/G4 生产者只会提交以下 durable 形状，两处判据对**合法可达状态零行为变化**，
仅对损坏 / 部分写入的 durable 状态 fail-closed：

- Plan 驱动路径在同一事务内同时写入 `ExecutionIntentRecord(EXECUTED)` 与 `PaperOrderRecord`
  （`g3/service.py`）⇒ EXECUTED Intent 必然有 Order；
- `g4/protection.py::close_position` 在无 protection authority 时传 `plan_id=""`，
  `g3/service.py::_risk_reducing_exit_once` 在同一事务内创建 `SELL`+`MARKET` order 并立即
  `_settle_order`（置 `FILLED`）⇒ 合法空 plan 形状恰为 A51 的 bundle；不存在合法空 plan 的 BUY / LIMIT /
  OPEN / CANCELLED durable 行。

**判据有效性（teeth）证据**：同一仓库外探针脚本
`tmp-i03-evidence/_probe_close01_a80_a51.py` 在**修复前**产物与**修复后**产物上各运行一次，输出分别落盘为
`_probe_close01_prefix-out.txt`（非法形状全部「NO ERROR」并产出投影）与 `_probe_close01_postfix-out.txt`
（全部 `SnapshotError`，且 legal no-plan SELL control 仍「NO ERROR」）；focused 测试对每条非法形状断言
**具体错误消息**（`match="executed intent without order"` / `match="empty-plan order"`），故判据被破坏时该测试
必然失败。

**受影响验证重跑**（任务卡 §5）：focused TradingAudit、Product regression、Ruff/static/format、API drift、
`git diff --check`、以及**受影响的经济完整性 PostgreSQL 证据**（见上「Request-Level PostgreSQL Evidence
（重捕获）」）。生产实现**已变化** ⇒ 前序窗口的 `919 passed` 与本批的关系见下。

## Verification

### 本批实测（final candidate bytes）

| 项 | 命令 | 结果 |
| --- | --- | --- |
| focused TradingAudit（修复前基线，本批实测） | `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_product_trading_audit.py -q` | **62 passed**, 1 warning, exit `0` |
| focused TradingAudit（**final**） | 同上 | **68 passed**, 1 warning, 1.47s, exit `0` |
| Product regression（**final**） | `pytest backend/tests/test_product_{system,trading_audit,market_scanner,opportunities}.py -q` | **144 passed**, 20 warnings, 29.55s, exit `0` |
| Ruff check | `py -3.14 -m ruff check backend/src backend/tests` | `All checks passed!`, exit `0` |
| Ruff format | `py -3.14 -m ruff format --check <2 touched files>` | `2 files already formatted`, exit `0` |
| API drift | `node scripts/check-api-drift.mjs` | `no OpenAPI drift … generated.ts matches the backend contract`, exit `0` |
| `git diff --check` | — | exit `0`（仅 `generated.ts` 的 LF→CRLF 提示，无 whitespace error） |
| 隔离 PostgreSQL 证据 | `PYTHONPATH=backend/src py -3.14 tmp-i03-evidence/evidence_harness.py` | exit `0`；`validation_problems=[]`；新证据 sha256 见上 |

### 前序窗口记录（CIP-07：**本批未独立复核**，不据此升级状态）

- `complete backend regression = 919 passed / 23 warnings / exit 0`
- `OpenAPI contract = PASS`、`generate:api` / drift = `PASS`
- `frontend typecheck` / `7 files / 57 tests` / `build` = `PASS`
- `isolated PostgreSQL = established`、`isolated Alembic current == head`
- 本批可独立复核的旁证：隔离库 `alembic_version = 20260917_0010` **等于**仓库单 head（10 个迁移文件，
  head = `20260917_0010_advisory_ingress_core`）。

### `919 passed` 与本 candidate 的关系（诚实边界）

- `919 passed` 绑定的是**修复前**的生产字节（`trading_audit.py` = `89eb2fa5…`，
  `test_product_trading_audit.py` = `0c4b208b…`）。本批的生产修复使这两个 blob 变为
  `bdac7389…` / `1633fc38…` ⇒ **本批未对修复后字节重跑全量 919 回归**。
- 依任务卡 §9.4「If production implementation changes: re-evaluate required regression breadth under §5」，
  本批按 §5 最低要求执行 focused + Product regression + Ruff/static + API drift + 受影响 PostgreSQL 证据，
  并**额外**捕获 A16 empty-workspace 证据。
- 变更面收敛性旁证：修复仅位于 `api/product/trading_audit.py::_validate`（单端点内部校验），该模块的
  importer 仅 `api/product/system.py`（router 注册）；`Ruff check backend/src backend/tests` 全绿。
- **全量 919 回归在本 candidate 上 = `NOT RE-CAPTURED`**（如实标注，供 Independent Review 决定是否需要
  在评审前补跑）。

### 环境漂移观察（**非** I03 变更）

- 共享 `127.0.0.1:5432/marketpulse` 当前 `alembic_version = 20260922_0011`，而仓库（New Task Base
  `7a023f99…`）单 head = `20260917_0010`（10 个迁移文件）⇒ 存在**本 Task Base 之外的**外部 schema 推进。
- 本批**未**对共享库执行任何 DDL / DML / migrate / clean；该漂移也**不**影响隔离库证据（isolated 容器
  独立 volume，仍 `20260917_0010`）。
- 记录原因：前序窗口的共享库相关数值（如 shared `alembic_version = 20260917_0010`）在**本批复读**时为
  `20260922_0011`；若后续批次以共享库作为回归基线，需先确认该漂移。

## A0–A95 Self Review

对 96 个编号章节逐节分类（无章节跳过；未引入新状态；未做语义重设计）：

| 处置 | 章节 |
| --- | --- |
| `IMPLEMENTED / VERIFIED` | A1–A3、A5–A53（含 A16/A28 空工作区证据）、A54–A86、A90 |
| `BOUNDARY PRESERVED / VERIFIED` | A4（Out of Scope）、A50（经济角色语义未新增 Risk Admission）、A92（STOP 条件未触发语义变更）、A94（`NONE INTENTIONALLY DELEGATED TO IMPLEMENTATION` **保持为真**） |
| `EVIDENCE CAPTURED` | A88（fixture A/B/C 对应 §11.8 / focused fixtures / §11.5–11.6）、A89（结构门 + 报告项；延迟判定不做） |
| `NOT APPLICABLE TO IMPLEMENTATION / BOUNDARY PRESERVED` | A0（Authority）、A87（Schema/Migration/Index = ZERO CHANGE，已实证）、A91（Human Acceptance 边界；实现侧条件已备，Human Acceptance = PENDING）、A93（Human Decision Boundary）、A95（冻结态记录；artifact 本身 ZERO CHANGE） |
| `REMAINS / NON-BLOCKING` | 仅 `R04-P2-01`（已 Frozen 如此） |

**本次 Self Review 结论**：修复 A51 / A56 / A62 / A80 的未实现判据后，**无遗留实现 gap**；未发现需要新语义
决策的歧义，未发现需要 forbidden path 的修复，未扩大 Scope。`A94 = NONE INTENTIONALLY DELEGATED TO
IMPLEMENTATION` **未被本实现静默新增任何语义决策**。

### A52 / A53 与 A25 / A26 强制复审区（任务卡 §4）

- A25/A26：无 current canonical 替换；direct PRE-01B-I2 `DecisionSnapshotRecord` 绑定；多条 durable 来源
  不兼容 ⇒ `SNAPSHOT_FAILED`（见「Decision Binding」）。
- A52/A53：三值齐备、`missing_links` 十值齐备、strong-integrity-before-traceability 顺序成立；
  **当前行为事实**（`PARTIAL` 不可达）见「Traceability Interpretation Note」，本批**未**为实现可达性而改动
  实现（这是任务卡 §4 的明确指示，也是本批唯一的语义性观察项，交由 Independent Review）。
- A74–A80：见「Economic Integrity」；A81–A83 见「Stable Snapshot 与 HTTP / Sanitization」；A84–A86 见
  「Timeline / Cancellation / Cursor」与「OpenAPI / generated.ts」；A87 见「Zero-Change 证明」。
- A88/A89：证据已捕获，**未**转换为 Human performance PASS。
- A91：Acceptance Boundary 的实现侧条件已具备；最终 Human Acceptance = `PENDING`。
- A94：`NONE INTENTIONALLY DELEGATED TO IMPLEMENTATION` 保持为真。

## Zero-Change 证明（相对 New Task Base `7a023f99ac44ac744e5a9885fd82f8a87ef51a94`）

`git diff --name-only <Task Base> -- <path>` 计数：

| 路径组 | changed |
| --- | --- |
| Frozen Requirement（`docs/design/UI-RD01/UI-RD01-I03-Implementation-Requirements.md`） | **0** |
| `backend/src/marketpulse/runtime`（RuntimeHost） | **0** |
| `backend/src/marketpulse/g2` | **0** |
| `backend/src/marketpulse/g3` | **0** |
| `backend/src/marketpulse/g4` | **0** |
| `backend/src/marketpulse/advisory` | **0** |
| `backend/src/marketpulse/edge`（Edge producers） | **0** |
| `backend/src/marketpulse/db`（DB models） | **0** |
| `backend/alembic`（migration / schema / index；仍 10 文件，head `20260917_0010`） | **0** |
| `DECISIONS.md` | **0** |
| `PRODUCT_REQUIREMENTS.md` | **0** |
| `AGENTS.md` | **0** |
| 包清单（`pyproject.toml` / `backend/requirements.txt` / `frontend/package.json`） | **0** |
| `frontend/src/pages`（Product UI） | **0** |

- 全部 tracked 变更 = `api/product/{cursor,models,system}.py` + `frontend/src/api/generated.ts`（4 文件，+1206 行）
  + 本批前述 docs/state 载体；无其他 Product endpoint 被改动（`market_scanner` / `opportunities` / `context` /
  `auth` 均 0）。
- `PRE-RAI Advisory` 变更（`6ebf7a6` / `f0e51d9` / `7a023f9`）已是 New Task Base 的基线，**不是** I03 变更。

## Implemented-on-Candidate Fingerprints

| 文件 | blob（`git hash-object`） | sha256 | 相对 checkpoint |
| --- | --- | --- | --- |
| `api/product/cursor.py` | `849b0692f0d584c5b87be9242a90afde09a9ab7b` | `46e94497767856b5…c03551` | 未变 |
| `api/product/models.py` | `8e8791bceaa0e8b244770fc1614bee072357deb5` | `31d9b7a1cf5c8e2c…dde8bae0` | 未变 |
| `api/product/system.py` | `4d4cad4fb8437687948e1084ecf6381cb48588ee` | `1eabc0819b8b7dfd…79abfcd1` | 未变 |
| `frontend/src/api/generated.ts` | `50640c81352843c2e5acb88db5f23e447d0ad8bb` | `1ae00be9f614beb8…5c92c12c` | 未变 |
| `api/product/trading_audit.py` | `bdac7389ae9d95e36bedf2f0ac60c90aa108ea83` | `d49c9df71bd91303271dcbd9cca7c9dba68a77ddecbb5a473aaa736e4383c054` | **CLOSE-01 修复后** |
| `tests/test_product_trading_audit.py` | `1633fc38dd2d62fa82340e31d004297ceda6139f` | `e16fd30ddee4a7fda0d4ac16a036697ae4743d751ca6184f438a7975572627a5` | **CLOSE-01 修复后** |

## Source clean-01 Preservation

`E:/Documents/MarketPulse-AI-ui-rd01-i03-trading-audit-read-clean-01`（**只读复核，未清理、未改动**）：

- HEAD = `d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b`；branch = `ui-rd01-i03-trading-audit-read-clean-01`
- status = ` M cursor.py / M models.py / M system.py / M generated.ts / ?? trading_audit.py / ?? test_product_trading_audit.py / ?? dev_log/2026-09-22-ui-rd01-i03-trading-audit-read.md`（其 dev_log 为 `STOPPED / BLOCKED` 版本，**未**被移植到 clean-02）
- 6 个 WIP 文件 sha256 **逐字节等于** `tmp-i03-evidence/_baseline_sha256.json`（本批实测复读）：

| 文件 | sha256 |
| --- | --- |
| `cursor.py` | `46e94497767856b577a01f08493323b448933f25a5075583727ca0668ec03551` |
| `models.py` | `31d9b7a1cf5c8e2c6fc806125b8610ab5fe9b38e6ae025e14a391f12dde8bae0` |
| `system.py` | `1eabc0819b8b7dfde235ab2cca816951f26690597ebea947f6305c7d79abfcd1` |
| `generated.ts` | `1ae00be9f614beb89c08f0720ab49d1714f14e1d374443b560edf8875c92c12c` |
| `trading_audit.py` | `1a1c99a5664164f4175d020d6c13e27a7cb48dfdd4a704da3d5105f86fc415a6`（= carry-forward 前的 clean-01 版本） |
| `test_product_trading_audit.py` | `be333b3aa7f2e05a340b23e1329d5b5ea3293be091e3f12b53e44bd72e869beb` |

⇒ clean-01 → clean-02 carry-forward 为 **exact**（4 个 modified + 2 个 added 文件 sha256 完全一致），
且 clean-01 在本批**未被**推进或清理。

## Temporary Evidence

- `tmp-i03-evidence/**`：`.gitignore` **未**覆盖 `tmp-*/`（新增 ignore 规则会构成超范围仓库变更），故以
  untracked 状态存在，**未** stage、**未** commit，从而留在 candidate Git diff **之外**。
- 本批新增的临时工件：`_probe_close01_a80_a51.py`、`_probe_close01_prefix-out.txt`、
  `_probe_close01_postfix-out.txt`、`_probe_conn_close01.txt`、`evidence-20260922-204505.json`、
  `evidence-20260922-204704.json`。
- 本批对 `evidence_harness.py`（仓库外临时设施）做了两处证据性扩展：`_http_probe` 补记 account / collection /
  pending-intents / `timeline_upper_bound` 字段；新增 `ev_empty_workspace`（A16 / A88 fixture A）并纳入
  `_validate_output` 的内建 fail-closed 自校验（缺证据即非零退出）。生产实现**未**被该扩展影响。
- 本地 `.env`（指向隔离 `5450`）、`node_modules` junction、build 产物、临时日志**均未**纳入 candidate。

## Git Evidence

- worktree HEAD = `7a023f99ac44ac744e5a9885fd82f8a87ef51a94`（未动，= New Task Base）
- branch = `ui-rd01-i03-trading-audit-read-clean-02`；candidate ancestry = `7a023f99… → I03 candidate`（单 commit，无 merge / rebase / reset / squash / force）
- `git ls-remote origin refs/heads/main` = `7a023f99ac44ac744e5a9885fd82f8a87ef51a94`（resume 读 + 提交前复读，均未漂移）
- 本批**未**执行 `git reset` / `git checkout` / `git stash`；`git add` **仅**覆盖授权路径

## Remaining / Blockers

1. **无阻塞**：A0–A95 复审完成，A51/A56/A62/A80 conformance fix 已落地并重跑受影响验证。
2. `Performance Human Disposition = PENDING` —— 仅捕获证据，**不**做性能 PASS/FAIL 判定，**不**声称达标。
   事实记录（非结论）：5,200×4 人口下请求耗时 ~14 s，其中 SQL 侧亚毫秒~毫秒级，主要成本在请求内 Python 组装
   （26,007 timeline 候选 + 5,202 行全局校验）；人口级读取走 Seq Scan（契约要求的整人口读取）。
3. **未重跑**：修复后字节的全量 backend 919 回归（见「`919 passed` 与本 candidate 的关系」）。
4. **未执行**：Independent Review、Human Acceptance、`main` 整合。
5. **环境漂移**：共享 5432 `alembic_version = 20260922_0011`（本 Task Base 之外的外部推进；本批零写入）。
6. 遗留容器（未授权清理，未触碰）：`-pg` @ 5434/5437/5438/5440/5441/5443；共享库残留 disposable 库。
7. `R04-P2-01 = REMAINS / NON-BLOCKING`（frozen 如此；本批未修）。

## Context For Next AI

- 本文件**不**构成 Independent Review PASS，也**不**构成 Human Acceptance。下一步 = Independent Review
  （Human 授权后另行开窗），**不**自动整合 `main`，**不**启动 `I04` / `I05`。
- 候选分支 = `ui-rd01-i03-trading-audit-read-clean-02`，单 commit 直接以 `7a023f99…` 为父。
- A52/A53 的 `PARTIAL` 不可达属**已记录的现行行为**，不是本批缺陷；若要改变需新 Batch + Human 决定。
- 本批修复的三处 fail-closed 判据位于 `_validate` 尾部（A51/A62 empty-plan bundle、A56/A80 executed-intent
  without order），改动时**必须**同时维护 focused 测试的消息断言。
- 证据权威工件 = `tmp-i03-evidence/evidence-20260922-204704.json`；harness 可重跑（守卫要求端口 5450、
  cwd = clean-02 worktree 根）；重跑会 `TRUNCATE` 隔离库全部 public 表（保留 `alembic_version`），
  shared 5432 **绝不受影响**。
- 若需补跑全量回归：请先确认共享库 schema 漂移（`20260922_0011` vs Task Base head `20260917_0010`），
  并注意既有环境敏感失败模式（disposable 库建表不完整 / G4 `asyncio.Event` 阻塞）。

---

本批状态

- `UI-RD01-I03-IMP-01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`
- `Latest-Main Reconciliation = PASS`
- `TradingAuditRead = IMPLEMENTED ON CANDIDATE`
- `Request-Level PostgreSQL Evidence = CAPTURED / PERSISTED`
- `History-Heavy Structural Performance Evidence = CAPTURED`
- `Performance Human Disposition = PENDING`
- `UI-RD01-I03-REQ-04 = ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`（未变）
- `Human Acceptance = PENDING`
- `main integration = NOT PERFORMED`
- `R04-P2-01 = REMAINS / NON-BLOCKING`
