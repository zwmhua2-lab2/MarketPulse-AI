# SE-ARCH-FIX-02｜Outcome Revision Chain Scope

- Date: 2026-09-13
- 专项: SE｜Strategy & Trading Edge（SE-02C 启动前第二个 Architecture Blocker）
- Batch: SE-ARCH-FIX-02
- Branch: `se-arch-fix-02-outcome-revision-chain-scope`
- Worktree: `E:\Documents\MarketPulse-AI-se-arch-fix-02`（从 Accepted Main clean worktree 创建）
- Status: `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（未自行 Acceptance，未 merge `main`，未开始 SE-02C）

---

## 1. Task / Requirement

只修复 Forward Outcome revision chain 的 **scope integrity**：一个 outcome revision chain 的
identity scope 冻结为

```text
opportunity_id + evidence_id + horizon
```

即每个 `(opportunity_id, evidence_id, horizon)` 拥有**自己独立**的 revision chain；`revision N > 1`
只能 supersede **同 scope 的 `N - 1`**。任何维度不同 → fail closed。

本任务**不**是 SE-02C 的实现，完成后仍需 Independent Review → Human Acceptance → Pre-SE-02C Re-Gate。

---

## 2. Repository Truth（preflight 实测）

| 项 | 值 |
|---|---|
| Task Base SHA（Accepted Main，`git ls-remote origin refs/heads/main`） | `fc619242c99a794a2eb2b87ee02b8b72aa782f05` |
| 本地 `main` / `origin/main` | 同为 `fc61924` |
| 创建 worktree 时 HEAD | `fc61924`（`git worktree add -b <branch> <path> fc61924`） |
| Migration head（实现前） | `20260913_0008`（单 head，`0005 → 0006 → 0007 → 0008`） |
| Migration head（实现后） | `20260913_0009`（单 head） |
| Implementation Commit | `4c835828f482875d1d7ce934f8808d3953a9105b` |

说明：

- 工作区 `E:\Documents\MarketPulse AI` 检出 `prb-01-product-requirements-baseline` @ `d47313a`，
  含 27 项未提交变更（历史脏工作树）。该工作树按项目约定**只读**，本批未在其中做任何操作；
  本批 preflight 的文档读取也**不**取自该工作树（其 `PROJECT_STATE.md` 停在 PRB-01 时代，
  与 Accepted Main 不一致），一律从 clean worktree 读取。
- 无 production / schema drift：`main` 仍为 `fc61924`，head 仍为 `20260913_0008`，与任务书
  §1/§2 导航一致。**未触发 STOP。**

---

## 3. Scope

允许修改并实际修改：

```text
backend/src/marketpulse/edge/repository.py            （service 校验）
backend/src/marketpulse/db/models.py                  （ORM / schema 对齐）
backend/alembic/versions/20260913_0009_*.py           （一个 additive + fail-closed 迁移）
backend/tests/test_se_02a_edge_persistence.py         （SE-02A Edge persistence tests，含 FIX-02 回归）
backend/src/marketpulse/g5/replay.py                  （G5 schema-head 常量）
dev_log/（本文件）
PROJECT_STATE.md / AI_CONTEXT.md                      （最小状态更新）
```

## 4. Out of Scope（未触碰）

Forward Outcome Calculator 业务算法、MFE/MAE、return / cost model / expectancy、SE-02C runtime、
SE-02D aggregation、AI、G3/G4 economic semantics、N01 production behavior、Capture Anchor FIX-01
语义、Attribution 语义、Real AI、Live Trading。

同时**未**顺手修 `TEST-ISO-01` / `RRF-03` / `RRF-04`（保持独立 P2）。

---

## 5. Confirmed Defect（实现前实测）

`append_forward_outcome()`（`edge/repository.py`）在 `outcome_revision > 1` 时只验证：

```text
predecessor.opportunity_id == record.opportunity_id
predecessor.outcome_revision == record.outcome_revision - 1
```

缺少 `evidence_id` 与 `horizon` 校验，因此同一 opportunity 内可产生：

- **Cross-Evidence**：`(O1,E2,5m,R2)` 错误 supersede 了 `(O1,E1,5m,R1)`；
- **Cross-Horizon**：`(O1,E1,15m,R2)` 错误继承了 `(O1,E1,5m,R1)`。

两者都是 invalid correction lineage。DB 层同样无法阻止：`20260911_0005` 建立的
`fk_edge_outcome_supersedes` 只携带 `(supersedes_outcome_id, opportunity_id)`，作用域过宽。
**Service 与 DB 双层都必须 fail closed。**

---

## 6. Implementation

### 6.1 Service 层（`edge/repository.py`）

`append_forward_outcome()` 的 predecessor 校验补齐为四项，任一不成立抛
`EdgeInvalidOutcomeSupersedes`（**未新增** exception 类型）：

```text
predecessor.opportunity_id == record.opportunity_id
predecessor.evidence_id    == record.evidence_id          ← 新增
predecessor.horizon        == record.horizon.value        ← 新增
predecessor.outcome_revision == record.outcome_revision - 1
```

`revision = 1`（无 supersedes）、idempotency（同 `(opportunity, evidence, horizon, revision)` +
同 `outcome_record_hash` → `IDEMPOTENT`）、conflict（同 logical revision + 不同 hash →
`EdgeOutcomeConflict`）语义**逐一保持**，未改动。

### 6.2 DB backstop（`db/models.py` + 迁移）

`EdgeForwardOutcomeRecord`：

- 删除唯一约束 `uq_edge_outcome_id_opportunity (outcome_id, opportunity_id)`；
- 新增唯一约束 `uq_edge_outcome_id_scope (outcome_id, opportunity_id, evidence_id, horizon)`；
- `fk_edge_outcome_supersedes` 由
  `(supersedes_outcome_id, opportunity_id) → (outcome_id, opportunity_id)`
  收紧为
  `(supersedes_outcome_id, opportunity_id, evidence_id, horizon) → (outcome_id, opportunity_id, evidence_id, horizon)`。

于是「同 opportunity + 同 evidence + 同 horizon」由 PostgreSQL 自身保证，绕过 repository 直接
写库也无法产生 cross-scope chain。**未引入 trigger / stored procedure**；revision adjacency 继续
由 service 层负责（FK 无法表达）。

ORM metadata 与迁移完全一致（同一个 `uq_edge_outcome_id_scope` + 同一 4 列 FK）。

### 6.3 G5 schema head

`ReplayTradingRunner.schema_head` `20260913_0008 → 20260913_0009`；
`test_se_02a_edge_persistence.py::HEAD_REVISION` 同步为 `20260913_0009`。
（RRF-02 专属测试的 `_FIX_HEAD` 保持 `20260913_0008`：它证明的是 0007→0008 那次 fail-closed
升级，语义不应被 0009 改写。）

---

## 7. Migration

文件：`backend/alembic/versions/20260913_0009_outcome_revision_scope.py`
（`revision = 20260913_0009`，`down_revision = 20260913_0008`）。

`upgrade()`：

1. **preflight**（任何 DDL 之前）：统计 `supersedes_outcome_id IS NOT NULL` 且 predecessor
   不存在或 scope 不一致的行；
2. 若有 → `RuntimeError`（消息含 `20260913_0009` 与 `20260913_0008`），事务整体回滚，
   `alembic_version` 不变，行保持原样；
3. 收敛 FK、替换唯一约束、建立 4 列 scoped FK。

`downgrade()`：反向恢复 `(supersedes_outcome_id, opportunity_id)` FK 与
`uq_edge_outcome_id_opportunity`。

---

## 8. Existing-Row Policy（Human Semantic Decision 的执行）

本批对**已有 invalid outcome chain 一律 FAIL CLOSED / ABORT MIGRATION**。**没有**任何自动行为：

- 不改 `supersedes_outcome_id`
- 不拆 revision chain
- 不重新编号
- 不猜正确 predecessor
- 不删除 outcome
- 不改 `horizon` / `evidence_id`

理由：非法形状只能证明该行不是合法 immutable correction，**不足以证明正确 predecessor 是谁**，
自动改写即等于伪造 lineage。非法行原样保留供人工审计。

---

## 9. Files Changed

| 文件 | 变更 |
|---|---|
| `backend/src/marketpulse/edge/repository.py` | predecessor 校验增 `evidence_id` / `horizon`；docstring 说明 scope |
| `backend/src/marketpulse/db/models.py` | `uq_edge_outcome_id_scope` 取代 `uq_edge_outcome_id_opportunity`；`fk_edge_outcome_supersedes` 扩为 4 列；docstring |
| `backend/alembic/versions/20260913_0009_outcome_revision_scope.py` | 新增（fail-closed preflight + 约束收敛 + reversible downgrade） |
| `backend/src/marketpulse/g5/replay.py` | `schema_head` = `20260913_0009` |
| `backend/tests/test_se_02a_edge_persistence.py` | `HEAD_REVISION` = `20260913_0009`；新增 8 个 FIX-02 回归 + 3 个 harness helper |

---

## 10. Business Behavior

- **revision chain scope** = `(opportunity_id, evidence_id, horizon)`；每个 scope 独立编号。
- `revision = 1` ⇒ `supersedes_outcome_id IS NULL`（未变）。
- `revision > 1` ⇒ 必须 supersede 同 scope 的 `revision - 1`；跨 opportunity / cross-evidence /
  cross-horizon / 跳号 / 悬空一律 `EdgeInvalidOutcomeSupersedes`。
- 同 scope + 同 revision + 同 hash ⇒ `IDEMPOTENT`；同 logical revision + 不同 hash ⇒
  `EdgeOutcomeConflict`（均未变）。
- 绕过 service 直接 INSERT cross-scope supersedes ⇒ PostgreSQL `IntegrityError`。
- 0008 → 0009 遇 cross-scope 存量行 ⇒ `RuntimeError` + rollback，`alembic_version` 停在 0008。

---

## 11. Verification

### 11.1 验证隔离（§23 要求）

- 独立 disposable PostgreSQL：`postgres:16-alpine`，容器 `marketpulse-se-fix-02-pg` @
  `127.0.0.1:5437`（**非** 5432 共享库，**非** N01-7 的 5434）。
- 测试经 gitignored `.env` 路由（仅覆盖 `DATABASE_URL` 一行）：`Settings().database_url` =
  `postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5437/marketpulse`，
  `test_se_02a_edge_persistence.py` 的 `PRIMARY_URL` 同值；`_edge_database()` 在该实例内
  `CREATE DATABASE marketpulse_se02a_*`，因此所有测试库都在 5437 上。
  `TEST-ISO-01` **未修改**。
- 共享 5432 只读快照：revision `20260905_0004`、24 表、digest
  `03a9cf6b44712571246a0efcee42629f6c71ba0eac91d8d514a80f29f09546dc`，**无 edge 表、未被本批升级**。
- 收尾：5432 与 5437 上的 `marketpulse*` 库均只剩 `marketpulse`，**无 disposable 残留**。

### 11.2 命令与结果

| 门 | 命令 | 结果 |
|---|---|---|
| 基线（改动前） | `pytest backend/tests/test_se_02a_edge_persistence.py -q` | `32 passed` (55.14s) |
| FIX-02 focused | 同上 `-k fix02` | **`8 passed`** (15.78s) |
| 定向回归 | `pytest test_se_02a_edge_contracts test_se_02a_edge_persistence test_se_02b_attribution test_se_02b_opportunity_capture test_group5_1..5_4 -q` | **`196 passed`** (272.84s) |
| Full backend | `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` | **`371 passed, 1 warning`** (437.93s) |
| Ruff | `py -3.14 -m ruff check backend/src backend/tests scripts backend/alembic` | `All checks passed!` |
| Compileall | `py -3.14 -m compileall -q backend/src backend/tests scripts backend/alembic` | rc=0 |
| Whitespace | `git diff --check` | 无输出（PASS） |
| Alembic heads | `py -3.14 -m alembic heads`（5437） | `20260913_0009 (head)` 单 head |
| Alembic current | `py -3.14 -m alembic current`（5437） | `20260913_0009 (head)` |
| G5 schema head | `ReplayTradingRunner.schema_head` | `20260913_0009` = Alembic head |
| 5437 约束实测 | `pg_get_constraintdef` | `fk_edge_outcome_supersedes :: FOREIGN KEY (supersedes_outcome_id, opportunity_id, evidence_id, horizon) REFERENCES edge_forward_outcomes(outcome_id, opportunity_id, evidence_id, horizon)`；`uq_edge_outcome_id_scope :: UNIQUE (outcome_id, opportunity_id, evidence_id, horizon)`；`uq_edge_outcome_id_opportunity` 已不存在 |

唯一的 warning 是既有 FastAPI/Starlette `TestClient` deprecation（非本批引入）。
`ruff format --check` **不是**本项目门（accepted main 上即有 25 个文件未 format，已实测 HEAD
版本对 `db/models.py:398`、`edge/repository.py:213` 报同样位置 ⇒ 本批未引入新的 format 差异）；
本批新增的迁移文件单独 `ruff format --check` = `already formatted`。

---

## 12. Acceptance Matrix（对照任务书 §25）

| # | 项 | 结果 | 证据 |
|---|---|---|---|
| F2-01 | Repository Truth | PASS | §2；main `fc61924`、head `20260913_0008` 实时读取一致 |
| F2-02 | Scope identity = `(opportunity, evidence, horizon)` | PASS | §6.1/§6.2；`uq_edge_outcome_id_scope` + 4 列 FK |
| F2-03 | Service Cross-Evidence rejected | PASS | `test_fix02_cross_evidence_and_cross_horizon_outcome_revisions_are_rejected` |
| F2-04 | Service Cross-Horizon rejected | PASS | 同上 |
| F2-05 | Adjacency（只能 supersede `revision - 1`） | PASS | `test_fix02_cross_opportunity_skipped_and_dangling_outcome_revisions_are_rejected`（R1→R3 拒绝） |
| F2-06 | Idempotency（same revision + same hash） | PASS | `test_fix02_outcome_idempotency_and_conflict_are_preserved` |
| F2-07 | Conflict（same logical revision + different hash） | PASS | 同上（`EdgeOutcomeConflict`） |
| F2-08 | DB Backstop | PASS | `test_fix02_database_rejects_cross_scope_supersedes`（DB1/DB2 拒绝、DB3 允许） |
| F2-09 | Existing invalid migration（0008→0009 abort + rollback） | PASS | `test_fix02_invalid_legacy_outcome_scope_aborts_the_upgrade` |
| F2-10 | Clean migration（upgrade/downgrade/re-upgrade） | PASS | `test_fix02_clean_migration_chain_reaches_0009_and_round_trips`；`test_fix02_valid_legacy_outcome_chain_survives_and_the_scoped_fk_is_enforced` |
| F2-11 | Single Alembic head | PASS | `20260913_0009 (head)` |
| F2-12 | G5 Schema Head 一致 | PASS | `schema_head` = `20260913_0009`；G5-1..5-4 全通过 |
| F2-13 | FIX-01 / SE-02A / SE-02B Regression | PASS | 定向 `196 passed`；full `371 passed` |
| F2-14 | Full Backend | PASS | `371 passed, 1 warning` |
| F2-15 | Scope（无 SE-02C/SE-02D/unrelated） | PASS | 改动文件仅 §9 列出的 5 个 + docs |

---

## 13. Self-Check（Reviewer 应重点挑战处）

1. **`uq_edge_outcome_id_opportunity` 被“替换”而非“新增”**：它原本只服务于旧的过宽 FK；
   保留会造成两个冗余唯一约束，且 ORM/迁移必须同时声明两个。选择替换，`downgrade()` 完整还原。
   任务书 §8 允许 "最小 additive/schema correction"，未指定保留旧约束。
2. **preflight 只覆盖 service 之外的既有行**：`0008` schema 下 `fk_edge_outcome_supersedes`
   已保证 predecessor 存在，但 preflight 仍用 `LEFT JOIN` 显式检测 dangling，避免依赖 FK 现状。
3. **adjacency 未下沉到 DB**：FK 无法表达 `revision = N - 1`；任务书 §8 明确不得为此引入
   trigger / stored procedure，故保持 service 层。
4. **`_FIX_HEAD` 未随 head 前移**：RRF-02 测试证明的是 0007→0008 的 fail-closed 语义，
   保持不变才能继续精确表述该边界；`HEAD_REVISION` 才跟随真实 head 前移。
5. **`ruff format --check` 未纳入门**：项目门是 `ruff check`；已在 §11.2 用 HEAD 版本对照证明
   本批未引入新的 format 差异，而非靠"看起来没问题"。

---

## 14. Result

```text
SE-ARCH-FIX-02 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW
```

Implementation Commit：`4c835828f482875d1d7ce934f8808d3953a9105b`
Branch：`se-arch-fix-02-outcome-revision-chain-scope`（base `fc61924`）

`SE-02C` 保持 `BLOCKED / NOT STARTED`。

---

## 15. Remaining

- Independent Review → Human Acceptance → Pre-SE-02C Re-Gate（**未执行**，本批边界之外）。
- `SE-02C` / `SE-02D` / `N01-8` / Integrated Runtime Host：`NOT STARTED`。

## 16. Known Risks / Notes

- **`RRF-03`（P2，保持独立）**：`scripts/verify_n01_7_f01_r1_migration_gate.py` 仍钉
  `single_head == ["20260912_0006"]`（line 761）。新增 `20260913_0009` 后，该 accepted 证据
  脚本若重跑会在 head 断言处失败 —— 这是 FIX-01 时期就已记录的 RRF-03 状态
  （该脚本 pin 的是更早的 head），**本批按 §21 未修改它**。它不在 pytest 默认集合中
  （`scripts/` 不被 `pytest backend/tests` 收集），故不影响本批任何验证门。
  Supersede / re-baseline 需人工决定。
- 本批**未**执行真实网络验证，也未触碰 OKX / AI provider；无网络面。
- 迁移为 schema 收敛：在存量合法数据上通过；在存量非法数据上按设计 abort。

## 17. Context For Next AI

- 本批唯一实现提交是 `4c83582`（parent `fc61924`），**未** merge `main`。
- 若要复现验证：新建 clean worktree → 独立 disposable PostgreSQL（勿用 5432 / 5434）→
  gitignored `.env` 只写 `DATABASE_URL` → 先 `alembic upgrade head`（隔离实例的 `marketpulse`
  库必须在 head，否则依赖 `Settings().database_url` 的模块级 engine 会全批 `relation does not exist`）
  → `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q`。
- 迁移 `20260913_0009` 之后，`ReplayTradingRunner.schema_head` 必须与 Alembic head 同步，
  否则 `ReplayWorkspaceGuard` 会拒绝启动 replay。

## 18. Evidence

| 证据 | 位置 |
|---|---|
| 实现提交 | `4c83582`（branch `se-arch-fix-02-outcome-revision-chain-scope`） |
| 隔离实例 | Docker `marketpulse-se-fix-02-pg` @ `127.0.0.1:5437`（本次会话创建） |
| 逐条测试输出 | `E:/Temp/se-fix-02/`：`baseline_se02a.txt`、`fix02.txt`、`regression.txt`、`full.txt` |
| 5432 / 5437 快照与约束定义 | 本次会话 `asyncpg` 只读查询输出（见 §11.1/§11.2） |

---

## 19. Human Acceptance + Final Main Integration Closeout（2026-09-13）

- Task: `SE-ARCH-FIX-02A`｜Human Acceptance Closeout（Human Acceptance Integration / Final
  Closeout；**非**新实现、**非**重新 Review、**非** SE-02C 启动）。
- **Human Acceptance = `APPROVED`**（2026-09-13）：SE-ARCH-FIX-02｜Outcome Revision Chain Scope。
- 前置 Independent Review Verdict = `PASS — READY FOR HUMAN ACCEPTANCE`；F2-01～F2-15 全 PASS；
  无 P0/P1/P2/P3 Finding。本节**不**重新争论该 Review 结论。

### 19.1 最终 Accepted Semantic（必须按此表述）

Forward Outcome revision chain scope = `(opportunity_id, evidence_id, horizon)`；
`revision N > 1` 只能 supersede 同 `opportunity_id` + 同 `evidence_id` + 同 `horizon` 的
`revision N - 1`。

责任划分（**不得**描述成数据库负责 adjacency）：

- **数据库负责 scope integrity** — `uq_edge_outcome_id_scope`
  `(outcome_id, opportunity_id, evidence_id, horizon)` 与 4 列 `fk_edge_outcome_supersedes`。
- **Service 同时负责** scope integrity **与** revision adjacency
  （FK 无法表达 `revision = N - 1`；未引入 trigger / stored procedure）。

### 19.2 Preflight（实测，未依赖导航信息）

| 项 | 实测值 |
|---|---|
| `git ls-remote origin refs/heads/main` | `fc619242c99a794a2eb2b87ee02b8b72aa782f05` |
| `git ls-remote origin refs/heads/se-arch-fix-02-outcome-revision-chain-scope` | `15da7c1bac719d17271c7df9fcccbf80535b6d1b` |
| `merge-base(main, candidate)` | `fc619242c99a794a2eb2b87ee02b8b72aa782f05`（== Accepted Main） |
| `git rev-list --left-right --count main...candidate` | `2 / 0`（main ahead 0，candidate ahead 2、behind 0） |
| candidate 链 | `fc61924 → 4c83582（implementation）→ 15da7c1（evidence）` |
| 本地 `main` ref | `fc619242c99a794a2eb2b87ee02b8b72aa782f05` |

**未触发 STOP**：remote `main`、candidate SHA、merge-base 均与任务书导航一致。

### 19.3 Closeout 提交与集成

- Docs-only closeout commit：`docs(edge): accept outcome revision chain scope`，parent = `15da7c1`；
  仅 `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` / 本 dev_log 变化。
- 集成方法 = **`FAST-FORWARD ONLY`**：
  `fc619242 → 4c835828 → 15da7c1 → docs-only closeout`。
  未创建 merge commit 到 `main`；未 squash / rebase / cherry-pick / 重建历史 / force push。
- Pre-push drift check：`git ls-remote origin refs/heads/main` 仍为 `fc619242…`（未漂移）⇒ 允许 push。
- Post-push read-back 与 ancestry check 证据见本窗口 Final Report（`15da7c1` / `4c835828` /
  `fc619242` 均为 final `main` 的 ancestor）。
- Closeout 期间四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`。

