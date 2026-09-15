# PRE-01B-D2｜AdvisoryIngress / G2→G3 Activation Formal Design

## Task

- Role：FORMAL DESIGN / ARCHITECTURE CONTRACT AUTHOR。
- Type：DESIGN ONLY / REPOSITORY READ-ONLY SOURCE AUDIT + DOCS CANDIDATE DELIVERY。
- Result target：冻结 persisted Opportunity/SETUP → Host-owned AdvisoryIngress → live advisory decision 的
  identity、ownership、durability、queue、deadline、failure、restart 与 Gate A/B 边界。
- Human Acceptance：`NOT PERFORMED`。

## Base / Git

| 项 | 值 |
|---|---|
| Protocol | `v1.1.0 / ACCEPTED` |
| Protocol SHA | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| Task Base | `664207a9caba0c3f5c2589cfca2a10af24f89108` |
| verified local `main` | `664207a9caba0c3f5c2589cfca2a10af24f89108` |
| verified `origin/main` after fetch | `664207a9caba0c3f5c2589cfca2a10af24f89108` |
| Baseline drift | `NO` |
| Branch | `design/pre-01b-d2-advisory-ingress-contract` |

根工作区位于 unrelated dirty branch `prb-01-product-requirements-baseline@d47313a...`。本任务使用从
verified main 建立的独立 worktree；未修改、reset、stash、clean、rebase 或提交根工作区既有内容。

## Scope

- 只新增 D2 Formal Design artifact 与本 dev log。
- 只做 repository/source/test/schema audit；不执行 runtime/provider/test/migration。
- 冻结 future I2 contract，不实现 I2，不激活 Gate A/B。

## Out of Scope / Forbidden

- `PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md`。
- `backend/**`、`frontend/**`、`scripts/**`、`alembic/**`、requirements、config、deployment、Docker、WinSW。
- existing design docs / existing dev logs。
- `.workbuddy`、memory、skills。
- Real AI/provider call、live G2→G3 wiring、Gate A/B/Live、SE-02D next batch。

## Files Reviewed

### Global / project truth

- Global `AI_BOOTSTRAP.md`、`AI_DEVELOPMENT_PROTOCOL.md`、`PROJECT_REGISTRY.md` @ `07e2df8...`。
- `AGENTS.md`、`AI_CONTEXT.md`、`PROJECT_STATE.md`、`PRODUCT_REQUIREMENTS.md`、`DECISIONS.md`。
- `dev_log/2026-09-15-pre-01b-i1-close-final-validation.md`。

### Accepted contracts

- `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`（完整）。
- `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`（完整）。

### Source / schema / tests

- `backend/src/marketpulse/runtime_host.py`。
- `backend/src/marketpulse/g2/models.py`、`scanner.py`、`runtime.py`、`repository.py`。
- `backend/src/marketpulse/g3/models.py`、`provider.py`、`service.py`。
- `backend/src/marketpulse/db/models.py`。
- `backend/src/marketpulse/edge/capture.py`、`models.py`、`identity.py`、`repository.py`、`attribution.py`。
- `backend/tests/test_group3.py`、`test_runtime_host.py`、
  `test_se_02b_opportunity_capture.py`、`test_se_02b_attribution.py` 的相关测试与 adverse cases。

## Key Repository Facts

1. authoritative Opportunity 是与 G2 SETUP facts 同 transaction committed 的
   `edge_opportunity_evidence`，不是 Scanner candidate 或 Capture Anchor。
2. Capture Anchor 可在 formal persistence失败后重启恢复，也可成为 durable orphan；anchor-only 必须被
   Advisory忽略。
3. 当前 `G3Workflow` 对 valid LONG 创建/持久化 TradePlan，不能直接用于 Gate A。
4. 当前 `DecisionService`/schema不具备 invocation-aware identity、durable attempts、absolute deadline、
   winner atomicity或完整 provider provenance。
5. 当前 `BoundedAITaskQueue`不具备本任务所需 non-blocking full policy、restart/deadline/durable fence。
6. `RuntimeHost` 已拥有 safety/scanner隔离、single composition owner、TaskGroup与有界 shutdown，可最小扩展
   Host-owned auxiliary Advisory wrapper。
