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

---

# SE-02D-I03-FIX-01｜Close Malformed Projection Identity Gap

```text
SE02D-I03-R1 = CLOSED BY FIX CANDIDATE
SE-02D-I03-FIX-01 = READY FOR INDEPENDENT RE-REVIEW
Human Acceptance = NOT GRANTED
SE-02D = IN PROGRESS（未完成，未宣称 complete）
```

## Review finding（本卡响应对象）

| 项 | 值 |
| --- | --- |
| Finding | `SE02D-I03-R1` |
| Severity | P1 |
| Status（修复前） | OPEN |
| Reviewed candidate（**不可变**，未被本卡移动） | `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4` |
| FIX branch | `se-02d-i03-fix-01-projection-identity-validation`（base `44d0e4b`） |
| FIX worktree | `E:\Documents\MarketPulse-AI-se-02d-i03-fix-01` |

问题：I03 承诺对每个必需身份字段做 projection 级 fail-closed 校验，但此前直接假设
`projection.horizon` / `fact.horizon` / `fact.population_key` 的运行时类型合法，并直接解引用
`.value` / `.canonical_payload()`。`CanonicalScopeFacts` 与 `CurrentSnapshotProjection`
自身均不做运行时类型校验，故畸形 / 篡改输入会以 `AttributeError` 之类偶发异常逃出
`AggregationOrchestrationError` 边界，违反冻结的 I03 任务 §9 rule 8 / §14。

## Root-cause evidence（修复前实测泄漏，非推断）

同一只读探针，以 I02 真实路径（`_project` / `_fold_*`）构造的 projection 为输入，分别加载
「已复审候选源码」与「FIX 源码」：

| 篡改点 | 修复前（`44d0e4b` 源码） | 修复后（FIX-01） |
| --- | --- | --- |
| `projection.horizon="5m"` | **LEAK** `AttributeError: 'str' object has no attribute 'value'` | `AggregationOrchestrationError: malformed_projection_identity:horizon:str` |
| `fact.horizon="5m"` | **LEAK** `AttributeError: 'str' object has no attribute 'value'` | `AggregationOrchestrationError: malformed_fact_logical_identity:horizon:str` |
| `fact.population_key="not-a-key"` | **LEAK** `AttributeError: 'str' object has no attribute 'canonical_payload'` | `AggregationOrchestrationError: malformed_fact_population_key:str` |

⇒ R1 为**可复现的真实缺口**（修复前该路径确实不被拦截），且新判据**确有牙齿**。

## Exact code fix（最小改动）

`backend/src/marketpulse/edge/aggregation_orchestration.py`：

1. 新增两个**非泛化**类型证明 helper：
   - `_require_forward_horizon(value, *, marker)` —— 非 `ForwardHorizon` 抛
     `AggregationOrchestrationError(f"{marker}:{type(value).__name__}")`；
   - `_require_population_key(value)` —— 非 `PopulationKey` 抛
     `malformed_fact_population_key:<type>`。
2. 在 `_index_facts` 内、**三处解引用之前**插入证明（该函数是 `aggregate_projection` 的首个
   调用，亦是首个解引用 `projection.horizon` 之处）：
   - 循环前：`_require_forward_horizon(projection.horizon, marker="malformed_projection_identity:horizon")`；
   - 每条 fact：`_require_forward_horizon(fact.horizon, marker="malformed_fact_logical_identity:horizon")`
     与 `_require_population_key(fact.population_key)`。
3. 模块 docstring 增补一条边界说明；`_index_facts` docstring 同步更新（原描述未提及新判据）。

放置位置在既有 `isinstance(fact, CanonicalScopeFacts)` 之后、`_require_text` 之前：既有
`malformed_fact:not_canonical_scope_facts` 的优先级不变，`test_non_canonical_scope_fact_fails_closed`
仍通过，未改变任何既有输入的报错路径。未引入通用校验框架；未改动 `_index_manifest`
（其 `projection.horizon.value` 由 `_index_facts` 的先行使证明覆盖）。I01/I02 源码与其测试
**逐字节未改**。

## New tests（§4 A–E）

`backend/tests/test_se_02d_aggregation_orchestration.py` 新增 7 个测试 / 18 个用例：

| § | 测试 | 断言 |
| --- | --- | --- |
| A | `test_malformed_projection_horizon_fails_closed`（`"5m"` / `"M5"` / `None` / `5` / `[]`） | `malformed_projection_identity:horizon` |
| A | `test_malformed_projection_horizon_fails_closed_without_any_fact` | 空 facts 时 projection 级证明仍生效 |
| B | `test_malformed_fact_horizon_fails_closed`（5 参数） | `malformed_fact_logical_identity:horizon` |
| C | `test_malformed_fact_population_key_fails_closed`（str / `None` / int / tuple） | `malformed_fact_population_key` |
| — | `test_malformed_projection_identity_messages_are_exact_and_deterministic` | 三条消息**逐字符**全等 |
| D | `test_malformed_projection_identity_never_reaches_i01` | 三种畸形输入均抛 `AggregationOrchestrationError`，且 I01 `aggregate` 调用数为 **0** |
| E | `test_valid_projection_behavior_is_unchanged_by_the_fix` | 3 population / 3 次调用 / 规模 1·2·3 / `canonical_key` 有序 / `horizon` 保真 / 空 projection 仍返回 `()` |

全部经 `dataclasses.replace` 作用于 I02 真实路径产出的 projection / fact，未手工伪造 I02 输出。
未削弱任何既有 I01／I02／I03 测试。

## Verification

