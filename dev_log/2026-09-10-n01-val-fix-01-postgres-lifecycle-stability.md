# N01-VAL-FIX-01 — PostgreSQL Lifecycle Evidence Stability

## Result

`VALIDATED / AWAITING REVIEW`。本记录只说明 validation implementation 与真实验证已完成；
不构成 Independent Review 或 Human Acceptance，未推进 `main`，未修改 `N01-A` / `N01-B`
既有验收结论，也未声明 `N01-C` 开始或 `N01 overall` 被接受。

## Repository Truth / Workspace Isolation

- Task Base / `Accepted Main`（preflight 实时读取）：`git rev-parse main` =
  `git ls-remote origin refs/heads/main` = `e0dab188e55c32b7607c18a66644d25449dc2236`。
- Branch：`fix/n01-val-postgres-lifecycle-evidence`。
- Isolated clean worktree：`E:\Documents\MarketPulse-AI-n01-val-fix-01`（从 Task Base 创建，
  开工时 `git status --porcelain` 为空）。
- 历史脏工作树 `E:\Documents\MarketPulse AI`（`prb-01-product-requirements-baseline`）与
  `E:\Documents\MarketPulse-AI-n01-a` / `-n01-b` / `-n01-fix-01` 未被修改、reset、stash 或 clean。
- 环境：Python `3.14.2`、SQLAlchemy `2.0.52`、asyncpg `0.31.0`、Docker `marketpulse-postgres`（healthy）。

## Finding

`N01-VAL-F01`（沿用任务书编号）。现有测试
`backend/tests/test_n01_runtime_resource_lifecycle.py::test_n01_twenty_real_postgres_lifecycles_dispose_tasks_queues_inflight_and_connections`
在每次 `runtime.stop()` + `await engine.dispose()` 之后立即读取 `pg_stat_activity`，并要求
`activity == baseline`。N01-B Final Gate 曾观察到一次 `{'sessions': 1} != {'sessions': 0}`。

本任务**先复现、先诊断，再改 assertion**，不做任何猜测性放宽。

### 复现结果（原测试 assertion 完全未改）

在 `E:\Documents\MarketPulse-AI-n01-b`（`HEAD = e0dab18`，原测试文件未修改）上，用只读
pytest 插件替换 `_database_activity`（同一 engine、同一 SQL、同一调用时机，仅在计数非 0 时
补一次身份 dump）重复执行：

| 批次 | 执行次数 | 结果 |
|---|---|---|
| 纯计数复现（原测试逻辑） | 10 | `run 6: 1 failed, 4 passed in 3.83s` |
| 身份捕获复现（同一 assertion） | 30 | `run 26: 1 failed, 4 passed in 5.26s` |

即该现象在**当前 accepted `main` 上真实可复现**（2/40 次文件级执行）。

## Diagnosis

### 捕获到的异常行（决定性证据）

复现失败瞬间在同一连接上 dump 出 `pg_stat_activity` 的全部身份字段
（原始证据：`E:\Temp\marketpulse-n01-val-fix-01\lifecycle_flake_evidence.jsonl`）：

```json
{
  "database_name": "marketpulse_n01_a_fe9127935ec9",
  "observed": { "sessions": 1, "idle_in_transaction": 0 },
  "rows": [
    {
      "pid": 54926,
      "application_name": "",
      "usename": null,
      "state": "active",
      "backend_type": "autovacuum worker",
      "wait_event_type": "IO",
      "wait_event": "WALSync",
      "backend_start": "2026-09-10 15:01:05.704687+00:00",
      "state_change": "2026-09-10 15:01:05.738979+00:00",
      "xact_start": "2026-09-10 15:01:05.738979+00:00",
      "last_query": "autovacuum: ANALYZE pg_catalog.pg_class"
    }
  ]
}
```

### Root cause classification

该行**不是任何 harness 连接**：

- `backend_type = 'autovacuum worker'` —— 由 PostgreSQL 服务端创建与拥有的维护进程；
- `usename = null`、`application_name = ''` —— 没有客户端角色、没有 pool 会话标识，
  不可能是 SQLAlchemy/asyncpg 连接池建立的会话；
- `last_query = 'autovacuum: ANALYZE pg_catalog.pg_class'` —— 服务端自动维护动作。

