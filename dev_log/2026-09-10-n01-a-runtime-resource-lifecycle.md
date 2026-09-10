# N01-A — Deterministic Runtime + Resource Lifecycle

## Result

`VALIDATED / AWAITING REVIEW`。本记录只说明 validation implementation 与真实验证已完成；
不构成 Independent Review 或 Human Acceptance，未推进 `main`。

## Repository Truth / Workspace Isolation

- Verified Accepted Main / Task Base: `origin/main = bc635787eafdf88fdc8e5810109452b5e394a076`。
- Branch: `n01-a-runtime-resource-lifecycle`。
- Isolated clean worktree: `E:\Documents\MarketPulse-AI-n01-a`。
- 原 `prb-01-product-requirements-baseline` 脏工作树未修改、未 reset/stash/clean。

## Scope

- Allowed and changed: `backend/tests/test_n01_runtime_resource_lifecycle.py`、本 dev_log、
  `PROJECT_STATE.md`、`AI_CONTEXT.md` 的最小当前态索引。
- Validation-only: no `backend/src` change; no schema/migration, Runtime Host, provider/OKX,
  business/state-machine semantics, real reconnect gate, or 15m/2h/12h Soak.
- `DECISIONS.md` 未修改：本任务没有产品或架构决策变化。

## N01-0 Preflight

- Python `3.14.2` 与 SQLAlchemy/asyncpg/Alembic 依赖可用。
- `marketpulse-postgres` healthy；Alembic `current == heads == 20260905_0004`。
- Primary database baseline: one probe `active` session, `idle in transaction = 0`；结束时同为
  one probe `active` / `idle in transaction = 0`。
- R01 bounded FIFO EventRuntime dedupe、R02 bounded worker diagnostics、R03 publisher
  cancellation/inflight ownership、PostgreSQL conflict-first durable duplicate TOCTOU 均由当前
  accepted source、现有 G2 regression 与 N01-A repeated tests 复核。

## N01-1 Deterministic Runtime Evidence

- Bounded queue/backpressure: capacity 1 + controlled repository gate；第三 producer 到达
  `queue.put()` boundary 时保持 blocked，release 后三事件全部 persisted，queue drains to 0。
- Finite workers: `worker_count=2`，worker task identity remains fixed under queued load；没有
  per-event spawning。
- Serialization/concurrency: same `BTC-USDT` persist overlap maximum为 1；`BTC-USDT` 与
  `ETH-USDT` 同时进入 controlled persist，证明没有全局锁串行化。
- Duplicate/retry/cancellation: recent duplicate no-op；FIFO-evicted duplicate reaches durable
  repository and remains no-op；injected repository failure retry succeeds；cancelled publisher
  leaves Runtime-owned shared work to duplicate waiter，且该 shared work 的 injected failure 会准确
  交给 duplicate waiter，随后 retry succeeds；最终 `_inflight == {}`。

## N01-2 Resource Lifecycle Evidence

- 20 个完整 disposable PostgreSQL lifecycle：create engine/runtime → start → controlled BTC/ETH
  workload → queue join → runtime stop → `await engine.dispose()`。
- 每 cycle: worker tasks all done; no pending `g2-event-worker-*`; queue 0; inflight 0;
  dedupe 2/2; worker exceptions 0/2。
- Disposable DB session before/after remains equal and `idle in transaction = 0`。Focused run
  printed `db_before={'sessions': 0, 'idle_in_transaction': 0}` and identical `db_after`；full-suite
  assertion intentionally compares per-disposable baseline to after, because Alembic setup may own
  a pre-cycle baseline connection, while any harness-caused accumulation is forbidden.
- No temporary N01 DB remains after the run (`pg_database LIKE 'marketpulse_n01_a_%' = 0`)。
- Fixed universe retention: EventRuntime dedupe FIFO capacity 3; worker diagnostics deque maxlen 2;
  lock keys and state records exactly BTC/ETH; rolling trade deque `120` each; SignalLifecycle active
  map bounded by fixed universe × 11 finite EventTypes (=22). No meaningful-event map is exercised
  by this gate. RSS is observational only; no approved threshold exists, so no leak claim is made.

## Verification

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_n01_runtime_resource_lifecycle.py -q -s`
  → `5 passed in 6.65s`。
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q` → `30 passed in 5.86s`。
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` → `168 passed, 1 warning in 184.10s`。
  Warning 是既有 FastAPI/Starlette TestClient/httpx deprecation。
- `py -3.14 -m ruff check backend/src backend/tests scripts` → PASS。
- `py -3.14 -m compileall -q backend/src backend/tests` → PASS。
- `git diff --check` → PASS；`git diff -- backend/src` empty。
- 完整 final backend stdout/stderr: `E:\Temp\marketpulse-n01-a\backend-full-final2-20260910.txt`。

## Claim Boundary / Next Gate

- Production code changed: `NO`。
- N01-A is not a Continuous Runtime, real OKX reconnect, 15m/2h/12h Soak, 7x24, or Trading Edge proof.
- Recommendation: `READY FOR INDEPENDENT REVIEW`。N01-B 只能在 N01-A independent review / human
  acceptance 后执行。
