# Approved Decisions

- Group 1 使用 Modular Monolith。
- Backend/Frontend 本地运行，PostgreSQL 使用 Docker，默认监听 `127.0.0.1`。
- Market data 采用 Raw Adapter → Normalized Data 边界。
- `SPOT` 与 `SWAP` 是严格不同的 market type；衍生品上下文通过明确关联提供。
- Hot Score 仅用于 Universe/Priority，不进入 Buy/Sell 逻辑。
- G3 采用单一可配置 Primary AI Provider 边界；V1 没有自动 model fallback、投票或多模型 reviewer。AI 仅输出分析建议，Paper execution 只能由程序化 Trade Plan/Execution Intent 驱动。
- G3 V1 仅支持 Spot Paper 的 LONG 风险计划；`SHORT_BIAS` 只保留分析记录，绝不产生 Short Execution。
- G4 区分 Operator Intent（NORMAL/PAUSED/EMERGENCY_STOP）与 System Derived State（RECOVERING/DATA_DEGRADED/SAFE_MODE/ERROR），二者分别持久化；重启不得把人工 EMERGENCY_STOP 错恢复为 RUNNING。
- G4 所有风险增加动作（BUY/ADD/OPEN BUY Limit Fill）必须经过唯一程序化 `SystemRiskGate`；SELL 风险降低动作在 Pause/SafeMode/Emergency 下仍被允许。
- G4 的 SL/TP 为 Trigger Price，Protective Exit 一律以当前 Fresh Best Bid − slippage 成交；不伪造停机期间历史 Fill。
- G4 以 PostgreSQL 为 Restart Recovery 唯一事实源；Recovery 不依赖内存 Queue，Reconciliation 是 Detector 而非 Repair Engine。
- G4 AI 重估值响应对冻结 snapshot 有效；provider 返回后、任何 programmatic action 前必须重验 state_version / active plan(version) / position lifecycle，任一变化判 STALE 并零副作用（不得 ADD/REDUCE/CLOSE/UPDATE_*/REPLACE_PLAN，保留 SL/TP，不改 Position/Account/Plan，按审计链记 stale decision）。
- G4 重启恢复不得以 STARTING/RECOVERING 覆盖重启前持久化的 SAFE_MODE；未解决的 blocking incident（POSITION_UNPROTECTED / RECOVERY_FAILED / ACCOUNT_INTEGRITY_ERROR）不得静默进入 RUNNING，须显式 safe-mode recovery → PAUSED → 人工 Resume。
- G4 AI response 的最终 stale 校验与 mutation 共用 PostgreSQL 事务：先锁 runtime control，再锁 durable state/expected active plan/position/trade；Plan replacement 只允许 expected-current CAS，继续由 `uq_trade_plans_one_active` 兜底，冲突视为 STALE 且旧 response 零副作用。
- G4 Recovery 不把 transient `RECOVERING` 当作取消原因；OPEN BUY 改按 current Fresh BBO、entry/stop、symbol block 与 G3 capacity durable facts 判定，永久失效才原子 cancel + release reservation。
- G4 V1（已批准）：`TradePlan.invalidation` = AI/human-readable advisory text。用途为 AI reasoning context、Position Re-evaluation context、人工阅读、审计与解释。它不是 machine-executable condition。Runtime MUST NOT 解析 invalidation 自然语言、不得依据 invalidation 文本自动触发交易、不得创建 NLP parser / condition DSL / 第二套 invalidation execution engine。V1 唯一 machine-enforceable hard price invalidation 是 `stop_loss`。未来如需 structured machine-executable invalidation，必须作为新的独立需求重新设计。
- G5-4 V1（已批准）：Deterministic Replay Evaluation。从 G5-3 ACCEPTED 的 Replay PostgreSQL durable workspace 派生最小确定性评估指标（`ReplayEvaluationReport`）；不引入 replay_run_id / backtest_id，不新增 performance 或 evaluation 持久化表，不保存 Evaluation Report，不修改 trading / accounting semantics；不计算 MFE、MAE、drawdown、equity curve、win rate、expectancy、R-multiple、Sharpe、Sortino、profit factor（当前 durable facts 不足以无歧义证明其完整语义）；高级分析、Strategy Ranking 与 Parameter Optimization 未来单独设计。
- G4 / N01-7-F01 V1（已批准，2026-09-13 Human Acceptance = CONFIRMED）：TradePlan TTL 仅控制 **risk-increasing freshness**（BUY / ADD / pending LIMIT fill 的新鲜度闸门），与保护寿命无关；附着于当前 OPEN Position 的 durable protection snapshot 是该 Position 的**唯一** protection-lifetime authority，直至（1）经批准的 successor snapshot 被原子提交到同一 Position 行，或（2）Position 变为 flat。新创建的 ACTIVE TradePlan 不因「有效」而自动成为保护权威——plan 仅是 authority **source**，只有被原子提交到 Position 行后才成为权威。（取代 F01 §3.3 的 TTL-only carve-out 与 FG-C protection-lifetime 语义；历史契约文件保持原样，见 `dev_log/2026-09-12-n01-7-f01-r1-protection-authority-closure.md` §0 与 `dev_log/2026-09-13-n01-7-f01-final-acceptance-closeout.md`。）
- SE-ARCH-FIX-02 V1（已批准，2026-09-13 Human Acceptance = `APPROVED`）：Forward Outcome revision chain 的 identity scope 冻结为 `(opportunity_id, evidence_id, horizon)`；每个 scope 拥有自己独立的 revision chain，`revision N > 1` 只能 supersede **同 scope 的 `N - 1`**，跨 opportunity / cross-evidence / cross-horizon / 跳号 / 悬空一律 fail closed。责任划分：**数据库负责 scope integrity**（`uq_edge_outcome_id_scope` + 4 列 `fk_edge_outcome_supersedes`；绕过 service 直接写库亦不能产生 cross-scope chain），**service 同时负责 scope integrity 与 revision adjacency**（FK 无法表达 `revision = N - 1`，且不引入 trigger / stored procedure）。既有非法存量 chain 在 migration `20260913_0009` 中 **fail-closed abort**，不自动改写 / 重编号 / 删除任何行。`revision = 1`（无 supersedes）、idempotency（同 scope + 同 revision + 同 hash ⇒ `IDEMPOTENT`）与 conflict（同 logical revision + 不同 hash ⇒ `EdgeOutcomeConflict`）语义保持不变。详见 `dev_log/2026-09-13-se-arch-fix-02-outcome-revision-chain-scope.md`。
- SE-ARCH-FIX-01 V1（已批准，2026-09-13 Human Acceptance = `APPROVED`）：Forward Paper admission boundary 为 append-only durable **Capture Anchor**（`edge_opportunity_capture_anchors` + durable orphan 分类）。入选的 qualifying candidate 在 admission 前冻结 causal payload（稳定 T0 / reference BBO / ingress provenance / session proof）；anchor durable 之后，重试与重启一律复用 frozen payload，**禁止**以新 clock 或新 BBO 重建 Formal Evidence。anchor 在 durable 之前 crash ⇒ 该样本 = `NOT ADMITTED / UNVERIFIABLE / NO FORWARD EVIDENCE`，属**已批准的 V1 capture-coverage 限制**（coverage loss > forged Forward sample），不得事后修补。新 `FORWARD_PAPER` admission 必须携带 live-ingress 签发的 session-start causal fence proof：issuer 只能是 live ingress（`ScannerPipeline`），durable repository 仅持有 verifier；`HISTORICAL_REPLAY` 永不创建 Forward anchor。既有非法 legacy row（`OK` 且 reference BBO id 为 NULL）在 migration `20260913_0008` 中 **fail-closed abort**，不做任何自动语义重分类。详见 `dev_log/2026-09-12-se-arch-fix-01-stable-evidence-anchor.md`。
- SE-02C V1（已批准，2026-09-14 Human Acceptance = `CONFIRMED`）：Forward Outcome normal evaluator。（1）scope identity = `(opportunity_id, evidence_id, horizon)`；（2）`revision = 1` 的 normal outcome 一经写入即 **immutable**，normal evaluator 永不改写、永不写 revision > 1；（3）Forward reference authority = durable FIX-01 **Capture Anchor** BBO（anchor 只作 reference，**不得**作 endpoint）；（4）path = **complete causal Forward BBO path**（完整 keyset 分页遍历，无静态读取上限）；（5）normal calculation 的 reference 与 **全部** path pages 使用 **同一个** PostgreSQL `REPEATABLE READ` / `READ ONLY` transaction snapshot（`SET TRANSACTION ...` 作为该 transaction 的第一条 SQL；snapshot 建立后 commit 的 row 对本次 attempt 不可见，但该 row 仍合法 durable，fresh snapshot 可见）；（6）same-scope evaluator coordination = PostgreSQL **advisory transaction lock**（`pg_advisory_xact_lock`，key = canonical scope 文本的 SHA-256 signed-int64；覆盖 task / process / independent session，Python `asyncio.Lock` 不是 correctness 边界）；（7）取锁后发现已存在 revision-1 则**重读并直接返回** existing，不建立 calculation snapshot、不重算、不报冲突；（8）**不**自动创建 revision 2；（9）SE-02C-FIX-02 **未**引入 schema / migration；（10）Alembic head = `20260913_0009`（单 head）；（11）`SE02C-R7`（源码 comment 对 PostgreSQL MVCC snapshot boundary 措辞不准确 —— `SET TRANSACTION` 设置的是 transaction characteristics，真正 snapshot 由第一次 snapshot-taking query 建立）= **Human Accepted non-blocking P3** documentation / comment accuracy finding，**未**修复（修注释会改变 Human-Accepted reviewed candidate）。详见 `dev_log/2026-09-14-se-02c-final-acceptance-closeout.md`、`dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md` 与 `dev_log/2026-09-13-se-02c-forward-outcome-calculator.md`。
- PRE-01A-D1 V1（已批准，2026-09-14 Human Acceptance = `CONFIRMED`）：Real AI V1 Trade Decision Experiment Contract（Accepted Design artifact = `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`；Human-Accepted candidate = `e3fb721c678e2b3ca0af6fb4663f349c6a641159`，branch `design/pre-01a-d1-real-ai-v1-contract`，immutable；Independent Re-Review = `PASS`；`D1-R1` / `D1-R2` = `CLOSED`）。冻结以下语义：
  - **Placement**：Real AI V1 placement = **`C. Trade Decision` only**。**AI = Advisory；Deterministic System = Authority**；AI 不得获得 repository/risk/execution/accounting/protection 任何 handle。
  - **WITHOUT-AI selection benchmark** = **`ALL_ELIGIBLE_LONG_SHADOW_V1`**（对每个已正式准入的 Opportunity 一律「参与 LONG」，确定性、不调用 provider、shadow-only、不产生 TradePlan/intent/order/Fill/Position/Ledger mutation；缺失/陈旧 reference evidence 与 `INSUFFICIENT_DATA` / `INVALID` 结果保持显式、不得静默丢弃）。
  - **V1 causal claim** = **REAL AI TRADE-DECISION SELECTION / PARTICIPATION EDGE ONLY**，treatment variable 仅为 `PARTICIPATE_LONG` vs `NO_LONG`。**明确不得**把该实验结论扩展为 **entry edge / stop edge / target edge / sizing edge / full `AIAnalysis` package edge / executed-trade edge**（这些 claim 需要另经 Human 验收的 symmetric economic comparison contract，D1 既未设计也未授权）。
  - **Decision identity**：**one `decision_invocation_id` → exactly one collision-free logical durable final decision**（retry 共享同一 invocation，每次 attempt 有独立 identity 与 provider-attempt provenance；durable final identity 在 `experiment_id` / `pair_id` / `arm_id` / `input_binding_digest` / prompt version / schema version / configured treatment version 上 collision-free，retry 不得产生第二个 actionable final decision）。
  - **Provider 边界**：**Single Primary Provider；No automatic fallback；No model voting**；provider-native strict structured output REQUIRED；tools/autonomous loop/Agent Runtime/LangGraph/multi-provider router EXCLUDE。
  - **Activation gates**：**Gate A = Provider Shadow Activation**（真实 provider 调用 + durable provenance，零新增风险权限）；**Gate B = Paper Economic Activation**（每 pair 恰好一个预先声明的 authoritative arm，activation/safety gate，不构成 edge 证明）；**Gate C = Selection / Participation Edge Evidence**（仅 selection/participation edge 判定，不授权 Live）。
  - **依赖边界**：**SE-02C = REUSE**（不重算、不重定义其 cost model / horizon identity / revision chain / completeness 语义）；**SE-02D = required before Gate C edge declaration**（family/arm aggregation 与 Expectancy 尚未实现/验收，SE-02D 前 Gate C 不得通过）；**Runtime Host = separate future design/research boundary**（D1 不选型、不设计 asyncio TaskGroup / Docker supervisor / systemd / Celery / Redis / Kafka / Kubernetes）。
  - **边界**：本 Acceptance **不**声称 Real AI implemented / activated、AI edge proven、SE-02D complete、Runtime Host complete 或 Live Trading enabled；Real AI runtime activation 仍 `NOT STARTED / NOT ACTIVATED`，Real AI provider runtime evidence 仍 `NOT PRESENT`，`SE-02D` / `Integrated Runtime Host` 仍 `NOT STARTED`，live Opportunity → G3 integrated handoff 仍 `NOT ACCEPTED / NOT ACTIVE`。详见 `dev_log/2026-09-14-pre-01a-d1-real-ai-v1-experiment-contract.md`。

