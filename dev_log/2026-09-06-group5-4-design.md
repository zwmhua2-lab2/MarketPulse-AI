# 2026-09-06 G5-4 — Deterministic Replay Evaluation DESIGN（已批准）

> 状态：`G5-4 DESIGN = APPROVED`；`READY FOR IMPLEMENTATION`。本文只描述设计与验收契约，未实现任何代码。
> 依据：G5-3 Acceptance = ACCEPTED；Accepted Main SHA 以 Git `main` / `origin/main` 实时读取为准（CIP-02）。

## 1. Requirement（问题陈述）

G5-3 证明了：相同 Replay 输入在两个独立 PostgreSQL workspace 中产生逐行逐值一致的 durable
business facts，并以 `workspace_digest` 作为可复现指纹。

但 G5-3 只能回答「两次回放是否一致」，不能回答：

> 这次可信、可重复的 Replay 最终产生了什么确定性的交易与经济结果？

G5-4 的目标：在 G5-3 ACCEPTED 的 deterministic Replay 之上增加一层**最小、可信、可重复的
Evaluation Layer**，从完成后的 Replay PostgreSQL durable workspace 派生 `ReplayEvaluationReport`。

- **R1 只从 durable facts 推导**：指标事实源只能是 Replay PostgreSQL durable business facts，
  不允许使用 `ReplayTradingResult` 内存字段、测试预期值或 fixture hardcode。
- **R2 确定性**：所有 float 聚合必须基于 primary-key 稳定排序的 row input，并用
  `math.fsum()` 聚合；不得依赖 PostgreSQL 自然行序或无序迭代；不得用无 `ORDER BY` 的 float SQL
  aggregate 作为验收依据。
- **R3 不自欺**：当 durable facts 不足以无歧义证明某指标时，不做该指标。本 V1 明确不计算
  MFE / MAE / drawdown / equity curve / win rate / expectancy / R-multiple / Sharpe / Sortino /
  profit factor。
- **R4 fail closed**：fill 找不到 order、side 未知、account 不唯一、position quantity < 0、
  未知 trade status、accounting fee mismatch 一律抛 `ReplayEvaluationError`。

## 2. 已核实代码事实（本窗口真实读取，2026-09-06）

| 事实 | 位置 | 结论 |
|---|---|---|
| `_REPLAY_BUSINESS_TABLES` = accepted 22 表，顺序固定 | `g5/replay.py:344` | 沿用，不重定义 |
| `capture_workspace_snapshot()` 使用 `REPEATABLE READ, READ ONLY` + PK 排序 | `g5/canonical.py:124` | 沿用为 `workspace_digest` 唯一来源 |
| `canonicalize_value()` 为 type-tagged 无损规范化 | `g5/canonical.py:79` | 沿用为 `evaluation_digest` 唯一规范化规则 |
| `FillRecord` 含 `fill_id / order_id / intent_id / price / quantity / fee` | `db/models.py:209` | fill 侧事实源 |
| `PaperOrderRecord.side` 为 `String(8)`，值来自 `OrderSide`（`BUY` / `SELL`） | `db/models.py:199` | fill 分类事实源 |
| `LedgerEntryRecord` 含 `cash_delta / fee / fill_id`，与 Fill 一一对应 | `db/models.py:258` | accounting 一致性事实源 |
| `PositionRecord.quantity` 为 `Float`，G3 平仓时精确置 `0` | `db/models.py:228`、`g3/service.py:1101` | flat 判定事实源 |
| `TradeRecord.status` 取值仅 `OPEN` / `CLOSED`；`exit_reason` nullable | `db/models.py:240/245`、`g3/service.py:1094/1105`、`g4/reconciliation.py:146` | trade lifecycle 事实源 |
| `AccountRecord.run_mode` 唯一；`cash_balance / reserved_cash / realized_pnl` | `db/models.py:251-254` | 账户事实源 |
| SELL 结算：`realized = (price - average_cost) * qty - fee`，`cash_delta = gross - fee` | `g3/service.py:1095/1111` | **不改** |
| BUY 结算：`realized = 0`，`cash_delta = -(gross + fee)`，BUY fee 不进 `realized_pnl` | `g3/service.py:1091` | **不改** |
| Fill 与 Ledger 的 `fee` 由同一次结算写入同一 `fee` 值 | `g3/service.py:1046/1123/1135` | fee 一致性成立 |

## 3. Scope（批准后实现范围）

1. 新增 `backend/src/marketpulse/g5/evaluation.py`：
   - `ReplayEvaluationError`
   - `ReplayEvaluationReport`
   - `evaluate_replay_workspace(...)`
2. `ReplayTradingResult` additive 增补 `evaluation` 字段（内存 dataclass，无 schema 变更）。
3. `ReplayTradingRunner.run()` 流程改为：
   `run trading workspace → capture canonical workspace → workspace_digest →
   evaluate durable replay workspace → attach evaluation → verify primary unchanged → return`。
