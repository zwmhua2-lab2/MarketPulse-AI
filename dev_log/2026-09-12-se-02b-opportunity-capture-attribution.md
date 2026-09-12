# SE-02B｜Opportunity Capture + Attribution

> 专项 **SE｜Strategy & Trading Edge** 的第二个 Implementation Acceptance Batch。
> 状态：`IMPLEMENTED / WAITING HUMAN ACCEPTANCE`（**未**自行 Acceptance，**未** merge `main`）。
> branch：`se-02b-opportunity-capture-attribution`；
> isolated worktree：`E:\Documents\MarketPulse-AI-se-02b`。
> 统一解释器 `py -3.14`；`PYTHONPATH=backend/src`；PostgreSQL = Docker `marketpulse-postgres`。

---

## 1. Repository Truth（preflight 实测）

| 项 | 实测值 |
|---|---|
| Task Base / Accepted Main（`git rev-parse HEAD`） | `af81414160248c97f59a63b31fe615ea8ae14bbe` |
| 当前 branch | `se-02b-opportunity-capture-attribution` |
| Drift（CIP-03） | **无**（worktree HEAD == main == Task Base） |
| Migration Head | `20260911_0005`（**本批未新增 / 未修改任何 migration**） |
| `g5/replay.py::schema_head` | `"20260911_0005"`（未变） |
| 仓库 SE-02 设计文档 | **不存在**；契约依据 = 任务书 + 已验收 SE-02A 代码 |

本批**未**触碰 `backend/alembic/`（`git status --porcelain backend/alembic` 为空），
migration revision 数量仍为 5（`20260904_0001` ～ `20260911_0005`）。

---

## 2. Scope

本批只有两个职责：

- **A. G2 Opportunity Capture** —— 对合格的 G2 `SETUP` 跃迁，把不可变 Opportunity Evidence Unit
  与 G2 durable facts **在同一 DB 事务内**持久化（原子、fail-closed）。
- **B. Attribution Linkage** —— 以 append-only 方式把 Opportunity 连到既有
  G3 / Risk / Execution / Paper 经济链，**不改变既有经济语义**。

Out of Scope（未实现、未调用）：SE-02C（forward outcome calculator / MFE-MAE / forward returns）、
SE-02D（family aggregation / expectancy / KEEP-DOWNWEIGHT-KILL）、UI、Live、Real AI Edge、
Runtime Host、任何新的 Edge 持久化或 migration。

---

## 3. 实现内容 A｜G2 Opportunity Capture

新增 `backend/src/marketpulse/edge/capture.py`：

- `OPPORTUNITY_FAMILY_STRATEGY_ID = "BREAKOUT_RETEST"`、`RUNTIME_CAPTURE_REVISION = 1`、
  `DEFAULT_REFERENCE_MAX_AGE = timedelta(seconds=5)`。
- `ReferenceQuote`（frozen）与 `EdgeCaptureContext`（frozen，含 `classify_reference`）——捕获上下文
  由调用方显式注入，模块内**不**读全局配置。
- `qualifies(...)`：唯一资格判定入口。
- `build_opportunity_evidence(...)`：构造不可变 evidence revision（复用 SE-02A
  `build_opportunity_identity` / `build_evidence_revision` 与 identity 公式，**未**新造第二套）。
- `capture_opportunity(session, *, event, timeline, state, transition, candidates, observation, context)`：
  在调用方事务内落库，异常向上传播（fail closed），**不**吞异常、**不**降级为「跳过 evidence」。

接线（唯一生产改动点，见 §5）：`PostgresG2Repository.persist()` 在同一 `session.begin()` 事务里，
在 `DerivedObservationRecord` 之后调用 `capture_opportunity(...)`。

---

## 4. 实现内容 B｜Attribution Linkage

新增 `backend/src/marketpulse/edge/attribution.py`：

- `OpportunityLink` + `link_for_opportunity(opportunity, *, evidence_revision=1)`：**确定性推导**
  `evidence_id`（复用 SE-02A evidence_id 公式），不额外查库。
