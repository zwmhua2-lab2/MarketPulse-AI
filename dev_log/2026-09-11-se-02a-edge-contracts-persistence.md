# SE-02A｜Contracts + Additive Persistence

- Date: 2026-09-11
- 专项: SE｜Strategy & Trading Edge
- Batch: SE-02A（SE-02 第一个 Implementation Acceptance Batch）
- Branch: `se-02a-contracts-additive-persistence`
- Worktree: `E:\Documents\MarketPulse-AI-se-02a`（从 Accepted Main clean worktree 创建）
- Status: `IMPLEMENTED / WAITING REVIEW`（未自行 Acceptance，未 merge `main`）

---

## 1. Repository Truth（preflight 实测）

| 项 | 值 |
|---|---|
| Task Base SHA | `e0dab188e55c32b7607c18a66644d25449dc2236` |
| Accepted Main (`git ls-remote origin refs/heads/main`) | `e0dab188e55c32b7607c18a66644d25449dc2236` |
| 本地 `main` | `e0dab18`（与远端一致） |
| 创建 worktree 时 HEAD | `e0dab18` |
| 创建后 worktree 状态 | clean（`git status --porcelain` = 0 项） |
| Migration head（实现后） | `20260911_0005` |
| Migration head（实现前） | `20260905_0004` |

说明：

- 工作区 `E:\Documents\MarketPulse AI` 当时检出 `prb-01-product-requirements-baseline` @ `d47313a`，
  含 27 项未提交变更（历史脏工作树）。`git merge-base e0dab18 d47313a = d47313a`，即该 checkout
  是 Accepted Main 的**祖先**。按项目约定该工作树只读，本批**未**在其中做任何操作。
- 本批从实时 Accepted Main 新建独立 clean worktree 与专项 branch，符合 CIP-02 / CIP-04。

### Repository Truth 差异（必须报告）

**仓库中不存在 SE-02 设计 / approved contract 文档。** 全仓库检索 `SE-02` / `SE02` /
`BREAKOUT_RETEST` / `edge_opportunity_evidence` 仅命中既有 G2 `strategy.py`（`BREAKOUT_RETEST`
作为 setup_type 字符串）与 `test_group2.py`，无 SE 专项目录、无 SE-02 design 文档、
无 `dev_log` SE-02 记录。

因此本批的契约依据只有：任务书 §2–§9 的显式规定 + 既有仓库约定。任务书授权的实现自由度
（"至少覆盖"、"最小充分保护"、"使用当前 PostgreSQL / SQLAlchemy / migration 风格做最小实现"）
用于补齐列级/约束级细节。**所有因缺少 SE-02 design 文档而由本批自行确定的语义，均在
§3「本批自行确定的契约决策」逐条列出，供 Reviewer 挑战。**

---

## 2. 实现内容

### A. Edge domain contracts（新增 `backend/src/marketpulse/edge/`）

| 文件 | 内容 |
|---|---|
| `__init__.py` | 包声明（contracts only，无 capture / 无 calculator / 无 runtime） |
| `hashing.py` | canonical hashing 基础设施（复用 G5 canonicalization） |
| `identity.py` | deterministic identity 派生（approved 公式） |
| `models.py` | domain contracts / 冻结枚举 / 版本常量 |
| `repository.py` | append-only persistence（仅 insert；幂等 / fail closed / supersedes） |

契约清单：

- **Opportunity Identity**：`opportunity_id` / `family_id` / `family_version` /
  `instrument_id` / `market_type` / `candidate_id`。
- **Evidence Revision**：`evidence_id` / `opportunity_id` / `evidence_revision` /
  `evidence_contract_version` / `evidence_hash` / `feature_snapshot_hash` /
  `feature_snapshot_hash_version` / `supersedes_evidence_id`（+ detected/evidence/expiry time、
  source identity、reference BBO、evidence payload、feature snapshot payload、status/reason、
  immutable source manifest identity，覆盖 §3 列出的全部持久化字段）。
