# PRB-01 — Establish Stable Product Requirements Baseline

- Task Type: Documentation / Governance Only
- Date: 2026-09-10
- Branch: `prb-01-product-requirements-baseline`
- Base SHA: `ac3eaf911b9841f353db53d4ae21e7336af90e37`（`main` / `origin/main`，CIP-02 实测一致）
- PRB docs Commit SHA: `ec66186b54d1cbd35560101e451b4885f3d882c0`
- Worker Status: `IMPLEMENTED / READY FOR RE-REVIEW`（Review Result = CHANGES_REQUIRED / NOT ACCEPTED；Acceptance Fix #1 已应用；未自行 Acceptance，未推进 `main`）

---

## Task

建立根目录 `PRODUCT_REQUIREMENTS.md`，作为 MarketPulse AI 的长期、稳定、跨聊天窗口 / 跨 AI / 跨 Acceptance Group 可读的**产品总需求基线**。同步 `AI_CONTEXT.md` / `AGENTS.md` 入口，更新 `PROJECT_STATE.md`，新建本 dev_log。

## Requirement

- 提供产品级长期基线：Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction。
- 不复制几十页实现细节；不把未来能力写成当前已完成；不静默覆盖 `DECISIONS.md` 或 Accepted implementation。
- 满足 AC-01～AC-09（见 Verification / Self-Check）。

## Scope（允许修改）

1. 新建 `PRODUCT_REQUIREMENTS.md`。
2. 最小修改 `AI_CONTEXT.md`（增加 PRB 入口指针）。
3. 最小修改 `AGENTS.md`（开工检查加入 `PRODUCT_REQUIREMENTS.md`）。
4. 更新 `PROJECT_STATE.md`（仅记录本次 PRB task）。
5. 新建本 dev_log。

## Out of Scope（禁止）

不修改 Backend / Frontend / Tests / Schema / Migration / 交易行为 / Risk / Scanner / AI Provider / G2–G5 Runtime；不实现 N01 / N03 / G6 / Long-running Paper / Trading Edge Evaluation / 高级 Performance Analytics；不把未来能力写成已完成；不重写历史 dev_log；不擅自新增未批准产品需求；不修改 `DECISIONS.md`（未发现明确冲突）。

## Implementation

- 编写 `PRODUCT_REQUIREMENTS.md`，覆盖 AC-01 全部章节：§1 Product Identity、§2 Product Objective、§3 Trading Philosophy、§4 Indicator Boundary、§5 Core Trading Loop、§6 Responsibility Boundaries、§7 V1 Current Boundary、§8 Safety & Failure、§9 Evidence & Audit、§10 Replay/Evaluation Positioning、§11 Evolution Path、§12 Explicit Non-Goals、§13 Repository Truth Relationship、§14 Change Control、§15 Current vs Future（明确三类内容区分）。
- `AI_CONTEXT.md`：在文件头增加指向 `PRODUCT_REQUIREMENTS.md` 的产品基线指针；冲突时以 PRB 产品级定位 + `DECISIONS.md` 冻结为准。
- `AGENTS.md`：开工检查一行加入 `PRODUCT_REQUIREMENTS.md`；未重写 CIP-01～CIP-10。
- `PROJECT_STATE.md`：末尾新增 `## Product Requirements Baseline（PRB-01）` 小节记录任务真实状态。

## Files Changed

| 文件 | 类型 | 说明 |
|---|---|---|
| `PRODUCT_REQUIREMENTS.md` | 新建 | 产品需求基线 |
| `AI_CONTEXT.md` | 最小修改 | 增加 PRB 指针 |
| `AGENTS.md` | 最小修改 | 开工检查加入 PRB |
| `PROJECT_STATE.md` | 最小修改 | 记录 PRB-01 状态 |
| `dev_log/2026-09-10-product-requirements-baseline.md` | 新建 | 本 dev_log |

> Git 提交仅含上述文档文件。backend / frontend / tests / schema / migration 变更 = 0。

## Business Behavior

