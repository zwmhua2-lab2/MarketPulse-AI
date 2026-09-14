# SE-02C-FIX-02｜Stable Read Snapshot

## Task

- Task Type：Implementation + Verification。
- 修复目标：Independent Re-Review 新发现 `SE02C-R5`（P1 / BLOCKING）与
  `SE02C-R6`（P3 / NON-BLOCKING）。
- 本窗口不是 Review、不是 Human Acceptance；不得 merge/push `main`，不得开始 SE-02D。

## Review Finding R5

Fix-01 的 `_load_observations()` 使用 `(available_at, observation_id)` keyset pagination，
但多个 SELECT 运行在普通 `AsyncSession` 的不同 READ COMMITTED statement snapshot。Page 1
之后并发提交且满足 `evidence_at <= available_at <= due_at` 的 observation，可能被同一次
calculation 的后续 page 吸收。endpoint、MFE/MAE、returns、`calculation_digest` 与
`outcome_record_hash` 因数据库 commit timing 而变化；两个 evaluator 还可能得到不同 hash。

## R6

旧 docstring 错称 pagination traversal order 与 endpoint total order 相同。已更正为：

- pagination traversal：`(available_at, observation_id)`，只负责完整遍历；
- endpoint total order：`(available_at, has_source_sequence, source_sequence, observation_id)`，
  由 pure calculator 在完整 observation set 上独立决定。

## Repository Truth

- Repository：`zwmhua2-lab2/MarketPulse-AI`。
- preflight `git ls-remote origin refs/heads/main`：
  `dd78a979d128dee385c7a8ddc2254a53366af714`。
- preflight `git ls-remote origin refs/heads/se-02c-fix-01-review-blockers`：
  `2f9868278ab1652c4e338ffb01337c6e736545d9`。
- 新 branch：`se-02c-fix-02-stable-read-snapshot`。
- Worktree：`E:\Documents\MarketPulse-AI-se-02c-fix-02`。
- Base / initial HEAD：`2f9868278ab1652c4e338ffb01337c6e736545d9`。
- Implementation SHA：`6b084595cde9c3e3257046b4694b134954923a4d`。
- 原 Fix-01 worktree/branch 未写入，shared checkout 的既有 dirty delta 未触碰。

## Scope

- `ForwardOutcomeService.evaluate_scope()` 的 same-scope PostgreSQL advisory transaction lock。
- deterministic SHA-256 signed-int64 lock key。
- lock 后 revision-1 existing check。
- reference + 全 path page 的同一 PostgreSQL `REPEATABLE READ READ ONLY` snapshot。
- cursor-after / cursor-before / fresh snapshot / two-evaluator + concurrent ingress PostgreSQL tests。
- R6 docstring、更改后的 settled retry regression、状态文档与本日志。

## Out of Scope

- schema / migration / ORM model；Redis、Kafka、scheduler、lock table、新 persistence architecture。
- market-data、G2、Forward formula、cost model、horizon、anchor、tradability、revision-chain 语义。
- Runtime activation、Production、Live、SE-02D、Human Acceptance、merge/push `main`。

## Frozen Snapshot Boundary

一个 calculation attempt 的 durable fact set 同时满足：

1. market-time eligibility：`evidence_at <= available_at <= due_at`；
2. transaction visibility：row 在该 attempt 的 PostgreSQL snapshot 建立时可见。

snapshot 建立后才 commit 的 row 即使 `available_at <= due_at`，当前 attempt 也不可见；row
仍合法 durable，fresh snapshot 可以看到。没有新增 commit timestamp 字段，也没有把 commit time
写入业务模型。

## Evaluator Advisory Lock

normal `evaluate_scope(scope)` 打开 coordinator session，以默认 READ COMMITTED transaction 执行：

1. `pg_advisory_xact_lock(scope_key)`；
2. lock 后查询 revision-1；
3. existing 存在则 rehydrate + return，不建立 calculation snapshot；
4. existing 不存在才计算；
5. 同一 coordinator transaction 中 append revision-1 并 commit；commit/rollback 自动释放锁。

锁覆盖 task/process/independent session；Python `asyncio.Lock` 未被用作 correctness 边界。

## Lock Key Contract

canonical UTF-8 text：

```text
se02c|{opportunity_id}|{evidence_id}|{horizon.value}
```

SHA-256 前 8 bytes 按 signed 64-bit big-endian 转换，传给
`pg_advisory_xact_lock(bigint)`。固定向量：
`se02c|opp-fixed|ev-fixed|5m -> 750685418615989498`。碰撞只增加 serialization，不改变
correctness。

## Coordinator Transaction

