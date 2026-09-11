# SE-02A｜Contracts + Additive Persistence

- Date: 2026-09-11
- 专项: SE｜Strategy & Trading Edge
- Batch: SE-02A（SE-02 第一个 Implementation Acceptance Batch）
- Branch: `se-02a-contracts-additive-persistence`
- Worktree: `E:\Documents\MarketPulse-AI-se-02a`（从 Accepted Main clean worktree 创建）
- Status: `IMPLEMENTED / AWAITING RE-REVIEW`（Acceptance Fix #1 已落地，见 §14；未自行 Acceptance，未 merge `main`）

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
  `ReferenceDataStatus(OK | REFERENCE_MISSING | REFERENCE_STALE)`（**Acceptance Fix #1 后**；
  原 `DEGRADED | UNAVAILABLE` 二态与整个 `ReferenceDataReason` 枚举已删除，见 §14）。
- **Forward Horizon**：`30s | 5m | 15m | 1h`（`duration_seconds` = 30/300/900/3600）。
- **Outcome contract types**：`calculation_status`（COMPLETE/INSUFFICIENT_DATA/INVALID；
  **Acceptance Fix #1 后**，原 PENDING/CALCULATED/INCOMPLETE_DATA/NOT_APPLICABLE/FAILED 已删除）、
  `opportunity_lifecycle_at_horizon`（ACTIVE/EXPIRED，原 INVALIDATED/UNKNOWN 已删除；**Fix #1 后**）、
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
| `edge_opportunity_evidence` | PK `evidence_id`；`UNIQUE(opportunity_id, evidence_revision)`；`UNIQUE(evidence_id, opportunity_id)`；复合自引用 FK `(supersedes_evidence_id, opportunity_id) → (evidence_id, opportunity_id)`；CHECK：revision ≥ 1、family = BREAKOUT_RETEST、market_type ∈ {SPOT,SWAP}、source_type ∈ {HISTORICAL_REPLAY,FORWARD_PAPER}、reference_data_status ∈ {OK,REFERENCE_MISSING,REFERENCE_STALE}、`ck_edge_evidence_reference_consistency`（OK ⇒ bid/ask/received_at 全非 NULL 且正/有序；MISSING/STALE ⇒ 三者全 NULL）、`supersedes IS NOT NULL OR revision = 1`（**Fix #1 后**） |
| `edge_bbo_observations` | PK `observation_id`（内容寻址）；CHECK：bid/ask > 0 且 ask ≥ bid、`available_at = received_at`（V1 因果规则，**Fix #1 后**）、market_type、data_quality；复合索引 `(instrument_id, market_type, available_at)` |
| `edge_forward_outcomes` | PK `outcome_id`；`UNIQUE(opportunity_id, evidence_id, horizon, outcome_revision)`；`UNIQUE(outcome_id, opportunity_id)`；复合 FK `(evidence_id, opportunity_id) → edge_opportunity_evidence`；复合自引用 FK `(supersedes_outcome_id, opportunity_id)`；CHECK：revision ≥ 1、horizon ∈ {30s,5m,15m,1h}、calculation_status ∈ {COMPLETE,INSUFFICIENT_DATA,INVALID}、lifecycle ∈ {ACTIVE,EXPIRED}、source_type、`supersedes IS NOT NULL OR revision = 1`（**Fix #1 后**） |
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
   不产生重复的 horizon 参考点。**（Acceptance Fix #1 修正，见 §14.3）**：identity 覆盖
   全部因果事实（含 `available_at`），`data_quality` / `tradable` 留在 identity 之外，
   但 repository 在命中已有 ID 时**必须比较**这两个 immutable eligibility facts ——
   与 identity 内容一致 ⇒ `IDEMPOTENT`，冲突 ⇒ `EdgeBboObservationConflict`（fail closed）。
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

另有测试内 migration boundary 证据（`test_migration_cycle_only_adds_and_removes_edge_tables`；
**Acceptance Fix #1 后新增** `test_migration_reaches_revision_0005_through_a_full_cycle` 与
`test_migration_makes_reference_metrics_nullable_and_drops_the_reason_field`）：
`downgrade 20260905_0004` 后 **edge 表消失而 `positions` / `paper_orders` / `trade_plans` /
`market_events` 等既有表仍在** → 证明本批只新增 Edge 对象，未改动既有 schema。

Fix #1 后的完整往返（disposable PostgreSQL，`marketpulse_se02a_mig_*`）：
`0004 → upgrade head(0005) → downgrade 0004 → upgrade head(0005)`，逐轮断言
`alembic_version` 与 edge 表存在性，并断言 `reference_bid/ask/received_at` 的 nullability
与 `reference_data_reason` 列已消失（详见 §14）。

---

## 8. Verification（真实执行）

> **Acceptance Fix #1 已落地（见 §14），本节数字为「首次实现（Fix #1 前）」的运行记录，
> 保留作为历史证据。Fix #1 后的重新验证数字见 §14.6（contracts 62 / persistence 26 /
> full backend 259）。**