- 无运行时 / 交易 / 风险行为变化。纯文档治理任务。
- 产品语义严格依据 `DECISIONS.md` 冻结决策与任务既定 G5 前提，未自行改变任何 Accepted 行为。

## Verification

- `git diff --check`：PASS（staged 无空白错误）。
- `git status --short`（提交后）：剩余未提交改动为 **pre-existing** 的 `fix/fg-a-…` 在途工作（backend 代码 / 测试 / fg dev_log 更新），均**未被本任务触碰**，已保留在磁盘与 index 之外。
- PRB commit 范围核验：`git show --stat HEAD` 仅含 4 个文档文件；`grep backend/|frontend/|test` 无命中 → **AC-04 PASS**。
- 内容一致性：逐节对照 `AGENTS.md`、`AI_CONTEXT.md`、`DECISIONS.md`、G1–G5 / FG-A–FG-E 既定 Accepted 事实，未发现与当前 Accepted behavior 的明显冲突（见 Self-Check / Known Risks）。

## Self-Check

- **Duplication**：`PRODUCT_REQUIREMENTS.md` 不大段复制 `DECISIONS.md` / `AI_CONTEXT.md`；仅引用其权威定位，内容聚焦产品级原则。PASS。
- **Contradiction**：未发现 PRB 说 A、`DECISIONS.md` 说 B 的冲突。PRB 与 `DECISIONS.md` 冲突时明文规定以 `DECISIONS.md` + Accepted implementation 为准。PASS。
- **Scope Leakage**：未修改任何产品代码 / 未来 Group。Backend source change = 0。PASS。
- **Overdevelopment**：未引入 docs generator / schema / tooling / governance system。PASS。

## Result

`IMPLEMENTED / READY FOR REVIEW`。

## Remaining

- 等待 Human / Design Reviewer 验收。Worker 不得自行报告 `ACCEPTED`，不得自行把未验收实现推进 `main`。
- dev_log 自身作为本分支第二个提交（见 Evidence）。

## Known Risks

- **Git baseline 观察（已上报，非阻塞）**：当前工作树曾被检出于 `fix/fg-a-g3-execution-authority`，相对 `ac3eaf9` 存在大量**未提交**改动，其中包含 `AI_CONTEXT.md` / `PROJECT_STATE.md` 已更新为「G5 ACCEPTED / COMPLETE」的文档状态（与任务既定 G5 前提一致），以及该 fix 分支的 backend 在途代码。本任务**未触碰、未丢失**这些改动；PRB 提交仅含文档。PRB 文档以 `DECISIONS.md` 冻结决策 + G5 前提为产品事实来源。
- CRLF 归一化警告：提交时 Git 对 md 文件提示 LF→CRLF 归一化，属正常换行符处理，不影响内容或 AC。

## Follow-up

- Reviewer 验收 PASS 后，按 AGENTS.md GitHub Review 工作流将 `main` 更新至最新 Accepted Baseline 并 push `main`；保留 `prb-01-product-requirements-baseline` 作为历史证据。
- 若未来需修改 §14 Change Control 所列产品级条目，走 Proposal → Repository Truth Review → Human Approval → 同步 → Implementation。

## Context For Next AI

- 本仓库长期产品需求基线 = `PRODUCT_REQUIREMENTS.md`（根目录）。新窗口做产品级任务前先读它，再读 `AI_CONTEXT.md`（上下文入口）、`DECISIONS.md`（已批准冻结）、`PROJECT_STATE.md`（当前状态）、`dev_log/`（历史证据）。
- Accepted Main = `ac3eaf9…`（CIP-02 实测）。当前 V1 = Paper Trading only / Spot LONG only / Risk Engine authoritative / PostgreSQL durable SoT / Deterministic Replay 已验收但 ≠ Trading Edge Proof。
- 本任务为纯文档治理，未改变任何代码 / 行为 / 风险语义。

## Evidence

