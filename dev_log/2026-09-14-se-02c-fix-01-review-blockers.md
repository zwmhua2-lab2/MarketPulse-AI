# SE-02C-FIX-01｜Review Blockers

- Date: 2026-09-14
- 专项: SE｜Strategy & Trading Edge
- Batch: SE-02C-FIX-01（修复 SE-02C 第一次 Independent Review 的 Acceptance Blockers）
- 窗口类型: **Implementation + Verification**（**非** Review、**非** Human Acceptance）
- Branch: `se-02c-fix-01-review-blockers`
- Worktree: `E:\Documents\MarketPulse-AI-se-02c-fix-01`
- Status: `SE-02C-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`
  （**未** merge `main`、**未** push `main`、**未** Human Accept、**未**启动 SE-02D）
- Latest Accepted Main: `dd78a979d128dee385c7a8ddc2254a53366af714`
- Original Reviewed Candidate: `be3aa6c817582f6161ea9903f7824200b7f5c843`（**immutable，未改写**）
- Integration Merge SHA: `51891c7d3f74429b2d6ef29d166a3f57617a57fe`
- Fix Implementation SHA: `7ab1d42ca248310f3857a4087d7ecfdfc14fa6ca`
- Docs / Status Commit = Final Branch Tip: 本文件所在 commit（SHA 见 §23 Evidence 远端复读）

---

## 1. Task

修复 SE-02C（Forward Outcome Calculator）第一次 Independent Review 判定的
`FAIL — FIX REQUIRED`，关闭 4 个 Findings，并把已复审 SE-02C candidate 安全集成到
最新 Accepted Main，产出可进入**独立复审**的候选。

关闭目标：

| Finding | 级别 | 关闭方式 |
|---|---|---|
| `SE02C-R1` | P1 BLOCKING | 删除 50,000 条读取上限，改为无上限读全量 Forward Path |
| `SE02C-R2` | P1 BLOCKING | tradability 由真实 instrument state 提供，禁止硬编码 True |
| `SE02C-R3` | P1 BLOCKING | 以最新 Accepted Main 为重基，真实 merge 原候选，重建合法 lineage |
| `SE02C-R4` | P2 NON-BLOCKING | anchor 仅作 reference authority，不再被当作 endpoint |

## 2. Review Findings

第一次 Independent Review = `FAIL — FIX REQUIRED`。

- **`SE02C-R1`（P1 BLOCKING）**：当 horizon 内 durable observation 超过 50,000 条时，
  `forward_service.py` 以 `MAX_FORWARD_PATH_OBSERVATIONS = 50_000` + `LIMIT 50_001`
  只向 Calculator 提供**最早** 50,000 条。后果：endpoint 可能不是真实 latest，MFE / MAE /
  `reference_return` / `executable_long_return` / `cost_adjusted_forward_return` 全部可能错误，
  且**不完整 path 仍会持久化 `COMPLETE`**。
- **`SE02C-R2`（P1 BLOCKING）**：live ingress 以 `DEFAULT_INGRESS_TRADABLE = True`
  无条件把 Forward BBO 记为 `tradable=True`，丢失真实 instrument tradable 状态。后果：
  suspended / non-tradable instrument 的 quote 被错误当作可交易行情参与
  `COMPLETE` / `executable return` / `cost-adjusted return`。
- **`SE02C-R3`（P1 BLOCKING）**：Review 期间 remote `main` 由 `8a29306` 推进到 `dd78a979`，
  旧候选 `be3aa6c` 不再建立在最新 Accepted Main lineage 上，必须重建合法 lineage。
- **`SE02C-R4`（P2 NON-BLOCKING）**：Anchor-only 情况当前可能返回 `ENDPOINT_STALE`；
  Approved semantics 要求 `ENDPOINT_MISSING`。Forward Path 范围必须严格
  `evidence_at < available_at <= due_at`，Capture Anchor（`available_at == evidence_at`）
  只允许作为 reference authority，本身不是 Forward endpoint。

