# PRE-01B-D2-FIX-05｜Connection Return Completion Authority Fix

## PRE-01B-D2-CLAR-01-FIX-02｜Retry-Gap Terminal Provenance Fix Candidate

```text
Fix: PRE-01B-D2-CLAR-01-FIX-02
Status: FIX CANDIDATE DESIGN / READY FOR INDEPENDENT RE-REVIEW
Task type: CLARIFICATION FIX / DOCS ONLY
Reviewed FIX-01 candidate: e408ef7d14213aa5a6ff2cad37dc04b1a65810fd
Finding: PRE01B-D2-CLAR01-FIX01-RR-P1-01
Independent Re-Review: NOT PERFORMED
Human Acceptance: NOT PERFORMED
Implementation / Migration / Runtime change authorized: NO
```

本候选只修复 retry-gap terminal provenance：Invocation 可已有历史 Attempt，但当前
dispatch/retry cycle 的下一个 Attempt 尚未 durable create，而 deadline、stale、binding/config、
capacity、queue 或 shutdown 使 Invocation 直接终态化。这些终态没有 terminal-producing
Attempt；历史 Attempt 只是 immutable audit history，不得因为它是“latest historical
Attempt”而被写入 `final_attempt_id`。

唯一 normative provenance model 区分三态：

1. **Zero Attempt History**：Invocation 从未成功 commit Attempt row；无 terminal-producing
   Attempt，`final_attempt_id=NULL`。
2. **Retry Gap**：一个或多个历史 Attempt 已存在，但当前 retry cycle 尚未成功
   commit 新 Attempt；新的外部 terminal predicate 直接产生终态，因此
   `final_attempt_id=NULL`，历史 Attempt 保留但不连接为 terminal producer。
3. **Current Terminal-Producing Attempt Exists**：当前 cycle 的 Attempt-start transaction 已成功
   commit；若该 Attempt 的 lifecycle/result 直接产生 authoritative terminal，
   `final_attempt_id` 必须引用该 exact same-Invocation Attempt。

`final_attempt_id` 的唯一语义是“其 lifecycle/result 直接产生 authoritative terminal
result 的 durable Attempt”；它不是“latest historical Attempt”。禁止为前两态伪造
Attempt。§14.2 九个 exact pair 是“无 terminal-producing Attempt”闭集，不是
“Invocation 没有任何历史 Attempt”闭集。`*_BEFORE_PROVIDER` 表示在**当前**
dispatch/retry cycle 本应创建的 provider Attempt 之前，不表示 Invocation 生命期内
从未调用 provider。因此 retry-gap 可以有历史 provider call，但终态化的当前
cycle 新增 provider call 必须为 zero。

本契约的 bounded `AdvisoryIngress` queue 是 initial dispatch、retry continuation 与 recovery
re-dispatch 的唯一 process-local dispatch mechanism；它不是 durable authority。Attempt finalizer
或 recovery 将 Invocation 保持/置为 `RETRY_PENDING` 后，只能在 commit 后将同一 frozen
`AdvisoryWorkRef` non-blocking re-offer 到该队列。retry-gap 的 re-offer 若遭
**REJECT NEWEST**，使用既有
`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`，`final_attempt_id=NULL`；不伪造新 Attempt，
不链接历史 Attempt。本澄清不新增 queue、reason literal、table、column 或 dispatch
framework，不改 retry budget 或 REJECT NEWEST policy。

## PRE-01B-D2-CLAR-01-FIX-01｜Reviewed Historical Parent

```text
Fix: PRE-01B-D2-CLAR-01-FIX-01
Status: FAILED INDEPENDENT RE-REVIEW / SUPERSEDED BY FIX-02
Task type: CLARIFICATION FIX / DOCS ONLY
Reviewed parent candidate: f583e096d3a9ed33dcce97b6581b8c336a57d671
Independent Re-Review: FAIL — FIX REQUIRED
Human Acceptance: NOT PERFORMED
Implementation / Migration / Runtime change authorized: NO
```

本历史父候选修复 CLAR-01 Independent Review 的两个 P1：deadline 以 durable Attempt existence
划界，以及所有 no-Attempt terminal 的 exact pair 闭集完整性。除 §14、§17、§18、§19、
§27 的直接同步外，PRE-01B-D2 的架构、业务语义、Gate、SAVEPOINT、DB fence、shutdown、
provider 边界与 CLAR-01 已通过的 F-01/F-02 均不重开。原 PRE-01B-D2 仍是最后一份
Human-Accepted design。FIX-01 因 retry-gap provenance 不完整而失败，由顶部 FIX-02 候选继承；
二者均不授权继续 I2 implementation。

### CLAR-01-B-01｜Historical no-Attempt wording（superseded by FIX-02 provenance model）

`final_status` 是既有 `DecisionStatus` 终态类别；`final_reason_code` 是该终态的精确诊断原因。
两者是不同字段、不同 vocabulary，任何 status token 都不得因为名称相近而充当 reason code。

CLAR-01 的七-pair 列表被 FIX-01 的完整性修复取代；FIX-01 的“no-Attempt”命名又被
FIX-02 精确为“no terminal-producing Attempt”。§14.2 的表是本 artifact **唯一 current
normative no-terminal-producing-Attempt pair authority**；本节不再维护第二份 active whitelist。DB CHECK、§17、
§18、§19 与 §27 只能引用 §14.2 exact pair set，不得按 reason-only、status wildcard、phase name
或 network-call count 自行扩展。`CAPACITY_BLOCKED` 仍只可作为 status，不是 reason code；不得为
任何无 terminal-producing Attempt terminal 伪造 Attempt。

I2 尚未合并，故 continuation 可在最终 descendant candidate 中直接修正未接受的
`20260917_0010_advisory_ingress_core.py` CHECK；不得仅为保留该 unaccepted candidate mistake
而新增第二条 Alembic revision。本 clarification fix 不修改 migration。

### CLAR-01-F-01｜Canonical arm identity domain

三个选项的裁定如下：

| Option | Verdict | Reason |
|---|---|---|
| A. `pair_id` 作为动态 hash domain | REJECTED | 没有固定、可审计、可版本化的 arm domain literal；把实例 identity 混入 domain 角色 |
| B. 专用固定/versioned arm domain | **SELECTED** | 保持 canonical serialization，同时提供 pair 与 arm 的语义域隔离、独立版本边界和 replay 可审计性 |
| C. 复用 `pre01a-pair-v1` | REJECTED | 虽可确定性计算，但把 pair/arm 两种 identity 置于同一语义 domain，且 arm derivation 没有独立 version authority |

唯一 canonical derivation 为：

```text
arm_id = H("pre01a-arm-v1", pair_id, arm_label)

baseline_arm_id = H("pre01a-arm-v1", pair_id, "WITHOUT_AI_BASELINE")
treatment_arm_id = H("pre01a-arm-v1", pair_id, "REAL_AI_TREATMENT")
```

其中 `H(domain, *parts)` 使用项目 versioned canonical JSON digest；精确 canonical preimage
分别为：

```json
["pre01a-arm-v1", "<pair_id>", "WITHOUT_AI_BASELINE"]
["pre01a-arm-v1", "<pair_id>", "REAL_AI_TREATMENT"]
```

`pre01a-arm-v1` 是冻结的 arm hash domain/version literal。canonical JSON 必须保持类型、
顺序与边界，不得用 delimiter join、`repr()`、process hash 或 provider output。collision
语义仍依赖所选 cryptographic digest 的 collision resistance；专用 domain 防止相同 canonical
parts 在 pair/arm 等不同 identity class 间发生 accidental aliasing，并允许未来 arm contract
变化通过新 domain version 建立新 lineage，而不重解释 `pre01a-arm-v1` row。

该澄清不改变 `pair_id`、两条 arm label、baseline/treatment separation、treatment
participation、experiment definition 或 `decision_invocation_id` semantic ownership。I2 未合并且
不存在 Production Advisory row，故 correction 不需要兼容 foundation candidate 派生出的 arm ID。

### CLAR-01-F-02｜Future I2 exact-derivation test

未来 I2 tests 必须独立构造 canonical JSON preimage/digest，并逐字断言
`pre01a-arm-v1`、`pair_id` 与 exact arm label 的输入顺序。只断言
`baseline_arm_id != treatment_arm_id` 不充分；调用被测实现自身来生成 expected digest 的
self-referential test 也不充分。

## Artifact Status

```text
Artifact: PRE-01B-D2 AdvisoryIngress / G2→G3 Activation Contract
Status: ACCEPTED / COMPLETE
Human Acceptance: CONFIRMED — 2026-09-17
Human-Accepted reviewed candidate: cce1ae7b862b038a99976c802c0985df01b35285
Independent Re-Review: PRE-01B-D2-FIX-05 = PASS
Review severity: P0 = NONE / P1 = NONE / P2 = NONE / P3 = NONE
Task type: DESIGN FIX ONLY / DOCS ONLY
Implementation authorized by this artifact: NO
Runtime or provider activation authorized by this artifact: NO

Latest Accepted Main: a90c5968be4b456aabde814eb35d4757380761f7
FIX-05 Base / failed reviewed FIX-04 candidate: d3922dd35ba83312194d124e17fa8645dead6e4d
FIX-05 branch: design/pre-01b-d2-fix-05-return-completion-authority
Preserved FIX-04 branch: design/pre-01b-d2-fix-04-db-semantics
FIX-04 Base / failed reviewed FIX-03 candidate: 4548920fddc7e4f84b0edab8a7e5d72fc35d54ff
Preserved FIX-03 branch: design/pre-01b-d2-fix-03-lease-disabled
FIX-03 Base / failed reviewed FIX-02 candidate: b5767d147adfeb885dd285243a32041a6731918c
Preserved FIX-02 branch: design/pre-01b-d2-fix-02-latest-main
Failed reviewed FIX-01 candidate (immutable evidence):
  design/pre-01b-d2-fix-01-advisory-ingress-contract
  @ adb1364218d29faba55626c68b9c1a07cc7f2cee
Failed candidate parent: c0bd0e8145a82372a6322f63369e6467cae9022f

Historical lineage:
Original D2 Base: 664207a9caba0c3f5c2589cfca2a10af24f89108
Original Blocked Local Draft: be836c0ed008058508eb4a9065d03c7b617f7c0b
  (branch design/pre-01b-d2-advisory-ingress-contract，BLOCKED DRAFT / NON-CANONICAL /
   NOT REVIEWED / NOT ACCEPTED；仅作 DRAFTING INPUT，不 push / 不 rebase / 不 amend /
   不 repoint)
Block Reason: SE-02D-I02 material baseline drift
Rebuilt Baseline: d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6
Candidate branch: design/pre-01b-d2-advisory-ingress-contract-r1
Reviewed parent candidate: c0bd0e8145a82372a6322f63369e6467cae9022f
Fix branch: design/pre-01b-d2-fix-01-advisory-ingress-contract
```

本文件从 immutable failed reviewed FIX-04 candidate `d3922dd…` carry forward 已关闭语义，
并只修复 RR04 `P1-01`（connection return completion authority）。FIX-04 对 RR03
`P1-01`（Advisory timeout 泄漏）与 `P2-01`（token acquisition / SAVEPOINT ordering）的
处置保持关闭；RR03 `P1-02` 的“exact checkin callback 即可释放”规则已被 RR04 反例推翻，
由 §35 的 two-factor completion authority 完整取代。
它只冻结未来独立获批的
`PRE-01B-I2` 所需设计边界；不实现、不迁移、不接通
live `G2→G3`、不构造真实 provider，也不授权 Gate A / Gate B / Live。本次重建以
blocked draft 为起草输入，但**每一个重要决策都对照 latest Accepted Repository Truth
（当前含已接受的 SE-02D-I01/I02/I03 与 Overall closeout）重新审计**；与旧 draft 的差异
在 §0.3、§32～§34 与 dev_log 中显式列出。

## 0. Rebuild 说明

### 0.1 原始重建授权（historical）

Human / Design AI 已明确授权：在 latest Accepted Main `d1e5534` 上重建 PRE-01B-D2。
旧 draft `be836c0` 的处理遵循任务边界：不 push、不 rebase、不 amend、不 repoint、
不删除其本地历史；其内容仅作为起草输入。

### 0.2 重建方法

1. 实时核验 Global Protocol（v1.1.0 / ACCEPTED / `07e2df8…`）与 `origin/main = d1e5534`。
2. 完整重读两份 Accepted Contract（PRE-01A-D1、PRE-01B-D1）与新接受的 SE-02D-I02
   真值（`aggregation_snapshot.py` + 测试 + 两份 dev_log）。
3. 对照 latest 代码重审计旧 draft 的全部 source facts（G2 formal transaction、
   EventRuntime、capture/qualifies、G3 Workflow/Decision/Queue、RuntimeHost、
   DB schema、attribution）。
4. 对 §8 列出的每一项重要决策逐条重审；改动者给出新证据，保留者给出重验证证据。

### 0.3 相对旧 draft 的决策变更总览（详情见各节）

| # | 旧 draft 决策 | 重建决策 | 变更原因（证据） |
|---|---|---|---|
| 1 | Admission staging 失败 ⇒ 回滚**整个** G2 formal transaction（G2 facts + Evidence 一并丢失） | Admission staging 在同一 transaction 内以 **SAVEPOINT 隔离**；staging 失败只回滚 advisory 部分，G2 facts + Evidence 照常 commit | 旧设计让 AI provenance 基础设施失败摧毁 durable G2 market truth —— 恰是任务 §12 质疑的「AI advisory persistence 污染 Scanner core responsibility」。Atomicity 由 savepoint 保留，G2 真值不再被 AI infra 劫持 |
| 2 | queue full 的 durable 终态 = `INVALID_SCHEMA / ADVISORY_QUEUE_REJECTED` | = `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` | PRE-01A-D1 §8.1 冻结 `CAPACITY_BLOCKED` = 「downstream capacity outcome, not an AI/provider failure」；queue full 正是 capacity outcome，映射为 `INVALID_SCHEMA` 会污染 failure-rate 诊断 |
| 3 | `decision_requested_at` 权威 = 读回 formal Evidence 的 durable `created_at` | 权威 = **PostgreSQL admission clock 在同一 CTE 中单次捕获的 timestamp**，先进 Evidence admission seed，再原样进 Invocation | Evidence.created_at 不是 accepted clock authority；「same transaction ⇒ 数值相等」无效且已删除；见 §17 |
| 4 | Evidence supersede 仅在 stale matrix 一句带过 | **独立 Evidence Supersede Contract**（§10）+ 明确「N+1 可另立新 Invocation」规则 | SE-02D-I02 新接受语义使 revision-chain / canonical head 成为必须显式设计的边界；PRE-01A-D1 §10 已冻结「新 Evidence revision ⇒ 新 unit/invocation」 |
| 5 | （无此节；旧 draft 早于 I02） | **Admission Evidence vs Canonical Evidence Head 区分**（§9）+ SE-02D-I02 runtime reuse = NONE（§23.2） | 任务 Critical Question A；I02 是 aggregation-oriented REPEATABLE READ 只读投影，与 live decision-ingress 不耦合 |
| 6 | `input_binding_digest` 不含 `feature_snapshot_hash` | **纳入** `feature_snapshot_hash` | 任务 §9 要求逐项评估五个 identity 字段；feature snapshot hash 是 Evidence 身份的组成部分（schema 实测存在于 `edge_opportunity_evidence`） |

### 0.4 FIX-01 授权与边界

Independent Review 对 parent candidate `c0bd0e8145a82372a6322f63369e6467cae9022f`
的结论为 `FAIL — FIX REQUIRED`（P0 = NONE；P1 × 5；design P2 × 1）。
FIX-01 只处置这 6 项，不修复 process P2，不改动已通过区域，不执行实现/
测试/迁移/激活。`CLOSED` 仅代表本 Candidate 声称设计处置完成；最终
closure 归 Independent Reviewer，Human Acceptance 未执行。

### 0.5 FIX-02 授权与边界

Independent Re-Review `PRE-01B-D2-RR01` 对 immutable failed candidate `adb1364…`
的结论为 `FAIL — FIX REQUIRED`。仅以下两项是本轮 blocking fix：

- `PRE01B-D2-RR01-P1-01`：完整 seed/accounting 在 SAVEPOINT 外，Advisory-only
  failure 仍可能回滚 valid G2 truth；
- `PRE01B-D2-RR01-P1-05`：只有 shutdown time reservation，没有 Advisory-vs-Protection
  DB capacity / acquisition / transaction resource fence。

`P1-02` / `P1-03` / `P1-04` / `P2-01` 保持关闭，除非本轮修改与其冲突；未发现冲突。
`P3-01` 只作当前 SE-02D 描述刷新。§32 是 FIX-02 的集中 disposition 与非回归证明；
本文件早期带日期的 historical baseline 叙述保留为历史记录，不覆盖 §32 的 latest-main
结论。

### 0.6 FIX-03 授权与边界

Independent Re-Review `PRE-01B-D2-RR02` 对 immutable FIX-02 candidate `b5767d1…`
的结论为 `FAIL — FIX REQUIRED`（P0 = NONE；P1 = 2）。本轮仅关闭：

- `PRE01B-D2-RR02-P1-01`：caller-owned G2 connection 在持连接等待 token、token
  lifetime 与 shutdown ownership 上未被一致计数；
- `PRE01B-D2-RR02-P1-02`：`DISABLED` 同时要求 classification writer / DB fence，
  又允许 Pack-B unset，无法实现。

RR01 `P1-01`～`P1-05` 与 `P2-01` 的已关闭语义全部保留；不重做 Evidence supersede、
Invocation final authority、deadline、fake `QUEUED` 或原 resource-fence 方向。§33 是
FIX-03 的集中 normative disposition；§7、§8、§20、§21、§24、§25、§27、§28、§30～§32
已同步删除与之冲突的 current normative wording。历史带日期事实仍保留为历史证据。

### 0.7 FIX-04 授权、proof-first 边界与证据

Independent Re-Review `PRE-01B-D2-RR03` 对 immutable FIX-03 candidate `4548920…`
的结论为 `FAIL — FIX REQUIRED`。本轮只关闭：

- `PRE01B-D2-RR03-P1-01`：caller-owned outer G2 transaction 中的 Advisory-specific
  `SET LOCAL` timeout 会在 SAVEPOINT release 后继续生效；client cancellation / idle timeout
  还可能终止 connection，污染 otherwise-valid G2 transaction；
- `PRE01B-D2-RR03-P1-02`：进入 `finally` 或开始 `close()` 不是 connection 已 return/
  invalidate-complete 的可观察事实，不能据此回补 Advisory token；
- `PRE01B-D2-RR03-P2-01`：SQLAlchemy `begin_nested()` 会在发出 SAVEPOINT 前无条件 flush
  pending state，故 token acquisition 必须位于显式 G2/Evidence core flush 之后、
  `begin_nested()` 之前。

Phase A 在独立 PostgreSQL 16.15、SQLAlchemy 2.0.52、asyncpg 0.31.0 环境完成真实实验；
未连接项目数据库。官方与实测证据、八类 failure matrix 和最终 normative disposition 见 §34。
RR01/RR02 已关闭语义全部保留；不实施 I2、不修改 Runtime/schema/migration/test/config、不激活
任何 Gate/Real AI/Live。

### 0.8 FIX-05 授权、唯一修正与状态

Independent Re-Review `PRE-01B-D2-RR04` 对 immutable FIX-04 candidate `d3922dd…`
的结论为 `FAIL — FIX REQUIRED`（P0 = NONE；P1 = 1）：

- `PRE01B-D2-RR04-P1-01`：SQLAlchemy 2.0.52 的 exact `PoolEvents.checkin`
  callback 在 pool return sequence 完成前执行；callback 被观察后，后续 listener/return step
  仍可抛错并让 physical pool slot 保持 checked out。因此 callback observation 不等于 owner
  lifecycle/disposition 已成功完成，不能单独恢复 Advisory capacity。

FIX-05 只冻结 normal return、caller-owned G2 owner-completion、explicit invalidation、exact
generation correlation、uncertain retirement、late/duplicate、capacity 与 shutdown 的直接依赖语义。
§35 是最终 normative disposition；§34 仅保留 FIX-04 historical evidence。RR03-P1-01 与
RR03-P2-01 保持 `PRESERVED CLOSED`；RR01/RR02 其余 closed findings、DISABLED、Gate/Real
AI/Live 边界不变。I2 implementation、Runtime/schema/migration/test/config/project DB/service/provider
mutation 均未授权、未执行。

## 1. Repository Truth

### 1.1 Reviewed candidate historical baseline（2026-09-15 / 2026-09-16）

| 项 | 实时核验事实 |
|---|---|
| Global Protocol | `zwmhua2-lab2/ai-dev-protocol`，`git ls-remote` 实测 `main = 07e2df83266d4ecdea46caff5c61f000937b8913` |
| Protocol Version / Status | `1.1.0 / ACCEPTED`（`AI_BOOTSTRAP.md` @ `07e2df8` 实读） |
| Project repository | `zwmhua2-lab2/MarketPulse-AI` |
| Remote `origin/main`（`git ls-remote` 实测） | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Local `main` | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Task Base / Rebuilt Baseline | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Baseline drift | `NO`（与任务卡 issuance 值一致） |
| Candidate branch | `design/pre-01b-d2-advisory-ingress-contract-r1`（base = `d1e5534`，新 worktree） |

FIX-01 于 2026-09-16 重新执行 realtime check：

| FIX-01 项 | 实测事实 |
|---|---|
| Reviewed parent candidate | `design/pre-01b-d2-advisory-ingress-contract-r1 = c0bd0e8145a82372a6322f63369e6467cae9022f`（local/remote 一致，未移动） |
| FIX branch/base | `design/pre-01b-d2-fix-01-advisory-ingress-contract` from exact `c0bd0e8...` |
| Current `main` / remote | `44df66603e6bdba1f3f80c21be5b30c295e4a20a`（local/origin/ls-remote 一致） |
| `d1e5534..main` drift | 只有 `aa2232e` + `44df666`，仅修改 SE-02D-I02 final-acceptance incident disclosure/closure dev_log |
| Drift classification | **ORTHOGONAL**；未触及 G2/G3/RuntimeHost/Opportunity/Evidence/DB/schema/PRE-01A/PRE-01B/SE-02D identity semantics |

会话根工作区位于 `prb-01-product-requirements-baseline@d47313a`（另一条历史分支）。
D2 在从 verified `main = d1e5534` 建立的独立 clean worktree 中完成；未 reset、stash、
clean、rebase、覆盖或归因根工作区内容。

#### 1.1.1 FIX-02 latest-main baseline（2026-09-16 实时核验）

| FIX-02 项 | 实测事实 |
|---|---|
| Global Protocol | live `main` = tag `protocol-v1.1.0` = `07e2df83266d4ecdea46caff5c61f000937b8913`; `AI_BOOTSTRAP.md` = `1.1.0 / ACCEPTED` |
| Accepted Main / Task Base | `origin/main = main = a90c5968be4b456aabde814eb35d4757380761f7` |
| Failed reviewed candidate | local/remote `design/pre-01b-d2-fix-01-advisory-ingress-contract = adb1364218d29faba55626c68b9c1a07cc7f2cee`，保持 immutable |
| Failed candidate parent | `c0bd0e8145a82372a6322f63369e6467cae9022f` |
| FIX-02 branch/base | `design/pre-01b-d2-fix-02-latest-main` from exact `a90c5968…` in isolated clean worktree |
| Reviewed-candidate merge base | `d1e5534dcd8eb63fe71f0e3c06ab80dfc1a6f0e6` |
| Relevant source drift | G2/G3/G4/RuntimeHost/DB/session/schema/PRE-01A/PRE-01B-D1 source semantics unchanged；新增 SE-02D-I03 aggregation orchestration 与状态收尾，正交于 live Advisory ingress |

#### 1.1.2 FIX-03 incremental baseline（2026-09-16 实时核验）

| FIX-03 项 | 实测事实 |
|---|---|
| Global Protocol | live `main` = tag `protocol-v1.1.0` = `07e2df83266d4ecdea46caff5c61f000937b8913`; `AI_BOOTSTRAP.md` = `1.1.0 / ACCEPTED` |
| Accepted Main | `origin/main = main = a90c5968be4b456aabde814eb35d4757380761f7` |
| Failed reviewed FIX-02 candidate | local/remote `design/pre-01b-d2-fix-02-latest-main = b5767d147adfeb885dd285243a32041a6731918c`，保持 immutable |
| Candidate parent | `b5767d1^ = a90c5968be4b456aabde814eb35d4757380761f7` |
| FIX-03 branch/base | `design/pre-01b-d2-fix-03-lease-disabled` from exact `b5767d1…` in isolated clean worktree |
| Root checkout | unrelated dirty state preserved；未 reset/stash/clean/rebase/覆盖/归因 |

### 1.2 Accepted inputs

- `PRE-01A-D1` = `ACCEPTED / COMPLETE`：冻结 Real AI V1 placement（C. Trade Decision only）、
  input binding、`decision_invocation_id` → exactly one logical durable final decision、
  retry/deadline/failure taxonomy、`ALL_ELIGIBLE_LONG_SHADOW_V1` baseline、Gate A/B/C 边界。
- `PRE-01B-D1` = `ACCEPTED / COMPLETE`：冻结 `RuntimeHost` 唯一 composition owner、
  FastAPI lifespan 唯一 activation boundary、AnyIO structured concurrency、Protection
  isolation、shutdown 顺序（step 2 显式预留 advisory 槽位）、backpressure 契约、
  以及「future batch may add one Host-owned `AdvisoryIngress`」的显式边界。
- `PRE-01B-I1` / Integrated Runtime Host Core V1 = `ACCEPTED / COMPLETE`
  （candidate `68dd7e9`，branch `pre-01b-i1-fix-01-runtime-host-lifecycle`）。
- `SE-02D-D01` / `SE-02D-I01` / `SE-02D-I02` / `SE-02D-I03` /
  `SE-02D-CLOSE-D01` / `SE-02D Overall` = `ACCEPTED / COMPLETE`；
  `SE-02D V1 CAPABILITY COMPLETE AFTER I03`；`I04 = NOT REQUIRED`。
- Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACCEPTED / NOT ACTIVE`；
  Gate C = `NOT PASSED`；Live = `NOT AUTHORIZED`。

### 1.3 Known stale index statement（已知陈旧索引行，非新矛盾）

`AI_CONTEXT.md`（§4 等）与 `PROJECT_STATE.md` Current Group 列表仍残留
「Integrated Runtime Host — NOT STARTED」一类较旧摘要行。按任务卡 §4，这是**已知陈旧
索引语句**：权威状态以 per-batch 条目为准 —— `PRE-01B-I1` 条目明确记录
「Runtime Host Core V1 = ACCEPTED / COMPLETE」（仅 Core V1，不含 OS/service、
Real AI、G2→G3）。本轮 re-audit **未发现**该已知模式之外的**新**矛盾。

### 1.4 Source facts that control this design（latest main 实测）

1. `PostgresG2Repository.persist()` 在单个 `session.begin()` transaction 内写
   `MarketEvent`（on-conflict dedupe）、timeline、`SymbolStateStore` merge、transition、
   candidates、observation，并在 capture context 配置时经 `capture_opportunity()`
   → `append_evidence_revision()` 写 qualifying `edge_opportunity_evidence`。
   当前返回值仅为 `bool`。（`g2/repository.py` 实读）
2. qualifying 规则 = `qualifies()`：transition `APPLIED` → `to_state = SETUP`、
   event `BREAKOUT`、state `SETUP`、存在 `watch_expires_at`、`BREAKOUT_RETEST`
   candidate 全 identity/version 一致；reference/AI/Risk/Trade/BBO **不是** admission
   条件。（`edge/capture.py` 实读）
3. `RUNTIME_CAPTURE_REVISION = 1`：runtime capture 恒写 logical opportunity 的
   **初始 revision**；revision > 1（supersedes 链）是 SE-02A 已接受 schema/契约能力，
   当前 live G2 路径不产生。（`edge/capture.py` 实读）
4. `edge_opportunity_evidence` 已持有 deterministic
   `opportunity_id/evidence_id/evidence_revision/evidence_hash/feature_snapshot_hash`、
   `supersedes_evidence_id`（同 opportunity FK）、family/instrument/market/source identity、
   `detected_at/evidence_at/expires_at/created_at`、reference quote 三态
   （`OK/REFERENCE_MISSING/REFERENCE_STALE`）与 immutable payload；DB 侧
   `uq_edge_evidence_opportunity_revision` + `fk_edge_evidence_supersedes` 保证
   revision/scope integrity。（`db/models.py` 实读）
5. `DecisionSnapshotRecord` 无 Opportunity/Evidence 绑定、无 payload hash、无
   request time / absolute deadline；`AIDecisionRecord.decision_id` 仅由
   `stable_id("decision", snapshot_id, model)` 派生，无 invocation linkage / unique
   fence；`DecisionService.decide()` provider 返回后才写 snapshot+decision（同
   transaction 含 attribution append），retry 无 durable attempt / joint deadline /
   winner fence。（`g3/service.py`、`db/models.py` 实读）
6. `G3Workflow.process_setup()` 在 `VALID + LONG_BIAS` 时经 `TradePlanManager` 构造并
   `persist_trade_plan()` —— 它不是 Shadow-safe consumer。（`g3/service.py` 实读）
7. `BoundedAITaskQueue.put()` await queue space（blocking）、process-local
   `datetime.now(UTC)`、混合 `POSITION_REVIEW/PLAN_REVIEW/NEW_SETUP/LOW` 优先级、
   无 full-rejection / restart / deadline / durable dedupe 契约。（`g3/service.py` 实读）
8. `EdgeAttributionRecorder` 以 caller-transaction 内 append-only / idempotent 方式绑定
   exact `opportunity_id/evidence_id` AI lineage（`DecisionService.decide()` 已在
   decision 同 transaction 调 `record_ai_decision`）。identity 可复用，但 attribution
   不是 invocation / final-result authority。（`g3/service.py` 调用点 + SE-02B 验收记录）
9. I1 Host：safety lane 与 scanner lane 隔离；`AI_AUXILIARY` health 组件注册为
   `DEGRADED/ai_reevaluation_disabled`，**不在** Core readiness 阻断合取内；Host
   不构造任何 AI provider（`_AIDisabledSentinel`）；`_shutdown()` step 2 注释显式
   预留 advisory 关闭槽位。（`runtime_host.py` 实读）
10. SE-02D-I02 `aggregation_snapshot.py`：`CurrentSnapshotRevisionReader.read(horizon)`
    在单个 `REPEATABLE READ READ ONLY` snapshot 内以 DB `statement_timestamp()` 为
    `as_of`，折叠全量可见 Evidence / 精确 horizon Outcome 修订链、选 canonical head、
    cross-integrity 校验、输出 `CanonicalScopeFacts` + revision-aware manifest；
    不调用 `aggregate()`、无 historical `as_of` 接口。I03 已在其 projection 上实现
    population grouping + aggregate orchestration；它仍不是 live Advisory runtime dependency。
    （latest-main 源码 + accepted dev_log 实读）

## 2. Problem Statement

当前缺少的不是「再调用一次 G3」，而是一条能够证明下列性质的 live boundary：

```text
committed qualifying G2 SETUP / Opportunity Evidence revision
  -> durable invocation admission（与 Evidence 原子）
  -> bounded Host-owned queue（post-commit 发布）
  -> shadow-safe advisory invocation
  -> durable attempts（provider call 之前 durable）
  -> exactly one durable final winner（PostgreSQL fence）