- **Evidence Source / Status**：`EvidenceSource(HISTORICAL_REPLAY | FORWARD_PAPER)`；
  `ReferenceDataStatus(OK | DEGRADED | UNAVAILABLE)`；
  `ReferenceDataReason(NONE | MISSING_BBO | STALE_BBO | NON_TRADABLE | CROSSED_BOOK | SOURCE_GAP | UNKNOWN)`。
- **Forward Horizon**：`30s | 5m | 15m | 1h`（`duration_seconds` = 30/300/900/3600）。
- **Outcome contract types**：`calculation_status`（PENDING/CALCULATED/INCOMPLETE_DATA/
  NOT_APPLICABLE/FAILED）、`opportunity_lifecycle_at_horizon`、
  `cost_model_version`、`calculator_version`、`outcome_contract_version`、
  `calculation_digest` + `calculation_digest_version`、`outcome_record_hash` +
  `outcome_record_hash_version`、`outcome_revision`、`supersedes_outcome_id`。
  未来字段 `mfe` / `mae` / `reference_return` / `executable_long_return` /
  `cost_adjusted_forward_return` 已具备持久化能力，**本批不计算**。
- **Attribution**：`AttributionSubjectType(AI | PLAN | RISK | EXECUTION | ECONOMIC_RESULT)`、
  `AttributionEvent`（generic + versioned + append-only lineage）。

### B. Additive Persistence（新增 4 张 Edge 表 + Alembic `20260911_0005`）

| 表 | 关键约束 |
|---|---|
| `edge_opportunity_evidence` | PK `evidence_id`；`UNIQUE(opportunity_id, evidence_revision)`；`UNIQUE(evidence_id, opportunity_id)`；复合自引用 FK `(supersedes_evidence_id, opportunity_id) → (evidence_id, opportunity_id)`；CHECK：revision ≥ 1、family = BREAKOUT_RETEST、market_type ∈ {SPOT,SWAP}、source_type ∈ {HISTORICAL_REPLAY,FORWARD_PAPER}、reference_data_status ∈ {OK,DEGRADED,UNAVAILABLE}、`supersedes IS NOT NULL OR revision = 1` |
| `edge_bbo_observations` | PK `observation_id`（内容寻址）；CHECK：bid/ask > 0 且 ask ≥ bid、market_type、data_quality；复合索引 `(instrument_id, market_type, available_at)` |
| `edge_forward_outcomes` | PK `outcome_id`；`UNIQUE(opportunity_id, evidence_id, horizon, outcome_revision)`；`UNIQUE(outcome_id, opportunity_id)`；复合 FK `(evidence_id, opportunity_id) → edge_opportunity_evidence`；复合自引用 FK `(supersedes_outcome_id, opportunity_id)`；CHECK：revision ≥ 1、horizon ∈ {30s,5m,15m,1h}、calculation_status、lifecycle、source_type、`supersedes IS NOT NULL OR revision = 1` |
| `edge_attribution_events` | PK `attribution_event_id`（内容寻址）；CHECK：subject_type ∈ {AI,PLAN,RISK,EXECUTION,ECONOMIC_RESULT} |

Migration 文件：`backend/alembic/versions/20260911_0005_edge_evidence_foundation.py`
（`down_revision = 20260905_0004`，`upgrade` 建 4 表 + Edge index，`downgrade` 逆序 drop）。

---

## 3. 本批自行确定的契约决策（Reviewer 需重点复核）

1. **revision 链规则（对冻结语义表的解释）**：冻结语义只授权
   "higher revision + valid supersedes → legitimate immutable correction"。
   本批据此实现：`revision = 1` 必须无 supersedes；`revision > 1` 必须提供 supersedes，
   且目标必须是**同一 opportunity 的、revision 恰为 R-1 的既有 revision**。
   跳号（3 supersedes 1）与跨机会/悬空引用一律拒绝。
   理由：这是唯一能保证 correction lineage 无分叉、无缺口的解释，符合项目一贯的 fail-closed 取向。
   若 Reviewer 认为应放宽为"任意更低 revision"，属规格解释变化，须先走 Proposal。
   该规则同时有 DB 层 backstop（`supersedes IS NOT NULL OR revision = 1` + 复合 FK）。
