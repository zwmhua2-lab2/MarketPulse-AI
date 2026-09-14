# 2026-09-15 — SE-02D-D01｜Family Aggregation / Expectancy Contract

## Task

产出 `SE-02D-D01` Human-reviewable V1 设计候选；docs only，无 implementation authority。

## Scope

- 新增 `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`；
- 新增本最小 task dev_log；
- 从实时核验的 Accepted `main` 建立隔离 design branch/worktree。

## Out of Scope

Production Python、tests、ORM、migration、frontend、configuration、Runtime、DB、Scanner、
Strategy Ranking、G3 Risk、Execution、Position/Ledger、Real AI implementation/activation、Live、
`PROJECT_STATE.md`、`AI_CONTEXT.md`、`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md` 与 `main` merge。

## Repository Truth

- Task Base / local `main` / live remote `main`：
  `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`；`BASELINE MISMATCH = NO`。
- Branch：`design/se-02d-d01-family-aggregation-expectancy`。
- Worktree：`E:\Documents\MarketPulse-AI-se-02d-d01`，从 clean Accepted `main` 创建。
- 原会话 checkout 的既有 dirty changes 属 `PREEXISTING_DELTA`，未读取为 SE truth、未修改。
- Global Protocol：live `main@07e2df83266d4ecdea46caff5c61f000937b8913`，version
  `1.1.0 / ACCEPTED`。

## Implementation

无 production implementation。设计候选提出：

- sample = full aggregate key 下每个 logical Opportunity × fixed horizon 最多一次；
- Evidence/Outcome 在一个 stable MVCC snapshot 内分别折叠到 valid head；
- instrument/source/manifest/horizon/version 全部显式隔离；
- primary Expectancy = mean(`cost_adjusted_forward_return`)；
- coverage 强制包含 complete/insufficient/invalid/missing/not-due/folded/reason counts；
- current-snapshot `as_of` + canonical manifest/fingerprint；
- overlap-cluster percentile bootstrap，无 SciPy；
- primary horizon 推荐 5m，其他三个 secondary；
- 无固定经验 N，使用 coverage/cluster CI/leave-one-cluster-out sufficiency rule；
- worst observation + worst-decile mean；
- 无 regime gate、无 K/D/K label、on-demand derived aggregate；
- experiment/pair/arm identity 与 Gate C snapshot 保持未来独立 prerequisite。

## Key Finding

`D01-F01 = DESIGN BLOCKER / SCHEMA PREREQUISITE`：现有 Evidence `created_at` 不是 DB
visibility fact，Outcome normal `created_at = due_at`；当前 schema 无法在后续时间仅凭历史
`as_of` 恢复当时可见的 revision head。候选只支持 current stable snapshot，历史重建需独立
visibility/manifest contract。未发明 timestamp，未修改 schema。

## Files Changed

- `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`
- `dev_log/2026-09-15-se-02d-d01-family-aggregation-expectancy-contract.md`

## Verification

完成后实际执行并在 Final Report 报告：

- live remote/local main/base re-check；
- changed-path Scope check；
- forbidden-path diff check；
- candidate status / required section / decision-label checks；
- `git diff --check`；
- production/tests/schema/runtime diff = zero。

本 task 不运行 backend pytest：没有 production/test/schema 变更；验证边界是文档内容、Scope 与
Git evidence。未执行的 runtime/statistical implementation verification 标记 `NOT APPLICABLE —
NO IMPLEMENTATION AUTHORIZED`。

## Result

`SE-02D-D01 = DESIGN CANDIDATE / READY FOR INDEPENDENT REVIEW`。

不是 Human Acceptance；不声明 `SE-02D = ACCEPTED/COMPLETE`，不授权 implementation、Gate C
或 Live。

## Remaining / Risks

- Independent Review + explicit Human Acceptance 尚未发生；
- historical revision-as-of visibility、experiment/pair/arm identity、durable regime identity
  是后续前置；
- primary horizon、confidence、coverage floor、uncertainty、tail、instrument pooling、K/D/K、
  persistence 与 Gate C artifact retention 均须 Human 决定。

## Context For Next AI

只从本 candidate branch/commit 读取 D01；不得把设计 AI 的 `READY FOR REVIEW` 当作 Acceptance。
Reviewer 必须独立核对 repository source、revision semantics、coverage formula、as-of blocker 与
Gate C boundaries。若 Human 接受，再另开 docs/state closeout；不得从本窗口开始实现。

## Evidence

事实源包括 current `AGENTS.md`、`AI_CONTEXT.md`、`PRODUCT_REQUIREMENTS.md`、`DECISIONS.md`、
`PROJECT_STATE.md`、Edge source/ORM/migrations/SE-02A/B/C tests、相关 SE dev_log、Accepted
PRE-01A-D1 与外部 `SE-02D-R01-Design-Evidence-Pack.md`。R01 仅作 evidence input；Repository
Truth 优先。
