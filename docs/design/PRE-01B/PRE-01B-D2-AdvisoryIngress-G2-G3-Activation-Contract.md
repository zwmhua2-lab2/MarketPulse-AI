# PRE-01B-D2-FIX-01｜AdvisoryIngress / G2→G3 Activation Contract Review Fix

## Artifact Status

```text
Artifact: PRE-01B-D2 AdvisoryIngress / G2→G3 Activation Contract
Status: FIX CANDIDATE DESIGN
Review: READY FOR INDEPENDENT RE-REVIEW
Human Acceptance: NOT PERFORMED
Task type: DESIGN FIX ONLY / DOCS ONLY
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
Reviewed parent candidate: c0bd0e8145a82372a6322f63369e6467cae9022f
Fix branch: design/pre-01b-d2-fix-01-advisory-ingress-contract
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
| 3 | `decision_requested_at` 权威 = 读回 formal Evidence 的 durable `created_at` | 权威 = **PostgreSQL admission clock 在同一 CTE 中单次捕获的 timestamp**，先进 Evidence admission seed，再原样进 Invocation | Evidence.created_at 不是 accepted clock authority；「same transaction ⇒ 数值相等」无效且已删除；见 §17 |
| 4 | Evidence supersede 仅在 stale matrix 一句带过 | **独立 Evidence Supersede Contract**（§10）+ 明确「N+1 可另立新 Invocation」规则 | SE-02D-I02 新接受语义使 revision-chain / canonical head 成为必须显式设计的边界；PRE-01A-D1 §10 已冻结「新 Evidence revision ⇒ 新 unit/invocation」 |
| 5 | （无此节；旧 draft 早于 I02） | **Admission Evidence vs Canonical Evidence Head 区分**（§9）+ SE-02D-I02 runtime reuse = NONE（§23.2） | 任务 Critical Question A；I02 是 aggregation-oriented REPEATABLE READ 只读投影，与 live decision-ingress 不耦合 |
| 6 | `input_binding_digest` 不含 `feature_snapshot_hash` | **纳入** `feature_snapshot_hash` | 任务 §9 要求逐项评估五个 identity 字段；feature snapshot hash 是 Evidence 身份的组成部分（schema 实测存在于 `edge_opportunity_evidence`） |

### 0.4 FIX-01 授权与边界

Independent Review 对 parent candidate `c0bd0e8145a82372a6322f63369e6467cae9022f`
的结论为 `FAIL — FIX REQUIRED`（P0 = NONE；P1 × 5；design P2 × 1）。
FIX-01 只处置这 6 项，不修复 process P2，不改动已通过区域，不执行实现/
测试/迁移/激活。`CLOSED` 仅代表本 Candidate 声称设计处置完成；最终
closure 归 Independent Reviewer，Human Acceptance 未执行。

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

FIX-01 于 2026-09-16 重新执行 realtime check：

| FIX-01 项 | 实测事实 |
|---|---|
| Reviewed parent candidate | `design/pre-01b-d2-advisory-ingress-contract-r1 = c0bd0e8145a82372a6322f63369e6467cae9022f`（local/remote 一致，未移动） |
| FIX branch/base | `design/pre-01b-d2-fix-01-advisory-ingress-contract` from exact `c0bd0e8...` |
| Current `main` / remote | `44df66603e6bdba1f3f80c21be5b30c295e4a20a`（local/origin/ls-remote 一致） |
| `d1e5534..main` drift | 只有 `aa2232e` + `44df666`，仅修改 SE-02D-I02 final-acceptance incident disclosure/closure dev_log |
| Drift classification | **ORTHOGONAL**；未触及 G2/G3/RuntimeHost/Opportunity/Evidence/DB/schema/PRE-01A/PRE-01B/SE-02D identity semantics |

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
13. Gate-A-eligible Evidence revision 不得因 snapshot/Invocation staging 失败而从
    experiment/provenance accounting 中永久消失；它必须可查询为已创建、
    可恢复，或按原 deadline 终态失败（见 §8.3）。

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
| existing AI decision persistence（`decision_snapshots` / `ai_decisions`） | `REUSE WITH MINIMAL EXTENSION` | snapshots 继续存 frozen input；`ai_decisions` 只存 normalized provider artifact 并强制 Attempt origin；Invocation 五个 final fields 是唯一 terminal authority（§14/§24） |
| `RuntimeHost` TaskGroup / lifecycle | `ADAPT` | Host 构造/启动/停止 Advisory（D1 shutdown step 2 预留槽位）；一个受控 wrapper child 拥有内部 finite workers；Advisory 异常在 wrapper 内分类，不得取消 safety siblings；沿用 I1 fatal matrix，不自建 restart loop |
| existing attribution identity（`EdgeAttributionRecorder`） | `REUSE` | exact `opportunity_id/evidence_id` lineage、append-only、caller-transaction pattern 保持；payload 可增 invocation/experiment facts；attribution 不是 winner authority |
| `PostgresG2Repository` formal transaction | `ADAPT` | 复用 G2+Evidence 原子提交；Evidence admission accounting/seed 在 savepoint 外，snapshot + invocation + state flip 在 savepoint 内；queue 只在 commit 成功后触达；`persist()` 返回 typed result |
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
2. 每个 formal Evidence revision 在写入时必须同时得到可持久的 admission
   classification：非 qualifying 为 `NOT_ELIGIBLE`；Gate A 未启用为
   `GATE_A_DISABLED`；Gate A 已启用且 qualifying 时，Evidence 行在**外层
   G2 transaction** 先持久 `RECOVERY_REQUIRED / ADMISSION_STAGING_FAILED`
   与 canonical `AdvisoryAdmissionSeed`（§8.3）。该行本身就是「资格已存在但尚未被
   Invocation 记账」的 PostgreSQL authority；不依赖 process-local counter。
3. Host-composed 并注入的 `AdvisoryAdmissionWriter` 只对上述
   `RECOVERY_REQUIRED` Evidence 在**同一 transaction 的 SAVEPOINT 内**：
   - 使用 exact `EvidenceRevision`、seed 和同 transaction 的 resulting
     SETUP/state facts；
   - 构造 deterministic snapshot / input binding / invocation identity；
   - 写 `decision_snapshots` 与
     `advisory_decision_invocations(state=ADMITTED)`；
   - 在同一 SAVEPOINT 内将 Evidence accounting 更新为
     `INVOCATION_CREATED` 并绑定 `decision_invocation_id`；
   - 不调用 provider、不触达 queue、不写 final、不写任何
     TradePlan/economic table。
4. `session.begin()` 正常退出（commit）后，`persist()` 返回 typed result（含 frozen
   `AdvisoryWorkRef`，若 admission 成立）。
5. `EventRuntime` 仅在 `persisted=true` 且持有 ref 后，调用 Host-owned
   `AdvisoryIngress.post_commit_offer(ref)`。
6. `post_commit_offer` 使用 non-blocking `put_nowait`/equivalent；consumer 只收到 ref。

**Phantom proof**：queue 只在 commit 后被触达；staging 失败（savepoint 回滚，§8.3）或
transaction 失败时 ref 不存在，步骤 5 永不执行 ⇒ 不存在「queue 已看见但 DB 不存在」
的 phantom advisory work。Capture Anchor 可能仍按 accepted contract durable，但它没有
formal Evidence/invocation，Advisory recovery 必须忽略它。

**Crash-gap proof**：commit 成功而进程在 enqueue 前死亡时，`ADMITTED` invocation 已
durable；restart scan 恢复**同一** invocation，绝不创建「全新 decision」（§15）。

### 8.3 Admission staging failure polarity（相对旧 draft 的核心变更）

Admission staging 属 critical provenance infrastructure，但其失败**不得**摧毁 durable
G2 market truth。本修复冻结的最小持久 authority 是
`edge_opportunity_evidence` 上的 **Advisory Admission Accounting extension**，而不是
另一个 outbox/service：

```text
advisory_admission_state =
  NOT_ELIGIBLE | GATE_A_DISABLED | RECOVERY_REQUIRED |
  INVOCATION_CREATED | ADMISSION_FAILED_FINAL
