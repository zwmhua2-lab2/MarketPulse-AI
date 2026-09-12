# N01-7-F01-I1-C1 — Latest-Main Integration Evidence Closeout

- Date: 2026-09-13（批次 `N01-7-F01-I1-C1`；被收尾的 merge 于 2026-09-12 执行）
- Task: **N01-7-F01-I1-C1**｜Integration Evidence Closeout + Push（**非**新实现任务）
- Branch: `n01-7-f01-latest-main-integration`（**未** merge / rebase / squash / force push `main`）
- Worktree: `E:\Documents\MarketPulse-AI-n01-7-f01-latest-main-integration`
- Status:
  - **`N01-7-F01-I1 = INTEGRATED / VERIFIED`**
  - **`N01-7-F01 = INTEGRATED / AWAITING FINAL REVIEW`**
  - **`N01-7 = BLOCKED / WAITING F01 ACCEPTANCE`**
  - **`N01-8 = NOT STARTED`**
  - **`Integrated Runtime Host = NOT STARTED`**
  - 未标记 `ACCEPTED`；未重跑 full suite / F01 migration cycle / N01-7 soak；未推进 `main`

## 0. Scope / Out of Scope

**允许修改**：仅本 devlog + `PROJECT_STATE.md` / `AI_CONTEXT.md` 的最小状态同步。

**Out of Scope（一行未改）**：production code（`backend/src/`）、tests（`backend/tests/`）、
migrations（`backend/alembic/`）、`scripts/`、Candidate A semantics、SE-02B semantics、`main`
（未 merge / 未 push）、N01-7 的 2h soak、N01-8、Integrated Runtime Host。

**未重跑（按任务书 §0 明令禁止）**：full backend 341 tests、N01 A/B/C full regression、
F01 migration cycle、N01-7 soak。本批只做**证据收尾**，既有 I1 验证证据已充分。

## 1. Repository Truth（CIP-02 / CIP-03，本批实测）

| 项 | 实测值 | 来源 |
|---|---|---|
| `origin/main` | `1579707eff083007f1ac7ec65e10e6043f32b31e` | `git ls-remote origin refs/heads/main` |
| Reviewed F01 source（远端分支） | `c0ce0affd6158c9773805fb3607451c441f801a2` | `git ls-remote origin refs/heads/fix/n01-7-f01-durable-protection-snapshot` |
| Local integration branch | `n01-7-f01-latest-main-integration` | `git branch --show-current` |
| Local integration HEAD | `ddf39f2ac11ae53fb18c493f5bcc91974779bc3a`（== 任务书报告值） | `git rev-parse HEAD` |
| Integration worktree 状态 | `git status --porcelain` = 空（clean） | 实测 |
| 基线漂移 | **无**（`origin/main` 全程 `1579707`，未推进）⇒ 未触发 STOP | CIP-03 |
| 远端是否已存在集成分支 | **否**（`ls-remote` 无 `refs/heads/n01-7-f01-latest-main-integration`）⇒ 本批 push 首次创建 | 实测 |

main 自 F01 原始基线起由并行 SE-02B 工作推进到 `1579707`；集成以**真实 merge**（非 rebase /
squash）把已复审 F01 源落到最新 main 之上，未改写任何历史。

## 2. Merge Lineage（本批实测）

| 项 | 值 |
|---|---|
| Merge commit | `ddf39f2ac11ae53fb18c493f5bcc91974779bc3a`（**true merge，2 parents**） |
| Parent 1（最新集成基线） | `1579707eff083007f1ac7ec65e10e6043f32b31e` == 实测 `origin/main` |
| Parent 2（已复审 F01 源） | `c0ce0affd6158c9773805fb3607451c441f801a2` == 远端 F01 分支 tip |
| Merge message | `merge(n01-7-f01): refresh reviewed fix onto latest main` |
| Merge 时间 | 2026-09-12 19:38:44 +0800 |
| `c0ce0af` 是 `ddf39f2` ancestor | **YES**（`merge-base --is-ancestor` rc=0） |
| `1579707` 是 `ddf39f2` ancestor | **YES**（rc=0） |
| **Reviewed Source Preserved** | **YES** —— `c0ce0af` 作为 parent 2 原样进入历史，未 rebase / 未 squash / 未改写 |

