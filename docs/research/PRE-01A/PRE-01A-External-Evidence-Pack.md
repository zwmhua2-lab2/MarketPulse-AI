# PRE-01A External Evidence Pack

**Task:** PRE-01A-DS1｜External Reference Research + Evidence Pack
**Model:** DeepSeek V4.1 Flash
**Task type:** READ_ONLY External Reference Research
**Reality baseline:** `PRE-01A Context Pack`（随任务附件提供，路径 `C:\Users\hua\Downloads\PRE-01A-Context-Pack.md`）
**Research date:** 2026-09-14
**MarketPulse repository modification:** NONE
**Final MarketPulse Architecture Verdict:** NOT PROVIDED (out of scope — §17)

> Scope guard: 本文件是 external reference evidence。它不改变 MarketPulse，不提出 implementation，不选择 provider，不选择 runtime host，不引入 agent framework，不重设计 G3/G4/Risk/Execution/Protection，不宣布最终 AI Placement，不宣布 AI 已提升 Trading Edge。
> 所有 MarketPulse 事实均引自随任务提供的 Context Pack（下称 **CP**），本文件未重新读取 MarketPulse 源码、未运行测试、未接触 Runtime/Docker/PostgreSQL。

---

## 1. Research Scope & Sources

### 1.1 实际研究范围

| Part | 对象 | 状态 |
| --- | --- | --- |
| A（必选 4） | NautilusTrader / Hummingbot / Freqtrade / QuantConnect LEAN | 完成 |
| A（额外 +1） | VeighNa（vn.py）+ `vnpy_riskmanager` | 完成（见 §1.4 加入理由） |
| A（额外第 2 位） | — | **未加入**（理由见 §1.4） |
| B（必选 4） | OpenAI Structured Outputs / PydanticAI / Instructor / LiteLLM | 完成 |
| B（限定范围） | LangChain + LangGraph（仅 structured output / schema validation / action permission / deterministic policy boundary / retry / tracing 相关部分） | 完成（tracing 面见 §10 GAP-04） |
| B（额外 +2） | OpenAI Agents SDK（guardrails）/ Langfuse（datasets + experiments） | 完成 |

### 1.2 主要官方来源（全部为本轮实际抓取）

| # | 来源 | 类型 | 抓取日 |
| --- | --- | --- | --- |
| S1 | `nautilustrader.io/docs/latest/concepts/architecture/` | 官方文档 | 2026-09-14 |
| S2 | `nautilustrader.io/docs/latest/concepts/execution/` | 官方文档 | 2026-09-14 |
| S3 | `nautilustrader.io/docs/latest/concepts/strategies/` | 官方文档 | 2026-09-14 |
| S4 | `api.github.com/repos/nautechsystems/nautilus_trader/releases/latest` | 官方 release API | 2026-09-14 |
| S5 | `hummingbot.org/strategies/v2-strategies/` | 官方文档 | 2026-09-14 |
| S6 | `hummingbot.org/strategies/v2-strategies/executors/` | 官方文档 | 2026-09-14 |
| S7 | `freqtrade.io/en/stable/strategy-callbacks/` | 官方文档（stable 分支） | 2026-09-14 |
| S8 | `freqtrade.io/en/stable/plugins/` | 官方文档（stable 分支） | 2026-09-14 |
| S9 | `quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview` | 官方文档 | 2026-09-14 |
| S10 | `quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/risk-management/key-concepts` | 官方文档 | 2026-09-14 |
| S11 | `quantconnect.com/docs/v2/writing-algorithms/trading-and-orders/order-errors` | 官方文档 | 2026-09-14 |
| S12 | `lean.io/docs/v2/lean-engine/class-reference/classQuantConnect_1_1Packets_1_1RuntimeErrorPacket.html` | 官方 API class reference | 2026-09-14 |
| S13 | `raw.githubusercontent.com/vnpy/vnpy/master/vnpy/trader/engine.py` | 官方源码（master 快照） | 2026-09-14 |
| S14 | `github.com/vnpy/vnpy_riskmanager`（README）+ `raw.githubusercontent.com/vnpy/vnpy_riskmanager/main/vnpy_riskmanager/engine.py` | 官方仓库与源码 | 2026-09-14 |
| S15 | `raw.githubusercontent.com/openai/openai-cookbook/main/examples/Structured_Outputs_Intro.ipynb` | OpenAI 官方 cookbook | 2026-09-14 |
| S16 | `learn.microsoft.com/.../azure-ai-foundry/openai/how-to/structured-outputs` | Azure OpenAI 官方文档（Structured Outputs 语义/子集） | 2026-09-14 |
| S17 | `ai.pydantic.dev/output/`（`pydantic.dev/docs/ai/core-concepts/output/`） | PydanticAI 官方文档 | 2026-09-14 |
| S18 | `python.useinstructor.com/concepts/retrying/` | Instructor 官方文档 | 2026-09-14 |
| S19 | `docs.litellm.ai/docs/proxy/reliability` | LiteLLM 官方文档 | 2026-09-14 |
| S20 | `docs.litellm.ai/docs/completion/json_mode` | LiteLLM 官方文档 | 2026-09-14 |
| S21 | `python.langchain.com/docs/how_to/structured_output/` → Docs by LangChain "Structured output" | LangChain 官方文档 | 2026-09-14 |
| S22 | `docs.langchain.com/oss/python/langgraph/interrupts` | LangGraph 官方文档 | 2026-09-14 |
| S23 | `openai.github.io/openai-agents-python/guardrails/` | OpenAI Agents SDK 官方文档 | 2026-09-14 |
| S24 | `docs.langfuse.com/`、`langfuse.com/docs/evaluation/get-started/offline`、`langfuse.com/docs/datasets/python-cookbook`、`python.reference.langfuse.com/langfuse/experiment` | Langfuse 官方文档与 SDK reference | 2026-09-14 |

### 1.3 明确未能取得的来源（诚实声明）

| 目标 | 结果 |
| --- | --- |
| `platform.openai.com/docs/guides/structured-outputs` | **被 Cloudflare 拦截**（`Sorry, you have been blocked`）⇒ 改用 S15（OpenAI 官方 cookbook）+ S16（Azure OpenAI 官方文档，同为 Structured Outputs 语义与 schema 子集的官方权威描述） |
| LangSmith tracing/provenance 官方页 | **本轮未抓取** ⇒ §3 中标注 `NOT VERIFIED` |
| NautilusTrader 官方 "strategy exception 处理" 页 | **未找到** ⇒ §2 标 `UNKNOWN` |
| Hummingbot 官方 risk/budget 层页（BudgetChecker 等） | **未抓取** ⇒ §2 标 `UNKNOWN` |

### 1.4 Optional additions 的加入理由（并说明为何只加 1 个 Trading System）

**Trading System 侧加入 VeighNa（vn.py）：**
CP §3 明确 MarketPulse 的 risk-increasing authority 是**结构性**的 `SystemRiskGate`（构造函数注入、可被 G3/G4 路径强制）。vn.py 是唯一在本轮找到的、其 **core 完全没有 pre-trade risk check**、而把风控放在**可选 app 中以 monkey-patch `MainEngine.send_order` 实现**的成熟框架（S13/S14）。它因此构成了"结构性 gate vs 附加式 gate"这一 authority 放置问题的**直接对照证据**，与本研究问题高度相关。

**Trading System 侧不加入第 2 个（候选 Jesse / Backtrader / Zipline / Qlib 均被排除）：**
四者的可核实材料在本轮未显示任何比 LEAN/Nautilus/vn.py **更直接相关**于"advisory → deterministic authority / failure isolation"的机制差异：Jesse/Backtrader 属"策略直接下单"（与 Nautilus 同类、信息量更低）；Zipline/Qlib 为回测/研究框架，不提供 live execution authority 分离证据。按任务 §4"禁止无限扩大研究范围"，**不加入**。

**LLM 侧加入 OpenAI Agents SDK 与 Langfuse 的理由：**
CP §5/§6 列出的真实 gap 中包含"没有 without-AI / with-AI treatment identity、paired assignment 或 baseline provenance"与"AI provenance 没有独立 provider identity / request-response ID / latency / token-cost / experiment arm"。Agents SDK 提供**typed fail-closed tripwire + guardrail 结果留存**（S23）；Langfuse 提供**dataset + experiment run identity + item-level 评估 + error isolation**（S24）。二者分别对应"authority safety/failure semantics"与"experimentability"，属 §13 要求的可对应真实 gap 的候选。

### 1.5 FACT / INFERENCE 约定

- 标 `FACT` = 来自 §1.2 所列官方来源的可引用陈述或官方源码；附来源编号。
- 标 `INFERENCE` = 本模型基于 FACT 作出的推理，**不具官方来源**。
- 标 `UNKNOWN` / `NOT VERIFIED` = 本轮未取得官方证据；**不得**当作事实使用。

---

## 2. Trading Framework Evidence

### 2.1 NautilusTrader

**版本：** 官方 release `NautilusTrader 1.231.0 Beta`（最新 release，S4）；文档为 `docs/latest`（S1–S3）。**精确 commit / 发布日期：NOT VERIFIED**（S4 载荷未含日期字段）。

#### A. Strategy / Signal Authority

- `FACT` — Strategy 拥有**下单命令发起权**：`Strategy` 提供 `submit_order(...)`、`submit_order_list(...)`、`modify_order(...)`、`cancel_order(...)`、`close_position(...)` 等方法；"These methods send point-to-point execution commands over the message bus."（S2）
- `FACT` — 因此 Nautilus 的 strategy 输出的是**可执行 order command**，而不是仅是 advisory intent/signal。策略可选设置 `exec_algorithm_id`，此时命令改道 `ExecutionAlgorithm`。（S2）
- `FACT` — Strategy 不直接接触 venue：新订单流 `Strategy → OrderEmulator | ExecutionAlgorithm | RiskEngine`，下游 `ExecutionAlgorithm → RiskEngine → ExecutionEngine → ExecutionClient`。（S2）
- `FACT` — 框架存在 `Signal` 数据类与 `on_signal` handler（S3），但**签名/命令路径不经过它**；Signal 属数据面，不属 authority 面。（S3）
- `INFERENCE` — 若把 MarketPulse 的 `AIAnalysis` 类比为 Nautilus signal，则 Nautilus 的对应物是"策略把 decision 直接变成可执行 command"，**authority 位置比 MarketPulse 更靠前**，不是 MarketPulse 可借用的 authority 模型。

#### B. Risk Authority

- `FACT` — `RiskEngine` 存在于**每一个** Nautilus system（backtest / sandbox / live），"It sits on the submit and modify path, and it also receives order events such as `OrderReleased` from the `OrderEmulator`. Cancel and query commands route directly to other execution components and **do not pass through the `RiskEngine`**."（S2）
- `FACT` — 校验范围（除非在 `RiskEngineConfig` 中被 bypass）：价格/触发价精度、正价格、数量精度与 min/max、GTD 过期、**`reduce_only` 订单不得增加持仓**、engine 级 `max_notional_per_order` 与 instrument `max_notional`、现金账户余额影响、提交/修改速率限制、**trading-state 限制**。（S2）
- `FACT` — 拒绝语义为**带 reason code 的显式事件**：submit 失败产生 `OrderDenied`，modify 失败产生 `OrderModifyRejected`；reason code 含 `REDUCE_ONLY_WOULD_INCREASE_POSITION`、`TRADING_HALTED`、`TRADING_STATE_REDUCING`、`RATE_LIMIT_EXCEEDED`、`NOTIONAL_EXCEEDS_MAX_PER_ORDER` 等。（S2）
- `FACT` — **风险增加 / 风险减少被显式区分**：`TradingState` 三态 —— `ACTIVE`（正常）、`HALTED`（新 submit/modify 被拒，**cancel 仍可通过**）、`REDUCING`（"Cancels are allowed, and only submit or modify commands that do not increase exposure are accepted."）。（S2）
- `FACT` — 风控可为 `None`/bypass：文档明确 "Unless bypassed in `RiskEngineConfig`"；但该 config 是**结构性构造参数**，与 MarketPulse `PaperExecutionService.risk_gate=None` 的"保留 standalone 行为"形状相近（CP §3 已知限定）。（S2）
- `INFERENCE` — `TradingState.REDUCING` 是成熟框架中把"风险减少动作必须在受限状态下继续可用"表达为**一等状态**的直接先例；与 CP §7 "Risk-reducing exit 在 Pause/SafeMode/Emergency 下保持可用" 属**同族语义**，但 MarketPulse 的 runtime control 已存在，二者不可直接互相替代。

#### C. Execution Authority

- `FACT` — `ExecutionEngine` "Routes trading commands to the appropriate execution clients. Tracks order and position states. Coordinates with risk management systems. Handles execution reports and fills from venues. Handles reconciliation of external execution state."（S1）
- `FACT` — 真正向交易所提交的是 venue-specific `ExecutionClient`（adapter）；策略不持有 adapter 句柄。（S1、S2）
- `FACT` — Order/Fill 与 strategy state 解耦：Fill 事件回流 `ExecutionEngine`，"which updates order state in the `Cache` and delivers the event to the strategy's handler. Fill events also trigger position and portfolio updates."（S1）
- `FACT` — `ExecutionEngine` 承担 **execution reconciliation**（外部执行状态对账）。（S1、S2 交叉引用页标题 "Execution reconciliation: Live state recovery and runtime consistency checks"）

#### D. Position / Accounting Authority

- `FACT` — `Portfolio` 维护**派生**账户与持仓状态：balances、net positions、margin、realized/unrealized PnL、exposure；由 account/order/position/quote/bar/mark-price 事件更新。（S1）
- `FACT` — `Cache` 保存 instruments/accounts/orders/positions 并提供索引读取；可选持久化 backing store。（S1）
- `FACT` — Strategy 的 `Capabilities` 列出 "Cache access"、"Portfolio access"，即**读**访问；未见任何直接的 balance/position mutation API 文档化。（S3）
- `INFERENCE` — Nautilus 的 accounting authority 与 MarketPulse 一致（engine-owned，strategy 只读）；但 Nautilus 的 accounting 更新来自**事件流**，而 MarketPulse 的经济事实在 `PaperExecutionService._settle_order()` 的**同一 transaction 内原子**写 Fill/Account/Position/Ledger（CP §3）。MarketPulse 的原子性更强。

#### E. Failure Isolation

- `FACT` — 存在**状态门控**式隔离："Subscribed data, order, and position handlers dispatch only while the strategy is `RUNNING`. Messages that arrive in any other state are logged but not passed to your handlers."（S3）
- `FACT` — 存在 supervisory 生命周期 hook：`on_resume`、`on_reset`、`on_dispose`、`on_degrade`、`on_fault`、`on_save`、`on_load`。（S3）
- `FACT` — 策略可在 `on_start` 中主动 `self.stop()` 转到 STOPPED（官方示例用于 instrument 缺失的防御路径）。（S3）
- `UNKNOWN` — **strategy handler 抛出异常后的官方行为（是否隔离该策略、是否影响 execution/accounting）在本轮抓取的官方页中未找到明文**；标 `NOT VERIFIED`。
- `INFERENCE` — 单线程 core + 事件队列 + `on_fault`/`on_degrade` 状态的存在，构成"组件级 supervisory"设计的**形状证据**；但"策略失败不损坏 accounting"这一具体保证无法从本轮材料证实。

#### NautilusTrader Evidence Record

```text
Project / Framework: NautilusTrader
Claim: Strategy 可直接 submit/modify/cancel order command；风控在 submit+modify 路径上以 RiskEngine 结构性校验并以 OrderDenied/OrderModifyRejected 拒绝；TradingState 区分 HALTED 与 REDUCING（cancel 恒通过，REDUCING 仅接受不增加敞口的 submit/modify）；Portfolio/Cache 为 engine-owned 派生状态。
FACT / INFERENCE: FACT（上述含引号的陈述）；authority 位置对比结论为 INFERENCE
Official Source: S1 architecture / S2 execution / S3 strategies
Repository / Module: nautechsystems/nautilus_trader（`risk`、`execution`、`portfolio`、`trading` crate 模块划分见 S1）
Version / Commit / Date: release tag 1.231.0 Beta（S4）；commit 与日期 NOT VERIFIED；docs=latest
Evidence Summary: 提交流 Strategy→(Emulator|ExecAlgo|RiskEngine)→ExecutionEngine→ExecutionClient；RiskEngine 校验清单与 reason code 枚举见 S2；TradingState 三态语义见 S2。
Relevance to MarketPulse: 提供"风险减少动作必须在受限状态继续可用"的外部先例（REDUCING），以及"拒绝必须是带 reason code 的显式事件"的成熟做法；同时显示 Nautilus 的 strategy 拥有比 MarketPulse 更靠前的下单权，故其 authority 模型不可直接照搬。
```

