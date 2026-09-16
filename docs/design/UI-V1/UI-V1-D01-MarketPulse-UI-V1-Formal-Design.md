# UI-V1-D01｜MarketPulse UI V1 Formal Design

## Artifact Status

```text
Artifact: UI-V1-D01 MarketPulse UI V1 Formal Design
Status: ACCEPTED / FROZEN
Human Acceptance: CONFIRMED — 2026-09-17
Included closure: UI-V1-D01-FIX-01 = INCLUDED / CLOSED
Independent Final Review: PASS — READY FOR FORMAL FREEZE
Review severity: P0 = NONE / P1 = NONE / P2 = NONE / P3 = NONE
Task type: FORMAL DESIGN / DOCS ONLY

Implementation authorized by this artifact: NO
Frontend implementation authorized by this artifact: NO
Backend / Product Read API implementation authorized by this artifact: NO
Runtime or provider activation authorized by this artifact: NO

Task branch: design/ui-v1-d01-formal-freeze
Task Base SHA: 547095f6705ce651272363676e2a2b51a66bb8b6
Accepted Main at freeze: 547095f6705ce651272363676e2a2b51a66bb8b6
```

---

## 0. 本文件定位与阅读顺序

### 0.1 文档权威边界

本文件是 **MarketPulse UI V1 的正式设计基线（Formal Design Baseline）**，不是 PRD，不是实现
Spec，也不是验收证据。它只负责：

- 冻结 UI V1 的**产品定位、信息架构、页面职责、语义契约与边界**；
- 冻结 UI 与既有已接受权威（Runtime / G4 durable state / SE-02D / PRE-01A-D1 /
  PRE-01B-D1 / PRE-01B-D2）之间的**只读关系**；
- 冻结**未来的客观验收边界**与**设计层实施顺序**。

本文件**不**：新增产品需求、改变业务语义、改变任何已接受的架构 / 风险 / 数据语义、
选择前端库、授权任何实现。

文档权威优先级以 `AI_CONTEXT.md` §2 Source of Truth 为准；本文件不得静默覆盖
`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md` 或已接受实现。若本文件与上述任一处冲突，
以更高优先级事实源为准并报告差异。

### 0.2 Human Acceptance 记录

- `UI-V1-D01｜MarketPulse UI V1 Formal Design` = **HUMAN-ACCEPTED / FROZEN**（2026-09-17）。
- `UI-V1-D01-FIX-01｜Formal Contract Closure` = **INCLUDED / CLOSED**（其全部语义已并入本
  文件；FIX-01 不产生独立 artifact）。
