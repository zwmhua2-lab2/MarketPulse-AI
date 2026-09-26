[AI Development Workflow｜UI-RD01-I04-DESIGN-01｜Rules 0.1.0｜Rule Load: PASS]

## Result

**`GOVERNANCE REBOUND / DESIGN CANDIDATE COMPLETE / READY FOR INDEPENDENT DESIGN REVIEW`**

```
Governance Rebind:
PASS

Workflow Main:
1e2732a90d302955387920edaf6116c2f761e0cc

MarketPulse Main:
8c94ea338f500e2ea4dd2f8a5ccc81a65502468e

Original Scope Changed:
NO

Implementation Authority:
NOT GRANTED

Repository Mutation:
NONE

Candidate Persistence:
NOT PERFORMED

Independent Design Review:
NOT PERFORMED
```

开始恢复任务时和完成输入核验后，两个仓库的实时 `main` 均与重绑定卡一致。本轮继续原 `UI-RD01-I04-DESIGN-01`，没有另建任务、修改仓库或开始实现。 

以下为完整候选正文。**候选中确定的新参数与实现约束仍须经过独立设计评审和后续冻结；不代表当前仓库已经实现。**

---

# UI-RD01-I04 Implementation Requirements Candidate v0.1

## 1. Candidate Identity

| 字段值                     |                                                                              |
| ----------------------- | ---------------------------------------------------------------------------- |
| Project                 | `MarketPulse AI`                                                             |
| Task ID                 | `UI-RD01-I04-DESIGN-01`                                                      |
| Rebind Record           | `UI-RD01-I04-DESIGN-01-REBIND-01`                                            |
| Work                    | `UI-RD01-I04｜EdgeAggregateRead Requirement / Implementation Contract Design` |
| Candidate ID            | `UI-RD01-I04-Implementation-Requirements-v0.1`                               |
| Candidate Status        | `DESIGN CANDIDATE / NON-AUTHORITATIVE`                                       |
| Role / Mode             | `DESIGNER / STRICT READ_ONLY / REQUIREMENT DESIGN`                           |
| Delivery                | 本次回复中的完整候选正文                                                                 |
| Recommended Future Path | `docs/design/UI-RD01/UI-RD01-I04-Implementation-Requirements.md`             |
| Freeze                  | `NOT PERFORMED`                                                              |
| Implementation          | `NOT STARTED BY THIS TASK / NOT AUTHORIZED`                                  |

本候选只规定未来 I04 实现的要求与验收边界，不执行代码修改、文件持久化、分支创建、提交、推送或状态推进。

后续评审必须绑定这份完整正文的确定版本；仅有候选名称或版本号不能替代内容身份。持久化后的文件哈希不得在本轮伪造。

---

## 2. Governance Binding

### 2.1 当前绑定

```
Workflow Repository:
zwmhua2-lab2/ai-dev-workflow

Workflow Commit:
1e2732a90d302955387920edaf6116c2f761e0cc

Governance Version:
0.1.0

Rule Pack:
0.1.0

Rule Manifest:
fd00-rule-manifest/0.1.0

Governance Mode:
SELF_HOSTED
```

### 2.2 完整规则加载记录

以下文件均从上述精确提交完成全文读取：

| 文件加载结果                                    |             |
| ----------------------------------------- | ----------- |
| `AI_WORKFLOW_BOOTSTRAP.md`                | `FULL READ` |
| `governance/WORKFLOW_RULE_MANIFEST.md`    | `FULL READ` |
| `governance/AUTHORITY_RULES.md`           | `FULL READ` |
| `governance/TASK_CONTRACT_RULES.md`       | `FULL READ` |
| `governance/ROLE_AUTHORITY_RULES.md`      | `FULL READ` |
| `governance/RISK_AND_ACCEPTANCE_RULES.md` | `FULL READ` |
| `governance/CONTEXT_AND_HARNESS_RULES.md` | `FULL READ` |
| `governance/SELF_HOSTING_RULES.md`        | `FULL READ` |
| `PROJECT_STATE.md`                        | `FULL READ` |

治理身份、规则版本和 Manifest 一致。旧 `ai-dev-protocol` 不作为缺失规则的回退来源。正式验收仍须满足当前绑定、正式验证、必要独立评审、零开放阻断项、有效证据与适用的人类治理门，不能由设计者自行宣布成立。  

---

## 3. Repository Binding and Authoritative Inputs

### 3.1 产品基线

```
Repository:
zwmhua2-lab2/MarketPulse-AI

Product Baseline:
8c94ea338f500e2ea4dd2f8a5ccc81a65502468e
```

### 3.2 四份权威输入

| ID文件已核验 Git Blob |                                                                           |                                            |
| ---------------- | ------------------------------------------------------------------------- | ------------------------------------------ |
| A                | `docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md`           | `f98dd6e92695aa9e56237d1c7fa6000b7368aff5` |
| B                | `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`          | `62173554e3824418326a9f782e1f9c7e971ca25a` |
| C                | `docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md`           | `b3af9d9aa0ee4ac7152216761a57974217935a88` |
| D                | `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md` | `f9b9ac904bb31c61ed95ce6f3a268e7836dfbd70` |

四个 Blob 均与任务卡一致。产品接口、UI 选择语义、冻结修订和 SE-02D 数学契约分别以这些输入为依据。   

本候选同时核对了当前 SE-02D reader、folding、orchestration、result 类型，以及 Product DTO、认证、数据库借用边界和前端类型生成入口。**实现符号与设计中建议新增的符号，在后文明确区分。**

---

## 4. Risk Classification、Scope 与 Out of Scope

### 4.1 风险保持不变

```
Risk Tier:
L2

Risk Tags:
PUBLIC_CONTRACT
PERSISTENCE
CONCURRENCY

Protected Subsystem Direct Ownership:
NONE

Consumed Authority:
Accepted SE-02D aggregation / expectancy truth
```

I04 只消费已有数学、持久化事实与认证能力，不拥有这些能力的修改权。

如果实现需要改变 SE-02D 数学、schema、migration、index、RuntimeHost 权限、交易或经济语义，必须停止相关变更并重新分类、重新授权，不能以“完成 I04”为由顺带实施。

### 4.2 In Scope

设计并在未来同一验收单元中交付：

```
GET /api/v1/product/edge-aggregates
EdgeAggregateRead

Typed DTO
Population selector / catalog pagination
Exact provenance selection
Stable read-only snapshot
Accepted revision folding reuse
Bounded full-query admission
Bounded CPU admission and thread offload
State/error mapping
OpenAPI/generated.ts integration
Deterministic verification
Performance evidence
```

### 4.3 Out of Scope

仍排除实现执行本身，以及 schema/migration/index 变更、SE-02D 数学变更、新统计、策略排名、Edge Score、A/B/C Grade、Win Rate、Sharpe、Sortino、Profit Factor、Drawdown、Equity Curve、R-Multiple、KEEP/DOWNWEIGHT/KILL、Gate C、Real AI activation、live G2→G3、Live Trading、前端 Edge Lab 页面、`UI-I04` 和 `UI-RD01-I05`。

---

## 5. 产品语义与唯一计算权威

### R-01：只提供证据，不提供策略决策

接口输出的是指定人口、指定 horizon 的 **Family Aggregation / Forward Outcome Expectancy evidence**。