`ddf39f2` 相对两父的差异（`git diff --stat`）分别等于 **F01 的贡献** 与 **SE-02B 的贡献**，
确认它是两条 lineage 的真实汇合，而非单向覆盖：

- `git diff 1579707 ddf39f2` = F01 贡献（migration `20260912_0006`、`db/models.py`、
  `g3/models.py`、`g3/protection_snapshot.py`、`g3/service.py`、`g4/{control,planning,protection,reconciliation}.py`、
  `g5/replay.py`、`test_group4.py`、`test_se_02a_edge_persistence.py`、
  `scripts/verify_n01_7_f01_r1_migration_gate.py`、3 篇 F01 devlog）。
- `git diff c0ce0af ddf39f2` = SE-02B 贡献（`edge/{__init__,attribution,capture}.py`、
  `g2/repository.py`、`g3/service.py`、`test_se_02b_attribution.py`、
  `test_se_02b_opportunity_capture.py`、4 篇 SE-02B devlog、`AI_CONTEXT.md` / `PROJECT_STATE.md`）。

## 3. Conflict / G3 Semantic-Union Resolution

- **唯一冲突文件**：`backend/src/marketpulse/g3/service.py`（两父差异文件集合的唯一交集）。
- **解决方式**：**语义并集（semantic union）**——保留 SE-02B 的 attribution 接线 **且** 加入
  F01 的 protection 接线，二者互不覆盖。实测合并结果同时包含两组符号：
  - SE-02B：`from marketpulse.edge.attribution import (EdgeAttributionRecorder, OpportunityLink, ...)`、
    `record_plan_created` / `record_ai_decision` / `record_risk_rejected` / `record_execution_rejected` /
    `record_risk_accepted` / `record_order_open` / `record_buy_filled` / `record_trade_opened` /
    `record_trade_closed` / `record_economic_result` / `record_order_cancelled`，
    以及 `attribution=` 贯穿 G3 执行路径与 `_deferred_order_attribution()`。
  - F01：`PositionProtectionAuthority`、`from .protection_snapshot import (apply_position_protection, clear_position_protection)`、
    `authority_from_plan(...)`，以及 fill 路径上的 `protection=` 与 `apply_position_protection` /
    `clear_position_protection` 调用。
- **冲突残留检查**：`git grep -nE "^(<<<<<<<|>>>>>>>|=======)$" -- backend/ scripts/` = **无标记**。
- **语义边界未被改写**：仅做机械合并 + 两处接线共存，未改变任何一方的业务语义、风险规则或
  状态机语义（CIP-06）。

## 4. Migration

| 项 | 值 |
|---|---|
| Migration head（整合后） | `20260912_0006`（单 head；`down_revision = 20260911_0005`） |
| 谱系 | `0001 → 0002 → 0003 → 0004 → 0005（SE-02A Edge）→ 0006（F01 Position Protection Snapshot）`，线性无分叉 |
| 新增 revision | `backend/alembic/versions/20260912_0006_position_protection_snapshot.py`（F01 引入） |
| `g5/replay.py::schema_head` | 已同步为 `20260912_0006`（随 F01 贡献进入） |

## 5. I1 Verification（本批**未重跑**；记录既有证据）

证据源：`E:\Temp\marketpulse-n01-7-f01-integration-*.log`（I1 窗口产物，外部，不入库）。