| 验证 | 命令 | 结果 |
| --- | --- | --- |
| I03 定向 | `py -3.14 -m pytest -q backend/tests/test_se_02d_aggregation_orchestration.py` | **57 passed**（39 既有 + 18 新增） |
| I01+I02+I03 定向回归 | 三文件同批 | **209 passed in 16.13s**（108 + 44 + 57） |
| 变更文件 ruff | 两个变更文件 | All checks passed! |
| 项目 ruff 门 | `backend/src backend/tests scripts` | All checks passed! |
| 空白检查 | `git diff --check` | PASS（exit 0，无输出） |
| 修复前/后取证 | 只读探针 × 2 | 见 Root-cause evidence 表 |
| 全量 backend suite | — | 未跑（任务 §5 明确 NOT REQUIRED；定向回归未暴露跨边界问题） |

## Evidence

| 证据 | 值 |
| --- | --- |
| Reviewed candidate（不可变，未移动） | `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4` |
| FIX branch base | `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4`（单父、forward） |
| `origin/main`（实测未动） | `44df66603e6bdba1f3f80c21be5b30c295e4a20a` |
| FIX commit（源码 + 测试） | `1631f251eda0bcc1d0f74cd8e073ee176643f158`（2 文件 / +161 −3） |
| 变更面 | 严格 2 个既有文件 + 本 dev_log；无新增文件、无删除 |

## Remaining / Deviations

- `SE02D-I03-R1 = CLOSED BY FIX CANDIDATE`；R2 / R3 未被本卡授权处理，保持原状。
- 未 merge `main`；未 force push；未 rebase；**未移动**原候选分支
  `se-02d-i03-population-aggregate-orchestration`；未启动 I04；未宣称 Human Acceptance；
  未宣称 ACCEPTED；未宣称 SE-02D complete。
- 前文 `Remaining Boundaries` 记录的 `edge/__init__.py` 包文档陈旧问题**依旧未修**
  （不在本卡允许写入面内，CIP-05 记录不修）。
- 无阻塞项；无 Scope 偏差。

---

# SE-02D-I03-FINAL｜Human Acceptance + Final Acceptance Record

> 本节为**追加**记录（2026-09-16 closeout 窗口）。既有 worker / review 历史条目**逐字未改**。

```text
SE-02D-I03 Initial Independent Review = FAIL — FIX REQUIRED
SE02D-I03-R1 / P1 = CLOSED
SE-02D-I03-FIX-01 Independent Re-Review = PASS — READY FOR HUMAN ACCEPTANCE
Human Acceptance = CONFIRMED — 2026-09-16
SE-02D-I03 = ACCEPTED / COMPLETE
SE-02D = IN PROGRESS（未完成，未宣称 complete）
```

| 项 | 值 |
| --- | --- |
| Human-Accepted Reviewed HEAD | `20a7c333abf81077c409811302331119dff485a5` |
| Original Reviewed Candidate | `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4` |
| 原候选 branch（immutable） | `se-02d-i03-population-aggregate-orchestration` |
| FIX branch（immutable） | `se-02d-i03-fix-01-projection-identity-validation` |
| Closeout branch | `se-02d-i03-final-acceptance-closeout`（base = FIX HEAD） |
| 集成方法 | `FAST-FORWARD ONLY`（无 merge / squash / rebase / cherry-pick / force push） |

## Final Accepted Implementation Scope

```text
CurrentSnapshotProjection
    -> strict facts <-> revision-aware manifest integrity gate（fail closed）
    -> complete structural PopulationKey grouping
    -> exactly one I01 aggregate() invocation per population
    -> deterministic ordered tuple[AggregationResult, ...]
```

（第二行 `facts` 与 `manifest` 之间原文为双向箭头；此处以 `<->` 记录以免歧义。）

## Final Regression（closeout 窗口实测）

cwd = Human-Accepted FIX lineage worktree（HEAD = `20a7c333…`）；未导出 `DATABASE_URL`；
DB-backed I02 用例在既有 disposable 路径下通过，未触碰 accepted / shared 应用库。

| 验证 | 命令 | 结果 |
| --- | --- | --- |
| I03 定向 | `pytest -q backend/tests/test_se_02d_aggregation_orchestration.py` | **57 passed** |
| I01 | `pytest -q backend/tests/test_se_02d_aggregation.py` | **108 passed** |
| I02 | `pytest -q backend/tests/test_se_02d_aggregation_snapshot.py` | **44 passed** |
| I01+I02+I03 合并 | 三文件同批 | **209 passed** |
| 项目 ruff 门 | `ruff check backend/src backend/tests scripts` | `All checks passed!` |
| 空白检查 | `git diff --check` | rc = 0 |
| 全量 backend suite | — | **NOT REQUIRED FOR THIS CLOSEOUT / NOT VERIFIED** |

## Closeout Scope Verification

- `Production Code Changed After Human Review = NO`
- `Tests Changed After Human Review = NO`
- `Schema Changed = NO` / `Migration Added = NO`
- `Production Dependency Changed = NO` / `Runtime Behavior Changed By Closeout = NO`
- `20a7c333…` → closeout HEAD 的 diff **仅**含：本批 dev_log 追加、新增 closeout dev_log、
  `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md`（无其它 tracked 文件）。

## Boundaries

`SE-02D = IN PROGRESS`；aggregate / API / product integration 仍 `NOT IMPLEMENTED`；
historical revision-as-of 仍 `OPEN`；`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；
Real AI 未由本验收获得任何新授权。本收尾**不**定义也不启动 I04。