`expectancy` 的产品含义是“平均成本调整后后续收益”，不是实际成交收益、账户收益或策略推荐。`evidence_sufficient=true` 不能被翻译为“值得交易”“KEEP”或“Gate C 已通过”。

### R-02：唯一聚合入口

未来 Product 路径必须调用现有：

```
marketpulse.edge.aggregation_orchestration.aggregate_projection()
```

不得在路由、DTO adapter 或前端重新实现均值、bootstrap、coverage、sufficiency、tail 或 revision folding。

当前 `aggregate_current_snapshot()` 在读取后同步调用纯聚合函数，不能未经拆分直接作为异步 HTTP 路径使用；I04 必须把 snapshot 读取与 CPU offload 分开。

### R-03：严格保留实际枚举

聚合 `status` 只能是：

```
VALID
NOT_CALCULABLE
INCOMPATIBLE_MEASUREMENT_SIGNATURES
INTEGRITY_CONFLICT
NOT_APPLICABLE
```

**`INSUFFICIENT_DATA` 是 Outcome/coverage 分类，不新增为 AggregateStatus。**

`calculability` 保留现有可空类型：

```
NOT_CALCULABLE
CALCULABLE_DESCRIPTIVE_ONLY
CALCULABLE_WITH_UNCERTAINTY
null
```

Adapter 必须复制实际 `AggregationResult.calculability`。例如当前实现某些非 `VALID` 结果返回 `null`，Product 不得自行补成另一个枚举值。 

---

## 6. Exact Population Key 与 Horizon

### R-04：人口身份

`PopulationKeyDTO` 必须完整包含：

| 字段类型与来源                     |                                       |
| --------------------------- | ------------------------------------- |
| `family_id`                 | Accepted `EdgeFamily` 值               |
| `family_version`            | 非空字符串                                 |
| `instrument_id`             | 非空字符串                                 |
| `market_type`               | Accepted `MarketType` 值               |
| `source_type`               | `FORWARD_PAPER` 或 `HISTORICAL_REPLAY` |
| `source_identity`           | 非空字符串                                 |
| `evidence_contract_version` | 非空字符串                                 |

全部取自 canonical Evidence head 对应的现有 `PopulationKey`。

人口相等性由七个结构字段决定，不能由显示名称、字符串拼接、selector、digest 或某个字段子集决定。`source_manifest_id` 和 Measurement Signature 不进入 Population Key。现有实现已将结构相等性与用于排序的 `canonical_key()` 明确分离。

### R-05：聚合身份

```
Aggregate Identity = (PopulationKey, horizon)
```

`horizon` 仅允许：

| Horizon角色 |                  |
| --------- | ---------------- |
| `5m`      | Primary，同时为请求默认值 |
| `30s`     | Secondary        |
| `15m`     | Secondary        |
| `1h`      | Secondary        |

每次请求只计算一个 horizon。禁止跨 horizon 池化、平均、自动选择表现最好的一项，或把 `5m` 解释成查询最近五分钟的记录。

---

## 7. Query Contract

### R-06：正式参数

| 参数类型默认值 / 约束              |                                   |                            |
| ------------------------- | --------------------------------- | -------------------------- |
| `horizon`                 | 上述四值枚举                            | `5m`                       |
| `selected_population_key` | server-issued opaque selector，可省略 | 这里是 selector，不是客户端提交的七字段对象 |
| `source_type`             | 两值枚举                              | `FORWARD_PAPER`            |
| `source_identity`         | 可省略的精确字符串过滤条件                     | 不 trim、不大小写折叠、不改写身份        |
| `limit`                   | integer                           | `100`，范围 `1..500`；只分页人口目录  |
| `cursor`                  | opaque/versioned token，可省略        | 只推进人口目录，不分页统计样本            |

`limit/cursor` 继承父设计的 collection pagination 约束，不增加统计筛选维度。

本端点不接受 `range/start/end/as_of/offset/order_by/ranking`。未知参数、重复参数、非法枚举、空 selector 或格式错误均返回 `422`。

输入长度约束属于本候选的解析资源边界：

```
Population selector:
固定格式，68 个 ASCII 字符。

source_identity:
1..4096 UTF-8 bytes；禁止 ASCII 控制字符。
不执行 Unicode 归一化或身份改写。

cursor:
最多 16384 个 ASCII 字符。
```

这些限制不允许反过来截断数据库中的身份字段。

### R-07：source identity 要求矩阵

| 请求行为                             |                                                   |
| -------------------------------- | ------------------------------------------------- |
| Forward；无 identity、无 selector    | 发现当前 snapshot 中全部 Forward 人口，按完整目录决定是否可自动选择       |
| Forward；有 identity、无 selector    | 在 canonical folding 后按精确 identity 过滤，再决定选择状态      |
| Forward；有 selector               | selector 必须解析到当前 Forward 人口；同时提供 identity 时必须完全一致 |
| Replay；有 identity、无 selector     | 只发现该精确 Replay identity 的人口                        |
| Replay；有 selector                | selector 必须解析到当前 Replay 人口；可由它确定 identity         |
| Replay；identity 和 selector 都没有   | `422`，不得隐式扫描并选择某个 Replay 来源作为结果                   |
| 未显式请求 Replay，却提交 Replay selector | `422`，不得从 selector 自动切换 source type               |

对不同 `source_identity` 的数据，不建立合并人口，不推断“同一交易所应该算一个来源”。

### R-08：选择行为

选择判断基于**分页前的完整匹配人口集合**：

| 完整匹配数量 / 输入`selection_state`行为 |                      |                     |
| ------------------------------ | -------------------- | ------------------- |
| 0，无显式 selector                 | `NONE_AVAILABLE`     | 无 aggregate         |
| 1，无显式 selector                 | `SELECTED`           | 自动选择唯一人口            |
| 大于 1，无显式 selector              | `SELECTION_REQUIRED` | 返回人口目录，不计算任意“默认第一名” |
| 合法显式 selector，当前存在             | `SELECTED`           | 只计算该完整人口            |
| selector 当前不存在或不匹配请求来源         | 无成功选择状态              | `422`，不得换选其他人口      |

不能因为当前目录页只有一条，就把“完整目录有多个匹配”误判成唯一人口。唯一匹配才允许自动选择，是已冻结的 UI 选择语义。

---

## 8. Selector 与 Population Catalog Pagination

### R-09：Population selector

本候选选择 **基于现有 session secret 的、域隔离的 HMAC selector**。它只保护选择器完整性，**不是认证 token，也不授予额外读取权限**。

格式：

```
ep1.<64 lowercase hexadecimal characters>
```

生成材料固定为：

```
HMAC-SHA256(
    key = UTF-8(existing Settings.session_secret),
    message = canonical_bytes([
        "ui-rd01-edge-population-selector-v1",
        PopulationKey.canonical_payload()
    ])
)
```

复用现有 `canonical_bytes()`，不另造 Population Key serializer。仓库已有 `Settings.session_secret`、HMAC-SHA256 和 `verify_session` 认证路径；I04 不修改它们的认证规则或 secret 生命周期。 

要求如下：