Coordinator 从 lock acquisition 一直保持到 outcome append/commit。等待者的 lock statement
返回后，下一条 READ COMMITTED existing SELECT 看到 winner 已提交 revision-1。异常由 transaction
rollback，advisory xact lock 自动释放。

## REPEATABLE READ Snapshot

`calculate_scope()` 在独立 session 的 transaction 中，把
`SET TRANSACTION ISOLATION LEVEL REPEATABLE READ READ ONLY` 作为第一条 SQL；随后同一 session
完成 durable reference resolution 与全部 keyset page SELECT。snapshot session 不写 outcome。

真实 PostgreSQL witness 在 Page 1 后读取：

- `SHOW transaction_isolation` = `repeatable read`；
- `SHOW transaction_read_only` = `on`；
- reference session identity = path session identity。

## Pagination Behavior

- production page size 仍为 10,000；无静态 50k cap。
- R5 tests 临时 monkeypatch page size 为 2，仅用于精确制造至少两个 page 的边界。
- production SQL 与 production `_load_observations()` 未被测试替身替代；测试只包装该 snapshot
  session 的 `scalars()`，在真实 Page-1 SELECT 返回后设置 barrier。
- 原真实 50,001 path regression 独立保留并通过。

## Concurrent Ingress Semantics

ForwardPathRecorder 不取得 outcome scope lock，允许并发写。Page 1 后通过独立 writer commit 的
合法 due-path BBO 已确认 durable，但当前 calculation 的 loaded count、endpoint、MFE/MAE、
`calculation_digest`、`outcome_record_hash` 与 insert 前 baseline 完全相同；fresh snapshot 的
loaded count 增加 1 并观察到指标/hash 变化。

## Two-Evaluator Semantics

两个独立 engine/session 的 `ForwardOutcomeService` 同时 evaluate 同一 scope：

- A 持 scope lock 并在 Page 1 后暂停；
- B 的独立 `application_name` 在 `pg_stat_activity` 实测
  `wait_event_type='Lock' AND wait_event='advisory'`；
- A snapshot 建立后，真实 `ForwardPathRecorder` commit due-at BBO；
- A 不吸收 late row，append/commit revision-1；
- B 得锁后 existing check 命中，`calculation_count == 0`；
- 两 caller 均成功且 `outcome_id` / `calculation_digest` / `outcome_record_hash` 相同；
- durable outcome rows = 1，revision = 1，无 `EdgeOutcomeConflict` / `IntegrityError` / revision 2。

## Files Changed

- `backend/src/marketpulse/edge/forward_service.py`
- `backend/tests/test_se_02c_forward_outcome_service.py`
- `PROJECT_STATE.md`
- `AI_CONTEXT.md`
- `dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md`

未修改 `DECISIONS.md`：本窗口执行用户已冻结设计，没有新增或改变产品/架构决策。

## Business Behavior

| 行为 | Before | After |
|---|---|---|
| Page 1 后 late commit，key > cursor | 后续 page 可能吸收 | 当前 attempt 不可见；fresh snapshot 可见 |
| Page 1 后 late commit，key < cursor | 偶然由 keyset cursor 排除 | 同样由 snapshot visibility 排除；fresh snapshot 可见 |
| 同 scope 两 evaluator | 可能计算不同 fact set/hash 并 conflict | DB advisory lock 序列化；B 锁后 return existing |
| settled revision-1 normal retry | 可能重算后 conflict | 锁后直接 return existing；不重算、不 revision 2 |
| causal rule / formulas / anchor / tradability | frozen | 未变 |

## PostgreSQL Identity

- container：`marketpulse-se-02c-fix-02-pg`
- image：`postgres:16-alpine`
- host/port：`127.0.0.1:5443 -> 5432`
- database/user：`marketpulse` / `postgres`
- server：`PostgreSQL 16.15 on x86_64-pc-linux-musl`
- primary `alembic_version`：`20260913_0009`
- public tables：30；`market_events` / `edge_bbo_observations` /
  `edge_forward_outcomes` 均存在。
- worktree-local gitignored `backend/.env` 只用于让 `Settings()` 指向 5443；pytest 时未导出
  `DATABASE_URL`，防止 `alembic/env.py` 覆盖 disposable child database URL。

## Verification

