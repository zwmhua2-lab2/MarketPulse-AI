# PRE-01B-D2｜AdvisoryIngress / G2→G3 Activation Contract（Rebuilt on Latest Main）

## Artifact Status

```text
Artifact: PRE-01B-D2 AdvisoryIngress / G2→G3 Activation Contract
Status: CANDIDATE DESIGN
Review: PENDING INDEPENDENT REVIEW
Human Acceptance: NOT PERFORMED
Task type: BASELINE RE-AUDIT + DESIGN RECONCILIATION + CANDIDATE REBUILD / DOCS ONLY
Implementation authorized by this artifact: NO
Runtime or provider activation authorized by this artifact: NO

Original D2 Base: 664207a9caba0c3f5c2589cfca2a10af24f89108
Original Blocked Local Draft: be836c0ed008058508eb4a9065d03c7b617f7c0b
  (branch design/pre-01b-d2-advisory-ingress-contract，BLOCKED DRAFT / NON-CANONICAL /
   NOT REVIEWED / NOT ACCEPTED；仅作 DRAFTING INPUT，不 push / 不 rebase / 不 amend /
   不 repoint)
Block Reason: SE-02D-I02 material baseline drift
Rebuilt Baseline: d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6
Candidate branch: design/pre-01b-d2-advisory-ingress-contract-r1
```

本文件只冻结未来独立获批的 `PRE-01B-I2` 所需设计边界。它不实现、不迁移、不接通
live `G2→G3`、不构造真实 provider，也不授权 Gate A / Gate B / Live。本次重建以
blocked draft 为起草输入，但**每一个重要决策都对照 latest Accepted Repository Truth
（含新接受的 SE-02D-I02）重新审计**；与旧 draft 的差异全部在 §0.3 与 dev_log 中显式列出。

## 0. Rebuild 说明

### 0.1 重建授权

Human / Design AI 已明确授权：在 latest Accepted Main `d1e5534` 上重建 PRE-01B-D2。
旧 draft `be836c0` 的处理遵循任务边界：不 push、不 rebase、不 amend、不 repoint、
不删除其本地历史；其内容仅作为起草输入。

### 0.2 重建方法

1. 实时核验 Global Protocol（v1.1.0 / ACCEPTED / `07e2df8…`）与 `origin/main = d1e5534`。
2. 完整重读两份 Accepted Contract（PRE-01A-D1、PRE-01B-D1）与新接受的 SE-02D-I02
   真值（`aggregation_snapshot.py` + 测试 + 两份 dev_log）。
3. 对照 latest 代码重审计旧 draft 的全部 source facts（G2 formal transaction、
   EventRuntime、capture/qualifies、G3 Workflow/Decision/Queue、RuntimeHost、
   DB schema、attribution）。
4. 对 §8 列出的每一项重要决策逐条重审；改动者给出新证据，保留者给出重验证证据。

### 0.3 相对旧 draft 的决策变更总览（详情见各节）

| # | 旧 draft 决策 | 重建决策 | 变更原因（证据） |
|---|---|---|---|
| 1 | Admission staging 失败 ⇒ 回滚**整个** G2 formal transaction（G2 facts + Evidence 一并丢失） | Admission staging 在同一 transaction 内以 **SAVEPOINT 隔离**；staging 失败只回滚 advisory 部分，G2 facts + Evidence 照常 commit | 旧设计让 AI provenance 基础设施失败摧毁 durable G2 market truth —— 恰是任务 §12 质疑的「AI advisory persistence 污染 Scanner core responsibility」。Atomicity 由 savepoint 保留，G2 真值不再被 AI infra 劫持 |
| 2 | queue full 的 durable 终态 = `INVALID_SCHEMA / ADVISORY_QUEUE_REJECTED` | = `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` | PRE-01A-D1 §8.1 冻结 `CAPACITY_BLOCKED` = 「downstream capacity outcome, not an AI/provider failure」；queue full 正是 capacity outcome，映射为 `INVALID_SCHEMA` 会污染 failure-rate 诊断 |
| 3 | `decision_requested_at` 权威 = 读回 formal Evidence 的 durable `created_at` | 权威 = **Invocation 自身 admission 时写入的 durable timestamp**（与 Evidence 同 transaction） | 任务 §17 明确 Evidence.created_at 不是 Accepted Truth。Admission timestamp 自包含、满足 PRE-01A「attempt 1 前固定」；同 transaction 下与 Evidence.created_at 数值一致（见 §17 论证），但 authority 是 invocation 自身事实 |
| 4 | Evidence supersede 仅在 stale matrix 一句带过 | **独立 Evidence Supersede Contract**（§10）+ 明确「N+1 可另立新 Invocation」规则 | SE-02D-I02 新接受语义使 revision-chain / canonical head 成为必须显式设计的边界；PRE-01A-D1 §10 已冻结「新 Evidence revision ⇒ 新 unit/invocation」 |
| 5 | （无此节；旧 draft 早于 I02） | **Admission Evidence vs Canonical Evidence Head 区分**（§9）+ SE-02D-I02 runtime reuse = NONE（§23.2） | 任务 Critical Question A；I02 是 aggregation-oriented REPEATABLE READ 只读投影，与 live decision-ingress 不耦合 |
| 6 | `input_binding_digest` 不含 `feature_snapshot_hash` | **纳入** `feature_snapshot_hash` | 任务 §9 要求逐项评估五个 identity 字段；feature snapshot hash 是 Evidence 身份的组成部分（schema 实测存在于 `edge_opportunity_evidence`） |

## 1. Repository Truth

### 1.1 Verified baseline（2026-09-15 实时核验）

| 项 | 实时核验事实 |
|---|---|
| Global Protocol | `zwmhua2-lab2/ai-dev-protocol`，`git ls-remote` 实测 `main = 07e2df83266d4ecdea46caff5c61f000937b8913` |
| Protocol Version / Status | `1.1.0 / ACCEPTED`（`AI_BOOTSTRAP.md` @ `07e2df8` 实读） |
| Project repository | `zwmhua2-lab2/MarketPulse-AI` |
| Remote `origin/main`（`git ls-remote` 实测） | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Local `main` | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Task Base / Rebuilt Baseline | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Baseline drift | `NO`（与任务卡 issuance 值一致） |
| Candidate branch | `design/pre-01b-d2-advisory-ingress-contract-r1`（base = `d1e5534`，新 worktree） |

会话根工作区位于 `prb-01-product-requirements-baseline@d47313a`（另一条历史分支）。
D2 在从 verified `main = d1e5534` 建立的独立 clean worktree 中完成；未 reset、stash、
clean、rebase、覆盖或归因根工作区内容。

### 1.2 Accepted inputs

- `PRE-01A-D1` = `ACCEPTED / COMPLETE`：冻结 Real AI V1 placement（C. Trade Decision only）、
  input binding、`decision_invocation_id` → exactly one logical durable final decision、
  retry/deadline/failure taxonomy、`ALL_ELIGIBLE_LONG_SHADOW_V1` baseline、Gate A/B/C 边界。
- `PRE-01B-D1` = `ACCEPTED / COMPLETE`：冻结 `RuntimeHost` 唯一 composition owner、
  FastAPI lifespan 唯一 activation boundary、AnyIO structured concurrency、Protection
  isolation、shutdown 顺序（step 2 显式预留 advisory 槽位）、backpressure 契约、
  以及「future batch may add one Host-owned `AdvisoryIngress`」的显式边界。
- `PRE-01B-I1` / Integrated Runtime Host Core V1 = `ACCEPTED / COMPLETE`
  （candidate `68dd7e9`，branch `pre-01b-i1-fix-01-runtime-host-lifecycle`）。
- `SE-02D-D01` / `SE-02D-I01` / `SE-02D-I02` = `ACCEPTED / COMPLETE`；
  `SE-02D Production` = `IN PROGRESS`（population grouping + 调用 `aggregate()` 未实现）。
- Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACCEPTED / NOT ACTIVE`；
  Gate C = `NOT PASSED`；Live = `NOT AUTHORIZED`。

### 1.3 Known stale index statement（已知陈旧索引行，非新矛盾）

`AI_CONTEXT.md`（§4 等）与 `PROJECT_STATE.md` Current Group 列表仍残留
「Integrated Runtime Host — NOT STARTED」一类较旧摘要行。按任务卡 §4，这是**已知陈旧
索引语句**：权威状态以 per-batch 条目为准 —— `PRE-01B-I1` 条目明确记录
「Runtime Host Core V1 = ACCEPTED / COMPLETE」（仅 Core V1，不含 OS/service、
Real AI、G2→G3）。本轮 re-audit **未发现**该已知模式之外的**新**矛盾。

### 1.4 Source facts that control this design（latest main 实测）

1. `PostgresG2Repository.persist()` 在单个 `session.begin()` transaction 内写
   `MarketEvent`（on-conflict dedupe）、timeline、`SymbolStateStore` merge、transition、
   candidates、observation，并在 capture context 配置时经 `capture_opportunity()`
   → `append_evidence_revision()` 写 qualifying `edge_opportunity_evidence`。
   当前返回值仅为 `bool`。（`g2/repository.py` 实读）
2. qualifying 规则 = `qualifies()`：transition `APPLIED` → `to_state = SETUP`、
   event `BREAKOUT`、state `SETUP`、存在 `watch_expires_at`、`BREAKOUT_RETEST`
   candidate 全 identity/version 一致；reference/AI/Risk/Trade/BBO **不是** admission
   条件。（`edge/capture.py` 实读）
3. `RUNTIME_CAPTURE_REVISION = 1`：runtime capture 恒写 logical opportunity 的
   **初始 revision**；revision > 1（supersedes 链）是 SE-02A 已接受 schema/契约能力，
   当前 live G2 路径不产生。（`edge/capture.py` 实读）
4. `edge_opportunity_evidence` 已持有 deterministic
   `opportunity_id/evidence_id/evidence_revision/evidence_hash/feature_snapshot_hash`、
   `supersedes_evidence_id`（同 opportunity FK）、family/instrument/market/source identity、
   `detected_at/evidence_at/expires_at/created_at`、reference quote 三态
   （`OK/REFERENCE_MISSING/REFERENCE_STALE`）与 immutable payload；DB 侧
   `uq_edge_evidence_opportunity_revision` + `fk_edge_evidence_supersedes` 保证
   revision/scope integrity。（`db/models.py` 实读）
5. `DecisionSnapshotRecord` 无 Opportunity/Evidence 绑定、无 payload hash、无
   request time / absolute deadline；`AIDecisionRecord.decision_id` 仅由
   `stable_id("decision", snapshot_id, model)` 派生，无 invocation linkage / unique
   fence；`DecisionService.decide()` provider 返回后才写 snapshot+decision（同
   transaction 含 attribution append），retry 无 durable attempt / joint deadline /
   winner fence。（`g3/service.py`、`db/models.py` 实读）
6. `G3Workflow.process_setup()` 在 `VALID + LONG_BIAS` 时经 `TradePlanManager` 构造并
   `persist_trade_plan()` —— 它不是 Shadow-safe consumer。（`g3/service.py` 实读）
7. `BoundedAITaskQueue.put()` await queue space（blocking）、process-local
   `datetime.now(UTC)`、混合 `POSITION_REVIEW/PLAN_REVIEW/NEW_SETUP/LOW` 优先级、
   无 full-rejection / restart / deadline / durable dedupe 契约。（`g3/service.py` 实读）
8. `EdgeAttributionRecorder` 以 caller-transaction 内 append-only / idempotent 方式绑定
   exact `opportunity_id/evidence_id` AI lineage（`DecisionService.decide()` 已在
   decision 同 transaction 调 `record_ai_decision`）。identity 可复用，但 attribution
   不是 invocation / final-result authority。（`g3/service.py` 调用点 + SE-02B 验收记录）
9. I1 Host：safety lane 与 scanner lane 隔离；`AI_AUXILIARY` health 组件注册为
   `DEGRADED/ai_reevaluation_disabled`，**不在** Core readiness 阻断合取内；Host
   不构造任何 AI provider（`_AIDisabledSentinel`）；`_shutdown()` step 2 注释显式
   预留 advisory 关闭槽位。（`runtime_host.py` 实读）
10. SE-02D-I02 `aggregation_snapshot.py`：`CurrentSnapshotRevisionReader.read(horizon)`
    在单个 `REPEATABLE READ READ ONLY` snapshot 内以 DB `statement_timestamp()` 为
    `as_of`，折叠全量可见 Evidence / 精确 horizon Outcome 修订链、选 canonical head、
    cross-integrity 校验、输出 `CanonicalScopeFacts` + revision-aware manifest；
    不调用 `aggregate()`、无 historical `as_of` 接口。（源码 + I02 dev_log 实读）

## 2. Problem Statement

当前缺少的不是「再调用一次 G3」，而是一条能够证明下列性质的 live boundary：

```text
committed qualifying G2 SETUP / Opportunity Evidence revision
  -> durable invocation admission（与 Evidence 原子）
  -> bounded Host-owned queue（post-commit 发布）
  -> shadow-safe advisory invocation
  -> durable attempts（provider call 之前 durable）
  -> exactly one durable final winner（PostgreSQL fence）
