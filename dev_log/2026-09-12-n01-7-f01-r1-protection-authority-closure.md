# N01-7-F01-R1 — Protection Authority Closure + Validation Environment Recovery

- Date: 2026-09-12
- Task: **N01-7-F01-R1**｜Protection Authority Closure + Validation Environment Recovery（采用已批准的 **Candidate A**）
- Branch: `fix/n01-7-f01-durable-protection-snapshot`（续 F01 分支；**未** merge `main`）
- Worktree: `E:\Documents\MarketPulse-AI-n01-7-f01-wt2`
- Task Base: `9d22240a458d02f00ee8a18ecc6b926742de1c86`（被审 F01 实现 HEAD）
- Status:
  - **`N01-7-F01 = IMPLEMENTED / VERIFIED / READY FOR INDEPENDENT RE-REVIEW`**
  - **`N01-7 = BLOCKED / WAITING F01 ACCEPTANCE`**
  - **`N01-8 = NOT STARTED`**
  - 未标记 `ACCEPTED`；未推进 `main`

## 0. Superseding contract（取代关系，明确声明）

本批的 **Candidate A** 取代以下历史权威契约（历史文件**保持原样**，不改写，仅作 evidence）：

| 被取代 | 文件 | 被取代的语义 |
|---|---|---|
| F01 §3.3 "TTL-only carve-out" | `dev_log/2026-09-12-n01-7-f01-durable-protection-snapshot.md` | 「plan 有效则 plan 优先；仅当 plan *expired 且 otherwise-valid* 才回落 snapshot」——保护寿命仍受 TradePlan TTL 影响 |
| FG-C protection-lifetime 契约 | `dev_log/2026-09-09-fg-c-safety-recovery-validity.md` | 同一族「plan 参与保护寿命裁决」的语义 |

**Candidate A 权威契约（本批冻结）**：

```text
TradePlan TTL controls risk-increasing freshness ONLY.
(TTL + state_version gate: BUY / ADD / pending LIMIT fill —— 与保护寿命无关)

A durable protection snapshot atomically attached to the current OPEN Position is the
SOLE protection-lifetime authority, until either:
  1. an approved successor snapshot is durably committed to the same Position row, or
  2. the Position becomes flat.

A newly created ACTIVE TradePlan does NOT become the protection authority merely by
being "valid". A plan is only an authority *source*; it becomes authoritative only
after being atomically committed onto the Position row.
```

## 1. Scope / Out of Scope

**允许修改**：`backend/src/marketpulse/{g3,g4}`、`backend/alembic/versions/20260912_0006_*.py`、`backend/tests/test_group4.py`、新增 `scripts/verify_n01_7_f01_r1_migration_gate.py`、本 devlog。

**Out of Scope（未触碰）**：N01-7 的 2h rerun、N01-8、Integrated Runtime Host、Real AI、Live Trading、策略/风控规则变更、自动 TTL 强平、protection scheduler、renewal service、新 Position subsystem、新保护表、新 DB 编排子系统。

## 2. Repository Truth（CIP-02 / CIP-03，本批实测）

| 项 | 实测值 | 来源 |
|---|---|---|
| `origin/main` | `af81414160248c97f59a63b31fe615ea8ae14bbe`（**全程未变**） | `git ls-remote origin refs/heads/main`（本批开工 + 收尾各一次） |
| F01 分支远端 tip | `9d22240a458d02f00ee8a18ecc6b926742de1c86` | `git ls-remote origin refs/heads/fix/n01-7-f01-...` |
| 本批 Task Base | `9d22240…`（== 分支 tip，**无基线漂移**） | `git rev-parse HEAD` |
| Migration head | `20260912_0006`（单 head，`down_revision = 20260911_0005`） | `scripts/verify_n01_7_f01_r1_migration_gate.py` step_1 |
| 共享主库外部状态基线 | `20260905_0004` | `marketpulse` @ `127.0.0.1:5432` |
| 解释器 | `py -3.14`（3.14.2） | 环境合同 |

## 3. Implementation（相对 `9d22240` 的增量）

### 3.1 §5 保护权威判定：plan-first → snapshot-only

`g4/planning.py::resolve_open_position_protection` 由 `async (session, position, *, now)` 改为**同步、无 I/O、快照唯一**：

```python
def resolve_open_position_protection(position: PositionRecord) -> PositionProtectionAuthority | None:
    return read_position_protection(position)
```

调用点同步改为不再传入 `now`/`session`：`g4/protection.py::evaluate`、`g4/protection.py::_close_position_in`、`g4/control.py::_open_position_protection_gate`。
`load_valid_long_active_plan` / `plan_business_errors` **保留**，继续独任 risk-increasing 新鲜度契约（BUY/ADD/pending fill），不再参与保护寿命。