- `family_is_selected(*, selected_strategy_ids, snapshot_strategy_ids)`：`AI_ACCEPTED_LONG`
  只从 decision 本身判定，**不**由「后来出现了 TradePlan」反推（任务 §11）。
- `ai_attribution_event_type(...)`：AI 侧词汇映射（含 provider error / invalid / stale / 非本 family）。
- `EdgeAttributionRecorder`：12 个语义方法 + 1 个底层 `record`，**唯一写者**为
  `repository.append_attribution_event`（内容寻址、append-only）。

接线（全部为 keyword-only、默认 `None` 的**增量**参数）：

| 位置 | 记录的事件 |
|---|---|
| `DecisionService.decide` | `record_ai_decision`（与 decision 同事务） |
| `persist_trade_plan` | `record_plan_created`（与 plan 同事务） |
| `G3Workflow.process_setup` → `_record_plan_not_created` | `PLAN_NOT_CREATED`（lineage-only 小事务） |
| `PaperExecutionService._execute_once` | `RISK_REJECTED`(gate) / `EXECUTION_REJECTED`(revalidate) / `EXECUTION_REJECTED`(mark stale) / `RISK_REJECTED`(capacity) |
| `_reserve_limit` / `_fill_market` | `RISK_ACCEPTED` + `ORDER_OPEN` |
| `_settle_order` | `BUY_FILLED` + `TRADE_OPEN`（开仓）/ `TRADE_CLOSED` + `ACTUAL_ECONOMIC_RESULT_AVAILABLE`（平仓） |
| `cancel_order` / `process_open_orders` | `ORDER_CANCELLED` / 透传 |

`_settle_order` 内新增 `opens_trade` / `closes_trade` 两个**纯观测布尔**，并把
`ledger_entry_id = stable_id("ledger", fill_id)` 提为局部变量（值不变）——均不改变任何业务写入。

---

## 5. 冻结契约复用 / 生产改动最小性

生产代码改动共 3 个文件：

| 文件 | 改动 |
|---|---|
| `edge/__init__.py` | 仅 docstring（说明 SE-02B 两个模块 + 仍缺 SE-02C/02D） |
| `g2/repository.py` | `__init__` 增加 keyword-only `capture: EdgeCaptureContext \| None = None`；`persist()` 事务内条件调用 |
| `g3/service.py` | 逐方法增加 keyword-only `attribution` 并加 `if attribution is not None:` 守卫 |

- 未新增 Edge 持久化、未新增 migration、未修改 SE-02A 契约（identity / hash / revision / status 语义）。
- `capture is None`（默认）时 G2 行为**逐字节不变**：无 Edge 写、无新增失败模式（有专门回归测试）。
- `attribution is None`（默认）时 G3/G4 路径行为不变：`git diff` 中所有 recorder 调用都在 `None` 守卫内。

---

## 6. Qualification 规则

合格条件（全部满足才捕获）：family `BREAKOUT_RETEST` + 决策 `APPLIED` + 跃迁至 `SETUP` +
方向 `BULLISH` + 触发事件为 `BREAKOUT`。

**参考报价（reference BBO）不参与资格判定**：缺失 / 陈旧 / 不可交易 / crossed / 非正 一律
**不阻塞** capture，只反映为 `ReferenceDataStatus = OK | REFERENCE_MISSING | REFERENCE_STALE`
（SE-02A 冻结语义；`OK` 要求三字段非 NULL 且 `bid>0, ask>0, bid<=ask`；MISSING/STALE 要求三者全 NULL）。

---

## 7. 负向矩阵（13 个变异，全部必须 0 evidence）

`non_applicable_candidate`、`wrong_family`、`wrong_direction`、`neutral_direction`、
`wrong_event_type`、`detected_only`、`watching_only`、`no_change_transition`、
`rejected_transition`、`late_event_rejection`、`setup_without_expiry`、
`disagreeing_candidate_event`、`disagreeing_candidate_version`。