```

任何 transient Scanner object、uncommitted row、ORM session-bound object、process
callback identity 或 in-memory dedupe 都不能成为该链的 correctness authority。
此外，SE-02D-I02 的接受使「Evidence revision chain / canonical head」成为已接受的
durable 语义：live advisory admission 必须显式回答它绑定的是**哪一份** Evidence 身份、
以及 supersede 发生时旧 Invocation 的命运（§9 / §10）。

## 3. Scope

- 精确冻结 qualifying Opportunity/Evidence revision 的 producer 与 post-commit handoff。
- 冻结 Host-owned `AdvisoryIngress` 的 construction/start/task/queue/shutdown/health ownership。
- 冻结 admission Evidence vs canonical Evidence head 的区分与 Evidence supersede 契约。
- 冻结 immutable work reference、durable re-read、snapshot/input binding、
  invocation/attempt/final identity。
- 冻结 experiment/pair/arm binding、retry/deadline/cancellation、duplicate/late/winner fence。
- 冻结 bounded queue/full policy、staleness、restart、failure isolation、health/readiness。
- 冻结 Gate A Shadow 与 Gate B Paper Economic activation 的结构性分离。
- 审计并裁定现有 schema/components（含 SE-02D-I02）的复用方式，提出最小未来 schema delta。
- 给出一个可独立获批的最小 I2 Implementation Batch 与 AC。

## 4. Out of Scope

- 任意 production code、test、migration、schema、config、runtime 或 DB 改动。
- 真实 provider/model 选择、constructor、API call、credential 或 provider runtime evidence。
- Gate A 启动、Gate B 启动、Live Trading、Short、自动 fallback、model voting。
- 修改 G2 state-machine/Scanner/Strategy business 语义或 SE-02A Evidence 契约。
- 修改 `TradePlanManager`、Risk、Execution、Accounting、Protection、Recovery、
  Reconciliation 语义。
- SE-02D 后续实现（population grouping、`aggregate()` 调用、Gate C threshold、
  profitability/edge 声明）；historical revision-as-of。
- Position re-evaluation、generic workflow/event bus、microservice 或 process supervisor。

## 5. Accepted Invariants

1. `RuntimeHost` 是唯一 production composition owner；FastAPI lifespan 是唯一 Host
   activation boundary（PRE-01B-D1 / I1）。
2. AI = Advisory；deterministic system = Authority（PRE-01A-D1）。
3. Gate A 必须结构性地拥有 **ZERO** TradePlan/Risk/Execution/Position/Account/Ledger
   mutation capability。
4. Protection 与 risk-reducing path 不等待、不共享 queue/lock/task failure domain 给
   Advisory（PRE-01B-D1 Protection Isolation Contract）。
5. PostgreSQL 是 durable correctness authority；queue、lock、set、TaskGroup 仅是进程内
   执行机制。
6. one `decision_invocation_id` → exactly one collision-free logical durable final
   decision（PRE-01A-D1 §6.3 / AC-21）。
7. retry 共享 invocation/deadline/input/experiment/pair/arm/provider/model；每次 attempt
   有独立 identity。
8. Single Primary Provider；no automatic fallback；no model voting；provider 不拥有本地
   identity。
9. missing/stale/invalid/failure 均 fail closed，不能转成 baseline BUY 或伪装为 AI
   decision；AI failure → zero new risk（PRE-01A-D1 §5.2）。
10. Paper only / SPOT LONG only；`SHORT_BIAS` 仅是分析/no-long。
11. Gate A、Gate B、Gate C 与 Live 是互不替代的独立授权边界。
12. Durable G2 market/Evidence truth 不依赖 AI 基础设施的健康状态（本次重建新增，
    见 §8.3）。
13. Gate-A-eligible Evidence revision 不得因 snapshot/Invocation staging 失败而从
    experiment/provenance accounting 中永久消失；它必须可查询为已创建、
    可恢复，或按原 deadline 终态失败（见 §8.3）。

## 6. Historical Baseline Reconciliation（664207a → d1e5534）

### 6.1 Delta 事实（实测）

`git log 664207a..d1e5534` = 单一 commit `d1e5534`（`docs(se-02d-i02): accept I02 via
latest-main reconciliation`）。`git diff --stat` 显示改动恰为 7 个文件：
`AI_CONTEXT.md`、`DECISIONS.md`、`PROJECT_STATE.md`、
`backend/src/marketpulse/edge/aggregation_snapshot.py`（+666）、
`backend/tests/test_se_02d_aggregation_snapshot.py`（+981）、两份 SE-02D-I02 dev_log。
**零** G2/G3/RuntimeHost/前端/config 变更。

### 6.2 Delta 分类

- Accepted change：`SE-02D-I02 = ACCEPTED / COMPLETE`（Current-Snapshot Revision
  Folding / canonical-head projection）。
- 它引入的已接受语义：full visible Evidence revision-chain validation；canonical
  Evidence head selection；frozen logical fact validation；exact-horizon Outcome
  revision-chain folding；canonical Outcome head / `NO_OUTCOME`；canonical
  Evidence ↔ Outcome cross-integrity；`CanonicalScopeFacts` projection；
  `CURRENT_STABLE_SNAPSHOT`（REPEATABLE READ READ ONLY + DB
  `statement_timestamp()` 作 `as_of`）。
- **Classification：MATERIAL TO D2 DESIGN AUDIT** —— 它使 revision-chain /
  canonical-head 成为已接受语义，D2 必须显式回答 Critical Question A（§9）与
  supersede 语义（§10）。
- 它**不**自动意味着：AdvisoryIngress 必须调用 `aggregation_snapshot.py`（裁定：
  **NONE**，§23.2）；也不自动意味着 current canonical Evidence head 就是 live
  advisory admission identity（裁定：**不是**，§9）。

### 6.3 对旧 draft source facts 的影响

§1.4 facts 1–9 与旧 draft 的 source facts 逐条比对：d1e5534 相对 664207a 未触碰
G2/G3/RuntimeHost/Edge capture/schema/attribution 任何路径，旧 facts 在 latest main
上复测全部成立（本窗口直接实读源码复核，非沿用旧 draft 自述）。唯一新增材料性输入
是 fact 10（I02 投影层）。

## 7. Reuse Decisions

| 现有组件 | Verdict | 设计裁定（latest main 复核后） |
|---|---|---|
| `BoundedAITaskQueue` | `DO NOT USE IN GATE A` | blocking `put`、process-local wall clock、混合 Position/Plan/New 优先级、无 full/restart/deadline/final fence；不得把 Position Review 与 Gate A setup 混队列。仅「bounded queue」概念参考 |
| `DecisionService` | `ADAPT` | 复用 provider-neutral boundary、`PromptBuilder`/`DecisionValidator`/`redact` pieces；拆为 pre-call durable admission、attempt runner、finalizer。不沿用 call-first/persist-later、legacy retry、legacy `decision_id` |
| `G3Workflow` | `DO NOT USE IN GATE A` | 实测 `process_setup()` 持有 `TradePlanManager` 并在 VALID+LONG path 调 `persist_trade_plan()`；直接复用会产生未授权经济前置事实 |
| `DecisionSnapshotBuilder` | `ADAPT` | 改为从 exact formal Evidence revision + 同 transaction durable facts 构造 canonical immutable snapshot；增加 content hash 与完整 binding。不以 caller mutable object / global market object 为 authority |
| `TradePlanManager` | `DO NOT USE IN GATE A` | Gate A consumer 不构造、不注入、不调用 |
| existing AI decision persistence（`decision_snapshots` / `ai_decisions`） | `REUSE WITH MINIMAL EXTENSION` | snapshots 继续存 frozen input；`ai_decisions` 只存 normalized provider artifact 并强制 Attempt origin；Invocation 五个 final fields 是唯一 terminal authority（§14/§24） |
| `RuntimeHost` TaskGroup / lifecycle | `ADAPT` | Host 构造/启动/停止 Advisory（D1 shutdown step 2 预留槽位）；一个受控 wrapper child 拥有内部 finite workers；Advisory 异常在 wrapper 内分类，不得取消 safety siblings；沿用 I1 fatal matrix，不自建 restart loop |
| existing attribution identity（`EdgeAttributionRecorder`） | `REUSE` | exact `opportunity_id/evidence_id` lineage、append-only、caller-transaction pattern 保持；payload 可增 invocation/experiment facts；attribution 不是 winner authority |
| `PostgresG2Repository` formal transaction | `ADAPT` | 复用 G2+Evidence 原子提交；startup epoch 明确 `DISABLED` 时，existing formal Evidence INSERT 直接携带 frozen literal `GATE_A_DISABLED`，不构造 writer/fence/SAVEPOINT；Gate A active ordering = explicit core flush → immediate non-blocking token try → nested SAVEPOINT；全部 Advisory preparation/persistence 在 SAVEPOINT 内；caller-owned timeout 只用 captured/restored statement/lock；token 覆盖 outer result、pool-return observation 与 owner lifecycle completion，直到 §20.3/§35 full positive predicate；任何 Advisory-only failure 只在 connection valid + rollback confirmed 时隔离；queue 只在 commit 成功且 Invocation 已 durable 后触达；`persist()` 返回 typed result |
| SE-02D-I02 `aggregation_snapshot`（`CurrentSnapshotRevisionReader` / `CurrentSnapshotProjection` / `CanonicalScopeFacts`） | `DO NOT USE IN GATE A`（runtime reuse = NONE） | I02 是 Edge/Expectancy 的 REPEATABLE READ READ ONLY、aggregation-oriented 投影；live advisory decision-ingress 不得与之耦合。概念性复用见 §23.2 |

## 8. Producer Boundary

### 8.1 Exact qualifying record

唯一 producer input 是已满足 accepted `qualifies()` 规则、将要写成
`EdgeOpportunityEvidenceRecord` 的 formal Evidence revision（当前恒为 revision 1，
`RUNTIME_CAPTURE_REVISION = 1`；若未来已接受的 G2 变更引入 live revision > 1，本契约
按 revision 粒度自动适用，见 §10）。以下均**不是** producer input：

- `StrategyCandidate` 单独存在；
- Capture Anchor（含其 `UNVERIFIABLE_ORPHAN` 分类）；
- `SignalTimelineEvent` 单独存在；
- process-local `SETUP` state；
- callback 自造的 symbol/time identity。

### 8.2 Exact transaction and enqueue timing

未来 I2 必须把当前 bool-only `persist()` 结果最小扩展为 typed result。流程固定为：

1. `PostgresG2Repository.persist()` 在现有 G2 formal transaction 中写 G2 facts 与
   exact Evidence revision（`capture_opportunity()` 内），然后由 G2/core owner 执行一次
   **显式 `session.flush()`**。该 flush 只含 G2/Evidence core state，必须在任何 token
   acquisition、`begin_nested()` 或 Advisory-specific SQL 之前成功；失败是 legitimate core
   transaction failure，禁止尝试 Advisory、SAVEPOINT 或 provider。
2. I2 migration 对既有 Evidence 一次性标为 `LEGACY_PRE_I2`；新 row 的 PostgreSQL
   safe default 为 `UNSTAGED`。Host startup 先冻结 current runtime epoch 的 immutable
   activation classification。若该分类合法且为 `DISABLED`，existing formal Evidence
   INSERT 在同一 statement 直接携带 literal `GATE_A_DISABLED`；不构造
   `AdvisoryIngress`、provider、worker、`AdvisoryDbFence`、完整
   `AdvisoryAdmissionWriter`，不执行额外 Advisory SQL/SAVEPOINT，也不要求 Pack-B
   capacity/timeout config。若不能建立合法 disabled classification，则 INSERT 不覆盖
   server default，durable safe fallback 为 `UNSTAGED`。上述 accounting field 均不进入
   Evidence hash/payload，DISABLED Evidence 永不补绑 experiment/pair/arm。
3. 仅当 startup epoch 已由另行批准的 activation boundary 冻结为 Gate A active 且
   所需 Pack-B config 完整时，Host 才构造 `AdvisoryAdmissionWriter` 与
   `AdvisoryDbFence`。步骤 1 的 explicit core flush 成功且 session healthy 后，G2 caller
   才能调用 **immediate non-blocking try-acquire**。持该 connection 时禁止 queue、await
   或 timeout-based token wait，也禁止为取得 token 再开第二 connection。try-acquire 失败
   则 **zero Advisory SQL + zero SAVEPOINT**，保留 G2/Evidence outer transaction；Evidence
   保持 `UNSTAGED` 并沿既有 deterministic unbound-failure accounting；需要 completeness
   的 Gate A fail closed。
4. try-acquire 成功后才调用 `session.begin_nested()`；调用前 session 必须无 pending
   G2/Evidence/Advisory state。SQLAlchemy 会在 `begin_nested()` 前无条件 flush pending state，
   故任何依赖 implicit pre-SAVEPOINT flush、或把 token try 放进 nested context 内的实现均
   违反本 ordering。writer 随后在**同一外层 transaction 内的 nested SAVEPOINT**执行全部
   Advisory work：timeout capture/apply/restore、一次 PostgreSQL admission clock、完整 seed
   construction、canonicalization/digest、config/experiment/pair/arm binding、snapshot、
   Invocation、FK/constraints 与 `UNSTAGED -> INVOCATION_CREATED`。
5. caller-owned path 只允许 SAVEPOINT 内 transaction-local `statement_timeout` 与
   `lock_timeout`：改变前读取 exact effective values；成功路径在 `RELEASE SAVEPOINT` 前以
   `set_config(..., true)` 恢复并核对返回值。任一 restore error/mismatch 必须使该 SAVEPOINT
   rollback；PostgreSQL rollback-to-savepoint 自动撤销 SAVEPOINT 内的 `SET LOCAL`。禁止在
   caller-owned path 设置 `idle_in_transaction_session_timeout`，也禁止以 client task
   cancellation/connection invalidation 实现 Advisory transaction timeout。caller-owned
   `advisory_db_transaction_timeout` 只能作为 cooperative monotonic budget：在下一条 statement
   前拒绝继续；已开始的 SQL 由 server statement/lock timeout 收束。
6. token 在全部 SAVEPOINT work、outer commit/rollback 以及 caller-owned connection
   **exact-generation pool observation 与 caller-owned cleanup success 的 full predicate** 期间始终持有；SAVEPOINT
   release、outer transaction completion、进入 `finally`、开始 `close()` 或 ref publication
   均不得释放。两种 activation 路径都不在 DB resource 下调用 provider，不写
   TradePlan/economic table。
7. active path 任一 Advisory-only exception 必须由 nested transaction 捕获并 rollback 到
   SAVEPOINT；不得污染、标记 rollback-only 或重新抛出到外层 G2 transaction。随后可在
   **第二个独立 nested SAVEPOINT** 只写常量终态
   `ADMISSION_FAILED_FINAL / ADMISSION_STAGING_FAILED_UNBOUND / NO_LONG_UNBOUND`。
   该 best-effort terminal write 再失败时也只 rollback 自己；外层仍可提交，Evidence
   保持 `UNSTAGED`。§8.3 冻结 restart 解释。
8. `session.begin()` 完成 commit/rollback 后，G2 caller 仍拥有 session 与 connection
   return。G2/core owner 负责等待 §20.3 的 authoritative pool event 或 completed explicit
   invalidation/discard，再 disposition token；unknown cleanup 绝不回补 available capacity。
   `AdvisoryDbFence`/writer 不得提前释放或取得 outer transaction ownership。随后
   `persist()` 返回 typed result（含 frozen `AdvisoryWorkRef`，若 admission 成立）。
9. `EventRuntime` 仅在 `persisted=true` 且持有 ref 后，调用 Host-owned
   `AdvisoryIngress.post_commit_offer(ref)`。
10. `post_commit_offer` 使用 non-blocking `put_nowait`/equivalent；consumer 只收到 ref。

**Phantom proof**：queue 只在 commit 后被触达；staging 失败（savepoint 回滚，§8.3）或
transaction 失败时 ref 不存在，步骤 7 永不执行 ⇒ 不存在「queue 已看见但 DB 不存在」
的 phantom advisory work。Capture Anchor 可能仍按 accepted contract durable，但它没有
formal Evidence/invocation，Advisory recovery 必须忽略它。

**Crash-gap proof**：commit 成功而进程在 enqueue 前死亡时，`ADMITTED` invocation 已
durable；restart scan 恢复**同一** invocation，绝不创建「全新 decision」（§15）。

### 8.3 Admission staging failure polarity（相对旧 draft 的核心变更）

Admission staging 属 critical provenance infrastructure，但其失败**不得**摧毁 durable
G2 market truth。FIX-01 的错误是把 `RECOVERY_REQUIRED`、完整 seed 与 accounting
preparation 放在 SAVEPOINT 外。FIX-02 冻结的最小 authority 仍是
`edge_opportunity_evidence` 上的 Advisory accounting extension，但把边界收紧为：

```text
advisory_admission_state =
  LEGACY_PRE_I2 | UNSTAGED | GATE_A_DISABLED |
  INVOCATION_CREATED | ADMISSION_FAILED_FINAL
advisory_admission_reason_code
advisory_treatment_participation nullable
advisory_admission_seed_version
advisory_admission_seed_digest
advisory_admission_seed (canonical JSONB)
advisory_decision_invocation_id nullable
```

- `LEGACY_PRE_I2` 只标识 migration 前已经存在的 Evidence；永不被 post-hoc 纳入
  Gate A。`UNSTAGED` 是 migration 后每个新 formal Evidence 的 schema-default first
  marker，表示「Advisory classification/seed/Invocation 尚未原子完成」，不是 Invocation、
  不是 provider work、也不是某个 experiment/arm 的成员。
- 完整 `AdvisoryAdmissionSeed` 只能在第一 nested SAVEPOINT 内构造和持久化。成功时
  它包含 exact Evidence identity、resulting G2 state、config epoch、experiment/pair/arm、
  provider/model、全部 version literals，以及 §17 的单次 DB clock/deadline；与 snapshot、
  Invocation、`INVOCATION_CREATED` 同 SAVEPOINT 原子提交。seed 不进入 `evidence_hash`，
  不改写 SE-02A Evidence identity/immutable payload。
- seed construction/canonicalization/digest/config binding/optional persistence 任一失败：
  第一 SAVEPOINT 全部 rollback，故无 partial seed、snapshot、Invocation、Attempt 或
  AIDecision。第二 SAVEPOINT 若成功，只写无需 seed/config/deadline 的 constant terminal
  `ADMISSION_FAILED_FINAL / ADMISSION_STAGING_FAILED_UNBOUND / NO_LONG_UNBOUND`；若失败，
  outer commit 后 durable fact 为 `UNSTAGED`。
- restart 对 `UNSTAGED` 的唯一合法动作是以固定 reason 原子转为同一
  `ADMISSION_FAILED_FINAL / ...UNBOUND / NO_LONG_UNBOUND`。**禁止**重新构造 seed、读取
  current config/experiment/provider/model、补造 deadline 或创建 Invocation。若 terminal
  update 因 DB failure 不能 commit，状态继续是 `UNSTAGED`，Gate A readiness 保持
  `FAIL_CLOSED`，下次 restart/reconciler 只重试同一常量 terminalization。
- `UNSTAGED` / `...UNBOUND` 是明确的 completeness hole：因 experiment binding 未 durable，
  不得伪造 `experiment_id/pair_id/arm_id`，也不得混入任一 arm 的 ordinary denominator；
  必须进入独立的 `unbound_eligible_admission_failure` accounting/health count，并使相关
  Gate A evidence completeness 与任何未来 Gate C evaluation fail closed。正常成功的
  treatment 仍按 Invocation 记账；正常 disabled 的 formal Evidence INSERT 直接写
  `GATE_A_DISABLED`，不经过 writer/fence/SAVEPOINT。
- 没有 formal Evidence 的 G2 event 不创建 accounting row；其非资格由 accepted
  qualifying facts + Evidence 缺席共同确定，不伪造 Evidence。
- process-local counter 仅是 health telemetry，不是 coverage authority。
- 不调用 provider（Invocation 不存在）；不传播为 safety/protection
  sibling cancellation；不影响 Protection / Core Host readiness。
- 外层 transaction 在 staging 之后失败：整体（G2 + Evidence + advisory）原子回滚，
  无 phantom、无半提交。
- Gate A `DISABLED` 时 startup classification 是 current epoch 的 immutable literal；
  不构造 provider/consumer/worker、`AdvisoryDbFence` 或完整
  `AdvisoryAdmissionWriter`。existing formal Evidence INSERT 直接写
  `GATE_A_DISABLED`，因此没有 separate optional writer failure。若分类不能合法冻结，
  column 保持 DB default `UNSTAGED`；不得临时查 mutable config、不得补写 experiment/pair/arm。
  从 `DISABLED` 到 Gate A active 必须经过另行授权的 activation boundary 并创建新的
  explicitly frozen runtime epoch，禁止 same-epoch silent in-place activation。

**理由（任务 §12 逐问回答）**：

| 问题 | 裁定 |
|---|---|
| Evidence + accounting + Snapshot + Invocation 能否合法同 transaction？ | 能 —— active path 的 base Evidence 先取 schema-default `UNSTAGED`；全部 Advisory accounting + seed + Snapshot + Invocation + `INVOCATION_CREATED` 在 SAVEPOINT 内原子；SAVEPOINT 失败只留下 `UNSTAGED` 或 constant unbound terminal。DISABLED path 只有原 Evidence INSERT + literal `GATE_A_DISABLED`，无 Snapshot/Invocation |
| 是否不当扩大 Scanner/G2 authority？ | 否 —— G2 formal transaction 只是 **atomicity host**；admission 的 identity/policy authority 属 Host-composed、config-gated 的 `AdvisoryAdmissionWriter`；writer opt-in 注入，Gate A disabled 时 G2 路径不变 |
| AI advisory persistence 是否污染 Scanner core responsibility？ | 旧 draft 会（staging 失败回滚 G2 facts ⇒ AI infra 失败摧毁 market truth）；savepoint 方案消除该污染：Scanner/G2/Edge 真值独立于 AI infra 健康（invariant 12） |
| rollback 能否产生 phantom advisory work？ | 不能（§8.2 phantom proof）；Evidence 仍以 `UNSTAGED` 或 constant unbound terminal 可查询，且永不由 mutable config 补绑 |
| DB commit 成功而进程在 enqueue 前崩溃？ | 可能；由 durable `ADMITTED` + restart scan 恢复（§15），process-local queue publication 不是 authoritative delivery fact |
| 谁拥有 admission creation？ | active Gate A 的 `AdvisoryAdmissionWriter` 由 Host 在 `_compose_services` 构造且仅在 config 完整时注入；G2 caller 继续拥有 outer transaction/session/final connection return，writer 只拥有 token/capability 与 Advisory operations。DISABLED 只消费 frozen startup literal，不存在 admission writer |

## 9. Evidence Revision Binding（Critical Question A）

### 9.1 两个必须区分的概念

```text
A. Admission Evidence = 在 live Advisory admission 的 G2 formal transaction 中
   staged 的那份 exact、durable、immutable Evidence revision N
   （opportunity_id + evidence_id + evidence_revision + evidence_hash
    + feature_snapshot_hash）。

B. SE-02D-I02 current canonical Evidence head = 在某个 REPEATABLE READ READ ONLY
   快照内对全量可见 Evidence revision chain 折叠后选出的 canonical head ——
   这是 Edge / Expectancy aggregation projection 的概念。