## 3. Latest Main Drift

| 项 | 值 | 读取方式 |
|---|---|---|
| 写操作前 remote `main` | `dd78a979…` | `git ls-remote origin refs/heads/main` |
| 写操作前 original candidate | `be3aa6c…` | `git ls-remote origin refs/heads/se-02c-forward-outcome-calculator` |
| 原 SE-02C Task Base | `8a29306d904223f03408fe55538ba6cb05222f15` | `git merge-base dd78a979 be3aa6c` |
| `8a29306..dd78a979` 累积面 | 仅 `AI_CONTEXT.md` / `PROJECT_STATE.md` / `scripts/verify_n01_7_*.py` / `dev_log`（N01-7 收尾） | `git diff --stat 8a29306 dd78a979` |

**判定：`remote main` 与任务书声明一致（无二次 drift），候选亦未变，未触发 §39 STOP。**

关键核对：`8a29306..dd78a979` 中**没有** SE-02C production implementation —— 该区间为
N01-7 / N01-7-R01 收尾，与 SE-02C 代码面无交集。因此「以 `dd78a979` 为重基 + merge 原候选」
不会重复引入或覆盖 SE-02C 实现。

## 4. Integration Lineage

```text
8a29306  (Original SE-02C Task Base)
  ├─ se-02c-forward-outcome-calculator … be3aa6c   (已复审候选，immutable)
  └─ main … dd78a979                                (N01-7 / N01-7-R01 已 Accepted)

dd78a979 ─┐
          ├─ 51891c7  merge --no-ff  (Integration Merge SHA; 双父系保留)
be3aa6c ──┘
            │
            7ab1d42  fix(edge): close R1/R2/R4   (Fix Implementation SHA)
            │
            <docs>  dev_log + 状态同步            (Final Branch Tip)
```

- 第一父系 = `dd78a979`（最新 Accepted Main），第二父系 = `be3aa6c`（原已复审候选）。
- 集成方式 = `git merge --no-ff`：**无** rebase / squash / cherry-pick / force push；
  原候选 commit 与 N01-7 accepted lineage **均未被改写**。
- 冲突面（任务书 §6 预测一致）：仅 `AI_CONTEXT.md` 与 `PROJECT_STATE.md`，按 semantic union
  解决 —— 保留 N01-7 / N01-7-R01 已 Accepted 状态，同时记录 SE-02C =
  `IMPLEMENTED / FIXED / NOT ACCEPTED` 与 `SE-02C-FIX-01 = IMPLEMENTED / READY FOR
  INDEPENDENT RE-REVIEW`。**未**发生 production / tests / migration / schema 冲突。
- 合并引入面（`git diff --stat dd78a979 51891c7`）：`edge/forward.py`、`edge/forward_service.py`、
  `edge/__init__.py`、`g2/runtime.py`、两个 SE-02C 测试文件、SE-02C dev_log，以及两份状态文档。
  无 G3 / G4 / G5 语义改动。

## 5. Scope

允许并实际修改（**仅** 6 个文件）：

- `backend/src/marketpulse/edge/forward.py`
- `backend/src/marketpulse/edge/forward_service.py`
- `backend/src/marketpulse/market_data/models.py`
- `backend/src/marketpulse/market_data/normalizer.py`
- `backend/tests/test_se_02c_forward_outcome_service.py`
- `backend/tests/test_group1.py`
- 文档：`dev_log/2026-09-14-se-02c-fix-01-review-blockers.md`、`PROJECT_STATE.md`、`AI_CONTEXT.md`

另含集成动作：新建 branch / worktree、`git merge --no-ff` 原候选。

## 6. Out of Scope

- **未**修改 `backend/alembic/**`、`backend/src/marketpulse/db/models.py`（NO NEW MIGRATION）。
- **未**修改 G3 / G4 经济语义、G5 replay business semantics。
- **未**修改 `frontend/**`、`PRODUCT_REQUIREMENTS.md`。
- **未**引入 Redis / Kafka / Celery / new scheduler / Runtime Host / 第二个 OKX WS /
  第二条 BBO archive / new Outcome table / materialized view / background worker。