- Independent Final Review = `PASS — READY FOR FORMAL FREEZE`；
  P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NONE`。
- **本 Acceptance 是 Design Acceptance only**：它接受的是设计本身，
  **不授权实现**（详见 §44）。

### 0.3 与既有 Repository Truth 的一致性

本设计不改变任何已接受语义，只在其上定义只读呈现契约。明确对应关系：

| 本设计引用 | 已接受权威 |
|---|---|
| Family 级 Forward Outcome Expectancy 作为 Edge Lab headline | `SE-02D`（D01 设计 + I01/I02/I03 实现 + Overall Closeout）；`PRODUCT_REQUIREMENTS.md` §10 已接受能力调和 |
| Position Protection 寿命权威 = OPEN Position 上的 durable snapshot | `DECISIONS.md`「G4 / N01-7-F01 V1」条目 |
| `TradePlan.invalidation` = advisory text；`stop_loss` = 唯一 hard invalidation | `DECISIONS.md`「G4 V1」条目；`PRODUCT_REQUIREMENTS.md` §7 |
| Operator Intent 与 System Derived State 分离；Reconciliation = detector | `DECISIONS.md`「G4」条目；`PRODUCT_REQUIREMENTS.md` §7 |
| AI = Advisory / Deterministic System = Authority | `PRE-01A-D1 V1`；`AI_CONTEXT.md` §3 |
| AI activation / G2→G3 现状 | `PRE-01B-D2 V1`（Design `ACCEPTED`；`PRE-01B-I2 = NOT STARTED`） |
| Scanner 不写死 BUY/SELL | `PRODUCT_REQUIREMENTS.md` §3 / §6 |

---

## 1. Scope

UI V1 设计范围（本文件冻结的对象）：

1. 产品定位与产品边界（只读运维 / 证据终端）。
2. 顶层信息架构（恰好五个产品页）。
3. 每一页回答的问题、职责、必须区分的经济 / 运行时对象。
4. 全局状态模型（正常 / 提示 / 注意 / 警告 / 严重 / 未激活 / 不可用）。
5. 数据展示状态模型（Loading / Empty / Fresh / Stale / Unavailable /
   Capability Not Integrated）。
6. 双轴数据能力模型（读面存在性 × 运行可用性）。
7. 机会证据的双分支因果链模型。
8. Opportunity 时间契约与 Forward Outcome horizon 契约。
9. Edge Lab 的人口身份、指标、充分性与聚合执行安全契约。
10. 账户 / 经济集合 / 执行语义 / 保护权威 / Trade 经济结果边界的**只读呈现契约**。
11. Auth Shell 与读接口授权边界。
12. Transport / OpenAPI / 部分可用性 / 域来源隔离 / 查询边界。
13. 桌面与可访问性边界、视觉治理原则。
14. 五个 Product Read Projection（逻辑读模型）的冻结清单。
15. 未来客观验收边界（Acceptance Boundary）与设计层实施顺序。
16. 前端基础决策**需求清单**（不选库）。

---

## 2. Out of Scope

本文件**不**包含、**不**授权、**不**隐含以下内容（完整非目标清单见 §43）：

- 任何前端 / 后端代码实现、任何 UI 页面落地；
- 任何库 / 框架选型（Router / Query / 状态 / 测试框架等，见 §42）；
- 任何新 Product Read API 的实现、路由或 DTO 代码；
- 任何 schema / migration / index 变更；
- 任何 config / runtime / dependency manifest 变更；
- PRE-01B-I2 实现或激活；
- Real AI 激活、provider 配置、真实 provider 调用；
- live `G2→G3` 接通、Forward Outcome 运行时调度接通；
- Gate A / Gate B / Gate C 任何运行时激活或判定；
- Live Trading 授权；
- 任何交易控制 / 变更动作（下单、平仓、撤单、SL/TP 修改、计划修改、暂停 / 恢复 /
  急停 / 封禁 / 解除 / 事件处置 / 对账修复）；
- 策略配置、策略排名、参数优化、KEEP / DOWNWEIGHT / KILL；
- 任何未获接受的收益 / 风险指标（Win Rate、Sharpe、Sortino、Profit Factor、MFE/MAE、
  Drawdown、Equity Curve、R-Multiple、Account Equity、Unrealized PnL、
  per-Trade lifetime total PnL、Positive Rate 主 UI 展示、Edge Score / A-B-C 评级）；
- 历史任意 as-of Edge 浏览、Replay Dashboard、raw DB browser、桌面壳架构、
  3D / GPU 重负载可视化。

---

## 3. Product Positioning（产品定位，冻结）

> **MarketPulse UI V1 是 Read-Only Paper Trading Operations & Evidence Terminal**
> **（只读纸面交易运维与证据终端）。**

它不是：

- 手工交易终端（manual trading terminal）；
- 运行时控制面板（runtime control panel）；
- Live Trading UI；
- AI 自主控制界面（AI autonomous control interface）。

| 维度 | 冻结值 |
|---|---|
| 主语言 | 简体中文 |
| 目标形态 | Desktop-first（桌面优先） |
| 视觉方向 | 深色、专业量化终端风格；高信息密度但不杂乱；正常状态低噪声；风险 / 陈旧 / 故障状态醒目 |
| 参考图用途 | 视觉参考图仅为**方向性参考**，不是 pixel-perfect Product Truth |
| 冲突裁决 | **Repository Truth 始终优先于 mock 视觉** |

---

## 4. Authority Boundaries（权威边界，冻结）

UI V1 的核心设计约束：**前端是呈现层，不是业务权威。**

### 4.1 前端允许做的事（presentation only）

- 数字格式化；
- 时间戳格式化；
- 百分比格式化；
- 枚举翻译（en / zh 展示映射）；
- 简单 display-only spread（例如价格差额的展示计算）；
- 依据**权威观测时间戳**渲染数据年龄（age）；
- 依据后端返回的显式状态字段选择展示样式。

### 4.2 前端禁止做的事（business derivation）

- 判定 Risk Admission；
- 判定 Position 生命周期；
- 选择 Canonical Evidence；
- 通过猜测选择 Aggregate Population；
- 计算 Edge Verdict；
- 用不相关表重建 Causal Trace；
- 选择 Protection Authority；
- 发明 account / economic 指标；
- 推断 Real AI 激活状态；
- 依据时间戳单独推断「Recovery Complete」。

### 4.3 权威归属（冻结）

| 语义 | 唯一权威 |
|---|---|
| Canonical Evidence | Backend（durable evidence） |
| Edge Population 身份 | Backend（Population Key + Horizon） |
| Edge 充分性 | Backend（`evidence_sufficient` / `sufficiency_reasons`） |
| Risk Admission | Backend Risk Authority（`SystemRiskGate`） |
| Position Protection | OPEN Position 上的 durable protection snapshot（见 §23） |
| 经济事实（Fill / Ledger / Trade） | PostgreSQL durable facts |
| Operator Intent / System Derived State | Backend（二者分离持久化） |
| Real AI 激活状态 | Backend activation state |
| 数据质量（Fresh / Stale / Unavailable） | Backend 显式状态 + 权威观测时间戳 |

---

## 5. Information Architecture（冻结的顶层信息架构）

顶层产品页**恰好五个**：

| # | 页面 | 回答的问题 |
|---|---|---|
| 1 | 总览 | 现在有没有事情需要我关注？ |
| 2 | 市场与机会 | 市场发生了什么，为什么形成 Opportunity？ |
| 3 | 策略研究 | 同类 Opportunity 聚合后的研究证据怎样？ |
| 4 | 交易与仓位 | 系统如何处理经济动作，现在资金 / 仓位怎样？ |
| 5 | 系统 | Runtime、安全、恢复和基础设施是否可信？ |

**AI 不获得独立的顶层页面。** AI 上下文性地出现在：

- Opportunity / Trading Trace；
- Trading decision lineage（决策谱系）；
- System activation / runtime status（激活与运行时状态）。

---

## 6. Page Responsibilities（页面职责）

### 6.1 总览

**回答的问题**：「现在有没有事情需要我关注？」

**职责**：

- 全局状态（Global status）；
- **Needs Attention 优先**（详见 §33）；
- BTC / ETH 市场概要；
- 开放仓位概要；
- 活动计划 / 待执行概要；
- 近期正式 Opportunity 概要（**仅当能力存在时**）；
- 薄层运行时概要（thin runtime summary）。

**明确不做**：

- 巨幅 KPI 墙；
- 大 K 线图；
- 经济动作；
- 控制动作。

### 6.2 市场与机会

**回答的问题**：「市场发生了什么，为什么形成 Opportunity？」

**桌面三列工作区**：

| 列 | 内容 |
|---|---|
| 左 | Market / Scanner |
| 中 | Opportunity List |
| 右 | Opportunity Detail |

**冻结语义**：

- **Scanner Event 不是 Trading Signal。**
- **绝不允许把 Scanner Event 标注为 BUY / SELL。**
- 当前已接受的正式 Strategy Family = **`BREAKOUT_RETEST`**；
  **不得发明额外 family。**

**Opportunity Detail 分区（顺序冻结）**：

1. 概况
2. Trigger / 形成原因
3. Evidence
4. Forward Outcome
5. Attribution / Downstream
6. Technical Trace

**Canonical Evidence 由 backend 拥有**，前端不得自行选择或重排。

### 6.3 策略研究 / Edge Lab

**回答的问题**：「同类 Opportunity 聚合后的研究证据怎样？」

它是 **family 级 Current Snapshot 研究视图**。

它**不是**：

- 盈利排名（profitability ranking）；
- 策略推荐（strategy recommendation）；
- Edge 判定（edge verdict）；
- 回测仪表盘（backtest dashboard）。

**Horizon 契约**：

- **`5m` = Primary Horizon**；
- Secondary Horizons = `30s` / `15m` / `1h`；
- **每个 horizon 分别报告**；
- **禁止跨 horizon 平均**；
- **禁止事后挑选「最佳 horizon」**。

### 6.4 交易与仓位

**回答的问题**：「系统如何处理经济动作，现在资金 / 仓位怎样？」

它是**只读经济动作 / 审计工作区**。

**必须严格区分以下对象**：

| # | 对象 | 说明 |
|---|---|---|
| 1 | Account | 账户 |
| 2 | Trade Plan | 交易计划 |
| 3 | Risk Admission | 风险准入 |
| 4 | Execution Intent | 执行意图 |
| 5 | Paper Order | 纸面订单 |
| 6 | Fill | 成交 |
| 7 | Position | 仓位 |
| 8 | Position Protection | 仓位保护 |
| 9 | Trade | 交易 |
| 10 | Economic Facts | 经济事实 |

**没有交易控制按钮。**

### 6.5 系统

**回答的问题**：「Runtime、安全、恢复和基础设施是否可信？」

它是**只读可观测性 / 安全 / 恢复控制台**。

**必须严格区分以下对象**：

- Live
- Ready
- Health
- Runtime telemetry
- Market data / provider
- Queues / lanes
- DB
- Singleton
- Recovery
- Reconciliation
- Runtime / Operator state
- Incidents
- AI activation status

---

## 7. Global Status Model（全局状态模型，冻结）

### 7.1 状态分级

```text
S0 = 正常
S1 = 提示
S2 = 注意
S3 = 警告
S4 = 严重