```

任何 transient Scanner object、uncommitted row、ORM session-bound object、process
callback identity 或 in-memory dedupe 都不能成为该链的 correctness authority。
此外，SE-02D-I02 的接受使「Evidence revision chain / canonical head」成为已接受的
durable 语义：live advisory admission 必须显式回答它绑定的是**哪一份** Evidence 身份、
以及 supersede 发生时旧 Invocation 的命运（§9 / §10）。

## 3. Scope

- 精确冻结 qualifying Opportunity/Evidence revision 的 producer 与 post-commit handoff。
- 冻结 Host-owned `AdvisoryIngress` 的 construction/start/task/queue/shutdown/health ownership。
- 冻结 admission Evidence vs canonical Evidence head 的区分与 Evidence supersede 契约。
- 冻结 immutable work reference、durable re-read、snapshot/input binding、
  invocation/attempt/final identity。
- 冻结 experiment/pair/arm binding、retry/deadline/cancellation、duplicate/late/winner fence。
- 冻结 bounded queue/full policy、staleness、restart、failure isolation、health/readiness。
- 冻结 Gate A Shadow 与 Gate B Paper Economic activation 的结构性分离。
- 审计并裁定现有 schema/components（含 SE-02D-I02）的复用方式，提出最小未来 schema delta。
- 给出一个可独立获批的最小 I2 Implementation Batch 与 AC。

## 4. Out of Scope

- 任意 production code、test、migration、schema、config、runtime 或 DB 改动。
- 真实 provider/model 选择、constructor、API call、credential 或 provider runtime evidence。
- Gate A 启动、Gate B 启动、Live Trading、Short、自动 fallback、model voting。
- 修改 G2 state-machine/Scanner/Strategy business 语义或 SE-02A Evidence 契约。
- 修改 `TradePlanManager`、Risk、Execution、Accounting、Protection、Recovery、
  Reconciliation 语义。
- SE-02D 后续实现（population grouping、`aggregate()` 调用、Gate C threshold、
  profitability/edge 声明）；historical revision-as-of。
- Position re-evaluation、generic workflow/event bus、microservice 或 process supervisor。

## 5. Accepted Invariants

1. `RuntimeHost` 是唯一 production composition owner；FastAPI lifespan 是唯一 Host
   activation boundary（PRE-01B-D1 / I1）。
2. AI = Advisory；deterministic system = Authority（PRE-01A-D1）。
3. Gate A 必须结构性地拥有 **ZERO** TradePlan/Risk/Execution/Position/Account/Ledger
   mutation capability。
4. Protection 与 risk-reducing path 不等待、不共享 queue/lock/task failure domain 给
   Advisory（PRE-01B-D1 Protection Isolation Contract）。
5. PostgreSQL 是 durable correctness authority；queue、lock、set、TaskGroup 仅是进程内
   执行机制。
6. one `decision_invocation_id` → exactly one collision-free logical durable final
   decision（PRE-01A-D1 §6.3 / AC-21）。
7. retry 共享 invocation/deadline/input/experiment/pair/arm/provider/model；每次 attempt
   有独立 identity。
8. Single Primary Provider；no automatic fallback；no model voting；provider 不拥有本地
   identity。
9. missing/stale/invalid/failure 均 fail closed，不能转成 baseline BUY 或伪装为 AI
   decision；AI failure → zero new risk（PRE-01A-D1 §5.2）。
10. Paper only / SPOT LONG only；`SHORT_BIAS` 仅是分析/no-long。
11. Gate A、Gate B、Gate C 与 Live 是互不替代的独立授权边界。
12. Durable G2 market/Evidence truth 不依赖 AI 基础设施的健康状态（本次重建新增，
    见 §8.3）。

## 6. Baseline Reconciliation（664207a → d1e5534）

### 6.1 Delta 事实（实测）

`git log 664207a..d1e5534` = 单一 commit `d1e5534`（`docs(se-02d-i02): accept I02 via
latest-main reconciliation`）。`git diff --stat` 显示改动恰为 7 个文件：
`AI_CONTEXT.md`、`DECISIONS.md`、`PROJECT_STATE.md`、
`backend/src/marketpulse/edge/aggregation_snapshot.py`（+666）、
`backend/tests/test_se_02d_aggregation_snapshot.py`（+981）、两份 SE-02D-I02 dev_log。
**零** G2/G3/RuntimeHost/前端/config 变更。

### 6.2 Delta 分类

- Accepted change：`SE-02D-I02 = ACCEPTED / COMPLETE`（Current-Snapshot Revision
  Folding / canonical-head projection）。
- 它引入的已接受语义：full visible Evidence revision-chain validation；canonical
  Evidence head selection；frozen logical fact validation；exact-horizon Outcome
  revision-chain folding；canonical Outcome head / `NO_OUTCOME`；canonical
  Evidence ↔ Outcome cross-integrity；`CanonicalScopeFacts` projection；
  `CURRENT_STABLE_SNAPSHOT`（REPEATABLE READ READ ONLY + DB
  `statement_timestamp()` 作 `as_of`）。
- **Classification：MATERIAL TO D2 DESIGN AUDIT** —— 它使 revision-chain /
  canonical-head 成为已接受语义，D2 必须显式回答 Critical Question A（§9）与
  supersede 语义（§10）。
- 它**不**自动意味着：AdvisoryIngress 必须调用 `aggregation_snapshot.py`（裁定：
  **NONE**，§23.2）；也不自动意味着 current canonical Evidence head 就是 live
  advisory admission identity（裁定：**不是**，§9）。

### 6.3 对旧 draft source facts 的影响

§1.4 facts 1–9 与旧 draft 的 source facts 逐条比对：d1e5534 相对 664207a 未触碰
G2/G3/RuntimeHost/Edge capture/schema/attribution 任何路径，旧 facts 在 latest main
上复测全部成立（本窗口直接实读源码复核，非沿用旧 draft 自述）。唯一新增材料性输入
是 fact 10（I02 投影层）。

## 7. Reuse Decisions

| 现有组件 | Verdict | 设计裁定（latest main 复核后） |
|---|---|---|
| `BoundedAITaskQueue` | `DO NOT USE IN GATE A` | blocking `put`、process-local wall clock、混合 Position/Plan/New 优先级、无 full/restart/deadline/final fence；不得把 Position Review 与 Gate A setup 混队列。仅「bounded queue」概念参考 |
| `DecisionService` | `ADAPT` | 复用 provider-neutral boundary、`PromptBuilder`/`DecisionValidator`/`redact` pieces；拆为 pre-call durable admission、attempt runner、finalizer。不沿用 call-first/persist-later、legacy retry、legacy `decision_id` |
| `G3Workflow` | `DO NOT USE IN GATE A` | 实测 `process_setup()` 持有 `TradePlanManager` 并在 VALID+LONG path 调 `persist_trade_plan()`；直接复用会产生未授权经济前置事实 |
| `DecisionSnapshotBuilder` | `ADAPT` | 改为从 exact formal Evidence revision + 同 transaction durable facts 构造 canonical immutable snapshot；增加 content hash 与完整 binding。不以 caller mutable object / global market object 为 authority |
| `TradePlanManager` | `DO NOT USE IN GATE A` | Gate A consumer 不构造、不注入、不调用 |
| existing AI decision persistence（`decision_snapshots` / `ai_decisions`） | `REUSE WITH MINIMAL EXTENSION` | snapshots 继续存 frozen input；`ai_decisions` 继续作唯一 logical final；新增 invocation linkage 等 queryable 字段（§24）；attempt/history 用最小新表 |
| `RuntimeHost` TaskGroup / lifecycle | `ADAPT` | Host 构造/启动/停止 Advisory（D1 shutdown step 2 预留槽位）；一个受控 wrapper child 拥有内部 finite workers；Advisory 异常在 wrapper 内分类，不得取消 safety siblings；沿用 I1 fatal matrix，不自建 restart loop |
| existing attribution identity（`EdgeAttributionRecorder`） | `REUSE` | exact `opportunity_id/evidence_id` lineage、append-only、caller-transaction pattern 保持；payload 可增 invocation/experiment facts；attribution 不是 winner authority |
| `PostgresG2Repository` formal transaction | `ADAPT` | 复用 G2+Evidence 原子提交；Gate A 显式启用时在同一 transaction（savepoint 内，§8.3）stage immutable snapshot + invocation；queue 只在 commit 成功后触达；`persist()` 返回 typed result |
| SE-02D-I02 `aggregation_snapshot`（`CurrentSnapshotRevisionReader` / `CurrentSnapshotProjection` / `CanonicalScopeFacts`） | `DO NOT USE IN GATE A`（runtime reuse = NONE） | I02 是 Edge/Expectancy 的 REPEATABLE READ READ ONLY、aggregation-oriented 投影；live advisory decision-ingress 不得与之耦合。概念性复用见 §23.2 |

## 8. Producer Boundary

### 8.1 Exact qualifying record

唯一 producer input 是已满足 accepted `qualifies()` 规则、将要写成
`EdgeOpportunityEvidenceRecord` 的 formal Evidence revision（当前恒为 revision 1，
`RUNTIME_CAPTURE_REVISION = 1`；若未来已接受的 G2 变更引入 live revision > 1，本契约
按 revision 粒度自动适用，见 §10）。以下均**不是** producer input：

- `StrategyCandidate` 单独存在；
- Capture Anchor（含其 `UNVERIFIABLE_ORPHAN` 分类）；
- `SignalTimelineEvent` 单独存在；
- process-local `SETUP` state；
- callback 自造的 symbol/time identity。

### 8.2 Exact transaction and enqueue timing

未来 I2 必须把当前 bool-only `persist()` 结果最小扩展为 typed result。流程固定为：

1. `PostgresG2Repository.persist()` 在现有 G2 formal transaction 中写 G2 facts 与
   exact Evidence revision（`capture_opportunity()` 内）。
2. 仅当 Gate A Shadow config 完整且显式启用、且本次 persist 确实 staged 了 qualifying
   Evidence revision 时，Host-composed 并注入的 `AdvisoryAdmissionWriter` 在**同一
   transaction** 内：
   - 使用该 exact `EvidenceRevision` 与同 transaction 的 resulting SETUP/state facts；
   - 构造 deterministic snapshot / input binding / experiment / pair / arm /
     invocation identity（§12 / §13）；
   - 写 `decision_snapshots`（extended row）与
     `advisory_decision_invocations(state=ADMITTED)`；
   - 不调用 provider、不触达 queue、不写 `ai_decisions` final、不写任何
     TradePlan/economic table。
3. `session.begin()` 正常退出（commit）后，`persist()` 返回 typed result（含 frozen
   `AdvisoryWorkRef`，若 admission 成立）。
4. `EventRuntime` 仅在 `persisted=true` 且持有 ref 后，调用 Host-owned
   `AdvisoryIngress.post_commit_offer(ref)`。
5. `post_commit_offer` 使用 non-blocking `put_nowait`/equivalent；consumer 只收到 ref。

**Phantom proof**：queue 只在 commit 后被触达；staging 失败（savepoint 回滚，§8.3）或
transaction 失败时 ref 不存在，步骤 4 永不执行 ⇒ 不存在「queue 已看见但 DB 不存在」
的 phantom advisory work。Capture Anchor 可能仍按 accepted contract durable，但它没有
formal Evidence/invocation，Advisory recovery 必须忽略它。

**Crash-gap proof**：commit 成功而进程在 enqueue 前死亡时，`ADMITTED` invocation 已
durable；restart scan 恢复**同一** invocation，绝不创建「全新 decision」（§15）。

### 8.3 Admission staging failure polarity（相对旧 draft 的核心变更）

Admission staging 属 critical provenance infrastructure，但其失败**不得**摧毁 durable
G2 market truth：

- staging 在同一 G2 formal transaction 内以 **SAVEPOINT**（SQLAlchemy
  `begin_nested()` / PostgreSQL `SAVEPOINT`）执行；staging 的任一错误只 rollback 到该
  savepoint（advisory rows 消失），**外层 transaction 照常 commit** G2 facts +
  Evidence。
- 后果：该 qualifying Opportunity 的 Evidence 正常 durable，但**没有** admission ——
  这是一个显式的 experiment coverage hole，不是被静默删除的样本：
  - `AdvisoryIngress` 递增 admission-staging-failure 计数并转入 `FAIL_CLOSED`
    （关闭新 advisory admission，Gate A readiness = false）；
  - 不调用 provider（invocation 不存在，无从调用）；
  - 不传播为 safety/protection sibling cancellation；
  - 不影响 Protection / Core Host readiness；
  - 不伪装成 provider failure（diagnostic = `ADMISSION_STAGING_FAILED`）。
- 外层 transaction 在 staging 之后失败：整体（G2 + Evidence + advisory）原子回滚，
  无 phantom、无半提交。
- Gate A `DISABLED` 时 writer 不注入，现有 G2 persistence 行为与 I1/SE-02B accepted
  路径逐字节一致（与 `EdgeCaptureContext` opt-in 同型）。

**理由（任务 §12 逐问回答）**：

| 问题 | 裁定 |
|---|---|
| Evidence + Snapshot + Invocation 能否合法同 transaction？ | 能 —— same-session/same-transaction 是既有 accepted 模式（`capture_opportunity` 在 G2 transaction 内；`DecisionService` 已同 transaction 写 snapshot+decision+attribution）。SAVEPOINT 只隔离失败，不破坏原子性 |
| 是否不当扩大 Scanner/G2 authority？ | 否 —— G2 formal transaction 只是 **atomicity host**；admission 的 identity/policy authority 属 Host-composed、config-gated 的 `AdvisoryAdmissionWriter`；writer opt-in 注入，Gate A disabled 时 G2 路径不变 |
| AI advisory persistence 是否污染 Scanner core responsibility？ | 旧 draft 会（staging 失败回滚 G2 facts ⇒ AI infra 失败摧毁 market truth）；savepoint 方案消除该污染：Scanner/G2/Edge 真值独立于 AI infra 健康（invariant 12） |
| rollback 能否产生 phantom advisory work？ | 不能（§8.2 phantom proof） |
| DB commit 成功而进程在 enqueue 前崩溃？ | 可能；由 durable `ADMITTED` + restart scan 恢复（§15），process-local queue publication 不是 authoritative delivery fact |
| 谁拥有 admission creation？ | `AdvisoryAdmissionWriter`（Host 在 `_compose_services` 构造，唯 Gate A config 完整时注入）；Scanner/EventRuntime/G2 不拥有 admission policy |

## 9. Evidence Revision Binding（Critical Question A）

### 9.1 两个必须区分的概念

```text
A. Admission Evidence = 在 live Advisory admission 的 G2 formal transaction 中
   staged 的那份 exact、durable、immutable Evidence revision N
   （opportunity_id + evidence_id + evidence_revision + evidence_hash
    + feature_snapshot_hash）。