advisory_admission_reason_code
advisory_treatment_participation nullable
advisory_admission_seed_version
advisory_admission_seed_digest
advisory_admission_seed (canonical JSONB)
advisory_decision_invocation_id nullable
```

`AdvisoryAdmissionSeed` 在 Evidence insert 之时、任何 SAVEPOINT 之外冻结：exact
Evidence identity，resulting G2 state/config/family/instrument/market facts，Gate activation
level，config epoch id，experiment definition digest/id，pair/baseline/treatment arm ids，
provider/model 与全部 version literals，以及 §17 的单次 DB admission clock、deadline
duration/value。这些值足以在 restart 后以**原 seed**确定性重建同一
snapshot/input/invocation；禁止读当前 config 事后重绑。seed 不进入
`evidence_hash`，不改写 SE-02A Evidence identity/immutable payload。

- 对 Gate A active + qualifying 的 Evidence，外层 insert 先写
  `RECOVERY_REQUIRED / ADMISSION_STAGING_FAILED` + complete seed。在同一未提交
  transaction 中这是一个 fail-safe initial value：成功 SAVEPOINT 会与
  snapshot/invocation 一起将它原子更新为 `INVOCATION_CREATED`；SAVEPOINT
  任一错误会回滚这些 advisory rows/update，外层则提交 G2 facts +
  Evidence + `RECOVERY_REQUIRED`。
- `RECOVERY_REQUIRED` 是可查询、可恢复的 durable state，明确表示
  「Gate-A-eligible Evidence 已存在，admission staging 未完成」；reconciler
  只能使用原 seed 重试。重复 persistence failure 不能把该行终态排除，
  不能创建 provider Attempt，也不能改绑新 experiment/config；它持续
  `RECOVERY_REQUIRED`，Gate A 持续 `FAIL_CLOSED`，直到同一 seed 成功创建
  Invocation，或 DB clock 证明原 decision deadline 已过。后者由 reconciler
  将 Evidence accounting 原子转为 `ADMISSION_FAILED_FINAL /
  ADMISSION_STAGING_FAILED_DEADLINE_EXPIRED`，写
  `advisory_treatment_participation=NO_LONG`，仍无 Invocation/Attempt/AIDecision。
  若连该终态 update 也因 DB 失败无法 commit，诚实状态继续是
  `RECOVERY_REQUIRED`；下次 recovery 重试，不伪造已终态结论。
- `NOT_ELIGIBLE` 与 `GATE_A_DISABLED` 不创建 experiment/pair/arm 或
  Invocation；`INVOCATION_CREATED` 必须有对应 Invocation FK。对于没有 formal
  Evidence 的 G2 event，其非资格事实由 qualifying G2 facts + Evidence 缺席共同
  确定，不伪造 Evidence row。
- process-local counter 仅是 health telemetry，不是 coverage authority。
- 不调用 provider（Invocation 不存在）；不传播为 safety/protection
  sibling cancellation；不影响 Protection / Core Host readiness。
- 外层 transaction 在 staging 之后失败：整体（G2 + Evidence + advisory）原子回滚，
  无 phantom、无半提交。
- Gate A `DISABLED` 时 full writer 不注入；Host 只向 G2 capture context 注入一个
  无 provider/无 persistence handle 的 immutable activation classification，使 qualifying
  Evidence insert 明确写 `GATE_A_DISABLED`。非 qualifying/non-G2-admission 路径写
  `NOT_ELIGIBLE`。这不改 G2 business/qualifies 语义；旧行的 nullable legacy 值不得
  伪造成历史 Gate A classification。

**理由（任务 §12 逐问回答）**：

| 问题 | 裁定 |
|---|---|
| Evidence + accounting + Snapshot + Invocation 能否合法同 transaction？ | 能 —— Evidence accounting 与 Evidence 外层共提交；snapshot + Invocation + `INVOCATION_CREATED` 在 SAVEPOINT 内原子；SAVEPOINT 失败仍留下 `RECOVERY_REQUIRED` |
| 是否不当扩大 Scanner/G2 authority？ | 否 —— G2 formal transaction 只是 **atomicity host**；admission 的 identity/policy authority 属 Host-composed、config-gated 的 `AdvisoryAdmissionWriter`；writer opt-in 注入，Gate A disabled 时 G2 路径不变 |
| AI advisory persistence 是否污染 Scanner core responsibility？ | 旧 draft 会（staging 失败回滚 G2 facts ⇒ AI infra 失败摧毁 market truth）；savepoint 方案消除该污染：Scanner/G2/Edge 真值独立于 AI infra 健康（invariant 12） |
| rollback 能否产生 phantom advisory work？ | 不能（§8.2 phantom proof）；但 qualifying Evidence 不会永久消失于记账，因为 `RECOVERY_REQUIRED` 保留原 seed |
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

1. Advisory admission 绑定 **A**，永不绑定 B。绑定先写入 Evidence 行的
   `AdvisoryAdmissionSeed`，再在成功 SAVEPOINT 中被 Invocation / Decision
   Snapshot 重复绑定。身份字段（全部进入 `decision_invocation_id` /
   provider input provenance / `input_binding_digest`）：
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
   `evidence_revision`），**不**调用 `aggregation_snapshot.py`。用于终态胜者或
   未来经济消费的检查还必须遵守下述共享锁，普通无锁预检仅是早停优化。
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
5. **共享 PostgreSQL serialization authority（关闭 TOCTOU）**：
   - lock target = 被 Invocation 绑定的 exact Evidence row N，即
     `edge_opportunity_evidence(opportunity_id, evidence_revision=N)`；它是现有 Evidence
     chain authority，不创建第二个 opportunity/identity authority。
   - 所有 accepted Evidence supersede writer（当前即 `append_evidence_revision`）在写 N+1
     前必须先 `SELECT` immediate predecessor N `FOR UPDATE`，在持锁时重验
     same-opportunity、adjacent revision 与 existing head，再 insert N+1，持锁到
     commit/rollback。
   - Advisory attempt-start、finalizer，以及未来 Gate B 对该 final 的经济消费，
     均必须先 lock bound Evidence N `FOR UPDATE`，**然后** lock Invocation，
     再 lock/update Attempt；持锁后重读 same-opportunity max revision / supersedes
     chain 和 Invocation final fields。全部路径的锁顺序统一为
     `Evidence N -> Invocation -> Attempt`，禁止反序。
   - 这些事务使用 PostgreSQL `READ COMMITTED`：等待 N row lock 后的下一条
     statement 必须重读新 snapshot。若实现改用更高 isolation 并遇到
     serialization failure，则整个 transaction 失败并在原 deadline 下有界重试；
     禁止使用旧 snapshot 继续 final。
   - 锁仅由 PostgreSQL transaction 在 commit/rollback 释放；Python lock 不参与该不变量。
   - 序列化证明：若 N+1 先获得 N 锁并 commit，finalizer 后获锁后必须
     看见 N+1 并将 N 终态化为 `EVIDENCE_SUPERSEDED`；若 finalizer 先获锁并
     commit，N+1 writer 才能继续，属于下述合法 final-then-supersede。
   - 外部语义依据：PostgreSQL 官方
     [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html) 与
     [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)；
     前者定义 `FOR UPDATE` 等待/事务结束释放，后者定义
     `READ COMMITTED` 每条 command 的新 snapshot。
6. **Final-then-supersede 语义**：N 在当时 current 时完成的 final 及其
   Invocation/Attempt/AIDecision/attribution 永久 immutable audit，N+1 不回写它们。
   N+1 Evidence row 及其 `supersedes_evidence_id=N.evidence_id` 就是「final 之后已被
   supersede」的 durable authority；不增加可漂移的 `actionable=true/false`
   第二权威。任何未来 Gate B 消费者必须在同一 Evidence N lock 下重验
   no-higher-revision，并在同一 transaction 内提交经济授权；否则旧 final
   即 `NON_ACTIONABLE_FOR_FUTURE_ECONOMIC_USE`。Gate A 仍 non-economic，D2 不实现
   Gate B。
7. **生命周期覆盖（任务 §10 清单）**：
   - before queue publication：offer 前置检查 ⇒ 不入 queue，terminalize；
   - while queued：dequeue durable re-read ⇒ terminalize，zero provider；
   - before provider call：attempt-start transaction 拒绝，zero provider；
   - during provider call：best-effort cancel（非 authority）；response 后 finalizer
     durable re-read ⇒ `STALE_DECISION / EVIDENCE_SUPERSEDED`；
   - after provider result / before finalization：finalizer transaction 判 stale，
     valid response 只留 attempt audit，不能赢 final；
   - final 已存在后 supersede 发生：final 不变；新 Evidence chain 事实使它
     对任何未来经济消费 non-actionable，N+1 仍可按规则新 admission。
8. **Denominator 边界**：superseded revision N 的 pair 在实验分母中如何计数
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
ai_decisions (optional invocation/attempt-linked normalized result rows)
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
   instrument_id, market_type, advisory_config_epoch_id, decision_requested_at,
   deadline_duration_ms, deadline_policy_version, decision_deadline_at)`。所有时间字段使用
   §17.1 的 canonical UTC serialization。
