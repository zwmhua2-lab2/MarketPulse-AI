# PRE-01B-I2-CONT-01 — Runtime Completion from Foundation Checkpoint

- 任务卡：`PRE-01B-I2-CONT-01`｜Role = `HIGH-RISK IMPLEMENTATION CONTINUATION EXECUTOR`
- 日期：2026-09-17
- **状态 = `BLOCKED`**（§6 Foundation Integrity Gate 命中 1 项 P1 级契约冲突 → 见「8. BLOCKER B-01」）
- Independent Review = `NOT PERFORMED`；Human Acceptance = `NOT PERFORMED`
- Gate A = `NOT ACTIVATED`；Gate B = `NOT ACTIVATED`；Gate C = `NOT PASSED`；Real AI = `NOT ACTIVATED`；Live = `NOT AUTHORIZED`

---

## 1. Task

从已验证的 foundation checkpoint 继续实现 `PRE-01B-I2`（AdvisoryIngress Core / Shadow-Safe Durable
Path）的**运行时层**，使 Accepted D2 §27 的完整 vertical slice 达到
`IMPLEMENTED / READY FOR INDEPENDENT REVIEW`。

## 2. Scope（本批次授权范围）

`backend/alembic/versions/**`、`backend/src/marketpulse/**`、`backend/tests/**`、`scripts/**`、
`PROJECT_STATE.md`、新 dev_log（本文件）。

历史 foundation dev_log `dev_log/2026-09-17-pre-01b-i2-advisory-ingress-core.md` 视为历史证据，
READ ONLY，本批次未修改。

## 3. Out of Scope（未做 / 禁止项）

未修改：`PRODUCT_REQUIREMENTS.md`、已接受 PRE-01A / PRE-01B 设计契约、`frontend/**`、
`deployment/**`、`.workbuddy/**`、memory、skills、daily logs。

未执行：任何 Gate 激活、真实 provider 构造 / 调用、production provider/model 选型、Live 授权、
真实 AI。未改变：Trading / Risk / Execution / Accounting / Protection / SE-02D aggregation 语义。

未引入：第二 engine / pool / DSN、Redis、Kafka、Celery、RabbitMQ、microservice、
generic workflow engine、event bus、saga framework、provider router、model voting、
automatic provider fallback。

## 4. Exact Continuation Base

| 项 | 值 | 实测方式 |
|---|---|---|
| Accepted Main | `547095f6705ce651272363676e2a2b51a66bb8b6` | `git rev-parse main` / `git ls-remote origin refs/heads/main` |
| Foundation branch | `pre-01b-i2-advisory-ingress-core` | `git ls-remote origin refs/heads/pre-01b-i2-advisory-ingress-core` |
| Foundation commit | `b0b89a8919303bbbd34b4e7c685282e95e0c73ed` | 同上（远端与本地一致） |
| `b0b89a8^` | `547095f6705ce651272363676e2a2b51a66bb8b6` | `git rev-parse b0b89a8^` |
| Continuation branch | `pre-01b-i2-runtime-completion`（从 `b0b89a8` 精确创建） | `git worktree add` |
| Continuation worktree | `E:/Documents/MarketPulse-AI-pre-01b-i2-runtime-completion` | `git worktree list` |
| `main` | **UNCHANGED** | `git rev-parse main` = `547095f…`（本批次**未**移动） |

未执行：amend `b0b89a8`、repoint 原分支、rebase foundation、merge `main`、force push。
Foundation checkpoint 分支原样保留为不可变证据。

## 5. §4 Realtime Baseline Gate

| 检查 | 期望 | 实测 | 判定 |
|---|---|---|---|
| remote `main` | `547095f…` | `547095f6705ce651272363676e2a2b51a66bb8b6` | **PASS** |
| remote foundation branch | `b0b89a8…` | `b0b89a8919303bbbd34b4e7c685282e95e0c73ed` | **PASS** |
| `b0b89a8^` | `547095f…` | `547095f6705ce651272363676e2a2b51a66bb8b6` | **PASS** |
| local `main` | 与远端一致 | `547095f6705ce651272363676e2a2b51a66bb8b6` | **PASS** |

### 5.1 SHA Delta Check（CIP-03）

`main` 相对上一已接受基线 `a90c5968be4b456aabde814eb35d4757380761f7` 推进 5 个 commit：

