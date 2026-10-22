# Product Requirements Baseline — MarketPulse AI

> 本文件是 MarketPulse AI 的**长期产品需求基线（Product Requirements Baseline）**。
> 它不是完整 PRD，也不是代码 Spec。目标是：小、稳定、长期有效、产品级、可跨聊天窗口 / 跨 AI / 跨 Acceptance Group 恢复。
> 本文件只描述**产品为什么存在、长期要解决什么、稳定产品边界、核心职责模型、长期能力方向**。
> 任何实现细节、临时 branch、commit SHA、Bug 编号、测试数量都不应写在这里——这些会快速过期。

## 0. 文档权威定位（先读这段）

```text
PRODUCT_REQUIREMENTS.md        ← 本文件：产品为什么存在 / 长期要解决什么 / 稳定产品边界
        │
        ▼
DECISIONS.md                   ← 已经正式拍板的产品语义 / 架构 / 风险 / 行为冻结
        │
        ▼
Current Group Design / Acceptance Contract  ← 当前这一批具体允许做什么（Scope / AC）
        │
        ▼
Code / Schema / Tests          ← 当前实际已经实现什么
        │
        ▼
PROJECT_STATE.md               ← 当前项目推进到哪里
        │
        ▼
dev_log / Acceptance Evidence  ← 历史实施与验收证据
```

> 注：上方关系图是**文档职责图（document responsibility map）**，描述各文档在产品信息链中的职责分工与衔接顺序，**不代表 Source-of-Truth 权威性优先级**。真正的权威性优先级以 `AI_CONTEXT.md` §2 Source of Truth 为准（代码/Schema/Tests → PROJECT_STATE.md → DECISIONS.md → PRODUCT_REQUIREMENTS.md → Group Spec → dev_log → AI_CONTEXT.md → Chat），且本文件不得静默覆盖 `DECISIONS.md` 与已验收实现。

**若本文件与已批准 `DECISIONS.md` 或当前 Accepted 实现冲突：`DECISIONS.md` + Accepted implementation 不得被本文件静默覆盖。** 走变更流程（见 §14）。

---

## 1. Product Identity（产品定位）

**MarketPulse AI** 是一个 **AI-assisted quantitative Paper Trading system（AI 辅助量化纸面交易系统）**。

当前 V1 产品目标：

- BTC / ETH 为当前主要交易对象；
- 接收真实市场行情；
- 发现值得进一步分析的市场行为；
- AI 基于结构化市场 Evidence 做分析；
- 程序生成 Trade Plan；
- Risk Engine 做最终风险授权；
- Paper Execution 执行；
- Position Manager 持续保护和重新评估仓位；
- Ledger / Trade / Account 保留完整经济事实；
- Replay / Evaluation 提供可验证证据；
- 最终通过长期 Paper 数据验证 Trading Edge，再决定后续 Live Trading。

**不得把「已经能够 Live Trading」写成当前能力。** V1 当前是 Paper Trading。

### 1.1 当前阶段（2026-10-22 Human 确认）：信号研究优先

当前阶段的目标**不是**优先交付完整的 AI Paper 交易系统，而是用 `research/` 沙盒快速证伪假设：

> 找到一个 family：相对无条件基线有信息优势（G1）、扣除成本后仍有正期望（G2），并在**独立新数据**上被确认。

找不到有效信号也是允许的研究结果。**不得为了让某个 family 过门槛而调参。**

**阶段顺序**（后续各阶段均需单独授权；本次只确认研究阶段）

```text
离线探索（research/ 沙盒：K 线 + 可获得的免费衍生品数据）
    ↓
独立新数据确认（未参与选择的数据）
    ↓
获准后：仅该 family 的最小生产接线 + 实时前向验证
    ↓
自动 Paper（无人工介入的持续纸面运行）
    ↓
可选 AI 对照，具体实验设计另行确定
    ↓
另行决定是否 Live
```

**两道门**（沿用 `research/kernel.py` 现有实现，本文件不改算法、不改门槛）

- **G1**：事件净收益相对无条件基线的差值区间下界 > 0 —— 信号携带信息。
- **G2**：事件净收益的成本后期望区间下界 > 0 —— 扣成本后赚钱。
- 两道门均按 Bonferroni 校正后的 `alpha / m` 判定；`m` = `research/test_registry.json` 累计登记的比较数（当前 60 = 12 + 12 + 36），**只增不减**。

