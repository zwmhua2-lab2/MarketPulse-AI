# 2026-09-15 — SE-02D-I01｜Deterministic Aggregation Core

## Task / Status

实现 Human-Accepted `SE-02D-D01` V1 contract 所要求的**纯确定性计算内核**：
`marketpulse.edge.aggregation`。

```text
SE-02D-I01 = READY FOR INDEPENDENT REVIEW
Human Acceptance = NOT GRANTED
```

Worker 不宣称 ACCEPTED。本批次只交付可被 Independent Review 独立验证的实现候选。

## Requirement / Scope

In Scope（仅下列文件）：

- `backend/src/marketpulse/edge/aggregation.py`（新增）；
- `backend/tests/test_se_02d_aggregation.py`（新增）；
- `backend/src/marketpulse/edge/__init__.py`（可选，仅包导出/文档字符串）；
- `dev_log/2026-09-15-se-02d-i01-aggregation-core.md`（本文件）。

模块必须 self-own：Canonical Scope Inputs → Population Coverage → Measurement
Compatibility → Expectancy / Descriptive Statistics → Overlap Clustering →
Deterministic Cluster Bootstrap → Evidence Sufficiency → Leave-One-Cluster-Out
Stability → Tail Evidence → Manifest Diagnostics → Deterministic Fingerprint
Primitive。

## Out of Scope（明确不做）

- PostgreSQL 加载、revision-chain discovery、canonical head selection、
  REPEATABLE READ snapshot orchestration、aggregate 持久化、scheduler / runtime host；
- 任何 ORM / session / migration / API / UI / worker / scheduler import；
- NumPy / SciPy / pandas 及任何新 production dependency；
- KEEP / DOWNWEIGHT / KILL、任何 economic threshold、strategy / risk / execution /
  Gate C / Live 动作；
- 既有 Accepted 代码、DB、migration head、frontend、runtime configuration、
  `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` / `PRODUCT_REQUIREMENTS.md` / `main`。

I01 **不 fold revision chain**。它消费已 canonicalize 的 scope facts，只证明
"given those facts, the aggregate is a deterministic function of them"。

## Accepted Design Pointer

- `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`
  @ Human-Accepted D01（`f887981` 树上）；
- 收口链：`9e0553f5 → f887981`（单 parent、FF、docs/state-only 恰 7 文件）；
  candidate `245b068` **不是** new main 的 ancestor（内容级 carry-forward）。

## Repository Truth（实测，不引用任务书静态 SHA）

| 项 | 实测值 |
| --- | --- |
| I01 branch | `se-02d-i01-aggregation-core` |
| Task Base / expected navigation SHA | `f887981d18fd7fc696d99cde702d0fec3e72a16c` |
| 本地 `main` | `f887981d18fd7fc696d99cde702d0fec3e72a16c` |
| `origin/main` | `f887981d18fd7fc696d99cde702d0fec3e72a16c` |
| live remote main（`git ls-remote`） | `f887981d18fd7fc696d99cde702d0fec3e72a16c` |
| `BASELINE MISMATCH` | **NO** |
| I01 candidate commit | `0c8c095df5b6dd9a168da399fe2e6fec3a3d3e54` |

补充事实：

- 事前确认 `se-02d-i01*` 分支不存在 ⇒ 本批次为真正新分支，无重放风险；
- 会话 cwd `E:\Documents\MarketPulse AI` 检出的是一条无关的脏历史分支
  （`prb-01-product-requirements-baseline`），**未**作为 SE truth 使用；
  SE 事实一律从已验证为 `f887981` 的 worktree 读取；
- I01 worktree `E:\Documents\MarketPulse-AI-se-02d-i01` 在实现前 clean。

## Human Design Clarification（2026-09-15，必须留档）

Accepted D01 §10.1 item 6 把 `uncertainty_method_version` 列为 bootstrap seed 的组成
成分，并要求 I01 将其作为常量暴露，但**从未冻结其字面量**。全仓库搜索
（spec、`DECISIONS.md`、`dev_log`、R01 evidence pack、`C:\Users\hua\.workbuddy\traces\*`）
均无该字面量的任何冻结值。

按任务 §30（发现需变更 Design 才能继续时停止并汇报）已 STOP / REPORT。用户随后给出
explicit Human Design Clarification：

```text
UNCERTAINTY_METHOD_VERSION = "se02d-overlap-cluster-percentile-bootstrap-v1"
```

该字面量表示 Accepted D01 已接受的 deterministic overlap-cluster percentile
bootstrap V1 方法。**本次 clarification 仅补齐缺失的 version identifier，不改变任何
已接受统计语义**；不影响 D01 任何其他 literal、算法、precedence 或判据。

据此澄清继续 I01，且**未**修改 Accepted Design、`DECISIONS.md`、`PROJECT_STATE.md`、
`AI_CONTEXT.md`，**未**借此扩大 Scope。正式状态同步留待后续 Acceptance Closeout。