```
a90c596 → b5767d1 → 4548920 → d3922dd → cce1ae7 → 547095f
```

`git diff --name-status a90c596..547095f` = **9 个文件，全部为文档**：
`AI_CONTEXT.md`、`DECISIONS.md`、`PROJECT_STATE.md`、5 个 `dev_log/2026-09-16…09-17` 文件、
Accepted D2 设计 artifact `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`。

⇒ **零代码 / 零 migration / 零 frontend / 零 schema**。未触碰 PRE-01A、PRE-01B、RuntimeHost、
DB / session / models、migration、G2、G3、Evidence、Protection、Recovery、Reconciliation 的
实质内容 ⇒ **无 material drift，BASELINE OK**。

### 5.2 Global Protocol（§2）

| 项 | 期望 | 实测 | 判定 |
|---|---|---|---|
| protocol remote main | `a80c55b…` | `a80c55b7451f77883d8b0713a228f0d9bebf7d22` | **PASS** |
| Protocol Version | `1.1.0` | `1.1.0` | **PASS** |
| Protocol Status | `ACCEPTED` | `ACCEPTED` | **PASS** |

⇒ **RULE BASELINE VERIFIED**（未发生 version/status 变化）。

附带事实（非本批次授权范围，未修改）：本地 `E:/Documents/ai-dev-protocol/.git` 已损坏——仅剩
`hooks/`、`info/`、`objects/`、`refs/`，无 `HEAD` / `config` / `index`，`git` 报
`not a git repository`。为复读真值改用一次性浅克隆（`git clone --depth 1` → HEAD 精确等于
`a80c55b…`），原目录未被改动。

## 6. §6 Foundation Integrity Gate（runtime coding 前置，非 Independent Acceptance）

### 6.1 Migration `20260917_0010`

真实 disposable PostgreSQL **16.15**（本任务专用容器 `marketpulse-pre-01b-i2-cont-01-pg`，
`127.0.0.1:5451`）上的机械验证，**全部 PASS**：

| 检查 | 结果 |
|---|---|
| single head | `heads == ['20260917_0010']` |
| `down_revision` | `20260913_0009` |
| 完整链 | `0010 → 0009 → 0008 → 0007 → 0006 → 0005 → 0004 → 0003 → 0002 → 0001` |
| 新增表 | **恰好两张**：`advisory_decision_attempts`、`advisory_decision_invocations`（无第三张 final / marker / outbox 表） |
| 既有表扩展 | `edge_opportunity_evidence` +7 列、`decision_snapshots` +14 列、`ai_decisions` +12 列（与 D2 §24.2 逐项一致） |
| `advisory_admission_state` | `NOT NULL`，server default `'UNSTAGED'` |
| `LEGACY_PRE_I2` 回填 | 真实**预先存在**的 Evidence 行 → `LEGACY_PRE_I2`，且 `bound_columns = 0`（零 fabricated experiment/pair/arm/seed/Invocation） |
| `UNSTAGED` 新行默认 | 经真实插入验证 |
| deferred composite FK | 5 条（`fk_advisory_invocation_evidence`、`fk_advisory_evidence_invocation`、`fk_advisory_invocation_final_attempt`、`fk_advisory_invocation_final_decision`、`fk_ai_decisions_advisory_attempt`）全部 `DEFERRABLE INITIALLY DEFERRED`；单事务插入 Evidence ↔ Invocation 两半任一顺序均可 commit |
| Invocation final-field 约束 | `ck_advisory_invocation_final_completeness`、`ck_advisory_invocation_no_attempt_reason`、`ck_advisory_invocation_final_decision_requires_attempt` 均在位并经正/负例验证 |
| Attempt 唯一性 / origin | `uq_advisory_attempt_invocation_number`、`uq_advisory_attempt_invocation_attempt`、`fk_advisory_attempt_prior`（同 Invocation retry 谱系）均在位并经负例验证 |
| winner fence | `uq_advisory_invocation_experiment_pair_arm`、`ai_decisions` 上 partial unique Invocation 唯一索引、`fk_ai_decisions_advisory_attempt` 均经负例验证 |
| downgrade / upgrade 完整性 | `0010 → 0009 → 0010` 往返 + `base → head` 全链往返，均成功；downgrade 后两张新表与 Evidence accounting 列消失、旧 schema 仍可插入 Evidence |
| 门 | foundation 自带真 PG 验证脚本 **60/60 checks PASS**（`RESULT: PASS`） |