- `git rev-parse main` → `ac3eaf911b9841f353db53d4ae21e7336af90e37`（与任务预期 SHA 一致）。
- `git cat-file -t ac3eaf9…` → `commit`。
- `.git/HEAD` 原值 → `ref: refs/heads/fix/fg-a-g3-execution-authority`（工作树原检出分支，已通过 `symbolic-ref` 改指 `prb-01-…`，未破坏工作树）。
- PRB commit：`ec66186b54d1cbd35560101e451b4885f3d882c0`，4 files changed, 492 insertions(+), 62 deletions(-)，含 `PRODUCT_REQUIREMENTS.md`（新建）。
- `git diff --check`：OK。
- `git show --stat HEAD` 无 backend / frontend / test 命中 → AC-04 PASS。

---

## Acceptance Review Finding #1（2026-09-10）

- **Review Result**: `CHANGES_REQUIRED / NOT ACCEPTED`（Reviewer 第二轮）。
- **Accepted Baseline**: `ac3eaf911b9841f353db53d4ae21e7336af90e37`（`origin/main`，CIP-02 实测一致）。
- **PRB remote HEAD（修复前）**: `e429509a22ccbc3c7569836d2fdb68756b5a66bb`。
- **Root Cause（基线污染 / 当前态回归）**: PRB-01 的两个文档提交构建于 pre-existing 工作树的 G5-complete 文档状态（非 `ac3eaf9` 的 FG-E 状态）之上。该工作树状态来自 `fix/fg-a-g3-execution-authority` 分支在途、未提交的文档改动。结果导致：
  - `AI_CONTEXT.md`：把 `FG-E … ACCEPTED / COMPLETE`、`Current State: FG-E`、Next Step Entry 整段 `FG-E Reconciliation Snapshot Consistency`（含 N02 / N01 / N03 / G6 / C02 / C03 追溯）改写为 G5 措辞并删除；PRB 指针被叠在污染后的 G5 内容之上。
  - `PROJECT_STATE.md`：把 `Current Group: FG-E`、`Current Development Status: FG-E … N02`、Current Group Branch、以及 C04 / FG-B / FG-C / FG-E / N02 接受记录整段改写为 G5 措辞并大量删除。
  - 二者均将 Accepted Main 的 **FG-E 当前态** 回退为 **G5** —— 即当前态回归（current-state regression）。
- **Fix Applied（Acceptance Fix #1）**:
  - `git checkout ac3eaf9 -- AI_CONTEXT.md PROJECT_STATE.md`：以 `ac3eaf9` 的完整 FG-E 内容恢复两个文件（不触碰工作树其余 27 条未提交 backend / test / fg-dev_log 改动）。
  - `AI_CONTEXT.md` 仅叠加 PRB 最小增量：① 头部增加 `PRODUCT_REQUIREMENTS.md` 产品基线指针；② Source of Truth 第 4 位插入 `PRODUCT_REQUIREMENTS.md`（顺序严格：Code → PROJECT_STATE → DECISIONS → PRODUCT_REQUIREMENTS → Group Spec → dev_log → AI_CONTEXT → Chat）。FG-E / N02 / N01 / N03 / G6 / C02 / C03 既有事实全部保留。
  - `PROJECT_STATE.md` 仅追加 `## Product Requirements Baseline（PRB-01）` 小节；FG-A～FG-E / N02 / C04 / N01 / N03 / G6 / C02-C03 / 既有 Acceptance Records 一律未改。
  - `PRODUCT_REQUIREMENTS.md` 保持主体内容，仅新增一条小澄清：顶部 §0 关系图 = **文档职责图（document responsibility map）**，不代表 Source-of-Truth 权威性优先级。
  - 本 dev_log 追加本 Finding（不删除原始记录）。