4. `experiment_id = H(experiment_definition_version, canonical_experiment_definition)`。
5. `pair_id = H("pre01a-pair-v1", experiment_id, input_binding_digest)`。
6. `baseline_arm_id = H(pair_id, "WITHOUT_AI_BASELINE")`。
7. `treatment_arm_id = H(pair_id, "REAL_AI_TREATMENT")`。
8. `decision_invocation_id = H("advisory-invocation-v1", experiment_id, pair_id,
   treatment_arm_id, input_binding_digest, prompt_version, schema_version,
   treatment_version, configured_provider_id, configured_model_id)`。
9. `attempt_id = H("advisory-attempt-v1", decision_invocation_id, attempt_number)`。
10. logical final-result identity = `decision_invocation_id`；它对成功与失败均唯一。
    仅当终态 Attempt 产生 normalized AIDecision 时，
    `decision_id = H("advisory-final-v1", decision_invocation_id)` 才存在；其
    origin 由强制 `attempt_id` FK 证明，不从 digest/timestamp 推断。

### 12.2 Authority and idempotency

- `AdvisoryAdmissionWriter` 创建 invocation identity（admission transaction 内）；
  provider/model 只被记录，不能回写 identity；provider 永不是本地 identity authority。
- Evidence 行的 `AdvisoryAdmissionSeed` 是 staging 失败时唯一合法恢复输入；
  reconciler 必须重算 digest 并与 seed digest 相等，否则 invariant conflict /
  fail closed，不得用当前 config 补值。
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
  Evidence admission seed 在任何 staging/provider 结果前持久化
  `baseline_policy_version` 与 deterministic
  `baseline_participation=PARTICIPATE_LONG`，使 baseline arm 不是事后推导的隐式标签。
  它不调用 provider、不产生 TradePlan，且不在 AI failure 时升级为 fallback。
- treatment arm 固定为 `REAL_AI_TREATMENT`。
- arm 不得由 response、confidence、盈利结果、retry outcome 或 latency 事后选择。
- Gate A active + qualifying 时，`REAL_AI_TREATMENT` arm 也在 Evidence seed 中
  pre-assigned；后续只记录该预分配 arm 的 participation outcome：
  admission staging failure 在 `RECOVERY_REQUIRED` 时为显式 unresolved（不是漏样），
  只在恢复成功后按 Invocation 结果记账，或原 deadline 过期后以
  `ADMISSION_FAILED_FINAL / NO_LONG` 收口；capacity blocked、
  deadline-before-provider、Evidence superseded、provider failure 均为
  `NO_LONG` + exact reason；valid normalized
  provider result 仅在 direction = `LONG_BIAS` 时为 `PARTICIPATE_LONG`，
  `WAIT/SHORT_BIAS` 为 `NO_LONG`。这些是 per-unit operational facts；
  superseded unit 是否进入 Gate C denominator 仍由 SE-02D 决定。
- `NOT_ELIGIBLE` / `GATE_A_DISABLED` 不被事后改标为 treatment；新配置只能
  创建新 config epoch / experiment lineage，不能回填历史 Evidence。
- baseline result 的未来聚合可引用同一 pair/Opportunity 的 accepted SE-02C outcome；
  I2 不复制 Outcome calculator，也不创建第二套 execution account。
- **SE-02D-I02 不解决 PRE-01A experiment identity**：SE-02D 的 population grouping
  （PopulationKey = family/version/instrument/market/source identity/contract version，
  D01 冻结）与 PRE-01A 的 experiment/pair/arm identity 是两套正交身份；二者不得
  混同，也不得从 AI output 或 population 归属 post-hoc 推导 arm。

## 14. Persistence / Transaction Contract

### 14.1 Invocation lifecycle

```text
ADMITTED -> ACTIVE -> RETRY_PENDING -> ACTIVE -> FINAL
ADMITTED/ACTIVE/RETRY_PENDING -> FINAL (failure/cancel/stale/expired/capacity)
```

本修复**删除 durable `QUEUED`**。Invocation 在 process-local queue ref 存在时仍为
`ADMITTED`；queue 只是 bounded wake-up/dispatch mechanism，不是 durable authority。
consumer 在任何 provider I/O 前以 §10.1 共享锁顺序原子执行
`ADMITTED/RETRY_PENDING -> ACTIVE` 与 Attempt insert。状态是 durable execution state，
不是新 `DecisionStatus`。

### 14.2 Exactly-one authoritative terminal result

Invocation row 是**唯一 logical final-result authority**，不再以「查询最新 Attempt/
`ai_decisions` timestamp」推断结果：

```text
state = FINAL
final_status                 NOT NULL
final_reason_code            NOT NULL
finalized_at                 NOT NULL
final_attempt_id             NULLABLE only for named no-Attempt terminals
final_decision_id            NULLABLE when no normalized AIDecision exists
```

DB constraints 冻结：

