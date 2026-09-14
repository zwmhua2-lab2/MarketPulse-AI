# PRE-01A Real AI Research Verdict

## 1. Executive Verdict

靓仔，**VERDICT — Real AI V1 First Placement = C. Trade Decision。**

## 2. Current Repository Reality

**FACT**

- GitHub 当前 `main`：`b77c80333b85d6e3f1095ac7da9b13e9bf08163a`。
- `research/pre-01a` 固定提交：`ff3efff54a9a505fdcbd55f2658f6dbf8e18e05a`，直接父提交正是当前 `main`，无 baseline drift。
- 两份研究文件仅是 Research Input；旧 Context Pack 中 `SE-02C = BLOCKED / NOT STARTED` 已过时，未被沿用。[Context Pack](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/ff3efff54a9a505fdcbd55f2658f6dbf8e18e05a/docs/research/PRE-01A/PRE-01A-Context-Pack.md)、[External Evidence Pack](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/ff3efff54a9a505fdcbd55f2658f6dbf8e18e05a/docs/research/PRE-01A/PRE-01A-External-Evidence-Pack.md)
- 当前 `SE-02C Forward Outcome Calculator = ACCEPTED / COMPLETE`：支持 `30s / 5m / 15m / 1h`、MFE、MAE、reference return、executable-long return、cost-adjusted return、确定性 revision-1、并发 exactly-one 与稳定快照。[PROJECT_STATE.md](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/PROJECT_STATE.md)、[forward.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/edge/forward.py)、[forward_service.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/edge/forward_service.py)
- `live Opportunity → G3 handoff` 仍未接通；`G3Workflow` 明确保留为未获 activation approval 的显式入口。
- Real AI provider 仍为 deferred；当前无真实 provider runtime evidence，`OPENAI_API_KEY` 缺失，接受基线使用 fake provider。
- `SE-02D Family Aggregation / Expectancy = NOT STARTED`。
- `Integrated Runtime Host = NOT STARTED`。[AI_CONTEXT.md](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/AI_CONTEXT.md)、[g3/service.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/g3/service.py)

## 3. Independently Verified External Findings