B. SE-02D-I02 current canonical Evidence head = 在某个 REPEATABLE READ READ ONLY
   快照内对全量可见 Evidence revision chain 折叠后选出的 canonical head ——
   这是 Edge / Expectancy aggregation projection 的概念。
```

**裁定**：

1. Advisory admission 绑定 **A**，永不绑定 B。绑定的 Evidence identity 字段（全部
   进入 `decision_invocation_id` / Decision Snapshot / experiment / pair / arm
   binding / provider input provenance / `input_binding_digest`）：
   - `opportunity_id`（bound）
   - `evidence_id`（bound）
   - `evidence_revision`（bound）
   - `evidence_hash`（bound）
   - `feature_snapshot_hash`（bound；旧 draft 漏，本版纳入）
2. canonical Evidence head（B）是**事后**可能随新 revision 变化的聚合视图概念；
   AdvisoryIngress 在 admission、consume、finalize 任何时点都**不**查询、**不**依赖 B。
3. **An already-created Invocation must never silently switch to a later canonical
   Evidence head**：Invocation 的 Evidence binding 是 admission transaction 写入的
   immutable facts；不存在任何代码路径把 invocation 的绑定改写为 chain 的另一节点。
   supersede 的后果是旧 Invocation 变 stale（§10），而不是换绑。

### 9.2 一致性说明

因为 admission 与 Evidence revision N 的持久化发生在**同一 transaction**，admission
时「durably visible 的 revision」恰为 N 本身；不存在「admission 时看到 N、事后发现
canonical 已是 N+1」的 admission 竞态。canonical head 的漂移只发生在 admission 之后，
其唯一合法影响是使旧 Invocation stale（§10）。

## 10. Evidence Supersede Contract

场景：Invocation 已按 Evidence revision N admission；随后 revision N+1 durable 且
supersedes N（当前 live G2 路径恒写 revision 1，N+1 今天不会由 runtime 产生；但
schema/SE-02A 契约与 I02 折叠语义使该场景成为必须显式设计的边界）。

### 10.1 冻结规则

1. **旧 Invocation 永久绑定 N**：identity、`input_binding_digest`、snapshot、
   experiment/pair/arm binding 全部 immutable。**Forbidden**（任务 §10 红线）：
   把旧 Invocation 从 N 改写到 N+1；改写 input-binding digest；把同一 Invocation
   当作「一直以 N+1 为输入」复用；post-hoc experiment rebinding。
2. **旧 Invocation 的命运 = stale / non-actionable**：在任一检查点（pre-enqueue /
   dequeue / pre-provider / during-provider→finalizer / pre-finalization）检测到
   「同 `opportunity_id` 存在 revision > N 的 durable Evidence row（或等价的
   supersedes 链事实）」⇒ 该 Invocation terminalize 为
   `STALE_DECISION / EVIDENCE_SUPERSEDED`，zero provider call（若尚未调用），
   valid response 只留 attempt audit、不能赢 final（若已调用）。检测方式 = 直接
   durable 查询 `edge_opportunity_evidence`（按 `opportunity_id` 取 max
   `evidence_revision`），**不**调用 `aggregation_snapshot.py`。
3. **N+1 可另立新 Invocation**：若 N+1 本身经 accepted `qualifies()` 规则在一个
   G2 formal transaction 中 staged（即它是 qualifying 的），则 §8 的 admission 规则
   对它自动适用 —— 同一 experiment 下，每个 exact Evidence revision 至多一个
   `REAL_AI_TREATMENT` invocation。新 Invocation 是**全新**的
   invocation/pair/identity（`input_binding_digest` 含 N+1 的
   evidence_id/revision/hash），与旧 Invocation 无任何改写关系。若 N+1 不是
   qualifying capture（如仅作为重检/修订被其他已接受路径写入），则不产生新
   Invocation —— admission 只认 §8.1 的 qualifying record。
4. **PRE-01A-D1 §10 依据**：「A new evidence revision … creates a new
   unit/invocation and may not reuse the old result」—— 本契约是该冻结语义在
   live ingress 路径上的落地。
5. **生命周期覆盖（任务 §10 清单）**：
   - before queue publication：offer 前置检查 ⇒ 不入 queue，terminalize；
   - while queued：dequeue durable re-read ⇒ terminalize，zero provider；
   - before provider call：attempt-start transaction 拒绝，zero provider；
   - during provider call：best-effort cancel（非 authority）；response 后 finalizer
     durable re-read ⇒ `STALE_DECISION / EVIDENCE_SUPERSEDED`；
   - after provider result / before finalization：finalizer transaction 判 stale，
     valid response 只留 attempt audit，不能赢 final；
   - final 已存在后 supersede 发生：final 不变（winner 不可被 supersede 改写）；
     supersede 只影响**未来**的 admission。
6. **Denominator 边界**：superseded revision N 的 pair 在实验分母中如何计数
   （如是否按 predeclared exclusion rule 排除）是 SE-02D / Gate C aggregation
   contract 的问题，D2 不决定、不发明规则（§23.3）。

## 11. Consumer / Shadow Safety Boundary

Gate A consumer 是新的最小 `ShadowAdvisoryDecisionPath`，不是第二套 G3。它只拥有：

- read-only loading of invocation / snapshot / evidence / durable state facts；
- provider adapter；
- deterministic validator（复用/适配 `DecisionValidator` 语义 + PRE-01A §7.3 校验清单）；
- attempt writer、finalizer 与 attribution append writer。

它在 constructor/type boundary 上**不得拥有**：

- `TradePlanManager`；`persist_trade_plan` callable；`SystemRiskGate`；
  `PaperExecutionService`；Position/Account/Ledger/Protection mutation repository；
  `G3Workflow`。

允许写入的 table allow-list 仅为：

```text
advisory_decision_invocations
advisory_decision_attempts
decision_snapshots (extended rows)
ai_decisions (invocation-linked final rows)
edge_attribution_events (AI lineage only)
```

Gate A tests 必须监视并证明 `trade_plans`、scenarios、intents、orders、fills、
positions、trades、accounts、ledger、outbox economic events 全部零新增/零修改。
不能用「后面的 Risk 会挡住」作为安全证明 —— Shadow path 本身必须 non-economic。

## 12. Identity Model

### 12.1 Construction order

所有 hash 使用 versioned canonical JSON（sorted keys、UTC timestamps、finite numeric
policy）；禁止 Python `repr()`、process hash、provider response 参与identity；禁止
未转义 `"|".join(...)` 之类非单射编码作身份判断（项目 identity 铁律）。

1. `snapshot_payload_hash = H(snapshot_contract_version, canonical_snapshot_payload)`。
2. `snapshot_id = H("advisory-snapshot-v1", opportunity_id, evidence_id,
   snapshot_payload_hash)`。
3. `input_binding_digest = H(binding_version, opportunity_id, evidence_id,
   evidence_revision, evidence_hash, feature_snapshot_hash, snapshot_id,
   snapshot_payload_hash, state_version, config_version, family_id/version,
   instrument_id, market_type, decision_requested_at, decision_deadline_at)`。
4. `experiment_id = H(experiment_definition_version, canonical_experiment_definition)`。
5. `pair_id = H("pre01a-pair-v1", experiment_id, input_binding_digest)`。
6. `baseline_arm_id = H(pair_id, "WITHOUT_AI_BASELINE")`。
7. `treatment_arm_id = H(pair_id, "REAL_AI_TREATMENT")`。
8. `decision_invocation_id = H("advisory-invocation-v1", experiment_id, pair_id,
   treatment_arm_id, input_binding_digest, prompt_version, schema_version,
   treatment_version, configured_provider_id, configured_model_id)`。
9. `attempt_id = H("advisory-attempt-v1", decision_invocation_id, attempt_number)`。
10. `decision_id = H("advisory-final-v1", decision_invocation_id)`；与 winner attempt
    无关，terminal failure 与 valid winner 共享同一 logical final identity
    （PRE-01A §6.3）。

### 12.2 Authority and idempotency

- `AdvisoryAdmissionWriter` 创建 invocation identity（admission transaction 内）；
  provider/model 只被记录，不能回写 identity；provider 永不是本地 identity authority。
- same immutable facts 重试/重放得到同一 invocation；相同 hash 为 idempotent，不同
  content 为 invariant conflict 并 fail closed。
- retry 只增加 attempt row，绝不增加 invocation / final identity。
- provider request/response ID（若有）记录在 attempt；不存在时为 `NULL/UNKNOWN`，
  不得伪造。
- 每个 hash 的 version literal 属 I2 实现契约，须在实现窗口逐字冻结（教训：
  SE-02D-D01 `uncertainty_method_version` 曾缺失 literal ⇒ Human Design Clarification
  补齐；D2 把该项列入 I2 实现前置核对清单）。

## 13. Experiment / Pair / Arm Binding

### 13.1 Experiment authority

Host startup config 必须提供完整 canonical experiment definition，并由确定性代码验证
`experiment_id`。definition 至少冻结：placement（C. Trade Decision only）、baseline
policy/version（`ALL_ELIGIBLE_LONG_SHADOW_V1`）、treatment version、exact configured
provider/model、prompt/schema/input-binding/snapshot versions、retry/deadline/cost
policy values/versions、horizons/metrics definition、activation level。

Host config 在一个 process lifetime 内 immutable。旧 invocation 自包含完整
binding/digest；restart 恢复它时不使用新 config 重配 pair/arm/model。若
config/definition 变化，必须产生新 `experiment_id`（即新实验 lineage，与旧 lineage
无 identity 冲突，PRE-01A AC-23）。

### 13.2 One Evidence revision, one explicit binding

- 每个 exact Evidence revision 在一个 experiment 中至多一个 `REAL_AI_TREATMENT`
  invocation（§10.3）。
- `pair_id` 在 provider call 前、outcome 前冻结。
- baseline arm 固定为 `ALL_ELIGIBLE_LONG_SHADOW_V1 / WITHOUT_AI_BASELINE`；同一
  invocation row 持久化 `baseline_policy_version` 与 deterministic
  `baseline_participation=PARTICIPATE_LONG`，使 baseline arm 不是事后推导的隐式标签。
  它不调用 provider、不产生 TradePlan，且不在 AI failure 时升级为 fallback。
- treatment arm 固定为 `REAL_AI_TREATMENT`。
- arm 不得由 response、confidence、盈利结果、retry outcome 或 latency 事后选择。
- baseline result 的未来聚合可引用同一 pair/Opportunity 的 accepted SE-02C outcome；
  I2 不复制 Outcome calculator，也不创建第二套 execution account。
- **SE-02D-I02 不解决 PRE-01A experiment identity**：SE-02D 的 population grouping
  （PopulationKey = family/version/instrument/market/source identity/contract version，
  D01 冻结）与 PRE-01A 的 experiment/pair/arm identity 是两套正交身份；二者不得
  混同，也不得从 AI output 或 population 归属 post-hoc 推导 arm。

## 14. Persistence / Transaction Contract

### 14.1 Invocation lifecycle

```text
ADMITTED -> QUEUED -> ACTIVE -> RETRY_PENDING -> ACTIVE -> FINAL
ADMITTED/QUEUED/ACTIVE/RETRY_PENDING -> FINAL (failure/cancel/stale/expired/capacity)
```

状态是 durable execution state，不是新的 `DecisionStatus`。`ai_decisions.status`
继续使用 accepted `DecisionStatus` vocabulary（含本契约启用的 `CAPACITY_BLOCKED`，
§16）；细节写 versioned `error_category`。

### 14.2 Attempt start（provider call 之前必须 durable）

consumer 在 provider call **之前**用一个 transaction：

1. lock invocation `FOR UPDATE`；
2. 若 final 已存在，直接 fence，不调用 provider；
3. 重验 deadline / stale（含 supersede）/ activation / budget；
4. 插入 exact next attempt row（`STARTED`）并把 invocation 置 `ACTIVE`；
5. commit；
6. provider call 才可开始。

任何真实 provider call 都有先行 durable attempt provenance。

### 14.3 Winner atomicity

provider completion 的 finalizer 必须在一个 PostgreSQL transaction 中：

1. durable 更新该 attempt 的 response/error/usage/timestamps/validation/late facts；
2. `SELECT ... FOR UPDATE` invocation；
3. 查询 `ai_decisions.decision_invocation_id` 是否已有 final（unique linkage）；
4. 按固定顺序执行 duplicate → deadline → binding/stale（含 supersede）→
   provider/schema → business validation（PRE-01A §8.2 precedence）；
5. 若 retryable 且 budget/deadline 仍允许，只置 `RETRY_PENDING`，不写 final；
6. 否则插入唯一 `ai_decisions` final、append AI attribution、把 invocation 置
   `FINAL` 并绑定 `decision_id`；
7. commit。

`ai_decisions.decision_invocation_id` 的 unique constraint（partial，仅 non-null 新行）
+ invocation row lock 是 durable winner fence。两个 concurrent completion、
retry/shutdown/restart race 中只有一个 transaction 能插入 final；loser attempt 写
`DUPLICATE_SUPPRESSED` / `LATE_RESULT` audit，绝不改写 winner。

Python lock、queue dedupe、TaskGroup、in-memory set 均不参与 winner correctness。
duplicate completion 不得产生第二个 final decision；late result 只能 audit、不得替换
winner；restart 不得把同一 Invocation 变成新的 logical decision（PRE-01A AC-16/21）。

## 15. Crash Recovery

PostgreSQL 是 correctness authority；process-local queue publication 不是
authoritative delivery fact：

- commit 成功 + enqueue 前崩溃：`ADMITTED` invocation 已 durable ⇒ restart scan
  恢复同一 invocation（原 deadline、原 identity、原 budget），绝不创建新 decision。
- 该 durable 机制即 invocation 表自身的 state machine —— **不**新增 outbox 表、
  **不**引入通用 event bus / framework（最小机制原则）。
- restart 恢复规则：
  - final 已存在：永不 requeue；
  - `ADMITTED/QUEUED` 且未过期：按 durable ordering 分页填充 bounded queue，
    同 invocation；一次最多持有 capacity 个 ref，不建立 unbounded in-memory backlog；
  - `ACTIVE` 且 attempt 无 completion：原 attempt 记 `PROCESS_LOST/ABANDONED`；
    仅当原 joint budget 与 deadline 允许才创建下一 attempt；
  - `RETRY_PENDING`：按原 provider/model/input/deadline 继续；不重建 pair/arm；
  - 已过 deadline / Opportunity invalid / Evidence superseded / activation disabled：
    原 invocation terminalize，zero provider。
- Core recovery/Protection 可先完成并诚实 ready；Gate A readiness 在 advisory
  recovery 完成前为 false。

## 16. Queue / Backpressure Contract

| 项 | 冻结策略 |
|---|---|
| owner | one `AdvisoryIngress` per `RuntimeHost`（Host-owned auxiliary） |
| capacity | positive finite explicit config；unset 时 activation disabled |
| item | frozen `AdvisoryWorkRef { decision_invocation_id, decision_deadline_at }` only |
| ordering | `(decision_requested_at, decision_invocation_id)` ascending；无 response-based priority |
| priorities | Gate A 只有 `NEW_SETUP` 一类；不得与 Position/Plan Review 混合 |
| enqueue | post-commit `put_nowait` / equivalent；绝不 await queue space |
| full policy | **REJECT NEWEST**；不 DROP accepted item、不 COALESCE、不阻塞 producer |
| full durable result | same invocation 原子 terminalize：`CAPACITY_BLOCKED` + diagnostic `ADVISORY_QUEUE_REJECTED`；zero provider call |
| accepted item | queue 一旦接受，不 silent drop；consumer/finalizer 或 restart 必须给出 durable terminal state |
| shutdown | close admission；offer 被拒（admission closed）⇒ invocation 保持 `ADMITTED`，由 restart recovery 处理；不等待新 slot |

REJECT NEWEST 的理由（含 PRE-01B-D1 先例）：scanner lane 已接受「full ⇒ reject
newest input + rejection counter + degraded」（D1 Backpressure Contract：missing a
new opportunity is fail-closed）；advisory 同型 —— Opportunity/pair/invocation
uniqueness 必须保留（coalesce 会合并两个 Opportunity，drop 会删除实验 denominator，
blocking 会反压 scanner/provider）。rejection 仍保留 exact invocation/pair audit。

**Queue rejection ≠ durable admission rejection**：durable admission rejection 发生在
admission transaction（staging 失败 / admission-time stale ⇒ 无 invocation）；queue
rejection 发生在 admission 已 durable 之后（⇒ 同 invocation terminalize，显式留在
denominator）。二者在 telemetry 与 durable state 上都必须可区分。

queue full handling 的 durable terminal transaction 若因 DB failure 未提交，invocation
保持原 state；这不是已完成的 rejection。Advisory 立即 fail closed，restart 按 durable
state 恢复并在原 deadline 下重新裁决。

无 coalescing（identity safety 未被形式化证明前禁止）。

## 17. Deadline / Cancellation Contract

### 17.1 Deadline authority（相对旧 draft 变更）

- `decision_deadline_at = decision_requested_at + explicitly_configured_absolute_budget`。
- **`decision_requested_at` 的 authority = Invocation 自身 admission 时（admission
  transaction 内）写入的 durable timestamp** —— 不是对 Evidence `created_at` 的事后
  读回，不是 dequeue/restart/provider-call 时间。
- duration 未配置（Human Decision B，§25）时 Gate A 不能 active；I2 可实现 disabled
  path / test injection，不得给 production 猜默认值。
- PRE-01A 冻结语义保持：absolute、attempt 1 前固定、所有 retry 共享、per-attempt
  timeout 不能延长它。

**为何 admission timestamp 是正确的 latency-budget origin（任务 §17 论证义务）**：
advisory latency budget 界定的是「系统为一个**已被承认的决策请求**还剩多少时间」，
其自然原点是 admission 点本身；又因为 admission 与 Evidence revision 的持久化原子
（同一 G2 formal transaction，§8.2），admission timestamp 在当前一切合法路径上与
Evidence 创建时刻**同一 transaction 语境**（无观测差异），同时保持 invocation
self-contained —— restart/recovery 不需要读回 Evidence 行即可重放 deadline，也不可能
为一个旧 invocation 重新 mint 一份完整 budget。若未来某获批批次引入 deferred
admission（admission 与 Evidence 创建解耦），Evidence 年龄在 admission 时点的检查必须
作为显式 stale 规则另行设计；本契约不预建该规则（不加投机防御）。

### 17.2 Propagation（PRE-01B-D1 AI Deadline Contract 落地）

- producer、durable Invocation、queue item（ref 内）、consumer、每次 Attempt、
  provider call 传递/重读**同一** immutable UTC absolute `decision_deadline_at`。
- 每个边界用 accepted clock 计算剩余时间并一次性映射为 AnyIO monotonic cancel scope
  （`fail_after` / equivalent）。
- enqueue/dequeue/before-call 已过期：zero provider call，terminal
  `STALE_DECISION / DEADLINE_EXPIRED`。
- provider 返回时已过期：不能增加风险；late-result semantics（audit only，不能赢
  final）。
- retry 共享 deadline；conservative remaining-time/cost/attempt check 不通过则不启动
  新 attempt；per-attempt timeout 取 `min(configured_per_attempt_timeout, remaining)`。

## 18. Retry / Failure Matrix

沿用 PRE-01A-D1 §8/§9 accepted taxonomy（transport/validation 分离、joint
deadline/attempt/cost、失败不得增加风险）。Gate A 落地：

| Failure class | Retry? | Final status / diagnostic | Durable provenance | Risk effect |
|---|---|---|---|---|
| transport retryable | 仅显式分类、attempt/deadline/cost budget 均允许 | exhaustion 时 `INVALID_SCHEMA / TRANSPORT_FAILURE + RETRY_EXHAUSTED` | every attempt | zero |
| provider transient/server unavailable | 同上 | `INVALID_SCHEMA / PROVIDER_UNAVAILABLE` | every attempt | zero |
| rate limit | 仅 server/provider 明确 retryable 且 deadline 容纳；无无限 backoff | `INVALID_SCHEMA / RATE_LIMIT` | every attempt | zero |
| schema/partial/malformed repairable | validator 明确 repairable 时才允许 validation retry | `INVALID_SCHEMA / SCHEMA_FAILURE\|PARTIAL_RESULT\|MALFORMED_OUTPUT` | raw/normalized validation facts | zero |
| business validation repairable | 仅预先枚举的可修正格式/数值关系 | `INVALID_BUSINESS / exact reason` | full reasons | zero |
| unsupported/hallucinated evidence | NO | `INVALID_BUSINESS / UNSUPPORTED_EVIDENCE` | yes | zero |
| refusal | NO | `INVALID_SCHEMA / REFUSAL` | yes | zero |
| auth/permission | NO；subsystem Gate A fail closed | `INVALID_SCHEMA / AUTH_PERMISSION` | yes | zero |
| invalid request/schema capability/model | NO；activation config invalid | `INVALID_SCHEMA / INVALID_REQUEST` | yes | zero |
| deadline expiry | NO | `STALE_DECISION / DEADLINE_EXPIRED` | yes | zero |
| Evidence superseded | NO | `STALE_DECISION / EVIDENCE_SUPERSEDED` | yes | zero |
| retry exhaustion | NO | 最后 failure status + `RETRY_EXHAUSTED` | all attempts | zero |
| cancellation | NO（restart 另按原 invocation/budget 裁决） | `INVALID_SCHEMA / CANCELLED`，或 process-loss attempt audit | yes | zero |
| late result | NO | `STALE_DECISION / LATE_RESULT` 或 loser audit | yes | zero |
| duplicate completion | NO | winner 不变；`DUPLICATE_SUPPRESSED` | loser attempt yes | zero |
| internal invariant/hash/fence failure | NO；Advisory subsystem fail closed | 无 provider 或 terminal invariant failure；不得伪造 valid | sanitized durable evidence where possible | zero |
| queue rejected | NO | `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` | invocation/final yes | zero |
| admission staging failure | n/a（无 invocation） | 无 final row；counter + `ADMISSION_STAGING_FAILED`；subsystem `FAIL_CLOSED` | G2/Evidence 照常 commit | zero |

无任何 failure 触发 baseline BUY、自动 participate、TradePlan fallback 或 deterministic
fake-AI substitution；AI failure ⇒ treatment 侧按 PRE-01A §15 记 `NO_LONG` 语义入
operational denominator，但不因此产生任何经济动作。

## 19. Stale Matrix

六类 stale 判定相互独立，不得折叠成一个 boolean：

| 维度 | Authority | 含义 |
|---|---|---|
| Evidence revision superseded | durable `edge_opportunity_evidence`（同 opportunity 存在更高 revision） | §10 |
| Opportunity eligibility lost | formal Evidence `expires_at` + durable current G2 `symbol_states.state/state_version` | setup 已失效 / normalize / version moved |
| market freshness lost | frozen Evidence `reference_data_status`（`OK/REFERENCE_MISSING/REFERENCE_STALE`）+ snapshot market facts | Opportunity 仍存在，但 Gate A no-call，显式计入 denominator |
| Decision Snapshot / input-binding invalid | `snapshot_payload_hash` + `input_binding_digest` + exact `evidence_hash`/`feature_snapshot_hash` | payload corruption / misrouting / incompatible binding；critical invariant |
| experiment config mismatch | invocation self-contained binding vs current activation | activation disabled / definition changed（新 experiment_id lineage） |
| deadline expired | immutable `decision_deadline_at` | invocation latency budget 耗尽，与 business expiry 不同 |

| 时点 | 必须动作 |
|---|---|
| stale before enqueue | 不入 queue；同 invocation terminalize，zero provider |
| stale while queued | dequeue durable re-read 后 terminalize，zero provider |
| stale immediately before provider | attempt-start transaction 拒绝，zero provider |
| stale during provider call | 不新增 market subscription / second event bus；response 后 finalizer durable re-read 判 stale；可 best-effort cancel，cancellation 不是 authority |
| valid response 后、finalization 前变 stale | finalizer transaction 判 `STALE_DECISION`（含 `EVIDENCE_SUPERSEDED`），valid response 只留 attempt audit，不能赢 final |

每个 case 显式给出：durable state（terminal row + diagnostic）、provider call yes/no、
audit retention（attempt audit 保留）、economic effect = **ZERO**。所有 stale outcome：
zero risk increase。

## 20. Shutdown / Restart

RuntimeHost 拥有 AdvisoryIngress lifecycle；关闭动作落在 PRE-01B-D1/I1 已接受的
shutdown 顺序的 step 2 槽位（「close/cancel new advisory work」—— I1 实现为 no-op
注释，本设计填充该槽位）：

1. Host 设 `advisory_admission_open=false`，拒绝新 post-commit offer（offer 被拒 ⇒
   invocation 保持 `ADMITTED`，交 restart recovery）。
2. 停止从 durable admission 向 queue 补充；不再启动新 attempt。
3. cancel active provider I/O；取消仅作用于 Advisory nested scope，不能传播到
   safety/protection siblings。
4. 对 bounded queue 中未开始项在 Host 剩余 shutdown deadline 内写 `CANCELLED` final；
   已开始项完成 attempt cancellation audit。写入受 D1 graceful window（30s）约束，
   仅 short DB cleanup 可 shielded。
5. 若 DB/时间不足：保留非 terminal durable state，记录 subsystem shutdown failure，
   立即让出 Protection cleanup；不得无限 drain、不得消耗 D1 已接受的 Protection
   cleanup window。
6. nested workers 全部结束后 wrapper 向 Host acknowledge；engine 仍由 Host 最后 dispose。

选择 **cancel，不做 provider drain**。无 detached daemon、无 in-process restart
supervisor（沿用 I1 fatal matrix）。

## 21. Health / Readiness

### 21.1 Minimum surface

```text
activation_level: DISABLED | GATE_A_SHADOW | GATE_B_PAPER
state: DISABLED | STARTING | RECOVERING | ACTIVE | DEGRADED | FAIL_CLOSED | STOPPING | STOPPED
queue_size / capacity / high_water
admitted / admission_staging_failed / queue_rejected / expired
active_attempts / completed / failed / timed_out / cancelled
late_results / duplicate_fenced
last_success_at / last_failure_at / last_failure_category
recovery_pending
provider_configured (identity only; no secret)
```

只保留 current snapshot、monotonic counters、high-water 与 bounded error samples；
不构建 metrics platform / unbounded time series。

### 21.2 Readiness split（显式裁定：DISABLED vs GATE_A_SHADOW）

- `DISABLED`：AdvisoryIngress 不构造（无 provider/consumer）；`AI_AUXILIARY` 维持
  I1 现状（`DEGRADED/ai_reevaluation_disabled` 类语义），对 RuntimeHost overall
  readiness **无影响**。
- `GATE_A_SHADOW`：AdvisoryIngress degraded / `FAIL_CLOSED`（含 admission staging
  failure、provenance persistence failure）**只**影响 Gate A readiness
  （`AI_AUXILIARY` 组件置 unavailable/degraded + 关闭新 advisory admission），
  **不**影响 Core readiness / Protection / risk gate —— I1 已验证 `AI_AUXILIARY`
  不在 Core readiness 阻断合取内，本设计保持该性质。
- Gate A Shadow provider failure（ordinary transport/refusal/validation/timeout）：
  仅 terminalize 单个 invocation，worker 继续，**must not disable Protection**；
  provenance/invocation persistence failure：**must fail closed for new advisory
  admission**。
- shared DB/singleton/engine ownership failure 仍按 I1 Host fatal matrix —— 那是
  Host failure，不被「降级」为 AI failure。

## 22. Gate A / Gate B Boundary

唯一 activation config：

```text
advisory_activation_level = DISABLED | GATE_A_SHADOW | GATE_B_PAPER
```

- default = `DISABLED`。
- I2 只可实现/接受 `DISABLED` 与 `GATE_A_SHADOW`（wiring 完成不等于 active；
  Human activation 前保持 disabled）。
- 未经独立 Gate B implementation + Human Approval，配置 `GATE_B_PAPER` 必须
  startup fail closed（不自动降级/解释成 Gate A，不创建 plan）。

| Level | Allowed | Forbidden |
|---|---|---|
| Gate A | real provider call（另行激活后）、decision/provenance/AI attribution | TradePlan、Risk、Execution、Position、Account、Ledger mutation |
| Gate B | 仅在独立批准后，一条 predeclared authoritative arm 进入 existing deterministic chain（`DecisionValidator`/`TradePlanManager`/`SystemRiskGate`/Paper Execution 不变） | baseline fallback、绕过 validator/risk/execution/accounting/protection、Live |

Gate A wiring 完成不等于 Gate A active；Gate A active 不等于 Gate B；Gate B 不等于
Gate C / Live。Gate A wiring 不得自动解锁 TradePlan/Risk/Execution/Accounting/
Protection-controlled economic activation。

## 23. SE-02D Boundary

### 23.1 当前状态

`SE-02D-I01` / `SE-02D-I02` = `ACCEPTED / COMPLETE`；`SE-02D Production` =
`IN PROGRESS`（population grouping + 调用 I01 `aggregate()`、aggregate/API/product
integration、historical revision-as-of 未实现）。

### 23.2 SE-02D-I02 runtime reuse = NONE（显式裁定）

AdvisoryIngress **不** import / 调用：`aggregation_snapshot.py`、
`CurrentSnapshotRevisionReader` / `CurrentSnapshotProjection` /
`CanonicalScopeFacts`。理由：I02 是 Edge/Expectancy 的 current-snapshot 投影 ——
`REPEATABLE READ READ ONLY`、aggregation-oriented、Outcome-chain folding、
statement-timestamp `as_of`；live advisory decision-ingress 与之耦合只会扩大 blast
radius 与延迟，无 correctness 收益。

**概念性复用（conceptual reuse）**的已接受语义：

1. revision chain 按 chain 校验（supersedes 链、同-opportunity scope integrity 由
   DB `uq_edge_evidence_opportunity_revision` + `fk_edge_evidence_supersedes` 保证）；
2. canonical head = validated chain 的最高 revision（advisory 的 supersede 检测只需
   「同 opportunity 存在更高 revision」这一最小 durable 查询，§10.2，不需要完整
   folding projection）；
3. integrity conflict ⇒ fail closed（`SnapshotIntegrityError` 先例 ⇒ advisory
   invariant failure / stale，conflict 标识符沿用单元素元组铁律）；
4. versioned canonical JSON / 身份编码纪律（无未转义 join、无 digest 作语义
   equality authority）；
5. 「fold complete revision chains before membership」（D01）在 advisory 侧的对应
   物 = supersede 判定永远基于 durable 最高 revision，而非任何 process-local 视图。

### 23.3 禁止事项

D2 / I2 不得：推进 SE-02D、实现 population grouping、调用 `aggregate()`、定义 Gate C
threshold、声明 profitability/edge、决定 superseded-revision pair 的实验分母计数
（该问题归 SE-02D / Gate C aggregation contract）。Gate C 仍需另行接受的 SE-02D
expectancy evidence。

## 24. Schema Decision

### 24.1 REUSE AS-IS

- `edge_opportunity_evidence`：Opportunity/Evidence durable identity、revision chain、
  hash、snapshot source、expiry、reference 三态 authority（SE-02A/ARCH-FIX 契约原样）。
- G2 event/timeline/state/transition/candidate/observation tables 与 transaction 语义。
- `edge_attribution_events` schema/identity：append-only lineage；不是
  invocation/final fence。
- Trade/Risk/Execution/Position/Account/Ledger schema：Gate A 完全不写。

### 24.2 REUSE WITH MINIMAL EXTENSION

`decision_snapshots`（新 Shadow rows 增加 queryable binding facts，legacy rows 兼容）：

```text
opportunity_id, evidence_id, evidence_revision, evidence_hash,
feature_snapshot_hash, market_type, snapshot_payload_hash, input_binding_digest,
decision_requested_at, decision_deadline_at
```

`ai_decisions`（继续作唯一 logical final，最小增加）：

```text
decision_invocation_id（partial UNIQUE for non-null new rows）,
input_binding_digest, experiment_id, pair_id, arm_id,
provider_id, configured_model_id, provider_reported_model_id nullable,
output_digest, error_category, finalized_at
```

legacy `decision_id(snapshot_id, model)` 只保留给既有非-Advisory 路径；新 Gate A rows
必须使用 invocation-derived `decision_id`（PRE-01A §6.3 物理方案 2：separate
invocation-aware final identity + one-to-one linkage）。migration/backfill 策略属 I2
design review；不得把旧 row 伪造为新 invocation。

### 24.3 NEW MINIMAL PERSISTENCE REQUIRED

`advisory_decision_invocations`（一 row / logical invocation）：

```text
decision_invocation_id PK
snapshot_id FK
opportunity_id / evidence_id / evidence_revision / evidence_hash / feature_snapshot_hash
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