U0 = 未激活
U1 = 不可用 / 未知
```

### 7.2 最小权威严重度映射

| 事实 | 状态 |
|---|---|
| READY / normal | `S0` |
| informational recovered fact | `S1` |
| `HostReadinessStatus.DEGRADED` | `S2` |
| Scanner lane degradation | `S2` |
| Telemetry degradation | `S2` |
| Active non-blocking Incident | `S2` |
| Position / Protection truth `UNKNOWN` | `S3` |
| `FAIL_CLOSED` | `S4` |
| Active blocking Incident | `S4` |
| `POSITION_UNPROTECTED` | `S4` |
| Real AI intentionally disabled | `U0` |
| ordinary unavailable read source | `U1` |

**状态绝不可仅依赖颜色传达。**（见 §36）

---

## 8. Data Display States（数据展示状态，冻结）

必须区分以下六个互不相同的状态：

```text
LOADING
EMPTY
FRESH
STALE
UNAVAILABLE
CAPABILITY_NOT_INTEGRATED
```

**冻结规则**：

- **Unavailable ≠ zero。**
- Unavailable Position ≠ no Position。
- Unavailable Account ≠ zero balance。
- Unavailable Outcome ≠ 0%。
- **STALE 的 last-known 数据可以继续可见**，但必须显式标记为 stale，
  并在适用时显示数据年龄（data age）。
- **`CAPABILITY_NOT_INTEGRATED` ≠ `EMPTY`。**

**示例（正式机会实时生产链未接入时）**：

```text
正确：“正式机会实时生产链尚未接入。”
错误：“当前市场没有机会。”
```

---

## 9. Data Capability Model（双轴数据能力模型，冻结）

冻结**两条相互独立**的轴。

### 9.1 Axis A — Read Surface（读面）

```text
A = Current formal HTTP Read Contract exists.
B = Accepted backend truth exists but Product Read API is needed.
C = No current consumable formal Read Truth.
```

### 9.2 Axis B — Operational Availability（运行可用性）

```text
ACTIVE
ACCEPTED_NOT_INTEGRATED
NOT_ACTIVATED
```

### 9.3 当前最小矩阵（冻结）

| 能力 | Axis A | Axis B |
|---|---|---|
| Runtime Live / Ready / Health | `A` | `ACTIVE` |
| Runtime Telemetry | `A` | `ACTIVE` |
| Market freshness | `A` | `ACTIVE` |
| Scanner Event | `B` | `ACTIVE` |
| Strategy Candidate | `B` | `ACTIVE` |
| Formal live Opportunity Evidence | `B` | `ACCEPTED_NOT_INTEGRATED` |
| Forward Outcome automatic production | `B` | `ACCEPTED_NOT_INTEGRATED` |
| SE-02D Aggregate | `B` | `ACCEPTED_NOT_INTEGRATED` |
| Trading durable facts | `B` | `ACTIVE` |
| Incident durable facts | `B` | `ACTIVE` |
| Real AI | `C` | `NOT_ACTIVATED` |
| live `G2→G3` Advisory | `C` | `NOT_ACTIVATED` |
| Gate A / B / C runtime activation | `C` | `NOT_ACTIVATED` |
| Live Trading | `C` | `NOT_ACTIVATED` |

SE-02D aggregation core is Accepted / callable, but currently has no Product consumer;
therefore its Operational Availability classification is `ACCEPTED_NOT_INTEGRATED`.

> Axis A / Axis B 相互独立：`A + NOT_ACTIVATED` 与 `C + ACTIVE` 都是合法组合形态。
> UI 必须按后端返回的显式能力状态渲染，不得由任一轴推断另一轴。

---

## 10. Current Runtime Limitation（当前运行局限，冻结）

冻结的当前运行真值：

> 当前 `RuntimeHost` / Scanner runtime **尚未**提供完整接通的

```text
live G2
  → Formal Opportunity Evidence
  → Forward Outcome scheduling
  → live Advisory / G3 chain
