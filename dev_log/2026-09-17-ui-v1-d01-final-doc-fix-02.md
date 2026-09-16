# UI-V1-D01-FINAL-DOC-01-FIX-02｜UI V1 Formal Design Persistence — Capability Matrix Contract Closure

## Task

- Task ID：`UI-V1-D01-FINAL-DOC-01-FIX-02`。
- Task Type：**DOCS ONLY / MINIMAL CONTRACT FIX**。`NO IMPLEMENTATION`。
- Reviewed candidate：`e7d69ae38f8a24bdecb4780661342d5cfda734f7`
  （branch `design/ui-v1-d01-final-doc-fix-01`）。
- Goal：修复 §9.3 能力矩阵中唯一剩余的 **Axis B 词汇表违约项** —— `SE-02D Aggregate`
  的 Axis B 被写成自然语言（`accepted callable core, **no Product consumer**`），
  而非 §9.2 冻结的枚举值。
- 本任务**不**重新设计、**不**新增需求、**不**改业务语义、**不**改任何其它 capability
  分类、**不**实现任何代码、**不** merge `main`、**不**改动 reviewed candidate branch。

## Scope

执行角色为 **EXECUTOR**：只做一处契约收敛 + 一处澄清注解 + 一份新 dev_log。

允许改动路径**恰好两个**：

