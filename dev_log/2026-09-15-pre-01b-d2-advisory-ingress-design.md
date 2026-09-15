# PRE-01B-D2 — AdvisoryIngress / G2→G3 Activation Contract 设计（Latest-Main 重建）

日期：2026-09-15（重建窗口；提交于 2026-09-16 凌晨）
任务：`PRE-01B-D2-BASE-01`｜Latest-Main Re-Audit + D2 Candidate Rebuild
分支：`design/pre-01b-d2-advisory-ingress-contract-r1`（base = `d1e5534`，新 worktree
`E:\Documents\MarketPulse-AI-pre-01b-d2-r1`）
Artifact status：**CANDIDATE DESIGN / PENDING INDEPENDENT REVIEW**（不代表 Accepted）

## 1. 旧 Blocked Draft 的定位

- 旧 branch `design/pre-01b-d2-advisory-ingress-contract` @
  `be836c0ed008058508eb4a9065d03c7b617f7c0b`，base `664207a`。
- 分类：**BLOCKED DRAFT / NON-CANONICAL / NOT REVIEWED / NOT ACCEPTED**；
  Block Reason = SE-02D-I02 material baseline drift。
- 本轮处置：仅作 **DRAFTING INPUT**。未 push、未 rebase、未 amend、未 repoint、
  未删除其本地历史；其 worktree 与 branch 保持原状。
- 旧 draft 的两个文档（design + dev_log）被完整读取为起点文本，其后逐节对照
  latest truth 重审（见 §4/§5）。

## 2. Latest-Main Re-Audit

- Global Protocol：`zwmhua2-lab2/ai-dev-protocol`，`git ls-remote` 实测
  `main = 07e2df83266d4ecdea46caff5c61f000937b8913`，`AI_BOOTSTRAP.md` 实读
  `1.1.0 / ACCEPTED`（与任务卡预期一致）。本地 `E:\Documents\ai-dev-protocol\.git`
  为已知残缺目录（无 HEAD/config），未修、未锚定。
- MarketPulse：`git ls-remote origin refs/heads/main` = `d1e5534…`（= 任务卡
  Rebuilt Baseline）；本地 `main` 同 SHA；无 drift。
- Delta `664207a..d1e5534`：单一 commit `d1e5534`（`docs(se-02d-i02): accept I02
  via latest-main reconciliation`），7 个文件 = 3 个 state docs +
  `aggregation_snapshot.py`（+666）+ `test_se_02d_aggregation_snapshot.py`（+981）
  + 2 个 I02 dev_log。**零** G2/G3/RuntimeHost/前端/config 变更 ⇒ 旧 draft 的
  G2/G3/Host source facts 在 latest main 上复测全部成立。
- 权威状态核验：`PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` per-batch
  条目确认 PRE-01B-D1 / PRE-01B-I1（Runtime Host Core V1）/ SE-02D-D01 /
  SE-02D-I01 / SE-02D-I02 均 `ACCEPTED / COMPLETE`；Real AI `NOT ACTIVATED`；
  live G2→G3 `NOT ACCEPTED / NOT ACTIVE`；SE-02D Production `IN PROGRESS`。
- 已知陈旧索引行：`AI_CONTEXT.md` §4 与 `PROJECT_STATE.md` Current Group 列表仍
  残留「Integrated Runtime Host — NOT STARTED」摘要行（任务卡 §4 预告的已知模式）；
  权威以 PRE-01B-I1 per-batch 条目为准（Core V1 ACCEPTED，仅 Core V1）。
  **未发现该已知模式之外的新矛盾** ⇒ 无 STOP 事由。

## 3. SE-02D-I02 Impact（MATERIAL TO D2 DESIGN AUDIT）

I02 引入已接受语义：full visible Evidence revision-chain validation、canonical
Evidence head selection、frozen logical fact validation、exact-horizon Outcome
revision-chain folding、canonical Outcome head / NO_OUTCOME、cross-integrity、
`CanonicalScopeFacts`、`CURRENT_STABLE_SNAPSHOT`（REPEATABLE READ READ ONLY +
DB `statement_timestamp()`）。对 D2 的设计影响（全部落入新合同）：

1. 新增 **Critical Question A** 裁定：Admission Evidence（admission transaction 内
   staged 的 exact revision）vs SE-02D canonical Evidence head（事后聚合视图）；
   admission 永绑前者，任何已建 Invocation 不得静默切换到后者（合同 §9）。
2. 新增 **Evidence Supersede Contract**：旧 Invocation immutable + stale
   （`EVIDENCE_SUPERSEDED`）；qualifying N+1 可另立新 invocation；禁止改写/
   换绑/digest 重写/post-hoc rebinding（合同 §10；依据 PRE-01A-D1 §10）。
