# N01-VAL-FIX-02 — N01-B PostgreSQL Activity Evidence Stability

## Result

`VALIDATED / AWAITING REVIEW`。本记录只说明 validation implementation 与真实验证已完成；
不构成 Independent Review 或 Human Acceptance，未推进 `main`，未修改 `N01-A` / `N01-B`
既有验收结论，也未声明 `N01-C` 开始或 `N01 overall` 被接受。

状态汇总：

```text
N01-VAL-FIX-01 = REVIEW PASS / CLOSEOUT BLOCKED BY F02
N01-VAL-FIX-02 = VALIDATED / AWAITING REVIEW
N01-A          = ACCEPTED / COMPLETE
N01-B          = ACCEPTED / COMPLETE
N01 overall    = NOT ACCEPTED
N01-C          = NOT STARTED
```

## Repository Truth / Workspace Isolation

- `Accepted Main`（preflight 实时读取）：`git ls-remote origin refs/heads/main` =
  `git rev-parse main` = `e0dab188e55c32b7607c18a66644d25449dc2236`。文档静态 SHA 未被当作事实源。
- Task Base（任务书指定）：`N01-VAL-FIX-01` 已评审 commit
  `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2`（其 parent = `e0dab188`）。
- Branch：`fix/n01-val-n01b-postgres-activity-evidence`，从 Task Base 创建。
- Isolated clean worktree：`E:\Documents\MarketPulse-AI-n01-val-fix-02`（开工时
  `git rev-parse HEAD` = `67b0cb5`，`git status --porcelain` 为空，与 Task Base 零差异）。
- 未修改的其它工作树：历史脏工作树 `E:\Documents\MarketPulse AI`
  （`prb-01-product-requirements-baseline`）、`-n01-a`、`-n01-b`、`-n01-fix-01`、
  `-n01-val-fix-01`。Nor did this task reset / stash / clean any of them.
- **未修改已评审 commit `67b0cb5`**：本任务在其之上新增 commit；`67b0cb5` 的 tree 与
  消息保持不变，远端 `refs/heads/fix/n01-val-postgres-lifecycle-evidence` 仍指向 `67b0cb5`。
- 环境：Python `3.14.2`、SQLAlchemy `2.0.52`、asyncpg `0.31.0`、
  Docker `marketpulse-postgres`（`Up ... (healthy)`，`127.0.0.1:5432`）。
- 沙箱说明（环境旁路，非产品行为）：本机新建分支/worktree 的 ref 写入会静默丢失，故本任务用
  直接写 `.git/refs/heads/...` 文件的方式建立分支 ref；`N01-VAL-FIX-01` 的本地 ref 在同一步骤
  中被沙箱一并吞掉，已按**原值 `67b0cb5` 恢复**（未改动其 commit，远端一直是 `67b0cb5`）。

## Finding

`N01-VAL-F02`。目标文件 `backend/tests/test_n01_okx_paper_safety.py`。两个 PostgreSQL
lifecycle 断言：

```text
test_n01_b_freshness_boundary_blocks_risk_increasing_actions_and_fails_closed
test_n01_b_post_transition_controlled_fresh_bbo_still_triggers_protection
```

原先都使用：

```python
SELECT count(*) AS sessions,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction
FROM pg_stat_activity WHERE datname = :database_name
```

并在 `await engine.dispose()` 之后立即断言 `activity_after == baseline`。

这是错误的 ownership model（所有权模型）：`datname` 只能说明某个 PostgreSQL backend 正在该
数据库上工作，**不能**证明该 backend 是 validation harness 拥有的客户端连接。
`N01-VAL-FIX-01` 已实际捕获反例：`backend_type='autovacuum worker'`、`usename=null`、
`application_name=''`——服务端拥有的维护进程同样出现在同一 `datname` 结果集里。

## Historical Failure — what is known / what is NOT proven

**已知**：

```text
8 次 full backend 运行
7 PASS
1 FAIL
```

唯一失败的 test 是
`test_n01_b_freshness_boundary_blocks_risk_increasing_actions_and_fails_closed`，
且**该次失败执行没有 traceback**。

**未证明（必须准确记录）**：