- **未**改动冻结的 V1 公式与 FIX-01 reference authority、FIX-02 revision scope。
- **未**顺手处理 `TEST-ISO-01`（仍维持 NON-BLOCKING P2）。
- **未**启动 `SE-02D`、**未** merge `main`、**未** push `main`、**未** Human Accept。

## 7. R1 Root Cause

`ForwardOutcomeService._load_observations` 把「一次查询的工作集上限」当成了
「计算正确性边界」：

```python
MAX_FORWARD_PATH_OBSERVATIONS = 50_000
...
.limit(MAX_FORWARD_PATH_OBSERVATIONS + 1)
truncated = len(rows) > MAX_FORWARD_PATH_OBSERVATIONS
return (tuple(... for row in rows[:MAX_FORWARD_PATH_OBSERVATIONS]), truncated)
```

超出部分被静默丢弃：endpoint 退化为「前 50,000 条里的最后一条」，MFE / MAE 只覆盖
path 前缀。更严重的是完整性：`truncated` 只进 diagnostics，**从未参与终态判定**，
因此不完整 path 仍可被写成 `COMPLETE`。

## 8. R1 Fix

- 删除 `MAX_FORWARD_PATH_OBSERVATIONS` 与 `LIMIT 50_001`（以及 `truncated=True` 语义）。
- 引入 `FORWARD_PATH_READ_PAGE_SIZE = 10_000`，语义明确为**单条语句页大小**，
  **不是**正确性上限。
- `_load_observations` 改为 keyset 分页循环，键 = 与 endpoint tie-break **同一**
  `(available_at, observation_id)` 全序：

  ```python
  tuple_(EdgeBboObservationRecord.available_at,
         EdgeBboObservationRecord.observation_id) > last_key
  ```

  循环仅在 durable 窗口耗尽时结束（`page` 为空，或 `len(page) < PAGE_SIZE`）。
- 返回类型由 `tuple[tuple[BboObservation, ...], bool]` 简化为 `tuple[BboObservation, ...]`；
  Calculator 侧删除 `truncated` 参数与 `path_truncated` diagnostic 键。
  于是「不完整 path + COMPLETE」不再是**可表示状态** —— 缺观测只会把结果**削弱**为
  `INSUFFICIENT_DATA`，不会误判为 `COMPLETE`（满足 §10 fail-closed 要求）。

## 9. R2 Root Cause

live ingress 把「有 quote 到达」错误地等价于「instrument 可交易」：

```python
DEFAULT_INGRESS_TRADABLE = True
...
tradable=DEFAULT_INGRESS_TRADABLE,   # 无条件 True
```

`Instrument.tradable`（G1 由 `instrument_from_okx()` 依 OKX `state == "live"` 解析）
这一**已批准 authority** 在 `Instrument → NormalizedBookTicker → Forward BBO` 链路上丢失，
且 normalized ticker 契约里没有承载该事实的字段。

## 10. R2 Fix

- 删除 `DEFAULT_INGRESS_TRADABLE`。
- `NormalizedBookTicker` 增加可选运行期字段：

  ```python
  tradable: bool | None = None
  ```

  取值语义：`True` / `False` = 上游明确知道；`None` = 该 frame **没有**权威 tradability fact。
  optional + 默认 `None` 保证既有 Replay fixtures、旧 constructors、非 Forward consumers
  仍可构建（**不是** DB schema change）。
- `normalize_book_ticker` 传递 `tradable=inst.tradable`，即把 `Instrument.tradable`
  端到端保留。
- `build_forward_path_observation` 读取 `event.tradable`：
  - `True` / `False` → 原样持久化（Calculator 随后排除 `tradable=False`）；
  - `None` → 抛 `ForwardPathTradabilityUnknown`（`ValueError` 子类）。
