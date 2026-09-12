# SE-02B-FIX-02｜Reference Quote Quality & Provenance

> 专项 **SE｜Strategy & Trading Edge**，SE-02B 的专项执行窗口：关闭 SE-02B-FIX-01
> Independent Re-review 之后**仅剩的 P0-1 Reference BBO 两个 Acceptance Blocker**。
> 状态：`IMPLEMENTED / VERIFIED / READY FOR INDEPENDENT RE-REVIEW`（**未**自行 Acceptance，
> **未** merge `main`，**未**开始 SE-02C）。
> branch：`se-02b-opportunity-capture-attribution`；worktree：`E:\Documents\MarketPulse-AI-se-02b`。
> 统一解释器 `py -3.14`；`PYTHONPATH=backend/src`；PostgreSQL = Docker `marketpulse-postgres`。

---

## 1. Repository Truth（动作前实测）

| 项 | 实测值 |
|---|---|
| Reviewed HEAD（本 Fix 的 parent / Task Base） | `b8a5fe32fa38245ebd1ae9e30c31fe5654a7c05b` |
| Fix commit | `0b8a275050d11ba31b2df15823759750a049d1f1` |
| Diff Range（reviewed → fix） | `b8a5fe3..0b8a275` |
| branch（remote 实测） | `se-02b-opportunity-capture-attribution` |
| Remote main（实测 `git ls-remote`） | `af81414160248c97f59a63b31fe615ea8ae14bbe`（**未动**） |
| Migration Head | `20260911_0005`（单 head；**本 Fix 未新增 / 未修改任何 migration**） |
| worktree 状态 | 动作前 clean；动作后仅 2 个已声明文件被修改后提交 |
| Drift（CIP-03） | **无**：worktree HEAD == reviewed `b8a5fe3`，remote branch tip == `b8a5fe3`，remote main == `af81414` |

`af81414`（Accepted Main）→ `f261766`（SE-02B）→ `7e86757`（FIX-01 fix）→ `b8a5fe3`（FIX-01 docs）
→ `0b8a275`（本 Fix）为纯 fast-forward 链；**未** amend / 未 rebase / 未 force push / 未 merge `main`。

**外部窗口观察（非本 Fix 所致，如实记录）**：全量门执行前进程扫描发现**另一个窗口**正在跑
`python.exe -m pytest backend/tests -q`（PID 32596，13:44:48 启动）。因共享单一 PostgreSQL 实例
（`marketpulse`）且各套件会在同一库上 `clean()` 整表清空，本 Fix **等待其退出**（13:51:20）后才开始
全量门，并在门内以每 5 s 采样监控并发写者（§7）。等待期间不做任何 reset / rebase / 覆盖动作。

---

## 2. Scope

| 项 | 内容 |
|---|---|
| Task | 只关闭 P0-1 Reference BBO 的两个 Acceptance Blocker（Finding A / Finding B） |
| 允许修改 | `backend/src/marketpulse/edge/capture.py`、`backend/tests/test_se_02b_opportunity_capture.py`、`dev_log/`、`PROJECT_STATE.md` |
| Out of Scope（未触碰） | SE-02C / SE-02D、Forward Outcome Calculator、MFE/MAE、quote-path capture、30s/5m/15m/1h calculation、family aggregation、expectancy、KEEP/DOWNWEIGHT/KILL、Real AI、Live、OKX real orders、UI、新 Opportunity Family、architecture refactor、`backend/alembic/`、`edge/{models,identity,hashing,repository}.py`（SE-02A 冻结契约）、`g2/repository.py`、`g3/service.py`、`edge/attribution.py`、G4/G5、Frontend、`DECISIONS.md`、`PRODUCT_REQUIREMENTS.md` |

**未接管 market data subsystem**：无新组件、新表、新 migration；quote 仍由调用方持有并经
`PostgresG2Repository(reference_quote_for=...)` 有界访问器按 persist 注入。
**未做任何顺手重构 / 优化**；每行 diff 均可由 Finding A / Finding B 直接论证。

**FIX-01 已验收结论未回退**（逐项核对）：P0-2 `evidence_at == candidate.created_at` 未改；
P0-3 `AI_ACCEPTED_LONG` 只认 `selected_strategy_ids` 显式包含 `BREAKOUT_RETEST` 未改；
P0-4 durable `ORDER_OPEN` → per-order exact resolution 未改；P1 cross-fact checks 未改。
本 Fix 对上述四处**零 diff**。

---

## 3. Finding A｜Feed quality 必须参与 OK

### Root cause

`ReferenceQuote` 自 FIX-01 起已携带 `data_quality`，但 `classify_reference` 的可用性判定
（`_is_well_formed`）只检查 `tradable` + 有限性 + 正序，**没有**把 `data_quality` 纳入。