## Implementation Summary

`aggregation.py`（1549 行）结构：

1. **Frozen literals**：`AGGREGATION_CONTRACT_VERSION`
   （D01 §16 literal）、`UNCERTAINTY_METHOD_VERSION`（上述 Human clarification）、
   `RNG_ALGORITHM_VERSION`（D01 §10.1 item 7 literal）、`VISIBILITY_MODE`（D01 §5.1/§9.1
   literal）、`BOOTSTRAP_REPLICATES=10_000`、`BOOTSTRAP_LOWER_INDEX=249`、
   `BOOTSTRAP_UPPER_INDEX=9749`、`CONFIDENCE_LEVEL="TWO_SIDED_95"`、
   `MIN_CLUSTERS_FOR_INTERVAL=2`、`MIN_CLUSTERS_FOR_SUFFICIENCY=3`、
   `REQUIRED_COVERAGE_RATE=1.0`、`WORST_DECILE_DENOMINATOR=10`、
   `DEPENDENCE_LIMITATIONS`、`REGIME_GATE="NONE_IN_SE02D_V1"`、
   `REGIME_SUFFICIENCY="NOT_EVALUABLE"`、
   `INTEGRITY_STATEMENT="Positive Expectancy != Evidence Completeness Proven."`、
   `UNOBSERVABLE_COVERAGE_LIMITATIONS`、`NO_MEASUREMENT`。
2. **Frozen enums**：`AggregateStatus`、`MaturityClass`、
   `MeasurementSignatureState`、`Calculability`、`IntervalSide`、
   `UncertaintyUnavailableReason`、`SufficiencyReason`。
3. **Errors**：`AggregationError`（基类）、`DuplicateSampleIdentityError`、
   `ForeignScopeFactError`。
4. **Immutable dataclasses**：`PopulationKey`、`MeasurementSignature`、
   `AggregateIdentity`、`CanonicalScopeFacts`、`OverlapCluster`、`BootstrapInterval`、
   `EconomicStatistics`、`TailEvidence`、`CoverageReport`、`ManifestDiagnostics`、
   `LocoResult`、`AggregationResult`（含 `to_dict()`）。
5. **Entry point**：`aggregate(facts, *, identity, as_of)`，fail-closed precedence
   → `evidence_sufficient = (no sufficiency reasons)`。
6. **Reuse**：`marketpulse.edge.hashing.canonical_bytes`（G5 canonicalization + hashing
   boundary）、`marketpulse.edge.models`（`EdgeFamily`、`EvidenceSource`、
   `ForwardHorizon`、`OpportunityLifecycleAtHorizon`、`OutcomeCalculationStatus`、
   `ReferenceDataStatus`）、`marketpulse.edge.forward.ForwardOutcomeReason`、
   `marketpulse.market_data.models.MarketType`。

`__init__.py`：新增 `aggregation` 模块条目；把 "Still absent by design (SE-02D): expectancy,
family aggregation and KEEP/DOWNWEIGHT/KILL" 更正为
"Still absent by design: the durable SE-02D revision-folding snapshot layer, and
KEEP/DOWNWEIGHT/KILL"（I01 已实现 expectancy 与 family aggregation，仅 revision-folding
snapshot layer 与 K/D/K 仍属未实现/未授权）。

## Deterministic Contracts（逐条对应 D01 / 任务判据）