**探索数据与确认数据必须分开**

- 任何参与过 family 选择、参数比较或方向判断的数据，都是**探索数据**。
- 本轮引入的更早历史（即使此前从未看过）**不自动成为独立确认集**；一旦用于选择，它就是探索。
- 独立确认只能使用**未来新积累、且未用于任何选择**的数据，并在开始确认前预先约定窗口与判据。
- 已知事实：现有 730 天文件已被看过，属探索；真正的确认窗口需要未来数据。

**时间盒**：研究阶段按四周方向排期，起点与截止日期尚未最终核定；本文件不写具体日期，也不自动延期。

**后续任务**：N1 长周期补证据、N2 衍生品上下文、N3 用户假设转 family，仅列为待办，状态记在 `NOW.md`；本次 N0 不启动 N1–N3，后续按各自授权推进，也不默认并行派发。

**本阶段不改变**：§7 的 V1 边界（Paper only、Spot LONG only、无 Live）与 §8 的全部安全不变量（Fail Closed、风险降低动作仍可用、Recovery First、No Fake History、Exactly-Once）继续有效。§11 的 AI 激活与长期 Paper 仍属 Future Direction，不因本阶段提前。

---

## 2. Product Objective（产品核心目的）

产品不是为了：

- 尽可能多交易；
- 追逐所有市场波动；
- 用大量大众指标生成信号；
- 猜测某个具体「庄家是谁」；
- 让 AI 自由决定并直接执行资金动作。

产品核心目标：

> 根据可观察、可验证、可审计的市场事实，识别具有潜在交易价值的市场行为，在严格风险控制下进行 Paper Trading，并通过真实长期 Evidence 判断系统是否拥有可持续 Trading Edge（交易优势）。

允许从主导资金留下的可观察痕迹推断市场行为，但：

> **不得把不可验证的参与者身份或主观「庄家下一步一定怎么走」当作事实。**

---

## 3. Trading Philosophy（交易哲学）

系统核心关注**市场行为**，例如：

- Price Structure（价格结构）
- Volume / Trade Activity（成交活动）
- Aggressive Buying / Selling（主动买卖）
- Liquidity（流动性）
- Breakout / Failed Breakout（突破 / 突破失败）
- Volatility Expansion（波动扩张）
- Relative Strength（相对强弱）
- Open Interest / Liquidation 等衍生品 Context（在数据和当前产品边界允许时，作为市场证据）

**Scanner 的职责**：发现异常、变化、值得分析的事实。

**Scanner 不应直接把 `异常 = BUY` 或 `异常 = SELL` 写死。** Scanner 负责「值得分析」，不拥有经济动作权。

---

## 4. Indicator Boundary（指标边界）

以下大众技术指标**不得**作为 Opportunity / Trade Candidate / 开仓的**单一直接触发依据**：

- MACD 金叉 / 死叉
- RSI 超买 / 超卖
- 单纯 EMA / MA crossover
- 单一 DOM 信号
- Fear & Greed Index
- DVOL
- Basis Rate
- 其它类似单指标机械规则

它们可以作为：

- Context
- Observation
- Supporting Evidence

但不得替代：

> 市场结构 + 市场行为 + 风险约束 + 可验证 Evidence。

**不要因此删除仓库中已有辅助指标。** 本文件只记录产品原则，不要求改动任何现有代码。

---

## 5. Core Trading Loop（核心业务闭环）

长期责任链（名称依据当前 Accepted Repository Truth；禁止为写文档而重构模块）：

```text
Market Data
    ↓
Scanner
    ↓
Candidate / Watch Context
    ↓
AI Analyst
    ↓
Trade Decision
    ↓
Trade Plan
    ↓
Risk Engine
    ↓
Execution
    ↓
Position Manager
    ↓
Trade / Account / Ledger
    ↓
Evaluation / Review
```

每一条链路的**职责**见 §6。

---

## 6. Responsibility Boundaries（责任边界）

### Market Data

负责：提供规范化、具有时间语义的市场事实。
不负责：Buy / Sell 决策。

### Scanner

负责：检测市场事件、异常和状态变化。
不直接拥有经济动作权（不把 `异常 = BUY/SELL` 写死）。

### AI（Advisory / Analysis Authority）

AI 可以：

- 解释市场 Evidence；
- 输出结构化 Decision；
- 对仓位重新评估；
- 提供 Trade Plan 所需分析输入。

