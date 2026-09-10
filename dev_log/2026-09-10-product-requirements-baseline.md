# PRB-01 — Establish Stable Product Requirements Baseline

- Task Type: Documentation / Governance Only
- Date: 2026-09-10
- Branch: `prb-01-product-requirements-baseline`
- Base SHA: `ac3eaf911b9841f353db53d4ae21e7336af90e37`（`main` / `origin/main`，CIP-02 实测一致）
- PRB docs Commit SHA: `ec66186b54d1cbd35560101e451b4885f3d882c0`
- Worker Status: `IMPLEMENTED / READY FOR REVIEW`（未自行 Acceptance，未推进 `main`）

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