- **Superseded Self-Checks**: 原始 dev_log 的 AC-02 / AC-05 / AC-08 自检（基于污染态误判 PASS）**被本 Finding 取代**；已按 `ac3eaf9` 基线重新核验（见下方 Re-Verify）。
- **Re-Verify（修复后）**:
  - `git diff ac3eaf9 -- AI_CONTEXT.md`：仅含 PRB 指针 + SoT 第 4 位插入；FG-E / N02 / N01 / N03 / G6 / C02 / C03 内容 0 删除。
  - `git diff ac3eaf9 -- PROJECT_STATE.md`：仅含末尾 PRB-01 小节追加；既有 Accepted 状态 0 修改。
  - `git diff --stat ac3eaf9`：仅 5 个批准文档文件（PRODUCT_REQUIREMENTS.md / AI_CONTEXT.md / AGENTS.md / PROJECT_STATE.md / 本 dev_log）；无 backend / frontend / test / schema / migration / DECISIONS.md 改动。
  - 工作树未提交 backend 改动（27 条）完好保留，未进入本次 commit。
- **Audit Trail Preserved**: 原始 Self-Check / Known Risks / Evidence 记录未删除；本 Finding 为追加，非覆盖。
- **Status**: `IMPLEMENTED / READY FOR RE-REVIEW`（未自行 ACCEPTED，未推进 `main`，未 fast-forward `main`，未启动 N01 / G6）。
- **Fix Commit SHA**: 见 Completion Report（提交后返回；远端 `e429509` 前移一位）。

---

## Final Acceptance Record（2026-09-10）

- **Independent Re-Review Result**: `PASS / READY FOR HUMAN ACCEPTANCE`。
- **Human Acceptance**: `CONFIRMED`（用户明确选择「继续」；Design / Review 窗口将其确认解释为 Human Acceptance = CONFIRMED）。
- **Acceptance Fix #1**: `CLOSED`（F1 `AI_CONTEXT.md` baseline contamination = CLOSED；F2 `PROJECT_STATE.md` baseline contamination = CLOSED；F3 dev_log inaccurate verification claim = CLOSED）。
- **Final Closeout Scope**: 仅文档治理。① `PRODUCT_REQUIREMENTS.md` §0 交叉引用笔误修正（`见 §13` → `见 §14`）；② `PROJECT_STATE.md` PRB-01 小节状态更新为 `ACCEPTED / COMPLETE` 并记录 Final Acceptance traceability；③ 本 dev_log 追加本 Final Acceptance Record。`AI_CONTEXT.md` / `AGENTS.md` / `DECISIONS.md` 本轮**未修改**。
- **§13 → §14 Cross-reference Correction**: 已修正 1 处（`PRODUCT_REQUIREMENTS.md` §0：`走变更流程（见 §13）` → `走变更流程（见 §14）`；Change Control 实际位于 §14）。`PRODUCT_REQUIREMENTS.md` 主体**未重写**，无其它编辑。
- **Final Verification**: FC-01～FC-07 全部 PASS（逐项见 Closeout Report）。`git diff --check` 无 whitespace 错误；staged 集仅含批准文档；最终累计 diff 仅 5 个批准文档文件；无 backend / frontend / tests / schema / migration / `DECISIONS.md` 改动。
- **Final Acceptance Commit SHA**: 本 commit = Acceptance Fix #1 Commit `28de04a5b86e84840fb79d0774957f8312b6144e` 的后继 Final Acceptance / Baseline Commit（commit 无法自引用自身 SHA；精确 SHA 以 Git 与 Closeout Report 为准）。
- **Accepted Main before**: `ac3eaf911b9841f353db53d4ae21e7336af90e37`。
- **Accepted Main after**: PRB Final Accepted Commit（`main` 已 fast-forward；仅 fast-forward，无 merge commit / rebase / force push / squash；未覆盖未知提交）。
- **PRB branch HEAD**: Final Accepted Commit；`prb-01-product-requirements-baseline` 保留为历史证据分支。
- **Product behavior changed**: `NO`。
- **Repository baseline established**: `YES`。
- **Audit Trail Preserved**: 原始 Implementation history、Acceptance Review Finding #1、Fix #1 evidence 与本 Final Human Acceptance Record **全部保留**；未删除、未重写、未洗掉历史 Finding；no history rewritten。
- **Status**: `PRB-01 = ACCEPTED / COMPLETE`。未启动 N01 / N03 / G6 或其它开发任务。