补充证据（本批次新写，仓库外）：migration 图 / 两表 / 三处扩展列数 / deferrable 标志 /
downgrade 往返 / 全链往返的机械断言脚本全 PASS。

### 6.2 既有 Schema 后果（re-audit）

**`backend/src/marketpulse/g5/replay.py`**

唯一变更 = `ReplayTradingRunner.schema_head` `"20260913_0009"` → `"20260917_0010"`，
并在注释中补记 0010 为 additive revision。判定：**严格 migration 兼容性更新**，
不改 replay 语义、不改 workspace 隔离行为。**PASS**

**`backend/tests/test_se_02a_edge_persistence.py`**

两处变更：

1. `HEAD_REVISION` `"20260913_0009"` → `"20260917_0010"`（head 常量跟随 migration 链）；
   并把原先钉在 `_FIX02_HEAD` 的 re-upgrade 断言改为 `HEAD_REVISION`。判定：**兼容性更新**。
2. `_stage_evidence()` 由 ORM `session.add(row)` 改为显式 `insert(table).values(**subset)`，
   其中 `_LEGACY_EVIDENCE_COLUMNS` 命名 pre-0010 列集合。**变更原因**：FIX-02 测试在历史 revision
   `20260913_0008` 上暂存 durable Evidence 行后再向前走 migration，而 `0010` 之后 ORM 模型已带
   advisory accounting 列，ORM insert 只能针对已迁移 schema。

**是否弱化被测试的已接受 SE-02A 行为？逐条判定 = 未弱化**：

- `_LEGACY_EVIDENCE_COLUMNS` 实测 **26 项，与模型列集合减去 7 个新 advisory 列后完全相等**
  （集合相等，非子集）⇒ 没有任何既有列被静默省略、没有值被退化成 DB 默认值；
- 7 个新 advisory 列的 Python 侧 `default` 全部为 `None`（仅 `advisory_admission_state` 有
  server_default）⇒ Core insert 不会因遗漏列而注入客户端默认值，SQL 形态与原先等价；
- 列**取值**未变（同一 `row` 对象属性）；
- 真实执行结果：`test_se_02a_edge_persistence.py` **40 passed / 0 failed**（含
  `0005 → 0006 → 0007 → 0008 → 0009 → head` 往返与 `head → 0004 → head` 循环）。

**PASS**

### 6.3 Identity / Vocabulary（D2 §12）

| 检查项 | 结果 |
|---|---|
| §12.1 派生序列（步 1–10） | 全部实现且顺序一致（`snapshot_payload_hash` → `advisory_snapshot_id` → `input_binding_digest` → `experiment_definition_digest` / `experiment_id` → `pair_id` → `baseline_arm_id` / `treatment_arm_id` → `decision_invocation_id` → `attempt_id` → `final_decision_id`） |
| §12.2 冻结 literal | `FROZEN_VERSION_LITERALS` 一处集中（10 项），`vocabulary.py` 为唯一来源；D2 明文给出的 5 个 domain literal 逐字一致 |
| canonical JSON 复用 | 全部 digest 走已接受 `marketpulse.edge.hashing.canonical_digest`（`SHA256` over `[domain, *parts]`），**未**引入第二套 serializer |
| timestamp canonicalization | `canonical_utc_timestamp()` = RFC 3339 `Z` + 固定 6 位小数秒；naive datetime 被拒绝（不猜测时区）；非 UTC offset 归一化后渲染一致 |
| 无 delimiter 歧义编码 | advisory 包内 **零** `"\|".join(...)`（Grep 实测） |
| `feature_snapshot_hash` 纳入 binding | 在 `input_binding_digest` 的 18 项中，并有逐字段参与测试 |
| 无 process-local authority | advisory 包内零 `uuid` / `random` / `time.time` / `datetime.now` / `utcnow` / `repr()` / `hash()`（Grep 实测） |
| 身份测试 | `test_pre_01b_i2_advisory_identity.py` **47 passed / 0 failed** |

判定：**PASS，附带 2 项非阻塞观察**（见 §7）。

## 7. Foundation Findings（本批次**未**修改，供 Independent Review 裁定）

### F-01（P2，契约字面偏差，未修改）

