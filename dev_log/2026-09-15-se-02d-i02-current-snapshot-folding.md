# SE-02D-I02 — Current-Snapshot Revision Folding（实现记录）

日期：2026-09-15
分支：`se-02d-i02-current-snapshot-folding`
Accepted Main SHA（CIP-02 实时读取）：`0ae5b0b`（HEAD = main = origin/main，无 baseline drift，AC-01 满足）

## 1. 任务与边界

- 归属：单个 `REPEATABLE READ READ ONLY` 快照读取 → `statement_timestamp()` 作 `as_of`
  （非 Python 时钟）→ 全量可见 Evidence 修订链校验/折叠 → 规范化 Evidence 头 →
  精确 horizon 可见 Outcome 修订链校验/折叠 → 规范化 Outcome 头 / `NO_OUTCOME` →
  `CanonicalScopeFacts` → 修订感知 manifest。
- 禁止（Out of Scope）：聚合统计、historical `as_of` 接口、调用 `aggregate()`、改动
  I01（`aggregation.py`）、schema / migration / frontend / config / scripts 变更。
- 新增：`backend/src/marketpulse/edge/aggregation_snapshot.py`；
  测试 `backend/tests/test_se_02d_aggregation_snapshot.py`（35 个：30 纯 + 4 MVCC + 1 regression）。

## 2. 实现要点

- `CurrentSnapshotRevisionReader.read(horizon)`：单事务
  `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` →
  `SELECT statement_timestamp()` 作 `as_of` → 读取两表 → fold → project → rollback。
  无 `as_of` 形参（测试 `test_no_historical_as_of_interface` 断言）。
- fail-closed：`SnapshotIntegrityError(conflicts: Sequence[str])` →
  `self.conflicts = tuple(conflicts)`；所有冲突标识符一律以**单元素元组**
  `((f"...",))` 包裹，从设计上杜绝原 I01-R1 类「`tuple("字符串")` 拆字符」缺陷
  （CIP-07：冲突标识符须可信、不可由 digest 派生）。
- 复用 I01：`PopulationKey` / `MeasurementSignature` / `CanonicalScopeFacts` /
  `classify_maturity` / `forward_due_at`。

## 3. 验证结果（真实验行）

- `ruff check`：**All checks passed!**（RUFF_RC=0）。修复项：
  导入 `Mapping` / `Sequence` 改自 `collections.abc`（UP035）；
  11 处冲突标识符多行 f-string 隐式拼接加括号包裹（ISC004）。
- I02 测试：**35 passed**（10.08s）。含 4 个真实 Postgres MVCC 测试
  （snapshot_a/b/c/d，验证 REPEATABLE READ 快照隔离、`statement_timestamp()` 作
  `as_of`、snapshot_b 断言 `(2,1)`）与 1 个 query-time regression。
- 回归（I01 / SE-02A / SE-02C，5 个文件）：**263 passed**（228.68s）。
  确认 I02 纯增量未破坏既有模块。
- `git diff --check`：rc=0（与 commit 同步复核）。

## 4. 事故披露（须 Independent Review 知悉）

- 上一会话执行 `git show :backend/.../aggregation_snapshot.py > 该文件` 时，git index
  该条目为**空 blob**（`e69de29bb2d1d6434b8b29ae775ad8c2e48c5391`），命令把工作树文件
  覆盖为 0 字节，原实现文件**已丢失且无任何副本可恢复**（已排查 .pyc / git 对象库 213
  个候选 blob / WorkBuddy traces / conversation_search / 主工作区，均无副本）。
- 本次实现基于**权威测试契约（35 用例，精确规定 API 与行为）+ 任务规格 + I01 复用块**
  重建，非凭空自创，属「已批准设计」的忠实重构。重建后经 35 测试全过、ruff 0、回归
  263 全过验证。
- 重建中修正 / 补全（均对照真实测试契约，非自创设计）：
  ① `MarketType` 从 `marketpulse.market_data.models` 导入（edge.models 不导出）；
  ② `CanonicalScopeFacts` 两分支均设 `folded_evidence_revision_count`；
  ③ manifest 条目与每个 `outcome_revision_identities` 元素补 `outcome_id`
  （测试契约要求，原摘要漏列，已对照真实测试补齐 — 见下方「编辑丢失」说明）。

## 5. 编辑丢失修复说明

- 首次补 `outcome_id` 时，将两个 Edit **并行**作用于同一文件，触发已知坑
  （「同一文件多次 Edit 必须串行，并行 Edit 丢更新」）：`outcome_identities` 的
  `outcome_id` 生效，manifest 条目的 `outcome_id` 被覆盖丢失 → 单测
  `test_folded_evidence_outcomes_excluded_not_in_economic_facts` 报
  `KeyError: 'outcome_id'`。