4. Evaluation 从 Replay DB **重新读取** durable facts，不从 `result.fills / result.trades /
   result.final_account` 计算。
5. 新增 `backend/tests/test_group5_4_evaluation.py`（真实 PostgreSQL）。
6. 状态文档同步：`dev_log`、`PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md`（仅第 4 节批准决策）。

## 4. Out of Scope（禁止）

- schema migration；`replay_run_id` / `backtest_id`；performance / evaluation / replay_run 表。
- Evaluation Report 持久化（V1 为 deterministic derived in-memory result）。
- Replay API / Replay UI / Dashboard / CSV / export / report file system。
- historical downloader / dataset manager / raw historical ingestion。
- Real AI / AI post-trade review / batch AI review。
- 高级指标：MFE、MAE、drawdown、equity curve、win rate、expectancy、R-multiple、Sharpe、Sortino、
  profit factor、strategy ranking、parameter optimization。
- Live Trading；G2 / G3 / G4 / Risk / Paper Execution 语义变更；第二套 trading engine 或 replay engine。
- G5-5 及后续功能。

## 5. ReplayEvaluationReport Contract

| 字段 | 类型 | 精确定义 |
|---|---|---|
| `workspace_digest` | `str` | G5-3 `capture_workspace_snapshot(...).digest()`，provenance 指纹 |
| `market_event_count` | `int` | `market_events` 行数 |
| `decision_count` | `int` | `ai_decisions` 行数 |
| `plan_count` | `int` | `trade_plans` 行数 |
| `order_count` | `int` | `paper_orders` 行数 |
| `fill_count` | `int` | `fills` 行数 |
| `buy_fill_count` | `int` | side == `BUY` 的 fill 数 |
| `sell_fill_count` | `int` | side == `SELL` 的 fill 数 |
| `buy_filled_notional` | `float` | `fsum(fill.price * fill.quantity)` over BUY fills（fill_id 序） |
| `sell_filled_notional` | `float` | `fsum(fill.price * fill.quantity)` over SELL fills（fill_id 序） |
| `total_fees` | `float` | `fsum(FillRecord.fee)`（fill_id 序） |
| `ledger_cash_delta` | `float` | `fsum(LedgerEntryRecord.cash_delta)`（entry_id 序） |
| `account_realized_pnl` | `float` | durable `AccountRecord.realized_pnl`（SELL 口径，见第 6 节） |
| `final_cash_balance` | `float` | durable `AccountRecord.cash_balance` |
| `final_reserved_cash` | `float` | durable `AccountRecord.reserved_cash` |
| `open_position_count` | `int` | `quantity > 0` 的 durable Position 数 |
| `open_quantity` | `float` | `fsum(quantity)` over `quantity > 0` positions（position_id 序） |
| `trade_count` | `int` | `trades` 行数 |
| `closed_trade_count` | `int` | `status == CLOSED` |
| `open_trade_count` | `int` | `status == OPEN` |
| `exit_reason_counts` | `tuple[tuple[str \| None, int], ...]` | 仅 CLOSED trade 的 durable `exit_reason` 计数；`None` first，随后 string lexicographic ASC |
| `is_flat` | `bool` | 全部 `Position.quantity == 0` **AND** `final_reserved_cash == 0` |
| `evaluation_digest` | `str` | 见第 7 节 |

## 6. Accounting Semantics（不可混同）

当前 accepted G3 settlement semantics：

- SELL realized PnL = `(price - average_cost) * quantity - SELL fee`。
- BUY fee 直接从 `cash_balance` 扣除，**不进入** `account.realized_pnl`。
- `LedgerEntryRecord.cash_delta`：BUY = `-(gross + fee)`；SELL = `gross - fee`。

因此以下三个指标必须**分别报告**，不得合并为「profit / net_profit」：

| 指标 | 含义 |
|---|---|
| `account_realized_pnl` | 仅 SELL 结算累计 realized（已扣 SELL fee，不含 BUY fee） |
| `total_fees` | 全部 Fill fee（BUY + SELL） |
| `ledger_cash_delta` | 全部 ledger cash 变动（BUY 付钱 + SELL 收钱，均含 fee） |

## 7. Evaluation Digest Contract

- 输入：**全部评估指标**，但**排除** `workspace_digest` 与 `evaluation_digest`。
  理由：`workspace_digest` 是 provenance；evaluation digest 必须只因「评估经济结果变化」而变，
  不能仅因与评估无关的 durable workspace fact 改变而变。
- 规范化：复用 G5-3 `canonicalize_value()`（type-preserving，float → hex，Decimal → exact，
  datetime → UTC，dict key 排序，array 保序）。
- 序列化：deterministic JSON（`ensure_ascii=False` / `sort_keys=True` / `separators=(",", ":")` /
  `allow_nan=False`）→ UTF-8 → SHA-256 hex。