```

**裁定**：

1. Advisory admission 绑定 **A**，永不绑定 B。绑定在成功 nested SAVEPOINT 中同时写入
   Evidence 行的 `AdvisoryAdmissionSeed`、Invocation 与 Decision Snapshot。身份字段
   （全部进入 `decision_invocation_id` /
   provider input provenance / `input_binding_digest`）：
   - `opportunity_id`（bound）
   - `evidence_id`（bound）
   - `evidence_revision`（bound）
   - `evidence_hash`（bound）
   - `feature_snapshot_hash`（bound；旧 draft 漏，本版纳入）
2. canonical Evidence head（B）是**事后**可能随新 revision 变化的聚合视图概念；
   AdvisoryIngress 在 admission、consume、finalize 任何时点都**不**查询、**不**依赖 B。
3. **An already-created Invocation must never silently switch to a later canonical
   Evidence head**：Invocation 的 Evidence binding 是 admission transaction 写入的
   immutable facts；不存在任何代码路径把 invocation 的绑定改写为 chain 的另一节点。
   supersede 的后果是旧 Invocation 变 stale（§10），而不是换绑。

### 9.2 一致性说明

因为 admission 与 Evidence revision N 的持久化发生在**同一 transaction**，admission
时「durably visible 的 revision」恰为 N 本身；不存在「admission 时看到 N、事后发现
canonical 已是 N+1」的 admission 竞态。canonical head 的漂移只发生在 admission 之后，
其唯一合法影响是使旧 Invocation stale（§10）。

## 10. Evidence Supersede Contract

场景：Invocation 已按 Evidence revision N admission；随后 revision N+1 durable 且
supersedes N（当前 live G2 路径恒写 revision 1，N+1 今天不会由 runtime 产生；但
schema/SE-02A 契约与 I02 折叠语义使该场景成为必须显式设计的边界）。

### 10.1 冻结规则

1. **旧 Invocation 永久绑定 N**：identity、`input_binding_digest`、snapshot、
   experiment/pair/arm binding 全部 immutable。**Forbidden**（任务 §10 红线）：
   把旧 Invocation 从 N 改写到 N+1；改写 input-binding digest；把同一 Invocation
   当作「一直以 N+1 为输入」复用；post-hoc experiment rebinding。
2. **旧 Invocation 的命运 = stale / non-actionable**：在任一检查点（pre-enqueue /
   dequeue / pre-provider / during-provider→finalizer / pre-finalization）检测到
   「同 `opportunity_id` 存在 revision > N 的 durable Evidence row（或等价的
   supersedes 链事实）」⇒ 当前 cycle 尚无 terminal-producing Attempt 时（包括有历史
   Attempt 的 retry gap）该 Invocation terminalize 为
   `STALE_DECISION / EVIDENCE_SUPERSEDED_BEFORE_PROVIDER`；当前 Attempt-start 已 commit 时使用
   `STALE_DECISION / EVIDENCE_SUPERSEDED`。前者当前 cycle 新增 provider call = zero；
   valid response 只留 attempt audit、不能赢 final（若已调用）。检测方式 = 直接
   durable 查询 `edge_opportunity_evidence`（按 `opportunity_id` 取 max
   `evidence_revision`），**不**调用 `aggregation_snapshot.py`。用于终态胜者或
   未来经济消费的检查还必须遵守下述共享锁，普通无锁预检仅是早停优化。
3. **N+1 可另立新 Invocation**：若 N+1 本身经 accepted `qualifies()` 规则在一个
   G2 formal transaction 中 staged（即它是 qualifying 的），则 §8 的 admission 规则
   对它自动适用 —— 同一 experiment 下，每个 exact Evidence revision 至多一个
   `REAL_AI_TREATMENT` invocation。新 Invocation 是**全新**的
   invocation/pair/identity（`input_binding_digest` 含 N+1 的
   evidence_id/revision/hash），与旧 Invocation 无任何改写关系。若 N+1 不是
   qualifying capture（如仅作为重检/修订被其他已接受路径写入），则不产生新
   Invocation —— admission 只认 §8.1 的 qualifying record。
4. **PRE-01A-D1 §10 依据**：「A new evidence revision … creates a new
   unit/invocation and may not reuse the old result」—— 本契约是该冻结语义在
   live ingress 路径上的落地。
5. **共享 PostgreSQL serialization authority（关闭 TOCTOU）**：
   - lock target = 被 Invocation 绑定的 exact Evidence row N，即
     `edge_opportunity_evidence(opportunity_id, evidence_revision=N)`；它是现有 Evidence
     chain authority，不创建第二个 opportunity/identity authority。
   - 所有 accepted Evidence supersede writer（当前即 `append_evidence_revision`）在写 N+1
     前必须先 `SELECT` immediate predecessor N `FOR UPDATE`，在持锁时重验
     same-opportunity、adjacent revision 与 existing head，再 insert N+1，持锁到
     commit/rollback。
   - Advisory attempt-start、finalizer，以及未来 Gate B 对该 final 的经济消费，
     均必须先 lock bound Evidence N `FOR UPDATE`，**然后** lock Invocation，
     再 lock/update Attempt；持锁后重读 same-opportunity max revision / supersedes
     chain 和 Invocation final fields。全部路径的锁顺序统一为
     `Evidence N -> Invocation -> Attempt`，禁止反序。
   - 这些事务使用 PostgreSQL `READ COMMITTED`：等待 N row lock 后的下一条
     statement 必须重读新 snapshot。若实现改用更高 isolation 并遇到
     serialization failure，则整个 transaction 失败并在原 deadline 下有界重试；
     禁止使用旧 snapshot 继续 final。
   - 锁仅由 PostgreSQL transaction 在 commit/rollback 释放；Python lock 不参与该不变量。
   - 序列化证明：若 N+1 先获得 N 锁并 commit，finalizer 后获锁后必须
     看见 N+1 并将 N 终态化为 `EVIDENCE_SUPERSEDED`；若 finalizer 先获锁并
     commit，N+1 writer 才能继续，属于下述合法 final-then-supersede。
   - 外部语义依据：PostgreSQL 官方
     [Explicit Locking](https://www.postgresql.org/docs/current/explicit-locking.html) 与
     [Transaction Isolation](https://www.postgresql.org/docs/current/transaction-iso.html)；
     前者定义 `FOR UPDATE` 等待/事务结束释放，后者定义
     `READ COMMITTED` 每条 command 的新 snapshot。
6. **Final-then-supersede 语义**：N 在当时 current 时完成的 final 及其
   Invocation/Attempt/AIDecision/attribution 永久 immutable audit，N+1 不回写它们。
   N+1 Evidence row 及其 `supersedes_evidence_id=N.evidence_id` 就是「final 之后已被
   supersede」的 durable authority；不增加可漂移的 `actionable=true/false`
   第二权威。任何未来 Gate B 消费者必须在同一 Evidence N lock 下重验
   no-higher-revision，并在同一 transaction 内提交经济授权；否则旧 final
   即 `NON_ACTIONABLE_FOR_FUTURE_ECONOMIC_USE`。Gate A 仍 non-economic，D2 不实现
   Gate B。
7. **生命周期覆盖（任务 §10 清单）**：
   - before queue/retry publication：offer 前置检查 ⇒ 不入 queue，以
     `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` terminalize；
   - while queued：dequeue durable re-read 后以
     `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` terminalize，当前 cycle 新增 provider call = zero；
   - before provider call：当前 cycle 的 attempt-start transaction 拒绝，以
     `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` terminalize，当前 cycle 新增 provider call = zero；
   - during provider call：best-effort cancel（非 authority）；response 后 finalizer
     durable re-read ⇒ `STALE_DECISION / EVIDENCE_SUPERSEDED`；
   - after provider result / before finalization：finalizer transaction 判 stale，
     valid response 只留 attempt audit，不能赢 final；
   - final 已存在后 supersede 发生：final 不变；新 Evidence chain 事实使它
     对任何未来经济消费 non-actionable，N+1 仍可按规则新 admission。
8. **Denominator 边界**：superseded revision N 的 pair 在实验分母中如何计数
   （如是否按 predeclared exclusion rule 排除）是 SE-02D / Gate C aggregation
   contract 的问题，D2 不决定、不发明规则（§23.3）。

## 11. Consumer / Shadow Safety Boundary

Gate A consumer 是新的最小 `ShadowAdvisoryDecisionPath`，不是第二套 G3。它只拥有：

- read-only loading of invocation / snapshot / evidence / durable state facts；
- provider adapter；
- deterministic validator（复用/适配 `DecisionValidator` 语义 + PRE-01A §7.3 校验清单）；
- attempt writer、finalizer 与 attribution append writer。

它在 constructor/type boundary 上**不得拥有**：

- `TradePlanManager`；`persist_trade_plan` callable；`SystemRiskGate`；
  `PaperExecutionService`；Position/Account/Ledger/Protection mutation repository；
  `G3Workflow`。

允许写入的 table allow-list 仅为：

```text
advisory_decision_invocations
advisory_decision_attempts
decision_snapshots (extended rows)
ai_decisions (optional invocation/attempt-linked normalized result rows)
edge_attribution_events (AI lineage only)
```

Gate A tests 必须监视并证明 `trade_plans`、scenarios、intents、orders、fills、
positions、trades、accounts、ledger、outbox economic events 全部零新增/零修改。
不能用「后面的 Risk 会挡住」作为安全证明 —— Shadow path 本身必须 non-economic。

## 12. Identity Model

### 12.1 Construction order

所有 hash 使用 versioned canonical JSON（sorted keys、UTC timestamps、finite numeric
policy）；禁止 Python `repr()`、process hash、provider response 参与identity；禁止
未转义 `"|".join(...)` 之类非单射编码作身份判断（项目 identity 铁律）。

1. `snapshot_payload_hash = H(snapshot_contract_version, canonical_snapshot_payload)`。
2. `snapshot_id = H("advisory-snapshot-v1", opportunity_id, evidence_id,
   snapshot_payload_hash)`。
3. `input_binding_digest = H(binding_version, opportunity_id, evidence_id,
   evidence_revision, evidence_hash, feature_snapshot_hash, snapshot_id,
   snapshot_payload_hash, state_version, config_version, family_id/version,
   instrument_id, market_type, advisory_config_epoch_id, decision_requested_at,
   deadline_duration_ms, deadline_policy_version, decision_deadline_at)`。所有时间字段使用
   §17.1 的 canonical UTC serialization。
4. `experiment_id = H(experiment_definition_version, canonical_experiment_definition)`。
5. `pair_id = H("pre01a-pair-v1", experiment_id, input_binding_digest)`。
6. `baseline_arm_id = H("pre01a-arm-v1", pair_id, "WITHOUT_AI_BASELINE")`。
7. `treatment_arm_id = H("pre01a-arm-v1", pair_id, "REAL_AI_TREATMENT")`。
8. `decision_invocation_id = H("advisory-invocation-v1", experiment_id, pair_id,
   treatment_arm_id, input_binding_digest, prompt_version, schema_version,
   treatment_version, configured_provider_id, configured_model_id)`。
9. `attempt_id = H("advisory-attempt-v1", decision_invocation_id, attempt_number)`。
10. logical final-result identity = `decision_invocation_id`；它对成功与失败均唯一。
    仅当终态 Attempt 产生 normalized AIDecision 时，
    `decision_id = H("advisory-final-v1", decision_invocation_id)` 才存在；其
    origin 由强制 `attempt_id` FK 证明，不从 digest/timestamp 推断。

### 12.2 Authority and idempotency

- `AdvisoryAdmissionWriter` 创建 invocation identity（admission transaction 内）；
  provider/model 只被记录，不能回写 identity；provider 永不是本地 identity authority。
- Evidence 行的 `AdvisoryAdmissionSeed` 只存在于 staging **成功**的原子结果；reconciler
  必须重算 digest 并与 seed digest 相等，否则 invariant conflict / fail closed。staging
  失败的 `UNSTAGED` / unbound terminal 没有合法恢复输入，禁止用 current config 补值。
- same immutable facts 重试/重放得到同一 invocation；相同 hash 为 idempotent，不同
  content 为 invariant conflict 并 fail closed。
- retry 只增加 attempt row，绝不增加 invocation / final identity。
- provider request/response ID（若有）记录在 attempt；不存在时为 `NULL/UNKNOWN`，
  不得伪造。
- 每个 hash 的 version literal 属 I2 实现契约，须在实现窗口逐字冻结；arm identity 的
  domain/version literal 已由 CLAR-01 冻结为 `pre01a-arm-v1`，不得复用
  `pre01a-pair-v1` 或把 `pair_id` 当动态 domain（教训：
  SE-02D-D01 `uncertainty_method_version` 曾缺失 literal ⇒ Human Design Clarification
  补齐；D2 把该项列入 I2 实现前置核对清单）。

## 13. Experiment / Pair / Arm Binding

### 13.1 Experiment authority

Host startup config 必须提供完整 canonical experiment definition，并由确定性代码验证
`experiment_id`。definition 至少冻结：placement（C. Trade Decision only）、baseline
policy/version（`ALL_ELIGIBLE_LONG_SHADOW_V1`）、treatment version、exact configured
provider/model、prompt/schema/input-binding/snapshot versions、retry/deadline/cost
policy values/versions、horizons/metrics definition、activation level。

Host config 在一个 process lifetime 内 immutable。旧 invocation 自包含完整
binding/digest；restart 恢复它时不使用新 config 重配 pair/arm/model。若
config/definition 变化，必须产生新 `experiment_id`（即新实验 lineage，与旧 lineage
无 identity 冲突，PRE-01A AC-23）。

### 13.2 One Evidence revision, one explicit binding

- 每个 exact Evidence revision 在一个 experiment 中至多一个 `REAL_AI_TREATMENT`
  invocation（§10.3）。
- `pair_id` 在 provider call 前、outcome 前冻结。
- baseline arm 固定为 `ALL_ELIGIBLE_LONG_SHADOW_V1 / WITHOUT_AI_BASELINE`；成功的
  Evidence admission SAVEPOINT 在任何 provider 结果前原子持久化 seed 中的
  `baseline_policy_version` 与 deterministic
  `baseline_participation=PARTICIPATE_LONG`，使 baseline arm 不是事后推导的隐式标签。
  它不调用 provider、不产生 TradePlan，且不在 AI failure 时升级为 fallback。
- treatment arm 固定为 `REAL_AI_TREATMENT`。
- arm 不得由 response、confidence、盈利结果、retry outcome 或 latency 事后选择。
- Gate A active + qualifying 且 staging 成功时，`REAL_AI_TREATMENT` arm 也在 Evidence seed 中
  pre-assigned；后续只记录该预分配 arm 的 participation outcome：
  admission staging failure 则以 `UNSTAGED` / `ADMISSION_STAGING_FAILED_UNBOUND`
  进入独立 completeness-hole accounting，永不 post-hoc 绑定该 arm；capacity blocked、
  deadline-before-provider、Evidence superseded、provider failure 均为
  `NO_LONG` + exact reason；valid normalized
  provider result 仅在 direction = `LONG_BIAS` 时为 `PARTICIPATE_LONG`，
  `WAIT/SHORT_BIAS` 为 `NO_LONG`。这些是 per-unit operational facts；
  superseded unit 是否进入 Gate C denominator 仍由 SE-02D 决定。
- `LEGACY_PRE_I2` / `UNSTAGED` / `GATE_A_DISABLED` 不被事后改标为 treatment；新配置只能
  创建新 config epoch / experiment lineage，不能回填历史 Evidence。
- baseline result 的未来聚合可引用同一 pair/Opportunity 的 accepted SE-02C outcome；
  I2 不复制 Outcome calculator，也不创建第二套 execution account。
- **SE-02D-I02 不解决 PRE-01A experiment identity**：SE-02D 的 population grouping
  （PopulationKey = family/version/instrument/market/source identity/contract version，
  D01 冻结）与 PRE-01A 的 experiment/pair/arm identity 是两套正交身份；二者不得
  混同，也不得从 AI output 或 population 归属 post-hoc 推导 arm。

## 14. Persistence / Transaction Contract

### 14.1 Invocation lifecycle

```text
ADMITTED -> ACTIVE -> RETRY_PENDING -> ACTIVE -> FINAL
ADMITTED/ACTIVE/RETRY_PENDING -> FINAL (failure/cancel/stale/expired/capacity)
```

本修复**删除 durable `QUEUED`**。Invocation 在 process-local queue ref 存在时仍为
`ADMITTED`；queue 只是 bounded wake-up/dispatch mechanism，不是 durable authority。
consumer 在任何 provider I/O 前以 §10.1 共享锁顺序原子执行
`ADMITTED/RETRY_PENDING -> ACTIVE` 与 Attempt insert。状态是 durable execution state，
不是新 `DecisionStatus`。

“dispatch/retry cycle”从一个 frozen `AdvisoryWorkRef` 被 initial offer、retry re-offer 或
recovery re-dispatch 开始，到该 cycle 的 Attempt-start transaction 成功 commit 为止。
`RETRY_PENDING` 可已有一个或多个历史 Attempt；在下一个 Attempt-start commit 之前，
它处于 **retry gap**。此时可以直接 `RETRY_PENDING -> FINAL`，但不得将旧
Attempt 误作新终态的 provenance。初次、retry 与 recovery 的 ref publication 共用§16
同一 bounded queue；不建立第二 dispatch path。

### 14.2 Exactly-one authoritative terminal result

Invocation row 是**唯一 logical final-result authority**，不再以「查询最新 Attempt/
`ai_decisions` timestamp」推断结果：

```text
state = FINAL
final_status                 NOT NULL
final_reason_code            NOT NULL
finalized_at                 NOT NULL
final_attempt_id             NULLABLE only for named no-terminal-producing-Attempt terminals
final_decision_id            NULLABLE when no normalized AIDecision exists
```

DB constraints 冻结：

1. `state=FINAL` iff `final_status/final_reason_code/finalized_at` 三者全非空；
   non-FINAL 时全部 final fields 必须为 NULL。
2. `final_attempt_id` 含义是「其 lifecycle/result **直接产生 authoritative 终态结果**
   的 durable Attempt」（失败终态也可有）；它不是 latest historical Attempt，也不是
   Invocation 中任一曾经发生的 Attempt。
   非空时必须通过 composite FK `(decision_invocation_id, final_attempt_id)` 指向同
   Invocation 的 Attempt。对 FINAL Invocation，DB CHECK 必须实现双向约束：
   `final_attempt_id IS NULL` **IFF** exact `(final_status, final_reason_code)` 属于下方唯一
   authoritative no-terminal-producing-Attempt pair set；不得使用 status wildcard、
   reason-only whitelist 或 generic `CAPACITY_BLOCKED` reason。该 CHECK 不断言「Invocation
   中没有任何 Attempt row」；历史行仍由 `advisory_decision_attempts` 查询。属于该
   set 时 `final_decision_id` 也必须为 NULL。不需要 CHECK subquery、trigger、新 Invocation
   column 或 fake Attempt。
3. 新 Advisory `AIDecision` row 必须同时持有
   `decision_invocation_id` 与 `attempt_id`；composite FK 证明 Attempt 属于同一
   Invocation。`AIDecision` 只表示已成功 normalized 的 provider result；
   transport/auth/refusal/malformed/pre-provider outcome 只保留 Attempt/final reason，不伪造
   AIDecision。
4. `final_decision_id` 非空时，通过 deferred composite FK
   `(decision_invocation_id, final_decision_id, final_attempt_id)` 指向同 Invocation、同
   final Attempt 产生的 `AIDecision`；因此 `final_decision_id != NULL`
   必然推出 `final_attempt_id != NULL`。该 FK 与 AIDecision 反向 FK 为
   `DEFERRABLE INITIALLY DEFERRED`，使同一 finalizer transaction 可原子提交。
5. terminalization 与 final Attempt update、可选 AIDecision insert、attribution append 必须
   同一 transaction commit；不得先写 final fields 再补链接。
6. `finalized_at` 来自 finalizer transaction 的 PostgreSQL server clock，不使用
   application wall clock，也不用 timestamp 排序选 winner。只有终态获胜 Attempt
   的 normalized result 可插入 Advisory `ai_decisions`；中间 retry/non-winning
   normalized output 只留在 Attempt audit，不占用 final-decision unique linkage。

Current-cycle terminal provenance 是唯一 boundary，必须区分：

- **State A — Zero Attempt History**：同 Invocation 从未成功 commit Attempt row。无
  terminal-producing Attempt，`final_attempt_id=NULL`、`final_decision_id=NULL`；本 Invocation
  lifetime provider-call count 也为 zero。
- **State B — Retry Gap**：同 Invocation 存在一个或多个 immutable historical Attempt，但当前
  dispatch/retry cycle 尚未成功 commit 新 Attempt。若新的 external terminal predicate 在此时
  成立，则无 terminal-producing Attempt：`final_attempt_id=NULL`、
  `final_decision_id=NULL`。历史 provider calls 可以大于 zero，但当前终态化 cycle 的新增
  provider call 必须为 zero。历史 Attempt 保留并不得被链接为 `final_attempt_id`。
- **State C — Current Terminal-Producing Attempt Exists**：当前 cycle 的 Attempt-start
  transaction 已成功 commit。若该 Attempt 后续直接产生终态，`final_attempt_id`
  必须引用它；不能因 provider I/O 尚未开始、network call count 仍为 zero、queue phase
  名称或 Python wall-clock 位置而使用任何 `*_BEFORE_PROVIDER` reason。
- 当前 Attempt-start commit 后 deadline 才过期，即使 provider I/O 尚未开始，也必须使用
  `STALE_DECISION / DEADLINE_EXPIRED`；`final_attempt_id` required，`final_decision_id=NULL`，
  除非 D2 finalizer contract 下已经合法存在该 Attempt 的 accepted normalized artifact。
  `BEFORE_PROVIDER` 在 reason 中只表示「当前 dispatch/retry cycle 本应创建的 durable
  provider Attempt 尚不存在」，不表示 Invocation lifetime 从未调用 provider。

唯一 authoritative no-terminal-producing-Attempt pair set（State A 与 State B 共用）：

| Terminal class | `final_status` | `final_reason_code` | `final_attempt_id` | `final_decision_id` | New provider calls for terminalizing cycle |
|---|---|---|---|---|---|
| deadline expired before durable Attempt | `STALE_DECISION` | `DEADLINE_EXPIRED_BEFORE_PROVIDER` | NULL | NULL | ZERO |
| queue rejected | `CAPACITY_BLOCKED` | `ADVISORY_QUEUE_REJECTED` | NULL | NULL | ZERO |
| Advisory DB capacity unavailable | `CAPACITY_BLOCKED` | `ADVISORY_DB_CAPACITY_UNAVAILABLE` | NULL | NULL | ZERO |
| Evidence revision superseded | `STALE_DECISION` | `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` | NULL | NULL | ZERO |
| Opportunity eligibility lost or market freshness lost | `STALE_DECISION` | `OPPORTUNITY_STALE_BEFORE_PROVIDER` | NULL | NULL | ZERO |
| activation genuinely disabled | `STALE_DECISION` | `ACTIVATION_DISABLED_BEFORE_PROVIDER` | NULL | NULL | ZERO |
| immutable Decision Snapshot / input-binding invalid | `STALE_DECISION` | `BINDING_INVALID_BEFORE_PROVIDER` | NULL | NULL | ZERO |
| activation enabled but invocation-bound experiment/config definition mismatched | `STALE_DECISION` | `EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER` | NULL | NULL | ZERO |
| shutdown terminal | `INVALID_SCHEMA` | `SHUTDOWN_BEFORE_PROVIDER` | NULL | NULL | ZERO |

`BINDING_INVALID_BEFORE_PROVIDER` 的唯一语义类是：当前 cycle 的 terminal-producing Attempt
尚不存在时（可有历史 Attempt），对 immutable
Decision Snapshot / `snapshot_payload_hash` / `input_binding_digest` / bound Evidence hashes 的
deterministic integrity check 证明 binding corrupted、invalid、misrouted 或 incompatible。它不是
market staleness、capacity、activation、provider 或 DB-fence failure。

`EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER` 的唯一语义类是：当前 cycle 的 terminal-producing
Attempt 尚不存在（可有历史 Attempt）、activation 仍 enabled，但 Invocation 已绑定的
experiment definition/config epoch 与 current authoritative
activation/config definition 不兼容。若 current state 实际为 DISABLED，只能使用
`ACTIVATION_DISABLED_BEFORE_PROVIDER`。

除上述两项新 narrow literal 外，其余 reason 均为 CLAR-01 retained literal。queue 与 DB
capacity 保持两个 exact pair；Opportunity eligibility lost 与 market freshness lost 明确共享
`OPPORTUNITY_STALE_BEFORE_PROVIDER`。无法可靠提交 terminal row 的 DB/lock/fence failure 保留原
durable state 并 fail closed，交由 restart 在原 deadline 下重裁；它不是额外
no-terminal-producing-Attempt pair。

Attempt-origin / success mapping（不构成第二份 no-terminal-producing-Attempt whitelist）：

| Terminal class | `final_attempt_id` | `final_decision_id` | Authority result |
|---|---|---|---|
| successful valid AI decision | required | required | `VALID / VALID_PROVIDER_DECISION` |
| refusal | required | NULL | `INVALID_SCHEMA / REFUSAL` |
| auth/permission failure | required | NULL | `INVALID_SCHEMA / AUTH_PERMISSION` |
| retry exhaustion | required（last terminal-producing Attempt） | 仅当该 Attempt 产生可持久 normalized result 时 required，否则 NULL | exact last failure + `RETRY_EXHAUSTED` |
| shutdown cancellation with ACTIVE provider Attempt | required | NULL | `INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT` |

normalized-but-business-invalid 或 provider 返回后才变 stale 的 final 可持有
`final_decision_id`，但其 actionability 仍由 `final_status/reason` 与 §10 supersede
revalidation 决定；AIDecision 存在不等于 actionable。

Retry exhaustion 不属于 State B：若最后一个 completed Attempt 的 result 本身使 joint retry
policy 决定不再 retry，该 last Attempt 就是 terminal-producing Attempt，必须写入
`final_attempt_id` 并保留 `RETRY_EXHAUSTED` 语义。只有 Invocation 已进入 `RETRY_PENDING`
后，在下一 Attempt 创建前发生一个**新的外部 terminal condition**，才是 retry gap。

### 14.3 Attempt start（provider call 之前必须 durable）

consumer 在 provider call **之前**用一个 transaction：

1. lock bound Evidence row `FOR UPDATE`；
2. lock invocation `FOR UPDATE`；
3. 若 final 已存在，直接 fence，不调用 provider；
4. 持 Evidence 锁重验 supersede，再重验 DB-clock deadline / other stale /
   activation / budget；
5. 插入当前 dispatch/retry cycle 的 exact next attempt row（`STARTED`）并把 invocation 置
   `ACTIVE`；该 commit 是 retry gap 与 current Attempt 存在的唯一 durable boundary；
6. commit；
7. provider call 才可开始。

任何真实 provider call 都有先行 durable attempt provenance。

### 14.4 Winner atomicity

provider completion 的 finalizer 必须在一个 PostgreSQL transaction 中：

1. `SELECT ... FOR UPDATE` bound Evidence N；
2. `SELECT ... FOR UPDATE` invocation；
3. lock/update final-producing Attempt；
4. 检查 Invocation final fields 是否已存在；
5. 持 Evidence 锁重读 max revision，并按固定顺序执行 duplicate →
   DB-clock deadline → binding/stale（含 supersede）→
   provider/schema → business validation（PRE-01A §8.2 precedence）；
6. 持久该 Attempt 的 response/error/usage/timestamps/validation/late facts；
7. 若 retryable 且 budget/deadline 仍允许，只置 `RETRY_PENDING`，不写 final；
8. 否则按 §14.2 可选插入 `AIDecision`、append attribution，并一次写入
   Invocation 的五个 final fields；
9. commit。

Invocation row lock + final-field completeness constraints + optional
`ai_decisions.decision_invocation_id` unique constraint 是 durable winner fence。两个 concurrent completion、
retry/shutdown/restart race 中只有一个 transaction 能提交 authoritative final fields；loser attempt 写
`DUPLICATE_SUPPRESSED` / `LATE_RESULT` audit，绝不改写 winner。

Python lock、queue dedupe、TaskGroup、in-memory set 均不参与 winner correctness。
duplicate completion 不得产生第二个 final result；late result 只能 audit、不得替换
winner；restart 不得把同一 Invocation 变成新的 logical decision（PRE-01A AC-16/21）。

## 15. Crash Recovery

PostgreSQL 是 correctness authority；process-local queue publication 不是
authoritative delivery fact：

- commit 成功 + enqueue 前崩溃：`ADMITTED` invocation 已 durable ⇒ restart scan
  恢复同一 invocation（原 deadline、原 identity、原 budget），绝不创建新 decision。
- 该 durable 机制即 invocation 表自身的 state machine —— **不**新增 outbox 表、
  **不**引入通用 event bus / framework（最小机制原则）。
- restart 恢复规则：
  - Evidence accounting = `UNSTAGED`：不构造 seed、不读新 config、不补造 deadline；
    只原子 terminalize 为 `ADMISSION_FAILED_FINAL /
    ADMISSION_STAGING_FAILED_UNBOUND / NO_LONG_UNBOUND`；DB failure 时保持
    `UNSTAGED` 并使 Gate A fail closed；
  - final 已存在：永不 requeue；
  - `ADMITTED` 且未过期：按 durable ordering 分页填充 bounded queue，
    同 invocation；一次最多持有 capacity 个 ref，不建立 unbounded in-memory backlog；
  - `ACTIVE` 且 attempt 无 completion：原 attempt 记 `PROCESS_LOST/ABANDONED`；
    仅当原 joint budget 与 deadline 允许才创建下一 attempt；
  - `RETRY_PENDING`：按原 provider/model/input/deadline 继续；不重建 pair/arm。recovery 以
    同一 frozen ref 按 durable ordering 填充§16 bounded queue；若 re-offer 遭 REJECT NEWEST，
    它作为 retry-gap terminal 使用 `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`，
    `final_attempt_id=NULL`，历史 Attempt 保留；
  - 已过 deadline / Opportunity invalid / Evidence superseded / activation disabled：
    若当前 cycle 尚无 Attempt-start commit（包括 retry gap），按§14.2 相应
    `*_BEFORE_PROVIDER` pair terminalize，`final_attempt_id=NULL`，当前 cycle 新增
    provider call = zero；任何历史 Attempt 保留且不被伪链接。若当前 Attempt-start 已
    commit，按§14.2 Attempt-origin mapping 并引用 exact current Attempt。
- Core recovery/Protection 可先完成并诚实 ready；Gate A readiness 在 advisory
  recovery 完成前为 false。

## 16. Queue / Backpressure Contract

| 项 | 冻结策略 |
|---|---|
| owner | one `AdvisoryIngress` per `RuntimeHost`（Host-owned auxiliary） |
| capacity | positive finite explicit config；unset 时 activation disabled |
| item | frozen `AdvisoryWorkRef { decision_invocation_id, decision_deadline_at }` only；initial、retry continuation 与 recovery re-dispatch 共用同一 ref/queue |
| ordering | process-local queue 按 `(decision_requested_at, decision_invocation_id)` ascending；无 response-based priority；该顺序不是 durable correctness state |
| priorities | Gate A 只有 `NEW_SETUP` 一类；不得与 Position/Plan Review 混合 |
| enqueue | admission commit 后 initial offer，或 Attempt finalizer/recovery 持久 `RETRY_PENDING` 后 retry re-offer；均使用 post-commit `put_nowait` / equivalent，绝不 await queue space |
| full policy | **REJECT NEWEST**；不 DROP accepted item、不 COALESCE、不阻塞 producer |
| full durable result | same invocation 按 §14.2 原子 terminalize：`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`，`final_attempt_id=NULL`、`final_decision_id=NULL`；当前 terminalizing cycle 新增 provider call = zero。retry-gap 可有 historical Attempt/provider calls，但不得链接旧 Attempt 或伪造新 Attempt |
| accepted item | queue 一旦接受，不 silent drop；consumer/finalizer 或 restart 必须给出 durable terminal state |
| shutdown | close admission；offer 被拒（admission closed）⇒ invocation 保持 `ADMITTED`，由 restart recovery 处理；不等待新 slot |

REJECT NEWEST 的理由（含 PRE-01B-D1 先例）：scanner lane 已接受「full ⇒ reject
newest input + rejection counter + degraded」（D1 Backpressure Contract：missing a
new opportunity is fail-closed）；advisory 同型 —— Opportunity/pair/invocation
uniqueness 必须保留（coalesce 会合并两个 Opportunity，drop 会删除实验 denominator，
blocking 会反压 scanner/provider）。rejection 仍保留 exact invocation/pair audit。

**Queue rejection ≠ durable admission rejection**：durable admission rejection 发生在
admission transaction（staging 失败 / admission-time stale ⇒ 无 invocation）；queue
rejection 发生在 Invocation 已 durable 之后，可以是 initial offer，也可以是已有
historical Attempt 的 retry/recovery re-offer（⇒ 同 invocation terminalize，显式留在
denominator）。二者在 telemetry 与 durable state 上都必须可区分。

queue full handling 的 durable terminal transaction 若因 DB failure 未提交，invocation
保持原 state；这不是已完成的 rejection。Advisory 立即 fail closed，restart 按 durable
state 恢复并在原 deadline 下重新裁决。

精确 ordering / crash 语义（P2-01）：

1. DB commit 产生 `ADMITTED`；成功 `put_nowait` 不改 durable state。
2. consumer dequeue 只取得 ref；它必须先成功提交 §14.3 的
   `ADMITTED -> ACTIVE` + Attempt，才可调用 provider。
3. enqueue 前 crash、enqueue 后 crash、dequeue 后/claim 前 crash 均留下同一
   `ADMITTED`，restart 重建 ref；无法误认为已经开始 provider。
4. claim transaction DB failure 整体 rollback，Invocation 仍 `ADMITTED`，Attempt 不存在，
   provider call = zero。claim commit 后/provider 前 crash 则留 `ACTIVE` + `STARTED`
   Attempt，restart 按 `PROCESS_LOST/ABANDONED` 规则处理。
5. duplicate process-local refs 经 Invocation row lock/state check 被 fence；不会创建第二个
   concurrent Attempt。
6. queue full 时 ref 未进队，必须同步尝试上述 durable capacity final。
   若该 final commit 失败，诚实状态仍是 `ADMITTED`，subsystem fail closed；
   restart 不伪造历史 capacity result，而是按原 deadline/stale 再次 bounded offer。
7. retry/recovery re-offer 同样受该 capacity gate约束。若 full 时状态为 `RETRY_PENDING`，
   它处于 retry gap：按上表 pair terminalize，保留所有历史 Attempt/provider-call audit，
   `final_attempt_id=NULL`；不允许把旧 Attempt 链接为 terminal producer，也不允许为获得
   provenance 先插入新 Attempt。若 retry-gap capacity final commit 失败，诚实状态仍是
   `RETRY_PENDING`，restart 在原 deadline 下重裁。

无 durable `QUEUED`、无 coalescing（identity safety 未被形式化证明前禁止）。

## 17. Deadline / Cancellation Contract

### 17.1 Deadline authority（相对旧 draft 变更）

- clock authority = **PostgreSQL server clock**。第一 nested SAVEPOINT 在 exact
  Evidence 已 staged 后执行一次、且仅一次如下语义的 DB statement：
  `WITH admission_clock AS (SELECT statement_timestamp() AS requested_at) SELECT
  requested_at, requested_at + (:deadline_duration_ms * interval '1 millisecond') AS
  deadline_at FROM admission_clock`。同一 CTE 值产生两个字段；禁止第二次
  clock read、禁止 application wall clock 参与身份或持久期限计算。
- 外部语义依据 = PostgreSQL 官方
  [Date/Time Functions and Operators](https://www.postgresql.org/docs/current/functions-datetime.html)；
  `statement_timestamp()` 表示 current statement start，不与 transaction-start
  timestamp 或会在单个 statement 内变化的 `clock_timestamp()` 混用。
- `decision_requested_at` 与 `decision_deadline_at` 在同一 successful SAVEPOINT 写入
  Evidence 的 `AdvisoryAdmissionSeed` 并原样复制到 Invocation/Snapshot；它们不是从
  Evidence `created_at` 读回或推断的。**「same transaction ⇒
  Evidence.created_at 与 Invocation timestamp 数值相等」不成立，也不再作为任何
  proof。**
- 数据库类型 = PostgreSQL `TIMESTAMPTZ(6)`；读出后统一归一化为 UTC。
  进入 canonical JSON/hash 时使用 RFC 3339 `Z` + 固定 6 位小数秒；不受
  DB session timezone 或 locale 影响。duration 以 positive integer milliseconds 及
  `deadline_policy_version` 一并持久，不使用 float seconds。
- duration 未配置（Human Decision B，§25）时 Gate A 不能 active；I2 可实现 disabled
  path / test injection，不得给 production 猜默认值。
- PRE-01A 冻结语义保持：absolute、attempt 1 前固定、所有 retry 共享、per-attempt
  timeout 不能延长它。

advisory latency budget 从该 DB-authoritative admission instant 开始；queue 等待、
recovery、retry、provider I/O 全部消耗同一 budget。restart 必须复用已持久值；
config reload 只能创建新 config epoch/experiment，不改动旧 seed/Invocation。
若该 SAVEPOINT 在 clock/seed/Invocation 原子提交前失败，则不存在合法 Invocation deadline；
该 Evidence 只能按 §8.3 进入 unbound terminal path，restart 禁止读取新配置补造 deadline。

### 17.2 Propagation（PRE-01B-D1 AI Deadline Contract 落地）

- producer、durable Invocation、queue item（ref 内）、consumer、每次 Attempt、
  provider call 传递/重读**同一** immutable UTC absolute `decision_deadline_at`。
- 每个 durable correctness transaction 以该 transaction 内单次 PostgreSQL
  `statement_timestamp()` 与 persisted deadline 比较。开始 provider I/O 时可将 DB 返回的
  remaining interval 一次性映射为 AnyIO monotonic cancel scope（`fail_after` /
  equivalent），但 monotonic scope 仅负责本地取消；终态 deadline verdict 仍由
  finalizer 的 DB clock 重验决定。
- deadline terminal mapping 只按**当前 cycle 的 terminal-producing Attempt 是否已 durable
  commit** 判断：在该 commit 之前（包括 applicable 的 initial/retry enqueue、dequeue、
  pre-claim 路径）使用 `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER`，
  `final_attempt_id=NULL`，当前 cycle 新增 provider call = zero。这同时适用于从无 Attempt 的
  first dispatch 与可有 historical Attempt/provider call 的 retry gap。当前 Attempt-start transaction
  已 commit 后使用 `STALE_DECISION / DEADLINE_EXPIRED`，即使 provider I/O 尚未开始，
  并要求 exact current `final_attempt_id`。phase 名称、历史 Attempt 总数与 network-call count
  均不是 provenance boundary。
- provider 返回时已过期：不能增加风险；late-result semantics（audit only，不能赢
  final）。
- retry 共享 deadline；conservative remaining-time/cost/attempt check 不通过则不启动
  新 attempt；per-attempt timeout 取 `min(configured_per_attempt_timeout, remaining)`。

## 18. Retry / Failure Matrix

沿用 PRE-01A-D1 §8/§9 accepted taxonomy（transport/validation 分离、joint
deadline/attempt/cost、失败不得增加风险）。Gate A 落地：

下表中“no current Attempt”的唯一含义是：当前 terminalizing dispatch/retry cycle
尚无 terminal-producing Attempt；它包括 State A zero-history 与 State B retry gap，后者可有
historical Attempts/provider calls。“current Attempt exists”表示当前 cycle 的 Attempt-start
transaction 已 durable commit，不是「attempt table 中存在任意一行」。

| Failure class | Retry? | Final status / diagnostic | Durable provenance | Risk effect |
|---|---|---|---|---|
| transport retryable | 仅显式分类、attempt/deadline/cost budget 均允许 | exhaustion 时 `INVALID_SCHEMA / TRANSPORT_FAILURE + RETRY_EXHAUSTED` | every attempt | zero |
| provider transient/server unavailable | 同上 | `INVALID_SCHEMA / PROVIDER_UNAVAILABLE` | every attempt | zero |
| rate limit | 仅 server/provider 明确 retryable 且 deadline 容纳；无无限 backoff | `INVALID_SCHEMA / RATE_LIMIT` | every attempt | zero |
| schema/partial/malformed repairable | validator 明确 repairable 时才允许 validation retry | `INVALID_SCHEMA / SCHEMA_FAILURE\|PARTIAL_RESULT\|MALFORMED_OUTPUT` | raw/normalized validation facts | zero |
| business validation repairable | 仅预先枚举的可修正格式/数值关系 | `INVALID_BUSINESS / exact reason` | full reasons | zero |
| unsupported/hallucinated evidence | NO | `INVALID_BUSINESS / UNSUPPORTED_EVIDENCE` | yes | zero |
| refusal | NO | `INVALID_SCHEMA / REFUSAL` | yes | zero |
| auth/permission | NO；subsystem Gate A fail closed | `INVALID_SCHEMA / AUTH_PERMISSION` | yes | zero |
| invalid request/schema capability/model | NO；activation config invalid | `INVALID_SCHEMA / INVALID_REQUEST` | yes | zero |
| deadline expiry | NO | no current Attempt: `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER`；current Attempt exists: `STALE_DECISION / DEADLINE_EXPIRED` | yes；retry-gap historical Attempt preserved, not linked | current cycle zero before current Attempt |
| Evidence superseded | NO | no current Attempt: `STALE_DECISION / EVIDENCE_SUPERSEDED_BEFORE_PROVIDER`；current Attempt exists: `STALE_DECISION / EVIDENCE_SUPERSEDED` | yes；retry-gap historical Attempt preserved, not linked | current cycle zero before current Attempt |
| Opportunity eligibility lost or market freshness lost | NO | no current Attempt: `STALE_DECISION / OPPORTUNITY_STALE_BEFORE_PROVIDER`；current Attempt exists: `STALE_DECISION / STALE_BINDING` | invocation/final yes | current cycle zero before current Attempt |
| Decision Snapshot / input-binding invalid | NO | no current Attempt: `STALE_DECISION / BINDING_INVALID_BEFORE_PROVIDER`；current Attempt exists: `STALE_DECISION / STALE_BINDING` | invocation/final yes | current cycle zero before current Attempt |
| activation genuinely disabled | NO | no current Attempt: `STALE_DECISION / ACTIVATION_DISABLED_BEFORE_PROVIDER`；current Attempt exists: `STALE_DECISION / STALE_BINDING` | invocation/final yes | current cycle zero before current Attempt |
| activation enabled but experiment/config definition mismatched | NO | no current Attempt: `STALE_DECISION / EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER`；current Attempt exists: `STALE_DECISION / STALE_BINDING` | invocation/final yes | current cycle zero before current Attempt |
| retry exhaustion | NO | 最后 failure status + `RETRY_EXHAUSTED`；last completed Attempt 本身为 terminal producer | last terminal-producing Attempt required | follows last Attempt facts |
| cancellation / shutdown | NO（restart 另按原 invocation/budget 裁决） | no current Attempt（包括 retry gap）: `INVALID_SCHEMA / SHUTDOWN_BEFORE_PROVIDER`；current ACTIVE Attempt: `INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT`；或 process-loss attempt audit | current Attempt pair requires it；retry-gap historical Attempt not linked | current cycle zero before current Attempt |
| late result | NO | `STALE_DECISION / LATE_RESULT` 或 loser audit | yes | zero |
| duplicate completion | NO | winner 不变；`DUPLICATE_SUPPRESSED` | loser attempt yes | zero |
| internal invariant/hash/fence failure | NO；Advisory subsystem fail closed | immutable snapshot/binding integrity failure 按上方 exact binding pair；不能可靠写 terminal 的 DB/lock/fence failure 保留原 durable state 并由 restart 重裁，不得发明额外 terminal pair | sanitized durable evidence where possible | zero |
| queue rejected | NO | initial/retry/recovery offer 均用 `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`；`final_attempt_id=NULL` | invocation/final yes；retry-gap history preserved | terminalizing cycle new calls zero |
| Advisory DB capacity unavailable before provider | NO | no current Attempt（包括 retry gap）: `CAPACITY_BLOCKED / ADVISORY_DB_CAPACITY_UNAVAILABLE`；`final_attempt_id=NULL` | invocation/final yes；retry-gap history preserved | terminalizing cycle new calls zero |
| admission preparation/canonicalization/digest/config-binding/optional persistence failure | NO retry to Invocation；只重试 constant terminal write | `UNSTAGED`，或 `ADMISSION_FAILED_FINAL / ADMISSION_STAGING_FAILED_UNBOUND / NO_LONG_UNBOUND`；subsystem `FAIL_CLOSED` | valid G2/Evidence durable；无 seed/Invocation/Attempt/AIDecision；unbound completeness-hole counter durable/queryable | zero |

无任何 failure 触发 baseline BUY、自动 participate、TradePlan fallback 或 deterministic
fake-AI substitution；AI failure ⇒ treatment 侧按 PRE-01A §15 记 `NO_LONG` 语义入
operational denominator，但不因此产生任何经济动作。

## 19. Stale Matrix

六类 stale 判定相互独立，不得折叠成一个 boolean：

| 维度 | Authority | no terminal-producing Attempt for current cycle（zero-history 或 retry gap） | current terminal-producing Attempt durably committed |
|---|---|---|---|
| Evidence revision superseded | durable `edge_opportunity_evidence`（同 opportunity 存在更高 revision） | `STALE_DECISION / EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` | `STALE_DECISION / EVIDENCE_SUPERSEDED` |
| Opportunity eligibility lost | formal Evidence `expires_at` + durable current G2 `symbol_states.state/state_version` | `STALE_DECISION / OPPORTUNITY_STALE_BEFORE_PROVIDER` | `STALE_DECISION / STALE_BINDING` |
| market freshness lost | frozen Evidence `reference_data_status`（`OK/REFERENCE_MISSING/REFERENCE_STALE`）+ snapshot market facts | `STALE_DECISION / OPPORTUNITY_STALE_BEFORE_PROVIDER` | `STALE_DECISION / STALE_BINDING` |
| Decision Snapshot / input-binding invalid | `snapshot_payload_hash` + `input_binding_digest` + exact `evidence_hash`/`feature_snapshot_hash` | `STALE_DECISION / BINDING_INVALID_BEFORE_PROVIDER` | `STALE_DECISION / STALE_BINDING` |
| experiment config mismatch | invocation self-contained binding vs current activation | actually DISABLED ⇒ `STALE_DECISION / ACTIVATION_DISABLED_BEFORE_PROVIDER`；enabled-but-incompatible ⇒ `STALE_DECISION / EXPERIMENT_CONFIG_MISMATCH_BEFORE_PROVIDER` | `STALE_DECISION / STALE_BINDING` |
| deadline expired | immutable `decision_deadline_at` | `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER` | `STALE_DECISION / DEADLINE_EXPIRED` |

| 时点 | 必须动作 |
|---|---|
| stale before initial/retry enqueue | 不入 queue；同 invocation 按无 terminal-producing Attempt pair terminalize，当前 cycle 新增 provider call = zero |
| stale while initial/retry queued | dequeue durable re-read 后按无 terminal-producing Attempt pair terminalize，当前 cycle 新增 provider call = zero |
| stale immediately before current Attempt creation | attempt-start transaction 在 Evidence lock 下拒绝，当前 cycle 新增 provider call = zero |
| current Attempt-start committed, provider I/O not begun | current Attempt 已存在；按对应 Attempt-origin exact behavior terminalize，禁止 `*_BEFORE_PROVIDER` reason |
| stale during provider call | 不新增 market subscription / second event bus；response 后 finalizer durable re-read 判 stale；可 best-effort cancel，cancellation 不是 authority |
| valid response 后、finalization 前变 stale | finalizer 按 `Evidence -> Invocation -> Attempt` 锁顺序重读后判 `STALE_DECISION`（含 `EVIDENCE_SUPERSEDED`），valid response 只留 attempt/AIDecision audit，不能成为 current/actionable winner |

前三个时点只有在当前 cycle 的 Attempt-start transaction 尚未 commit 时才使用上表
无 terminal-producing Attempt pair；这可以是 zero-history，也可以是保留 historical Attempts 的
retry gap。若当前 Attempt 已 durably inserted，则即使 provider I/O 未开始，也必须走 current
Attempt 列并要求 exact same-Invocation `final_attempt_id`。current-Attempt terminal 的
`final_decision_id` 仅在 D2 finalizer
contract 已合法接受 normalized artifact 时可非 NULL，否则为 NULL。每个 case 显式给出：
durable state（terminal row + exact diagnostic）、provider call yes/no、audit retention（Attempt
存在时保留 attempt audit）、economic effect = **ZERO**。retry gap 中 historical Attempt/provider-call
facts 不变；“zero”只指 terminalizing current cycle 无新 provider call。所有 stale outcome
zero risk increase。

## 20. Shutdown / Restart

RuntimeHost 拥有 AdvisoryIngress lifecycle；关闭动作落在 PRE-01B-D1/I1 已接受的
shutdown 顺序的 step 2 槽位（「close/cancel new advisory work」—— I1 实现为 no-op
注释，本设计填充该槽位）。本修复在已有 Host shared graceful deadline 内冻结两个
必须显式配置、不在本 Design 发明数值的 duration：

```text
protection_reserved_budget
advisory_cleanup_budget

