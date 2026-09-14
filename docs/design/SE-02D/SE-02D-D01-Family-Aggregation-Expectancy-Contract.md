# SE-02D-D01｜Family Aggregation / Expectancy Contract

> **STATUS: ACCEPTED DESIGN**
>
> Task: `SE-02D-D01`
> Task Type: `DESIGN / CONTRACT FREEZE CANDIDATE / DOCS ONLY`
> Implementation Authorization: **NO**
> Candidate Branch: `design/se-02d-d01-family-aggregation-expectancy`
> Verified Task Base: `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`
> FIX-01 Reviewed Candidate: `1b2494c66e0c7623edf8a00d3b88f29627882771`

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

### 1.6 FIX-01 Scope Boundary

本 revision 只修复 reviewed candidate `1b2494c` 的 `D01-R1 / P1`、`D01-R2 / P1`，并最小
澄清 `D01-R3 / P2`。未重设计 Expectancy formula、uncertainty、primary horizon、minimum
sufficiency、tail risk、regime、K/D/K、persistence 或 Gate C/Live boundary；无 implementation。

---

## 2. Repository Truth

### 2.1 Baseline

| Classification | Item | Verified value |
|---|---|---|
| `FACT` | FIX-01 starting HEAD / reviewed candidate | `1b2494c66e0c7623edf8a00d3b88f29627882771` |
| `FACT` | reviewed candidate parent / D01 Task Base | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| `FACT` | local `main` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| `FACT` | live remote `refs/heads/main` | `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b` |
| `FACT` | remote candidate before FIX-01 | `1b2494c66e0c7623edf8a00d3b88f29627882771` |
| `FACT` | branch | `design/se-02d-d01-family-aggregation-expectancy` |
| `FACT` | isolated worktree | `E:\Documents\MarketPulse-AI-se-02d-d01` |
| `FACT` | design worktree before FIX-01 | clean |
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

### 2.3 R01 Evidence Treatment, Review Findings and Material Difference

`SE-02D-R01` 可读，作为 Evidence Input 使用；其 recommendation 不自动成为本候选决策。
Repository Truth 与 R01 的基础模型没有冲突，但独立复核发现一项必须收紧的差异：