- 禁止：Python `hash()`、`round()`、tolerance-based digest、全局 stringify。

## 8. Deterministic Read Contract

- 读取事务：`REPEATABLE READ, READ ONLY`（与 `capture_workspace_snapshot` 等价模式）。
- 所有 row input 按真实 primary key 稳定排序；float 聚合一律 Python `math.fsum()`。
- 禁止无 `ORDER BY` 的 float SQL aggregate 作为验收依据。

## 9. Fail-Closed 规则

| 条件 | 行为 |
|---|---|
| fill 找不到对应 order | `ReplayEvaluationError` |
| order side 非 `BUY` / `SELL` | `ReplayEvaluationError` |
| Replay Account 不存在或不唯一 | `ReplayEvaluationError` |
| `PositionRecord.quantity < 0` | `ReplayEvaluationError` |
| trade status 非 `OPEN` / `CLOSED` | `ReplayEvaluationError` |
| `fsum(Fill.fee) != fsum(Ledger.fee)` | `ReplayEvaluationError` |

不使用大 tolerance 掩盖 mismatch。

## 10. 验收契约（AC）

- **AC-01 Basic Metrics**：从 durable facts 正确产出第 5 节全部字段。
- **AC-02 A/B Evaluation Equality**：`Evaluation(A) == Evaluation(B)`。
- **AC-03 A/B Evaluation Digest Equality**：`EvaluationDigest(A) == EvaluationDigest(B)`；
  并继续 `WorkspaceDigest(A) == WorkspaceDigest(B)`。
- **AC-04 A/C Sensitivity**：`EvaluationDigest(A) != EvaluationDigest(C)`，且测试指出至少一个
  真实变化的 approved economic field（`sell_filled_notional` / `total_fees` / `ledger_cash_delta` /
  `account_realized_pnl` / `final_cash_balance`）；禁止以 fixture ID、DB name、run label 制造差异。
- **AC-05 Lifecycle Validity**：A/B/C 均为 G2→G3→BUY→Position→Recorded G4 HOLD→STOP_LOSS→
  Protective SELL→Trade CLOSED；C（bid 88）仍 `status=CLOSED`、`exit_reason=STOP_LOSS`。
- **AC-06 Recorded G4**：A/B/C 的 G4 decision `model == replay-recorded-g4`、`error is None`；
  禁止 silently 经过 `ReplayPositionReviewRecordMissing` safe HOLD fallback。
- **AC-07 Flat Fixture**：`closed_trade_count == 1`、`open_trade_count == 0`、
  `open_position_count == 0`、`open_quantity == 0`、`final_reserved_cash == 0`、`is_flat is True`；
  并验证 `final_cash_balance - configured_initial_cash == ledger_cash_delta`（本条为 accepted flat
  fixture 的测试证据，不写成所有未来 open-position evaluation 的普遍规则）。
- **AC-08 Open Position**：独立场景（同一 fixture，protective exit 前结束）证明
  `open_position_count == 1`、`open_quantity > 0`、`open_trade_count == 1`、
  `closed_trade_count == 0`、`is_flat is False`。不允许第二套 trading engine。
- **AC-09 Consistency Failure**：focused PostgreSQL test 篡改 isolated workspace 使
  Fill fees != Ledger fees → 必须 `raise ReplayEvaluationError`（证明一致性检查不是死代码）；
  仅 test-local deliberate corruption，不改生产 trading semantics。
- **AC-10 Isolation**：Real AI call = 0；OKX/network call = 0；primary DB unchanged。
- **AC-11 No Persistence Expansion**：无新表、无新 migration；Alembic head 仍为 `20260905_0004`。
- **AC-12 Regression**：G5-4 targeted、G5-3、G5-2、G5-1、G1/G2、G3、G4、full backend、Ruff、
  compileall、`git diff --check`、Alembic current/heads 全部实际运行并记录结果。

## 11. Documentation Drift Note

审计发现一个历史文本现象：`DECISIONS.md` 当前正式事实为
「`TradePlan.invalidation` = advisory text；`stop_loss` = 唯一 machine-executable hard invalidation」；
而 `PROJECT_STATE.md` 的历史 G4 段仍保留旧的「PENDING PRODUCT DECISION」措辞。

本任务**不修改 G4 历史记录来重写历史**，仅在此注明：current authoritative decision = `DECISIONS.md`。
不扩大为文档清理专项。

## 12. Scope Check（本设计阶段）

- G5-4 code added：NO（本文仅为设计）。
- Schema migration / `replay_run_id` / performance table：NO。
- Real AI / OKX / 网络：NO。Live changed：NO。primary DB written：NO。
- G2/G3/G4 trading semantics changed：NO。
- Next State：`G5-4 DESIGN APPROVED → IMPLEMENTATION`；完成后只提交当前 Group branch，
  不自行 merge `main`、不自行 Acceptance、不进 G5-5。