| 命令 | 结果 |
|---|---|
| `pytest backend/tests/test_se_02a_edge_contracts.py -q` | 24 passed |
| `pytest backend/tests/test_se_02a_edge_persistence.py -q` | 14 passed |
| `pytest backend/tests -q`（修复后，运行 #2 与 #4） | **209 passed, 2 warnings**（256.99s / 261.19s） |
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
  （full backend `209 passed` ×2 = 运行 #2 与 #4，逐次记录见 §13）。
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
5. **BBO 观察必须走 `record_bbo_observation()`**，identity 为内容寻址
   （**Fix #1 后输入集合 = instrument_id / market_type / source / source_sequence /
   source_event_time / available_at / received_at / bid / ask**）；
   SE-02B 只负责提供规范化后的 L1 BBO 事实，不改变 identity 输入集合。
   `available_at` 必须等于 `received_at`（V1 因果规则，domain + DB CHECK 双重锁定）；
   重复身份若 `data_quality` / `tradable` 冲突 ⇒ `EdgeBboObservationConflict`，SE-02B
   **不得**吞掉该异常或自行覆盖既有行。
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

---

## 13. Addendum｜全量回归稳定性确认（收尾补记）

本节补记 §8 表格之前的第 3 次全量运行与后续确认，使 §9 中「`209 passed ×2`」的断言有逐次可追溯的运行记录。

| 运行 | 结果 | 证据文件 |
|---|---|---|
| #1 | `23 failed, 186 passed`（`schema_head` 修复前，见 §8） | — |
| #2 | **`209 passed, 2 warnings in 256.99s`** | `E:/Temp/se02a/full_run_2.txt` |
| #3 | **中途卡死**：输出仅 `..............................................FFFFFFFFF.F`（57 B，无 summary） | `E:/Temp/se02a/full_run_3.txt` |
| #4 | **`209 passed, 2 warnings in 261.19s`** | `E:/Temp/se02a/full_run_4.txt` |

命令一律为
`E:/Documents/MarketPulse AI/.venv/Scripts/python.exe -m pytest backend/tests -q --tb=short`，
工作树与 `main` 基线在 #2–#4 之间未变。

**第 3 次卡死的诊断（如实记录）**

- 卡死位置在收集顺序的 group4 中段（约第 58 个用例）；SE-02A 的 38 个用例排在末段，
  **根本未被执行到**，故该次失败**不可能**由本批代码引起；
- 数据库侧排查：无长事务（1 个 active `client backend`）、无锁等待（2 个 lock）；docker 资源正常；
- **`C:` 盘此时 100% 满（可用 ≈1.8 G）**，`E:` 盘 80%；
- 磁盘恢复到 `C:` 可用 ≈4.8 G 后，**同一命令、同一工作树、同一 `main` 立即重跑 #4** ⇒ `209 passed`；
- 结论：判定为**环境资源压力（磁盘写满）叠加共享主库并发**导致的 flaky/阻塞，
  **不是 SE-02A 引入的回归**。#3 早段的 10 个 `F` 与 §8 第 1 次运行中 8 个 `test_group3.py`
  失败同源（共享主库 + `_clean()` 不清理 G2 表 / G4 控制表的既有隔离弱点）。

⇒ §8 与 §9 中的「`209 passed ×2`」由 **运行 #2 与 #4** 构成：两次均为真实执行、
有完整 summary、pytest exit code 0。

**环境备注（本次收尾实测）**：WorkBuddy Bash 工具的 `PATH` 缺失 coreutils
（`ls` / `which` / `head` / `tail` / `dirname` 均 `command not found`），Git 与绝对路径
`python` / `docker` 可用；PowerShell 工具 stdout 被吞。文件枚举改用 `git ls-files -o`、
`Read`、`python -c`。此属工具环境问题，不影响上表任何运行结果（pytest 输出的重定向与
`python` 自持执行均正常）。

---

## 14. Acceptance Fix #1｜3 个 contract blocker 的关闭

- 输入：Independent Acceptance Review 对 `se-02a-contracts-additive-persistence @ 54b8223`
  判定 3 个 contract blocker（P0-1 / P0-2 / P0-3）。
- 约束：只修 SE-02A；不开始 SE-02B；不 merge `main`；不改 G2–G5 economic semantics；
  不实现 calculator / MFE / MAE / expectancy。
- 结果：三项全部落地，migration **就地修正 `20260911_0005`**（未新增 `0006` —— 该 revision
  尚未 Accepted、未 merge、未部署到 primary DB，故不存在"已发布 migration 不可改"的前提）。

### 14.1 P0-1｜evidence 必须能在参考 BBO 缺失/陈旧时存活

