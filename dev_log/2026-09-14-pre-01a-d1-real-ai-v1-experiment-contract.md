# 2026-09-14 — PRE-01A-D1｜Real AI V1 Trade Decision Experiment Contract — Final Acceptance Closeout

## 0. Task

`PRE-01A-D1-FINAL`｜Acceptance Closeout & Main Integration。

类型：`HUMAN-ACCEPTED FINAL CLOSEOUT` + `ACCEPTED BASELINE INTEGRATION`。

本任务**不是** Implementation、New Design、New Review、Real AI activation、Runtime Host design、
SE-02D implementation。Human Acceptance 已由用户明确确认，本窗口只做设计工件状态收尾 +
状态文档同步 + fast-forward only 集成。

## 1. Scope

- 将 Human-Accepted 设计工件状态由 `CANDIDATE DESIGN / PENDING HUMAN REVIEW` 收尾为
  `ACCEPTED DESIGN`。
- 最小同步 `DECISIONS.md` / `PROJECT_STATE.md` / `AI_CONTEXT.md`。
- 新增本 dev_log。
- 新建独立 closeout branch → commit → fast-forward only 推进 `main` → push。

## 2. Out of Scope

- **不**修改已验收的 substantive design。
- **不**调用 Real AI provider、**不**运行 Runtime、**不**重启 Docker、**不**触碰 PostgreSQL。
- **不**实现 SE-02D、**不**实现 G2 → G3 handoff、**不**设计 Runtime Host、**不**选择
  provider/model。
- **不**修改 `backend/src` / `backend/tests` / `backend/alembic` / `frontend` / `config` /
  `PRODUCT_REQUIREMENTS.md` / `AGENTS.md` / `research/pre-01a` / `.workbuddy` / user-level memory /
  skills。

## 3. Bootstrap / Preflight（实时读取，CIP-01/02/31）

| Item | Value | How verified |
|---|---|---|
| Global Protocol | `zwmhua2-lab2/ai-dev-protocol`，Protocol `1.0.0 / ACCEPTED` | 远端 clone 后读取 `AI_BOOTSTRAP.md` / `AI_DEVELOPMENT_PROTOCOL.md` / `PROJECT_REGISTRY.md` |
| MarketPulse remote | `https://github.com/zwmhua2-lab2/MarketPulse-AI.git` | `git remote -v` |
| Accepted main / Task Base | `b77c80333b85d6e3f1095ac7da9b13e9bf08163a` | `git ls-remote origin refs/heads/main`，与本地 `refs/heads/main` 一致 |
| Human-Accepted candidate | `e3fb721c678e2b3ca0af6fb4663f349c6a641159` | `git ls-remote origin refs/heads/design/pre-01a-d1-real-ai-v1-contract`，与本地 ref 一致 |
| Ancestry | `b77c803` = ancestor of `e3fb721` | `git merge-base --is-ancestor` → `ANCESTOR_OK` |
| Lineage | 线性单 parent | `git rev-list --parents`：`e3fb721 → f612f0a → b77c803` |
| Drift | `main drift = NO` | 起止两次远端读取同为 `b77c803` |

**Preflight verdict = PASS（无 `BASELINE MISMATCH`）。**

## 4. Acceptance Lineage

```text
PRE-01A Research
→ S1 Context Pack
→ DS1 External Evidence
→ FIX-01
→ S2 Final Research Verdict
→ D1 Candidate
→ Human Review FAIL / FIX REQUIRED
→ D1-R1
→ D1-R2
→ FIX-01
→ Independent Re-Review PASS
→ Human Acceptance CONFIRMED（2026-09-14）
→ Final Acceptance Closeout
```

Commit lineage（线性、无 merge / rebase / squash / cherry-pick / force）：

```text
b77c80333b85d6e3f1095ac7da9b13e9bf08163a
→ f612f0afbc5b0e17135364335261345cfe0f6e19
→ e3fb721c678e2b3ca0af6fb4663f349c6a641159  ← Human-Accepted candidate（immutable）
→ <closeout SHA>
```

## 5. Human-Accepted Candidate

```text
Branch: design/pre-01a-d1-real-ai-v1-contract
SHA:    e3fb721c678e2b3ca0af6fb4663f349c6a641159
```

该 ref 在本轮**未被移动**（起止两次远端读取同 SHA），且本轮全部工作发生在其派生的独立
closeout branch `pre-01a-d1-final-acceptance-closeout` 上。

## 6. Implementation（docs/state-only）

### 6.1 Design Artifact — `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`

仅 Acceptance 状态收尾，**未**改写 substantive design：

- §1.1 Artifact status：`CANDIDATE DESIGN / PENDING HUMAN REVIEW` → `ACCEPTED DESIGN`，
  并新增 Acceptance Record 行（Independent Re-Review = `PASS`；`D1-R1` / `D1-R2` = `CLOSED`；
  Human Acceptance = `CONFIRMED`（2026-09-14）；Human-Accepted Candidate = `e3fb721…`）。
- §1.1 前导句改为「自 2026-09-14 Human Acceptance 起为 Accepted Design」，保留
  **不授权** implementation / migration / Runtime Host / provider-model 选择 / 真实 provider 调用 /
  Paper Economic activation / Live Trading 的边界。
- §22 末句「remain Candidate Design pending Human review of this document as a whole」→
  「are Accepted Design as of the 2026-09-14 Human Acceptance recorded in §1.1」。
- 末尾 verdict 标题 `## Candidate Design Verdict` → `## Accepted Design Verdict`；
  `Status = ACCEPTED DESIGN`，并补 Human Acceptance / Human-Accepted Candidate 两行。

其余章节（§2 ～ §21、§23、§24 及全部 `DESIGN DECISION` 语义）逐字未改。