---

### 2.2 Hummingbot

**版本：** 文档页元数据显示发布日 `2026-09-05`（S5、S6），文中提及 `LP Executor` 为 "new in v2.13.0"。**精确 commit：NOT VERIFIED。**

#### A. Strategy / Signal Authority

- `FACT` — V2 Scripts/Controllers **不再直接下单**："V2 Scripts: All scripts now inherit from `StrategyV2Base` ... it uses Executors for order management **instead of raw `buy()` / `sell()` calls**."（S5）
- `FACT` — Controller 是"长跑的模块化 sub-strategy"，不是直接执行者："Controllers are production-grade, modular sub-strategies ... not started directly — a special launcher script (`v2_with_controllers.py`) loads one or more controllers into a single bot instance"。（S5）
- `FACT` — Controller 通过 **`ExecutorAction`** 表达意图：`ExecutorOrchestrator` "can execute various actions (`ExecutorAction`) such as creating, stopping, and storing executors"（`CreateExecutorAction` / `StopExecutorAction` / `StoreExecutorAction`）。（S6）
- `FACT` — 存在**绕过 controller 的 authority seam**：Executors "**Can be created directly via the Hummingbot API** without a running bot or script"。（S5）
- `INFERENCE` — 因此 Hummingbot V2 的 authority 形状是"决策层产出 **workflow 实例化请求**，执行层（Executor）持有 order 权"，与 MarketPulse 的"AI 产出 analysis → 程序化 TradePlan → caller 创建 ExecutionIntent"在**形状**上同族；但 Hummingbot 缺少"intent 必须经 gate 才可执行"的明文约束。

#### B. Risk Authority

- `UNKNOWN` — 本轮抓取的 S5/S6 架构页**未出现**独立 risk engine 或 pre-trade gate 的描述；`BudgetChecker`、`RateOracle` 等亦未在抓取页中出现。**标 NOT VERIFIED**。
- `INFERENCE` — 由 A 可知，controller 侧不存在 "risk 可 veto" 的明文结构；controller 能做的是"不创建/停止 executor"（即**策略层自我约束**），而不是被 gate 拒绝。

#### C. Execution Authority

- `FACT` — Executor 是 order 生命周期的实际持有者："Executors are self-managing components ... tasked with **managing the state of orders — initiating, refreshing, and canceling orders**, as well as halting their own operation when certain conditions are met."（S6）
- `FACT` — Executor 具有明确有限生命周期："designed to **start and finish**: each executor has a lifecycle (active → closed/failed) and handles its own order management internally"。（S5）
- `FACT` — Controller ↔ Executor 通过 **event queue** 通信，且 Controller 之间"loosely-coupled"。（S5）
- `INFERENCE` — "execution failure 是否污染 controller state" 无法从本轮材料判定；因 controller 不持有 order state，污染面**应**被限制在 executor 内，但这是 INFERENCE，非 FACT。

#### D. Position / Accounting Authority

- `FACT` — Orchestrator 可产出绩效报告："generate detailed performance reports for individual controllers or globally across all controllers. These reports include metrics such as realized and unrealized P&L, trading volume, and the distribution of close types"。（S6）
- `UNKNOWN` — position/balance 的权威持有者（client-side account tracker vs exchange connector）在本轮抓取页中**未明文**；`NOT VERIFIED`。
- `INFERENCE` — Controller 未见任何 balance mutation 能力；经济事实不由决策组件维护。

#### E. Failure Isolation

- `UNKNOWN` — Controller/Executor 抛异常后的官方行为（是否停止 bot、是否影响在途 order）在本轮抓取页中**未明文**；`NOT VERIFIED`。
- `FACT`（弱形式） — Executor 具备自终止能力："halting their own operation when certain conditions are met"（S6），即有**组件级自查终止**这一形状。

#### Hummingbot Evidence Record

```text
Project / Framework: Hummingbot (V2 strategies / executors)
Claim: V2 决策层不直接 buy()/sell()，而是经 ExecutorOrchestrator 的 ExecutorAction 创建/停止 Executor；Executor 自管 order 生命周期且具有 active→closed/failed 的有限生命周期；Executor 可经 API 绕过 controller 直接创建。
FACT / INFERENCE: FACT（引号部分）；对"authority 形状同族"的判断为 INFERENCE
Official Source: S5 `hummingbot.org/strategies/v2-strategies/`；S6 `.../executors/`
Repository / Module: hummingbot/hummingbot（`StrategyV2Base`、`ExecutorOrchestrator`、executor 类型族）
Version / Commit / Date: 文档页发布标记 2026-09-05；文中提及 v2.13.0 新增 lp_executor；commit NOT VERIFIED
Evidence Summary: Executor 类型 = Position/DCA/Grid/Arbitrage/TWAP/XEMM/LP；orchestrator 维护 controller_id→executor 映射并处理 create/stop/store 动作。
Relevance to MarketPulse: "有限生命周期、自管 order、可被显式创建/停止的执行单元"是 TradePlan + ExecutionIntent + PaperExecution 分离的外部同形物，可用于交叉验证 CP 中"Plan 与 Intent 分离"的形状；但未提供 veto-gate 先例。
```

---

### 2.3 Freqtrade

**版本：** 官方 `stable` 文档分支（S7、S8）；内容包含 ≥ `2021.12` 的特性（S7 提及 "Custom prices are supported in backtesting starting with 2021.12"），但**页面未给出具体发行版本号 ⇒ NOT VERIFIED**；源码对应 `develop` 分支（页面编辑链接）。

#### A. Strategy / Signal Authority

- `FACT` — 策略参与**入场/出场的最终确认/否决**：`confirm_trade_entry()` "Called right before placing a entry order"、"the last methods that will be called before an order is placed"；"**When True is returned, then the buy-order is placed on the exchange. False aborts the process**"；未实现则默认 `True`。（S7）
- `FACT` — `confirm_trade_exit()` 同理；官方给出**明确风险警告**："`confirm_trade_exit()` can prevent stoploss exits, causing significant losses as this would ignore stoploss exits ... will not be called for Liquidations - as liquidations are forced by the exchange, and therefore cannot be rejected."（S7）
- `FACT` — 策略**不能自行修改余额/持仓**：`custom_stake_amount()` 示例仅 `self.wallets.get_total_stake_amount()` **读取**；`adjust_trade_position()` "return a positive stake_amount ... if an additional entry order should be made" / negative for partial exit，即**以返回值表达请求**，订单由框架生成；"Modifications to leverage are not possible"。（S7）
- `FACT` — 策略可对 trade 附加**非经济**元数据：`trade.set_custom_data(key=..., value=...)`。（S7）
- `INFERENCE` — Freqtrade 的 `confirm_trade_exit()` 是"决策层可以否决保护性退出"的反面教材；MarketPulse 通过 "AI-independent durable protection" 从结构上排除了这一类否决（CP §4/§7），属 MarketPulse 更强约束。

#### B. Risk Authority

- `FACT` — Protections 是**临时停止交易**的机制："Protections will protect your strategy from unexpected events and market conditions by **temporarily stop trading** for either one pair, or for all pairs."；"All protection end times are rounded up to the next candle to avoid sudden, unexpected intra-candle buys."（S8）
- `FACT` — 控制面**仅 entries，不含 exits**：`CooldownPeriod` "locks a pair for stop_duration ... **after exiting**, avoiding a re-entry for this pair"，且 "This Protection applies only at pair-level, and will never lock all pairs globally"。（S8）
- `FACT` — 规则明细：`StoplossGuard`（lookback 内止损次数 ≥ `trade_limit` 则停，"applies across all pairs, unless `only_per_pair` is set to true"，futures 可 `only_per_side`）；`MaxDrawdown`（回撤超阈值停 `stop_duration`）；`LowProfitPairs`（pair 级利润比低于 `required_profit` 则锁该 pair）。（S8）
- `INFERENCE` — "只锁风险增加方向、不锁退出"是与 Nautilus `REDUCING` 状态同族但更弱（全局/单对锁 vs 敞口方向判定）的实现；**不构成** MarketPulse "SystemRiskGate 对 risk-increasing 有最终 veto"的等价物，因为 Freqtrade 的 Protections 不判定单笔订单敞口方向。

#### C. Execution Authority

- `FACT` — 交易由框架核心执行；策略仅通过回调**返回值**与框架交互（`custom_stake_amount` / `adjust_trade_position` / `custom_stoploss` / `custom_roi` / `custom_entry_price` / `custom_exit_price`）。（S7）
- `FACT` — 额外订单由框架管理且有独立约束："Additional orders also result in additional fees and those orders don't count towards `max_open_trades`"。（S7）
- `FACT` — 策略不与交易所直接交互（无 exchange 句柄出现在任何回调示例中）。（S7）

#### D. Position / Accounting Authority

- `FACT` — 钱包为**只读**访问（`self.wallets.get_*`）；trade/order/fee 生命周期由框架管理。（S7）
- `FACT` — 策略只能通过 `set_custom_data` 在 trade 上**附加**信息。（S7）
- `INFERENCE` — Freqtrade：accounting authority ∈ framework core，strategy ∉ accounting authority。与 Nautilus/MarketPulse 同向。

#### E. Failure Isolation

- `FACT` — **逐回调的 fail-safe-to-default**（注意：是回退到默认值，**不一定是 fail-closed**）：
  - `custom_stake_amount()`："**Freqtrade will fall back to the `proposed_stake` value should your code raise an exception. The exception itself will be logged.**"
  - `custom_stoploss()`：返回 `None` = "no desire to change"；`NaN`/`inf` 视为无效 ⇒ 等同 `None`。
  - `custom_roi()`：`NaN`/`inf` 视为无效 ⇒ 等同 `None` ⇒ 使用 `minimal_roi`。
  - `custom_entry_price()` / `custom_exit_price()`：返回 `None` 或无效值 ⇒ 回退 `proposed_rate`。
  - `confirm_trade_entry/exit`：未实现 ⇒ 默认 `True`。（S7）
- `INFERENCE` — 该模式意味着**策略异常不阻断交易**（回退到框架提议值继续执行）。这与 CP §7 的 "stale / invalid / provider-failed AI 不产生经济副作用" **不兼容**：MarketPulse 需要的是异常 ⇒ **零经济副作用**，而 Freqtrade 的默认是异常 ⇒ **按提议值继续**。属**冲突项**，记录不改 MarketPulse。

#### Freqtrade Evidence Record

```text
Project / Framework: Freqtrade
Claim: 策略不能修改余额/持仓，只能以回调返回值表达请求；confirm_trade_entry/exit 是最后的下单前确认/否决点；Protections 通过"临时停止交易"仅锁 entries（CooldownPeriod 为 pair 级、绝不全局锁）；回调异常按逐回调规则回退到框架默认值并记录日志。
FACT / INFERENCE: FACT（引号部分）；与 MarketPulse 失败语义的冲突判定为 INFERENCE
Official Source: S7 strategy-callbacks；S8 plugins
Repository / Module: freqtrade/freqtrade（docs/strategy-callbacks.md 源自 develop 分支）
Version / Commit / Date: stable 文档分支；具体发行号 NOT VERIFIED；内容含 ≥2021.12 特性
Evidence Summary: 回调清单、返回值→框架行为映射、Protections 四规则及其 pair/全局范围与"仅 entries"约束。
Relevance to MarketPulse: 两处高价值对照 —— (1) "锁入场、不锁出场"的风险增加/减少分离先例；(2) 反面教材：策略可否决 stoploss exit，且回调异常默认回退而非 fail-closed，二者均与 MarketPulse 的 AI-independent protection 与 fail-closed 约束冲突。
```

---

### 2.4 QuantConnect / LEAN

**版本：** 官方文档（S9–S11，"v2" 文档线，页面无版本号 ⇒ `NOT VERIFIED`）与 LEAN 官方 class reference（S12，注明源文件 `Common/Packets/RuntimeErrorPacket.cs`）。

#### A. Strategy / Signal Authority

- `FACT` — Algorithm Framework 的决策层输出**非可执行对象**：术语表定义 `Insight` = "An object that represents a trading signal. The Alpha model generates these objects for the Portfolio Construction model."，`PortfolioTarget` = "An object that represents the target position size for an asset"。（S9）
- `FACT` — 数据流："The assets that the Universe Selection model selects are fed into the Alpha model to generate trade signals (`Insight` objects). The `Insight` objects from the Alpha model are fed into the Portfolio Construction model to create `PortfolioTarget` objects ... The `PortfolioTarget` objects from the Portfolio Construction model are fed into the **Risk Management** model ... The `PortfolioTarget` objects from the Risk Management model are fed into the **Execution** model, which efficiently places trades to acquire the target portfolio."（S9）
- `FACT` — **仅 Execution model 下单**："Execution ... A framework module that places trades to reach the target risk-adjust portfolio based on the `PortfolioTarget` objects it receives from the Risk Management model."（S9）
- `FACT` — 存在**并行的直接下单模式**：Classic design 下 `QCAlgorithm` 同样内置 framework 方法，文档亦说明 "If your algorithm uses special order types ... use the classic design"，classic 模式下算法自行下单。（S9）
- `FACT` — 框架要求模块**互不通信**：每个模块的输出"should be the same, regardless of what you select for the Portfolio Construction, Risk Management, and Execution models"；"In the Algorithm Framework, the models should not communicate."（S9）
- `INFERENCE` — 这是本轮找到的**最接近 MarketPulse** 的 authority 形状：advisory value object（Insight）→ 程序化 sizing（PortfolioTarget）→ 风险调整 → 唯一执行者。差异在于 LEAN 的 risk 层可**调整**目标（含加仓/对冲），而 MarketPulse 的 gate 只做**拒绝**（veto）。

#### B. Risk Authority

- `FACT` — Risk Management 的定位："A framework module that manages market risks and ensures the algorithm remains within target parameters. **This model adjusts the `PortfolioTarget` objects it receives from the Portfolio Construction model before they reach the Execution model.**"（S9）
- `FACT` — 多模型**顺序串联**："the original collection of `PortfolioTarget` objects ... is passed to the first Risk Management model. The risk-adjusted targets from the first Risk Management model are passed to the second ... proceeds sequentially"。（S10）
- `FACT` — 可**清仓**（风险减少）：官方示例在 PnL 低于 TVaR 时 `targets.append(PortfolioTarget(security, 0, tag="Liquidate due to TVaR"))`，并 `algorithm.insights.cancel([security])` 以 "avoid reordering afterward"。（S10）
- `FACT` — 也可**增加风险**：官方列出的风险模型示例包含 "Option Hedging Risk Management Model: Purchase options to hedge large equity exposures"（S10）⇒ 风险层是**调整权**（adjust），不限于减少。
- `FACT` — 提供**退出优先执行**工具："`order_by_margin_impact` ... To get an enumerable where **position reducing orders are executed first** and the remaining orders are executed in decreasing order value"。（S10）
- `FACT` — 官方指引明确风险模型清仓时必须取消对应 insight："If the method creates a `PortfolioTarget` object to liquidate a security, cancel the security's insights to avoid re-entering the position."（S10）

#### C. Execution Authority

- `FACT` — Execution model 是唯一"places trades"的模块（S9，见 A）。
- `FACT` — 拒绝/失败面由框架记录并终止：见 E。

#### D. Position / Accounting Authority

- `FACT` — 持仓/盈亏由引擎持有，风险模型只**读**：示例使用 `security.invested`、`security.holdings.unrealized_profit_percent`、`security.log_return_mean.current.value` 等读取型属性。（S10）
- `UNKNOWN` — LEAN 的 balance/ledger 权威类文档本轮未抓取；`NOT VERIFIED`。
- `INFERENCE` — 在 Algorithm Framework 中，算法模块未见任何直接写 holdings 的途径；经济事实由 engine + brokerage 维护。