| | BEFORE | AFTER |
|---|---|---|
| `reference_bid` / `reference_ask` / `reference_received_at` | 三列 `NOT NULL`（domain `float` / `datetime`） | 三列可空（domain `float \| None` / `datetime \| None`；ORM + 0005 `nullable=True`） |
| 参考状态词表 | `ReferenceDataStatus(OK \| DEGRADED \| UNAVAILABLE)` **+ 独立** `ReferenceDataReason(NONE \| MISSING_BBO \| STALE_BBO \| NON_TRADABLE \| CROSSED_BOOK \| SOURCE_GAP \| UNKNOWN)` | 单字段三态 `ReferenceDataStatus(OK \| REFERENCE_MISSING \| REFERENCE_STALE)`；**整个 `ReferenceDataReason` 枚举删除** |
| 跨字段契约 | 无（NULL 与 0 占位无法区分） | `_reference_data_is_consistent` model_validator + DB CHECK `ck_edge_evidence_reference_consistency` |
| effect | **参考 BBO 缺失的机会无法持久化** → durable sample 系统性丢失 | 缺失/陈旧仍可持久化，指标保持 NULL；**禁止 0 占位** |

最终语义（domain 与 DB 双层一致）：

- `OK` ⇒ `reference_bid` / `reference_ask` / `reference_received_at` **全非 NULL**，
  且 `bid > 0`、`ask > 0`、`bid <= ask`；
- `REFERENCE_MISSING` / `REFERENCE_STALE` ⇒ 三者**全为 NULL**（写 0/哨兵值一律拒绝）；
- `reference_data_reason` 已从 immutable content / `evidence_hash` 输入集合中移除，
  MISSING 与 STALE 因此产生**不同** `evidence_hash`（不是同一 hash 的伪区分）。

### 14.2 P0-2｜恢复 Approved 的 forward outcome 终态语义

| | BEFORE | AFTER |
|---|---|---|
| `calculation_status` | `PENDING \| CALCULATED \| INCOMPLETE_DATA \| NOT_APPLICABLE \| FAILED`，默认 `PENDING` | `COMPLETE \| INSUFFICIENT_DATA \| INVALID`；**必填，无默认** |
| `opportunity_lifecycle_at_horizon` | `ACTIVE \| EXPIRED \| INVALIDATED \| UNKNOWN` | `ACTIVE \| EXPIRED`（不扩展） |
| PENDING 行 | 可持久化（`clock < due_at` 时） | **不存在**：`clock < due_at` ⇒ 无 row；Pending 由 Opportunity + Horizon + Clock **派生**，禁止 `UPDATE PENDING → COMPLETE` |
| invalid data 表达 | 与 lifecycle 词表混用 | 只用 `calculation_status = INVALID`，**不混入** opportunity lifecycle |

- `ForwardOutcomeContract.calculation_status` 由「有默认值」改为**必填**，因此
  construction 阶段就无法造出 `PENDING` 行（contracts 测试覆盖 `TypeError`）。
- DB CHECK `ck_edge_outcome_calculation_status` / `ck_edge_outcome_lifecycle` 同步收紧。
- metrics（`mfe` / `mae` / `reference_return` / `executable_long_return` /
  `cost_adjusted_forward_return`）在终态下**允许为 NULL**（`INSUFFICIENT_DATA` / `INVALID`
  必须可持久化），测试对此逐态验证。
- **仍未实现 SE-02C calculator**（本批只有 persistence contract）。

### 14.3 P0-3｜BBO 观察的因果身份与幂等

| | BEFORE | AFTER |
|---|---|---|
| 因果规则 | 未约束，测试中出现 `available_at=T+5, received_at=T+4` 的分歧 | `available_at == received_at`（domain ModelValidator + DB CHECK `ck_edge_bbo_causal_time`） |
| `observation_id` 输入 | 不含 `available_at` | 含 `available_at`（位于 `received_at` 之前），identity 覆盖全部因果事实 |
| `data_quality` / `tradable` | 不在 identity，命中已有 ID 时**静默**返回 `IDEMPOTENT` | 不在 identity，但命中已有 ID 时 repository **显式比较**这两个 immutable eligibility facts |
| 冲突处理 | 无（冲突被当作重复吞掉） | 内容一致 ⇒ `IDEMPOTENT`；内容冲突 ⇒ **`EdgeBboObservationConflict`（fail closed）** |
| 报价合法性 | 仅 DB CHECK | domain `_positive_prices`（非有限值/非正数拒绝）+ DB CHECK（`bid>0, ask>0, ask>=bid`） |

- 新增异常：`EdgeBboObservationConflict(EdgePersistenceError)`（`repository.py`）。
- 比较集合 `_BBO_IMMUTABLE_FIELDS` = instrument_id / market_type / bid / ask / available_at /
  source_event_time / received_at / source / source_sequence / data_quality / tradable，
  经 `_normalized` 把 `StrEnum` 折叠为持久化字符串形式后逐项比较。
- 可选 `source_sequence`（None）正常参与 identity 与比较，不阻塞。