`advisory/identity.py` 的 `baseline_arm_id` / `treatment_arm_id` 以
`ADVISORY_PAIR_ID_DOMAIN`（`"pre01a-pair-v1"`）作为 domain 调用 `canonical_digest`，故实际
canonical 数组是 `["pre01a-pair-v1", pair_id, "WITHOUT_AI_BASELINE"]`（3 元素），而 Accepted D2
§12.1 步 6 / 7 冻结的公式是 `H(pair_id, "WITHOUT_AI_BASELINE")`（**2 元素**，未给 domain literal
—— 与步 2/5/8/9/10 明确写出 domain 的写法形成对比）。

- 实际碰撞不可行（需要 `experiment_id == pair_id`，即需 hash 原像），无 correctness / safety 影响；
- 但它是**对已接受 §12.1 派生公式的字面偏离**，且意味着 arm 与 pair 共用同一 domain ⇒
  「domain 标识概念」这一语义被削弱。

**未修改理由**：该偏离存在两种实质性解释（(a) 严格字面 = 2 元素；(b) 与其余步骤模式一致 = 带
domain 元素），属**设计/语义裁定**，依 CIP-06（Decision Isolation）不由执行 AI 自行改写已接受
派生语义。**建议**：由 Independent Review / Human 裁定后，若取 (a)，则最小修正为
`canonical_digest(pair_id, BASELINE_ARM_LABEL)`。

### F-02（P3，证据质量，未修改）

`test_pre_01b_i2_advisory_identity.py::test_domains_are_separated` 的断言
`pair_id(...) != baseline_arm_id(pair_id=pair_id(...))` 比较的是两组**不同输入**的 digest，
在 (a)/(b) 两种解释下都会通过 ⇒ 该测试**并未**证明 pair 与 arm 的 domain separation，与测试名
所声称的覆盖不符。建议在 F-01 裁定后一并收紧。

## 8. BLOCKER B-01（P1 —— 本批次停机原因）

### 8.1 事实（真实 PostgreSQL 16.15 逐案实证，非推断）

在由 `20260917_0010` 建出的 schema 上，写入 `state='FINAL'`、`final_attempt_id IS NULL`、
`final_decision_id IS NULL` 的 Invocation 行（其两条父行 FK 均已就位，故拒绝只可能来自
Invocation 行自身的 CHECK）：

| 终态（`final_status / final_reason_code`） | PostgreSQL 裁定 | 依据 |
|---|---|---|
| `STALE_DECISION / DEADLINE_EXPIRED_BEFORE_PROVIDER` | **ACCEPTED** | §14.2 item 2 枚举 |
| `STALE_DECISION / EVIDENCE_SUPERSEDED_BEFORE_PROVIDER` | **ACCEPTED** | §14.2 item 2 枚举 |
| `STALE_DECISION / OPPORTUNITY_STALE_BEFORE_PROVIDER` | **ACCEPTED** | §14.2 item 2 枚举 |
| `STALE_DECISION / ACTIVATION_DISABLED_BEFORE_PROVIDER` | **ACCEPTED** | §14.2 item 2 枚举 |
| `INVALID_SCHEMA / SHUTDOWN_BEFORE_PROVIDER` | **ACCEPTED** | §14.2 item 2 枚举 |
| `CAPACITY_BLOCKED / CAPACITY_BLOCKED` | **ACCEPTED** | §14.2 item 2 枚举（以 reason 形式列入） |
| `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` | **REFUSED** by `ck_advisory_invocation_no_attempt_reason` | §14.2 named-terminal 表 / §16 / §18 / §27 AC-6 |
| `CAPACITY_BLOCKED / ADVISORY_DB_CAPACITY_UNAVAILABLE` | **REFUSED** by `ck_advisory_invocation_no_attempt_reason` | §20.1 item 8 |

PostgreSQL 中该约束的实际物化定义（`pg_get_constraintdef` 读出）：

```
CHECK (final_attempt_id IS NOT NULL OR final_reason_code IS NULL
       OR final_reason_code::text = ANY (ARRAY[
            'DEADLINE_EXPIRED_BEFORE_PROVIDER', 'CAPACITY_BLOCKED',
            'EVIDENCE_SUPERSEDED_BEFORE_PROVIDER', 'OPPORTUNITY_STALE_BEFORE_PROVIDER',
            'ACTIVATION_DISABLED_BEFORE_PROVIDER', 'SHUTDOWN_BEFORE_PROVIDER']::text[]))
```