#### E. Failure Isolation

- `FACT` — **fail-stop（整个算法停止）**，而不是组件级隔离：
  - "Order Errors: If an error occurs with one of your orders, **LEAN logs the error message and stops executing**."（S11）
  - `RuntimeErrorPacket`："Algorithm runtime error packet from the lean engine. **This is a managed error which stops the algorithm execution.**"（S12）
  - `DefaultBrokerageMessageHandler`：`BrokerageMessageType.Error` ⇒ "**Sets the algorithm runtime error and stops it**"；`Disconnect` ⇒ "Stops the algorithm after 15 minutes if the market is open"。（S11 中 Brokerage Message Handler 页；来源见 S11 同域文档）
  - 第三方库致命错误："FATAL ERROR EXCEPTION refers to a critical failure from third-party libraries ... that **LEAN doesn't handle**"；其余运行时错误 "LEAN gracefully handles runtime errors that your code raises. It generally informs the location and cause of the error **before the algorithm is terminated**."（机器学习 Key Concepts 页，同域官方文档）
- `INFERENCE` — LEAN 的失败语义与 MarketPulse 目标**不同向**：LEAN 选择"停机保安全"，MarketPulse 要求"AI/advisory 失败时经济零副作用，且保护链不中断"。停机范式无法满足"position 必须在 AI 不可用时仍被保护并最终退出"这一需求。

#### LEAN Evidence Record

```text
Project / Framework: QuantConnect LEAN (Algorithm Framework)
Claim: Alpha 输出 Insight（signal value object）而非订单；Portfolio Construction 生成 PortfolioTarget；Risk Management 在 Execution 之前"调整" targets（可清仓、也可对冲加仓），多模型顺序串联；只有 Execution model "places trades"；算法级错误导致整个算法停止。
FACT / INFERENCE: FACT（引号部分）；与 MarketPulse 目标不同向的判定为 INFERENCE
Official Source: S9 framework overview；S10 risk-management key-concepts；S11 order-errors；S12 RuntimeErrorPacket class reference
Repository / Module: QuantConnect/Lean（Common/Packets/RuntimeErrorPacket.cs；Framework 模块见 QuantConnect/Documentation 03 Writing Algorithms/34 Algorithm Framework）
Version / Commit / Date: 文档为 v2 线，版本/commit NOT VERIFIED
Evidence Summary: 模块术语表与流向、manage_risk 签名与返回值约束、TVaR 清仓示例、order_by_margin_impact 语义、错误→算法终止的三处官方陈述。
Relevance to MarketPulse: 提供"advisory signal → 程序化 target → 风险调整 → 唯一执行者"的最完整外部同形链；同时给出两条可对照差异：(1) LEAN risk 层是 adjust 权（可加风险），MarketPulse 的 SystemRiskGate 是 veto 权；(2) LEAN 失败语义是 fail-stop，而非 fail-closed-at-action。
```

---

### 2.5 [额外] VeighNa（vn.py）+ vnpy_riskmanager

**版本：** 核心库源码抓取自 `vnpy/vnpy` **master** 快照（S13，2026-09-14）；风控模块 `vnpy/vnpy_riskmanager` README 显示 **2.0.0**（commit `a7b30bb` "更新版本号到2.0.0"，2025-10-29；Cython 优化 commit `e6d4f76` 2025-10-12）（S14）。核心库精确版本号/commit：`NOT VERIFIED`（第三方来源曾称 4.3.0，**未采用**）。

#### A. Strategy / Signal Authority

- `FACT` — 策略以 `buy()` 发起请求，经 `CtaEngine` → `MainEngine.send_order` → `Gateway`（由第二方文档描述；**核心决策路径由 S13 源码确证**：`send_order(req, gateway_name)` 直接转 `gateway.send_order(req)`）。（S13 + 二级来源，二级来源在 §1.2 未收录，故此处只采用 S13 的源码事实）
- `FACT`（源码） — 请求对象为 `OrderRequest`（S14 规则签名 `check_allowed(self, req: OrderRequest, gateway_name: str) -> bool`）。（S14）
- `INFERENCE` — CTA 策略在本系统中**没有中间批准层**：只要 `MainEngine.send_order` 未被替换，策略的 `buy()` 请求会直达 gateway。authority 位置与 Nautilus 类似（策略握有实际下单权），**不是** MarketPulse 模型。

#### B. Risk Authority

- `FACT`（源码） — **核心 `MainEngine.send_order` 不含任何风控**：
  ```python
  def send_order(self, req: OrderRequest, gateway_name: str) -> str:
      gateway: BaseGateway | None = self.get_gateway(gateway_name)
      if gateway:
          self.write_log(_("委托下单 -> {}：{}").format(gateway_name, req))
          return gateway.send_order(req)
      else:
          return ""
  ```
  `cancel_order` 同样直接转 gateway，均不经过任何风控或 `OmsEngine`。（S13）
- `FACT`（源码） — 事前风控是**可选的独立 app**，以**动态替换主引擎方法**接入：
  ```python
  def patch_functions(self) -> None:
      """动态替换主引擎函数"""
      self._send_order = self.main_engine.send_order
      self.main_engine.send_order = self.send_order

  def send_order(self, req: OrderRequest, gateway_name: str) -> str:
      result: bool = self.check_allowed(req, gateway_name)
      if not result:
          return ""
      return self._send_order(req, gateway_name)
  ```
  任一启用规则返回 `False` ⇒ 整个 `send_order` 返回 `""`，订单**不发出**（fail-closed at send）。（S14）
- `FACT` — 内置规则集：`ActiveOrderRule`（活动委托数上限）、`DailyLimitRule`（全天委托/撤单笔数）、`DuplicateOrderRule`（极短窗口内同合约同向同价重复单拦截）、`OrderSizeRule`（单笔数量上限）、`OrderValidityRule`（合约存在性、价格是否为最小变动整数倍、是否超交易所单笔最大手数）。（S14）
- `FACT` — 规则开发契约为 `check_allowed(req, gateway_name) -> bool`；"如果订单允许通过，返回 True。如果订单被拦截，调用 `self.write_log()` 记录原因，并返回 False。"；规则可 `on_init/on_tick/on_order/on_trade/on_timer` 维护内部状态。（S14）
- `INFERENCE` — 该设计的 authority 是**附加式（attribute rebinding）而非结构性**：任何在 patch 之前取得 `main_engine.send_order` 绑定引用的代码、或直接持有 `BaseGateway` 句柄的代码，都可绕过风控；框架核心不提供不变量保证。**这是 MarketPulse 应当继续保有结构性 gate 的对照理由**（CP §3 显示 `PaperExecutionService` 以构造参数注入 gate）。

#### C. Execution Authority

- `FACT`（源码） — `MainEngine.send_order` 不更新本地 order state、不调用 `OmsEngine`；订单状态的更新由 `OmsEngine.process_order_event` 在 `EVENT_ORDER` 事件到达时**异步**完成（`self.orders[order.vt_orderid] = order` / `active_orders` 维护）。（S13）
- `FACT` — 真正向交易所下单的是 `BaseGateway.send_order`（adapter）。（S13/S14）
- `INFERENCE` — "发送路径（同步）"与"状态管理（异步事件）"解耦是 vn.py 的明确设计；与 Nautilus 一致，但与 MarketPulse "同一 transaction 内原子 settle" 相比，**MarketPulse 的原子性更强**。

#### D. Position / Accounting Authority

- `FACT` — `OmsEngine` 维护 orders/trades/positions/accounts/contracts 的内存缓存并提供查询（`get_order`、`get_position`、`get_all_orders` 等），被描述为 "single-source-of-truth data access"（二级来源）；S13 源码确证 `OmsEngine` 在 `MainEngine.init_engines` 中初始化并订阅 `EVENT_ORDER`。
- `UNKNOWN` — 持久化层（BaseDatabase 实现）与该 in-memory 视图的一致性保证本轮未抓取；`NOT VERIFIED`。

#### E. Failure Isolation

- `UNKNOWN` — 策略异常/网关异常后的官方行为本轮未取得官方明文；`NOT VERIFIED`。
- `FACT`（弱形式） — 风控拦截路径会发出 `EVENT_LOG`（level=ERROR）与 `EVENT_RISK_NOTIFY` 事件，即有**拒绝可观测性**。（S14）

#### VeighNa Evidence Record

```text
Project / Framework: VeighNa (vn.py) core + vnpy_riskmanager
Claim: 核心 MainEngine.send_order 仅做 gateway 转发，无任何 pre-trade 风控；事前风控由可选 app 以 monkey-patch main_engine.send_order 的方式接入，任一规则 check_allowed 返回 False 则该笔订单不发出；OmsEngine 通过事件异步维护 order/position/account 视图，与发送路径解耦。
FACT / INFERENCE: FACT（源码级，S13/S14）；"gate 为附加式、非结构性"的架构含义为 INFERENCE
Official Source: S13 raw master vnpy/trader/engine.py；S14 github.com/vnpy/vnpy_riskmanager README + raw main engine.py
Repository / Module: vnpy/vnpy @ master 快照 2026-09-14；vnpy/vnpy_riskmanager @ 2.0.0（commit a7b30bb, 2025-10-29）
Version / Commit / Date: riskmanager 2.0.0 / a7b30bb / 2025-10-29；核心库版本 NOT VERIFIED
Evidence Summary: send_order/cancel_order 无风控的源码；patch_functions() 的 rebinding；check_allowed 契约与五条内置规则；OmsEngine 异步更新。
Relevance to MarketPulse: 提供"gate 作为可选附加层 vs 作为结构性不变量"的直接对照，支持 CP §3 中 SystemRiskGate + 构造参数注入的既有形态；其规则集（活动委托数、单笔上限、重复报单、指令合法性）可作为"gate 应覆盖哪些判据"的成熟清单参考，但不改变 MarketPulse 现有 gate 语义。
```

---

### 2.6 Trading System 横向对照（节选事实）

| 维度 | NautilusTrader | Hummingbot | Freqtrade | LEAN | VeighNa |
| --- | --- | --- | --- | --- | --- |
| 决策层输出物 | 可执行 order command | `ExecutorAction`（创建/停止执行单元） | 回调返回值（stake/stop/price/bool） | `Insight`（signal 值对象） | `OrderRequest` |
| 决策层可直接下单 | 是 | 否（V2） | 否 | Framework 模式否 / Classic 模式是 | 是 |
| 决策与执行之间是否有 gate | 有：`RiskEngine`（submit+modify 路径） | 未见（UNKNOWN） | 有：Protections（仅锁 entries） | 有：`RiskManagementModel`（adjust 权） | 核心无；可选 app 以 patch 接入 |
| 风险增加/减少区分 | 显式：`TradingState.REDUCING`（cancel 恒通过） | 未见 | 隐式：只锁 entries、不锁 exits | 部分：`order_by_margin_impact` 先执行减仓 | 未见 |
| accounting 归属 | Portfolio / Cache（engine） | UNKNOWN | framework core（wallet 只读） | engine（模块只读） | OmsEngine（异步视图） |
| 失败语义 | 状态门控 + degrade/fault hook（异常语义 UNKNOWN） | UNKNOWN | 逐回调回退默认值（可继续交易） | 算法级 fail-stop | UNKNOWN |

---

## 3. LLM Structured / Authority Evidence

### 3.1 OpenAI Structured Outputs（provider-native 强制）

#### Structured Output

- `FACT` — 能力定义："Structured Outputs is a new capability in the Chat Completions API and Assistants API that **guarantees the model will always generate responses that adhere to your supplied JSON Schema**."；启用方式为 `strict: true`（配合 `response_format` 或 function 定义）。（S15）
- `FACT` — 与 JSON mode 的区别："Unlike JSON mode, Structured Outputs **constrains the shape of the JSON, not only its validity**."；"Previously, the `response_format` parameter was only available to specify that the model should return a valid JSON."（S15）
- `FACT` — schema 由**provider 侧**（约束解码）强制，而非仅客户端校验；因此属 provider-native 层。（S15、S16）
- `FACT` — 支持的 JSON Schema **子集**（Azure OpenAI 官方文档）：类型限 String / Number / Boolean / Integer / Object / Array / Enum / `anyOf`（根对象不可为 `anyOf`）；**所有字段必须 required**（可用 `["string","null"]` 模拟可选）；`additionalProperties: false` **必须**设置；**最多 100 个对象属性、最多 5 层嵌套**；`$defs` 与递归 schema 受支持。（S16）
- `FACT` — **不支持的 type-specific 关键字**：String 的 `minLength`/`maxLength`/`pattern`/`format`；Number 的 `minimum`/`maximum`/`multipleOf`；Object 的 `patternProperties`/`unevaluatedProperties`/`propertyNames`/`minProperties`/`maxProperties`；Array 的 `unevaluatedItems`/`contains`/`minContains`/`maxContains`/`minItems`/`maxItems`/`uniqueItems`。（S16）
- `FACT` — 输出顺序跟随 schema 字段顺序；"Structured outputs aren't supported with: Bring your own data scenarios; Assistants or Foundry Agents Service; `gpt-4o-audio-preview` / `gpt-4o-mini-audio-preview` version 2024-12-17"。（S16）

#### Advisory vs Action Authority

- `FACT` — Structured Outputs 只约束**输出的形状**；它在架构上不携带任何 action authority；tool/function 也是同一约束机制（`strict: true` 使 function schema 被严格遵守），**是否执行 function 由调用方应用决定**。（S15）

#### Failure Semantics

- `FACT` — **refusal 是 schema 之外的分支**："Since a refusal does not follow the schema you have supplied in response_format, the API has a new field `refusal` to indicate when the model refused to answer. This is useful ... **to avoid errors trying to deserialize to your supplied format**."；官方示例中 `result.parsed` 为空、`result.refusal` 有值。（S15）
- `INFERENCE` — 因此"schema 合规"≠"业务可用"：refusal 必须作为**独立分支**处理。对 MarketPulse，这意味着即使启用 provider-native strict schema，`AIAnalysis` 的解析仍有第三个状态（除 VALID / 解析失败外）需要显式建模——与现有 `DecisionValidator` 的 `INVALID_*` 状态族同族，但**不作为本任务的实现建议**。
- `FACT` — 官方表述未提供 provider error / timeout / retry 语义（属 API 客户端与 SDK 层问题）⇒ 该层**不提供** stale 语义。

#### Complexity

- `FACT` — 无额外 runtime、无 agent 框架；仅一个 API 参数（`strict: true`）+ schema 约束。（S15）
- `INFERENCE` — 对 MarketPulse 而言这是**最低复杂度**的一层，但**只覆盖"shape"**，无法表达任何价格关系/业务规则（因为 `minimum`/`maximum`/`multipleOf`/`pattern` 等关键字不受支持）。程序化 validator 仍然必需。

#### Evidence Record

```text
Project / Framework: OpenAI Structured Outputs (Chat Completions / Responses)
Claim: strict:true + json_schema 由 provider 侧强制 schema 形状（非仅 JSON 有效性）；schema 只支持子集（全字段 required、additionalProperties:false、≤100 属性/≤5 层、无 min/max/pattern/format/minItems 等）；refusal 是 schema 之外的独立字段。
FACT / INFERENCE: FACT
Official Source: S15 openai/openai-cookbook `examples/Structured_Outputs_Intro.ipynb`；S16 learn.microsoft.com Azure OpenAI "Structured outputs"
Repository / Module: openai/openai-cookbook（main 分支快照）；Azure OpenAI Chat Completions `response_format`
Version / Commit / Date: cookbook 内示例模型 `gpt-4o-2024-08-06`（说明该页为 2024-08 时代内容）；Azure 页注明结构化输出自 API 版本 `2024-08-01-preview` 起支持；抓取日 2026-09-14
Evidence Summary: 能力定义与 JSON mode 对比、strict 开关、refusal 字段的存在理由、完整 schema 子集与不支持关键字清单、若干不支持场景。
Relevance to MarketPulse: 直接对应 CP §6 gap "structured provider reliability"：若未来激活 Real AI，现有 G3/G4 schema 必须落在该子集内（否则 provider 侧拒绝或静默降级），且必须显式处理 refusal 分支；但 schema 层无法承载价格关系校验 ⇒ 程序化 validator 不可被替代。
冲突记录：无（不改变 MarketPulse 任何 authority 原则）。
```