- 以**串行** Edit 补回 manifest 条目 `outcome_id` 后，35/35 全过。此属实现内修复，
  不影响设计边界。

## 6. 授权状态说明

- 注入的项目记忆（I01 closeout 时期）曾标注 `SE-02D-I02` = NOT STARTED / 未授权，
  且「收尾不自动解锁下游」。
- 本工作依据后续下发的 I02 任务卡（含明确 Scope / Out-of-Scope）及用户「continue」指令
  执行；分支 `se-02d-i02-current-snapshot-folding` 已建、文件已 staged、测试已写并全过。
  据此判定 I02 已获授权，前述记忆基线为更早快照，不冲突。
- **未改动 `main`**，未 merge / rebase / force；仅 commit 至 I02 分支并 push 供
  Independent Review。

## 7. 状态

- 实现完成、验证全绿、待 Independent Review。STOP（不启动 I03）。

## 8. FIX-01 — Cross-Integrity + Canonical Manifest Contract（2026-09-15）

Independent Review = **FAIL — FIX REQUIRED**（P0：NONE）

| Finding | 级别 | 状态 |
|---|---|---|
| `SE02D-I02-R1` Evidence ↔ Outcome cross-integrity omits `source_type` | P1 | **FIXED / AWAITING INDEPENDENT RE-REVIEW** |
| `SE02D-I02-R2` I02 hand-built manifest drops Accepted I01/D01 canonical manifest fields | P1 | **FIXED / AWAITING INDEPENDENT RE-REVIEW** |
| `SE02D-I02-R3` `CurrentSnapshotProjection` does not explicitly carry `horizon` | P2 | **FIXED / AWAITING INDEPENDENT RE-REVIEW** |

> Worker 不将任何 finding 标记为 CLOSED / ACCEPTED。

### 8.1 SHA 基线

- Previous candidate SHA（Independent Review 时点）：`77c01c945d2a9dc7cae68435e0c334b1cd5d9c72`
- FIX-01 fix commit（code + tests）：`bf8cb6f33f724f2e68872d27b68df627afe14fd8`
- FIX-01 dev_log 记录 commit（= new branch tip）：紧随 `bf8cb6f` 的
  `docs(se-02d-i02): record FIX-01 verification evidence`；literal SHA 见 FIX-01 Final Report Section D
- 当前 live main（实时 `git ls-remote origin refs/heads/main`）：`41558c9096a42bc7a960d4d04cd4b0a9955163ea`（= 任务卡 issuance 值，无新增 main drift）
- I02 lineage：`0ae5b0b` → `77c01c9` → `bf8cb6f` →（dev_log commit）。
  未 rebase / squash / merge main / cherry-pick main / reset history / force push；未 amend `77c01c9`。

### 8.2 改动文件（仅 3 个授权文件）

| 文件 | 变更 |
|---|---|
| `backend/src/marketpulse/edge/aggregation_snapshot.py` | R1 交叉完整性补齐 4 项校验；R2 manifest 改为复用 `build_ordered_input_manifest`；R3 `CurrentSnapshotProjection` 增加 `horizon` |
| `backend/tests/test_se_02d_aggregation_snapshot.py` | 新增 9 个测试（R1 ×2、R2 ×5、R3 ×2） |
| `dev_log/2026-09-15-se-02d-i02-current-snapshot-folding.md` | 本 FIX-01 记录 |

### 8.3 R1 — 完整 Evidence ↔ Outcome 交叉完整性

`_check_cross_integrity` 现在逐项 fail closed（`SnapshotIntegrityError`，冲突标识符一律单元素元组）：

1. `outcome.opportunity_id == evidence.opportunity_id`
2. `outcome.evidence_id == evidence.evidence_id`
3. `outcome.horizon == requested horizon`
4. `outcome.source_type == evidence.source_type`（**新增，R1 核心**）
5. `outcome.source_identity == evidence.source_identity`（保持）
6. `outcome.due_at == forward_due_at(evidence.evidence_at, horizon)`（保持）

不把任一侧规范化到另一侧，不静默保留 Outcome。定向回归：Evidence `source_type=HISTORICAL_REPLAY` /
`source_identity="same-source"` vs Outcome `source_type=FORWARD_PAPER` / `source_identity="same-source"`
→ `SnapshotIntegrityError`，证明匹配的 `source_identity` 不能掩盖 `source_type` 不一致
（`test_evidence_outcome_source_type_mismatch_fails_closed`）。六项链接各有独立反例
（`test_cross_integrity_checks_every_link_field_fail_closed`），并验证 `outcome=None` 仍为 no-op。

### 8.4 R2 — I01 canonical manifest 权威

- 删除 I02 手写 manifest schema，改调 `build_ordered_input_manifest(facts, as_of=as_of)` 生成 base，
  再逐条扩展 `no_outcome`（I02 原有诊断字段；任务 §11/§14 允许 I02 附加字段，§5 禁止清单未含此键）、
  `evidence_revision_identities`、`outcome_revision_identities`。
