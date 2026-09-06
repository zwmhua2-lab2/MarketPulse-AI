# 2026-09-06 Group 5 Closeout — Acceptance Group 5 ACCEPTED / COMPLETE

> 本文件是 Group 5（G5-0 ~ G5-4）验收收尾的**摘要 / 索引**，非项目历史重写。
> 详细证据见各子组 dev_log 与 `dev_log/2026-09-06-group5-4.md`「Formal Acceptance Record」。

## Group

Acceptance Group 5 — Deterministic Replay（G5-0 → G5-4）。
本次动作：G5-4 正式验收收尾 + Group 5 整体关闭。

## Scope

仅文档与状态同步（ACCEPTANCE / GROUP CLOSEOUT ONLY）：
`PROJECT_STATE.md`、`AI_CONTEXT.md`、`dev_log/2026-09-06-group5-4.md`、本文件。
**未**修改任何 backend business code / test / schema / migration / Live / API / UI / perf。

## Accepted Subgroups

| Subgroup | 内容 | 状态 |
|---|---|---|
| G5-0 | Repository Context + Context Isolation Protocol（CIP-01~CIP-10） | ACCEPTED |
| G5-1 | Deterministic Replay Foundation | ACCEPTED |
| G5-2 | Trading Replay Integration | ACCEPTED |
| G5-3 | End-to-End Determinism | ACCEPTED |
| G5-4 | Deterministic Replay Evaluation | ACCEPTED |

**Group 5 overall = ACCEPTED / COMPLETE**

## Final Capability

Delivered chain：
Repository Context → Deterministic G2 Replay → Full Trading Replay → End-to-End Durable Determinism → Deterministic Evaluation。

G5-4 从 Replay PostgreSQL durable workspace 生成 `ReplayEvaluationReport`（21 指标 + `workspace_digest` + `evaluation_digest` = 23 字段），
仅读 durable facts、事务 `REPEATABLE READ, READ ONLY`、三个会计指标分别报告、fail-closed 边界完整、A==B 评估相等、A!=C 经济敏感。

## Regression

Fresh Acceptance Regression（2026-09-06，执行后记录于 Final Report）：
G5-4 targeted = 10 passed；G5-3 / G5-2 / G5-1 / G1+G2 / G3 / G4 串行通过；
full backend ≈ 107 passed；Ruff（`backend/src backend/tests`）= PASS；
compileall = PASS；`git diff --check` = PASS；Alembic `heads` / primary `current` = `20260905_0004 (head)`。

## Known Non-Blocking Notes

- Real AI Provider 仍 `DEFERRED`（`OPENAI_API_KEY=MISSING`）；测试用 deterministic Fake / recorded provider，未伪造真实 AI 结果。
- advanced backtest / performance metrics（MFE/MAE/drawdown/Sharpe/…）不在 G5-4，仍为后续 Group 范围。
- 无 `replay_run_id` / `backtest_id`；Evaluation Report 不持久化。
- 本地 scratch 文件 `scripts/_g54_selfreview.py` 与 `.workbuddy/` 仍为 untracked，未进入 Git。
- Flat fixture 现金恒等式存在 IEEE-754 ULP 量级差（≈ `5.68e-13`），以 machine-precision 派生容差对账，非会计容差。

## Out of Scope

MFE/MAE/drawdown/equity curve/win rate/expectancy/R-multiple/Sharpe/Sortino/profit factor；
`replay_run_id`/`backtest_id`；performance/evaluation/replay_run 表；Replay API/UI/Dashboard；
historical downloader/dataset manager；AI post-trade review/Batch AI review；optimizer/strategy ranking；
Live Trading；G5-5 及后续功能。

## Final Git Evidence

- Accepted Main SHA = `8f55cfd786cefa07be315cc6555a61636a7c8a16`（preflight `git ls-remote` 实时核对）
- G5-4 reviewed branch HEAD / Self Review Fix #1 Evidence = `fe610c1f23457ff11f2d5c8654e9de0aec4ff289`
- G5-4 Production Implementation Basis = `8678b2927a2d029ac0767e49acc9e0732c329bfa`
- Acceptance Closeout commit = documentation-only（见 Final Report）
- `8f55cfd` 为 G5-4 branch 祖先，无 divergence；promotion 为 fast-forward。

## Final State

`GROUP 5 = ACCEPTED / COMPLETE`。
`NEXT GROUP = NOT STARTED`（G5-5 未定义）。

## Context For Next Group

- 当前 Accepted Baseline：以 Git `main` / `origin/main` 为准（CIP-02 preflight 实时读取）。
- 下一个动作：等待人工 / 设计决策启动 Next Group Design（G5-5 之前需先 design，未开始）。
- frozen invariants 见 `AI_CONTEXT.md` 第 3 节；Source of Truth 优先级见 `AI_CONTEXT.md` 第 2 节。
- 禁止依据旧聊天 / 模型记忆直接实现；新窗口须重新从 repository truth 建立 Context Pack。

---

## Post-Closeout Documentation Consistency Fix（2026-09-06）

- initial closeout commit = `fccbb659489870f9205688bafc31d2eec4162122`（remote `main` / `g5-replay-evaluation` baseline，preflight `git ls-remote` 实时核对一致）。
- Reviewer independently found stale current-state fields：`PROJECT_STATE.md` / `AI_CONTEXT.md` 仍残留 "G5-4 IMPLEMENTED / WAITING REVIEW"、"G5 overall = NOT ACCEPTED"、"g5-replay-evaluation 未 merge main" 等 current-state 文字。
- no acceptance result changed：G5-4 = `ACCEPTED`；Group 5 = `ACCEPTED / COMPLETE`；Next Group Design = `NOT STARTED`。
- `PROJECT_STATE.md` / `AI_CONTEXT.md` current truth synchronized；G5-0～G5-4 历史实施证据未重写。
- no code / test / schema changes（纯文档修正）。