### 14.4 Schema｜`20260911_0005` 最终形态（就地修正，无 0006）

| 表 | 变化 |
|---|---|
| `edge_opportunity_evidence` | `reference_bid` / `reference_ask` / `reference_received_at` → `nullable=True`；**删除** `reference_data_reason` 列；`ck_edge_evidence_reference_status` → `('OK','REFERENCE_MISSING','REFERENCE_STALE')`；**新增** `ck_edge_evidence_reference_consistency` |
| `edge_bbo_observations` | **新增** `ck_edge_bbo_causal_time`：`available_at = received_at` |
| `edge_forward_outcomes` | `ck_edge_outcome_calculation_status` → `('COMPLETE','INSUFFICIENT_DATA','INVALID')`；`ck_edge_outcome_lifecycle` → `('ACTIVE','EXPIRED')` |
| 其它 | 表集合、既有列、既有 UNIQUE / 复合 FK / index **未变**；仍是纯 additive（相对 `0004`） |

ORM（`backend/src/marketpulse/db/models.py`）与 migration 逐项对齐；`alembic heads` 仍为
`20260911_0005`。**primary `marketpulse` 库未被本批升级**（复核见 §14.7）。

### 14.5 Required Tests 覆盖对照

| 任务书要求 | 覆盖用例 |
|---|---|
| 无 reference BBO 可创建 / stale 可创建 / 缺失字段为 NULL | `test_evidence_persists_without_a_usable_reference_quote`（参数化 MISSING/STALE）、`test_evidence_survives_a_missing_or_stale_reference_quote`（参数化，真实 DB）、`test_unavailable_reference_data_must_not_carry_a_placeholder_quote` |
| OK + NULL prices reject / OK + 非法或交叉价 reject | `test_ok_reference_status_requires_a_complete_quote`、`test_ok_reference_status_rejects_non_positive_or_crossed_prices`、`test_database_rejects_reference_data_that_contradicts_its_status` |
| 状态词表收敛为冻结三态 | `test_reference_status_vocabulary_is_the_frozen_three_state_set`、`test_missing_and_stale_reference_data_do_not_share_an_evidence_hash` |
| missing/stale opportunity 仍占 durable sample | `test_evidence_survives_a_missing_or_stale_reference_quote`（行数断言，non-OK 不被丢弃）、`test_reference_status_change_is_a_conflict_not_a_rewrite` |
| COMPLETE / INSUFFICIENT_DATA / INVALID 可持久化且 metrics 可 NULL | `test_terminal_outcome_statuses_persist_and_metrics_may_be_null`（参数化）、`test_terminal_statuses_build_with_optional_metrics` |
| DB CHECK 拒绝未批准 status / PENDING 不能作为终态 | `test_database_rejects_unapproved_or_pending_outcome_status`、`test_calculation_status_is_required_so_no_pending_row_can_be_built`、`test_only_approved_terminal_outcome_statuses_are_licensed` |
| ACTIVE / EXPIRED 固定 | `test_only_approved_lifecycle_vocabulary_is_licensed`、`test_lifecycle_is_independent_of_calculation_status` |
| exact duplicate → IDEMPOTENT | `test_bbo_observation_persists_the_horizon_reference_schema`、`test_exact_duplicate_revision_is_idempotent` |
| same identity + conflicting eligibility → fail closed | `test_bbo_identity_reuse_with_conflicting_eligibility_fails_closed`（`data_quality` / `tradable` / 价格 三场景 → `EdgeBboObservationConflict`） |
| `available_at != received_at` → reject | `test_bbo_observation_requires_available_at_to_equal_received_at`、`test_database_rejects_bbo_rows_that_bypass_the_causal_rule` |
| non-positive / crossed BBO → reject | `test_bbo_observation_rejects_non_positive_or_crossed_quotes` |
| 可选 source sequence 正常 | `test_bbo_observation_accepts_an_absent_source_sequence` |
| stable deterministic ID / identity 覆盖全部因果事实 | `test_bbo_observation_identity_is_stable_and_deterministic`、`test_bbo_observation_identity_covers_every_causal_fact` |

### 14.6 Verification（Fix #1 后真实执行）

| 命令 | 结果 | 证据文件 |
|---|---|---|
| `pytest backend/tests/test_se_02a_edge_contracts.py -q` | **62 passed** | `E:/Temp/se02a/fix1_contracts.txt` |
| `pytest backend/tests/test_se_02a_edge_persistence.py -q` | **26 passed**（46.11s，真实 disposable PostgreSQL） | `E:/Temp/se02a/fix1_persistence2.txt` |
| `pytest backend/tests/test_group5_2_trading_replay.py test_group5_3_determinism.py test_group2.py -q` | **62 passed**（102.63s） | `E:/Temp/se02a/fix1_targeted2.txt` |
| `pytest backend/tests -q --tb=short -rf` | **259 passed, 2 warnings in 232.78s**（EXIT=0） | `E:/Temp/se02a/fix1_full1.txt` |
| `ruff check backend/src backend/tests scripts backend/alembic` | All checks passed | `E:/Temp/se02a/fix1_ruff.txt` |
| `compileall -q backend/src backend/tests backend/alembic` | PASS（空输出） | `E:/Temp/se02a/fix1_compile.txt` |
| `git diff --check` | PASS（EXIT=0；仅 Git 的 LF→CRLF 换行提示，**无 whitespace error**） | `E:/Temp/se02a/fix1_diffcheck.txt` |