### 6.2 Accepted Boundaries（只列已 Human-Accepted 内容）

```text
Real AI V1 Placement      = C. Trade Decision only
AI                        = Advisory
Deterministic System      = Authority
WITHOUT-AI benchmark      = ALL_ELIGIBLE_LONG_SHADOW_V1
Causal treatment          = PARTICIPATE_LONG vs NO_LONG
V1 causal claim           = REAL AI TRADE-DECISION SELECTION / PARTICIPATION EDGE ONLY
Decision identity         = one decision_invocation_id → exactly one collision-free
                            logical durable final decision
Provider                  = Single Primary Provider / No automatic fallback / No model voting
Gates                     = A Provider Shadow Activation
                            B Paper Economic Activation
                            C Selection / Participation Edge Evidence
SE-02C                    = REUSE
SE-02D                    = required before Gate C edge declaration
Runtime Host              = separate future design / research boundary
```

**明确不得**把该实验结论扩展为：entry edge / stop edge / target edge / sizing edge /
full `AIAnalysis` package edge / executed-trade edge。

### 6.3 DECISIONS.md

新增 PRE-01A-D1 V1 accepted decision（2026-09-14 Human Acceptance = `CONFIRMED`），冻结 §6.2
全部条目与「不得扩展为 entry/stop/target/sizing/full-package/executed-trade edge」的 claim 边界。
**未**新增新设计。

### 6.4 PROJECT_STATE.md

- `Current Group` 新增 `PRE-01A-D1 — Real AI V1 Trade Decision Experiment Contract —
  ACCEPTED / COMPLETE` 条目（含 Re-Review / Human Acceptance / candidate SHA / artifact 指针）。
- 文末新增 `## PRE-01A-D1 Result` 章节。
- 同步保持如下**未**启动状态：Real AI runtime activation = `NOT STARTED / NOT ACTIVATED`；
  Real AI provider runtime evidence = `NOT PRESENT`；`SE-02D` = `NOT STARTED`；
  `Integrated Runtime Host` = `NOT STARTED`；live Opportunity → G3 integrated handoff =
  `NOT ACCEPTED / NOT ACTIVE`。**未**把 `PRE-01A-D1 accepted` 写成 Real AI implementation
  complete / PRE-01 complete / AI edge proven / Runtime Host complete。

### 6.5 AI_CONTEXT.md

- §1 新增 PRE-01A-D1 accepted 指针（仅指针 + candidate + artifact path）。
- §3 新增 frozen invariant 11（Real AI V1 设计边界）。
- §6 新增 `### PRE-01A-D1 Real AI V1 Trade Decision Experiment Contract — ACCEPTED / COMPLETE`
  入口，含 blockers / prerequisites。
- 遵守 Context Compression：**未**复制 Design 正文。

## 7. Files Changed

```text
docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md
DECISIONS.md
PROJECT_STATE.md
AI_CONTEXT.md
dev_log/2026-09-14-pre-01a-d1-real-ai-v1-experiment-contract.md
```

## 8. Verification

- `git diff --check` = PASS（无 whitespace / conflict marker 问题）。
- `git diff e3fb721...HEAD --name-status` 只包含 §7 允许的 docs/state 文件。
- `backend/src` diff = **EMPTY**；`backend/tests` diff = **EMPTY**；
  `backend/alembic` diff = **EMPTY**；`frontend` diff = **EMPTY**。
- `Schema Changed = NO`；`Migration Added = NO`；`Production Code Changed = NO`；
  `Runtime Impact = ZERO`。
- `main` 只经 **FAST-FORWARD ONLY** 推进；`design/pre-01a-d1-real-ai-v1-contract` 保持
  `e3fb721…` 不变。
- 因本任务为 docs/state-only，**未**执行 production test suite（不需要）。

## 9. Result

```text
PRE-01A-D1 = ACCEPTED / COMPLETE
Real AI V1 Design Placement = C. Trade Decision only
V1 Experiment Contract = ACCEPTED
```

Closeout 后仍**禁止**声称：Real AI implemented / Real AI activated / AI edge proven /
SE-02D complete / Runtime Host complete / Live Trading enabled。

## 10. Remaining / Risks

- `SE-02D｜Family Aggregation / Expectancy` = `NOT STARTED`（Gate C 的前置）。
- `Integrated Runtime Host` = `NOT STARTED`。
- live Opportunity → G3 integrated handoff = `NOT ACCEPTED / NOT ACTIVE`。
- Real AI provider runtime evidence = `NOT PRESENT`（`DEFERRED / NOT VERIFIED`）。
- Design 内 `OPEN QUESTION`（attempt limits、timeout/deadline/cost、raw envelope retention、
  Gate A shadow window、Gate C thresholds）仍为 `NEEDS HUMAN DECISION`，须在后续实现/Shadow
  窗口内解决。本轮**未**改动这些项。

## 11. Context For Next AI

- 本文件是 PRE-01A-D1 的 Acceptance 记录；设计事实源为
  `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`（Accepted）。
- 下一窗口若继续 PRE-01A，须另开独立获批的任务；**不**自动进入实现 / SE-02D / Runtime Host。
- `main` 的新 accepted tip 见 `PROJECT_STATE.md` 与 Git `main`（CIP-02 实时读取）。

## 12. Evidence Pointer

- Design artifact（Accepted）：`docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`
- Human-Accepted candidate：`e3fb721c678e2b3ca0af6fb4663f349c6a641159`
  （branch `design/pre-01a-d1-real-ai-v1-contract`）
- Previous Accepted main：`b77c80333b85d6e3f1095ac7da9b13e9bf08163a`
- Closeout branch：`pre-01a-d1-final-acceptance-closeout`