- `ForwardPathRecorder.record_event` 捕获 `ForwardPathTradabilityUnknown` →
  bounded warning + 返回 `None`，**不落库、不猜测、不中断 ingest loop**。

## 11. R4 Root Cause

`ForwardObservationSelection.endpoint` 在 `self.eligible`（`evidence_at <= available_at
<= due_at`）上取最大，而 capture anchor 恰好满足 `available_at == evidence_at`，
因此 anchor 会**合法地**成为 endpoint 候选。

## 12. R4 Fix

- `ForwardObservationSelection` 增加 `evidence_at: datetime` 字段；
  `path_points` 由带参方法改为属性，定义为严格 `available_at > evidence_at`；
  `endpoint` 只在 `path_points` 上取最大。
- 结果：Anchor-only scope（唯一 durable 行即自身 anchor）的 `path_points` 为空 ⇒
  `endpoint = None` ⇒ `INSUFFICIENT_DATA` + `ENDPOINT_MISSING`，metrics 全 `NULL`，
  `end_bbo_observation_id = NULL`；reference 仍正常绑定（anchor 作为 reference authority）。

## 13. Files Changed

| 文件 | 变更 | 对应 Finding |
|---|---|---|
| `edge/forward.py` | `ForwardObservationSelection` 增 `evidence_at`；`endpoint` / `path_points` 限定严格 forward path；删 `truncated` 参数与 `path_truncated` 诊断键 | R1 / R4 |
| `edge/forward_service.py` | 删 `MAX_FORWARD_PATH_OBSERVATIONS` / `DEFAULT_INGRESS_TRADABLE`；增 `FORWARD_PATH_READ_PAGE_SIZE` / `ForwardPathTradabilityUnknown`；`_load_observations` 改 keyset 分页无上限；`build_forward_path_observation` 读 `event.tradable`；recorder fail-closed | R1 / R2 |
| `market_data/models.py` | `NormalizedBookTicker.tradable: bool \| None = None` | R2 |
| `market_data/normalizer.py` | `normalize_book_ticker` 传 `tradable=inst.tradable` | R2 |
| `tests/test_se_02c_forward_outcome_service.py` | 新增 50,001 观测回归 + tradability Case A/B/C + anchor-only 断言更新 | R1 / R2 / R4 |
| `tests/test_group1.py` | 新增 OKX BBO normalization 保留 instrument tradability 回归 | R2 |
| `PROJECT_STATE.md` / `AI_CONTEXT.md` | 状态与血缘同步（merge conflict semantic union） | R3 |
| `dev_log/2026-09-14-se-02c-fix-01-review-blockers.md` | 本文件 | 文档 |

## 14. Business Behavior

| 行为 | Before | After |
|---|---|---|
| >50,000 观测的 horizon | 只算前 50,000 条；endpoint / MFE / MAE 可能错；可误判 `COMPLETE` | 全量参与；endpoint = 真实 latest；MFE / MAE 覆盖完整 path |
| 不完整 path | 可能 `COMPLETE` | 不可表示（缺观测只会削弱为 `INSUFFICIENT_DATA`），无 `truncated` 标志 |
| non-tradable instrument 的 later quote | 记为 `tradable=True`，可能成为 endpoint 并产生 `COMPLETE` + executable / cost-adjusted return | `tradable=False` 原样持久化并被 Calculator 排除；不产生 `COMPLETE` |
| `tradable=None` frame | 落库为 `True` | fail closed：不落库 + bounded warning；ingest 不中断 |
| Anchor-only scope | 可能 `ENDPOINT_STALE` | `ENDPOINT_MISSING`，metrics NULL |
| 已 settled scope | 幂等，不自动 revision 2 | 不变 |
| Frozen V1 公式 / 5 s TTL / due_at 定义 / 四 horizon | —— | 完全未改 |
| Schema / Migration | `20260913_0009` | `20260913_0009`（**未变**） |

