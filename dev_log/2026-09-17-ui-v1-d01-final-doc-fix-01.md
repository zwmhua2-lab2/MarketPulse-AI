# UI-V1-D01-FINAL-DOC-01-FIX-01｜UI V1 Formal Design Persistence — Contract Consistency & Documentation Compression Fix

## Task

- Task ID：`UI-V1-D01-FINAL-DOC-01-FIX-01`。
- Task Name：UI V1 Formal Design Persistence — Contract Consistency & Documentation Compression Fix。
- Type：**DOCS / STATE ONLY**。`NO IMPLEMENTATION`。
- Reviewed candidate：`1919832a5d9ddbcbec6ea535d178e3d21795b539`
  （branch `design/ui-v1-d01-formal-freeze`）。
- Goal：修复该候选上独立复审提出的两条 P1 finding —— Axis A 契约不一致（P1-01）与
  `DECISIONS.md` 过度复制 Formal Design（P1-02）。
- 本任务**不**重新设计 UI、**不**新增或改变产品需求与业务语义、**不**选前端库、
  **不**实现任何前端 / 后端代码、**不**改 schema / migration / config / runtime、
  **不** merge `main`、**不** amend reviewed candidate。

## Scope

执行角色为 **EXECUTOR**（不是 product designer）：只做两处最小修复 + 一份新 dev_log。

允许改动路径**恰好三个**：