| 对象 | 独立结论 |
|---|---|
| LEAN | **FACT** — `Insight → Portfolio Construction → PortfolioTarget → Risk Management → Execution` 成立。Insight 是信号对象；Portfolio Construction 生成 target；Risk 可调整 target，不只是 veto；Execution 才执行订单。[LEAN Algorithm Framework](https://www.quantconnect.com/docs/v2/writing-algorithms/algorithm-framework/overview) |
| NautilusTrader | **FACT** — `RiskEngine` 位于 submit/modify 路径；`REDUCING` 只允许不增加 exposure 的 submit/modify，cancel 继续可用。这支持 MarketPulse 的“风险增加失败关闭、风险降低继续”。[NautilusTrader Execution](https://nautilustrader.io/docs/latest/concepts/execution/) |
| Freqtrade | **FACT** — callback 异常 fallback 是逐 callback 定义，不能泛化；`confirm_trade_exit()` 可阻止包括 stoploss 在内的退出，但不能阻止 liquidation；Protections 主要锁定后续 entry/re-entry，不是统一 exit authority。[Callbacks](https://www.freqtrade.io/en/stable/strategy-callbacks/)、[Protections](https://www.freqtrade.io/en/stable/plugins/) |
| vn.py | **FACT（源码事实）** — core `MainEngine.send_order` 直接委托 gateway；`vnpy_riskmanager` 通过替换/patch `send_order` 接入检查。**不是官方架构保证**。[vn.py engine.py](https://github.com/vnpy/vnpy/blob/master/vnpy/trader/engine.py)、[vnpy_riskmanager](https://github.com/vnpy/vnpy_riskmanager/blob/main/vnpy_riskmanager/engine.py) |
| OpenAI Structured Outputs | **FACT** — provider-native `json_schema` 可强制结构；refusal 是独立分支；严格 Schema 仍只能保证结构约束，不能证明输入事实、`state_version`、数值关系或交易权限正确。[OpenAI Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs) |
| OpenAI 限制表 | **FACT — Research Pack 部分已过时**：当前普通模型支持 `pattern`、部分 `format`、数值边界、`multipleOf`、`minItems/maxItems`；当前上限为总计 5,000 properties、10 层嵌套。部分限制仍适用于 fine-tuned models；`allOf/not/if-then-else` 等仍不支持。 |
| PydanticAI | **FACT** — 支持 Tool/Native/Prompted structured output、output validator 和有界 ModelRetry。**NOT VERIFIED** — 未找到与 MarketPulse `state_version/stale result` 等价的内置业务语义，也未确认统一的跨 provider 完整失败历史契约。[PydanticAI Output](https://pydantic.dev/docs/ai/core-concepts/output/) |
| Instructor | **FACT** — parsing/validation retry 可有界，暴露 attempt/failed-attempt 信息；retry exhaustion 不等于重启恢复，也没有 MarketPulse stale-state 语义。[Instructor Retrying](https://python.useinstructor.com/concepts/retrying/) |
| LiteLLM | **FACT** — 支持重试后自动 model/provider fallback；若启用，会直接冲突于 `Single Primary Provider / No automatic fallback / No model voting`。[LiteLLM Reliability](https://docs.litellm.ai/docs/proxy/reliability) |
| Langfuse | **FACT** — 提供 experiment/run/item identity、版本化 dataset、item/run evaluators、并发执行及 individual failure isolation；具体指标由用户 evaluator 定义。它不会直接提供 MFE、MAE、R-Multiple 或 Trading Expectancy。[Experiments SDK](https://langfuse.com/docs/evaluation/experiments/experiments-via-sdk)、[Data Model](https://langfuse.com/docs/evaluation/experiments/data-model) |
| LangChain / LangGraph | **FACT** — LangChain 可切换 provider-native/tool structured output；LangGraph 提供 checkpoint、interrupt 和 durable graph execution。这些能力不是当前单次、有界 Trade Decision 调用的必要条件。[LangChain Structured Output](https://docs.langchain.com/oss/python/langchain/structured-output)、[LangGraph Persistence](https://docs.langchain.com/oss/python/langgraph/persistence) |
| OpenAI Agents SDK | **FACT** — 提供 agent loop、tools、handoffs、sessions 和 guardrail tripwire；当前 MarketPulse 不需要 agent loop 才能完成单次 advisory decision。[Agents SDK Guardrails](https://openai.github.io/openai-agents-python/guardrails/) |
| Hummingbot | **FACT** — Controller 产生 ExecutorActions，Executor 管理订单生命周期；属于执行框架模式参考，不是 MarketPulse Real AI Placement 的直接组件。[Controllers](https://hummingbot.org/strategies/v2-strategies/controllers/)、[Executors](https://hummingbot.org/strategies/v2-strategies/executors/) |

## 4. Placement Matrix

| Placement | 当前契约适配 | Authority / Failure Risk | 可归因与可测量性 | 成本与复杂度 | 独立判断 |
|---|---|---|---|---|---|
| A. Opportunity Qualification | Scanner/Admission 已是确定性市场事实路径 | AI 故障可能直接删除样本并改变机会总体 | 高 selection bias；Missed Opportunity 难观察 | 中 | 不适合首发 |
| B. Market Context Interpretation | 可作为 Evidence Snapshot 上的 advisory label | 权限风险低，失败易隔离 | 标签质量易测；经济增量若不影响决策则很弱 | 低 | 可作为后续 shadow 能力 |
| C. Trade Decision | 已有 `AIProvider`、`AIAnalysis`、`DecisionValidator`、`state_version`、计划/风险/执行隔离 | AI 不直接下单；错误可在经济动作前关闭 | 同一机会、同一证据可比较 WAIT/LONG 等决策；现有 attribution 与 Forward Outcome 可承接 | 中 | **最强首发位置** |
| D. Trade Plan Generation | 当前已有确定性 `TradePlanManager` | entry/stop/target 数值错误更接近经济动作；重复现有能力 | AI 决策与计划效果容易混合 | 中高 | 初期不应替换确定性计划 |
| E. Position Re-evaluation | 已有 advisory reevaluation contract | 实时性要求高；绝不能阻塞保护与风险降低退出 | 可测但受入场决策、持仓路径和退出机制多重混杂 | 高 | 可在 C 稳定后以 shadow/advisory 研究 |

**INFERENCE** — C 的首选不是因为 Worker 给了最高分，而是因为当前仓库已经提供最成熟的 advisory contract、最强的下游 authority separation，以及最短的实验归因路径。

## 5. Final Placement Verdict

| Placement | Verdict | 理由 |
|---|---|---|
| A. Opportunity Qualification | **NOT RECOMMENDED INITIALLY** | 会改变样本进入机制，破坏无偏机会总体与 missed-opportunity 归因。 |
| B. Market Context Interpretation | **ACCEPTABLE LATER** | 安全、适合 shadow，但单独启用时难证明经济增量。 |
| C. Trade Decision | **RECOMMENDED FIRST** | 唯一首选；现有 G3 contract 能将 AI 限定为建议，下游 Risk/Execution 保持确定性权威。 |
| D. Trade Plan Generation | **NOT RECOMMENDED INITIALLY** | 重复确定性计划能力，并把模型错误推进至更接近交易执行的位置。 |
| E. Position Re-evaluation | **ACCEPTABLE LATER** | 有既有契约，但延迟、旧状态与保护连续性风险高于 C。 |

**VERDICT** — Real AI V1 只启用 C；不得同时启用 A+C+D+E。多 Placement 会同时改变样本选择、决策、参数和退出路径，使 incremental AI edge 无法清晰归因。

## 6. AI MAY / AI MUST NOT

### AI MAY

**VERDICT — 仅可提出 advisory output：**

- market evidence interpretation；
- context classification；
- confidence；
- WAIT / NO TRADE recommendation；
- direction recommendation；V1 Spot 只能将 SHORT 作为 bearish analysis，不能形成 short order；
- entry、stop、target suggestion；
- position-management suggestion，但仅属于后续 E，不能承担保护责任。

所有建议必须绑定 immutable Evidence Snapshot、版本与 `state_version`，并通过 deterministic schema/business validation、Risk Gate 和 execution authority。

### AI MUST NOT

**VERDICT — 无例外：**

- Balance mutation；
- Risk-limit authority；
- Leverage enforcement；
- Margin validation；
- Order execution；
- Fill creation；
- Position accounting；
- PnL accounting；
- Ledger mutation；
- Protection trigger；
- Stop enforcement；
- Recovery；
- Reconciliation。

**Invariant：AI = Advisory；Deterministic System = Authority。**  
这与当前 [PRODUCT_REQUIREMENTS.md](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/PRODUCT_REQUIREMENTS.md) 及 [DECISIONS.md](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/DECISIONS.md) 一致。

## 7. Failure Semantics

| Failure | AI Path | Deterministic Runtime | New Risk-Increasing Trade? | Existing Position Protection | Safe Result |
|---|---|---|---|---|---|
| timeout | 截止调用，记录 timeout | 继续运行 | **No** | 必须继续 | WAIT/NO_TRADE；保留失败 provenance |
| provider unavailable | 记录 provider error；有界 transport retry 后终止 | 继续运行 | **No** | 必须继续 | PROVIDER_ERROR，不自动 fallback |
| malformed output | parsing 失败 | 继续运行 | **No** | 必须继续 | INVALID |
| schema failure | schema validation 失败 | 继续运行 | **No** | 必须继续 | INVALID |
| refusal | 识别独立 refusal 分支 | 继续运行 | **No** | 必须继续 | REFUSED/NO_TRADE |
| hallucinated fact | 无法由冻结 Snapshot 证明即拒绝 | 继续运行 | **No** | 必须继续 | UNSUPPORTED_EVIDENCE/INVALID |
| invalid numeric relation | deterministic business validator 拒绝 | 继续运行 | **No** | 必须继续 | INVALID |
| stale `state_version` | 结果不得进入 plan/action | 继续处理当前状态 | **No** | 必须继续 | STALE、零经济副作用 |
| duplicate result | 复用既有结果或抑制重复 | 继续运行 | **No duplicate action** | 必须继续 | IDEMPOTENT_EXISTING/DUPLICATE_SUPPRESSED |
| late result | 仅保留审计，不再行动 | 继续运行 | **No** | 必须继续 | LATE/STALE |
| partial result | 不补猜缺失字段 | 继续运行 | **No** | 必须继续 | INVALID |

**VERDICT**

```text
AI failure → fail-closed at economic action
```

必须成立；但：

```text
fail-closed at economic action ≠ stop entire runtime
```

风险降低、cancel、stop enforcement 和既有 Position Protection 必须独立继续工作。

## 8. Structured Output / Provider Boundary Verdict

**REUSE**

- 保留当前轻量 `AIProvider` interface、`AIAnalysis` Pydantic model、`DecisionValidator` 和 `state_version` stale check。
- 保留 deterministic business validator 为最终可信边界。[g3/provider.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/g3/provider.py)

**ADAPT**

- provider 支持时采用 provider-native Structured Outputs，优于当前 `output_text → json.loads → model_validate`。
- 明确处理 refusal、incomplete/partial response 与 schema-version provenance。
- transport retry 与 validation retry 必须分开计数、分开分类，并共同受 deadline、attempt 和成本预算约束。
- 所有 retry 必须 bounded；迟到结果仍须经过 stale check。

**AVOID**

- 不引入完整第三方 structured-output framework；当前 Pydantic + provider-native schema + deterministic validator 足够。
- 不引入 Agent Runtime、tool loop、handoff graph 或 autonomous planning。
- 不引入 provider/model automatic fallback。
- 不扩大现有 `AIProvider` 为通用 orchestration abstraction。

**VERDICT** — Schema validation 负责 shape/type/required fields；Business validation 负责 Snapshot 一致性、数值关系、产品规则、交易语义、权限和 freshness。前者不能替代后者。

## 9. Experiment Verdict

**VERDICT — Real AI V1 必须保持 Single Placement：C。**

```text
Same Opportunity + Same immutable Evidence Snapshot
            ├─ Baseline decision
            └─ AI-assisted decision
                     ↓
       Same Forward Outcome contract
                     ↓
  Family / regime / expectancy comparison
```

Baseline 与 treatment 必须有显式 arm identity 和 pair identity；不能以时间相近、symbol 相同或事后 join 猜测配对。Baseline policy 当前尚未冻结，是 **REAL GAP**。两个 arm 不能同时产生真实经济动作；非权威 arm 只能作为 shadow/replay counterfactual。

| 指标 | 当前准备度 | Verdict |
|---|---|---|
| Expectancy | NOT PRESENT | 必须成为核心比较指标；依赖 SE-02D |
| R Multiple | NOT PRESENT | 需要 MarketPulse 定义 risk-at-entry 与结果的冻结语义 |
| MFE / MAE | READY | SE-02C 已支持四个 horizon |
| Forward return | READY | reference、executable-long、cost-adjusted 均已具备 |
| Drawdown | NOT PRESENT | G5 当前只提供最小经济汇总，没有 accepted drawdown contract |
| Trade Frequency | PARTIAL | 原始 order/trade counts 可取，但 arm/family aggregation 缺失 |
| Missed Opportunities | PARTIAL | 全机会 Forward Outcome 已可支持分析，但 baseline/treatment pairing 缺失 |
| Fees | READY/PARTIAL | 实际 fill fee 已持久化；counterfactual fee 仍需冻结定义 |
| Slippage | PARTIAL | SE-02C 使用固定 5 bps 模型；实际相对 benchmark 的 slippage contract 未接受 |
| Market Regime | PARTIAL | Evidence 可承载上下文，但无 accepted regime aggregation |
| AI latency | NOT PRESENT | 真实 provider 尚未运行，也无完整 provenance 字段 |
| AI cost | NOT PRESENT | 无真实 token/cost evidence |

**VERDICT** — Win Rate alone is insufficient。最终判断至少需要 Expectancy、分布与 tail risk、频率、费用/滑点、regime 分层、延迟和成本；当前代码只证明 outcome calculator 可用，不证明样本充分，也不证明 AI 有 edge。

## 10. Evidence Readiness & Gaps

以下是 capability readiness；不表示当前已有真实 AI 样本。

| Evidence | Readiness | Gap Type | 依据 |
|---|---|---|---|
| Opportunity Identity | **READY** | **NOT NEEDED** | 已有稳定 opportunity/evidence identity |
| Evidence Snapshot | **READY** | **NOT NEEDED** | immutable revision、hash、source/provenance 已有 |
| Decision Provenance | **READY** | **NOT NEEDED** | snapshot、state/config/prompt/schema/model、raw input/output、status/error 已持久化 |
| Attribution | **READY** | **NOT NEEDED** | AI→Plan→Risk→Execution→Economic Result append-only lineage 已有 |
| Forward Outcome | **READY** | **NOT NEEDED** | SE-02C 已 accepted；MFE/MAE/returns/cost-adjusted return 可用 |
| Family Aggregation | **NOT PRESENT** | **REAL GAP** | SE-02D 未开始 |
| Expectancy | **NOT PRESENT** | **REAL GAP** | 无 accepted expectancy contract |
| Model Provenance | **PARTIAL** | **REAL GAP** | 有 `model`/版本字段；缺精确 provider response/config/usage 身份 |
| Provider Provenance | **NOT PRESENT** | **REAL GAP** | 无明确 provider/request/attempt/latency/token/cost contract |
| Experiment Arm Identity | **NOT PRESENT** | **REAL GAP** | 无 baseline/treatment arm identity |
| Baseline / Treatment Pairing | **NOT PRESENT** | **REAL GAP** | 无同 opportunity/evidence 的显式 pair contract |

相关现有实现：[db/models.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/db/models.py)、[edge/attribution.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/edge/attribution.py)、[g5/evaluation.py](https://github.com/zwmhua2-lab2/MarketPulse-AI/blob/b77c80333b85d6e3f1095ac7da9b13e9bf08163a/backend/src/marketpulse/g5/evaluation.py)。

## 11. Reuse Verdict

| 候选 | Classification | Verdict |
|---|---|---|
| OpenAI Structured Outputs | **ADAPT** | 作为 provider adapter 的第一层结构保证 |
| PydanticAI | **REFERENCE ONLY** | 参考 native/tool output 与 validator/retry 模式；不引入依赖 |
| Instructor | **REFERENCE ONLY** | 参考有界 validation retry 与 attempt evidence |
| LiteLLM | **NOT JUSTIFIED** | 自动 fallback 与 frozen provider policy 冲突 |
| LangChain | **NOT JUSTIFIED** | 当前不需要 agent abstraction 或双策略路由层 |
| LangGraph | **NOT JUSTIFIED** | 当前单次决策无 graph/checkpoint/HITL gap |
| OpenAI Agents SDK | **REFERENCE ONLY** | 仅参考 guardrail/tripwire 语义；agent runtime 不引入 |
| Langfuse | **REFERENCE ONLY** | 参考 run/item/pair identity；平台依赖当前不必要 |
| NautilusTrader | **REFERENCE ONLY** | 参考 risk-increasing/reducing 与 cancel 连续性 |
| Hummingbot | **REFERENCE ONLY** | 参考 controller/executor 生命周期分层 |
| Freqtrade | **REFERENCE ONLY** | 参考 callback failure 与保护语义反例 |
| LEAN | **REFERENCE ONLY** | 参考 signal/target/risk/execution authority 分离 |
| vn.py | **REFERENCE ONLY** | 仅作源码接入方式反例，不能视为架构保证 |
| MarketPulse-specific experiment binding and metrics | **BUILD** | 由 MarketPulse 自己冻结最小领域契约 |

### A. 不应为了成熟框架而替换的现有能力

- Scanner/admission 和 stable Opportunity Identity；
- immutable Evidence Snapshot；
- 轻量 `AIProvider`、`AIAnalysis`、`DecisionValidator`；
- `state_version` stale fencing；
- deterministic TradePlan、Risk Gate、Execution；
- Position Protection、Recovery、Reconciliation；
- Paper accounting、ledger 与 G5 replay；
- Edge Attribution；
- SE-02C Forward Outcome。

### B. 必须由 MarketPulse 自己定义的问题

- without-AI baseline policy；
- arm identity 与 baseline/treatment pairing；
- provider/model/request/attempt/latency/cost provenance；
- `state_version`、late/duplicate result 与经济动作之间的绑定；
- R-Multiple、Expectancy、drawdown、missed opportunity、regime aggregation；
- Spot LONG-only、成本、滑点和风险降低语义；
- AI 建议与 deterministic authority 的正式边界。

## 12. Over-engineering Exclusions

| 排除项 | 当前 REAL GAP？ | Verdict |
|---|---|---|
| Agent Runtime / autonomous tool loop | 无；当前是一次有界 advisory decision | **NOT JUSTIFIED** |
| LangGraph workflow/checkpointer | 无；Integrated Runtime Host 又属于独立研究 | **NOT JUSTIFIED** |
| LiteLLM multi-provider router | 无；且违反 Single Primary Provider | **NOT JUSTIFIED** |
| Automatic fallback / model voting | 无；会增加实验变量并违反冻结规则 | **NOT JUSTIFIED** |
| 引入完整外部 trading framework | 无；现有 G2–G5 authority chain 已接受 | **NOT JUSTIFIED** |
| 同时启用 A+C+D+E | 不解决 gap，反而破坏因果归因 | **NOT JUSTIFIED** |
| 用 AI 替代 Risk/Protection/Accounting | 无，且违反安全 invariant | **NOT JUSTIFIED** |
| 第三方 structured-output wrapper 堆叠 | 无；native schema + Pydantic 已足够 | **NOT JUSTIFIED** |
| 立即部署 Langfuse | arm identity 是 REAL GAP，但完整平台超出最小必要解 | **NOT JUSTIFIED INITIALLY** |
| 在本任务选择 Runtime Host | 属于另一项 Research/Design | **OUT OF SCOPE** |

## 13. Risks / Unknowns

- **UNKNOWN** — 未执行真实 provider call，因此真实延迟、成本、拒绝率、schema failure rate 和输出分布均未验证。
- **UNKNOWN** — without-AI baseline 的确定性行为尚未冻结。
- **UNKNOWN** — 当前 Accepted Main 是否已积累足够、跨 regime 的 Forward Outcome 样本；calculator readiness 不等于 sample readiness。
- **UNKNOWN** — Real AI 是否改善 Expectancy；本研究没有、也不能宣称已证明 Trading Edge。
- **UNKNOWN** — 实际 slippage、tail drawdown 和 rare provider failure 对经济结果的影响。
- **RISK** — OpenAI model/schema capability 会随服务演进，后续 Design 必须绑定可审计的 provider/model/config identity。
- **RISK** — live Opportunity→G3 handoff 与 Runtime supervision 尚不存在；这只是 C Placement 的 activation prerequisite，本任务没有选择 Runtime Host。
- **FACT** — 本次仅做 GitHub/source/official-document read-only review；未运行 Runtime、Docker、PostgreSQL、Real AI provider 或测试。
- **FACT** — Repository、Git refs、`.workbuddy/`、memory/skills 均未修改；本地已有 dirty worktree 保持原状。

## 14. Minimal Next Step

**RECOMMENDATION — 仅创建一项 Design Task：**

```text
PRE-01A-D1｜Real AI V1 Trade Decision Experiment Contract Design
```

该 Design Task 只冻结 C Placement 的 authority boundary、provider-native schema/refusal、bounded retry、stale/late/duplicate semantics、provider provenance、baseline/treatment arm identity 与 pairing、指标定义和 activation prerequisites；不得实现代码、修改数据库、调用真实 provider、选择 Integrated Runtime Host，完成后等待 Human Design Review。

<oai-mem-citation>
<citation_entries>
MEMORY.md:231-231|note=[private repository identity and GitHub tree API navigation]
</citation_entries>
<rollout_ids>
01a06d18-937f-72c3-8fbc-5d127bf36050
</rollout_ids>
</oai-mem-citation>
