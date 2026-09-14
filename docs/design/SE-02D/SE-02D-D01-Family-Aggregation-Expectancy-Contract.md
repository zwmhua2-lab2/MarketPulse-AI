# SE-02D-D01｜Family Aggregation / Expectancy Contract

> **STATUS: DESIGN CANDIDATE — NOT HUMAN ACCEPTED**
>
> Task: `SE-02D-D01`
> Task Type: `DESIGN / CONTRACT FREEZE CANDIDATE / DOCS ONLY`
> Implementation Authorization: **NO**
> Candidate Branch: `design/se-02d-d01-family-aggregation-expectancy`
> Verified Task Base: `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`

本文件是供 Independent Review 与 Human Acceptance 使用的候选契约。除明确标为
`FACT` 的当前仓库事实外，本文每一项选定的 V1 规则均标为
`PROPOSED — REQUIRES HUMAN ACCEPTANCE`；在 Human Acceptance 前，它们不是 Accepted
产品语义，也不授权任何实现、schema、Runtime、交易行为或 Gate C 判定。

---

## 1. Task / Requirement / Scope

### 1.1 Current Task

把 Human-Accepted `SE-02D-R01` 研究证据转化为一份内部一致、可实现、可独立复核的
Family Aggregation / Forward-Outcome Expectancy V1 候选契约。

### 1.2 Requirement

本候选必须确定：一个统计样本是什么、Evidence/Outcome revision 如何折叠、哪些维度能否
合并、Expectancy 与 coverage 如何计算、不确定性如何表示、`KEEP / DOWNWEIGHT / KILL`
的责任边界，以及 V1 是否持久化 aggregate。

### 1.3 In Scope

- canonical sample、revision folding、aggregate identity；
- Expectancy、coverage、uncertainty、minimum-sufficiency、tail-risk 的计算契约；
- primary horizon、regime、K/D/K、persistence 与 Gate C 边界；
- 实现前置 blocker 与 Human Decision Package。

### 1.4 Out of Scope

- 任何 Python / test / ORM / migration / API / frontend / runtime 实现；
- Scanner、Strategy Ranking、G3 Risk、Execution、Position、Ledger 或 Paper economics 变更；
- Real AI experiment identity、provider、Runtime Host、Live Trading 实现或激活；
- 修改 `PRODUCT_REQUIREMENTS.md`、既有 SE-02A/B/C 契约或 Accepted PRE-01A-D1；
- 接受本候选、通过 Gate C、合并 `main`。

### 1.5 Acceptance Boundary

本文只有在 Independent Review 后取得显式 Human Acceptance，才可成为 implementation
contract。即使本设计未来被接受：

```text
SE-02D capability complete != Gate C PASS
Gate C PASS != Live authorization
```

---

## 2. Repository Truth

### 2.1 Baseline

| Classification | Item | Verified value |
|---|---|---|
| `FACT` | design worktree HEAD | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| `FACT` | local `main` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| `FACT` | live remote `refs/heads/main` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| `FACT` | branch | `design/se-02d-d01-family-aggregation-expectancy` |
| `FACT` | isolated worktree | `E:\Documents\MarketPulse-AI-se-02d-d01` |
| `FACT` | source worktree before authoring | clean |
| `FACT` | original session checkout | unrelated dirty `prb-01-product-requirements-baseline`; preserved and not used as SE truth |

结论：`BASELINE MISMATCH = NO`。候选从实时核验的 Accepted `main` 建立。

### 2.2 Re-verified Current SE Facts

| Classification | Fact |
|---|---|
| `FACT` | 当前 V1 `EdgeFamily` 只有 `BREAKOUT_RETEST`。 |
| `FACT` | 当前运行时 `StrategyEngine.version = "g2-v1"`；Evidence 的 `family_version = candidate.strategy_version`。 |
| `FACT` | `ForwardHorizon = {30s, 5m, 15m, 1h}`；`due_at = evidence_at + horizon.duration_seconds`。 |
| `FACT` | logical Opportunity identity 由 `(family_id, family_version, instrument_id, candidate_id)` 确定，排除 Evidence revision / hash / calculator version。 |
| `FACT` | Evidence revision 是 immutable append-only chain；同 opportunity 的 `revision N > 1` 必须紧邻 supersede `N-1`。 |
| `FACT` | Outcome revision chain scope 是 `(opportunity_id, evidence_id, horizon)`；同 scope 的 `revision N > 1` 必须紧邻 supersede `N-1`。 |
| `FACT` | normal SE-02C evaluator 只写 revision 1；命中已有 revision 1 时直接返回，不重算、不自动写 revision 2。 |
| `FACT` | 显式 immutable correction path 仍允许 Evidence / Outcome revision 大于 1。 |
| `FACT` | terminal Outcome status 只有 `COMPLETE / INSUFFICIENT_DATA / INVALID`；`PENDING` 不落库。 |
| `FACT` | `COMPLETE` 可提供 `reference_return`、`executable_long_return`、`cost_adjusted_forward_return`、MFE、MAE。 |
| `FACT` | `source_type = HISTORICAL_REPLAY / FORWARD_PAPER`；Forward reference authority 是 durable Capture Anchor BBO，Historical Replay 使用 Evidence 冻结 reference。 |
| `FACT` | Evidence 持有 family/instrument/market/source facts；Outcome 不持有 family/version/instrument/market，聚合必须 join Evidence。 |
| `FACT` | 当前没有 SE-02D aggregation implementation、Accepted aggregate key、Accepted K/D/K threshold policy 或 durable Accepted regime identity。 |