2. **expectancy 未实现为 per-outcome 持久化字段**：任务书 §2 把 "expectancy" 与
   forward return / MFE / MAE 并列，但 expectancy 是 **family 级聚合指标**（SE-02D
   Family Aggregation 的产物），不是单条 outcome revision 的属性。为不制造语义错误的列，
   本批未在 `edge_forward_outcomes` 增加 expectancy 列；`completeness_diagnostics` JSON
   仍可承载诊断信息。若 Reviewer 要求，需先明确 expectancy 的归属层级。
3. **`market_type` 不参与 `opportunity_id`**：严格按任务书给定公式
   `SHA256("se02-opportunity-id-v1", family_id, family_version, instrument_id, candidate_id)`。
   SPOT/SWAP 经 `instrument_id` 区分（符合既有 DECISIONS：二者是不同 instrument）。
4. **append-only 的实现层级**：按 §6 指示"避免复杂 trigger framework"，
   `repository.py` 只暴露 insert（无 update/delete API），immutability 由
   PK/UNIQUE/复合 FK/CHECK 在 DB 层兜底。PostgreSQL 层阻止 UPDATE/DELETE 需要
   trigger/rule，本批**有意未引入**。
5. **`calculation_digest` 与 `outcome_record_hash` 的边界**：
   `calculation_digest` 覆盖"计算事实"（opportunity/evidence/horizon/BBO 引用/价格/MFE/MAE/
   returns/cost policy/cost model/calculator version/calculation status/diagnostics），
   **不含 provenance**；`outcome_record_hash` 覆盖完整不可变记录（含 `source_type` /
   `source_identity` / revision / supersedes / created_at / digest）。
   因此 Replay 与 Forward Paper 在同一市场事实下共享同一 calculation digest，
   而 record hash 不同——正是 §9 要求证明的分离性。
6. **BBO observation identity 为内容寻址**：同一 observation 重复摄取幂等，
   不产生重复的 horizon 参考点。
7. **Attribution event identity 为内容寻址**：沿用 PK 唯一性实现幂等，
   因此未引入额外的 `dedupe_key` 字段（避免创造多余概念）。

---

## 4. 阻塞性最小修复（必须报告）

**`backend/src/marketpulse/g5/replay.py:446`：`schema_head` 由 `20260905_0004` 改为 `20260911_0005`。**

- 原因：`ReplayWorkspaceGuard.validate()` 断言 replay workspace 的 `alembic_version`
  等于硬编码 head。本批授权的新 Alembic revision 必然使该常量过期，
  导致 G5-2 / G5-3 / G5-4 全部失败（实测：`replay schema is '20260911_0005',
  expected Alembic head '20260905_0004'`）。
- 判定：该常量是 **migration head 的派生事实**，不是 replay 业务语义、不是风险规则、
  不是状态机语义、不是数据语义。按 CIP-05，它**阻塞当前 AC**
  （AC 要求 "full backend regression PASS" 且 G1–G5 保持），因此做最小修复。
- 变更范围：单行常量 + 注释。Guard 的行为（separate + migrated + clean workspace）未变；
  未触碰 Replay 编排逻辑、G2/G3/G4 组件、canonical/evaluation。
- 这是本批对 G5 文件的**唯一**改动；请 Reviewer 独立确认其对 G5-1～G5-4 已验收语义零影响。

---

## 5. Identity & Immutability 证据

### Identity（`backend/tests/test_se_02a_edge_contracts.py`）

- `opportunity_id` 确定性：同输入两次构建相等，且等于按 approved 公式独立重算的值（64 hex）。
- 敏感性：`candidate_id` / `instrument_id` / `family_version` 任一变化 → id 变化。
- `evidence_id` 确定性：同输入相等；`evidence_revision` 变化 → `evidence_id` 变化。
- **correction 不改 logical opportunity identity**：revision 2（supersedes revision 1）与
  revision 1 的 `opportunity_id` 相同，`evidence_id` / `evidence_hash` 不同。
