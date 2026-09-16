# UI-V1-D01-FINAL-DOC-01｜MarketPulse UI V1 Formal Design — Repository Persistence

## Task

- Task ID：`UI-V1-D01-FINAL-DOC-01`。
- Task Name：MarketPulse UI V1 Formal Design — Repository Persistence。
- Type：**DOCS / STATE ONLY**。`NO PRODUCTION IMPLEMENTATION`。
- Goal：把已被 Human 明确接受并冻结的 `UI-V1-D01｜MarketPulse UI V1 Formal Design`
  （含 `UI-V1-D01-FIX-01｜Formal Contract Closure`）持久化进 Repository Truth：
  新增正式设计 artifact、新增本 dev_log、并对 `PROJECT_STATE.md` / `DECISIONS.md` /
  `AI_CONTEXT.md` 做**最小必要同步**。
- 本任务**不**重新设计 UI、**不**新增产品需求、**不**改变业务语义、**不**实现任何
  前端 / 后端代码、**不**安装包、**不**改 schema / migration / config / runtime、
  **不**激活 PRE-01B-I2、**不**激活 Real AI、**不**接通 live `G2→G3`、
  **不**接通 Forward Outcome 运行时调度、**不**改测试、**不** merge `main`。

## Scope

执行角色为 **EXECUTOR**（不是 product designer）：只把已冻结设计写入仓库真值。

允许改动路径恰为 5 个（见「Changed Paths」）：