### 3.2 §6 可创建 / 变更 ACTIVE TradePlan 的生产路径审计

| 路径 | 行为 | 处理 |
|---|---|---|
| `G3Workflow.process_setup` → `persist_trade_plan`（持仓已 OPEN 时建新 plan） | 新建 ACTIVE plan，**不**触碰 Position 行 | 依 Candidate A：不改保护权威（新 plan 仅作 risk-increasing 来源）。回归 `test_f01_r1_01` / `test_f01_r1_02` |
| `PlanManager.replace` → `_replace_in`（UPDATE_STOP / UPDATE_TP / REPLACE_PLAN / ADD） | 同事务原子替换 / 清除 snapshot | **保持**既有原子后继快照语义（§10） |
| `persist_trade_plan` 其他调用方 | 同上，不写 Position 行 | 同上 |

新增回归 `test_f01_r1_05`：**fresh 且有效**的 plan + 无 snapshot ⇒ 仍 `POSITION_UNPROTECTED`（incident 开启、resume refused）——直接证伪「新 plan 因有效而自动成为保护权威」。

### 3.3 §7 受保护 / 无保护退出的经济 identity

`g4/protection.py::_close_position_in` 的 intent id：

```python
authority = resolve_open_position_protection(position)
if authority is not None:
    intent_id = stable_id("exit", run_mode, instrument_id, trade_id, plan_id, plan_version,
                          exit_reason, exit_quantity)
else:   # 无 durable authority：必须仍按 持仓+成交生命周期 唯一
    intent_id = stable_id("exit", run_mode, instrument_id, position.position_id, trade_id,
                          exit_reason, exit_quantity)
```

- 受保护退出 identity 至少含 `trade_id / protection_plan_id / protection_plan_version / exit_reason / quantity`。
- 无快照 fallback identity 至少含 `position_id / trade_id / exit_reason / quantity`；**不再**使用 `plan_id=""` + `plan_version=0` 的单例形式。
- 新增 `test_f01_r1_03`：同一 symbol 的**两次无保护 manual full close**（两个持仓生命周期）必须产生 **2 个不同** 经济 identity，且都不是 legacy `""/0` 形式——彻底消除跨生命周期 false `duplicate_intent` no-op。
- 新增 `test_f01_r1_04`：受保护 close 的 identity 由 authority + 生命周期组成，且 protective SELL 的 `plan_id` == authority 的 `plan_id`。

### 3.4 §8 / §11 迁移 `20260912_0006` 重写

- 模块级 `PROTECTION_COLUMNS`（5 列）、`PROTECTION_CHECKS`（3 约束）；`upgrade()` = add_column ×5 → create_check_constraint ×3 → `backfill_legacy_position_protection(op.get_bind())`；`downgrade()` 只逆序删 3 约束 + 5 列（**不**动其他任何对象）。
- 确定性 legacy backfill（一次性、纯函数、**不读时钟**）：
  - `_LEGACY_CANDIDATES`：`JOIN trade_plans ON run_mode/instrument_id/status='ACTIVE' WHERE positions.quantity > 0 AND positions.protection_plan_id IS NULL ORDER BY position_id, plan_id`；
  - `_legacy_authority(row)`：校验 `plan_version >= 1`、payload 可解析为 dict、`plan_id/run_mode/instrument_id/plan_version/status` 一致、SL/TP 有限且 `stop_loss < take_profit`；否则 `None`；
  - 每个 position **恰 1** 候选 → 回填（`protection_updated_at = trade_plans.created_at`，**忽略 TTL**、**不**恢复 BUY/ADD 权威）；**0 或 >1** → 不猜测，保持 NULL。
- Legacy 兼容矩阵：**CASE A**（FLAT）保持 NULL；**CASE B**（OPEN + 唯一确定权威）确定性 backfill；**CASE C**（OPEN + 缺失 / 歧义 / 损坏 payload / 身份不一致 / 反向价位 / `plan_version = 0`）→ `DO NOT GUESS` → NULL ⇒ 运行时呈 `POSITION_UNPROTECTED` / `SAFE_MODE` / Resume refused / BUY 取消 / manual close 可用。

### 3.5 §9 reconciliation 消费规范化契约

`g4/reconciliation.py` invariant #13 改为直接消费 `read_position_protection(position)`：