```

`PRE-01B-D2` Formal Design 已 `ACCEPTED`，但 **`PRE-01B-I2` 未实现 / 未激活**。

**UI 实现绝不允许静默接通这些能力。** UI 必须暴露相应的 capability 状态
（见 §8 / §9）。

---

## 11. Opportunity Double-Branch Trace（机会双分支因果链，冻结）

冻结以下**概念性**因果链：

```text
Market Event
  ↓
Strategy Candidate
  ↓
Opportunity + Evidence
  ├─ Forward Outcome branch:
  │    30s / 5m / 15m / 1h
  │
  └─ Trading Decision branch:
       Advisory / AI
         ↓
       Decision
         ↓
       Trade Plan
         ↓
       Risk
         ↓
       Execution
         ↓
       Position
         ↓
       Economic Result
```

**冻结规则**：

- **Forward Outcome 绝不可被展示为 AI / Decision / Trading 的前置（predecessor）。**
- Forward Outcome 与 Trading Decision 是从 `Opportunity + Evidence` 出发的
  **两个并列分支**，不是串行关系。
- **Forward Outcome ≠ Economic Result**（见 §43）。

---

## 12. `NONE` Semantics（五个「无 / 未」概念，冻结）

必须冻结为**五个互不相同**的概念，**不得合并**：

| 概念 | 语义 | 判据 |
|---|---|---|
| 未激活 | capability not enabled | 能力未启用（后端显式能力状态） |
| 未发生 | backend proves step did not occur | 后端**证明**该步未发生 |
| 未到达 | upstream chain ended before this step | 上游链路在该步之前已结束 |
| 暂无可证明记录 | durable evidence cannot prove occurrence / non-occurrence | durable 证据既不能证明发生、也不能证明未发生 |
| 暂不可用 | read / API failure | 读取 / API 失败 |

---

## 13. Opportunity Time Contract（机会时间契约，冻结）

**Market & Opportunity 记录范围（record range）选项**：

```text
15分钟 / 30分钟 / 1小时 / 4小时 / 6小时 / 24小时 / 7天 / 30天 / 自定义
```

- **默认值：`1小时`**
- **Opportunity list range 语义**：`detected_at ∈ [start, end)`
  （左闭右开区间）
- **Scanner timeline**：使用 Scanner Event 的 `event_time`
- **Forward Outcome**：从 `evidence_at` 起算，**独立于 Opportunity
  record-range 过滤器**（即：Forward Outcome 的计算起点不受机会列表时间筛选范围影响）

**Forward Outcome horizons（冻结）**：

```text
30s
5m   ← Primary
15m
1h
```

---

## 14. Operational vs Historical Provenance（运行态与历史态来源，冻结）

- **Operational Market & Opportunity UI 必须使用 `FORWARD_PAPER` 语义。**
- 当前 `Forward Paper` 数据不可用时，**绝不静默替换为 `HISTORICAL_REPLAY`**。
- **Edge Lab**：`FORWARD_PAPER` 可以是默认研究来源，但**来源身份必须始终显式**
  （source identity must remain explicit）。
- **Historical Replay 绝不可作为当前 live operational truth 呈现。**

---

## 15. Edge Lab Population Contract（研究人口契约，冻结）

**Exact Population Key** 包含：

```text
family_id
family_version
instrument_id
market_type
source_type
source_identity
evidence_contract_version
```

**Aggregate identity** = `Population Key + Horizon`。

**冻结规则**：

- **前端不得合并 / 池化 populations（must not pool populations）。**
- Backend 必须暴露：

```text
available_populations[]
selected_population_key
```

- **恰好一个 exact population 匹配**时：允许自动选择。
- **多个 exact population 匹配**时：必须显示「研究人口」选择器。

---

## 16. Edge Lab Metrics Contract（研究指标契约，冻结）

**主标题（Primary headline）**：

> **“平均成本调整后后续收益”**

技术含义 = **Family-level Forward Outcome Expectancy**。

**绝不可称为**：

- strategy return；
- PnL；
- trading profit。

**Headline 组必须在同一视觉层级同时展示**：

```text
Expectancy
95% uncertainty interval
Evidence Sufficiency
Coverage
```

- **Coverage 分母 = mature population。**
- **`NOT_YET_DUE` 不算 missing。**

**Positive Rate：V1 主 UI 不展示。**

**明确不展示**：

```text
Win Rate
Sharpe
Sortino
Profit Factor
MFE
MAE
Drawdown
Equity Curve
R-Multiple
```

---

## 17. Edge Sufficiency Contract（充分性契约，冻结）

- 前端读取 backend 返回的：

```text
evidence_sufficient
sufficiency_reasons
```

- **前端不重新计算、不自行评分（frontend does NOT recompute or score
  sufficiency）。**
- **不引入**：

```text
Edge Score
0–100 score
A/B/C grade
```

- **Tail evidence（V1）**：

```text
Worst Observation
Worst Decile Mean
```

- **不设 tail-risk Pass/Fail 阈值。**
- **仅 Current Snapshot。**
- **不提供任意历史 as-of UI。**

---

## 18. Edge Aggregation Execution Safety（Edge 聚合执行安全，冻结）

`SE-02D` aggregate 使用 **CPU 重负载的确定性 bootstrap 计算**。

**Product API 实现必须**：

1. 先执行 async snapshot / database 工作；
2. 再通过 **bounded execution** 在主 async event loop **之外**执行 CPU 重负载的
   **纯** aggregation。

**bounded thread offload 是可接受的方案。**

**不得**仅为满足本 UI 需求而增加：

```text
Celery
Redis
Kafka
worker service
scheduler
```

**Edge Lab 刷新策略**：低频 / 手动 / 变更通知（change-notice）。
**禁止高频轮询。**

---

## 19. Account Contract（账户契约，冻结）

冻结精确语义：

| 字段 | 中文标签 |
|---|---|
| `cash_balance` | **现金余额** |
| `reserved_cash` | **预留资金** |
| `available_cash` | = `cash_balance - reserved_cash`（**优先由 backend Read Projection 显式返回**） |
| `realized_pnl` | **账户累计已实现盈亏** |

**冻结规则**：

- **绝不可把 `cash_balance` 标注为「可用资金」。**
- **不得**在未来出现已接受契约之前引入 **Account Equity** 或 **Unrealized PnL**。

---

## 20. Economic Collection Model（经济集合模型，冻结）

**绝不可假设存在全局单例经济对象。**

**Current Economic State 必须建模为**：

```text
positions[]
active_plans[]
open_orders[]
pending_intents[]
```

**BTC 与 ETH 可以同时持有经济状态。**

因此 **Overview 使用计数 / 摘要**：

```text
开放仓位 N
活动计划 N
未完成订单 N
```

**Position Protection 始终是 per Position 的**（见 §23）。

---

## 21. Execution Semantics（执行语义，冻结）

必须严格区分：

```text
Risk Accepted
  ≠ Execution Intent
  ≠ Order Open
  ≠ Fill
  ≠ Position