> The test contains a source-proven defective DB observation model. Whether the single
> uncaptured full-suite failure was caused by that exact assertion remains **unproven** unless
> reproduced/captured.

即：**不得**声称"该次 full-suite failure 已确定发生在 `activity_after == baseline`"。
它只是**可能**发生在该断言；缺陷本身由源码与 `N01-VAL-FIX-01` 的捕获证据独立证明。

## Diagnosis

### Reproduction attempt (bounded, Task Base unmodified)

在**未修改的** Task Base（`67b0cb5`）上，用一个**仓库外**只读 pytest 插件
（`E:\Temp\n01_val_f02_diag\f02_diag.py`：包装 `_database_activity`，在不改变计数逻辑的前提下
额外 dump 该 disposable DB 上 `pg_stat_activity` 的全部身份字段）执行有界复现：

| 批次 | 执行内容 | 结果 |
|---|---|---|
| A | full backend `pytest backend/tests -q -p f02_diag` ×1 | `1 failed, 171 passed`；失败点是 **`test_group4.py`**（见下「Out-of-Scope Finding」），**N01-B activity 断言全部为 0** |
| B | `pytest backend/tests/test_n01_okx_paper_safety.py -q -s -p f02_diag` ×12 | `12/12 PASS`；24 个观测点全部 `{'sessions': 0, 'idle_in_transaction': 0}` |

**复现结论**：`single historical full-suite failure not independently recaptured`。
12 次文件级执行 + 1 次 full suite 均未再次出现该断言失败，也**没有观测到任何非零行**
（既无 client backend，也无 server-owned backend）位于 baseline 或 dispose 之后。
依任务书 §7，**不阻塞 Fix**：继续修复已被源码与 `N01-VAL-FIX-01` 证据证明有缺陷的观测模型。

原始产物：`E:\Temp\n01_val_f02_diag\repro_12x_transcript.txt`。

### Source-proven observation defect

不在"是否存在一次历史失败"上立论，而在**观测模型本身**上立论。可独立复核的事实：

1. 旧 gate 只按 `datname` 聚合 `pg_stat_activity`，缺少 `backend_type` / `application_name`
   ownership 过滤。
2. `N01-VAL-FIX-01` 在同栈上真实捕获到 `datname` 命中却是 `autovacuum worker` 的行，并进一步
   证明了 disposable DB 内确实会产生死元组、确实会被 autovacuum/autoanalyze 作用
   （见 `dev_log/2026-09-10-n01-val-fix-01-postgres-lifecycle-stability.md`）。
3. 因此，是否以及何时出现该行**取决于服务端调度**，不受测试控制；旧 gate 把不受控的服务端
   事实纳入了"cleanup 是否成功"的判据。

### Captured backend identity

本任务**未**新增捕获（复现中未再出现非零行）。身份证据沿用 `N01-VAL-FIX-01` 已完成捕获的
同一查询路径上的真实反例：

```json
{
  "database_name": "marketpulse_n01_a_fe9127935ec9",
  "observed": { "sessions": 1, "idle_in_transaction": 0 },
  "rows": [
    {
      "backend_type": "autovacuum worker",
      "usename": null,
      "application_name": "",
      "state": "active",
      "wait_event_type": "IO",
      "wait_event": "WALSync",
      "last_query": "autovacuum: ANALYZE pg_catalog.pg_class"
    }
  ]
}
```

新 detector 对 `pid` / `backend_type` / `application_name` / `usename` / `state` /
`wait_event_type` / `wait_event` / `last_query` 全字段留证，下条 full-suite 若再失败可立即定位。

## Fix

### Old observation model

```python
# 在 await engine.dispose() 返回的同一瞬间与 baseline 做相等比较
SELECT count(*) AS sessions,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction
FROM pg_stat_activity WHERE datname = :database_name
```

只有 `datname` 一个判据，无法区分"本 harness 拥有的客户端连接"与"服务端在该库上运行的维护进程"。

### New observation model

1. **所有权可识别**：每个 N01-B PostgreSQL 测试的 engine 通过
   `connect_args={"server_settings": {"application_name": "marketpulse-n01-b-owned-<purpose>"}}`
   获得**唯一** `application_name`（`freshness` / `post-transition-trigger` /
   `injected-leak`）。
