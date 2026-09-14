# SE-02C-FINAL｜Acceptance Closeout & Main Integration

## Task

- Task Type：Human-Accepted Final Closeout + Accepted Baseline Integration。
- 授权来源：Human Authorization（Human Acceptance = `CONFIRMED`，2026-09-14，接受
  `SE-02C` 与 `SE-02C-FIX-02`，并允许 Acceptance Closeout + `main` integration）。
- 本窗口**不是**新实现、**不是**重新 Review、**不是**新 Acceptance；只做
  Acceptance documentation / State synchronization / Accepted Decision synchronization /
  Fast-forward `main` integration / Remote verification。
- 本窗口**不**修改 production code / tests / migration / schema / runtime config / frontend /
  scripts / business semantics；**不**修 `SE02C-R7`；**不**启动 `SE-02D`。

## Human Acceptance

- Human Acceptance = `CONFIRMED`（Acceptance Date = 2026-09-14）。
- 接受范围：`SE-02C`、`SE-02C-FIX-02`。
- 明确接受 `SE02C-R7`（P3 / NON-BLOCKING）为**已接受的非阻塞遗留项**。
- 事实边界：本 dev_log 记录的是**人工验收结果与收尾事实**，不代替 Reviewer 的独立判断。

## Independent Re-Review Verdict

