# SE-02C｜Forward Outcome Calculator

- Date: 2026-09-13
- 专项: SE｜Strategy & Trading Edge
- Batch: SE-02C
- Branch: `se-02c-forward-outcome-calculator`
- Worktree: `E:\Documents\MarketPulse-AI-se-02c`（从 Accepted Main clean worktree 创建）
- Status: `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（未自行 Acceptance，未 merge `main`，未 push `main`，未启动长期 runtime，未开始 SE-02D）
- Implementation Commit: `721c488`
- Test Coverage Commit: `7a68bf0`
- Docs / Status Commit: 本文件所在 commit = 远端 branch tip（`7a68bf0` 的**子** commit；SHA 见
  §29 Evidence 的远端复读）

---

## 1. Task

实现并验证 **Deterministic Forward Outcome Calculator**：把已验收的 SE-02A / SE-02B Edge 事实
（opportunity evidence + FIX-01 capture anchor + normalized BBO observations）确定性转换为
**终态、不可变、可重算**的 Forward Outcome 记录。

```text
Forward Evidence → Forward BBO Path Capture → Durable Horizon Due Discovery
  → Deterministic Calculator → Terminal ForwardOutcome → Append-only Persistence
```

## 2. Requirement

| # | 要求 | 出处（任务书） |
|---|---|---|
| R1 | NO NEW MIGRATION / NO SCHEMA CHANGE；Alembic head 必须保持 `20260913_0009` | §10、§62-§63、§66 |
| R2 | 复用已验收契约与 writer，不新增 BBO 表 / Outcome 表 / 第二档案 | §62、§64 |
| R3 | 四个 horizon `30s` / `5m` / `15m` / `1h`，各自独立 `due_at` / `outcome_id` / scope / revision chain | §7、§67 C-15 |
| R4 | 冻结 V1 公式（mid / reference return / executable LONG / MFE-MAE / 成本） | §32-§36、§53 |
| R5 | `due_at = evidence_at + horizon.duration`；因果截断 `available_at <= due_at` | §13、§22、§48 |
| R6 | reference 权威 = FIX-01 durable capture anchor BBO | §18、§23 |
| R7 | endpoint 5 s freshness TTL；PENDING 仅派生不落库；仅三类终态 | §24、§27、§41-§43 |
| R8 | 评估者只写 `outcome_revision = 1`；retry / later run 不得自动产生 revision 2 | §9、§44、§46 |
| R9 | 无 resident loop / scheduler / 第二个 OKX WS / 第二条行情管线 | §15、§17、§64 |
| R10 | required regression：SE-02A/B、FIX-01、FIX-02、G5、full backend（环境允许必须跑） | §65 |
| R11 | static gates：ruff / compileall / `git diff --check` / `alembic heads` 单 head | §66 |
| R12 | 产出 `dev_log/2026-09-13-se-02c-forward-outcome-calculator.md`（含 §68 全部章节） | §68 |
| R13 | 完成后状态 `SE-02C = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`，随后 STOP | §69、§73 |

---

## 3. Repository Truth（preflight 实测）

| 项 | 值 | 读取方式 |
|---|---|---|
| Task Base SHA | `8a29306d904223f03408fe55538ba6cb05222f15` | `git rev-parse HEAD` |
| 远端 `main` | `8a29306d904223f03408fe55538ba6cb05222f15` | `git ls-remote origin refs/heads/main` |
| 本地 `main` | `8a29306d904223f03408fe55538ba6cb05222f15` | `git rev-parse main` |
| Migration head（实现前 / 后） | `20260913_0009` / `20260913_0009`（**单 head，未新增**） | `cd backend && py -3.14 -m alembic heads` |
| G5 `schema_head` | `20260913_0009`（未改） | `g5/replay.py:453` |
| Task Branch | `se-02c-forward-outcome-calculator`（此前不存在） | `git for-each-ref` |
| Worktree | `E:\Documents\MarketPulse-AI-se-02c` | `git worktree list --porcelain` |
| 最终远端 branch tip | `7a68bf0…` | `git ls-remote origin refs/heads/se-02c-forward-outcome-calculator` |
| 最终远端 `main` | `8a29306…`（**未变**） | `git ls-remote origin refs/heads/main` |

**判定：无 baseline drift，未触发 §70 STOP。**

## 4. Pre-SE-02C Re-Gate Authorization

任务书声明 Pre-SE-02C Re-Gate 已返回 `PASS — SE-02C MAY START`，本窗口即为该 gate 授权的
Implementation + Verification 窗口。**该 gate 记录为外部任务书内容**，本仓库内无副本；
本窗口**未**自行签发 gate、**未**改 `PROJECT_STATE.md` 中该 gate 的既有表述。

## 5. Recovery Preflight

本窗口开工前的现场实测（只读）：

| 检查 | 结果 |
|---|---|
| 既有 `se-02c*` branch（本地/远端） | 不存在 |
| 既有 `E:\Documents\MarketPulse-AI-se-02c` 目录 | 不存在 |
| 既有 SE-02C 相关 commit / untracked 实现 | 无 |
| 其它 writer 正在实现同一 Acceptance Boundary | 未发现 |

**结论：从 Accepted Main `8a29306` 新建 branch + worktree，无半成品需保留（未执行任何
reset / checkout . / stash / clean）。** 工作区 `E:\Documents\MarketPulse AI`（脏历史 worktree）
全程**只读**，本批的文档读取一律取自 clean worktree。

---

## 6. Scope

允许并实际修改（4 个代码/测试文件 + 3 个文档文件）：

```text
backend/src/marketpulse/edge/forward.py                          （新增）
backend/src/marketpulse/edge/forward_service.py                  （新增）
backend/src/marketpulse/edge/__init__.py                         （修改：包内模块清单）
backend/src/marketpulse/g2/runtime.py                            （修改：opt-in ingress hook）
backend/tests/test_se_02c_forward_outcome_calculator.py          （新增）
backend/tests/test_se_02c_forward_outcome_service.py             （新增）
dev_log/2026-09-13-se-02c-forward-outcome-calculator.md          （本文件）
PROJECT_STATE.md / AI_CONTEXT.md                                 （最小状态同步）
```

## 7. Out of Scope（未触碰，符合 §63 / §64）

`backend/alembic/**`、`backend/src/marketpulse/db/models.py`、G3/G4 economic semantics、
G5 business semantics、`frontend/**`、`PRODUCT_REQUIREMENTS.md`、`DECISIONS.md`；
SE-02D aggregation / expectancy / KEEP-DOWNWEIGHT-KILL / strategy ranking / AI learning /
Trade-Risk-Execution redesign / Portfolio / Live Trading / UI / Dashboard / generic scheduler /
Integrated Runtime Host / Kafka / Redis / Celery / L2-L3 order book / candles-based math /
trade-fill MFE-MAE / new BBO table / new Outcome table / new migration；
`TEST-ISO-01` / `RRF-03` / `RRF-04` 维持独立 P2，**未**顺手修复。

---

## 8. Frozen V1 Formulas

```text
reference_mid          = (reference_bid + reference_ask) / 2
end_mid                = (end_bid + end_ask) / 2
reference_return       = end_mid / reference_mid - 1
executable_long_return = end_bid / reference_ask - 1
path_return(i)         = mid(i) / reference_mid - 1
MFE                    = max(0, path_returns)        参考点 0.0 计入
MAE                    = min(0, path_returns)
entry_exec             = reference_ask * (1 + slippage)
exit_exec              = end_bid * (1 - slippage)
cost_adjusted          = (exit_exec * (1 - fee)) / (entry_exec * (1 + fee)) - 1
```

```text
CALCULATOR_VERSION = "se02c-forward-outcome-v1"
COST_POLICY        = "SPOT_LONG_TAKER_ROUND_TRIP"
COST_MODEL_VERSION = "se02c-paper-cost-v1"
FEE_RATE = 0.001    SLIPPAGE_BPS = 5    SLIPPAGE_FRACTION = 0.0005
END_FRESHNESS_TTL = 5 s             FORWARD_PATH_WINDOW = 3600 s
RUNTIME_OUTCOME_REVISION = 1
```

成本为**精确乘性模型**：测试直接断言它与 `reference_return − 2·fee − 2·slippage` 近似式
差值 > 1e-9（§36）。

## 9. Implementation

### 9.1 新增 `edge/forward.py` —— 纯计算核心（557 行）

无 DB、无 Clock、无 `Settings`、无 IO：`ForwardScopeFacts`、`ForwardReference`、
`ForwardOutcomeReason`、`ForwardObservationSelection`、`classify_forward_observations()`、
`forward_due_at()`、`is_forward_due()`、`forward_cost_prices()`、
`cost_adjusted_forward_return()`、`calculate_forward_outcome()`。

分类顺序（冻结）：`INVALID` → `INSUFFICIENT_DATA` → `COMPLETE`；不可计算指标一律 NULL。
`created_at` 冻结为 `due_at`（重试/重启得到同一 `outcome_record_hash`），
`outcome_revision` 恒为 1，`supersedes_outcome_id` 恒为 `None`。

### 9.2 新增 `edge/forward_service.py` —— durable orchestration（619 行）

`build_forward_path_observation()`、`ForwardPathRecorder`、`DueForwardScope`、
`discover_due_scopes()`、`load_forward_outcome_contract()`、`_contract_from_record()`、
`ForwardOutcomeService`（`evaluate_due_outcomes` / `evaluate_scope` / `calculate_scope` /
`append_outcome`）、模块级 `evaluate_due_outcomes()`。
**无** `sleep` / `while` / scheduler / daemon / cache。

### 9.3 修改 `g2/runtime.py` —— 最小 opt-in ingress hook（+20 −0）

`ScannerPipeline.__init__(..., forward_path_recorder: ForwardPathRecorder | None = None)` 与
`async def record_forward_path(market_event)`（仅当 recorder 已注入且帧为
`NormalizedBookTicker` 时转发）。**未注入时接受路径逐字节不变**；historical replay pipeline
永远拿不到 recorder。未新增 WS、未新增行情管线。

### 9.4 新增测试

`test_se_02c_forward_outcome_calculator.py`（864 行，37 项，纯核心）与
`test_se_02c_forward_outcome_service.py`（1200+ 行，10 项，真实 disposable PostgreSQL）。

## 10. Forward Path Capture（§15-§17、C-17）

- 仅当同一 `instrument_id + market_type` 存在 `FORWARD_PAPER` evidence 且
  `evidence_at <= available_at <= evidence_at + 1h` 时才落库；没有窗口 ⇒ **完全不归档**。
- 存储只经已验收 `record_bbo_observation()`（content-addressed、append-only）：
  无第二条 BBO 档案、无第二个 identity、无全市场 dump。
- `available_at = received_at`（V1 因果规则）、`created_at = received_at` ⇒ 重放同一帧得到
  同一 `observation_id` ⇒ `IDEMPOTENT`。
- 不可表示的帧（crossed / 非正 / 非有限）在 ingress 边界跳过并记日志，不中断 ingest。
- 实测：无 evidence ⇒ `None` + 0 行；开窗后 ⇒ `INSERTED`；同帧重放 ⇒ `IDEMPOTENT`；
  第二个 opportunity 复用同帧 ⇒ `IDEMPOTENT`（**共享一行**，不是第二份）；
  `+3601 s` ⇒ `None`；crossed ⇒ `None` 且不抛；`HISTORICAL_REPLAY` evidence 不构成窗口。

## 11. Due Discovery（§39-§40、C-03）

`due_at = evidence_at + duration` ⇒ `due_at <= now` 严格等价于 `evidence_at <= now - duration`。
discovery 是 immersive 事实 + 评估时钟的纯函数：只用 PostgreSQL 行，**进程内零记忆**。
实测：`now = START+29 s` ⇒ `[]`；`now = START+30 s` ⇒ `["30s"]`；
`now = EVAL_NOW` ⇒ 四 horizon，`due_at` 逐一等于 `forward_due_at(START, horizon)`。

## 12. Reference Selection（§18、§23、C-05）

- `FORWARD_PAPER` scope：reference 取 FIX-01 durable capture anchor 的
  `reference_bbo_observation_id`，回读该 BBO 行作为权威价格；**永不**使用"评估时最新报价"。
- anchor 缺失 ⇒ `INVALID_FORWARD_ANCHOR_MISSING`（fail closed）；anchor 指向的 BBO 行不存在 ⇒
  `INVALID_REFERENCE_OBSERVATION_MISSING`。
- `HISTORICAL_REPLAY` scope：无 Forward anchor（设计如此），使用其已冻结的 reference metrics。
- 实测：`reference_bbo_observation_id == anchor.reference_bbo_observation_id`，
  `reference_price == (anchor.bid + anchor.ask)/2 == 100.0`。

## 13. End Selection（§20-§22、C-06）

合格性（有序，每条只进一个桶）：identity → `FRESH` → `tradable` → `available_at <= due_at`。
endpoint = 合格集合在总序 `(available_at, has_source_sequence, source_sequence,
observation_id)` 上的最大值；path points = 合格集合中 `available_at > evidence_at` 的部分。

## 14. Causal Rules（§22、§48、C-22）

`available_at > due_at` 的观测是**未来数据**：durable 层加载窗口已截断
（`evidence_at <= available_at <= due_at`），纯核心再独立拒绝一次。
实测：30s horizon 账面 6 条 durable 观测，但窗口只加载 3 条；5m 4 条；15m 5 条；1h 6 条；
四个 endpoint 全部 `<= due_at`（`+29` / `+299` / `+899` / `+3599`）。

## 15. Cost Model（§32-§36、C-11）

见 §8。实测（reference_ask = 100.5、end_bid = 103.0）：
`cost_adjusted == ((103 × 0.9995) × 0.999) / ((100.5 × 1.0005) × 1.001) − 1`，
且与近似式差值 > 1e-9。

## 16. Terminal Classification（§41-§45、C-12/13/14）

| 状态 | 触发 | 绑定 | 指标 |
|---|---|---|---|
| `COMPLETE` | reference OK + 有合格 endpoint 且距 `due_at` ≤ 5 s | reference + end 观测 | 全量产出 |
| `INSUFFICIENT_DATA` | reference missing/stale、无 endpoint、endpoint 龄 > 5 s | reference（若已接受）、**不绑** end | 全 NULL |
| `INVALID` | durable 事实自相矛盾 / 结构不可能（含 Forward scope 缺 anchor） | 全 NULL | 全 NULL |

`PENDING` **不落库**（实测 `pending_rows == 0`）；`opportunity_lifecycle_at_horizon` 由
`due_at < expires_at` 判定（实测 30s/5m/15m = `ACTIVE`，1h = `EXPIRED`）。

## 17. Concurrency（§57-§58、C-19）

两个**独立 engine**（独立连接池）并发 `evaluate_scope` 同一 scope：
PostgreSQL 由 `uq_edge_outcome_evidence_horizon_revision` 保证**恰一行**，落败方在
`_reconcile()` 回读并返回等价记录，而不是抛裸 `IntegrityError`。
实测：1 行、`distinct_returned_outcome_ids == 1`、`distinct_returned_hashes == 1`、
两个 caller 都持有该持久行；第二轮并发后仍 1 行。

## 18. Restart（§57、C-18）

第一轮 evaluate 用 engine₁，跑完 `dispose()`；随后**新建 engine₂**（全新连接池、零继承记忆）
重新发现：`discover_due_scopes(now)` ⇒ `[]`；`discover_due_scopes(now + 4h)` ⇒ `[]`；
`evaluate_due_outcomes` 第二遍 ⇒ 0 条；总行数不变；`created_at == due_at` 对 4/4 成立。

## 19. Retry / Idempotency（§46、C-20）

对已结算 scope 重试 `evaluate_scope`（同一 durable 事实）⇒ 返回**同一** `outcome_id` 与
同一 `outcome_record_hash`，行数不变。
事实变化（结算后落一条窗口内 late frame）时：`discover_due_scopes` 仍拒绝重开该 scope
（**C-21 不产生自动 revision 2**）；强制重评估抛 `EdgeOutcomeConflict`（fail closed），
行数仍 4、revision 仍全 1 —— 这是刻意的失败关闭，不是 revision 2。

---

## 20. Files Changed

| 文件 | 类型 | 行数 | 变更 |
|---|---|---|---|
| `backend/src/marketpulse/edge/forward.py` | 新增 | 557 | 纯计算核心 |
| `backend/src/marketpulse/edge/forward_service.py` | 新增 | 619 | path recorder / due discovery / bounded evaluation |
| `backend/src/marketpulse/edge/__init__.py` | 修改 | +5 −3 | 包内模块清单 |
| `backend/src/marketpulse/g2/runtime.py` | 修改 | +20 −0 | opt-in ingress hook |
| `backend/tests/test_se_02c_forward_outcome_calculator.py` | 新增 | 864 | 37 项 |
| `backend/tests/test_se_02c_forward_outcome_service.py` | 新增 | ~1210 | 10 项（真实 PG） |
| `dev_log/2026-09-13-se-02c-forward-outcome-calculator.md` | 新增 | 本文件 | 文档 |
| `PROJECT_STATE.md` / `AI_CONTEXT.md` | 修改 | 局部 | 状态同步 |

**未新增 migration**；`backend/alembic/**` 与 `backend/src/marketpulse/db/models.py` 零改动。
Commit：`721c488`（implementation）、`7a68bf0`（test coverage）、docs commit（本文件 + 状态）。

## 21. Business Behavior

一个已验收 Forward Paper opportunity（`FORWARD_PAPER` evidence + FIX-01 anchor）在
`evidence_at + horizon` 之后，系统可确定性地得到一个终态 Forward Outcome：
它绑定被接受的 reference BBO 与 horizon endpoint，给出该 horizon 的
`reference_return` / `executable_long_return` / `cost_adjusted_forward_return`
与路径 `mfe` / `mae`，且**同一份 durable 事实永远得到同一条记录**（同 hash），
无论何时、由哪个进程、重试多少次评估。

---

## 22. Verification

### 22.1 测试（真实 disposable PostgreSQL @ `127.0.0.1:5438`）

每个测试自建 + 自删 disposable database（`CREATE DATABASE` → `alembic upgrade head` →
跑 → `pg_terminate_backend` + `DROP DATABASE`）；共享 `:5432`、FIX-02 legacy `:5437`、
N01 DB 均**未被本批触碰**。

| 范围 | 命令 | 结果 |
|---|---|---|
| SE-02C focused | `pytest backend/tests/test_se_02c_forward_outcome_calculator.py backend/tests/test_se_02c_forward_outcome_service.py -q` | **47 passed**（27.73 s；37 纯 + 10 集成） |
| 命名回归（SE-02A contracts/persistence、SE-02B capture/attribution、G5-1..4） | 见 §25 Evidence | **196 passed**（269.99 s） |
| Full backend | `pytest backend/tests -q` | **418 passed**，1 warning（`StarletteDeprecationWarning`），457.05 s |

baseline：SE-ARCH-FIX-02 收编时 full = 371；371 + 47 = **418** ⇒ 新增 47 项、既有 **0** 回归。

### 22.2 Static / repository gates（§66）

| 门 | 命令 | 结果 |
|---|---|---|
| Lint | `py -3.14 -m ruff check backend/src backend/tests scripts` | `All checks passed!`（RC=0） |
| 语法 | `py -3.14 -m compileall -q backend/src backend/tests` | RC=0 |
| Whitespace | `git diff --check` | 无输出 |
| Migration | `cd backend && py -3.14 -m alembic heads` | `20260913_0009 (head)` — **单 head** |
| G5 head 常量 | `g5/replay.py:453` | `schema_head = "20260913_0009"`（未改） |

### 22.3 隔离性

本批测试的 `PRIMARY_URL = Settings().database_url` ⇒ worktree 根 gitignored `.env`
⇒ `127.0.0.1:5438/marketpulse`（本批专用容器 `marketpulse-se-02c-pg`，已迁到 head
`20260913_0009`）。**已实测**：共享 `:5432` 未被升级、未被写入。

### 22.4 环境发现（必须写入，避免下一窗口重踩）

🚩 **跑本批测试时不得导出 `DATABASE_URL`。**
`backend/alembic/env.py` 是
`os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))` —— **环境变量优先**。
本批测试 harness 用 `command.upgrade(config_with_disposable_url, "head")`（靠 config 回落），
首次运行时导出了 `DATABASE_URL`，于是迁移被打到环境变量指向的库、disposable 库保持空表，
症状为 `asyncpg.exceptions.UndefinedTableError: relation "edge_opportunity_evidence"
does not exist`（9/9 全红，极易误判为产品缺陷）。
正确姿势：`cd <worktree> && PYTHONPATH=backend/src py -3.14 -m pytest backend/tests`，**不设**
`DATABASE_URL`。

---

## 23. Acceptance Matrix（对照任务书 §67：C-01 ～ C-29）

判定只用 `PASS` / `FAIL` / `NOT VERIFIED`；**未推测 PASS**。

| 编号 | 判据 | 判定 | 证据 |
|---|---|---|---|
| C-01 | Repository Truth | **PASS** | `origin/main` = `8a29306…` = base，无 drift；worktree/branch 之前不存在；AGENTS.md CIP-02 实时读取 |
| C-02 | No Schema Change | **PASS** | `alembic heads` 单 head `20260913_0009`；`backend/alembic/**` 与 `db/models.py` `git diff` 空；G5 `schema_head` 未改 |
| C-03 | Due Determinism | **PASS** | `now=START+29s` ⇒ `[]`；`now=START+30s` ⇒ `["30s"]`；4 horizon `due_at == forward_due_at(START, h)` |
| C-04 | Pending Is Derived | **PASS** | 评估前该 scope 无行；落库行中 `PENDING` 计数 = 0；未到期 scope 不进入 discovery |
| C-05 | Stable Reference | **PASS** | `reference_bbo_observation_id == anchor.reference_bbo_observation_id`；`reference_price == anchor mid == 100.0`；无 anchor ⇒ `INVALID` 而非回落"最新报价" |
| C-06 | Causal End Selection | **PASS** | endpoint = 4 horizon 的 `+29 / +299 / +899 / +3599 s` 分别被选中；纯核心另有 3 组总序 tie-break 用例 |
| C-07 | End Freshness | **PASS** | 4/4 COMPLETE 的 `end_age_seconds <= 5.0`；纯核心另有 6 s 龄 ⇒ `ENDPOINT_STALE` + `INSUFFICIENT_DATA` |
| C-08 | MFE / MAE Formula | **PASS** | 5m 实测 `mfe == 0.04`、`mae == 0.0`；纯核心 §53 向量同值 |
| C-09 | Reference Return Formula | **PASS** | `reference_return == 104/100 − 1`（精确到 rel 1e-12） |
| C-10 | Executable LONG Return Formula | **PASS** | `executable_long_return == 103/100.5 − 1` |
| C-11 | Cost-Adjusted Formula | **PASS** | 等于精确乘性式；与近似式差值 > 1e-9；`cost_policy` / `cost_model_version` / `calculator_version` 三常量精确匹配 |
| C-12 | COMPLETE Classification | **PASS** | 4 horizon 全部 `COMPLETE`，reference + end 两个观测 id 都被绑定，诊断 `reason == "COMPLETE"` |
| C-13 | INSUFFICIENT_DATA Classification | **PASS** | 有 anchor 但无自身 forward 观测的 scope ⇒ `INSUFFICIENT_DATA`；6 个指标全 NULL；`end_*` 不绑定 |
| C-14 | INVALID Classification | **PASS** | 有 evidence、无 anchor 的 FORWARD_PAPER scope ⇒ `INVALID` / `INVALID_FORWARD_ANCHOR_MISSING`；`reference_*` / `end_*` / `mfe` 全 NULL |
| C-15 | Four Horizons Independent | **PASS** | 一次 pass ⇒ 4 行、4 个不同 `outcome_id`、4 个不同 `due_at`、各自 revision 1 |
| C-16 | Cross-Evidence Independent | **PASS** | 同一 opportunity 的 evidence rev1 / rev2 各占 4 个独立 scope（8 行、8 个不同 `outcome_id`）；rev1 仍 `COMPLETE` 且 `due_at` 未变；rev2 有自己的 `due_at = evidence_at₂ + duration` |
| C-17 | Forward Path Capture | **PASS** | 无窗口 ⇒ 不落库；开窗 ⇒ `INSERTED`；同帧重放 ⇒ `IDEMPOTENT`；两 opportunity 共享 1 行；`+3601 s` ⇒ 不落库；crossed ⇒ 跳过；`HISTORICAL_REPLAY` 不构成窗口 |
| C-18 | Restart Determinism | **PASS** | engine₂ 重发现 ⇒ `[]`；第二遍 evaluate ⇒ 0 条；行数不变；4/4 `created_at == due_at` |
| C-19 | Concurrent Exactly-One Outcome | **PASS** | 两独立 engine 并发 ⇒ 1 行；返回的 `outcome_id` 与 `outcome_record_hash` 各只有 1 种；两 caller 都持有该持久行 |
| C-20 | Retry Idempotency | **PASS** | 重试返回同一 `outcome_id` / 同一 `outcome_record_hash`，行数不变 |
| C-21 | No Automatic Revision 2 | **PASS** | 全部落库行 `outcome_revision == 1`、`supersedes_outcome_id IS NULL`；late frame 到达后 discovery 仍拒绝重开；强制重评估 ⇒ `EdgeOutcomeConflict`（**未**写 revision 2） |
| C-22 | Late/Future Observation Rejected | **PASS** | 6 条 durable 观测中，30s/5m/15m/1h 窗口只加载 3/4/5/6 条；4 个 endpoint 全部 `<= due_at`；纯核心另有 `available_at > due_at` 排除用例 |
| C-23 | Replay / Forward Digest Separation | **PASS** | 纯核心断言：同一市场事实的 `HISTORICAL_REPLAY` 与 `FORWARD_PAPER` outcome 共享 `calculation_digest`、`outcome_record_hash` 不同（provenance 只进后者） |
| C-24 | Provenance Inheritance | **PASS** | durable 行 `source_type == "FORWARD_PAPER"`、`source_identity == "okx-ws-bbo"`，与其 evidence 行逐字一致 |
| C-25 | FIX-01 Regression | **PASS** | FIX-01 回归面（capture anchor / `reference_bbo_observation_id` / anchor 冲突与篡改防护）在 `test_se_02b_opportunity_capture.py`，属 196 命名回归且全绿；本批未改 `edge/capture.py` 与 anchor 表 |
| C-26 | FIX-02 Regression | **PASS** | FIX-02 回归面（scoped supersedes：`EdgeInvalidOutcomeSupersedes` 跨 evidence / horizon / opportunity 全部 fail closed）在 `test_se_02a_edge_persistence.py`，属 196 命名回归且全绿；本批未改 `edge/repository.py`、`db/models.py`、migration |
| C-27 | SE-02A/B Regression | **PASS** | `test_se_02a_edge_contracts.py`、`test_se_02a_edge_persistence.py`、`test_se_02b_attribution.py`、`test_se_02b_opportunity_capture.py` 全绿 |
| C-28 | Full Backend | **PASS** | `pytest backend/tests -q` ⇒ **418 passed**，0 failed |
| C-29 | Scope | **PASS** | 改动面 = 4 个代码/测试文件 + 3 个文档文件；`git diff --name-only 8a29306 HEAD` 不含任何 §63 forbidden 文件 |

---

## 24. Self-Check（Reviewer 应重点挑战处）

1. **`INSUFFICIENT_DATA` 仍绑定 reference**（C-13）。reference 已 `OK` 但 horizon 无可用 endpoint
   时，`reference_bbo_observation_id` 会绑定（它是被**接受**的参考），只有 `end_*` 与全部指标
   为 NULL。刻意语义：reference 是可审计的已接受事实，horizon 只是不可计算。
2. **窗口内只有 anchor BBO 自身时 reason 是 `ENDPOINT_STALE` 而非 `ENDPOINT_MISSING`。**
   冻结合格性规则（identity → FRESH → tradable → `available_at <= due_at`）未对
   `available_at <= evidence_at` 另设下界，因此 anchor 观测本身是合格候选，其龄 = horizon 长度
   > 5 s ⇒ `ENDPOINT_STALE`。**状态与指标契约不受影响**（仍 `INSUFFICIENT_DATA` + 全 NULL +
   不绑 end）。集成测试以"窗口是否为空"显式推导期望 reason，不硬编码猜测。
   → 若 Independent Review 认为 endpoint 只能取自 `available_at > evidence_at` 的 forward path，
   这是一处**语义收紧**（行为保持：任何情况下都不会改变 COMPLETE 判定），需另开窗口处理。
3. **事实变化后的强制重评估抛 `EdgeOutcomeConflict` 而非静默返回旧行**（C-21）。生产路径由
   `discover_due_scopes` 排除已结算 scope，正常不会走到；但 late frame 在结算后落库这类极端
   竞争会让强制重评估失败关闭。选择 fail closed 而非静默忽略内容差异。
   → 若 Reviewer 期望"已结算 scope 直接回读、不重算"，需要改 `evaluate_scope` 顺序，属行为
   变更，本批**未**自行决定。
4. **`ForwardPathRecorder` 对每帧做一次窗口查询。** recorder 已注入且窗口打开时，ingest 路径
   多一次 DB 读 + 一次可能的写；本批未做 batch / 缓存（避免引入未要求的状态）。
   → 若 N01-8 Integrated Runtime Host 认为影响 ingest 时延，属 N01-8 scope，需单独评估。
5. **`record_forward_path` 位于 trade-dedupe 早退之后**：重复 trade 帧不触发归档；BBO 帧不走
   trade dedupe，故不受影响。G2 既有行为由 418 全量回归背书。
6. **`evidence_revision = 2` 只能由 accepted append-only writer 产生**（C-16 场景）：
   SE-02B runtime capture 路径硬钉 `RUNTIME_CAPTURE_REVISION = 1`，本批未改该路径，
   C-16 用 `append_evidence_revision` 造出 rev2 来验证独立性。

## 25. Result

```text
SE-02C = IMPLEMENTED / READY FOR INDEPENDENT REVIEW
```

- 未写 `ACCEPTED` / `COMPLETE`；未 Human Accept；未 merge `main`；未 push `main`。
- `SE-02D` 仍 `NOT STARTED`；Long-running Runtime **NOT ACTIVATED**。
- C-01 ～ C-29 全部 `PASS`（无 `FAIL`、无 `NOT VERIFIED`、无推测）。

## 26. Remaining

- Independent Review（独立窗口，按 CIP-07 / CIP-08 不得采信本文件的自述结论）。
- Human Acceptance（本窗口不签发）。
- §24-2 / §24-3 两处语义点需 Reviewer 明确裁定；若需变更则另开窗口。
- SE-02D / N01-7 / N01-8 / Integrated Runtime Host 仍 `NOT STARTED`。

## 27. Known Risks

- 隔离容器 `marketpulse-se-02c-pg` @ `127.0.0.1:5438` 在验证期间保持运行，worktree 根与
  `backend/` 下存在 gitignored `.env`（**只含 `DATABASE_URL`**，未写 `ADMIN_PASSWORD`，
  故 `test_auth` 不受影响）。**本批未授权清理，故原样保留**供 Reviewer 复现；
  释放命令：`docker rm -f -v marketpulse-se-02c-pg` + 删除两处 `.env`。
  副作用：在该 worktree 跑 pytest 会走 5438 而非共享 5432。
- 本批测试 harness 依赖"`DATABASE_URL` 未被导出"（见 §22.4）；新窗口若习惯性导出会把测试
  打到错误库。
- `git commit` 提示 `LF will be replaced by CRLF` 是本机 `core.autocrlf` 行为；index blob 仍为
  LF-only，与仓库既有文件一致（已实测 Accepted Main 的 `capture.py` CRLF=0）。
- 未提交的 `.env` 不在 `git status` 中，**不会**被 push。

## 28. Context For Next AI

新增公开入口：

```text
marketpulse.edge.forward           ForwardScopeFacts / ForwardReference / ForwardOutcomeReason /
                                   classify_forward_observations / calculate_forward_outcome /
                                   forward_due_at / cost_adjusted_forward_return
marketpulse.edge.forward_service   ForwardPathRecorder / DueForwardScope / discover_due_scopes /
                                   ForwardOutcomeService / evaluate_due_outcomes /
                                   load_forward_outcome_contract
marketpulse.g2.runtime             ScannerPipeline(forward_path_recorder=...) /
                                   ScannerPipeline.record_forward_path()
```

- 跑本批测试：`cd E:\Documents\MarketPulse-AI-se-02c && PYTHONPATH=backend/src py -3.14 -m pytest backend/tests`，
  **不要**设 `DATABASE_URL`；确保 5438 容器在跑（否则先 `CREATE DATABASE` 会失败）。
- 上游契约：`edge/models.py`（`ForwardOutcomeContract` / `build_forward_outcome_contract` /
  `build_evidence_revision`）、`edge/repository.py`（`record_bbo_observation` /
  `append_forward_outcome` / `append_evidence_revision`）、`edge/capture.py`（FIX-01 anchor）、
  `db/models.py`（`uq_edge_outcome_evidence_horizon_revision`）。
- 若要加 horizon 或改公式：先确认 §8 冻结常量与 `ALL_FORWARD_HORIZONS`，这会改变
  `calculation_digest` 语义 —— 属新的 Requirement 决策，不得顺手改。

## 29. Evidence

| 证据 | 命令 / 位置 |
|---|---|
| focused | `py -3.14 -m pytest backend/tests/test_se_02c_forward_outcome_calculator.py backend/tests/test_se_02c_forward_outcome_service.py -q` ⇒ `47 passed in 27.73s` |
| 命名回归 | SE-02A contracts + persistence + SE-02B attribution + capture + G5-1/2/3/4 ⇒ `196 passed in 269.99s` |
| full backend | `py -3.14 -m pytest backend/tests -q` ⇒ `418 passed, 1 warning in 457.05s` |
| lint | `py -3.14 -m ruff check backend/src backend/tests scripts` ⇒ `All checks passed!` |
| compile | `py -3.14 -m compileall -q backend/src backend/tests` ⇒ RC=0 |
| whitespace | `git diff --check` ⇒ 无输出 |
| migration | `cd backend && py -3.14 -m alembic heads` ⇒ `20260913_0009 (head)` |
| G5 head | `grep -n schema_head backend/src/marketpulse/g5/replay.py` ⇒ `453: schema_head = "20260913_0009"` |
| remote truth | `git ls-remote origin refs/heads/main refs/heads/se-02c-forward-outcome-calculator` ⇒ `8a29306…` / `7a68bf0…`（收尾时复读） |
| 失败现场（环境伪影） | 首次 service run `9 failed`，全部 `relation "edge_opportunity_evidence" does not exist` ⇒ 根因 `DATABASE_URL` 优先级，见 §22.4 |
