# PRE-01B-D2-FIX-05｜Connection Return Completion Authority Fix

## 1. Task / Requirement / Scope

- Task：`PRE-01B-D2-FIX-05`，`PROOF-FIRST DESIGN FIX / DOCS ONLY`。
- Required finding only：`PRE01B-D2-RR04-P1-01` — `PoolEvents.checkin` callback
  observation is not completed physical pool-return/owner-lifecycle authority。
- Requirement：normal return 仅在 exact-generation pool observation + owning caller cleanup
  success 两事实齐全后 once-only release；explicit invalidation 使用更严格 full predicate；
  callback-entry alone 永不恢复 capacity。
- Allowed exactly：
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
  与本 new dev_log。
- Out of Scope / forbidden：Runtime、backend/frontend/tests、schema/migration、scripts/config/
  deployment、state docs、existing dev_logs、project DB/service/provider、I2、Gate A/B/C、Real AI、
  Live、`.workbuddy`、memory、skills、daily logs、Human Acceptance、Independent Re-Review。

## 2. Baseline / isolation evidence

```text
Protocol = v1.1.0 / ACCEPTED
Protocol SHA = 07e2df83266d4ecdea46caff5c61f000937b8913
origin/main = a90c5968be4b456aabde814eb35d4757380761f7
FIX-04 branch = d3922dd35ba83312194d124e17fa8645dead6e4d
FIX-04 parent = 4548920fddc7e4f84b0edab8a7e5d72fc35d54ff
FIX-05 branch = design/pre-01b-d2-fix-05-return-completion-authority
FIX-05 base = d3922dd35ba83312194d124e17fa8645dead6e4d
```

共享 root checkout 位于另一 branch 且含 pre-existing dirty delta；本任务未清理、reset、rebase、
checkout 或覆盖。FIX-05 使用仓库外独立 worktree。FIX-04、`main` 与既有 worktrees 未移动。

## 3. Repository/source evidence

- `PostgresG2Repository.persist()` 当前使用 caller-owned
  `async with self._session_factory() as session, session.begin()`；G2/core caller 拥有 outer
  transaction、Session/context-exit 与 final connection disposition。
- `DatabaseResources` 仍是一个 Host-owned primary engine/session factory；未冻结 pool capacity。
- `RuntimeHost` accepted shutdown step 2 仍明确为 deferred Advisory work；shared engine 最后 dispose。
- 因此 future I2 可在 G2 owner lifecycle 外层增加 application-owned observer/wrapper，在 awaited
  close/context-exit 成功返回后报告 Fact B；不需要把 G2 cleanup ownership 移交给 Advisory。

## 4. SQLAlchemy 2.0.52 source / official evidence

Installed source（Python 3.14，SQLAlchemy `2.0.52`）显示：

```text
ConnectionPoolEntry.checkin()
  -> fairy_ref = None
  -> dispatch.checkin(connection, entry)
  -> pool._return_conn(entry)
```

所以 checkin callback 在 `_return_conn()` 前执行。`PoolEvents.invalidate`/`close` 也在最终
close attempt 前；callback-entry 不能证明其后 return machinery 已成功。

Official public surfaces：

- <https://docs.sqlalchemy.org/en/20/core/events.html#connection-pool-events>
- <https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.ManagesConnection.record_info>
- <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>

`ConnectionPoolEntry.record_info` 跨同 entry invalidation/reconnect 保留；
`PoolProxiedConnection.info` / public `AsyncConnection.info` 可携带并读回 current checkout key；
`AsyncSession.connection()` 与 `AsyncSession.close()` 均是 public surface。

## 5. Standalone adverse proof

Environment：Windows / Python 3.14 / SQLAlchemy 2.0.52 / SQLite + `QueuePool`；async case 使用
aiosqlite 0.22.1。全部 evidence 位于仓库外：

```text
E:/Documents/pre-01b-d2-fix-05-evidence/pool_return_completion_probe.py
E:/Documents/pre-01b-d2-fix-05-evidence/async-owner-proof.sqlite
```

未连接 `marketpulse-postgres`、未连接/修改 project DB、未使用 project volume。

| Required case | Observed result | Frozen disposition |
|---|---|---|
| normal close | sync + async checkin callback 内 `checkedout=1`；owner close await 返回后 `checkedout=0` | checkin ⇒ `RETURN_PENDING`；matching owner-success 后 release |
| later checkin listener failure | registry 已观察 checkin；owner close 抛 injected error；`checkedout=1`；next checkout timeout | `RETURN_UNCERTAIN_RETIRED`；release count 0 |
| checkin only | state=`RETURN_PENDING` | no release |
| owner success only | state=`OWNER_COMPLETED_PENDING_POOL_CONFIRMATION` | no release |
| duplicate signals | duplicate checkin + owner-success | release count exactly 1 |
| owner-first ordering | owner pending；late matching pool fact | release exactly once |
| late generation N vs N+1 | N+1 owner pending；N callback injected | N+1 release count 0 |
| explicit invalidation | event order checkout → invalidate → `checkin(None)`；callbacks 内 `checkedout=1`；owner `Session.invalidate()` return 后 0 | full predicate only；then release once |
| invalidation/cleanup unknown | pool fact + owner failure | uncertain-retired；release count 0 |