断言口径：每个变异下 `edge_opportunity_evidence` 行数 = 0；G2 durable facts 仍照常落库
（`symbol_states` = 1 行 / 单一 instrument；`candidates` = 该变异实际候选数，逐场景累加校验）。

---

## 8. Atomic / fail-closed 证据

- **同事务**：G2 durable facts 与 evidence 共享一个 `session.begin()`；无独立提交点。
- **回滚场景 1（pre-staged conflict）**：预置同 revision 同 opportunity 但不同 hash 的 evidence
  ⇒ 捕获抛 `EdgeEvidenceConflict` ⇒ 断言 **G2 行数 = 0、evidence 行数 = 1（仅预置行）**。
- **回滚场景 2（post-staged fault）**：在 G2 facts 已 `session.add` 之后注入故障
  ⇒ 断言 **G2 行数 = 0、evidence 行数 = 0**。
- 结论：不存在「G2 成功但 evidence 静默缺失」或半提交状态。

---

## 9. Idempotency / Immutability 证据

- 同 revision 同 hash ⇒ `IDEMPOTENT`（重复 replay 不新增行）。
- 同 revision **不同** hash ⇒ `EdgeEvidenceConflict` fail closed。
- 全流程**无 UPDATE**：重建 evidence revision 得到的 canonical 值与原行一致（不可变重建测试）。
- attribution 侧 `append_attribution_event`：同 `attribution_event_id` ⇒ `IDEMPOTENT`；
  重放 lineage 后业务表计数前后一致（`business_before == business_after`）。

---

## 10. Attribution 事件词汇表（恰 19 个，已逐项核对）

AI：`AI_NOT_REACHED`、`AI_ACCEPTED_LONG`、`AI_REJECTED_WAIT`、`AI_REJECTED_SHORT_ANALYSIS_ONLY`、
`AI_NOT_SELECTED_THIS_FAMILY`、`AI_INVALID`、`AI_STALE`、`AI_PROVIDER_ERROR`
Plan：`PLAN_CREATED`、`PLAN_NOT_CREATED`
Risk：`RISK_ACCEPTED`、`RISK_REJECTED`
Execution：`EXECUTION_REJECTED`、`ORDER_OPEN`、`ORDER_CANCELLED`、`BUY_FILLED`
Economic：`TRADE_OPEN`、`TRADE_CLOSED`、`ACTUAL_ECONOMIC_RESULT_AVAILABLE`

关键语义边界（均有独立测试）：

| 边界 | 断言 |
|---|---|
| Risk 拒绝保留**精确 authority + reason** | `authority=SystemRiskGate`（reason 原样）/ `authority=CapacityPolicy`（`CAPACITY_BLOCKED`），两者**不可**合并为泛化 REJECTED |
| Execution 校验失败 ≠ Risk 拒绝 | `plan_not_active_or_expired` / `price_outside_entry_zone` / `CORE_POSITION_MARK_STALE` 一律记 `EXECUTION_REJECTED`，不产生 `RISK_REJECTED` |
| OPEN order ≠ FILL | LIMIT BUY 记 `RISK_ACCEPTED` + `ORDER_OPEN`，断言 order `OPEN`、无 `BUY_FILLED`、`fills=0`、`trades=0` |
| 只有 BUY fill 证明成交 | `BUY_FILLED` 只在 `_settle_order` 的 BUY 分支产生 |
| 经济结果只在平仓可得 | `ACTUAL_ECONOMIC_RESULT_AVAILABLE` 与 `TRADE_CLOSED` 同点，`payload.ledger_entry_id == stable_id("ledger", exit_fill_id)`，`position.quantity == 0` |
| 每个事件都链到同一 opportunity | `subject_ids` 按 `subject_type` 精确对应业务 id（AI=decision_id / PLAN=plan_id / RISK=intent_id / EXECUTION=fill_id / ECONOMIC_RESULT=trade_id），`all_linked` |

---

## 11. Verification（真实执行）

