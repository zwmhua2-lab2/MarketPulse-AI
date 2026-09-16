# PRE-01B-D2-FIX-04｜DB Semantics Proof + Minimal Contract Fix

## 1. Task / Requirement / Scope

- Task：`PRE-01B-D2-FIX-04`，`DESIGN FIX / PROOF-FIRST / DOCS ONLY`。
- Required findings only：`RR03-P1-01` timeout leakage；`RR03-P1-02` connection
  return/cancellation + token release authority；`RR03-P2-01` token/SAVEPOINT ordering。
- Allowed：
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
  与本 new dev_log。
- Forbidden / unchanged：Runtime、migration、schema、tests、configuration、project DB、service、
  provider、I2、Gate A/B/C、Real AI、Live、`main`。
- Result language：candidate only；never Human Acceptance。

## 2. Baseline / isolation evidence

```text
main = origin/main = a90c5968be4b456aabde814eb35d4757380761f7
FIX-03 branch = 4548920fddc7e4f84b0edab8a7e5d72fc35d54ff
merge-base --is-ancestor a90c5968… 4548920f… = exit 0
FIX-04 branch = design/pre-01b-d2-fix-04-db-semantics
FIX-04 worktree start = detached exact 4548920f…; clean
```

共享 root worktree 位于其他 branch 且有 pre-existing dirty delta；本任务未触碰。Phase A
先在 detached clean worktree 完成 proof，确认 feasible 后才创建 FIX-04 branch。FIX-03
candidate/branch preserved，未 amend/rebase/repoint。

## 3. Repository/source evidence

- `backend/src/marketpulse/g2/repository.py`：`PostgresG2Repository.persist()` 使用
  caller-owned `async with session, session.begin()`；G2 facts 与 formal Evidence 同 outer
  transaction；session context 拥有最终 return。
- `backend/src/marketpulse/edge/capture.py` → `edge/repository.py`：formal Evidence writer
  执行 `await session.flush()`；因此可冻结 explicit core flush boundary。
- `backend/src/marketpulse/db/session.py`：single Host-owned primary engine/session factory；
  current construction 未冻结 explicit pool capacity。
- `backend/src/marketpulse/runtime_host.py`：RuntimeHost owns shutdown/final shared-engine dispose；
  accepted step 2 是 deferred Advisory slot；cleanup failure / terminal state must remain truthful。
- complete D2 §8 / §20 / §32 / §33 reread；所有 current conflicting wording 已同步修正，
  FIX-04 final normative disposition 在 §34。

## 4. Official semantics evidence

- PostgreSQL 16 `SET`：`SET LOCAL` 到 outer transaction end；rollback 到更早 SAVEPOINT
  会撤销，RELEASE 不撤销：<https://www.postgresql.org/docs/16/sql-set.html>。
- SAVEPOINT / rollback / release：
  <https://www.postgresql.org/docs/16/sql-savepoint.html>、
  <https://www.postgresql.org/docs/16/sql-rollback-to.html>、
  <https://www.postgresql.org/docs/16/sql-release-savepoint.html>。
- timeout：`idle_in_transaction_session_timeout` 会终止 idle open-transaction session；
  `lock_timeout` 仅在 lock wait 生效：
  <https://www.postgresql.org/docs/16/runtime-config-client.html>。
- SQLAlchemy 2.0：`begin_nested()` 在 SAVEPOINT 前 unconditional flush；Session close/
  invalidate 与 PoolEvents semantics：
  <https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#using-savepoint>、
  <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#flushing>、
  <https://docs.sqlalchemy.org/en/20/orm/session_api.html>、
  <https://docs.sqlalchemy.org/en/20/core/events.html>。
- Installed source recheck：SQLAlchemy 2.0.52 `SessionTransaction._take_snapshot()` calls
  `session.flush()` for nested boundary；`Connection.invalidate()` discards connection even when
  underlying DBAPI close error is only logged；PoolEvents `invalidate`/`close` occur before close
  attempt，`checkin` is return-to-pool event。

## 5. Disposable PostgreSQL proof

Environment：isolated `postgres:16-alpine` container，PostgreSQL 16.15，host port `55441`，
database/user `proof`；SQLAlchemy 2.0.52 + asyncpg 0.31.0。No project volume；never connected
to `marketpulse-postgres` / project DB。

External evidence（not repository content）：

```text
E:/Documents/pre-01b-d2-fix-04-evidence/db_semantics_probe.py
E:/Documents/pre-01b-d2-fix-04-evidence/db_semantics_probe-output.json
E:/Documents/pre-01b-d2-fix-04-evidence/db_semantics_probe-stderr.txt
```

Final run：`exit 0`，`stderr_chars=0`，`duration_seconds=2.356`，final pool
`checkedout=0`。

