# 2026-09-16 — SE-02D-I03｜Population Grouping + Aggregate Orchestration

## Task / Status

在 Human-Accepted 的 SE-02D-I03 Scope 内，实现 I02（current stable-snapshot
revision folding）与 I01（纯确定性 family aggregation core）之间**最小完整编排单元**：
`marketpulse.edge.aggregation_orchestration`。

```text
SE-02D-I03 = READY FOR INDEPENDENT REVIEW
Human Acceptance = NOT GRANTED
SE-02D = IN PROGRESS（未完成，未宣称 complete）
```

Executor 不宣称 ACCEPTED，不宣称 SE-02D 完成，不 merge `main`，不启动 I04。

## Requirement / Scope

In Scope（仅下列三个新文件）：

- `backend/src/marketpulse/edge/aggregation_orchestration.py`（新增，343 行）；
- `backend/tests/test_se_02d_aggregation_orchestration.py`（新增，841 行）；
- `dev_log/2026-09-16-se-02d-i03-population-aggregate-orchestration.md`（本文件）。

实现目标只有一个：

```text
CurrentSnapshotProjection
    -> facts ↔ manifest 完整性校验
    -> 按完整 PopulationKey 分组
    -> 每个 population 恰好一次 I01 aggregate()
    -> 确定性有序 tuple[AggregationResult, ...]
```

## Explicitly Out of Scope（本批次未做）

- I01／I02 实现与其既有测试的任何修改（**实测未改**）；
- API endpoint、frontend、aggregate 持久化 / 表 / migration / schema change；
- scheduler、background worker、runtime host integration、Real AI activation；
- Gate C、Live Trading、KEEP / DOWNWEIGHT / KILL；
- 任何新统计、新阈值、新 fingerprint 算法、新 Measurement Signature、新 Population
  Key、新 horizon 语义、`experiment_id` / `pair_id` / `arm_id` / regime gating /
  historical revision-as-of；
- `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` / `PRODUCT_REQUIREMENTS.md`
  与 `main`（实现期不做任何 state-document acceptance 更新）；
- `.workbuddy` 清理、agent memory / skill mutation、无关文件系统清理。

## Repository Truth（实测，不引用任务书静态 SHA）

| 项 | 实测值 |
| --- | --- |
| Global Protocol `Version` | `1.1.0` |
| Global Protocol `Status` | `ACCEPTED` |
| Protocol `main` = `protocol-v1.1.0` tag | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| Task Base / expected main | `44df66603e6bdba1f3f80c21be5b30c295e4a20a` |
| 本地 `refs/heads/main` | `44df66603e6bdba1f3f80c21be5b30c295e4a20a` |
| `origin/main`（`git ls-remote`） | `44df66603e6bdba1f3f80c21be5b30c295e4a20a` |
| `BASELINE MISMATCH` | **NO** |
| I03 branch | `se-02d-i03-population-aggregate-orchestration` |
| I03 worktree | `E:\Documents\MarketPulse-AI-se-02d-i03` |
| worktree HEAD（实现前 / 实现中） | `44df66603e6bdba1f3f80c21be5b30c295e4a20a` |

补充事实：

- 事前 `git ls-remote origin "refs/heads/se-02d-i03*"` 返回空、本地
  `.git/refs/heads/se-02d-i03-...` 不存在 ⇒ 本批次为真正新分支，无 replay 风险；
- 会话 cwd `E:\Documents\MarketPulse AI` 检出的是一条无关脏历史分支
  （`prb-01-product-requirements-baseline`，HEAD `d47313a`），**未**作为 SE truth
  使用；SE 事实一律从 worktree `E:\Documents\MarketPulse-AI-se-02d-i03` 读取；
- 该 worktree 由 Write 直写 ref（`44df666`）+ `git worktree add` 建立，实现前
  `git status --porcelain` 为空；
- `E:\Documents\ai-dev-protocol\.git` 为残缺目录（仅 `hooks/info/objects/refs`，
  无 `HEAD`/`config`），无法锚定 ⇒ Protocol 版本以远端 `git ls-remote` +
  GitHub contents API 单独核实，未修该目录。

## Reuse Decisions（避免重复实现）