### 8.2 冲突定位

Accepted D2 在 **6 处**明确要求 `final_reason_code = ADVISORY_QUEUE_REJECTED` / 
`ADVISORY_DB_CAPACITY_UNAVAILABLE` 且 **Attempt 为 NULL**：

| D2 位置 | 内容 |
|---|---|
| §0.3 决策表（行 77） | queue full 的 durable 终态 = `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` |
| §14.2 named-terminal 表（行 862） | `final_attempt_id = NULL`、`final_decision_id = NULL`、`CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` |
| §16 queue full durable result（行 948） | `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED`，**明文** `final_attempt_id=NULL` |
| §18 failure matrix（行 1058） | `CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED` |
| §27 AC-6（行 1675） | `full = durable REJECT NEWEST（CAPACITY_BLOCKED / ADVISORY_QUEUE_REJECTED）` |
| §20.1 item 8（行 1187） | `CAPACITY_BLOCKED / ADVISORY_DB_CAPACITY_UNAVAILABLE` |

而 §14.2 item 2（行 833）枚举 NULL-Attempt 合法 reason 时给出的是
`CAPACITY_BLOCKED`（status 名，非 `ADVISORY_QUEUE_REJECTED`），**未**列入上述两个 reason code；
foundation 的 CHECK 逐字镜像了该枚举。

⇒ 冲突**位于 Accepted D2 自身**（§14.2 item 2 枚举 vs §14.2 mapping 表 / §16 / §20.1 item 8 /
§27 AC-6），**不是** foundation 的实现错误——foundation 对 §14.2 item 2 是忠实的。

### 8.3 后果

任务 §16 / §18 / §23 / §29（22 项 adverse matrix 之 1、6、18）/ §30 与 D2 §27 **AC-6**、
§20.1 item 8 所要求的 durable 终态**无法在当前 schema 上持久化**。要满足 AC-6 只能二者之一：

- **(a)** 放弃冻结的 reason code，改用 `CAPACITY_BLOCKED / CAPACITY_BLOCKED`（违反 §0.3 / §14.2 表 /
  §16 / §18 / §27 AC-6 的逐字要求）；
- **(b)** 放宽由 Accepted D2 §14.2 item 2 派生出的 `ck_advisory_invocation_no_attempt_reason`
  ⇒ 修改已接受契约的约束语义。

两者都是**设计裁定**，属 CIP-06 禁止执行 AI 自行决定的范围。故依任务 §6（P1 级 foundation
mismatch ⇒ STOP / `FOUNDATION INTEGRITY FAIL`，不得在其上构建 runtime）与 §7（真实 blocker ⇒
`BLOCKED`）**停机**。

### 8.4 Minimal Unblock Condition（最小解锁条件）

一次 Human / Design 澄清（可走 `Proposal → Human approval → Spec / DECISIONS sync`）：
裁定 D2 §14.2 item 2 的 NULL-Attempt reason 枚举**是否为完整集合**。

- 若「枚举不完整，以 §16 / §20.1 / §27 AC-6 的 outcome 为准」⇒ 授权把
  `ADVISORY_QUEUE_REJECTED`、`ADVISORY_DB_CAPACITY_UNAVAILABLE` 补入该枚举
  （`ck_advisory_invocation_no_attempt_reason`），并同步 `vocabulary.NO_ATTEMPT_FINAL_REASONS`；
  依任务 §6「PRE-01B-I2 未 merge，最终候选树可在 descendant commit 中直接修正 0010」，
  可**不**新增第二个 revision。
- 若「枚举完整，`CAPACITY_BLOCKED` 即为其唯一合法 reason」⇒ 授权把 §0.3 / §14.2 表 / §16 / §18 /
  §27 AC-6 的 reason 改为 `CAPACITY_BLOCKED`（并明确它与 `ADVISORY_QUEUE_REJECTED` 的关系）。

裁定后本批次可在同一 continuation branch 继续；F-01 建议同批一并裁定。

## 9. Runtime Implementation

**`NOT STARTED`**（§6 为 runtime coding 的强制前置门，门未通过 ⇒ 依 §6 不得在其上构建 runtime）。