### 24.4 Necessity proof（对照当前 schema）

当前 schema（`db/models.py` 实测）无 invocation/attempt/experiment/pair/arm 持久层、
`decision_snapshots` 无 binding/hash/deadline、`ai_decisions` 无 invocation linkage
与 unique final fence —— PRE-01A AC-21/22 与 winner fence（§14.3）在现有表上不可表达；
两张最小新表 + 两处最小扩展是满足契约的最小集。不新增 generic workflow、event bus、
saga、job、provider registry 或 metrics table；`ai_decisions` unique linkage 即 final
winner row，不建第三个 final table。**本契约不创建 migration**。

## 25. Human Decision Pack

### 25.1 Classification

| 未决项 | 分类 | Safe I2 posture |
|---|---|---|
| joint total attempts / transport retries / validation retries | **B** | positive explicit config；unset ⇒ Shadow activation rejected；tests inject boundary values |
| per-attempt timeout | **B** | interface/enforcement implemented；unset ⇒ disabled |
| absolute decision deadline duration | **B** | field/digest/propagation implemented；unset ⇒ disabled |
| per-decision token/cost budget | **B** | nullable usage provenance + fail-closed budget checker；unset ⇒ disabled |
| advisory queue capacity / finite worker count | **B** | bounded implementation accepts explicit injected values；production activation unset ⇒ disabled |
| exact provider/model | **B** | provider-neutral interface only；I2 candidate 不含 real constructor |
| raw provider envelope retention size/duration/access | **B** | retention OFF / columns NULL；normalized/redacted required provenance 仍保存 |
| Gate A Shadow observation window / sufficiency thresholds | **C** | collection counters implemented；no PASS threshold invented |
| superseded-revision pair 的实验分母计数规则 | 归 SE-02D/Gate C aggregation contract（非 D2 决策；记录边界，不算 Human Decision Pack 数值项） | shadow 照常记录 per-invocation facts |

