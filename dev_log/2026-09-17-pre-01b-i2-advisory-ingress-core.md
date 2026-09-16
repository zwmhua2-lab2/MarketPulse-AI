# PRE-01B-I2｜AdvisoryIngress Core / Shadow-Safe Durable Path — **PARTIAL FOUNDATION DELIVERY**

## Task

- Type：IMPLEMENTATION / VERIFICATION / CANDIDATE DELIVERY（**非** Human Acceptance）。
- Goal：实现 Accepted Design `PRE-01B-D2` 的
  **AdvisoryIngress Core / Shadow-Safe Durable Path** 单一 vertical slice ——
  durable Invocation/Attempt authority、Evidence admission accounting、Snapshot binding、
  AI Decision attempt-origin、DISABLED epoch、active-capable 但未激活的 admission path、
  Advisory DB resource fence、caller-owned G2 lease semantics、bounded AdvisoryIngress、
  fake/injected provider boundary、immutable snapshot/input binding、attempt/retry/final
  winner persistence、stale/supersede fencing、restart/recovery、bounded shutdown、
  未来 Gate A evidence 所需的有界 telemetry。
- 本任务**不**激活：Gate A / Gate B / Gate C / Real AI / Live；**不**配置 production
  provider/model；**不**调用任何真实 provider；**不**产生任何经济 mutation。
- 本任务**不**执行 Human Acceptance、**不** merge / fast-forward `main`。

## Status（先读这一节）

```text
PRE-01B-I2 = PARTIAL / BLOCKED / NOT READY FOR INDEPENDENT REVIEW
```

本批次**只**完成并验证了 vertical slice 的**基础两层**，运行时路径**尚未实现**。
因此：

- **不**满足任务 §5 的 Acceptance Criteria（「ALL Accepted D2 §27 criteria are implemented
  and evidenced」未成立）；
- **不**满足任务 §36 的 `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`，
  **不得**当作 review-ready 候选；
- Gate A = `NOT ACTIVATED`；Gate B = `NOT ACTIVATED`；Gate C = `NOT PASSED`；
  Real AI = `NOT ACTIVATED`；Live = `NOT AUTHORIZED`（本批次零触碰，与候选状态无关）。

已交付并**经真实验证**：

| 层 | 内容 | 验证 |
|---|---|---|
| L1 Schema / Migration | `advisory_decision_invocations` + `advisory_decision_attempts` 两张最小新表；`edge_opportunity_evidence` durable admission accounting；`decision_snapshots` binding facts；`ai_decisions` Attempt origin | 真实 disposable PostgreSQL 16.15，**60/60** 通过 |
| L2 Identity / Vocabulary | D2 §12.1 全部十个确定性 identity 派生 + §12.2 冻结 version literal 集合 + §8.3/§14/§18/§19/§22 冻结词表 + advisory 包 import/code 隔离守卫 | **47/47** 通过 |

未交付（运行时路径本身）：见下方「Scope NOT Delivered」的精确清单。

## Repository Truth Preflight（实时读取）

- Task Base = dispatch 声明的 Accepted Main = `547095f6705ce651272363676e2a2b51a66bb8b6`。
- `git ls-remote origin refs/heads/main` = `547095f6705ce651272363676e2a2b51a66bb8b6`；
  本地 `git rev-parse main` = 同值 ⇒ **Baseline Drift = NONE**。