### 2.3 R01 Evidence Treatment and Material Difference

`SE-02D-R01` 可读，作为 Evidence Input 使用；其 recommendation 不自动成为本候选决策。
Repository Truth 与 R01 的基础模型没有冲突，但独立复核发现一项必须收紧的差异：

| ID | Classification | Finding |
|---|---|---|
| `D01-F01` | `FACT / DESIGN BLOCKER` | `edge_opportunity_evidence.created_at` 没有 DB-assigned commit/visibility 语义或单调约束；Accepted tests 允许 Evidence rev1/rev2 使用同一回溯 `created_at`。`edge_forward_outcomes.created_at` 在 normal SE-02C 中被故意冻结为 `due_at`，也不是持久化可见时间。 |

因此，R01 的无条件“按 max revision 折叠”只适用于**一个当前稳定 MVCC snapshot 内的可见行**；
它不能从现有 durable fields 恢复“历史 `as_of` 时当时已存在的最高 revision”。本文不会把
`created_at`、`evidence_at` 或 `due_at` 冒充 revision availability time。

---

## 3. Contract Vocabulary

| Term | Exact V1 meaning |
|---|---|
| `logical opportunity` | 一个 `opportunity_id`；Evidence correction 不产生第二个 logical opportunity。 |
| `canonical evidence` | 在同一稳定读取 snapshot 内，对一个 logical opportunity 可见且通过 chain/integrity 校验的最高 Evidence revision。 |
| `canonical outcome` | 对 canonical evidence 的一个固定 horizon scope，在同一 snapshot 内可见且通过 chain/integrity 校验的最高 Outcome revision。 |
| `sample` | full aggregate key 下，一个 logical opportunity 在一个固定 horizon 的一次 observation；事实载体是 canonical Evidence + canonical Outcome。 |
| `mature` | canonical Evidence 的 `due_at <= as_of`。 |
| `calculable` | 至少存在一个完整、finite 的主 return，可计算描述性 Expectancy。 |
| `statistically resolved` | coverage、cluster-bootstrap interval 与 leave-one-cluster-out 稳定性满足 §10 的候选规则；不等于业务 materiality 或 K/D/K 决策。 |
| `Gate C eligible` | 还须具备 explicit experiment/pair/arm identity 与 Accepted Gate C policy；当前 SE-02D family aggregate 自身不具备。 |

本文中的 Expectancy 专指：

> fixed-horizon, fixed-cost-policy, counterfactual Forward Outcome Expectancy

它不是已执行交易 PnL expectancy，不含 Position、Fill、stop、R-Multiple 或 portfolio return。

---

## 4. Canonical Statistical Sample

### 4.1 Sample Identity

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

全局 sample identity 定义为：

```text
(aggregate_key, opportunity_id)
```

由于 `horizon` 已进入 aggregate key，同一 Opportunity 在每个 horizon 的结果是四个**分开的
repeated-measure views**，绝不进入同一个 aggregate，也绝不相加成为 `n = 4`。在单一
aggregate 内，一个 `opportunity_id` 最多贡献一个 return observation。

### 4.2 Deterministic Selection Algorithm

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

在一个 PostgreSQL `REPEATABLE READ / READ ONLY` snapshot 内，严格按下列顺序选择：

1. 读取与请求 aggregate key 相容的全部 Evidence revision；不得先按 Outcome status 过滤。
2. 按 `opportunity_id` 分组，验证 revision 从 1 连续、每个 `N>1` 紧邻 supersede `N-1`，并验证
   所有 revision 的 Opportunity identity facts 一致。失败则 aggregate `INTEGRITY_CONFLICT`，
   不输出 Expectancy。
3. 每个 `opportunity_id` 选择 snapshot 内可见的最高 `evidence_revision`；较低 revision 标记
   `FOLDED_EVIDENCE`，不得回退使用其更完整或更有利的 Outcome。
4. 对 canonical Evidence 只构造 aggregate key 指定的一个 horizon scope。
5. 若 `due_at > as_of`，归类 `NOT_YET_DUE`；不进入 mature denominator，不读取旧 Evidence
   revision 的已完成 Outcome 替代它。
6. 若 mature，读取 exact scope `(opportunity_id, evidence_id, horizon)` 的全部可见 Outcome
   revision，验证 chain 连续/紧邻/同 scope，再选最高 revision。较低 revision 标记
   `FOLDED_OUTCOME`。
7. 若 mature scope 没有 Outcome row，归类 `MISSING_OUTCOME`；不得推断为 PENDING、
   INSUFFICIENT_DATA 或 INVALID。
8. canonical Outcome 为 `COMPLETE` 时，只有
   `cost_adjusted_forward_return` 非 NULL 且 finite 才可进入主统计样本。若 status 与 metric
   shape 矛盾，aggregate `INTEGRITY_CONFLICT`，不得静默丢弃该行。