- **calculator version 不影响 `opportunity_id`**：`calculator_version` calc-v1 → calc-v9 时
  `opportunity_id` / `outcome_id` 不变，而 `calculation_digest` 变化。
- 篡改派生值（`opportunity_id` / `evidence_id` / `evidence_hash` /
  `feature_snapshot_hash` / payload）→ `ValidationError`（fail closed）。

### Canonical hashing（复用 G5 canonicalization，不引入第二套 serializer）

`hashing.canonical_bytes` 直接调用 `marketpulse.g5.canonical.canonicalize_value`，
仅在其上增加字节编码、domain separation 与非有限值拒绝。

- 同语义对象 → 同 hash；字典键序不影响结果。
- 类型敏感：`1` ≠ `"1"`，`1` ≠ `1.0`，`0.1` ≠ `Decimal("0.1")`，`0.1` ≠ `0.1.hex()`，
  `{"a":1}` ≠ `{"a":"1"}`。
- domain separation：不同 domain tag → 不同 digest；`feature_snapshot_hash` ≠
  `outcome_record_hash` 对同一输入。
- datetime 归一：同一时刻不同时区 → 同 hash；naive datetime → 拒绝
  （`CanonicalHashError`，且在 contract 层之前失败）。
- float canonicalization：精度损失可区分。
- 非有限值拒绝：`nan` / `inf` / `-inf` / `Decimal("NaN")` / `Decimal("Infinity")`
  在顶层与嵌套位置均 `CanonicalHashError`。

### Immutability / idempotency（`backend/tests/test_se_02a_edge_persistence.py`）

真实 disposable PostgreSQL（`marketpulse_se02a_<label>_<hex>`，`alembic upgrade head`）：

| 场景 | 结果 |
|---|---|
| 首次 evidence 插入 | `INSERTED`，全字段（含检测/证据/过期时间、source identity、reference BBO、payload、hash、manifest）读回一致 |
| 完全相同 revision 重复插入 | `IDEMPOTENT`，行数保持 1 |
| 同 opportunity + 同 revision + 不同 hash | `EdgeEvidenceConflict`（fail closed），行数保持 1 |
| revision 2 supersedes revision 1 | `INSERTED`，两行共存，revision 1 未被覆盖/删除 |
| 跨 opportunity supersedes | `EdgeInvalidSupersedes`（服务层）+ `IntegrityError`（DB 复合 FK 直插） |
| 不存在 supersedes 目标 | `EdgeInvalidSupersedes` + DB FK `IntegrityError` |
| 跳号 revision 3 supersedes revision 1 | `EdgeInvalidSupersedes` |
| 绕过服务层直插 revision 2 无 supersedes | DB CHECK `IntegrityError` |
| 绕过服务层直插 family = TREND_PULLBACK | DB CHECK `IntegrityError` |
| 绕过服务层直插 revision 0 | DB CHECK `IntegrityError` |

---

## 6. BBO / Outcome 证据

- `edge_bbo_observations`：bid/ask、`available_at`、`source_event_time`、`received_at`、
  `data_quality`、`tradable`、`source`、可选 `source_sequence`（int + nullable）、market identity
  均正确持久化；重复观察 `IDEMPOTENT`；`ask < bid` 被 DB CHECK 拒绝。
  **未测试任何 runtime quote capture（本批不存在）。**
- `edge_forward_outcomes`：immutable revision 持久化（revision 1 / 2 + supersedes）、
  重复插入 `IDEMPOTENT`、`calculation_digest` ≠ `outcome_record_hash`、
  Replay 与 Forward Paper 两条 provenance 不同但共享同一 `calculation_digest` 且
  `outcome_record_hash` 不同、跨机会/悬空 evidence 引用被复合 FK 拒绝、
  `horizon = 1m / 5s`、非法 `calculation_status`、非法 lifecycle、revision > 1 无 supersedes
  均被 DB CHECK 拒绝。**未测试任何 MFE/MAE calculator（本批不存在）。**