- PRE-01B-D1 V1（已批准，2026-09-15 Human Acceptance = `CONFIRMED`）：Integrated Runtime Host
  Formal Design（Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`；Human-Accepted reviewed
  candidate = `80cb2babe9f55b3a3b1dc2d3b7913a405607ac22`，branch
  `design/pre-01b-d1-runtime-host-contract`，immutable；Independent Review = `PASS WITH
  NON-BLOCKING FINDINGS`；P0 / P1 = `NONE`）。冻结以下架构决策（**仅** Design
  层；Implementation 未开始）：
  - **Composition owner**：`RuntimeHost` = 唯一 production composition root / owner；
    production 只存在一个 Runtime。
  - **Lifecycle anchor**：FastAPI `lifespan` = Host 唯一 activation boundary（创建 /
    进入 / 退出）；它 **不是** process supervisor；模块导入与普通
    request 不创建 Runtime。
  - **Structured concurrency**：AnyIO TaskGroup / CancelScope 为唯一 Host
    structured-concurrency model。
  - **TaskGroup ≠ restart supervisor**：AnyIO TaskGroup 不提供自动 restart 语义；
    child failure 按失败矩阵 fail closed 并产生 external-restart signal。
  - **Process model**：single process / one Uvicorn worker / `reload=off`；不得依赖
    多 worker 共享 Runtime。
  - **Duplicate fence**：PostgreSQL session advisory lock = duplicate-host
    defense-in-depth（补充部署约定，非替代）。
  - **DB ownership**：Host 拥有 DB engine / session lifecycle 与 disposal（补上当前无
    production engine dispose owner 的缺口）。
  - **State authority**：latest market / BBO observation 可为 ephemeral；durable business /
    state-version authority 仍为已接受的 durable state —— Host state 不替代、
    不重定义 G4 durable state，且 `RuntimeHost` / `LiveMarketState` **不得**自造
    并行 `state_version` authority。
  - **Startup ordering**：DB / singleton → recovery-only live BBO warm-up → Recovery +
    startup reconciliation → bounded safety / G2 runtime → readiness conjunction；
    recovery-only fresh-BBO warm-up 先于 new-risk readiness。
  - **Readiness**：API liveness **不**等于 trading readiness；STALE / reconnect / SAFE_MODE /
    DB failure 返回诚实的 503 + reason。
  - **Protection isolation**：Protection path 与 Scanner / 未来 AI backpressure 隔离；
    per-instrument bounded non-lossy safety lanes，safety BBO 永不静默 drop / coalesce；
    scanner overload 不阻塞 protection。
  - **Shutdown**：30 s graceful + 5 s shielded disposal reserve；producer-first stop、
    engine-last dispose。
  - **G2→G3 live advisory handoff** = `DEFERRED`（Host Core V1 不构造 AI queue /
    consumer / provider）。
  - **Real AI** 保持 `NOT ACTIVATED`；本设计不新增 Real AI business timeout 数值，
    继承 PRE-01A-D1 absolute `decision_deadline_at` 语义。
  - **Periodic reconciliation** = detector-only（+ 已接受 fail-closed transition），
    不 repair。
  - **OS / service process supervision**（如 WinSW）= Host Core 之外的独立边界，
    future task。
  - Memory P2 `N01-7-R01-RR-P2-01` 保持 observation-only / `REMAINS / NON-BLOCKING`。
  - **Implementation carry-ins**：`F-01`（`state_version_for` 实现必须绑定已接受的
    durable state/version authority）；`F-02`（safety queue capacity `64` = 初始可配置
    默认值，Implementation Acceptance 必须以 queue high-water / runtime evidence
    验证 sizing，非免证据永久常量）。
  - **边界**：本 Acceptance **仅**接受 Formal Design，不构成
    `Integrated Runtime Host Implementation`（`NOT STARTED`）/ runtime validation / Real AI
    activation / G2→G3 activation / `SE-02D` / Live Trading / profitability / edge 的任何进度。
    详见 `dev_log/2026-09-15-pre-01b-d1-final-acceptance-closeout.md`。

- PRE-01B-I1 V1（已批准，2026-09-15 Human Acceptance = `CONFIRMED`）：Integrated Runtime Host Core V1 Implementation（Human-Accepted reviewed candidate = `68dd7e96cc8547433794b045fa99e1e9dc5b7892`，branch `pre-01b-i1-fix-01-runtime-host-lifecycle`，immutable；Original Candidate = `b66e17d34173156b3797b664dbe09625511a0a11`；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS`；P0 / P1 = `NONE`）。冻结以下实现层决策（仅 Implementation 层；Design 决策见 `PRE-01B-D1 V1`）：
  - **RuntimeHost Core V1 accepted**：集成 RuntimeHost 作为唯一 production composition owner。
  - **Host singleton fence** 使用 PostgreSQL session advisory lock（defense-in-depth，非替代部署约定）。
  - **SQLAlchemy transaction**：由 lock/liveness SQL 创建的 transaction 必须结束，session advisory lock 仍持有。
  - **Critical Host failure**：先 bounded cleanup，再 `HostTerminalResult`，再 lifespan/process failure signal。
  - **No in-process child restart supervisor**：child failure 按失败矩阵 fail closed 并产生 external-restart signal。
  - **DatabaseResources** 仅在实际成功 dispose 后才报告 disposed。
  - **External cancellation** 不能绕过 bounded shielded mandatory cleanup。
  - **Host telemetry / history retention** 有界（bounded）。
  - **Enabled Host V1** 需 BTC-USDT + ETH-USDT。
  - **Real AI / G2→G3 / Live** 在本 Acceptance 之外（仍 `NOT ACTIVATED / NOT ACCEPTED / DISABLED`）。
  - **`F-01`** durable `state_version` authority 保留（Host 不造并行 authority）；**`F-02`** safety queue capacity `64` 仍 configurable / evidence-based（非永久架构常量）。
  - **边界**：本 Acceptance **仅**接受 Implementation Core V1，不构成 OS/service deployment / Real AI activation / G2→G3 activation / `SE-02D` Production complete / Live Trading / profitability / edge 的任何进度。详见 `dev_log/2026-09-15-pre-01b-i1-final-acceptance-reconciliation.md`。