未实现：`AdvisoryAdmissionWriter`、caller-owned G2 admission integration、SAVEPOINT 隔离、
timeout capture / restore、PostgreSQL admission clock、`AdvisoryDbFence`、lease / disposition
registry、Protection DB reserve、bounded `AdvisoryIngress`、fake / injected provider protocol、
shadow-safe consumer、durable attempt-start、retry、final winner authority、supersede locking、
stale matrix、restart / recovery、telemetry、RuntimeHost 集成、DISABLED epoch behavior、
G2 typed persistence result、Pack-B config surface。

## 10. Migration State

- `head` = `20260917_0010`（**single head**，本批次未新增、未修改任何 migration）
- 本批次**未**修改 `20260917_0010`（无 Foundation Correction）

## 11. Files Changed

- **代码 / migration / 测试 / scripts：`ZERO`**（本批次未做任何实现改动）
- 文档 / 状态：新增 `dev_log/2026-09-17-pre-01b-i2-runtime-completion.md`（本文件）；
  `PROJECT_STATE.md` 增加一段 PRE-01B-I2-CONT-01 记录
- 仓库外证据（未入 git）：`E:/Documents/_i2cont_evidence/`、`E:/Documents/_i2cont_scratch_d2.md`
- 本地环境（gitignored，未入 git）：continuation worktree 根 `.env`（仅指向本任务的一次性容器）

## 12. PostgreSQL Evidence

- 本任务**新建专用一次性容器** `marketpulse-pre-01b-i2-cont-01-pg`（`postgres:16-alpine`，
  卷 `marketpulse-pre-01b-i2-cont-01-pgvol`，`127.0.0.1:5451`）；§6 全部 schema 证据来自该容器
- **零触碰**：`marketpulse-postgres`（项目库，`5432`）、production DB、任何既有项目卷、
  上一执行者保留的证据容器 `marketpulse-pre-01b-i2-pg`（`5450`，本批次未启停、未读写）
- 取证后**已移除本任务自己的容器与卷**（按 §28）
- 证据脚本（仓库外，可重跑）：`foundation_migration_gate.py`、`dump_0010_constraints.py`、
  `terminal_persistability_probe.py`（本节 BLOCKER 证据即来自最后一个）

### 12.1 Harness / 环境缺陷与其修复（§32：不得把环境性失败从报告中移除）

首次在容器上跑 `test_se_02a_edge_persistence.py` 得到 **39 failed / 1 passed**，全部为
`relation ... does not exist` / `relation "alembic_version" does not exist`。

- **根因（实测）**：`backend/alembic/env.py` 为
  `database_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))`。
  我把 `DATABASE_URL` 作为**进程环境变量**导出后，测试进程内的每次 `command.upgrade(cfg, …)`
  都被该环境变量覆盖，全部打到同一个库；测试自己创建的 disposable 库因而保持空。
  （测试用 `_alembic_config()` 设的是 `config` 的 `sqlalchemy.url`，优先级低于环境变量。）
- **修复**：不再导出 `DATABASE_URL`；改为写入 gitignored 的 worktree 根 `.env`
  （`.gitignore` 已含 `.env`）。于是 `Settings()`（读 `.env`）指向本任务容器，
  而 alembic 继续使用测试传入的 disposable URL。
- **重跑结果**：**40 passed / 0 failed**；`git status --porcelain` 保持为空。

## 13. Concurrency Evidence

`NOT EXECUTED` —— 依赖未实现的 runtime 层（§6 门未通过，依 §6 不得先构建 runtime）。

## 14. Regression

| 范围 | 结果 |
|---|---|
| `test_pre_01b_i2_advisory_identity.py` | **47 passed / 0 failed** |
| `test_se_02a_edge_persistence.py`（既有 schema 后果专项） | **40 passed / 0 failed** |
| foundation 真 PG schema 门 `scripts/verify_pre_01b_i2_advisory_schema.py` | **60/60 PASS** |
| 全后端回归 | `NOT EXECUTED`（§31 要求的是运行时候选的完整回归；本批次无实现改动，且已被 BLOCKER 停在该门之前） |

## 15. Verification（本批次实际执行）