| 契约 | 实现 |
| --- | --- |
| Population Key | `(family_id, family_version, instrument_id, market_type, source_type, source_identity, evidence_contract_version)`；`source_manifest_id` **不入 key**（provenance/stratification） |
| Population Aggregate Identity | `(Population Key, horizon)` |
| Measurement Signature | `(outcome_contract_version, calculator_version, cost_policy, cost_model_version, outcome_source_type, outcome_source_identity)`；只防 COMPLETE 跨语义混算，不拥有 coverage membership |
| Sample identity | `(population_key, horizon, opportunity_id)`，重复 ⇒ `DuplicateSampleIdentityError`（不保留首/末、不静默去重） |
| Foreign scope | 不属于请求 identity 的 fact ⇒ `ForeignScopeFactError`；horizon 严格分离，四 horizon 不混池 |
| Maturity | `NOT_YET_DUE` / `MISSING_OUTCOME` / `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID` |
| Coverage denominator | `complete + insufficient_data + invalid + missing_outcome`；`coverage_rate = complete / mature_denominator`，denominator=0 ⇒ NULL |
| Mixed signatures | `INCOMPATIBLE_MEASUREMENT_SIGNATURES`，coverage 全保留，headline economic statistics = NULL |
| Integrity fail-closed | COMPLETE 且 return 为 None/NaN/±Inf ⇒ `INTEGRITY_CONFLICT`；precedence 高于 mixed / NOT_APPLICABLE / NOT_CALCULABLE / VALID |
| Market-type boundary | SWAP ⇒ `NOT_APPLICABLE`（coverage 保留）；SPOT long economically applicable |
| Expectancy | `math.fsum(x_i) / n`，输入按确定性顺序（lexical ascending）排序 |
| Descriptive set | mean / median / positive / flat / negative counts / sample stddev(n−1，n<2 ⇒ NULL) / worst_observation / worst_decile_mean |
| Tail | `k = max(1, ceil(0.10*n))`，**无 threshold**；`worst_decile_mean` = k 个最小值均值 |
| Clustering | `[evidence_at, due_at]` 区间，overlap **或 touch** 合并，传递闭包；sweep 顺序 `(evidence_at, opportunity_id)`；cluster end = max(due_at) |
| Bootstrap | resample unit = 整个 cluster；10,000 replicates；`SHA256_COUNTER_REJECTION_V1` rejection sampling；`j = replicate_index * n_clusters + draw_index`；`k`（rejection attempt）0-based |
| RNG digest | `SHA256(seed ‖ uint64_be(j) ‖ uint32_be(k))`；`limit = 2^256 − (2^256 mod m)`，上界拒绝 |
| Replicate mean | **sample-weighted**（非 cluster-weighted），按确定性顺序累加 |
| Percentile | 精确 index `[249, 9749]` 取有序 replicate means |
| Interval NULL | `TOO_FEW_CLUSTERS`（n_clusters<2）/ `DEGENERATE_SAMPLE`（全同值，不当作高确定性） |
| Sufficiency | integrity==0 **AND** coverage_rate==1.0 **AND** n_clusters≥3 **AND** 非退化 **AND** interval 不含 0 **AND** LOCO 保持同侧 |
| LOCO | 逐 cluster 移除后重算，复用**未改变**的 frozen seed 派生（不发明第二套 seed） |
| Fingerprint | 复用 `canonical_bytes`，输入 manifest 绑定 `float.hex()` 表示 |
| 输出边界 | **无** K/D/K、无 threshold、无 strategy/risk/execution/Gate C 动作（evidence only） |

确定性说明：

- 所有派生序列在使用前排序 ⇒ `facts` 输入顺序不可影响任何输出（permutation invariance）；
- `ceil(0.10*n)` 实现为精确整数形式 `-(-n // 10)`；`math.ceil(0.10*n)` 是浮点表达式，
  其自身结果可能与数学定义漂移。两者在本模块可达样本量上可证明一致，测试中与浮点形式
  逐值对照断言；
- `j` 与 `k` 均为 0-based，与 `j = replicate_index * n_clusters + draw_index` 的 0-based
  构造一致；
- manifest 记录 canonical Measurement Signature，或 `NO_MEASUREMENT` marker；零填充冻结
  封闭词表（`REFERENCE_STATUS_KEYS {OK, REFERENCE_MISSING, REFERENCE_STALE}`、
  `LIFECYCLE_KEYS {ACTIVE, EXPIRED, NULL}`，D01 §8.1）。

## Files Changed

```text
backend/src/marketpulse/edge/aggregation.py      | 1549 +++++++++++++++++
backend/tests/test_se_02d_aggregation.py         | 1262 +++++++++++++
backend/src/marketpulse/edge/__init__.py         |    6 +-
3 files changed, 2815 insertions(+), 2 deletions(-)
```

Commit：`0c8c095df5b6dd9a168da399fe2e6fec3a3d3e54`
(`feat(se-02d-i01): add deterministic aggregation core`)

## Tests Executed

`backend/tests/test_se_02d_aggregation.py`：83 个 test function，**94 个 collected test**
（部分参数化）。覆盖任务 §32 全部条目：

- identity / key / signature 字段集与顺序、key 相等与分离、manifest 不入 key；
- horizon 分离（含跨 horizon 不混池）；
- duplicate sample identity fail-closed（且证明非静默去重）；
- foreign scope fail-closed；`NO_OUTCOME` marker 不得携带 Outcome 字段；
- maturity 分类矩阵；`NOT_YET_DUE` 不入 mature denominator；每种 mature status 恰好计数一次；
- 零 denominator ⇒ NULL coverage_rate；coverage diagnostics 全量上报；未知 reason 保留不改写；
- 单 signature 可算；mixed ⇒ fail closed 且 coverage 不丢；zero COMPLETE ⇒ NOT_CALCULABLE；
- integrity conflict fail-closed，并分别压过 incompatible / NOT_APPLICABLE；
- SWAP ⇒ NOT_APPLICABLE 且保留 coverage；
- expectancy = fsum / n；descriptive 值、奇偶中位数、n−1 stddev、n<2 为 NULL、无 trend/portfolio 统计；
- worst_decile_k 与浮点公式逐值一致 + 已知值；worst_observation / worst_decile_mean；
- tail 无 threshold；
- 非重叠 / touch / 相邻但不相交 / 传递重叠 四类聚类；cluster 顺序确定且输入无关；
  sweep 用 `(evidence_at, opportunity_id)`；cluster end = max(due_at)；
