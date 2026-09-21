# 2026-09-21 UI-RD01-I03 Requirements Freeze Persistence — FIX-01

## Task

- Task ID: `UI-RD01-I03-REQ-04-FREEZE-PERSIST-01-FIX-01`
- Window Title: `UI-RD01｜需求冻结落库修复·I03`
- Task Type: `DOCUMENTATION-ONLY / FINDING CLOSURE`
- Requirement ID: `UI-RD01-I03-REQ-04`
- Accepted Limited Amendment: `UI-RD01-I03-PLA-01`
- Mode: `DOCS ONLY — NO PRODUCTION IMPLEMENTATION`
- Finding Under Closure: `UI-RD01-I03-FREEZE-IR-F01 / P1`
- Parent Candidate: `ad69fec94e28a827eebefa7bbdcb0f737cac3c97`
- Target Branch: `ui-rd01-i03-requirements-freeze-persist`
- Completion Marker: `FIXED / READY FOR INDEPENDENT RE-REVIEW`

## Parent Candidate

- Parent = `ad69fec94e28a827eebefa7bbdcb0f737cac3c97`
- 解析方式：`git rev-parse ad69fec94e28a827eebefa7bbdcb0f737cac3c97`；local `refs/heads/ui-rd01-i03-requirements-freeze-persist` 同值。
- remote 同分支同值：`git ls-remote origin refs/heads/ui-rd01-i03-requirements-freeze-persist` = `ad69fec94e28a827eebefa7bbdcb0f737cac3c97`。
- 本批 Fix commit 的 **唯一 parent** = 上述 SHA；**未** amend、**未** rewrite、**未** force push。

## Finding

`UI-RD01-I03-FREEZE-IR-F01 / P1`

冻结工件 `docs/design/UI-RD01/UI-RD01-I03-Implementation-Requirements.md` 的 `A88. Performance Fixtures` 中，Human-Frozen threshold 被错误持久化为带断行的比较运算符：

```text
* > = 5,000 Orders
* > = 5,000 Fills
* > = 5,000 Ledger entries
* > = 5,000 PositionEvents
```

准确 Frozen Requirement 应为紧邻形式：

```text
* >= 5,000 Orders
* >= 5,000 Fills
* >= 5,000 Ledger entries
* >= 5,000 PositionEvents
```

影响面仅限于 A88 这四条 verification workload fixture threshold 的**书写形式**；threshold 数值（5,000）与所涉对象（Orders / Fills / Ledger entries / PositionEvents）**未**改变，也不涉及任何 other section。

## Root Cause

Persistence 阶段从任务卡 `APPENDIX A — HUMAN-FROZEN UI-RD01-I03-REQ-04` 逐字搬运正文时，该四条 `>=` 在 source 侧（长文本 / 粘贴链路）已被拆成 `> =`（`>` 与 `=` 之间插入空格），持久化脚本按「逐字持久化」原则原样落盘，未对比较运算符做形式校验，因此该偏差未被捕获。

- 性质：**source-side 字符级转录偏差**（`>=` → `> =`），非设计/语义决策。
- 非根因（已排除）：**不是** Requirement 设计变更、**不是** wording cleanup 遗漏、**不是** A88 结构问题。
- 范围特征：全文 `> = ` 命中数 = **4**，全部位于 A88（`git grep -n "> = "` 实测）。其余 `>` / `>=` 用法均正常，无同源偏差。

## Exact Fix

仅对 A88 四条目标行做字符级替换（`> = 5,000` → `>= 5,000`）：

| # | 行号 | FROM | TO |
|---|---|---|---|
| 1 | 1934 | `* > = 5,000 Orders` | `* >= 5,000 Orders` |
| 2 | 1935 | `* > = 5,000 Fills` | `* >= 5,000 Fills` |
| 3 | 1936 | `* > = 5,000 Ledger entries` | `* >= 5,000 Ledger entries` |
| 4 | 1937 | `* > = 5,000 PositionEvents` | `* >= 5,000 PositionEvents` |

替换执行方式：逐条 exact-string 替换，每条**断言命中数 == 1** 后再写入（避免锚点漂移导致静默 0 命中或误伤）。每行仅移除 1 个空格字符。

**未**做：Requirement redesign、wording cleanup、formatting cleanup、section reordering、REQ-05、新 Amendment、四行以外任何字符改动。

## Changed Paths

| 路径 | 类型 | 说明 |
|---|---|---|
| `docs/design/UI-RD01/UI-RD01-I03-Implementation-Requirements.md` | 修改 | 仅 A88 四条 threshold 行（1934–1937） |
| `dev_log/2026-09-21-ui-rd01-i03-requirements-freeze-persist-fix-01.md` | 新增 | 本文件 |

`PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` / `backend/**` / `backend/tests/**` / `backend/alembic/**` / `frontend/**` / `scripts/**` **全部零改动**（实测证据见 §Verification）。

## Verification