因此：

```text
CASE A（transient server-side connection close visibility）= 不成立
CASE B（persistent leaked connection）              = 不成立
实际分类 = 观测模型缺陷（datname-only 过滤把服务端维护进程当成了 harness 连接）
```

任务书给定的 A/B 二分以"连接"为前提。证据表明第三类机制才是真因，故如实标注为
**`Case C — non-client server-side backend counted by a `datname`-only filter`**，
并明确声明它**取代**了此前 `TEST-SIDE TIMING OBSERVATION` 的假设性分类。

### 为什么 A/B 都被排除（测量证据）

1. **关闭路径无可见窗口**（`E:\Temp\marketpulse-n01-val-fix-01\diag_*_report.json`）：
   - 160 个真实 lifecycle cycle：首个观测点落在 `await engine.dispose()` 之后
     `0.85 – 8.35 ms`，**每一轮 client session 均为 0**；
   - 12 × 24 与 10 × 80 突发关闭（后者叠加 CPU 竞争）：首个观测点仍为 0，
     整批 24 条关闭耗时 1.3 ms、80 条 4.3–6.1 ms；
   - graceful `Connection.close()` 与强制 `Connection.terminate()` 对比：两者的行都在首个
     观测点（≤7.1 ms / ≤1.7 ms）前消失；
   - 历史观测模型自身的查询开销：dispose 之后 `49.1 – 72.6 ms`。
2. **无累积**：以上所有轮次结束后 client session 恒为 0，没有跨 cycle 或跨 DB 的残留。
3. **autovacuum 确实会作用到 disposable DB**（`diag_autovacuum_report.json`）：
   - `autovacuum = on`、`autovacuum_naptime = 1min`、`autovacuum_max_workers = 3`；
   - 真实 20-cycle workload 之后，disposable DB 内已存在死元组
     （`alembic_version` `n_dead_tup = 3`；`derived_observations` `n_mod_since_analyze = 40`），
     达到 autovacuum 候选条件；
   - 被人为置为候选的探针表被真实 autovacuum + autoanalyze 处理过
     （`autovacuum_count = 1`、`autoanalyze_count = 1`、
     `last_autovacuum = 2026-09-10T14:59:11.559552+00:00`）。

结论：`pg_stat_activity` 中 `datname = <disposable db>` 并不等价于"本测试拥有的连接"。

## Fix

### Old observation model

```python
SELECT count(*) AS sessions,
       count(*) FILTER (WHERE state = 'idle in transaction') AS idle_in_transaction
FROM pg_stat_activity WHERE datname = :database_name
```

在 `await engine.dispose()` 返回的同一瞬间与 `baseline` 做相等比较。它按 `datname` 聚合，
无法区分"本 harness 拥有的客户端连接"与"服务端在该库上运行的维护进程"。

### New observation model

1. **所有权可识别**：每个 lifecycle cycle 的 engine 通过
   `connect_args={"server_settings": {"application_name": "marketpulse-n01-vf01-lifecycle-cycle-NN"}}`
   获得唯一 `application_name`；观测引擎自身使用
   `marketpulse-n01-vf01-observer`，且连接的是 primary 库（不进 disposable DB 计数）。
2. **所有权拆分**：快照按 `backend_type` 拆为
   `client_sessions`（`client backend`，harness 唯一可能拥有/泄漏的资源）与
   `server_sessions`（服务端维护进程，仅作观测证据记录）。
3. **显式最终条件 + 硬截止**：`_wait_for_lifecycle_cleanup()` 轮询
   （间隔 2 ms）直到 `client_sessions == 0`，条件是**明确的最终状态**，一旦成立即返回；
   超过 hard deadline（`1.0 s`）仍未成立即 `released = False`，测试 FAIL。
   不使用 `sleep` 后重新断言，不使用 rerun-the-test retry。
4. **跨 cycle 归属断言**：任何被观测到、但不属于当前 cycle `application_name` 的
   **client** backend 都进入 `foreign_rows`，并直接 FAIL（`VF07`）。
5. **deadline 依据**：本栈实测客户端连接关闭后最长可见时间 `8.3 ms`（含 CPU 竞争下的
   80 路突发关闭），deadline = `1.0 s` 约为实测最大值的 120 倍；既足以吸收服务端慢关闭，
   又能让真实泄漏在 1 秒内失败。**未**使用"很大的值"兜底。