- 只为已验证、canonical population 生成 selector。
- 请求 selector 必须与当前 snapshot 目录中的服务器重建值匹配。
- 格式、版本、MAC、来源或当前成员关系不成立时返回 `422`。
- 两个不同结构人口意外得到相同 selector 时，整次请求 fail closed，不能保留第一项。
- selector 不包含 horizon；切换 horizon 不改变人口身份，但必须重新读取该 horizon 的 current snapshot。
- secret 轮换可使旧 selector 失效，但不得改变结构人口身份、SE-02D fingerprint 算法或数学结果。
- 将一个合法 selector 换成另一个当前合法 selector，是合法选择操作，不是权限升级。

### R-10：目录排序与 cursor

`available_populations` 按完整 selector 的 ASCII lexical ascending 排序，不按 expectancy、样本数或 sufficiency 排序。

Cursor 固定采用：

```
ec1.<base64url-without-padding payload>.<HMAC-SHA256>
```

Payload 必须具有确定字段：

```
version
endpoint
visibility_mode
time_range = null
horizon
source_type
source_identity
selected_population_key
limit
last_selector
catalog_digest
```

MAC 使用与人口 selector 不同的 domain：

```
ui-rd01-edge-population-cursor-v1
```

`catalog_digest` 绑定当前过滤后完整、排序后的 selector 集合。它只用于目录分页一致性，**不是 SE-02D input_fingerprint**。

Cursor 验证必须检查 MAC、版本、字段集合、字段类型、endpoint、全部查询绑定、目录 digest 和最后排序位置。重复 JSON key、未知字段或非规范结构不得宽容接受。

目录成员集合变化时，旧 cursor 返回 `422`，客户端须从第一页重新发现。后续页仍是新的 current snapshot，不声称重建上一页的历史 MVCC snapshot。

分页不裁剪参与选中人口聚合的 samples、revision chains 或 manifest。成功分页的 `meta.is_partial=false`：这是完整目录中的一页，不是“不完整的聚合结果”。

---

## 9. Concrete DTO Contract

### R-11：公共类型约束

新增公开 DTO 必须使用具体 Pydantic 类型，拒绝未声明字段。

```
Count:
非负整数，不接受 bool 冒充整数。

FiniteReturn:
有限 JSON number；不允许 NaN / Infinity。

UtcTimestamp:
timezone-aware UTC timestamp。

Nullable:
只有本合同明确允许缺失事实的字段可以为 null。
```

不得暴露 `dict[str, object]`、任意 payload、ORM row、session、provider handle 或整个 `AggregationResult.to_dict()`。

### 9.1 Envelope

`EdgeAggregateReadResponse`：

| 字段类型                  |                                    |
| --------------------- | ---------------------------------- |
| `meta`                | 复用 `ProjectionMetaDTO`             |
| `operational_context` | 复用 `OperationalContextDTO`         |
| `query_context`       | `EdgeAggregateQueryContextDTO`     |
| `data`                | `EdgeAggregateReadDataDTO \| null` |

`query_context`：

| 字段类型                            |                  |
| ------------------------------- | ---------------- |
| `horizon`                       | 四值 horizon       |
| `source_type`                   | 两值 source type   |
| `requested_source_identity`     | `string \| null` |
| `requested_population_selector` | `string \| null` |
| `limit`                         | `integer`        |

查询回显不是人口存在性或来源可用性的证明。

`data`：

| 字段类型 / 语义                      |                                                  |
| ------------------------------ | ------------------------------------------------ |
| `available_populations`        | `list[EdgePopulationOptionDTO]`，当前目录页            |
| `population_count`             | `Count`，分页前完整匹配人口数                               |
| `selection_state`              | `NONE_AVAILABLE / SELECTION_REQUIRED / SELECTED` |
| `selected_population_key`      | `PopulationKeyDTO \| null`                       |
| `selected_population_selector` | `string \| null`                                 |
| `horizon`                      | 本次请求 horizon                                     |
| `source_type`                  | 本次显式解析的查询 provenance                             |
| `source_identity`              | 已选人口 identity；未选中时为显式请求的 identity 或 `null`       |
| `as_of`                        | 成功 DB snapshot 的时间                               |
| `aggregate`                    | `EdgeAggregateDTO \| null`                       |

`EdgePopulationOptionDTO` 仅包含：

```
selector: string
population_key: PopulationKeyDTO
```

没有选中人口时，不存在可合法伪造的单一 aggregate identity。此时 `aggregate=null`，相关选择字段明确为 `null`；目录中每个人口仍完整携带自己的七字段身份。禁止用 `"ALL"` 或 `"UNKNOWN"` 代替真实 `source_identity`。

### 9.2 Aggregate

`EdgeAggregateDTO`：

| 字段类型 / 唯一来源                         |                                         |
| ----------------------------------- | --------------------------------------- |
| `status`                            | `AggregateStatus`，复制 `R.status`         |
| `expectancy`                        | `ExpectancyDTO \| null`                 |
| `uncertainty`                       | `EdgeUncertaintyDTO \| null`            |
| `evidence_sufficient`               | `bool`，复制 R                             |
| `sufficiency_reasons`               | `list[SufficiencyReason]`，复制 R          |
| `coverage`                          | `EdgeCoverageDTO`，必须存在                  |
| `worst_observation`                 | `FiniteReturn \| null`，来自 `R.tail_risk` |
| `worst_decile_mean`                 | `FiniteReturn \| null`，来自 `R.tail_risk` |
| `tail_sample_count`                 | `Count \| null`，复制 `R.tail_risk.k`      |
| `measurement_signature_state`       | `EXACT / NO_MEASUREMENT / MIXED`        |
| `measurement_signature`             | `MeasurementSignatureDTO \| null`       |
| `calculability`                     | 前述可空 Calculability                      |
| `source_type`                       | `R.population_key.source_type`          |
| `source_identity`                   | `R.population_key.source_identity`      |
| `as_of`                             | `R.as_of`                               |
| `aggregation_contract_version`      | 复制 R                                    |
| `uncertainty_method_version`        | 复制 R                                    |
| `rng_algorithm_version`             | 复制 R                                    |
| `visibility_mode`                   | `CURRENT_STABLE_SNAPSHOT`，校验后复制 R       |
| `audit_identity`                    | `AggregateAuditIdentityDTO`             |
| `manifest_provenance`               | `ManifestProvenanceDTO`                 |
| `limitations`                       | `list[string]`，原样复制 R                   |
| `unobservable_coverage_limitations` | `list[string]`，原样复制 R                   |
| `integrity_conflicts`               | 已接受 conflict token 列表                   |
| `integrity_statement`               | 原样复制 R                                  |
| `regime_gate`                       | 原样复制 R                                  |
| `regime_sufficiency`                | 原样复制 R                                  |

这里的 `R` 始终指**同一个实际 `AggregationResult` 实例**。现有结果类型已承载这些事实，Product adapter 不创建第二套事实来源。

### 9.3 Expectancy 与 uncertainty

`ExpectancyDTO`：

```
value: FiniteReturn                  ← R.statistics.mean
n_economic_samples: Count           ← R.statistics.n_economic_samples
unit: "DECIMAL_RETURN"
```

`0.01` 表示 `+1%`，不是 `1`。`R.statistics=None` 时整个 `expectancy=null`，不得用零值补齐，也不得以 raw COMPLETE count 重建经济样本数。

`EdgeUncertaintyDTO` 完整复制现有 interval 字段：