## 15. PostgreSQL Identity

- 容器：`marketpulse-se-02c-fix-01-pg`（本窗口一次性 disposable）
- 镜像：`postgres:16-alpine`；端口绑定 `127.0.0.1:5441 → 5432`
- 库 / 用户：`marketpulse` / `marketpulse`
- 服务端版本：`PostgreSQL 16.15 on x86_64-pc-linux-musl`（`select version()`）
- 主库迁移状态：`alembic_version = 20260913_0009`，`public` 表 30 张，
  `market_events` / `edge_bbo_observations` / `edge_forward_outcomes` 均存在
- 端口合规：`5441` ∉ {5432, 5437, 5438, 5439, N01 DB, 其它 Acceptance DB}
- 隔离路由：仅由 gitignored `worktree/.env` 与 `worktree/backend/.env` 提供
  `DATABASE_URL=postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5441/marketpulse`；
  测试运行**未导出** `DATABASE_URL`（见 §20 环境发现）。

## 16. Tests

- R1（§11 required 50,001 regression）：`test_more_than_fifty_thousand_forward_observations_are_used_in_full`
  —— 真实 PostgreSQL，durable = 1 anchor + 50,001 forward observations。
- R2（§18 Case A/B/C + suspended）：`test_tradability_is_carried_from_the_instrument_and_unknown_tradability_fails_closed`
  —— 另加 `test_group1.py::test_okx_bbo_normalization_carries_the_instrument_tradability`。
- R4：`test_terminal_status_matrix_is_persisted_without_any_pending_row`（anchor-only ⇒ `ENDPOINT_MISSING`）。
- 既有判据全部保持：original formula fixture、due boundary、pending 派生、stable reference、
  late arrival / future quote 排除、5 s freshness、四 horizon、cross evidence、retry、restart、
  concurrency exactly-one、no auto revision 2、Replay / Forward provenance separation。

## 17. Regression

| 套件 | tests | fail | err |
|---|---|---|---|
| SE-02C focused（`test_se_02c_forward_outcome_calculator.py` + `_service.py`） | 49 | 0 | 0 |
| market_data relevant（`test_group1.py`） | 7 | 0 | 0 |
| SE-02A（`edge_contracts` + `edge_persistence`） | 102 | 0 | 0 |
| SE-02B（`attribution` + `opportunity_capture`） | 62 | 0 | 0 |
| G2（`test_group2.py`） | 30 | 0 | 0 |
| G5（`test_group5_1..5_4`） | 32 | 0 | 0 |
| **指定回归合计** | **282** | **0** | **0** |
| **full backend（`pytest backend/tests -q`）** | **421** | **0** | **0** |

静态门：`ruff check backend/src backend/tests scripts` = `All checks passed!`；
`compileall -q backend/src` = rc 0；`git diff --check` = rc 0；
`alembic heads` = 单 head `20260913_0009`；`G5 schema_head = 20260913_0009`。

> FIX-01 / FIX-02 无独立测试文件：其判据内嵌于 SE-02A（capture anchor / FIX-01）与
> SE-02C（revision scope / FIX-02）套件，已随上表一并运行。

## 18. Acceptance Matrix

