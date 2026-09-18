# UI-RD01-I02｜需求冻结 — 需求持久化

## Task

- Task ID: `UI-RD01-I02-REQ-01-PERSIST`
- Window Title: `UI-RD01-I02｜需求冻结`
- Task Type: `DOCUMENT PERSISTENCE + STATE SYNC ONLY`
- Protocol Baseline: `v1.4.0 / ACCEPTED`（协议仓 `zwmhua2-lab2/ai-dev-protocol` main = `c6023356a02b23866d805c30f9fed08a0fabdfce`；`AI_BOOTSTRAP.md` 实读 Protocol Version = `1.4.0`、Protocol Status = `ACCEPTED`）
- formal task_state: `IMPLEMENTING`
- Completion Marker: `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`

## Requirement

将已 Human-Confirmed 的 `UI-RD01-I02`（市场扫描与机会追踪 Product Read）实施需求语义持久化为正式仓库工件，并只做最小状态同步。本任务**不**实现 `UI-RD01-I02`。

## Scope

1. 复核 Global Protocol `v1.4.0 / ACCEPTED`。
2. 复核远端 MarketPulse `main` 实际 ref。
3. 创建正式 I02 需求工件：`docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`。
4. 持久化已批准需求语义（**不**重新设计）。
5. 最小同步 `PROJECT_STATE.md` / `AI_CONTEXT.md`。
6. 新增 `dev_log/2026-09-19-ui-rd01-i02-requirements.md`。
7. 记录 v1.4.0 timing 字段。
8. 验证 docs/state-only scope。
9. commit 并 push 专用 candidate branch。
10. STOP，等待 Independent Review。

## Out of Scope

- `UI-RD01-I02` implementation（I02-A coding / I02-B coding）、Product endpoint implementation、schema / migration / index 变更、RuntimeHost / ProductReadContext / Product DTO implementation、runtime 变更。
- `backend/src/**`、`backend/tests/**`、`backend/alembic/**`、`frontend/src/**`（含 `frontend/src/api/generated.ts`）、`frontend/package.json`、`frontend/package-lock.json`、`pyproject.toml`、`PRODUCT_REQUIREMENTS.md`、`DECISIONS.md`、既有 frozen UI-RD01 artifact、既有 Post-Freeze Amendment artifact = **ZERO CHANGE**。
- **不** merge `main`；**不** reset / rebase / squash / force push。
- **不**声称任何 Human Acceptance / `ACCEPTED` / `FROZEN`；**不**激活 `PRE-01B-I2` / Real AI / live `G2→G3` / Gate A/B/C / Live。

## Human Content Confirmation

`CONFIRMED — 2026-09-19`

## Repository Baseline

| 字段 | 值 |
|---|---|
| Task Base（任务卡声明） | `08b6c5d6eebb5339756378ace80cb97d504ee25d` |
| remote `main`（执行前实读 `git ls-remote origin refs/heads/main`） | `08b6c5d6eebb5339756378ace80cb97d504ee25d` |
| baseline drift | **无**（一致） |
| task branch | `design/ui-rd01-i02-requirements`（单 parent = Task Base） |
| 集成 | **未** merge `main` |

- 本地 `main` ref 实测 = `de0f8d83c4a917f3fa801e1ef5c703cd9d9a5a84`（**陈旧**，落后于远端）。按 CIP-02 / CIP-03 以远端 `ls-remote` 真值为准；本任务**未**以任何形式推进本地 `main`，**未**做 reset / rebase。
- 任务 worktree = `E:/Documents/MarketPulse-AI-ui-rd01-i02-persist`（执行前 `git status --porcelain` 为空）。

## Changes

| 文件 | 类型 |
|---|---|
| `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md` | 新增（正式 I02 需求工件） |
| `PROJECT_STATE.md` | 最小插入（Current Group 条目 + 文末 `## UI-RD01-I02 Requirement Persistence Result`） |
| `AI_CONTEXT.md` | 最小插入（`## UI-RD01 Accepted Design Pointer` 顶部 1 条 compact pointer） |
| `dev_log/2026-09-19-ui-rd01-i02-requirements.md` | 新增（本文件） |

Markdown 归一化声明（**仅格式，无语义改动**）：

