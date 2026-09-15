# PRE-01B-D2｜AdvisoryIngress / G2→G3 Activation Contract

## Artifact Status

```text
Artifact: PRE-01B-D2 AdvisoryIngress / G2→G3 Activation Contract
Status: CANDIDATE DESIGN
Review: PENDING INDEPENDENT REVIEW
Human Acceptance: NOT PERFORMED
Task type: FORMAL DESIGN / REPOSITORY SOURCE AUDIT / DOCS ONLY
Implementation authorized by this artifact: NO
Runtime or provider activation authorized by this artifact: NO
```

本文件只冻结未来独立获批的 `PRE-01B-I2` 所需设计边界。它不实现、不迁移、不接通
live `G2→G3`、不构造真实 provider，也不授权 Gate A / Gate B / Live。

## 1. Repository Truth

### 1.1 Verified baseline

| 项 | 实时核验事实 |
|---|---|
| Global Protocol | `zwmhua2-lab2/ai-dev-protocol` |
| Protocol SHA | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| Protocol Version / Status | `1.1.0 / ACCEPTED` |
| Project repository | `zwmhua2-lab2/MarketPulse-AI` |
| Local `main` | `664207a9caba0c3f5c2589cfca2a10af24f89108` |
| Remote `origin/main`（fetch 后） | `664207a9caba0c3f5c2589cfca2a10af24f89108` |
| Task Base | `664207a9caba0c3f5c2589cfca2a10af24f89108` |
| Baseline drift | `NO` |
| Candidate branch | `design/pre-01b-d2-advisory-ingress-contract` |

根工作区位于 `prb-01-product-requirements-baseline@d47313a...` 且有大量既有修改。D2 在从
verified `main` 建立的独立 worktree 中完成；未 reset、stash、clean、rebase、覆盖或归因根工作区
内容。SHA Delta Check 证明该根工作区是另一条历史/在研分支，不是本 Task Base；D2 不继承其内容。

### 1.2 Accepted inputs

- `PRE-01A-D1` = `ACCEPTED / COMPLETE`，冻结 Real AI V1 placement、identity、experiment、
  deadline、failure 与 Gate A/B/C 边界。
- `PRE-01B-D1` = `ACCEPTED / COMPLETE`，冻结 `RuntimeHost` 唯一 composition owner、AnyIO
  structured concurrency、Protection isolation 与 shutdown 顺序，并明确 defer live `G2→G3`。
- `PRE-01B-I1` / Integrated Runtime Host Core V1 = `ACCEPTED / COMPLETE`。
- Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACCEPTED / NOT ACTIVE`。
- `SE-02D Production` = `IN PROGRESS`；它不阻塞 D2 或 Gate A，但 Gate C edge declaration 仍受其
  accepted expectancy evidence 约束。

### 1.3 Source facts that control this design

1. `PostgresG2Repository.persist()` 当前把 `MarketEvent`、timeline、`SymbolStateStore`、transition、
   candidates、observation 和 qualifying `edge_opportunity_evidence` 放在同一 PostgreSQL transaction。
2. qualifying Opportunity 要求：transition 为 `APPLIED`、目标与结果 state 均为 `SETUP`、event 为
   `BREAKOUT`、存在 expiry，且 `BREAKOUT_RETEST` bullish applicable candidate 的 identity/version 全部一致。
3. Forward Capture Anchor 先于 Formal G2 transaction durable；它可能在 recovery 中成为
   `UNVERIFIABLE_ORPHAN`。因此 Anchor 不是可调用 Advisory 的 authoritative Opportunity。
4. `edge_opportunity_evidence` 已持有 deterministic `opportunity_id`、`evidence_id`、revision、hash、
   feature snapshot hash、family/instrument/market/source identity、expiry 与 immutable payload。
5. 当前 `DecisionSnapshot` 不绑定 Opportunity/Evidence，也没有 payload hash、request time 或 absolute
   deadline；当前 `decision_id = hash(snapshot_id, model)` 不能满足 experiment/invocation collision fence。
6. 当前 `DecisionService` 在 provider 返回后才写 snapshot/decision，retry 没有 durable attempt、joint
   deadline/cost 或 winner transaction。
7. 当前 `G3Workflow.process_setup()` 在 `VALID + LONG_BIAS` 时创建并持久化 `TradePlan`。它不是
   Shadow-safe consumer。
8. 当前 `BoundedAITaskQueue.put()` 会等待 queue space，使用 process-local payload/time，没有
   post-commit admission、restart recovery、full rejection、deadline 或 durable dedupe contract。
9. 当前 `EdgeAttributionRecorder` 已能把 AI lineage 绑定 exact `opportunity_id/evidence_id`，且在 caller
   transaction 内 append-only/idempotent；该 identity 可复用，但不能替代 invocation/final-result authority。
10. I1 Host 的 safety lane 与 scanner lane 已隔离；`AI_AUXILIARY` 当前不属于 core readiness 的风险阻断
    authority。D2 必须保持这项性质。

## 2. Problem Statement

当前缺少的不是“再调用一次 G3”，而是一条能够证明下列性质的 live boundary：

```text
committed qualifying G2 SETUP / Opportunity
  -> durable invocation admission
  -> bounded Host-owned queue
  -> shadow-safe advisory invocation
  -> durable attempts
  -> exactly one durable final winner