### 25.2 Human Decisions Blocking I2 Implementation

`NONE` —— 前提：I2 必须接受「production activation disabled when required explicit
config is unset」，且只用 fake/injected provider 做 deterministic tests。**Safe I2
implementation with activation OFF、required config unset、fake/injected provider only
是可行的**（显式声明，任务 §29 要求）。若 I2 被要求同时真实激活 Gate A，则上表 B 项
立即变成 blocker。

### 25.3 Human Decisions Blocking Real Provider Activation

1. exact Single Primary Provider + exact model/deployment identity；
2. total/transport/validation attempt limits；
3. per-attempt timeout + absolute deadline duration；
4. token/cost budget 与 usage-unavailable policy；
5. queue capacity + finite worker count；
6. raw envelope retention/access policy；
7. selected provider/model 的 strict structured output、refusal、usage、request-id
   能力验收（PRE-01A §11）。

### 25.4 Human Decisions Blocking Gate A Acceptance Only

- minimum Shadow observation window；
- latency/deadline miss、failure/refusal/schema/stale/late/duplicate/cost 与
  coverage 的 sufficiency/pass thresholds。

## 26. Implementation Batch Proposal

### PRE-01B-I2 — AdvisoryIngress Core / Shadow-Safe Durable Path

一个最小 vertical slice：

