# N01-7-F01-R2 — Legacy Authority Proof Closure

- Date: 2026-09-12
- Task: **N01-7-F01-R2**｜Legacy Authority Proof Closure（唯一阻断 = R1 Re-Review 的 `N01-7-F01-R1-R01`）
- Branch: `fix/n01-7-f01-durable-protection-snapshot`（续用同一分支；**未** merge / rebase / squash / force push `main`）
- Worktree: `E:\Documents\MarketPulse-AI-n01-7-f01-wt2`
- Task Base / R1 Reviewed HEAD: `979e5d2ee6b2cc4f26ae382cd3e46020d868a088`
- Status:
  - **`N01-7-F01-R2 = IMPLEMENTED / VERIFIED`**
  - **`N01-7-F01 = READY FOR INDEPENDENT RE-REVIEW`**
  - **`N01-7 = BLOCKED / WAITING F01 ACCEPTANCE`**
  - **`N01-8 = NOT STARTED`**
  - 未标记 `ACCEPTED`；未启动 2h soak；未推进 `main`

## 0. Finding（唯一阻断项）

| 项 | 内容 |
|---|---|
| Finding ID | **N01-7-F01-R1-R01** |
| Root Cause | `20260912_0006` migration 的 legacy CASE B authority proof 只验证了 **authoritative TradePlan row/payload identity 的子集** —— `plan_id` / `run_mode` / `instrument_id` / `plan_version` / `status`。正式 pre-migration runtime `marketpulse.g4.planning.load_active_plan()` 的 authority identity 还要求 `snapshot_id` / `decision_id` / `symbol` / `state_version` / `created_at` / `expires_at` 一致。 |
| 后果 | runtime 原本会拒绝的 corrupt TradePlan，migration 仍可能把其 SL/TP **永久 backfill 成 durable Position authority** —— 即 Candidate A 的 "DO NOT GUESS" 违规。 |
| Fix | CASE B 的 migration-local authority proof 现在与冻结的 legacy authority contract 对齐：冻结 `TradePlan` shape + **全 11 字段** row/payload identity + business-valid protection contract；TTL 仅豁免 `now < expires_at`。 |

**R1 已通过源码 Review 的部分本批未重新设计、未改动**：durable snapshot 为唯一 protection-lifetime authority、TradePlan TTL 仅 gate risk-increasing freshness、manual-close 跨生命周期 identity、reconciliation 消费 snapshot authority。§11 列出的 runtime 文件（`g4/planning.py`、`g4/protection.py`、`g4/control.py`、`g4/reconciliation.py`、`g3/`）**一行未改**（见 §8）。

## 1. Scope / Out of Scope

**允许修改**：`backend/alembic/versions/20260912_0006_position_protection_snapshot.py`、`scripts/verify_n01_7_f01_r1_migration_gate.py`、本 devlog。

**Out of Scope（未触碰）**：runtime 源码（`g2/g3/g4`）、`backend/tests/**`、N01-7 的 2h rerun、N01-8、Integrated Runtime Host、Real AI、Live Trading、`main`、`PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md`（CIP-09：contract change 在人工 Acceptance PASS 前不写入状态文件）。

## 2. Repository Truth（CIP-02 / CIP-03，本批实测）

| 项 | 实测值 | 来源 |
|---|---|---|
| `origin/main` 开工 | `1579707eff083007f1ac7ec65e10e6043f32b31e` | `git ls-remote origin refs/heads/main`（与任务书导航值一致） |
| `origin/main` 收尾 | `1579707eff083007f1ac7ec65e10e6043f32b31e`（**全程未变**） | 同上 |
| F01 分支 tip（本地 + 远端） | `979e5d2ee6b2cc4f26ae382cd3e46020d868a088` == R1 Reviewed HEAD | `git ls-remote origin refs/heads/fix/n01-7-f01-...` + `git rev-parse HEAD` |
| 基线漂移 | **无**（`HEAD == Task Base == R1 reviewed HEAD`）⇒ 未触发 "STOP / RE-REVIEW CONTEXT REQUIRED" | CIP-03 |
| Migration head | `20260912_0006`（单 head，`down_revision = 20260911_0005`） | 闸门 step_1（`heads == ["20260912_0006"]`） |
| 共享主库外部状态 | `20260905_0004`（**升级前 / 运行中 / 收尾后完全一致**） | `127.0.0.1:5432/marketpulse` |
| 解释器 | `py -3.14`（3.14.2） | 环境合同 |