| ID | Classification | Finding |
|---|---|---|
| `D01-F01` | `FACT / DESIGN BLOCKER` | `edge_opportunity_evidence.created_at` 没有 DB-assigned commit/visibility 语义或单调约束；Accepted tests 允许 Evidence rev1/rev2 使用同一回溯 `created_at`。`edge_forward_outcomes.created_at` 在 normal SE-02C 中被故意冻结为 `due_at`，也不是持久化可见时间。 |
| `D01-R1` | `INDEPENDENT REVIEW / P1` | reviewed candidate 先按包含 revision-mutable fields 的 full key 过滤 Evidence，再 fold；predecessor/successor 可被过滤隐藏，旧 revision 可残留旧 aggregate。FIX-01 必须先看完整 visible chain、再由 canonical heads 决定 membership。 |
| `D01-R2` | `INDEPENDENT REVIEW / P1` | reviewed candidate 把 Outcome-only version/cost fields 与 Evidence population fields 合成一个 key；没有 Outcome 时无法知道 `MISSING_OUTCOME` 属于哪个 coverage denominator。FIX-01 必须拆开 population identity 与 measurement compatibility。 |
| `D01-R3` | `INDEPENDENT REVIEW / P2` | Repository 证明 `source_manifest_id` 是 caller/context-supplied immutable provenance，但没有 Accepted 事实证明不同 manifest 必然是不同经济 population。FIX-01 不再无依据冻结 `MUST SEPARATE`。 |

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
| `population key` | 只由 canonical Evidence head 与 Accepted contract 可确定的 cohort identity；Outcome 缺失时仍可确定 coverage membership。 |
| `population aggregate identity` | `(population_key, horizon)`；它拥有 eligible/maturity/coverage denominator。 |
| `measurement signature` | 只从 canonical Outcome head 派生的经济/计算兼容性签名；只负责防止 COMPLETE returns 跨语义混算，不拥有 coverage membership。 |
| `sample` | 一个 population aggregate 下，一个 logical opportunity 在固定 horizon 的一次 observation；事实载体是 canonical Evidence head + canonical Outcome head 或显式 `NO_OUTCOME` marker。 |
| `mature` | canonical Evidence 的 `due_at <= as_of`。 |
| `calculable` | 至少存在一个完整、finite 的主 return，且 canonical COMPLETE Measurement Signature 唯一，可计算描述性 Expectancy。 |
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
(population_key, horizon, opportunity_id)
```

同一 Opportunity 在四个 horizon 上形成四个**分开的 repeated-measure views**；每个
`(population_key, horizon)` 内最多贡献一个 observation。四个 horizon 绝不进入同一个
population aggregate，也绝不相加成为一个经济结果的 `n = 4`。

Measurement Signature 不进入 sample identity：Outcome correction 不能制造第二个 sample；signature
只决定这一组 canonical COMPLETE observations 能否共同计算经济统计。

### 4.2 Deterministic Selection Algorithm

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

在一个 PostgreSQL `REPEATABLE READ / READ ONLY` snapshot 内，规范顺序是：

```text
full visible Evidence revision chain
-> chain/integrity validation
-> canonical Evidence head
-> exact-horizon full visible Outcome revision chain
-> chain/integrity validation
-> canonical Outcome head or NO_OUTCOME
-> derive population membership, coverage class and measurement compatibility
```

确定性算法：

1. 先取得计算 universe 内每个 `opportunity_id` 的**完整 visible Evidence chain**。在 head selection
   前禁止按 `source_type/source_identity/source_manifest_id/evidence_contract_version/market_type`
   等可随 revision 改变的字段过滤。实现可分页/分片，但不得截断任一 visible chain；本合同不指定
   SQL/window-function 物理实现。
2. 对每条完整 chain 验证 revision 从 1 连续、每个 `N>1` 紧邻 supersede `N-1`，并验证
   `family_id/family_version/instrument_id/candidate_id/market_type` 的 logical Opportunity facts
   跨 revision 一致。失败则相关输出 `INTEGRITY_CONFLICT`，不输出 Expectancy。
3. 每个 `opportunity_id` 选择 snapshot-visible 最高 valid `evidence_revision`。只有该 canonical
   Evidence head 可以决定 `population_key`；所有较低 revision 标记 `FOLDED_EVIDENCE`，不得在其
   旧 population 中保留 sample 或 coverage membership。
4. 对 canonical Evidence 的每个被请求 fixed horizon，构造 exact scope
   `(opportunity_id, canonical_evidence_id, horizon)`；读取该 scope 的**完整 visible Outcome chain**。
   即使尚未到期也不得通过 membership filter 隐藏已存在的 revision。
5. 若 Outcome chain 存在，验证 revision 连续、紧邻 supersede、全部保持 exact scope，再选择最高
   valid revision；较低 revision 标记 `FOLDED_OUTCOME`。只有 canonical Outcome head 可决定 status、
   return 与 `measurement_signature`；旧 Outcome 不得留在旧经济统计。
6. 若 Outcome chain 不存在，产生显式 `NO_OUTCOME` marker；不猜 Outcome contract/calculator/cost
   version。
7. 完成两层 canonicalization 后，才从 canonical Evidence head 派生 `population_key`，与 horizon
   组成 population aggregate identity，并按 `due_at <= as_of` 归类 maturity。
8. `due_at > as_of` 归类 `NOT_YET_DUE`；`due_at <= as_of` 且 marker 为 `NO_OUTCOME` 时必须归类
   `MISSING_OUTCOME`。两者均不回退使用 superseded Evidence 的 Outcome。
9. canonical Outcome 存在时，其 `source_type/source_identity/due_at` 必须与 canonical Evidence
   scope 一致；不一致为 `INTEGRITY_CONFLICT`。status 为 `COMPLETE` 时，只有 finite、非 NULL
   `cost_adjusted_forward_return` 可进入经济统计；矛盾 shape 同样 fail closed。
10. `INSUFFICIENT_DATA`、`INVALID`、`MISSING_OUTCOME` 全部保留在 population-level coverage；
    `ACTIVE / EXPIRED` 仅作 stratification，绝不作为排除理由。

### 4.3 Explicit Anti-Double-Count Rules

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

- Evidence rev1 -> rev2 -> rev3：先看完整 chain，只允许 rev3 head 决定当前 population；即使 rev1
  匹配旧 population key，它也不能继续成为旧 aggregate 的 canonical sample。rev1/rev2 只在
  head 所属 population 的 folding diagnostics 中可见。
- Evidence correction 改变 `source_type/source_identity/evidence_contract_version` 等 Population Key
  field 时，logical Opportunity 从旧 population **移动**到 head 决定的新 population；不得同时出现
  在两边。若只改变 `source_manifest_id` 或其它非 Population Key field，Opportunity 仍只有一个
  population membership，但 provenance/diagnostics 只采用 head 的新值；旧值只留在 folding manifest，
  也不得生成第二个 sample。
- Outcome rev1 -> rev2：先看完整 exact-scope chain，只允许 rev2 head 决定 status、measurement
  signature 与经济统计；rev1 只在 folding diagnostics 中可见。
- Outcome correction 改变 contract/calculator/cost/source field 时，旧 Outcome 不得留在旧经济
  统计；若新 head 与 Evidence source scope 矛盾则 fail closed，而不是回退 rev1。
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
canonical revision = highest valid revision selected only after validating the full chain visible
                     in that one MVCC snapshot
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

同一 stable snapshot facts + 同一 contract version + 同一 population aggregate identity 必须产生
逐字相同的 canonical manifest、fingerprint、coverage 与数值结果。历史重跑不能只传 `as_of`；必须同时持有原
`input_manifest`。若 manifest 未留存而数据库后来增加 correction，原 snapshot selection 只能
标记 `NOT RECONSTRUCTABLE`，不得伪造复现成功。

---

## 6. Population Identity and Measurement Compatibility

### 6.1 Exact Proposed V1 Identity Model

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 不再使用一个 full aggregate key 同时承担 population、coverage 与经济兼容性。冻结为：

```text
Population Key = (
  family_id,
  family_version,
  instrument_id,
  market_type,
  source_type,
  source_identity,
  evidence_contract_version
)