1. §24 的 migration + minimal models/constraints；
2. G2 formal transaction 内的 savepoint-isolated staged invocation + typed
   post-commit ref（`persist()` 返回值扩展）；
3. Host-owned bounded AdvisoryIngress queue / nested auxiliary lifecycle（D1
   shutdown step 2 槽位）；
4. adapted immutable snapshot/input builder（binding 含
   evidence_hash/feature_snapshot_hash/deadline）；
5. durable attempt-start / final winner transactions（invocation lock + unique
   final linkage）；
6. fake/injected provider only，activation default `DISABLED`；
7. identity version literals 冻结清单（§12.2）；
8. deterministic rollback / savepoint-failure / full / deadline / stale（含
   supersede）/ race / shutdown / restart / adverse tests；
9. focused G2/G3/SE-02B/RuntimeHost regression + real disposable PostgreSQL
   transaction evidence（含 admission staging 失败时 G2/Evidence 照常 commit 的
   专项证明）；
10. zero Real API call、zero Gate A activation、zero Gate B/economic mutation。

Real provider adapter selection / contract validation 与 Gate A activation 为后续
独立获批 batch/gate；不得并入 I2。

## 27. Acceptance Criteria（I2 Candidate ready for review 的独立证据要求）

1. qualifying formal Evidence + invocation/snapshot 同 transaction 原子；外层失败 ⇒
   queue/provider/rows 全为零。