> main 相对 F01 原始基线 `af81414` 已由并行 SE-02B 工作推进；本批**未** rebase / merge / cherry-pick，F01 保持 `979e5d2 → R2 commit` 的清晰 lineage。main 整合留给 R2 Independent Review PASS 之后的独立任务。

## 3. Implementation（migration authority contract）

### 3.1 完整 identity 字段（§5）

`_LEGACY_CANDIDATES` 的 SELECT 由 8 列扩为 13 列（新增 `tp.snapshot_id` / `tp.decision_id` / `tp.symbol` / `tp.state_version` / `tp.expires_at`；`tp.status` / `tp.created_at` 的别名改为与 payload key 同名）。

`_legacy_authority()` 现在要求 **三部分互相独立** 的证明，全部 frozen 在 migration 文件内（不 import application code）：

| # | 证明 | 内容 |
|---|---|---|
| 1 | frozen `TradePlan` shape | payload 可解析为 JSON object；无默认值字段（`plan_id` / `snapshot_id` / `decision_id` / `instrument_id` / `symbol` / `run_mode` / `state_version` / `plan_version` / `status` / `created_at` / `expires_at` / `entry_zone` / `stop_loss` / `take_profit` / `intended_notional`）类型正确；可选字段（`order_type` / `side` / `invalidation` / `probe` / `backup_scenarios`）**若存在**类型必须正确 |
| 2 | row ↔ payload identity（**11 字段**） | `plan_id` / `snapshot_id` / `decision_id` / `instrument_id` / `symbol` / `run_mode` / `state_version` / `plan_version` / `status` / `created_at` / `expires_at` **全部一致**（即 `load_active_plan()` 比较的那一份完整清单） |
| 3 | business-valid protection contract | `entry_zone` 有限且 `lower <= upper`；SL/TP 有限且 `stop_loss < take_profit`；`intended_notional` 有限（= `plan_business_errors` 的等价语义） |

目标原则（§5）落地为：**runtime 会因 identity mismatch 拒绝的 plan，migration 一定拒绝 backfill**；不存在 "runtime says invalid / migration says authoritative"。

### 3.2 TTL 例外（§6）—— 精确语义

- **允许忽略**：`now < expires_at`（expired plan 仍可提供已批准的 SL/TP 用于一次性兼容迁移）。
- **不允许忽略**：`row.expires_at == payload.expires_at`（属 §3.1 第 2 部分的 identity，必须一致）。
- backfill **不恢复** BUY / ADD / pending risk-increasing authority：plan 行本身未被修改，`TTL + state_version` 照旧 gate 一切 risk-increasing 动作。

### 3.3 确定性（§10）

`protection_updated_at = trade_plans.created_at`，**且只在** row/payload identity 全部通过后使用；仍不读时钟。第二次 `0005 → 0006` 复跑产出**逐行一致**的值（闸门 step_7）。

### 3.4 自审发现的次要缺陷（同一批内修正）

`value not in frozenset(...)` 在 `value` 为 dict/list 时会抛 `TypeError`：单个 corrupt row 会让**整个 upgrade 崩溃**，而不是把该 row 留为 NULL。已在 `_legacy_identity_mismatch`（`run_mode` / `status`）与 `_legacy_shape_invalid`（`order_type` / `side`）的成员判断前加 `isinstance(value, str)` 守卫，并新增两个 no-raise 探针（`CASE_C_MALFORMED_ENUM_VALUE` / `CASE_C_UNHASHABLE_OPTIONAL_FIELD`）将其固化。修复前的纯函数冒烟确认这两类输入确实会 raise；修复后 26/26 探针全部返回 `NOT_AUTHORITATIVE` 且无异常。

## 4. Expanded CASE C Matrix（§8 / §9）

`trade_plans` 除 PK 与 partial unique index `uq_trade_plans_one_active (run_mode, instrument_id) WHERE status='ACTIVE'` 外**无任何约束**覆盖 identity 列 ⇒ **8 个 mismatch 全部真实可 seed，无一为 `NOT SEEDABLE BY SCHEMA`**。每个 probe = 一个真实 OPEN position + 单一 ACTIVE plan，仅扰动一个字段（row 侧或 payload 侧）。