2. **observer 不污染被测库**：观测统一走 `marketpulse-n01-b-observer`，且连接
   **primary 库**（`Settings().database_url`），其自身后端 `datname = 'marketpulse'`，
   永远不进入 disposable DB 的 client-session 计数。
3. **所有权拆分**：快照按 `backend_type` 拆为
   `client_sessions`（`client backend`，harness 唯一可能拥有/泄漏的资源）与
   `server_sessions`（服务端维护进程，仅作观测证据记录），另含 `idle_in_transaction`。
4. **显式最终条件 + 硬截止**：`_wait_for_owned_client_cleanup()` 轮询（间隔 `2 ms`）直到
   `client_sessions == 0`，条件是**明确的最终状态**，一旦成立即返回；超过 hard deadline
   （`1.0 s`）仍未成立即 `released = False`，测试 FAIL。
5. **跨归属断言**：任何被观测到、但 `application_name != 本测试 owned 名` 的 **client**
   backend 都进入 `foreign_rows` 并直接 FAIL。
6. **deadline 依据（沿用既有测量，不新造尺度）**：本栈 `N01-VAL-FIX-01` 实测客户端连接
   关闭后最长可见时间 `8.3 ms`（160 real lifecycles + 12×24 / 10×80 突发关闭、含 CPU 竞争）；
   deadline = `1.0 s` ≈ 该实测最大值的 120 倍。本次未重做该测量，故**不主张**新的时间常数，
   只声明它来自当前 SQLAlchemy / asyncpg / PostgreSQL 环境的既有实测证据。

### Server backend handling

服务端维护进程（`backend_type != 'client backend'`，例如 autovacuum worker）：

- 记入 `server_backends` / `server_sessions` 作为**观测证据**并打印；
- **不**计入 `client_sessions`；
- 因此**不**被判定为 connection leak。

### Why this does NOT weaken leak detection

- harness 唯一能创建/泄漏的后端类型是 `client backend`；服务端 autovacuum/后台进程不可能由
  测试创建，也不可能被测试"泄漏"。
- 判据仍是零容忍：`client_sessions` 必须归零，**没有** `baseline + 1` 容差。
- 观测边界由"某一瞬间的总行数等于 baseline"改为"测试拥有的客户端连接必须在有界清理契约内
  真正终止"——这是**更强**的契约：旧模型只要 dispose 后瞬间恰好为 0 就通过，即使某个连接稍后
  才真正关闭；新模型必须等到客户端连接真正消失，否则在 deadline 处 FAIL。
- 未引入 rerun-the-test retry，未用固定 `sleep()` 伪装 cleanup proof。
- `N01-A Acceptance Fix #2` 曾**撤销**的 `baseline + 1` 放松**没有**被重新引入。

### Negative Leak Strength（req §13）

新增一个**极小**的 tests-only 负向对照
`test_n01_b_owned_client_leak_is_never_reported_as_released`：持有一个 test-owned client 连接
（`SELECT 1` 后保持事务打开 → `idle in transaction`），调用**同一个** detector。实测：

```text
{'n01_b_injected_leak': {'leak_pid': 4020, 'detected_client_sessions': 1,
 'detected_idle_in_transaction': 1, 'detected_seconds': 1.036357,
 'cleanup_deadline_seconds': 1.0}}
```

`released = False`、`client_sessions = 1`、`idle_in_transaction = 1`、`elapsed >= deadline`、
行内含注入 `pid` 与注入 `application_name`，且该行归入 owned 而非 `foreign_rows`。
即满足 **`client backend > 0 → cleanup condition cannot report success`**。
未为此复制 N01-VAL-FIX-01 的数百行负向基础设施。

## N01-B DB Cleanup Evidence（实测，`-s`）

正常场景（两个 PostgreSQL 测试各一次）：

```text
freshness        : baseline client=0 server=0
                   cleanup released=True in 0.064142s (1 poll), transient=0, foreign=[]
                   final client=0 server=0 idle_in_transaction=0, server_backends_seen=[]
post-transition  : baseline client=0 server=0
                   cleanup released=True in 0.055374s (1 poll), transient=0, foreign=[]
                   final client=0 server=0 idle_in_transaction=0, server_backends_seen=[]
```