后果：上游已标记 `STALE` / `UNAVAILABLE` 的报价，只要 bid/ask 在数值上「看起来正常」，
就会被判定为 `ReferenceDataStatus.OK` 并被写为 Opportunity 的 reference metrics
（顶层 `reference_bid/ask/received_at` 非空）——即**一个非新鲜(不新鲜)的 BBO 被提升为机会证据**。
这是冻结语义的违反：`OK` 必须是全部可用条件的**合取**，而不是「价格形状」的子集。

### Fix

`capture.py::ReferenceQuote._is_well_formed` → 重命名 `_is_usable`，并把
`data_quality is DataQuality.FRESH` 作为**第一条**条件纳入（重命名理由：方法现在表达的是
「可用性」而非「形状」，保留误导性名字会成为维护负债）。

冻结规则（`classify_reference` docstring 内逐条枚举为 10 项）：
quote 存在 → `instrument_id` 匹配 → `market_type` 匹配 → `data_quality == FRESH` → `tradable`
→ bid/ask 有限 → `bid > 0` → `ask > 0` → `bid <= ask` → `0 <= evidence_at - received_at <= max_age`。
任一失败：Opportunity 样本仍保留，`reference_data_status != OK`，顶层
`reference_bid / reference_ask / reference_received_at` **全部 NULL**（禁 zero / 伪造占位）。

### Tests

| 测试 | 断言 |
|---|---|
| `test_stale_and_unavailable_feed_quality_is_never_accepted_as_reference` | `DataQuality.STALE` / `UNAVAILABLE` 两例：Opportunity 行存在；`status != "OK"` 且 `== "REFERENCE_STALE"`；顶层三列全 NULL；payload 的 `supplied_quote.data_quality` 分别为 `STALE` / `UNAVAILABLE` 且 `bid == 99.5`（**同一报价在 FRESH 时被接受**，故被拒的唯一差异就是质量位本身） |
| `_reference_cases()`（既有 adverse matrix 扩展） | 新增 `data_quality_stale` / `data_quality_unavailable` 两例，纳入 `test_reference_availability_never_blocks_capture` 全矩阵（现 12 例） |

---

## 4. Finding B｜保留原始「被提供」的 quote 证据

### Root cause

不可变 `evidence_payload.reference_data` 在非 `OK` 时把 `bid / ask / received_at` 写成 `None`
（与 SE-02A 顶层契约保持一致的合理复用），但同时**也**用 `usable_quote` 作为唯一来源 ⇒
**被拒 quote 的真实 bid / ask / received_at 永久丢失**，只留下 `instrument_id / market_type /
data_quality / tradable`。

后果：future / stale-time / wrong identity / crossed / untradable / 质量不合格 等拒绝场景下，
事后无法从不可变证据回答「**当时到底收到了什么 quote，为什么拒绝它？**」——而这正是
SE-02B 证据自足性（self-sufficient immutable evidence）的核心要求。

### Payload structure（v3）

仅修改 `immutable evidence_payload`；**SE-02A 顶层 Reference contract 未修改**。

```
reference_data:
  status: OK | REFERENCE_MISSING | REFERENCE_STALE
  supplied_quote:            # 原始输入，逐字保留；无 quote 时为 null
    instrument_id, market_type, bid, ask, received_at, data_quality, tradable
  accepted_reference:        # 真正被 SE-02B 接受为 reference 的 metrics
    bid, ask, received_at    # status != OK 时三者全为 null
```

- `supplied_quote` 对**所有**已成功通过结构模型构造的 `ReferenceQuote` 逐字保留：future quote、
  stale-time quote、`STALE` / `UNAVAILABLE`、wrong instrument、wrong market type、untradable、
  crossed、non-positive、non-finite 一律不抹掉真实输入。
- **不伪造**任何 source / timestamp / exchange fact：每个字段都取自 quote 自身的 fact。
- 非有限价格（`NaN` / `±Infinity`）：canonical hashing contract 会 fail closed 拒绝，`JSON` 列也无法
  承载 ⇒ 以**规范名**字符串记录（`"NaN"` / `"Infinity"` / `"-Infinity"`），既不丢真实输入、
  也不破坏哈希确定性与 JSON 合法性（`_json_safe_price`）。这是「如实记录非有限输入」，
  不是伪造数值。
- `accepted_reference` 与 `supplied_quote` 在 `OK` 时一致（`accepted_reference` 即
  `supplied_quote` 的 bid/ask/received_at），非 `OK` 时保持 NULL；顶层
  `EdgeOpportunityEvidence` 的 `reference_bid/ask/received_at` 继续为 NULL（SE-02A 契约不变）。

### Payload version

`RUNTIME_CAPTURE_PAYLOAD_VERSION`：`se02b-runtime-capture-v2` → **`se02b-runtime-capture-v3`**。