| # | 判据 | 结果 | 依据 |
|---|---|---|---|
| F01-01 | Latest Accepted Main 正确 | PASS | `git ls-remote` = `dd78a979…`；任务书一致 |
| F01-02 | Original candidate lineage preserved | PASS | `51891c7` 双父系含 `be3aa6c`；原候选 SHA 未变 |
| F01-03 | No schema / migration change | PASS | `alembic heads` 单 `20260913_0009`；`alembic/**` 与 `db/models.py` 零 diff |
| F01-04 | 50,001 observations 选择真实 latest endpoint | PASS | `endpoint_is_the_true_latest = true` |
| F01-05 | 50,001 的 MFE / MAE 使用完整 path | PASS | `mfe = 0.10`、`mae = -0.10`（`path_point_count = 50001`） |
| F01-06 | Incomplete / truncated path 不得 COMPLETE | PASS | `truncated`/`path_truncated` 已不存在（不可表示）；`no_truncation_flag = true` |
| F01-07 | No hard-coded tradable=True authority | PASS | `DEFAULT_INGRESS_TRADABLE` 全库零引用 |
| F01-08 | Normalizer 保留 `Instrument.tradable=True` | PASS | Case A：`normalized=True → durable=True`；`test_group1` 同名回归 |
| F01-09 | Normalizer 保留 `Instrument.tradable=False` | PASS | Case B + suspended：`normalized=False → durable=False` |
| F01-10 | Unknown tradability fail closed | PASS | Case C：`recorded=None`、`builder_raises=true`、`rows=0` |
| F01-11 | Non-tradable BBO 被 Calculator 排除 | PASS | `case_b_is_the_endpoint=false`；`excluded_untradable_count=1`；suspended `COMPLETE` 行 = 0 |
| F01-12 | Anchor 不得成为 endpoint | PASS | `endpoint` 仅在 `path_points`（严格 `>`）上取最大 |
| F01-13 | Anchor-only ⇒ `ENDPOINT_MISSING` | PASS | `eth_window_path_point_count=0`；`insufficient_reason="ENDPOINT_MISSING"`；metrics NULL |
| F01-14 | Original formula fixture PASS | PASS | `test_required_formula_vector_matches_the_frozen_specification` |
| F01-15 | Settled scope normal evaluator idempotent | PASS | `test_a_settled_scope_never_grows_an_automatic_revision_two` |
| F01-16 | No automatic revision 2 | PASS | 同上 + `test_the_calculator_never_creates_a_revision_above_one` |
| F01-17 | Retry PASS | PASS | `test_one_evaluation_pass_appends_one_terminal_outcome_per_scope_and_a_restart_changes_nothing`（retry 段） |
| F01-18 | Restart PASS | PASS | 同上（restart 段） |
| F01-19 | Concurrency exactly-one PASS | PASS | `test_two_concurrent_evaluators_append_exactly_one_outcome_for_the_scope` |
| F01-20 | Four horizons PASS | PASS | `test_the_four_horizons_are_independent_scopes` |
| F01-21 | Cross evidence PASS | PASS | `test_two_evidence_revisions_of_one_opportunity_own_disjoint_outcome_scopes` |
| F01-22 | Replay / Forward provenance PASS | PASS | `test_replay_and_forward_share_the_calculation_digest_but_not_the_record_hash` |
| F01-23 | SE-02A/B + FIX-01/FIX-02 regression PASS | PASS | §17：SE-02A 102 + SE-02B 62 + SE-02C 49，全 0 fail |
| F01-24 | N01-7 accepted files preserved | PASS | `git diff dd78a979 51891c7 -- scripts/verify_n01_7_*.py` 为空 |
| F01-25 | Full backend PASS | PASS | `421 passed` |
| F01-26 | Ruff / compileall / diff-check PASS | PASS | 三者 rc = 0（`All checks passed!`） |

## 19. Self-Check

- [x] 写操作前实测 remote 真值，`main` / candidate 均与任务书一致，无二次 drift。
- [x] 以 `dd78a979` 为重基、真实 merge 原候选，双血缘保留，未 rewrite 原候选。
- [x] Production Code 修改面 = 任务书 §27 允许清单；无 `while I'm here` 顺手改动。
- [x] 未改公式、未改 FIX-01 authority、未改 FIX-02 revision scope、未改 G3/G4/G5 语义。
- [x] 无新表 / 新迁移 / 新依赖；head 保持单 `20260913_0009`。
- [x] 新增回归覆盖 R1（50,001）、R2（True/False/None）、R4（anchor-only）。
- [x] 全部验证在真实 disposable PostgreSQL 上执行，未用 mock 替代。
- [x] 未导出 `DATABASE_URL`；仅靠 worktree `.env` 路由隔离库。
- [x] 状态仅写 `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`，**未**写 ACCEPTED / COMPLETE。