Population Aggregate Identity = (Population Key, horizon)

Measurement Signature = (
  outcome_contract_version,
  calculator_version,
  cost_policy,
  cost_model_version,
  outcome_source_type,
  outcome_source_identity
)
```

职责严格分开：

- `Population Key + horizon` 只从 canonical Evidence head 和 Accepted horizon contract 得出，拥有
  eligible、not-yet-due、mature、missing 与 coverage denominator；
- `Measurement Signature` 只从 canonical Outcome head 得出，负责防止不同经济/计算语义的
  COMPLETE returns 静默混算；它不创建、删除或移动 coverage membership；
- Outcome 不存在时 signature = `NO_MEASUREMENT`，但 population membership 完整存在；
- `aggregation_contract_version`、`calculation_digest_version`、`outcome_record_hash_version` 是
  result/integrity metadata，进入 manifest/fingerprint，不是 population key 或经济语义 signature。

### 6.2 Mixed Measurement Signature Rule

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

V1 选择 Minimal Sufficient Candidate A。对一个 population aggregate：

```text
complete_measurement_signatures
  = distinct Measurement Signature values among canonical COMPLETE outcomes

if count(complete_measurement_signatures) == 0:
    economic_status = NOT_CALCULABLE
elif count(complete_measurement_signatures) == 1:
    economic_status = VALID
    headline expectancy uses only that one signature
else:
    economic_status = INCOMPATIBLE_MEASUREMENT_SIGNATURES
    headline expectancy and all cross-sample economic statistics = NULL