---

### 3.2 PydanticAI

#### Structured Output

- `FACT` — 通过 `Agent(output_type=...)` 声明类型；支持标量/list/dict/TypedDict/StructuredDict/dataclass/Pydantic model/union 与多选类型；"Structured outputs (like tools) use Pydantic to build the JSON schema used for the tool, and to validate the data returned by the model."（S17）
- `FACT` — 三种输出模式：
  1. **Tool Output（默认）**："the output JSON schema of each output type (or function) is provided to the model as the parameters schema of a special output tool. This is the default as it's supported by virtually all models"。
  2. **Native Output**："uses a model's native 'Structured Outputs' feature（aka 'JSON Schema response format'）, where the model is **forced** to only output text matching the provided JSON schema"；"not supported by all models, and sometimes comes with restrictions"。
  3. **Prompted Output**：仅通过 instructions 要求模型遵守 schema；"usable with all models, but is often the **least reliable** approach as the model is not forced to match the schema"。（S17）
- `FACT` — schema 强制归属随模式变化：Native = provider 强制；Tool/Prompted = 客户端 Pydantic 校验 + 重试。（S17）
- `FACT` — 陷阱：`StructuredDict` 路径**不做任何校验** —— "Pydantic AI will not perform any validation of the received JSON object and it's up to the model to correctly interpret the schema and any constraints expressed in it"。（S17）

#### Advisory vs Action Authority

- `FACT` — 输出是**数据对象**或 **output function 调用**；`Agent` 运行时负责 orchestrating tools 与 retries，但 authority 归属于调用方应用：输出以 `AgentRunResult.output` 返回。（S17）
- `INFERENCE` — 框架本身**不提供**"输出必须经过外部 deterministic gate 才能产生副作用"的结构；它与 MarketPulse 的 authority 边界正交（不冲突，也不提供帮助）。

#### Failure Semantics

- `FACT` — `ModelRetry` 是核心重试信号：output function 与 output validator 均可 `raise ModelRetry(...)` 要求模型重出。（S17）
- `FACT` — **重试预算默认 = 1**："Each `ModelRetry` raised here consumes one unit of the run's output retry budget. **The budget defaults to `1`** and can be set on the agent with `AgentRetries` via `Agent(retries={'output': N})`, on a single run via `agent.run(retries={'output': N})`, or per output tool via `ToolOutput(max_retries=N)`."（S17）
- `FACT` — 预算耗尽 ⇒ 抛 `UnexpectedModelBehavior`（官方示例：`except UnexpectedModelBehavior as e:`，并检查 `e.__cause__` 是否为 `ModelRetry`）。（S17）
- `FACT` — 非 `ModelRetry` 的普通异常（含 `ToolFailed`）："an `on_output_process_error` hook can recover from it, **otherwise it aborts the run**."；另有 "A run can also be cancelled if usage limits are exceeded"。（S17）
- `UNKNOWN` — timeout / provider error / **stale result** 的特定语义：`NOT VERIFIED`（该页未覆盖；stale 语义在 LLM 结构化框架中未见对应概念）。

#### Complexity

- `FACT` — 引入完整 **Agent runtime**：agent、tools、deps、`RunContext`、output functions/validators、streaming、usage limits、retries 配置面。（S17）
- `INFERENCE` — 相对 MarketPulse 现有 `AIProvider.analyze(snapshot, prompt) -> AIAnalysis` 的**单次无工具调用**契约，PydanticAI 的运行时面显著更大；其中仅"output validator + 有界 retry + 结构化解析"与本任务直接相关。

#### Evidence Record

```text
Project / Framework: PydanticAI
Claim: 支持 Tool/Native/Prompted 三种结构化输出模式，强制点分别为客户端校验 / provider 原生强制 / 指令依赖；output retry 预算默认 1，耗尽抛 UnexpectedModelBehavior；非 ModelRetry 异常在无 recover hook 时中止本次 run；StructuredDict 路径不做校验。
FACT / INFERENCE: FACT
Official Source: S17 ai.pydantic.dev/output/（pydantic.dev/docs/ai/core-concepts/output/）
Repository / Module: pydantic/pydantic-ai（Agent.output_type、AgentRetries、ToolOutput.max_retries、output_validator、ModelRetry、UnexpectedModelBehavior）
Version / Commit / Date: 页面未标注版本号 ⇒ NOT VERIFIED（页面内容含 gpt-5-mini/gpt-5.2/claude-opus-4-6 等较新模型标识，推断为近期版本；此为 INFERENCE）
Evidence Summary: 三模式定义与可靠性排序、校验归属、重试预算与默认值、耗尽异常、validator 与 function 的区别、StructuredDict 无校验。
Relevance to MarketPulse: 直接对应 "structured provider reliability"（校验失败处理 + 有界重试）与 "provenance"（每次重试的失败原因可被应用记录）。其 Agent runtime 属 OVER-ENGINEERING RISK（见 §8），但其 output-validator/retry 语义是 REFERENCE ONLY 的有价值最小集。
冲突记录：无。
```

---

### 3.3 Instructor

#### Structured Output

- `FACT` — 以 `client.create(response_model=...)` 方式取得经 Pydantic 校验的对象；校验为**客户端**进行（在 SDK 响应之后）。（S18）
- `FACT` — 支持 `context` 参数把**运行时数据**传入 validator：官方示例 `verify_quote_exists` 用 `info.context['source_text']` 校验 `quote` 是否真的出现在源文本中，否则 `raise ValueError`。（S18）
- `FACT` — 支持 `token_budget` 作为**重试成本上限**："Use `token_budget` to stop validation retries after cumulative provider usage reaches a positive token limit"；"The budget is checked after a response fails validation and before Instructor prepares another request."；无法安全计量时抛 `TokenUsageUnavailableError` 而**不再发请求**。（S18）
- `FACT` — 支持流式与结构化并存（`token_budget` 目前要求非流式结构化响应）。（S18）

#### Advisory vs Action Authority

- `FACT` — Instructor 是"客户端 patch + 校验 + 重ask"层：不定义 tool/action permission，不提供 action authority。（S18）
- `INFERENCE` — 与 MarketPulse 边界正交；其价值集中在"如何把 LLM 输出安全地变成 Python 对象"，不涉及"谁能下订单"。

#### Failure Semantics

- `FACT` — **两个同名重试设置必须区分**：`OpenAI(max_retries=2)` 是 SDK transport 重试；`client.create(max_retries=2)` 是 Instructor 的 validation 重试；"Negative integer values are treated as zero retries."。（S18）
- `FACT` — 整数 `max_retries` 下 Instructor 只重试**解析与校验错误**；"An exhausted SDK rate-limit, connection, or server error is wrapped in `InstructorRetryException`; **Instructor does not restart it automatically**."（S18）
- `FACT` — 耗尽 ⇒ `InstructorRetryException`，并携带**失败历史**：`e.n_attempts`、`e.failed_attempts`（每次尝试的异常），"Failed attempts are automatically propagated to reask handlers, enabling contextual error messages and progressive corrections."（S18）
- `FACT` — 官方最佳实践表：rate limits 5 次（1s→60–120s）、**validation errors 2–3 次**、network errors 4 次；并明确 "Always Set Stop Conditions"、把无界重试标为 Bad。（S18）
- `FACT` — 官方明确要求测定口径诚实："A missing measurement must remain unknown rather than being reported as zero."（S18）
- `UNKNOWN` — stale result 语义：无对应概念，`NOT VERIFIED`（LLM 层不存在 MarketPulse 式 `state_version` staleness）。

#### Complexity

- `FACT` — 轻量：patch 现有 client（`instructor.from_openai(...)` / `from_provider(...)`）+ Pydantic 模型；**无需 agent runtime**；额外依赖为 tenacity（可选）。（S18）
- `INFERENCE` — 在本轮所有 LLM 候选中，Instructor 的"引入面 / 与本任务相关能力"比最高。

#### Evidence Record

```text
Project / Framework: Instructor
Claim: 客户端 Pydantic 校验 + 有界重试；SDK 传输重试与校验重试是两个独立同名参数；耗尽抛 InstructorRetryException 并保留 n_attempts / failed_attempts；支持 token_budget 成本上限与 context 驱动 validator；官方给出按错误类型分档的重试预算与"必须有 stop condition"的要求。
FACT / INFERENCE: FACT
Official Source: S18 python.useinstructor.com/concepts/retrying/
Repository / Module: instructor（`from_provider`/`from_openai`、`client.create(response_model=…)`、`InstructorRetryException`、`TokenBudgetExceeded`、`TokenUsageUnavailableError`、tenacity `Retrying`）
Version / Commit / Date: 页面未标注版本 ⇒ NOT VERIFIED
Evidence Summary: 重试计数口径与乘积陷阱说明、异常包装边界、failed_attempts 结构、token_budget 检查时机、validator context 用法、最佳实践表。
Relevance to MarketPulse: 直接对应 "structured provider reliability" 与 "provenance"（失败历史可入库，补充 CP §4 指出 `ai_decisions` 现缺 latency/token/cost/attempt 维度）；其 `context` validator 模式对应"用冻结 snapshot 校验 AI 输出"的既有思路（MarketPulse 已有 DecisionValidator），属同族强化。
冲突记录：无。
```

---

### 3.4 LiteLLM

#### Structured Output

- `FACT` — 统一入口支持 `response_format={"type":"json_schema", ...}` 与 `response_format=<Pydantic Model>`；官方列出可用范围（OpenAI / Azure / xAI / Google AI Studio / Vertex / Bedrock / Anthropic / Groq / Ollama / Databricks）。（S20）
- `FACT` — 提供能力探测 API：`get_supported_openai_params(model=..., custom_llm_provider=...)` 与 `supports_response_schema(model=..., custom_llm_provider=...)`。（S20）
- `FACT` — 对不支持 native json_schema 的模型，提供**客户端校验**开关："Not all models support passing the json_schema to them natively. To solve this, LiteLLM supports client-side validation of the json schema."（`litellm.enable_json_schema_validation=True`，用 `jsonvalidator` 校验响应）。（S20）
- `FACT` — 对 Gemini 2.0+ 会自动改用原生 `responseJsonSchema` 以支持 `additionalProperties: false`；Gemini 1.5 用 `responseSchema`（OpenAPI 风格）**不支持** `additionalProperties`（自动按版本选择）。（S20）

#### Advisory vs Action Authority

- `FACT` — LiteLLM 是**调用层路由器/gateway**，不定义 tool/action permission 与业务 authority。（S19、S20）
- `FACT` — 关键冲突点：其 core 语义是**跨 provider 自动故障转移** —— "Fallbacks are how LiteLLM does automatic **failover**. If a call fails after num_retries, LiteLLM falls back to another model group, so a failing model or provider automatically fails over to a healthy backup."；并明确 "If you are looking for 'provider failover' or 'model failover', this is the page."（S19）
- `FACT` — 默认行为甚至会绕过 key 的模型访问边界："By default a fallback configured in `router_settings` runs for every request, **even when the calling key is not allowed to call the fallback model directly**."；需要显式 `general_settings.enforce_fallback_model_access: true` 才施加访问检查。（S19）
- `INFERENCE` — 这与 CP §7 的 "单一 Primary Provider 边界，无自动 fallback/voting" **结构性冲突**。按任务 §3，此处只**记录冲突**，不建议改变 MarketPulse。

#### Failure Semantics

- `FACT` — 失败面由 gateway 处理：`num_retries`（每 model_name 重试次数）、`request_timeout`、`fallbacks`、`allowed_fails`（"cooldown model if it fails > 1 call in a minute"）、`cooldown_time`、"Covers all errors (429, 500, etc.)"；fallbacks 按数组顺序 in-order 尝试；全部 cooldown 时回退到 specific model ID 且跳过 cooldown 检查；另有 `content_policy_fallbacks`、`context_window_fallbacks`、`default_fallbacks`。（S19）
- `INFERENCE` — 该层的失败语义是"**用另一个 provider 的结果替代失败结果**"，其可观测后果是：同一逻辑决策的产出可能来自不同 provider —— 与 CP §4 "`ai_decisions` 无独立 provider identity" 叠加时，会产生**归因不可分辨**的风险（本项为 INFERENCE，属对本任务 experimentability 的观察，不是对 MarketPulse 的建议）。

#### Complexity

- `FACT` — 引入面包含 Router/Proxy、key 与团队/项目访问控制、spend logs、cooldown、EU-region filtering、wildcard models 等企业级能力。（S19）
- `INFERENCE` — 明显超过 MarketPulse 当前需求（单 provider、单进程 Modular Monolith、Paper-only）。见 §8 `NOT JUSTIFIED`。

#### Evidence Record

```text
Project / Framework: LiteLLM
Claim: 提供跨 provider 的 json_schema 统一入口与能力探测；对无 native 支持的模型提供客户端 schema 校验开关；其核心可靠性语义是自动跨 provider failover（含默认绕过 key 模型访问边界的行为）。
FACT / INFERENCE: FACT
Official Source: S19 docs.litellm.ai/docs/proxy/reliability；S20 docs.litellm.ai/docs/completion/json_mode
Repository / Module: BerriAI/litellm（Router、`enable_json_schema_validation`、`supports_response_schema`、`model_prices_and_context_window.json`）
Version / Commit / Date: 页面未标注版本 ⇒ NOT VERIFIED（S20 引用了代码 permalink `671d8ac496b6229970c7f2a3bdedd6cb84f0746b`）
Evidence Summary: fallback/retry/cooldown 配置与语义、默认绕过访问边界的行为、json_schema 支持矩阵、客户端校验开关、Gemini 版本差异。
Relevance to MarketPulse: 记录结构性冲突（跨 provider failover ↔ 单一 Primary Provider 边界；多 provider 结果 ↔ 单 provider 归因）。其"能力探测 + 客户端校验回退"的**思路**可用于校验层设计参考，但其 gateway 形态为 OVER-ENGINEERING RISK。
冲突记录：CONFLICT（跨 provider 自动 failover / 默认绕过调用方模型访问边界）。
```

---

### 3.5 LangChain / LangGraph（限定范围）

#### Structured Output

- `FACT` — `create_agent` 的策略面：`ToolStrategy[StructuredResponseT]`（"Uses tool calling for structured output"）与 `ProviderStrategy[StructuredResponseT]`（"Uses provider-native structured output"）；直接传 schema 类型时自动选择 —— "`ProviderStrategy` if the model and provider chosen supports native structured output (e.g. OpenAI, Anthropic (Claude), or xAI (Grok)). `ToolStrategy` for all other models."；"JSON Schema dictionaries must be wrapped in an explicit strategy ... They are not automatically detected when passed directly to `response_format`."（S21）
- `FACT` — 强制归属："Provider-native structured output provides high reliability and **strict validation because the model provider enforces the schema**."；Pydantic 侧："returns validated Pydantic instance"。（S21）
- `FACT` — 捕获路径："the model generates the structured data, it's **captured, validated, and returned** in the `'structured_response'` key of the agent's state."（S21）

#### Advisory vs Action Authority

- `FACT` — tool 调用的**批准**是一个显式框架原语：`interrupt()` 可放在 tool 内部 —— "This makes the tool itself pause for approval whenever it's called, and allows for human review and editing of the tool call before it is executed."（S22）
- `FACT` — 官方列出的 pattern 含 "Approval workflows: Pause before executing critical actions (API calls, database changes, financial transactions)" 与 "Interrupting tool calls: Pause before executing tool calls to review and edit the tool call before execution"。（S22）
- `INFERENCE` — 该原语的**语义形状**（执行前必须通过一个外部确定性裁决点）与 MarketPulse 的 gate 同族；但其默认裁决者是**人**，而 MarketPulse 需要的是**程序**（`SystemRiskGate`）。不构成引入理由。

#### Failure Semantics