1. `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
2. `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-02.md`（本文件，新增）

## Out of Scope

明确**未**触碰：

- `DECISIONS.md`、`PROJECT_STATE.md`、`AI_CONTEXT.md`、`PRODUCT_REQUIREMENTS.md`
- `backend/**`、`frontend/**`、`tests/**`、`scripts/**`、`alembic/**`、schema、migration
- 配置 / dependency manifest、runtime 代码与运行状态
- 其它既有 design artifact、任何往期 `dev_log`（含 `2026-09-17-ui-v1-d01-final-doc-fix-01.md`）
- 任何 Skill、`.workbuddy`、用户记忆 / 工作区记忆

并明确**未**：重新设计任何内容、创建或更新 Skill、更新 `.workbuddy`、更新用户 / 工作区记忆、
执行任何无关清理、merge `main`、rebase / amend 任何既有 commit、force push。

## Preflight

### Rule Baseline

- Repository：`zwmhua2-lab2/ai-dev-protocol`。
- 实时实测 `git ls-remote https://github.com/zwmhua2-lab2/ai-dev-protocol.git refs/heads/main`
  = `a80c55b7451f77883d8b0713a228f0d9bebf7d22`（与 FIX-01 记录同值 ⇒ 协议基线**未漂移**）。
- `Protocol Version = 1.1.0` / `Protocol Status = ACCEPTED`（沿用已实测值，remote `main` SHA 未变）。
- 结论：Rule baseline = **VERIFIED**。

### Reviewed Candidate / Accepted Main / Lineage

| 项 | 期望 | 实测 | 结论 |
|---|---|---|---|
| remote `design/ui-v1-d01-final-doc-fix-01` | `e7d69ae38f8a24bdecb4780661342d5cfda734f7` | `e7d69ae38f8a24bdecb4780661342d5cfda734f7` | MATCH |
| remote `main` | `547095f6705ce651272363676e2a2b51a66bb8b6` | `547095f6705ce651272363676e2a2b51a66bb8b6` | MATCH |
| local `main` / `origin/main` | 同上 | `547095f…` / `547095f…` | MATCH |
| remote `design/ui-v1-d01-final-doc-fix-02` | 不存在（本批新建） | 不存在 | MATCH |
| FIX-02 branch base | = reviewed candidate | HEAD `e7d69ae…`，其 parent = `1919832…` | MATCH |

⇒ **无 baseline drift**；FIX-01 branch `design/ui-v1-d01-final-doc-fix-01` **逐字未改**。

### 事实核对

- §9.2 冻结 Axis B 词汇表**恰好三个值**：`ACTIVE` / `ACCEPTED_NOT_INTEGRATED` / `NOT_ACTIVATED`。
- 修复前 §9.3 矩阵 14 行中，13 行命中该词汇表，**仅** `SE-02D Aggregate` 一行使用
  自然语言描述 ⇒ 该行是唯一的 Axis B 契约违约项。
- §45 Non-Claims 表内 `SE-02D` Aggregate Product consumer = 「不存在（accepted callable core
  only）」仍准确，**不**属能力矩阵、**未**修改（不在授权面内）。
- `SE-02D` 的已接受状态（Design + I01/I02/I03 实现 + Overall Closeout = `ACCEPTED`，
  accepted **callable core**，**无** Product consumer）与 `ACCEPTED_NOT_INTEGRATED`
  语义一致 —— 该枚举值的定义即「已接受但尚未集成到运行消费面」。

## Fix

### 变更 1 —— Axis B 收敛为冻结枚举值

```diff
-| SE-02D Aggregate | `B` | accepted callable core, **no Product consumer** |
+| SE-02D Aggregate | `B` | `ACCEPTED_NOT_INTEGRATED` |
```

### 变更 2 —— 矩阵下方澄清注解（紧随矩阵）

```text
SE-02D aggregation core is Accepted / callable, but currently has no Product consumer;
therefore its Operational Availability classification is `ACCEPTED_NOT_INTEGRATED`.
```

- 位置：**紧随能力矩阵**，位于既有 axis-independence blockquote 之前。
- 文本：按任务卡给定内容**逐字**插入（未改写、未意译）。

**未**改动任何其它 capability 分类：`Runtime Live / Ready / Health`、`Runtime Telemetry`、
`Market freshness`、`Scanner Event`、`Strategy Candidate`、`Formal live Opportunity Evidence`、
`Forward Outcome automatic production`、`Trading durable facts`、`Incident durable facts`、
`Real AI`、`live G2→G3 Advisory`、`Gate A / B / C runtime activation`、`Live Trading`
共 13 行**逐字未变**。

## Changed Paths

相对 reviewed candidate `e7d69ae…`，本分支**恰好**改动 2 个路径：

1. `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（`+4 / −1`）
2. `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-02.md`（新增，本文件）

除上述 2 个允许路径外，**无任何其它路径变更**。

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
DECISIONS.md = ZERO CHANGE
PROJECT_STATE.md = ZERO CHANGE
AI_CONTEXT.md = ZERO CHANGE
PRODUCT_REQUIREMENTS.md = ZERO CHANGE
```

docs-only ⇒ **无 runtime verification 需求**：未运行 Runtime Host、未调用 provider、
未跑 PostgreSQL validation / Docker / soak / Real AI；`ruff` / `pytest` =
`NOT REQUIRED / NOT RUN`。

## Verification

| # | 检查 | 结果 |
|---|---|---|
| 1 | FIX-02 branch base = reviewed candidate `e7d69ae…`（单 parent，parent = `1919832…`） | `PASS` |
| 2 | §9.3 Axis A 取值仅 `A` / `B` / `C` | `PASS` |
| 3 | §9.3 Axis B 取值仅 `ACTIVE` / `ACCEPTED_NOT_INTEGRATED` / `NOT_ACTIVATED` | `PASS` |
| 4 | `SE-02D Aggregate` = `B` / `ACCEPTED_NOT_INTEGRATED` | `PASS` |
| 5 | `live G2→G3 Advisory` 仍 = `C` / `NOT_ACTIVATED` | `PASS` |
| 6 | Changed paths 恰为 2 个允许文件 | `PASS` |
| 7 | `git diff --cached --check`（无 whitespace error / conflict marker） | `PASS` |
| 8 | production / runtime / frontend / backend / schema / config 零改动 | `PASS` |
| 9 | 行尾完整性：artifact 保持**纯 CRLF**（bare LF = 0） | `PASS` |

### 禁止虚假声明扫描（否定感知）

对本批新增 / 修改行逐行扫描 8 类禁止性肯定声明（`Real AI active` / `G2→G3 active` /
`Gate C passed` / `Live authorized` / `UI implemented` / `Forward Outcome runtime wired` /
`PRE-01B-I2 complete` / `Trading Edge proven`），每一命中均须在**同行或相邻行**存在否定词：

- 本批改动面为**能力矩阵的枚举值与解释性注解**，**不**含任何新增能力断言
  ⇒ **未否定肯定声明数 = 0**（无命中）。

## Self Review（Reality Check）

- **忽略了什么**：§45 Non-Claims 表内的 `SE-02D` Aggregate 行仍是自然语言
  （「不存在（accepted callable core only）」）。该表**不是**能力矩阵，不受 §9.2 词汇表约束，
  且**不在**本批授权面内 ⇒ **未**改动；作为后续复审观察项记录（非本批 scope、非本批 finding）。
- **最坏情况**：若把 `SE-02D Aggregate` 的 Axis B 改为 `ACTIVE`，会虚假声称该聚合已被运行面
  消费，可能诱使 UI 直接渲染不存在的 Product consumer ⇒ 选用 `ACCEPTED_NOT_INTEGRATED`
  与 §45「accepted callable core only / 无 Product consumer」一致，且与同行
  `Formal live Opportunity Evidence` / `Forward Outcome automatic production` 的分类口径统一。
- **有没有更简单的方案**：能否只改矩阵行、不加澄清注解？不能 —— 任务卡要求紧随矩阵补充
  分类依据，避免后续读者误以为 `SE-02D` 能力退化。能否改写注解为中文以贴合文档主语言？
  **未**自行改写：任务卡给出的是待插入内容，EXECUTOR 逐字落盘、不意译（此点已在报告
  「Remaining」中如实标注，供 Human 决定是否后续统一语言）。
- **口径一致性核对**：修复后 §9.3 与 §9.2 词汇表、§10 当前运行局限、§31 AI 当前状态、
  §45 Non-Claims 四处的分类口径**一致**，未产生新的语义冲突。

## Remaining / Non-Claims

本批**不**声称、**不**证明以下任何一项，且**未**改变其既有真值：

```text
UI implementation            = NOT STARTED
Product Read API             = NOT STARTED
PRE-01B-I2                   = NOT STARTED / NOT ACTIVATED
Real AI                      = NOT ACTIVATED
live G2→G3 Advisory          = NOT ACTIVE
Forward Outcome runtime      = NOT INTEGRATED（无 Product consumer）
SE-02D Product consumer      = 不存在（accepted callable core only）
Gate C                       = NOT PASSED
Live                         = NOT AUTHORIZED
Trading Edge                 = 未证明
```

- reviewed candidate `e7d69ae…`（= 本批 Task Base）保持 **immutable**：本批在其之上新建
  FIX-02 branch，**未** amend、**未**改写该 branch，也**未**改写 FIX-01 branch。
- **语言一致性待 Human 决定（非本批 finding）**：本批未自行改写任务卡给定文本，澄清注解
  以英文插入中文为主的 artifact §9.3；如 Human 要求，可另开最小批次统一为中文。

## Git / Delivery

- Commit 到 task branch `design/ui-v1-d01-final-doc-fix-02`。
- Commit message：`docs(ui-v1): close capability matrix contract`。
- 推送 task branch；**不** merge `main`；推送后停止。

## Evidence Pointers

- Formal Design artifact：`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
  （`ACCEPTED / FROZEN`，Human Acceptance = `CONFIRMED — 2026-09-17`）。
- Reviewed candidate：`e7d69ae38f8a24bdecb4780661342d5cfda734f7`
  （branch `design/ui-v1-d01-final-doc-fix-01`）。
- Accepted main：`547095f6705ce651272363676e2a2b51a66bb8b6`。
- 上一批 dev_log：`dev_log/2026-09-17-ui-v1-d01-final-doc-fix-01.md`。
- 本文件**不**写入自身 commit SHA —— Git ref 是该自引用事实的权威来源。