- 只对 `quantity > TOLERANCE` 且 `read_position_protection(...) is None` 的持仓记 `{"instrument_id": ..., "reason": "NO_DURABLE_AUTHORITY"}`；
- **不再**导入 / 调用 `load_active_plan` / `load_valid_long_active_plan` / `plan_business_errors` ⇒ 「仅 TradePlan 过期」不再被判为 UNPROTECTED；
- report key `open_position_protection_survives_plan_ttl` 与诊断字符串 `open_position_unprotected_after_plan_ttl` **逐字未变**（detector-only 语义与既有连接生命周期修复一并保留）。

### 3.6 §10 保留的既有良好工作（未重写）

`g3/protection_snapshot.py` 四个函数代码未改（仅重写 docstring 以对齐 Candidate A）；0006 谱系、5 列 / 3 约束、G3 同事务原子写、partial/full close 行为、过期 plan 仍阻断 risk-increasing、`PlanManager._replace_in` 原子替换、reconciliation 连接泄漏修复、既有 F01 回归全部保留。

## 4. Test environment recovery（§4 + §12）

### 4.1 共享主库恢复到 `20260905_0004`（§4，本批已完成）

| 项 | 实测 |
|---|---|
| `alembic_version` | `20260905_0004` |
| `positions.protection_*` 列 | **0** |
| `ck_positions_protection_*` 约束 | **0** |
| 变更表 | 仅 `alembic_version`、`positions`（downgrade 只删 0006 增量） |

**重要发现（纠正 F01 devlog §6 的建议）**：共享主库 `marketpulse` **含真实数据**——`positions=3`、`trades=3`、`execution_intents=134`、`strategy_candidates=28`、`fills=4`、`paper_orders=5`（24 表，digest `ffc06271e1a2de7ccf733cea26326c252d673b89c08bcb14bb524f7ead74dc5a`）。

⇒ F01 devlog §6 所述「运行本套件前主库必须先 `alembic upgrade head`」**不应再执行**：把承载真实持仓状态的库当作测试目标既污染数据、又违反「不得让主库停在 0006」。R1 改为在**独立 PG 实例**上验证（见 4.3）。

### 4.2 `TEST-ENVIRONMENT ISOLATION CONSTRAINT`——结构性绑定（含 file:line 证据）

单次全量调用**无法**仅靠进程级 `DATABASE_URL` 指向一个「不同名的隔离库」。三处**互相冲突**的既有绑定：

| # | 位置 | 绑定 |
|---|---|---|
| 1 | `backend/alembic/env.py:12` | `os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))` —— **进程环境变量优先**于 per-call `set_main_option` |
| 2 | `test_group2.py:1152-1163`、`test_n01_okx_paper_safety.py:414-435`、`test_n01_restart_recovery.py:421-434`、`test_n01_runtime_resource_lifecycle.py:312-333`、`test_se_02a_edge_persistence.py:108-117` | 自建 disposable 库**只**用 `config.set_main_option("sqlalchemy.url", url)` + `command.upgrade`，**不**设 `os.environ` ⇒ 任何进程级 `DATABASE_URL` 都会把它们的迁移打到别的库，自己的库保持未迁移（**36** 项伪失败即由此产生，见 §5.2） |
| 3 | `test_group5_2_trading_replay.py:60` + `:481` | `PRIMARY_URL = Settings().database_url`（import 时）+ `assert result.primary_database == "marketpulse"` ⇒ `Settings` 必须解析到**名为** `marketpulse` 的库 |
| 4 | `test_group3.py:56-57`、`test_group4.py:84-85` | import 时 `create_async_engine(Settings().database_url)`，无 disposable workspace ⇒ 该库必须已在 **0006**（F01 保护列） |

（3）+（4）要求目标库**名为 `marketpulse` 且处于 0006**；（1）+（2）禁止用进程级环境变量把套件指向别处 ⇒ 唯一满足的库就是共享主库，而它必须留在 0004。

### 4.3 解法：专用隔离 PG 实例 + 既有 `.env` 接缝（零产品架构改动）

- 项目**无** `load_dotenv`（全仓 `backend/src`、`backend/tests`、`scripts`、`backend/alembic` 扫描为 0 命中）⇒ `.env` **只**被 pydantic-settings 读进 `Settings`，**不**写入 `os.environ`；`alembic/env.py` 继续走 `config.get_main_option(...)` fallback ⇒ 约束（1）(2) 同时满足。
- 起一个**独立 PG 实例**（Docker `postgres:16-alpine`，`127.0.0.1:5433`，库**名仍为** `marketpulse`，无命名卷、可与主实例完全无关）⇒ 约束（3）(4) 同时满足。
- worktree 根写 gitignored `.env`：`DATABASE_URL=postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5433/marketpulse`。

**未修改任何产品架构、未新建 DB 编排子系统、共享主库零改动。**