7. existing attribution 可复用 exact opportunity/evidence lineage，但不替代 final winner authority。

## Key Design Decisions

- Producer boundary：在现有 G2+Evidence transaction 中 stage immutable decision snapshot + invocation；
  transaction commit 后才可 enqueue frozen ref。
- Rollback：G2/Evidence/snapshot/invocation一起 rollback；queue/provider零触达，phantom impossible。
- Restart：commit→enqueue crash 通过 durable `ADMITTED` invocation恢复 same identity。
- Gate A consumer：新的 minimal `ShadowAdvisoryDecisionPath`；provenance-only table allow-list；无
  TradePlan/Risk/Execution/Position handle。
- `G3Workflow`：`DO NOT USE IN GATE A`。
- Queue：bounded、post-commit non-blocking、FIFO by durable key、full = `REJECT NEWEST`、no coalesce/drop/block。
- Identity：deterministic invocation/pair/arms；baseline policy/participation 与 treatment arm pre-call durable；
  retries共享 invocation；attempt identity独立。
- Winner：PostgreSQL invocation row lock + unique `ai_decisions.decision_invocation_id`；attempt update、final
  insert、attribution、invocation FINAL 同 transaction。
- Deadline：以 durable Evidence `created_at` 为 immutable request fact；所有 retries共享 absolute deadline。
- Shutdown：先关 admission，cancel而不 drain provider；Advisory不能延迟 Protection cleanup。
- Readiness：Core Host readiness 与 Gate A readiness分离；Advisory fail closed不取消 safety siblings。
- Gate A/B：explicit `DISABLED | GATE_A_SHADOW | GATE_B_PAPER`；I2/Gate A不得自动开启 Gate B。
- Schema：reuse exact Evidence；minimally extend snapshots/finals；新增 invocation + attempt 两张最小表。

## Reuse Decisions

| Component | Decision |
|---|---|
| `BoundedAITaskQueue` | `DO NOT USE IN GATE A` |
| `DecisionService` | `ADAPT` |
| `G3Workflow` | `DO NOT USE IN GATE A` |
| `DecisionSnapshotBuilder` | `ADAPT` |
| `TradePlanManager` | `DO NOT USE IN GATE A` |
| existing AI decision persistence | `REUSE WITH MINIMAL EXTENSION` |
| `RuntimeHost` TaskGroup | `ADAPT` |
| existing attribution identity | `REUSE` |

## Human Decisions

### Blocking I2

`NONE`，条件是 required numeric/provider config unset 时 production activation fail closed，I2 只用
fake/injected provider 验证。

### Blocking Real Provider Activation

- exact provider/model；attempt/retry limits；per-attempt timeout；absolute deadline；token/cost budget；
- queue capacity/worker count；raw envelope retention/access；
- selected provider/model strict schema/refusal/usage/request-id能力验收。

### Blocking Gate A Acceptance / Declaration Only

- Shadow observation window；operational sufficiency/pass thresholds。

## Artifact

`docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`

Status：`CANDIDATE DESIGN / PENDING INDEPENDENT REVIEW`。

## Verification

- Repository/Protocol/Main/Accepted status：实时只读核验。
- Accepted D1 contracts：完整阅读。
- Source/schema/tests：相关最小范围审计。
- Required artifact headings/20 design questions：人工逐项对照。
- `git diff --cached --check`：`PASS`（rc=0；LF→CRLF checkout warning 不构成 whitespace error）。
- exact staged delta：`PASS`；仅本 Task 两个新文件，均为 `A`。
- Tests：`ZERO / NOT RUN BY DESIGN`。
- Production/DB/Runtime/Provider：`ZERO TOUCH`。

## Remaining

- Independent Review：`PENDING`。
- Human Acceptance：`NOT PERFORMED`。
- I2 Implementation：`NOT STARTED / NOT AUTHORIZED BY THIS ARTIFACT`。
- Real provider/Gate A/Gate B/Live：`NOT ACTIVATED / NOT AUTHORIZED`。

## Evidence Boundary

本 dev log 是 Candidate 工作记录，不是 Acceptance evidence verdict。Worker 自审与文档文字不能替代
Independent Review。`main` 保持不变；Candidate branch push 后停止。