- `leftover marketpulse_n01_b_* databases = 0`（两个测试内均 `assert ... == 0`）。
- `client_sessions = 0`；`idle_in_transaction = 0`。
- 本窗口未观测到 server-owned maintenance backend；其处理路径已实现并有负向/服务端分类逻辑，
  但**未**在本窗口被真实触发（如实记录，不夸大）。

## Out-of-Scope Finding（本任务未修，必须上报）

在 Task Base（`67b0cb5`，未改动）的 full-suite baseline 运行中观察到 **1 个与本任务无关的
既有 flaky 失败**：

```text
FAILED backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen
>   assert order.status == OrderStatus.CANCELLED and position.quantity == 0
E   AssertionError: assert ('FILLED' == <OrderStatus....: 'CANCELLED'>  ... - CANCELLED  + FILLED)
backend\tests\test_group4.py:1709
```

- 独立复跑同 test：`5/5 PASS`（2.74 / 1.91 / 1.90 / 1.85 / 1.85 s）→ 属**套件上下文下的时序
  flaky**，不是稳定失败。
- `test_group4.py` 未被 `N01-VAL-FIX-01` 触碰（`git diff --name-only e0dab188..67b0cb5` 只有
  `AI_CONTEXT.md`、`PROJECT_STATE.md`、`test_n01_runtime_resource_lifecycle.py`、FIX-01 dev_log），
  故该现象**在 Accepted Main `e0dab188` 上同样存在**，为 pre-existing。
- 依 CIP-05，本任务**不修**该问题（超出批准 Scope），仅记录；证据：
  `E:\Temp\n01_val_f02_diag\group4_flake_transcript.txt`。
- 本 Fix 之后的 2 次 full-suite 连续运行**未**复现该失败（各 `173 passed`）。

## Production Code Changed

`NO`。`git diff e0dab188..HEAD -- backend/src backend/alembic` 为空；未修改 schema、migration、
production OKX provider、G2/G3/G4/G5 业务语义，也未开始 `N01-C`。

## Files Changed

- `backend/tests/test_n01_okx_paper_safety.py`（唯一代码改动；含 1 个新增 tests-only 负向对照）
- `dev_log/2026-09-10-n01-val-fix-01-postgres-lifecycle-stability.md`
  （**仅**删除文件末尾多余空行；无实质内容改动）
- `dev_log/2026-09-10-n01-val-fix-02-n01b-postgres-activity-evidence.md`（本文件）
- `PROJECT_STATE.md`、`AI_CONTEXT.md`（仅最小状态同步）

`scripts/verify_n01_b_okx_paper_safety.py` **未改动**：`_database_activity` 被保留为
ownership-aware 诊断接口，其返回字典仍含向后兼容的 `idle_in_transaction` 键，故该 real-OKX
validation script 无需任何兼容调整。

## N01-B Business Semantics

本 Fix **只**改 DB lifecycle evidence。以下语义**完全未变**（原断言逐条保留、全部仍通过）：
`Fresh → Stale → Fresh`、`CORE_MARKET_DATA`、`CORE_DATA_STALE`、`SystemRiskGate`、
BUY fail-closed（`RUNTIME_STATE_DATA_DEGRADED`）、SELL risk-reducing semantics、
no fabricated Fill、Position Protection、STOP_LOSS deterministic case、economic duplicate safety、
reconciliation。

## Known Risks

1. **历史失败未被复现**：本窗口以 12 次文件级 + 1 次 full suite 的有界复现未捕获到该断言失败。
   Fix 的依据是**源码缺陷 + FIX-01 的既有捕获证据**，而非一次新失败。若 Independent Review
   要求"同一断言的失败复现"，本任务无法提供，并如实声明。
2. **deadline = 1.0 s** 仍依赖 FIX-01 的实测（≤8.3 ms）。若未来换用远慢的存储/网络，需按新
   实测重新论证；当前证据不支持更大值。本窗口观测到的 release 时间为 55–64 ms（含 observer
   连接建立），仍显著低于 deadline。