protection_handoff_at = host_shutdown_deadline - protection_reserved_budget
advisory_subdeadline = min(
    advisory_cleanup_started_at + advisory_cleanup_budget,
    protection_handoff_at,
)
```

Host shutdown monotonic clock 与 shared deadline 沿用 D1；上述两个 duration 是 B 类 activation
config，必须为 positive finite、并在 Gate A activation 前验证与 Host 总窗口相容。
缺失/非法时 Gate A 不能 active，不猜 production default。

### 20.1 Advisory-vs-Protection DB resource/concurrency fence（FIX-02）

FIX-01 只保留 shutdown **时间**，但 latest main 的 `DatabaseResources` 只有一个 Host-owned
primary engine/session factory，`create_async_engine()` 未显式冻结 pool capacity；G2、Execution、
Protection、Recovery 等均共享该 factory。故仅有 subdeadline 不能证明 Advisory 不耗尽连接。
FIX-02 在不引入第二 engine/DSN/DB authority 的前提下冻结以下机械契约：

```text
C = effective_db_capacity
R = protection_reserved_db_capacity
A = advisory_db_max_concurrency

C, R, A are positive finite integers
R < C
A + R <= C
```

1. **Capacity authority**：现有 Host-owned primary `DatabaseResources` / engine 是唯一容量
   authority。I2 必须让 `pool_size`、finite `max_overflow` 与 `pool_timeout` 由 explicit
   Pack-B config 构造并由 `DatabaseResources` 暴露经验证的 `C = pool_size +
   max_overflow`；unbounded overflow、不能证明的 injected pool、配置与 engine 实况不一致、
   或上述方程失败 ⇒ Gate A startup/activation fail closed。现有 singleton-lock engine 不属于
   `C`，也不得供 Advisory/Protection 借用。
2. **Owner/capability boundary**：`RuntimeHost` 唯一构造并拥有
   `AdvisoryDbFence`（bounded limiter + session/transaction wrapper）。Advisory constructors
   不得接收 raw engine、raw primary `session_factory` 或可另开 connection 的 handle；只接收
  该 capability。Protection/Safety 保持使用 Host primary session factory，绝不获取
   Advisory limiter。无第二 general DB authority、无 separate Advisory DSN/pool。
3. **Acquire/release**：每个执行 Advisory SQL 的 call path 必须先取得一个 limiter token；
   token 数上限 = `A`，ordinary fence-owned Advisory session 必须在 token 后 checkout，
   且一个 token 最多对应一个 checked-out connection；nested/parallel second session 禁止。
   Admission 复用已经 checkout 的 caller-owned G2 session 时，在第一条 Advisory-specific
   operation 前只允许 **immediate non-blocking try-acquire**：持 G2 connection 时不得
   queue/await/timeout wait；不得为取 token checkout 第二 connection。失败即 skip Advisory
   SQL，Evidence 保持 `UNSTAGED` 并走 deterministic unbound-failure accounting，外层 G2
   继续；需要 completeness 的 Gate A fail closed。成功后 token 从 try-acquire 起持续覆盖
   全部 nested SAVEPOINT work、outer transaction commit/rollback，以及 caller-owned
   exact-generation pool observation + owner lifecycle completion 的 full positive predicate；SAVEPOINT completion、
   `finally` entry 或 close-start 绝不释放 token。
   G2 caller 仍独占 outer transaction/session/final connection return ownership；writer/fence
   只拥有 bounded token/capability 与 Advisory-specific operations。try-acquire 不执行 SQL/
   checkout；返回的 `CallerOwnedAdvisoryLease` 绑定 already-owned session，writer 不接收 raw
   engine/session factory，也不能 close/invalidate/commit/rollback outer resource。
4. **Bounded acquisition/transaction**：Gate A active 时 Pack B 必须提供 positive finite
   `advisory_db_acquire_timeout`、`advisory_db_transaction_timeout`、
   `advisory_statement_timeout`、`advisory_lock_timeout`、
   `advisory_idle_in_transaction_timeout`。每次 operation 的 local deadline 取这些配置、
   persisted invocation deadline（若存在）与当前 shutdown subdeadline 的最小值；要求
   `lock_timeout <= statement_timeout <= transaction_timeout` 且所有值能在
   `advisory_cleanup_budget` 内完成 cancel/rollback。checkout wait 同时受 wrapper
   acquire timeout 与 primary pool timeout 约束。该 bounded wait 只适用于尚未持有 primary
   connection 的 ordinary Advisory call；caller-owned G2 path 始终使用上项 zero-wait try。
   ordinary fence-owned Advisory transaction 可用 PostgreSQL
   `SET LOCAL statement_timeout/lock_timeout/idle_in_transaction_session_timeout`，也可在其
   自有 transaction deadline 到达时 client-cancel 后 bounded rollback/close/invalidate；因为
   fence owns whole transaction/session，失败只影响 Advisory。caller-owned G2 path **只能**在
   nested SAVEPOINT 内使用 `statement_timeout/lock_timeout`，并按 §8.2 capture/restore；禁止
   `idle_in_transaction_session_timeout`、client task cancellation 与 solely-for-Advisory
   invalidation。其 transaction budget 只作 cooperative pre-statement gate；server timeout
   error 必须 rollback SAVEPOINT。任何 connection-level termination 均不再声称可保全 outer G2。
5. **Provider/DB separation**：provider network I/O 前必须已 commit/rollback 并关闭
   Advisory DB session、释放 token；provider I/O 期间 `advisory_db_tokens_held = 0`。
   Attempt-start 与 finalizer 是两个短事务。禁止在 provider await、retry backoff、queue wait、
   logging/metrics flush、shutdown provider cancellation期间持有 session/transaction/token。
6. **Lock-surface fence**：Gate A Advisory transaction 仅可锁 §11 allow-list 及 bound
   Evidence row；不得查询 `FOR UPDATE` 或写 Account/Position/Order/Fill/Trade/Ledger/
   Protection/Safety authority tables。这样即使一个 Advisory connection 在取消中延迟，
   也不能持有 Protection 的经济 row-lock graph；§10 的 Evidence lock order保持不变。
7. **Capacity proof**：任意时刻 Advisory 最多占 `A` 个 primary-pool connection，故即使
   它们全部 wedged，在仅考虑 Advisory 对 pool 的贡献时仍有至少 `R` 容量未被 Advisory
   占用。该保证不声称 PostgreSQL/core failure 或其他 core caller 永不失败；它只证明
   Advisory 不能耗尽 Protection reserve，符合 P1-05 的 failure attribution 边界。
8. **Cannot acquire**：caller-owned G2 admission 的 immediate try-acquire 失败时留
   `UNSTAGED` 并按 §8.3 终态化；已有 Invocation
   在能取得一个 bounded terminal-write lease 时写
   `CAPACITY_BLOCKED / ADVISORY_DB_CAPACITY_UNAVAILABLE`，否则保持原 durable state、
   Gate A fail closed、当前 acquisition/terminalizing cycle 新增 provider call = zero，并由
   restart 在原 deadline 下重裁。不得 unbounded wait、
   不得借用 `R`、不得 fallback 到 raw session factory。`DISABLED` path 不构造 fence、
   不取得 token，也不要求本节 Pack-B 数值。
   对 `RETRY_PENDING` Invocation，下一 Attempt 创建前无法取得 DB capacity 就是
   retry-gap terminal：若 bounded terminal-write lease 可用，写入上述 exact pair、
   `final_attempt_id=NULL`、`final_decision_id=NULL`，当前 retry cycle 新增 provider call = zero。
   historical Attempt/provider-call facts 可存在且必须保留；不得链接 last historical
   Attempt，不得伪造 next Attempt，不得声称 Invocation-lifetime provider calls = zero。
9. **Release authority**：每个 lease 必须绑定 RuntimeHost epoch + application-assigned pool-entry
   identity + monotonically increasing checkout generation + lease/token identity。`checkout` listener
   只用 public `ConnectionPoolEntry.record_info` / `PoolProxiedConnection.info` 写入 correlation；
   caller 在 connection 已 checkout 后通过 public `AsyncSession.connection()` →
   `AsyncConnection.info` 取得 exact key。normal return 只有 exact-generation `checkin`
   observation（Fact A）与 owning caller 的 awaited `AsyncSession.close()` / session context-exit
   成功返回（Fact B）**同时存在**才可 once-only `RELEASE_CONFIRMED`；callback observation 单独
   只是 `RETURN_PENDING`。explicit invalidation 还必须有同代 hard-invalidation observation、
   `checkin(None)` 与 owning caller awaited invalidate/close-context success；任一 callback-entry
   或 `invalidate()` return 单独都不释放。cleanup raised/cancelled/unknown/missing notification =
   `RETURN_UNCERTAIN_RETIRED`；token 在本 process epoch 保持 unavailable、计入
   `advisory_db_uncertain_resources`，Gate A fail closed。只有迟到的完整 exact-correlated predicate
   可幂等恢复一次；duplicate/旧 generation 事件不改变 capacity。process death 不制造 release；
   新 epoch 只在 singleton ownership、fresh pool capacity validation 成功后建立自己的 limiter，
   旧 epoch uncertainty 仅作历史 shutdown/restart evidence。完整状态机与矩阵见 §20.3/§35。

### 20.2 Shutdown subdeadline / deterministic handoff

1. Host 立即设 `advisory_admission_open=false`，拒绝新 post-commit offer（Invocation 保持
   `ADMITTED`）；同时 `AdvisoryDbFence.close_for_new_acquisitions()`，包括拒绝 caller-owned
   G2 的新 immediate try-acquire，停止 durable recovery scan / queue 补充 / dequeue claim，
   不再启动新 Attempt/DB lease。已取得 token 的 caller-owned G2 operation 仍被计入 `A`。
2. cancel active provider I/O；取消仅作用于 Advisory nested scope，不能传播到
   safety/protection siblings。Provider boundary 必须无 detached callback/task；late response
   无法绕过 Invocation finalizer fence。
3. 在 `advisory_subdeadline` 前可 best-effort terminalize 已取消 ACTIVE Attempt 或少量
   ADMITTED items，但**不要求每个 queued ref/Invocation 都写 cancellation final**。任何
   shielded DB cleanup 的 shield 上限也是 advisory subdeadline，绝不是 Host deadline；
   每次 fence-owned cleanup 仍需取得 Advisory token 且受 §20.1 server/client timeout 约束；
   已持 token 的 caller-owned G2 admission 不重新 acquire。
   若能在 budget 内写入 shutdown final：State A 或 `RETRY_PENDING` retry gap 使用
   `INVALID_SCHEMA / SHUTDOWN_BEFORE_PROVIDER`，`final_attempt_id=NULL`，保留任何历史
   Attempt；`ACTIVE` current Attempt 使用
   `INVALID_SCHEMA / SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT` 并要求该 exact current Attempt
   provenance。禁止为 shutdown 伪造 next Attempt。
4. 到达 `advisory_subdeadline` 时，Host 必须拒绝新 Advisory work/token，并取消/rollback
   Advisory SAVEPOINT work where possible。fence-owned Advisory session 无法及时 clean close
   时可 invalidate，但不得 dispose shared engine。**不得仅为停止 Advisory 而 invalidate
   caller-owned G2 connection、强制 rollback otherwise-valid G2 truth，或取得 outer
   transaction ownership**；该 outer G2 operation 按 accepted core RuntimeHost lifecycle
   完成 commit/rollback 和 connection return。其 token 必须如实保持 held/counting，直到
   §20.3/§35 two-factor/full invalidation predicate；pool-observed、owner-completed-only、pending/
   uncertain 均必须 counted/retired，Host 不得提前报告
   released。丢弃 process-local
   queue refs 后进入 Protection/Safety phase；Protection 不等待这些最多 `A` 个 holders，
   直接使用其余 `R` capacity。Advisory 不得开启新事务、等待 provider、或以日志/metrics
   flush 占用 reserve。
5. 结构不变量：无论 Advisory backlog/DB/provider 状态如何，
   `protection_handoff_at..host_shutdown_deadline` 始终留给 Protection/Safety。
   Advisory cancellation 既不 cancel Protection，也不得阻塞 safety drain；即使 cleanup
   connection（包括延迟退出的 caller-owned G2 holder）尚在 driver/DB/core lifecycle，
   被 Advisory 计数的总数也不超过 `A`，`R` 不可被 Advisory 占用。
6. engine 仍由 Host 最后 dispose。选择 **cancel，不做 provider drain**；无 detached
   daemon、无 in-process restart supervisor（沿用 I1 fatal matrix）。

`advisory_subdeadline` 到达时允许的 durable 状态与 restart 解释：

| Exit-time fact | 允许留存 | 本次 shutdown 内的 actionability | Restart interpretation |
|---|---|---|---|
| Evidence accounting `UNSTAGED` | yes | admission closed，zero provider | 不读 config/不补 seed；只写 constant unbound terminal，失败则保持 `UNSTAGED` / fail closed |
| Evidence accounting `ADMISSION_FAILED_FINAL` | yes | accounting terminal，zero provider | 保留 `NO_LONG` + exact reason，不创建 Invocation |
| `ADMITTED`（含 queue ref 已存但未 claim） | yes | queue ref 丢弃；不 claim | 按原 deadline/stale/config epoch 重新 bounded offer 或 terminalize |
| `ACTIVE` + `STARTED` Attempt，provider I/O in flight | yes | cancel scope；不等 drain；不允许新 finalizer 越过 subdeadline | 原 Attempt 记 `PROCESS_LOST/ABANDONED`；仅在原 budget/deadline 允许时 retry |
| provider cancellation completed、DB terminalization 也在 budget 内 commit | no（Invocation 已 FINAL） | terminal/non-actionable | 永不 requeue |
| provider cancellation completed、但 DB terminalization 未在 budget 内 commit | yes（仍 ACTIVE/STARTED） | 本 process 已关闭 finalizer，zero economic use | 按 process-lost 规则，不伪造 cancellation final |
| `RETRY_PENDING` | yes | 不启动新 Attempt | 处于 retry gap；原 identity/provider/model/deadline 继续，或按§14.2 无 terminal-producing Attempt pair terminalize；历史 Attempt 保留、`final_attempt_id=NULL` |

### 20.3 Connection disposition / token state machine（FIX-05）

每个 lease 的 registry key 至少为 `(runtime_epoch, pool_entry_id, checkout_generation,
lease_id)`；owner cleanup attempt 另有 application-owned correlation id，以防一次失败 callback
的 observation 被错误复用于另一次 cleanup。generation 在每次 checkout reuse 时单调递增。
状态保存 `pool_return_observed`、`owner_completed` 与 disposition kind（normal / invalidation）
事实位，顺序不构成权威：

```text
HELD
  -- exact-generation normal checkin observed --> RETURN_PENDING
  -- owner cleanup returns successfully ------> OWNER_COMPLETED_PENDING_POOL_CONFIRMATION
  -- explicit hard invalidation starts --------> INVALIDATE_PENDING