```
n_clusters: Count
n_resamples: Count
confidence_level: "TWO_SIDED_95"
lower_index: Count
upper_index: Count
lower: FiniteReturn | null
upper: FiniteReturn | null
unavailable_reason: TOO_FEW_CLUSTERS | DEGENERATE_SAMPLE | null
is_degenerate: bool | null
excludes_zero: bool | null
side: POSITIVE | NEGATIVE | null
seed_hex: string
rng_algorithm_version: string
```

整个 uncertainty 可以为 `null`；也可以对象存在但上下界为 `null`。这两种情形不得合并。

不新增“置信概率”，不修改 resample 数，不用近似算法替换现有 bootstrap 或 LOCO。上述字段与 nullable 行为以现有 `BootstrapInterval` 为准。

### 9.4 Coverage

`EdgeCoverageDTO` 必须包含：

```
eligible_opportunities: Count
not_yet_due: Count
mature_denominator: Count
complete: Count
insufficient_data: Count
invalid: Count
missing_outcome: Count

coverage_rate: finite number | null
settlement_rate: finite number | null

folded_evidence_revisions: Count
folded_outcome_revisions: Count
outcomes_excluded_with_folded_evidence: Count
integrity_conflict_count: Count

reference_status_counts: ReferenceStatusCountsDTO
lifecycle_counts: LifecycleCountsDTO
status_reason_counts: list[ReasonCountDTO]
measurement_signature_counts: list[MeasurementSignatureCountDTO]
```

固定计数对象：

```
ReferenceStatusCountsDTO:
  OK
  REFERENCE_MISSING
  REFERENCE_STALE

LifecycleCountsDTO:
  ACTIVE
  EXPIRED
  NULL
```

以上值均为 `Count`，零值不得省略。

动态词汇使用具体记录列表，不用任意 object：

```
ReasonCountDTO:
  reason_token: string
  count: Count

MeasurementSignatureCountDTO:
  signature_canonical_key: string
  signature: MeasurementSignatureDTO
  count: Count
```

`UNKNOWN_REASON:<raw value>` 必须保留原始 token，不重写成通用“其他”。

Measurement Signature 六字段为：

```
outcome_contract_version
calculator_version
cost_policy
cost_model_version
outcome_source_type
outcome_source_identity
```

计数直接来自 `R.coverage.measurement_signature_counts`；对应结构签名只能从**同一个 R 的 manifest**中进行无损身份查找，不能重新统计。

特别注意：当前 signature state 与 raw COMPLETE signature counts 的统计口径并不完全相同。不得强行规定 `EXACT` 必须只有一条 raw count，或 `NO_MEASUREMENT` 必须伴随空 count 列表；必须保留实际 R 的组合。

### 9.5 Manifest provenance 与 limitations

`ManifestProvenanceDTO`：

```
manifest_count: Count
ordered_manifest_ids: list[string]
manifest_counts: list[ManifestCountDTO]
max_manifest_concentration: finite number | null

ManifestCountDTO:
  source_manifest_id: string
  count: Count
```

这里只复制 `R.manifest`，不按 manifest 拆出新的聚合。

必须保留：

```
Positive Expectancy != Evidence Completeness Proven.

BEYOND_HORIZON_SERIAL_DEPENDENCE_UNMODELED
REGIME_IDENTITY_UNAVAILABLE
```

以及 R 中不可观测 coverage 的限制说明。不得把 Capture Anchor durable 之前的损失或 session-start fence 未准入机会编入可观测分母。 

---

## 10. Aggregate Audit Identity

### R-12：指标与审计身份必须同源

`AggregateAuditIdentityDTO`：

```
as_of: UtcTimestamp
input_fingerprint: string
aggregation_contract_version: string
selected_population_key: PopulationKeyDTO
horizon: ForwardHorizon
```

唯一合法映射：

```
audit.as_of                       = R.as_of
audit.input_fingerprint           = R.input_fingerprint
audit.aggregation_contract_version = R.aggregation_contract_version
audit.selected_population_key    = R.identity.population_key
audit.horizon                    = R.identity.horizon
```

必须验证：

```
R.identity.population_key == 实际选中的结构 PopulationKey
R.identity.horizon        == requested horizon
R.as_of                   == 当前 projection.as_of
```

不得拿另一次查询的 fingerprint、Python 当前时间或请求回显拼装 audit identity。没有实际 R 时，不生成假的 audit identity。

Public API 不暴露完整 `input_manifest`，也不新增 manifest 下载端点；这是投影边界，不是允许丢掉内部的 revision-aware manifest。

该约束直接保留已冻结 Amendment 的同结果绑定要求。

---

## 11. Stable Snapshot、Canonical Folding 与 Materialization

### R-13：读取模型

唯一合法读取模型：

```
Host-owned session factory
    ↓
REPEATABLE READ / READ ONLY
    ↓
SELECT statement_timestamp() → as_of
    ↓
完整可见 Evidence revision chains
完整 requested-horizon Outcome revision chains
    ↓
accepted rehydration / chain validation / canonical folding
    ↓
canonical cross-integrity validation
    ↓
revision-aware CurrentSnapshotProjection
    ↓
deep immutable materialization
    ↓
END TRANSACTION / SESSION RELEASED
```

禁止历史 `as_of` 参数，禁止按 `created_at` 模拟 revision 在历史时点的可见性。

### R-14：先 fold，后人口过滤

不得在 SQL 中先按 revision-mutable source 字段过滤，再把留下的 revision 当作完整链。

完整链验证、canonical-head selection 与缺失 Outcome 判定继续由现有 SE-02D 实现拥有：

```
fold_evidence_records()
fold_outcome_records()
validate_canonical_outcome()
CurrentSnapshotRevisionReader
```

不存在 canonical Outcome 时，不能回退到旧 Evidence 或旧 Outcome 的结果。当前 reader 的读取域是全部 Evidence 和该 horizon 的全部 Outcome；本候选不以“性能优化”为名缩小它的权威链读取域。  

### R-15：有界读取适配，不复制 reader 算法

当前 reader 使用 `.all()` 读取上述记录，本身没有 I04 的行数和字节预算。I04 不能直接复用后声称“已经有界”。

本候选选定的适配方式：

**新增 Product-owned `BoundedEdgeSnapshotReader`，继承现有 reader；只在同一个 transaction 的 `_read_in_session()` 中增加预算预检，再委托原有实现。**

预算预检必须先于 ORM 全量 materialization，在同一 RR snapshot 中取得：

```
Evidence row count
requested-horizon Outcome row count
两类行合计 UTF-8 JSON representation bytes
最大单行 UTF-8 JSON representation bytes
```

字节定义使用数据库端完整 row JSON 的 UTF-8 字节数，不使用字符串长度或只估算几个选定字段。

超限必须整次失败。不得读取前 N 行后给出不完整聚合；也不得用预检与正式读取之间的第二个 transaction 制造 TOCTOU。

### R-16：真正的 immutable handoff

现有 `CurrentSnapshotProjection` 是 frozen dataclass，但 `manifest` 内部仍包含字典。因此不得把浅层 frozen 当作完整的跨线程不可变证明。

在 transaction 结束前，必须将 manifest 无损深复制为只读 mappings 和 tuples，且不存在外部可写别名。