| 门 | 结果 | 证据 |
|---|---|---|
| F01 migration gate（disposable-migration-0006） | **PASS**（`result=PASS`；`single_head=true`，heads=`["20260912_0006"]`，`f01_down_revision=20260911_0005`；step_1→step_7 完整 upgrade / downgrade / re-upgrade 且 `cycle_reproduced_identical_values=true`；disposable residue=0） | `…-migration-gate-rerun.log` |
| N01 / G3 / G4 定向回归 | **137 passed** | `…-targeted-formal.log` |
| SE-02A + SE-02B 定向回归 | **134 passed** | `…-se-targeted-formal.log` |
| 集成定向合计 | **271 passed**（137 + 134） | 同上两文件 |
| Full backend | **341 passed, 1 warning**（`372.84s`） | `…-full-backend-formal.log`（rerun 亦 `341 passed, 1 warning`） |
| 静态门（ruff / compileall / `git diff --check`） | **PASS**（I1 记录） | I1 报告 |

**未重跑声明**：上述 heavy gate **本批未复跑**（任务书 §0 明令），状态标记为「记录既有 I1 证据」，
非本批新执行的 PASS。本批亲自执行的轻量门见 §8。

## 6. E1 Adjudication（环境归因，READ-ONLY）

### 6.1 分类

**`E1 Classification = FOREIGN WRITER CONFIRMED`**

**原始 I1 shared-primary fingerprint（`before == after`）门结论：**

> **原始 shared-primary `before/after` 门 = `INVALIDATED BY ENVIRONMENT`**
> **理由：`FOREIGN WRITER CONFIRMED`**
> 这 **不是** `PASS`。
> 这 **不是** product failure。
> 这 **不是** I1 test-isolation failure。

即：应用**既有规则**「外来写者 ⇒ 环境使该门失效 ⇒ 既非 PASS 亦非产品 FAIL」，
**并未放松** `before == after` 规则本身；同时也未把外部污染错判为产品缺陷。

### 6.2 事实链

| 项 | 内容 |
|---|---|
| 原始 I1 指纹漂移 | `900e0e4a… → ea7c87d3…`（shared primary `127.0.0.1:5432/marketpulse` before/after 不等） |
| I1 行为 | **所有** 集成测试/闸门调用均指向隔离实例 `marketpulse-postgres-f01-integration` @ `127.0.0.1:5433`；I1 在 5432 的 `pg_stat_activity` 仅见自身只读 `psql` |
| I1 隔离断言（已执行） | `assert 'DATABASE_URL' not in os.environ; assert Settings().database_url.endswith(':5433/marketpulse')` |
| 外来写者 worktree | `E:\Documents\MarketPulse AI.se-arch-fix-01`（branch `se-arch-fix-01-stable-evidence-anchor` @ `5105375`） |
| 外来写者行为 | 会话内 **0 处** `DATABASE_URL`、无 `.env` ⇒ `Settings()` 落默认 DSN `127.0.0.1:5432/marketpulse`；`pytest`（含 `pytest tests -q`，`318 passed`）直接写共享主库 |
| 漂移窗口表活动 | 12 表 `+1622 ins / +575 upd / +1619 del`，形态 = insert-then-cleanup（`n_tup_ins ≈ n_tup_del`，残留极少）⇒ `test_group3/4` fixture 生命周期，**非** operator/production 流量 |
| 安静窗口 | **obtained = YES**（≈6.7 min）；**fingerprint stable = YES**（normalized SHA-256 两端同为 `ea7c87d3…`）；`tup_inserted/updated/deleted = 0` |
| 结论 | 漂移由**并发外来写者**产生；I1 集成测试证据**仍然有效**，因为它们跑在隔离 `:5433` 上 |

### 6.3 原始证据（外部，**不**入库）