- Dispatch 声明的其他真值实测一致：
  - Accepted PRE-01B-D2 artifact =
    `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
    （`Artifact Status: ACCEPTED / COMPLETE`，Human Acceptance CONFIRMED 2026-09-17，
    reviewed candidate `cce1ae7b862b038a99976c802c0985df01b35285`）；
  - PRE-01B-I1 = `ACCEPTED / COMPLETE`（`pre-01b-i1-*` 谱系在 main 上）；
  - 当前 Alembic head = `20260913_0009`（单 head）；
  - 会话根工作区位于 `prb-01-product-requirements-baseline@d47313a`（另一条历史分支，**脏**）。
- 本轮**未** reset / rebase / stash / clean / 覆盖根工作区任何内容；全部工作在从
  exact `547095f` 新建的隔离 clean worktree 中完成。
- 全局 Protocol：`v1.1.0 / ACCEPTED`（按 dispatch 声明与 `AI_BOOTSTRAP.md` 语义，本批次
  未修改协议仓库）。

## Scope Delivered

### L1 — Schema / Migration（D2 §24、任务 §7 / §29）

**唯一一个**新增 migration：`backend/alembic/versions/20260917_0010_advisory_ingress_core.py`
（`down_revision = 20260913_0009`，单 head ⇒ `20260917_0010`）。

新表：

- `advisory_decision_invocations`（31 列 / 7 CHECK / 4 FK）——唯一 logical final authority。
  §14.2 的四条 DB 约束逐条物化：
  1. `ck_advisory_invocation_final_completeness`：`state = FINAL` **iff**
     `final_status/final_reason_code/finalized_at` 三者全非空；non-FINAL 时五个 final 字段
     必须全 NULL；
  2. `ck_advisory_invocation_no_attempt_reason`：`final_attempt_id` 只在
     §14.2 穷举的六个 no-provider terminal（`DEADLINE_EXPIRED_BEFORE_PROVIDER` /
     `CAPACITY_BLOCKED` / `EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` /
     `OPPORTUNITY_STALE_BEFORE_PROVIDER` / `ACTIVATION_DISABLED_BEFORE_PROVIDER` /
     `SHUTDOWN_BEFORE_PROVIDER`）可为 NULL；
  3. `ck_advisory_invocation_final_decision_requires_attempt`：显式 CHECK 补上
     `MATCH SIMPLE` 复合 FK 遇到 NULL 会跳过的那条蕴含（§14.2 item 4 要求
     `final_decision_id != NULL` ⇒ `final_attempt_id != NULL`）；
  4. `fk_advisory_invocation_final_attempt` / `fk_advisory_invocation_final_decision` /
     `fk_advisory_invocation_evidence` / `fk_ai_decisions_advisory_attempt` /
     `fk_advisory_evidence_invocation` 全部 `DEFERRABLE INITIALLY DEFERRED`。
- `advisory_decision_attempts`（31 列 / 9 CHECK / 2 FK）——每 provider attempt 一行；
  `UNIQUE(decision_invocation_id, attempt_number)` + `UNIQUE(decision_invocation_id, attempt_id)`
  作为复合 FK target；`fk_advisory_attempt_prior` 强制 retry lineage 留在同一 Invocation；
  token/cost provenance 用「值存在 **或** `usage_unavailable_reason` 存在」二选一表达，
  **不允许静默 NULL**。

既有表的最小扩展（全部 additive、nullable，legacy 行继续合法）：

- `edge_opportunity_evidence`：`advisory_admission_state`（NOT NULL，server default
  `'UNSTAGED'`）、`advisory_admission_reason_code`、`advisory_treatment_participation`、
  `advisory_admission_seed_version`、`advisory_admission_seed_digest`、
  `advisory_admission_seed (JSONB)`、`advisory_decision_invocation_id` + 9 条 CHECK。
  这些字段**不进入** `evidence_hash`、Evidence immutable payload 或 revision identity。
- `decision_snapshots`：14 个 queryable Shadow binding 字段 + 4 条 CHECK
  （binding 全有或全无、`evidence_revision >= 1`、duration > 0、deadline 顺序）。
- `ai_decisions`：12 个 Attempt-origin 字段 + `ck_ai_decisions_advisory_origin_pair` +
  `UNIQUE(decision_invocation_id, decision_id, attempt_id)` +
  partial unique index `uq_ai_decisions_advisory_invocation`（`WHERE decision_invocation_id
  IS NOT NULL`，legacy 行豁免）。

Migration 语义要点：

- **历史真值优先**：先 `ADD COLUMN ... NULL` → `UPDATE ... = 'LEGACY_PRE_I2' WHERE NULL`
  → 再 `SET NOT NULL` + `SET DEFAULT 'UNSTAGED'`。既有 Evidence 行**永不**被猜成 Gate A
  成员，也**不**被补造 experiment/pair/arm/seed/deadline。
- 无第三张 "final" 表、无 supersession marker 表、无 generic job/outbox/workflow 表
  （D2 §24.4 最小集）。
- `downgrade()` 完整反向拆除，已在真实 PostgreSQL 上验证 `0010 → 0009 → 0010` 往返。

### L2 — Identity / Vocabulary（D2 §12、§17.1、§20）

新增包 `backend/src/marketpulse/advisory/`：

- `vocabulary.py`：D2 逐字冻结的激活级别 / admission 状态 / participation / Invocation 状态 /
  Attempt 生命周期 / final status / reason code / no-attempt terminal 集合 / arm 标签 /
  六个 stale 维度；以及 §12.2 明确要求「在实现窗口逐字冻结」的 **version literal 集合**
  （`FROZEN_VERSION_LITERALS`，10 项，供 reviewer 一次审完）。
- `identity.py`：§12.1 的十步派生全部实现
  （`snapshot_payload_hash` → `advisory_snapshot_id` → `input_binding_digest` →
  `experiment_definition_digest` / `experiment_id` → `pair_id` →
  `baseline_arm_id` / `treatment_arm_id` → `decision_invocation_id` → `attempt_id` →
  `final_decision_id`）。
  - 全部 digest 走 accepted `marketpulse.edge.hashing.canonical_digest`
    （`SHA256` over versioned canonical JSON `[domain, *parts]`），**不引入第二套
    serializer**，且 domain 是数组元素而非字符串前缀 ⇒ 禁止未转义 `"|".join(...)`
    与跨 domain 碰撞。
  - §17.1 冻结的 canonical UTC 序列化 `canonical_utc_timestamp()`：RFC 3339 `Z` +
    固定 6 位小数秒。**刻意不把 `datetime` 对象直接交给 canonicalizer**：accepted
    canonicalizer 会渲染成 `+00:00`，与 §17.1 冻结形式不一致。timestamp 先转成冻结字符串
    再入 hash，保证 DB `TIMESTAMPTZ(6)` 值与参与 hash 的值是同一事实。
  - naive `datetime` 一律拒绝（不许猜 UTC）；非 UTC offset 先归一到 UTC。
  - `state_version` 采用 non-negative 校验（G2 durable 计数器；0 合法——符号无 durable 行
    时即 0，见 I1 的 `F-01` accessor），负数拒绝。
  - `logger`/`__all__` 之外无副作用；无 clock read、无 provider response、无 process-local 状态。
- `__init__.py`：以 docstring 记录包边界（provenance-only、只允许 `AdvisoryDbFence`
  capability、禁 import `aggregation_snapshot`、activation 默认 DISABLED、`GATE_B_PAPER`
  必须 fail closed）。

## Scope NOT Delivered（精确清单，BLOCKED 原因）

以下**全部未开始**。这是本批次 `BLOCKED` 的直接原因，也是 D2 §27 运行时 AC 全部未达成的
原因：

1. `advisory/admission.py` —— `AdvisoryAdmissionWriter`：G2 formal transaction 内的
   §8.2 固定排序（explicit core flush → immediate non-blocking try-acquire →
   `begin_nested()` → SAVEPOINT 内 timeout capture/apply/restore + 单次 PostgreSQL
   admission clock + seed canonicalization/digest + config/experiment/pair/arm/provider/model
   binding + Snapshot + Invocation + `UNSTAGED → INVOCATION_CREATED` →
   release 前 restore 确认）；任一 Advisory-only 失败只回滚 SAVEPOINT，第二 SAVEPOINT 只写
   常量 `ADMISSION_FAILED_FINAL / ADMISSION_STAGING_FAILED_UNBOUND / NO_LONG_UNBOUND`。
2. `advisory/fence.py` —— Host-owned `AdvisoryDbFence` + lease registry：
   `A + R <= C` 与 primary-pool effective capacity 证明、`PoolEvents.checkout/checkin/
   invalidate/close` 监听、public `record_info` / `info` 上的 `pool_entry_id` +
   monotonic `checkout_generation` correlation、two-factor `RELEASE_CONFIRMED`、
   `RETURN_PENDING` / `OWNER_COMPLETED_PENDING_POOL_CONFIRMATION` / `INVALIDATE_PENDING` /
   `RETURN_UNCERTAIN_RETIRED`、once-only CAS、duplicate/late 幂等、`H_o + H_g + U <= A` 计数。
3. `advisory/ingress.py` —— Host-owned 有界 queue（**REJECT NEWEST**、post-commit
   `put_nowait`、无 durable `QUEUED`）+ finite worker + `advisory_subdeadline` shutdown
   与 Protection handoff。
4. `advisory/provider.py` —— provider-neutral protocol + injected fake
   （**禁** real OpenAI/DeepSeek client、禁 API key 读取、禁网络调用、禁 fallback/router/voting）。
5. `advisory/consumer.py` —— shadow-safe consumer：attempt-start transaction
   （`Evidence N FOR UPDATE → Invocation FOR UPDATE → Attempt` 固定锁序）、provider I/O
   期间 zero DB resource、finalizer 单 transaction 写五终态字段 + optional `AIDecision` +
   attribution、六维 stale × 六时点矩阵、supersede 共享行锁（supersede-first / final-first
   双向证明）、retry 共享原 deadline/input/experiment/pair/arm。
6. `advisory/recovery.py` —— §15 / §32.4 restart matrix（`UNSTAGED` 只做常量终态化、
   `ADMITTED` 恢复同一 Invocation、`ACTIVE` 无 completion ⇒ `PROCESS_LOST`、`RETRY_PENDING`
   原 identity 继续、`FINAL` 幂等、`GATE_A_DISABLED` 永久不变）。
7. `advisory/telemetry.py` + health/readiness（D2 §21 全部计数器与 `DISABLED` vs
   `GATE_A_SHADOW` readiness 分流）。
8. `runtime_host.py` 集成：startup-epoch immutable activation classification 冻结、
   `DISABLED` literal 注入 G2 Evidence INSERT、`_compose_services` Gate A wiring
   （仅 active-capable）、`_shutdown` step 2 槽位填充、Advisory telemetry 接入；
   `db/session.py` 暴露经验证的 `effective_db_capacity`。
9. `g2/repository.py`：`persist()` 返回 typed result（含 frozen `AdvisoryWorkRef`）、
   DISABLED epoch 下原 INSERT 直接写 literal `GATE_A_DISABLED`、post-commit offer；
   `edge/repository.py`：`append_evidence_revision` 写 N+1 前先 `SELECT ... FOR UPDATE`
   immediate predecessor N。
10. `config.py`：Pack-B settings（**全部可 unset**；缺失/非法 ⇒ Gate A activation fail closed；
    本批次**不**发明任何 production 数值）。
11. 全部测试：任务 §30 的 **21 项** real disposable PostgreSQL adverse tests，以及 §31 的
    功能/并发矩阵（migration/model constraints、`DISABLED + Pack B unset`、ordinary
    Evidence insert、Evidence insert failure、`GATE_A_DISABLED` immutability、`UNSTAGED`
    recovery、post-commit enqueue only、commit→enqueue crash recovery、bounded queue /
    reject newest、no durable `QUEUED`、queue ordering、supersede-first、final-first、
    concurrent final winner、retry identity/deadline、stale matrix、restart matrix、
    shutdown race、Gate A zero economic mutation、no `G3Workflow` call、no TradePlan writes、
    no Real Provider construction/call、SE-02D import isolation、exact allow-list DB writes）。
12. `scripts/` 的 real-PG advisory runtime evidence runner。

**未发明任何数值**：Pack A 仍 = `NONE`；Pack B（retries / timeout / deadline / budget /
queue capacity / worker count / shutdown budget / pool capacity / `R` / `A` / 各 DB timeout /
provider / model / retention）与 Pack C（observation window / sufficiency threshold）
**全部保持 UNRESOLVED**，未写入任何 production default，也未把测试夹具值转成 production 值。

## Migration

```text
old head = 20260913_0009
new head = 20260917_0010（单 head）
Migration Files = backend/alembic/versions/20260917_0010_advisory_ingress_core.py（唯一一个）
```

## Files Changed

新增：

- `backend/alembic/versions/20260917_0010_advisory_ingress_core.py`
- `backend/src/marketpulse/advisory/__init__.py`
- `backend/src/marketpulse/advisory/vocabulary.py`
- `backend/src/marketpulse/advisory/identity.py`
- `backend/tests/test_pre_01b_i2_advisory_identity.py`
- `scripts/verify_pre_01b_i2_advisory_schema.py`

修改（全部为 additive schema 的**必要**连带，逐条在下方「Non-regression」说明）：

- `backend/src/marketpulse/db/models.py`
- `backend/src/marketpulse/g5/replay.py`
- `backend/tests/test_se_02a_edge_persistence.py`

未修改：`frontend/**`（零改动）、`deployment/**`（不存在，零改动）、
`PRODUCT_REQUIREMENTS.md`、accepted PRE-01A / PRE-01B 设计语义、
`.workbuddy/**` / memory / skills / daily logs（零改动）、`AI_CONTEXT.md` /
`DECISIONS.md`（本轮**未**触碰）。

## Verification

### V1 — Real disposable PostgreSQL 16.15 schema evidence（**60/60 PASS**）

- 运行物：`scripts/verify_pre_01b_i2_advisory_schema.py`（可重跑；每次自建 + 自删
  disposable database）。
- 实例：**新建** 独立容器 `marketpulse-pre-01b-i2-pg`（`postgres:16-alpine`，
  `127.0.0.1:5450`，独立命名卷 `mp-pre01b-i2-data`）。服务端版本实测 `16.15`。
  **零触碰** `marketpulse-postgres`（`127.0.0.1:5432`，任务期间保持 `Up (healthy)`）与既有
  项目卷；脚本内置 guard：admin DSN 指向 `127.0.0.1:5432` / `localhost:5432` 时直接
  `SystemExit` 拒绝运行。
- 覆盖（逐条真实执行、断言 PostgreSQL 自己的拒绝/接受）：

| 组 | 内容 | 结果 |
|---|---|---|
| [1] revision graph | 单 head / 无重复 revision / 无 dangling down_revision / 新 revision 直接继承 `20260913_0009` | 5 PASS |
| [2] upgrade + backfill | `0009 → 0010`；既有 Evidence 行 = `LEGACY_PRE_I2` 且零 fabricated binding；新行 server default = `UNSTAGED`；legacy `ai_decisions` / `decision_snapshots` 行不变 | 8 PASS |
| [3] constraint inventory | 五张表存在；五条 cycle/origin FK 存在且**全部** `DEFERRABLE INITIALLY DEFERRED`；18 条冻结 CHECK 全部存在；`ai_decisions` Invocation 唯一性是 partial unique index | 5 PASS |
| [4] Evidence CHECK 负例/正例 | UNSTAGED 带 seed/reason/participation 被拒；`GATE_A_DISABLED`/`LEGACY_PRE_I2` 带 seed 或 participation 被拒；半写 seed（有 digest 无 payload / 有 payload 无 digest）被拒；`INVOCATION_CREATED` 缺 seed 或 Invocation 被拒；只有 `INVOCATION_CREATED` 可携带 Invocation（**隔离证明**：用非 unbound 的 `ADMISSION_FAILED_FINAL` + 完整 seed 只触发 `ck_advisory_evidence_invocation_only_created`）；unbound terminal 带 seed / 带 Invocation / participation≠`NO_LONG_UNBOUND` 被拒；非 unbound terminal 无完整 seed 被拒；未知 state / 未知 participation 被拒；精确 unbound terminal 与 `GATE_A_DISABLED` 被接受 | 17 PASS |
| [5] deferred cycle + winner fence | **Invocation 先写、其 Evidence 行后写、同一 transaction 提交成功**（deferred FK 的最强形式）；`(experiment, pair, arm)` 第二 Invocation 被拒；同 `attempt_number` 重复被拒；retry lineage 留在同一 Invocation；跨 Invocation 的 `prior_attempt_id` 被拒；`state=FINAL` 缺三字段被拒；non-FINAL 带 final 字段被拒；非枚举 reason 配 NULL final Attempt 被拒；枚举 reason 配 NULL final Attempt 被接受；`final_decision_id` 无 `final_attempt_id` 被拒；只带 `decision_invocation_id` 的 AIDecision 被拒 | 12 PASS |
| [6] finalizer atomicity | 单 transaction 写 AIDecision + 五终态字段并 commit；五字段可查；同 Invocation 第二 AIDecision 被拒（winner fence）；跨 Invocation/Attempt 的 AIDecision 被拒；token 与 unavailable-reason 互斥被拒；cost 无 pricing_version 被拒 | 7 PASS |
| [7] downgrade round trip | `0010 → 0009`、两张新表消失、Evidence accounting 列消失、旧 schema 仍可插入 Evidence、`0009 → 0010` 再次成功 | 5 PASS |

### V2 — Identity / vocabulary（**47/47 PASS**）

`backend/tests/test_pre_01b_i2_advisory_identity.py`：timestamp 冻结形式与 UTC 归一；
binding 全部 18 个字段**逐字段**参与（含 D2 §0.3 决策 6 修正的 `feature_snapshot_hash`）；
新 Evidence revision ⇒ 新 binding（不是 rebinding）；experiment identity 是 definition-addressed；
arm 标签是冻结 literal；domain separation 不碰撞；空/零/负数输入被拒；
零 `state_version` 合法；冻结 version literal 集合完整；advisory 包**零** forbidden import
与**零** forbidden code token（AST 级，含 docstring 豁免）。

### V3 — Static verification（全部 PASS）

```text
ruff check backend/src backend/tests scripts        → All checks passed!
compileall 全部改动文件                              → exit 0
git diff --check（工作区 / vs main）                → 干净
conflict marker scan（全部改动 .py）                → []
Alembic single-head audit                           → 单 head 20260917_0010
```

### V4 — Regression（后端完整套件）

见下方「Regression 结果」一节。

## Regression 结果

以**正确环境**（`PYTHONPATH=backend/src`，见下方说明）运行完整后端套件：

```text
732 passed, 0 failed（详见 .i2-pytest-final.txt → 见 Evidence Pointers）
```

### 环境说明（重要，供复现者）

- 完整套件首次运行时出现 145 个失败，根因是**环境**而非代码：已有测试通过
  `Settings().database_url` 直连「已被迁移过的主库」。本轮为满足任务 §29 的隔离要求，
  主库指向**新建的** 5450 实例，而其 `marketpulse` 库初始为空 ⇒ `relation ... does not
  exist`。对 5450 主库执行 `alembic upgrade head` 后该批失败全部消失。
- 剩余 6 个失败全部集中在
  `test_n01_restart_recovery.py::test_n01_c_real_postgres_restart_recovery_across_two_python_processes[...]`
  （6 个参数），根因是**子进程环境**：该测试用 `subprocess.Popen([sys.executable, ...])`
  起子进程，而 pytest 的 `pythonpath = ["backend/src"]`（`pyproject.toml`）只作用于本进程、
  **不会**导出到 `os.environ`，子进程报
  `ModuleNotFoundError: No module named 'marketpulse'`。
  实测证据：同一命令加 `PYTHONPATH=backend/src` 后 **6/6 通过**（`.i2-n01c.txt`）。
  ⇒ 与本批次改动无关，属既有测试对运行环境的前置要求。
- 本轮**未**导出 `DATABASE_URL`：项目 `backend/alembic/env.py` 会优先读该环境变量，
  一旦导出会让每个测试的 disposable DB URL 被覆盖、迁移到错误的库（既有已知坑）。
  改为使用**被 gitignore 的**根 `.env`（`database_url=...@127.0.0.1:5450/marketpulse`），
  它只影响 `Settings`，不污染 alembic 的 per-test URL。
  `.env` **不在**提交范围（`.gitignore` 已覆盖 `.env` / `.env.*`）。

### Non-regression：additive schema 带来的必要连带改动（3 处）

新增 migration 必然移动 Alembic head，仓库自身已把这一约定写在代码注释里
（`test_se_02a_edge_persistence.py`：「The head moves with the schema, exactly like
`ReplayTradingRunner.schema_head`」）。因此：

1. `backend/src/marketpulse/g5/replay.py`：`ReplayTradingRunner.schema_head`
   `20260913_0009` → `20260917_0010`（replay workspace guard 校验的是**当前** head；
   注释同步扩写链尾）。**不改**其行为契约。
2. `backend/tests/test_se_02a_edge_persistence.py`：`HEAD_REVISION`
   `20260913_0009` → `20260917_0010`；`test_fix02_clean_migration_chain_...` 的
   re-upgrade 断言由「`head` == 0009」改为「`head` == 当前 head」。
   `_FIX02_HEAD = "20260913_0009"` 作为 **历史 revision** 保持不变。
3. `backend/tests/test_se_02a_edge_persistence.py` 的 `_stage_evidence`
   改为用**冻结的 pre-0010 Evidence 列集**（`_LEGACY_EVIDENCE_COLUMNS`，26 列）走 core
   `insert()`。原因：这些 FIX-02 测试刻意在历史 revision `0008` 上落盘 Evidence 行再向前
   走 migration，而 ORM 模型自 `20260917_0010` 起携带 Advisory accounting 列，
   ORM insert 只能面向已迁移 schema。列**值**逐字未变 ⇒ 这些测试证明的东西不变。
   实测：`test_se_02a_edge_persistence.py` **40/40 PASS**。

## Failure / Adverse Evidence

**未执行**。任务 §30 的 21 项 real-PG adverse tests 与 §31 的功能/并发矩阵全部属于
未交付的运行时层，本批次**不**声称任何 PASS，也**不**以基础层证据替代它们。

## Result

```text
Status = PARTIAL / BLOCKED / NOT READY FOR INDEPENDENT REVIEW
L1 Schema/Migration = IMPLEMENTED / VERIFIED（60/60 real PostgreSQL 16.15）
L2 Identity/Vocabulary = IMPLEMENTED / VERIFIED（47/47）
Runtime path（admission / fence+lease / ingress / provider / consumer / recovery /
  telemetry / host integration / G2 typed result / Pack-B config）= NOT STARTED
Adverse + functional/concurrency test matrices = NOT EXECUTED
D2 §27 运行时 AC = NOT MET
Gate A = NOT ACTIVATED；Gate B = NOT ACTIVATED；Gate C = NOT PASSED
Real AI = ZERO CONSTRUCTION / ZERO CALL；Live = NOT AUTHORIZED
Gate A economic mutation = ZERO（无运行时路径可产生）
Production DB / shared marketpulse-postgres = ZERO TOUCH
.workbuddy / memory / skills / daily logs = ZERO CHANGE
Human Acceptance = NOT PERFORMED
```

## Remaining

按依赖顺序的最小续作清单（每项都可在本批次既有基础上直接开工）：

1. `advisory/fence.py` + `db/session.py` 的 `effective_db_capacity` 暴露（§20.1 / §35；
   需真实 pool-saturation 证据）。
2. `advisory/admission.py`（§8.2 / §32.2 / §34.5；需 SQL trace 证明
   flush→token→`SAVEPOINT` 排序）。
3. `g2/repository.py` typed result + DISABLED literal + `edge/repository.py`
   predecessor `FOR UPDATE`（§8.2 / §10.1）。
4. `advisory/ingress.py` + `advisory/provider.py` + `advisory/consumer.py`
   （§14 / §16 / §19 / §10）。
5. `advisory/recovery.py` + `advisory/telemetry.py`（§15 / §21）。
6. `runtime_host.py` 集成 + `config.py` Pack-B（§20.2 / §22 / §33.6 / §26）。
7. 任务 §30 / §31 全部测试矩阵 + `scripts/` 运行时 evidence runner。

## Risks

1. **`BLOCKED` 是诚实的规模判断，不是遇到技术阻塞**：任务 8,000+ 行（约 I1 批次的 2 倍）
   的高风险 transaction/state-machine 实现，若在一个批次内一次性写完而无法对
   `SAVEPOINT` / timeout restore / pool-event two-factor / deferred FK 这些语义做真实
   实验迭代，则任何 `READY FOR INDEPENDENT REVIEW` 都会是**未经验证的自述**。
   D2 自身的 FIX-04 → FIX-05 历史已证明这条链上的结论必须靠真实实验而不是推理确认。
2. `ck_advisory_invocation_no_attempt_reason` 与 `ck_advisory_evidence_participation` 是
   **词表约束**：若未来批次引入 D2 未列出的 named terminal 或 participation 值，
   migration 必须同步扩表约束（这是**预期**行为——约束正是为了让「偷偷引入新终态」不可能）。
3. 冻结 version literal 集合（`FROZEN_VERSION_LITERALS`）是本批次按 §12.2 首次冻结的；
   reviewer 应逐条确认其命名是否符合 PRE-01A 语义，一经接受即不可原地改名
   （改名会改变所有派生 identity）。
4. 3 处 non-regression 连带改动（head 常量 + legacy staging helper）虽已实证无行为变化，
   仍属**改动既有已接受测试文件**，需要 reviewer 明确确认「证明的东西未变」。
5. 本批次**未**触碰 `AI_CONTEXT.md` / `DECISIONS.md`：按任务 §5 的候选态指针同步约定
   未发现强制要求，故保持不动。

## Context For Next AI

- 先重读 `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`
  §8 / §14 / §20 / §35（normative 优先级：§35 > §34 > §33 > §32 > 其余），
  以及本文件「Scope NOT Delivered」清单。
- 本批次**已可复用**的实现真值：
  - schema 与全部冻结约束（`20260917_0010`）——运行时层直接依赖，无需再改 migration；
    若确需新列，**必须**新增第二个 revision 而**不得**原地改写 `20260917_0010`。
  - `advisory/vocabulary.py` 是全部冻结 literal 的唯一来源；**禁止**在运行时模块内联
    同义字符串。
  - `advisory/identity.py` 的十步派生即 §12.1 的全部 identity authority；运行时层**不得**
    另造 identity 派生。
  - `scripts/verify_pre_01b_i2_advisory_schema.py` 是可重跑的 schema 回归门；任何后续
    schema 改动都必须让它继续全绿（或按新 revision 扩展它）。
- 真实验证走新建 disposable 容器（`127.0.0.1:5450`）；**禁止**触碰
  `marketpulse-postgres`。测试环境的两个已知前置：主库需先 migrated；需要
  `PYTHONPATH=backend/src` 供子进程导入（或导出 `PYTHONPATH` 而**不要**导出 `DATABASE_URL`）。

## Evidence Pointers

原始输出按项目既有先例保留在**仓库外**：`E:/Documents/pre-01b-i2-evidence/`（同
`E:/Documents/pre-01b-d2-fix-04-evidence/` 的做法），包含：

- `.i2-schema-evidence.txt` —— schema 门原始输出（`checks passed : 60/60`、`RESULT : PASS`、
  `postgres : 16.15`）；
- `.i2-identity-check.txt` —— identity/vocabulary 原始输出（`47 passed` + `All checks passed!`）；
- `.i2-static.txt` —— ruff / compileall / `git diff --check` / conflict-marker 原始输出；
- `.i2-focused1.txt` / `.i2-focused2.txt` —— 聚焦回归子集（含环境根因的原始 traceback）；
- `.i2-n01c.txt` —— `PYTHONPATH` 下 N01-C `6 passed`；
- `.i2-pytest-baseline.txt` / `.i2-pytest-candidate.txt` —— 环境修复前/后的完整套件原始输出
  （用于证明「145 失败 = 环境」与「6 失败 = 子进程模块路径」）；
- `.i2-pytest-final.txt` —— **最终完整回归**原始输出（`732 passed, 1 warning`、`EXIT=0`）；
- `.pg-start.txt` / `.pg-status.txt` / `.docker-probe.txt` —— disposable 实例创建与
  「`marketpulse-postgres` 全程未触碰」的实测记录。

仓库内可重跑的入口（无需原始输出即可复现）：

- schema：`PYTHONPATH=backend/src py -3.14 scripts/verify_pre_01b_i2_advisory_schema.py`
  （需一个 disposable PostgreSQL；admin DSN 由 `PRE_01B_I2_ADMIN_URL` 提供，默认
  `127.0.0.1:5450`，指向 `5432` 会被脚本拒绝）；
- identity/vocabulary：`py -3.14 -m pytest -q backend/tests/test_pre_01b_i2_advisory_identity.py`；
- 完整回归：`PYTHONPATH=backend/src py -3.14 -m pytest -q`。

**复现前置（重要）**：本 worktree **不含** `.env`（它被 `.gitignore` 覆盖且已移除）。运行
DB 相关测试前必须保证两件事：（1）`Settings().database_url` 指向一个**已 migrated** 的实例
（默认 `5432` 为本项目常规环境；若改用 disposable 实例需自建根 `.env` 并
`alembic upgrade head`）；（2）子进程测试需要 `PYTHONPATH=backend/src`（`pyproject.toml` 的
`pythonpath` 不导出到子进程）。**不要**导出 `DATABASE_URL`（`alembic/env.py` 会优先读它）。
- Disposable 实例（保留供复现，未清理）：容器 `marketpulse-pre-01b-i2-pg` @ `127.0.0.1:5450`，
  卷 `mp-pre01b-i2-data`；清理命令
  `docker rm -f marketpulse-pre-01b-i2-pg; docker volume rm mp-pre01b-i2-data`。
  `marketpulse-postgres` 全程 `Up (healthy)`、零触碰。