可以做与此直接相关的 `Mapping` 类型注解兼容调整，但不能改变任何字段、manifest 内容、folding 行为或 hashing 规则。现有 canonicalization 对 mappings 以及 list/tuple 的处理可支持这类无损冻结；验收仍必须证明冻结前后的 canonical bytes 完全一致。

### R-17：选择单个人口，不产生第二套编排

建议新增的唯一 Edge orchestration 公共适配 seam：

```
partition_projection(projection)
```

这是**待新增符号，不是当前已存在的函数**。

它必须委托现有 orchestration 中的 facts/manifest 一一对应检查、结构人口分组和 manifest subset 原语，只产生保留相同 `as_of/horizon` 的人口子 projection，不做统计。

选中人口的完整子 projection 再交给原有 `aggregate_projection()`。结果必须恰好为一个 R，并验证其身份。

禁止只调用 `filter_by_population_key()` 获取 facts，却遗漏对应 manifest；禁止重新调用不含 revision 扩展的 manifest builder 作为替代。

---

## 12. Full-query Admission 与 Bounded CPU Execution

### R-18：先限制整条查询，再接触 DB

已冻结 Amendment 要求 admission 在昂贵 DB 操作之前发生，而不只是限制最后的统计线程。

完整顺序固定为：

```
authenticate
→ bounded syntax validation
→ full-query admission
→ Host/context capability check
→ bounded stable DB snapshot
→ canonical folding / immutable materialization
→ END TRANSACTION / SESSION RELEASED
→ population discovery / selector validation
→ no selection: typed discovery response
  or
  selected population:
    CPU admission
    → thread offload
    → existing aggregate_projection()
    → exact result identity validation
    → typed DTO adaptation / serialization
→ release full-query admission
```

### R-19：资源预算候选

以下是本候选确定的 **V1 防护参数**，不是已经验证的容量、延迟 SLA 或统计门槛：

| 参数候选值                                    |                                 |
| ---------------------------------------- | ------------------------------- |
| 同时占用的 full-query permits                 | `2`                             |
| full-query 等待队列                          | `0`，立即接受或拒绝                     |
| 同时实际运行的 Edge CPU aggregate jobs          | `1`                             |
| CPU admission 等待者上限                      | `1`，由 full-query 上限共同保证         |
| CPU admission 等待超时                       | `5 seconds`                     |
| DB 读取阶段 deadline                         | `30 seconds`，不含无法瞬时完成的清理        |
| DB statement timeout                     | 本次只读 transaction 内 `30 seconds` |
| Evidence + requested-horizon Outcome 总行数 | `4096`                          |
| 两类记录合计 UTF-8 row-JSON bytes              | `16 MiB`                        |
| 单行 UTF-8 row-JSON bytes                  | `1 MiB`                         |
| 选中人口 canonical scopes 上限                 | `64`                            |
| 已物化 manifest canonical bytes             | `16 MiB`                        |
| 成功响应 UTF-8 JSON bytes                    | `4 MiB`                         |

`1 MiB = 1,048,576 bytes`。

`64 scopes` 是本候选的 CPU 输入防护上限，**不是最低样本数、统计充分性阈值或允许裁剪到的样本数量**。65 个 scopes 必须整次拒绝，不能取前 64 个。

这些限制也意味着较大人口可能返回 unavailable；不得在尚无测量证据时承诺可支持任意历史规模。提高预算必须经过明确的性能决策，不能由 Executor 自行放宽。

### R-20：实现机制

使用项目已经依赖的 AnyIO，不引入服务、分布式队列或新的 executor ownership。当前 production dependency 已包含 `anyio>=4.4,<5`。

确定机制：

```
Full-query:
共享的非阻塞 permit gate，容量 2。

CPU admission:
共享的容量 1 admission gate；
最多一个等待者；
只对 admission wait 应用 5 秒超时。

Thread dispatch:
anyio.to_thread.run_sync(
    existing aggregate_projection,
    immutable selected projection,
    limiter = Edge 专用 CapacityLimiter(1),
    abandon_on_cancel = False
)
```

Admission gate 与 thread limiter 是不同原语，不能在同一 borrower 上重复获取同一个 limiter 造成死锁。

协调对象只保存 Product 请求的 admission 状态，不拥有 DB engine、session factory、provider、RuntimeHost、任务守护服务或独立线程池。所有请求共享同一协调对象，禁止按请求创建 limiter。

### R-21：取消与真实完成