用例总数自洽：baseline `171` + Fix #1 前 SE-02A `24+14=38` = `209`；
Fix #1 后 SE-02A `62+26=88` ⇒ `171+88 = 259`。**full backend 一次干净运行即 259 passed，
无失败、无重跑。**

### 14.7 Regression / 并发写者取证（必须如实记录）

定向回归第 1 次运行出现 `4 failed`（`test_group5_2_trading_replay.py` ×3 +
`test_group5_3_determinism.py` ×1），全部为
`ReplayWorkspaceIsolationError("primary database changed during replay")`（`g5/replay.py:492`）。

诊断（`E:/Temp/se02a/diag_primary.py`、`probe_writers.py`，均为**只读**脚本，不入仓库）：

- 主库业务表存在非零残留数据（如 `market_events=9`），正常跑完的套件会清空；
- 同时段存在**外部并发 pytest 进程**（PID 14732，父链不属于本会话，命令行
  `python.exe -m pytest backend/tests -q --tb=short -rf`）；
- 判定：**环境级共享主库并发写者**（共享单一 `marketpulse` 库 + 整表 `clean()`），
  非本批代码回归。按 CIP-05 **不扩大 Scope**、不修改他人测试隔离实现。

Fix #1 全量运行前/后取证：

| 项 | 值 | 证据 |
|---|---|---|
| 运行前 python 进程扫描 | 无任何 `pytest` 进程（仅 MCP server 与只读 sampler） | `E:/Temp/se02a/procs_now.txt` |
| 运行后 python 进程扫描 | 无任何 `pytest` 进程 | `E:/Temp/se02a/procs_after.txt` |
| 采样器（每 5 s，48 tick，覆盖 06:35:21–06:39:19 ≈ 运行全程） | 全部 `client backend`，**无外来 writer 特征**；套件自身随开随关 | `E:/Temp/se02a/se02a_sampler_log.txt`、`sampler_summary.txt` |
| 运行后 primary `alembic_version` | `20260905_0004`（**未被本批升级**） | `E:/Temp/se02a/post_run_check.txt` |
| 运行后 `pg_database LIKE 'marketpulse_se02a_%'` | `[]`（无残留 disposable DB） | 同上 |
| 运行后 primary client backends | 仅检查脚本自身 1 条 | 同上 |

⇒ 本次 `259 passed` 的运行**无可信外部写者**，结果可采信。

### 14.8 Repository Truth（Fix #1 完成时实测）

| 项 | 值 |
|---|---|
| Task Base SHA | `54b8223ffa95827833029c7fb80369a79982bf7f`（其 parent = `e0dab188`） |
| branch | `se-02a-contracts-additive-persistence` |
| remote branch HEAD（push 前 / push 后） | `54b8223ffa95827833029c7fb80369a79982bf7f` / `48aed372082461e042b4ff71e6066ebb99044f72`（`54b8223..48aed37`） |
| `main`（**任务开始时**实测） | `e0dab188e55c32b7607c18a66644d25449dc2236`（本地 / `origin/main` / `ls-remote` 三者一致） |
| `main`（**push 时**实测，已漂移，见 §14.11） | `6cc4c36e11c380f638872598e4766a4436d0d255`（本地 / `origin/main` / `ls-remote` 三者一致） |
| Fix #1 改动文件 | 5 production + 2 tests + `PROJECT_STATE.md` + 本 dev_log（提交 `48aed37`，9 files changed） |
| 新增 migration | 无（就地修正 `20260911_0005`） |

### 14.9 Fix #1 交付文件

修改（`git diff --stat`：7 files changed, 986 insertions(+), 147 deletions(-)）：

- `backend/src/marketpulse/edge/models.py`（冻结词表 / 可选 reference quote / 跨字段 validator / BBO 因果校验 / `calculation_status` 必填）
- `backend/src/marketpulse/edge/identity.py`（`bbo_observation_id` 纳入 `available_at`）
- `backend/src/marketpulse/edge/repository.py`（`EdgeBboObservationConflict` + immutable eligibility 比较）
- `backend/src/marketpulse/db/models.py`（3 个 Edge ORM 类同步）
- `backend/alembic/versions/20260911_0005_edge_evidence_foundation.py`（就地修正）
- `backend/tests/test_se_02a_edge_contracts.py`（24 → 62 用例）
- `backend/tests/test_se_02a_edge_persistence.py`（14 → 26 用例）