| 需求 | 复用 | 未做 |
| --- | --- | --- |
| population 身份 | I01 `PopulationKey`（结构相等/哈希） | 未新建 key 类型 |
| 聚合统计 / 成熟度 / 覆盖 / bootstrap / LOCO / 充分性 | I01 `aggregate()` | 未重算任何统计 |
| 快照 / as_of / revision folding | I02 `CurrentSnapshotRevisionReader.read()` | 未新建 session / 快照 / 折叠 |
| manifest 扩展字段语义 | I02 产出的 revision-aware manifest 原样透传 | 未 strip、未重建 |
| 规范化边界 | 仅通过 `PopulationKey.canonical_key()` 复用 G5 `canonical_bytes` 做**排序** | 未新增序列化器、未用 digest 作身份判据 |

## Implementation Summary

`aggregation_orchestration.py` 结构：

1. **`AggregationOrchestrationError(ValueError)`** — 唯一新增异常类型，仅承载
   projection 级 facts ↔ manifest / grouping 完整性失败。刻意做
   `AggregationError` 的**兄弟**而非子类：`issubclass(AggregationOrchestrationError,
   AggregationError)` 为 `False`，因此 I03 既不捕获、也不重包裹 I01
   `AggregationError`，也不吞 I02 `SnapshotIntegrityError`。消息首段为不变量名、
   随后为肇事 logical identity；集合型肇事者（missing / extra / duplicate）一律报**最小
   成员**，故消息与输入迭代顺序无关。
2. **facts ↔ manifest 完整性门**（任务 §9 九条判据）：
   `_index_facts` / `_index_manifest` / `_require_one_to_one_mapping` /
   `_require_declared_population_key`。
3. **分组**：`_ordered_population_groups` — 以 `PopulationKey` 结构相等/哈希分桶，
   按 `canonical_key()` 排序。
4. **manifest 子集**：`_manifest_subset` — 逐条原样透传（`no_outcome` /
   `evidence_revision_identities` / `outcome_revision_identities` / 全部 I01 base
   manifest 字段保留），按 `(opportunity_id, evidence_id, horizon)` 确定性排序。
5. **公开面**：`aggregate_projection(projection)`（纯函数）与
   `aggregate_current_snapshot(reader, horizon)`（薄 async wrapper，仅
   `projection = await reader.read(horizon)` + `return aggregate_projection(projection)`）。

## Files Changed

```text
A  backend/src/marketpulse/edge/aggregation_orchestration.py   (+343)
A  backend/tests/test_se_02d_aggregation_orchestration.py      (+841)
2 files changed, 1184 insertions(+)
```

I01（`aggregation.py`）与 I02（`aggregation_snapshot.py`）及其既有测试
**逐字节未改**（`git status --porcelain` 仅显示上述两个 `??` → `A`）。

## Public API Added

```python
AggregationOrchestrationError(ValueError)
LogicalIdentity = tuple[str, str, str]          # (opportunity_id, evidence_id, horizon)

def aggregate_projection(projection: CurrentSnapshotProjection) -> tuple[AggregationResult, ...]
async def aggregate_current_snapshot(reader: CurrentSnapshotRevisionReader,
                                     horizon: ForwardHorizon) -> tuple[AggregationResult, ...]
```

## Facts ↔ Manifest Integrity Behavior（fail closed）

按任务 §9 逐条实现，全部 fail closed，绝不静默丢弃 / 去重 / 伪造 / 回退
`build_ordered_input_manifest()` / 从 facts 反推 revision-aware manifest：

| # | 判据 | 实现点 | 错误标记 |
| --- | --- | --- | --- |
| 1 | fact 无 manifest entry | `_require_one_to_one_mapping` | `fact_without_manifest_entry:<oid>:<eid>:<hz>` |
| 2 | manifest entry 无 fact | `_require_one_to_one_mapping` | `manifest_entry_without_fact:...` |
| 3 | fact logical identity 重复 | `_index_facts` | `duplicate_fact_logical_identity:...` |
| 4 | manifest logical identity 重复 | `_index_manifest` | `duplicate_manifest_logical_identity:...` |
| 5 | `fact.horizon != projection.horizon` | `_index_facts` | `fact_horizon_mismatch:...` |
| 6 | manifest horizon ≠ `projection.horizon.value` | `_index_manifest` | `manifest_horizon_mismatch:...` |
| 7 | manifest Population Key ≠ `fact.population_key.canonical_payload()` | `_require_declared_population_key` | `manifest_population_key_mismatch:...` |
| 8 | 身份字段缺失 / 畸形 | `_require_text`（facts + manifest） | `malformed_fact_logical_identity:<field>:<type>` / `malformed_manifest_logical_identity:<field>:<type>` |

补充：非 `CanonicalScopeFacts` 的 fact → `malformed_fact:not_canonical_scope_facts:<type>`；
非 Mapping 的 manifest entry → `malformed_manifest_entry:not_a_mapping:<type>`；
manifest `population_key` 非 Mapping → `malformed_manifest_identity:population_key:...`。