Python 工作线程不能因调用方取消就被认为已经停止；AnyIO 也明确区分“等待者取消”与“线程继续运行”。因此 `abandon_on_cancel=False` 只是实现基础，不是验收证明。[AnyIO](https://anyio.readthedocs.io/en/stable/threads.html)

必须满足：

| 取消发生点行为                |                                             |
| ---------------------- | ------------------------------------------- |
| full-query admission 前 | 不获取 DB、不派发 CPU                              |
| DB 阶段                  | 取消读取，完成 session/transaction 清理；不得启动 CPU     |
| CPU admission 等待中      | 移除等待者，清理后释放 full-query permit               |
| 已提交但尚未确认完成的 CPU job    | 保持 job 的明确所有权，不能通过取消 awaitable 假装结束         |
| CPU 实际运行中              | 保留 CPU 与 full-query 占用，等待真实线程完成，然后丢弃取消请求的结果 |
| DTO 阶段                 | 不发送半个成功结果；清理后结束                             |

每个已派发 job 必须有强引用、受 admission 上限约束的 completion ownership。请求取消时必须 shield/drain 该 job，不能让它变成无人持有的 fire-and-forget 工作。

必须同时测试 AnyIO cancellation 和原生 `asyncio.Task.cancel()`，包括重复取消。仅证明普通路径能退出，不足以验收。

本候选**不增加运行中纯聚合的硬中断 timeout**，不为满足 timeout 修改 bootstrap/LOCO 算法。CPU 等待超时与运行中取消必须是不同概念。

### R-22：释放与失败

只有在实际线程结束、DTO 成功或明确失败、DB/session 清理已完成后，才允许释放对应占用。

清理失败且无法证明资源已释放时，不得把该次占用标记为空闲并继续无限接纳新请求。必须保留未清理占用的事实并记录证据；I04 不执行自动 repair/recovery，也不取得新的进程重启权。

所有饱和或预算拒绝均为一次性失败，不在服务端自动循环重试。

---

## 13. State / Availability / Error Mapping

### R-23：四个维度独立

必须区分：

```
Aggregate business status
ProjectionState
OperationalAvailability
ReadFailureReason / HTTP
```

下表规定未来 I04 正式安装后的行为，不声称当前基线已经具有该端点。

| 情形AggregateProjectionStateOperationalAvailabilityHTTP / ReadFailureReason |    |                  |                 |                          |
| ------------------------------------------------------------------------- | -- | ---------------- | --------------- | ------------------------ |
| Host 未启用或不存在                                                              | 无  | `UNAVAILABLE`    | `NOT_ACTIVATED` | `200`，reason 为 `null`    |
| 完整可信读取，匹配人口为零                                                             | 无  | `EMPTY`          | `ACTIVE`        | `200`，reason 为 `null`    |
| 多个人口，需要选择                                                                 | 无  | `FRESH`          | `ACTIVE`        | `200`，reason 为 `null`    |
| 返回实际 `VALID` R                                                            | 原样 | `FRESH`          | `ACTIVE`        | `200`                    |
| 返回实际 `NOT_CALCULABLE` R                                                   | 原样 | `FRESH`          | `ACTIVE`        | `200`                    |
| 返回实际 `INCOMPATIBLE_MEASUREMENT_SIGNATURES` R                              | 原样 | `FRESH`          | `ACTIVE`        | `200`                    |
| 返回实际 `INTEGRITY_CONFLICT` R                                               | 原样 | `FRESH`          | `ACTIVE`        | `200`                    |
| 返回实际 `NOT_APPLICABLE` R                                                   | 原样 | `FRESH`          | `ACTIVE`        | `200`                    |
| 已激活 Host 不能提供可用 session/source                                            | 无  | 逻辑上 unavailable  | 不据故障伪造未激活状态     | `503 SOURCE_UNAVAILABLE` |
| DB 连接、获取、网络或读取 timeout                                                    | 无  | 逻辑上 unavailable  | 不改写业务激活事实       | `503 SOURCE_UNAVAILABLE` |
| admission 饱和、预算超限、CPU admission timeout                                   | 无  | 逻辑上 unavailable  | 不改写业务激活事实       | `503 SOURCE_UNAVAILABLE` |
| revision/cross-integrity/facts–manifest 失败，无法形成可信 projection              | 无  | 逻辑上 unavailable  | 不改写业务激活事实       | `503 SNAPSHOT_FAILED`    |
| 参数、selector、cursor 无效                                                     | 无  | 不生成成功 projection | 不改变             | `422`                    |
| 认证失败                                                                      | 无  | 不生成成功 projection | 不改变             | 现有 `401`                 |
| 未分类程序异常、意外 CPU 异常或 DTO 适配错误                                               | 无  | 不生成成功 projection | 不改变             | sanitized `500`          |

\*\*现有共享 503 DTO 不含 ProjectionState 或 OperationalAvailability 字段。\*\*表中的“逻辑上 unavailable”不能被误认为需要向共享错误体偷偷添加字段。 

### R-24：不能混淆的具体情形

`INSUFFICIENT_DATA` 进入 coverage；最终 aggregate status 由 SE-02D 决定。

实际 R 的 `INTEGRITY_CONFLICT` 可以是 HTTP 200 的业务证据；而 `SnapshotIntegrityError` 导致根本没有可信 R，不能伪造一个同名 aggregate status 来维持 200。

`FRESH` 在本端点表示本次 current-snapshot 投影已完成，不证明市场 feed 实时、新 Outcome 正在自动生产或交易已激活。

`EMPTY` 必须来自可用来源上的成功完整读取。数据库读不到、Forward 来源不可用或预算拒绝，均不得变成 EMPTY。

共享状态中的 `STALE`、`CAPABILITY_NOT_INTEGRATED` 保留其含义，但本候选不增加缓存、TTL 或新的 integration flag 来主动产生它们。完整 I04 安装不以“缺少数据”推断未接线；缺少必要路由接线属于集成验收失败，不应靠伪状态掩盖。

### R-25：成功时间字段

有数据 snapshot 时：

```
meta.snapshot_at = data.as_of = projection.as_of
aggregate.as_of  = R.as_of
```

`meta.observed_at` 在缺少独立定义的 observation-time authority 时为 `null`，不得拿响应生成时间冒充市场观察时间。

`operational_context.context_snapshot_at` 是独立的当前 Host context 采样时间，不能宣称与 PostgreSQL 构成 global ACID snapshot。

Host 不存在时，允许 envelope 的 `snapshot_at` 使用响应 context 时间，但必须 `data=null`，不得伪造 DB `as_of` 或 aggregate audit。

### R-26：错误体

`503` 复用 `ProductUnavailableResponse`：

```
projection = "EdgeAggregateRead"
contract_version = PRODUCT_READ_CONTRACT_VERSION
read_surface_class = "A"
read_failure_reason = SOURCE_UNAVAILABLE | SNAPSHOT_FAILED
correlation_id
```

`500` 复用：

```
ProductInternalErrorResponse:
  correlation_id
```

`401` 复用现有认证体。`422` 使用具体 validation issue 类型，只提供受控的 query location、类型和错误说明，不回显原始异常、完整 token、数据库信息或任意 payload。

不新增 `CPU_BUSY` 等 `ReadFailureReason` 枚举；饱和、预算和 timeout 的细分类别记录在服务端安全诊断中，不改变冻结的公共 reason 集合。

---

## 14. Authentication、Provenance 与 Authority

### R-27：认证边界

复用 `marketpulse.api.auth.verify_session`。未认证请求不得进入人口发现、DB snapshot 或 CPU job 路径。Host 禁用时也不能绕过认证。

Population selector 和 cursor 均不能替代 session authentication。

### R-28：Forward/Replay 隔离

SQL 全链读取可以为 canonical validation 接触共享数据库中的不同 provenance，但**人口筛选、目录输出和实际 CPU 计算**必须遵守显式请求来源。

默认 Forward 请求不得输出或计算 Replay aggregate。Forward 失败不能重试 Replay；Replay 只能标为明确的 research/historical evidence，不能被包装成 current operational truth。

完整读取返回零个 durable population，只证明本次查询域内没有人口，不证明市场没有机会，也不证明 Forward 自动生产链路健康。

### R-29：只读能力不外溢

I04 不调用 activation、repair、recovery、risk admission、execution、Gate C 或 Live 控制方法。

`ProductReadContext` 继续只是 Host 能力的非 owning borrower。数据库的创建和释放权仍属于现有 `DatabaseResources`/RuntimeHost 所有者；请求不得创建新 engine 或 dispose Host engine。 

---

## 15. Reuse Decisions 与未来修改边界

下表中的“新增/适配”仅为未来实现要求，不是本轮修改授权。

| 分类精确文件 / 符号决定 |                                                                                                     |                                                        |
| ------------- | --------------------------------------------------------------------------------------------------- | ------------------------------------------------------ |
| KEEP          | `backend/src/marketpulse/edge/aggregation.py::aggregate`、`AggregationResult`、`PopulationKey`、相关结果类型 | 数学与业务语义零修改                                             |
| KEEP          | `.../edge/aggregation_snapshot.py::CurrentSnapshotRevisionReader`                                   | 继续拥有同一 snapshot 的读取和 folding                           |
| KEEP          | 同文件 `fold_evidence_records`、`fold_outcome_records`、`validate_canonical_outcome`                     | 不复制算法                                                  |
| KEEP          | `.../edge/aggregation_orchestration.py::aggregate_projection`                                       | 唯一 Product CPU 聚合调用                                    |
| ADAPT         | 同文件新增 `partition_projection`                                                                        | 仅委托既有验证、分组、manifest subset 原语                          |
| ADAPT         | `CurrentSnapshotProjection.manifest` 的只读 Mapping 兼容注解                                               | 仅支持无损 deep-freeze；保持现有行为                               |
| KEEP          | `.../edge/hashing.py::canonical_bytes`                                                              | identity、selector MAC 材料等复用 canonical boundary         |
| KEEP          | `.../api/product/context.py::ProductReadContext`                                                    | 借用 Host-owned session factory                          |
| KEEP          | `.../api/product/models.py` 的共享 meta/context/error DTO                                              | 不另造通用状态模型                                              |
| KEEP          | `.../api/auth.py::verify_session`                                                                   | 不改变认证协议                                                |
| KEEP          | `.../db/session.py::DatabaseResources`                                                              | 不改变 ownership                                          |
| ADAPT         | `.../api/product/system.py`                                                                         | 按现有方式注册 I04 router                                     |
| ADAPT         | `.../api/app.py::create_app`                                                                        | 仅安装共享、无运行资源所有权的 admission 对象；不修改 Host lifecycle        |
| NEW           | `.../api/product/edge_aggregates.py`                                                                | route、Product read service、bounded reader/admission 适配 |
| NEW           | `.../api/product/edge_aggregate_models.py`                                                          | 具体 DTO                                                 |
| NEW           | `.../api/product/edge_population_cursor.py`                                                         | 本端点 selector/cursor；不改变其他端点 cursor                     |
| KEEP          | `frontend/src/api/transport.ts::requestData`                                                        | 保留唯一通用 transport 解释路径                                  |
| REGENERATE    | `frontend/src/api/generated.ts`                                                                     | 从 OpenAPI 生成，禁止手工补类型                                   |

现有 Product 注册方式、共享 DTO、transport 和类型生成脚本均已核对。`requestData()` 对普通 `503` 返回 `HttpError`，不能为 Edge 偷增 `/ready` 式例外。  

本候选不允许修改 authentication policy、session secret lifecycle、RuntimeHost authority、`aggregation.py` 数学、schema 或索引。若上述最小适配无法保持这些边界，必须回到设计门，而不是由 Executor 改架构。

---

## 16. OpenAPI / generated.ts Acceptance Boundary

### R-30：同一验收单元完成

未来 I04 验收必须同时包含：

```
Backend endpoint
Typed request/response/error schemas
OpenAPI
frontend/src/api/generated.ts regeneration
npm run generate:api
npm run check:api-drift
TypeScript regression
Transport regression
```

OpenAPI 必须准确声明：

```
200
401
422
503 ProductUnavailableResponse
500 ProductInternalErrorResponse
```

接口必须能在既有离线 OpenAPI export 路径中导出，不得要求启动真实 Host 或连接数据库才能生成类型。现有生成脚本就是从 FastAPI application object 导出，而非从运行中的服务器抓取。

前端验收不实现 Edge Lab 页面，但必须证明生成类型能够表达：

```
null aggregate
selection required
exact population key
business status
nullable uncertainty
coverage
audit identity
503/500 error contracts
```

不得以 `any`、`unknown as` 或手写备用类型绕过缺失 schema。

---

## 17. Verification Contract

### 17.1 验证身份

```
Verification Profile Candidate:
UI-RD01-I04-VP-v0.1

Current Profile Status:
CANDIDATE / NOT FROZEN

Official Verification:
NOT RUN IN THIS DESIGN TASK
```

未来正式证据必须绑定实现 Candidate SHA、冻结需求身份、Verification Profile 版本、测试资产身份，以及 Python、依赖、数据库、Node/npm 和运行环境身份。

Executor 自检不替代正式验证；SQLite 或 mock 通过不能替代 PostgreSQL MVCC 证明。该区分保留当前治理的 verification/acceptance 规则。

### 17.2 必需测试集合

| ID验证场景必须证明 |                                                |                                                                           |
| ---------- | ---------------------------------------------- | ------------------------------------------------------------------------- |
| V01        | 默认请求                                           | `5m + FORWARD_PAPER`；无 Replay fallback                                    |
| V02        | 零人口                                            | 完整读取后 `200 EMPTY`，aggregate/audit 不伪造                                     |
| V03        | 唯一人口                                           | 自动选择唯一完整匹配                                                                |
| V04        | 多人口与分页                                         | 不选“第一名”；当前页一项不能触发错误自动选择                                                   |
| V05        | 显式选择                                           | 选中人口不受目录分页裁剪，完整参与聚合                                                       |
| V06        | selector 格式、版本、MAC、成员关系                        | 非法、篡改、已消失和跨来源 selector 均按合同拒绝                                             |
| V07        | secret 轮换                                      | selector 可失效，但结构人口和固定输入下的数学结果不变                                           |
| V08        | cursor                                         | filter/horizon/source/selection/limit/catalog 绑定；tamper 和 stale cursor 拒绝 |
| V09        | Replay identity 缺失                             | 需要 identity 时返回 `422`，不代选来源                                               |
| V10        | 显式 Replay                                      | 只计算匹配 Replay 人口，保持历史 provenance                                           |
| V11        | Forward source failure                         | `503`，不得返回 EMPTY 或 Replay 数据                                              |
| V12        | Evidence revision correction                   | 完整链先 fold；旧人口不被复活                                                         |
| V13        | Outcome correction / missing Outcome           | 不回退旧 head；missing 与 not-yet-due 分开                                        |
| V14        | 跨 horizon / 跨人口污染                              | 拒绝 foreign facts；分母、manifest 与指标不混合                                       |
| V15        | Mixed signatures                               | 复制 core fail-closed status；coverage 保留                                    |
| V16        | 坏 COMPLETE return                              | raw COMPLETE count 保留；actual R 的业务冲突为 `200`                               |
| V17        | reader / projection integrity failure          | 无可信 R 时返回 `503 SNAPSHOT_FAILED`，不伪造业务结果                                   |
| V18        | insufficient / not calculable / not applicable | 保留实际 status、null、coverage、reasons                                         |
| V19        | signature state 与 raw counts 差异                | 不把不同口径强行“修正”为一致                                                           |
| V20        | Audit 同结果绑定                                    | 混入另一 R 的 key/horizon/as_of/fingerprint 必须被检测                              |
| V21        | 深不可变 handoff                                   | 嵌套结构不可写；无可写别名；canonical bytes 不变                                          |
| V22        | full-query admission                           | 第三个并发请求在创建 DB session 前被拒绝                                                |
| V23        | CPU admission                                  | 实际运行最多 1，等待最多 1；等待 timeout 不启动 job                                        |
| V24        | DB/CPU 分界                                      | CPU 开始前 transaction/session 已结束；worker 无 DB/Host/provider handle          |
| V25        | 各阶段取消                                          | AnyIO、原生 Task.cancel 和重复取消均不提前释放实际占用                                      |
| V26        | CPU 已运行时取消                                     | 测试线程被阻塞期间仍占用名额；真实结束后才清理                                                   |
| V27        | 资源预算边界                                         | 每项 limit、limit+1；超限无 partial aggregate                                    |
| V28        | CPU/DTO 意外异常                                   | `500` correlation-only；无异常内容泄漏                                            |
| V29        | Host 未启用 / 认证失败                                | NOT_ACTIVATED 与 source failure 分离；认证边界不绕过                                 |
| V30        | 真实 PostgreSQL snapshot                         | isolation/read-only、并发 late corrections、DB `as_of`、无写入                    |
| V31        | 数学回归                                           | 原有 SE-02D golden、permutation、coverage、bootstrap、LOCO、tail 用例保持            |
| V32        | OpenAPI / TS / transport                       | 类型生成无漂移；业务状态是正常 200；Edge 503 仍是普通 HttpError                               |

并发与取消测试必须使用可控制的 barrier/event 来证明先后关系，不能只通过 `sleep()` 后看一次计数推断正确。

### 17.3 已确认的回归入口

现有 SE-02D 回归文件：

```
backend/tests/test_se_02d_aggregation.py
backend/tests/test_se_02d_aggregation_snapshot.py
backend/tests/test_se_02d_aggregation_orchestration.py
```

其中现有测试已经包含 RNG golden vector 和 PostgreSQL snapshot 顺序场景；未来 I04 必须保留并扩展，而不是以新的 mock-only 测试替换。 

建议新增：

```
backend/tests/test_product_edge_aggregates.py
```

前端至少执行现有脚本：

```
npm run generate:api
npm run check:api-drift
npm run typecheck
npm run test:run
npm run build
```

这些脚本名称已在当前 `frontend/package.json` 中核验。本轮没有执行它们。

---

## 18. Performance Evidence Contract

### 18.1 必须记录的观测量

| 阶段必需证据         |                                                                      |
| -------------- | -------------------------------------------------------------------- |
| DB acquisition | 获取 session/connection 的等待时间与结果                                       |
| DB queries     | SQL statement 数量；控制语句、预算预检、正式数据 SELECT 分开计数                          |
| DB transaction | 开始、snapshot 建立、读取完成、实际结束时间                                           |
| Input size     | Evidence/Outcome rows、canonical scopes、manifest bytes、response bytes |
| Folding        | Evidence fold、Outcome fold、cross-validation/materialization 耗时       |
| CPU            | admission wait、worker 实际起止、pure aggregation 耗时                       |
| Adapter        | DTO validation 与序列化耗时                                                |
| End-to-end     | 成功、拒绝、timeout、取消各自的总耗时                                               |
| Concurrency    | full-query occupied、CPU running、CPU waiting 的 peak                   |
| Memory         | 测量环境中的 peak memory 与基线增量，不把 row-JSON bytes 冒充 RSS 上限                 |

Folding 的细分测量可以由隔离验证 harness 包装现有函数取得，但不能修改数学行为或将生产 API 变成调试接口。

### 18.2 工作负载

必须覆盖：

```
空数据库
单人口、单 scope
多个来源与多个 populations
低 overlap 与高 overlap
接近 4096 raw rows 的完整 revision chains
64 selected canonical scopes
各字节预算边界
同一 selected population 的并发请求
一个运行、一个等待、第三个拒绝
取消后的实际线程仍在运行
```

预算测试与数学测试须分开。测试预算可以使用受控 worker，但至少一组上界以内的性能证据必须运行真实 `aggregate_projection()`。

### 18.3 查询计划与 schema 边界

必须对预算查询和现有正式数据查询取得可审查的 `EXPLAIN`、duration、row count 证据，说明目录分页没有被误用为聚合样本分页。

当前默认边界：

```
Schema = ZERO CHANGE
Migration = ZERO CHANGE
Index = ZERO CHANGE
```

发现性能不足时，先报告证据及不满足之处，再进入独立性能决策。禁止以“否则测试太慢”为由降低 bootstrap 次数、略过 LOCO、增加索引或更换聚合引擎。

本候选不定义新的响应延迟 SLA。资源保护 timeout 不是成功响应时限承诺。

---

## 19. Acceptance Criteria

| AC验收条件 |                                                       |
| ------ | ----------------------------------------------------- |
| AC-01  | 精确治理、产品与权威输入绑定成立；无未处理 drift                           |
| AC-02  | 七字段 Population Key 和单 horizon 身份完整保留                  |
| AC-03  | Forward/Replay 与 source identity 隔离，无隐式 fallback      |
| AC-04  | 唯一人口自动选择、多人口显式选择、目录分页语义确定                             |
| AC-05  | selector/cursor 的版本、完整性、绑定、失效语义全部实现                   |
| AC-06  | 公开 DTO 全部具体类型，无任意 payload / ORM 暴露                    |
| AC-07  | 指标、coverage、uncertainty、sufficiency 与 audit 来自同一个实际 R |
| AC-08  | 完整链先 fold，missing Outcome 无历史 head 回退                 |
| AC-09  | snapshot 为 RR/RO，`as_of` 来自 DB，worker 无 DB 资源         |
| AC-10  | full-query 与 CPU 均有界，取消不造成“名额释放但线程仍运行”                |
| AC-11  | 所有预算超限整次失败，不裁剪聚合输入                                    |
| AC-12  | 业务状态、availability、projection state、HTTP failure 不混淆   |
| AC-13  | 现有 SE-02D 数学与 golden regression 保持                    |
| AC-14  | OpenAPI、generated.ts、TypeScript 和 transport 同单元验收     |
| AC-15  | 性能证据完整，未暗加 SLA、schema、index 或新 worker                 |
| AC-16  | 正式验证、必要独立评审、当前证据与适用治理门满足后，才能建立实现验收                    |

**本设计任务的完成不等于这些实现 AC 已经通过。**

---

## 20. Open Decisions / Blocking Issues / Remaining

### Open Decisions

```
Material implementation decisions delegated to Executor:
NONE
```

本候选已经选择了 DTO、query、selector/cursor、population selection、snapshot reuse、resource budget、CPU admission、取消、错误映射和验证边界。

这些决定仍可被独立评审要求修改，但 Executor 不得在实现时自行换方案。

### Blocking Issues

```
Governance/Input Drift:
NONE OBSERVED

Known missing authoritative product input:
NONE

Independent Design Review Blocking Findings:
NOT YET ASSESSED
```

不把“尚未评审”写成“零评审阻断”。

### Remaining

```
Independent Design Review:
REQUIRED

Candidate Freeze:
NOT PERFORMED

Implementation Authorization:
NOT GRANTED

Implementation Verification:
NOT RUN

Performance Capacity:
NOT YET MEASURED
```

特别需要评审关注：本候选的保守资源预算、bounded reader 适配面、selector 对既有 secret 的只读复用、跨取消模型的 completion ownership，以及只读 Mapping 兼容调整。它们已经作出候选决定，但尚未通过独立评审。

---

## 21. Recommended Independent Review Profile

```
Review Task:
UI-RD01-I04-DESIGN-R01

Review Role:
INDEPENDENT DESIGN REVIEWER

Mode:
STRICT READ_ONLY

Risk:
L2

Review Target:
UI-RD01-I04-Implementation-Requirements-v0.1
```

建议将评审分为两个互补检查面，但不以此擅自新增治理角色或改变风险等级：

| 检查面核心问题    |                                                                                            |
| ---------- | ------------------------------------------------------------------------------------------ |
| 契约与权威一致性   | 四份冻结输入是否保留；DTO/null/status 是否符合实际 R；selector 是否误成身份权威；是否新增统计或隐藏决策                          |
| 实现可行性与失败路径 | 全查询早期 admission 是否真实有界；读取预算能否在 materialization 前生效；取消/cleanup 是否保留实际占用；是否触碰 Host ownership |

评审必须读取候选全文和必要源代码，不能只审核本报告前面的 Result。

Reviewer 的模型、工具和运行配置由评审派发卡明确绑定，并确认具备相应任务审查能力；本候选不继承旧模型路由，也不代用户切换模型。

---

## 22. Next Legal Gate

```
UI-RD01-I04-DESIGN-R01
Independent Design Review
```

**本轮结束状态：治理重绑定通过，原 I04 需求候选已交付；未持久化，未冻结，未授权实现。**