RETURN_PENDING + matching owner-success
  -- same lease/generation/cleanup attempt ----> RELEASE_CONFIRMED

OWNER_COMPLETED_PENDING_POOL_CONFIRMATION + matching pool observation
  -- same lease/generation/cleanup attempt ----> RELEASE_CONFIRMED

any non-confirmed state
  -- cleanup raise/cancel/unknown/missing notice --> RETURN_UNCERTAIN_RETIRED
```

- normal return 的 Fact A = exact-generation `PoolEvents.checkin` observation；Fact B = owning
  caller awaited `AsyncSession.close()` / `Session.close()` / session context-exit **成功返回之后**
  发出的 owner-completion signal；若 direct `AsyncConnection` / `Connection` 才是 owning boundary，
  则以其 awaited close/context-exit 成功返回为 Fact B，session-owned connection 不得绕过 Session
  boundary。只在 A + B 均存在时 once-only `RELEASE_CONFIRMED`；A 单独
  是 `RETURN_PENDING`，B 单独是 `OWNER_COMPLETED_PENDING_POOL_CONFIRMATION`，两者均不增容。
- owner observer 属于 G2/core lifecycle wrapper。它在 owner cleanup API 成功返回后，把已捕获的
  exact key/attempt id 报告给 Host-owned registry；Advisory 只能观察，不能 close/commit/rollback/
  cancel/invalidate 健康的 caller-owned resource。notification 缺失即 fail closed，绝不推测成功。
- explicit invalidation 的 full predicate 更严格：same-generation hard `invalidate` observation +
  same-generation `checkin(None)` + owning caller awaited `AsyncSession.invalidate()`（它本身是 owner
  session cleanup boundary）成功返回；若 owner 使用 explicit connection invalidation，则还必须在
  subsequent connection/session close-context 成功返回后才发送 Fact B。`invalidate`、`close`、
  `checkin(None)` 或 `invalidate()` return 任一个单独都不释放。
- callback/listener/后续 return step 抛错时，即使 registry 已记录 checkin observation，owner cleanup
  也不会产生 success Fact B；该 cleanup attempt 进入 `RETURN_UNCERTAIN_RETIRED`，capacity 不增加。
  迟到恢复只允许在同一 authoritative epoch 内取得一个新的、完整且 exact-correlated positive
  predicate；旧/失败 attempt 的单一 fact 不得复用。重复 fact 与 `RELEASE_CONFIRMED` 后所有事件 no-op。
- `available_advisory_tokens = A - HELD - RETURN_PENDING -
  OWNER_COMPLETED_PENDING_POOL_CONFIRMATION - INVALIDATE_PENDING - RETURN_UNCERTAIN_RETIRED`
  （下限 0）。上述所有未确认状态均属于 `U`，仍占 Advisory 的 A attribution、不借 R、使 Gate A
  readiness `FAIL_CLOSED`。只有 `RELEASE_CONFIRMED` 从 `H_o / H_g / U` 移除 holder。
- shutdown 输出 held/return-pending/owner-pending/invalidate-pending/uncertain/release-confirmed、
  oldest age、exact key/attempt、cleanup error/cancel、over-subdeadline 与 `STOP_FAILED` reason。
  subdeadline 不改变 predicate；late confirmation 可更新 telemetry/state，但 close-new 后不得重开
  Gate A 或 admit work。process death 不制造 release；new epoch 在 singleton + fresh pool/capacity
  validation 后建立新 limiter，旧 uncertainty 只作历史 evidence，不跨进程持久化 token。

single RuntimeHost singleton fence + `advisory_admission_open=false` + stopped claim path 是关闭期间
的执行 fence；durable non-terminal 行本身不授权任何经济行为。Protection reserve 不以
「Advisory 先全部写完」为前置；DB reserve 由 `A + R <= C` 与 capability isolation 独立保证。

## 21. Health / Readiness

### 21.1 Minimum surface

```text
activation_level: DISABLED | GATE_A_SHADOW | GATE_B_PAPER
state: DISABLED | STARTING | RECOVERING | ACTIVE | DEGRADED | FAIL_CLOSED | STOPPING | STOPPED
queue_size / capacity / high_water
admitted / admission_staging_failed / queue_rejected / expired
active_attempts / completed / failed / timed_out / cancelled
late_results / duplicate_fenced
unbound_eligible_admission_failures / unstaged_rows
effective_db_capacity / protection_reserved_db_capacity / advisory_db_max_concurrency
advisory_db_tokens_held / waiters / high_water
advisory_db_sessions_checked_out / active_transactions
advisory_db_acquire_timeouts / pool_checkout_timeouts / statement_timeouts / lock_timeouts
advisory_db_forced_invalidations / over_subdeadline_sessions
protection_db_acquire_latency / protection_db_acquire_timeouts
db_fence_equation_valid / protection_reserve_headroom
last_success_at / last_failure_at / last_failure_category
recovery_pending
provider_configured (identity only; no secret)
```

只保留 current snapshot、monotonic counters、high-water 与 bounded error samples；
不构建 metrics platform / unbounded time series。

上述 DB-fence/queue/attempt metrics 是 active-capable Gate A surface；`DISABLED` epoch
不因 fence/worker 未构造而制造缺失告警，可明确报告 `not_applicable`/zero。唯一必须可查询的
durable classification 是 Evidence INSERT 中的 `GATE_A_DISABLED` 或 safe fallback
`UNSTAGED`。

### 21.2 Readiness split（显式裁定：DISABLED vs GATE_A_SHADOW）

- `DISABLED`：AdvisoryIngress 不构造（无 provider/consumer）；`AI_AUXILIARY` 维持
  I1 现状（`DEGRADED/ai_reevaluation_disabled` 类语义），对 RuntimeHost overall
  readiness **无影响**。Host 只冻结本 runtime epoch 的 immutable activation
  classification；formal Evidence INSERT 直接写 literal `GATE_A_DISABLED`。无 worker、
  无 `AdvisoryDbFence`、无 full writer、无 extra Advisory SQL/SAVEPOINT；Pack-B
  capacity/timeout values 可 unset。若不能建立 valid disabled classification，new Evidence
  保持 DB default `UNSTAGED`，不得被追溯补绑。任何 `DISABLED -> active` 都要求独立授权
  boundary + new explicitly frozen runtime epoch，禁止 silent in-place activation。
- `GATE_A_SHADOW`：AdvisoryIngress degraded / `FAIL_CLOSED`（含 admission staging
  failure、provenance persistence failure、DB fence invalid/acquire timeout）**只**影响 Gate A readiness
  （`AI_AUXILIARY` 组件置 unavailable/degraded + 关闭新 advisory admission），
  **不**影响 Core readiness / Protection / risk gate —— I1 已验证 `AI_AUXILIARY`
  不在 Core readiness 阻断合取内，本设计保持该性质。
- Gate A Shadow provider failure（ordinary transport/refusal/validation/timeout）：
  仅 terminalize 单个 invocation，worker 继续，**must not disable Protection**；
  provenance/invocation persistence failure：**must fail closed for new advisory
  admission**。
- shared DB/singleton/engine ownership failure 仍按 I1 Host fatal matrix —— 那是
  Host failure，不被「降级」为 AI failure。
- `db_fence_equation_valid=false`、Advisory bypass raw session、token/session mismatch、
  `advisory_db_tokens_held > A` 或检测到 provider I/O 持 DB token，均为 invariant failure：
  Gate A 立即 fail closed；Protection reserve/readiness 单独报告，不能被 AI health 掩盖。

## 22. Gate A / Gate B Boundary

唯一 activation config：

```text
advisory_activation_level = DISABLED | GATE_A_SHADOW | GATE_B_PAPER
```

- default = `DISABLED`。
- I2 只可实现/接受 `DISABLED` 与 `GATE_A_SHADOW`（wiring 完成不等于 active；
  Human activation 前保持 disabled）。
- 未经独立 Gate B implementation + Human Approval，配置 `GATE_B_PAPER` 必须
  startup fail closed（不自动降级/解释成 Gate A，不创建 plan）。

| Level | Allowed | Forbidden |
|---|---|---|
| Gate A | real provider call（另行激活后）、decision/provenance/AI attribution | TradePlan、Risk、Execution、Position、Account、Ledger mutation |
| Gate B | 仅在独立批准后，一条 predeclared authoritative arm 进入 existing deterministic chain（`DecisionValidator`/`TradePlanManager`/`SystemRiskGate`/Paper Execution 不变） | baseline fallback、绕过 validator/risk/execution/accounting/protection、Live |

Gate A wiring 完成不等于 Gate A active；Gate A active 不等于 Gate B；Gate B 不等于
Gate C / Live。Gate A wiring 不得自动解锁 TradePlan/Risk/Execution/Accounting/
Protection-controlled economic activation。

## 23. SE-02D Boundary

### 23.1 当前状态

`SE-02D-D01` / `I01` / `I02` / `I03` / `CLOSE-D01` / `SE-02D Overall` =
`ACCEPTED / COMPLETE`；`SE-02D V1 CAPABILITY COMPLETE AFTER I03`；
`I04 = NOT REQUIRED`。API / frontend / runtime product consumer 不属于 SE-02D V1
completion requirement。historical arbitrary revision-as-of 仍 `OPEN / NOT SUPPORTED`。

以下边界不因 SE-02D complete 而改变：experiment/pair/arm identity = `OPEN Gate C
prerequisite`；arm-level selection Expectancy/delta = `FUTURE CONSUMER`；durable regime
identity/criteria = `OPEN`；Gate C immutable evidence retention = `FUTURE TASK`；
`Gate C = NOT PASSED`；Real AI = `NOT ACTIVATED`；Live = `NOT AUTHORIZED`。

### 23.2 SE-02D-I02 runtime reuse = NONE（显式裁定）

AdvisoryIngress **不** import / 调用：`aggregation_snapshot.py`、
`CurrentSnapshotRevisionReader` / `CurrentSnapshotProjection` /
`CanonicalScopeFacts`。理由：I02 是 Edge/Expectancy 的 current-snapshot 投影 ——
`REPEATABLE READ READ ONLY`、aggregation-oriented、Outcome-chain folding、
statement-timestamp `as_of`；live advisory decision-ingress 与之耦合只会扩大 blast
radius 与延迟，无 correctness 收益。

**概念性复用（conceptual reuse）**的已接受语义：

1. revision chain 按 chain 校验（supersedes 链、同-opportunity scope integrity 由
   DB `uq_edge_evidence_opportunity_revision` + `fk_edge_evidence_supersedes` 保证）；
2. canonical head = validated chain 的最高 revision（advisory 的 supersede 检测只需
   「同 opportunity 存在更高 revision」这一最小 durable 查询，§10.2，不需要完整
   folding projection）；
3. integrity conflict ⇒ fail closed（`SnapshotIntegrityError` 先例 ⇒ advisory
   invariant failure / stale，conflict 标识符沿用单元素元组铁律）；
4. versioned canonical JSON / 身份编码纪律（无未转义 join、无 digest 作语义
   equality authority）；
5. 「fold complete revision chains before membership」（D01）在 advisory 侧的对应
   物 = supersede 判定永远基于 durable 最高 revision，而非任何 process-local 视图。

### 23.3 禁止事项

D2 / I2 不得：改动已接受的 SE-02D、把 I03 orchestration 接入 Advisory runtime、定义 Gate C
threshold、声明 profitability/edge、决定 superseded-revision pair 的实验分母计数
（该问题归 SE-02D / Gate C aggregation contract）。Gate C 仍需另行接受的 SE-02D
expectancy evidence。

## 24. Schema Decision

### 24.1 REUSE AS-IS

- `edge_opportunity_evidence`：Opportunity/Evidence durable identity、revision chain、
  hash、snapshot source、expiry、reference 三态 authority（SE-02A/ARCH-FIX 契约原样）；
  exact bound/predecessor Evidence row 另被**复用**为 §10.1 的 transaction row-lock
  target，不创建第二 identity authority。
- G2 event/timeline/state/transition/candidate/observation tables 与 transaction 语义。
- `edge_attribution_events` schema/identity：append-only lineage；不是
  invocation/final fence。
- Trade/Risk/Execution/Position/Account/Ledger schema：Gate A 完全不写。

### 24.2 REUSE WITH MINIMAL EXTENSION

`edge_opportunity_evidence`（新 admission accounting fields，不进入/不改变
`evidence_hash`、Evidence payload 或 revision identity）：

```text
advisory_admission_state NOT NULL
advisory_admission_reason_code nullable
advisory_treatment_participation nullable
advisory_admission_seed_version nullable
advisory_admission_seed_digest nullable
advisory_admission_seed JSONB nullable
advisory_decision_invocation_id nullable
```

Migration 必须先把 existing rows 固定 backfill 为 `LEGACY_PRE_I2`，再把 new-row
server default 设为 `UNSTAGED`；不得把历史 Evidence 猜成 Gate A 成员。startup epoch
合法冻结为 `DISABLED` 时，existing formal Evidence INSERT **在原 INSERT statement 内**
显式写 literal `GATE_A_DISABLED`；不经 separate UPDATE/writer/fence/SAVEPOINT，不准备
seed/config/digest/provider，也不改变 Evidence identity/hash/payload。分类无法合法建立时不
覆盖 default，持久值为 `UNSTAGED`。conditional CHECK
要求：`LEGACY_PRE_I2/UNSTAGED/GATE_A_DISABLED` 不得有 invocation；
`UNSTAGED` 不得有 partial seed/digest/config/clock/arm；
`ADMISSION_FAILED_FINAL` 的 `...UNBOUND` reason 必须无 seed、无 experiment/pair/arm、
`NO_LONG_UNBOUND` 且无 invocation；其他未来 named terminal 只有在完整 seed 已原子
存在时才可使用；`INVOCATION_CREATED` 必须有完整 seed 与 Invocation FK。Evidence ↔
Invocation 的循环 FK 必须 `DEFERRABLE INITIALLY DEFERRED`，使 §8.3 SAVEPOINT
在单一 transaction 内原子插入/翻转，不可暂时提交半链接状态。除 schema literal
`UNSTAGED` 外，只有 original Evidence INSERT 上的 literal `GATE_A_DISABLED` 可不经
nested SAVEPOINT；active path 的其他 seed/accounting write 全在 nested SAVEPOINT 内。
该 extension 是关闭
P1-01 的 minimum PostgreSQL authority；不新增 admission/outbox/framework table。

`decision_snapshots`（新 Shadow rows 增加 queryable binding facts，legacy rows 兼容）：

```text
decision_invocation_id, opportunity_id, evidence_id, evidence_revision, evidence_hash,
feature_snapshot_hash, market_type, snapshot_payload_hash, input_binding_digest,
advisory_config_epoch_id, decision_requested_at, deadline_duration_ms,
deadline_policy_version, decision_deadline_at
```

`ai_decisions`（继续作 normalized provider-result artifact；**不再作 no-provider
terminal authority**）：

```text
decision_invocation_id（partial UNIQUE for non-null new rows）, attempt_id,
input_binding_digest, experiment_id, pair_id, arm_id,
provider_id, configured_model_id, provider_reported_model_id nullable,
output_digest, error_category, finalized_at
```

legacy `decision_id(snapshot_id, model)` 只保留给既有非-Advisory 路径；新 Gate A rows
必须使用 invocation-derived `decision_id` 并以 Attempt FK 证明 origin。migration/
backfill 策略属 I2 design review；不得把旧 row 伪造为新 invocation/Attempt。

### 24.3 NEW MINIMAL PERSISTENCE REQUIRED

`advisory_decision_invocations`（一 row / logical invocation）：

```text
decision_invocation_id PK
snapshot_id FK
opportunity_id / evidence_id / evidence_revision / evidence_hash / feature_snapshot_hash
experiment_id / experiment_definition_digest
pair_id / baseline_arm_id / treatment_arm_id / arm_id
baseline_policy_version / baseline_participation
input_binding_digest
prompt_version / schema_version / treatment_version
configured_provider_id / configured_model_id
decision_requested_at / decision_deadline_at
state (ADMITTED/ACTIVE/RETRY_PENDING/FINAL)
final_status nullable
final_reason_code nullable
finalized_at nullable
final_attempt_id nullable
final_decision_id nullable
created_at / updated_at
UNIQUE(experiment_id, pair_id, arm_id)
```

`advisory_decision_attempts`（一 row / attempt）：

```text
attempt_id PK
decision_invocation_id FK
attempt_number
retry_class / retry_reason / prior_attempt_id nullable
provider_request_id / provider_response_id nullable
configured_provider_id / configured_model_id / provider_reported_model_id nullable
started_at / response_received_at / finished_at / latency_ms nullable
provider_outcome / normalized_status / error_category
input/output/total_tokens nullable + unavailable_reason nullable
monetary_cost nullable + pricing_version nullable
output_digest / validation_result / validation_errors
redacted request/response envelope nullable (policy-gated)
UNIQUE(decision_invocation_id, attempt_number)
UNIQUE(decision_invocation_id, attempt_id)
```

Invocation 的 final-field completeness CHECK、named-nullability CHECK、Attempt composite FK、
AIDecision `(decision_invocation_id, attempt_id)` composite FK 及 §14.2 的 deferred
final-decision composite FK 均是 `MINIMAL EXTENSION/CONSTRAINT`，不建第三 final table。

### 24.4 Necessity proof（对照当前 schema）

当前 schema（`db/models.py` 实测）无 durable admission gap accounting，也无
invocation/attempt/experiment/pair/arm 持久层；`decision_snapshots` 无 binding/hash/
deadline；`ai_decisions` 无 Attempt origin；任何现有表都无 queryable exactly-one terminal
fields。因此 PRE-01A AC-21/22、P1-01 恢复、P1-03 final authority 与 winner fence
在现有 schema 上不可表达。**两张最小新表**（Invocation/Attempt）+
**三处最小 extension**（Evidence accounting、Snapshot binding、AIDecision origin）
是满足契约的最小集。P1-05 还要求现有 `DatabaseResources` 暴露 primary-pool effective
capacity 并由 Host 构造 `AdvisoryDbFence`；这是同一 engine/session ownership 的 capability
extension，**不是**新 table/engine/DSN，且仅在 Gate A active-capable epoch 需要；
`DISABLED` epoch 不构造该 fence。caller-owned G2 admission 的 token lease 覆盖其实际
connection return，使同一 equation 能计数该路径而不转移 G2 transaction ownership。
Evidence supersession 与 final-then-supersede actionability
完全复用现有 Evidence chain + row lock，故**不**增 supersession marker/table。
不新增 generic workflow、event bus、saga、job、provider registry、outbox 或 metrics
table；Invocation row 即 final authority，不建第三 final table。**本契约不创建 migration**。

## 25. Human Decision Pack

### 25.1 Classification

| 未决项 | 分类 | Safe I2 posture |
|---|---|---|
| joint total attempts / transport retries / validation retries | **B** | positive explicit config；unset ⇒ Shadow activation rejected；tests inject boundary values |
| per-attempt timeout | **B** | interface/enforcement implemented；unset ⇒ disabled |
| absolute decision deadline duration | **B** | field/digest/propagation implemented；unset ⇒ disabled |
| per-decision token/cost budget | **B** | nullable usage provenance + fail-closed budget checker；unset ⇒ disabled |
| advisory queue capacity / finite worker count | **B** | bounded implementation accepts explicit injected values；production activation unset ⇒ disabled |
| Protection-reserved shutdown budget / Advisory cleanup budget | **B** | active-capable Gate A 实现 §20 的 subdeadline 关系；tests 注入明确值；`DISABLED` 可 unset，activation 前 unset/invalid ⇒ rejected |
| primary pool size / finite max overflow / pool timeout（共同定义 `effective_db_capacity`） | **B** | active-capable Gate A 暴露 explicit config/engine facts；`DISABLED` 可 unset；无法证明 capacity 或 overflow unbounded ⇒ Gate A activation rejected |
| Protection-reserved DB capacity / Advisory DB max concurrency | **B** | active-capable Gate A 要求 positive integers 且 `A + R <= C`；`DISABLED` 可 unset，activation 前缺失/非法 ⇒ rejected |
| Advisory DB acquire / transaction / statement / lock / idle-in-transaction timeouts | **B** | active-capable Gate A 要求 positive finite 且满足 §20.1 顺序/cleanup 方程；`DISABLED` 可 unset，activation 前缺失/非法 ⇒ rejected；ordinary owner 可使用全组；caller-owned G2 只消费 statement/lock 数值并 capture/restore，transaction budget cooperative，idle/client cancel 禁止 |
| exact provider/model | **B** | provider-neutral interface only；I2 candidate 不含 real constructor |
| raw provider envelope retention size/duration/access | **B** | retention OFF / columns NULL；normalized/redacted required provenance 仍保存 |
| Gate A Shadow observation window / sufficiency thresholds | **C** | collection counters implemented；no PASS threshold invented |
| superseded-revision pair 的实验分母计数规则 | 归 SE-02D/Gate C aggregation contract（非 D2 决策；记录边界，不算 Human Decision Pack 数值项） | shadow 照常记录 per-invocation facts |

### 25.2 Human Decisions Blocking I2 Implementation

`NONE` —— P1 修复已冻结 lock target/order、terminal model、DB clock authority、
durable admission accounting、core-flush-before-token ordering、caller-owned timeout capture/restore、
immediate try-acquire 与 authoritative-disposition/uncertain-retire lease、
shared-engine DB capacity fence、shutdown ownership，以及 DISABLED direct-literal/no-writer
authority，不再需要人工选设计方向；第二 engine/DSN 未引入、也不需要 Human 选型。
前提：I2 必须接受「production activation disabled when required explicit config is unset」，
且只用 fake/injected provider 做 deterministic tests。**Safe I2
implementation with activation OFF、Pack-B config unset、no provider construction
是可行的**（显式声明，任务 §29 要求）。若 I2 被要求同时真实激活 Gate A，则上表 B 项
立即变成 blocker。

### 25.3 Human Decisions Blocking Real Provider Activation

1. exact Single Primary Provider + exact model/deployment identity；
2. total/transport/validation attempt limits；
3. per-attempt timeout + absolute deadline duration；
4. token/cost budget 与 usage-unavailable policy；
5. queue capacity + finite worker count；
6. Protection-reserved shutdown budget + Advisory cleanup budget；
7. primary pool capacity config、Protection DB reserve、Advisory DB concurrency 与全部
   acquire/transaction/statement/lock/idle timeout；
8. raw envelope retention/access policy；
9. selected provider/model 的 strict structured output、refusal、usage、request-id
   能力验收（PRE-01A §11）。

### 25.4 Human Decisions Blocking Gate A Acceptance Only

- minimum Shadow observation window；
- latency/deadline miss、failure/refusal/schema/stale/late/duplicate/cost 与
  coverage 的 sufficiency/pass thresholds。

## 26. Implementation Batch Proposal

### PRE-01B-I2 — AdvisoryIngress Core / Shadow-Safe Durable Path

一个最小 vertical slice：

1. §24 的 migration + minimal models/constraints（含 Evidence durable accounting 与
   Invocation authoritative final fields）；
2. `DISABLED` epoch 由 original formal Evidence INSERT 直接写 `GATE_A_DISABLED`，无
   writer/fence/extra SQL；active Gate A 的 G2 formal transaction 使用 schema-default
   `UNSTAGED` + explicit core flush + caller-owned immediate try-acquire + all-Advisory nested
   SAVEPOINT + captured/restored statement/lock timeout + through-authoritative-disposition token
   lifetime + uncertain-retire accounting + constant unbound terminal fallback + typed post-commit
   ref（`persist()` 返回值扩展）；
3. Host-owned bounded AdvisoryIngress queue（无 durable `QUEUED`）/ nested auxiliary
   lifecycle / shared-primary-engine `AdvisoryDbFence` / Protection DB reserve /
   Protection-reserved Advisory subdeadline（D1 shutdown step 2 槽位）；
4. adapted immutable snapshot/input builder（binding 含
   evidence_hash/feature_snapshot_hash/deadline）；
5. durable attempt-start / final winner transactions（Evidence predecessor row shared lock +
   Invocation terminal authority + constrained Attempt/AIDecision linkage）；
6. fake/injected provider only，activation default `DISABLED`；
7. identity version literals 冻结清单（§12.2）；
8. deterministic rollback / savepoint-failure+unbound terminalization / DB capacity/acquire/
   statement/lock timeout / full / DB-clock deadline /
   stale（含 supersede two-serialization）/ final linkage / queue ordering / reserved-budget
   shutdown / restart / adverse tests；
9. focused G2/G3/SE-02B/RuntimeHost regression + real disposable PostgreSQL
   transaction evidence（含 admission staging 失败时 G2/Evidence 照常 commit 的
   专项证明）；
10. zero Real API call、zero Gate A activation、zero Gate B/economic mutation。

Real provider adapter selection / contract validation 与 Gate A activation 为后续
独立获批 batch/gate；不得并入 I2。

## 27. Acceptance Criteria（I2 Candidate ready for review 的独立证据要求）

1. active Gate A qualifying formal Evidence + successful invocation/snapshot 同 outer
   transaction；ordering 必须为 explicit G2/Evidence core flush → immediate non-blocking
   token try → `begin_nested()`；token failure = zero Advisory SQL + zero SAVEPOINT。全部
   Advisory-specific work 在 nested SAVEPOINT 原子；caller-owned timeout 只用 captured/restored
   statement/lock，且 restore 在 release 前确认；token 直到 §20.3/§35 exact-generation pool
   observation + owner cleanup success 的 full positive predicate 后才释放。callback-entry、outer
   result、finally、close-start 均不得释放。外层 core failure ⇒ queue/provider/Advisory rows 全为零。
2. **Admission preparation/canonicalization/digest/config-binding/optional persistence 任一失败
   ⇒ nested SAVEPOINT 回滚，G2 facts + formal Evidence (`UNSTAGED`) 仍 commit**；无 partial
   seed/invocation/phantom。第二 SAVEPOINT 或 restart 只能写 constant
   `ADMISSION_FAILED_FINAL / ...UNBOUND / NO_LONG_UNBOUND`，不得读取 mutable config、
   补造 deadline 或创建 Invocation；unbound completeness hole 可查询并阻断 Gate evidence。
3. Capture Anchor without formal Evidence 永不进入 Advisory。
4. initial offer 与 `RETRY_PENDING` retry/recovery re-offer 只发生在对应 commit 后；
   crash-after-commit-before-offer 恢复同一 invocation/ref，不重建 identity 或 Attempt。
5. queue object 只有 frozen ref；consumer durable re-read 并验证全部
   binding/hash（含 feature_snapshot_hash）。
6. queue bounded；无 durable `QUEUED`；full = durable REJECT NEWEST
   （`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`）；
   no block/drop/coalesce；queue rejection 与 durable admission rejection 在 durable
   state/telemetry 上可区分。queue 与 DB capacity no-terminal-producing-Attempt terminal
   必须分别以
   `ADVISORY_QUEUE_REJECTED` / `ADVISORY_DB_CAPACITY_UNAVAILABLE` 持久化，且
   `final_attempt_id=NULL`、`final_decision_id=NULL`；该要求同时覆盖 zero-history 与 retry-gap
   状态，§14.2 exact pair CHECK 必须真实验证。
7. Protection lane 在 queue full、slow provider、provider timeout、admission staging
   failure、Advisory critical failure、Advisory pool wait/statement/lock timeout 下持续工作；
   real PostgreSQL adverse test 证明 `A + R <= C` 且 A 个 wedged Advisory holders 时
   Protection 仍可取得至少一个 reserve connection；holders 集合同时覆盖 ordinary
   Advisory session 与 caller-owned G2 admission，token unavailable 时 G2 zero-wait skip。
8. Gate A consumer constructor/call graph 无 TradePlan/Risk/Execution/Position
   mutation handle。
9. Gate A adversarial valid LONG response 仍产生 zero TradePlan/economic mutation；
   `G3Workflow`、`TradePlanManager`、`persist_trade_plan` 在 Gate A call count = 0。
10. one invocation identity collision-free 绑定 exact
    opportunity/evidence(revision/hash/feature_snapshot_hash)/snapshot/experiment/
    pair/arm/versions/model。baseline/treatment arm tests 必须使用独立构造的 canonical
    digest/preimage，逐字证明 `H("pre01a-arm-v1", pair_id, exact arm label)`；只比较两 arm
    不相等或调用同一被测 helper 生成 expected value 均不构成证据。
11. Invocation 的 Evidence binding immutable：supersede 场景下旧 invocation 只能
    terminalize（`EVIDENCE_SUPERSEDED`），任何改写/换绑/digest 重写测试必须失败；
    N+1 qualifying 时另立新 invocation。
12. retry same invocation/deadline/input；attempt identity 独立且
    start-before-provider durable。
13. N+1 writer 与 N finalizer 使用同一 Evidence N row lock；必须证明
    supersede-first ⇒ N 不可成 current/actionable final，以及 final-first ⇒ N audit
    immutable 但被 N+1 持久 chain 事实屏蔽于未来经济消费。
14. two concurrent completions、retry/shutdown/restart race 只产生一个 Invocation
    authoritative final；五个 terminal fields 可直接查询；final Attempt/AIDecision 必须
    同 Invocation 且 origin constrained；late/duplicate loser 不能覆盖 winner。
15. §14.2 唯一 authoritative no-terminal-producing-Attempt exact pair set 的每个 legal pair
    都必须真实持久化。每个 pair 均需分别证明 State A zero-history 与 State B retry-gap；
    retry-gap fixture 必须预先持久 Attempt #1（允许它已有 provider call）、置
    `RETRY_PENDING`、不创建 Attempt #2，然后持久 legal pair，并证明
    `final_attempt_id=NULL`、`final_decision_id=NULL`、Attempt #1 保留但未链接、当前 cycle
    新增 provider call = zero。exact-pair CHECK 必须在同 Invocation 有历史 Attempt 时仍接受
    NULL `final_attempt_id`；并至少拒绝一个非九-pair且 `final_attempt_id=NULL` 的 terminal、
    一个 status-correct/reason-wrong 与一个 reason-correct/status-wrong near-miss。不得使用
    status/reason wildcard、CHECK subquery、trigger、新 Invocation column 或 fake Attempt。
16. retry-gap deadline 必须证明：Attempt #1 completed → `RETRY_PENDING` → Attempt #2 未创建
    → deadline → `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER` →
    `final_attempt_id=NULL`，Attempt #1 保留。对照 case 在 Attempt #2 start commit 后过期，
    必须使用 `STALE_DECISION / DEADLINE_EXPIRED` 且 `final_attempt_id=Attempt #2`。