Probe exit = 0；all assertions passed。No private method was called；installed-source inspection is
evidence only，not future implementation dependency。

## 6. Frozen correction

- normal Fact A = same epoch/pool-entry/checkout-generation/lease/cleanup-attempt checkin observation。
- normal Fact B = owning caller awaited Session close/context-exit 成功返回后的 owner signal；只有
  direct Connection 是 owning boundary 时，才使用其 awaited close/context-exit successful return。
- A/B order-independent；A-only=`RETURN_PENDING`；B-only=
  `OWNER_COMPLETED_PENDING_POOL_CONFIRMATION`；A+B=`RELEASE_CONFIRMED` once。
- explicit invalidation requires same-generation hard-invalidate observation + `checkin(None)` +
  successful owner `Session.invalidate()`/full connection-session cleanup boundary。
- owner failure/cancel/unknown/missing notice = no capacity restoration；failed-attempt fact 不得与另一
  cleanup attempt 拼接。
- Advisory registry observes only；G2/core retains cleanup/transaction/Session ownership。
- exact correlation uses public `record_info`/`info` and application-owned ids；never DBAPI address、
  Session identity、timestamp proximity or callback order。

## 7. Capacity / shutdown / restart

- `U` now includes checkin-only、owner-only、cleanup error/cancel/unknown、uncertain invalidation。
- `H_o + H_g + U <= A` and `A + R <= C` remain conservative；only
  `RELEASE_CONFIRMED` removes a holder。
- Shutdown closes new Advisory acquisition first；pending/uncertain does not release and does not wait
  indefinitely；Protection proceeds on R；late full confirmation may update telemetry but never reopen
  admission/Gate A during shutdown。
- Process death does not fabricate release or persist token；new epoch validates singleton + fresh
  pool/capacity state，old uncertainty remains historical evidence。

## 8. Non-regression / Human Decision Pack

- DISABLED remains exactly `GATE_A_DISABLED` / no ingress/provider/worker/fence/token/SAVEPOINT/
  full writer；Pack-B may remain unset。
- RR03-P1-01 Timeout Semantics = `PRESERVED CLOSED`。
- RR03-P2-01 Token/SAVEPOINT Ordering = `PRESERVED CLOSED`。
- RR01 P1-01/P1-02/P1-03/P1-04/P2-01 and RR02 P1-02 unchanged。
- RR01 P1-05 / RR02 P1-01 only receive the directly dependent conservative capacity correction。
- Pack A = `NONE`；Pack B remains numeric pool/concurrency/timeout/shutdown/queue/retry/provider config；
  Pack C remains observation/sufficiency thresholds。

## 9. Changes

- Modified：
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`。
- Added：本 dev_log。
- No other repository path authorized or changed。

## 10. Verification / result

Pre-commit verification actually executed：

| Verification | Result |
|---|---|
| exact branch base / merge-base | `HEAD = merge-base = d3922dd35ba83312194d124e17fa8645dead6e4d` |
| accepted refs | `origin/main = a90c5968be4b456aabde814eb35d4757380761f7`；FIX-04 = `d3922dd…`；parent = `4548920…` |
| staged exact-base scope | exactly 2 paths：one design doc modified + this dev_log added；zero unauthorized path |
| `git diff --cached --check` | exit 0 |
| conflict-marker scan | 0 |
| whole-artifact authority scan | no live callback-only positive authority；FIX-04 callback-only wording only remains as explicitly rejected historical evidence |
| required state/matrix/Pack coverage | present：normal two-factor、owner failure/cancel/unknown/missing、duplicate/late/generation、full invalidation、capacity、shutdown/restart、Pack A/B/C |
| external adverse probe | `py -3.14 .../pool_return_completion_probe.py` exit 0；all assertions passed；SHA256 `C2EBA188AFAFCBFC469B380B73E66DC4B846041DD0A4E41788AC0DB1BD5E1E72` |
| project tests / DB / service | intentionally not run/touched：docs-only scope；zero implementation/schema/runtime change |

Post-commit clean status、candidate SHA 与 remote branch identity 由 Completion Report 记录；commit
无法自包含其自身 SHA。Windows working-copy `git diff --check` 另显示 LF→CRLF conversion warning，
exit 0；cached diff 无 whitespace error。

```text
PRE-01B-D2-FIX-05 = FIX CANDIDATE DESIGN
RR04 P1-01 = CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW
STATUS = READY FOR INDEPENDENT RE-REVIEW
HUMAN ACCEPTANCE = NOT PERFORMED
I2 IMPLEMENTATION = NOT AUTHORIZED
PRODUCTION / TESTS / SCHEMA / MIGRATION / RUNTIME / CONFIG / PROJECT DB = ZERO CHANGE
```

## 11. Remaining / risks / context for next AI

- Independent Reviewer must independently re-read source/diff/proof and decide closure；author does not
  self-accept。
- I2 must convert the public-surface contract into production-call-chain tests，including real async
  PostgreSQL callback/owner failure and shutdown races；this design fix does not implement them。
- Any future inability to obtain exact public correlation or owner completion must `STOP / BLOCKED`；
  callback-only、private monkeypatching or heuristic correlation is forbidden。