- RNG golden vector、独立手写 rejection sampling 对照、首轮 digest pin、`j`/`k` 0-based 连续；
- seed golden；fingerprint 变化 ⇒ seed 变化；
- replicate mean 为 sample-weighted（非 cluster-weighted）；bootstrap 可复现；
- percentile index 与冻结 quantile 规则一致，且精确取有序 replicate means；
- n_clusters<2 ⇒ NULL；全同值 ⇒ degenerate；2 clusters 有区间但 insufficient；
  正向/负向 resolved 案例 sufficient；coverage<1 / 跨 0 / LOCO 翻转 三类 insufficient；
- LOCO 逐 cluster 重算、确定性；
- 输入 permutation invariance（含 integrity conflict 场景）、重复调用 byte-identical、
  sample 排序 lexical ascending；
- fingerprint 可复现 / manifest 敏感 / 绑定 return bits / 拒绝非有限 canonical 数据；
- caller manifest 逐字使用、manifest 记录 `float.hex()` 表示与 `NO_MEASUREMENT` marker；
- version 常量与 Accepted literal 一致；limitations / integrity statement / 无 regime gate；
  result 上报冻结版本常量；**无 K/D/K 输出**；
- AST 层 AC-02：模块无 direct database / runtime import。

## Exact Test Results

```text
PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_se_02d_aggregation.py -q
94 passed in 4.92s
```

## Regression

```text
PYTHONPATH=backend/src py -3.14 -m pytest \
  backend/tests/test_se_02a_edge_contracts.py \
  backend/tests/test_se_02c_forward_outcome_calculator.py -q
99 passed in 0.63s
```

（两条 pure / 无 DB 的相邻批次回归；DB-backed 的 `test_se_02a_edge_persistence.py` /
`test_se_02c_forward_outcome_service.py` 与本纯模块无依赖交集，未纳入本次回归。）

Ruff 门禁：

```text
py -3.14 -m ruff check backend/src backend/tests scripts
All checks passed!
```

## Scope Verification

- changed paths = 3，全部在允许清单内；unexpected / forbidden path = 0；
- `backend/tests/` 未新增 conftest / `__init__` / 跨模块 import；
- 无 DB / alembic / repository / forward_service / frontend / config / scripts / state-doc 变更；
- migration head 未变；
- 无新 production dependency（无 NumPy / SciPy / pandas）；
- 无 KEEP / DOWNWEIGHT / KILL、无 threshold、无 Gate C / Live 动作；
- 未修改 `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` /
  `PRODUCT_REQUIREMENTS.md` / Accepted Design / `main`；
- `git diff --check` clean；未触碰原 session checkout 的既有 dirty entries。

## Verification Limitations（诚实标注）

- 本批次为**纯函数内核**，无 DB / runtime 集成路径 ⇒ 无真实数据库或运行时验证；
  该层属后续另开获批窗口（I01 明确不 own）。标记
  `NOT APPLICABLE — PURE MODULE, NO DB/RUNTIME INTEGRATION AUTHORIZED`；
- D01 §16 `aggregation_contract_version` 在 Accepted 文本中仅以 proposal 语句给出并被采纳，
  本实现按该 literal 落地；
- AC-02 的 import 断言只覆盖**直接** import。`canonical_bytes` 经 `g5.canonical` 传递性地
  import `sqlalchemy`；因此断言落在本模块 direct import 上，而非全依赖闭包。

## Remaining Work

- Independent Review 与 explicit Human Acceptance（Worker 不自行宣告 ACCEPTED）；
- 后续（未授权）层：PostgreSQL 加载 / revision-chain folding / canonical head selection /
  REPEATABLE READ snapshot orchestration / aggregate 持久化 / runtime host；
- 既有 carry-over：`SE-02D` implementation 其余部分、PRE-01B D1 Integrated Runtime Host
  Implementation、Gate C experiment identity、durable regime identity 均仍为未授权/未开始；
- `uncertainty_method_version` 的正式 Design 落字需在后续 Acceptance Closeout 中同步
  （本次仅按 Human Design Clarification 使用，未改 Design 文档）。

## Git

```text
branch  = se-02d-i01-aggregation-core
base    = f887981d18fd7fc696d99cde702d0fec3e72a16c
commit  = 0c8c095df5b6dd9a168da399fe2e6fec3a3d3e54
main    = f887981d18fd7fc696d99cde702d0fec3e72a16c（本地 = origin = live remote）
```

未 push、未 merge `main`、未创建 tag（等待 Independent Review）。