2. **Admission staging 失败 ⇒ savepoint 内回滚，G2 facts + Evidence 照常 commit，
   无 invocation、无 phantom、counter/FAIL_CLOSED 记录**（新，对应 §8.3）。
3. Capture Anchor without formal Evidence 永不进入 Advisory。
4. enqueue 只发生在 commit 后；crash-after-commit-before-enqueue 恢复同一 invocation。
5. queue object 只有 frozen ref；consumer durable re-read 并验证全部
   binding/hash（含 feature_snapshot_hash）。
6. queue bounded；full = durable REJECT NEWEST（`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`）；
   no block/drop/coalesce；queue rejection 与 durable admission rejection 在 durable
   state/telemetry 上可区分。
7. Protection lane 在 queue full、slow provider、provider timeout、admission staging
   failure、Advisory critical failure 下持续工作。
8. Gate A consumer constructor/call graph 无 TradePlan/Risk/Execution/Position
   mutation handle。
9. Gate A adversarial valid LONG response 仍产生 zero TradePlan/economic mutation；
   `G3Workflow`、`TradePlanManager`、`persist_trade_plan` 在 Gate A call count = 0。
10. one invocation identity collision-free 绑定 exact
    opportunity/evidence(revision/hash/feature_snapshot_hash)/snapshot/experiment/
    pair/arm/versions/model。
11. Invocation 的 Evidence binding immutable：supersede 场景下旧 invocation 只能
    terminalize（`EVIDENCE_SUPERSEDED`），任何改写/换绑/digest 重写测试必须失败；
    N+1 qualifying 时另立新 invocation。
12. retry same invocation/deadline/input；attempt identity 独立且
    start-before-provider durable。
13. two concurrent completions、retry/shutdown/restart race 只产生一个
    `ai_decisions` final；late/duplicate loser 保留 attempt audit 但不能覆盖 winner。
14. all expiry/stale phases（六维度 × 六时点）匹配 §19，no provider/no risk 精确。
15. restart 对 ADMITTED/QUEUED/ACTIVE/RETRY_PENDING/FINAL 均匹配 §15。
16. failure matrix 全部有 targeted tests；无 baseline fallback / fake-AI substitution。
17. deadline authority/propagation 匹配 §17：admission timestamp 持久化、retry 不
    重置、attempt timeout 不延长。
18. Gate A health fail closed 不取消/阻塞 safety sibling；shared Host fatal 沿用 I1；
    DISABLED 与 GATE_A_SHADOW 的 readiness 影响按 §21.2 裁定。
19. activation default disabled；缺任何 B 类 config 或请求 Gate B 均 startup fail
    closed。
20. exact allow-list tables 之外零写；Production/Live/Real API = zero。
21. no G2 state-machine、G3 economic、Risk、Execution、Accounting、Protection
    semantic regression；SE-02D 边界（§23.3）零触碰（`aggregation_snapshot.py`
    import count in advisory path = 0）。

## 28. Risk Register

| Risk | Treatment |
|---|---|
| 把 Capture Anchor 当正式 Opportunity | producer 必须验证 exact Evidence row/invocation FK；anchor-only ignored |
| G3Workflow 产生 TradePlan | Gate A 禁用其类型/handle + call-count + table-delta tests |
| G2 transaction rollback 却已 enqueue | queue touch 严格 post-commit；typed result 在 transaction exit 后返回 |
| commit→enqueue crash 丢任务 | durable `ADMITTED` scan，same invocation recovery |
| admission staging 失败摧毁 G2 truth（旧 draft 风险） | savepoint 隔离（§8.3）+ 专项 AC-2 证明 |
| queue full 删样本/阻塞行情 | REJECT NEWEST + durable final；non-blocking offer；scanner/protection lanes 隔离 |
| queue rejection 被误分类为 provider failure | `CAPACITY_BLOCKED` 映射 + 与 admission rejection 的 durable 区分 |
| canonical head 误作 admission identity | §9 显式区分 + advisory path 禁 import aggregation_snapshot（AC-21） |
| supersede 后旧 Invocation 被改写 | identity immutable + supersede stale 规则 + 改写负向测试（AC-11） |
| legacy decision_id collision | invocation-derived final id + partial unique linkage |
| two provider completions 双 winner | invocation row lock + unique final constraint + one transaction |
| retry 重置 deadline/arm | immutable invocation facts；attempt 不得覆写 |
| restart 用新 config 重配旧 decision | invocation self-contained；old row 不读新 experiment/model 重建 identity |
| provider alias/model drift | configured + provider-reported exact identity 分别保存；unknown != configured |
| Advisory failure 拖垮 Protection | nested auxiliary wrapper catches/classifies；Core/Gate A readiness 拆分 |
| raw envelope 泄密/无限增长 | retention OFF until approved；redaction + size/TTL/access decision required |
| Shadow result 被未来代码误接 economic path | activation enum、constructor allow-list、Gate B startup reject、table mutation tests |
| 身份编码非单射 | versioned canonical JSON；禁未转义 join；conflict 标识符单元素元组 |
| SE-02D 分母问题被 D2 越权决定 | 显式归 SE-02D/Gate C（§23.3）；D2 只保 per-invocation identity |

## 29. Explicit Non-Goals / Overengineering Check

明确不设计/不引入：Kafka、Redis、Celery、RabbitMQ、Kubernetes、microservice split、
LangGraph、generic agent runtime、LiteLLM Router、model voting、automatic provider
fallback、distributed workflow engine、new event bus、generic saga framework、第二套
完整 G3、第二个 RuntimeHost、in-process process supervisor、outbox 通用框架、
metrics platform。

默认并保持：Modular Monolith、one RuntimeHost、one process、bounded in-process
queue、PostgreSQL durable authority。当前 repository truth 足以满足 correctness；
无证据需要扩大基础设施。

## 30. Design Verification / Candidate Verdict

本 Artifact 的验证边界为 repository/source/diff 静态检查 + 实时 git 真值：

- Global Protocol v1.1.0 / ACCEPTED @ `07e2df8…`（ls-remote 实测）；
  `origin/main = main = d1e5534`（ls-remote / rev-parse 实测）；无 baseline drift；
- 两份 Accepted Contracts（PRE-01A-D1、PRE-01B-D1）完整重读；SE-02D-I02 真值
  （`aggregation_snapshot.py` + 测试 + 两份 dev_log）重读；DECISIONS.md 相关条目
  （PRE-01A-D1 V1 / PRE-01B-D1 V1 / PRE-01B-I1 V1 / SE-02D-D01 V1 / I01 澄清）重读；
- G2 formal transaction / EventRuntime / capture+qualifies / G3 Workflow·Decision·
  Queue / RuntimeHost ownership·isolation·shutdown / DB schema / attribution 调用点
  在 latest main 上实读复核（§1.4）；
- 664207a→d1e5534 delta 实测分类（§6）；
- production/tests/migration/schema/runtime/state docs = zero change；
- Candidate 必须由 Independent Reviewer 重新读取 source/diff 后裁决；本作者不
  Human Accept。

```text
Producer Boundary = formal edge_opportunity_evidence + savepoint-isolated staged
                    invocation（同 G2 formal transaction commit，post-commit 发布）
Admission Evidence Identity = admission transaction 内 staged 的 exact Evidence
                    revision（opportunity/evidence_id/revision/evidence_hash/
                    feature_snapshot_hash），不是 SE-02D canonical head
Superseding Evidence Policy = 旧 Invocation immutable 且 stale（EVIDENCE_SUPERSEDED）；
                    qualifying N+1 另立新 invocation；禁止改写/换绑/rebinding
Gate A Consumer = ShadowAdvisoryDecisionPath with provenance-only write allow-list
G3Workflow = DO NOT USE IN GATE A
Invocation Authority = deterministic AdvisoryAdmissionWriter（attempt 1 前，
                    admission transaction 内）
Durable Fence = PostgreSQL invocation row lock + unique ai_decisions invocation linkage
Queue = bounded / non-blocking / REJECT NEWEST / durable CAPACITY_BLOCKED terminal
Deadline Authority = admission-time durable timestamp + explicitly configured budget；
                    immutable、retry 不重置、attempt timeout 不延长
Stale Policy = 六维度 × 六时点矩阵，全部 zero risk increase
Shutdown / Restart = D1 step-2 槽位、cancel-not-drain、durable ADMITTED recovery
Gate A vs Gate B = explicit activation level；Gate B startup fail-closed until approval
SE-02D-I02 Runtime Reuse = NONE（仅概念性复用其 canonicalization 语义）
Schema = reuse evidence/attribution + minimal extension of snapshot/final +
         two new minimal tables；无 migration（属 I2）
I2 Numeric Blockers = NONE when activation remains disabled and config explicit/unset
Artifact Status = CANDIDATE DESIGN / PENDING INDEPENDENT REVIEW
```