```

**冻结规则**：

- **只有实际 Fill 才能证明 Paper 经济动作已发生。**
- **Risk rejection 与 execution rejection 保持分离。**
- **Risk rejection 必须保留**：authority + 精确 reason。
- **Order Open 的含义 = 「等待成交」。**
- **绝不可**在无 durable Position 事实证明时显示「已建仓」。

---

## 22. Position Protection Authority（仓位保护权威，冻结）

**OPEN Position 上的 durable protection snapshot 是唯一的
protection-lifetime authority。**

其**原子权威组**为：

```text
protection_plan_id
protection_plan_version
protection_stop_loss
protection_take_profit
protection_updated_at
```

**规则**：要么**全部为 null**，要么**全部完整**。

**冻结规则**：

- **Current Protection 绝不可从最新的 Active Plan 推断。**
- **`Plan Expired` 不蕴含 `Position Protection Expired`。**
- **Active Plan B 可以与源自 Plan A snapshot 的当前 Position Protection 并存。**
- **UI 必须展示真实权威（the true authority）。**

**Protection 展示状态（冻结四态）**：

```text
NOT_REQUIRED
PROTECTED
UNPROTECTED
UNKNOWN
```

**`UNPROTECTED ≠ UNKNOWN`。**

---

## 23. Trade Economic Result Boundary（交易经济结果边界，冻结）

**V1 不得要求展示「整笔 Trade 总盈亏」**，因为当前不存在覆盖部分减仓的、
已接受的 per-trade lifetime PnL 契约。

**Trade Audit 可以展示**：

```text
Trade lifecycle
Open / Close timestamps
Exit Reason
Orders
Fills
Fees
Ledger cash facts
individual settlement economic facts
```

未来的 per-trade 总 PnL 需要**另行接受**的
**`TradeEconomicSummary`** 契约。

**前端不得自行发明它。**

---

## 24. Product Boundary vs Runtime Mode（产品边界与运行模式，冻结）

必须始终区分两个不同维度：

| 维度 | 取值 |
|---|---|
| **Product boundary（产品边界）** | 纸面交易 / 现货 / 仅做多 |
| **Runtime mode（运行模式）** | `LIVE_PAPER` / `REPLAY` / `TEST` |

**中文 UI 映射（冻结）**：

```text
LIVE_PAPER → 实时纸面
REPLAY     → 回放
TEST       → 测试
```

**`TEST` 绝不可在视觉上伪装成 `LIVE_PAPER`。**

---

## 25. Auth Contract（认证契约，冻结）

**Auth Shell 属于 UI V1，但**不是第六个顶层产品页。

**流程**：

```text
Unauthenticated
  → Login
  → Authenticated 5-page App Shell