AI 不可以：

- 直接写账户余额；
- 直接创建未经程序化验证的 Fill；
- 绕过 Risk Engine；
- 绕过 Position Protection；
- 自行改变系统风险规则。

### Risk Engine

所有**风险增加型**经济动作继续以程序化 Risk Authority 为最终授权边界。

### Execution

只执行：已通过完整程序化授权链的合法 Execution Intent。

### Position Protection

已有持仓保护优先级必须高于：

- 新 Opportunity；
- 新 Entry；
- AI 延迟；
- AI 超时；
- 非关键分析工作。

---

## 7. V1 Current Product Boundary（当前 V1 边界）

依据 Accepted Repository Truth 写明**当前边界**，不是未来愿景：

- **Paper Trading only**；不启用 Live Trading。
- 当前 Spot Paper = **LONG only**。
- `SHORT_BIAS` 可以作为分析事实，但**不得产生 Short Execution**。
- Live Trading 尚未开放。
- **SPOT / SWAP 语义严格隔离**（不同的 `market_type` / `instrument_id`）。
- AI 单一 Primary Provider 边界；当前**没有**自动 multi-model voting / fallback。
- Risk Engine authoritative。
- PostgreSQL 是 Restart Recovery 的 durable source of truth。
- Reconciliation = detector，不是 repair engine。
- `TradePlan.invalidation` 为 advisory text（AI / human-readable，非 machine-executable condition）。
- `stop_loss` 为当前 machine-enforceable hard price invalidation。
- 默认本地安全运行边界按当前 Accepted 配置记录（`LOCAL_ONLY=true`、`RUN_MODE=TEST`、监听 `127.0.0.1`；Secret 不进入 Git / Frontend / API 返回）。

**不得擅自扩大 V1。**

---

## 8. Safety & Failure Philosophy（安全与失败原则）

### Fail Closed

任何会增加风险的链路若关键事实 **stale / missing / invalid / unverifiable**：

> **默认不得增加新的经济风险。**

### Risk Reduction Remains Available

Pause / Safe Mode / Emergency 等状态下：

> 风险降低型动作原则上必须仍可工作。

具体语义以 `DECISIONS.md` 和 Accepted Runtime Contract 为准。

### Recovery First

系统重启后：

> 必须先恢复并验证已有 durable economic state，再重新允许新增风险。

### No Fake History

不得伪造停机期间：

- Fill
- historical execution
- 虚构市场成交

### Exactly-Once Economic Safety

重复事件、重试、网络恢复、并发以及 restart 不应导致重复经济动作。

> 这里只记录产品级 invariant。具体事务和锁实现仍属于 Group Spec / Code。

---

## 9. Evidence & Audit Principle（证据原则）

MarketPulse AI 不是只输出 `BUY / SELL`。

任何重要经济行为都应尽量能够回答：

```text
发生了什么市场事实？
↓
Scanner 为什么产生 Event / Candidate？
↓
AI 看到了什么 Evidence？
↓
AI 输出了什么 Decision？
↓
Trade Plan 是什么？
↓
Risk 为什么允许 / 拒绝？
↓
实际 Paper Execution 如何发生？
↓
仓位后来发生什么？
↓
最终经济结果如何？
```

未来 Trading Edge 的结论必须建立在 **durable / reproducible evidence** 上。

不得把以下任一直接视为 Trading Edge 已被证明：

- AI 自我解释；
- 单次盈利；
- 单个测试结果；
- 高胜率。

---

## 10. Replay / Evaluation Positioning（回放与评估定位）

当前已证明的主要是：

- Replayability（可回放）
- Determinism（确定性）
- Durable fact consistency（持久事实一致性）
- Minimal deterministic evaluation（最小确定性评估）

必须明确：

> **Deterministic Replay ≠ Trading Edge Proof。**

当前 Accepted 状态**未支持**的高级分析指标，不得在本文档中描述为已完成能力，例如：

- MFE / MAE
- Drawdown
- Equity Curve
- Win Rate
- R-Multiple
- Sharpe
- Sortino
- Profit Factor

这些未来只有在 Evidence 足够且单独批准设计之后才能进入产品能力。

**例外（已接受能力，2026-09-16 Human Acceptance = `CONFIRMED`）**：

> **Family-level current-snapshot Forward Outcome Expectancy = SUPPORTED / ACCEPTED
> via SE-02D V1。**