- PRE-01B-D2 V1（已批准，2026-09-17 Human Acceptance = `CONFIRMED`）：AdvisoryIngress /
  durable G2→G3 Activation Contract Formal Design（Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`；Human-Accepted
  reviewed candidate = `cce1ae7b862b038a99976c802c0985df01b35285`，branch
  `design/pre-01b-d2-fix-05-return-completion-authority`，immutable；Independent Re-Review =
  `PRE-01B-D2-FIX-05 = PASS`；P0 / P1 / P2 / P3 = `NONE`；closeout branch =
  `pre-01b-d2-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`）。冻结以下架构决策
  （**仅** Design 层；`PRE-01B-I2` Implementation 未开始、本 Acceptance 未授权）：
  - **Host-owned AdvisoryIngress boundary**：未来 `AdvisoryIngress` 由 `RuntimeHost` 拥有；
    producer 只在已接受的 G2 formal transaction 内产出 exact qualifying record。
  - **Exact admission Evidence revision binding**：admission 绑定同 transaction 内 staged 的
    exact Evidence revision（opportunity / evidence_id / revision / evidence_hash /
    feature_snapshot_hash），**不是** SE-02D canonical head；Admission Evidence 与
    Canonical Evidence Head 是两个必须区分的概念。
  - **Immutable decision invocation identity**：one `decision_invocation_id` → exactly one
    collision-free logical durable final decision（沿用 PRE-01A-D1 已接受语义，retry 共享
    invocation 但拥有独立 attempt identity）。
  - **Bounded in-process advisory dispatch**：bounded / non-blocking queue；无 durable `QUEUED`
    状态；`REJECT NEWEST`；queue full 的 durable 终态 = `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`。
  - **PostgreSQL durable correctness authority**：admission Evidence / Invocation / terminal
    result 的 durable 正确性权威在 PostgreSQL，不在进程内状态；process death 不 fabricate release。
  - **Shadow-safe Gate A boundary**：Gate A consumer = shadow advisory decision path，
    provenance-only write allow-list；`G3Workflow` **不**在 Gate A 使用。
  - **Provider / DB separation**：provider I/O 持有 zero DB resource。
  - **Protection isolation**：Advisory 不得消费 Protection-reserved 容量；shared-pool 声明
    仅为 attribution-only（`H_o + H_g + U <= A`、`A + R <= C`）。
  - **Accepted DB timeout / SAVEPOINT semantics**：caller-owned timeout capture / restore、
    no idle/client cancel、rollback / connection-validity 规则不变；core flush → immediate
    token try → `begin_nested()`；token failure = zero Advisory SQL + zero SAVEPOINT。
  - **Accepted connection-return completion authority**：容量释放需要完整 positive predicate
    （同 generation pool observation + owner cleanup 成功 + 同 epoch / lease / cleanup attempt
    authoritative）；**no callback-only capacity release** —— 单一 callback、单次
    `invalidate()` return 或 checkin observation 均**不**增加容量；unknown / cancelled cleanup
    退化为 `RETURN_UNCERTAIN_RETIRED` 并 fail closed。
  - **Gate A / Gate B separation**：显式 activation level；Gate B startup fail-closed 直至获批。
  - **边界**：本 Acceptance **仅**接受 Formal Design，**不**构成 `PRE-01B-I2` implementation /
    live G2→G3 activation / Real AI activation / provider configuration / Gate A activation /
    Gate B activation / Gate C PASS / Live authorization / profitability / edge 的任何进度。
    Human Decision Pack：Pack A = `NONE`；Pack B（numeric provider / model / retry / timeout /
    deadline / pool / concurrency / shutdown / queue / cost / retention 数值）与 Pack C（Gate-A
    observation / sufficiency / acceptance thresholds）仍 `UNRESOLVED`。详见
    `dev_log/2026-09-17-pre-01b-d2-final-acceptance-closeout.md`。

- SE-02D-D01 V1（已批准，2026-09-15 Human Acceptance = `CONFIRMED`）：Family Aggregation /
  Forward-Outcome Expectancy Contract V1（Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`；Human-Accepted
  candidate = `245b068199b7e6f3d32bf67e3b00163e4804afdf`，branch
  `design/se-02d-d01-family-aggregation-expectancy`，immutable；Independent Initial Review =
  `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS`；`D01-R1` / `D01-R2` = `CLOSED`；
  `D01-R3` = `CLARIFIED / NON-BLOCKING`；Closeout Reconciliation Base =
  `9e0553f5dee3fcb4a2dad0b672280657235656aa`；集成方法 = `FAST-FORWARD ONLY`）。冻结以下 V1
  决策（**仅** Design 层；Implementation 未开始；权威细节以 Accepted Design artifact 为准，
  本节不复制全文）：
  - **Canonicalization**：先取完整 visible Evidence revision chain → 校验 → canonical Evidence
    head → 该 head 的 exact-horizon 完整 visible Outcome chain → canonical Outcome head 或
    `NO_OUTCOME` → 再由 heads 决定 membership / coverage / measurement compatibility。
    **Fold complete revision chains before membership**：revision-mutable 字段不得在 head
    selection 前用于过滤；superseded revision 不保留旧 population sample 或旧经济统计。
  - **Population Key** = `family_id + family_version + instrument_id + market_type +
    source_type + source_identity + evidence_contract_version`；**Population Aggregate
    Identity** = `Population Key + fixed horizon`，它拥有 eligible / maturity / coverage
    denominator（Outcome 缺失时 coverage membership 仍完整存在）。
  - **Measurement Signature** = `outcome_contract_version + calculator_version + cost_policy +
    cost_model_version + outcome_source_type + outcome_source_identity`，只由 canonical Outcome
    head 派生，**只**负责经济/计算兼容性，不拥有 coverage membership。
  - **`source_manifest_id` = provenance / stratification**，**不是** population identity、
    **不是** measurement-signature 字段（有限、预先声明的 comparability rule）。
  - **Mixed Measurement Signatures** = headline fail closed：`INCOMPATIBLE_MEASUREMENT_SIGNATURES`，
    coverage 仍完整输出。
  - **Primary Expectancy** = 唯一 compatible signature 下 `mean(cost_adjusted_forward_return)`
    over canonical COMPLETE samples；**Primary Horizon = `5m`**；**Secondary Horizons =
    `30s / 15m / 1h`** 分别报告，不平均、不合并、不换 primary。
  - **Coverage = population-based**：`COMPLETE / INSUFFICIENT_DATA / INVALID / MISSING_OUTCOME`
    必须显式输出、不得静默消失；`coverage_rate` / `settlement_rate` 定义见 artifact §8。
  - **Statistical Sufficiency** = 已接受的确定性规则（无固定 raw N；100% coverage +
    `n_clusters >= 3` + 非退化 95% interval + interval excludes 0 + leave-one-cluster-out
    稳定）；**Uncertainty** = 已接受的 deterministic overlap-cluster percentile bootstrap，
    双侧 95%，**无 SciPy production dependency**。
  - **Tail Evidence** = `worst_observation` + `worst_decile_mean`；**V1 不设 tail pass/fail
    threshold**。
  - **Instrument Pooling = NO**；**K/D/K = SE-02D V1 不输出任何 KEEP / DOWNWEIGHT / KILL
    label**；**Persistence = deterministic on-demand derived aggregate**（无新表 / migration /
    worker）；**Regime Gate = `NONE_IN_SE02D_V1`**；**Historical revision-as-of = 无独立
    prerequisite 前 `NOT SUPPORTED`**。
  - **边界**：**`SE-02D capability complete != Gate C PASS`**、**`Gate C PASS != Live
    authorization`**；SE-02D-D01 Acceptance **不**构成 `SE-02D` implementation
    （`NOT STARTED`）/ family aggregation 实现 / expectancy 实现 / Gate C PASS / Real AI
    activated / Live authorized；Gate C 前仍需 experiment/pair/arm identity 与 durable regime
    两个独立 prerequisite。详见 `dev_log/2026-09-15-se-02d-d01-final-acceptance-closeout.md`。