### Why this does NOT weaken leak detection

- harness 唯一能够创建/泄漏的后端类型是 `client backend`；服务端 autovacuum/后台进程
  无法由测试创建，也不可能被测试"泄漏"。
- 泄漏判据仍是零容忍：`client_sessions` 必须归零，**没有** `baseline + 1` 之类的聚合容差。
- 观测边界由"某一瞬间的总行数等于 baseline"改为"每个 lifecycle 拥有的连接必须在有界
  清理契约内真正终止，且不得跨 lifecycle 累积"——这是**更强的**契约：旧模型只要在
  dispose 后的瞬间恰好为 0 就通过，即使某个连接稍后才真正关闭；新模型必须等到
  客户端连接真正消失，否则在 deadline 处 FAIL。
- `idle_in_transaction` 仍逐 cycle 强制为 0；EventRuntime 侧 gate（worker task / queue /
  inflight / dedupe / worker_exceptions）强度未变。
- `N01-A Acceptance Fix #2` 曾**撤销**的 `baseline + 1` 放松**没有**被重新引入。

## Negative Control（关键 Acceptance Criteria）

新增 `test_n01_injected_leaked_connection_is_detected_then_released`：故意持有一个
test-owned client 连接（`application_name = marketpulse-n01-vf01-injected-leak`，
`SELECT 1` 后不提交，使事务保持打开），然后调用同一 detector。

实测（`-s` 输出）：

```text
{'leak_control_pid': 55588, 'detected_client_sessions': 1,
 'detected_idle_in_transaction': 1, 'detected_seconds': 1.014112,
 'released_seconds': 0.002921, 'cleanup_deadline_seconds': 1.0}
```

- 注入连接被**准确检出**：`released = False`、`client_sessions = 1`、
  `idle_in_transaction = 1`、行内含注入 `pid` 与注入 `application_name`；
- 以另一个 cycle 名提问时，该连接被正确归入 `foreign_rows`（所有权归属可识别）；
- 安全关闭注入连接后，同一 detector 在 `2.9 ms` 内回到 `released = True` / 0 残留，
  不污染其它测试（`_disposable_postgres_database` 随后 `pg_terminate_backend` + `DROP DATABASE`）。

若新机制无法抓到故意制造的泄漏，本 Fix 即为 FAIL；实测可抓到。

## 20-Cycle Evidence

正常场景继续证明（`-s` 输出，20/20 cycle）：

```text
'db_baseline': {'client_sessions': 0, 'server_sessions': 0}
cycle 1..20: released_seconds 0.0023 – 0.0044（均为 1 次轮询命中），
             transient_snapshots = 0，foreign = 0，server_backends_seen = []
'db_final': {'client_sessions': 0, 'server_sessions': 0, 'idle_in_transaction': 0}
```

每 cycle 同时保留原有断言：`queue = 0`、`inflight = 0`、`workers = 2`、`dedupe = 2`
（capacity 2，bounded）、`worker_exceptions = 0`（capacity 2，bounded）、
worker tasks 全部 done 且无新增 pending `g2-event-worker-*`。

## Repeatability

见 `Verification` 章节实测记录。

## Regression

见 `Verification` 章节实测记录。

## Production Code Changed

`NO`。`git diff e0dab18..HEAD -- backend/src backend/alembic` 为空；未修改 schema、migration、
Runtime Host、OKX、G2/G3/G4/G5 语义或 `N01-B` validation。

## Files Changed

- `backend/tests/test_n01_runtime_resource_lifecycle.py`（唯一代码改动）
- `dev_log/2026-09-10-n01-val-fix-01-postgres-lifecycle-stability.md`（本文件）
- `PROJECT_STATE.md`、`AI_CONTEXT.md`（仅最小状态同步）

## Known Risks

1. **服务端维护进程仍可能出现在 `pg_stat_activity`**（本次已实测捕获 autovacuum worker）。
   新 gate 将其显式归类为 `server_sessions` 证据而不判失败。这不是容差，而是所有权边界：
   测试无法也不应控制服务端 autovacuum 的调度。