1. `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（P1-01，1 行）
2. `DECISIONS.md`（P1-02，压缩 UI-V1-D01 条目）
3. `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-01.md`（本文件，新增）

## Out of Scope

明确**未**触碰：

- `PROJECT_STATE.md`、`AI_CONTEXT.md`、`PRODUCT_REQUIREMENTS.md`
- `backend/**`、`frontend/**`、`scripts/**`、`tests/**`、`alembic/**`、schema、migration
- 配置 / dependency manifest、runtime 代码与运行状态
- 其它既有 design artifact（含 `PRE-01B-D2`）、任何往期 `dev_log`
- 外部 Skill、用户记忆、任何无关工作区治理文件

并明确**未**：创建 / 修改外部 Skill、写入用户记忆、merge `main`、rebase、
amend reviewed candidate、force push、改动远端任何其它 ref。

## Preflight

### Rule Baseline

- Repository：`zwmhua2-lab2/ai-dev-protocol`。
- 实时实测 `git ls-remote https://github.com/zwmhua2-lab2/ai-dev-protocol.git refs/heads/main`
  = `a80c55b7451f77883d8b0713a228f0d9bebf7d22`（与上一批 `UI-V1-D01-FINAL-DOC-01` 记录同值
  ⇒ 协议基线**未漂移**）。
- `Protocol Version = 1.1.0` / `Protocol Status = ACCEPTED`（沿用上一批已实测值，本批
  remote `main` SHA 未变）。
- 结论：Rule baseline = **VERIFIED**（非 `RULE BASELINE NOT VERIFIED`）。

### Reviewed Candidate / Accepted Main / Lineage

| 项 | 期望 | 实测 | 结论 |
|---|---|---|---|
| remote `main` | `547095f6705ce651272363676e2a2b51a66bb8b6` | `547095f6705ce651272363676e2a2b51a66bb8b6` | MATCH |
| local `main` / `origin/main` | 同上 | `547095f…` / `547095f…` | MATCH |
| remote `design/ui-v1-d01-formal-freeze` | `1919832a5d9ddbcbec6ea535d178e3d21795b539` | `1919832a5d9ddbcbec6ea535d178e3d21795b539` | MATCH |
| remote `design/ui-v1-d01-final-doc-fix-01` | 不存在（本批新建） | 不存在 | MATCH |
| FIX branch base | = reviewed candidate | HEAD `1919832…`，其 parent = `547095f6…` | MATCH |

⇒ **无 baseline drift**，无需 SHA delta 分类；未做任何 reset / rebase / overwrite。
reviewed candidate branch `design/ui-v1-d01-formal-freeze` **逐字未改**。

### 事实核对（P1-01 的事实依据）

- `git grep -n "advisory_decision_invocations"` 全仓库命中**仅** 2 处，均在
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`；
  `backend/**` **零命中**。
- `git grep -i "advisory" -- backend/src` 的命中项**全部**是 PostgreSQL **advisory lock**
  与 plan invalidation 的 advisory text，**与 AdvisoryIngress 无关**。
- `backend/src/marketpulse/api/` 仅 `__init__.py` / `app.py` / `auth.py` / `market.py`，
  **无** Advisory / G2→G3 读面。
- ⇒ `PRE-01B-I2 = NOT STARTED`（D2 设计已 `ACCEPTED` 但无实现），live `G2→G3` Advisory
  **不存在**当前可消费的正式 Read Truth ⇒ Axis A = `C` 是唯一与 §9.1 冻结词汇表自洽的取值。
  **Accepted Design != 当前 Read Surface。**

## Findings Fixed

### P1-01 — Data Capability Axis A 契约不一致

- 问题：§9.1 冻结 `Axis A ∈ {A, B, C}`，但 §9.3 当前矩阵中 `live G2→G3 Advisory` 的
  Axis A 取值为 `future`（词汇表外取值），契约不自洽。
- 修复：改为 `C`。**仅此一处**，**未**改动任何其它 capability 状态。

```diff
-| live `G2→G3` Advisory | future | `NOT_ACTIVATED` |
+| live `G2→G3` Advisory | `C` | `NOT_ACTIVATED` |
```

- 修复后矩阵 Axis A 取值集合 = `{A, B, C}`（14 行全部命中冻结词汇表）。
- `C` 与 Axis B `NOT_ACTIVATED` 的组合形态合法（§9.3 注：两轴相互独立）。

### P1-02 — `DECISIONS.md` 过度复制 Formal Design

- 问题：UI-V1-D01 条目 145 行，复刻了 Formal Design 的完整细节，使 `DECISIONS.md`
  变成第二份 UI Spec。
- 修复：原地替换该条目正文，压缩为 **47 行决策摘要**（条目仍为文件末条）。
- **保留**（逐条实测存在，共 20 项断言）：`HUMAN-ACCEPTED / FROZEN` + Human Acceptance
  日期 `2026-09-17`、formal artifact 路径、五页 IA、AI 无独立顶层页、Read-Only Business UI、
  前端 = 呈现层而非业务权威、双轴能力模型、Exact Edge Population / 不池化 populations、
  durable Position Protection 权威、当前 live producer 局限、Product Read Projection 原则、
  实施顺序、`不授权任何实现`、`PRE-01B-I2` / Real AI / live `G2→G3` / Forward Outcome
  runtime / Live 的未激活与未集成状态、指向 artifact 的细节指针。
- **移除**（逐条实测已不在新条目内，共 12 项断言）：数据展示状态细目
  （`LOADING` / `EMPTY` / `FRESH` / `STALE` / `UNAVAILABLE` / `CAPABILITY_NOT_INTEGRATED`）、
  `S0`–`S4` / `U0`–`U1` 完整严重度映射表、公开 / 认证 API 全清单与 `/ready` 细节、
  Account 字段全表、System 页对象全清单、Execution Semantics 与经济集合模型细节、
  Edge 指标与充分性细节（含 Tail evidence）、Edge 聚合执行安全细节、Trace 与域来源隔离细节、
  时区与布局细节、前端基础决策清单、`Explicit Out of Scope` 长清单。
- 体量：entry **145 → 47 行**；`DECISIONS.md` **53,038 → 43,294 bytes**。
- ⚠ 本批**不是**纯追加型改动（P1-02 的本质就是压缩），故 deletions 非 0 属**预期**；
  P1-01 仍为单行等价替换（`+1 / −1`）。

## Changed Paths

相对 reviewed candidate `1919832…`，本分支**恰好**改动 3 个路径：

1. `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（P1-01）
2. `DECISIONS.md`（P1-02）
3. `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-01.md`（本文件，新增）

除上述 3 个允许路径外，**无任何其它路径变更**。

## Explicit Zero-Change Production Scope

```text
Production Code = ZERO CHANGE
Frontend Code   = ZERO CHANGE
Backend Code    = ZERO CHANGE
Tests           = ZERO CHANGE
Schema          = ZERO CHANGE
Migration       = ZERO CHANGE
Configuration   = ZERO CHANGE
Dependency Manifests = ZERO CHANGE
Runtime Behavior = ZERO CHANGE
PROJECT_STATE.md = ZERO CHANGE
AI_CONTEXT.md    = ZERO CHANGE
PRODUCT_REQUIREMENTS.md = ZERO CHANGE
```

docs-only ⇒ **无 runtime verification 需求**：未运行 Runtime Host、未调用 provider、
未跑 PostgreSQL validation / Docker / soak / Real AI；`ruff` / `pytest` =
`NOT REQUIRED / NOT RUN`。

## Verification

| # | 检查 | 结果 |
|---|---|---|
| 1 | FIX branch base = reviewed candidate `1919832…`（单 parent，parent = `547095f6…`） | `PASS` |
| 2 | `git diff --cached --check`（无 whitespace error / conflict marker） | `PASS` |
| 3 | Changed paths 恰为 3 个允许路径 | `PASS` |
| 4 | Formal Design Axis A 仅含 `A` / `B` / `C` | `PASS` |
| 5 | `live G2→G3` Advisory = `C` / `NOT_ACTIVATED` | `PASS` |
| 6 | `DECISIONS.md` UI-V1-D01 条目为摘要 + 指针（非重复 Spec） | `PASS` |
| 7 | production / frontend / backend / schema / runtime 零改动 | `PASS` |
| 8 | 行尾完整性：三文件均保持**纯 CRLF**（bare LF = 0） | `PASS` |

### 禁止虚假声明扫描（否定感知）

对本批 3 个改动文件逐行扫描 8 类禁止性肯定声明，每一命中均在**同行或相邻行**存在否定词
（`NOT` / `不` / `未` / `无` / `非` / `≠` / `!=` / `DISABLED` / `绝不` / `禁止`）：

```text
"Real AI active / activated"       → 仅以 `NOT ACTIVATED` 形式出现
"G2→G3 active / activated"         → 仅以 `NOT ACTIVE` 形式出现
"Gate C passed / PASS"             → 仅以 `NOT PASSED` 形式出现
"Live authorized"                  → 仅以 `NOT AUTHORIZED / DISABLED` 形式出现
"UI implemented / completed"       → 仅以 `NOT STARTED` 形式出现
"Forward Outcome runtime wired"    → 仅以 `NOT INTEGRATED` 形式出现
"PRE-01B-I2 complete"              → 仅以 `NOT STARTED / NOT ACTIVATED` 形式出现
"Trading Edge proven"              → 仅以 未证明 形式出现
```

**本批新增 / 修改行内的未否定肯定声明数 = 0。**

- **预存在项（本批未改动、属其它条目、**非**本批 scope）**：`DECISIONS.md` 的
  `PRE-01B-D2` 条目内有一条跨行语句，其否定词「**不**构成」位于折行前的上一行（相距 2 行），
  在「同行或相邻行」判据下会出现 1 处**假阳性**；该行与本批改动**无关**
  （与 Task Base 逐字相同），**未**修改。

## Self Review（Reality Check）

- **忽略了什么**：本批只改读面契约字面值与文档体量，**不**改变 `PRE-01B-I2` 未实现的既有
  真值。§9.3 中 `SE-02D Aggregate` 行的 Axis B 写成自然语言
  （`accepted callable core, **no Product consumer**`）而非冻结枚举值 —— 该行**不在**任务卡
  要求面内，**未**改动；作为后续复审观察项记录（非本批 scope，非本批 finding）。
- **最坏情况**：若把 Axis A 改成 `A` 或 `B`，会虚假声称存在可消费读面，可能诱使 UI 静默接通
  Advisory 链；改为 `C` 且 Axis B 保持 `NOT_ACTIVATED`，与 §10 / §45 一致。
  `DECISIONS.md` 压缩的最坏情况是丢失未来实现所需的决策依据 ⇒ 已用 20 项「必须保留」断言
  与 12 项「必须移除」断言双向把守，并保留指向 artifact 的权威指针。
- **有没有更简单的方案**：P1-01 能否只加脚注说明 `future` 的意图？不能 —— §9.1 已冻结 Axis A
  值域，脚注会留下一个词汇表外取值，契约仍不自洽。P1-02 能否只删若干子项？不能 —— 复审结论是
  「条目整体过度复制」，逐项删会留下残缺的第二份 Spec。

## Remaining / Non-Claims

本批**不**声称、**不**证明以下任何一项，且**未**改变其既有真值：

```text
UI implementation            = NOT STARTED
Product Read API             = NOT STARTED
PRE-01B-I2                   = NOT STARTED / NOT ACTIVATED
Real AI                      = NOT ACTIVATED
live G2→G3 Advisory          = NOT ACTIVE
Forward Outcome runtime      = NOT INTEGRATED（无 Product consumer）
Gate A / Gate B              = NOT ACTIVATED
Gate C                       = NOT PASSED
Live                         = NOT AUTHORIZED
Trading Edge                 = 未证明
前端库选型                    = DEFERRED 至 UI-F01
```

- reviewed candidate `1919832…` 保持 **immutable**：本批在其之上新建 FIX branch，
  **未** amend、**未**改写该 branch。
- 下一 Acceptance Group = `NOT STARTED / REQUIRES SEPARATE HUMAN-AUTHORIZED DECISION`；
  本批**不**选择、**不**启动。

## Git / Delivery

- Commit 到 task branch `design/ui-v1-d01-final-doc-fix-01`。
- Commit message：`docs(ui-v1): fix frozen design persistence review findings`。
- 推送 task branch；**不** merge `main`；推送后停止。

## Evidence Pointers

- Formal Design artifact：`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
  （`ACCEPTED / FROZEN`，Human Acceptance = `CONFIRMED — 2026-09-17`）。
- Reviewed candidate：`1919832a5d9ddbcbec6ea535d178e3d21795b539`
  （branch `design/ui-v1-d01-formal-freeze`）。
- Accepted main：`547095f6705ce651272363676e2a2b51a66bb8b6`。
- 上一批 dev_log：`dev_log/2026-09-17-ui-v1-d01-formal-design-freeze.md`。
- `DECISIONS.md` 指针：文末 `UI-V1-D01 V1` 条目。
- 本文件**不**写入自身 commit SHA —— Git ref 是该自引用事实的权威来源。