- SE-02D-I01（已批准 / 已验收，2026-09-15 Human Acceptance = `CONFIRMED`）：Deterministic
  Aggregation Core = `ACCEPTED / COMPLETE`；Human-Accepted reviewed candidate =
  `13b37dff4b8150dea869ba6257ae9f3df24cc1e5`（branch `se-02d-i01-aggregation-core`，
  immutable）；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent
  Re-Review = `PASS`；`SE02D-I01-R1` / `R2` / `R3` = `CLOSED`；集成方法 = `FAST-FORWARD
  ONLY`。权威细节以 Accepted Design artifact 与 `dev_log/2026-09-15-se-02d-i01-aggregation-core.md`
  为准，本节不复制契约全文。
  - **实现契约澄清（accepted implementation-contract clarification）**：
    `UNCERTAINTY_METHOD_VERSION` = `"se02d-overlap-cluster-percentile-bootstrap-v1"`。
    Accepted `SE-02D-D01` §10.1 要求该 version identifier 进入 deterministic bootstrap seed，
    但**未**冻结其字面量 ⇒ 由 Human Design Clarification 补齐。它是**已接受**的
    deterministic overlap-cluster percentile bootstrap V1 的 version identifier，
    **不修改任何统计语义**（bootstrap 语义、RNG 语义、95% 双侧区间、10,000 replicates、
    clustering、LOCO、coverage、sufficiency、tail evidence、Gate C 边界均不变）；
    Accepted D01 design artifact 逐字**未**改。
  - **边界**：`SE-02D-I01 = ACCEPTED / COMPLETE` **≠** `SE-02D` Overall complete ——
    PostgreSQL loading / revision-chain folding / canonical-head loading / current-snapshot
    orchestration 已于 `SE-02D-I02` 实现并验收（见下方 `SE-02D-I02` 条目）；population
    grouping + 调用 I01 `aggregate()` 已于 `SE-02D-I03` 实现并验收（见下方 `SE-02D-I03`
    条目）；`SE-02D V1` capability 完成边界其后已由 `SE-02D-CLOSE-D01`（2026-09-16 Human
    Acceptance = `CONFIRMED`）接受为 `COMPLETE AFTER I03`（见下方 `SE-02D-CLOSE-D01` 条目）；
    aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend /
    runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical
    revision-as-of 仍 `OPEN`；`SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall Final
    Acceptance Closeout 转 `ACCEPTED / COMPLETE`；
    `Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`。详见
    `dev_log/2026-09-15-se-02d-i01-final-acceptance-closeout.md`。

- SE-02D-I02（已批准 / 已验收，2026-09-15 Human Acceptance = `CONFIRMED`）：
  Current-Snapshot Revision Folding = `ACCEPTED / COMPLETE`；Human-Accepted reviewed
  candidate = `9b860437b14f64192d3298d30c0204bed1b118f8`（branch
  `se-02d-i02-current-snapshot-folding`，immutable）；Independent Initial Review =
  `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS`；`SE02D-I02-R1` / `R2` /
  `R3` = `CLOSED`；集成方法 = `FAST-FORWARD ONLY`（latest-main content-level
  carry-forward）。本节仅为**实现验收指针 + 已接受边界**，权威细节以 Accepted `D01` /
  `I01` 行为与 `dev_log` 为准，**不**新增设计决策：
  - **Accepted implementation boundary**：`CURRENT_STABLE_SNAPSHOT` only —— 一个
    PostgreSQL `REPEATABLE READ` + `READ ONLY` 快照拥有整个 projection；`as_of` 权威 =
    数据库 `statement_timestamp()`；**无** historical caller-supplied `as_of`。
  - **无新统计语义**：`I01` 仍为 canonical manifest base fields、fingerprint、bootstrap、
    statistics、uncertainty、sufficiency 的权威；I02 只在该 base 上附加修订链身份字段。
  - **已实现**：全量可见 Evidence revision-chain 校验 / 折叠、canonical Evidence head
    selection、精确 horizon Outcome revision-chain 校验 / 折叠、canonical Outcome head /
    `NO_OUTCOME`、canonical Evidence ↔ Outcome cross-integrity、`CanonicalScopeFacts`
    projection、revision-aware canonical manifest。
  - **边界**：`SE-02D-I02 = ACCEPTED / COMPLETE` **≠** `SE-02D` Overall complete ——
    population grouping + orchestration that invokes I01 `aggregate()` 已于 `SE-02D-I03`
    实现并验收（见下方 `SE-02D-I03` 条目）；`SE-02D V1` capability 完成边界其后已由
    `SE-02D-CLOSE-D01`（2026-09-16 Human Acceptance = `CONFIRMED`）接受为
    `COMPLETE AFTER I03`：aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；
    API / frontend / runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`；
    historical arbitrary revision-as-of 仍 `OPEN`；`SE-02D Overall` 其后已于 2026-09-16 经
    SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；`Gate C = NOT PASSED`；
    `Live = NOT AUTHORIZED`。详见
    `dev_log/2026-09-15-se-02d-i02-final-acceptance-reconciliation.md`。