- 未引入第二个 serializer、第二个 float→hex 实现，未在 I02 重算任何 I01 字段。
- revision identity 补全身份字段：Evidence `{evidence_id, evidence_revision, evidence_hash, role}`；
  Outcome `{outcome_id, outcome_revision, outcome_record_hash, role}`；role 仍为
  `CANONICAL` / `FOLDED_EVIDENCE` / `FOLDED_OUTCOME`，按 revision 升序。
- 强兼容证明：`zip(base, projection.manifest, strict=True)` 后逐 key 断言 `i02_entry[key] == value`
  （`test_i02_manifest_preserves_every_i01_base_key_and_value`）。
- `NO_OUTCOME` 保持 I01 语义：`outcome_id` / `outcome_revision` / `outcome_record_hash` = `None`、
  `measurement_signature = NO_MEASUREMENT`、`outcome_revision_identities = []`。
- COMPLETE 数值位绑定保持：5 个 `*_hex` 与 I01 base 逐位相等且非 None，`integrity_conflicts == []`。

### 8.5 R3 — 显式 projection horizon

`CurrentSnapshotProjection` 形状 = `as_of` / `horizon` / `facts` / `manifest`；
`read(horizon)` 返回 `projection.horizon == horizon`。空快照证明：0 行 Evidence 的 disposable 库上
`read(ForwardHorizon.M5)` → `horizon == ForwardHorizon.M5`、`facts == ()`、`manifest == ()`，
horizon 不依赖 sample facts 是否存在。

### 8.6 验证结果（真实验行）

| 项 | 结果 |
|---|---|
| I02 focused（`test_se_02d_aggregation_snapshot.py`） | **44 passed**（11.34s）；原 35 + 新增 9 |
| PostgreSQL MVCC（snapshot A/B/C/D + query-time regression + empty projection） | **全过**（含在 44 内） |
| I01 回归（`test_se_02d_aggregation.py`） | **108 passed**（6.17s） |
| SE-02A/SE-02C 回归（contracts / persistence / calculator / service） | **155 passed**（220.38s） |
| `ruff check backend/src backend/tests scripts` | **All checks passed!**（rc=0） |
| `git diff --check` | rc=0 |

DB-backed 测试全部使用 disposable DB（`marketpulse_se02d_*` 现场建/删），未触碰 accepted / shared 应用库。
reader 事务契约（单事务 / `REPEATABLE READ READ ONLY` / `statement_timestamp()` 作 `as_of` / rollback）
未做任何改动。

### 8.7 Scope 核实

Schema = NO；Migration = NO；Production Dependency = NO；Accepted I01 实现改动 = NO；
State Docs（AGENTS / AI_CONTEXT / PROJECT_STATE / DECISIONS / PRODUCT_REQUIREMENTS）= NO；
Runtime 激活 = NO；API/UI = NO；`main` 被 FIX-01 改动 = NO。

### 8.8 剩余限制

- I01 = ACCEPTED / COMPLETE；I02 = **AWAITING INDEPENDENT RE-REVIEW**（Worker 不判 CLOSED）。
- Population grouping + invocation of I01 aggregate = NOT YET IMPLEMENTED。
- Historical revision-as-of = OPEN；Experiment / pair / arm identity = OPEN；Durable regime identity = OPEN。
- Gate C = NOT PASSED；Live = NOT AUTHORIZED。
- 已知残留（本 FIX-01 未触碰、未获授权清理）：工作树内上一会话遗留日志
  `pytest_i02_pure.log` / `pytest_i02_pure2.log` / `pytest_i02_all.log`（gitignored，非本次产物）。
- 未启动 I03。STOP。

### 8.9 NEW MAIN DRIFT（FIX-01 期间实测记录，更正 §8.1）

FIX-01 push 后复核远端真值时发现 `main` 已推进：

- 任务卡 issuance 时 live main：`41558c9096a42bc7a960d4d04cd4b0a9955163ea`
- FIX-01 完成后实测 live main（`git ls-remote origin refs/heads/main`）：
  `664207a9caba0c3f5c2589cfca2a10af24f89108`
- 新增 commit：`664207a` `docs(pre-01b): record final I1 validation evidence`（2026-09-15 21:24:00 +0800）
- 该 commit 改动文件（全部）：`dev_log/2026-09-15-pre-01b-i1-close-final-validation.md`（+138，仅文档）
- 关系：`git merge-base --is-ancestor 41558c9 664207a` 成立 ⇒ **forward**，非历史重写；
  与 I02 分支 lineage（`0ae5b0b → 77c01c9 → bf8cb6f → 3e9b8f0`）正交。