## 20. Result

`SE-02C-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`

- `SE02C-R1` = PASS（50k 上限已删除，全量 path 参与；不完整 path 不可表示）
- `SE02C-R2` = PASS（tradability 端到端权威；`None` fail closed）
- `SE02C-R3` = PASS（双血缘真实 merge，原候选 immutable）
- `SE02C-R4` = PASS（anchor-only ⇒ `ENDPOINT_MISSING`）
- `F01-01 .. F01-26` = 全 PASS
- `Schema Changed = NO` / `Migration Added = NO` / `Runtime Activated = NO`
- `SE-02C = IMPLEMENTED / FIXED / NOT ACCEPTED`；`SE-02D = NOT STARTED`

## 21. Remaining

- 本窗口**不**自行 Acceptance、**不** merge `main`、**不** push `main`、**不**启动 SE-02D；
  等待 Independent Re-Review。
- `N01-8`（12-hour Extended Soak）与 Integrated Runtime Host 仍 `NOT STARTED`，
  须由总进度窗口另开独立获批的任务窗口。
- 环境遗留（**未授权清理，原样保留**）：容器 `marketpulse-se-02c-fix-01-pg` @ `5441`
  与其 worktree 的 gitignored `.env`（⇒ 在该 worktree 跑 pytest 会走 5441，主库已迁至 head）。
  释放方式：`docker rm -f -v marketpulse-se-02c-fix-01-pg`。

## 22. Known Risks

- `TEST-ISO-01`（P2 NON-BLOCKING）仍存在：本窗口未顺手修，仅确保未导出 `DATABASE_URL`
  以不污染测试 DB routing。
- `RRF-03` / `RRF-04` 等既有 NON-BLOCKING 项不受本窗口影响，也未处理。
- keyset 分页把「一次查询工作集」压到 `FORWARD_PATH_READ_PAGE_SIZE`，但单 scope 的
  **总内存**仍与 path 长度线性相关（返回完整 tuple）。这是 Approved semantics
  （complete path correctness 优先于 bounded memory）的直接结果，**不是**截断；
  若未来需要更强内存约束，须走 Proposal → Human approval，不得在本类修复中暗自引入上限。
- `NormalizedBookTicker.tradable` 为 optional 字段：任何**新建**该类型的代码若忘记传值，
  得到的是 `None`（fail closed，不落库），而非静默 `True` —— 方向安全，但会让该 frame
  不再进入 Forward path。Replay fixtures 与非 Forward consumers 不受影响。

## 23. Context For Re-Reviewer

- 复审对象 = branch `se-02c-fix-01-review-blockers` 的 Final Branch Tip（本文件所在 commit）。
- 请独立复核而非采信本摘要：`git diff dd78a979..<tip>` 应仅含 §13 所列文件；
  `git rev-list --parents -n 1 51891c7` 应为 `dd78a979` + `be3aa6c` 双父系；
  `git rev-parse be3aa6c` 应与远端候选一致（未被改写）。
- 重点复核项：
  1. R1 —— 确认 `_load_observations` 的分页循环**无**任何隐式上限，且
     `FORWARD_PATH_READ_PAGE_SIZE` 不参与正确性判定；确认 `truncated` 语义确实消失而非改名。
  2. R2 —— 确认 `tradable=False` 的 observation 真的**不能**成为 endpoint，
     且 `tradable=None` 的 frame 真的不落库；确认 ingest loop 不中断。
  3. R4 —— 确认 anchor-only 走的是 `ENDPOINT_MISSING` 而非 `ENDPOINT_STALE`，
     且 metrics / `end_bbo_observation_id` 全 NULL 而 reference 仍绑定。