3. **SE-02D-I02 runtime reuse = NONE**：advisory path 禁 import
   `aggregation_snapshot.py`；仅概念性复用 canonicalization 纪律（合同 §23.2）。
4. supersede 检测 = 最小 durable 查询（同 `opportunity_id` 的 max
   `evidence_revision`），不引入 REPEATABLE READ 投影调用。

## 4. 相对旧 Draft 的决策变更（每项附新证据）

| # | 变更 | 证据/理由 |
|---|---|---|
| 1 | Admission staging 失败：整事务回滚 ⇒ **SAVEPOINT 隔离**（G2 facts + Evidence 照常 commit；invocation 消失 + counter + `FAIL_CLOSED`） | 旧设计让 AI provenance infra 失败摧毁 durable G2 market truth，即任务 §12 质疑的「污染 Scanner core responsibility」。savepoint 保留 admission↔Evidence 原子性，同时使 G2 真值独立于 AI infra 健康（合同 invariant 12） |
| 2 | Queue full durable 终态：`INVALID_SCHEMA` ⇒ **`CAPACITY_BLOCKED`** + `ADVISORY_QUEUE_REJECTED` | PRE-01A-D1 §8.1 冻结 `CAPACITY_BLOCKED` = downstream capacity outcome（非 AI/provider failure）；queue full 正属此类，误映射会污染 failure-rate 诊断 |
| 3 | Deadline origin：读回 Evidence `created_at` ⇒ **Invocation 自身 admission-time durable timestamp** | 任务 §17：Evidence.created_at 非 Accepted Truth。admission timestamp 自包含、attempt 1 前固定；与 Evidence 创建同 transaction 故数值同源，但 authority 独立；restart 不可能为旧 invocation 重 mint budget（合同 §17.1 论证） |
| 4 | Evidence supersede 从一句带过 ⇒ **独立契约**（六时点生命周期 + N+1 新 invocation 规则） | 任务 §10 + I02 新接受语义 + PRE-01A-D1 §10 |
| 5 | 新增 **Admission vs Canonical Head 区分** 与 **I02 reuse = NONE** | 任务 Critical Question A / §11 |
| 6 | `input_binding_digest` **纳入 `feature_snapshot_hash`** | 任务 §9 五字段逐项评估；该列实测存在于 `edge_opportunity_evidence` |
| 7 | 新增「identity version literals 须在 I2 实现窗口逐字冻结」前置核对项 | SE-02D-D01 `uncertainty_method_version` literal 缺失教训（DECISIONS.md I01 澄清条目） |

## 5. 保留决策（重验证通过）

| 旧 draft 决策 | 重验证证据（latest main 实读） |
|---|---|
| Producer = qualifying formal Evidence revision（G2 formal transaction 内）+ 同事务 staged admission + post-commit typed ref | `PostgresG2Repository.persist()` 单 `session.begin()` 含 G2 facts + `capture_opportunity()`；`EventRuntime._apply()` 消费 bool 结果（需 typed 扩展）；`qualifies()` 规则实读 |
| Capture Anchor 不是 authoritative Opportunity | `g2/repository.py` orphan 路径（`UNVERIFIABLE_ORPHAN`）实读 |
| `G3Workflow` / `TradePlanManager` = DO NOT USE IN GATE A；`ShadowAdvisoryDecisionPath` 最小 consumer + table allow-list | `process_setup()` 在 VALID+LONG 调 `persist_trade_plan()` 实读 |
| `BoundedAITaskQueue` = DO NOT USE IN GATE A | blocking `put` / process-local `datetime.now()` / 混合优先级实读 |
| Identity 构造序（snapshot→binding→experiment→pair→arm→invocation→attempt→final） | PRE-01A-D1 §6.3 碰撞自由清单 + 当前 schema 无冲突面 |
| Experiment authority = Host config（process lifetime immutable）+ baseline arm 持久化、非事后推导 | PRE-01A-D1 §13 + AC-09 |
| Attempt-start-before-provider 事务 + winner atomicity（invocation `FOR UPDATE` + unique final linkage） | PRE-01A-D1 §6.3/§9.1；当前 `ai_decisions` 无 invocation linkage（实测）⇒ minimal schema delta |
| Bounded queue / REJECT NEWEST / non-blocking offer / no coalesce | PRE-01B-D1 Backpressure Contract（scanner lane reject-newest 先例）+ 任务 §21 |
| Deadline 传播 / retry 不重置 / attempt timeout 不延长 | PRE-01A-D1 §9 + PRE-01B-D1 AI Deadline Contract |
| Shutdown：admission 先关、cancel-not-drain、D1 step-2 槽位、bounded、不占 Protection window | I1 `_shutdown()` 实读（step 2 为 no-op 注释槽位）；D1 Graceful Shutdown Contract |
| Restart：durable `ADMITTED` scan、PROCESS_LOST audit、原 budget/deadline 继续 | PRE-01A-D1 §10 + I1 recovery 契约 |
| Health/readiness 拆分；`AI_AUXILIARY` 不阻断 Core；persistence failure ⇒ admission fail closed | I1 `_validate_configuration()` 注册 `AI_AUXILIARY DEGRADED` 非 Core 阻断（实读） |
| Gate A/B enum；GATE_B_PAPER startup fail closed | PRE-01A-D1 §19 + 任务 §27 |
| Schema 决策（REUSE/EXTEND/两新表） | `db/models.py` 逐表实读（evidence revision chain / decision_snapshots / ai_decisions / attribution） |
| Human Decision Pack A/B/C 分类（A = NONE，activation-off 前提） | PRE-01A-D1 §9.2/§22 OPEN QUESTION 状态未变 |
| Overengineering 禁止清单 | 任务 §31 + PRE-01A-D1 §21.2 + PRE-01B-D1 Non-Goals |