- `edge_attribution_events`：AI / PLAN / ECONOMIC_RESULT 三条事件 append 后共存
  （append 不覆盖），重复 append `IDEMPOTENT`，非法 `subject_type` 被 DB CHECK 拒绝。
  **未修改任何 G3/G4 economic semantics。**

---

## 7. Migration 验证

Disposable PostgreSQL（`marketpulse_se02a_mig_*`）：

```
alembic upgrade head      → 20260911_0005 (head)，4 张 edge 表建立
alembic current / heads   → 20260911_0005 (head) / 20260911_0005 (head)
alembic downgrade base    → 全部表移除
alembic upgrade head      → 重新建立
DROP DATABASE             → 无残留
```

另有测试内 migration boundary 证据
（`test_migration_cycle_only_adds_and_removes_edge_tables`）：
`downgrade 20260905_0004` 后 **edge 表消失而 `positions` / `paper_orders` / `trade_plans` /
`market_events` 等既有表仍在** → 证明本批只新增 Edge 对象，未改动既有 schema。

---

## 8. Verification（真实执行）

| 命令 | 结果 |
|---|---|
| `pytest backend/tests/test_se_02a_edge_contracts.py -q` | 24 passed |
| `pytest backend/tests/test_se_02a_edge_persistence.py -q` | 14 passed |
| `pytest backend/tests -q`（第 2 次） | **209 passed, 2 warnings** |
| `ruff check backend/src backend/tests scripts backend/alembic` | All checks passed |
| `compileall -q backend/src backend/tests backend/alembic` | PASS |
| `git diff --check` | PASS |
| `alembic upgrade/downgrade/upgrade`（disposable DB） | PASS（见 §7） |
| `pg_database LIKE 'marketpulse_se02a_%'` | 0（无残留 disposable DB） |

### 关于第 1 次全量回归（必须如实记录）

实现 `schema_head` 修复**之前**的第 1 次全量运行：`23 failed, 186 passed`。
其中 15 项（G5-2 ×5、G5-3 ×1、G5-4 ×9）已**确定性根因化**为硬编码 schema head，
修复后全部通过（见 §4）。剩余 8 项为 `test_group3.py` 的 PostgreSQL 用例：

- `test_group3.py` 不 import 任何 G5 模块，结构上不可能受 `schema_head` 影响；
- 该模块单独运行 `16 passed`（多次）；修复后两次全量运行均通过；
- 主库当前无异常控制状态（`runtime_controls` = NORMAL/RUNNING、无 blocked symbol、
  无 incident），本批未对主库做任何写入。

结论：这 8 项**未复现**，且与本批交付的变更无结构耦合；按证据判定为 `test_group3.py`
依赖共享主库状态（`_clean()` 不清理 G2 表与 G4 控制表）的既有隔离弱点/环境依赖波动，
**不属于 SE-02A 引入的回归**。本项作为**未独立复现的观察**保留，供 Reviewer 独立判断。

---

## 9. Regression（G1–G5 是否保持）

- `G1 / G2 / G3 / G4 / G5-1 / G5-2 / G5-3 / G5-4` 定向与全量用例全部通过
  （full backend 209 passed ×2）。
- G5 canonicalization（`g5/canonical.py`）**零改动**：SE-02A 只是复用方。
- `g5/replay.py` 仅改 `schema_head` 常量（见 §4）。
- 未修改任何 G2/G3/G4/G5 既有表 semantics、Risk、Execution、State Machine、
  Replay semantics、G3 accounting semantics。

---

## 10. Scope Check

- Runtime behavior changed = **NO**（未接 Scanner / EventRuntime / StrategyEngine /
  G3 Decision / Risk Gate / PaperExecutionService / G4 / G5 Replay orchestration）