## 5. Verification（全部实际执行）

### 5.1 §11 迁移闸门（disposable PG，`scripts/verify_n01_7_f01_r1_migration_gate.py`）

`result = PASS`（完整 JSON：`E:/Temp/r1_gate3.txt`）。要点：

- 单 head `20260912_0006`，`down_revision = 20260911_0005`；
- 0005 期无任何 protection 列；`0005 → 0006` 后 5 列 + 3 约束，**行数不变**；
- 兼容矩阵：CASE_A_FLAT = NULL；**CASE_B_OPEN = `backfilled plan-r1-case-b v1 [80.0, 140.0]`**，且 `protection_updated_at == trade_plans.created_at`（30 天前创建 = **TTL 被忽略**）；CASE_C ×5 = NULL；AMBIGUITY_PROBE 的第二个 ACTIVE plan 被 `uq_trade_plans_one_active` 拒绝（`IntegrityError`）⇒ 健康 schema 下「同 symbol 双 ACTIVE plan」不可达；
- ambiguity guard（stub connection 直调迁移函数）：单候选 `converted=1/updates=1`；双候选 `not_authoritative=1/converted=0/updates=0`；不可解析 payload `not_authoritative=1/updates=0`；
- downgrade 后列 / 约束清空，legacy 行 fingerprint 与升级前**完全一致**；`0005→0006→0005→0006` 复跑 `cycle_reproduced_identical_values = True`；
- 共享主库 `before == after == 20260905_0004`；`disposable_residue = 0`。

### 5.2 隔离库里先前的伪失败已定性（不改 harness 语义，仅修正我自己的导出方式）

首轮分段回归曾出现 **36 项**失败（`test_se_02a_edge_persistence` 25 / `test_n01_restart_recovery` 6 / `test_n01_okx_paper_safety` 2 / `test_group2` 1 / `test_group5_2` 1 / `test_n01_runtime_resource_lifecycle` 1），失败签名统一为 `relation "…" does not exist` + `primary_database` 名称不符。

根因**唯一**：我在 shell 中 `export DATABASE_URL=<隔离库>`，命中 `alembic/env.py:12` 的环境变量优先，使 §4.2 表中 5 个「只用 `set_main_option`」的文件的迁移落到别处（**非产品缺陷、非测试语义缺陷**，是执行方式伪影）。修正执行方式后这 36 项全部转绿（§5.4 / §5.5），失败集合被完全解释 ⇒ 非 rerun-until-green。

### 5.3 静态门

| 门 | 命令 | 结果 |
|---|---|---|
| ruff | `py -3.14 -m ruff check backend/src backend/tests scripts` | `All checks passed!` |
| compileall | `py -3.14 -m compileall -q backend/src scripts` | exit 0 |
| whitespace | `git diff --check` | exit 0 |
| 收集 | `py -3.14 -m pytest backend/tests --collect-only -q` | `295 tests collected` |

### 5.4 分段门（两个目标互斥，均不触碰共享主库）

| 段 | `DATABASE_URL` | 覆盖 | 结果 |
|---|---|---|---|
| A | **未设置**（8 个自建 disposable 库的文件） | `test_group2`(30) `test_group5_2`(7) `test_group5_3`(5) `test_group5_4`(10) `test_n01_okx_paper_safety`(4) `test_n01_restart_recovery`(6) `test_n01_runtime_resource_lifecycle`(6) `test_se_02a_edge_persistence`(26) = **94** | **94 passed**（230.25s） |
| B | `…:5432/marketpulse_r1_9f4c1ab77e02`（0006） | `test_group3`(16) `test_group4`(105) `test_group5_1_replay`(10) `test_se_02a_edge_contracts`(62) `test_group1`(6) `test_auth`(2) = **201** | **201 passed**（115.39s，1 warning） |

### 5.5 §13 单次全量调用（专用隔离 PG 实例，独占）

```
$ unset DATABASE_URL
$ PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q
295 passed, 1 warning in 386.06s (0:06:26)
```

前置断言（同一次调用内）：`EFFECTIVE_DATABASE_URL postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5433/marketpulse`、`OS_ENVIRON_DATABASE_URL None`。

**这是本项目首次出现「单次调用、全量 295 例、且不要求共享主库离开 0004」的干净 PASS。**

### 5.6 隔离与残留取证