## Population Grouping / Invocation Behavior

- 分组身份 = 完整结构 `PopulationKey`（7 个冻结字段），**不是** `source_manifest_id`
  、不是 Measurement Signature、不是 outcome/calculator/cost version、不是
  lifecycle/status/return，不是 instrument/family 单独；
- 每个 distinct `PopulationKey` **恰好一次** I01 `aggregate()` 调用；
- 输出 tuple 按 `PopulationKey.canonical_key()` 排序（排序用，非身份判据；未使用
  delimiter-joined 身份字符串）；
- `market_type` 属 PopulationKey，SWAP 等非适用 population **不被 I03 过滤**，
  原样送达 I01，由 I01 给出既有 `NOT_APPLICABLE`；
- 混用 Measurement Signature 的同一 PopulationKey 仍为**单次**调用，由 I01 给出既有
  `INCOMPATIBLE_MEASUREMENT_SIGNATURES`；
- 空 projection（`facts == ()` 且 `manifest == ()`）返回 `()`，且**零次**
  `aggregate()` 调用。

## Tests

`backend/tests/test_se_02d_aggregation_orchestration.py`，39 个测试，覆盖任务 §17
A–O 全部条目（含 boundary 增补）：

| 组 | 覆盖 |
| --- | --- |
| A | 空 projection → `()` 且 aggregate 零调用 |
| B | 单 population：恰好一次调用、identity / horizon / `as_of` 保真、revision-aware manifest 送达 I01 且**不等于** I01 自身 base manifest、子集按 logical identity 排序 |
| C | 多 population（3 组，事实数 3/2/1）：每组恰好一次调用、按 `canonical_key()` 有序 |
| D | 同 PopulationKey + 不同 `source_manifest_id` → 单 population / 单次调用 |
| E | 同 PopulationKey + 混合 Measurement Signature → 单次调用 + I01 `INCOMPATIBLE_MEASUREMENT_SIGNATURES` |
| F | SWAP population 未被过滤并抵达 I01（`NOT_APPLICABLE`）；SPOT/SWAP 保持分离 |
| G / H | fact 缺 manifest row / manifest row 缺 fact（含 facts 为空）→ fail closed |
| I / J | fact / manifest logical identity 重复 → fail closed，且报告确定 |
| K / L | fact horizon / manifest horizon 不匹配 → fail closed |
| M | manifest Population Key 不匹配 → fail closed；字段次序颠倒不算不匹配（结构比较，非 digest） |
| 增补 | 畸形身份字段（`None` / `""` / `int` / `list`）、缺字段、非 Mapping entry、非 Mapping `population_key`、非 `CanonicalScopeFacts` fact → 全部 fail closed |
| N | async wrapper：`reader.read(horizon)` **恰好一次**、传入的正是同一 projection 对象、端到端结果与纯编排器一致、I02 `SnapshotIntegrityError` 原样上抛 |
| O | facts + manifest 同时反转 → population 顺序、`input_fingerprint`、`to_dict()` 全等；population 规模保持 3/2/1 |
| 边界 | 公开面形状（纯函数 / coroutine、签名、`__all__`）、异常类型边界、I01 `AggregationError` 不被吞、编排模块 **零** DB import（AST 级证明） |

测试方法学披露：projection 一律由 I02 自身路径（`_project`, `_fold_evidence_chains`,
`_fold_outcome_chains`，与 I02 既有测试同一用法）用真实 Accepted 契约构造，以确保 I03
消费的是**真实 I02 输出**；任务 §9 的 fail-closed 场景则在该真实输出上**篡改**——因为
I02 按构造不可能产出不一致 projection，不存在别的合法触发途径。未削弱任何 I01／I02 测试。

## Verification

| 验证 | 命令 | 结果 |
| --- | --- | --- |
| I03 定向 | `py -3.14 -m pytest -q backend/tests/test_se_02d_aggregation_orchestration.py` | **39 passed** |
| I01 回归 | `... test_se_02d_aggregation.py` | **108 passed** |
| I02 回归 | `... test_se_02d_aggregation_snapshot.py` | **44 passed**（含 disposable PostgreSQL MVCC 快照用例） |
| I01+I02+I03 合并 | 三文件同批 | **191 passed in 16.44s** |
| 变更文件 ruff | `py -3.14 -m ruff check <2 new files>` | All checks passed! |
| 项目 ruff 门 | `py -3.14 -m ruff check backend/src backend/tests scripts` | All checks passed! |
| 空白检查 | `git diff --check` / `git diff --cached --check` | 均 clean（exit 0） |
| 变更面 | `git status --porcelain` | 仅 2 个新增文件；I01/I02 未改；未触碰 `main` |
| 全量 backend suite | — | **未跑**（任务 §18 明确 full suite NOT REQUIRED；定向回归未暴露跨边界问题，故按 §18 不做仪式性大套件） |

