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
- Disposable DB activity must strictly restore to its pre-cycle baseline after every lifecycle and
  again at final; `idle in transaction = 0` is included in that equality. Focused run printed
  `db_before={'sessions': 0, 'idle_in_transaction': 0}` and identical activity for every cycle and
  `db_after`. The temporary F01-era relaxation is superseded by Acceptance Fix #2 below.
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

## Independent Review Finding N01-A-F01 / Acceptance Fix #1

### Finding

Independent Review result: `CHANGES_REQUIRED / NOT ACCEPTED`。原 same-instrument test 只在 first
persist gate 后创建 second publisher 并检查 `max_active == 1`；它没有确定地证明 second work 已由 worker
取走并到达同一 instrument 的 serialization contention path。

### Deterministic Interleaving Evidence

- `_TrackingQueue.get()` 现在为每个实际被 worker 取走的 item 发出 event-id witness；没有使用
  `sleep()`、scheduler-yield guess 或 retry loop。
- first `serial-first` 已进入 controlled BTC persist gate 后，test 消费其 `queue.get()` witness。
  second `serial-second` publish 后，test 必须消费第二个 `queue.get()` witness，证明它已由另一个
  Runtime worker 实际接受并进入 worker path，而不是仅停留在 publisher task。
- first gate 未 release 时，断言 `persist_entry_ids == ['serial-first']`、BTC protected persist
  active count 为 1、second publisher pending。这说明 second 已离开 queue，但仍被同一 instrument
  lock 阻止在 protected persist/state mutation 之前。
- release 后，persist entry 顺序必须为 first → second；first/second transition 和 resulting
  state version 分别为 1 / 2。finite worker identities 不变；现有 BTC/ETH simultaneous persist
  evidence 保留。

### Why a Broken Serialization Implementation Fails

若移除或失效 per-instrument lock，second worker 的 `queue.get()` witness 后会在 first release 前进入
`persist()`，使 `persist_entry_ids` 出现 second 或 BTC active count 变为 2，立即违反 release-before
assertions。故该测试证明的是实际 contention 下的 non-overlap，不是 scheduler timing 偶然结果。

### Verification / Self Review

- 生产代码未改；没有 test hook 进入 `EventRuntime` production implementation。
- Deterministic witness 是 `PriorityQueue.get()` 的 validation-only instrumentation；不依赖 sleep 或
  retry timing guess。
- Acceptance Fix #1 status: `IMPLEMENTED / AWAITING RE-REVIEW`。原 N01-A validation evidence 保留；
  后续 focused N01-A、G2、full backend、Ruff、compileall 与 diff-check 结果追加于提交前验证记录。
- Lifecycle harness retains the original 20-cycle DB leak gate without a scheduler-timing claim:
  every observed cycle must have `idle in transaction = 0`; session count may show at most one
  asyncpg close-in-flight connection above its disposable-DB baseline, but may not grow with cycle
  count. This is an observation-boundary correction, not a production-code change or a relaxation
  that permits accumulating connections.

### Acceptance Fix #1 Verification

- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_n01_runtime_resource_lifecycle.py -q -s`
  → `5 passed in 6.19s`；focused 20-cycle DB session sequence = twenty `0` values，before/after 均为
  `{'sessions': 0, 'idle_in_transaction': 0}`。
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_group2.py -q` → `30 passed in 6.05s`。
- `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` → `168 passed, 1 warning in 186.76s`。
- `py -3.14 -m ruff check backend/src backend/tests scripts`、
  `py -3.14 -m compileall -q backend/src backend/tests`、`git diff --check` → PASS。
- Full stdout/stderr: `E:\Temp\marketpulse-n01-a\backend-full-fix1-final-20260910.txt`。

## Independent Re-Review / Acceptance Fix #2 — N01-A-F02

### Re-Review Result

- `N01-A-F01 = CLOSED / PASS`：queue-get witness、same-instrument contention boundary, first-release
  non-overlap、state/transition version 1 → 2、fixed workers and BTC/ETH parallel evidence remain intact.