## 6. Files Reviewed（本窗口实际读取）

- Protocol（gh api @ `07e2df8`）：`AI_BOOTSTRAP.md`（全）、`AI_DEVELOPMENT_PROTOCOL.md`
  / `PROJECT_REGISTRY.md`（落盘待查结构）。
- 状态：`AGENTS.md`（会话注入）、`AI_CONTEXT.md`（全）、`PROJECT_STATE.md`
  （头部 + PRE-01B/SE-02D 段）、`DECISIONS.md`（PRE-01A-D1 V1 / PRE-01B-D1 V1 /
  PRE-01B-I1 V1 / SE-02D-D01 V1 / SE-02D-I01 澄清条目）。
- 设计输入：`docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`
  （全）、`docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`（全）、
  旧 draft `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
  @ `be836c0`（全，起草输入）。
- SE-02D-I02 真值：`backend/src/marketpulse/edge/aggregation_snapshot.py`（模块
  docstring + 全部 public surface）、`dev_log/2026-09-15-se-02d-i02-current-snapshot-folding.md`
  （全）、`dev_log/2026-09-15-se-02d-i02-final-acceptance-reconciliation.md`（结论经
  PROJECT_STATE/AI_CONTEXT 交叉核验）。
- 实现（latest main 实读）：`backend/src/marketpulse/g2/repository.py`（全）、
  `g2/runtime.py`（全）、`g3/service.py`（stable_id/redact/SnapshotBuilder/Validator/
  BoundedAITaskQueue/DecisionService/G3Workflow 段）、`g3/models.py`（全）、
  `db/models.py`（decision_snapshots/ai_decisions/edge 全表段）、
  `runtime_host.py`（模块契约、validate/compose/shutdown 段）、
  `edge/capture.py`（qualifies/RUNTIME_CAPTURE_REVISION/版本常量段）、
  `edge/aggregation_snapshot.py`（surface）。

## 7. Unresolved Human Decisions（不发明数值）

- B 类（不阻塞 I2，阻塞 Real Provider Activation）：attempt/timeout/deadline/cost
  数值、queue capacity/worker count、exact provider/model、raw envelope retention。
- C 类（仅阻塞 Gate A Acceptance/Declaration）：Shadow observation window 与
  sufficiency/pass thresholds。
- 边界归属（非 D2 决策）：superseded-revision pair 的实验分母计数规则 —— 归
  SE-02D / Gate C aggregation contract。
- 显式声明：activation OFF + required config unset + fake/injected provider only
  的 I2 实现可行，无 A 类 blocker。

## 8. Artifact / Verification / Scope

- Artifact：`docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
  （CANDIDATE DESIGN / PENDING INDEPENDENT REVIEW；29 个必备 section 全部覆盖，
  含任务 §32 要求的 baseline/draft/block-reason 记录）。
- Verification：`git diff --check`（rc=0）；仓库 delta 恰为 2 个文件（本 dev_log +
  design artifact）；Production/Tests/Migration/Schema/Runtime/State docs =
  ZERO CHANGE；`.workbuddy` / memory / skills = ZERO CHANGE。
- Scope：仅 docs；无 production code、无 provider/API call、无 runtime activation。
- 旧 draft：未 push（`be836c0` 本地保持 immutable）；`main` 未动。

## 9. Remaining

- Independent Review（另行窗口；本作者不自行 Review / 不 Human Accept）。
- I2 Implementation（另行授权批次）。
- SE-02D 后续批次、Gate A/B activation、Real AI —— 均未启动。
- STOP。
