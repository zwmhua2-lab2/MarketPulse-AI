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