- `FACT` — `ToolStrategy` 有**错误重试机制**："Models can make mistakes when generating structured output via tool calling. LangChain provides intelligent retry mechanisms to handle these errors automatically."；`handle_errors` 默认 `True`（"Catch all errors with default error template"），`False` ⇒ "No retry, let exceptions propagate"。（S21）
- `FACT` — 重试提示为**模板化错误回注**，含具体校验细节："Error: Failed to parse structured output for tool 'ProductRating': 1 validation error for ProductRating.rating Input should be less than or equal to 5 [type=less_than_equal, input_value=10, input_type=int]. Please fix your mistakes."；多结构化输出冲突亦有专门错误文案。（S21）
- `FACT` — 中断的持久化与恢复：`interrupt()` 触发时 "LangGraph saves the graph state using its persistence layer and waits **indefinitely** until you resume execution"；`thread_id` 为持久化游标；恢复用 `Command(resume=...)`（S22）
- `FACT` — **重要陷阱**：恢复时 "the runtime **restarts the entire node from the beginning** — it does not resume from the exact line where `interrupt` was called. This means any code that ran before the `interrupt` will execute again."（S22）
- `INFERENCE` — "中断前副作用会重放"是对本任务 experimentability/幂等性的重要警告：任何"先执行、后审批"的写法都会被重放。

#### Tracing / Decision Provenance

- `NOT VERIFIED` — 本轮**未抓取** LangSmith tracing 的官方页；因此 LangChain 生态中 model/prompt 版本与 trace provenance 的具体机制在本包内**不作断言**。（§10 GAP-04）

#### Complexity

- `FACT` — 引入面含 graph runtime、nodes、conditional edges、checkpointer（InMemory/Sqlite 等）、状态 schema、streaming API（`stream_events(..., version="v3")`）与 interrupt 语义。（S21、S22）
- `INFERENCE` — 对 MarketPulse 当前需求（一次无工具 LLM 调用 + 程序化校验）而言过大；其 `handle_errors` 与 provider-native 选择逻辑是 REFERENCE ONLY。

#### Evidence Record

```text
Project / Framework: LangChain (create_agent) + LangGraph (interrupt)
Claim: 结构化输出在 provider 支持时优先 ProviderStrategy（provider 强制 schema），否则 ToolStrategy（客户端校验 + 模板化错误重试，handle_errors 默认 True）；interrupt() 可在 tool 执行前暂停并持久化状态，官方明确推荐用于"关键动作（含金融交易）前的批准"；恢复时会重放 interrupt 之前的节点代码。
FACT / INFERENCE: FACT
Official Source: S21 Docs by LangChain "Structured output"（/docs/how_to/structured_output/ 重定向后内容）；S22 docs.langchain.com/oss/python/langgraph/interrupts
Repository / Module: langchain（create_agent、ToolStrategy、ProviderStrategy、handle_errors）；langgraph（interrupt、Command、checkpointer、thread_id）
Version / Commit / Date: 页面未标注版本 ⇒ NOT VERIFIED；抓取日 2026-09-14
Evidence Summary: 策略选择与自动回退逻辑、provider 强制 vs 客户端校验、错误模板原文、interrupt 语义与"整节点重放"规则、状态持久化与恢复方式。
Relevance to MarketPulse: 直接对应 "authority safety"（执行前确定性裁决点的形状）与 "structured provider reliability"（有界重试 + 错误回注）。但 tracing/provenance 部分本轮未取证；graph runtime 属 OVER-ENGINEERING RISK。
冲突记录：无（但 interrupt 的"重放"语义与 MarketPulse 的幂等/归因要求存在潜在紧张关系，记录为研究观察）。
```

---

### 3.6 [额外] OpenAI Agents SDK — Guardrails

#### 结构化 / 裁决边界

- `FACT` — 两类 guardrail："Input guardrails run on the initial user input; Output guardrails run on the final agent output"；输入护栏只在链上**第一个** agent 运行，输出护栏只在**最后一个** agent 运行。（S23）
- `FACT` — tripwire 即 fail-closed："The runner **immediately raises** an `InputGuardrailTripwireTriggered` or `OutputGuardrailTripwireTriggered` exception and **halts agent execution**."；检查点为 `.tripwire_triggered` 属性；tool 级对应 `ToolInputGuardrailTripwireTriggered` / `ToolOutputGuardrailTripwireTriggered`。（S23）
- `FACT` — 输入护栏可配 `run_in_parallel`：默认并行（低延迟，但"the agent may have already consumed tokens and executed tools before being cancelled"）；`run_in_parallel=False` 为阻塞式 —— "**Blocking execution guarantees that the expensive model does not start**"。输出护栏**不支持**该参数（"always run after the agent completes"）。（S23）
- `FACT` — 结果可留证：`GuardrailFunctionOutput` 包入 `InputGuardrailResult` / `OutputGuardrailResult`；异常暴露 `guardrail_result`，且 `exception.run_data.input_guardrail_results` / `output_guardrail_results` 保留失败前已完成的全部结果（含触发者）。（S23）

#### Failure Semantics / Complexity

- `FACT` — 失败语义为**强类型、fail-closed、可留痕**（异常 + 结果列表）。（S23）
- `INFERENCE` — 该模式约束的是 **LLM run 的生命周期**，不是金融 authority；对 MarketPulse 而言其价值是"如何把'模型输出不合格'变成一条强制中断且可审计的路径"这一**形状参考**。引入 SDK 本身不解决 MarketPulse 的任何真实 gap（MarketPulse 的 DecisionValidator 已在**经济副作用之前**完成该角色）。

#### Evidence Record

```text
Project / Framework: OpenAI Agents SDK (Guardrails)
Claim: input/output guardrails 通过 tripwire 触发强类型异常并立即中止 agent 执行；输入护栏支持 blocking 模式以保证昂贵模型根本不启动；护栏结果与失败原因通过 guardrail_result / run_data.*_guardrail_results 留痕。
FACT / INFERENCE: FACT（引号部分）；"对 MarketPulse 无新增 gap 覆盖"为 INFERENCE
Official Source: S23 openai.github.io/openai-agents-python/guardrails/
Repository / Module: openai/openai-agents-python（GuardrailFunctionOutput、InputGuardrailResult、OutputGuardrailResult、tripwire 异常族）
Version / Commit / Date: 页面未标注版本 ⇒ NOT VERIFIED；抓取日 2026-09-14
Evidence Summary: 两类护栏的触发阶段、tripwire 检查点、异常与中止语义、并行 vs 阻塞执行模式差异、结果留痕结构。
Relevance to MarketPulse: 提供"输出不合格 ⇒ 强制中断 + 可审计"的成熟形状（对应 CP §7 "stale/invalid/provider-failed AI 不产生经济副作用" 的外部同形强化）；但不解决 Integrated Runtime Host、live handoff、Forward Outcome Calculator、experiment identity 等真实 gap ⇒ 不构成引入理由。
冲突记录：无。
```

---

### 3.7 [额外] Langfuse（Datasets + Experiments）

#### 结构化 / 实验边界

- `FACT` — 提供 dataset 与 experiment runner："Experiments via SDK are used to programmatically loop your applications or prompts through a dataset and optionally apply Evaluation Methods to the results."；dataset 可托管于 Langfuse 或本地。（S24）
- `FACT` — runner 自动处理："**Concurrent execution** of tasks with configurable limits；**Automatic tracing** of all executions for observability；**Flexible evaluation** with both item-level and run-level evaluators；**Error isolation so individual failures don't stop the experiment**；Dataset integration for easy comparison and tracking"。（S24）
- `FACT` — **实验身份**存在：`ExperimentResult` 含 `experiment_id`（"For Langfuse datasets, this matches the dataset run ID. For local experiments, this is a stable SDK-generated identifier for the run."）、可选的 `dataset_run_id` / `dataset_run_url`、`run_name`、`run_evaluations`（"aggregate evaluation results computed across all items"）。（S24）
- `FACT` — dataset 版本语义有限："Experiments always run on the latest dataset version at experiment time. **Support for running experiments on specific dataset versions will be added to the SDK shortly.**"（S24）⇒ 固定 dataset 版本 = 目前 **NOT VERIFIED / 不可用**。
- `FACT` — 平台同时提供 Prompt Management 与 tracing（"Online Trace traces · sessions · agents · prompts"；"Integrate Prompt Management"）与 evaluation 流程（online/offline）。（S24）

#### Failure Semantics / Complexity

- `FACT` — "Error isolation so individual failures don't stop the experiment" = 单样本失败不终止整轮实验。（S24）
- `INFERENCE` — 对 MarketPulse 的 experimentability gap（CP §5：without-AI vs with-AI attribution = NOT PRESENT；model attribution = PARTIAL），Langfuse 给出了"item-level 评估 + run identity + run-level 聚合"的**成熟形状**；但它评估的是**模型输出质量**，不是**交易经济结果**（Expectancy/R-Multiple/MFE/MAE 等 CP §5 明确缺失的 per-opportunity outcome）。二者不可互替。

#### Evidence Record

```text
Project / Framework: Langfuse
Claim: 提供 dataset + experiment runner，含 item-level 与 run-level 评估、实验身份（experiment_id / dataset_run_id / run_name）、自动 tracing 与单样本错误隔离；dataset 版本固定目前不受支持（始终使用最新版本）。
FACT / INFERENCE: FACT（引号部分）；"可作为 experimentability 的形状参考但不能替代经济结果计算"为 INFERENCE
Official Source: S24 docs.langfuse.com/ 概览；langfuse.com/docs/evaluation/get-started/offline；langfuse.com/docs/datasets/python-cookbook；python.reference.langfuse.com/langfuse/experiment
Repository / Module: langfuse（`langfuse.run_experiment`、`dataset.run_experiment`、`ExperimentResult`、`Evaluation`、dataset items/versions、prompt management）
Version / Commit / Date: 页面未标注版本 ⇒ NOT VERIFIED；抓取日 2026-09-14
Evidence Summary: runner 自动职责清单、实验身份字段与语义、评估分层、错误隔离、dataset 版本限制、平台 tracing/prompt 能力。
Relevance to MarketPulse: 直接对应 CP §6 gap "当前没有 without-AI / with-AI treatment identity、paired assignment 或 baseline provenance" 的**身份与配对**维度（实验 arm 命名、run 身份、item 级配对、单样本隔离）；其领域是 LLM 输出评估而非交易期望值，故不能覆盖 Forward Outcome / Expectancy gap。
冲突记录：无。
```

---

## 4. Cross-system Patterns

> 以下是从 §2/§3 官方证据中提取的**反复出现的成熟模式**。按任务要求：**不得**直接把模式等同于 MarketPulse Recommendation。每条给出证据出处与"是否已在 CP 中具备"的对照（对照本身是 FACT 引用 CP，判定为 INFERENCE）。

### P1 — 决策层产出值对象，执行层产出命令（FACT，5/5 trading systems 有对应物）

- 证据：LEAN `Insight`（signal 值对象）→ `PortfolioTarget` → Execution（S9）；Hummingbot `ExecutorAction`（S5/S6）；Freqtrade 回调返回值（S7）；vn.py `OrderRequest`（S13/S14）；Nautilus `Signal` 数据面 vs order command（S2/S3）。
- 对照 CP：MarketPulse 已有同形分层（`AIAnalysis` → 程序化 `TradePlan` → caller 创建 `ExecutionIntent` → `PaperExecutionService`，CP §2）。
- `INFERENCE`：该模式 **已被 MarketPulse 满足**；其价值是交叉验证 CP 的既有形状，而非引入新机制。

### P2 — 决策与执行之间存在"验证/调整"层（FACT，但**位置与权限差异极大**）

- Nautilus：**结构性** engine 组件，位于 submit+modify 路径（S2）。
- LEAN：**可插拔模型链**，会 *adjust* targets（可减也可加风险）（S10）。
- Freqtrade：**全局/单对 lock**，只锁 entries（S8）。
- vn.py：**可选 app，monkey-patch façade**（S14）。
- Hummingbot：**未见**（UNKNOWN，S5/S6）。
- `INFERENCE`：成熟系统普遍承认"需要一个 gate"，但**没有任何一个**把 gate 定义为"只做 veto、且必须是不可绕过的结构性组件"。MarketPulse 的 `SystemRiskGate`（CP §3：构造参数注入 + G4-wired 风险增加路径 veto）在该维度上比本轮全部候选**更强**。差距表现为：Nautilus 允许 `RiskEngineConfig` bypass；vn.py 允许绕过 patch；LEAN 的 risk 层被允许增加风险。

### P3 — 风险减少动作与风险增加动作被区别对待（FACT，3/5）

- Nautilus：`TradingState.REDUCING` —— cancels 恒通过，仅接受不增加敞口的 submit/modify；`REDUCE_ONLY_WOULD_INCREASE_POSITION` 为独立 reason code（S2）。
- LEAN：`order_by_margin_impact()` —— "position reducing orders are executed first"（S10）。
- Freqtrade：Protections 只锁 entries，"after exiting" 才有 cooldown ⇒ exits/stoploss 不受锁（S8）。
- 反面证据：Freqtrade `confirm_trade_exit()` **可以阻止 stoploss exit**，官方标注为会造成重大亏损的危险用法（S7）。
- 对照 CP：MarketPulse 要求 "Risk-reducing exit 在 Pause/SafeMode/Emergency 下保持可用"、"Protection 不等待 AI"、"stale/invalid AI 不产生经济副作用"（CP §7）。
- `INFERENCE`：该模式的成熟度上限是"把风险减少方向做成一等状态/排序规则"；MarketPulse 的相关约束**已在 CP 中显式存在**，且比 Freqtrade 更严格（后者允许策略否决保护性退出）。

### P4 — 会计与持仓真值归 engine 所有，决策层只读（FACT，4/5 明确，1/5 UNKNOWN）

- Nautilus：`Portfolio` 派生账户/持仓，`Cache` 存 orders/positions；strategy 只列 "Cache access / Portfolio access"（S1/S3）。
- vn.py：`OmsEngine` 为 in-memory single-source-of-truth；发送路径与状态更新**异步解耦**（S13）。
- Freqtrade：wallet 只读、`adjust_trade_position` 只能返回变更请求（S7）。
- LEAN：模块只读 `security.holdings`（S10）。
- Hummingbot：UNKNOWN（S5/S6）。
- 对照 CP：MarketPulse 的经济事实由 `PaperExecutionService._settle_order()` 在**同一 transaction** 内写 Fill/Account/Position/Ledger/Outbox（CP §3）。
- `INFERENCE`：模式普遍成立；且在**原子性**维度上 MarketPulse 强于本轮全部候选（Nautilus/vn.py 均为事件流式异步更新）。

### P5 — 失败语义**不统一**，且没有任何成熟系统实现 MarketPulse 的目标组合（FACT + INFERENCE）

- LEAN：**算法级 fail-stop**："stops the algorithm execution"（S11/S12）。
- Freqtrade：**逐回调 fail-safe-to-default**，异常回退到 `proposed_stake` / `proposed_rate` 并**继续交易**（S7）。
- Nautilus：状态门控（非 RUNNING 不派发 handler）+ `on_degrade` / `on_fault` hook；异常语义 UNKNOWN（S3）。
- Hummingbot / vn.py：UNKNOWN（S5/S6/S13/S14）。
- `INFERENCE`（关键观察）：**本轮未找到任何一个成熟系统同时满足** —— (a) advisory 失败 ⇒ 零经济副作用；(b) 持仓保护在 advisory 不可用时继续有效；(c) 风险减少退出在受限状态下仍可用。这三条组合是 MarketPulse 的**特异性不变量**，不是可照搬的行业模式。**该"未找到"属 UNKNOWN（absence of evidence），不得表述为"不存在"。**

### P6 — 订单/成交身份在**执行边界**强制，而非由决策层保证（FACT）

- Nautilus：`INVALID_CLIENT_ORDER_ID`、`ORDER_LIST_INCOMPLETE`、`ORDER_ALREADY_EXISTS` 类 reason code 位于 RiskEngine/ExecutionEngine（S2）。
- LEAN：`ORDER_ALREADY_EXISTS`、`ORDER_QUANTITY_ZERO`、`EXCEEDED_MAXIMUM_ORDERS` 位于 order error 层（S11）。
- Freqtrade：额外订单的计数与费用由框架处理（S7）。
- 对照 CP：MarketPulse 的 `fills` 每 order/intent 唯一、`ledger_entries` 每 Fill 唯一（CP §3）。
- `INFERENCE`：模式已被 MarketPulse 满足，且以 DB 唯一性约束实现，比框架级检查更强。

### P7 — 结构化输出的强制点分两层，**provider-native 层无法表达业务规则**（FACT）