17. Evidence supersede、Opportunity/market stale、binding invalid、activation disabled 与 enabled-but-
    incompatible config 都必须以同一 retry-gap shape 证明各自 §14.2 `*_BEFORE_PROVIDER`
    pair + NULL final Attempt，并以 Attempt #2 start commit 后的 current-Attempt mapping 作对照。
    禁止从历史 Attempt 总数推断 provenance。
18. queue retry/recovery re-offer rejection、DB capacity unavailable 与 shutdown 必须各有 retry-gap
    证明：历史 Attempt/provider call 可存在，当前 cycle 新增 provider call = zero，
    `final_attempt_id=NULL`，不伪造 Attempt #2。shutdown 的 current ACTIVE Attempt #2 对照必须
    使用 `SHUTDOWN_CANCELLED_ACTIVE_ATTEMPT` 并引用 Attempt #2。另必须证明 true retry
    exhaustion 引用 last terminal-producing Attempt 并保留 `RETRY_EXHAUSTED`，不误入 NULL set。
    负向不变式：Attempt #1 绝不能仅因为它是 latest historical Attempt 而成为后续
    retry-gap terminal 的 `final_attempt_id`；Attempt #2 row count 必须仍为 zero。
19. all expiry/stale phases（六维度 × 六时点）匹配 §19；每个维度必须同时证明
    zero-history、retry-gap 与 current-Attempt exact behavior。restart 对
    UNSTAGED/ADMISSION_FAILED_FINAL/ADMITTED/ACTIVE/RETRY_PENDING/FINAL 均匹配 §15，
    且 RETRY_PENDING 恢复在新 Attempt commit 前触发 terminal predicate 时使用 retry-gap
    semantics，不伪造下一 Attempt。
20. failure matrix 全部有 targeted tests；无 baseline fallback / fake-AI substitution。
21. deadline authority/propagation 匹配 §17：PostgreSQL single-read timestamp、UTC/
    precision/canonical serialization、duration+version 持久化、queue/retry 消耗同一 budget。
22. Advisory 在其 subdeadline 到达时关闭新 acquisition；fence-owned session 可
    cancel/rollback/close/invalidate。caller-owned G2 session 禁止 client task cancellation/
    idle-in-transaction timeout，只能让 server statement/lock timeout 触发后 rollback nested
    SAVEPOINT，或在下一条 statement 前 cooperative stop；不能仅为停止 Advisory 被
    invalidate 或强制回滚 valid G2 truth；token 保持 counted/retired 直到 authoritative
    disposition。即使最多 A 个
    connection 延迟退出，Protection 不等待并使用 reserve R；不 dispose shared engine，
    不要求 per-Invocation cancellation final。
23. Gate A health fail closed 不取消/阻塞 safety sibling；shared Host fatal 沿用 I1；
    DISABLED 与 GATE_A_SHADOW 的 readiness 影响按 §21.2 裁定。
24. activation default disabled；`DISABLED` startup epoch 不构造 ingress/provider/worker/
    fence/full writer，original Evidence INSERT 直接写 literal `GATE_A_DISABLED`，Pack-B
    capacity/timeout config 可 unset；不能冻结 valid classification 时 DB default
    `UNSTAGED`。从 DISABLED 激活必须是另行授权的新 epoch。active Gate A 缺任何 required
    B 类 config 或请求 Gate B 均 startup/activation fail closed。
25. exact allow-list tables 之外零写；Production/Live/Real API = zero。
26. no G2 state-machine、G3 economic、Risk、Execution、Accounting、Protection
    semantic regression；SE-02D 边界（§23.3）零触碰（`aggregation_snapshot.py`
    import count in advisory path = 0）。
27. Advisory call graph 只能取得 `AdvisoryDbFence`，raw engine/session-factory capability
    injection count = 0；provider await 时 token/session/transaction count = 0；ordinary path 的
    acquire/checkout/statement/lock/idle timeout，与 caller-owned path 的 captured/restored
    statement/lock/cooperative budget，必须分别验证；禁止把 ordinary-path cancel/idle contract
    套到 caller-owned session。
28. `DISABLED + Pack B unset`、ordinary Evidence INSERT、Evidence INSERT failure，以及
    restart `UNSTAGED/GATE_A_DISABLED` 必须逐案证明 §33.7 的 durable/owner/provider/
    Protection/restart outcome；DISABLED Evidence 永不 retroactive 绑定 experiment/pair/arm。
29. connection release adverse tests 必须覆盖：normal checkin 时 callback 内 checkedout 仍 active、
    awaited owner close/context-exit 成功后才 release；checkin 被观察但后续 listener/return step
    抛错；checkin-only；owner-success-only；cleanup cancellation/unknown；duplicate/late 两类 signal；
    successful hard invalidation + checkin(None) + successful owner cleanup；invalidation/close unknown；
    process death/restart。任何不满足 exact-correlated full predicate 的 lease 不得增加 available
    token；uncertain count > 0 时 Gate A fail closed，Host shutdown 不得报告 clean STOPPED。

## 28. Risk Register

| Risk | Treatment |
|---|---|
| 把 Capture Anchor 当正式 Opportunity | producer 必须验证 exact Evidence row/invocation FK；anchor-only ignored |
| G3Workflow 产生 TradePlan | Gate A 禁用其类型/handle + call-count + table-delta tests |
| G2 transaction rollback 却已 enqueue | queue touch 严格 post-commit；typed result 在 transaction exit 后返回 |
| commit→enqueue crash 丢任务 | durable `ADMITTED` scan，same invocation recovery |
| admission staging 失败摧毁 G2 truth | base Evidence 仅 schema-default `UNSTAGED`；全部 Advisory work 在 nested SAVEPOINT；failure 只留 `UNSTAGED`/constant unbound terminal，outer G2 可提交（§8.3） |
| staging failure 被未来 config 重新解释或从 experiment accounting 消失 | `UNSTAGED` restart 只允许 constant `...UNBOUND` terminal；不补 seed/deadline/arm；独立 completeness-hole accounting 阻断 Gate evidence |
| queue full 删样本/阻塞行情 | REJECT NEWEST + durable final；non-blocking offer；scanner/protection lanes 隔离 |
| queue rejection 被误分类为 provider failure | `CAPACITY_BLOCKED` 映射 + 与 admission rejection 的 durable 区分 |
| canonical head 误作 admission identity | §9 显式区分 + advisory path 禁 import aggregation_snapshot（AC-21） |
| supersede 检查与 final commit 之间 TOCTOU | N predecessor Evidence row 被 writer/finalizer 共享 `FOR UPDATE`；持锁重读（§10.1） |
| final 后 supersede 仍被未来 Gate B 消费 | N+1 durable chain row 为 actionability authority；Gate B 必须同锁重验，不改写历史 final |
| legacy decision_id collision | invocation-derived final id + partial unique linkage |
| two provider completions 双 winner / final 来源只能靠 timestamp 猜 | Invocation five terminal fields + row lock + completeness/FK constraints + one transaction |
| retry 重置 deadline/arm | immutable invocation facts；attempt 不得覆写 |
| restart 用新 config 重配旧 decision | invocation self-contained；old row 不读新 experiment/model 重建 identity |
| provider alias/model drift | configured + provider-reported exact identity 分别保存；unknown != configured |
| Advisory failure/backlog 耗尽 Protection shutdown window | Host 预留 Protection budget + Advisory subdeadline；到点立即停 DB cleanup，无 per-row final 前置 |
| Advisory 耗尽 shared pool 或在 provider I/O 中长期持 connection | Host-owned `AdvisoryDbFence`；`A + R <= C`；Advisory 无 raw session capability；token 覆盖 checkout→matching pool observation + owner cleanup success；provider await 持 DB = 0 |
| G2 持 caller-owned connection 等待 token，或 SAVEPOINT/callback 后提前 release | explicit core flush 后、begin_nested 前 immediate non-blocking try-acquire；失败 zero-wait/zero SQL/zero SAVEPOINT；成功 token 覆盖 SAVEPOINT + outer result + exact pool observation + owner cleanup completion；checkin/invalidate/close callback 单独不释放，unknown retires capacity |
| Advisory statement/lock/rollback 越过 Protection handoff | fence-owned path 可用 server statement/lock/idle + owned client cancellation；caller-owned 只用 captured/restored statement/lock + cooperative budget，禁用 idle/client cancel；pending/uncertain 仍计入 A 并留 R reserve |
| shutdown 为停止 Advisory 破坏 valid G2 truth | caller-owned connection 始终由 G2/core owner 管理；subdeadline 只拒绝新 work 并尽可能取消 nested work，不得 solely-for-Advisory invalidate/force outer rollback；token 如实计数到 return |
| DISABLED 仍要求 writer/fence/Pack-B，或事后补绑 | startup epoch 冻结 literal；original Evidence INSERT 直接写 `GATE_A_DISABLED`；无 writer/fence/extra SQL；Pack-B capacity/timeouts 可 unset；激活须新授权 epoch，历史 Evidence 永不补绑 |
| durable QUEUED 与 process queue 顺序歧义 | 删除 QUEUED；queue 只 wake-up；consumer 先原子 `ADMITTED -> ACTIVE` + Attempt |
| raw envelope 泄密/无限增长 | retention OFF until approved；redaction + size/TTL/access decision required |
| Shadow result 被未来代码误接 economic path | activation enum、constructor allow-list、Gate B startup reject、table mutation tests |
| 身份编码非单射 | versioned canonical JSON；禁未转义 join；conflict 标识符单元素元组 |
| SE-02D 分母问题被 D2 越权决定 | 显式归 SE-02D/Gate C（§23.3）；D2 只保 per-invocation identity |

## 29. Explicit Non-Goals / Overengineering Check

明确不设计/不引入：Kafka、Redis、Celery、RabbitMQ、Kubernetes、microservice split、
LangGraph、generic agent runtime、LiteLLM Router、model voting、automatic provider
fallback、distributed workflow engine、new event bus、generic saga framework、第二套
完整 G3、第二个 RuntimeHost、in-process process supervisor、outbox 通用框架、
metrics platform。

默认并保持：Modular Monolith、one RuntimeHost、one process、bounded in-process
queue、PostgreSQL durable authority。当前 repository truth 足以满足 correctness；
无证据需要扩大基础设施。

## 30. Design Verification / Candidate Verdict

本 Artifact 的验证边界为 repository/source/diff 静态检查 + 实时 git 真值：

- Global Protocol v1.1.0 / ACCEPTED @ `07e2df8…`（ls-remote 实测）；
  `origin/main = main = a90c5968…`（fetch/rev-parse 实测）；无 baseline drift；
- 两份 Accepted Contracts（PRE-01A-D1、PRE-01B-D1）完整重读；SE-02D-I02/I03/Overall
  latest-main 真值重读；DECISIONS/AI_CONTEXT/PROJECT_STATE 相关 accepted 条目重读；
- G2 formal transaction / EventRuntime / capture+qualifies / G3 Workflow·Decision·
  Queue / RuntimeHost ownership·isolation·shutdown / DB schema / attribution 调用点
  在 latest main 上实读复核（§1.4）；
- reviewed candidate merge base `d1e5534` → latest main `a90c5968` delta 实测分类（§1.1.1/§32.9）；
- production/tests/migration/schema/runtime/state docs = zero change；
- Candidate 必须由 Independent Reviewer 重新读取 source/diff 后裁决；本作者不
  Human Accept。

```text
Producer Boundary = DISABLED: original Evidence INSERT literal GATE_A_DISABLED；
                    ACTIVE: schema-default UNSTAGED + immediate caller-owned token try +
                    all-Advisory SAVEPOINT（同 G2 formal transaction）
Admission Gap Authority = UNSTAGED / ADMISSION_STAGING_FAILED_UNBOUND；
                    restart 只做 constant terminal，不构造 seed/deadline/config binding
Admission Evidence Identity = admission transaction 内 staged 的 exact Evidence
                    revision（opportunity/evidence_id/revision/evidence_hash/
                    feature_snapshot_hash），不是 SE-02D canonical head
Superseding Evidence Policy = N predecessor Evidence row shared FOR UPDATE；
                    supersede-first fences N final；final-first 保留 audit 但未来 non-actionable
Gate A Consumer = ShadowAdvisoryDecisionPath with provenance-only write allow-list
G3Workflow = DO NOT USE IN GATE A
Invocation Authority = deterministic AdvisoryAdmissionWriter（attempt 1 前，
                    admission transaction 内）
Final Authority = Invocation final_status/reason/finalized_at/final_attempt_id/
                    final_decision_id + constrained Attempt/AIDecision origin
Queue = bounded / non-blocking / no durable QUEUED / REJECT NEWEST /
                    durable CAPACITY_BLOCKED terminal
Deadline Authority = PostgreSQL statement_timestamp single read + persisted integer-ms
                    duration/version；UTC TIMESTAMPTZ(6) canonicalization；queue/retry 消耗同一 budget
Stale Policy = 六维度 × 六时点矩阵，全部 zero risk increase
Shutdown / Restart = Protection-reserved budget + Advisory subdeadline；到点停 DB cleanup；
                    cancel-not-drain；UNSTAGED 无配置终态化；非终态 Invocation durable recovery
DB Resource Fence = one Host-owned primary engine；A + R <= C；Advisory capability-only
                    session access；ordinary path bounded acquire/transaction/statement/lock/idle；
                    caller-owned captured/restored statement+lock only，no idle/client cancel；
                    core flush -> token -> SAVEPOINT；token held through exact pool observation +
                    owner cleanup success full predicate；callback-entry alone never releases；
                    unknown cleanup retires capacity and Gate A fails closed；
                    provider I/O holds zero DB resource
DISABLED Authority = frozen startup-epoch literal；no ingress/provider/worker/fence/full writer；
                    Pack-B capacity/timeouts may remain unset；activation requires new authorized epoch
Gate A vs Gate B = explicit activation level；Gate B startup fail-closed until approval
SE-02D-I02/I03 Runtime Reuse = NONE（仅概念性复用 accepted canonicalization 语义）
Schema = reuse Evidence chain/attribution + minimal Evidence/Snapshot/AIDecision
         extensions + two new minimal tables；无 migration（属 I2）
I2 Numeric Blockers = NONE when activation remains disabled and config explicit/unset
Artifact Status = PRE-01B-D2 / ACCEPTED / COMPLETE
Task Status = ACCEPTED / COMPLETE（Human Acceptance 2026-09-17）
```

## 31. Independent Review Finding Dispositions

| Finding | Previous Severity | Disposition | Design Change | Residual Risk |
|---|---|---|---|---|
| `PRE01B-D2-RR-P1-01` | P1 | **CLOSED / PRESERVED BY RR02** | schema-default `UNSTAGED` 是 active path SAVEPOINT 外 marker；全部 active Advisory preparation/persistence 在 nested SAVEPOINT；failure 只留 unbound constant terminal/no mutable rebind；DISABLED 无 optional write | 真实 schema/migration/savepoint failure race 仍待 I2 独立实现与 PostgreSQL 验证 |
| `PRE01B-D2-RR-P1-02` | P1 | **CLOSED** | supersede writer/finalizer 共享 predecessor Evidence row lock；固定 lock order/re-read/commit；final-then-supersede 由 durable N+1 chain 使旧 final 未来 non-actionable | 所有 Evidence writer 必须在 I2 审计为同一锁协议 |
| `PRE01B-D2-RR-P1-03` | P1 | **CLOSED** | Invocation 五个 final fields 为唯一终态权威；Attempt/AIDecision 同 Invocation/origin composite FK 与原子 terminalization | deferred composite constraints 与 legacy-row compatibility 待 migration review |
| `PRE01B-D2-RR-P1-04` | P1 | **CLOSED** | PostgreSQL `statement_timestamp()` 单次 CTE；TIMESTAMPTZ(6)/UTC/canonical serialization；duration/version 持久；restart/config reload/queue delay 语义冻结 | 数值 duration 仍是 B 类 activation decision |
| `PRE01B-D2-RR-P1-05` | P1 | **CLOSED / ORIGINAL RESOURCE-FENCE DIRECTION PRESERVED BY RR02** | one primary engine capacity authority + Host-owned `AdvisoryDbFence` + `A + R <= C` + capability isolation + bounded checkout/statement/lock/transaction + deterministic handoff；caller-owned lifetime gap separately closed in §33 | capacity/timeouts 仍是 B 类 activation values；I2 需真实 pool saturation/DB lock/shutdown adverse proof |
| `PRE01B-D2-RR-P2-01` | P2 | **CLOSED** | 删除 durable `QUEUED`；queue 仅 bounded wake-up；consumer 先原子 claim `ADMITTED -> ACTIVE` + Attempt | duplicate-ref/crash/claim DB-failure 需 I2 adverse tests |

Process P2（memory / skills compliance narrative contradiction）仅记录为
`PROCESS P2 / NOT PRODUCT DESIGN BLOCKER`；FIX-01 未修改 `.workbuddy`、memory、skills 或 daily
logs，也不以修改产品设计的方式「修复」该 process finding。

RR02 incremental dispositions：

| Finding | Severity | FIX-03 disposition | Design change | Residual implementation proof |
|---|---|---|---|---|
| `PRE01B-D2-RR02-P1-01` | P1 | **FIX-03 CLAIMED CLOSED / PRESERVED AND TIGHTENED BY FIX-05** | caller-owned G2 connection 只允许 core flush 后 immediate non-blocking token try；成功 token 覆盖 SAVEPOINT、outer result 与 exact pool observation + owner cleanup success；shutdown 不夺取 outer ownership | I2 需真实 PostgreSQL/pool test 覆盖 delayed commit、server timeout、return/invalidation uncertainty 与 truthful token metrics；caller-owned client cancellation 已禁止 |
| `PRE01B-D2-RR02-P1-02` | P1 | **FIX-03 CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW** | DISABLED 使用 frozen startup literal 随 original Evidence INSERT 写 `GATE_A_DISABLED`；无 ingress/provider/worker/fence/full writer/extra SQL；Pack-B capacity/timeouts 可 unset | I2 需证明 DB-default fallback、insert failure、restart immutability 与 no retroactive binding |

RR03 incremental dispositions（FIX-04 historical；FIX-05 current disposition in §35）：

| Finding | Severity | FIX-04 disposition | Design change | Residual implementation proof |
|---|---|---|---|---|
| `PRE01B-D2-RR03-P1-01` | P1 | **FIX-04 CLAIMED CLOSED / RR04 PRESERVED CLOSED** | caller-owned timeout 仅 SAVEPOINT 内 captured/restored `statement_timeout` + `lock_timeout`；release 前恢复；restore failure rollback；禁用 idle timeout/client cancellation | I2 需把实测 probe 变成 production-call-chain PostgreSQL adverse tests，并证明全部 caller-owned SQL 受 server bound |
| `PRE01B-D2-RR03-P1-02` | P1 | **FIX-04 CLAIM REJECTED BY RR04 / FIX-05 CLAIMED CLOSED** | checkin callback 只记录 pool observation；exact-generation pool observation + owner cleanup success two-factor predicate 才释放；failure/unknown retains capacity | I2 需证明 public-surface correlation、owner wrapper、late/duplicate once-only、real driver cleanup failure 与 restart telemetry |
| `PRE01B-D2-RR03-P2-01` | P2 | **FIX-04 CLAIMED CLOSED / RR04 PRESERVED CLOSED** | explicit core flush → immediate token try → `begin_nested()`；token failure zero Advisory SQL/zero SAVEPOINT | I2 需 SQL trace/spy + real PostgreSQL 证明 core flush failure/token failure/implicit preflush adverse ordering |

## 32. FIX-02｜RR01 P1-01 + P1-05 Latest-Main Closure Contract

本节记录 FIX-02 的集中 disposition；其仍-current 内容与 §0.5、§8、§20、§24～§31
共同解释。RR02 指出的 caller-owned lease 与 DISABLED path 由 §33 修正并最终控制；本节
已同步删除相反的 release/writer/shutdown wording。
若 failed FIX-01 的历史措辞与本节冲突，以本节为准；历史时间点的 baseline/status 事实不被
改写。

### 32.1 RR01 verdict / exact scope

```text
PRE-01B-D2-RR01 = FAIL — FIX REQUIRED
P1-01 = OPEN IN FAILED CANDIDATE -> FIX-02 CLAIMED CLOSED / AWAITING RE-REVIEW
P1-05 = OPEN IN FAILED CANDIDATE -> FIX-02 CLAIMED CLOSED / AWAITING RE-REVIEW
P1-02 / P1-03 / P1-04 / P2-01 = REMAIN CLOSED
P3-01 = REFRESHED TO LATEST ACCEPTED MAIN
```

只修改 transaction isolation、unbound admission terminal semantics、DB resource fence、
相关 Pack/AC/metrics，以及 latest-main/SE-02D 描述；不重开其余已通过语义。

### 32.2 P1-01 root cause and corrected contract

**Root cause**：failed candidate 在 outer G2 transaction、SAVEPOINT 之外执行完整
`AdvisoryAdmissionSeed` construction/canonicalization/digest/config binding，并持久
`RECOVERY_REQUIRED` accounting。任何只属于 Advisory 的异常都可能把 SQLAlchemy session
置为 failed/rollback-only，最终回滚 valid G2 facts + formal Evidence。

**Corrected exact boundary**：

```text
OUTER G2 TRANSACTION (core authority)
  write G2 facts
  write formal SE-02A Evidence
    -> DB schema supplies literal advisory_admission_state = UNSTAGED
    -> no seed/config/digest/optional Advisory statement

  explicit flush G2 + Evidence core state
    -> failure = legitimate core failure; no token / SAVEPOINT / Advisory SQL

  immediate non-blocking try-acquire caller-owned Advisory lease
    -> unavailable = zero Advisory SQL + zero SAVEPOINT; keep UNSTAGED

  NESTED SAVEPOINT #1 (all Advisory work)
    capture exact caller statement_timeout / lock_timeout
    SET LOCAL Advisory statement_timeout / lock_timeout
    activation classification
    one PostgreSQL admission clock
    build/canonicalize/digest complete seed
    bind config/experiment/pair/arm/provider/model/deadline
    write Snapshot + Invocation(ADMITTED)
    UNSTAGED -> INVOCATION_CREATED
    restore exact caller timeout values; mismatch/error => rollback SAVEPOINT
    RELEASE SAVEPOINT only after restore confirmation

  keep token through SAVEPOINT + outer commit/rollback + connection disposition

  on any Advisory-only error:
    rollback SAVEPOINT #1 only
    NESTED SAVEPOINT #2 best effort:
      UNSTAGED -> ADMISSION_FAILED_FINAL /
                  ADMISSION_STAGING_FAILED_UNBOUND /
                  NO_LONG_UNBOUND
    if #2 also fails: keep UNSTAGED

COMMIT OUTER G2 TRANSACTION unless a genuine core PostgreSQL/G2/Evidence failure occurred
G2/core owner dispositions token only after exact-generation pool observation + successful owner
cleanup full predicate (explicit invalidation additionally requires hard-invalidate + checkin(None));
unknown cleanup retires capacity and never increments availability
```

`UNSTAGED` 是 first durable marker，不是“DB write 不会失败”的假设：若 PostgreSQL 无法持久
canonical G2/Evidence row，core transaction 可合法失败；保证仅覆盖在 core Evidence 已可写时，
Advisory preparation/canonicalization/digest/config-binding/optional write 的失败不会再回滚它。

`UNSTAGED` 没有合法 seed/deadline/experiment binding。restart 不允许“稍后用当前配置重试”，
只能写固定 unbound terminal；因此不会 phantom-create Invocation/Attempt/Decision，不修改
SE-02A Evidence identity/hash/payload，也不会把失败样本事后塞进某一 experiment arm。

### 32.3 P1-01 failure matrix

| Failure point | Outer G2/Evidence | Durable Advisory fact | Invocation / Attempt / Decision | Accounting / next action |
|---|---|---|---|---|
| PostgreSQL/connection/core G2 integrity failure before/at Evidence write | may rollback | none required | none | legitimate core failure；不声称 G2 survives |
| caller-owned immediate token try unavailable before SAVEPOINT work | commits if core valid；zero wait | `UNSTAGED` | none | no Advisory SQL；restart constant unbound terminal；Gate A fail closed where completeness requires |
| seed construction / canonicalization / digest failure | commits if core valid | `UNSTAGED` or constant unbound terminal | none | durable completeness hole；no mutable rebind |
| config/experiment/pair/arm binding failure | commits if core valid | `UNSTAGED` or constant unbound terminal | none | 不伪造 experiment membership；Gate evidence blocked |
| snapshot/Invocation/FK/optional Advisory persistence failure | commits if core valid | `UNSTAGED` or constant unbound terminal | none（SAVEPOINT rollback） | no partial/phantom row |
| constant terminal SAVEPOINT also fails | commits if core valid | `UNSTAGED` | none | later only retries same constant terminal write |
| successful Advisory SAVEPOINT，outer commit later fails | rolls back atomically | none | none | no post-commit ref / provider |
| successful outer commit，crash before queue offer | committed | `INVOCATION_CREATED` + `ADMITTED` | Invocation only | restart recovers same identity/deadline |

### 32.4 P1-01 restart matrix