| Gate | Result | Evidence |
|---|---|---|
| Fix-01 baseline service | PASS | `12 passed in 172.97s` |
| R5/R6 new focused | PASS | `4 passed, 12 deselected in 9.78s` |
| SE-02C service excluding 50,001 | PASS | `15 passed, 1 deselected in 44.47s` |
| 50,001 path | PASS | `1 passed, 15 deselected in 140.46s` |
| SE-02C pure calculator | PASS | `37 passed in 0.68s`；focused 合计 53 |
| market-data tradability | PASS | `7 passed in 0.21s` |
| SE-02A/B + pure calculator + revision regressions | PASS | `201 passed in 183.67s` |
| G2 + G5-1/2/3/4 | PASS | `62 passed in 130.83s` |
| G4 / N01-7 preservation | PASS | `105 passed in 115.10s` |
| Full backend | PASS | `425 passed, 1 warning in 702.59s` |
| Ruff | PASS | `All checks passed!` |
| compileall | PASS | rc 0 |
| git diff --check | PASS | rc 0；仅 LF→CRLF warning |
| Alembic | PASS | `current = heads = 20260913_0009` |
| G5 schema head | PASS | `ReplayTradingRunner.schema_head = 20260913_0009` |

唯一 warning：既有 `StarletteDeprecationWarning`（FastAPI TestClient / httpx2），无失败。

## C-01..C-29 Matrix

| # | 判据 | 结果 | Evidence |
|---|---|---|---|
| C-01 | Repository Truth | PASS | remote `main=dd78a979…`、Fix-01=`2f986827…`；本 branch base 精确 |
| C-02 | No Schema Change | PASS | schema/model diff 空；单 head `20260913_0009` |
| C-03 | Due Determinism | PASS | due-boundary + snapshot focused/full green；`due_at=evidence_at+horizon` 未改 |
| C-04 | Pending Is Derived | PASS | 无 PENDING durable outcome；既有 regression green |
| C-05 | Stable Reference | PASS | reference 仍绑定 Capture Anchor；与 path 同 snapshot |
| C-06 | Causal End Selection | PASS | cursor-after late row 当前不可见，fresh endpoint 可见；pure total-order green |
| C-07 | End Freshness | PASS | 5s TTL regressions green；公式代码未改 |
| C-08 | MFE / MAE Formula | PASS | frozen fixture + cursor tests + 50,001 full-path green |
| C-09 | Reference Return Formula | PASS | frozen formula fixture green |
| C-10 | Executable LONG Return Formula | PASS | `103/101 - 1` fixture green |
| C-11 | Cost-Adjusted Formula | PASS | exact multiplicative model regression green |
| C-12 | COMPLETE Classification | PASS | terminal matrix/formula/full-path green |
| C-13 | INSUFFICIENT_DATA Classification | PASS | anchor-only reason `ENDPOINT_MISSING`，end/metrics NULL |
| C-14 | INVALID Classification | PASS | missing-anchor fail-closed regression green |
| C-15 | Four Horizons Independent | PASS | four-horizon restart regression green |
| C-16 | Cross-Evidence Independent | PASS | cross-evidence 8-scope regression green |
| C-17 | Forward Path Capture | PASS | recorder window/idempotency/replay separation green |
| C-18 | Restart Determinism | PASS | fresh engine rediscovery/restart regression green |
| C-19 | Concurrent Exactly-One | PASS | B advisory wait；A/B same id/digest/hash；1 durable row |
| C-20 | Retry Idempotency | PASS | lock-after existing returns durable twin |
| C-21 | No Automatic Revision 2 | PASS | settled retry returns existing；all durable revisions = 1 |
| C-22 | Late/Future Rejected | PASS | due cutoff preserved；snapshot-late current attempt excluded |
| C-23 | Replay / Forward Separation | PASS | pure digest/provenance regression + G5 green |
| C-24 | Provenance Inheritance | PASS | durable source type/identity regression green |
| C-25 | FIX-01 Regression | PASS | >50k、tradability、anchor-only 全 green |
| C-26 | FIX-02 Regression | PASS | scoped supersedes persistence regressions green |
| C-27 | SE-02A/B Regression | PASS | included in 201-pass suite |
| C-28 | Full Backend | PASS | `425 passed, 1 warning` |
| C-29 | Scope | PASS | 1 production file + tests + 3 required docs；无 forbidden file |

## F02-01..F02-24 Matrix

