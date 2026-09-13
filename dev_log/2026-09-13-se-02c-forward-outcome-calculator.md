# SE-02C｜Forward Outcome Calculator

- Date: 2026-09-13
- 专项: SE｜Strategy & Trading Edge
- Batch: SE-02C
- Branch: `se-02c-forward-outcome-calculator`
- Worktree: `E:\Documents\MarketPulse-AI-se-02c`（从 Accepted Main clean worktree 创建）
- Status: `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（未自行 Acceptance，未 merge `main`，未 push `main`）
- Implementation Commit: `721c488`
- 本文件 Commit: 见分支 tip（`721c488` 之后一个 docs-only commit）

---

## 1. Task / Requirement

实现并验证 **Deterministic Forward Outcome Calculator**：把已验收的 SE-02A/SE-02B Edge 事实
（opportunity evidence + FIX-01 capture anchor + normalized BBO observations）确定性转换为
**终态、不可变、可重算**的 Forward Outcome 记录。

链路：

```text
Forward Evidence → Forward BBO Path Capture → Durable Horizon Due Discovery
  → Deterministic Calculator → Terminal ForwardOutcome → Append-only Persistence
```

硬约束（任务书 §0-§6）：

```text
NO NEW MIGRATION / NO SCHEMA CHANGE  →  Alembic head 必须保持 `20260913_0009`
复用已验收契约                        →  ForwardOutcomeContract / edge_forward_outcomes /
                                        edge_bbo_observations / edge_opportunity_evidence /
                                        edge_opportunity_capture_anchors /
                                        record_bbo_observation() / append_forward_outcome()
四个独立 horizon                      →  30s / 5m / 15m / 1h，各自独立 due_at / outcome_id /
                                        scope / revision chain