**未修改**：`g5/replay.py`（Fix #1 未触碰 G5）、`backend/src/marketpulse/edge/hashing.py`、
`scripts/verify_*`；未修改 `DECISIONS.md` / `PRODUCT_REQUIREMENTS.md` / `AI_CONTEXT.md`。

### 14.10 Scope Check（Fix #1）

- SE-02B started = **NO**；SE-02C calculator = **NO**；MFE / MAE / expectancy = **NO**
- G2–G5 economic semantics changed = **NO**；G5 canonicalization = 零改动
- Runtime behavior changed = **NO**；Real AI = **NO**；Live Trading = **NO**
- New quant framework = **NO**；`main` merged = **NO**
- 状态：`SE-02A IMPLEMENTED / AWAITING RE-REVIEW`（**未自行写 ACCEPTED**）

### 14.11 基线漂移记录（CIP-03，必须报告）

Fix #1 的 push 完成时（2026-09-11 06:4x）实测发现 **Accepted Main 已从 `e0dab188` 推进**：

| 项 | 值 |
|---|---|
| 任务开始时（本次 Fix #1 的 preflight） | `main` = `e0dab188e55c32b7607c18a66644d25449dc2236` |
| push 时（**已漂移**） | `main` = `6cc4c36e11c380f638872598e4766a4436d0d255`（本地 / `origin/main` / `git ls-remote origin refs/heads/main` 三者一致） |
| 漂移链 | `e0dab18 → 67b0cb5 → 14f387a → 13049a0 → 6cc4c36`（N01-VAL-FIX-01/02/03 + 验收收尾） |
| 性质 | **纯 fast-forward**：`git merge-base --is-ancestor e0dab188 6cc4c36` = 0（`e0dab188` 是新 main 的祖先），无 rewrite、无丢弃 |
| 与 SE-02A 的关系 | `git merge-base --is-ancestor 54b8223 6cc4c36` = 1 ⇒ 本 branch 与漂移后的 main **在 `e0dab188` 处分叉** |
| 重叠面 | `git diff --stat e0dab188 6cc4c36` 仅含 `AI_CONTEXT.md` / `PROJECT_STATE.md` / `backend/tests/test_group4.py` / `backend/tests/test_n01_okx_paper_safety.py` / `backend/tests/test_n01_runtime_resource_lifecycle.py` / 3 个 N01-VAL dev_log —— **不含任何 SE-02A 文件**（`edge/*`、`20260911_0005`、`test_se_02a_*`） |
| 本批动作 | **未** reset / **未** rebase / **未** 改动 main；只 push 自己的 branch（`54b8223..48aed37`） |

两个必须让 Reviewer 知道的结论：

1. **基线漂移发生在任务开始之后**，来源是并行的 N01-VAL 验证修复线收尾（非本批、非本会话所为），
   且为纯 fast-forward，`e0dab188` 仍是当前 main 的祖先 ⇒ 本批的 Task Base 语义未被破坏。
2. **§14.6 的 `259 passed` 是在本 branch（base `e0dab188`）上取得的**，其 baseline 常量
   `171` 也对应 `e0dab188`。因此该数字**只对本 branch 成立**；main 漂移引入的
   `test_group4.py` / `test_n01_*.py` 增量不在其中。若后续把本 branch 合并进新 main，
   全量总数应高于 `259`，需在合并后窗口重新计数（本批不代理该动作）。
   漂移文件与 SE-02A 文件零重叠 ⇒ 预期无 textual conflict（**未验证合并**，不作断言）。

## Latest-Main Final Integration Refresh（2026-09-11）

> 目的：在**最新 Accepted `main`** 上重新构建 SE-02A 集成候选并重跑全部门禁，使
> 集成结果不再绑定被后续 commit 追越的旧基线。本批**不**写 `ACCEPTED / COMPLETE`、
> **不**合并 `main`、**不**改写已评审源码（`0c206c9`）、**不**删除历史分支。

| 项 | 值 |
|---|---|
| 上一次集成时的 main（Previous Integration Main） | `6cc4c36e11c380f638872598e4766a4436d0d255` |
| 当前 Accepted main（Current Accepted Main） | `b3ac21b89e11490a0760f560bc099b9acf91ff48` |
| 已评审 SE-02A 源（Reviewed SE Source，未改写） | `0c206c9c598c735d8f708db6603c02fc4d5a3fa3` |
| 历史集成候选（Historical，仅作证据保留） | `9998e1b`（branch `se-02a-final-integration`） |
| 新集成分支 | `se-02a-final-integration-refresh`（worktree `E:\Documents\MarketPulse-AI-se02a-refresh`） |
| 新集成候选（merge commit） | `2e7bf6a`（parents = `b3ac21b` + `0c206c9`） |
| merge-base(`b3ac21b`, `0c206c9`) | `e0dab188e55c32b7607c18a66644d25449dc2236` |

### 1. 漂移来源与集成构造