| # | CASE C probe | 扰动 | 结果 |
|---|---|---|---|
| 1 | `NO_PLAN` | 无 plan 行 | NULL |
| 2 | `CORRUPT_PAYLOAD` | payload 非 TradePlan | NULL |
| 3 | `IDENTITY_MISMATCH` | payload.plan_id ≠ row | NULL |
| 4 | `INVERTED_LEVELS` | SL 140 / TP 80 | NULL |
| 5 | `PLAN_VERSION_ZERO` | row/payload `plan_version = 0` | NULL |
| 6 | `SNAPSHOT_ID_MISMATCH` | payload.snapshot_id ≠ row | NULL |
| 7 | `DECISION_ID_MISMATCH` | payload.decision_id ≠ row | NULL |
| 8 | `SYMBOL_MISMATCH` | payload.symbol ≠ row | NULL |
| 9 | `STATE_VERSION_MISMATCH` | payload.state_version ≠ row | NULL |
| 10 | `CREATED_AT_MISMATCH` | payload.created_at ≠ row | NULL |
| 11 | `EXPIRES_AT_MISMATCH` | payload.expires_at ≠ row（**TTL 例外不豁免 identity**） | NULL |
| 12 | `RUN_MODE_MISMATCH` | payload.run_mode = TEST（合法枚举值）≠ row | NULL |
| 13 | `INSTRUMENT_ID_MISMATCH` | payload.instrument_id ≠ row | NULL |
| 14 | `INCOMPLETE_PSEUDO_PLAN`（§9 对照） | 只保留 `plan_id / run_mode / instrument_id / plan_version / status / stop_loss / take_profit`（**R1 判据会全部接受**） | NULL |
| 15 | `SCHEMA_INCOMPLETE_PAYLOAD` | identity 完整，但缺 `entry_zone` / `intended_notional` | NULL |
| 16 | `INVALID_OPTIONAL_FIELD` | `side = "LONG"` | NULL |
| 17 | `MALFORMED_ENUM_VALUE` | `run_mode = {}`（unhashable，必须 NULL 而非 raise） | NULL |
| 18 | `UNHASHABLE_OPTIONAL_FIELD` | `side = ["BUY"]` | NULL |
| — | `CASE_A_FLAT` | FLAT position | NULL（合法态） |
| — | `CASE_B_OPEN` | 唯一 fully authoritative plan，**已过期 30 天** | backfilled `plan-r1-case-b v1 [80.0, 140.0]`，`protection_updated_at == trade_plans.created_at` |
| — | `AMBIGUITY_PROBE` | 同 symbol 第二个 ACTIVE plan | 第二个被 `uq_trade_plans_one_active` 拒绝（`IntegrityError`）⇒ 健康 schema 下 ambiguity 不可达，唯一残留 authority 被转换 |

矩阵合计 **21 case / 19 NULL**；`NOT SEEDABLE BY SCHEMA` 项 = 0（见上）。

## 5. Teeth Witness —— R1 predicate 复演（§9 的直接证明）

闸门新增 `step_5b_authority_proof_teeth`：用 `git show 979e5d2:...20260912_0006...py` 取出**已 Review 的 R1 判据本体**，对**同一批 probe row** 求值，与 R2 判据并列报告。

| 量 | 值 |
|---|---|
| probe 数 | 17（4 个 R1 CASE C 带 plan 的 case + 13 个 R2 新探针） |
| `r1_predicate_loaded` | `true` |
| R1 判据接受 | **10**，且集合**恰等于** `_R1_GAP_CASES`（6 个 identity mismatch + pseudo-plan + schema-incomplete + invalid-optional + unhashable-optional） |
| R2 判据接受 | **0** |

即：R1-R01 的缺口被精确枚举，且已全部关闭。`RUN_MODE_MISMATCH` / `INSTRUMENT_ID_MISMATCH` 被 R1 **拒绝**（该两项 R1 本就比较），仍作为独立 DB 级 case 保留，因此矩阵是 R1 覆盖面的严格超集。

## 6. 变异验证（证明闸门本身有牙齿）

| 变异 | 语义 | 闸门结果 | 判据扫描（11→13 个 R2 探针中被接受者） |
|---|---|---|---|
| M1 `write-r1-identity` | identity 证明退回 R1 子集 | **FAIL** @ `CASE_C_CREATED_AT_MISMATCH`（该行被 backfill 成 `plan-r2-created-at-mismatch`） | 6 个 identity probe 全部被接受（= R1-R01 复现） |
| M2 `write-bare-levels` | shape 证明退回裸 SL/TP 检查 | **FAIL** @ `CASE_C_INVALID_OPTIONAL_FIELD` | `INVALID_OPTIONAL_FIELD` / `SCHEMA_INCOMPLETE_PAYLOAD` / `UNHASHABLE_OPTIONAL_FIELD` 被接受 |
| 干净态 | — | **PASS** | 0 个被接受 |

两次变异后均逐字节还原：migration sha256 前后同为 `b1e01e377574b278fb03bc4b4141e82ed6691064cd72efce3cd96806909cd580`。