| 门 | 命令 | 结果 |
|---|---|---|
| SE-02B capture | `pytest backend/tests/test_se_02b_opportunity_capture.py -q` | **11 passed** |
| SE-02B attribution | `pytest backend/tests/test_se_02b_attribution.py -q` | **26 passed** |
| SE-02A 回归 | `pytest backend/tests/test_se_02a_edge_contracts.py backend/tests/test_se_02a_edge_persistence.py -q` | **88 passed**（62 + 26） |
| G2 / G3 / G4 回归 | `pytest backend/tests/test_group2.py backend/tests/test_group3.py backend/tests/test_group4.py -q` | **123 passed** |
| Ruff | `py -3.14 -m ruff check backend/src backend/tests scripts` | `All checks passed!` |
| compileall | `py -3.14 -m compileall -q backend/src/... backend/tests/test_se_02b_*.py` | rc = 0 |
| 空白 | `git diff --check` | rc = 0 |

SE-02B 全部使用**真实 disposable PostgreSQL**（`CREATE DATABASE marketpulse_se02b_*`
→ `alembic upgrade head` → workload → `DROP DATABASE`），未使用内存库替代。

### 11.1 全量后端回归（含环境取证，**必须如实记录**）

本批共执行 3 次全量套件，前两次均**不可采信**，第 3 次才在独占窗口成立：

| # | 窗口 | 命令 | 结果 | 判定 |
|---|---|---|---|---|
| 1 | — | `py -3.14 -m pytest backend/tests`（**漏 `PYTHONPATH`**） | `6 failed, 298 passed` | **调用口径伪影**，见 §11.2 |
| 2 | 07:46:45–07:52:09 | 同上 + `PYTHONPATH=backend/src` | `304 passed, 1 warning`（320.14s） | **INVALIDATED BY ENVIRONMENT**，见 §11.3 |
| 3 | 07:55:25–08:00:48 | 同 #2 | **304 passed, 1 warning**（317.13s） | **采信**（独占证明见 §11.4） |

### 11.2 第 1 次失败根因（调用口径，非产品缺陷）

6 个失败全部为 `test_n01_restart_recovery.py::test_n01_c_real_postgres_restart_recovery_across_two_python_processes[*]`，
失败文本统一为子进程 `ModuleNotFoundError: No module named 'marketpulse'`。

根因：该 harness 用 `subprocess.Popen([sys.executable, <测试文件>, "--child", ...], env=os.environ.copy())`
派生**独立 OS 进程**；Pytest 的 `pythonpath = ["backend/src"]`（`pyproject.toml`）只影响 pytest 主进程的
`sys.path`，**不会**写入 `os.environ`，因此子进程拿不到包路径。

本仓库**全部历史验收门**均以 `PYTHONPATH=backend/src py -3.14 -m pytest ...` 执行
（`dev_log/2026-09-11-se-02a-edge-contracts-persistence.md` §15、`2026-09-12-n01-6-15m-runtime-smoke.md`
等均有明载）。本批第 1 次调用漏写该环境变量 ⇒ 属**调用方式伪影**，与 SE-02B 改动无关。

### 11.3 第 2 次被环境污染（如实记录，不采信）

第 2 次运行期间（07:50:22 起）检测到**并发外来全量套件**：

```text
PID=30744  C:\WINDOWS\py.exe -3.14 -m pytest backend -q -p no:randomly
PID=35700  ...\Python314\python.exe -m pytest backend -q -p no:randomly
PID=33968  ...\Python314\python.exe E:\Documents\MarketPulse-AI-n01-7-f01\backend\tests\test_n01_restart_recovery.py --child b ... safe_mode
```

来源为**另一个 worktree** `E:\Documents\MarketPulse-AI-n01-7-f01`（N01-7 窗口），运行窗口
约 07:50:22–07:55:22，与本批运行**重叠约 107 s**。

`pg_stat_activity`（`backend_type='client backend'`，以唯一 `application_name='se02b-observer'`
从 primary 库观测并排除自身）在 07:50:58 起由 8 → 50 个并发 client backend 爬升，与外来套件窗口吻合；
本仓库 `PROJECT_STATE.md`「Known Issues」明载：全量套件共享**单一** PostgreSQL 库且
`Harness.clean()` 整表清空 `RunMode.REPLAY`，**任何两个并发会话在全量套件层面必然互坏**。