- 层 1（provider 强制形状）：OpenAI `strict:true`（S15/S16）、PydanticAI `Native Output`（S17）、LangChain `ProviderStrategy`（S21）、LiteLLM 原生 json_schema（S20）。
- 层 2（客户端校验 + 重试）：PydanticAI `Tool/Prompted Output` + output validator、Instructor、LiteLLM `enable_json_schema_validation`、LangChain `ToolStrategy.handle_errors`（S17/S18/S20/S21）。
- 关键限制（FACT）：provider 层**不支持** `minimum`/`maximum`/`multipleOf`/`pattern`/`format`/`minItems`/`maxItems` 等关键字（S16）⇒ **价格关系、刻度、区间类业务规则不可能由 schema 强制**。
- `INFERENCE`：无论采用哪一层，**程序化 validator 仍然必需**；这与 MarketPulse 既有 `DecisionValidator` 的角色一致（CP §4），属对既有设计的**独立支持性证据**，而非新增需求。

### P8 — 重试预算必须有界、可配置、可观测（FACT）

- PydanticAI：output retry 预算**默认 1**，可 `Agent(retries=...)` / per-tool `max_retries`（S17）。
- Instructor：官方按错误类型分档（validation 2–3、network 4、rate limit 5），要求 stop condition，并保留 `failed_attempts` 历史（S18）。
- LangChain：`handle_errors` 默认 True（模板化回注），False ⇒ 异常传播（S21）。
- Nautilus：submit/modify 速率限制（S2）。
- `INFERENCE`：**stale 语义在本轮全部 LLM 候选中均不存在**（无任何"结果已过期"概念）。MarketPulse 的 `state_version` stale 检查（CP §4）在外部候选中**没有对应物** ⇒ 该能力是 MarketPulse 自有的必要补充，无法从外部借鉴。

### P9 — "执行前外部裁决点"作为框架原语存在，但默认裁决者是人（FACT）

- LangGraph `interrupt()`：官方推荐用于"关键动作（API calls、database changes、**financial transactions**）"前的批准（S22）。
- OpenAI Agents SDK guardrails：tripwire ⇒ 立即中止 run；blocking 模式保证昂贵模型不启动（S23）。
- `INFERENCE`：形状（deterministic gate before action）与 MarketPulse 同族，但二者引入的是 **agent/graph runtime**；对 MarketPulse 而言属 OVER-ENGINEERING RISK（§8）。

### P10 — 交易框架提供"确定性重放"，但**不提供 treatment/control 身份**；实验身份来自 LLM 评估工具（FACT + INFERENCE）

- 交易侧：Nautilus 单线程 core 提供 backtest-live parity（S1）；MarketPulse 已有 G5 deterministic replay（CP §5）。
- LLM 侧：Langfuse 提供 `experiment_id` / `dataset_run_id` / run-level 聚合 / 单样本错误隔离（S24）。
- `INFERENCE`：**没有任何本轮候选**同时提供"同一 opportunity/evidence 上的 with-AI vs without-AI 配对 + 经济结果比较"。交易框架给重放不给 arm；LLM 工具给 arm 不给经济结果。⚠️ 精确边界：Langfuse 等**确实**提供了 experiment identity / run identity / item-level 配对 / 单样本隔离等**可复用的子模式**（S24，见 E1/E2）；缺的是这些身份与"同一机会的经济反事实 + forward outcome + expectancy"的**组合**，因此**不得**概括为"没有任何候选提供 with-AI vs without-AI 实验身份"。CP §5 的 `without-AI vs with-AI attribution = NOT PRESENT` 因此是一个**跨领域缺口**，需由 MarketPulse 侧定义实验身份才能闭合（本任务不给实现）。该结论的成立范围限于本轮候选集，属 absence of evidence（见 GAP-09）。

---

## 5. AI Placement Evidence Matrix

### 5.1 评分口径（必须先声明方向性，否则数字不可解释）

| 类 | Dimensions | 方向 |
| --- | --- | --- |
| **收益型**（越高越好） | Edge Potential、Experimental Isolation、Failure Safety、Replayability、Explainability、Current Architecture Fit | 5 = 最有利 |
| **风险型**（越高越差） | Authority Risk、Latency Sensitivity、Call Frequency / Cost、Implementation Complexity、Over-engineering Risk | 5 = 风险/成本最高 |

- 每个分数后的括号内为**理由**；理由中的 `CP` 引用均来自随任务提供的 Context Pack。
- 全部评分为 **INFERENCE**：它们由本模型基于 CP 事实与 §2/§3 的官方证据合成，**不是**官方来源的陈述，也**不是**对 MarketPulse 的架构裁决。
- 对每个 Placement 单列一张 11 行表；末尾给汇总矩阵。
- **方向性修正（PRE-01A-DS1-FIX-01）**：原 §5.4 / §5.5 / §5.6 的 `Call Frequency / Cost` 分数是在与上表**相反**的方向上给出的（数值越高 = 成本越低），与本节声明的"5 = 风险/成本最高"冲突。修正后统一按 `1 = 最低` / `5 = 最高`；三个修正值与原分满足 `6 − x`，即原评分**理由**（C / D = 低、E = 最高、A / B = 中）在正确口径下被保留，而**不是**为了维持原排序。A、B 两列的该维度分数无需变动。

---

### 5.2 Placement A — Opportunity Qualification

`Formal Opportunity → AI → accept / reject / wait`

| Dimension | Score | 理由 |
| --- | --- | --- |
| Edge Potential | 4 | 在"已成立机会"上做二次筛选是最经典的 edge 杠杆（提高 precision、过滤伪突破）。但 CP 显示 Formal Opportunity 已由 `edge.capture.qualifies()` 在确定性身份/版本一致的前提下判定（CP §2），AI 只能在既定证据之上增量判断，不能创造证据中不存在的信息。 |
| Experimental Isolation | 3 | 可做 A/B，但被拒绝的样本若不进入下游即**没有可观测 outcome**；要证明"AI 的拒绝是对的"必须记录反事实（counterfactual decision recording），而 CP §5 明确 `without-AI vs with-AI attribution = NOT PRESENT`。因此可隔离但不可自证。 |
| Authority Risk | 4 | 高。CP §2 明确规定 "AI、Risk、Trade 和 reference-data availability 都不是 Opportunity admission 条件"。让 AI 参与 admission 等于修改 Formal Opportunity 的准入语义，而 opportunity identity 是 downstream evidence/attribution 的派生根（CP §5）。 |
| Failure Safety | 3 | fail-closed 极易实现（AI 失败 ⇒ 视作 reject），但"拒绝"会把失败从"坏交易"转化为"漏掉的机会 + 样本选择偏置"，属**静默失败**；这是本 Placement 特有的安全悖论。 |
| Latency Sensitivity | 3 | admission 位于 capture 时点（G2 tick 路径），同步调用会给 ingest 加延迟；CP §2 显示当前 live 路径尚无 accepted host handoff，因此延迟无法实测。 |
| Call Frequency / Cost | 3 | 频率 = Formal BREAKOUT_RETEST 机会率（每个 Formal Opportunity 一次）。CP §5 显示 `BREAKOUT_RETEST` 是当前唯一获准 family，频率可控但不最低。 |
| Replayability | 3 | 输入侧理想（immutable/hash-bound evidence，CP §5 `evidence snapshot = READY`），但重放时"是否被 admission 接受"必须有 as-admitted 记录才可复现，否则同一 evidence 在不同 AI 版本下会改变进入下游的集合。 |
| Explainability | 3 | AI 的 reason 可随 decision record 落库，但被抑制机会的归因链（Plan/Risk/Execution/Economic 全缺席）无法解释，且 CP §5 指出 attribution recorder 是 caller 可选注入。 |
| Current Architecture Fit | 2 | 低。它触碰 CP §7 "Do not redesign" 清单中的 Opportunity identity 与 admission；CP §6 亦将其列为既有确定性能力。 |
| Implementation Complexity | 4 | 高：需要新 hook + 反事实记录 + 新评估口径，并要重新定义"被拒绝机会"的持久语义。 |
| Over-engineering Risk | 4 | 高：在最高扇出点引入 AI 依赖，且与既有确定性准入契约冲突。 |

---

### 5.3 Placement B — Market Context Interpretation

`Immutable Evidence → AI interpretation → Structured Market Context → existing downstream logic`

| Dimension | Score | 理由 |
| --- | --- | --- |
| Edge Potential | 3 | 中。可产出 regime/liquidity/structure 类解读供下游确定性逻辑使用；但 CP §4 显示 `DecisionSnapshot` 已含 frozen market context、BBO、rolling features/structure/derivatives、timeline 与 strategy contexts —— 即"上下文"大部分已存在。增量来自**语义标注**而非新数据，且没有既定的下游消费者，edge 属间接且未证。 |
| Experimental Isolation | 4 | 高。输入是不可变证据，输出是纯派生产物，可完全离线、无经济副作用地计算与比较；这是五者中最容易做"同一 evidence 上 with/without 解读"的形态。 |
| Authority Risk | 2 | 低（按本 Placement 的既定边界：下游 deterministic logic 不变）。AI 只输出派生结构，不进入 veto 路径。⚠️ INFERENCE 条件：若该结构被写入 `DecisionSnapshot` 并被 validator 当硬判据使用，authority risk 会升至 3。 |
| Failure Safety | 5 | 最高。失败 = 缺少一份注解；不产生经济副作用，无任何组件等待它（可异步/可选消费）。 |
| Latency Sensitivity | 2 | 低。可在冻结证据之后离线/异步计算，不位于 tick 或 decision 的关键路径上。 |
| Call Frequency / Cost | 3 | 每个 evidence revision 一次（CP §5 显示 evidence 以 immutable/versioned/hash-bound 方式产生），若一次机会有多份 revision，调用次数可高于 decision 次数。 |
| Replayability | 5 | 最高。输入 = 已 immutable/hash/version 化的 evidence（CP §5 `evidence snapshot = READY`），输出 = 纯派生物，二者均可 frozen replay 并逐条比对。 |
| Explainability | 4 | 高。解读文本与其输入证据同源可查，provenance 清晰；扣分因"解读 → 最终经济结果"的链路仍是间接的，无法单独归因。 |
| Current Architecture Fit | 3 | 中。不违反任何 CP §7 约束（不改 identity/authority），但 CP §4 显示目前**不存在**接受"Structured Market Context"的既有契约，属新增能力面。 |
| Implementation Complexity | 2 | 低–中。一次 provider 调用 + 一个持久化派生件；无 identity/authority 变更。若要避免 AI 结果污染 `DecisionSnapshot` 的 frozen 语义，仍需明确其存放位置（INFERENCE：这是设计问题，不是本任务可决定的）。 |
| Over-engineering Risk | 3 | 中。最大风险是产出一个**无人消费的 context schema**（投机性抽象）—— 这正是 §13 所针对的膨胀形态。 |

---

### 5.4 Placement C — Trade Decision

`DecisionSnapshot → AI → LONG_BIAS / SHORT_BIAS / WAIT`（CP §4 显示此 contract **已存在**）

| Dimension | Score | 理由 |
| --- | --- | --- |
| Edge Potential | 4 | 高。这是 advisory 模型对确定性特征做语义整合的**规范位置**；且是五者中唯一拥有 **accepted、已结构化、已 validator 化**契约的位置（CP §4）。其上限受限于证据集本身（AI 不能生成新证据），故不评 5。 |
| Experimental Isolation | 4 | 高。CP §4/§5 显示 frozen `DecisionSnapshotRecord.payload`、`AIDecisionRecord`（含 model/status/prompt/schema version/raw response/error）、`TradePlanRecord` 关联链均已存在；G5 replay 已能用 recorded provider 走通 decision→plan→risk→execution（CP §2）。缺的是 treatment/control 身份（CP §5 `NOT PRESENT`），故不评 5。 |
| Authority Risk | 2 | 低。CP §4 明确：provider 只拿 frozen snapshot + prompt，"没有 repository、Risk 或 Execution handle"；prompt 禁止 tool use 与直接交易；`SHORT_BIAS` 只持久化不执行；notional 由程序按 min(equity, single-order cap, AI suggestion) 生成。 |
| Failure Safety | 5 | 最高（CP §7 直接支持）：stale/invalid/provider-failed AI ⇒ 不产生经济副作用；Risk/Protection 不等待 AI；`VALID + LONG_BIAS` 才可能生成 plan。 |
| Latency Sensitivity | 2 | 低。位于 SETUP 决策边界，不在 tick/ingest 路径上；CP §2 显示该边界当前尚未接入 live 连续 host（故当前无实际延迟暴露）。 |
| Call Frequency / Cost | 2 | 低。每个 SETUP/Formal Opportunity 至多一次决策调用，是"每个机会一次"的最小充分调用量；与 D 同属五者中最低档（E 的 position×时间 频率高于此；A 位于 admission 上游，调用数 ≥ 决策数）。 |
| Replayability | 5 | 最高。CP §4/§5：`decision_snapshots` 冻结 persistent + `ai_decisions` 记录 prompt/response/model/status；G5 deterministic replay 已在生产源码中调用 `process_setup()`（CP §2）。 |
| Explainability | 4 | 高。`ai_decisions` 保存 status、model、prompt/schema version、raw prompt、raw response、error（CP §4）。扣分因 CP §4 明确 `ai_decisions` **没有** provider identity、provider request/response ID、latency、token、cost、experiment-arm 字段。 |
| Current Architecture Fit | 5 | 最高。contract 已 accepted、provider-neutral、无新增 authority；CP §7 的 must-preserve 清单无需改动。 |
| Implementation Complexity | 2 | 低（就 AI 侧而言）：无需新契约、无需新 authority，主要是 Real AI activation + host handoff + provenance 字段补齐。⚠️ CP §6 指出 "Integrated Runtime Host 不存在" 与 "live `Opportunity → DecisionSnapshot → G3Workflow` handoff 不存在"，**该缺口对所有五个 Placement 同等存在**，不是本 Placement 特有。 |
| Over-engineering Risk | 1 | 最低。不引入任何新抽象。 |

---

### 5.5 Placement D — Trade Plan Generation

AI 直接提出 `entry / stop / target / position percentage / invalidation`

| Dimension | Score | 理由 |
| --- | --- | --- |
| Edge Potential | 2 | 低。CP §4 显示 `AIAnalysis` **已经包含** entry zone、stop loss、take profit、invalidation、confidence、suggested position percentage；CP §2 显示 `TradePlanManager.from_analysis()` 已把这些确定性地转成 plan 并做 notional cap。把 plan 权交给 AI **重复既有能力**，不新增信息。 |
| Experimental Isolation | 3 | 中。可比较，但 plan 参数（尺寸/止损位置）与"决策好坏"混淆，无法把差异归因到单一变量；需要参数级归因，而 CP §5 显示 model attribution 仅 PARTIAL。 |
| Authority Risk | 3 | 中–高。plan 是数值关系与暴露上限所在：CP §7 明确 `stop_loss` 是**唯一** machine-enforceable hard price invalidation，且 notional 由程序 caps。让 AI 持有 plan 权会把数值幻觉直接放在 gate 之前。 |
| Failure Safety | 3 | 中。可以校验（价格关系、必需字段），但**形状正确而经济上错误**的 plan 能通过；且尺寸错误会与 capacity/risk policy 交互。 |
| Latency Sensitivity | 2 | 低。与 C 同一边界。 |
| Call Frequency / Cost | 2 | 低。与 decision 1:1（每个 SETUP 决策至多一次），与 C 同属五者中最低档。 |
| Replayability | 4 | 中–高。`trade_plans`/`trade_plan_scenarios` 已持久化（CP §3），G5 replay 存在；但 CP §2 显示生成者目前是**确定性** `TradePlanManager`，改由 AI 生成会分叉该契约的 replay 语义。 |
| Explainability | 3 | 中。"为什么这个尺寸/止损"与执行结果纠缠，归因清晰度低于 C（C 的 status/direction 有明确 validator 语义）。 |
| Current Architecture Fit | 2 | 低。与 CP §2 的 `AIAnalysis → deterministic TradePlanManager` 及 CP §7 "Do not redesign: TradePlan" 直接冲突。 |
| Implementation Complexity | 4 | 高。需要新的数值/关系校验层、风险重叠检查、replay 与 attribution 变更。 |
| Over-engineering Risk | 5 | 最高。用概率性组件替换一个已存在、已 cap、可确定重放的确定性能力，且无证据显示增益。 |