```

无论分支为何，population-level coverage、status/reason counts、folded counts 与
`measurement_signature_counts` 必须完整输出。V1 不额外生成 per-signature headline statistics；
这避免把一个 population result 扩张成任意多的子产品。若未来需要分层经济输出，须另行接受输出
contract。不得直接 pool 不同 signature。

### 6.3 `source_manifest_id` Decision

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

Repository Truth 只证明：`source_manifest_id` 是由 capture context/caller 提供、在一次 run/context
内稳定、进入 Capture Anchor/Evidence immutable payload 与 hash 的 **provenance token**；不同
process/context 可以提供不同 manifest，durable anchor 会保留首次获准的 manifest。Repository
没有 Accepted 语义证明不同 manifest 一定代表不同经济 population，或必然不可比较。

对 FIX-01 的四个问题，结论为：

- **是否可能变化：YES。** Capture context 明确按 run 构造，Historical Replay 也由 caller 提供
  manifest；Evidence correction contract 没有要求该字段跨 revision 不变。exact run/session/dataset
  taxonomy 并未 Accepted，因此只能称 context/manifest provenance。
- **身份职责：PROVENANCE / AUDIT。** canonical Evidence head 的 manifest 值是当前 authoritative
  provenance；superseded revision 的旧值只进入 folding manifest，不拥有 population membership。
- **不同 manifest 是否必然不可比较：NOT PROVEN。** 相同 manifest 也不能覆盖 source/contract
  差异；不同 manifest 本身也不证明经济语义不同。
- **长期碎片化风险：YES。** 若 caller 每个 run/context 使用不同 token，`MUST SEPARATE` 会把同一
  family/instrument/source/contract 的长期 expectancy 人为拆成 run-sized buckets。

因此 V1 分类为：

```text
source_manifest_id = REPORT AS STRATIFICATION / PROVENANCE
                      NOT A POPULATION-KEY FIELD
                      NOT A MEASUREMENT-SIGNATURE FIELD
```

明确 comparability rule：只有当 Population Key、horizon 和唯一 Measurement Signature 全部相同
时，才允许跨 manifest 形成一个 headline；结果必须报告 `manifest_counts`、`manifest_count`、
最大 manifest concentration 与 ordered manifest ids。manifest 不得被调用方按已观察 return
post-hoc 选择。任一真正改变 source identity、contract 或 measurement semantics 的变化已由相应
key/signature 隔离。该规则既不为增加 N 强行跨语义 pool，也不因 caller-supplied run token 无依据
无限拆桶。

### 6.4 Dimension Decisions

| Dimension | V1 classification | Selected contract |
|---|---|---|
| `family_id` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：只聚合 canonical Evidence head 的 exact family。 |
| `family_version` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：策略定义变化即新 population。 |
| `instrument_id` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：BTC 与 ETH 不池化。 |
| `market_type` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：SPOT/SWAP 绝不混合。 |
| SPOT | `MAY POOL` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：只在 Population Key 其余字段相同、horizon 相同且 COMPLETE signature 唯一时聚合。 |
| SWAP | `NOT APPLICABLE IN V1`（primary economic expectancy） | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：当前 cost policy 是 SPOT LONG；SWAP 只报 population coverage，直到另有 Accepted SWAP cost contract。 |
| Evidence `source_type` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：`FORWARD_PAPER` 与 `HISTORICAL_REPLAY` 是不同 population。 |
| Evidence `source_identity` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：不同 venue/feed authority 不默认可比。 |
| `evidence_contract_version` | `MUST SEPARATE / POPULATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：Evidence meaning 变化不能静默混入。 |
| `source_manifest_id` | `REPORT AS STRATIFICATION / PROVENANCE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：按 §6.3 有限 comparability rule，不再无依据 MUST SEPARATE。 |
| `horizon` | `MUST SEPARATE / POPULATION AGGREGATE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：四个持有期不混合、不平均。 |
| Outcome contract/calculator/cost/source fields | `MEASUREMENT SIGNATURE` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：只由 canonical Outcome head 决定；mixed COMPLETE signatures fail closed。 |
| Evidence revision | `MUST COLLAPSE BEFORE MEMBERSHIP` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：完整 chain 校验后取 head。 |
| Outcome revision | `MUST COLLAPSE BEFORE ECONOMIC BUCKETING` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：完整 exact-scope chain 校验后取 head。 |
| `ACTIVE / EXPIRED` | `REPORT AS STRATIFICATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：不影响 population eligibility。 |
| reference status | `REPORT AS STRATIFICATION` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：完整报告 OK/MISSING/STALE。 |
| `experiment_id/pair_id/arm_id` | `NOT APPLICABLE IN SE-02D V1` | **PROPOSED — REQUIRES HUMAN ACCEPTANCE**：当前 schema 不存在；见 §15 Gate C prerequisite。 |

较大的 N 不是跨 Population Key 或 Measurement Signature pooling 的理由；调用方不得临时关闭
这些 boundary。

---

## 7. Expectancy Contract

### 7.1 Primary Formula

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

令 `C(population_key, horizon, as_of)` 为 §4 选出的、canonical Outcome status 为 `COMPLETE`、
主 return shape 有效，且该 population aggregate 的 COMPLETE Measurement Signature 唯一时的
样本集合；`x_i = cost_adjusted_forward_return_i`：

```text
n_economic_samples = |C|
forward_outcome_expectancy = (sum over i of x_i) / n_economic_samples
```

- numerator population：只含 `C` 的 finite `cost_adjusted_forward_return`；
- denominator：`n_economic_samples`，不是 population-level `complete` 或 mature coverage denominator；
- units：dimensionless decimal return；`0.01 = +1%`，`-0.01 = -1%`；
- sign：`x > 0` positive，`x == 0.0` flat，`x < 0` negative；无 epsilon 重分类；
- `n_economic_samples = 0`：Expectancy = `NULL`，状态 `NOT_CALCULABLE`；
- distinct COMPLETE Measurement Signature 大于 1：Expectancy = `NULL`，状态
  `INCOMPATIBLE_MEASUREMENT_SIGNATURES`；coverage 仍完整输出；
- `NaN / +/-Infinity / COMPLETE+NULL`：`INTEGRITY_CONFLICT`，整个 aggregate 不出经济统计；
- 计算顺序：按 `sample_id` lexical ascending；使用确定性 `math.fsum` 或等价精确顺序，
  禁止依赖数据库任意返回顺序。

### 7.2 Minimum Secondary Evidence Set

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

同一 `C` 必报：

- `n_economic_samples`（仅 `economic_status = VALID` 时有值；此时无 integrity conflict，且等于
  population-level `complete`）；
- arithmetic mean（headline）；
- median（偶数样本取中间两数 arithmetic mean）；
- `positive_count / flat_count / negative_count`；
- `positive_rate = positive_count / n_economic_samples`；
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
measurement_signature_counts
manifest_counts
```