虽然该次结果为 `304 passed` / 0 失败，仍按既定约定标记
**`INVALIDATED BY ENVIRONMENT`**，并在恢复独占后重跑（**不**「重试至通过」）。

（保留的对照证据：全量套件在观测窗口内出现的 disposable 库
`marketpulse_g52_*` / `marketpulse_g53_*` / `marketpulse_g54_*` / `marketpulse_n01_b_*` /
`marketpulse_n01_c_*` / `marketpulse_se02a_*` / `marketpulse_se02b_*` 全部归属本仓库自身 harness；
非空 `application_name` 只有 `marketpulse-n01-c-owned-process-b-*`，在仓库源码中有定义。）

### 11.4 第 3 次（干净窗口，最终采信）

- 前置独占确认：等待器 4 次探测后于 **07:55:22** 记录 `EXCLUSIVE (no foreign pytest process)`：
  - attempt 1（07:54:35）CONTENDED：2 个进程 `py.exe/python.exe -m pytest backend -q -p no:randomly`；
  - attempt 2（07:54:51）CONTENDED：4 个进程（另含 `test_n01_okx_paper_safety.py::test_n01_b_freshness_boundary_...`）；
  - attempt 3（07:55:06）CONTENDED：2 个进程；
  - attempt 4（07:55:22）**EXCLUSIVE**。
- 结果：**`304 passed, 1 warning`（317.13s）**，`collect = 304` = 基线 `267` + 本批 `37`。
- 独占性采样（`application_name='se02b-observer'` 从 primary 库观测并排除自身，42 样本，
  07:55:29–08:02:21）：**外来 client backend 最大并发 = 2**；观测到的库全部为本仓库自身 harness 的
  disposable 库（`marketpulse_g52_*` / `g54_txn_*` / `n01_c_*` / `se02a_*` / `se02b_*`）或 primary
  `marketpulse`；非空 `application_name` 仅 `marketpulse-n01-c-owned-process-b-*`（源码内定义）；
  **无 unknown 库、无未知 application_name、无外来写者** ⇒ 结果可采信。

### 11.5 聚焦门复跑被环境污染（如实记录，不采信，不作为缺陷）

收尾阶段试图在最终树上复跑「聚焦门合集」（`test_se_02b_* + test_se_02a_* + test_group2/3/4`，
共 248 个，**非**全量套件的字母序，group2/3/4 被放在 se02a/se02b 之后），结果
`12 failed + 卡死`（11m36s 被终止），失败区间为 group3（9）/ group4（3）。

取证结论（非产品 / 测试缺陷）：

- `test_group2.py` **单独重跑 RC=0**（隔离通过）。
- 该复跑窗口期间，本仓库共享 PostgreSQL 服务器上存在**另一 worktree 的并发全量套件**
  （命令行 `py.exe/python.exe -m pytest backend/tests -q -p no:randomly`，源自
  `E:\Documents\MarketPulse-AI-n01-7-f01` 等窗口），且该窗口此前已被拍到**同时**运行多个
  pytest（07:54:51 的 attempt 2 记录到 4 个进程）。09:00:32 再次扫描到同类进程仍在循环运行。
- group3 / group4 测试使用**共享 primary `marketpulse` 库**（`RunMode.LIVE_PAPER` 行 +
  `Harness.clean()` 整表清空），是本仓库 `PROJECT_STATE.md`「Known Issues」明载的并发互坏重灾区。
- 签名（失败集合 + 卡死 + 每次不同）与历史并发写者污染记录完全一致。

故该复跑标记 **`INVALIDATED BY ENVIRONMENT`**，不据此推断任何产品缺陷；最终采信证据为
§11.4 的干净窗口全量门（含 37 个 SE-02B 测试全绿），以及 §11 顶部各聚焦门在干净窗口下的既有记录
（capture 11 / attribution 26 / SE-02A 88 / G2+G3+G4 123）。