9. `INSUFFICIENT_DATA`、`INVALID`、`MISSING_OUTCOME` 全部保留在 coverage denominator；
   `ACTIVE / EXPIRED` 仅作 stratification，绝不作为排除理由。

### 4.3 Explicit Anti-Double-Count Rules

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

- Evidence rev1 -> rev2 -> rev3：同一 snapshot 内只允许 rev3 的 fixed-horizon scope成为样本；
  rev1/rev2 仍在 folding diagnostics 中可见。
- Outcome rev1 -> rev2：只允许 rev2 进入统计；rev1 仍在 folding diagnostics 中可见。
- canonical Evidence 没有到期/Outcome 时，禁止用 superseded Evidence 的 Outcome 补位。
- 四个 horizon 必须分表/分 key 报告；禁止求平均、拼接或把它们当独立样本扩大 N。
- `EXPIRED` 是真实 forward outcome lifecycle，不是坏数据，不得删除。

---

## 5. Revision Folding and Causal `as_of`

### 5.1 Current-Snapshot Folding

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 可安全支持的计算模式是：

```text
visibility_mode = CURRENT_STABLE_SNAPSHOT
canonical revision = highest valid revision visible in that one MVCC snapshot
```

`as_of` 取建立该 snapshot 的第一条 snapshot-taking selection statement 的数据库
`statement_timestamp`（UTC），并同时作为 maturity cutoff。计算全过程必须共享同一 snapshot；
禁止分页/多次查询跨 transaction 读取。

### 5.2 Historical `as_of` Blocker

**DESIGN BLOCKER / SCHEMA PREREQUISITE**

当前 durable schema 不能回答：一条 Evidence/Outcome correction 是否在任意历史 `as_of` 已经
commit/available。具体原因：

- `Evidence.created_at` 是调用方提供的 immutable payload field，不是 DB visibility fact；
- revision chain 无 `recorded_at`/commit sequence 的 Accepted 语义或单调约束；
- normal Outcome `created_at = due_at`，明确与写入时刻解耦；
- MVCC visibility 只存在于当次 transaction snapshot，事后不能仅靠当前表重建。

因此，以下能力在独立 prerequisite 获得 Human Acceptance 前均为 `NOT SUPPORTED`：

- 任意过去时间的 revision-as-of 重选；
- 仅凭同一个历史 `as_of` 在后续新增 correction 后恢复原输入 population；
- 把现有 `created_at` 当 correction visibility timestamp。

解除条件必须是一个独立获批任务，提供以下二者之一：

1. durable、DB-authoritative、不可回溯伪造的 revision visibility/commit ordering contract；或
2. immutable input manifest/snapshot identity，能直接恢复当时选择的 exact revision set。

本 D01 不选择列名、表、migration 或物理实现，也不授权 schema 变更。

### 5.3 Reproducibility Consequence

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

同一 stable snapshot facts + 同一 contract version + 同一 aggregate key 必须产生逐字相同的
canonical manifest、fingerprint 与数值结果。历史重跑不能只传 `as_of`；必须同时持有原
`input_manifest`。若 manifest 未留存而数据库后来增加 correction，原 snapshot selection 只能
标记 `NOT RECONSTRUCTABLE`，不得伪造复现成功。

---

## 6. Aggregation Identity

### 6.1 Exact Proposed V1 Aggregate Key

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

R01 推荐的
`(family_id, family_version, market_type, source_type, horizon)` 不足：它会合并 BTC/ETH，且会
合并同 source type 下不同 feed/manifest sampling frames。V1 候选采用：

```text
(
  family_id,
  family_version,
  instrument_id,
  market_type,
  source_type,
  source_identity,
  source_manifest_id,
  horizon,
  evidence_contract_version,
  outcome_contract_version,
  calculator_version,
  cost_policy,
  cost_model_version
)
```

`aggregation_contract_version` 是结果 metadata，不是样本维度。`calculation_digest_version` 与
`outcome_record_hash_version` 必须在 input manifest 中一致并报告；若不一致则分开计算或
fail closed，不得混合。

### 6.2 Dimension Decisions