这些量全部属于 `(population_key, horizon)`，不属于 Measurement Signature。Exact identities：

```text
eligible_opportunities
  = count(canonical Evidence heads whose post-fold Population Key equals the requested key)

not_yet_due
  = count(eligible canonical Evidence heads where due_at > as_of)

mature_denominator
  = count(eligible canonical Evidence heads where due_at <= as_of)
  = complete + insufficient_data + invalid + missing_outcome

complete
  = mature canonical scopes whose canonical Outcome head status is COMPLETE

insufficient_data
  = mature canonical scopes whose canonical Outcome head status is INSUFFICIENT_DATA

invalid
  = mature canonical scopes whose canonical Outcome head status is INVALID

missing_outcome
  = mature canonical scopes carrying NO_OUTCOME after exact-scope full-chain lookup

coverage_rate
  = complete / mature_denominator, when mature_denominator > 0
  = NULL, when mature_denominator = 0

settlement_rate
  = (complete + insufficient_data + invalid) / mature_denominator
```

`complete/insufficient_data/invalid/missing_outcome` 四类对每个 mature canonical scope 恰好命中
一类。Measurement Signature 缺失、唯一或混合都不得改变这些 population counts。若 COMPLETE
row 的 metric/source shape 存在 integrity conflict，保留 raw COMPLETE status count并把
`integrity_conflict_count > 0`；coverage 仍可审计，但 economic result fail closed。

### 8.2 Constructive `MISSING_OUTCOME` Proof

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

给定：

```text
canonical Evidence head E exists
P = PopulationKey(E)
H = requested fixed horizon
due_at(E, H) <= as_of
visible Outcome rows for (E.opportunity_id, E.evidence_id, H) = empty
```

算法先由 `E` 得到 `(P,H)` membership，再由 empty exact-scope chain 产生 `NO_OUTCOME`：

```text
eligible_opportunities(P,H) += 1
mature_denominator(P,H) += 1
missing_outcome(P,H) += 1
measurement_signature = NO_MEASUREMENT
```

这里不读取、不默认、也不猜测 `outcome_contract_version/calculator_version/cost_policy/
cost_model_version`。因此不存在 Outcome 时仍能可靠进入正确 coverage denominator。