3. **server-owned backend 未被真实触发**：分类逻辑已实现且负向对照证明 detector 不会误报成功，
   但本窗口没有出现真实 autovacuum 行可作正例；正例证据来自 FIX-01 的同查询路径捕获。
4. **out-of-scope flake**：`test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`
   在负载下的套件上下文中可能 flaky（本窗口 1 次），会威胁"full backend 连续 PASS"门；
   本窗口 2 次连续 full suite 未复现。
5. `test_n01_okx_paper_safety.py` 依赖真实 OKX 的 `scripts/verify_n01_b_okx_paper_safety.py`
   属独立 real-network 门，**未**在本次回归中执行（需显式运行，且受本机代理环境 `N01-B-E01`
   影响）。

## Final Recommendation

`READY FOR INDEPENDENT REVIEW`

## Verification

全部在 `E:\Documents\MarketPulse-AI-n01-val-fix-02`、`HEAD = 67b0cb5` + 本 Fix 工作树改动、
Docker `marketpulse-postgres` 上**实际执行**（`PYTHONPATH=backend/src py -3.14`）：

| Gate | 命令 | 结果 |
|---|---|---|
| N01-B focused 1 | `pytest backend/tests/test_n01_okx_paper_safety.py -q -s` | `4 passed in 10.03s` |
| N01-B focused 2 | 同上 | `4 passed in 10.24s` |
| N01-B focused 3 | 同上 | `4 passed in 10.19s` |
| N01-B focused 4 | 同上 | `4 passed in 9.82s` |
| N01-B focused 5 | 同上 | `4 passed in 9.61s` |
| N01-VAL-FIX-01 focused 1 | `pytest backend/tests/test_n01_runtime_resource_lifecycle.py -q` | `6 passed in 7.89s` |
| N01-VAL-FIX-01 focused 2 | 同上 | `6 passed in 8.08s` |
| N01-VAL-FIX-01 focused 3 | 同上 | `6 passed in 7.89s` |
| G2 | `pytest backend/tests/test_group2.py -q` | `30 passed in 4.82s` |
| G3 | `pytest backend/tests/test_group3.py -q` | `16 passed in 18.26s` |
| G4 | `pytest backend/tests/test_group4.py -q` | `77 passed in 90.26s` |
| Full backend run 1 | `pytest backend/tests -q` | `173 passed, 1 warning in 226.89s` |
| Full backend run 2 | `pytest backend/tests -q` | `173 passed, 1 warning in 223.85s` |
| Ruff | `ruff check backend/src backend/tests scripts` | `All checks passed!` |
| compileall | `compileall -q backend/src backend/tests` | exit 0 |
| diff-check (current) | `git diff --check` | exit 0 |
| diff-check (range) | `git diff --check e0dab188..HEAD` | exit 0 |
| Production diff | `git diff e0dab188..HEAD -- backend/src backend/alembic` | 空 → `Production Code Changed = NO` |

- **Repetition Gate**：N01-B focused `5/5 PASS`（连续 5 次，每次 4 passed）；
  N01-VAL-FIX-01 focused `3/3 PASS`；full backend `2/2 PASS`（连续 2 次）。
- `173 = 既有 171 baseline + N01-VAL-FIX-01 新增负向对照 1 + 本任务新增负向对照 1`。
  1 条 warning 为既有上游 FastAPI/Starlette TestClient deprecation，非本次引入。
- 工作树最终改动文件（`git status --porcelain`）恰好为允许的 5 个（见「Files Changed」）。

### 诊断原始产物（仓库外，供 Independent Review 复核）

```text
E:\Temp\n01_val_f02_diag\f02_diag.py                    # 只读诊断插件（未入库）
E:\Temp\n01_val_f02_diag\repro_12x_transcript.txt       # 12 次文件级复现记录
E:\Temp\n01_val_f02_diag\group4_flake_transcript.txt    # out-of-scope flake 的 traceback 与隔离复跑
E:\Temp\n01_val_f02_regression_focused.log              # focused + G2/G3/G4 回归日志
E:\Temp\n01_val_f02_full_1.log / _2.log                 # full backend 两次连续 PASS 日志
```