| 检查 | 结果 |
|---|---|
| AC01 exact parent | branch = `ui-rd01-i03-requirements-freeze-persist`；HEAD = `ad69fec94e28a827eebefa7bbdcb0f737cac3c97`；worktree 执行前 `git status --porcelain` 为空 |
| AC02 A88 exact threshold audit | 四条 `* >= 5,000 {Orders\|Fills\|Ledger entries\|PositionEvents}` 各命中 **1** 次；`> = 5,000` 全文命中 **0** |
| AC03 Requirement delta audit | 行数不变 `2120 → 2120`；differing lines = `[1934,1935,1936,1937]` **仅 4 行**；`normalized(parent) === working_copy` 成立（把 parent 的 4 处 `> = ` 归一化后与工作副本**逐字节相等**）⇒ 除这 4 行外无任何语义变化 |
| file-form preservation | LF 计数不变 `2119`；无 BOM；仍以恰好一个换行结束；`git hash-object` 前后 blob 仅因这 4 行而变 |
| `git diff --check` | 无输出、rc = 0 |
| conflict-marker scan | 工件内 `<<<<<<<` / `=======` / `>>>>>>>` 零命中 |
| exact changed-path audit | `git status --porcelain` = 仅上述 2 路径；`git diff --name-only <parent>` 内容差异路径仅 1 条（Requirement artifact） |
| `"> = 5,000"` 反查 | 零命中（修复后） |
| backend zero-diff audit | `git status --porcelain -- backend` 空；vs parent 无差异 |
| frontend zero-diff audit | `git status --porcelain -- frontend` 空 |
| schema / migration zero-diff audit | `-- backend/alembic backend/src/marketpulse/db` 空；无新增/修改 migration |
| scripts zero-diff audit | `git status --porcelain -- scripts` 空 |
| lifecycle state preservation（AC04） | `UI-RD01-I03-REQ-04 = ACCEPTED / FROZEN`、`UI-RD01-I03-PLA-01 = ACCEPTED`、`R04-P2-01 = NON-BLOCKING / REMAINS`、`UI-RD01-I03 implementation = NOT STARTED / NOT AUTHORIZED`、`Freeze Persistence = READY FOR INDEPENDENT REVIEW` 全部**未变**；A88 块内不含任何 lifecycle 状态文本 |
| 原 persistence dev_log | **未修改**（历史记录保持原样，本批新增独立 FIX-01 dev_log） |
| candidate lineage（AC08） | Fix commit 单 parent = Parent Candidate；`git rev-list --parents -n 1 HEAD` 恰 2 token |
| push（AC09） | local FIX-01 SHA == remote branch SHA（`git ls-remote` 复读） |
| remote `main` untouched（AC10） | push 后 `git ls-remote origin refs/heads/main` = `f7715f58f9da6fa57426b1df31a23692ac6a41a1` |
| 后端 / 前端回归 | `NOT REQUIRED / NOT RUN`（docs-only，无实现面变更；**不**据此声称任何运行时行为已验证） |

## Candidate SHA

- Fix commit SHA（承载本文件的单 commit）见本批 Completion Report —— commit SHA 无法包含于其自身承载的文件中；**未**为此额外开第二个 commit。

## Remote Candidate SHA

- `git ls-remote origin refs/heads/ui-rd01-i03-requirements-freeze-persist` 复读值（见 Completion Report）。

## Remaining

- `UI-RD01-I03-FREEZE-IR-F01` = `CLOSED / READY FOR INDEPENDENT RE-REVIEW`（**未**声明 Independent Review PASS —— 复审由独立窗口执行）。
- Freeze Persistence Candidate = `FIXED / READY FOR INDEPENDENT RE-REVIEW`（**未**声明 `REPOSITORY-INTEGRATED`）。
- `UI-RD01-I03` implementation = `NOT STARTED / NOT AUTHORIZED`（**未**声明 `I03 COMPLETE`）。
- TradingAuditRead = **未**实现（**未**声明 `TradingAuditRead IMPLEMENTED`）。
- Closeout / main integration = **NOT PERFORMED**（**未** merge、**未** fast-forward、**未** push `main`）。
- `R04-P2-01` = `REMAINS / NON-BLOCKING`（**禁止**写成 resolved）。
- `UI-RD01-I04` / `UI-RD01-I05` = `NOT STARTED / NOT AUTHORIZED` **不变**。
- 边界保持：`PRE-01B-I2` = `ACCEPTED / COMPLETE`（本批**未**修改）；`Gate C = NOT PASSED`；Live = `NOT AUTHORIZED`。

## Context For Next AI

- 本批**仅**关闭一条 P1 转录缺陷，未改变任何 Requirement 语义、未改变任何 lifecycle 状态。
- 复核请实读 `A88. Performance Fixtures`（threshold 四条）与 `git diff ad69fec -- docs/design/UI-RD01/UI-RD01-I03-Implementation-Requirements.md` 的 4 行 diff；不要依赖本文件的自述。
- 本批**未**触碰 `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md`（与 FIX 任务卡的 Forbidden Paths 一致）；这三个文件中的 freeze persistence 陈述仍然有效。