| Required case | Observed evidence | Decision |
|---|---|---|
| Normal completion | restored timeout values；normal `checkin`；pool `1 -> 0` | confirmed checkin may release once |
| SQL error | division-by-zero rollback；outer `SELECT 42` | outer valid after confirmed rollback |
| SAVEPOINT rollback | statement/lock values restored；restore-error case outer `SELECT 431` | rollback cancels SAVEPOINT-local SET |
| SAVEPOINT release | without restore values remain `1111ms/222ms/3333ms` | release does not restore；explicit restore required |
| Outer delay | former 100ms statement timeout restored；`pg_sleep(0.25)` succeeds in 0.254s | no post-Advisory leakage |
| Cancellation | client cancel emits invalidate/close/`checkin(None)`；outer becomes `PendingRollbackError` | client cancel forbidden on caller-owned G2 |
| Return/close failure | close failure leaves checkout=1/no terminal event；explicit connection invalidate later yields invalidate/close/`checkin(None)` and checkout=0；invalidation-failure injection leaves checkout=1/no terminal event | close-start/finally not release；unknown retires token |
| Shutdown with G2 active | `C=3,A=1,R=2`；new Advisory acquisition rejected；G2 + two Protection backends coexist；G2 outer `SELECT 49` works | no ownership seizure；Protection uses R；token through disposition |

Additional proof：statement timeout and lock timeout each raised the expected PostgreSQL error inside
SAVEPOINT，rollback restored settings and outer remained usable；SQL trace proves core INSERT index 0，
SAVEPOINT index 1。

## 6. Frozen timeout contract

- Caller-owned：only captured/restored transaction-local `statement_timeout` + `lock_timeout`；
  restore + verify before release；restore failure ⇒ rollback SAVEPOINT。
- Caller-owned `advisory_db_transaction_timeout` = cooperative pre-statement budget only；running SQL
  is bounded by server statement/lock timeout。
- Caller-owned forbidden：`idle_in_transaction_session_timeout`、client task cancellation、
  solely-for-Advisory invalidation。
- Independently fence-owned Advisory session may use statement/lock/idle、owned client cancellation、
  bounded rollback/close/invalidation，因为它 owns whole transaction/session。
- Connection-level termination cannot be repaired by post-hoc restore and is never reported as
  preserved outer G2 truth。

## 7. Frozen release contract

- Exact owner：G2/core owner starts caller-owned cleanup；Host-owned lease registry correlates exact
  pool entry + checkout generation and owns token disposition；writer never releases。
- Positive authority：exact `PoolEvents.checkin`；or awaited explicit invalidate returned + exact
  invalidation/`checkin(None)`。
- `invalidate`/`close` event alone、`finally`、close-start、SAVEPOINT/outer completion are not release。
- Unknown/cancelled/failed cleanup ⇒ `RETURN_UNCERTAIN_RETIRED`；available capacity unchanged；
  Gate A fail closed；shutdown not clean；late exact terminal event is idempotent；no double release。
- Protection reserve：pending/uncertain stays inside A attribution；never borrows R；this is primary
  pool checkout attribution，not a global PostgreSQL availability promise。
- Process death：no in-process release；new epoch only after singleton + fresh pool capacity validation；
  old uncertainty remains historical evidence。No impossible “eventual cleanup must succeed” guarantee。

## 8. Frozen ordering

```text
G2/Evidence core writes
-> explicit core flush
-> immediate token try
-> begin_nested/SAVEPOINT
-> capture/apply timeouts + Advisory work
-> restore + release OR rollback
-> outer result
-> connection authoritative disposition
-> confirmed token release OR uncertain retire
```

Token failure = zero Advisory SQL + zero SAVEPOINT。`begin_nested()` 不能包住 token try，因为
SQLAlchemy 已在进入 SAVEPOINT 前 unconditional flush。

## 9. Changes

- Modified：
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`。
- Added：本 dev_log。
- No other path authorized or changed。

## 10. Cross-contract non-regression

- RR01 P1-01：Advisory writes remain SAVEPOINT-isolated；only connection-valid + confirmed rollback
  claims outer preservation；core flush remains core failure boundary。
- RR01 P1-02/P1-03/P1-04/P2-01：Evidence lock order、Invocation final authority、original
  PostgreSQL deadline、no durable `QUEUED` unchanged。
- RR01 P1-05 / RR02 P1-01：`H_o + H_g + U <= A` conservative accounting；uncertain does
  not create false headroom；`A + R <= C` / caller zero-wait preserved。
- RR02 P1-02：DISABLED remains frozen literal/no fence/writer/SAVEPOINT；Pack-B may be unset。
- PRE-01A-D1/PRE-01B-D1：AI advisory、one RuntimeHost/primary engine、provider/DB separation、
  Protection ownership、final shared-engine disposal unchanged。

## 11. Verification / candidate status

Required final checks：refs/ancestry、changed paths、diff、`git diff --check`、cross-section grep、
working-tree cleanliness after commit、remote branch push。Static assertions alone are not proof；
DB-dependent claims above come from the disposable PostgreSQL run。

```text
PRE-01B-D2-FIX-04 = FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW
HUMAN ACCEPTANCE = NOT PERFORMED
I2 IMPLEMENTATION = NOT AUTHORIZED
PRODUCTION / PROJECT DB / SERVICE / PROVIDER / GATE / REAL AI / LIVE = UNCHANGED
```