- SE-02D-I03（已批准 / 已验收，2026-09-16 Human Acceptance = `CONFIRMED`）：
  Population Grouping + Aggregate Orchestration = `ACCEPTED / COMPLETE`；Human-Accepted
  reviewed HEAD = `20a7c333abf81077c409811302331119dff485a5`（branch
  `se-02d-i03-fix-01-projection-identity-validation`，immutable）；Original Reviewed
  Candidate = `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4`（branch
  `se-02d-i03-population-aggregate-orchestration`，immutable）；Initial Independent
  Review = `FAIL — FIX REQUIRED`；`SE02D-I03-R1`（P1）= `CLOSED`；FIX-01 Independent
  Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；集成方法 = `FAST-FORWARD ONLY`。
  本节仅为**实现验收指针 + 已接受边界**，权威细节以 Accepted `D01` / `I01` / `I02` 行为
  与 `dev_log` 为准，**不**新增设计决策：
  - **Accepted implementation boundary**：I03 消费一份 I02
    `CurrentSnapshotProjection`，在 facts ↔ revision-aware manifest 一一对应完整性门
    （fail closed）之后按完整结构 `PopulationKey` 分组，每个 population **恰好一次** I01
    `aggregate()` 调用，并输出确定性有序 `tuple[AggregationResult, ...]`；薄 async
    wrapper 只做一次 `reader.read(horizon)`。
  - **无新统计 / 身份语义**：`I01` 仍为 statistics / uncertainty / sufficiency /
    fingerprint 的权威；`I02` 仍为 revision folding / snapshot / canonical head 的权威；
    I03 未新增 Population Key、Measurement Signature、horizon 语义，也未做二次审判。
  - **边界**：`SE-02D-I03 = ACCEPTED / COMPLETE` **≠** `SE-02D` Overall complete ——
    其完成边界其后已由 `SE-02D-CLOSE-D01`（2026-09-16 Human Acceptance = `CONFIRMED`）
    接受为 `SE-02D V1 CAPABILITY COMPLETE AFTER I03`：aggregate capability =
    `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend / runtime product consumer =
    `NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical arbitrary revision-as-of 仍 `OPEN`；
    `SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转
    `ACCEPTED / COMPLETE`；`Gate C = NOT PASSED`；
    `Live = NOT AUTHORIZED`。详见
    `dev_log/2026-09-16-se-02d-i03-final-acceptance-closeout.md`。

- SE-02D-CLOSE-D01（已批准 / 已验收，2026-09-16 Human Acceptance = `CONFIRMED`）：V1 Completion
  Boundary Reconciliation = `ACCEPTED / COMPLETE`；Independent Review = `PASS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted candidate = `a9e615726ee964c02a72ea6cbff490d3d74e08f7`（branch
  `design/se-02d-close-d01-v1-completion-boundary`，immutable）；Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-CLOSE-D01-V1-Completion-Boundary-Reconciliation.md`
  （status = `ACCEPTED DESIGN`）；Accepted Main before =
  `779eaf1ca781d64733c8264b0a06c7601deacdba`；集成方法 = `FAST-FORWARD ONLY`。
  本条目**不**新增设计决策，只记录被 Human 接受的完成边界与措辞调和：
  - **Accepted completion conclusion**：`SE-02D V1 CAPABILITY COMPLETE AFTER I03` —— Accepted
    D01 current-snapshot V1 责任已由 I01 + I02 + I03 完整实现（该 reconciliation 的 coverage
    verdict = `ACTUAL GAP = NONE FOUND`）。
  - **Accepted callable 边界**：`CurrentSnapshotRevisionReader.read(horizon)` →
    `CurrentSnapshotProjection` → `aggregate_projection(projection)` →
    `tuple[AggregationResult, ...]`；`aggregate_current_snapshot(reader, horizon)` = 恰好一次读 +
    同一纯编排。SE-02D V1 **不** own production consumer；RuntimeHost session-factory ownership
    **未**改变（属未来 consumer composition question，非 V1 blocker）。
  - **consumer 分类（已接受）**：HTTP API / FastAPI router / frontend / dashboard / operator
    panel / RuntimeHost child / scheduler / worker-daemon / aggregate persistence / materialized
    view / automatic consumer = `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT`（`DEFERRED TO
    FUTURE CONSUMER / PRODUCT / GATE C TASK AS APPLICABLE`，**不**写“已完成”）。
  - **措辞调和（已接受）**：aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 +
    I03`；historical arbitrary revision-as-of = `OPEN / NOT SUPPORTED / FUTURE PREREQUISITE`；
    `I04 = NOT REQUIRED FOR SE-02D V1`。
  - **边界**：本 Acceptance 当时**不**构成 `SE-02D` Overall Acceptance / COMPLETE
    （该句为 CLOSE-D01 收尾时；`SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall Final
    Acceptance Closeout 转 `ACCEPTED / COMPLETE`）；`Gate C prerequisites =
    OPEN`；`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；
    `KEEP / DOWNWEIGHT / KILL = NOT OWNED BY SE-02D V1`；`SE-02D V1 capability complete !=
    Gate C PASS`、`Gate C PASS != Live authorization`。详见
    `dev_log/2026-09-16-se-02d-close-d01-final-acceptance.md`。