| Durable state at restart | Required interpretation | Forbidden |
|---|---|---|
| `LEGACY_PRE_I2` | historical only；not Gate A member | backfill experiment/arm |
| `UNSTAGED` | constant `...UNBOUND / NO_LONG_UNBOUND` terminalization；failure leaves `UNSTAGED` | seed rebuild、current config lookup、new deadline、Invocation/Attempt |
| `GATE_A_DISABLED` | terminal classification；no provider | later activation reclassifies old Evidence |
| `ADMISSION_FAILED_FINAL/...UNBOUND` | immutable completeness-hole fact | attach experiment/pair/arm post hoc |
| `INVOCATION_CREATED` + `ADMITTED` | recover same Invocation/ref under original persisted deadline | new logical decision or config rebind |
| `ACTIVE/RETRY_PENDING/FINAL` | existing §15/§14 rules | deadline reset、new provider/model、second final |

Experiment/treatment accounting is therefore complete in two disjoint surfaces: successfully bound units use exact
experiment/pair/arm Invocation facts；unbound staging failures use a separate durable/queryable coverage-hole count that
prevents a false Gate A/Gate C completeness claim. `UNKNOWN` is not silently interpreted as treatment success/failure.

### 32.5 P1-05 root cause and corrected DB fence

**Root cause**：failed candidate only reserved shutdown time. Current accepted main composes one Host-owned primary
engine/session factory and passes it to G2/Execution/Protection/Recovery; engine construction has no explicit pool
capacity contract. Time budgeting alone cannot stop Advisory from checking out every usable connection, waiting forever,
or carrying a transaction/lock across provider I/O or cleanup handoff.

**Corrected exact fence**：`RuntimeHost` remains sole lifecycle/composition owner；the existing primary engine remains
the sole DB authority。I2 adds a Host-owned capability wrapper, not a new engine：

```text
A = advisory_db_max_concurrency
R = protection_reserved_db_capacity
C = explicit effective primary-pool capacity
A + R <= C

Advisory code receives only AdvisoryDbFence
Protection keeps primary session factory and never takes Advisory tokens
token before Advisory SQL/session checkout
token release only after transaction rollback/commit + exact pool observation + owner cleanup success
caller-owned G2 path uses zero-wait try after explicit core flush and before begin_nested
caller-owned timeout = captured/restored statement+lock only; no idle timeout/client cancellation
provider I/O holds zero token/session/transaction
```

All numeric values are Pack B。Missing/invalid/unbounded/engine-mismatch config, or an injected pool whose `C` cannot be
proven, makes Gate A non-ACTIVE。This task does not authorize a second engine/pool/DSN.

### 32.6 P1-05 resource / shutdown matrix

| Condition | Mechanical action | Protection guarantee | Durable/restart result |
|---|---|---|---|
| `A` tokens held | ordinary no-connection Advisory waits only to bounded acquire deadline；caller-owned G2 zero-wait skips | at least `R` capacity not consumable by Advisory | no new provider；state unchanged/terminalized if possible |
| primary pool checkout timeout after token | attempt bounded close/invalidate；only the matching pool-observation + owner-success full predicate releases，unknown retires token | no false capacity increase；reserve equation counts pending/uncertain within A | exact DB-capacity/cleanup reason；restart under original deadline |
| Advisory statement/row-lock timeout | PostgreSQL aborts statement；wrapper rollback/close；token 仅在 matching pool observation + owner cleanup success 后释放 | no indefinite Advisory statement/lock | Attempt/Invocation failure when writable；otherwise durable prior state |
| provider network I/O | DB token/session count must equal zero | provider latency cannot hold pool/locks | response later uses a new bounded finalizer transaction |
| shutdown begins | close admission + close fence to new leases + cancel provider | no new Advisory checkout | ADMITTED/ACTIVE/RETRY_PENDING remain interpretable |
| cleanup reaches subdeadline | fence-owned session cancel/rollback/close/invalidate；caller-owned G2 禁用 client cancel，只允许 server timeout 后 rollback SAVEPOINT 或 pre-statement cooperative stop；never solely-for-Advisory invalidate/force outer rollback；never dispose shared engine | at most `A` held/pending/uncertain dispositions remain truthfully counted，Protection uses `R` without waiting | incomplete terminal writes stay in prior durable state；G2 follows core lifecycle；uncertain cleanup ⇒ STOP_FAILED |
| Advisory rollback/driver close itself delays/fails | report pool-pending/owner-pending/uncertain/invalidation/over-subdeadline；无 full two-factor predicate ⇒ token retained/retired，wrapper不得伪报 release | capacity arithmetic仍把所有未确认状态算入 A，保留 `R`；Advisory lock allow-list excludes Protection rows | restart treats nonterminal rows honestly；Host stop is not clean |
| Protection needs DB during/after handoff | bypasses Advisory limiter, uses primary factory | Advisory cannot borrow reserve or queue ahead through raw factory | Protection semantics unchanged |

### 32.7 Pack A / B / C update

- **Pack A = NONE**：transaction polarity、unbound terminal semantics、single-engine resource ownership、
  caller-owned zero-wait acquisition/through-return lifetime、limiter capability、reserve equation、
  provider/DB separation、shutdown ownership、DISABLED direct-literal/no-writer authority 均已冻结。
- **Pack B**：joint attempts/retries、decision/provider budgets；queue/workers；shutdown budgets；explicit
  primary pool size/finite overflow/pool timeout；`R`、`A`；Advisory acquire/transaction/statement/lock/
  idle-in-transaction timeout；provider/model；retention policy。所有值须 positive/finite/internally valid；
  capacity/timeout values 在 `DISABLED` 可 unset；进入 Gate A active 前 missing/invalid ⇒ activation rejected。
- **Pack C**：Gate A observation window、latency/failure/coverage/duplicate/cost sufficiency thresholds；不在 D2
  发明 PASS threshold。

### 32.8 Closed-finding non-regression

| Closed finding | FIX-02 re-proof |
|---|---|
| P1-02 Evidence supersede/finalizer TOCTOU | bound Evidence N remains shared `FOR UPDATE` target；lock order remains `Evidence -> Invocation -> Attempt`；resource wrapper changes acquisition only, not lock semantics |
| P1-03 exactly one logical durable final | Invocation five terminal fields remain sole authority；Attempt/AIDecision composite origin and atomic finalizer unchanged；unbound path creates none |
| P1-04 clock/deadline | successful admission reads one PostgreSQL clock inside its atomic SAVEPOINT and persists immutable original deadline；restart never resets it；failed/unbound staging creates no fake deadline |
| P2-01 fake QUEUED | durable states remain `ADMITTED -> ACTIVE + Attempt`；process queue is wake-up/backpressure only；DB fence does not add durable queue ordering |

### 32.9 Latest-main and cross-contract compatibility

`adb1364… -> a90c5968…` 的 relevant source delta 只有 accepted SE-02D-I03 aggregation orchestration/package
description，以及状态/设计收尾；G2/G3/G4/RuntimeHost/DB/session/migration head 与 failed candidate 审计基础在该
区间无材料性改变。Current migration head remains `20260913_0009`；D2 不创建 migration。

**PRE-01A-D1 re-proof**：

- placement 仍仅 `C. Trade Decision`；AI 仍 Advisory，deterministic validator/Risk/Execution 为 Authority；
- one `decision_invocation_id` 仍仅一个 logical durable final；unbound failure不创建 fake Invocation/final；
- Single Primary Provider；no automatic fallback/model voting；retry 同 provider/model/input/deadline；
- failure taxonomy/precedence 保持，DB capacity 是 explicit `CAPACITY_BLOCKED`/diagnostic，不转 baseline BUY；
- baseline = `ALL_ELIGIBLE_LONG_SHADOW_V1`；unbound coverage hole诚实阻断完整性，不伪造 arm；
- Gate A/B/C 分离不变，任何本设计完成均不等于 activation/edge/Live。

**PRE-01B-D1 re-proof**：

- one `RuntimeHost` 仍是唯一 lifecycle/composition owner；FastAPI lifespan activation boundary 不变；
- Advisory wrapper/finite workers 仍在 Host structured concurrency 内，无 detached task/resource owner；
- Protection 不取得 Advisory limiter、queue/lock/task failure domain；shared engine ownership不变但 resource
  capacity被机械 fencing；
- queue bounded/nonblocking；shutdown 在 accepted step 2 槽位关闭 Advisory，engine 仍最后 dispose；
- no second production DB authority、no service/process supervisor、no broad Host/G2 redesign。

### 32.10 SE-02D refresh / implementation readiness / non-claims

Current accepted truth：`SE-02D = ACCEPTED / COMPLETE`；`SE-02D V1 CAPABILITY COMPLETE AFTER I03`；
`I04 = NOT REQUIRED`。仍保持：experiment/pair/arm = OPEN Gate C prerequisite；arm-level selection
Expectancy/delta = FUTURE CONSUMER；durable regime identity = OPEN；Gate C immutable evidence retention =
FUTURE TASK；Gate C NOT PASSED；Real AI NOT ACTIVATED；Live NOT AUTHORIZED。历史日期明确的旧状态不改写。

FIX-02 后，future PRE-01B-I2 不需再选择以下架构：G2/advisory transaction isolation、admission failure
polarity、unbound terminal/restart state、DB capacity authority、Advisory concurrency/reserve equation、checkout/
statement/lock behavior、provider/DB separation、shutdown handoff。只有 Pack-B 数值留待 implementation/
activation config。FIX-02 在当时的候选作者声明为（historical candidate status；current FIX-03
verdict 见 §33.9）：

```text
PRE-01B-D2-FIX-02 = FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW
HUMAN ACCEPTANCE = NOT PERFORMED
IMPLEMENTATION AUTHORIZED = NO
MIGRATION / RUNTIME CHANGE / ACTIVATION = NO
```

非声明：本文件不 Human Accept D2、不实施 I2、不修改 schema/runtime/config/test、不激活 Gate A/B/C、
Real AI 或 Live；不声称 provider/edge/profitability 已验证；不声称 production numeric sizing 已决定。

## 33. FIX-03｜RR02 Caller-Owned Lease + DISABLED Authority Closure Contract

本节是 FIX-03 的最终 normative disposition。若 §7、§8、§20、§21、§24、§25、§27、
§30～§32 的 current wording 与本节冲突，以本节为准；上述各节已同步修正，不允许 future
I2 executor 在 acquisition blocking、token lifetime、shutdown ownership 或 DISABLED writer/fence
上再次选择设计。

### 33.1 RR02 verdict / exact scope

```text
PRE-01B-D2-RR02 = FAIL — FIX REQUIRED
RR02 P1-01 = FIX-03 CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW
RR02 P1-02 = FIX-03 CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW
RR01 P1-01 / P1-02 / P1-03 / P1-04 / P1-05 / P2-01 = REMAIN CLOSED
```

本轮只修 caller-owned G2 connection lease 与 DISABLED authority。Evidence identity/hash、
supersede/finalizer locks、Invocation final authority、PostgreSQL original deadline、no fake
durable `QUEUED`、provider/DB separation、Gate A/B/C 边界均不重开。

### 33.2 Caller-owned G2 lease authority

1. G2 caller 始终拥有 outer transaction、G2 session、valid G2/Evidence commit/rollback 与
   final connection return。`AdvisoryDbFence`/writer 只拥有 bounded token/capability 与
   Advisory-specific operations，绝不取得整个 G2 transaction ownership。
2. G2 已持 connection 时，Advisory admission token 只能 **immediate non-blocking
   try-acquire**。持 connection 期间不得 queue、await 或 timeout wait；不得为取得 token
   再 checkout 第二 connection。该 try 是 Host-owned in-process limiter operation，不能
   执行 SQL 或 checkout connection。G2/core owner 将 already-owned session 绑定到返回的
   `CallerOwnedAdvisoryLease` capability；writer 只使用该 lease，不接收 raw engine/session
   factory，也不得 close/invalidate/commit/rollback outer resource。
3. G2/Evidence explicit core flush 成功后、`begin_nested()` 前才可 try-acquire。try-acquire
   失败：zero Advisory SQL、zero SAVEPOINT、zero provider；preserve outer
   G2/Evidence transaction；Evidence 保持 schema-default `UNSTAGED`，沿 deterministic
   unbound-failure/restart accounting；需要 completeness 的 Gate A fail closed。
4. try-acquire 成功：该 caller-owned connection 立即成为一个 counted Advisory holder。
   token 覆盖所有 Advisory SAVEPOINT work、outer commit/rollback，并持续到 connection
   exact-generation pool observation + owner cleanup success full predicate；explicit invalidation
   还要求 hard-invalidate observation + `checkin(None)`。SAVEPOINT release、outer
   transaction completion 回调、进入 `finally`、close-start 或 process-local ref publication
   都不得提前 release。
5. only the G2/core owner 启动 session return/cleanup；owner lifecycle wrapper 只在 awaited
   `AsyncSession.close()` / context-exit / `AsyncSession.invalidate()` 成功返回后报告 exact
   owner-completion fact。lease registry 将该 fact 与 same epoch/entry/generation/lease/cleanup-attempt
   的 checkin/invalidation observations 合取；任何 callback 单独都只是 pending observation。
   cleanup started/raised/cancelled/unknown 或 owner notification missing 时 token 必须
   `RETURN_UNCERTAIN_RETIRED`，writer/G2 `finally` 均不得释放；late full predicate once-only，
   duplicate/old-generation signal no-op。完整状态机与 metrics 见 §20.3/§35。

### 33.3 Acquisition failure matrix

| Path | Connection at request | Acquisition | Wait | Advisory SQL/provider | Durable/Gate result |
|---|---|---|---|---|---|
| caller-owned G2 admission | already held by G2 | immediate try only | exactly zero | unavailable ⇒ none/none | `UNSTAGED` + deterministic unbound handling；Gate A completeness fail closed |
| ordinary Advisory start/finalizer/recovery | none held | bounded fence acquire, then at most one checkout | Pack-B deadline clipped by invocation/shutdown | unavailable ⇒ zero provider/new SQL except a later separately leased terminal write | prior durable state retained；restart uses original identity/deadline |
| shutdown closed fence | none or caller-owned without token | reject new acquisition | exactly zero | none | no new work；prior durable state retained |

No path may borrow `R`, fall back to raw session factory, or turn capacity failure into baseline
participation/BUY.

### 33.4 Shutdown ownership and truthful handoff

At Advisory subdeadline the Host rejects new Advisory work/token and cancels provider work。
Fence-owned Advisory sessions may be client-cancelled、closed/invalidated within the bounded
cleanup contract。caller-owned G2 work only receives cooperative stop-before-next-statement plus
server statement/lock timeout；Host 不以 task cancellation 打断其 in-flight SQL。A caller-owned G2 connection must
**never** be invalidated solely to stop Advisory, and otherwise-valid G2 truth must not be forcibly
rolled back. Its outer transaction follows accepted core RuntimeHost lifecycle; its token remains
held/counting until §20.3/§35 full pool-observation + owner-completion predicate；cleanup unknown
时 retire、不得回补。

If that core G2 operation remains active after Advisory subdeadline, it is still one of at most
`A` counted Advisory-induced holders（含 return/invalidation pending 与 uncertain-retired）。Host health/metrics must expose it as held/over-subdeadline，
not released。Protection does not wait for those holders：it bypasses the Advisory limiter and uses
the remaining reserved capacity `R`。Shared engine is still disposed only by Host at accepted final
shutdown step。

### 33.5 Capacity proof

Let `H_o` be ordinary fence-owned Advisory sessions，`H_g` caller-owned G2 connections whose
Advisory try-acquire succeeded，`U` all not-yet-confirmed dispositions（checkin observed but owner
not complete、owner complete but no pool confirmation、cleanup error/cancel/unknown、uncertain
invalidation）。The single limiter enforces：

```text
H_o + H_g + U <= A
A + R <= C
C - (H_o + H_g + U) >= C - A >= R
```

Each token is bound to exactly one distinct primary connection for its full counted lifetime；
one connection cannot hold multiple Advisory tokens，and one lease cannot open a second/nested
connection。

- `A` ordinary Advisory sessions：`H_o=A, H_g=0`；new G2 try fails immediately，reserve `R`
  remains outside Advisory reach。
- caller-owned admissions：each successful G2 try consumes one of the same `A` tokens；they do
  not form a second uncounted class。
- token unavailable while G2 holds connection：zero wait means Advisory does not extend that
  uncounted connection lifetime；G2 continues core work without Advisory SQL。
- outer commit / driver return delayed，或 cleanup/invalidation failure：token remains counted or retired
  until exact pool observation + owner cleanup success full predicate；caller-owned client cancellation is forbidden，
  so the inequality stays true and the Host cannot falsely increase headroom。
- Protection new checkout：uses primary factory without Advisory token；even with `A` counted
  holders wedged, Advisory itself cannot consume `R`。

This is an attribution proof only：it does not promise Protection success under unrelated core
overload、all connections consumed by non-Advisory callers、PostgreSQL outage or shared engine
failure。

Only `RELEASE_CONFIRMED` removes one holder from `H_o / H_g / U` once。Pool callback entry、
owner-success-only、invalidation event 或 cleanup start 均不改变 available capacity。

### 33.6 DISABLED single authority

1. Host startup freezes one immutable activation classification for the current runtime epoch。
   The value passed to G2 persistence is a typed immutable literal value only，not a callable writer、
   session capability or mutable config reference。
2. If classification = `DISABLED`：no `AdvisoryIngress`、provider、worker、
   `AdvisoryDbFence`、full `AdvisoryAdmissionWriter`、extra Advisory SQL or SAVEPOINT。
3. The existing formal Evidence INSERT directly records literal `GATE_A_DISABLED` from that
   frozen classification。It performs no seed/config/digest/provider preparation and no separate
   optional DB write。The field remains outside Evidence identity/hash/payload。
4. If a valid disabled classification cannot be established，the INSERT omits the override and
   PostgreSQL default `UNSTAGED` is the safe durable fallback。No mutable config lookup may later
   reinterpret it。
5. `GATE_A_DISABLED` Evidence is terminal for that Evidence/epoch and is never retroactively
   assigned experiment、pair、arm、seed、deadline、Snapshot or Invocation。
6. `DISABLED -> active Gate A` requires a separately authorized activation boundary and a new
   explicitly frozen runtime epoch。No silent in-place activation。
7. Pack-B pool/concurrency/timeout values may remain unset throughout `DISABLED`。All become
   mandatory and must validate before a Gate A active epoch can start。

### 33.7 Required 13-case proof matrix

| # / Case | Session owner | Token ownership / lifetime | Durable Evidence state | G2 commit/rollback | Provider call | Protection capacity | Restart action |
|---|---|---|---|---|---|---|---|
| 1. DISABLED + Pack B unset | no Advisory session；Host only freezes classification | none；no fence exists | no row until ordinary Evidence；classification authority = `DISABLED` | N/A | no | normal primary capacity；no Advisory reservation/config required | new process freezes its own epoch；does not mutate old Evidence |
| 2. DISABLED + ordinary Evidence insert | G2 caller owns outer session/connection | none | same INSERT writes `GATE_A_DISABLED` | commit if all core G2/Evidence writes valid | no | unaffected；Advisory consumes 0 | terminal classification；no writer/reclassification/provider |
| 3. DISABLED + Evidence insert failure | G2 caller | none | no new durable Evidence row | outer core transaction rolls back；this is a core write failure | no | unaffected by Advisory | no Advisory recovery row/work；normal core recovery only |
| 4. Gate A + no Advisory token available | G2 caller | explicit core flush 已成功；try 在 begin_nested 前立即失败；none acquired；zero wait | `UNSTAGED` after valid outer commit | valid G2/Evidence commits | no | existing counted holders ≤ A；R remains unavailable to Advisory and available to Protection | only constant unbound terminalization under a later bounded lease；no seed/config/deadline/Invocation；otherwise remain `UNSTAGED` / fail closed |
| 5. Gate A + token acquired + SAVEPOINT success | G2 caller owns outer；writer owns only nested ops | core flush → token → SAVEPOINT；captured statement/lock timeout 在 release 前已恢复；token held through outer result + exact pool observation + owner cleanup success | commit yields `INVOCATION_CREATED` + `ADMITTED` atomically | commit if core valid | none before commit；only post-commit eligible ref may cause provider under original deadline | holder counts within A；R remains | recover same Invocation/ref/deadline；never create new logical identity |
| 6. Gate A + SAVEPOINT SQL/timeout/restore failure | G2 caller | same token remains through rollback-to-savepoint、optional constant-terminal SAVEPOINT、outer result and full two-factor disposition | `UNSTAGED` or constant `ADMISSION_FAILED_FINAL/...UNBOUND` if best-effort write succeeds | valid core G2/Evidence commits when connection remains valid；connection-level termination is core failure，not claimed isolated | no | counted within A until confirmed/retired disposition；R remains | retry only same constant terminal write；never bind mutable config/arm |
| 7. Gate A + outer G2 commit failure | G2 caller | held through rollback、exact pool observation and owner cleanup completion；callback-only/unknown cleanup retains token | no new Evidence/Invocation survives | whole outer transaction rolls back | no | counted within A until full predicate/retired disposition；only `RELEASE_CONFIRMED` restores headroom | no Advisory work for rolled-back row/ref |
| 8. Token acquired + outer commit delayed | G2 caller | remains held/counting for entire delay and through matching pool observation + owner cleanup success；never released at SAVEPOINT/callback-only | uncommitted facts are not durable/visible；eventual result follows case 5 or 7 | pending，then exact commit/rollback branch | no while outer unresolved | Protection does not wait；R remains by equation | crash/DB rollback ⇒ no phantom；commit ⇒ recover same Invocation |
| 9. Shutdown while G2 owns session | G2/core caller | reject new tokens；existing token stays counted；no client-cancel of caller SQL，no forced outer ownership transfer | nested success + outer commit ⇒ case 5；server timeout/SQL error rollback + outer commit ⇒ case 6；outer rollback ⇒ case 7 | core lifecycle decides only | no new call；active provider scope cancelled separately | Protection proceeds on R without waiting | interpret only committed resulting state under cases 5–7 |
| 10. Advisory subdeadline reached before G2 returns | G2/core caller | token remains held/over-subdeadline until full two-factor disposition；pool-only/owner-only/failed cleanup ⇒ pending or uncertain-retired，must not report released | no new durability claim before outer result | do not solely-for-Advisory cancel/invalidate or force rollback；core lifecycle completes | no new call | R remains and Protection proceeds；all unconfirmed states count inside A | after actual result，same committed-state rules；no synthetic cancellation final；STOP_FAILED if cleanup uncertain |
| 11. A holders/pending/uncertain dispositions + Protection needs DB | holders may be ordinary fence-owned and/or caller-owned G2；Protection owns its new session | `H_o + H_g + U = A`；no new Advisory lease；caller G2 zero-wait skips | existing states unchanged until their owners resolve | unrelated core transactions keep their own outcome | no new provider requiring DB；in-flight provider holds zero DB | conservative equation leaves at least R outside Advisory reach；Protection bypasses limiter | prior nonterminal states recover honestly；no false release/headroom |
| 12. Restart with `UNSTAGED` | bounded recovery session only when active-capable config/fence is valid；otherwise none | recovery must acquire an ordinary bounded token before SQL；no caller-owned lease | constant `...UNBOUND / NO_LONG_UNBOUND` terminal if write commits；else stays `UNSTAGED` | no historical G2 rewrite | no | recovery consumes at most one of A；R remains；DISABLED with no fence leaves row unchanged/fail closed | never read current experiment/provider config，never create seed/deadline/Invocation，retry only constant terminalization |
| 13. Restart with `GATE_A_DISABLED` | none | none | remains exactly `GATE_A_DISABLED` | no historical G2 rewrite | no | unaffected | no reclassification、seed、arm、Invocation or provider even if new epoch is active |

These branches are fully selected by durable state、token result and outer transaction result；
implementation may not invent another disabled/wait/release path。

### 33.8 Closed-finding non-regression

| Preserved finding | FIX-03 proof |
|---|---|
| RR01 P1-01 G2 truth isolation | active Advisory remains inside nested SAVEPOINT；token failure executes no Advisory SQL；DISABLED has no optional write，so Advisory-only failure cannot abort valid G2 truth |
| RR01 P1-02 supersede/finalizer TOCTOU | bound Evidence `FOR UPDATE` target、lock order and final actionability unchanged |
| RR01 P1-03 exactly one durable final | Invocation five terminal fields and Attempt/AIDecision origin constraints unchanged；DISABLED/unbound paths create none |
| RR01 P1-04 immutable original deadline | successful active admission still uses one persisted PostgreSQL clock/deadline；unbound/disabled creates none；restart never resets |
| RR01 P1-05 resource fence | same one-engine `A + R <= C` fence now also counts caller-owned G2 connections for their full actual lifetime |
| RR01 P2-01 no fake durable QUEUED | queue remains post-commit bounded wake-up only；DISABLED/token-failure paths never enqueue |

Evidence identity/hash、baseline attribution、provider/DB separation、Gate A/B/C/Real AI/Live
activation boundaries remain unchanged。

- PRE-01A-D1 compatibility：`GATE_A_DISABLED`/`UNSTAGED` create no experiment/pair/arm、
  Invocation、Attempt、Decision or provider call；active success still binds the original immutable
  deadline and exactly-one logical final。
- PRE-01B-D1 compatibility：RuntimeHost remains sole startup/lifecycle owner；DISABLED adds only
  a frozen literal value and no resource owner/task；active caller-owned lease does not transfer G2
  outer transaction ownership or create a second engine/pool/DSN。
- P1-01 SAVEPOINT compatibility：active optional work remains isolated；DISABLED has no optional
  Advisory write，while failure of the original combined Evidence INSERT remains a legitimate core
  transaction failure。

### 33.9 Pack A / B / C and candidate verdict

- **Pack A = NONE**：acquisition blocking rule、caller-owned lease start/end、outer ownership、
  shutdown cleanup、Protection handoff、DISABLED writer/fence/classification/state semantics are
  fully frozen。
- **Pack B**：retains numeric pool/concurrency/timeout/shutdown/queue/retry/provider values。
  Capacity/timeout settings may be unset while `DISABLED`；all required values must validate before
  Gate A active。
- **Pack C**：remains observation/sufficiency thresholds only。

```text
PRE-01B-D2-FIX-03 = FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW
HUMAN ACCEPTANCE = NOT PERFORMED
I2 IMPLEMENTATION = NOT AUTHORIZED
MIGRATION / RUNTIME CHANGE / ACTIVATION = NO
```

## 34. FIX-04｜DB Semantics Proof + Minimal Contract Fix（HISTORICAL / SUPERSEDED IN PART BY §35）

本节保留 FIX-04 当时的 proof 与 candidate disposition。RR04 已拒绝 §34.4 原“checkin callback
单独足以释放”的结论；connection-return completion authority 只以 §20.3/§35 的 FIX-05 规则为准。
§34.3 timeout 与 §34.5 ordering 保持 current/preserved closed。若本节任何 release wording 与
§35 冲突，以 §35 为唯一 normative authority。

### 34.1 RR03 verdict / exact scope

```text
PRE-01B-D2-RR03 = FAIL — FIX REQUIRED
RR03 P1-01 = FIX-04 CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW
RR03 P1-02 = FIX-04 CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW
RR03 P2-01 = FIX-04 CLAIMED CLOSED / AWAITING INDEPENDENT RE-REVIEW
RR01 + RR02 closed findings = REMAIN CLOSED
```

本轮只有 docs contract + new dev_log；zero Runtime/migration/schema/test/config/state/service/provider/
project-DB mutation。I2、Gate A/B/C、Real AI、Live 均未实现、未授权、未激活。

### 34.2 Source and official semantics evidence

Repository facts @ exact FIX-03 base `4548920…`：

- `PostgresG2Repository.persist()` 的 `async with session, session.begin()` 拥有 outer
  transaction/session return；G2 rows 与 `capture_opportunity()` 在同一 transaction；
- `append_evidence_revision()` 对 formal Evidence 执行 `await session.flush()`；因此 FIX-04
  ordering 可在不改变 G2 authority 下要求 explicit core flush；
- `DatabaseResources` 只构造一个 primary engine/session factory，当前 engine 未显式冻结 pool
  capacity；`RuntimeHost` 在 shutdown 最后 dispose shared engine，step 2 仍是 Advisory 槽位；
- SQLAlchemy 2.0 `Session.begin_nested()` 官方文档与 2.0.52 source 均显示：建立 SAVEPOINT
  前无条件 flush pending state；`Session.close()` 负责释放 connection，但 close-start 不等于完成。

Official authority：

- PostgreSQL 16 `SET`：`SET LOCAL` 持续到 **outer transaction end**；只有 rollback 到命令之前
  的 savepoint 会撤销；现代版本 RELEASE SAVEPOINT 不撤销：
  <https://www.postgresql.org/docs/16/sql-set.html>；
- PostgreSQL SAVEPOINT / rollback / release：
  <https://www.postgresql.org/docs/16/sql-savepoint.html>、
  <https://www.postgresql.org/docs/16/sql-rollback-to.html>、
  <https://www.postgresql.org/docs/16/sql-release-savepoint.html>；
- PostgreSQL timeout：`idle_in_transaction_session_timeout` 会终止 idle open-transaction
  session；`lock_timeout` 只在等待 lock 时触发：
  <https://www.postgresql.org/docs/16/runtime-config-client.html>；