1. `state=FINAL` iff `final_status/final_reason_code/finalized_at` 三者全非空；
   non-FINAL 时全部 final fields 必须为 NULL。
2. `final_attempt_id` 含义是「产生终态结果的 Attempt」（失败终态也可有）；
   必须通过 composite FK `(decision_invocation_id, final_attempt_id)` 指向同
   Invocation 的 Attempt。它仅可在预先枚举的 no-provider-Attempt 终态为 NULL：
   `DEADLINE_EXPIRED_BEFORE_PROVIDER`、`CAPACITY_BLOCKED`、
   `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER`、`OPPORTUNITY_STALE_BEFORE_PROVIDER`、
   `ACTIVATION_DISABLED_BEFORE_PROVIDER`、`SHUTDOWN_BEFORE_PROVIDER`。
3. 新 Advisory `AIDecision` row 必须同时持有
   `decision_invocation_id` 与 `attempt_id`；composite FK 证明 Attempt 属于同一
   Invocation。`AIDecision` 只表示已成功 normalized 的 provider result；
   transport/auth/refusal/malformed/pre-provider outcome 只保留 Attempt/final reason，不伪造
   AIDecision。
4. `final_decision_id` 非空时，通过 deferred composite FK
   `(decision_invocation_id, final_decision_id, final_attempt_id)` 指向同 Invocation、同
   final Attempt 产生的 `AIDecision`；因此 `final_decision_id != NULL`
   必然推出 `final_attempt_id != NULL`。该 FK 与 AIDecision 反向 FK 为
   `DEFERRABLE INITIALLY DEFERRED`，使同一 finalizer transaction 可原子提交。
5. terminalization 与 final Attempt update、可选 AIDecision insert、attribution append 必须
   同一 transaction commit；不得先写 final fields 再补链接。
6. `finalized_at` 来自 finalizer transaction 的 PostgreSQL server clock，不使用
   application wall clock，也不用 timestamp 排序选 winner。只有终态获胜 Attempt
   的 normalized result 可插入 Advisory `ai_decisions`；中间 retry/non-winning
   normalized output 只留在 Attempt audit，不占用 final-decision unique linkage。

Named terminal mapping：

| Terminal class | `final_attempt_id` | `final_decision_id` | Authority result |
|---|---|---|---|
| successful valid AI decision | required | required | `VALID / VALID_PROVIDER_DECISION` |
| refusal | required | NULL | `INVALID_SCHEMA / REFUSAL` |
| auth/permission failure | required | NULL | `INVALID_SCHEMA / AUTH_PERMISSION` |
| retry exhaustion | required（last terminal-producing Attempt） | 仅当该 Attempt 产生可持久 normalized result 时 required，否则 NULL | exact last failure + `RETRY_EXHAUSTED` |
| deadline before provider | NULL | NULL | `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER` |
| queue capacity blocked | NULL | NULL | `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` |
| Evidence stale/superseded before provider | NULL | NULL | `STALE_DECISION / exact *_BEFORE_PROVIDER` |
| shutdown before provider | NULL | NULL | `INVALID_SCHEMA / SHUTDOWN_BEFORE_PROVIDER` |
| shutdown cancellation with ACTIVE provider Attempt | required | NULL | `INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT` |

normalized-but-business-invalid 或 provider 返回后才变 stale 的 final 可持有
`final_decision_id`，但其 actionability 仍由 `final_status/reason` 与 §10 supersede
revalidation 决定；AIDecision 存在不等于 actionable。

### 14.3 Attempt start（provider call 之前必须 durable）

consumer 在 provider call **之前**用一个 transaction：

1. lock bound Evidence row `FOR UPDATE`；
2. lock invocation `FOR UPDATE`；
3. 若 final 已存在，直接 fence，不调用 provider；
4. 持 Evidence 锁重验 supersede，再重验 DB-clock deadline / other stale /
   activation / budget；
5. 插入 exact next attempt row（`STARTED`）并把 invocation 置 `ACTIVE`；
6. commit；
7. provider call 才可开始。

任何真实 provider call 都有先行 durable attempt provenance。

### 14.4 Winner atomicity

provider completion 的 finalizer 必须在一个 PostgreSQL transaction 中：

1. `SELECT ... FOR UPDATE` bound Evidence N；
2. `SELECT ... FOR UPDATE` invocation；
3. lock/update final-producing Attempt；
4. 检查 Invocation final fields 是否已存在；
5. 持 Evidence 锁重读 max revision，并按固定顺序执行 duplicate →
   DB-clock deadline → binding/stale（含 supersede）→
   provider/schema → business validation（PRE-01A §8.2 precedence）；
6. 持久该 Attempt 的 response/error/usage/timestamps/validation/late facts；
7. 若 retryable 且 budget/deadline 仍允许，只置 `RETRY_PENDING`，不写 final；
8. 否则按 §14.2 可选插入 `AIDecision`、append attribution，并一次写入
   Invocation 的五个 final fields；
9. commit。

Invocation row lock + final-field completeness constraints + optional
`ai_decisions.decision_invocation_id` unique constraint 是 durable winner fence。两个 concurrent completion、
retry/shutdown/restart race 中只有一个 transaction 能提交 authoritative final fields；loser attempt 写
`DUPLICATE_SUPPRESSED` / `LATE_RESULT` audit，绝不改写 winner。

Python lock、queue dedupe、TaskGroup、in-memory set 均不参与 winner correctness。
duplicate completion 不得产生第二个 final result；late result 只能 audit、不得替换
winner；restart 不得把同一 Invocation 变成新的 logical decision（PRE-01A AC-16/21）。

## 15. Crash Recovery

PostgreSQL 是 correctness authority；process-local queue publication 不是
authoritative delivery fact：

- commit 成功 + enqueue 前崩溃：`ADMITTED` invocation 已 durable ⇒ restart scan
  恢复同一 invocation（原 deadline、原 identity、原 budget），绝不创建新 decision。
- 该 durable 机制即 invocation 表自身的 state machine —— **不**新增 outbox 表、
  **不**引入通用 event bus / framework（最小机制原则）。
- restart 恢复规则：
  - Evidence accounting = `RECOVERY_REQUIRED`：以原 `AdvisoryAdmissionSeed`
    重建同一 snapshot/invocation；禁止读新 config 重绑；失败则保持
    recoverable 且 Gate A fail closed；DB clock 证明原 deadline 已过时转
    `ADMISSION_FAILED_FINAL / NO_LONG`，仍不创建 Invocation；
  - final 已存在：永不 requeue；
  - `ADMITTED` 且未过期：按 durable ordering 分页填充 bounded queue，
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
| ordering | process-local queue 按 `(decision_requested_at, decision_invocation_id)` ascending；无 response-based priority；该顺序不是 durable correctness state |
| priorities | Gate A 只有 `NEW_SETUP` 一类；不得与 Position/Plan Review 混合 |
| enqueue | post-commit `put_nowait` / equivalent；绝不 await queue space |
| full policy | **REJECT NEWEST**；不 DROP accepted item、不 COALESCE、不阻塞 producer |
| full durable result | same invocation 按 §14.2 原子 terminalize：`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`，`final_attempt_id=NULL`、`final_decision_id=NULL`；zero provider call |
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

精确 ordering / crash 语义（P2-01）：