### 8.3 Status Participation

| Status | Statistical return sample | Coverage denominator | Diagnostics |
|---|---:|---:|---|
| `COMPLETE` + valid finite return | yes | yes | count + lifecycle/reference stratification |
| `COMPLETE` + invalid metric shape | no aggregate result | yes | `INTEGRITY_CONFLICT`; fail closed |
| `INSUFFICIENT_DATA` | no | yes | exact `completeness_diagnostics.reason` histogram |
| `INVALID` | no | yes | exact `INVALID_*` reason histogram |
| due scope with no Outcome | no | yes | `MISSING_OUTCOME` |
| `NOT_YET_DUE` | no | no | separate count |
| folded Evidence/Outcome revision | no | no | separate folding count; never hidden |

同一 logical Opportunity 的 folded Evidence diagnostics 归属 canonical head 的当前 Population Key；
不得为了显示旧 key 的 folded count 而给旧 population 恢复 membership。Outcome folding diagnostics
同理由 canonical Evidence 当前 population + horizon 承载。

Reason distribution must preserve at least:
`REFERENCE_MISSING / REFERENCE_STALE / ENDPOINT_MISSING / ENDPOINT_STALE` and every durable
`INVALID_*` value. Unknown reason is `UNKNOWN_REASON` plus exact raw value；不得丢弃或重写。

### 8.4 Integrity Statement

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
- 同一计算的 Evidence selection、Outcome selection、population membership、Measurement
  Signature、folded counts 与 manifest 必须共享同一
  read-only repeatable-read snapshot。

### 9.2 Canonical Input Manifest

**PROPOSED — REQUIRES HUMAN ACCEPTANCE**

结果必须带 deterministic `input_manifest`。每个 logical opportunity 按
`(opportunity_id, evidence_id, horizon)` 排序，至少记录：

- Population Key + horizon；
- canonical Evidence `evidence_id/revision/evidence_hash/evidence_at/due_at/reference_status`；
- canonical Evidence 的 `source_manifest_id` 与 population-level manifest stratification；
- 每条 visible Evidence revision identity + `CANONICAL/FOLDED` role；
- canonical Outcome（若有）的 `outcome_id/revision/outcome_record_hash/status/reason`；
- canonical Outcome 的 Measurement Signature，或 `NO_MEASUREMENT`；
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
    population_key,
    horizon,
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

