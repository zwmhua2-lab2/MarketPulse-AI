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