```

任何 transient Scanner object、uncommitted row、ORM session-bound object、process callback identity 或
in-memory dedupe 都不能成为该链的 correctness authority。

## 3. Scope

- 精确冻结 qualifying Opportunity 的 producer 与 post-commit handoff。
- 冻结 Host-owned `AdvisoryIngress` 的 construction/start/task/queue/shutdown/health ownership。
- 冻结 immutable work reference、durable re-read、snapshot/input binding、invocation/attempt/final identity。
- 冻结 experiment/pair/arm binding、retry/deadline/cancellation、duplicate/late/winner fence。
- 冻结 bounded queue/full policy、staleness、restart、failure isolation、health/readiness。
- 冻结 Gate A Shadow 与 Gate B Paper Economic activation 的结构性分离。
- 审计并裁定现有 schema/components 的复用方式，提出最小未来 schema delta。
- 给出一个可独立获批的最小 I2 Implementation Batch 与 AC。

## 4. Out of Scope

- 任意 production code、test、migration、schema、config、runtime 或 DB 改动。
- 真实 provider/model 选择、constructor、API call、credential 或 provider runtime evidence。
- Gate A 启动、Gate B 启动、Live Trading、Short、自动 fallback、model voting。
- 修改 G2 state-machine/Scanner/Strategy business semantics。
- 修改 `TradePlanManager`、Risk、Execution、Accounting、Protection、Recovery、Reconciliation 语义。
- SE-02D 后续实现、aggregation、Gate C profitability/edge threshold。
- Position re-evaluation、generic workflow/event bus、microservice 或 process supervisor。

## 5. Accepted Invariants

1. `RuntimeHost` 是唯一 production composition owner；FastAPI lifespan 是唯一 Host activation boundary。
2. AI = Advisory；deterministic system = Authority。
3. Gate A 必须结构性地拥有 **ZERO** TradePlan/Risk/Execution/Position/Account/Ledger mutation capability。
4. Protection 与 risk-reducing path 不等待、不共享 queue/lock/task failure domain 给 Advisory。
5. PostgreSQL 是 durable correctness authority；queue、lock、set、TaskGroup 仅是进程内执行机制。
6. one `decision_invocation_id` -> exactly one collision-free logical durable final decision。
7. retry 共享 invocation/deadline/input/experiment/pair/arm/provider/model；每次 attempt 有独立 identity。
8. Single Primary Provider；no automatic fallback；no model voting；provider 不拥有本地 identity。
9. missing/stale/invalid/failure 均 fail closed，不能转成 baseline BUY 或伪装为 AI decision。
10. Paper only / SPOT LONG only；`SHORT_BIAS` 仅是分析/no-long。
11. Gate A、Gate B、Gate C 与 Live 是互不替代的独立授权边界。

## 6. Reuse Decisions

| 现有组件 | Verdict | 设计裁定 |
|---|---|---|
| `BoundedAITaskQueue` | `DO NOT USE IN GATE A` | 仅“bounded priority queue”概念可参考；其 blocking `put`、mutable payload、wall-clock enqueue time、无 full/restart/deadline/final fence 使其不能承载本契约。不得把 Position Review 与 Gate A setup 混队列。 |
| `DecisionService` | `ADAPT` | 复用 provider-neutral boundary、prompt/validator/redaction pieces；拆成 pre-call durable admission、attempt runner、finalizer。不得沿用 call-first/persist-later、legacy retry 或 legacy `decision_id`。 |
| `G3Workflow` | `DO NOT USE IN GATE A` | 它持有 `TradePlanManager`，并在 valid LONG path 调 `persist_trade_plan()`；直接复用会产生未授权经济前置事实。 |
| `DecisionSnapshotBuilder` | `ADAPT` | 改为从 exact formal Evidence + 同 transaction durable facts 构造 canonical immutable snapshot；增加 content hash 和完整 binding。不得以 caller mutable object/global market object 为 authority。 |
| `TradePlanManager` | `DO NOT USE IN GATE A` | Gate A consumer 不构造、不注入、不调用它。 |
| existing AI decision persistence | `REUSE WITH MINIMAL EXTENSION` | `decision_snapshots` 继续保存 frozen input；`ai_decisions` 继续保存唯一 logical final。新增 invocation linkage/hash fields；attempt/history 另用最小新表。 |
| `RuntimeHost` TaskGroup | `ADAPT` | Host 构造/启动/停止 Advisory；一个受控 wrapper child 可拥有内部 finite workers。Advisory exception 必须在 wrapper 内分类，普通/子系统故障不得取消 safety siblings。 |
| existing attribution identity | `REUSE` | exact `opportunity_id/evidence_id` lineage、append-only writer、caller-transaction pattern保持；payload 可增加 invocation/experiment facts，但 attribution 不是 winner authority。 |
| `PostgresG2Repository` formal transaction | `ADAPT` | 复用 G2+Evidence 原子提交；在 Gate A 配置显式启用时，同 transaction stage immutable snapshot + invocation。queue 只能在 commit 成功之后触达。 |

## 7. Architecture / Ownership

```text
RuntimeHost
  ├─ accepted safety lanes / scanner / G2
  └─ AdvisoryIngress (auxiliary, Host-owned)
       ├─ AdvisoryAdmissionWriter
       ├─ bounded in-process work queue
       ├─ finite attempt workers
       ├─ provider adapter (Gate A activation only)
       └─ durable finalizer / recovery scan

PostgreSQL
  ├─ G2 + edge_opportunity_evidence            existing authority
  ├─ decision_snapshots                        adapted immutable input
  ├─ advisory_decision_invocations             new durable admission/fence
  ├─ advisory_decision_attempts                 new attempt provenance
  └─ ai_decisions                              adapted one logical final