1. 工件标题由 `## UI-RD01-I02｜…` 提升为 `# UI-RD01-I02｜…`（与其他正式 artifact 的单 H1 约定一致）。
2. 在既有字段块（`Document ID` / `Status` / `Human Content Confirmation` / `Implementation Authorization` / `Protocol Baseline` / `Repository Baseline at Requirement Confirmation` / `Parent Design` / `Implementation Status`）之上补一个 `## Artifact Status` 标题；**字段本身逐字保留**。

除上述两处外，需求正文 59 个编号章节逐字持久化，**未**重写、**未**新增语义、**未**发明契约、**未**替换 Repository Truth 名称。

## Verification

| 检查 | 结果 |
|---|---|
| Protocol 复核 | `v1.4.0 / ACCEPTED`（`AI_BOOTSTRAP.md` 实读） |
| remote `main` 实读 | `08b6c5d6…` = 任务卡期望 ⇒ 无 drift |
| `git status --short` | 仅 4 个授权路径（执行见下） |
| changed-file inventory | `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`（新增）、`PROJECT_STATE.md`（M）、`AI_CONTEXT.md`（M）、`dev_log/2026-09-19-ui-rd01-i02-requirements.md`（新增） |
| scope guard | 路径白名单内**无** `backend/` / `frontend/` / `scripts/` / `tests/` / `alembic/` / 任何 manifest |
| frozen design integrity | `docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md`、`docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md` = `ZERO CHANGE` |
| 纯插入 | `git diff --numstat` = `2 0 AI_CONTEXT.md` / `16 0 PROJECT_STATE.md`（deleted 全为 0） |
| `git diff --check` | 无输出、rc = 0 |
| artifact 结构 | 1 × H1、60 × H2（`## Artifact Status` + 59 编号章节），编号 1–59 **无缺** |
| artifact 关键字段 | `UI-RD01-I02-REQ-01` / `CANDIDATE / PENDING INDEPENDENT REVIEW` / `CONFIRMED — 2026-09-19` / `NOT GRANTED` / `v1.4.0 / ACCEPTED` / `08b6c5d6…` / `NOT STARTED / NOT AUTHORIZED` 全部 PRESENT |
| CR-03 / CR-05 语义保留 | `current_canonical_evidence` vs `decision_bound_evidence`、`NOT_REACHED` vs `NOT_YET_DUE`、六值 `TraceNodeState` 均 PRESENT |
| revision-folding 复用要求 | `marketpulse.edge.aggregation_snapshot` 复用 + 禁第二套 folding 算法 PRESENT |
| 无新 schema 授权 | `Schema = ZERO CHANGE` / `Migration = ZERO CHANGE` / `Index = ZERO CHANGE` PRESENT |
| 虚假声明扫描 | `Real AI activated` / `G2→G3 activated` / `Gate C passed` / `Live authorized` / `Forward Outcome runtime wired` / `PRE-01B-I2 complete` 六类反向正则：**零命中** |
| state doc 授权口径 | `PROJECT_STATE.md` / `AI_CONTEXT.md` 均明写 `Implementation Authorization = NOT GRANTED` 与 `UI-RD01-I02 = NOT STARTED / NOT AUTHORIZED` |
| 无 `ACCEPTED` / `FROZEN` 声称 | 新工件与状态同步均标注 `CANDIDATE / PENDING INDEPENDENT REVIEW`（含显式 `**未** 声明 ACCEPTED / FROZEN` 否定） |
| 后端 / 前端回归 | `NOT REQUIRED / NOT RUN`（无实现面变更；**不**据此声称任何运行时行为已验证） |
| push 后远端复读 | 见 §Evidence（candidate branch SHA + `refs/heads/main` 双复读） |

> Commit / push / 远端复读紧随 timing 采集之后，其证据为 commit SHA 与 `git ls-remote` 复读结果（见 §Evidence），不计入下表 `Run Duration`。

## Timing

- Estimated Run Duration: `00:08:00–00:15:00`
- Execution Started At: `2026-09-19T01:12:53+08:00`（来源 = 宿主会话时钟在 Task 开始时的读数；早于 task ref 落盘时刻 `2026-09-19T01:14:17+08:00`）
- Completed At: `2026-09-19T01:18:01+08:00`
- Run Duration: `00:05:08`
- Estimate Delta: `-00:02:51 vs lower bound`

## Remaining