相关性判定：该 drift 不触及 `backend/**`、`frontend/**`、`config/**`、`scripts/**`、
`docs/design/**`，不含 schema / migration 变更，也不触及任何 R1 / R2 / R3 的修复面
（`backend/src/marketpulse/edge/aggregation_snapshot.py`、
`backend/tests/test_se_02d_aggregation_snapshot.py`）。
⇒ **demonstrably irrelevant to 三项授权修复**，按任务卡 §22 继续执行；
本 FIX-01 未做任何 main reconciliation（未 rebase / 未 merge main / 未 cherry-pick / 未改 main）。

> 更正声明：§8.1 中「无新增 main drift」系基于任务开始 preflight 的推断，现已过时；
> 以本节实测值为准。

### 8.10 远端真值（push 后核实）

| Ref | SHA |
|---|---|
| `refs/heads/se-02d-i02-current-snapshot-folding` | `3e9b8f016369758100fd5999388d815b097023ed` |
| `refs/heads/main` | `664207a9caba0c3f5c2589cfca2a10af24f89108` |

Push 为 fast-forward（`77c01c9..3e9b8f0`），未 force push。

### 8.11 FIX-01 追加 commit 全序列与最终 tip 定义

FIX-01 在 `77c01c9` 之后追加的 commit（fast-forward push；未 rebase / squash / merge main /
cherry-pick / reset history / force push；未 amend `77c01c9`）：

| # | SHA | message |
|---|---|---|
| 1 | `bf8cb6f33f724f2e68872d27b68df627afe14fd8` | `fix(se-02d-i02): close snapshot projection review blockers`（code + tests） |
| 2 | `3e9b8f016369758100fd5999388d815b097023ed` | `docs(se-02d-i02): record FIX-01 verification evidence` |
| 3 | `bcceedbb29af8c9c6c8340ba62894551bb78b68a` | `docs(se-02d-i02): record FIX-01 main drift observation` |
| 4 | 本 §8.11 记录 commit | `docs(se-02d-i02): record FIX-01 addendum commit sequence` |

- 权威 fix commit = #1 `bf8cb6f`（不随后续文档 commit 变化）。
- **New branch tip = 上述追加链的最后一个 commit（即承载本 §8.11 的 commit）**；
  字面值以 `git rev-parse se-02d-i02-current-snapshot-folding` /
  `git ls-remote origin refs/heads/se-02d-i02-current-snapshot-folding` 为准，
  并在 FIX-01 Final Report Section D 明确给出。
- §8.1 / §8.10 中出现的字面 tip 值均为其记录时点的观测值（写入时刻为真，后续文档 commit
  使其不再是 tip）；最终以本节定义为准。dev_log 无法自指承载自身的 commit SHA，
  因此 tip 以「追加链末端」定义而非字面自指。

## 9. Final Acceptance Record — `SE-02D-I02-FINAL`（2026-09-15）

Latest-Main Acceptance Reconciliation / Human Acceptance Closeout。
**本记录仅追加验收事实，不改写以上任何历史 Worker 状态。**

| 项 | 值 |
|---|---|
| SE-02D-I02 Initial Independent Review | `FAIL — FIX REQUIRED` |
| SE-02D-I02-FIX-01 Independent Re-Review | `PASS` |
| `SE02D-I02-R1` / P1 | `CLOSED` |
| `SE02D-I02-R2` / P1 | `CLOSED` |
| `SE02D-I02-R3` / P2 | `CLOSED` |
| Human Acceptance | `CONFIRMED — 2026-09-15` |
| Human-Accepted Reviewed Candidate | `9b860437b14f64192d3298d30c0204bed1b118f8` |

- Human-Accepted reviewed candidate branch = `se-02d-i02-current-snapshot-folding`，
  **immutable**：永久 pin 于 `9b860437b14f64192d3298d30c0204bed1b118f8`（未追加 closeout
  commit、未 rebase、未被 merge `main`、未 force push）。
- Original I02 Base = `0ae5b0b44e28db4c8c81c1a64057467d199954cb`；
  Latest Accepted Main before reconciliation = `664207a9caba0c3f5c2589cfca2a10af24f89108`。
- 集成方法 = `FAST-FORWARD ONLY`；本轮的搬运为 **content-level carry-forward**
  （对 production source / tests 保持 byte-identical blob），
  **非**重新实现、**非** re-design、**非** cherry-pick 重建、**非** divergent history merge。
- 完整 closeout 证据（drift 正交性、blob identity、最终回归、状态同步、远端真值）见
  `dev_log/2026-09-15-se-02d-i02-final-acceptance-reconciliation.md`。
- 边界：`SE-02D-I02 = ACCEPTED / COMPLETE` **≠** `SE-02D` complete ——
  `SE-02D Production Implementation = IN PROGRESS`；`Gate C = NOT PASSED`；
  `Live = NOT AUTHORIZED`。未启动 I03。