理由：payload semantics 再次变化（v2 的被拒 quote 不带原始 bid/ask/received_at），
按既有 versioning discipline **不得**静默沿用 v2 表示不同 semantics。该 tag 只是 payload
contract version tag，**不涉及 migration**。常量注释已记录 v1/v2/v3 的语义差异。

### Tests

| 测试 | 断言 |
|---|---|
| `test_every_supplied_quote_is_kept_verbatim_while_only_ok_is_accepted` | 12 个 case 全表逐一断言 payload 完整相等：`capture_version == se02b-runtime-capture-v3`；`reference_data == {status, supplied_quote, accepted_reference}`；顶层三列 `None if status != OK`。覆盖 usable / future / time_stale / data_quality_stale / data_quality_unavailable / wrong_instrument / wrong_market_type / untradable / crossed / non_positive / non_finite / missing |
| `test_stored_evidence_reconstructs_the_frozen_setup_without_runtime_state`（增强） | 重建改用 **supplied_quote** 而非已接受 metrics，并断言 `supplied_quote` / `accepted_reference` / 顶层行三列；`hash_rebuild` / `id_rebuild` / `feature_hash_rebuild` 仍全 True |

---

## 5. Changed Files

| 文件 | 变更 |
|---|---|
| `backend/src/marketpulse/edge/capture.py` | Finding A：`_is_well_formed` → `_is_usable` 并纳入 `data_quality == FRESH`；`classify_reference` 冻结 10 条条件逐条枚举；新增 `_json_safe_price` / `_supplied_quote_payload`；`reference_data` 拆为 `supplied_quote` + `accepted_reference`；payload version v2 → v3；模块 docstring 增补 SE-02B-FIX-02 规则 |
| `backend/tests/test_se_02b_opportunity_capture.py` | Section H 重写为质量 + provenance 全套；`_provenance_cases()` / `_provenance_scenario()` 新增；`_reference_cases()` 增 2 例；`_reconstruction_scenario` 改由 supplied_quote 重建并增强断言 |
| `dev_log/2026-09-12-se-02b-fix-02-reference-quality-provenance.md` | 本文件 |
| `PROJECT_STATE.md` | 同步 SE-02B-FIX-02 真实状态 |

`git status --porcelain` 在两次提交之间实测仅含上表对应文件。

**测试自身构造缺陷（非产品缺陷，如实记录）**：`_provenance_cases()` 的 `non_positive` 例初版
写了 `_quote(bid=0.0, ask=100.0)` 但期望只覆盖 `bid=0.0`（ask 仍为默认 100.5）⇒ 断言失败。
实测 payload 的 `ask` 为 `100.0`（即真实输入被正确保留），确认是**期望值漏写**而非实现缺陷；
补 `ask=100.0` 后转绿。

---

## 6. Verification（逐项核对 Acceptance Criteria）

| AC | 结果 | 证据 |
|---|---|---|
| `data_quality = STALE` ⇒ 非 OK | PASS | 专用测试 + 全矩阵 |
| `data_quality = UNAVAILABLE` ⇒ 非 OK | PASS | 专用测试 + 全矩阵 |
| 非 OK 时 Opportunity 样本仍保留 | PASS | 12 case 全 `persisted is True` |
| 非 OK 时顶层 `reference_bid/ask/received_at` 全 NULL | PASS | 12 case 顶层行断言 |
| 非 OK 时 `accepted_reference` 三项全 NULL | PASS | 12 case payload 断言 |
| `supplied_quote` 逐字保留 future / stale / 错身份 / 错市场 / untradable / crossed / 非正 / 非有限 | PASS | 12 case payload 完整相等断言 |
| usable FRESH：`supplied_quote == 实际输入` 且 `accepted_reference == 实际接受 metrics` | PASS | `usable` case |
| missing quote：`supplied_quote` 为 null、`accepted_reference` 为 null | PASS | `missing` case |
| payload version 升级为 v3 | PASS | 全 case `capture_version` 断言 + 常量 |
| SE-02A 顶层 Reference contract 未变 | PASS | `edge/models.py` / `db/models.py` **零 diff**；顶层三列语义断言 |
| FIX-01 四项未回退 | PASS | 见 §2；对应实现与测试均零 diff |

---

## 7. Full Regression（真实执行）