`E:\Temp\n01-7-f01-i1-e1\` —— `attribution_report.md`、`baseline.json`、`after.json`、
`table_diff.json`、`i1_drift_window_delta.json`、`quiet_window.json`、
`pg_stat_activity_samples.jsonl`、`process_samples.jsonl`、`netstat_samples.jsonl`、
`fp_now_1.json`、`fp_now_2.json`、`session_155648_scan.txt`、`pgprobe.py`、`fp.py`、`diff.py`。

**本批未把该目录（或任何外部证据文件）复制/提交进仓库**；仓库内只保留本节的书面摘要。

## 7. Isolation / Environment State

| 项 | 值 |
|---|---|
| 隔离实例 | Docker 容器 `marketpulse-postgres-f01-integration` @ `127.0.0.1:5433`，库名 `marketpulse` |
| 共享主库 | `127.0.0.1:5432/marketpulse`（`marketpulse-postgres`，`postgres:16-alpine`） |
| 共享主库 revision | `20260905_0004`（I1 全程「升级前 / 运行中 / 收尾后」一致）；`protection_*` 列 = 0；disposable residue = 0 |
| 已知跨窗口环境风险（超出本批 Scope，**非** F01 缺陷） | `Settings().database_url` 默认指向共享主库 `5432/marketpulse`，且所有 worktree 均无 `.env` ⇒ 任何并发窗口跑 `pytest backend/tests` 都会静默写共享主库（`test_group3/4` 直接绑定 `Settings().database_url`）；长时 soak / 验收窗须互斥，或强制每个窗口带显式 disposable DSN |

## 8. No Code Changes + Static Doc Gate（本批亲自执行）

| 检查 | 结果 |
|---|---|
| `git status`（文档改动前） | clean（`nothing to commit, working tree clean`） |
| `git diff`（文档改动前） | 空 |
| `git diff --check` | rc=0（无 whitespace / conflict marker 错误） |
| `git grep`（conflict markers） | 无 |
| **Production Code Changed after `ddf39f2`** | **NO** |
| **Tests Changed after `ddf39f2`** | **NO** |
| **Migration Changed after `ddf39f2`** | **NO** |
| 本批新增 delta | **docs/state only**（本 devlog + `PROJECT_STATE.md` + `AI_CONTEXT.md`） |

## 9. Commit / Push（本批）

- 恰好 **1 个** evidence/status commit（message：`docs(n01-7-f01): close integration evidence`）。
- 追加在 `ddf39f2` 之上；**未**改动 merge commit。
- Push **仅** `n01-7-f01-latest-main-integration`；**未** push `main`、**未** merge `main`、**未** force push。
- Push 后须确认：`origin/n01-7-f01-latest-main-integration` == 最终本地 HEAD；`origin/main` 未变
  （仍 `1579707`）。实测结果见末节「Closeout Execution Record」。

## 10. Closeout Execution Record

- 本批只产生 **1 个** docs/state commit（即包含本文件的提交），message =
  `docs(n01-7-f01): close integration evidence`，parent = `ddf39f2`（merge commit **未被改动**）。
- 提交内容：本 devlog + `PROJECT_STATE.md` + `AI_CONTEXT.md`；`Production Code Changed after
  ddf39f2 = NO` / `Tests Changed = NO` / `Migration Changed = NO`。
- Push：仅 `n01-7-f01-latest-main-integration`（**未** push `main`、**未** merge `main`、
  **未** force push）；远端分支 SHA 与 `origin/main` 不变确认（`origin/main` 保持
  `1579707eff083007f1ac7ec65e10e6043f32b31e`）见本批 Completion Report。

## 11. Claim Boundary

本 Closeout 可主张：

- `N01-7-F01-I1 = INTEGRATED / VERIFIED`
- `N01-7-F01 = INTEGRATED / AWAITING FINAL REVIEW`
- `N01-7 = BLOCKED / WAITING F01 ACCEPTANCE`

**不得**主张：`N01-7-F01 = ACCEPTED`；N01-7 2h soak 完成；N01-8 / Integrated Runtime Host /
Continuous Runtime / 7×24 / Real AI Edge / Live 完成；`N01 overall` 验收（仍 `NOT ACCEPTED`）。