1. `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（新建）
2. `dev_log/2026-09-17-ui-v1-d01-formal-design-freeze.md`（本文件，新建）
3. `PROJECT_STATE.md`（最小同步）
4. `DECISIONS.md`（最小同步）
5. `AI_CONTEXT.md`（最小同步）

## Out of Scope

明确**未**触碰：

- `PRODUCT_REQUIREMENTS.md`（**逐字未改**）
- `backend/**`、`frontend/**`、`scripts/**`、`tests/**`、`alembic/**`
- schema / migration / 配置 / dependency manifest
- runtime 代码与运行状态
- 任何往期 `dev_log`、任何其它 design artifact、任何状态文档的无关历史段落

并明确**未**：merge `main`、rebase、amend 他人 commit、force push、改动远端任何
其它 ref。

## Protocol Truth（Rule Baseline）

- Repository：`zwmhua2-lab2/ai-dev-protocol`。
- 实时实测 `git ls-remote https://github.com/zwmhua2-lab2/ai-dev-protocol.git
  refs/heads/main` = `a80c55b7451f77883d8b0713a228f0d9bebf7d22`。
- 实读 `AI_BOOTSTRAP.md`：`Protocol Version: 1.1.0` / `Protocol Status: ACCEPTED`。
- 实读 `AI_DEVELOPMENT_PROTOCOL.md`：`Protocol Version: 1.1.0` / `Status: ACCEPTED`
  / `Last Updated: 2026-09-15` / `Authority: User Confirmed Rules Only`。
- 结论：**`Protocol Version = 1.1.0`、`Protocol Status = ACCEPTED` 已确认**；
  Rule baseline = **VERIFIED**（非 `RULE BASELINE NOT VERIFIED`）。

## Actual Task Base SHA

- dispatch 期望 Task Base SHA = `547095f6705ce651272363676e2a2b51a66bb8b6`。
- 实时实测（`git ls-remote origin refs/heads/main`）= `547095f6705ce651272363676e2a2b51a66bb8b6`。
- 本地 `git rev-parse main` = `547095f6705ce651272363676e2a2b51a66bb8b6`；
  本地 `git rev-parse origin/main` = 同值。
- ⇒ **实际 origin/main == Task Base SHA**，**无 baseline drift**；
  无需 SHA delta 分类，未做任何 reset / rebase / overwrite。

## Branch

- Task branch：`design/ui-v1-d01-formal-freeze`。
- Exact base = 上节 Task Base SHA；单 parent、线性，无 merge commit。
- **不在 `main` 上工作**；本任务**不**推进、**不** merge `main`。

## Human Acceptance Fact

- `UI-V1-D01｜MarketPulse UI V1 Formal Design` = **HUMAN-ACCEPTED / FROZEN**
  （Human Acceptance = `CONFIRMED — 2026-09-17`）。
- `UI-V1-D01-FIX-01｜Formal Contract Closure` = **INCLUDED / CLOSED**
  （其语义已并入正式设计 artifact；FIX-01 不产生独立 artifact）。
- Independent Final Review = **`PASS — READY FOR FORMAL FREEZE`**。
- Review Findings：P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NONE`。
- **本 Acceptance 是 DESIGN ACCEPTANCE ONLY；它不授权实现。**

## Preflight：不存在既有 UI-V1-D01 artifact

执行前实测：

- `git ls-tree -r --name-only HEAD -- docs` 仅含
  `docs/design/PRE-01A/PRE-01A-D1-…md`、`docs/design/PRE-01B/PRE-01B-D1-…md`、
  `docs/design/PRE-01B/PRE-01B-D2-…md`、`docs/design/SE-02D/SE-02D-CLOSE-D01-…md`、
  `docs/design/SE-02D/SE-02D-D01-…md` ⇒ **不存在 `docs/design/UI-V1/`**。
- 全仓库 Markdown 检索 `UI-V1` / `MarketScannerRead` / `OpportunityTraceRead` /
  `EdgeAggregateRead` / `TradingAuditRead` / `SystemIncidentRead` = **零命中**。
- ⇒ 确认执行前**没有**已被接受的 UI-V1-D01 正式设计 artifact；本次为首次持久化。

## Design Artifact

`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
（Artifact status = `ACCEPTED / FROZEN`）。

artifact 内冻结内容清单（章节对应）：

```text
§0  本文件定位与阅读顺序 / 文档权威边界 / Human Acceptance 记录 / 与既有 Repository Truth 一致性
§1  Scope
§2  Out of Scope
§3  产品定位（Read-Only Paper Trading Operations & Evidence Terminal）
§4  Authority Boundaries（presentation vs business derivation）
§5  顶层信息架构（恰好五页；AI 无独立顶层页）
§6  页面职责（总览 / 市场与机会 / 策略研究 / 交易与仓位 / 系统）
§7  全局状态模型（S0–S4 / U0–U1 + 最小权威严重度映射）
§8  数据展示状态（LOADING / EMPTY / FRESH / STALE / UNAVAILABLE / CAPABILITY_NOT_INTEGRATED）
§9  双轴数据能力模型（Axis A 读面 / Axis B 运行可用性 + 当前最小矩阵）
§10 当前运行局限（live G2 → Evidence → Forward Outcome → Advisory/G3 未接通）
§11 机会双分支因果链（Forward Outcome != AI/Decision/Trading 前置）
§12 五个「无 / 未」概念（未激活 / 未发生 / 未到达 / 暂无可证明记录 / 暂不可用）
§13 Opportunity 时间契约（范围选项、默认 1 小时、[start,end)、horizon）
§14 运行态 vs 历史态来源（FORWARD_PAPER 语义；不得静默替换 HISTORICAL_REPLAY）
§15 Edge Lab Population Contract（Exact Population Key + Horizon；不得池化人口）
§16 Edge Lab Metrics Contract（headline = 平均成本调整后后续收益；禁用指标清单）
§17 Edge Sufficiency Contract（前端不重算；无 Edge Score / 无 A-B-C 评级）
§18 Edge Aggregation Execution Safety（CPU 工作离主 event loop；禁止 Celery/Redis/Kafka/worker/scheduler）
§19 Account Contract（cash_balance / reserved_cash / available_cash / realized_pnl）
§20 Economic Collection Model（非单例；positions[] / active_plans[] / open_orders[] / pending_intents[]）
§21 Execution Semantics（Risk Accepted != Intent != Order != Fill != Position）
§22 Position Protection Authority（durable snapshot 原子权威组；四态）
§23 Trade Economic Result Boundary（V1 不要求整笔 Trade 总盈亏）
§24 Product Boundary vs Runtime Mode（LIVE_PAPER 实时纸面 / REPLAY 回放 / TEST 测试）
§25 Auth Contract（Auth Shell 非第六页；密码不持久化）
§26 Read API Authorization Boundary（public / authenticated 清单）
§27 API Transport / OpenAPI（相对 /api + Vite proxy + typed DTO）
§28 /ready Contract（200 / 503 均为权威状态；UI 标签「运行就绪」）
§29 Recovery Contract（不得仅由时间戳推断 Recovery Complete）
§30 System Page Contract（Live/Ready/Health 等严格分离；无 mutation 控制）
§31 AI Current State（Design Accepted / Runtime Not Activated；U0）
§32 Needs Attention Contract（约 3 条；优先级顺序）
§33 Presentation vs Business Derivation（= §4 具体化）
§34 Timezone Contract（本地时区 + 指示；trace 用 UTC ISO 8601）
§35 Desktop / Accessibility（1440×900 主验收 / 1280×720 最低）
§36 Visual Governance（深色量化终端；禁止 3D / GPU 重负载）
§37 Product Read Projections（五个逻辑读模型）
§38 Partial Availability（跨域部分可用；不得整页置空）
§39 Domain Provenance Isolation（Trading 按 run_mode；Edge 按 source/population）
§40 Query / Performance Boundary（cursor/keyset；不因范围授权 index）
§41 Frontend Foundation Decisions Deferred（冻结需求、不选库）
§42 Implementation Order（UI-F01 → UI-RD01 → UI-I01..I06；仅排序）
§43 Acceptance Boundary（客观未来验收边界清单）
§44 Implementation Authorization（明确不授权实现）
§45 Non-Claims / Remaining Open
```

## Changed Paths

相对 Task Base SHA `547095f6…`，本任务分支**恰好**改动 5 个路径：

1. `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（**新增**）
2. `dev_log/2026-09-17-ui-v1-d01-formal-design-freeze.md`（**新增**，本文件）
3. `PROJECT_STATE.md`（最小同步：`Current Group` 增加 UI-V1-D01 行 + 文末新增
   `## UI-V1-D01 Result`）
4. `DECISIONS.md`（最小同步：文末新增 `UI-V1-D01 V1` 条目）
5. `AI_CONTEXT.md`（最小同步：§6 新增 UI-V1-D01 指针条目）

除上述 5 个允许路径外，**无任何其它路径变更**。

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
PRODUCT_REQUIREMENTS.md = ZERO CHANGE
```

本任务为 docs/state-only ⇒ **无 runtime verification 需求**：未运行 Runtime Host、
未调用 provider、未跑 PostgreSQL validation / Docker / soak / Real AI；
`ruff` / `pytest` = `NOT REQUIRED / NOT RUN`。

## Verification

| # | 检查 | 结果 |
|---|---|---|
| 1 | `git diff --check` | `PASS`（无 whitespace error、无 conflict marker） |
| 2 | Changed paths 仅限 5 个允许 docs/state 路径 | `PASS`（见「Changed Paths」） |
| 3 | `backend/` / `frontend/` / `scripts/` / `tests/` / `alembic/` / dependency / config **零改动** | `PASS` |
| 4 | 正式 artifact 无禁用虚假声明扫描（见下） | `PASS` |
| 5 | 正式 artifact 含必需章节（Scope / Out of Scope / Authority boundaries / Data capability model / 五页 IA / Acceptance Boundary / 实施顺序 / 未授权实现） | `PASS` |
| 6 | 自审：与 `PRODUCT_REQUIREMENTS.md` / `DECISIONS.md` / 已接受 source-runtime truth 无矛盾 | `PASS` |

### 检查 4 明细：禁止性声明扫描

正式 artifact 内**不包含**以下任何虚假声明（逐项实测）：

```text
"Real AI active" / "Real AI activated"      → 仅以 NOT ACTIVATED 形式出现
"G2→G3 active" / "activated"                → 仅以 Not Active / NOT ACTIVE 形式出现
"Gate C passed"                             → 仅以 NOT PASSED 形式出现
"Live authorized"                           → 仅以 NOT AUTHORIZED / DISABLED 形式出现
"UI implemented"                            → 仅以 NOT STARTED 形式出现
"Forward Outcome runtime wired"             → 仅以 NOT INTEGRATED 形式出现
"PRE-01B-I2 complete"                       → 仅以 NOT STARTED / NOT ACTIVATED 形式出现
"Trading Edge proven"                       → 仅以 未证明 形式出现
```

### 检查 6 明细：自审（Reality Check）

- **未忽略的事实**：`frontend/` 目前只是 Group 1 占位脚手架
  （`index.html` / `src/main.tsx` / `src/styles.css` / `src/api/generated.ts` /
  `package.json` 的 `generate:api`），`vite.config.ts` **尚未配置** `/api` proxy。
  ⇒ artifact §27 明确把 relative-path + Vite proxy + typed DTO + OpenAPI regeneration
  标记为**本设计冻结的契约**，并显式声明其落地属 UI-F01 / UI-RD01 / UI-I01，
  **不是当前已实现事实**；未把设计意图写成已有能力。
- **最坏情况**：本文件若被下游误读为「UI 已实现 / 已授权」，会诱发越权实现。
  ⇒ artifact §0.2、§44、§45 三处重复声明「Design Acceptance only / 不授权实现」，
  并在状态文档中同样标注 `Implementation = NOT STARTED`。
- **更简单的方案**：是否可以不新增 artifact、只改状态文档？不行 —— 任务要求持久化
  **正式设计本体**，且仓库此前**零** UI-V1 真值，仅改状态文档会留下悬空指针。
- **口径一致性核对**：artifact §16 的 Edge headline（Family-level Forward Outcome
  Expectancy）与 `PRODUCT_REQUIREMENTS.md` §10 已接受能力调和一致；
  §22 的保护权威与 `DECISIONS.md`「G4 / N01-7-F01 V1」一致；
  §31 的 AI 状态与 `DECISIONS.md`「PRE-01B-D2 V1」一致；
  §24 的产品边界与 `PRODUCT_REQUIREMENTS.md` §7 一致。

### 未验证项（如实标记）

- 无真实 UI 运行时 / 浏览器 / 截图验证 —— **本任务无实现面**，故**不适用**，
  但**不得**据此声称任何 UI 行为已被验证。
- 未执行 lint / 测试 —— docs-only，**`NOT REQUIRED / NOT RUN`**。

## Self Review

- 本任务严格遵守 EXECUTOR 角色：未重新设计、未新增产品需求、未改业务语义、
  未选择前端库、未扩大 Scope。
- 对 `PROJECT_STATE.md` / `DECISIONS.md` / `AI_CONTEXT.md` 只做因本任务确实发生
  变化的**最小**更新；**未**重写任何无关历史段落，**未**为了「看起来完整」
  重构文档。
- ⚠️ 按 `SE-02D-CLOSE-D01` 时点遗留的**已知 stale index** 惯例（`PROJECT_STATE.md`
  内 `Integrated Runtime Host — NOT STARTED` 一类历史索引行）：本任务
  **未**顺势改写它们（不在允许改动面内）；权威当前态以 per-batch 条目为准。
- 未修改任何往期 `dev_log`；本文件为新建。

## Remaining / Open Capabilities

- `PRE-01B-I2`（AdvisoryIngress Core 实现）= `NOT STARTED / NOT ACTIVATED`。
- Real AI = `NOT ACTIVATED`；live `G2→G3` Advisory = `NOT ACTIVE`。
- Forward Outcome 运行时自动生产集成 = `NOT INTEGRATED`（无 Product consumer）。
- `SE-02D` Aggregate = accepted callable core，**无 Product consumer**。
- **UI 实现 = `NOT STARTED`**（前端仅 Group 1 占位脚手架）。
- Product Read API 实现 = `NOT STARTED`。
- 前端基础库选型 = `DEFERRED` 至 `UI-F01`。
- Gate A / Gate B = `NOT ACTIVATED`；Gate C = `NOT PASSED`；
  Live Trading = `NOT AUTHORIZED / DISABLED`。
- Trading Edge = **未证明**；`Deterministic Replay != Trading Edge Proof` 仍成立。
- historical arbitrary revision-as-of = `OPEN`；experiment / pair / arm identity =
  `OPEN GATE C PREREQUISITE`；durable regime identity = `OPEN GATE C PREREQUISITE`；
  Gate C immutable evidence retention = `FUTURE GATE C EVIDENCE TASK`。
- Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS / NON-BLOCKING`。
- 下一计划设计任务 = `UI-F01` / `UI-RD01` 序列，但**本 docs 任务不授权它**；
  任何后续实现 / 设计都需另开独立获批窗口。

## Git / Delivery

- 提交到 task branch `design/ui-v1-d01-formal-freeze`。
- Commit message：`docs(ui-v1): freeze accepted formal UI design`。
- 推送 task branch。
- **不** merge `main`；推送后停止。

## Evidence Pointers

- Design artifact：`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
  （`ACCEPTED / FROZEN`，Human Acceptance = `CONFIRMED — 2026-09-17`）。
- Task branch：`design/ui-v1-d01-formal-freeze`（base = `547095f6…`）。
- 状态指针：`PROJECT_STATE.md`「Current Group」/「UI-V1-D01 Result」；
  `DECISIONS.md`「UI-V1-D01 V1」；`AI_CONTEXT.md` §6。
- Protocol truth：`zwmhua2-lab2/ai-dev-protocol` remote `main` =
  `a80c55b7451f77883d8b0713a228f0d9bebf7d22`（`1.1.0 / ACCEPTED`）。
- 本文件**不**写入自身 commit SHA —— Git ref 是该自引用事实的权威来源。