| 门 | 命令 | 结果 |
|---|---|---|
| Focused（SE-02B + SE-02A） | `py -3.14 -m pytest test_se_02b_opportunity_capture.py test_se_02b_attribution.py test_se_02a_edge_contracts.py test_se_02a_edge_persistence.py` | **`134 passed`**（108.48 s） |
| ├ SE-02B capture | 同上单文件 | **15 passed**（基线 14） |
| ├ SE-02B attribution | 同上 | **31 passed** |
| └ SE-02A（contracts + persistence） | 同上 | **88 passed** |
| G2 / G3 / G4 | `py -3.14 -m pytest test_group2.py test_group3.py test_group4.py` | **`123 passed`**（142.74 s；与 FIX-01 基线一致） |
| Full backend | `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` | **`313 passed, 1 warning`**（395.33 s）= FIX-01 **312** + 本 Fix **+1**（新增 provenance 测试，净 +1：−1 v2 旧用例 +2 新用例） |
| Ruff | `py -3.14 -m ruff check backend/src backend/tests` | `All checks passed!`（rc=0） |
| compileall | `py -3.14 -m compileall -q backend/src backend/tests` | rc=0 |
| `git diff --check` | —— | rc=0（仅 LF→CRLF 提示，无空白错误） |
| `alembic heads` | `py -3.14 -m alembic heads` | 单 head `20260911_0005` |

**唯一 warning** = 既有 FastAPI/Starlette `httpx` deprecation（FIX-01 / N01-6 门同样存在），非本 Fix 引入。

### 共享 PG 并发写者取证（不把 failure 归因于 environment）

全量门在**独占写者窗口**内执行，双证据：

1. **进程扫描**（开跑前 + 门内每 5 s 采样，按 `Name like '*python*'` 取进程名后**再**匹配
   `CommandLine` 中的 `pytest` + `backend`，避免仅匹配命令行而误命中字面量）：
   - 开跑前发现外部全量 pytest（PID 32596，13:44:48 启动）⇒ **等待其 13:51:20 退出**后开始；
   - 门内 13:52:09–13:58:44 采样的本任务运行 PID 恒为 `30956`（唯一），本任务门独占；
   - 13:52:26 一次采样命中另一 PID `11272` 的 `pytest backend/tests --collect-only -q`（存活 <5 s）。
     collect-only **不执行任何测试、不写数据库**（仅导入并收集），且仓库内无任何测试会 spawn
     `--collect-only`（已 grep 确认）⇒ 判定为外部窗口的只读收集动作，**不构成本任务 workload 窗口的并发写者**。
2. **PG 客户端会话采样**（`pg_stat_activity WHERE backend_type='client backend'`）：
   门前后均只有探针自身 1 条连接；`pg_database LIKE 'marketpulse%'` 在门后回到 `['marketpulse']`
   （门前的 `marketpulse_r1_9f4c1ab77e02` 残留为外部窗口所有，非本任务产生，已于其窗口内消失）。

本任务门**未出现任何 failure**，因此不存在需要作 baseline / isolation / ordering 取证的失败集合。

---

## 8. Migration Check

| 项 | 结果 |
|---|---|
| 新增 / 修改 migration | **NONE** |
| `alembic heads` | 单 head `20260911_0005`（未变） |
| SE-02A 冻结契约文件 | `edge/{models,identity,hashing,repository}.py`、`db/models.py`、`alembic/` 均**零 diff** |

---

## 9. Scope Check

- 未开始 SE-02C / SE-02D；未实现 Forward Outcome Calculator / MFE / MAE / quote-path capture /
  horizon calculation / family aggregation / expectancy / KEEP-DOWNWEIGHT-KILL。
- 未激活 Real AI、未接 Live、未下 OKX real order、未动 UI、未新增 Opportunity Family。
- 未做 architecture refactor；未 merge `main`；未 amend / rebase / force push。
- `DECISIONS.md`、`PRODUCT_REQUIREMENTS.md` **未改**（本 Fix 是纠正冻结语义，不是新设计决策）。

---

## 10. Review Handoff

| 项 | 值 |
|---|---|
| Previous Reviewed SHA | `b8a5fe32fa38245ebd1ae9e30c31fe5654a7c05b` |
| New Fix SHA | `0b8a275050d11ba31b2df15823759750a049d1f1` |
| Diff Range | `b8a5fe3..0b8a275`（含本 dev_log + PROJECT_STATE 同步的 docs commit 见远端分支 tip） |
| Remote Branch | `se-02b-opportunity-capture-attribution` |
| Remote `main` | `af81414…`（**未动**） |
| 最终状态 | `IMPLEMENTED / VERIFIED / READY FOR INDEPENDENT RE-REVIEW` |

**给 reviewer 的最小复核路径**：

1. `git show 0b8a275 -- backend/src/marketpulse/edge/capture.py` 核对 10 条冻结条件与
   `supplied_quote` / `accepted_reference` 的拆分；
2. `pytest backend/tests/test_se_02b_opportunity_capture.py -q` ⇒ 15 passed；
3. 直接读任一被拒 case 的 `evidence_payload -> reference_data`，验证 `supplied_quote` 保留真实输入
   且 `accepted_reference` 为 NULL；
4. 核对 `edge/models.py` / `db/models.py` / `alembic/` 零 diff（SE-02A 顶层契约未变）。