- 环境提示：`backend/alembic/env.py` 为
  `os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))`，**环境变量优先**。
  复审时**不要导出** `DATABASE_URL`，否则 disposable 库会保持空 schema。
  另：G5 的 `ReplayWorkspaceGuard.counts(primary)` 会对 **primary** 库统计
  `_REPLAY_BUSINESS_TABLES`，因此 primary 库**自身也必须**位于 Alembic head
  （本窗口即因 primary 库未迁移而先出现 15 个 `relation "market_events" does not exist`
  假失败，迁移 primary 后 G5 32 项全绿）。

## 24. Evidence

- 远端复读（§38 要求三 refs）：
  - `main` = `dd78a979d128dee385c7a8ddc2254a53366af714`（**未变**，本窗口未 push main）
  - `se-02c-forward-outcome-calculator` = `be3aa6c817582f6161ea9903f7824200b7f5c843`（**未变**）
  - `se-02c-fix-01-review-blockers` = 见本次 push 后复读结果（Final Branch Tip）
- R1 实测（真实 DB，disposable）：
  `forward_path_observation_count=50001`、`durable_bbo_rows=50002`、
  `endpoint_is_the_true_latest=true`、`path_point_count=50001`、
  `mfe=0.10000000000000009`、`mae=-0.09999999999999998`、
  `reference_return=0.10000000000000009`、
  `executable_long_return=0.09442786069651743`、`end_bid=109.99`、`end_ask=110.01`、
  `status=COMPLETE`、`no_truncation_flag=true`、
  `first_extreme_was_outside_the_old_ceiling=true`、
  `page_size_is_smaller_than_the_path=true`。
- R2 实测：Case A `normalized=true → durable=true → is_the_endpoint=true`；
  Case B `normalized=false → durable=false → is_the_endpoint=false`、
  `excluded_untradable_count=1`；Case C `recorded=None`、`builder_raises=true`、`rows=0`；
  suspended `durable=false`、`status=INSUFFICIENT_DATA`、`reason=ENDPOINT_MISSING`、
  `metrics_are_null=true`、`end_is_not_bound=true`、`complete_rows=0`。
- R4 实测：`eth_durable_observations=1`、
  `eth_window_available_at_equals_evidence_at=true`、`eth_window_path_point_count=0`、
  `insufficient_status=INSUFFICIENT_DATA`、`insufficient_reason=ENDPOINT_MISSING`、
  `insufficient_metrics_are_null=true`、`insufficient_end_is_not_bound=true`、
  `insufficient_reference_is_bound=true`；同场景 `INVALID`（`INVALID_FORWARD_ANCHOR_MISSING`）、
  `pending_rows=0`、`outcome_count=12`。
- 测试与静态门原始输出：`E:\Temp\se-02c-fix-01\`（`named2.xml` / `named2.txt` /
  `full_backend.txt` / `g5_rerun.txt` / `evidence_fresh.json` / `evidence_run.txt`）。

---

## 附：本窗口环境发现（可复用）

1. ✅ 已核对：`backend/alembic/env.py:12` =
   `os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))` —— 环境变量优先，
   跑 pytest 时不得导出 `DATABASE_URL`。
2. 🚩 **新发现**：G5 replay / evaluation 套件除 disposable replay 库外，还会对
   **primary 库**执行 `SELECT count(*) FROM <table>`（`g5/replay.py:485` →
   `ReplayWorkspaceGuard.counts(primary)`）。因此**新建 disposable PostgreSQL 后，
   primary 库自身也必须 `alembic upgrade head`**；否则整批报
   `asyncpg.exceptions.UndefinedTableError: relation "market_events" does not exist`，
   极易被误判为代码回归（本轮先出现 15 个此类假失败，迁移 primary 后全绿）。
3. `alembic` CLI 的 `script_location` 相对 **cwd** 解析：须 `cd backend` 后
   `py -3.14 -m alembic -c alembic.ini upgrade head`（在仓库根直接 `-c backend/alembic.ini`
   会报 `Path doesn't exist: alembic.`）。