---

### 5.6 Placement E — Position Re-evaluation

`PositionReviewProvider → HOLD / ADD / REDUCE / CLOSE / … → deterministic validation / execution`（CP §4 显示此 contract **已存在**）

| Dimension | Score | 理由 |
| --- | --- | --- |
| Edge Potential | 4 | 高。持仓生命周期（加仓时机、减仓/退出判定）通常是期望值的主要来源之一；AI 可在此结合更长的上下文。⚠️ 此评分为 INFERENCE，**无任何证据**表明实际存在增量 edge。 |
| Experimental Isolation | 2 | 低。反事实是"同一持仓在无 AI 下会怎么做"，属路径依赖、顺序依赖、样本不可交换的比较；CP §5 显示 `forward outcome = PARTIAL`（Accepted Calculator 不存在）、family aggregation/Expectancy 未实现（CP §6）⇒ 目前**无法闭合评估回路**。 |
| Authority Risk | 3 | 中。CP §4 已给出强边界：ADD 需再过 `SystemRiskGate` 与 Execution；REDUCE/CLOSE 走程序化 risk-reducing exit；plan update 走 schema/business validation + expected-current CAS；timeout/error/invalid ⇒ HOLD 零副作用。扣分因动作面大（9 个 advisory actions），且需要 action-time BBO 重新获取。 |
| Failure Safety | 5 | 最高（CP §4 逐条支持）：timeout/provider error/invalid business output ⇒ HOLD、零经济副作用；"既有 SL/TP 不因 AI 失败、延迟或不可用而失效"；mutation transaction 内再次锁定并重验。 |
| Latency Sensitivity | 3 | 中。CP §4 要求 action 前重新取得 BBO、provider 后重验 state version/active plan/position lifecycle，且 position 处于实时市场风险中。 |
| Call Frequency / Cost | 5 | 最高。频率 = 未平仓头寸数 × 复核节奏（随持仓时间线性增长），与机会数无关；成本压力是五者中最大。 |
| Replayability | 3 | 中。基于 DecisionSnapshot 可重放，但持仓级状态（active plan/version、trade lifecycle）与重新获取的 BBO 使其比 C 更难做到逐位一致；且 CP §6 显示 outcome 计算缺失，重放"能跑"但"不可评估"。 |
| Explainability | 3 | 中。与 C 同源 `ai_decisions` provenance，但 CP §4 指出 G4 `_persist_decision()` 写入 `raw_prompt=""` ⇒ **恰在此路径上 prompt provenance 不完整**。 |
| Current Architecture Fit | 4 | 中–高。G4 contract 与 authority 路由已定义（CP §4），但尚未启用；CP §3 显示 `PositionReviewProvider` 属 advisory，且 `g4/reevaluation.py` 已验证过 ADD/REDUCE/CLOSE 路径。 |
| Implementation Complexity | 3 | 中。契约已在，复杂度集中在调用调度、成本控制与评估口径，而非 authority。 |
| Over-engineering Risk | 3 | 中。风险在于"为未证收益的路径增加持续的模型调用与运维面"。 |

---

### 5.7 汇总矩阵（含方向归一后的合计）

`adj = Σ(收益型 6 项原始分) + Σ(风险型 5 项 (6 − 原始分))`（纯算术合成，仅供排序，**不构成裁决**）

| Dimension | A | B | C | D | E |
| --- | --- | --- | --- | --- | --- |
| Edge Potential | 4 | 3 | 4 | 2 | 4 |
| Experimental Isolation | 3 | 4 | 4 | 3 | 2 |
| Failure Safety | 3 | 5 | 5 | 3 | 5 |
| Replayability | 3 | 5 | 5 | 4 | 3 |
| Explainability | 3 | 4 | 4 | 3 | 3 |
| Current Architecture Fit | 2 | 3 | 5 | 2 | 4 |
| Authority Risk | 4 | 2 | 2 | 3 | 3 |
| Latency Sensitivity | 3 | 2 | 2 | 2 | 3 |
| Call Frequency / Cost | 3 | 3 | 2 | 2 | 5 |
| Implementation Complexity | 4 | 2 | 2 | 4 | 3 |
| Over-engineering Risk | 4 | 3 | 1 | 5 | 3 |
| **adj 合计（排序用）** | **30** | **42** | **48** | **31** | **34** |

`INFERENCE` — 该表的数字是本模型自建的合成指标（自定义权重均为 1），**不可**当作外部事实引用；其唯一用途是让 §9 的排序透明可复算。

`修正记录（PRE-01A-DS1-FIX-01）` — 本表已按 §5.1 修正后的 `Call Frequency / Cost`（C `4→2`、D `4→2`、E `1→5`）重算，每列均按 `adj = Σ(收益型 6 项原始分) + Σ(6 − 风险型 5 项原始分)` 逐项复算，无一项沿用旧总分。重算同时发现并修正一处**算术错误**：A 列旧合计 `32` 与公式不符，按公式应为 `30`（差额 2 恰好等于 A 列 `Over-engineering Risk` = 4 未做 `(6 − x)` 而归一、被直接计入 4 而非 2 的差额 —— 此成因说明为 `INFERENCE`，不影响修正后的数值）。

---

## 6. Experimentability Evidence

> 本节只做 **Reference Research**。**不为 MarketPulse 设计正式 Experiment implementation。**

### 6.1 目标问题的现状（来自 CP 的对照锚点）

- `FACT`（CP §5）：`without-AI vs with-AI attribution = NOT PRESENT` —— "没有 treatment/control assignment、AI-disabled decision provenance、paired baseline identity 或可比较的已计算 forward outcomes"。
- `FACT`（CP §5）：`decision provenance = PARTIAL`（DecisionSnapshot/AI decision/plan/attribution primitives 已存在；live handoff 不存在；attribution recorder 为可选注入；G4 prompt 不完整保存）。
- `FACT`（CP §5）：`forward outcome = PARTIAL`（contract/schema/append writer 已存在，Calculator 不存在）。
- `FACT`（CP §6）：`SE-02D` family aggregation / Expectancy 未实现；无 Accepted per-opportunity MFE/MAE/forward return。

### 6.2 可借鉴的成熟模式（逐条给来源与适用边界）

| # | 模式 | 官方证据 | 可复用内核 | 边界 / 缺口 |
| --- | --- | --- | --- | --- |
| E1 | **Item-level 配对评估 + run identity** | Langfuse：`dataset.run_experiment(name=..., run_name=..., task=..., evaluators=[...])`；`ExperimentResult.experiment_id`（dataset 场景等于 dataset run ID，本地场景为稳定 SDK 生成的 run 标识）、`dataset_run_id`、`dataset_run_url`、`run_evaluations`（S24） | 实验需要**显式 run 身份 + 每条样本的独立结果**，而不是只留一个聚合数 | Langfuse 评估的是**模型输出质量**，不含经济结果（Expectancy / R-Multiple / MFE / MAE 在 Langfuse 语义中不存在）⇒ 不可替代 CP §6 的 outcome gap |
| E2 | **单样本错误隔离** | Langfuse runner："Error isolation so individual failures don't stop the experiment"（S24） | 一个样本失败不应作废整轮实验（避免 CP §1 类"整批失败"式结论失真） | 与交易无关，仅流程语义 |
| E3 | **dataset 版本固定** | Langfuse："Experiments always run on the latest dataset version at experiment time. Support for running experiments on specific dataset versions will be added to the SDK shortly."（S24） | 反面经验：若不能钉住输入版本，"同实验"不可严格复现 | 目前**无**官方可用方案 ⇒ 若 MarketPulse 需要"同 evidence 同 experiment"，必须自带版本钉定能力（本任务不给实现） |
| E4 | **失败尝试历史作为 provenance** | Instructor：`InstructorRetryException.n_attempts` / `.failed_attempts`（每此尝试的异常）；官方要求"缺失的度量必须保持 unknown 而不是报 0"（S18） | provenance 应记录**尝试序列**与失败原因，而非最终状态 | 属 LLM 调用层；与市场 outcome 无关 |
| E5 | **有界重试预算默认 1（少即是好）** | PydanticAI：output retry 预算默认 `1`（S17）；Instructor：validation 2–3 次并强制 stop condition（S18） | "重试"必须显式有界，否则实验的"一次决策"语义被污染 | — |
| E6 | **确定性重放 / backtest-live parity** | Nautilus：单线程 core、"deterministic event ordering and helps maintain backtest-live parity"（S1） | 同一事件序列应产生同一定序 | 只给**重放**，不给 arm 分配；CP §5 显示 MarketPulse 已有 G5 deterministic replay |
| E7 | **Interrupt/approval 作为显式状态 + 持久化** | LangGraph：`interrupt()` 由 persistence layer 保存状态并无限等待，`thread_id` 为持久游标，`Command(resume=...)` 恢复（S22） | "决策—裁决—执行"之间可以有一个**可持久化、可恢复的中间状态** | 恢复会"restart the entire node from the beginning"（S22）⇒ 中介状态前后的副作用必须可重放安全；默认裁决者是**人** |
| E8 | **Guardrail 结果留痕 + 强类型中止** | OpenAI Agents SDK：`guardrail_result`、`run_data.input_guardrail_results` / `output_guardrail_results` 保留失败前全部结果（S23） | "为什么这次被拦下"应作为可查询记录，随 run 一起产出 | 约束 LLM run 生命周期，不含金融 authority |
| E9 | **模型/提示版本与 trace 关联** | `NOT VERIFIED`（LangSmith 官方页本轮未抓取）；Langfuse 提供 Prompt Management 与 tracing 能力声明，但**未取证到 arm 级关联细节**（S24 仅为能力清单） | 需要把 model/prompt/schema 版本与每次决策关联 | CP §4 显示 MarketPulse **已经**保存 config/prompt/schema versions 与 model ⇒ 该维度已有基础，缺的是 provider identity/request ID/latency/token/cost/arm |
| E10 | **Paper/shadow 环境作为无风险运行臂** | Nautilus：backtest/sandbox/live 共享同一 `NautilusKernel`（S1）；Freqtrade：dry-run 语义见 S7 文档线；Hummingbot：`Executor` 可经 API 直接创建以做无 bot 验证（S5） | "同一代码、不同环境"是成熟做法的通用前提 | `FACT`（CP §7）：MarketPulse **已经是 Paper Trading only** ⇒ "无风险"已具备；**但"Paper 臂" ≠ "without-AI 臂"**：absence 的是**第二个策略臂（同一 evidence 上不同 policy）**，不是环境 |

### 6.3 明确未被外部证据覆盖的部分（避免过度外推）

- `INFERENCE` — 本轮**没有任何候选**闭合完整的 MarketPulse with-AI vs without-AI **交易实验回路**。部分候选**确实**提供了可复用的**子模式**：实验/运行身份与 item 级配对、单样本隔离（Langfuse，S24；见 E1/E2）、失败尝试历史（Instructor，S18；见 E4）、guardrail 结果留痕（Agents SDK，S23；见 E8）。但**没有任何候选**同时给出下列组合：`experiment identity` + `same-opportunity economic counterfactual` + `forward outcome` + `expectancy`。故本结论的成立范围仅是"本轮候选集中未观察到"，保留 **absence of evidence ≠ evidence of absence**（见 P10、GAP-09）。
- `INFERENCE` — 本轮**没有任何候选**提供 LLM 层的 **stale 结果**语义（见 P8）。
- `INFERENCE` — 因此 CP §5 的两个缺口（treatment/control identity；paired baseline identity）**无法从成熟系统直接复用**，只能借用其**身份与留痕的形状**（E1/E4/E8）与**重放前提**（E6/E10）。本任务不给出实现方案。

---

## 7. Reuse Classification

分类语义（按任务 §12）：`DIRECT REUSE` / `ADAPT` / `REFERENCE ONLY` / `BUILD`；标签：`RELEVANT` / `OPTIONAL` / `OVER-ENGINEERING RISK`。

| Candidate / Pattern | Classification | MarketPulse Gap Addressed | Complexity | Evidence |
| --- | --- | --- | --- | --- |
| 决策值对象 → 程序化 sizing → 风险调整 → 唯一执行者（LEAN Insight/PortfolioTarget/RiskManagement/Execution） | `REFERENCE ONLY` + `RELEVANT` | 不新增 gap；**交叉验证** CP §2 既有分层形状 | 无（不引入） | S9、S10 |
| 结构性 pre-trade gate 位于 submit+modify 路径，拒绝为带 reason code 的显式事件（Nautilus `RiskEngine` / `OrderDenied`） | `REFERENCE ONLY` + `RELEVANT` | 支持 CP §3 `SystemRiskGate` 的既有形态；"拒绝必须可解释"的成熟做法 | 无（不引入） | S2 |
| 风险减少/增加的方向性区分（`TradingState.REDUCING`：cancel 恒通过、仅接受不增敞口） | `ADAPT` + `RELEVANT` | CP §7 "Risk-reducing exit 在 Pause/SafeMode/Emergency 下保持可用" 的外部先例（表达为显式状态而非分散判断） | 低（概念层；本任务不实现） | S2 |
| "锁风险增加方向、不锁退出"（Freqtrade Protections 仅锁 entries；CooldownPeriod 为 pair 级且绝不全局锁） | `REFERENCE ONLY` + `RELEVANT` | 同上；提供"保护不应阻断退出"的外部惯例句式 | 无 | S8 |
| 反面证据：策略可 veto stoploss exit（Freqtrade `confirm_trade_exit()` 警告） | `REFERENCE ONLY` + `RELEVANT` | 支持 CP §7 "Protection 不等待 AI"、AI-independent protection 的既有选择 | 无 | S7 |
| 反面证据：pre-trade gate 以 monkey-patch façade 接入（vn.py `patch_functions()`） | `REFERENCE ONLY` + `RELEVANT` | 支持"gate 必须是结构性不变量"的判断（对照 CP §3 构造参数注入） | 无 | S13、S14 |
| 反面证据：回调异常回退默认值并继续交易（Freqtrade `proposed_stake` / `proposed_rate` 回退） | `REFERENCE ONLY` + `RELEVANT` | 与 CP §7 "stale/invalid/failed AI 不产生经济副作用" 冲突 ⇒ 记录冲突，不改 MarketPulse | 无 | S7 |
| 反面证据：算法级 fail-stop（LEAN "stops the algorithm execution"） | `REFERENCE ONLY` + `RELEVANT` | 与"持仓保护不依赖 advisory 可用性"冲突 ⇒ 记录冲突 | 无 | S11、S12 |
| 发送路径与状态更新解耦（vn.py：同步 send + 异步 `OmsEngine` 事件更新） | `REFERENCE ONLY` + `RELEVANT` | 对照 CP §3 同 transaction 原子结算的更强保证 | 无 | S13 |
| 有限生命周期、自管 order 的执行单元（Hummingbot `Executor`：active → closed/failed） | `REFERENCE ONLY` + `RELEVANT` | 交叉验证 CP §2 "Plan 与 Intent 分离、Execution 由 caller 创建" 的形状 | 无 | S5、S6 |
| provider-native strict schema 强制（OpenAI `strict:true`；PydanticAI `Native Output`；LangChain `ProviderStrategy`） | `ADAPT` + `RELEVANT` | CP §6 "structured provider reliability"：**schema 必须落在受支持子集内**（全字段 required、`additionalProperties:false`、无 `min/max/pattern/format/minItems`、≤100 属性/≤5 层） | 低（schema 设计约束，无新依赖） | S15、S16、S17、S21 |
| refusal 为 schema 之外的分支（`refusal` 字段） | `ADAPT` + `RELEVANT` | CP §6 "structured provider reliability"：解析路径必须建模"拒绝"这一第三态 | 低 | S15 |
| 客户端业务校验 + 有界重试 + 失败历史（Instructor / PydanticAI output validator） | `ADAPT` + `RELEVANT` | CP §6 "structured provider reliability" + CP §5 provenance（`ai_decisions` 现无 attempt/latency/token/cost） | 中 | S17、S18 |
| validator 使用运行时上下文（Instructor `context=` 校验输出与源文本一致） | `REFERENCE ONLY` + `RELEVANT` | 同族强化 CP §4 既有 `DecisionValidator`（以 frozen snapshot 校验输出） | 无 | S18 |
| 重试预算默认极小且必须有 stop condition（PydanticAI 默认 1；Instructor 分档 + 强制 stop） | `ADAPT` + `RELEVANT` | 防"重试污染一次决策语义" | 低 | S17、S18 |
| typed fail-closed tripwire + 结果留痕（Agents SDK guardrails） | `REFERENCE ONLY` + `OPTIONAL` | authority safety 形状参考；MarketPulse 的 DecisionValidator 已在经济副作用之前承担该角色 | 无（SDK 不引入） | S23 |
| 执行前中断/批准作为持久化状态（LangGraph `interrupt()` + checkpointer） | `REFERENCE ONLY` + `OPTIONAL` | 形状参考（deterministic gate before action）；CP 未提出 human-in-the-loop 需求 | 无 | S22 |
| 实验身份 + item-level 配对 + run 级聚合 + 单样本隔离（Langfuse dataset/experiment） | `REFERENCE ONLY` + `RELEVANT`（**身份/配对形状**） | CP §6 "当前没有 without-AI / with-AI treatment identity、paired assignment 或 baseline provenance" —— 覆盖其**身份与配对**维度 | 若仅取形状：低；若引入平台：高（`OVER-ENGINEERING RISK`） | S24 |
| 确定性重放 / backtest-live parity（Nautilus 单线程 core；CP 已有 G5 replay） | `REFERENCE ONLY` + `RELEVANT` | CP §5 replayability 已 READY；用于确认"重放 ≠ 实验臂" | 无 | S1、S2 |
| 多 provider 自动 failover + 跨 provider 模型访问绕过（LiteLLM fallbacks / `enforce_fallback_model_access`） | `REFERENCE ONLY` + `OVER-ENGINEERING RISK` | **不覆盖任何 gap，直接冲突** CP §7 "单一 Primary Provider 边界，无自动 fallback/voting" | 高 | S19 |
| gateway/proxy 企业能力（spend logs、cooldowns、team/key 访问控制） | `REFERENCE ONLY` + `OVER-ENGINEERING RISK` | 无对应 gap | 高 | S19 |
| 完整 agent/graph runtime（PydanticAI Agent、LangGraph StateGraph/checkpointer） | `REFERENCE ONLY` + `OVER-ENGINEERING RISK` | 无对应 gap（CP §4 的 provider 契约为无工具单次调用；CP §7 要求 Modular Monolith、单一 Primary Provider） | 高 | S17、S21、S22 |
| **任何** Trading Framework 本体（Nautilus / Hummingbot / Freqtrade / LEAN / VeighNa）作为依赖 | `REFERENCE ONLY` + `OVER-ENGINEERING RISK` | 无一覆盖 Real AI activation / structured provider reliability / provenance / experimentability / live handoff / authority safety 的**缺口**（CP §6 的 REAL GAP 清单） | 极高 | S1–S14 |