1. 在一个 `(population_key, horizon)` 内，按 `evidence_at`、`opportunity_id` 排序；
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
   `SHA256(canonical_json({aggregation_contract_version, population_key, horizon, as_of,
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
| `n_economic_samples = 0` | `NOT_CALCULABLE`；所有 return stats/CI = NULL；coverage 仍完整输出。 |
| `n_economic_samples >= 1` but `n_clusters < 2` | `CALCULABLE_DESCRIPTIVE_ONLY`；mean/median/count/tail 可报；CI = NULL；`evidence_sufficient = false`。 |
| `n_clusters >= 2` | `CALCULABLE_WITH_UNCERTAINTY`；计算 cluster percentile interval；仍不自动 sufficient。 |
| below sufficiency rule | `evidence_sufficient = false`，明确列原因。 |
| at/above sufficiency rule | `evidence_sufficient = true` 只表示 fixed population/horizon expectancy sign 在本合同下 statistically resolved；不表示 material edge、K/D/K 或 Gate C PASS。 |

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
k = max(1, ceil(0.10 * n_economic_samples))
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
- 输出是可序列化 immutable result object，含 contract version、current-snapshot `as_of`、
  Population Key、horizon、Measurement Signature 状态、coverage、uncertainty、input manifest 与
  fingerprint；
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
status: VALID | NOT_CALCULABLE | INCOMPATIBLE_MEASUREMENT_SIGNATURES |
        INTEGRITY_CONFLICT | NOT_APPLICABLE
visibility_mode: CURRENT_STABLE_SNAPSHOT
as_of
population_key
horizon
measurement_signature: exact signature | NO_MEASUREMENT | MIXED
measurement_signature_counts
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
| Instrument pooling | **不池化；instrument_id 进 Population Key** | pooled + stratification / hierarchical model | BTC/ETH 分别计算，N 更小但语义更诚实 | 防止不同波动/流动性/频率造成 concentration bias |
| Source identity pooling | **不池化；Evidence source identity 进 Population Key** | 同 source_type 全池化 | venue/feed authority 分开 | source type 相同不证明 sampling process 相同 |
| Source manifest treatment | **provenance stratification；仅在 Population Key/horizon/唯一 signature 相同且预先声明时跨 manifest headline** | MUST SEPARATE / completely ignore manifest | 不按 run token 碎桶，但保留 manifest counts/concentration | Repository 未证明不同 manifest 必然不可比；也禁止 post-hoc 选择 |
| Mixed Measurement Signature | **Candidate A：coverage 保留，headline fail closed** | per-signature economic sub-results | 多版本时 `INCOMPATIBLE_MEASUREMENT_SIGNATURES` | 最小充分，避免跨 calculator/cost 语义混算与产品扩张 |
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
| `D01-F07` | P2 performance | family/version/source fields 只在 Evidence；现有索引不是为 post-fold Population Key/as-of aggregate 设计 | V1 on-demand 先量测；未授权加索引，后续有证据再提案 |
| `D01-R1` | P1 reviewed-candidate blocker | revision-mutable membership 先于 folding | **FIX-01 REMEDIATED IN CANDIDATE / RE-REVIEW REQUIRED**：§4 先完整 chain validation/fold，再由 heads 决定 membership |
| `D01-R2` | P1 reviewed-candidate blocker | Outcome fields 阻断 missing coverage identity | **FIX-01 REMEDIATED IN CANDIDATE / RE-REVIEW REQUIRED**：§6/§8 分离 Population Key 与 Measurement Signature |
| `D01-R3` | P2 clarification | manifest `MUST SEPARATE` 缺少 Accepted comparability 依据 | **FIX-01 CLARIFIED IN CANDIDATE**：provenance stratification + 有限、预先声明的 comparability rule |

---

## 19. Acceptance Criteria Mapping

### 19.1 Original D01 Regression

| AC | Candidate coverage |
|---|---|
| AC-01 Repository Truth | §2：HEAD/local main/live remote main/worktree/branch 已核验，无 drift |
| AC-02 Complete Sample Identity | §4：`(population_key, horizon, opportunity_id)`，每 population/horizon 最多一次 |
| AC-03 Revision Safety | §4-§5：完整 visible chains 先 fold、无 fallback、历史 causal blocker |
| AC-04 Aggregation Identity | §6：Population Key + horizon + Measurement Signature + 每维分类 |
| AC-05 Expectancy | §7：唯一 compatible signature 下 exact mean of cost-adjusted returns |
| AC-06 Coverage Integrity | §8：population-based denominator/status/reason/folding/missing counts |
| AC-07 Reproducibility | §5/§9：stable snapshot + manifest + canonical fingerprint；历史限制显式 |
| AC-08 Statistical Sufficiency | §10/§12：cluster bootstrap + deterministic sufficiency rule |
| AC-09 Tail Risk | §12：worst observation + worst-decile mean |
| AC-10 K/D/K Boundary | §14：evidence only，无 label/接线 |
| AC-11 Persistence Boundary | §15：on-demand derived，无 DB/worker/migration |
| AC-12 Gate C Boundary | §15：arm-agnostic + explicit future identity prerequisite |
| AC-13 Human Decisions | §17：每项有推荐、替代、后果、理由 |
| AC-14 No Implementation | 本 task 只允许本设计文档与最小 dev_log |
| AC-15 Candidate Status（reviewed candidate 时点）| 该时点文件首尾均为 `DESIGN CANDIDATE — NOT HUMAN ACCEPTED`；已由 §21 Acceptance Record 收口为 `ACCEPTED DESIGN` |

### 19.2 FIX-01 Acceptance Criteria

| AC | FIX-01 candidate evidence |
|---|---|
| FIX AC-01 Accepted lineage | §2：reviewed candidate `1b2494c` 直接位于 live accepted main `1e7eeb2` 之上 |
| FIX AC-02 Fold before membership | §4.2：完整 visible Evidence chain -> head ->完整 exact-horizon Outcome chain -> head/marker -> membership |
| FIX AC-03 Evidence correction move | §4.3：只有 head 决定 Population Key；old revision 不保留旧 population sample |
| FIX AC-04 Outcome correction move | §4.2/§6.2：只有 Outcome head 决定 signature/status/return；old outcome 不保留经济统计 |
| FIX AC-05 Missing population identity | §6.1/§8.2：Population Key + horizon 完全由 Evidence/Accepted horizon 确定 |
| FIX AC-06 Missing without Outcome fields | §8.2：`NO_OUTCOME` 直接进入 `MISSING_OUTCOME`，不猜 calculator/cost fields |
| FIX AC-07 Mixed measurement | §6.2：Candidate A `INCOMPATIBLE_MEASUREMENT_SIGNATURES`，coverage 保留、headline NULL |
| FIX AC-08 Manifest semantics | §6.3：Repository provenance facts + 明确有限 comparability rule，不再无依据 MUST SEPARATE |
| FIX AC-09 Human decisions consistent | §17：key、manifest、mixed signature rows 已同步 |
| FIX AC-10 Docs only | FIX-01 只允许本 design 与最小 dev_log；production/test/schema/runtime diff 必须为零 |
| FIX AC-11 Candidate status（reviewed candidate 时点）| 该时点首尾保持 `DESIGN CANDIDATE — NOT HUMAN ACCEPTED`；已由 §21 Acceptance Record 收口为 `ACCEPTED DESIGN` |

---

## 20. Candidate Verdict（reviewed candidate 时点）

```text
SE-02D-D01 = DESIGN CANDIDATE — READY FOR INDEPENDENT REVIEW
SE-02D-D01-FIX-01 = READY FOR INDEPENDENT RE-REVIEW
D01-R1 / D01-R2 = FIXED IN CANDIDATE / NOT YET ACCEPTED
D01-R3 = CLARIFIED IN CANDIDATE / NOT YET ACCEPTED
Human Acceptance = NOT YET GRANTED
Implementation Authorization = NO
SE-02D Implementation = NOT STARTED
Historical as_of Revision Selection = DESIGN BLOCKER / SCHEMA PREREQUISITE
Gate C = NOT PASSED / NOT AUTHORIZED
Live = NOT AUTHORIZED
```

> 上表为 reviewed candidate 时点的 Candidate Verdict；其后收口记录见 §21 Acceptance Record。

## 21. Acceptance Record

**ACCEPTED DESIGN** — 本文件已由 Human Acceptance 收口为 Accepted Design。实质契约内容与
Human-Accepted candidate 逐字一致；本记录只变更 Acceptance-state / closeout metadata。

| Field | Value |
|---|---|
| Artifact Status | `ACCEPTED DESIGN` |
| Independent Initial Review | `FAIL — FIX REQUIRED` |
| `D01-R1` | `CLOSED` |
| `D01-R2` | `CLOSED` |
| `D01-R3` | `CLARIFIED / NON-BLOCKING` |
| FIX-01 Independent Re-Review | `PASS` |
| Human Acceptance | `CONFIRMED — 2026-09-15` |
| Human-Accepted Candidate | `245b068199b7e6f3d32bf67e3b00163e4804afdf` |
| Human-Accepted Candidate Branch | `design/se-02d-d01-family-aggregation-expectancy`（immutable evidence pointer） |
| Closeout Reconciliation Base | `9e0553f5dee3fcb4a2dad0b672280657235656aa` |
| Reconciliation Shape | orthogonal PRE-01B accepted docs/state drift → latest-main content-level carry-forward（candidate **不是** current `main` 的 ancestor） |
| Integration Method | `FAST-FORWARD ONLY`（closeout commit 单 parent = `9e0553f5…` lineage） |
| Implementation Authorization | **NO** |
| `SE-02D Implementation` | `NOT STARTED` |

收口后仍保持：

```text
SE-02D capability complete != Gate C PASS
Gate C PASS != Live authorization
```

本 Accepted Design **不**授权 implementation、schema、runtime、交易行为或 Gate C / Live 判定；
historical revision-as-of、experiment/pair/arm identity 与 durable regime 仍是独立 prerequisite。

**STATUS: ACCEPTED DESIGN**