- 最新 `main` 在旧集成基线 `6cc4c36` 之上仅新增（`git diff --name-status 6cc4c36 b3ac21b`）：
  `AI_CONTEXT.md`(M)、`PROJECT_STATE.md`(M)、`backend/tests/test_n01_restart_recovery.py`(A)、
  `dev_log/2026-09-11-n01-c-restart-recovery-reconciliation.md`(A)。**未触碰 `backend/src`**。
- 构造方式：`git reset --hard b3ac21b` → `git merge --no-ff 0c206c9`。
  SE-02A 的代码 / 测试 / migration **全部无冲突自动合并**；唯一冲突为 `PROJECT_STATE.md`（`UU`）。
- 语义重叠面：两侧都改写 `PROJECT_STATE.md`（SE-02A 侧 blob 基于 `e0dab188`，相对最新 main
  删除了已验收的 N01-VAL-FIX-01/02/03 与 N01-C 记录）。因此冲突解决采用
  **非回归语义并集**：以最新 main blob 为底（保留 CRLF），仅重新施加 SE-02A 真正新增的增量
  （Migration Head → `20260911_0005`、In Progress 状态行、新增 `## SE-02A Result` 段）。
  验收记录 N01-A/B/C、N01-VAL-FIX-01/02/03、Consolidated Closeout 与 Known Issues 全部保留。

### 2. Diff Integrity（§6，全部 PASS）

对 `b3ac21b..HEAD` 的差异面做四重核验（脚本落盘取证，非目测）：

| 检查 | 方法 | 结果 |
|---|---|---|
| A. 新增文件字节级等同 | `0c206c9:<f>` vs `HEAD:<f>` SHA256 | **9/9 IDENTICAL**（migration 0005、`edge/*` 5 文件、`test_se_02a_*` 2 文件、dev_log） |
| B. `g5/replay.py` 增量等同 | `delta(e0dab188→0c206c9)` vs `delta(b3ac21b→HEAD)` | **IDENTICAL**（仅 `schema_head` 常量 + 注释） |
| C. `db/models.py` 增量等同 | 归一化 added-line 集合比对 | **EQUAL**（各 14037 bytes / 245 行） |
| D. 越界文件扫描 | 白名单外路径 | **0 个**（改动文件恰 12 个，全部属 SE-02A 面） |

改动文件全集（12）：`PROJECT_STATE.md`、`20260911_0005_edge_evidence_foundation.py`、
`db/models.py`、`edge/{__init__,hashing,identity,models,repository}.py`、`g5/replay.py`、
`test_se_02a_edge_contracts.py`、`test_se_02a_edge_persistence.py`、
`dev_log/2026-09-11-se-02a-edge-contracts-persistence.md`。

### 3. Contract / Production Integrity（§17，PASS）

- `git diff --name-status 6cc4c36 b3ac21b -- backend/src` = **空** ⇒ 最新 main 未改动任何生产源码。
- `git diff --name-status 0c206c9 HEAD -- backend/src` = **空** ⇒ 本 refresh **未新增任何** backend/src 改动。
- `git diff --name-only 0c206c9 HEAD -- backend/src/marketpulse/edge` = **空** ⇒ `edge/*` 与已评审源字节级相同。

结论：refresh 引入的**新增业务实现 = 0**；本批唯一的集成产物是 `PROJECT_STATE.md` 的语义并集与
merge commit 本身。

### 4. Migration Truth（§8）

`alembic heads`（refresh tree）实测 = `['20260911_0005']` —— **单 head**，
`20260911_0005`（additive Edge evidence revision，`down_revision = 20260905_0004`）。
`backend/src/marketpulse/g5/replay.py::ReplayTradingRunner.schema_head` 实测 = `20260911_0005`，与唯一 head 一致。

### 5. Migration Cycle（§9，disposable PostgreSQL）

在 disposable 库 `marketpulse_se02a_refresh_mig_<hex>` 上执行
`0004 → upgrade head(0005) → downgrade 0004 → upgrade head(0005)`：

- **23 断言 / 0 失败**，`RESULT=PASS`。
- 单 head、step1 edge 4 表缺席、step2 edge 4 表出现且既有表仍在（**additive**）、
  `edge_opportunity_evidence.reference_bid/reference_ask/reference_received_at` 三者 `is_nullable = YES`、
  `reference_data_reason` **缺席**（字段已删除）、Edge evidence / BBO / ForwardOutcome 约束组齐备
  （`ck_edge_outcome_{horizon,calculation_status,lifecycle,supersedes_required,revision_positive}` 等）、
  step3 edge 4 表移除且既有表保留、step4 重新升级回 `20260911_0005`。
- 收尾断言：无残留 disposable 库；`primary` 库 `alembic_version` 保持 `20260905_0004`（**未被升级**）。
- 脚本缺陷已修：`backend/alembic/env.py` 以 `os.getenv("DATABASE_URL", …)` 优先，故周期内显式把
  `DATABASE_URL` 锚定到 disposable 库（结束还原）；Alembic 同步 command API 经 `asyncio.to_thread()`
  派发，规避 `env.py` 内 `asyncio.run()` 的运行中事件循环冲突。