- Independent Review **pending**。
- Formal Human Freeze **pending**。
- `UI-RD01-I02-A` = `NOT STARTED`。
- `UI-RD01-I02-B` = `NOT STARTED`。
- `UI-RD01-I02` implementation = `NOT AUTHORIZED`。
- 未解锁（保持）：`I03` / `I04` / `I05`、`PRE-01B-I2`、Real AI、live `G2→G3`、Gate A/B/C、Live。

## Evidence

- Protocol: `AI_BOOTSTRAP.md`（协议仓 main `c6023356a02b23866d805c30f9fed08a0fabdfce`）实读 `Protocol Version: 1.4.0` / `Protocol Status: ACCEPTED`。
- remote main（before work）: `git ls-remote origin refs/heads/main` → `08b6c5d6eebb5339756378ace80cb97d504ee25d`。
- task branch: `design/ui-rd01-i02-requirements`。
- candidate commit SHA / 远端 candidate SHA / 远端 main（after push）: `candidate commit SHA = 承载本文件的单 commit（`git rev-parse HEAD`）；remote candidate SHA = push 后 `git ls-remote origin refs/heads/design/ui-rd01-i02-requirements` 复读；远端 `main` after push = `git ls-remote origin refs/heads/main` 复读。三项具体 SHA 值见本批 Completion Report（自引用约束：commit SHA 无法包含于其自身内容）。`。
- 重复设计反证：执行前 `git ls-tree -r --name-only 08b6c5d…` 显示 `docs/design/UI-RD01/` 仅含 `UI-RD01-Product-Read-API-Formal-Design.md`，`dev_log/` 无 `2026-09-19-*` ⇒ 新工件与本文**首次**写入。
- `git diff --numstat`（不含新增文件）: `2 0 AI_CONTEXT.md` / `16 0 PROJECT_STATE.md`。

## Reality Check

- **忽略了什么**：任务卡要求 `PROJECT_STATE.md` 记录 `I03–I05 remain unchanged`，但**未**授权改写既有的 `## UI-RD01 Final Design Acceptance Closeout` 段（该段含多处历史时点记录，且其 `I02–I05` 行已是 `NOT STARTED / NOT AUTHORIZED`）。本批因此**只做纯插入**（Current Group 条目 + 文末新段），不触碰既有历史段 ⇒ `I03–I05` 一行未改即等价于「不变」。
- **最坏情况**：若 `PROJECT_STATE.md` 的 `## Current Group` 段本身是陈旧索引（本仓库已知存在此类 stale index 行，例如 `Integrated Runtime Host — NOT STARTED`），则新条目可能被下游窗口当作「I02 正在进行中」的暗示。缓解：条目与文末段落均显式写 `Implementation Authorization = NOT GRANTED` 与 `UI-RD01-I02 = NOT STARTED / NOT AUTHORIZED`，并把 `I02-A` / `I02-B` 逐项标 `NOT STARTED`。
- **有没有更简单的方案**：可以把全段只写进文末 `## … Result` 段、不动 `## Current Group`。未采用：Current Group 是「当前 Group 状态」的第一入口，缺少条目会让 `UI-RD01-I02-REQ-01` 在常规入口不可见，反而提高后续窗口凭旧记忆推断的风险。两处插入合计 18 行，仍属最小同步。

## Context For Next AI

- 本批**仅**持久化需求。`UI-RD01-I02` 仍 `NOT STARTED / NOT AUTHORIZED`；下一步是 **Independent Review**（**不是**实现）。
- 复核本批前请实读：`docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`（尤其 `## Artifact Status`、§2 Source of Truth、§43 No New Schema、§48/§49 测试矩阵）、本 dev_log、以及 `git diff` 的**纯插入**证据。
- 若复审通过并获 Human Freeze，才按 §59 顺序下发 `UI-RD01-I02-A｜市场扫描读取`；I02-A / I02-B 必须**分别**路由（§55：I02-A = Risk `MEDIUM`，I02-B = Risk `HIGH`）。
- ⚠ 边界保持（禁止写成 resolved）：`PRE-01B-I2 = NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；`Gate C = NOT PASSED`；Live = `NOT AUTHORIZED`；Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS / NON-BLOCKING`。
- ⚠ 本批**未**修改 `DECISIONS.md`（任务卡明确列为 `ZERO CHANGE`）；`UI-RD01-I02-REQ-01` 的决策条目应在后续获授权窗口处理。