> 过程记录（诚实披露）：**首次** M2 变异闸门 **PASS**，即我最初的 §9 pseudo-plan 对照对 shape 证明**没有牙齿**——因为该 payload 同时缺失 identity 字段，被 identity 证明先行拦下。据此补入 `SCHEMA_INCOMPLETE_PAYLOAD`（identity 完整 / schema 不完整）与 `INVALID_OPTIONAL_FIELD` / `UNHASHABLE_OPTIONAL_FIELD`，M2 才按预期 FAIL。这是本轮"测试比表面看起来更弱"的真实发现。
>
> 首次探索性变异（把 `plan_version >= 1` 守卫一并移除）时，闸门在 `ck_positions_protection_version_positive` 上以 `IntegrityError` 中止——说明 0006 的 CHECK 约束是 `protection_plan_version >= 1` 的 schema 级 fail-closed 兜底；但它不是本 finding 的证明手段，故仅作观察记录。

## 7. Migration Cycle / CASE A / B / C（disposable PostgreSQL）

`scripts/verify_n01_7_f01_r1_migration_gate.py`（文件名保留 R1 名以维持 review lineage，内容已扩展为 R2 闸门）——`result = PASS`，完整 JSON：`E:/Temp/r2_gate_final.txt`。

| 步骤 | 断言 |
|---|---|
| 单 head | `heads == ["20260912_0006"]`，`down_revision == 20260911_0005` |
| 0005 | 无任何 protection 列；21 个 legacy position / 20 个 plan 成功 seed |
| 0005 → 0006 | 5 列 + 3 约束（`ck_positions_protection_complete` / `_version_positive` / `_prices`）；**行数不变** |
| CASE A / B / C | 见 §4（CASE B 唯一 backfill，TTL 被忽略；19 个 NULL case） |
| ambiguity guard（stub 直调迁移函数） | 单候选 `converted=1/updates=1`；双候选 `not_authoritative=1/converted=0/updates=0`；不可解析 payload `not_authoritative=1/updates=0` |
| 0006 → 0005 | 3 约束 + 5 列清空；legacy position fingerprint **与升级前完全一致**；行数不变 |
| 0005 → 0006（第二次） | `cycle_reproduced_identical_values = True`，`differing_positions = []` |
| 共享主库 | `before == after == 20260905_0004`；`disposable_residue = 0` |

## 8. Focused Regression / Full Backend

### 8.1 隔离环境（R1 已验证方法的复用，零产品架构改动）

专用隔离 PG 实例（Docker `postgres:16-alpine`，`127.0.0.1:5433`，库名**仍为** `marketpulse`，已 upgrade 到 `20260912_0006`）+ worktree 根 gitignored `.env`。前置断言：`EFFECTIVE_DATABASE_URL = postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5433/marketpulse`、`OS_ENVIRON_DATABASE_URL = None`。

### 8.2 聚焦回归

| 段 | 覆盖 | 结果 |
|---|---|---|
| migration gate | 21 case 迁移矩阵 + teeth | **PASS** |
| `test_group4.py`（整文件） | F01 / R1 / FG-B / protection / recovery / resume / reconciliation | **105 passed**（120.84s） |
| `-k "f01 or protection or recovery or resume or reconcil"` | 显式选择集 | **60 passed, 45 deselected**（57.64s） |
| F01 节点清点 | `test_f01_*` = 28（含 `test_f01_r1_01..05`）全部在文件内被收集 | collect-only 核对 |

### 8.3 Full Backend（§16）

```
$ py -3.14 -m pytest backend/tests --collect-only -q     ->  295 tests collected
$ PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q
295 passed, 1 warning in 355.98s (0:05:55)                （exit 0）
```

**首轮全量失败已定性为调用方式伪影（非产品缺陷、非本批改动所致）**：`6 failed, 289 passed`，失败集合全部落在 `test_n01_restart_recovery.py::test_n01_c_real_postgres_restart_recovery_across_two_python_processes[6 参数]`，错误为子进程 `ModuleNotFoundError: No module named 'marketpulse'`。根因：该用例用 `sys.executable` 启动独立 Python 子进程执行测试文件，`PYTHONPATH` 未被设置（`pyproject.toml` 的 `pythonpath` ini 只影响父进程进程内 `sys.path`，子进程不继承），而我首次调用漏掉了 `PYTHONPATH=backend/src` —— R1 §5.5 记录的既有正确调用方式本就带该变量。定点复跑同一文件（带 `PYTHONPATH`）**6 passed**，失败集合被完全解释；随后在冻结代码上完成 **唯一一次干净全量 PASS**（上表）。非 rerun-until-green。