| # | 判据 | 结果 | Evidence |
|---|---|---|---|
| F02-01 | Repository Truth correct | PASS | remote refs preflight exact |
| F02-02 | Base = Fix-01 candidate | PASS | initial HEAD `2f986827…` |
| F02-03 | No schema/migration change | PASS | diff 空；head `20260913_0009` |
| F02-04 | Deterministic advisory key | PASS | SHA-256/signed-int64 fixed vector |
| F02-05 | Lock across independent sessions | PASS | B `pg_stat_activity.wait_event=advisory` |
| F02-06 | Existing checked after lock | PASS | B waits then `calculation_count=0` and returns A row |
| F02-07 | Reference + pages one RR snapshot | PASS | same session；RR + read-only SHOW evidence |
| F02-08 | Cursor-after late commit excluded | PASS | count/endpoint/MFE/MAE/digest/hash = baseline |
| F02-09 | Cursor-before late commit excluded | PASS | count/endpoint/MFE/MAE/digest/hash = baseline |
| F02-10 | Fresh snapshot sees late rows | PASS | fresh count +1，MFE/digest/hash changed |
| F02-11 | Two evaluators + ingress same outcome | PASS | both callers succeed, same id/digest/hash |
| F02-12 | No normal-race conflict | PASS | no `EdgeOutcomeConflict` / surfaced `IntegrityError` |
| F02-13 | Exactly one revision-1 row | PASS | durable count 1，revision 1 |
| F02-14 | No automatic revision 2 | PASS | B return existing；settled retry return existing |
| F02-15 | 50,001 path | PASS | true endpoint, full MFE/MAE |
| F02-16 | Tradability | PASS | True/False/None regression green |
| F02-17 | Anchor-only | PASS | `ENDPOINT_MISSING` + NULL end/metrics |
| F02-18 | Formula/due/freshness/causal | PASS | calculator + service regressions green |
| F02-19 | Restart/retry/horizons/cross/replay | PASS | focused + G5 green |
| F02-20 | SE-02A/B + FIX-01/02 | PASS | 201-pass suite + focused |
| F02-21 | N01-7 preservation | PASS | G4 `105 passed` |
| F02-22 | Full backend | PASS | `425 passed, 1 warning` |
| F02-23 | Ruff/compileall/diff-check | PASS | all rc 0 |
| F02-24 | R6 docstring | PASS | traversal/endpoint orders explicitly separated |

## Self-Check

1. Coordinator 与 snapshot 是两个独立 transaction；snapshot 只读，Outcome 只在 coordinator
   写入，且 coordinator lock 覆盖计算与 commit。
2. B 的 coordinator 在 lock statement 等待期间已进入 transaction，但默认 READ COMMITTED
   下一 statement 取得新 snapshot，因此 lock 后 existing SELECT 看见 A commit；真实测试证明 B
   没有调用 calculator。
3. `calculate_scope()` 仍是可独立调用的 read-only capability；normal exactly-one 行为只由
   `evaluate_scope()` 协调。
4. public `append_outcome()` 旧的 conflict reconciliation 未删除；normal path 已不依赖它，避免
   扩大 API/兼容性 Scope。
5. advisory SHA-256 理论碰撞只让不同 scope 串行，不会共享 durable scope identity 或破坏正确性。
6. tests 的 page-size monkeypatch 不替代 production 10,000 与真实 50,001 regression。

## Result

```text
SE-02C-FIX-02 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW
SE-02C = IMPLEMENTED / FIXED / NOT ACCEPTED
SE-02D = NOT STARTED
```

## Remaining

- Independent Re-Review。
- Human Acceptance（本窗口不签发）。
- 未 merge/push `main`；未启动 SE-02D 或 Runtime。

## Known Risks

- PostgreSQL advisory lock key 存在密码学上极低概率碰撞；后果仅为额外 serialization。
- worktree-local gitignored `backend/.env` 会把该 worktree 的 tests 指向 5443；不得在 pytest
  进程导出 `DATABASE_URL`，否则 Alembic disposable child migration 会被重定向到 primary。
- 任务容器保留供 independent reviewer 复现；本窗口未清理。
- full backend 唯一既有 deprecation warning 未在本 Scope 修复。

## Context For Re-Reviewer

- Reviewer 不得采信本日志 PASS 自述，应独立读 source/diff/tests/runtime DB evidence。
- 重点 adverse cases：snapshot SET 是否确为 first SQL；reference/path 是否同 session；B 是否先锁后
  existing；coordinator 是否持锁到 commit；cursor-before 是否只是 cursor 偶然排除。
- cursor-before 的 fresh equivalent scope 看到相同语义 late commit 并改变 MFE/digest/hash，证明
  current exclusion 的可见性规则来自稳定 snapshot，而不是数据无效。
- Fix-01 candidate `2f986827…` 应保持 immutable；Fix-02 只在本新 branch。

## Evidence

- source：`backend/src/marketpulse/edge/forward_service.py`
- PostgreSQL tests：`backend/tests/test_se_02c_forward_outcome_service.py`
- schema evidence：`alembic current/heads = 20260913_0009`；schema/model diff empty。
- full regression：`425 passed, 1 warning in 702.59s`。
- Implementation commit：`6b084595cde9c3e3257046b4694b134954923a4d`。
- Final branch tip / push / remote read-back 在 docs/state commit 后由最终报告记录，避免在同一
  commit 内自引用尚不存在的 SHA。