```

**401 处理**：

```text
401 → 清除 session → Login → 在可行时保留原定目标路由（retain intended route where practical）
```

**冻结规则**：

- **密码不得持久化（must not be persisted）。**
- **Read-only 的含义是 Read-Only Business UI。**
- **通过 Login POST 建立认证会话是允许的**（Authentication Session
  Establishment via Login POST is allowed）。

---

## 26. Read API Authorization Boundary（读接口授权边界，冻结）

**Public（公开）**：

```text
POST /api/v1/auth/login
GET  /api/v1/live
GET  /api/v1/ready
GET  /api/v1/health
```

**Authenticated（需认证）**：

```text
/api/v1/runtime
existing instruments / universe
all future Product Read APIs:
  MarketScannerRead
  OpportunityTraceRead
  EdgeAggregateRead
  TradingAuditRead
  SystemIncidentRead
```

**冻结规则**：**任何 secret 不得在前端或 API 响应中暴露。**

> 现状核对（冻结时点）：`/api/v1/live` / `/ready` / `/health` 为公开；
> `/api/v1/runtime` 与 `/api/v1/protected/ping` 经 `verify_session`；`login` 为
> `POST`；`instruments` / `universe` 存在。本设计**不**改变该边界，只将其冻结为
> UI V1 的读接口前提。

---

## 27. API Transport / OpenAPI（传输与类型边界，冻结）

- **前端应用代码使用相对路径**：

```text
/api/...
```

- **开发环境使用 Vite `/api` proxy 指向**：

```text
127.0.0.1:8000
```

- **不得仅为本地 V1 引入宽泛 CORS。**
- **每个新的 Product Read endpoint 必须使用显式 typed Pydantic Response DTO。**
- **随后重新生成前端 OpenAPI types。**

**不得**将以下方式作为 Product API 的常规边界：

```text
any
unknown-as-business-model
handwritten duplicate authority DTOs
```

> 现状核对（冻结时点）：`frontend/` 目前只有 Group 1 占位脚手架
> （`index.html` / `src/main.tsx` / `src/styles.css` / `src/api/generated.ts` /
> `package.json` 内 `generate:api` 脚本 / `vite.config.ts` 尚未配置 `/api` proxy）。
> 因此本节的 relative-path + Vite proxy + typed DTO + OpenAPI regeneration 是
> **本设计冻结的契约**，其落地属 UI-F01 / UI-RD01 / UI-I01 范围，
> **不是当前已实现事实**。

---

## 28. `/ready` Contract（就绪契约，冻结）

```text
GET /api/v1/ready

