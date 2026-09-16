# 2026-09-16 PRE-01B-D2-FIX-03 — Caller-Owned Lease / DISABLED Path

## Task / Result

- Task ID: `PRE-01B-D2-FIX-03`
- Type: `FORMAL DESIGN FIX / DOCS ONLY`
- Result: `FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW`
- Human Acceptance: `NOT PERFORMED`
- I2 Implementation / Migration / Runtime Change / Activation: `NO`

## Requirement / Scope

从 immutable failed reviewed FIX-02 candidate `b5767d147adfeb885dd285243a32041a6731918c`
增量关闭 RR02 两项 P1：

1. `PRE01B-D2-RR02-P1-01` — caller-owned G2 connection 的 token acquisition、lifetime、
   shutdown ownership 与 `A + R <= C` 计数未完整冻结；
2. `PRE01B-D2-RR02-P1-02` — DISABLED classification writer / DB fence / Pack-B-unset
   语义互相冲突。

仅修改：

1. `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
2. `dev_log/2026-09-16-pre-01b-d2-fix-03-lease-disabled.md`

无 production code、tests、schema、migration、runtime config、state document 或 activation
修改。FIX-02 branch/commit 保持 immutable；未 reset、stash、clean、rebase、amend、force-push、
merge 或更新 `main`。

## Protocol / Exact Refs

| Check | Verified fact |
|---|---|
| Global Protocol live `main` | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| tag `protocol-v1.1.0` | same SHA |
| `AI_BOOTSTRAP.md` | `Version 1.1.0 / Status ACCEPTED` |
| `origin/main` / local `main` after fetch | `a90c5968be4b456aabde814eb35d4757380761f7` |
| failed reviewed FIX-02 candidate | `b5767d147adfeb885dd285243a32041a6731918c` |
| candidate parent | `a90c5968be4b456aabde814eb35d4757380761f7` |
| FIX-03 branch/base | `design/pre-01b-d2-fix-03-lease-disabled` / exact `b5767d1…` |
| lineage | `a90c596… -> b5767d1… -> FIX-03 commit` |

Work was performed in isolated clean worktree
`E:\Documents\MarketPulse AI.pre-01b-d2-fix-03-lease-disabled`。Root checkout 的 unrelated
dirty changes 保持原状，未读取为 Accepted Truth、未修改、未归因。

## Repository Truth / Compatibility

- `PostgresG2Repository.persist()` 的 current accepted implementation 由 caller-owned
  `session.begin()` transaction 写 G2 facts + formal Evidence，并由 caller 最终退出 session/
  connection context。
- `RuntimeHost` 唯一拥有 primary `DatabaseResources`；G2、Execution、Protection、Recovery
  共用该 primary session factory，Protection 不经过 Advisory limiter。
- Evidence identity/hash 已由 accepted immutable fields 构成；future admission accounting
  extension 不进入 hash/payload。因此 original Evidence INSERT 直接携带 disabled literal
  不改变 Evidence identity。
- 单一 shared-engine architecture 可用同一 token limiter 对 ordinary Advisory sessions 与
  caller-owned G2 admissions 共同计数；无需第二 engine/pool/DSN。
- PRE-01A-D1、PRE-01B-D1、RR01 closed semantics 与当前 G2/RuntimeHost/DB/Protection facts
  均已重读。RR02 task/controller findings 是本 fix 的 review input。

## Caller-Owned Lease Contract

- G2 已持 connection 时只允许 immediate non-blocking token try-acquire；禁止 queue、await、
  timeout wait 或为取 token checkout 第二 connection。
- token unavailable ⇒ zero Advisory SQL/provider，保留 valid G2/Evidence outer transaction；
  Evidence `UNSTAGED` + deterministic unbound handling；Gate A completeness fail closed。
- token acquired ⇒ 同一个 token 覆盖全部 Advisory SAVEPOINT work、outer commit/rollback，
  直到 caller-owned connection actual return/close/invalidate；SAVEPOINT completion 不释放。
- G2/core caller 始终拥有 outer transaction、session、commit/rollback、final return；writer/
  fence 只拥有 bounded capability 与 Advisory-specific operations。

## Shutdown / Protection Capacity Proof

- Advisory subdeadline 关闭新 work/token 并尽可能 cancel/rollback nested Advisory work。
- fence-owned session 可按 bounded contract close/invalidate；caller-owned G2 connection 不得
  solely-for-Advisory invalidate，valid G2 truth 不得被强制 rollback。
- caller-owned token 在 subdeadline 后仍如实 counted，直到 core owner actual return；Host
  不得假报 released。
- 定义 ordinary holders `H_o`、caller-owned holders `H_g`：

```text
H_o + H_g <= A
A + R <= C
C - (H_o + H_g) >= C - A >= R
```

故 A holders 全部 wedged 时，Advisory 自身仍不能消费 R；Protection 不等待 holders，直接
通过 primary factory 使用 reserve。该证明不覆盖 unrelated core overload、PostgreSQL outage
或 shared-engine failure。

## DISABLED Authority / Pack B

- Host startup 为 current runtime epoch 冻结 immutable activation classification。
- `DISABLED`：不构造 AdvisoryIngress/provider/worker/AdvisoryDbFence/full writer；无 extra
  Advisory SQL/SAVEPOINT。
- existing formal Evidence INSERT 直接写 literal `GATE_A_DISABLED`；不做 seed/config/digest/
  provider preparation，不 separate optional write，不改变 Evidence identity/hash/payload。
- 无法建立 valid disabled classification 时，DB default `UNSTAGED` 是 safe fallback。
- `GATE_A_DISABLED` 永不 retroactive 绑定 experiment/pair/arm；DISABLED→active 需要另行授权
  boundary + new explicitly frozen runtime epoch。
- Pack-B capacity/timeout config 可在 DISABLED unset；active Gate A 前全部 required values
  必须有效。

## Required Matrices / Non-Regression

D2 §33 includes：

- exact acquisition failure matrix；
- token lifetime、shutdown ownership、Protection capacity proofs；
- all 13 required cases（session owner、token lifetime、durable Evidence、G2 outcome、provider、
  Protection capacity、restart action）；
- RR01 P1-01～P1-05 / P2-01 closed-finding non-regression；
- Pack A = NONE；Pack B numeric values retained；Pack C observation thresholds retained。

## Verification

- Docs-only：`pytest = NOT REQUIRED`；`ruff = NOT REQUIRED`。
- `git fetch origin` + exact refs：`origin/main = main = a90c5968…`；FIX-02 candidate =
  `b5767d1…`；`b5767d1^ = a90c5968…`；Global Protocol live main/tag = `07e2df8…`。
- Global `AI_DEVELOPMENT_PROTOCOL.md` @ `07e2df8…` and Bootstrap were fetched/read；
  Protocol = `1.1.0 / ACCEPTED`。
- Static contract assertions：17/17 PASS（immediate try、zero wait、through-return lifetime、
  no SAVEPOINT release、DISABLED direct literal/no fence、Pack-B unset、新 epoch、capacity
  equation、13 matrix rows/columns、RR01 closed findings、FIX-03 verdict）。
- Required 13-case matrix：exactly 13 data rows；each row contains all 8 required outcome columns。
- Incremental FIX-02 → FIX-03 changed paths：exactly D2 design + this FIX-03 dev_log。
- Cumulative main → FIX-03 changed paths：exactly D2 design + FIX-02 dev_log + this FIX-03
  dev_log。
- `git diff --cached --check`：exit 0（Windows LF→CRLF warning only；no whitespace error）。
- conflict-marker scan over both FIX-03 paths：0。
- production code/tests/schema/migration/runtime config/state docs changed paths：0。
- prohibited current wording scan（SAVEPOINT release、DISABLED writer/fence requirement、
  Pack-B required while disabled）：0 actual contradictions；only finding/risk descriptions remain。

## Candidate Verdict / Non-Claims

```text
PRE-01B-D2-FIX-03 = FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW
HUMAN ACCEPTANCE = NOT PERFORMED
I2 IMPLEMENTATION = NOT AUTHORIZED
```

No migration、runtime/config/state change、Gate A/B/C activation、Real AI activation、Live
authorization、provider evidence、edge or profitability claim。