| 门 | 结果 |
|---|---|
| §4 Baseline Gate | **PASS** |
| Protocol Rule Baseline | **PASS**（v1.1.0 / ACCEPTED） |
| §6 migration up / down / round-trip / full-chain | **PASS** |
| §6 既有 schema 后果 | **PASS**（40/40，并证明未弱化） |
| §6 identity / vocabulary | **PASS**（47/47），附 F-01 / F-02 观察 |
| §6 真 PG schema 门 | **PASS**（60/60） |
| §6 → runtime 前置门 | **FAIL**（BLOCKER B-01） |
| §29 / §30 / §31 / §32 完整门 | `NOT EXECUTED`（依 §6 停机） |
| `ruff` / `compileall` / `git diff --check` / conflict-marker scan / Alembic single-head | 静态门：single-head 已验（PASS）；其余对本批次无实现改动而言无新增风险，**未**作为本批次门执行（不声称 PASS） |

## 16. Result

**`BLOCKED`**

- §4 Baseline Gate = **PASS**；Protocol = `v1.1.0 / ACCEPTED`
- §6 Foundation Integrity Gate = **FAIL**（1 项 P1 级契约冲突：BLOCKER B-01）
- Foundation Corrections = **NONE**（未修改 foundation 任何一行）
- Runtime = `NOT STARTED`；`PRE-01B-I2` 仍 `NOT READY FOR INDEPENDENT REVIEW`
- `main` = **UNCHANGED**（`547095f…`）；未 merge、未 review、未 Human Accept

## 17. Remaining

1. **BLOCKER B-01**：等待 §8.4 的设计裁定（另需 F-01 一并裁定）。
2. 裁定后继续同一 branch：实现 §9 列出的全部 runtime 层。
3. 运行时完成后再执行任务 §28（届时需**再新建**一个一次性容器）、§29（22 项 real-PG adverse）、
   §30（功能/并发矩阵）、§31（完整回归）、§32（静态门）。

## 18. Risks

- 若把 B-01 当成「实现细节」直接放宽 CHECK，等于**未经授权修改已接受契约语义**（CIP-06 违规），
  且会永久改变 `final_reason_code` 的 durable 词汇 —— 故本批次选择停机而非就地绕过。
- F-01 若在 Independent Review 中才被发现，将强制重算所有 arm identity 相关断言；建议与 B-01 同批裁定。
- §27 的运行时 AC 数量大、且 §20.3 / §35 的 lease / disposition 状态机对 release predicate 要求极严；
  下一批次应预留充足的 real-PG adverse 时间，不要用 mock 替代。

## 19. Context For Next AI

- 本批次是 **continuation**，不是新批次：起点固定为 foundation checkpoint `b0b89a8`
  （= 分支 `pre-01b-i2-advisory-ingress-core`），续做分支为 `pre-01b-i2-runtime-completion`。
- **先读 BLOCKER B-01 的裁定**；裁定未下来之前**不要**开始 runtime 实现（§6 明令）。
- foundation 的 L1 / L2 两层经本批次独立复核**可用**（见 §6），可直接在其上构建 runtime。
- 跑真 PG 证据的正确姿势：新建本任务自己的容器；**不要**导出 `DATABASE_URL`，用 worktree 根
  `.env` 指向自己的容器（见 §12.1）；**不要**碰 `5432` 项目库。
- 交付前注意 `contrib` 约束：仓库文件为 CRLF（`core.autocrlf=true`）。

## 20. Evidence Pointers

| 证据 | 位置 |
|---|---|
| Task Base / foundation / parent SHA 实时复读 | 本文 §4 / §5 |
| main drift 文件清单（纯文档） | `git diff --name-status a90c596..547095f` |
| migration 图 / 两表 / 扩展列 / deferrable / 往返 | `E:/Documents/_i2cont_evidence/foundation_migration_gate.py` 输出 |
| 约束物化定义 | `E:/Documents/_i2cont_evidence/dump_0010_constraints.py` 输出 |
| **BLOCKER B-01 逐案裁定** | `E:/Documents/_i2cont_evidence/terminal_persistability_probe.py` 输出 |
| foundation 真 PG schema 门 60/60 | `scripts/verify_pre_01b_i2_advisory_schema.py`（仓库内，本批次未改） |
| identity 47/47、SE-02A 40/40 | pytest 输出（本文 §12.1 / §14） |
| Accepted D2 契约 | `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`（`547095f` 内，行 77 / 833 / 862 / 948 / 1058 / 1187 / 1675） |
| Protocol 真值 | `zwmhua2-lab2/ai-dev-protocol` @ `a80c55b7451f77883d8b0713a228f0d9bebf7d22` |