200 = ready payload
503 = authoritative NOT READY payload
```

**冻结规则**：

- **`/ready` 返回 503 不是通用 transport / network failure。**
- **UI 必须解析并展示 readiness body。**
- **UI 标签**：`运行就绪`
- **Readiness 不等于 Risk Admission。**
- **前端不得从 ready 推断 `risk_admission_open`。**
- 若要展示 Risk Admission，**backend Product Read Projection 必须显式暴露它。**

---

## 29. Recovery Contract（恢复契约，冻结）

**前端不得仅从时间戳推断「Recovery Complete」。**

若 System UI 展示恢复状态，System Product Read Projection 应当显式暴露：

```text
recovery.status
recovery.ready_at
recovery.reason
```

---

## 30. System Page Contract（系统页契约，冻结）

必须严格分离：

```text
Live
Ready
Health

Market Data health / freshness
Provider state

Safety lane
Scanner lane

Database
Singleton fence

Recovery
Reconciliation

Operator Intent
System Derived State

Incidents

AI / Advisory activation
```

**Reconciliation：仅 detector，绝不是 repair engine。**

**UI V1 不提供**：

```text
Pause
Resume
Emergency Stop
Block
Unblock
Resolve Incident
Repair
```

---

## 31. AI Current State（AI 当前状态，冻结）

当前正确的 UI 语义：

```text
AI / Advisory

Design:              Accepted
Runtime:             Not Activated
live G2→G3:          Not Active
Real AI Provider:    Not Activated
```

**该预期内的 disabled 状态是 U0 未激活，不是 warning / error。**

**不得**发明 durable 的「AI 排队中」。

**当前已接受设计明确不存在 durable `QUEUED` 状态。**

---

## 32. Needs Attention Contract（需关注契约，冻结）

- **总览**：最多约 **3** 条最高价值的 attention items。
- **系统页**：完整的活动问题 / 事件视图（full active issue / incident view）。
- **优先级顺序（冻结）**：

```text
1. blocking system safety
2. position / protection safety
3. other warnings
4. informational items
```

- **不得把正常状态变成警报墙（alarm wall）。**
- **不得推断 backend 未返回的因果关系。**

---

## 33. Presentation vs Business Derivation

见 §4（权威边界）。§4.1 / §4.2 的清单是本节的具体化，二者为同一契约。

---

## 34. Timezone Contract（时区契约，冻结）

- **主 UI**：浏览器本地时区，并带时区指示（timezone indication）。
- **Technical trace**：UTC ISO 8601。
- **自定义时间范围**：`[start, end)`
- **前端将本地边界转换为 UTC 后再发起 API 查询。**

---

## 35. Desktop / Accessibility（桌面与可访问性，冻结）

- **Desktop-first。**
- **主验收视口**：`1440 × 900`
- **最低支持**：`1280 × 720`
- 低于最低支持时：**允许滚动**，但**不得出现关键状态重叠 / 裁切**。
- **状态 / 严重度 / 数据质量绝不可仅依赖颜色传达。**

---

## 36. Visual Governance（视觉治理，冻结）

深色专业量化终端风格。

**高信息密度，但不杂乱。**

**禁止**：

```text
3D
WebGL-heavy effects
GPU-heavy animation
gratuitous canvas effects
cyberpunk decoration that harms readability
```

**视觉 mockup 仅为参考。Formal Product Truth 优先。**

---

## 37. Product Read Projections（五个逻辑读模型，冻结）

```text
1. MarketScannerRead
2. OpportunityTraceRead
3. EdgeAggregateRead
4. TradingAuditRead
5. SystemIncidentRead
```

**冻结规则**：

- 这些是 **read projections（读投影）**，**不是**新的业务权威。
- **不得为每个视觉组件创建一个 endpoint。**

---

## 38. Partial Availability（部分可用性，冻结）

**必须支持跨域部分可用（cross-domain partial availability）。**

示例：

```text
Market      = AVAILABLE
Trading     = AVAILABLE
Opportunity = CAPABILITY_NOT_INTEGRATED
System      = AVAILABLE
```

**不得因为某一个域失败就把整个页面置空。**

**在强耦合的经济域内部**，backend 必须提供合理的快照一致性，尤其是：

```text
Position + Protection
Order + Fill
Account + Reservation
```

**前端不得用不相关的读取结果自行拼装出一致状态。**

---

## 39. Domain Provenance Isolation（域来源隔离，冻结）

**不得把统一的 `run_mode` 规则套用到每一张表。**

| 域 | 隔离维度 |
|---|---|
| Trading domain | 按 `run_mode` 隔离 |
| Edge / Opportunity domain | 按 `source_type` + `source_identity` + **exact Population identity** 隔离 |
| Operational Market / Scanner | 必须来自**当前 operational Runtime / database context** |

**Replay workspace 数据绝不可静默地作为当前 live operational 数据出现。**

---

## 40. Query / Performance Boundary（查询 / 性能边界，冻结）

**Market & Opportunity 范围**：

```text
15m / 30m / 1h / 4h / 6h / 24h / 7d / 30d / custom
```

- 大规模历史**使用稳定的 cursor / keyset 风格分页**。
- **不得因为这些范围存在就授权 schema / index 变更。**
- **先测量查询计划 / 延迟。**
- **任何新 index / migration 需要独立的证据与批准。**

---

## 41. Frontend Foundation Decisions Deferred（前端基础决策，冻结需求 + 延后选型）

本 D01 **冻结以下「需要」**：

```text
Router
Server Query / Cache
API Client
Auth Session Boundary
OpenAPI generation
Frontend test harness
Global Data State Boundary
```

本 D01 **不选择具体库**。

**库选型属于 `UI-F01` Formal Task Design。**

**优先复用成熟库。不得构建不必要的自定义框架。**

---

## 42. Implementation Order（设计层实施顺序，冻结）

```text
1. UI-F01    Frontend Foundation
2. UI-RD01   Product Read API Formal Design
3. UI-I01    Global Shell + System
4. UI-I02    Market / Scanner + Market & Opportunity
5. UI-I03    Trading & Position
6. UI-I04    Edge Lab
7. UI-I05    Overview
8. UI-I06    Cross-Page Integration / Final Acceptance
```

**这是 sequencing only。它不自动授权实现。**

---

## 43. Acceptance Boundary（未来客观验收边界，冻结）

未来 UI 实现的验收必须能客观核对以下边界（至少包含）：

- 顶层产品页**恰好五个**；
- AI **没有**独立顶层页；
- 简体中文为主 UI；
- desktop-first；
- 业务行为 read-only；
- `Loading` / `Empty` / `Stale` / `Unavailable` / `Capability Not Integrated`
  保持**互不相同**；
- **unavailable 绝不渲染为 zero / empty**；
- **Scanner Event 绝不成为 BUY / SELL signal**；
- Opportunity trace 使用**双分支模型**；
- **Forward Outcome ≠ Economic Result**；
- Edge **Primary horizon = `5m`**；
- Edge **Exact Population identity**；
- **不展示未支持的策略指标**；
- Account 现金语义正确（§19）；
- **支持多标的 / 多经济对象同时存在**；
- **在声称交易已发生之前必须有 Fill**；
- **Position Protection 仅来自 durable Position authority**；
- **Plan 过期不使 durable protection 失效**；
- `Live` / `Ready` / `Health` 保持互不相同；
- **`/ready` 503 被解析为合法状态**（而非网络故障）；
- Real AI disabled 渲染为 `U0`；
- **无 UI mutation 控制项**；
- Product boundary 与 Runtime Mode 分离（§24）；
- **historical / replay 数据绝不伪装成 live operational truth**；
- 认证后的 Product Read 边界；
- **Edge aggregation 的 CPU 工作不阻塞主 event loop**；
- `1440×900` 与 `1280×720` 布局验收；
- **状态不单靠颜色传达**。

---

## 44. Implementation Authorization（实现授权声明，冻结）

```text
本文件是 DESIGN ACCEPTANCE。