1. DB commit 产生 `ADMITTED`；成功 `put_nowait` 不改 durable state。
2. consumer dequeue 只取得 ref；它必须先成功提交 §14.3 的
   `ADMITTED -> ACTIVE` + Attempt，才可调用 provider。
3. enqueue 前 crash、enqueue 后 crash、dequeue 后/claim 前 crash 均留下同一
   `ADMITTED`，restart 重建 ref；无法误认为已经开始 provider。
4. claim transaction DB failure 整体 rollback，Invocation 仍 `ADMITTED`，Attempt 不存在，
   provider call = zero。claim commit 后/provider 前 crash 则留 `ACTIVE` + `STARTED`
   Attempt，restart 按 `PROCESS_LOST/ABANDONED` 规则处理。
5. duplicate process-local refs 经 Invocation row lock/state check 被 fence；不会创建第二个
   concurrent Attempt。
6. queue full 时 ref 未进队，必须同步尝试上述 durable capacity final。
   若该 final commit 失败，诚实状态仍是 `ADMITTED`，subsystem fail closed；
   restart 不伪造历史 capacity result，而是按原 deadline/stale 再次 bounded offer。

无 durable `QUEUED`、无 coalescing（identity safety 未被形式化证明前禁止）。

## 17. Deadline / Cancellation Contract

### 17.1 Deadline authority（相对旧 draft 变更）

- clock authority = **PostgreSQL server clock**。外层 admission transaction 在 exact
  Evidence 已 staged 后执行一次、且仅一次如下语义的 DB statement：
  `WITH admission_clock AS (SELECT statement_timestamp() AS requested_at) SELECT
  requested_at, requested_at + (:deadline_duration_ms * interval '1 millisecond') AS
  deadline_at FROM admission_clock`。同一 CTE 值产生两个字段；禁止第二次
  clock read、禁止 application wall clock 参与身份或持久期限计算。