2. **deadline = 1.0 s 是基于本栈实测的工程选择**。若未来换用远慢的存储/网络（例如非本机
   PostgreSQL），观测到的关闭可见窗口可能显著变大，需要按新的实测数据重新论证 deadline。
   当前证据（≤8.3 ms）不支持更大的值。
3. **根因偶发率低**（文件级执行约 2/40），本次以 40 次执行复现 2 次并成功捕获身份。
   结论建立在**捕获到的具体身份**而非统计推断上，但该身份证据来自单次捕获（另一条
   失败未带身份 dump）。
4. `test_n01_okx_paper_safety.py` 依赖真实 OKX 网络；其可运行性受本机代理环境
   （`N01-B-E01`）影响，与本 Fix 无关。

## Final Recommendation

`READY FOR INDEPENDENT REVIEW`

## Verification

全部在 `E:\Documents\MarketPulse-AI-n01-val-fix-01`、`HEAD = e0dab18` + 本 Fix 工作树改动、
Docker `marketpulse-postgres` 上**实际执行**（`PYTHONPATH=backend/src py -3.14`）：

| Gate | 命令 | 结果 |
|---|---|---|
| Focused run 1 | `pytest backend/tests/test_n01_runtime_resource_lifecycle.py -q` | `6 passed in 8.28s` |
| Focused run 2 | 同上 | `6 passed in 7.89s` |
| Focused run 3 | 同上 | `6 passed in 7.82s` |
| Focused run 4 | 同上 | `6 passed in 8.47s` |
| Focused run 5 | 同上 | `6 passed in 8.43s` |
| N01-B focused | `pytest backend/tests/test_n01_okx_paper_safety.py -q` | `3 passed in 7.71s` |
| G2 | `pytest backend/tests/test_group2.py -q` | `30 passed in 5.02s` |
| G3 | `pytest backend/tests/test_group3.py -q` | `16 passed in 19.82s` |
| G4 | `pytest backend/tests/test_group4.py -q` | `77 passed in 83.21s` |
| Full backend 1 | `pytest backend/tests -q` | `172 passed, 1 warning in 226.68s` |
| Full backend 2 | `pytest backend/tests -q` | `172 passed, 1 warning in 221.82s` |
| Ruff | `ruff check backend/src backend/tests scripts` | `All checks passed!` |
| compileall | `compileall -q backend/src backend/tests` | exit 0 |
| diff-check | `git diff --check` | exit 0 |
| Production diff | `git diff e0dab18..HEAD -- backend/src backend/alembic` | 空 → `Production code changed = NO` |

- **Repetition Gate**：focused `5/5 PASS`；full backend `2/2 PASS`；**本次未出现 lifecycle flake**
  （旧模型同期可复现率为文件级约 2/40）。
- 172 = 既有 171 baseline + 本次新增负向对照 1。1 条 warning 为既有上游
  FastAPI/Starlette TestClient deprecation（N01-B closeout 记为 2 条，属 pytest warning
  汇总口径差异，两者均非本 Fix 引入）。
- 工作树最终改动文件（`git status --porcelain`）恰好为允许的 4 个：
  `backend/tests/test_n01_runtime_resource_lifecycle.py`、本 dev_log、`PROJECT_STATE.md`、
  `AI_CONTEXT.md`。

### 诊断原始产物（仓库外，供 Independent Review 复核）

```text
E:\Temp\marketpulse-n01-val-fix-01\lifecycle_flake_evidence.jsonl        # 捕获到的 autovacuum worker 身份
E:\Temp\marketpulse-n01-val-fix-01\repro_loop.log                        # 30 次复现循环结果
E:\Temp\marketpulse-n01-val-fix-01\diag_pg_close_report.json             # 160 cycle 关闭可见窗口
E:\Temp\marketpulse-n01-val-fix-01\diag_burst_report.json                # 12x24 / 10x80 突发关闭
E:\Temp\marketpulse-n01-val-fix-01\diag_close_paths_report.json          # graceful vs terminate
E:\Temp\marketpulse-n01-val-fix-01\diag_autovacuum_report.json           # 死元组与 autovacuum 作用证据
E:\Temp\marketpulse-n01-val-fix-01\diag_*.py / diag_plugin.py            # 诊断脚本（只读，未入库）
```