即 family 级 current-snapshot 聚合口径的 Forward Outcome Expectancy 已由 `SE-02D`
（`SE-02D-D01` 设计 + `SE-02D-I01` / `SE-02D-I02` / `SE-02D-I03` 实现与验收）接受为
**当前已支持能力**。这是 capability-status 调和，**不是**新增产品需求。

该能力**不**声称：

- Trading Edge 已被证明；
- executed-trade edge 已被证明；
- Real AI edge 已被证明；
- `Gate C` 已通过；
- generic strategy profitability 已被证明。

本文件其余部分不变：**Deterministic Replay ≠ Trading Edge Proof** 仍然成立；上列其余
指标（MFE / MAE、Drawdown、Equity Curve、Win Rate、R-Multiple、Sharpe、Sortino、
Profit Factor）仍然**未支持**，未被本次调和提升为产品能力。

---

## 11. Product Evolution Path（产品演进原则）

这里只写高层路线，不预先冻结尚未批准的 Group 设计：

```text
Accepted Trading Components
        ↓
Continuous Runtime Validation
        ↓
Real AI Activation
        ↓
Long-running Paper / Soak
        ↓
Trading Edge Evaluation
        ↓
只有 Edge + Safety + Runtime Evidence 足够
才讨论 Live Trading
```

注意：

- 不应擅自把这些阶段命名为 G6 / G7 / G8 / G9；
- 当前 Repository 若尚未批准 Next Group，则继续保持 `NOT STARTED / NOT YET APPROVED`；
- 本文件只描述 **capability progression（能力演进）**，不替代未来 Design Gate。

---

## 12. Explicit Non-Goals（明确非目标）

Product Baseline 应防止后续 Scope 膨胀。当前**不因为长期目标而自动要求**：

- Microservices
- Kafka
- Redis
- Celery
- Kubernetes
- Multiple Trading Engines
- 多 AI 投票系统
- Small Brain
- 自动 Parameter Optimization
- 自动 Strategy Evolution
- Live Trading
- Contract Short Trading
- 超复杂 Dashboard
- 大量传统 Technical Indicators
- 为「架构高级」而增加的基础设施

原则：

> 新基础设施只有出现真实需求并经过独立批准后才能加入。

---

## 13. Relationship With Repository Truth（文档权威边界）

### PRODUCT_REQUIREMENTS.md（本文件）负责

- Product Goal
- Product Philosophy
- Stable Product Boundaries
- Core responsibility model
- Long-term capability direction

### DECISIONS.md 负责

已经正式批准的：

- 产品语义决策
- 架构决策
- 风险决策
- 行为冻结

### Group Design / Acceptance Contract 负责

某一个 Acceptance Batch 的：

- Scope
- Out of Scope
- Functional Contract
- Failure Contract
- AC

### Code / Schema / Tests 负责

当前实际实现事实。

### PROJECT_STATE.md 负责

当前项目状态。

### dev_log 负责

实施与验收历史证据。

**不存在一份文档同时宣称自己覆盖所有 Truth。**

---

## 14. Change Control（变更规则）

`PRODUCT_REQUIREMENTS.md` 必须被视为：

> **Stable Baseline，不是随手编辑的 Notes。**

以后若修改以下内容：

- Product Goal
- Trading Philosophy
- AI authority
- Risk authority
- Core Trading Loop
- Paper / Live boundary
- Market scope
- Safety invariant

必须：

```text
Proposal
→ Repository Truth Review
→ Human Approval
→ PRODUCT_REQUIREMENTS / DECISIONS 同步
→ Implementation
```

禁止：

> 先改代码，再回头修改需求解释代码。

---

## 15. Current vs Future（明确区分）

为避免误导，明确标注三类内容：

| 类别 | 含义 | 示例 |
|---|---|---|
| **Current Capability** | 当前已实现 / 已验收 | Paper Trading、Spot LONG、Risk Engine authoritative、Deterministic Replay |
| **Product Principle** | 长期稳定产品原则（冻结） | Fail Closed、AI advisory、Scanner 不写死 BUY/SELL、指标不单触发 |
| **Future Direction** | 未来方向，未批准 / 未完成 | Continuous Runtime、Real AI 激活、Long-running Paper、Trading Edge 证明、Live Trading |

本文件不把 Future Direction 描述为 implemented。