```

### 7.1 Ownership matrix

| Concern | Owner | Rule |
|---|---|---|
| construction | `RuntimeHost._compose_services` | config `DISABLED` 时不构造 provider/consumer；test 只能 inject fake。 |
| startup | `RuntimeHost` | Core recovery/readiness 后启动 Advisory recovery/wrapper；Advisory 不反向 gate Protection startup。 |
| task | Host AnyIO TaskGroup 中的 `AdvisoryIngress.run()` wrapper | wrapper owns nested finite workers；不自建 daemon/process/supervisor。 |
| queue | `AdvisoryIngress` | bounded、single-purpose、无外部 send handle。 |
| provider | `AdvisoryIngress` | adapter 只收到 frozen snapshot/prompt/request metadata，无 repository/risk/execution handles。 |
| shutdown | `RuntimeHost` | 第一步关闭 new advisory admission；随后 cancel queued/active work；不得延迟 safety cleanup。 |
| health | `AdvisoryIngress` 产出，Host 聚合 | Core readiness 与 Gate A readiness 分开。 |

## 8. Producer Boundary

### 8.1 Exact qualifying record

唯一 producer input 是已经满足 accepted `qualifies()` 规则、将要写成
`EdgeOpportunityEvidenceRecord` 的 formal Evidence revision。以下均不是 producer input：

- `StrategyCandidate` 单独存在；
- Capture Anchor；
- `SignalTimelineEvent` 单独存在；
- process-local `SETUP` state；
- callback 自造的 symbol/time identity。

### 8.2 Exact transaction and enqueue timing

未来 I2 必须把当前 bool-only persist result 最小扩展为 typed result。流程固定为：

1. `PostgresG2Repository.persist()` 在现有 G2 formal transaction 中写 G2 facts 与 exact Evidence revision。
2. 仅当 Gate A Shadow config 完整且显式启用时，injected `AdvisoryAdmissionWriter` 在**同一 transaction**：
   - 使用该 exact `EvidenceRevision` 与同 transaction 的 resulting SETUP/state facts；
   - 构造 deterministic snapshot/input/experiment/pair/arm/invocation identity；
   - 写 `decision_snapshots` 与 `advisory_decision_invocations(state=ADMITTED)`；
   - 不调用 provider、不触达 queue、不写 `ai_decisions` final、不写任何 TradePlan/economic table。
3. `session.begin()` 正常退出后，transaction 才算 committed。`persist()` 此时才返回 frozen
   `AdvisoryWorkRef`。
4. `EventRuntime` 只有在 `persisted=true` 且拿到该 ref 后，调用 Host-owned
   `AdvisoryIngress.post_commit_offer(ref)`。
5. `post_commit_offer` 使用 non-blocking `put_nowait`/equivalent；consumer 只收到 ref。

**Rollback proof**：步骤 2 的任一错误会回滚 G2 facts、Evidence、snapshot、invocation；步骤 4 永远不会
执行，因此不存在 queue 已看见但 DB 不存在的 phantom Opportunity。Capture Anchor 可能仍按 accepted
contract durable，但它没有 formal Evidence/invocation，Advisory recovery 必须忽略它。

**Crash-gap proof**：commit 成功而进程在 enqueue 前死亡时，`ADMITTED` invocation 已 durable。restart scan
会恢复同一 invocation；绝不创建“全新 decision”。

### 8.3 Critical staging failure

Gate A active 时，snapshot/invocation persistence 属关键 provenance infrastructure。其失败必须：

- 回滚该 formal admission transaction；
- 关闭新的 advisory admission、标记 Advisory `FAIL_CLOSED`；
- 绝不调用 provider；
- 不传播为 safety/protection sibling cancellation；
- 不伪装成 ordinary provider failure。

Gate A `DISABLED` 时 writer 不注入，现有 G2 persistence 行为保持不变。

## 9. Consumer Boundary / Shadow Safety Boundary

Gate A consumer 是新的最小 `ShadowAdvisoryDecisionPath`，不是第二套 G3。它只拥有：

- read-only loading of invocation/snapshot/evidence/state facts；
- provider adapter；
- deterministic validator；
- attempt writer、finalizer 与 attribution append writer。

它在 constructor/type boundary 上**不得拥有**：

- `TradePlanManager`；
- `persist_trade_plan` callable；
- `SystemRiskGate`；
- `PaperExecutionService`；
- Position/Account/Ledger/Protection mutation repository；
- `G3Workflow`。

允许写入的 table allow-list 仅为：

```text
advisory_decision_invocations
advisory_decision_attempts
decision_snapshots
ai_decisions
edge_attribution_events (AI lineage only)
```

Gate A tests 必须监视并证明 `trade_plans`、scenarios、intents、orders、fills、positions、trades、accounts、
ledger、outbox economic events 全部零新增/零修改。不能用“后面的 Risk 会挡住”作为安全证明。

## 10. Work Object / Durable Re-read

Queue 中唯一允许的对象：

```text
AdvisoryWorkRef {
  decision_invocation_id,
  decision_deadline_at
}
```

它必须是 frozen value object，不包含 ORM instance/session、provider object、mutable snapshot、global market
reference 或 callback identity。

dequeue 后 consumer 必须从 PostgreSQL 重读并交叉校验：

- invocation row 与唯一 snapshot row；
- exact `edge_opportunity_evidence` row；
- opportunity/evidence revision/hash、family、instrument、market、expiry；
- snapshot payload hash/input binding digest；
- current durable `symbol_states.state_version/state`；
- experiment/pair/arm/provider/model/prompt/schema/treatment identity；
- current final existence 与 attempt budget。

可直接消费而无需重新查询 transient market state的仅是已持久化、hash-verified 的 immutable snapshot
payload。consumer 不得用“现在的 latest BBO”悄悄替换原 snapshot；若需要新 input，必须形成新的 binding、
pair/invocation，而不是改写旧 snapshot。

## 11. Identity Model

### 11.1 Construction order

所有 hash 使用 versioned canonical JSON（sorted keys、UTC timestamps、finite numeric policy），禁止 Python
`repr()`、process hash 或 provider response 参与 identity。

1. `snapshot_payload_hash = H(snapshot_contract_version, canonical_snapshot_payload)`。
2. `snapshot_id = H("advisory-snapshot-v1", opportunity_id, evidence_id,
   snapshot_payload_hash)`。
3. `input_binding_digest = H(binding_version, opportunity_id, evidence_id,
   evidence_revision, evidence_hash, snapshot_id, snapshot_payload_hash, state_version,
   config_version, family_id/version, instrument_id, market_type,
   decision_requested_at, decision_deadline_at)`。
4. `experiment_id = H(experiment_definition_version, canonical_experiment_definition)`。
5. `pair_id = H("pre01a-pair-v1", experiment_id, input_binding_digest)`。
6. `baseline_arm_id = H(pair_id, "WITHOUT_AI_BASELINE")`。
7. `treatment_arm_id = H(pair_id, "REAL_AI_TREATMENT")`。
8. `decision_invocation_id = H("advisory-invocation-v1", experiment_id, pair_id,
   treatment_arm_id, input_binding_digest, prompt_version, schema_version,
   treatment_version, configured_provider_id, configured_model_id)`。
9. `attempt_id = H("advisory-attempt-v1", decision_invocation_id, attempt_number)`。
10. `decision_id = H("advisory-final-v1", decision_invocation_id)`；它与 winner attempt 无关，因此 terminal
    failure 与 valid winner 仍共享同一 logical final identity。

### 11.2 Authority and idempotency

- `AdvisoryAdmissionWriter` 创建 invocation identity；provider/model 只被记录，不能回写 identity。
- same immutable facts 重试/重放得到同一 invocation；相同 hash 为 idempotent，不同 content 为 invariant
  conflict 并 fail closed。
- retry 只增加 attempt row，绝不增加 invocation/final identity。
- provider request/response ID（若有）记录在 attempt；不存在时为 `NULL/UNKNOWN`，不得伪造。

## 12. Experiment / Pair / Arm Binding

### 12.1 Experiment authority

Host startup config 必须提供完整 canonical experiment definition，并由 deterministic code 验证
`experiment_id`。definition 至少冻结：placement、baseline policy/version、treatment version、exact configured
provider/model、prompt/schema/input-binding/snapshot versions、retry/deadline/cost policy values/versions、
horizons/metrics definition、activation level。

Host config 在一个 process lifetime 内 immutable。旧 invocation 自包含完整 binding/digest；restart 恢复它时
不使用新 config 重配 pair/arm/model。若 config/definition 变化，必须产生新 `experiment_id`。

### 12.2 One Opportunity, one explicit binding

- 每个 exact Evidence revision 在一个 experiment 中至多一个 `REAL_AI_TREATMENT` invocation。
- `pair_id` 在 provider call 前、outcome 前冻结。
- baseline arm 固定为 `ALL_ELIGIBLE_LONG_SHADOW_V1 / WITHOUT_AI_BASELINE`；同一 invocation row 必须持久化
  `baseline_policy_version` 与 deterministic `baseline_participation=PARTICIPATE_LONG`，使 baseline arm 不是
  事后推导的隐式标签。它不调用 provider、不产生 TradePlan，且不在 AI failure 时升级为 fallback。
- treatment arm 固定为 `REAL_AI_TREATMENT`。
- arm 不得由 response、confidence、盈利结果、retry outcome 或 latency 事后选择。
- baseline result 的未来聚合可引用同一 pair/Opportunity 的 accepted SE-02C outcome；I2 不复制 Outcome
  calculator，也不创建第二套 execution account。

## 13. Persistence / Transaction Contract

### 13.1 Invocation lifecycle

```text
ADMITTED -> QUEUED -> ACTIVE -> RETRY_PENDING -> ACTIVE -> FINAL
ADMITTED/QUEUED/ACTIVE/RETRY_PENDING -> FINAL (failure/cancel/stale/expired)
```

状态是 durable execution state，不是新的 `DecisionStatus`。`ai_decisions.status` 继续使用 accepted
`DecisionStatus` vocabulary；细节写 versioned `error_category`。

### 13.2 Attempt start

consumer 在 provider call **之前**用 transaction：

1. lock invocation `FOR UPDATE`；
2. 若 final 已存在，直接 fence，不调用 provider；
3. 重验 deadline/stale/activation/budget；
4. 插入 exact next attempt row（`STARTED`）并把 invocation 置 `ACTIVE`；
5. commit；
6. provider call 才可开始。

这证明任何真实 provider call 都有先行 durable attempt provenance。

### 13.3 Winner atomicity

provider completion 的 finalizer 必须在一个 PostgreSQL transaction 中：

1. durable 更新该 attempt 的 response/error/usage/timestamps/validation/late facts；
2. `SELECT ... FOR UPDATE` invocation；
3. 查询 `ai_decisions.decision_invocation_id` 是否已有 final；
4. 依固定顺序执行 duplicate -> deadline -> binding/stale -> provider/schema -> business validation；
5. 若 retryable 且 budget/deadline 仍允许，只置 `RETRY_PENDING`，不写 final；
6. 否则插入唯一 `ai_decisions` final、append AI attribution、把 invocation 置 `FINAL` 并绑定
   `decision_id`；
7. commit。

`ai_decisions.decision_invocation_id` 的 unique constraint + invocation row lock 是 durable winner fence。
两个 concurrent completion、retry/shutdown/restart race 中只有一个 transaction 能插入 final。loser attempt
可写 `DUPLICATE_SUPPRESSED`/`LATE_RESULT` audit，绝不能改写 winner。

Python lock、queue dedupe、TaskGroup 和 in-memory set 均不参与 winner correctness。

## 14. Queue / Backpressure Contract

| 项 | 冻结策略 |
|---|---|
| owner | one `AdvisoryIngress` per `RuntimeHost` |
| capacity | positive finite explicit config；unset 时 activation disabled |
| item | frozen `AdvisoryWorkRef` only |
| ordering | `(decision_requested_at, decision_invocation_id)` ascending；无 response-based priority |
| priorities | Gate A 只有 `NEW_SETUP` 一类；不得与 Position/Plan Review 混合 |
| enqueue | post-commit `put_nowait` / equivalent；绝不 await queue space |
| full policy | **REJECT NEWEST**；不 DROP accepted item、不 COALESCE、不阻塞 producer |
| full durable result | same invocation 原子 terminalize；`DecisionStatus.INVALID_SCHEMA` + diagnostic `ADVISORY_QUEUE_REJECTED`；zero provider call |
| accepted item | 一旦 queue 接受，不 silent drop；consumer/finalizer 或 restart 必须给出 durable terminal state |
| shutdown | close admission，cancel/finalize queued/active；不等待新 slot |

选择 REJECT 的理由：Opportunity/pair/invocation uniqueness 必须保留；coalesce 会把两个 Opportunity 合并，
drop 会删除实验 denominator，blocking 会反压 scanner/provider。rejection 仍保留 exact invocation/pair audit。

queue full handling 的 durable terminal transaction 若因 DB failure 未提交，invocation 保持 `ADMITTED`；这不是
已完成的 rejection。Advisory 立即 fail closed，restart 按 durable state 恢复并在原 deadline 下重新裁决。

## 15. Deadline Contract

- `decision_requested_at` 固定为 formal Evidence 的 durable `created_at`（当前等于 triggering event 的
  accepted receive time），不是 dequeue/restart/provider-call 时间。
- `decision_deadline_at = decision_requested_at + explicitly_configured_absolute_budget`，在 attempt 1 前且与
  snapshot/invocation 同 transaction durable。
- duration 未配置时，Gate A 不能 active；I2 可实现 disabled path/test injection，不得给 production 猜默认值。
- producer、queue ref、consumer、每次 attempt 与 finalizer传递/重读同一 UTC absolute deadline。
- per-attempt timeout 取 `min(configured_per_attempt_timeout, remaining_absolute_time)`；不得延长 deadline。
- retry 共享 deadline；conservative remaining-time/cost/attempt check 不通过则不启动。
- enqueue/dequeue/before-call 已过期：zero provider call，terminal `STALE_DECISION + DEADLINE_EXPIRED`。
- provider 返回时已过期：attempt audit 可以保留；不能成为 valid winner。

## 16. Retry / Failure Matrix

| Failure class | Retry? | Final status / diagnostic | Durable provenance | Risk effect |
|---|---|---|---|---|
| transport retryable | 仅显式分类、attempt/deadline/cost budget 均允许 | exhaustion 时 `INVALID_SCHEMA / TRANSPORT_FAILURE + RETRY_EXHAUSTED` | every attempt | zero new risk |
| provider transient/server unavailable | 同上 | `INVALID_SCHEMA / PROVIDER_UNAVAILABLE` | every attempt | zero |
| rate limit | 仅 server/provider 明确 retryable 且 deadline 容纳；无无限 backoff | `INVALID_SCHEMA / RATE_LIMIT` | every attempt | zero |
| schema/partial/malformed repairable | validator 明确 repairable 时才允许 validation retry | `INVALID_SCHEMA / SCHEMA_FAILURE|PARTIAL_RESULT|MALFORMED_OUTPUT` | raw/normalized validation facts | zero |
| business validation repairable | 仅预先枚举的可修正格式/数值关系 | `INVALID_BUSINESS / exact reason` | full reasons | zero |
| unsupported/hallucinated evidence | NO | `INVALID_BUSINESS / UNSUPPORTED_EVIDENCE` | yes | zero |
| refusal | NO | `INVALID_SCHEMA / REFUSAL` | yes | zero |
| auth/permission | NO；subsystem Gate A fail closed | `INVALID_SCHEMA / AUTH_PERMISSION` | yes | zero |
| invalid request/schema capability/model | NO；activation config invalid | `INVALID_SCHEMA / INVALID_REQUEST` | yes | zero |
| deadline expiry | NO | `STALE_DECISION / DEADLINE_EXPIRED` | yes | zero |
| retry exhaustion | NO | 最后 failure status + `RETRY_EXHAUSTED` | all attempts | zero |
| cancellation | NO（restart 另按原 invocation/budget裁决） | `INVALID_SCHEMA / CANCELLED`，或 process-loss attempt audit | yes | zero |
| late result | NO | `STALE_DECISION / LATE_RESULT` 或 loser audit | yes | zero |
| duplicate completion | NO | winner 不变；`DUPLICATE_SUPPRESSED` | loser attempt yes | zero |
| internal invariant/hash/fence failure | NO；Advisory subsystem fail closed | 无 provider 或 terminal invariant failure；不得伪造 valid | sanitized durable evidence where possible | zero |
| queue rejected | NO | `INVALID_SCHEMA / ADVISORY_QUEUE_REJECTED` | invocation/final yes | zero |

无任何 failure 会触发 baseline BUY、自动 participate、TradePlan fallback 或“像 AI 一样”的 deterministic fake。

## 17. Stale Opportunity Matrix

四类 freshness/validity 独立判断，不能折成一个 boolean：

| 维度 | Authority | Failure meaning |
|---|---|---|
| market freshness | frozen Evidence `reference_data_status`/snapshot market facts | `REFERENCE_MISSING` 或 `REFERENCE_STALE`；Opportunity 仍存在，但 Gate A no-call，显式计入 denominator |
| Opportunity business validity | formal Evidence expiry + durable current G2 `SETUP/state_version` | setup 已失效、normalize、version moved 或 superseded |
| input snapshot validity | `snapshot_payload_hash` + `input_binding_digest` + exact evidence hash | payload corruption/misrouting/incompatible binding；critical invariant |
| deadline | immutable `decision_deadline_at` | invocation latency budget expired，与 business expiry 不同 |

| 时点 | 必须动作 |
|---|---|
| stale before enqueue | 不入 queue；同 invocation terminalize，zero provider |
| stale while queued | dequeue durable re-read 后 terminalize，zero provider |
| stale immediately before provider | attempt-start transaction 拒绝，zero provider |
| stale during provider call | 不需新增 market subscription/second event bus；response 后 finalizer durable re-read并判 stale；可 best-effort cancel，但 cancellation 不是 authority |
| valid response 后、finalization 前变 stale | finalizer transaction 判 `STALE_DECISION`，valid response 只留 attempt audit，不能赢 final |

Evidence revision/hash superseded、state version moved、Opportunity expiry 或 deadline expiry都会使旧 result 不可行动；
Gate A 虽无经济动作，仍必须按与未来 Gate B 相同的 fence 记录，避免 Shadow 证明失真。

## 18. Shutdown / Cancellation / Restart

### 18.1 Shutdown order

1. Host 设置 `advisory_admission_open=false`，拒绝新 post-commit offer。
2. 停止从 durable admission 向 queue 补充；不再启动新 attempt。
3. cancel active provider I/O；取消仅作用于 Advisory nested scope，不能传播到 safety/protection siblings。
4. 对 bounded queue 中未开始项写 `CANCELLED` final；对已开始项完成 attempt cancellation audit。所有写入受
   Host 剩余 shutdown deadline 约束并 shielded only for short DB cleanup。
5. 若 DB/时间不足，保留非 terminal durable state，记录 subsystem shutdown failure，立即让出 Protection
   cleanup；不得无限 drain。
6. nested workers 全部结束后 wrapper 向 Host acknowledge；engine 仍由 Host 最后 dispose。

D2 选择 **cancel，不做 provider drain**。Advisory 不得消耗/延长 D1 已接受的 Protection cleanup window。

### 18.2 Restart recovery

Core recovery/Protection 可先完成并诚实 ready；Gate A readiness 在以下 recovery 完成前为 false：

- final 已存在：永不 requeue。
- `ADMITTED/QUEUED` 且未过期：按 durable ordering 分页填充 bounded queue；同 invocation。
- `ACTIVE` 且 attempt 无 completion：把原 attempt 记为 `PROCESS_LOST/ABANDONED`；只有原 joint budget与
  deadline 允许时才创建下一 attempt。
- `RETRY_PENDING`：按原 provider/model/input/deadline 继续；不重建 pair/arm。
- 已过 deadline/Opportunity invalid/activation disabled：原 invocation terminalize，zero provider。
- queue capacity 只限制 in-memory batch；recovery 分页且一次最多持有 capacity 个 ref，不建立 unbounded
  in-memory backlog。

## 19. Health / Readiness

### 19.1 Minimum surface

```text
activation_level: DISABLED | GATE_A_SHADOW | GATE_B_PAPER
state: DISABLED | STARTING | RECOVERING | ACTIVE | DEGRADED | FAIL_CLOSED | STOPPING | STOPPED
queue_size / capacity / high_water
admitted / rejected / expired
active_attempts / completed / failed / timed_out / cancelled
late_results / duplicate_fenced
last_success_at / last_failure_at
last_failure_category
recovery_pending
provider_configured (identity only; no secret)
```

只保留 current snapshot、monotonic counters、high-water 与 bounded error samples；不构建 metrics platform 或
unbounded time series。

### 19.2 Readiness split

- `RuntimeHost Core readiness`：Protection/DB/market/G2 的 accepted conjunction；Gate A auxiliary failure 不把
  Protection 判 unavailable。
- `Advisory/Gate A readiness`：只有 config complete、recovery complete、queue/workers live、provenance writer
  healthy、provider adapter eligible 时为 true。
- 系统声称 `GATE_A_SHADOW active` 时，invocation/attempt/final persistence failure 必须关闭 new advisory
  admission、把 Gate A health 置 `FAIL_CLOSED`；Core Host 可继续 ready/protective。
- shared DB/singleton/engine ownership failure 仍按 I1 Host fatal matrix；那是 Host failure，不是被“降级”为
  AI failure。

### 19.3 Failure-domain split

- ordinary provider/refusal/validation/timeout：仅 terminalize one invocation，worker 继续。
- Advisory critical failure（worker invariant、durable provenance unavailable、queue contract breach）：nested
  Advisory scope 关闭，wrapper 捕获并报告 `FAIL_CLOSED`，不得逃逸取消 Host safety siblings。
- shared Host critical failure：沿用 I1 external-restart signal，不由 Advisory 自建 restart loop。

## 20. Gate A / Gate B Boundary

唯一 activation config：

```text
advisory_activation_level = DISABLED | GATE_A_SHADOW | GATE_B_PAPER
```

- default = `DISABLED`。
- I2 只可实现/接受 `DISABLED` 与 `GATE_A_SHADOW`；在 Gate A Human activation 前仍保持 disabled。
- 未经独立 Gate B implementation + Human Approval，配置 `GATE_B_PAPER` 必须在 startup fail closed，不能
  自动降级/解释成 Gate A，也不能创建 plan。

| Level | Allowed | Forbidden |
|---|---|---|
| Gate A | real provider call（另行激活后）、decision/provenance/AI attribution | TradePlan、Risk、Execution、Position、Account、Ledger mutation |
| Gate B | 仅在独立批准后，一条 predeclared authoritative arm 可进入 existing deterministic chain | baseline fallback、绕过 validator/risk/execution/accounting/protection、Live |

Gate A wiring 完成不等于 Gate A active；Gate A active 不等于 Gate B；Gate B 不等于 Gate C/Live。

## 21. Schema Delta Decision

### 21.1 REUSE AS-IS

- `edge_opportunity_evidence`：Opportunity/Evidence durable identity、hash、snapshot source、expiry authority。
- G2 event/timeline/state/transition/candidate/observation tables与 transaction semantics。
- `edge_attribution_events` schema/identity：作为 append-only lineage；不是 invocation/final fence。
- Trade/Risk/Execution/Position/Account/Ledger schema：Gate A 完全不写。

### 21.2 REUSE WITH MINIMAL EXTENSION

`decision_snapshots`：为新 Shadow rows 增加/queryable binding facts（legacy rows 兼容）：

```text
opportunity_id, evidence_id, evidence_revision, evidence_hash,
market_type, snapshot_payload_hash, input_binding_digest,
decision_requested_at, decision_deadline_at
```

`ai_decisions`：继续作为唯一 logical final，最小增加：

```text
decision_invocation_id (unique for non-null new rows),
input_binding_digest, experiment_id, pair_id, arm_id,
provider_id, configured_model_id, provider_reported_model_id nullable,
output_digest, error_category, finalized_at
```

legacy `decision_id(snapshot_id, model)` 只保留给既有非-Advisory路径；新 Gate A 必须使用 invocation-derived
`decision_id`。migration/backfill 策略属于 I2 design review，不能把旧 row 伪造为新 invocation。

### 21.3 NEW MINIMAL PERSISTENCE REQUIRED

`advisory_decision_invocations`（一 row / logical invocation）：

```text
decision_invocation_id PK
snapshot_id FK
opportunity_id / evidence_id / evidence_revision / evidence_hash
experiment_id / experiment_definition_digest
pair_id / baseline_arm_id / treatment_arm_id / arm_id
baseline_policy_version / baseline_participation
input_binding_digest
prompt_version / schema_version / treatment_version
configured_provider_id / configured_model_id
decision_requested_at / decision_deadline_at
state (ADMITTED/QUEUED/ACTIVE/RETRY_PENDING/FINAL)
final_decision_id nullable
created_at / updated_at
UNIQUE(experiment_id, pair_id, arm_id)
```

`advisory_decision_attempts`（一 row / attempt）：

```text
attempt_id PK
decision_invocation_id FK
attempt_number
retry_class / retry_reason / prior_attempt_id nullable
provider_request_id / provider_response_id nullable
configured_provider_id / configured_model_id / provider_reported_model_id nullable
started_at / response_received_at / finished_at / latency_ms nullable
provider_outcome / normalized_status / error_category
input/output/total_tokens nullable + unavailable_reason nullable
monetary_cost nullable + pricing_version nullable
output_digest / validation_result / validation_errors
redacted request/response envelope nullable (policy-gated)
UNIQUE(decision_invocation_id, attempt_number)
```

不新增 generic workflow、event bus、saga、job、provider registry 或 metrics table。`ai_decisions` unique linkage
就是 final winner row，不另建第三个 final table。

## 22. Numeric Policy / Human Decision Pack

### 22.1 Classification

| 未决项 | 分类 | Safe I2 posture |
|---|---|---|
| joint total attempts / transport retries / validation retries | **B — does not block I2; blocks Real Provider Activation** | positive explicit config；unset => Shadow activation rejected；tests inject boundary values |
| per-attempt timeout | **B** | interface/enforcement implemented；unset => disabled |
| absolute decision deadline | **B** | field/digest/propagation implemented；unset => disabled |
| per-decision token/cost budget | **B** | nullable usage provenance + fail-closed budget checker；unset => disabled |
| advisory queue capacity / finite worker count | **B** | bounded implementation accepts explicit injected values；production activation unset => disabled |
| exact provider/model | **B** | provider-neutral interface only；no real constructor in I2 candidate unless separately authorized |
| raw provider envelope retention size/duration/access | **B** | retention OFF / columns NULL；normalized/redacted required provenance仍保存 |
| Gate A Shadow observation window / operational sufficiency thresholds | **C — blocks Gate A Acceptance/Declaration only** | collection counters implemented；no PASS threshold invented |

### 22.2 Human Decisions Blocking I2 Implementation

`NONE`，前提是 I2 必须接受“production activation disabled when required explicit config is unset”，并且只用
fake/injected provider做 deterministic tests。若 I2 被要求同时真实激活 Gate A，则上表 B 项立即变成 blocker。

### 22.3 Human Decisions Blocking Real Provider Activation

1. exact Single Primary Provider + exact model/deployment identity；
2. total/transport/validation attempt limits；
3. per-attempt timeout + absolute deadline；
4. token/cost budget与 usage unavailable policy；
5. queue capacity + finite worker count；
6. raw envelope retention/access policy；
7. selected provider/model 的 strict structured output、refusal、usage、request-id能力验收。

### 22.4 Human Decisions Blocking Gate A Acceptance Only

- minimum Shadow observation window；
- latency/deadline miss、failure/refusal/schema/stale/late/duplicate、cost与coverage 的 sufficiency/pass thresholds。

## 23. Implementation Batch Proposal

### PRE-01B-I2 — AdvisoryIngress Core / Shadow-Safe Durable Path

一个最小 vertical slice：

1. migration + minimal models/constraints in §21；
2. G2 formal transaction staged invocation + typed post-commit ref；
3. Host-owned bounded AdvisoryIngress queue/nested auxiliary lifecycle；
4. adapted immutable snapshot/input builder；
5. durable attempt-start/final winner transactions；
6. fake/injected provider only，activation default `DISABLED`；
7. deterministic rollback/full/deadline/stale/race/shutdown/restart/adverse tests；
8. focused G2/G3/SE-02B/RuntimeHost regression and real disposable PostgreSQL transaction evidence；
9. zero Real API call、zero Gate A activation、zero Gate B/economic mutation。

Real provider adapter selection/contract validation与 Gate A activation应为后续独立获批 batch/gate；不得为了
“一次完成”并入 I2。

## 24. Acceptance Criteria

I2 Candidate 只有在独立证据逐项证明以下事实时才 ready for review：

1. qualifying formal Evidence + invocation/snapshot 同 transaction；rollback 后 queue/provider/rows 全为零。
2. Capture Anchor without formal Evidence 永不进入 Advisory。
3. enqueue 只发生在 commit 后；crash-after-commit-before-enqueue 恢复同一 invocation。
4. queue object 只有 frozen ref；consumer durable re-read并验证所有 binding/hash。
5. queue bounded；full = durable REJECT NEWEST；no block/drop/coalesce。
6. Protection lane 在 queue full、slow provider、provider timeout、Advisory critical failure 下持续工作。
7. Gate A consumer constructor/call graph 无 TradePlan/Risk/Execution/Position mutation handle。
8. Gate A adversarial valid LONG response 仍产生 zero TradePlan/economic mutation。
9. `G3Workflow`、`TradePlanManager`、`persist_trade_plan` 在 Gate A call count = 0。
10. one invocation identity collision-free绑定 exact opportunity/evidence/snapshot/experiment/pair/arm/versions/model。
11. retry same invocation/deadline/input；attempt identity独立且 start-before-provider durable。
12. two concurrent completions、retry/shutdown/restart race只产生一个 `ai_decisions` final。
13. late/duplicate loser保留允许的 attempt audit但不能覆盖 winner。
14. all expiry/stale phases匹配 §17，且 no provider/no risk behavior精确。
15. restart 对 ADMITTED/QUEUED/ACTIVE/RETRY_PENDING/FINAL 均匹配 §18。
16. failure matrix 全部有 targeted tests；无 baseline fallback/fake-AI substitution。
17. Gate A health fail closed不取消/阻塞 safety sibling；shared Host fatal仍沿用 I1。
18. activation default disabled；缺任何 B 类 config 或请求 Gate B 均 startup fail closed。
19. exact allow-list tables之外零写；Production/Live/Real API = zero。
20. no G2 state-machine、G3 economic、Risk、Execution、Accounting、Protection semantic regression。

## 25. Risk Register

| Risk | Treatment |
|---|---|
| 把 Capture Anchor 当正式 Opportunity | producer 必须验证 exact Evidence row/invocation FK；anchor-only ignored |
| G3Workflow 产生 TradePlan | Gate A 禁用其类型/handle并做 call-count + table-delta tests |
| G2 transaction rollback却已 enqueue | queue touch严格 post-commit；typed result在 transaction exit 后返回 |
| commit→enqueue crash 丢任务 | durable `ADMITTED` scan，same invocation recovery |
| queue full删样本/阻塞行情 | REJECT NEWEST + durable final；non-blocking offer；scanner/protection lanes隔离 |
| legacy decision_id collision | new invocation-derived final id + unique invocation linkage |
| two provider completions双 winner | invocation row lock + unique final constraint + one transaction |
| retry重置 deadline/arm | immutable invocation facts；attempt不得覆写 |
| restart 用新 config 重配旧 decision | invocation self-contained；old row不读取新 experiment/model重建 identity |
| provider alias/model drift | configured + provider-reported exact identity分别保存；unknown != configured |
| Advisory failure拖垮 Protection | nested auxiliary wrapper catches/classifies；Core/Gate A readiness拆分 |
| raw envelope泄密/无限增长 | retention OFF until approved；redaction + size/TTL/access decision required |
| Shadow result被未来代码误接到 economic path | activation enum、constructor allow-list、Gate B startup reject、table mutation tests |
| staged provenance使 G2 admission失败 | 仅 Gate A active时启用；分类为 critical advisory infra fail-closed，不是 provider failure；Protection继续 |

## 26. Explicit Non-Goals / Overengineering Check

明确不设计/不引入：Kafka、Redis、Celery、RabbitMQ、Kubernetes、microservice split、LangGraph、generic
agent runtime、LiteLLM Router、model voting、automatic provider fallback、distributed workflow engine、new event
bus、generic saga framework、第二套完整 G3、第二个 RuntimeHost、in-process process supervisor。

默认并保持：Modular Monolith、one RuntimeHost、one process、bounded in-process queue、PostgreSQL durable
authority。当前 repository truth 足以满足 correctness；无证据需要扩大基础设施。

## 27. Design Verification / Candidate Verdict

本 Artifact 的验证边界仅为 repository/source/diff 静态检查：

- Global Protocol、`main/origin/main`、Accepted D1/I1状态已实时核验；
- mandatory Accepted Contracts 已完整阅读；
- G2 formal transaction、Opportunity/Anchor、G3 workflow/decision/plan、RuntimeHost ownership/isolation、
  attribution/schema与相关 adverse tests已审计；
- production/tests/migration/schema/runtime/state docs = zero change；
- Candidate 必须由 Independent Reviewer 重新读取 source/diff 后裁决；本作者不 Human Accept。

```text
Producer Boundary = formal edge_opportunity_evidence + staged invocation/snapshot transaction commit
Gate A Consumer = ShadowAdvisoryDecisionPath with provenance-only write allow-list
G3Workflow = DO NOT USE IN GATE A
Invocation Authority = deterministic AdvisoryAdmissionWriter before attempt 1
Final Fence = PostgreSQL invocation row lock + unique ai_decisions invocation linkage
Queue = bounded / non-blocking / REJECT NEWEST / no coalesce
Deadline = one immutable absolute deadline from durable Evidence created_at
Gate A vs Gate B = explicit activation level; Gate B rejected until separate approval
Schema = reuse existing evidence/snapshot/final + two minimal new persistence tables
I2 Numeric Blockers = NONE when activation remains disabled and config is explicit/unset
Artifact Status = CANDIDATE DESIGN / PENDING INDEPENDENT REVIEW
```