| Dimension | V1 classification | Selected contract |
|---|---|---|
| `family_id` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：只聚合 exact family；当前合法值仅 `BREAKOUT_RETEST`。 |
| `family_version` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：策略定义变化即新 population；当前 runtime 值 `g2-v1`。 |
| `instrument_id` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：BTC 与 ETH 不池化；避免波动、流动性与采样频率差异造成 Simpson/concentration bias。 |
| BTC vs ETH | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：分别给出 aggregate；family-level overview 只能并列 stratification，不计算 pooled headline。 |
| `market_type` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：SPOT/SWAP 绝不混合。 |
| SPOT | `MAY POOL` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：仅在 full key 其余字段相同时聚合。 |
| SWAP | `NOT APPLICABLE IN V1`（primary economic expectancy） | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：当前 cost policy 明确为 `SPOT_LONG_TAKER_ROUND_TRIP`；SWAP 只报 coverage/stratification，直到另有 Accepted SWAP cost contract。 |
| `source_type` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：`FORWARD_PAPER` 与 `HISTORICAL_REPLAY` 是不同 sampling population；Gate C 只可消费 Forward Paper。 |
| `source_identity` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：不同 venue/feed provenance 不默认具有相同数据生成语义。 |
| `source_manifest_id` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：不同 replay/forward manifest 不做 post-hoc pooling；上层可并列报告。 |
| `horizon` | `MUST SEPARATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：四个持有期不混合、不平均。 |
| Evidence revision | `MUST COLLAPSE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：per opportunity 只取 snapshot-visible valid head。 |
| Outcome revision | `MUST COLLAPSE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：per exact scope 只取 snapshot-visible valid head。 |
| `ACTIVE / EXPIRED` | `REPORT AS STRATIFICATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：不影响资格或 numerator。 |
| reference status | `REPORT AS STRATIFICATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：完整报告 OK/MISSING/STALE。 |
| `experiment_id/pair_id/arm_id` | `NOT APPLICABLE IN SE-02D V1` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：当前 schema 不存在；SE-02D V1 不猜测这些 identity，见 §15 Gate C prerequisite。 |

较大的 N 不是 pooling 理由。未来跨 instrument/source/manifest pooling 必须先有独立 Accepted
comparability/weighting contract，不能由调用方临时打开开关。

---

## 7. Expectancy Contract

### 7.1 Primary Formula

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

令 `C(key, as_of)` 为 §4 选出的、canonical Outcome status 为 `COMPLETE` 且主 return shape
有效的样本集合，`x_i = cost_adjusted_forward_return_i`：

```text
n_complete = |C|
forward_outcome_expectancy = (sum over i of x_i) / n_complete
```

- numerator population：只含 `C` 的 finite `cost_adjusted_forward_return`；
- denominator：`n_complete`，不是 mature coverage denominator；
- units：dimensionless decimal return；`0.01 = +1%`，`-0.01 = -1%`；
- sign：`x > 0` positive，`x == 0.0` flat，`x < 0` negative；无 epsilon 重分类；
- `n_complete = 0`：Expectancy = `NULL`，状态 `NOT_CALCULABLE`；
- `NaN / +/-Infinity / COMPLETE+NULL`：`INTEGRITY_CONFLICT`，整个 aggregate 不出经济统计；
- 计算顺序：按 `sample_id` lexical ascending；使用确定性 `math.fsum` 或等价精确顺序，
  禁止依赖数据库任意返回顺序。

### 7.2 Minimum Secondary Evidence Set

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

同一 `C` 必报：

- `n_complete`；
- arithmetic mean（headline）；
- median（偶数样本取中间两数 arithmetic mean）；
- `positive_count / flat_count / negative_count`；
- `positive_rate = positive_count / n_complete`；
- sample standard deviation（`n-1` denominator；`n<2 => NULL`）；
- `worst_observation = min(x_i)`；
- `worst_decile_mean`（见 §12）；
- mean 的 uncertainty interval（见 §10）。

允许的最小诊断，不与 primary Expectancy 混算：

- 在同一 canonical COMPLETE sample set 上分别报告
  `mean(reference_return)`、`mean(executable_long_return)`；
- 分别报告 MFE/MAE 的 mean 与 median；
- 三类 return 永远各自命名，禁止合成一个 return statistic。

V1 明确不引入 Sharpe、Sortino、Kelly、Profit Factor、R-Multiple、drawdown、equity curve、
portfolio performance 或 parameter optimization。

---

## 8. Coverage Contract

### 8.1 Required Counts

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

每个 aggregate 必须同时输出：

```text
eligible_opportunities
not_yet_due
mature_denominator
complete
insufficient_data
invalid
missing_outcome
folded_evidence_revisions
folded_outcome_revisions
outcomes_excluded_with_folded_evidence
reference_status_counts {OK, REFERENCE_MISSING, REFERENCE_STALE}
lifecycle_counts {ACTIVE, EXPIRED, NULL}
status_reason_counts
integrity_conflict_count
```

Exact identities：

```text
eligible_opportunities
  = canonical Evidence heads matching the full aggregate key

mature_denominator
  = count(canonical Evidence heads where due_at <= as_of)
  = complete + insufficient_data + invalid + missing_outcome

coverage_rate
  = complete / mature_denominator, when mature_denominator > 0
  = NULL, when mature_denominator = 0

settlement_rate
  = (complete + insufficient_data + invalid) / mature_denominator