环境记录：cwd = I03 worktree；`py -3.14`（系统 Python 3.14.2，含 pytest / ruff）；
该 worktree 无 `.env`，I02 harness 走 `Settings` 默认
`127.0.0.1:5432/marketpulse` 并自建 / 自删 disposable 库；未导出 `DATABASE_URL`。

## Self Review

1. **是否重复实现 I01/I02 权威？** 否。I03 无统计、无覆盖、无成熟度、无 fingerprint
   算法、无 folding、无 session；全部转交。
2. **是否可能让 I01 回退到自建 manifest？** 否。`ordered_input_manifest` 恒为非
   `None`；测试 B 以「result.input_manifest != build_ordered_input_manifest(...)」做反向
   证明。
3. **身份编码是否规避了非单射字符串？** 是。分组用 dataclass 结构相等；字符串仅由
   `canonical_bytes(...).hex()` 产出且仅用于排序；无 `"|".join(...)` 式身份。
4. **多违规时的报告是否确定？** 集合型判据取最小成员；去重报告取 `min(duplicated)`；
   population-key 判据按 `sorted(fact_index)` 遍历。单条违规（测试构造的唯一形态）报告
   完全确定，且与输入顺序无关。
5. **失败面是否 fail closed 而非静默？** 是；无静默丢弃、去重、补齐、推断。
6. **最坏情况？** 若 I02 未来改变 manifest 字段命名（例如 `horizon` 键改名），I03 的
   完整性门会 fail closed 报 `malformed_manifest_logical_identity` —— 这是**期望**行为
   （而非静默错配）；契约变更须走 Proposal → Human approval 流程，不由 I03 自行适配。
7. **更简单方案？** 可省略显式空 projection 短路，直接由通用算法自然产出 `()`；实测二者
   等价（测试 A 覆盖），故保留更少代码的通用路径。
8. **是否越界修改？** 否。仅新增 3 个文件（2 个本提交 + 1 个本文件）。

## Remaining Boundaries

- `aggregate_projection` 不校验 manifest 子集条目的**业务**合法性
  （`evidence_revision_identities` 内容等）——那是 I02 的构造责任，I03 不做二次审判；
- I03 不检测"跨 projection"的一致性，也不提供 historical `as_of`；
- `__init__.py` 的包文档仍写着 "Still absent by design: the durable SE-02D
  revision-folding snapshot layer"（I02 落地后已陈旧），但该文件不在本批次允许写入面内，
  按 CIP-05 记录而不顺手修复，留待 Closeout / 后续授权批次同步；
- `SE-02D` 父状态仍为 IN PROGRESS；I04+（aggregate/API/product 集成、historical
  revision-as-of）未启动、未授权。

## Evidence

| 证据 | 值 |
| --- | --- |
| 实现提交（本 dev_log 记录对象） | `0bf139efe47791b49b17fed639203e531ad9054c` |
| 实现提交 parent | `44df66603e6bdba1f3f80c21be5b30c295e4a20a`（单 parent、forward） |
| 新增文件 blob 行数 | src 343 / tests 841 |
| I03 测试 | 39 passed |
| I01+I02+I03 定向回归 | 191 passed |
| ruff（变更文件 / 项目门） | PASS / PASS |
| `git diff --check` | PASS |
| 变更面 | 2 个新增文件，0 个既有文件被修改 |

## Blockers / Deviations

- **Blockers：无。** 未触发任何 STOP / REPORT 条件；基线一致，无 baseline drift。
- **Deviations：无 Scope 或契约偏差。** 两点按任务 §8/§9 的实现取舍已在上文 Self Review
  第 7 条与 Facts↔Manifest 表中披露：
  1. 空 projection 未做显式短路，由通用算法等价产出 `()`（任务 §8 的语义要求已满足）；
  2. 「facts 为空但 manifest 非空」按 §9 判据 2 fail closed（而非返回 `()`），与本卡
     §8 的措辞不冲突且被测试覆盖。

```text
SE-02D-I03 = READY FOR INDEPENDENT REVIEW
```

未 merge `main`；未启动 I04；未宣称 Human Acceptance；未宣称 SE-02D complete。