## 9. Static Gate / 隔离取证（§17）

| 项 | 结果 |
|---|---|
| `py -3.14 -m ruff check backend/src backend/tests scripts` | `All checks passed!` |
| `py -3.14 -m compileall -q backend/src backend/tests scripts` | exit 0 |
| `git diff --check` | exit 0 |
| 共享主库 5432 before / during / after | digest `ce16f4220fa7cc78f0e1b2cee7a8bf5c21ec699a0bc46799a2557f5afa033b9e` ×3 **完全一致**；`alembic_version = 20260905_0004`；protection 列 0；full-dict `before == after` |
| 共享主库真实数据（未被触碰） | `positions=3`、`trade_plans=3`、`execution_intents=134`、`strategy_candidates=28`、`fills=4`、`paper_orders=5`，24 表 |
| 库清单（5432 / 5433） | 均为 `['marketpulse', 'postgres']` ⇒ 无 disposable 残留 |
| client backends | 5432 = 1、5433 = 1（均为探针自身）⇒ 无泄漏连接 |
| 隔离容器 | `marketpulse-postgres-r2` 已停止并移除；5433 端口回收 |
| 一次性 `.env` | 已删除（`os.path.exists` 由 True → False） |

## 10. Files Changed

| 文件 | 变更 |
|---|---|
| `backend/alembic/versions/20260912_0006_position_protection_snapshot.py` | sha256 `c64e1583…`（R1）→ `b1e01e37…`：docstring 明确 authority proof 与 TTL 例外；候选 SELECT 8 → 13 列；新增 `_LEGACY_IDENTITY_FIELDS` / `_LEGACY_INSTANT_FIELDS` / 枚举集合与 `_legacy_number` / `_legacy_integer` / `_legacy_instant` / `_legacy_identity_mismatch` / `_legacy_shape_invalid`；`_legacy_authority` 改为三段式 fail-closed |
| `scripts/verify_n01_7_f01_r1_migration_gate.py` | 负向矩阵 5 → 18 个 CASE C case（含 2 个 no-raise 探针）；`_legacy_plan` / `_candidate_from_fixture` / `_r1_candidate` builder；`step_5b_authority_proof_teeth`（从 `979e5d2` 取 R1 判据复演）；断言 `r2 accepted == 0` 且 `r1 accepted == _R1_GAP_CASES` |
| `dev_log/2026-09-12-n01-7-f01-r2-legacy-authority-proof.md` | 新增：本文件 |

`git diff --stat`（tracked，2 个代码文件）：**498 insertions(+), 121 deletions(-)**。

| 约束 | 结果 |
|---|---|
| **Runtime Files Changed** | **NO**（`g2/g3/g4`、`backend/tests` 零改动） |
| **Main Changed** | **NO**（未 merge / rebase / squash；`origin/main` 全程 `1579707`） |
| 未重写的历史文档 | `2026-09-09-fg-c-*`、`2026-09-12-n01-7-f01-durable-protection-snapshot.md`、`2026-09-12-n01-7-f01-r1-protection-authority-closure.md` 均保持原样 |

## 11. Git

- 分支：`fix/n01-7-f01-durable-protection-snapshot`，lineage `979e5d2 → R2 commit`（单次提交，无 squash）。
- 提交信息：`fix(n01-7-f01-r2): close legacy authority proof`。
- push 后返回 Completion Report 并 **STOP**；Review 之后不再追加提交。

## 12. Residual / Known Gaps（不扩大、不隐瞒）

- `test_group3.py` / `test_group4.py` 仍以 import-time `Settings()` 直连「当前配置库」，没有自己的 disposable workspace ⇒ 必须在隔离实例或已升级 0006 的库上运行（R1 已记录，本批未改其架构）。
- §4.2 的 5 个「只用 `set_main_option`」的 disposable helper 与进程级 `DATABASE_URL` 的冲突（R1 记录的环境/测试基建观察项）本批未处理（Scope Isolation）。
- 全量套件对 `PYTHONPATH` 的隐式依赖（子进程）本批**记录为调用约束**，未修改任何测试（Scope Isolation）；若未来要求零环境变量运行全量，需人工决策修改该 harness。
- 保护权威相关的真实 AI / Live Trading / Integrated Runtime Host 依赖：**不存在**（结构事实：本批未新增任何 service / scheduler / provider）。
- 本批**未**执行 N01-7 的 2h soak、未启动 N01-8；`N01-7-F01` 仍未 ACCEPTED。