```

### 8.2 Status Participation

| Status | Statistical return sample | Coverage denominator | Diagnostics |
|---|---:|---:|---|
| `COMPLETE` + valid finite return | yes | yes | count + lifecycle/reference stratification |
| `COMPLETE` + invalid metric shape | no aggregate result | yes | `INTEGRITY_CONFLICT`; fail closed |
| `INSUFFICIENT_DATA` | no | yes | exact `completeness_diagnostics.reason` histogram |
| `INVALID` | no | yes | exact `INVALID_*` reason histogram |
| due scope with no Outcome | no | yes | `MISSING_OUTCOME` |
| `NOT_YET_DUE` | no | no | separate count |
| folded Evidence/Outcome revision | no | no | separate folding count; never hidden |

Reason distribution must preserve at least:
`REFERENCE_MISSING / REFERENCE_STALE / ENDPOINT_MISSING / ENDPOINT_STALE` and every durable
`INVALID_*` value. Unknown reason is `UNKNOWN_REASON` plus exact raw value；不得丢弃或重写。

### 8.3 Integrity Statement

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

任何没有 coverage block 的 Expectancy 输出都是 `INVALID_AGGREGATE_OUTPUT`。每个 artifact 必须
显式显示：

> `Positive Expectancy != Evidence Completeness Proven.`

Capture Anchor durable 之前 crash 与 session-start fence 拒绝造成的未准入机会，在当前表中不可
计数。它们必须列入 `unobservable_coverage_limitations`，不得事后重建或假装 denominator 已覆盖。

---

## 9. As-Of / Manifest / Fingerprint Contract

### 9.1 `as_of`

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

- V1 `as_of` 是 `CURRENT_STABLE_SNAPSHOT` 建立时的 UTC database statement time；
- 它同时决定 maturity：`due_at <= as_of`；
- revision visibility 由同一 PostgreSQL MVCC snapshot 决定，不由 `created_at` 推断；
- corrections 在 snapshot 内可见则参与 head selection；snapshot 后 commit 的 correction 不可见；
- 同一计算的 Evidence selection、Outcome selection、folded counts 与 manifest 必须共享同一
  read-only repeatable-read snapshot。

### 9.2 Canonical Input Manifest

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

结果必须带 deterministic `input_manifest`。每个 logical opportunity 按
`(opportunity_id, evidence_id, horizon)` 排序，至少记录：

- full aggregate key；
- canonical Evidence `evidence_id/revision/evidence_hash/evidence_at/due_at/reference_status`；
- 每条 visible Evidence revision identity + `CANONICAL/FOLDED` role；
- canonical Outcome（若有）的 `outcome_id/revision/outcome_record_hash/status/reason`；
- 每条 visible Outcome revision identity + `CANONICAL/FOLDED` role；
- `NOT_YET_DUE` / `MISSING_OUTCOME` marker；
- selected numeric return bits/hex representation for COMPLETE rows。

### 9.3 `input_fingerprint`

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

```text
input_fingerprint = SHA256(
  canonical_json({
    aggregation_contract_version,
    visibility_mode,
    as_of_utc,
    aggregate_key,
    ordered_input_manifest
  })
)
```

Canonical JSON 必须复用项目已有 G5 canonicalization/hash boundary；禁止另造 serializer。
Fingerprint 覆盖 canonical 与 folded inputs、missing/not-due markers，不覆盖任意 SQL row order。

---

## 10. Statistical Uncertainty

### 10.1 Selected Minimum-Sufficient Method

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 选择 **deterministic overlap-cluster percentile bootstrap**，只为 primary mean 提供双侧
95% interval：

1. 在 full aggregate key 内，按 `evidence_at`、`opportunity_id` 排序；
2. 每个样本区间为 `[evidence_at, due_at]`；任何相交/相接区间形成同一 connected component，
   用 sweep-line 得到确定性的 `overlap_cluster_id`；
3. bootstrap 的 resample unit 是整个 overlap cluster，不是单行；抽中 cluster 时携带其中全部
   returns，replicate mean 为所携带 returns 的 sample-weighted mean；
4. `n_resamples = 10_000`；每个 replicate 有 `n_clusters` 次 cluster draw；抽取 cluster 后保留
   cluster 内全部 observation，不做 cluster-size reweight；replicate mean 是所抽 observations 的
   arithmetic mean；
5. 将 10,000 个 replicate means 升序为 `b[0..9999]`；95% interval 固定为
   `[b[ceil(0.025 * 10000)-1], b[ceil(0.975 * 10000)-1]] = [b[249], b[9749]]`，
   禁止实现库默认插值漂移；
6. RNG seed 是完整 32-byte SHA-256 digest：
   `SHA256(canonical_json({aggregation_contract_version, aggregate_key, as_of,
   input_fingerprint, uncertainty_method_version}))`；
7. RNG algorithm 冻结为 `SHA256_COUNTER_REJECTION_V1`：第 `j` 次 cluster draw 的第 `k` 次
   rejection attempt 生成 `u = uint256_be(SHA256(seed || uint64_be(j) || uint32_be(k)))`；令
   `m = n_clusters`、`limit = 2^256 - (2^256 mod m)`，若 `u < limit` 则选择
   `cluster_index = u mod m`，否则递增 `k` 重试。结果必须记录 algorithm/version 并通过
   golden-vector test；
8. `n_clusters < 2` 或 returns 全相同：interval = `NULL`，分别标记
   `TOO_FEW_CLUSTERS` / `DEGENERATE_SAMPLE`，不得给零宽“高确定性”区间。

选择理由：mean-only 没有不确定性；t interval 对小 N/偏斜/厚尾过强；BCa 增加 jackknife 与
SciPy 依赖但不能修复共享 Forward path 的依赖；简单 i.i.d. percentile bootstrap 会低估重叠
机会的不确定性。以现有 `evidence_at/due_at` 形成 overlap cluster，是不发明 regime 或任意
block length 的最小 dependence-aware V1。

### 10.2 Dependency Decision

**PROPOSED — HUMAN DECISION REQUIRED**

`SciPy production dependency = NO`。当前 production requirements 不含 NumPy/SciPy；V1 所需的
cluster resampling、mean 与 order statistics 可用 Python 标准库小范围实现。任何未来引入
SciPy/NumPy 的提案须证明维护收益并另行获批。

### 10.3 Limitation

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

Overlap clustering 处理直接/传递重叠的 Forward windows，但不声称消除更长时间尺度的 serial
correlation、regime dependence 或 data snooping。结果必须带
`dependence_limitations = [BEYOND_HORIZON_SERIAL_DEPENDENCE_UNMODELED,
REGIME_IDENTITY_UNAVAILABLE]`。Gate C 不能仅凭此 interval 通过。

---

## 11. Primary Horizon

### 11.1 Recommendation

**PROPOSED — HUMAN DECISION REQUIRED**

推荐 `5m` 为 V1 primary horizon；`30s / 15m / 1h` 全部保留为预先声明的 secondary evidence，
分别完整报告，禁止 post-hoc 选择最好看的 horizon 或跨 horizon 求平均。

### 11.2 Rationale and Consequence

- `30s` 更容易由 spread/微结构噪声主导；
- 当前 G3 initial TradePlan risk-increasing freshness TTL 是 5 分钟，`5m` 与“当下是否值得参与
  LONG”的 Trade Decision 时间尺度最接近；
- `15m`/`1h` 更偏向后续持有与路径演化，尤其 `1h` 超过当前 setup/watch/initial-plan 语义窗口；
- 选择 `5m` 会让 primary claim 限定为短期 selection quality，不得外推 1h edge；
- secondary horizons 用于一致性/延迟效应观察，不拥有替换 primary 的权力。

---

## 12. Minimum Sample and Tail Risk

### 12.1 No Arbitrary Fixed N

**PROPOSED — HUMAN DECISION REQUIRED**

V1 不写死 30/50/100。采用 deterministic sufficiency rule：

| State | Exact behavior |
|---|---|
| `n_complete = 0` | `NOT_CALCULABLE`；所有 return stats/CI = NULL；coverage 仍完整输出。 |
| `n_complete >= 1` but `n_clusters < 2` | `CALCULABLE_DESCRIPTIVE_ONLY`；mean/median/count/tail 可报；CI = NULL；`evidence_sufficient = false`。 |
| `n_clusters >= 2` | `CALCULABLE_WITH_UNCERTAINTY`；计算 cluster percentile interval；仍不自动 sufficient。 |
| below sufficiency rule | `evidence_sufficient = false`，明确列原因。 |
| at/above sufficiency rule | `evidence_sufficient = true` 只表示 fixed-key expectancy sign 在本合同下 statistically resolved；不表示 material edge、K/D/K 或 Gate C PASS。 |

候选 sufficiency rule 同时要求：

```text
integrity_conflict_count == 0
coverage_rate == 1.0
n_clusters >= 3
bootstrap interval is non-degenerate
interval excludes 0
leave-one-cluster-out recalculations all preserve the same interval-side-of-zero classification
```

`n_clusters >= 3` 不是经验性“交易笔数门槛”：它是执行 leave-one-cluster-out 后仍至少保留两个
clusters、使 uncertainty 仍可计算的最小结构条件。真正达到 sufficiency 所需的 raw N 由 overlap、
coverage、分布与 interval 自动决定。

**PROPOSED — HUMAN DECISION REQUIRED**：Coverage floor 推荐 100%，原因是 V1 没有
Missing-At-Random 或缺失收益界限模型；任何较低
coverage 下的 positive mean 都可能是非随机缺失造成。低 coverage 结果仍可计算并报告，但不能
标 statistically resolved。若 Human 希望 `<100%`，必须另行接受 missingness policy。

### 12.2 Tail-Risk Statistic

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 最小 tail statistic 为：

```text
k = max(1, ceil(0.10 * n_complete))
worst_decile_mean = mean(the k smallest cost_adjusted_forward_return values)
```

同时报告 `worst_observation`。`worst_decile_mean` 不依赖 quantile interpolation，样本小时自然
退化为 observed worst case，样本增大后又不会被单个点完全主导，适合当前 fixed-horizon returns。
它不是 portfolio VaR/CVaR，也不授权风险限额。

`acceptable tail-risk threshold = NOT PRESENT`。

**THRESHOLD — HUMAN DECISION REQUIRED**：D01 推荐暂不设置 tail pass/fail threshold；在真实
Forward Paper 分布存在后，另行冻结可接受界限。SE-02D V1 只输出 evidence。

---

## 13. Regime Sufficiency

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

Repository Truth 没有 durable Accepted regime identity。Evidence payload/feature fields 不是已
接受的 regime taxonomy，不得被 SE-02D 暗中重命名为 regime。

V1 决策：

```text
regime_gate = NONE_IN_SE02D_V1
regime_sufficiency = NOT_EVALUABLE
```

所有结果必须披露 `REGIME_IDENTITY_UNAVAILABLE`。SE-02D 不创建 regime detector、proxy、bucket
或阈值。PRE-01A-D1 Gate C 要求的 regime concentration/criteria 因而仍是独立 prerequisite；
在该 prerequisite Human-Accepted 前，SE-02D capability 不足以使 Gate C PASS。

---

## 14. KEEP / DOWNWEIGHT / KILL Boundary

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 选择方案 A：**SE-02D 只暴露 evidence、calculability、coverage、uncertainty 与统计
sufficiency；不输出 KEEP / DOWNWEIGHT / KILL label。**

- 不硬编码 K/D/K threshold；
- 不改变 Scanner、family admission、strategy ranking、G3 Risk、Execution、position sizing；
- 不自动禁用 family；
- 不把 `evidence_sufficient` 解释成 KEEP；
- 不授予 Paper/Live 经济动作权。

未来若保留 K/D/K architecture，唯一允许的边界是一个**外部、显式、versioned、单独
Human-Accepted policy**消费 SE-02D evidence。Policy Decision 与 SE-02D Evidence 必须是两个
不同 contract/version/authority；接线同样需要单独授权。

---

## 15. Persistence and Gate C Boundary

### 15.1 Persistence Strategy

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 选择 A：deterministic on-demand derived aggregate。

- 不新增 aggregate table、migration、materialized view、scheduler、worker、daemon；
- 输出是可序列化 immutable result object，含 contract version、current-snapshot `as_of`、full
  aggregate key、coverage、uncertainty、input manifest 与 fingerprint；
- calculation 本身无写操作；并发计算共享相同 snapshot facts 时产生相同结果；
- correction 后的新 current-snapshot result 是新 artifact/fingerprint，不覆盖旧 artifact。

### 15.2 Gate C Snapshot Recommendation

**PROPOSED — HUMAN DECISION REQUIRED**

推荐 Gate C 必须留存一份 immutable aggregate evidence artifact（含 full input manifest、
fingerprint 与 policy/contract versions），但不要求 SE-02D V1 建 DB table。其存储位置、签名、
retention 与是否最终升级为 persisted snapshot table，应在 Gate C evidence task 中单独获批。

### 15.3 Experiment Identity Gap

`FACT`：当前 schema 没有 `experiment_id / pair_id / arm_id`；PRE-01A-D1 明确要求 explicit
pair/arm identity，禁止 post-hoc join。

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

- SE-02D V1 保持 family-level、experiment-arm agnostic；
- 不用 symbol/time/source 等字段猜 arm 或 pair；
- 在 Real AI Gate C 前必须有独立 identity extension task，实现并验收 explicit
  `experiment_id / pair_id / arm_id` 与同一 Opportunity/Evidence binding；
- arm-level selection Expectancy/delta 属该 future accepted identity + policy 的消费者，不由
  D01 虚构。

因此：

```text
SE-02D family aggregate ready
  != arm/pair aggregate ready
  != Gate C PASS
  != Live authorization