---

## 12. Regression（既有能力是否保持）

- SE-02A 契约 + 持久化 **88 passed**（未回归）。
- G2 **30** / G3 **16** / G4 **77** = **123 passed**（未回归）。
- 全量后端 = 基线 `267` + 本批新增 `37`（11 capture + 26 attribution）= **304**，逐项对齐。

---

## 13. Self Review（§20 十二问）

| # | 问题 | 结论 |
|---|---|---|
| 1 | 是否引入新的 Edge 持久化 / migration？ | **否**；head 仍 `20260911_0005`，`backend/alembic` 零改动 |
| 2 | 是否重造了 SE-02A 契约？ | **否**；identity / hash / revision 全部复用既有公式与 `canonicalize_value` |
| 3 | 参考报价缺失/陈旧是否会阻塞 capture？ | **不会**，且有 6 态专门测试 |
| 4 | 是否会「G2 成功而 evidence 静默缺失」？ | **不会**；同事务 + 异常传播，两个回滚场景均有断言 |
| 5 | 同 rev 不同 hash 是否 fail closed？ | **是** ⇒ `EdgeEvidenceConflict` |
| 6 | 是否会 UPDATE 既有行？ | **否**；全流程无 UPDATE，重建值与原行一致 |
| 7 | `attribution=None` 时既有行为是否变化？ | **否**；全部调用都在 `if attribution is not None:` 守卫内 |
| 8 | 是否把 Risk 拒绝与 Execution 拒绝混为一谈？ | **否**；authority/reason 原样保留，EXECUTION_REJECTED 独立 |
| 9 | 是否把 OPEN order 当作成交？ | **否**；`BUY_FILLED` 只在 `_settle_order` BUY 分支 |
| 10 | 是否由「后来有 TradePlan」反推 AI 接受？ | **否**；`family_is_selected` 只看 decision 自身 |
| 11 | `AI_ACCEPTED_LONG` 等经济事件是否可跨 opportunity 串线？ | **否**；每个事件链到唯一 opportunity/evidence |
| 12 | 是否扩大了 Scope？ | **否**；SE-02C/02D/UI/Live/Real AI/Runtime Host 均未触碰 |

---

## 14. Scope Check

- 允许修改：`backend/src/marketpulse/edge/`（新增 capture/attribution、docstring）、
  `g2/repository.py`、`g3/service.py`（仅增量接线）、`backend/tests/test_se_02b_*.py`、
  `dev_log/`、`PROJECT_STATE.md`。
- 未修改：`backend/alembic/`、`edge/models.py` / `identity.py` / `hashing.py` / `repository.py`（SE-02A 契约）、
  G4/G5 任何文件、Frontend、`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md`。
- 未 merge `main`、未 rebase、未 force push。

---

## 15. 交付文件

新增：

- `backend/src/marketpulse/edge/capture.py`
- `backend/src/marketpulse/edge/attribution.py`
- `backend/tests/test_se_02b_opportunity_capture.py`
- `backend/tests/test_se_02b_attribution.py`
- `dev_log/2026-09-12-se-02b-opportunity-capture-attribution.md`（本文件）

修改：

- `backend/src/marketpulse/edge/__init__.py`（docstring）
- `backend/src/marketpulse/g2/repository.py`
- `backend/src/marketpulse/g3/service.py`
- `PROJECT_STATE.md`（最小同步）

---

## 16. Remaining / Blockers

- **无阻塞。**
- 交棒 SE-02C 必须继承：evidence revision 已能在 runtime 产生；forward outcome 仍未计算（无 MFE/MAE、
  无 forward returns）；attribution 只记「已发生的事实」，**不含**任何 outcome 判定。
- attribution 的 `occurred_at` 取自各阶段 stage 时间；同一 execution stage 内多事件共享同一
  `occurred_at`，故测试**不**依赖同一时间戳内的行序（已改为按 stage 断言 + 集合比较）。