### 6. Test Environment Exclusivity（§10，CLEAN）

- 主机进程普查（**先按进程名过滤** `python|py\.exe|pytest`，再匹配命令行）与
  `pg_stat_activity`（`backend_type='client backend'`）双视图：
  全量门**前 / 后**两次快照均 `CLEAN`（0 外来 pytest / 0 外来 MarketPulse 写者 / 0 外来 disposable 库）。
- 覆盖整个验证窗口的 5s 连续采样（t=0→724s）：期间出现的所有 `marketpulse_*` 库名逐一对应**本批自身**
  测试场景（`marketpulse_se02a_evidence_*` / `_bbo*` / `_outcome_*` / `marketpulse_n01_a|b|c_*` /
  `marketpulse_g52|g53|g54_*` / `_migration_*`），且 `backends=1`（单一写者）。
  其中 `marketpulse_n01_c_7a56d17b35eb` / `..._8a5b359d43b7` 与本批首次 N01-C 运行的失败输出库名一一吻合，
  归属明确。
- primary `marketpulse` 上的连接仅 `marketpulse||`（仓库 harness）与 N01-A/B 测试自带的
  `marketpulse-n01-vf01-observer` / `marketpulse-n01-b-observer`。

### 7. 解释器口径（本批发现，重要）

N01-C 的 `_run_child()` 断言 `payload["pid"] == Popen.pid`。**Windows venv 的
`…\.venv\Scripts\python.exe` 是重定向启动器**，会再 fork 真实解释器 ⇒ `Popen.pid` 落在启动器上、
子进程 `os.getpid()` 落在真实解释器上，断言必然失败（实测 `17340 ≠ 940`）。

- 这是**调用解释器选择**造成的环境伪影，**不是**产品缺陷、也**不是** refresh 引入的回归。
- 项目规范测试解释器为 `py -3.14`（`C:\Users\hua\AppData\Local\Programs\Python\Python314\python.exe`，
  非重定向；实测 `Popen.pid == 子进程 getpid`），依赖齐备（pytest 8.4.2 / SQLAlchemy 2.0.52 / asyncpg / alembic）。
- 因此本批**全部测试门统一以 `py -3.14` 执行**；凡以 venv `python.exe` 直接调用 pytest 的结果不计入验收。

### 8. 验证结果（§11–§16）

| 门 | 命令 | 结果 |
|---|---|---|
| SE-02A 定向（§11） | `pytest test_se_02a_edge_contracts.py test_se_02a_edge_persistence.py` | **88 passed**（contracts 62 + persistence 26） |
| N01-A（§12） | `pytest test_n01_runtime_resource_lifecycle.py` | **6 passed** |
| N01-B（§12） | `pytest test_n01_okx_paper_safety.py` | **4 passed** |
| N01-C（§12） | `pytest test_n01_restart_recovery.py` | **6 passed** |
| G2 / G3 / G4（§13） | `pytest test_group2.py test_group3.py test_group4.py` | **30 / 16 / 77 passed** |
| G5（§13） | `pytest test_group5_1..5_4` | **32 passed**（10+7+5+10） |
| collect-only 计数（§14） | `pytest backend/tests --collect-only -q` | **267** = 最新 main 基线 **179** + SE-02A **88**（零偏差） |
| 全量后端（§15） | `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` | **267 passed, 1 warning**（263.74s，独占窗口） |
| 静态门（§16） | `ruff check backend/src backend/tests scripts` | `All checks passed!` |
| 静态门（§16） | `compileall -q backend/src backend/tests` | rc=0（无输出） |
| 静态门（§16） | `git diff --check` / `git diff --check b3ac21b..HEAD` | rc=0 / rc=0 |

per-file 计数（§14）：auth 2、group1 6、group2 30、group3 16、group4 77、group5 32、n01 16、se_02a 88 ⇒ 267。

### 9. 本批特有产物与边界

- **refresh 特有的生产改动 = 无**（§17 已证 `0c206c9→HEAD` 的 `backend/src` 差分为空）。
- 本批仅产出：merge commit `2e7bf6a`、`PROJECT_STATE.md` 语义并集、本 dev_log 章节。
- 历史候选 `9998e1b` 与已评审源 `0c206c9` 保留不动；**未** merge `main`；**未** 开启 SE-02B / N01-6。

### 10. 状态

`SE-02A = LATEST-MAIN INTEGRATION VERIFIED / READY FOR INDEPENDENT REVIEW`

**不**写 `ACCEPTED / COMPLETE`（AC 未由独立评审裁决）；`N01 overall` 仍未验收，
`N01-6 / N01-7 / N01-8` 与 Integrated Runtime Host 仍 `NOT STARTED`。