不做 resident loop / scheduler / 第二个 OKX WS / 第二条 BBO 档案
```

前置授权：任务书声明 Pre-SE-02C Re-Gate 已返回 `PASS — SE-02C MAY START`。该 Re-Gate 记录是
**外部任务书内容**，本仓库内无副本；本窗口据此执行，**未**自行签发该 gate。

---

## 2. Repository Truth（preflight 实测）

| 项 | 值 |
|---|---|
| Task Base SHA（`git rev-parse HEAD`） | `8a29306d904223f03408fe55538ba6cb05222f15` |
| `origin/main`（`git ls-remote origin refs/heads/main`） | `8a29306…`（与 base 一致，无 drift） |
| 创建 worktree 的分支 | `se-02c-forward-outcome-calculator`（此前不存在） |
| Migration head（实现前） | `20260913_0009`（单 head） |
| Migration head（实现后） | `20260913_0009`（单 head，**未新增迁移**） |
| Implementation Commit | `721c488` |
| 隔离数据库 | `marketpulse-se-02c-pg` @ `127.0.0.1:5438`（避开 5432 shared / 5434 N01-7-R01 / 5437 FIX-02 legacy） |

说明：

- 未触发 CIP-03 baseline drift；`main` 未在其它窗口被改写。
- 工作区 `E:\Documents\MarketPulse AI`（脏历史 worktree）本批**只读**，未做任何操作；
  本批的文档/状态读取一律从 clean worktree 进行。
- 长期运行 runtime（Integrated Runtime Host / soak）**未**启动；本批不占用真实 OKX WS。

---

## 3. Scope

允许并实际修改：

```text
backend/src/marketpulse/edge/forward.py          （新增，纯计算核心）
backend/src/marketpulse/edge/forward_service.py  （新增，durable orchestration）
backend/src/marketpulse/edge/__init__.py         （docstring 包内清单）
backend/src/marketpulse/g2/runtime.py            （最小 opted-in live-ingress hook）
backend/tests/test_se_02c_forward_outcome_calculator.py   （新增）
backend/tests/test_se_02c_forward_outcome_service.py      （新增）
dev_log/（本文件）
PROJECT_STATE.md / AI_CONTEXT.md                 （最小状态更新）
```

## 4. Out of Scope（未触碰）

SE-02D（expectancy / family aggregation / KEEP-DOWNWEIGHT-KILL）、AI 语义、G3/G4 economic
semantics、risk 规则、任何 migration / schema / ORM 变更、任何已验收契约（SE-02A/SE-02B/
FIX-01/FIX-02）的行为、真实 OKX WS、live trading、N01 runtime host、`TEST-ISO-01` /
`RRF-03` / `RRF-04`（维持独立 P2，**未**顺手修）。

---

## 5. Implementation

### 5.1 `edge/forward.py` —— 纯计算核心（无 DB / 无 Clock / 无 Settings）

冻结常量：

```text
CALCULATOR_VERSION   = "se02c-forward-outcome-v1"
COST_POLICY          = "SPOT_LONG_TAKER_ROUND_TRIP"
COST_MODEL_VERSION   = "se02c-paper-cost-v1"
FEE_RATE             = 0.001
SLIPPAGE_BPS         = 5            SLIPPAGE_FRACTION = 0.0005
END_FRESHNESS_TTL    = 5 s
FORWARD_PATH_WINDOW  = 3600 s
RUNTIME_OUTCOME_REVISION = 1
```

冻结公式（V1）：

```text
reference_mid          = (reference_bid + reference_ask) / 2
end_mid                = (end_bid + end_ask) / 2
reference_return       = end_mid / reference_mid - 1
executable_long_return = end_bid / reference_ask - 1
path_return(i)         = mid(i) / reference_mid - 1
MFE                    = max(0, path_returns)      （参考点 0.0 计入）
MAE                    = min(0, path_returns)
entry_exec             = reference_ask * (1 + slippage)
exit_exec              = end_bid * (1 - slippage)
cost_adjusted          = (exit_exec * (1 - fee)) / (entry_exec * (1 + fee)) - 1
```

**成本为精确乘性模型，不是 `return - 2*fee - 2*slippage` 近似**（测试直接断言二者差值 > 1e-9）。

因果与确定性：

- `due_at = evidence_at + horizon.duration`（**不是** `now + horizon`）；
- 参考权威 = FIX-01 durable capture anchor 的 `reference_bbo_observation_id`
  （永不使用"评估时最新报价"）；
- endpoint = 在 `available_at <= due_at` 的合格观测中按总序
  `(available_at, has_source_sequence, source_sequence, observation_id)` 取最大；
- endpoint 与 `due_at` 距离 > 5 s ⇒ `ENDPOINT_STALE`；
- `created_at` 冻结为 `due_at`（重试/重启得到同一 `outcome_record_hash`）；
- PENDING **不落库**，仅由 opportunity + horizon + clock 派生；
- 只写终态 `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID`；不可计算的指标一律 NULL
  （绝不填 `0` / `NaN` / `Infinity`）；
- 计算分类顺序（冻结）：`INVALID`（事实自相矛盾/结构不可能）→ `INSUFFICIENT_DATA`
  （reference missing/stale、无 endpoint、endpoint 超 TTL）→ `COMPLETE`。

### 5.2 `edge/forward_service.py` —— durable orchestration

- **A. Forward BBO path capture**：`ForwardPathRecorder` 只在同一
  `instrument_id + market_type` 存在 `FORWARD_PAPER` evidence 且
  `evidence_at <= available_at <= evidence_at + 1h` 时才落库，且只经已验收的
  `record_bbo_observation()`；`available_at = received_at`（V1 因果规则），
  `created_at = received_at`（重放同一帧得到同一 identity ⇒ 幂等）。
  没有窗口 ⇒ 完全不归档；不可表示的帧（crossed / 非正）在 ingress 边界跳过并记日志。
- **B. Durable due discovery**：`discover_due_scopes(session, now, horizons, limit)` 只用
  PostgreSQL 事实：`evidence_at <= now - duration` 且 NOT EXISTS revision-1 outcome；
  `due_at <= now` 与 `evidence_at <= now - duration` 严格等价。
- **C. Bounded evaluation**：`ForwardOutcomeService` / `evaluate_due_outcomes(session_factory, now)`；
  一次调用处理 `<= max_scopes`（默认 500）个 scope，**无循环、无 sleep、无 timer、无 cache**；
  每个 scope：解析 reference → 加载窗口内观测（`evidence_at <= available_at <= due_at`，
  上限 50 000，超限置 `path_truncated`）→ 调纯计算器 → `append_forward_outcome` 追加。
- 并发：两个评估者同时追加同一 scope 时，已验收 writer 折叠 `IDEMPOTENT`；
  真正竞争的两个 `INSERT` 由 PostgreSQL 唯一约束
  `uq_edge_outcome_evidence_horizon_revision` 保证**恰一行**，落败方在
  `_reconcile()` 中回读并返回等价记录，而不是抛裸 `IntegrityError`。
- 永不写 revision > 1。

### 5.3 `g2/runtime.py` —— 最小 live-ingress hook

新增 `ScannerPipeline.__init__(forward_path_recorder=None)` 与
`async def record_forward_path(market_event)`；仅当 recorder 已注入且帧是
`NormalizedBookTicker` 时才调用。**未注入时 ingest 路径逐字节不变**，
historical replay pipeline 自然无法归档 Forward BBO path。
**未新增第二个 OKX WS、未新增第二条行情管线。**

---

## 6. Files Changed

| 文件 | 类型 | 行数 | 说明 |
|---|---|---|---|
| `backend/src/marketpulse/edge/forward.py` | 新增 | 557 | 纯计算核心 |
| `backend/src/marketpulse/edge/forward_service.py` | 新增 | 619 | path recorder / due discovery / bounded evaluation |
| `backend/src/marketpulse/edge/__init__.py` | 修改 | +5/-3 | 包内模块清单 |
| `backend/src/marketpulse/g2/runtime.py` | 修改 | +20/-0 | opted-in ingress hook |
| `backend/tests/test_se_02c_forward_outcome_calculator.py` | 新增 | 864 | 37 项纯核心测试 |
| `backend/tests/test_se_02c_forward_outcome_service.py` | 新增 | 1157 | 9 项真实 PG 集成测试 |

**未新增 migration**；`backend/alembic/versions/` 零改动。

---

## 7. Verification

### 7.1 静态与仓库门

| 门 | 命令 | 结果 |
|---|---|---|
| Lint | `py -3.14 -m ruff check backend/src backend/tests scripts` | `All checks passed!`（RC=0） |
| 语法 | `py -3.14 -m compileall -q backend/src backend/tests` | RC=0 |
| Whitespace | `git diff --check` | 干净 |
| Migration | `py -3.14 -m alembic heads`（cwd=`backend/`） | `20260913_0009 (head)` — **单 head** |

### 7.2 测试（真实可弃 PostgreSQL）

隔离库 `marketpulse-se-02c-pg` @ `127.0.0.1:5438`，已迁到 head `20260913_0009`；
每次测试自建 + 自删 disposable database（`CREATE DATABASE` → `alembic upgrade head` →
跑 → `pg_terminate_backend` + `DROP DATABASE`），**不触碰任何已验收数据库**。

| 范围 | 结果 |
|---|---|
| SE-02C focused（`test_se_02c_forward_outcome_calculator.py` + `..._service.py`） | **46 passed**（37 纯核心 + 9 集成） |
| 命名回归（SE-02A contracts/persistence、SE-02B capture/attribution、G5-1/2/3/4） | **196 passed** |
| 全量 `pytest backend/tests` | **417 passed**，1 warning（`StarletteDeprecationWarning`），470.49 s |

baseline 对照：SE-ARCH-FIX-02 收编时全量为 371 passed；371 + 46 = **417**，
即**新增 46 项、既有 0 项回归/失败**。

### 7.3 环境发现（写入本文件以免下一窗口重踩）

- 🚩 **测试脚本不得导出 `DATABASE_URL`。** `backend/alembic/env.py` 读
  `os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))` —— **环境变量优先于
  测试传入的 `sqlalchemy.url`**。首次运行集成测试时导出了 `DATABASE_URL`，导致
  `command.upgrade(config, disposable_url)` 实际迁移了**环境变量指向的库**，disposable 库
  保持空表（症状：`asyncpg.exceptions.UndefinedTableError: relation
  "edge_opportunity_evidence" does not exist`，9/9 全红）。去掉环境变量后即恢复正常
  （`Settings().database_url` 从 worktree 根 `.env` 读 5438）。
  ⇒ 集成测试一律：**设 `PYTHONPATH=backend/src`、不设 `DATABASE_URL`**。

---

## 8. Acceptance Matrix（自检）

⚠️ **编号说明（诚实声明）**：任务书要求的 `C-01 … C-29` 逐条清单属**外部任务书内容**，
本仓库与本地记忆中**均无副本**（`conversation_search` 亦不可用，返回 HTTP 400）。
因此下表**不伪造 C-xx 编号**，改为按任务书章节号（§nn）索引逐条给出**实际证据**。
若需 `C-xx` 编号对齐，请提供任务书原文，本窗口可补一张对照表。

| # | 任务书条款 | 判定 | 证据 |
|---|---|---|---|
| 1 | 无新增 migration / 无 schema 变更；head 保持单 `20260913_0009` | PASS | `alembic heads` = `20260913_0009 (head)`；`alembic/versions/` 零改动 |
| 2 | 复用已验收契约与 writer，无第二条 BBO 档案/identity | PASS | `forward_service.py` 仅调 `record_bbo_observation` / `append_forward_outcome`；§56 测试断言两 opportunity 共享 1 行（`rows_after_shared_capture == 2`，含 anchor BBO） |
| 3 | §15-§19 Forward BBO path 只在 FORWARD_PAPER 窗口内归档 | PASS | 无 evidence ⇒ `None` + 0 行；`+3601 s` ⇒ `None`；`HISTORICAL_REPLAY` evidence 不构成窗口（`recorded is None`、0 行） |
| 4 | §16/§19 ingress 不可表示帧不得崩溃 | PASS | crossed book ⇒ `None`、无异常、无新行 |
| 5 | §10/§39-§40 `due_at = evidence_at + duration`，discovery 纯函数 | PASS | `now = START+29 s` ⇒ `[]`；`now = START+30 s` ⇒ `["30s"]`；`planned_due_at == [forward_due_at(START, h) for h in ALL]` |
| 6 | §41-§42 四 horizon 各自独立 scope/due_at/outcome | PASS | 一次 pass ⇒ 4 行、4 个不同 `outcome_id`、4 个不同 `due_at` |
| 7 | §23 参考权威 = FIX-01 anchor BBO，绝不取"最新报价" | PASS | `reference_bbo_observation_id == anchor.reference_bbo_observation_id`；`reference_price == (anchor.bid+anchor.ask)/2 == 100.0` |
| 8 | §20/§21/§22 endpoint 取合格观测最大，总序 tie-break | PASS | `+29/+299/+899/+3599 s` 分别为 30s/5m/15m/1h 的 endpoint；纯核心另有 3 组 tie-break 用例 |
| 9 | §24 5 s endpoint freshness TTL | PASS | 4/4 COMPLETE 的 `end_age_seconds <= 5.0`；纯核心另有 `ENDPOINT_STALE` 用例 |
| 10 | §22/§48 `available_at > due_at` 是未来数据，不得参与 | PASS | 库里 6 条观测（含 `+0 anchor`），30s horizon 窗口只加载 3 条、5m 加载 4 条、15m 5 条、1h 6 条；endpoint 全部 `<= due_at` |
| 11 | §29/§53 冻结 V1 公式（含 MFE/MAE 与 mid 基准） | PASS | 5m 实测：`mfe == 0.04`、`mae == 0.0`、`reference_return == 104/100-1`、`executable_long_return == 103/100.5-1`、`reference_price == 100.0`；纯核心另有 §53 公式向量 |
| 12 | §32-§36 成本策略精确乘性，不可用近似 | PASS | `cost_adjusted == ((103*0.9995)*0.999)/((100.5*1.0005)*1.001)-1`；且与 `r-2f-2s` 近似差值 > 1e-9 |
| 13 | §35 成本策略/版本标识冻结 | PASS | `cost_policy == SPOT_LONG_TAKER_ROUND_TRIP`、`cost_model_version == se02c-paper-cost-v1`、`calculator_version == se02c-forward-outcome-v1` |
| 14 | §44 due_at 之后的报价不影响已到期 horizon | PASS | 见 #10；discovery 不受新观测影响 |
| 15 | §45 只有 COMPLETE / INSUFFICIENT_DATA / INVALID 落库；PENDING 不落库 | PASS | 同库出现三类状态；`pending_rows == 0`；`INSUFFICIENT_DATA` 的 6 个指标全 NULL |
| 16 | §41 INVALID 才丢失绑定（结构矛盾） | PASS | 有 evidence、无 anchor 的 FORWARD_PAPER scope ⇒ `INVALID` / `INVALID_FORWARD_ANCHOR_MISSING`，`reference_*` / `end_*` / `mfe` 全 NULL |
| 17 | §28/§30 `created_at` 冻结为 `due_at` | PASS | 4/4 `row.created_at == row.due_at` |
| 18 | §46/§20 重试幂等，绝不自动产生 revision 2 | PASS | 重跑 `evaluate_scope` 返回同一 `outcome_id`；`outcome_record_hash` 不变；事后补一条 late frame，`discover_due_scopes` 仍返回 `[]`，行数仍 4、revision 全 1 |
| 19 | §46 同 scope 同 revision 内容不同 ⇒ fail closed | PASS | 事实变化后强制再评估 ⇒ `EdgeOutcomeConflict`（**不**写 revision 2），行数仍 4 |
| 20 | §57 重启后无继承记忆仍发现同一批工作 | PASS | 第一条 engine 跑完并 dispose；新 engine `discover_due_scopes(now)` ⇒ `[]`，`evaluate_due_outcomes` 第二遍 ⇒ 0 条，总行数仍 4 |
| 21 | §57 更晚的 clock 不产生新工作 | PASS | `discover_due_scopes(now + 4 h)` ⇒ `[]` |
| 22 | §58 并发恰一条 outcome | PASS | 两个独立 engine 并发 `evaluate_scope` 同一 scope ⇒ 1 行、`distinct_returned_outcome_ids == 1`、`distinct_returned_hashes == 1`、两 caller 都持有该持久行；第二轮并发后仍 1 行 |
| 23 | §50/§51 provenance 继承 + replay/forward digest 分离 | PASS | `source_type` / `source_identity` 继承自 evidence；纯核心断言同一市场事实的 HISTORICAL_REPLAY 与 FORWARD_PAPER 共享 `calculation_digest`、`outcome_record_hash` 不同 |
| 24 | §17/§19 未新增 resident loop / scheduler / 第二个市场数据管线 | PASS | `forward_service.py` 无 `sleep` / `while` / scheduler；`g2/runtime.py` 仅新增 opt-in hook，无新 WS |
| 25 | §65-§66 focused + full backend 回归 | PASS | 46 / 196 / 417 passed；既有 0 回归 |
| 26 | 不扩大 Scope、不改已验收契约、不动 migration | PASS | diff 仅 6 文件（2 新增生产文件 + 2 新增测试 + 2 最小修改） |

---

## 9. Self-Check（Reviewer 应重点挑战处）

1. **`INSUFFICIENT_DATA` 仍绑定 reference。** 当 reference 已 `OK` 但 horizon 无可用 endpoint 时，
   `reference_bbo_observation_id` 会绑定（它是被**接受**的参考），只有 `end_*` 与全部指标为 NULL。
   这是刻意语义：reference 是可审计的已接受事实，horizon 只是不可计算。
2. **"窗口内只有 anchor BBO 自身"时的 reason 是 `ENDPOINT_STALE` 而非 `ENDPOINT_MISSING`。**
   冻结 eligibility 规则（identity → FRESH → tradable → `available_at <= due_at`）未对
   `available_at <= evidence_at` 另设下界，因此 anchor 观测本身是合格候选，其龄 = horizon 长度
   > 5 s ⇒ `ENDPOINT_STALE`。**状态与指标契约不受影响**（仍是 `INSUFFICIENT_DATA` + 全 NULL +
   不绑定 end）。集成测试以"窗口是否为空"显式推导期望 reason，不硬编码猜测。
   → 若 Independent Review 认为 endpoint 只能在 `available_at > evidence_at` 的 forward path 上
   选取，这是**一处语义收紧**（行为保持：任何情况都不会改变 COMPLETE 判定），需另开窗口处理。
3. **事实变化后的重评估抛 `EdgeOutcomeConflict` 而非静默返回旧行。** 生产路径由
   `discover_due_scopes` 排除已结算 scope，正常不会走到；但"late frame 在结算后落库"这类
   极端竞争会让强制重评估失败关闭。选择 fail closed 而不是静默忽略内容差异。
   → 若 Reviewer 期望"已结算 scope 直接回读、不重算"，需要改 `evaluate_scope` 的顺序，
   属行为变更，本批**未**自行决定。
4. **`ForwardPathRecorder` 对每个 BBO 帧做一次窗口查询。** 有 recorder 且窗口打开时，
   ingest 路径会多一次 DB 读 + 一次可能的写。本批未做 batch/缓存（避免引入未要求的状态）。
   → 若 N01-8 Integrated Runtime Host 认为这影响 ingest 时延，需单独评估（属 N01-8 scope）。
5. **`record_forward_path` 在 trade-dedupe 早退之后调用。** 重复 trade 帧不会触发归档；
   BBO 帧不走 trade dedupe，因此不受影响。已由全量回归背书的 G2 行为未改变。
6. **未对 `FORWARD_PAPER` 之外 source_type 做 path 归档**（`has_relevant_forward_window`
   只匹配 `FORWARD_PAPER`），已由 `test_forward_window_ignores_historical_replay_evidence` 固定。

---

## 10. Result

```text
SE-02C = IMPLEMENTED / READY FOR INDEPENDENT REVIEW
```

- Branch `se-02c-forward-outcome-calculator` @ `721c488`（+ docs-only commit）
- **未** merge `main`；**未** push `main`；**未**自行 Acceptance
- 未新增 migration；未触碰任何已验收契约语义
- 全量 417 passed（新增 46、回归 0）

## 11. Remaining / Blockers

- Independent Review（独立窗口，按 CIP-07/CIP-08 不得采信本文件的自述结论）。
- Human Acceptance（本窗口不签发）。
- 若需 `C-01 … C-29` 编号对照：**需提供任务书原文**（见 §8 声明）。
- 已暴露但**未**自行决定的两个语义点：§9-2（endpoint 下界）、§9-3（已结算 scope 是否重算）。
- SE-02D / N01-8 / Integrated Runtime Host 仍 `NOT STARTED`。

## 12. Known Risks / Notes

- 隔离容器 `marketpulse-se-02c-pg` @ 5438 在验证期间运行；worktree 根与 `backend/` 下有
  gitignored `.env`（只覆盖 `DATABASE_URL`，未写 `ADMIN_PASSWORD`，故 `test_auth` 不受影响）。
  **关闭本 batch 时需按授权清理**（容器 + 匿名卷 + 两个 `.env`），本窗口未清理。
- 未提交的 `.env` 不会被 push（已确认不在 `git status` 中）。
- `git commit` 时的 `LF will be replaced by CRLF` 提示是本机 `core.autocrlf` 行为；
  index blob 仍为 LF-only，与仓库既有文件一致（已实测 `capture.py` CRLF=0）。

## 13. Context For Next AI

- 本批**新增**的公开入口：`marketpulse.edge.forward`（纯核心）、
  `marketpulse.edge.forward_service`（`ForwardPathRecorder` / `discover_due_scopes` /
  `ForwardOutcomeService` / `evaluate_due_outcomes`）、
  `ScannerPipeline(forward_path_recorder=...)` + `ScannerPipeline.record_forward_path()`。
- 跑本批测试：`cd <worktree> && PYTHONPATH=backend/src py -3.14 -m pytest backend/tests`，
  **不要**设 `DATABASE_URL`（见 §7.3）。
- 上游契约位置：`edge/models.py`（`ForwardOutcomeContract` / `build_forward_outcome_contract`）、
  `edge/repository.py`（`record_bbo_observation` / `append_forward_outcome`）、
  `edge/capture.py`（FIX-01 anchor）、`db/models.py`（`uq_edge_outcome_evidence_horizon_revision`）。

## 14. Evidence

| 证据 | 路径 / 命令 |
|---|---|
| focused 测试输出 | `py -3.14 -m pytest backend/tests/test_se_02c_forward_outcome_calculator.py backend/tests/test_se_02c_forward_outcome_service.py -q` → `46 passed` |
| 命名回归输出 | SE-02A/SE-02B/G5-1..4 → `196 passed in 270.78s` |
| 全量回归输出 | `py -3.14 -m pytest backend/tests -q` → `417 passed, 1 warning in 470.49s` |
| Lint | `py -3.14 -m ruff check backend/src backend/tests scripts` → `All checks passed!` |
| Migration head | `cd backend && py -3.14 -m alembic heads` → `20260913_0009 (head)` |
| Whitespace | `git diff --check` → 无输出 |
| 分支/提交 | `git rev-parse HEAD` → `721c488`（工作树 `E:\Documents\MarketPulse-AI-se-02c`） |