```

---

## 16. Proposed Output Contract

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

最小 result shape：

```text
aggregation_contract_version
status: VALID | NOT_CALCULABLE | INTEGRITY_CONFLICT | NOT_APPLICABLE
visibility_mode: CURRENT_STABLE_SNAPSHOT
as_of
aggregate_key
input_manifest
input_fingerprint
coverage
statistics
uncertainty
tail_risk
stratifications
calculability
evidence_sufficient
sufficiency_reasons
limitations
```

建议 `aggregation_contract_version = "se02d-family-aggregation-v1"`。该字符串本身在 Human
Acceptance 前仍是 proposal；任何 sample、folding、formula、coverage、uncertainty 或 key 语义
变化必须发布新 contract version，不能同版本静默漂移。

---

## 17. Human Decision Package

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**：以下每一行均为候选，必须由 Human
明确接受/修改/拒绝：

| Decision | Recommended option | Alternatives | Consequence | Recommendation rationale |
|---|---|---|---|---|
| Primary horizon | **5m** | 30s / 15m / 1h | 决定 headline selection timescale；其余仍 secondary | 对齐当前 initial TradePlan 5m freshness；比 30s 少微结构噪声，比 15m/1h 更接近参与决策 |
| Minimum sample sufficiency | **无固定 raw N；100% coverage + >=3 overlap clusters + 95% CI excludes 0 + leave-one-cluster-out 稳定** | 固定 30/50/100；precision target | 动态决定 `evidence_sufficient`；不会用大 N 掩盖 overlap/缺失 | 由现有时间区间与可计算性推导，不搬用社区经验笔数 |
| Uncertainty method | **overlap-cluster percentile bootstrap** | mean only / t / i.i.d percentile / BCa | 输出 dependence-aware mean interval | 最小处理共享 Forward path；不引入 regime/block length |
| Confidence level | **双侧 95%** | 90% / 99% / 单侧 | 改变 resolved 难度 | 常用、可解释；仍需 Human authority |
| Tail-risk statistic | **worst observation + worst-decile mean** | min only / p05 / fixed worst-k | 同时保留 observed extreme 与稳定 lower-tail summary | 无 quantile interpolation；小 N 可定义 |
| Tail-risk threshold | **V1 不设 threshold** | 固定 loss bound / quantile bound | 不产生 tail pass/fail label | 当前没有真实分布或 Accepted 风险尺度，不能发明 authority |
| Coverage sufficiency floor | **100% for statistically resolved；低于此仅 descriptive** | 90% / 80% / missingness model | 严格限制 positive mean 的决策使用 | 当前无 missing-at-random/bounding contract |
| Instrument pooling | **不池化；instrument_id 进 key** | pooled + stratification / hierarchical model | BTC/ETH 分别计算，N 更小但语义更诚实 | 防止不同波动/流动性/频率造成 concentration bias |
| Source identity/manifest pooling | **不池化** | 同 source_type 全池化 | 多个 feed/manifest 分开 | source type 相同不证明 sampling frame 相同 |
| K/D/K responsibility | **SE-02D 不输出 label** | external versioned policy / hard-coded internal policy | V1 不改变交易行为 | evidence 与 Policy Decision 分权；避免越权接线 |
| Persistence strategy | **on-demand derived + manifest/fingerprint** | DB snapshot table | 无 schema/worker；correction 产生新 artifact | 输入 immutable，最小充分；历史 `as_of` blocker明确保留 |
| SciPy dependency | **NO** | add SciPy for BCa | 标准库小实现、无科学栈 production burden | BCa 不解决 dependence，当前 requirements 无 SciPy/NumPy |
| Gate C snapshot requirement | **YES，留存 immutable evidence artifact；存储另行设计** | on-demand only / DB table now | Gate C 可审计，但不扩 D01 schema scope | Human verdict 需要冻结证据；不等于现在建表 |
| Regime sufficiency | **SE-02D V1 无 regime gate；Gate C 前另做 durable regime prerequisite** | hidden proxy / omit limitation | D01 可完成，Gate C 仍 blocked | 当前不存在 Accepted regime identity；禁止伪造 |
| Historical revision-as-of | **separate schema/manifest prerequisite** | misuse `created_at` / current max revision | 历史重选保持 NOT SUPPORTED | 当前字段不能证明 correction 当时已存在 |

---

## 18. Risks / Findings / Prerequisites

| ID | Severity | Finding | Required treatment |
|---|---|---|---|
| `D01-F01` | P1 design prerequisite | 无 durable revision availability/commit fact，历史 `as_of` folding 不可证明 | 独立 schema/manifest contract；不得用 `created_at` 冒充 |
| `D01-F02` | P1 Gate C prerequisite | 无 `experiment_id/pair_id/arm_id` | Real AI Gate C 前独立 identity extension |
| `D01-F03` | P1 Gate C prerequisite | 无 durable Accepted regime identity | Gate C 前独立 regime decision/identity，或 Human 修改 Gate C criteria |
| `D01-F04` | P2 statistical | 同 instrument 的 Opportunity Forward windows 可重叠 | overlap-cluster bootstrap + limitation disclosure |
| `D01-F05` | P2 economic semantics | SE-02C cost policy 是 SPOT LONG；schema 仍允许 SWAP Outcome | SWAP primary Expectancy `NOT_APPLICABLE_IN_V1`，不得套用 SPOT economics 声称 edge |
| `D01-F06` | P2 integrity | DB/contract 允许 `COMPLETE` metrics 为 NULL；correction path 可形成矛盾 shape | aggregation revalidation fail closed；不得 silent drop |
| `D01-F07` | P2 performance | family/version/source fields 只在 Evidence；现有索引不是为 full key/as-of aggregate 设计 | V1 on-demand 先量测；未授权加索引，后续有证据再提案 |

---

## 19. Acceptance Criteria Mapping

| AC | Candidate coverage |
|---|---|
| AC-01 Repository Truth | §2：HEAD/local main/live remote main/worktree/branch 已核验，无 drift |
| AC-02 Complete Sample Identity | §4：`(aggregate_key, opportunity_id)`，每 key 最多一次 |
| AC-03 Revision Safety | §4-§5：snapshot-visible heads、无 fallback、历史 causal blocker |
| AC-04 Aggregation Identity | §6：full key + 每维分类 |
| AC-05 Expectancy | §7：exact mean of cost-adjusted returns |
| AC-06 Coverage Integrity | §8：完整 denominator/status/reason/folding/missing counts |
| AC-07 Reproducibility | §5/§9：stable snapshot + manifest + canonical fingerprint；历史限制显式 |
| AC-08 Statistical Sufficiency | §10/§12：cluster bootstrap + deterministic sufficiency rule |
| AC-09 Tail Risk | §12：worst observation + worst-decile mean |
| AC-10 K/D/K Boundary | §14：evidence only，无 label/接线 |
| AC-11 Persistence Boundary | §15：on-demand derived，无 DB/worker/migration |
| AC-12 Gate C Boundary | §15：arm-agnostic + explicit future identity prerequisite |
| AC-13 Human Decisions | §17：每项有推荐、替代、后果、理由 |
| AC-14 No Implementation | 本 task 只允许本设计文档与最小 dev_log |
| AC-15 Candidate Status | 文件首尾均保持 `DESIGN CANDIDATE — NOT HUMAN ACCEPTED` |

---

## 20. Candidate Verdict

```text
SE-02D-D01 = DESIGN CANDIDATE — READY FOR INDEPENDENT REVIEW
Human Acceptance = NOT YET GRANTED
Implementation Authorization = NO
SE-02D Implementation = NOT STARTED
Historical as_of Revision Selection = DESIGN BLOCKER / SCHEMA PREREQUISITE
Gate C = NOT PASSED / NOT AUTHORIZED
Live = NOT AUTHORIZED
```

**STATUS: DESIGN CANDIDATE — NOT HUMAN ACCEPTED**
