# 2026-09-16 PRE-01B-D2-FIX-02 — G2 Truth / Protection DB Fence

## Task / Result

- Task ID: `PRE-01B-D2-FIX-02`
- Type: `FORMAL DESIGN FIX / LATEST-MAIN RECONCILIATION / DOCS ONLY`
- Result: `FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW`
- Human Acceptance: `NOT PERFORMED`
- Implementation / Migration / Runtime Change / Activation: `NO`

## Requirement / Scope

从 immutable failed candidate `adb1364218d29faba55626c68b9c1a07cc7f2cee`
carry forward D2 artifact，只关闭 RR01：

- `PRE01B-D2-RR01-P1-01` — Advisory-only seed/accounting failure may abort valid G2 truth；
- `PRE01B-D2-RR01-P1-05` — shutdown time budget lacks mechanical Advisory-vs-Protection DB fence；
- refresh non-blocking `P3-01` SE-02D current status。

Preserved closed findings：P1-02 / P1-03 / P1-04 / P2-01。

Allowed paths only：

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-16-pre-01b-d2-fix-02-g2-truth-protection-db-fence.md`

## Baseline / Repository Truth

| Check | Result |
|---|---|
| Global Protocol live `main` | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| tag `protocol-v1.1.0` | same SHA |
| `AI_BOOTSTRAP.md` | `Version 1.1.0 / Status ACCEPTED` |
| `origin/main` after fetch | `a90c5968be4b456aabde814eb35d4757380761f7` |
| failed candidate | `adb1364218d29faba55626c68b9c1a07cc7f2cee` |
| failed candidate parent | `c0bd0e8145a82372a6322f63369e6467cae9022f` |
| FIX-02 branch/base | `design/pre-01b-d2-fix-02-latest-main` / exact `a90c5968…` |

Root checkout had unrelated dirty state before this task. Work was performed in isolated
`E:\Documents\MarketPulse AI.pre-01b-d2-fix-02-latest-main`; no reset/stash/clean/rebase or
attribution of root-worktree content occurred.

Current accepted source facts inspected：

- `PostgresG2Repository.persist()` owns one outer `session.begin()` containing G2 facts and
  formal Evidence；current return is bool。
- `RuntimeHost._compose_services()` passes one primary session factory to G2, Execution,
  Protection, Recovery and Control。
- `create_database_resources()` owns one primary async engine but does not explicitly configure
  pool size/max overflow/pool timeout。
- Protection opens primary sessions directly and never waits for current AI queue/provider。
- current migration head in repository is `20260913_0009`；this design creates no migration。
- `adb1364… -> a90c5968…` has no material G2/G3/G4/RuntimeHost/DB/schema change；SE-02D-I03
  orchestration/status closeout is orthogonal to live Advisory ingress。

## P1-01 Corrected Contract

- New formal Evidence gets only schema-literal `UNSTAGED` outside nested SAVEPOINT；existing rows
  migrate to `LEGACY_PRE_I2`。
- Every Advisory-specific operation is inside SAVEPOINT：activation classification, PostgreSQL
  admission clock, seed construction/canonicalization/digest, config/experiment/pair/arm binding,
  Snapshot, Invocation, constraints and accounting flip。
- Advisory-only failure rolls back only the SAVEPOINT. A second SAVEPOINT may write constant
  `ADMISSION_FAILED_FINAL / ADMISSION_STAGING_FAILED_UNBOUND / NO_LONG_UNBOUND`; if it also fails,
  outer G2/Evidence commits with `UNSTAGED`。
- Restart may only retry that constant terminal write. It may not read mutable current config,
  fabricate a deadline, or create Invocation/Attempt/Decision。
- Unbound failures enter a separate durable/queryable completeness-hole count and block false
  Gate A/Gate C completeness；they are not post-hoc assigned to an experiment arm。

## P1-05 Corrected Contract

- Existing Host-owned primary engine remains sole DB authority；no second engine/DSN/pool。
- Host owns `AdvisoryDbFence`; Advisory receives no raw engine/session factory。
- `A = advisory_db_max_concurrency`, `R = protection_reserved_db_capacity`,
  `C = effective_db_capacity`; freeze `A + R <= C` with positive finite integer validation。
- Token is acquired before Advisory SQL/session checkout and released only after transaction
  commit/rollback plus session close/invalidate；one token may use at most one connection。
- Provider network I/O holds zero DB token/session/transaction。
- Acquisition, pool checkout, transaction, statement, lock and idle-in-transaction waits are
  bounded by explicit Pack-B values and clipped by invocation/shutdown deadlines。
- Shutdown closes new leases, then cancel/rollback/close or invalidate by Advisory subdeadline；
  shared engine remains available to Protection and is disposed only by Host at the accepted last step。
- Even with A delayed Advisory holders, R capacity remains outside Advisory reach。

## Pack / Compatibility

- Pack A: `NONE`。
- Pack B: numeric retry/provider/queue/shutdown settings plus explicit primary pool capacity,
  Protection reserve, Advisory concurrency and DB timeouts。Missing/invalid/unprovable values ⇒ Gate A cannot ACTIVE。
- Pack C: observation/sufficiency thresholds only。
- PRE-01A-D1 preserved: Trade Decision only, AI advisory, deterministic authority, exactly-one
  final, Single Primary Provider, no fallback/voting, failure taxonomy,
  `ALL_ELIGIBLE_LONG_SHADOW_V1`, Gate A/B/C separation。
- PRE-01B-D1 preserved: one RuntimeHost, FastAPI lifespan, structured concurrency, Protection
  independence, bounded backpressure, deterministic shutdown, no detached ownership。

## SE-02D Refresh

`SE-02D = ACCEPTED / COMPLETE`; `SE-02D V1 CAPABILITY COMPLETE AFTER I03`;
`I04 = NOT REQUIRED`。Still open/deferred：experiment/pair/arm Gate C prerequisite, arm-level
selection Expectancy/delta consumer, durable regime identity, Gate C immutable evidence retention。
`Gate C = NOT PASSED`; Real AI = `NOT ACTIVATED`; Live = `NOT AUTHORIZED`。

## Verification

- docs-only：`pytest = NOT REQUIRED`; `ruff = NOT REQUIRED`。
- `git fetch origin` + ref recheck：`origin/main = a90c5968…`；failed candidate =
  `adb13642…`；parent = `c0bd0e8…`。
- `git rev-parse HEAD` / `git merge-base HEAD origin/main`：均为 `a90c5968…`。
- `PYTHONPATH=src py -3 -m alembic -c alembic.ini heads`（from `backend`）：
  `20260913_0009 (head)`。
- staged changed paths：恰为本任务 allow-list 两个文件。
- `git diff --cached --check`：exit 0；conflict marker scan：0。
- Production / tests / config / schema / migration / state docs changed paths：0。
- Final remaining mechanics：one coherent commit + normal push；commit/push evidence 在任务最终报告返回。

## Non-Claims

No Human Acceptance, I2 implementation, migration, runtime change, Gate A/B/C activation, Real AI
activation, Live authorization, profitability or edge claim。