### 19.4 验收后状态

| 项 | 状态 |
|---|---|
| SE-02A | `ACCEPTED / COMPLETE` |
| SE-02B | `ACCEPTED / COMPLETE` |
| SE-ARCH-FIX-01 | `ACCEPTED / COMPLETE` |
| SE-ARCH-FIX-02 | `ACCEPTED / COMPLETE` |
| SE-02C | `BLOCKED / NOT STARTED` |
| Migration head | `20260913_0009`（单 head） |

**Migration 链（全部保留，未重写 revision identity）**：`20260912_0006`（N01-7-F01）→
`20260913_0007`（FIX-01 Capture Anchor）→ `20260913_0008`（FIX-01 Review Fix）→
`20260913_0009`（FIX-02 Outcome Revision Scope）。

⚠️ **FIX-02 Accepted ≠ SE-02C MAY START**：SE-02C 仍需独立获批的 **Pre-SE-02C Re-Gate**；
只有该 Gate 返回 `PASS — SE-02C MAY START` 才允许启动。本窗口**未**启动该 Gate，也**未**启动 SE-02C。

### 19.5 Historical P2（保持原状，本任务未顺手修）

`TEST-ISO-01` / `RRF-03`（`DEFERRED`）/ `RRF-04` 维持既有状态与证据边界，**未**修改。

### 19.6 Result

```text
SE-ARCH-FIX-02 = ACCEPTED / COMPLETE
```

Closeout commit SHA 由本窗口 Final Report 记录（commit 自身 SHA 无法写入自身）。
