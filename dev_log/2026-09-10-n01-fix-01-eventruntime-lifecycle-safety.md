# N01-FIX-01 — G2 EventRuntime Lifecycle Safety

## Task / Requirement

修复 N01 Preflight 确认的 G2 `EventRuntime` 长期运行生命周期问题：R01 成功 Event
dedupe retention 无界、R02 worker exception retention 无界、R03 publisher cancellation 与
`_inflight` ownership 不安全。保持既有 G2 / FG-D 业务与确定性契约。

## Repository Truth / Workspace Isolation

- Task Base / verified GitHub `main` / `origin/main`：
  `d47313a1cb41996410606fe92b286a5046ed4fce`。
- Implementation branch：`fix/n01-eventruntime-lifecycle-safety`。
- Isolated clean worktree：`E:\Documents\MarketPulse-AI-n01-fix-01`。
- 原 worktree：`E:\Documents\MarketPulse AI`，branch
  `prb-01-product-requirements-baseline`，保留其全部未提交修改；本任务未修改、提交、清理或
  移动其中任何文件。
- `origin`：`https://github.com/zwmhua2-lab2/MarketPulse-AI.git`。

## Scope / Out of Scope

- Production：`backend/src/marketpulse/g2/runtime.py`；为真实 PostgreSQL durable duplicate
  race 的最小原子性修复，修改 `backend/src/marketpulse/g2/repository.py`。
- Tests：`backend/tests/test_group2.py`。
- 未修改 schema、migration、Runtime Host / FastAPI lifespan、scheduler、Scanner / Strategy
  规则、G3–G5、Live、Provider 或外部交易行为。

## Source-Proven Root Cause

- R01：`EventRuntime._dedupe` 为无限 `set[str]`，仅持续添加成功 Event ID。
- R02：`worker_exceptions` 为无限 `list[BaseException]`，每个 worker failure 持续 append。
- R03：publisher 在 `queue.put()` 前注册 `_inflight`，若被取消则无 cleanup；入队后直接 await
  shared Future，使 caller cancellation 可取消 worker / duplicate coalescing 所拥有的 Future。
- PostgreSQL：`session.get(event_id)` 后再 insert，两个独立 transaction 可跨过该 pre-check 并在
  commit 时发生唯一约束竞争。

## Implementation / Business Behavior

- `EventRuntime` 新增有限且 fail-fast 的 `dedupe_capacity`（默认 8192）与
  `worker_exception_capacity`（默认 128）。成功 Event ID 以 FIFO 保存，重复命中不刷新位置；
  `worker_exceptions` 为最近诊断 evidence 的 bounded deque。
- 入队前 cancellation 按 Future identity 删除 `_inflight` 并取消未被 Runtime 接受的 shared
  Future；入队成功后 publisher 以 `asyncio.shield()` 等待 Runtime-owned Future。worker completion
  仅完成未完成 Future，并按 identity 清理 `_inflight`。
- PostgreSQL 以 `INSERT ... ON CONFLICT DO NOTHING RETURNING` 作为同一业务 transaction 的首个
  写入门；duplicate no-op 在 timeline/state/transition/candidate/observation 排队前返回。
- `ScannerPipeline._trade_dedupe` 的独立 FIFO 8192 语义未改。

## Acceptance Cases / Evidence

- AC-01：配置 capacity=2，三个成功 Event 后 retained Event IDs 仅为 FIFO 最近两项。
- AC-02：既有 G2 reconnect duplicate regression 保持通过，memory-window duplicate 不持久化。
- AC-03：被 eviction 的 Event A 再到达由 durable repository 返回 `persisted=False`；完整
  InMemory business truth 与 state 均不变。
- AC-04：一次 disposable PostgreSQL database 中两个独立 Runtime / Repository 通过
  `asyncio.Barrier(2)` 同步竞争同一 Event ID；结果为一 writer、一 no-op、无 worker exception，
  后续各自独立 Event 均持久化，六类 G2 business facts 无重复。
- AC-05：五次 injected persist failure 下 capacity=2 仅保留第 4/5 个异常；publisher 仍接收原始
  exception，后续 valid Event 成功。
- AC-06：worker 被 Event gate 阻塞且 bounded queue 满时，tracked queue 确认取消 publisher 已到达
  `queue.put()` 边界；caller 收到 cancellation、无 orphan `_inflight`、无 phantom queued Event，
  retry 成功。
- AC-07：入队后 worker persist gate 阻塞时取消原 caller；测试在 duplicate waiter 进入 shared
  `shield()` 后才 release worker。worker 完成一次，duplicate 得到 valid outcome，无
  `InvalidStateError` / worker exception。
- AC-08：上述 cancellation/failure tests 完成后均断言 `_inflight` empty、queue drain 和 worker
  clean stop。
- AC-09：`backend/tests/test_group2.py` 定向结果见 Verification。
- AC-10：full backend suite、全量 Ruff、compileall 与 `git diff --check` 全部通过，结果见
  Verification。

## Self Review

- FIFO bounds、failure retention、Future cancellation ownership、identity-safe cleanup 和
  PostgreSQL conflict-first atomicity均已源代码与定向测试复核。
- 未将 EventRuntime dedupe 与 ScannerPipeline trade dedupe 合并。
- 仍须独立 reviewer 复核；本记录不构成 Human Acceptance。

## Result / Remaining / Known Risks

当前状态：`IMPLEMENTED / AWAITING REVIEW`。

- 已解除 N01 Pre-Soak 的 EventRuntime lifecycle blocker，前提是 full regression 和独立评审
  通过。
- N01 后续 Soak / Gate 不在本任务 Scope，必须按其单独批准的验收门重新执行。
- 无已知 production blocker；仍需独立 reviewer 与 Human Acceptance。

## Verification

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q` → `30 passed in 7.89s`。
- `py -3.14 -m ruff check backend/src/marketpulse/g2 backend/tests/test_group2.py` → PASS。
- `py -3.14 -m compileall -q backend/src backend/tests` → PASS。
- `git diff --check` → PASS（Windows LF→CRLF advisory only，exit 0）。
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` → `163 passed, 1 warning in
  207.33s`；stderr empty。唯一 warning 为既有 Starlette TestClient/httpx deprecation。
- `py -3.14 -m ruff check backend/src backend/tests scripts` → PASS。
- `py -3.14 -m compileall -q backend/src backend/tests` → PASS。
- `git diff --check` → PASS（Windows LF→CRLF advisory only，exit 0）。
- 完整 pytest stdout/stderr 保留于仓库外
  `E:\Temp\marketpulse-n01-fix-01\backend-tests-full-20260910-142304.*.txt`。