它不授权：
  - UI 实现
  - 前端实现
  - 后端 / Product Read API 实现
  - 任何 schema / migration / index 变更
  - 任何 runtime / config / dependency 变更

后续任何一步实现都需要独立的人工授权窗口。
§42 的实施顺序只是排序，不是授权。
```

---

## 45. Non-Claims / Remaining Open（非声称与剩余开放项）

本 Acceptance **不**声称、**不**证明、**不**授权：

| 项目 | 状态 |
|---|---|
| UI 实现 | `NOT STARTED` |
| `PRE-01B-I2` | `NOT STARTED / NOT ACTIVATED` |
| Real AI | `NOT ACTIVATED` |
| live `G2→G3` Advisory | `NOT ACTIVE` |
| Forward Outcome 运行时自动生产 | `NOT INTEGRATED`（无 Product consumer） |
| `SE-02D` Aggregate Product consumer | 不存在（accepted callable core only） |
| Gate A / Gate B | `NOT ACTIVATED` |
| Gate C | `NOT PASSED` |
| Live Trading | `NOT AUTHORIZED / DISABLED` |
| Trading Edge | **未证明**（`Deterministic Replay ≠ Trading Edge Proof` 仍成立） |
| 前端库选型 | `DEFERRED` 至 `UI-F01` |
| Product Read API 实现 | `NOT STARTED` |
| historical arbitrary revision-as-of | `OPEN / NOT SUPPORTED` |
| experiment / pair / arm identity | `OPEN GATE C PREREQUISITE` |
| durable regime identity | `OPEN GATE C PREREQUISITE` |
| Gate C immutable evidence retention | `FUTURE GATE C EVIDENCE TASK` |
| `KEEP / DOWNWEIGHT / KILL` | `NOT OWNED` |