- SQLAlchemy SAVEPOINT / unconditional preflush / close / invalidate / pool events：
  <https://docs.sqlalchemy.org/en/20/orm/session_transaction.html#using-savepoint>、
  <https://docs.sqlalchemy.org/en/20/orm/session_basics.html#flushing>、
  <https://docs.sqlalchemy.org/en/20/orm/session_api.html>、
  <https://docs.sqlalchemy.org/en/20/core/events.html>。

Disposable proof stack：PostgreSQL 16.15 / SQLAlchemy 2.0.52 / asyncpg 0.31.0；isolated
container/port/database，未连接 project DB。原始 probe/output 位于仓库外
`E:/Documents/pre-01b-d2-fix-04-evidence/`。

### 34.3 Timeout decision（frozen）

| Owner/path | Permitted | Forbidden | Failure handling |
|---|---|---|---|
| caller-owned G2 session | SAVEPOINT 内 capture exact effective `statement_timeout` / `lock_timeout`；`SET LOCAL` Advisory values；成功路径 release 前以 `set_config(..., true)` restore + verify；cooperative monotonic transaction budget 只在下一 statement 前 stop | `idle_in_transaction_session_timeout`；client task cancellation；Advisory-only connection invalidate；把 SAVEPOINT release 当 restore | SQL/statement/lock/restore error ⇒ rollback-to-savepoint；rollback confirmed + connection valid 才允许 outer 继续；rollback/connection state unknown ⇒ core owner failure path，绝不声称 G2 preserved |
| fence-owned independent Advisory session | bounded acquire/pool timeout；transaction-local statement/lock/idle timeout；owned client cancellation；bounded rollback/close/invalidate | crossing provider I/O；raw factory fallback；borrow R | owner 可丢弃整个 Advisory transaction/session；release authority仍按 §20.3，unknown retires capacity |

`advisory_db_transaction_timeout` 不是 PostgreSQL 16 server parameter。ordinary owner 可用 client
cancellation 收束自己的 whole transaction；caller-owned path 只能 cooperative gate + 每条 SQL 的
server statement/lock fence。client cancellation 实测产生 invalidate + `checkin(None)`，随后 outer
query 为 `PendingRollbackError`，故不能作为 preserving-G2 mechanism。

### 34.4 Connection release decision（RR04 REJECTED / HISTORICAL）

FIX-04 曾把 exact-generation `PoolEvents.checkin` callback 视为 normal return 的 sufficient
positive authority；RR04 的 SQLAlchemy 2.0.52 source/运行反例证明 callback 在
`ConnectionPoolEntry.checkin()` 调用 `pool._return_conn()` **之前**执行。后续 listener 抛错时，
callback 已发生但 close/context-exit 抛错、pool slot 仍 checked out，故该 sufficient-authority
结论被撤销。

保留仍正确的 historical 部分：`PoolEvents.invalidate`/`close` 是 pre-close observation；
close-start/finally/cancel/unknown 不可释放；process death 不制造 release；duplicate/late 必须
once-only。normal return、explicit invalidation、owner completion、capacity 与 shutdown 的 current
完整规则见 §20.3/§35；本节不得被 future I2 当作实现选择。

### 34.5 Token / SAVEPOINT ordering（frozen）

```text
G2 / Evidence core writes
-> explicit session.flush() of core state
-> if core flush fails: outer core failure; zero token / zero SAVEPOINT / zero Advisory SQL
-> immediate non-blocking Advisory token try-acquire
-> if unavailable: zero Advisory SQL / zero SAVEPOINT; keep UNSTAGED
-> session.begin_nested()  # session has no pending state
-> capture timeout values -> apply statement/lock bounds -> Advisory work
-> success: restore + verify -> RELEASE SAVEPOINT
-> SQL/timeout/restore failure: ROLLBACK TO SAVEPOINT
-> optional second constant-terminal SAVEPOINT
-> outer commit/rollback
-> exact-generation pool observation + owner cleanup success full predicate
-> once-only RELEASE_CONFIRMED, or pending/uncertain-retired token
```

SQLAlchemy pre-SAVEPOINT flush 实测 SQL trace = `INSERT core` index 0、`SAVEPOINT` index 1。
所以 token 不能在 `begin_nested()` context 内才取得；否则 core flush 已先发生，且 token failure
无法满足 zero SAVEPOINT。explicit flush + no-pending-state 是实现 AC，不依赖 `autoflush=False`。

### 34.6 Required eight-case proof matrix

| Required case | Disposable PostgreSQL result | Frozen interpretation |
|---|---|---|
| 1. Normal completion | capture/apply/restore/release 后 values = original；normal session exit `checkedout 1 -> 0` + exact `checkin` | FIX-04 observed success，but checkin callback alone is insufficient；FIX-05 requires matching owner cleanup success |
| 2. SQL error | division-by-zero、100ms `statement_timeout`、100ms `lock_timeout` 均在 SAVEPOINT 内报错；rollback 后 outer `SELECT` = 42/43/430 | rollback confirmed 时 outer remains valid |
| 3. SAVEPOINT rollback | rollback 后 statement/lock values 回到 `0`；restore-command invalid-value error 也 rollback，outer `SELECT 431` succeeds | failure path 自动撤销 SAVEPOINT-local values；restore failure 不得 release SAVEPOINT |
| 4. SAVEPOINT release | 未 restore 时 release 后仍为 `1111ms/222ms/3333ms`，不是原值 | proves leakage；success path must explicit restore before release |
| 5. Outer commit delay | former 100ms statement timeout restore 后，outer `pg_sleep(0.25)` = 0.254s success | Advisory timeout 不再影响 completed Advisory 之后的 valid outer work |
| 6. Cancellation | client cancel emits invalidate/close/`checkin(None)`；nested rollback call returns，但 outer query = `PendingRollbackError` | caller-owned client cancellation forbidden；connection termination不能靠 restore挽救 |
| 7. Connection close/return failure | injected rollback-on-close raises；only checkout，checkedout remains 1；explicit connection invalidate later emits invalidate/close/`checkin(None)` and returns to 0；injected invalidate failure leaves checkedout 1/no terminal event | finally/close-start不可 release；explicit invalidation 仍须 matching owner cleanup success；failure/unknown retires token |
| 8. Shutdown while G2 active | `C=3,A=1,R=2`：close-new 后新 Advisory try=false；G2 holder + 2 distinct Protection connections all checked out；G2 outer `SELECT 49` valid；owner cleanup + pool return full predicate 后 held=0 | Host 不夺 G2 owner；Protection 使用 R；token through actual disposition |

### 34.7 Cross-contract / closed-finding non-regression

- RR01 P1-01：core flush 在 token/SAVEPOINT 前完成；所有 Advisory writes 仍只在 SAVEPOINT；
  server SQL/lock error与 restore failure rollback 后 outer 可继续；connection termination 不伪称 isolated。
- RR01 P1-02/P1-03/P1-04/P2-01：Evidence lock order、Invocation terminal authority、single
  PostgreSQL admission clock/original deadline、no durable `QUEUED` 均未改变。
- RR01 P1-05 + RR02 P1-01：`H_o + H_g + U <= A` 保守计数；checkin-only、owner-only、
  cleanup-error/cancel/unknown 与 uncertain invalidation 全部进入 U 且不回补，
  `A + R <= C` 不被虚假 headroom 破坏；caller-owned zero-wait 保留。
- RR02 P1-02：DISABLED 仍为 frozen literal + original Evidence INSERT；no fence/writer/SAVEPOINT，
  Pack-B timeout/capacity 可 unset。
- G2 truth：只有 connection remains valid + rollback-to-savepoint confirmed 时才声称 Advisory error
  isolation；client cancellation/idle timeout 被禁，避免把 Advisory failure伪装为 core success。
- PRE-01A-D1 / PRE-01B-D1：AI 仍 Advisory、one RuntimeHost/one primary engine、provider/DB
  separation、Protection ownership、shutdown final engine disposal不变。

### 34.8 Candidate verdict / non-claims

```text
PRE-01B-D2-FIX-04 = FIX CANDIDATE DESIGN — READY FOR INDEPENDENT RE-REVIEW
HUMAN ACCEPTANCE = NOT PERFORMED
I2 IMPLEMENTATION = NOT AUTHORIZED
MIGRATION / SCHEMA / RUNTIME / TEST / CONFIG CHANGE = NO
PROJECT DATABASE / SERVICE / PROVIDER / GATE / REAL AI / LIVE MUTATION = NO
```

## 35. FIX-05｜Connection Return Completion Authority（CURRENT）

本节是 FIX-05 唯一最终 normative disposition。若 §8、§20、§27、§30～§34 的
connection-return、invalidation、capacity 或 shutdown wording 与本节冲突，以本节为准。
FIX-04 historical title/status/proof 可保留其时间点事实，但不得重新授权 callback-only release。

### 35.1 RR04 verdict / exact scope

```text
PRE-01B-D2-RR04 = FAIL — FIX REQUIRED
PRE01B-D2-RR04-P1-01 = CLOSED（Independent Re-Review PRE-01B-D2-FIX-05 = PASS）
RR03-P1-01 Timeout Semantics = PRESERVED CLOSED
RR03-P2-01 Token/SAVEPOINT Ordering = PRESERVED CLOSED
RR01 / RR02 closed findings = PRESERVED
Human Acceptance = CONFIRMED — 2026-09-17（见文末「Acceptance Record」）
```

本轮只修 connection-return completion authority 及其直接依赖的 capacity/shutdown wording。
zero Runtime/schema/migration/test/config/state-doc/service/provider/project-DB mutation；I2、Gate A/B/C、
Real AI、Live 均未实现、未授权、未激活。

### 35.2 SQLAlchemy 2.0.52 proof and public-surface implementability

Installed source 的 exact sequence 是：

```text
ConnectionPoolEntry.checkin()
  -> clear fairy_ref
  -> dispatch.checkin(connection, entry)
  -> pool._return_conn(entry)
```

故 `checkin` 是 return-path observation，不是“pool return sequence 已成功完成”的 postcondition。
FIX-05 standalone `QueuePool` + ORM/AsyncSession proof（仓库外、无 project DB）得到：

1. normal `Session.close()` / awaited `AsyncSession.close()`：checkin callback 内
   `pool.checkedout() == 1`；owner close 返回后才为 0；
2. registry listener 先观察同代 checkin，后续 checkin listener 注入异常：owner close 抛错、
   `pool.checkedout() == 1`、下一 checkout timeout；callback observation 不可释放；
3. owner-first 与 pool-first 的 application state machine 都只在两事实齐全后 release；
4. duplicate signal release count = 1；generation N late signal 不释放 generation N+1；
5. owner `Session.invalidate()` 真实顺序为 hard invalidate → close → `checkin(None)`，两 callback
   内 checkedout 仍为 1，owner invalidate 返回后为 0；仍只在 owner-success signal 合取后 release；
6. async path 可经 public `AsyncSession.connection()` → `AsyncConnection.info` 读回 checkout key。

Official public surfaces 足以实现，不依赖 monkeypatch/private `_return_conn()`/pool subclass/fork：

- official `PoolEvents` docs（checkin/checkout/invalidate/close）：
  <https://docs.sqlalchemy.org/en/20/core/events.html#connection-pool-events>；
- official `ManagesConnection.info` / `record_info` 与 public `ConnectionPoolEntry`：
  <https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.ManagesConnection.record_info>；
- official async public `AsyncConnection.info` / `AsyncSession.connection()` / `AsyncSession.close()`：
  <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html>；

- Host 在 `AsyncEngine.sync_engine` 注册 public `PoolEvents.checkout/checkin/invalidate/close` listeners；
- checkout listener 为 `ConnectionPoolEntry.record_info` 建立 application-assigned `pool_entry_id`
  并单调增加 `checkout_generation`，同时把 `(runtime_epoch, pool_entry_id, generation)` 写入
  public `PoolProxiedConnection.info`；`record_info` 跨同 entry 的 invalidation/reconnect 保留，
  `info` 只服务当前 DBAPI connection；
- explicit G2/Evidence core flush 成功后、immediate token try 之前，由已 checkout 的
  `await session.connection()` 返回 public `AsyncConnection`，从 `.info` 捕获 exact key；
  该 accessor 复用当前 transaction connection，不执行 Advisory SQL，也不引入第二次 checkout；
  不按 DBAPI address、Session identity、timestamp 或 callback order 猜关联；
- token 成功后 registry 绑定 exact key + `lease_id`；owner lifecycle wrapper 在 cleanup 开始前
  注册 application-owned `cleanup_attempt_id`，使 callback fact 与 owner result 属于同一次 cleanup；
- 所有 callback 只做 bounded process-local fact recording；owner wrapper 在 awaited cleanup API
  返回后同步报告 success/failure。无 background workflow engine、无 private SQLAlchemy dependency。

若 I2 无法只用上述 public surfaces 建立/读回 exact key 或观察 owner boundary，必须
`STOP / BLOCKED`，不得降级为 DBAPI address、timestamp 或 callback-only heuristic。

### 35.3 Normal return two-factor authority and owner boundary

normal return 的唯一 positive predicate：

```text
Fact A = POOL_RETURN_OBSERVED:
  exact epoch + pool_entry_id + checkout_generation + lease_id + cleanup_attempt_id
  的 PoolEvents.checkin observation

Fact B = OWNER_COMPLETED:
  owning G2/core caller 的 awaited AsyncSession.close() / Session.close() /
  session context-exit 已成功返回之后，owner wrapper 报告同一 exact key/attempt；
  只有 direct Connection 是 owner 时，才使用其 awaited close/context-exit successful return

RELEASE_CONFIRMED = Fact A AND Fact B
```

顺序不重要：A-first ⇒ `RETURN_PENDING`；B-first ⇒
`OWNER_COMPLETED_PENDING_POOL_CONFIRMATION`；只有 A+B ⇒ once-only `RELEASE_CONFIRMED`。
以下均不是 Fact B：进入 `finally`、close started、`__aexit__` entered、outer commit returned、
SAVEPOINT completed、checkin callback entered。owner success notification 缺失等同 unknown，
容量保持 unavailable。

G2/core caller 继续独占 outer transaction、Session lifecycle、commit/rollback、context-exit 与
connection disposition。Advisory registry 只观察 owner-completion；不得 close G2 Session、commit/
rollback outer transaction、cancel owner task、invalidate healthy G2 connection或夺取 cleanup ownership。

### 35.4 Normal return / owner cleanup matrix

| Case | Lease state | Capacity effect | Gate A | Shutdown consequence |
|---|---|---|---|---|
| owner close succeeds + same-attempt exact checkin observed | `RELEASE_CONFIRMED` once | +1 at most once | no new degradation | holder removed；may be clean if no other failure |
| owner close succeeds + no checkin observed | `OWNER_COMPLETED_PENDING_POOL_CONFIRMATION` | no increase | fail closed | pending/over-subdeadline；not clean |
| checkin observed + owner close raises | `RETURN_UNCERTAIN_RETIRED` | no increase | fail closed | `STOP_FAILED`/uncertain；do not report released |
| checkin observed + owner cleanup cancelled | `RETURN_UNCERTAIN_RETIRED` unless same shielded attempt later proves full predicate | no increase | fail closed | bounded wait only；otherwise `STOP_FAILED` |
| owner cleanup result unknown | `RETURN_UNCERTAIN_RETIRED` | no increase | fail closed | no indefinite wait；not clean |
| checkin observed, owner notification missing | `RETURN_PENDING` then uncertain at bounded owner deadline | no increase | fail closed | pending/uncertain；not clean |
| duplicate checkin | state unchanged；if A-only remains `RETURN_PENDING` | no increase | unchanged | duplicate counter only |
| late checkin after matching owner success | same epoch/key/attempt may transition once to `RELEASE_CONFIRMED` | +1 once | may clear this resource fault only before shutdown close-new; never auto-activate | telemetry update；shutdown admission stays closed |
| duplicate owner-completion | state unchanged | no increase | unchanged | duplicate counter only |
| late owner-success after matching pool observation | same epoch/key/attempt may transition once to `RELEASE_CONFIRMED` | +1 once | same rule as late checkin | telemetry update；shutdown admission stays closed |
| generation N callback while lease is N+1 | N+1 unchanged | no increase | invariant/late metric as applicable | never releases N+1 |

若一个 cleanup attempt 已明确 raised/failed，其先前 callback fact 被标记为该失败 attempt 的
historical observation，不得与另一 attempt 的 owner-success 拼接。late recovery 只有一个新的、
完整、同 key 且同 cleanup-attempt 的 positive predicate 才可 once-only 完成；无法产生该证据则
retire 到 process exit。

### 35.5 Explicit invalidation authority and matrix

hard invalidation 独立审计；soft invalidation 不构成 terminal disposition。caller-owned G2 只有
core owner 因 connection 已不安全而选择 invalidation，Advisory 不得为自身 shutdown/timeout
invalidate healthy G2 connection。

owner 使用 `AsyncSession.invalidate()` 时，它是“invalidate all in-use connections + close Session”
的 awaited owner cleanup boundary。owner 使用 explicit `AsyncConnection.invalidate()` 时，该 call
返回仍不等于 owning session/context lifecycle 已完成；必须继续由 owner 完成 connection/session
close-context。两类路径的 positive predicate 均要求：

```text
same-generation hard PoolEvents.invalidate observation
AND same-generation PoolEvents.checkin(None) observation
AND owning caller's full invalidate/close cleanup boundary returned successfully
AND same RuntimeHost epoch + lease + cleanup attempt remains authoritative
```

`PoolEvents.invalidate`、`PoolEvents.close`、`checkin(None)`、awaited `invalidate()` return 任一
单独都不增加 capacity；OS socket close 是否成功不是本 design 可观察/声称的事实。

| Invalidation case | Lease state | Capacity effect | Gate / shutdown |
|---|---|---|---|
| hard invalidate observed + `checkin(None)` + owner `Session.invalidate()`/full cleanup succeeds | `RELEASE_CONFIRMED` once，disposition=`INVALIDATED` | +1 once | ordinary completion；duplicate no-op |
| invalidate returns but owner session/connection close-context not complete | `INVALIDATE_PENDING` / `RETURN_PENDING` | no increase | fail closed；not clean |
| invalidate observation exists but `checkin(None)` absent | `INVALIDATE_PENDING` then uncertain at deadline | no increase | fail closed；`STOP_FAILED` if unresolved |
| invalidate raises | `RETURN_UNCERTAIN_RETIRED` | no increase | fail closed；`STOP_FAILED` |
| owner close raises after invalidation | `RETURN_UNCERTAIN_RETIRED` | no increase | fail closed；`STOP_FAILED` |
| `checkin(None)` observed but same cleanup later raises | `RETURN_UNCERTAIN_RETIRED` | no increase | fail closed；never callback-only release |
| cleanup cancelled | uncertain unless same shielded attempt later proves the entire predicate | no increase before full predicate | bounded wait；otherwise `STOP_FAILED` |
| completion unknown/missing owner signal | `RETURN_UNCERTAIN_RETIRED` | no increase | fail closed；no optimistic recovery |

### 35.6 Once-only token lifetime and Protection capacity proof

Registry transition uses CAS/idempotency on `(epoch, pool_entry_id, checkout_generation, lease_id)`；
`RELEASE_CONFIRMED` is reachable at most once。After it, every pool/owner/invalidation/late/duplicate
signal is telemetry-only and cannot increment/decrement capacity again。

`U` explicitly includes：

- checkin observed but owner not complete；
- owner complete but no checkin；
- cleanup error/cancel/unknown/missing notification；
- invalidation observation/return/checkin(None) without the full invalidation predicate。

```text
H_o + H_g + U <= A
A + R <= C
C - (H_o + H_g + U) >= C - A >= R
```

Only `RELEASE_CONFIRMED` removes a holder from `H_o / H_g / U`。Pool callback entry alone does
not change available capacity。`RETURN_UNCERTAIN_RETIRED` remains observable、consumes Advisory-
attributed capacity、does not borrow R、can degrade/fail-close Gate A、and cannot release twice。

该 proof 只保证 Advisory 不能消费 Protection-reserved capacity；不保证抵抗 all core load、
PostgreSQL outage、all Execution/Recovery traffic 或 shared-engine failure。

### 35.7 Shutdown, late confirmation and process restart

shutdown 首先原子关闭 new Advisory acquisition/admission；existing caller-owned G2 lifecycle
继续 core-owned。达到 Advisory subdeadline 时：

- `RETURN_PENDING`、`OWNER_COMPLETED_PENDING_POOL_CONFIRMATION`、`INVALIDATE_PENDING`、
  `RETURN_UNCERTAIN_RETIRED` 均不报告 released，也不无限等待；
- Host 不 seize/cancel/invalidate caller-owned G2，只记录 holder/age/error/attempt 与
  `STOP_FAILED` where applicable；Protection/Safety 按既有 R reserve 继续；
- late full predicate 可 once-only 更新 registry/telemetry；late checkin-only 或 owner-only 不足；
- close-new 已发生后，任何 late completion 都不得 reopen Gate A、admit new Advisory work 或
  启动 provider/finalizer；shared engine 仍在 accepted final Host step dispose。

process death 不fabricate release。process-local registry/token 随进程消失；new RuntimeHost epoch
必须先验证 singleton ownership、构造 fresh pool/capacity state 并重新证明 `A + R <= C`，再建立
新 limiter。旧 epoch uncertain token 是 historical evidence，不是新进程 active capacity；不引入
cross-process token persistence。

### 35.8 Non-regression, Human Decision Pack and candidate verdict

- **DISABLED unchanged**：`GATE_A_DISABLED`；no AdvisoryIngress/provider/worker/fence/token/
  SAVEPOINT/full writer；Pack-B 可 unset；Evidence 不 retroactive bind。
- **RR03-P1-01 preserved closed**：caller-owned timeout capture/restore、no idle/client cancel、
  rollback/connection-validity rules不变。
- **RR03-P2-01 preserved closed**：explicit core flush → immediate token try → `begin_nested()`；
  token failure = zero Advisory SQL + zero SAVEPOINT。
- **RR01 P1-01/P1-02/P1-03/P1-04/P2-01 preserved**：G2 truth isolation、supersede lock、
  Invocation final authority、deadline 与 no durable QUEUED 不变。
- **RR01 P1-05 / RR02 P1-01 corrected dependency**：two-factor/full invalidation predicate
  修复 false headroom；shared-pool claim remains attribution-only。
- **RR02 P1-02 preserved**：DISABLED single authority 不变。

- **Pack A = NONE**：connection-return completion authority 由本节唯一冻结，不是 numeric Human
  Decision；public-surface mechanism 已证明可实现，无 unresolved architecture choice。
- **Pack B**：仅保留 numeric pool/concurrency/timeout/shutdown/queue/retry/provider configuration；
  DISABLED 可 unset，Gate A active 前必须显式有效。
- **Pack C**：仅 observation window / sufficiency thresholds；不在 D2 发明 PASS threshold。

```text
PRE-01B-D2 = ACCEPTED / COMPLETE
STATUS = ACCEPTED / COMPLETE
REVIEWED CANDIDATE PRE-01B-D2-FIX-05 = cce1ae7b862b038a99976c802c0985df01b35285
SOURCE FIX-04 = d3922dd35ba83312194d124e17fa8645dead6e4d
FINDING PRE01B-D2-RR04-P1-01 = CLOSED（Independent Re-Review PRE-01B-D2-FIX-05 = PASS）
HUMAN ACCEPTANCE = CONFIRMED — 2026-09-17
I2 IMPLEMENTATION = NOT AUTHORIZED
MIGRATION / SCHEMA / RUNTIME / TEST / CONFIG CHANGE = NO
PROJECT DATABASE / SERVICE / PROVIDER / GATE / REAL AI / LIVE MUTATION = NO
```


## Acceptance Record

```text
Artifact: PRE-01B-D2 AdvisoryIngress / G2→G3 Activation Contract
Status: ACCEPTED / COMPLETE
Task type: FORMAL DESIGN / ARCHITECTURE CONTRACT / DOCS ONLY
Human Acceptance: CONFIRMED — 2026-09-17
Human-Accepted reviewed candidate: cce1ae7b862b038a99976c802c0985df01b35285
Reviewed candidate branch: design/pre-01b-d2-fix-05-return-completion-authority
Independent Re-Review: PRE-01B-D2-FIX-05 = PASS
P0: NONE
P1: NONE
P2: NONE
P3: NONE
Closeout branch: pre-01b-d2-final-acceptance-closeout
Main integration: FAST-FORWARD ONLY
PRE-01B-I2 Implementation: NOT STARTED / NOT AUTHORIZED BY THIS CLOSEOUT
Real AI: NOT ACTIVATED
live G2→G3: NOT ACTIVE
Gate A: NOT ACTIVATED
Gate B: NOT ACTIVATED
Gate C: NOT PASSED
Live: NOT AUTHORIZED
```

本 Acceptance **仅** 接受本文件所冻结的
`PRE-01B-D2 AdvisoryIngress / durable G2→G3 Activation Contract` Formal Design。

它 **不** 证明、**不** 授权：`PRE-01B-I2` implementation、live `G2→G3` activation、
Real AI activation、provider configuration、真实 provider 调用、Gate A activation、
Gate B activation、Gate C PASS、Live authorization、profitability / trading edge。
Design Acceptance 是前置条件，**不是** runtime activation。

### Accepted Reviewed Lineage（evidence pointers）

```text
a90c5968be4b456aabde814eb35d4757380761f7   Accepted Main before closeout
b5767d147adfeb885dd285243a32041a6731918c   failed reviewed FIX-02 candidate — historical evidence
4548920fddc7e4f84b0edab8a7e5d72fc35d54ff   failed reviewed FIX-03 candidate — historical evidence
d3922dd35ba83312194d124e17fa8645dead6e4d   failed reviewed FIX-04 candidate — historical evidence
cce1ae7b862b038a99976c802c0985df01b35285   Human-Accepted reviewed FIX-05 candidate — immutable
```

### Independent Re-Review Result Persistence

`PRE-01B-D2-FIX-05 Independent Re-Review = PASS`。

本 Acceptance 关闭的 finding（最终 resource-lifecycle 链）：

- `RR03-P1-01` timeout semantics — `CLOSED`
- `RR03-P2-01` token / SAVEPOINT ordering — `CLOSED`
- `RR03-P1-02` connection return authority — `CLOSED`（由 RR04 `P1-01` disposition 取代）
- `RR04-P1-01` return completion authority — `CLOSED`
- `RR01 P1-05` resource fence — `CLOSED`
- `RR02 P1-01` caller-owned lease / Protection capacity — `CLOSED`

Final review severity：`P0 = NONE` / `P1 = NONE` / `P2 = NONE` / `P3 = NONE`。

历史 failed candidate / failed review 记录（§32.10 / §33.9 / §34.8，以及
`design/pre-01b-d2-fix-01` ～ `design/pre-01b-d2-fix-04` 各分支）保持其 review 时点事实，
**不** 被改写为 PASS；这些历史 verdict block 中残留的 `HUMAN ACCEPTANCE = NOT PERFORMED`
属历史快照。本 artifact 的**当前** acceptance 状态**只**由顶部 `Artifact Status`、
§30、§35.8 与本「Acceptance Record」表达。

### Implementation Carry-Forward（Human Decision Pack）

本 Acceptance 冻结架构，但 **不** 填充 numeric activation policy：

- **Pack A = NONE**（connection-return completion authority 已由 §35 唯一冻结，
  不是 numeric Human Decision）。
- **Pack B** = numeric production activation settings 仍 `UNRESOLVED`：适用的
  provider / model / retry / timeout / deadline / pool / concurrency / shutdown /
  queue / cost / retention 数值均未在本收尾中发明，也未静默授权 production defaults
  （`DISABLED` 下可 unset；Gate A active 前必须显式有效）。
- **Pack C** = Gate-A observation window / sufficiency / acceptance thresholds 仍 `UNRESOLVED`。

### 协议版本说明

本文件 §1 `Repository Truth` 记录的是**设计 / review 时点**的 Global Protocol 快照
（v1.1.0 / `07e2df8…`）。本次 Human Acceptance 执行时点的 protocol remote `main` =
`2acef8fe802ce280f3e041925dd047d456ed6d54`，其 `AI_DEVELOPMENT_PROTOCOL.md` 仍为
`Protocol Version: 1.1.0` / `Status: ACCEPTED`。该差异属协议仓库自身的版本推进，
**不** 改变、**不** 影响本设计任何架构语义。

### 收口编辑边界

本次 closeout 对本文件只做状态级最小同步：顶部 `Artifact Status` 块、§30
`Design Verification / Candidate Verdict` 的 `Artifact Status` / `Task Status` 两行、
§35.1 RR04 verdict block 中两条已失效的 current-state 行、§35.8 candidate verdict block，
以及本「Acceptance Record」章节。**设计正文（normative architecture semantics）逐字未改**，
与 reviewed FIX-05 candidate（`cce1ae7b…`）保持语义一致；未新增任何 architecture decision。
文首 H1 保留 reviewed candidate 的迭代标题
（`# PRE-01B-D2-FIX-05｜Connection Return Completion Authority Fix`），未改写。