- 外部语义依据 = PostgreSQL 官方
  [Date/Time Functions and Operators](https://www.postgresql.org/docs/current/functions-datetime.html)；
  `statement_timestamp()` 表示 current statement start，不与 transaction-start
  timestamp 或会在单个 statement 内变化的 `clock_timestamp()` 混用。
- `decision_requested_at` 与 `decision_deadline_at` 先写入 Evidence 的
  `AdvisoryAdmissionSeed`，成功时原样复制到 Invocation/Snapshot；它们不是从
  Evidence `created_at` 读回或推断的。**「same transaction ⇒
  Evidence.created_at 与 Invocation timestamp 数值相等」不成立，也不再作为任何
  proof。**
- 数据库类型 = PostgreSQL `TIMESTAMPTZ(6)`；读出后统一归一化为 UTC。
  进入 canonical JSON/hash 时使用 RFC 3339 `Z` + 固定 6 位小数秒；不受
  DB session timezone 或 locale 影响。duration 以 positive integer milliseconds 及
  `deadline_policy_version` 一并持久，不使用 float seconds。
- duration 未配置（Human Decision B，§25）时 Gate A 不能 active；I2 可实现 disabled
  path / test injection，不得给 production 猜默认值。
- PRE-01A 冻结语义保持：absolute、attempt 1 前固定、所有 retry 共享、per-attempt
  timeout 不能延长它。

advisory latency budget 从该 DB-authoritative admission instant 开始；queue 等待、
recovery、retry、provider I/O 全部消耗同一 budget。restart 必须复用已持久值；
config reload 只能创建新 config epoch/experiment，不改动旧 seed/Invocation。

### 17.2 Propagation（PRE-01B-D1 AI Deadline Contract 落地）

- producer、durable Invocation、queue item（ref 内）、consumer、每次 Attempt、
  provider call 传递/重读**同一** immutable UTC absolute `decision_deadline_at`。
- 每个 durable correctness transaction 以该 transaction 内单次 PostgreSQL
  `statement_timestamp()` 与 persisted deadline 比较。开始 provider I/O 时可将 DB 返回的
  remaining interval 一次性映射为 AnyIO monotonic cancel scope（`fail_after` /
  equivalent），但 monotonic scope 仅负责本地取消；终态 deadline verdict 仍由
  finalizer 的 DB clock 重验决定。
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
| cancellation | NO（restart 另按原 invocation/budget 裁决） | 按 §14.2 区分 `SHUTDOWN_BEFORE_PROVIDER` / `SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT`，或 process-loss attempt audit | yes | zero |
| late result | NO | `STALE_DECISION / LATE_RESULT` 或 loser audit | yes | zero |
| duplicate completion | NO | winner 不变；`DUPLICATE_SUPPRESSED` | loser attempt yes | zero |
| internal invariant/hash/fence failure | NO；Advisory subsystem fail closed | 无 provider 或 terminal invariant failure；不得伪造 valid | sanitized durable evidence where possible | zero |
| queue rejected | NO | `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` | invocation/final yes | zero |
| admission staging failure | 在原 deadline 前恢复同一 seed；不启动 provider Attempt | Evidence accounting 先 = `RECOVERY_REQUIRED / ADMISSION_STAGING_FAILED`；deadline 过期后 = `ADMISSION_FAILED_FINAL / ADMISSION_STAGING_FAILED_DEADLINE_EXPIRED` + `NO_LONG`；subsystem `FAIL_CLOSED` | G2/Evidence + exact admission seed durable；process counter 仅 telemetry；无 Invocation/Attempt/AIDecision | zero |

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
| stale immediately before provider | attempt-start transaction 在 Evidence lock 下拒绝，zero provider |
| stale during provider call | 不新增 market subscription / second event bus；response 后 finalizer durable re-read 判 stale；可 best-effort cancel，cancellation 不是 authority |
| valid response 后、finalization 前变 stale | finalizer 按 `Evidence -> Invocation -> Attempt` 锁顺序重读后判 `STALE_DECISION`（含 `EVIDENCE_SUPERSEDED`），valid response 只留 attempt/AIDecision audit，不能成为 current/actionable winner |

每个 case 显式给出：durable state（terminal row + diagnostic）、provider call yes/no、
audit retention（attempt audit 保留）、economic effect = **ZERO**。所有 stale outcome：
zero risk increase。

## 20. Shutdown / Restart

RuntimeHost 拥有 AdvisoryIngress lifecycle；关闭动作落在 PRE-01B-D1/I1 已接受的
shutdown 顺序的 step 2 槽位（「close/cancel new advisory work」—— I1 实现为 no-op
注释，本设计填充该槽位）。本修复在已有 Host shared graceful deadline 内冻结两个
必须显式配置、不在本 Design 发明数值的 duration：

```text
protection_reserved_budget
advisory_cleanup_budget

protection_handoff_at = host_shutdown_deadline - protection_reserved_budget
advisory_subdeadline = min(
    advisory_cleanup_started_at + advisory_cleanup_budget,
    protection_handoff_at,
)
```

Host shutdown monotonic clock 与 shared deadline 沿用 D1；上述两个 duration 是 B 类 activation
config，必须为 positive finite、并在 Gate A activation 前验证与 Host 总窗口相容。
缺失/非法时 Gate A 不能 active，不猜 production default。

1. Host 立即设 `advisory_admission_open=false`，拒绝新 post-commit offer（Invocation 保持
   `ADMITTED`）；停止 durable recovery scan / queue 补充 / dequeue claim，不再启动新
   Attempt。
2. cancel active provider I/O；取消仅作用于 Advisory nested scope，不能传播到
   safety/protection siblings。Provider boundary 必须无 detached callback/task；late response
   无法绕过 Invocation finalizer fence。
3. 在 `advisory_subdeadline` 前可 best-effort terminalize 已取消 ACTIVE Attempt 或少量
   ADMITTED items，但**不要求每个 queued ref/Invocation 都写 cancellation final**。任何
   shielded DB cleanup 的 shield 上限也是 advisory subdeadline，绝不是 Host deadline。
4. 到达 `advisory_subdeadline` 时，Host 必须立即取消/停止所有 Advisory DB
   cleanup，丢弃 process-local queue refs，让 Advisory wrapper acknowledge/return，然后进入
   Protection/Safety phase。Advisory 不得开启新事务、等待 provider、或以日志/
   metrics flush 占用 reserve。
5. 结构不变量：无论 Advisory backlog/DB/provider 状态如何，
   `protection_handoff_at..host_shutdown_deadline` 始终留给 Protection/Safety。
   Advisory cancellation 既不 cancel Protection，也不得阻塞 safety drain。
6. engine 仍由 Host 最后 dispose。选择 **cancel，不做 provider drain**；无 detached
   daemon、无 in-process restart supervisor（沿用 I1 fatal matrix）。

`advisory_subdeadline` 到达时允许的 durable 状态与 restart 解释：

| Exit-time fact | 允许留存 | 本次 shutdown 内的 actionability | Restart interpretation |
|---|---|---|---|
| Evidence accounting `RECOVERY_REQUIRED` | yes | admission closed，zero provider | 用原 seed 恢复；重复失败仍 recoverable/fail closed |
| Evidence accounting `ADMISSION_FAILED_FINAL` | yes | accounting terminal，zero provider | 保留 `NO_LONG` + exact reason，不创建 Invocation |
| `ADMITTED`（含 queue ref 已存但未 claim） | yes | queue ref 丢弃；不 claim | 按原 deadline/stale/config epoch 重新 bounded offer 或 terminalize |
| `ACTIVE` + `STARTED` Attempt，provider I/O in flight | yes | cancel scope；不等 drain；不允许新 finalizer 越过 subdeadline | 原 Attempt 记 `PROCESS_LOST/ABANDONED`；仅在原 budget/deadline 允许时 retry |
| provider cancellation completed、DB terminalization 也在 budget 内 commit | no（Invocation 已 FINAL） | terminal/non-actionable | 永不 requeue |
| provider cancellation completed、但 DB terminalization 未在 budget 内 commit | yes（仍 ACTIVE/STARTED） | 本 process 已关闭 finalizer，zero economic use | 按 process-lost 规则，不伪造 cancellation final |
| `RETRY_PENDING` | yes | 不启动新 Attempt | 原 identity/provider/model/deadline 继续或 terminalize |

single RuntimeHost singleton fence + `advisory_admission_open=false` + stopped claim path 是关闭期间
的执行 fence；durable non-terminal 行本身不授权任何经济行为。Protection reserve 不以
「Advisory 先全部写完」为前置。

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
  hash、snapshot source、expiry、reference 三态 authority（SE-02A/ARCH-FIX 契约原样）；
  exact bound/predecessor Evidence row 另被**复用**为 §10.1 的 transaction row-lock
  target，不创建第二 identity authority。
- G2 event/timeline/state/transition/candidate/observation tables 与 transaction 语义。
- `edge_attribution_events` schema/identity：append-only lineage；不是
  invocation/final fence。
- Trade/Risk/Execution/Position/Account/Ledger schema：Gate A 完全不写。

### 24.2 REUSE WITH MINIMAL EXTENSION

`edge_opportunity_evidence`（新 admission accounting fields，不进入/不改变
`evidence_hash`、Evidence payload 或 revision identity）：

```text
advisory_admission_state nullable
advisory_admission_reason_code nullable
advisory_treatment_participation nullable
advisory_admission_seed_version nullable
advisory_admission_seed_digest nullable
advisory_admission_seed JSONB nullable
advisory_decision_invocation_id nullable
```

conditional CHECK 要求：`NOT_ELIGIBLE/GATE_A_DISABLED` 不得有 invocation；
`RECOVERY_REQUIRED` 必须有完整 Gate/config/experiment/time seed 且无 invocation；
`ADMISSION_FAILED_FINAL` 必须有完整 seed、`NO_LONG`、exact terminal reason 且无
invocation；`INVOCATION_CREATED` 必须有同一 seed 与 Invocation FK。Evidence ↔
Invocation 的循环 FK 必须 `DEFERRABLE INITIALLY DEFERRED`，使 §8.3 SAVEPOINT
在单一 transaction 内原子插入/翻转，不可暂时提交半链接状态。该 extension 是关闭
P1-01 的 minimum PostgreSQL authority；不新增 admission/outbox/framework table。
对 I2 之后的新 Evidence，`advisory_admission_state` schema default =
`NOT_ELIGIBLE`；qualifying G2 capture 根据 Host 注入的 immutable activation
classification 显式写 `GATE_A_DISABLED` 或（active writer）`RECOVERY_REQUIRED`。
nullable 仅用于 legacy compatibility，不作为当前 Gate state 推断权威。

`decision_snapshots`（新 Shadow rows 增加 queryable binding facts，legacy rows 兼容）：

```text
decision_invocation_id, opportunity_id, evidence_id, evidence_revision, evidence_hash,
feature_snapshot_hash, market_type, snapshot_payload_hash, input_binding_digest,
advisory_config_epoch_id, decision_requested_at, deadline_duration_ms,
deadline_policy_version, decision_deadline_at
```

`ai_decisions`（继续作 normalized provider-result artifact；**不再作 no-provider
terminal authority**）：

```text
decision_invocation_id（partial UNIQUE for non-null new rows）, attempt_id,
input_binding_digest, experiment_id, pair_id, arm_id,
provider_id, configured_model_id, provider_reported_model_id nullable,
output_digest, error_category, finalized_at
```

legacy `decision_id(snapshot_id, model)` 只保留给既有非-Advisory 路径；新 Gate A rows
必须使用 invocation-derived `decision_id` 并以 Attempt FK 证明 origin。migration/
backfill 策略属 I2 design review；不得把旧 row 伪造为新 invocation/Attempt。

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
state (ADMITTED/ACTIVE/RETRY_PENDING/FINAL)
final_status nullable
final_reason_code nullable
finalized_at nullable
final_attempt_id nullable
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
UNIQUE(decision_invocation_id, attempt_id)
```

Invocation 的 final-field completeness CHECK、named-nullability CHECK、Attempt composite FK、
AIDecision `(decision_invocation_id, attempt_id)` composite FK 及 §14.2 的 deferred
final-decision composite FK 均是 `MINIMAL EXTENSION/CONSTRAINT`，不建第三 final table。

### 24.4 Necessity proof（对照当前 schema）

当前 schema（`db/models.py` 实测）无 durable admission gap accounting，也无
invocation/attempt/experiment/pair/arm 持久层；`decision_snapshots` 无 binding/hash/
deadline；`ai_decisions` 无 Attempt origin；任何现有表都无 queryable exactly-one terminal
fields。因此 PRE-01A AC-21/22、P1-01 恢复、P1-03 final authority 与 winner fence
在现有 schema 上不可表达。**两张最小新表**（Invocation/Attempt）+
**三处最小 extension**（Evidence accounting、Snapshot binding、AIDecision origin）
是满足契约的最小集。Evidence supersession 与 final-then-supersede actionability
完全复用现有 Evidence chain + row lock，故**不**增 supersession marker/table。
不新增 generic workflow、event bus、saga、job、provider registry、outbox 或 metrics
table；Invocation row 即 final authority，不建第三 final table。**本契约不创建 migration**。

## 25. Human Decision Pack

### 25.1 Classification

| 未决项 | 分类 | Safe I2 posture |
|---|---|---|
| joint total attempts / transport retries / validation retries | **B** | positive explicit config；unset ⇒ Shadow activation rejected；tests inject boundary values |
| per-attempt timeout | **B** | interface/enforcement implemented；unset ⇒ disabled |
| absolute decision deadline duration | **B** | field/digest/propagation implemented；unset ⇒ disabled |
| per-decision token/cost budget | **B** | nullable usage provenance + fail-closed budget checker；unset ⇒ disabled |
| advisory queue capacity / finite worker count | **B** | bounded implementation accepts explicit injected values；production activation unset ⇒ disabled |
| Protection-reserved shutdown budget / Advisory cleanup budget | **B** | 实现 §20 的 subdeadline 关系；tests 注入明确值；production activation unset/invalid ⇒ disabled |
| exact provider/model | **B** | provider-neutral interface only；I2 candidate 不含 real constructor |
| raw provider envelope retention size/duration/access | **B** | retention OFF / columns NULL；normalized/redacted required provenance 仍保存 |
| Gate A Shadow observation window / sufficiency thresholds | **C** | collection counters implemented；no PASS threshold invented |
| superseded-revision pair 的实验分母计数规则 | 归 SE-02D/Gate C aggregation contract（非 D2 决策；记录边界，不算 Human Decision Pack 数值项） | shadow 照常记录 per-invocation facts |

### 25.2 Human Decisions Blocking I2 Implementation

`NONE` —— P1 修复已冻结 lock target/order、terminal model、DB clock authority、
durable admission accounting 与 shutdown subdeadline semantics，不再需要人工选设计方向。
前提：I2 必须接受「production activation disabled when required explicit config is unset」，
且只用 fake/injected provider 做 deterministic tests。**Safe I2
implementation with activation OFF、required config unset、fake/injected provider only
是可行的**（显式声明，任务 §29 要求）。若 I2 被要求同时真实激活 Gate A，则上表 B 项
立即变成 blocker。

### 25.3 Human Decisions Blocking Real Provider Activation

1. exact Single Primary Provider + exact model/deployment identity；
2. total/transport/validation attempt limits；
3. per-attempt timeout + absolute deadline duration；
4. token/cost budget 与 usage-unavailable policy；
5. queue capacity + finite worker count；
6. Protection-reserved shutdown budget + Advisory cleanup budget；
7. raw envelope retention/access policy；
8. selected provider/model 的 strict structured output、refusal、usage、request-id
   能力验收（PRE-01A §11）。

### 25.4 Human Decisions Blocking Gate A Acceptance Only

- minimum Shadow observation window；
- latency/deadline miss、failure/refusal/schema/stale/late/duplicate/cost 与
  coverage 的 sufficiency/pass thresholds。

## 26. Implementation Batch Proposal

### PRE-01B-I2 — AdvisoryIngress Core / Shadow-Safe Durable Path

一个最小 vertical slice：

1. §24 的 migration + minimal models/constraints（含 Evidence durable accounting 与
   Invocation authoritative final fields）；
2. G2 formal transaction 内的 Evidence admission seed + savepoint-isolated staged invocation + typed
   post-commit ref（`persist()` 返回值扩展）；
3. Host-owned bounded AdvisoryIngress queue（无 durable `QUEUED`）/ nested auxiliary
   lifecycle / Protection-reserved Advisory subdeadline（D1 shutdown step 2 槽位）；
4. adapted immutable snapshot/input builder（binding 含
   evidence_hash/feature_snapshot_hash/deadline）；
5. durable attempt-start / final winner transactions（Evidence predecessor row shared lock +
   Invocation terminal authority + constrained Attempt/AIDecision linkage）；
6. fake/injected provider only，activation default `DISABLED`；
7. identity version literals 冻结清单（§12.2）；
8. deterministic rollback / savepoint-failure+reconciliation / full / DB-clock deadline /
   stale（含 supersede two-serialization）/ final linkage / queue ordering / reserved-budget
   shutdown / restart / adverse tests；
9. focused G2/G3/SE-02B/RuntimeHost regression + real disposable PostgreSQL
   transaction evidence（含 admission staging 失败时 G2/Evidence 照常 commit 的
   专项证明）；
10. zero Real API call、zero Gate A activation、zero Gate B/economic mutation。

Real provider adapter selection / contract validation 与 Gate A activation 为后续
独立获批 batch/gate；不得并入 I2。

## 27. Acceptance Criteria（I2 Candidate ready for review 的独立证据要求）

1. qualifying formal Evidence + invocation/snapshot 同 transaction 原子；外层失败 ⇒
   queue/provider/rows 全为零。
2. **Admission staging 失败 ⇒ savepoint 内回滚，G2 facts + Evidence +
   exact config/experiment/time seed 照常 commit，Evidence = `RECOVERY_REQUIRED`；
   无 invocation、无 phantom、可恢复/FAIL_CLOSED**；restart/repeated-failure 不能
   post-hoc rebind 或永久漏样；原 deadline 过期后可原子收口为
   `ADMISSION_FAILED_FINAL / NO_LONG`，仍无 Invocation。
3. Capture Anchor without formal Evidence 永不进入 Advisory。
4. enqueue 只发生在 commit 后；crash-after-commit-before-enqueue 恢复同一 invocation。
5. queue object 只有 frozen ref；consumer durable re-read 并验证全部
   binding/hash（含 feature_snapshot_hash）。
6. queue bounded；无 durable `QUEUED`；full = durable REJECT NEWEST
   （`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`）；
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
13. N+1 writer 与 N finalizer 使用同一 Evidence N row lock；必须证明
    supersede-first ⇒ N 不可成 current/actionable final，以及 final-first ⇒ N audit
    immutable 但被 N+1 持久 chain 事实屏蔽于未来经济消费。
14. two concurrent completions、retry/shutdown/restart race 只产生一个 Invocation
    authoritative final；五个 terminal fields 可直接查询；final Attempt/AIDecision 必须
    同 Invocation 且 origin constrained；late/duplicate loser 不能覆盖 winner。
15. all expiry/stale phases（六维度 × 六时点）匹配 §19，no provider/no risk 精确。
16. restart 对 RECOVERY_REQUIRED/ADMISSION_FAILED_FINAL/ADMITTED/ACTIVE/
    RETRY_PENDING/FINAL 均匹配 §15。
17. failure matrix 全部有 targeted tests；无 baseline fallback / fake-AI substitution。
18. deadline authority/propagation 匹配 §17：PostgreSQL single-read timestamp、UTC/
    precision/canonical serialization、duration+version 持久化、queue/retry 消耗同一 budget。
19. Advisory 在其 subdeadline 到达时无条件让出 Protection reserve；不要求
    per-Invocation cancellation final；全部允许留存状态可解释/可恢复。
20. Gate A health fail closed 不取消/阻塞 safety sibling；shared Host fatal 沿用 I1；
    DISABLED 与 GATE_A_SHADOW 的 readiness 影响按 §21.2 裁定。
21. activation default disabled；缺任何 B 类 config 或请求 Gate B 均 startup fail
    closed。
22. exact allow-list tables 之外零写；Production/Live/Real API = zero。
23. no G2 state-machine、G3 economic、Risk、Execution、Accounting、Protection
    semantic regression；SE-02D 边界（§23.3）零触碰（`aggregation_snapshot.py`
    import count in advisory path = 0）。

## 28. Risk Register

| Risk | Treatment |
|---|---|
| 把 Capture Anchor 当正式 Opportunity | producer 必须验证 exact Evidence row/invocation FK；anchor-only ignored |
| G3Workflow 产生 TradePlan | Gate A 禁用其类型/handle + call-count + table-delta tests |
| G2 transaction rollback 却已 enqueue | queue touch 严格 post-commit；typed result 在 transaction exit 后返回 |
| commit→enqueue crash 丢任务 | durable `ADMITTED` scan，same invocation recovery |
| admission staging 失败摧毁 G2 truth 或留下无法恢复的 coverage hole | Evidence-row durable admission seed + `RECOVERY_REQUIRED` 在 savepoint 外；snapshot/invocation/state flip 在 savepoint 内（§8.3） |
| queue full 删样本/阻塞行情 | REJECT NEWEST + durable final；non-blocking offer；scanner/protection lanes 隔离 |
| queue rejection 被误分类为 provider failure | `CAPACITY_BLOCKED` 映射 + 与 admission rejection 的 durable 区分 |
| canonical head 误作 admission identity | §9 显式区分 + advisory path 禁 import aggregation_snapshot（AC-21） |
| supersede 检查与 final commit 之间 TOCTOU | N predecessor Evidence row 被 writer/finalizer 共享 `FOR UPDATE`；持锁重读（§10.1） |
| final 后 supersede 仍被未来 Gate B 消费 | N+1 durable chain row 为 actionability authority；Gate B 必须同锁重验，不改写历史 final |
| legacy decision_id collision | invocation-derived final id + partial unique linkage |
| two provider completions 双 winner / final 来源只能靠 timestamp 猜 | Invocation five terminal fields + row lock + completeness/FK constraints + one transaction |
| retry 重置 deadline/arm | immutable invocation facts；attempt 不得覆写 |
| restart 用新 config 重配旧 decision | invocation self-contained；old row 不读新 experiment/model 重建 identity |
| provider alias/model drift | configured + provider-reported exact identity 分别保存；unknown != configured |
| Advisory failure/backlog 耗尽 Protection shutdown window | Host 预留 Protection budget + Advisory subdeadline；到点立即停 DB cleanup，无 per-row final 前置 |
| durable QUEUED 与 process queue 顺序歧义 | 删除 QUEUED；queue 只 wake-up；consumer 先原子 `ADMITTED -> ACTIVE` + Attempt |
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
Producer Boundary = formal edge_opportunity_evidence durable admission seed +
                    savepoint-isolated staged invocation（同 G2 formal transaction）
Admission Gap Authority = Evidence accounting RECOVERY_REQUIRED / original seed；
                    restart 只能原样恢复，不后绑新 config
Admission Evidence Identity = admission transaction 内 staged 的 exact Evidence
                    revision（opportunity/evidence_id/revision/evidence_hash/
                    feature_snapshot_hash），不是 SE-02D canonical head
Superseding Evidence Policy = N predecessor Evidence row shared FOR UPDATE；
                    supersede-first fences N final；final-first 保留 audit 但未来 non-actionable
Gate A Consumer = ShadowAdvisoryDecisionPath with provenance-only write allow-list
G3Workflow = DO NOT USE IN GATE A
Invocation Authority = deterministic AdvisoryAdmissionWriter（attempt 1 前，
                    admission transaction 内）
Final Authority = Invocation final_status/reason/finalized_at/final_attempt_id/
                    final_decision_id + constrained Attempt/AIDecision origin
Queue = bounded / non-blocking / no durable QUEUED / REJECT NEWEST /
                    durable CAPACITY_BLOCKED terminal
Deadline Authority = PostgreSQL statement_timestamp single read + persisted integer-ms
                    duration/version；UTC TIMESTAMPTZ(6) canonicalization；queue/retry 消耗同一 budget
Stale Policy = 六维度 × 六时点矩阵，全部 zero risk increase
Shutdown / Restart = Protection-reserved budget + Advisory subdeadline；到点停 DB cleanup；
                    cancel-not-drain；非终态 durable recovery
Gate A vs Gate B = explicit activation level；Gate B startup fail-closed until approval
SE-02D-I02 Runtime Reuse = NONE（仅概念性复用其 canonicalization 语义）
Schema = reuse Evidence chain/attribution + minimal Evidence/Snapshot/AIDecision
         extensions + two new minimal tables；无 migration（属 I2）
I2 Numeric Blockers = NONE when activation remains disabled and config explicit/unset
Artifact Status = FIX CANDIDATE DESIGN / READY FOR INDEPENDENT RE-REVIEW
```

## 31. Independent Review Finding Dispositions

| Finding | Previous Severity | Disposition | Design Change | Residual Risk |
|---|---|---|---|---|
| `PRE01B-D2-RR-P1-01` | P1 | **CLOSED** | Evidence-row `RECOVERY_REQUIRED` + immutable admission seed 在 SAVEPOINT 外；snapshot/Invocation/state flip 在 SAVEPOINT 内 | 真实 schema/migration/recovery race 仍待 I2 独立实现与 PostgreSQL 验证 |
| `PRE01B-D2-RR-P1-02` | P1 | **CLOSED** | supersede writer/finalizer 共享 predecessor Evidence row lock；固定 lock order/re-read/commit；final-then-supersede 由 durable N+1 chain 使旧 final 未来 non-actionable | 所有 Evidence writer 必须在 I2 审计为同一锁协议 |
| `PRE01B-D2-RR-P1-03` | P1 | **CLOSED** | Invocation 五个 final fields 为唯一终态权威；Attempt/AIDecision 同 Invocation/origin composite FK 与原子 terminalization | deferred composite constraints 与 legacy-row compatibility 待 migration review |
| `PRE01B-D2-RR-P1-04` | P1 | **CLOSED** | PostgreSQL `statement_timestamp()` 单次 CTE；TIMESTAMPTZ(6)/UTC/canonical serialization；duration/version 持久；restart/config reload/queue delay 语义冻结 | 数值 duration 仍是 B 类 activation decision |
| `PRE01B-D2-RR-P1-05` | P1 | **CLOSED** | Protection reserve + Advisory subdeadline；到点立即停 Advisory DB cleanup；不以 per-Invocation cancellation final 为 Protection 前置 | 两个数值 budget 仍是 B 类 activation decision，I2 需仿真时钟/DB 阻塞 |
| `PRE01B-D2-RR-P2-01` | P2 | **CLOSED** | 删除 durable `QUEUED`；queue 仅 bounded wake-up；consumer 先原子 claim `ADMITTED -> ACTIVE` + Attempt | duplicate-ref/crash/claim DB-failure 需 I2 adverse tests |

Process P2（memory / skills compliance narrative contradiction）仅记录为
`PROCESS P2 / NOT PRODUCT DESIGN BLOCKER`；FIX-01 未修改 `.workbuddy`、memory、skills 或 daily
logs，也不以修改产品设计的方式「修复」该 process finding。