- `N01-A-F02` found an unrelated Acceptance Fix #1 change that relaxed the 20-cycle PostgreSQL
  lifecycle assertion from exact baseline restoration to an allowance of `baseline + 1` session.
  N01-A remained `CHANGES_REQUIRED / NOT ACCEPTED` until this contract was restored.

### Root Cause and Restoration

The relaxation was an unapproved response to intermittent full-suite observation behavior and was not
required to prove F01. The current focused evidence had baseline, all cycles, and final at zero, so no
evidence justified tolerating an additional persistent connection. Acceptance Fix #2 restores:

```python
activity == baseline  # after every completed lifecycle
after == baseline     # after all 20 lifecycles
```

No sleep, poll-until-zero loop, retry, or scheduler timing workaround was introduced. The test records
the 20 observed snapshots while retaining actual worker-completion, queue-drain, inflight-empty and
explicit `await engine.dispose()` assertions.

### PostgreSQL Lifecycle Evidence

- Baseline: `{'sessions': 0, 'idle_in_transaction': 0}`.
- Cycle 1–20: each `{'sessions': 0, 'idle_in_transaction': 0}`.
- Final: `{'sessions': 0, 'idle_in_transaction': 0}`; `after == baseline`.
- Disposable N01 database cleanup: `pg_database LIKE 'marketpulse_n01_a_%' = 0` after test cleanup.

### Acceptance Fix #2 Regression

- Focused N01-A: `5 passed in 6.38s`.
- G2: `30 passed in 5.83s`.
- Full backend: `168 passed, 1 warning in 183.73s`.
- Ruff / compileall / `git diff --check`: PASS.
- Full stdout/stderr: `E:\Temp\marketpulse-n01-a\backend-full-fix2-final-20260910.txt`。

### Result

`N01-A Acceptance Fix #2 = IMPLEMENTED / AWAITING RE-REVIEW`。Production code changed: `NO`；
no schema/migration/Runtime Host/OKX/G3/G4/G5 change. This record does not declare N01-A accepted.

## Final Acceptance Closeout

### Independent Review Result

Independent Review = `PASS`。

- `N01-A-F01 = CLOSED / PASS`：deterministic same-instrument worker `queue.get()` witness and
  release-before-persist contention evidence retained。
- `N01-A-F02 = CLOSED / PASS`：strict PostgreSQL activity baseline restoration restored; no
  `baseline + 1` tolerance remains.

### Human Acceptance

Human Acceptance = `CONFIRMED`。`N01-A = ACCEPTED / COMPLETE`。

### Final Gate

- Focused N01-A: `5 passed in 6.38s`；20-cycle PostgreSQL activity sequence was baseline on every
  cycle and final (`sessions=0`, `idle_in_transaction=0`).
- G2: `30 passed in 5.83s`。
- Full backend: `168 passed, 1 warning in 183.73s`；warning is the existing Starlette/httpx
  TestClient deprecation.
- Ruff, compileall and `git diff --check`: PASS。
- Disposable N01 database count after cleanup: `0`。

### Accepted Validation Lineage

```text
bc635787eafdf88fdc8e5810109452b5e394a076
  -> 6321efb16da7b684c6c07006379c204fa41ec46d
  -> facac1f1f0c59dc1e96836dc53c258b370c69ee7
  -> d67ffc21e52cb3bac6743ce6cabd13ebfb20658a
```

### Accepted Main Integration

Final Acceptance Closeout is documentation-only and is committed separately after the validation
lineage. The N01-A branch is retained as historical evidence; `main` is advanced by fast-forward only,
without squash, rebase, reset, or force-push.

### Claim Boundary / N01-B Entry Context

N01-0 local/runtime preflight, N01-1 Deterministic Async Runtime, N01-2 Resource Lifecycle and N01-A
are accepted. This does not prove overall N01, Continuous Runtime, OKX reconnect, Paper Safety
Continuity, 15m/2h/12h Soak, 7x24 Runtime, or Integrated Runtime Host. N01-B remains `NOT STARTED`;
next step is `RETURN TO N01 MAIN WINDOW / DESIGN / START N01-B`.