| 项 | 实测 |
|---|---|
| 共享主库 `marketpulse`@5432 指纹（运行前 / 运行中 / 运行后） | digest `ffc06271e1a2de7ccf733cea26326c252d673b89c08bcb14bb524f7ead74dc5a` ×3 **完全一致**；revision `20260905_0004`；protection 列 0 |
| 5432 库清单 | `['marketpulse', 'marketpulse_r1_9f4c1ab77e02']`（无新增 disposable 残留） |
| 5433 库清单 | `['marketpulse']`（全量运行 disposable 残留 = **0**） |
| client backends | 5432 = 1、5433 = 1（均为探针自身）⇒ 无泄漏连接 |

### 5.7 变异验证（防「通过但不载荷」的假回归）

把 `g4/protection.py::evaluate` 临时改回 plan-first（`load_valid_long_active_plan` + `authority_from_plan`，snapshot 仅 fallback）→ `test_f01_r1_02`（bid 落到新 plan 的 95 之下）与 `test_f01_r1_05`（无快照持仓被「有效 plan」救活）**确实 FAIL**；其余 3 项 PASS。还原后 sha256 `cbd83f6a31a30f2280cc03629249760f76600819f842b21eda8a50747ed8d9db`，**逐字节一致**。

## 6. Residual / Known Gaps（不扩大、不隐瞒）

- `test_group3.py` / `test_group4.py` 仍以 import-time `Settings()` 直连「当前配置库」，**没有**自己的 disposable workspace；因此它们**必须**运行在隔离实例或已升级到 0006 的库上。本批用隔离实例规避，未改这两个文件的架构。
- §4.2 的 5 个「只用 `set_main_option`」的 disposable helper 与 `test_group5_2.py:60-96`「显式 save/restore `os.environ`」的写法**不一致**；前者在存在进程级 `DATABASE_URL` 的环境里必然误迁移。本批**记录为环境/测试基建观察项**，未修改（Scope Isolation）。
- `test_group5_2.py:481` 的 `primary_database == "marketpulse"` 是**名称字面绑定**，使「把套件指向不同名库」在语义上不可行。若未来需要任意库名的隔离，须由人工决策修改该断言语义（本批不擅自改）。
- `.env`（gitignored）与 5433 容器为**一次性验证环境**，非产品配置；收尾已清理（见 §8）。
- 保护权威相关的真实 AI / Live Trading / Integrated Runtime Host 依赖：**不存在**（结构事实：无新 service / scheduler / provider）。

## 7. Git / GitHub Review 工作流

- 遵循 `AGENTS.md`：commit → push `fix/n01-7-f01-durable-protection-snapshot` → **不 merge `main`**，返回 branch / commit SHA / Completion Report，然后 STOP。
- **Review 之后、Closeout 之前不新增任何提交**（除本批自审增量外）；本批所有提交均在人工 Re-Review 之前完成。
- `DECISIONS.md` / `PROJECT_STATE.md` / `AI_CONTEXT.md` **未修改**——与 F01 §7 一致：contract change 在人工验收 PASS 前不写入 "Approved Decisions" 与状态文件（CIP-09）。本 devlog 是本批状态的权威记录。

## 8. Files Changed（相对 `9d22240`）

| 文件 | 变更 |
|---|---|
| `backend/alembic/versions/20260912_0006_position_protection_snapshot.py` | 重写（+142/-…）：模块级列/约束常量、确定性 legacy backfill、downgrade 只删增量 |
| `backend/src/marketpulse/g4/planning.py` | `resolve_open_position_protection` → 同步、快照唯一 |
| `backend/src/marketpulse/g4/protection.py` | 两处调用点改快照权威；§7 退出 identity |
| `backend/src/marketpulse/g4/control.py` | resume / safe-mode gate 改快照权威 |
| `backend/src/marketpulse/g4/reconciliation.py` | invariant #13 直接消费规范化契约（报告 key / 诊断串未变） |
| `backend/src/marketpulse/g3/protection_snapshot.py` | docstring 对齐 Candidate A（函数代码未改） |
| `backend/tests/test_group4.py` | +R1 回归 `test_f01_r1_01..05`、F01-12/14/15/16 期望翻转、2 处 resume 断言放宽为 `_assert_resume_refused_for_missing_authority`、`test_fg_b_*` 保护单归属修正、G3 setup helper |
| `scripts/verify_n01_7_f01_r1_migration_gate.py` | 新增：§11 迁移闸门（disposable PG，7 步断言 + JSON 报告） |
| `dev_log/2026-09-12-n01-7-f01-r1-protection-authority-closure.md` | 新增：本文件 |

`git diff --stat`（tracked）：7 files changed, **782 insertions(+), 132 deletions(-)**。

收尾环境清理：删除一次性 `.env`、停止并移除 5433 隔离容器、DROP 隔离库 `marketpulse_r1_9f4c1ab77e02` ⇒ 5432 恢复为仅 `marketpulse`（0004）。