- G2/G3/G4/G5 economic semantics changed = **NO**
- Existing account/order/fill/trade/ledger schema changed = **NO**
- Real AI activated = **NO**
- Live Trading activated = **NO**
- SE-02B Opportunity Capture = 未开始
- SE-02C Forward Outcome Calculator = 未实现（仅 persistence contract + digest 边界）
- SE-02D Family Aggregation / expectancy = 未实现
- L2/L3、Liquidation、cryptofeed、Tardis、hftbacktest、vectorbt、QuantStats、
  strategy optimization、KEEP/DOWNWEIGHT/KILL、API/UI/Dashboard = 未触碰

---

## 11. Remaining / 交棒 SE-02B 必须继承的事实

1. **Opportunity 事实源**：`opportunity_id` 只能由
   `(family_id, family_version, instrument_id, candidate_id)` 派生；
   SE-02B capture 必须复用 `build_opportunity_identity()`，不得自造 ID。
2. **本批唯一允许 family = `BREAKOUT_RETEST`**（domain enum + DB CHECK 双重锁定）；
   新增 family 需要新 migration 与新批准，不得只改 Python。
3. **本批唯一允许 horizon = 30s / 5m / 15m / 1h**（domain enum + DB CHECK）。
4. **evidence revision 写入必须走 `append_evidence_revision()`**：
   - revision 1 必须 `supersedes=None`；
   - revision > 1 必须 supersedes **恰好 R-1** 的同 opportunity revision；
   - 同 revision 同 hash 幂等，同 revision 不同 hash 一律 `EdgeEvidenceConflict`。
   不得在 SE-02B 里写第二条写入路径或做 UPDATE。
5. **BBO 观察必须走 `record_bbo_observation()`**，identity 为内容寻址；
   SE-02B 只负责提供规范化后的 L1 BBO 事实，不改变 identity 输入集合。
6. **`edge_forward_outcomes` 的 `evidence_id` 必须属于同一 `opportunity_id`**
   （复合 FK），且 outcome revision 链规则与 evidence 相同。
7. **`calculation_digest` 的输入集合已冻结**（见 §3.5）：
   SE-02C 若需要把新的计算事实纳入 digest，必须先改
   `_outcome_calculation_content()` 并接受 `calculation_digest_version` 变化。
8. **`calculation_digest_version` / `outcome_record_hash_version` /
   `feature_snapshot_hash_version` 的取值即 domain tag**，改 tag 等于改契约。
9. **Migration head 现为 `20260911_0005`**；SE-02B 若新增 migration 必须
   `down_revision = 20260911_0005`，并同步 `ReplayTradingRunner.schema_head`。
10. **本地主库 `marketpulse` 仍停在 `20260905_0004`**（未由本批升级，避免未经授权修改
    外部系统状态）。如需让主库与 head 一致，由 Operator 执行
    `alembic upgrade head`（纯 additive，可 `downgrade 20260905_0004` 回退）。
11. **`.workbuddy` 与 `E:/Temp/se02a/full_run_*.txt`** 为本批证据文件，未纳入 Git。

---

## 12. 本批交付文件

新增：

- `backend/src/marketpulse/edge/__init__.py`
- `backend/src/marketpulse/edge/hashing.py`
- `backend/src/marketpulse/edge/identity.py`
- `backend/src/marketpulse/edge/models.py`
- `backend/src/marketpulse/edge/repository.py`
- `backend/alembic/versions/20260911_0005_edge_evidence_foundation.py`
- `backend/tests/test_se_02a_edge_contracts.py`
- `backend/tests/test_se_02a_edge_persistence.py`
- `dev_log/2026-09-11-se-02a-edge-contracts-persistence.md`（本文件）

修改（additive / 最小）：

- `backend/src/marketpulse/db/models.py`：新增 4 个 Edge ORM 类 + import 扩展
  （未改动任何既有类）。
- `backend/src/marketpulse/g5/replay.py`：仅 `schema_head` 常量（见 §4）。
- `PROJECT_STATE.md`：Migration Head 与 SE-02A 状态（最小同步，见 §13）。

**未修改**：`DECISIONS.md`（本批未形成新的正式产品/架构决策）、
`PRODUCT_REQUIREMENTS.md`（未发现需求基线冲突）、`AI_CONTEXT.md`。