- SE-02D Overall（已批准 / 已验收，2026-09-16 Human Acceptance = `CONFIRMED`）：Family
  Aggregation / Forward-Outcome Expectancy = `ACCEPTED / COMPLETE`；Overall Final Review =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`（P0 = `NONE` / P1 = `NONE` /
  P2 = `NONE`）；Human-Accepted reviewed baseline =
  `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`（immutable）；集成方法 = `FAST-FORWARD ONLY`。
  本条目**不**新增产品语义，只记录被 Human 接受的总体验收与完成边界：
  - **Overall 状态**：`SE-02D Overall = ACCEPTED / COMPLETE`；`SE-02D = ACCEPTED / COMPLETE`。
  - **Completion boundary**：`SE-02D V1 CAPABILITY COMPLETE AFTER I03`；accepted lineage（`SE-02D-D01` /
    `I01` / `I02` / `I03` / `CLOSE-D01`）均 `ACCEPTED / COMPLETE`；aggregate capability =
    `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`。
  - **`I04 = NOT REQUIRED`**；**不存在**属于 SE-02D V1 的 accepted API / frontend /
    runtime consumer requirement（= `NOT REQUIRED FOR SE-02D V1 COMPLETION`）。
  - **Capability 状态调和**：Family-level current-snapshot Forward Outcome Expectancy =
    `SUPPORTED / ACCEPTED via SE-02D V1`（`PRODUCT_REQUIREMENTS.md` §10 已作最小真值修正）。
    **不**声称 Trading Edge / executed-trade edge / Real AI edge / `Gate C PASS` / generic
    strategy profitability 已证明；**Deterministic Replay != Trading Edge Proof** 保持不变。
  - **P3 closure**：`SE02D-OVERALL-R01-P3-01`（陈旧 `marketpulse.edge` package docstring）与
    `SE02D-OVERALL-R01-P3-02`（陈旧 capability / group metadata）= `CLOSED`；两者均为
    documentation / metadata finding，Human Acceptance 时为 `NON-BLOCKING`。
  - **边界**：historical arbitrary revision-as-of = `OPEN / NOT SUPPORTED / FUTURE
    PREREQUISITE`；experiment / pair / arm identity = `OPEN GATE C PREREQUISITE`；arm-level
    selection Expectancy / delta = `FUTURE CONSUMER`；durable regime identity / criteria =
    `OPEN GATE C PREREQUISITE`；Gate C immutable evidence artifact retention = `FUTURE GATE C
    EVIDENCE TASK`；`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT AUTHORIZED /
    NOT ACTIVATED`；`KEEP / DOWNWEIGHT / KILL = NOT OWNED BY SE-02D V1`；
    `SE-02D ACCEPTED / COMPLETE != Gate C PASS`、`Gate C PASS != Live authorization`、
    `SE-02D Expectancy capability != Trading Edge Proof`；下一 Acceptance Group =
    `NOT STARTED / REQUIRES SEPARATE HUMAN-AUTHORIZED DECISION`（本收尾**不**选择、**不**启动）。

- UI-V1-D01 V1 = **ACCEPTED / FROZEN / REPOSITORY-INTEGRATED**（2026-09-17 Human Acceptance =
  `CONFIRMED`）：MarketPulse UI V1 Formal Design。Accepted Design artifact =
  `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（Artifact status =
  `ACCEPTED / FROZEN`；included closure `UI-V1-D01-FIX-01` = `INCLUDED / CLOSED`；
  Independent Final Review = `PASS — READY FOR FORMAL FREEZE`；Independent Final Repository
  Review = `PASS`；P0 / P1 / P2 / P3 = `NONE`；task branch = `design/ui-v1-d01-formal-freeze`
  （该窗口自身**不** merge `main`，其后由 Final Acceptance Closeout 收编）；repository
  persistence `UI-V1-D01-FINAL-DOC-01` = `COMPLETE`（`FIX-01` / `FIX-02` = `COMPLETE`）；
  Human-Accepted / Reviewer-approved final candidate =
  `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4`（branch `design/ui-v1-d01-final-doc-fix-02`，
  immutable；远端同 SHA、未被移动）；closeout branch = `ui-v1-d01-final-acceptance-closeout`；
  集成方法 = `FAST-FORWARD ONLY`，已收编 `main`）。
  本条为**决策摘要**：全部细节（逐条契约、指标与状态表、API / 传输边界、Out of Scope 清单、
  未来验收边界）以该 artifact 为唯一权威，本条目**不**复制；设计持久化见
  `dev_log/2026-09-17-ui-v1-d01-formal-design-freeze.md`，本条压缩见
  `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-01.md`，本收尾见
  `dev_log/2026-09-17-ui-v1-d01-final-acceptance-closeout.md`。冻结的决策层要点：
  - **产品定位**：**Read-Only Paper Trading Operations & Evidence Terminal**（只读纸面交易运维
    与证据终端）；**不**是手工交易终端 / 运行时控制面板 / Live Trading UI / AI 自主控制界面。
  - **五页 IA（恰好五个）**：总览 / 市场与机会 / 策略研究 / 交易与仓位 / 系统；
    **AI 不获得独立顶层页**（仅上下文性出现在 Opportunity / Trading Trace、decision lineage、
    System activation status）。
  - **Read-Only 业务行为**：指 **Read-Only Business UI**，UI V1 **无**任何 mutation 控制
    （下单 / 平仓 / 撤单 / SL-TP 修改 / 计划修改 / 暂停 / 恢复 / 急停 / 封禁 / 解除 / 事件处置 /
    对账修复均不提供）；Authentication Session Establishment via Login POST 准许。
  - **Authority 边界**：前端是**呈现层**（格式化 / 枚举翻译 / display-only spread / 按权威观测
    时间戳渲染 age），**不是**业务权威；**不得**判定 Risk Admission、Position 生命周期、
    Canonical Evidence、Aggregate Population、Edge Verdict、Causal Trace、Protection
    Authority，**不得**发明 account / economic 指标，**不得**推断 Real AI 激活状态。
  - **双轴数据能力模型**：Axis A 读面（`A` = 当前正式 HTTP Read Contract 存在 / `B` = 已接受
    backend truth 存在但需要 Product Read API / `C` = 无当前可消费正式 Read Truth）× Axis B
    运行可用性（`ACTIVE` / `ACCEPTED_NOT_INTEGRATED` / `NOT_ACTIVATED`）；两轴**相互独立**，
    UI 按 backend 显式能力状态渲染，**不得**由一轴推断另一轴。
  - **Exact Edge Population**：Aggregate identity = Exact Population Key + Horizon；
    **前端不得合并 / 池化 populations**，**不得**自行猜测 population。
  - **durable Position Protection 权威**：protection-lifetime 唯一权威 = OPEN Position 上的
    durable protection snapshot（原子权威组：全部为 null 或全部完整）；Current Protection
    **绝不**从最新 Active Plan 推断；`Plan Expired` **不**蕴含 `Position Protection Expired`；
    `UNPROTECTED != UNKNOWN`。
  - **Product Read Projection 原则**：五个逻辑读模型（`MarketScannerRead` /
    `OpportunityTraceRead` / `EdgeAggregateRead` / `TradingAuditRead` /
    `SystemIncidentRead`）是 **read projections**，**不是**新的业务权威，
    **不得**为每个视觉组件创建 endpoint。
  - **当前 live producer 局限（冻结真值）**：当前 `RuntimeHost` / Scanner runtime **尚未**提供
    完整接通的 `live G2 → Formal Opportunity Evidence → Forward Outcome scheduling →
    live Advisory / G3`；`PRE-01B-D2` Formal Design 已 `ACCEPTED` 但 `PRE-01B-I2` **未**实现 /
    **未**激活；UI 实现**绝不**允许静默接通这些能力。
  - **实现顺序（仅排序，不授权）**：`UI-F01`（Frontend Foundation）→ `UI-RD01`（Product Read
    API Formal Design）→ `UI-I01` → `UI-I02` → `UI-I03` → `UI-I04` → `UI-I05` → `UI-I06`。
  - **边界**：本 Acceptance **仅**接受 Design 本身，**不授权任何实现**；UI 实现 / 前端实现 /
    后端 Product Read API 实现 = `NOT STARTED`；`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；
    Real AI = `NOT ACTIVATED`；live `G2→G3` Advisory = `NOT ACTIVE`；Forward Outcome 运行时
    自动生产 = `NOT INTEGRATED`（无 Product consumer）；`Gate C = NOT PASSED`；
    `Live = NOT AUTHORIZED`；Trading Edge = **未证明**。

- UI-F01-I01 V1 = **IMPLEMENTED / READY FOR INDEPENDENT REVIEW**（**非** ACCEPTED / COMPLETE；
  Independent Review 与 Human Acceptance 均未发生）：Frontend Foundation 的已批准复用决策落地。
  本条为**最压缩持久化**，来源 = Human 授权的 `UI-F01-I01` 任务卡（Task Base =
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`）；全部实现与证据细节以
  `dev_log/2026-09-17-ui-f01-i01-frontend-foundation.md` 为唯一权威，本条目**不**复制。
  冻结要点：
  - **Router** = `react-router`（Declarative 模式）；**不**使用 Framework Mode / SSR，
    **不**把 route loader 作为服务端数据所有权层；**不**自建 Router 框架。
  - **Server Query / Cache** = `@tanstack/react-query`，拥有服务端请求生命周期 / 响应缓存 /
    请求去重 / refetch 协调 / invalidation；**不**拥有 MarketPulse 业务新鲜度。
    **TanStack Query cache `stale` != MarketPulse backend business `STALE`**，**禁止**由 Query
    cache 状态推导业务 `FRESH / STALE`。
  - **API Client** = `openapi-fetch`（链路：FastAPI OpenAPI → `openapi-typescript` →
    `generated.ts` → `openapi-fetch` → frontend queries）；**禁止** Axios，**禁止**自建
    HTTP 框架；应用请求用相对 `/api/...`，**禁止**硬编码 `http://127.0.0.1:8000`。
  - **Global Client State**：**不**引入 Redux / Redux Toolkit / Zustand / MobX / XState。
    所有权冻结：服务端状态 → TanStack Query；可分享 route / filter 状态 → URL / Router；
    认证会话 → 专用 Auth Session Boundary；组件局部状态 → React local state；
    通用跨页 store = `NOT REQUIRED IN UI-F01`。
  - **Auth Session Boundary**：恰好一个，拥有 bearer session；access token 持久化 =
    `sessionStorage`；**密码永不持久化**（localStorage / sessionStorage / cookie / Query Cache /
    generated state / logs 均不得出现）；**不**解析 token 生成独立前端 auth 权威；
    backend `401` 是唯一 auth authority；**不存在** refresh token 机制，**禁止**新建。
  - **401 语义**：受保护请求 `401` ⇒ 清 token/session + 清已认证 Query cache + 在可行时保留
    原定安全内部路由 + 进入 Login 边界；**login POST 的 `401` = 凭据错误**（显示失败、留在登录页、
    **不**产生重定向循环）。`/ready` `503` **不**属此列。
  - **`/ready` 503 语义**：`503` + 合法 readiness body ⇒ 保留 body 并映射为语义 `NOT_READY`，
    视为**成功解释**；**不**得成为 `NetworkError` / 通用后端故障 / unavailable /
    自动重试失败；**Readiness != Risk Admission**，**禁止**由 ready 推断 `risk_admission_open`。
  - **Retry 策略**：`401` 不重试；普通 `4xx` 不重试；`/ready` `503` 不是 error 故不重试；
    network / 可重试 `5xx` 仅**有界**重试；**无**默认高频轮询、**无**全局 refetch interval。
  - **Vite 开发 proxy**：`/api/*` → `http://127.0.0.1:8000/api/*`，**不** rewrite `/api`；
    **禁止**以宽泛开发 CORS 作为绕行方案。
  - **OpenAPI 生成纪律**：`generated.ts` 保持 AUTO-GENERATED、**禁止**手改；**禁止**以手写
    重复后端权威 DTO 绕过弱 typing；生成可复现且存在可执行 drift 校验。
  - **边界**：本决策**仅**持久化 Foundation 复用选择，**不**授权任何业务页面 / Product Read
    API / `UI-RD01` / `UI-I01..UI-I06` 实现；`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；
    Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Forward Outcome runtime = `NOT
    INTEGRATED`；`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`。