`INFERENCE` — 本表**不含**任何 `DIRECT REUSE` 或 `BUILD` 项：本轮所有候选要么已被 MarketPulse 满足（⇒ 交叉验证），要么只提供 schema/校验/留痕层面的**约束或形状**（⇒ ADAPT，且均属"未来激活 Real AI 时的设计约束"，本任务不实施），要么构成冲突或膨胀风险（⇒ REFERENCE ONLY / OVER-ENGINEERING RISK）。（Reuse Classification 是"外部 `FACT` + MarketPulse Context Pack"之上的**研究判断**，不是官方来源陈述，故标 `INFERENCE` 而非 `FACT`。）

---

## 8. Over-engineering Findings

判定规则（任务 §13）：若候选解决的问题**不能**对应到 CP 的真实 gap（Real AI activation / structured provider reliability / provenance / experimentability / live handoff / authority safety），而只能回答 "enterprise grade / scalable / future proof / popular / elegant"，则标 `NOT JUSTIFIED`。

| Candidate | 它能对应 CP 的哪个真实 gap？ | 判定 |
| --- | --- | --- |
| **LiteLLM**（Router / Proxy / fallbacks / cooldowns / spend logs） | 无。它解决的是"跨 provider 可用性"，而 CP §7 明确要求单一 Primary Provider 边界且**无**自动 fallback/voting；其默认行为还会*绕过*调用方的模型访问边界（S19）。它不是 gap 的解法，而是约束的**违反** | `NOT JUSTIFIED` |
| **LangGraph 全量 graph runtime**（StateGraph / nodes / checkpointers / interrupt 编排） | 无。CP §4 的 provider 契约是无工具的单次 `analyze()`；没有多步 agent 编排需求。其"执行前裁决点"的形状已由既有 `DecisionValidator` + `SystemRiskGate` 承担 | `NOT JUSTIFIED` |
| **PydanticAI Agent runtime**（agent loop / tools / deps / RunContext / usage limits） | 无。其中仅 output validator + 有界 retry 与本任务相关，且那部分属**语义参考**（`ADAPT`） | `NOT JUSTIFIED`（runtime）；其 validator 语义 = `ADAPT` |
| **OpenAI Agents SDK 作为依赖**（guardrails 运行时） | 无新增覆盖。guardrail 要防的"输出不合格 ⇒ 产生副作用"在 MarketPulse 中已由 validator 在**经济副作用之前**阻断（CP §4/§7）；引入 SDK 只增加一层 LLM-run 运行时 | `NOT JUSTIFIED`（形状 = `REFERENCE ONLY`） |
| **Langfuse / LangSmith 作为托管平台依赖** | 部分：experimentability 的身份与配对维度（CP §6）。但引入平台 = 新增外部系统 + 数据外发 + 运行时依赖，而 CP §7 要求 Modular Monolith 与最小外部状态；且其评估域是模型输出质量，**替代不了** Forward Outcome / Expectancy 的计算缺口 | 平台 = `NOT JUSTIFIED`；dataset/run-identity 的**形状** = `REFERENCE ONLY / RELEVANT` |
| **Outlines / 约束解码库** | 无。provider-native strict schema 已提供形状强制（S15/S16），自建约束解码属重复投入 | `NOT JUSTIFIED` |
| **通用 structured-output 库（Instructor 作为依赖）** | 部分：重试/校验/provenance 语义（CP §6 "structured provider reliability"）。但 MarketPulse 的 `AIProvider` 契约是自有 provider-neutral 层，是否引入第三方库属未来激活决策（本任务不决定） | 语义 = `ADAPT`；作为**依赖**引入 = `OPTIONAL`（非 `NOT JUSTIFIED`，但亦非必需） |
| **NautilusTrader / Hummingbot / Freqtrade / LEAN / VeighNa 作为框架依赖** | 无。五者都不覆盖 CP §6 REAL GAP：Integrated Runtime Host、live Opportunity→AI handoff、Real AI activation、Forward Outcome Calculator、Expectancy/family aggregation、with/without-AI 实验身份、AI latency/cost/provider provenance。选它们的理由只能落在 "mature / popular / production-grade" | `NOT JUSTIFIED` |
| **多模型投票 / ensemble / 自动 fallback 类编排** | 无。与 CP §7 "单一 Primary Provider 边界，无自动 fallback/voting" 直接冲突 | `NOT JUSTIFIED` + `CONFLICT` |
| **由 AI 生成 TradePlan（Placement D 的实现）** | 无。CP §2/§4 显示该能力已存在且确定性强于 AI 版本；外部证据（S9/S10/S17）也未提供"AI 生成 plan 优于确定性 sizing"的支持 | `NOT JUSTIFIED`（在五项 Placement 中 over-engineering risk 最高，见 §5.5） |

`INFERENCE`（总结）：本轮**没有任何候选**能对应 CP §6 REAL GAP 的核心三项 —— (i) Integrated Runtime Host / live handoff、(ii) Forward Outcome Calculator / Expectancy、(iii) **完整的** with-AI vs without-AI 交易实验回路（= 实验身份 + 同机会经济反事实 + forward outcome + expectancy；部分候选提供其中的身份/配对子模式，但**无一**提供完整组合，见 §6.3、P10）。所有"引入外部框架"的动机因此都落在 enterprise/scalable/popular 一侧，按任务 §13 **不得**作为引入理由。

---

## 9. Preliminary Research Ranking

> **RESEARCH RANKING ONLY — NO FINAL MARKETPULSE ARCHITECTURE VERDICT**

排序依据：§5.7 的方向归一合计（自定义、等权、透明可复算）。排名**仅表示"作为外部研究对象的证据成熟度与风险轮廓"**，**不**表示 MarketPulse 应该采用该 Placement。

| Rank | Placement | adj 合计 | 排序主导因素（来自 §5 的评分理由） |
| --- | --- | --- | --- |
| 1 | **C. Trade Decision** | 48 | 唯一拥有 **accepted + validator 化 + provider-neutral** 契约的位置（CP §4）；failure safety 与 replayability 均为最高档；over-engineering risk 最低（1）；authority risk 最低档（provider 无 repository/risk/execution handle）；`Call Frequency / Cost` 属最低档（2）。 |
| 2 | **B. Market Context Interpretation** | 42 | replayability 与 failure safety 最高档（纯派生物、不产生经济副作用）；authority risk 最低；代价是"下游无既定消费者"与 over-engineering risk 中等（3）。 |
| 3 | **E. Position Re-evaluation** | 34 | failure safety 最高档、架构契合度高（G4 契约已在）；但 experimental isolation 最低档（2），且 `Call Frequency / Cost` 为**最高成本档（5，方向归一后）**。 |
| 4 | **D. Trade Plan Generation** | 31 | 与既有确定性 `TradePlanManager` 重复；over-engineering risk 为全场最高（5）；当前架构契合度低（2）；`Call Frequency / Cost` 属最低档（2）使其合计略高于 A，但其风险型维度（authority / complexity / over-engineering）仍全面偏高。 |
| 5 | **A. Opportunity Qualification** | 30 | authority risk 高（4）、implementation complexity 与 over-engineering risk 均高（4），且与 CP §2 的 admission 语义冲突；`Call Frequency / Cost` 为中档（3）不足以抵消上述风险型扣分。 |

`修正记录（PRE-01A-DS1-FIX-01）` — 本表已按修正后的 §5.7 重算（并采用 §5.7 已修正的 A 列算术值 30）。相对修正前，名次发生**一处对调**：D 与 A 互换（D `29→31`、A `32→30`），其余名次不变（C / B / E 与修正前同序）。**未**为维持原排序而保留任何旧分数。`RESEARCH RANKING ONLY — NO FINAL MARKETPULSE ARCHITECTURE VERDICT` 声明继续有效，本表**不是** Architecture Recommendation。

`INFERENCE` — 上述名次**改变不了**一个事实：CP §6 的 REAL GAP（Integrated Runtime Host、live handoff、Real AI activation、Forward Outcome Calculator、Expectancy、实验身份、AI provider provenance）对**全部五个** Placement 同等存在。因此该排序**不能**被解读为"应当先做 C"这一架构结论 —— 那属于后续高阶模型的职责范围，不在本任务内。

---

## 10. Unknowns / Evidence Gaps

### 10.1 外部研究侧的缺口（本包内不得当作事实）

| ID | 缺口 | 影响 |
| --- | --- | --- |
| GAP-01 | Hummingbot 的 risk/budget 层与 controller/executor 的异常语义：本轮抓取页未覆盖 ⇒ `NOT VERIFIED` | §2.2 B/E 留 UNKNOWN |
| GAP-02 | VeighNa 核心的策略/网关异常隔离语义：未取得官方明文 ⇒ `NOT VERIFIED` | §2.5 E 留 UNKNOWN |
| GAP-03 | NautilusTrader 的 strategy handler 异常后的官方行为（是否隔离、是否影响 accounting）⇒ 未找到明文 | §2.1 E 留 UNKNOWN |
| GAP-04 | LangSmith / LangChain tracing 与 decision provenance 的官方机制：本轮**未抓取** ⇒ §3.5 的 tracing 面 `NOT VERIFIED` | §3.5 未对 provenance 作断言 |
| GAP-05 | LEAN 的 `OnError` handler 官方页未直接抓取；本节改用 order-errors / RuntimeErrorPacket / Brokerage message handler 三处官方文档支撑"fail-stop"结论 | 结论仍为 FACT（三处官方来源），但覆盖面不完整 |
| GAP-06 | 全部候选文档均**未标注精确版本/commit**（除 Nautilus release tag 1.231.0 Beta、vnpy_riskmanager 2.0.0 / `a7b30bb`）；LEAN / Freqtrade / Hummingbot / LiteLLM / PydanticAI / Instructor / LangChain 的版本与日期为 `NOT VERIFIED` | 后续复核者需自行钉版本 |
| GAP-07 | `platform.openai.com` 官方 structured-outputs 页被 Cloudflare 拦截；改用 OpenAI 官方 cookbook（S15，内容时代约 2024-08）+ Azure OpenAI 官方页（S16） | schema 子集结论来自 Azure 官方（同一 Structured Outputs 语义），OpenAI 平台的**最新**差异未取证 |
| GAP-08 | Langfuse dataset **版本固定**：官方明确"特定版本实验的支持将稍后加入 SDK" ⇒ 目前无法钉住 dataset 版本 | §6 E3 |
| GAP-09 | "没有任何成熟系统实现 MarketPulse 三条件组合"属 **absence of evidence**（研究范围限 5 个 trading systems + 7 个 LLM 候选），**不得**表述为"不存在" | §4 P5 |
| GAP-10 | 本轮**未**取得任何关于"AI 提升 Trading Edge"的证据（无论真实市场或回测），且本任务禁止此类结论 | §17 合规 |

### 10.2 Context Pack 中保持 UNKNOWN 的事项（本任务**未**探测，按 CP 的 `DO NOT DISTURB` 保持）

`FACT`（CP §1/§8 转述）— 当前 Runtime 是否运行、运行 commit/config；PostgreSQL migration head；是否存在真实 Forward Opportunity / AI decision / attribution / outcome rows；是否存在可用 AI credential；Real AI 的输出质量/稳定性/延迟/成本/错误率；未提交工作树内容的来源与接受状态 —— **全部仍为 `UNKNOWN`**，本任务未做任何验证。

### 10.3 本任务未执行的动作（合规声明）

- 未修改 MarketPulse repository；未修改 `.workbuddy/`；未修改 memory / dev_log / project docs；未 commit / push。
- 未运行或干扰 Runtime / Docker / PostgreSQL；未调用任何 AI provider；未执行测试。
- 本文件为**仓外**产物（`E:\Temp\PRE-01A\`），不进入 Git。
- 未生成 Implementation Plan；未决定正式 Provider；未决定正式 Runtime Host；未引入 Agent Framework；未重设计 G3/G4/Risk/Execution/Protection；**未宣布最终 AI Placement**；**未宣布 AI 已提升 Trading Edge**。

### 10.4 Acceptance Criteria 自查（任务 §18）

| # | 判据 | 状态 | 证据位置 |
| --- | --- | --- | --- |
| 1 | 使用 Context Pack 作为 MarketPulse 事实基线 | PASS | 头部 Reality baseline 声明；全文 `CP §x` 引用 |
| 2 | 至少研究 4 个成熟 Trading Systems | PASS（5 个） | §2.1–§2.5 |
| 3 | 核心事实优先由官方资料/源码支持 | PASS | §1.2 来源表；§2/§3 每条 FACT 附来源编号 |
| 4 | 已研究成熟 Structured LLM / advisory authority 模式 | PASS（7 个候选） | §3.1–§3.7 |
| 5 | 五种 AI Placement 全部完成 | PASS | §5.2–§5.7 |
| 6 | 已研究 experimentability patterns | PASS | §6 |
| 7 | 所有重要候选完成 Reuse Classification | PASS | §7 |
| 8 | 完成 Over-engineering Test | PASS | §8 |
| 9 | FACT / INFERENCE 明确区分 | PASS | §1.5 约定；全文逐条标注 |
| 10 | 重要结论具有可供后续模型复核的来源 | PASS（含 GAP-06 的版本限制声明） | §1.2 / §1.3 / §2–§3 各 Evidence Record |
| 11 | 没有修改 MarketPulse | PASS | §10.3 |
| 12 | 没有给最终 Architecture Verdict | PASS | 头部声明 + §9 标题声明 + §10.3 |

---

**END — PRE-01A External Evidence Pack**