- Verdict = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`。
- 唯一遗留 finding = `SE02C-R7`（P3 / NON-BLOCKING）。
- Reviewer 已独立验证 `C-01..C-29 = ALL PASS`、`F02-01..F02-24 = ALL PASS`。
- 本窗口**未**重跑上述验证，**未**改写其结论；证据来源为 Independent Re-Review。

## Reviewed Candidate

| 字段 | 值 |
|---|---|
| Human-Accepted reviewed candidate | `7bb3835d6b14a3fc86becff1881c7f53f1acd567` |
| Reviewed candidate branch | `se-02c-fix-02-stable-read-snapshot` |
| Reviewed candidate branch 远端 | `7bb3835d6b14a3fc86becff1881c7f53f1acd567`（未移动） |
| Fix-02 implementation commit | `6b084595cde9c3e3257046b4694b134954923a4d` |
| Fix-01 candidate（immutable） | `2f9868278ab1652c4e338ffb01337c6e736545d9` |
| 原 SE-02C 候选（immutable） | `be3aa6c817582f6161ea9903f7824200b7f5c843` |
| Accepted Main before | `dd78a979d128dee385c7a8ddc2254a53366af714` |

Reviewed candidate branch **不作为** closeout 的写入目标：它在整个收尾过程中保持
`7bb3835…` immutable，且远端 ref 未被移动。

## Accepted Findings

| Finding | 严重度 | 状态 |
|---|---|---|
| `SE02C-R1`（>50,000 observations 被读取上限静默截断） | P1 / BLOCKING | `CLOSED / PASS` |
| `SE02C-R2`（live ingress 无条件 `tradable=True`） | P1 / BLOCKING | `CLOSED / PASS` |
| `SE02C-R3`（旧候选未建立在最新 Accepted Main lineage） | P1 / BLOCKING | `CLOSED / PASS` |
| `SE02C-R4`（anchor 被误当 endpoint ⇒ 应报 `ENDPOINT_MISSING`） | P2 / NON-BLOCKING | `CLOSED / PASS` |
| `SE02C-R5`（分页 SELECT 不共享稳定 snapshot） | P1 / BLOCKING | `CLOSED / PASS` |
| `SE02C-R6`（pagination / endpoint order docstring 错误） | P3 / NON-BLOCKING | `CLOSED / PASS` |
| `SE02C-R7`（MVCC snapshot boundary 注释措辞不准确） | P3 / NON-BLOCKING | `OPEN / NOT FIXED`（Human Accepted） |

`R1` / `R2` / `R3` / `R4` 由 `SE-02C-FIX-01` 闭合；`R5` / `R6` 由 `SE-02C-FIX-02` 闭合。

## Repository Truth

收尾开始时实测（`git fetch origin --prune` 后 `git ls-remote`；未采信任务书中的静态 SHA）：

| 项 | 实测值 | 期望 | 结果 |
|---|---|---|---|
| `refs/heads/main` | `dd78a979d128dee385c7a8ddc2254a53366af714` | `dd78a979…` | MATCH |
| `refs/heads/se-02c-fix-02-stable-read-snapshot` | `7bb3835d6b14a3fc86becff1881c7f53f1acd567` | `7bb3835…` | MATCH |
| `git merge-base <main> <candidate>` | `dd78a979d128dee385c7a8ddc2254a53366af714` | = main | MATCH |
| `git rev-list --left-right --count main...candidate` | `0	9` | behind = 0，ahead > 0 | MATCH |
| local `main` ref | `dd78a979…` | = remote main | MATCH |

- `behind = 0` ⇒ reviewed candidate 完全建立在当前 Accepted Main 之上，**fast-forward
  eligibility 成立**。
- 无 worktree 检出 `main`（`git worktree list` 实测）⇒ 可在 closeout 后安全更新本地
  `main` ref。
- `E:/Documents/MarketPulse-AI-se-02c-fix-02-r01-review`（reviewer 的 detached worktree）
  实测 clean、detached 于 `7bb3835`；本窗口**未**写入该 worktree。

## Integration Eligibility

- `merge-base(main, candidate) == main` ⇒ 无分叉。
- candidate 相对 main `ahead = 9`、`behind = 0` ⇒ `main` 可直接 fast-forward。
- 无 ref drift ⇒ 未触发 STOP 条件。

## Scope

- Acceptance documentation（`PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md`）。
- State synchronization（SE-02C / FIX-01 / FIX-02 的正式状态）。
- Accepted Decision synchronization（追加 `SE-02C V1`）。
- Fast-forward only `main` integration。
- Remote verification（closeout branch / `main` / reviewed candidate 三方远端复读）。

## Out of Scope

- production code / tests / migration / schema / ORM / runtime config / frontend / scripts。
- 修改 `se-02c-fix-02-stable-read-snapshot`（reviewed candidate 分支）。
- 修 `SE02C-R7`（修改源码 comment 会改变 Human-Accepted reviewed candidate）。
- `SE-02D`（Family Aggregation / Expectancy）的任何设计、实现或启动授权。
- merge commit / rebase / squash / cherry-pick / force push / history rewrite。
- 重跑 425 个 backend tests（见「Verification Evidence」）。

## Files Changed

```
PROJECT_STATE.md
AI_CONTEXT.md
DECISIONS.md
dev_log/2026-09-14-se-02c-final-acceptance-closeout.md
```

- 其它文件零 diff（`backend/**` / `tests/**` / `scripts/**` / `alembic/**` / `frontend/**`
  全部零 diff，见「Verification Evidence」的 changed-path scope check）。
- `Original seal`（不可变）：`se-02c-fix-02-stable-read-snapshot` 分支未被提交、未被推送、
  未被 force push。

## Accepted Behavior

`SE-02C = Forward Outcome Calculator` 已 Accepted 的能力：

- Forward Outcome Calculator（30s / 5m / 15m / 1h 四个 horizon）。
- stable Capture Anchor reference（reference authority = FIX-01 durable capture anchor BBO，
  anchor 只作 reference，**不**作 endpoint）。
- complete Forward BBO path（完整 keyset 分页遍历，无 50,000 静态读取上限）。
- deterministic endpoint（纯计算器在完整 observation set 上以
  `(available_at, has_source_sequence, source_sequence, observation_id)` 总序决定）。
- MFE / MAE。
- reference return。
- executable LONG return。
- paper cost-adjusted return（精确乘性 `SPOT_LONG_TAKER_ROUND_TRIP` 成本模型）。
- 终态仅 `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID`（PENDING 仅为派生状态，不落库）。
- revision-1 immutable normal outcome。
- retry / restart determinism。
- concurrent exactly-one。
- stable `REPEATABLE READ` calculation snapshot。
- same-scope PostgreSQL advisory coordination。
- tradability authority（真实 instrument tradable 状态，无硬编码 `True`）。
- Replay / Forward provenance separation（`calculation_digest` 排除 provenance，
  `outcome_record_hash` 包含 provenance）。
- `due_at = evidence_at + horizon.duration`；endpoint 5 s TTL；`created_at` 冻结为 `due_at`。

**不**扩展为 `SE-02D` capability。

## Accepted Concurrency Semantics

- normal `evaluate_scope(scope)` 先以 deterministic SHA-256 signed-int64 key 取得
  **same-scope PostgreSQL advisory transaction lock**（`pg_advisory_xact_lock(bigint)`）。
- lock 语义覆盖 task / process / independent session；Python `asyncio.Lock` **不是**
  correctness 边界。
- coordinator 持锁从 acquisition 直到 outcome append/commit；commit/rollback 自动释放。
- 等待者（第二个 evaluator）在 lock statement 返回后，以 READ COMMITTED 的下一 statement
  重新取 snapshot，命中 existing revision-1 后**直接 return existing**，不重算、不写
  revision 2、不产生 `EdgeOutcomeConflict`。
- concurrent ingress（`ForwardPathRecorder`）**不**取得 outcome scope lock，允许并发写；
  并发提交的合法 due-path BBO 对当前 attempt 不可见，但 durable 且对 fresh snapshot 可见。
- 最终 durable revision-1 row = 1，双方 `outcome_id` / `calculation_digest` /
  `outcome_record_hash` 相同。
- advisory key 的理论碰撞只增加 serialization，不改变 correctness。

## Accepted Snapshot Semantics

一个 calculation attempt 的 durable fact set 必须**同时**满足：

1. **market-time eligibility**：`evidence_at <= available_at <= due_at`；
2. **transaction visibility**：row 在该 attempt 的 PostgreSQL snapshot 建立时可见。

- `calculate_scope()` 在独立 session 的 transaction 中，把
  `SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` 作为**第一条 SQL**；随后同一
  session 完成 durable reference resolution 与**全部** keyset page SELECT。
- snapshot session 只读，**不**写 outcome；outcome 只在 coordinator transaction 写入。
- snapshot 建立后才 commit 的 row 即使 `available_at <= due_at`，当前 attempt 也不可见；
  该 row 仍合法 durable，fresh snapshot 可见。
- 未新增 commit timestamp 字段，未把 commit time 写入业务模型。
- Reviewer 独立确认：`R7` 所述的注释措辞不准确只影响维护者理解，**不**影响 runtime
  ordering、`R5` correctness、determinism 或 concurrency safety。

## R1-R6 Closure

| Finding | 闭合窗口 | 闭合内容（摘要） |
|---|---|---|
| `SE02C-R1` | SE-02C-FIX-01 | 移除 50,000 静态读取上限；真实 50,001 path 全量遍历，endpoint / MFE / MAE 完整 |
| `SE02C-R2` | SE-02C-FIX-01 | live ingress 不再硬编码 `tradable=True`，改为真实 tradability authority |
| `SE02C-R3` | SE-02C-FIX-01 | 以最新 Accepted Main 为第一父系真实 merge 原候选，重建于最新 lineage |
| `SE02C-R4` | SE-02C-FIX-01 | anchor 只作 reference authority；anchor-only 窗口报 `ENDPOINT_MISSING` |
| `SE02C-R5` | SE-02C-FIX-02 | reference + 全 path page 共享同一 `REPEATABLE READ READ ONLY` snapshot；同 scope advisory lock 序列化 evaluator |
| `SE02C-R6` | SE-02C-FIX-02 | 更正 docstring：pagination traversal order 与 endpoint total order 明确分离 |

- `SE02C-R1` ～ `SE02C-R6` = `CLOSED / PASS`。

## R7 Non-Blocking Finding

- `SE02C-R7`：源码 comment 对 PostgreSQL MVCC snapshot boundary 措辞不准确 ——
  `SET TRANSACTION` 设置的是 `REPEATABLE READ` / `READ ONLY` transaction characteristics；
  真正的 snapshot 由**第一次 snapshot-taking query** 建立。
- Severity = `P3`；Blocking = `NO`。
- Reviewer 已确认该问题只影响维护者理解，不影响 runtime ordering、`R5` correctness、
  determinism、concurrency safety。
- Human Acceptance 明确接受该 P3 non-blocking finding。
- **本 Closeout 不修 `SE02C-R7`**：修源码 comment 会改变 Human-Accepted reviewed candidate。
- 如需处理：单独建立 `P3 docs/comment cleanup task`。
- 本窗口**未**修改 `backend/src/marketpulse/edge/forward_service.py`。

## C-01..C-29 Final Matrix

| # | 结果 | 判据（逐条原文见下方 source 指针） |
|---|---|---|
| C-01 | PASS | Repository Truth |
| C-02 | PASS | No Schema Change |
| C-03 | PASS | Due Determinism |
| C-04 | PASS | Pending Is Derived |
| C-05 | PASS | Stable Reference |
| C-06 | PASS | Causal End Selection |
| C-07 | PASS | End Freshness |
| C-08 | PASS | MFE / MAE Formula |
| C-09 | PASS | Reference Return Formula |
| C-10 | PASS | Executable LONG Return Formula |
| C-11 | PASS | Cost-Adjusted Formula |
| C-12 | PASS | COMPLETE Classification |
| C-13 | PASS | INSUFFICIENT_DATA Classification |
| C-14 | PASS | INVALID Classification |
| C-15 | PASS | Four Horizons Independent |
| C-16 | PASS | Cross-Evidence Independent |
| C-17 | PASS | Forward Path Capture |
| C-18 | PASS | Restart Determinism |
| C-19 | PASS | Concurrent Exactly-One |
| C-20 | PASS | Retry Idempotency |
| C-21 | PASS | No Automatic Revision 2 |
| C-22 | PASS | Late / Future Rejected |
| C-23 | PASS | Replay / Forward Separation |
| C-24 | PASS | Provenance Inheritance |
| C-25 | PASS | FIX-01 Regression |
| C-26 | PASS | FIX-02 Regression |
| C-27 | PASS | SE-02A / SE-02B Regression |
| C-28 | PASS | Full Backend |
| C-29 | PASS | Scope |

- **合计：`C-01..C-29 = ALL PASS`。**
- 判据原文出处：`dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md` §C-01..C-29 Matrix。
- **Source = Independent Re-Review evidence**（Reviewer 在其独立复审中逐条验证）。
  **不是**本 Closeout 重跑得到；本窗口**未**重跑该矩阵，**未**改写其任何一条结论。

## F02-01..F02-24 Final Matrix

| # | 结果 | 判据（逐条原文见下方 source 指针） |
|---|---|---|
| F02-01 | PASS | Repository Truth correct |
| F02-02 | PASS | Base = Fix-01 candidate |
| F02-03 | PASS | No schema / migration change |
| F02-04 | PASS | Deterministic advisory key |
| F02-05 | PASS | Lock across independent sessions |
| F02-06 | PASS | Existing checked after lock |
| F02-07 | PASS | Reference + pages one RR snapshot |
| F02-08 | PASS | Cursor-after late commit excluded |
| F02-09 | PASS | Cursor-before late commit excluded |
| F02-10 | PASS | Fresh snapshot sees late rows |
| F02-11 | PASS | Two evaluators + ingress same outcome |
| F02-12 | PASS | No normal-race conflict |
| F02-13 | PASS | Exactly one revision-1 row |
| F02-14 | PASS | No automatic revision 2 |
| F02-15 | PASS | 50,001 path |
| F02-16 | PASS | Tradability |
| F02-17 | PASS | Anchor-only |
| F02-18 | PASS | Formula / due / freshness / causal |
| F02-19 | PASS | Restart / retry / horizons / cross / replay |
| F02-20 | PASS | SE-02A/B + FIX-01/02 |
| F02-21 | PASS | N01-7 preservation |
| F02-22 | PASS | Full backend |
| F02-23 | PASS | Ruff / compileall / diff-check |
| F02-24 | PASS | R6 docstring |

- **合计：`F02-01..F02-24 = ALL PASS`。**
- 判据原文出处：`dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md` §F02-01..F02-24 Matrix。
- **Source = Independent Re-Review evidence**（Reviewer 在其独立复审中逐条验证）。
  **不是**本 Closeout 重跑得到；本窗口**未**重跑该矩阵，**未**改写其任何一条结论。

## Verification Evidence

独立复审已完成的既有证据（**本 Closeout 未重跑**，仅登记为历史门）：425 backend tests、
SE-02C focused、Snapshot / Race、SE-02A/B、G2、G5、N01/G4、Ruff、compileall、diff-check。

本窗口实际执行的门（docs-only closeout 的最小充分验证）：

| Gate | 结果 | 说明 |
|---|---|---|
| Repository Truth preflight | PASS | `ls-remote` main / reviewed candidate 与期望一致；`merge-base` = main；`behind = 0` |
| 本窗口 production / tests / schema diff | PASS | 0（本窗口未触碰任何非 docs 文件） |
| `git diff --name-only <candidate>..HEAD`（closeout commit） | PASS | 仅 `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` / 新 dev_log |
| `git diff --check` | PASS | rc = 0 |
| `git diff --check <candidate>..HEAD` | PASS | rc = 0（commit 后复核） |
| `alembic heads`（轻量确认，只读） | PASS | 单 head `20260913_0009`；**未**修改 DB / schema |
| ancestry：`git merge-base --is-ancestor <Accepted Main before> <closeout SHA>` | PASS | YES |
| ancestry：candidate / implementation / merge commit 均为 closeout SHA ancestor | PASS | 三者皆 YES |
| parent 数：`git log --format=%h parents=%p <before>..<after>` | PASS | 每个 commit 单 parent（`51891c7` 为既有 true merge，收尾未新增 merge commit） |
| Remote read-back（closeout branch / main / reviewed candidate） | PASS | 见「Integration Method」与「Final Main SHA」 |
| Working tree status | PASS | clean |

**明确标记为 NOT RE-RUN 的门**：425 backend tests、SE-02C focused、Snapshot/Race、
SE-02A/B、G2、G5、N01/G4、Ruff、compileall。理由：Human Acceptance 已基于独立完整 Review，
且 Closeout 只允许 docs/state 修改（任务书 §12 Final Regression Policy）。
这些门**不得**被本窗口声称为「本次重跑 PASS」。

## Integration Method

- Integration Method = **`FAST-FORWARD ONLY`**。
- 未创建 merge commit、未 squash、未 rebase、未 cherry-pick 重构历史、未 force push、
  未 `--force-with-lease`。
- 顺序：先 push `se-02c-final-acceptance-closeout` → 远端复读 closeout branch tip 与本地一致
  → **再次**确认 remote `main` 仍为 `dd78a979…`（pre-push drift gate）→ 断言
  `git merge-base --is-ancestor dd78a979… <closeout SHA>` 成功 → `git push origin
  <closeout-SHA>:refs/heads/main`（后台执行）→ 远端复读 `main` == closeout SHA
  → 远端复读 reviewed candidate branch 仍为 `7bb3835…`。
- 本地 `main` ref 同步：确认无 worktree 检出 `main` 后更新本地 `main` ref 至 closeout SHA，
  并以独立进程 `git rev-parse main` 复核。

## Acceptance Closeout Commit

- Closeout commit message：`docs(se-02c): accept SE-02C and close final integration`。
- Parent = Human-Accepted reviewed candidate `7bb3835d6b14a3fc86becff1881c7f53f1acd567`
  （单一 parent ⇒ 满足「candidate 是 final `main` 的 ancestor」）。
- 具体 SHA **由最终 Closeout Report 记录**：commit 无法自引用其自身哈希（本仓库既有惯例，
  见 `dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md` §Evidence 同款处理）。

## Final Main SHA

- Accepted Main before = `dd78a979d128dee385c7a8ddc2254a53366af714`。
- Accepted Main after = Acceptance Closeout Commit SHA（**由最终 Closeout Report 记录**）。
- 最终 `main` delta 应只包含：Human-Accepted SE-02C implementation + Fix-01 + Fix-02 +
  docs-only Acceptance Closeout，**无**任何其它非预期代码。

## Result

```text
SE-02C = ACCEPTED / COMPLETE
SE-02C-FIX-01 = ACCEPTED / CLOSED
SE-02C-FIX-02 = ACCEPTED / CLOSED
SE-02D = NOT STARTED
```

- 状态语义边界：仅当 remote `main` 成功 fast-forward 并复读确认后，才成立
  `SE-02C Final Integration = COMPLETE`；docs commit 成功但 `main` push 未完成时**不得**
  宣称 Final Integration Complete。
- `SE02C-R7` 保持 `P3 / NON-BLOCKING / NOT FIXED`（Human Accepted non-blocking finding）。

## Remaining

- `SE02C-R7`（P3 / NON-BLOCKING）：如需清理，另开独立的 `P3 docs/comment cleanup task`。
- `SE-02D｜Family Aggregation / Expectancy` = `NOT STARTED`（**不**由本次验收解锁；须另开窗口
  并经批准的门）。
- `N01-8｜12-hour Extended Soak` / `Integrated Runtime Host` = `NOT STARTED`（与本次验收无关）。
- P2 保留项（`TEST-ISO-01` / `RRF-03` / `RRF-04`）与 `N01-7-R01-RR-P2-01`（Memory Operational
  Watch，必须留给 `N01-8`）均维持原状，**未**在本次触碰。

## Known Risks

- `SE02C-R7` 保留为已接受的 P3 文档/注释准确性问题：源码 comment 对 MVCC snapshot boundary
  的措辞仍不准确，可能误导后续维护者；不影响 runtime 行为。
- PostgreSQL advisory lock key 存在密码学上极低概率碰撞；后果仅为额外 serialization。
- 环境遗留（**未授权清理，原样保留**）：`SE-02C-FIX-02` 窗口的隔离容器
  `marketpulse-se-02c-fix-02-pg` @ `127.0.0.1:5443` 与 worktree `E:\Documents\MarketPulse-AI-se-02c-fix-02`
  内 gitignored `.env`；释放命令 `docker rm -f -v marketpulse-se-02c-fix-02-pg`。
  副作用：在该 worktree 内跑 pytest 会走 5443 而非共享 5432。
- 共享 primary PostgreSQL 库在本窗口**未**被触碰（无 migration / downgrade）。

## Context For Next AI

- `SE-02C` 已 `ACCEPTED / COMPLETE` 并收编 `main`；`SE-02C` 的语义事实源指针 =
  `PROJECT_STATE.md`（「SE-02C Result」/「SE-02C-FIX-01 Result」/「SE-02C-FIX-02 Result」）+
  `DECISIONS.md`（`SE-02C V1`）+ 本批三个 dev_log。
- **`SE-02C` Accepted ≠ `SE-02D` MAY START**：`SE-02D` 仍 `NOT STARTED`，启动前必须另开独立
  获批的窗口与门。
- **`SE-02C` Accepted ≠ `N01 overall` Accepted**；`N01-8` / `Integrated Runtime Host` 仍
  `NOT STARTED`。
- 下一个 AI 必须按 CIP-02 从 Git 实时读取 `main`，不得采信本文件或任何状态文档中的静态 SHA。
- `SE-02C-FIX-02` / `SE-02C-FIX-01` / `se-02c-forward-outcome-calculator` /
  `se-02c-final-acceptance-closeout` 分支均保留为历史证据，**不得**改写。
- 跑 SE-02C 相关测试时**不要导出 `DATABASE_URL`**（`alembic/env.py` 环境变量优先于测试传入的
  URL，会把迁移打到错误的库）。

## Evidence

- Repository truth：`git ls-remote origin refs/heads/main`、`refs/heads/se-02c-fix-02-stable-read-snapshot`。
- Ancestry / lineage：`git merge-base`、`git rev-list --left-right --count`、`git log --format="%h parents=%p"`。
- Changed-path scope：`git diff --name-only 7bb3835..HEAD`、`git diff --check`（工作树 + range）。
- Alembic：`alembic heads` = `20260913_0009`（单 head，只读确认）。
- Human Acceptance 输入：`SE-02C` + `SE-02C-FIX-02`（2026-09-14，`CONFIRMED`）。
- 独立复审证据出处：`dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md`
  （§C-01..C-29 Matrix、§F02-01..F02-24 Matrix、§Verification）与
  `dev_log/2026-09-14-se-02c-fix-01-review-blockers.md`。
- 验收后状态同步：`PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md`。
