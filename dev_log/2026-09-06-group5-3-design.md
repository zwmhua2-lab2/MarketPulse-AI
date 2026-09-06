# 2026-09-06 G5-3 — End-to-End Determinism DESIGN（已批准修订）

> 状态：`G5-3 DESIGN = APPROVED`；Reviewer 的 AC-01～AC-07 修订已纳入本记录，`READY FOR G5-3 IMPLEMENTATION`。本文只描述设计与验收契约，未实现任何代码。
> 依据：G5-2 Acceptance = `eb1e5f076ecbd6d74e622203b06e367e6058b295`；Current Accepted Main 以 Git `main` / `origin/main` 为准（CIP-02）。

## 1. Requirement（问题陈述）

G5-1 证明了 G2 内存链路「同一输入两次回放 → 相同 canonical trace」（in-memory, G2-only）。
G5-2 证明了全链路（G2→G3→G4/Paper Execution）单次回放在独立 PostgreSQL Replay workspace 产生
正确、历史时间、无 look-ahead、primary 不变的可信结果，并用 deterministic `stable_id` 验证了
snapshot/review/decision/plan/order/fill/trade/ledger/event 的 ID 与时间。

G5-3 的目标：把「确定性」从 G2-only / 单次运行提升为 **end-to-end、跨两次独立运行** 的可证性质：

- **R1 双跑一致**：完全相同的回放输入（frames + recorded G3/G4 provider records + scanner config），
  在两个全新 disposable Replay workspace 各跑一次，全部 durable 业务事实逐行逐值一致。
- **R2 无可泄漏源**：回放链中不存在会进入 durable 事实的 wall-clock / 随机 / 哈希序依赖；
  已注入的 `ReplayClock` / 稳定 ID factory 覆盖所有可达路径（含 payload 规范化）。
- **R3 可复现指纹**：存在确定性的 canonical workspace 提取与摘要（digest），相同输入 → 相同 digest；
  digest 可用作两条 runs 相等性的独立证据，不依赖内存对象。
- **R4 负向敏感**：单点有意义的 fixture 扰动（首选 protective-stop `BookTicker.bid: 89 → 88`）必然改变
  digest，且交易生命周期仍有效；canonical diff 必须证明受影响的业务事实可解释，防止「假相等」/ 测试退化为恒真。

## 2. 已核实代码事实（本窗口真实读取，2026-09-06）

| 事实 | 位置 | 确定性结论 |
|---|---|---|
| `stable_id` = sha256(排序 JSON parts)，无随机源 | `g3/service.py:54` | 确定 |
| G2 event/timeline/transition id 由 event_time 等派生 | `g2/runtime.py:225`、`g2/repository.py:72` | 确定 |
| G3 decision/plan/scenario/acct/order/fill/trade/pos/ledger/outbox id 全部 `stable_id(...)` | `g3/service.py:263/313/357/471/811/1045/1057/1060/1129/1149/1454` | 确定 |
| DB models 无 `uuid4`/`datetime.now` 列默认值（时间与 id 全部由 service 显式写入） | `db/models.py`（grep 无命中） | 确定 |
| G4 review snapshot 默认 ID factory 含 `uuid4().hex` | `g4/reevaluation.py:591` | **默认不确定**；Replay 已注入 `_review_snapshot_id`（`replay.py:552/761`） |
| `BoundedAITaskQueue.put` 用 `datetime.now(UTC)` | `g3/service.py:221` | **默认不确定**；`DecisionService.decide` 直呼 `provider.analyze`（`service.py:346`），Replay 用 recorded provider，queue 为 live 引擎路径（实现期须验证 Replay 链不可达） |
| `SystemClock.now()` = `datetime.now(UTC)`；`HealthRegistry.set`/`EventRuntime.started_at` 用 wall-clock | `clock.py:11`、`runtime.py:14/36/47` | 仅内存/非 durable（实现期须验证不落库） |
| Replay runner 每个组件均注入 clock（state/incident/risk/runtime/pipeline/execution/protection/plans/reevaluation/safety/decision/plan/builder） | `g5/replay.py:508-568` | 已注入 |
| `_rows()` 已具备全表提取原型；G5-2 E2E 单跑断言 22 类 durable 时间均落在历史窗口 | `tests/test_group5_2_trading_replay.py` | 单跑证据已存在 |
| G5-1 `same_replay_twice` 仅比较内存 G2 canonical trace | `tests/test_group5_1_replay.py:116` | G2-only |

已知需在 canonical 提取中处理的规范化点：PostgreSQL `jsonb` 列读回不保证 key 顺序；
numeric 列经 asyncpg 返回 `Decimal`；时间列需统一 UTC `isoformat`。

## 3. Scope（批准后实现范围）

1. **两次完全独立的真实 PostgreSQL Replay**：创建 Run A / Run B 两个全新、clean、disposable
   `marketpulse_g53_*` workspace，均处于相同 Alembic head，使用相同 normalized historical fixture、Scanner
   配置、初始 balance/configuration、Recorded G3/G4 responses。每次均重新构造
   `ReplayTradingRunner`、`ReplayClock`、`EventRuntime`、providers、services 与所有内存 runtime state；不得复用
   workspace 或已初始化 runner。
2. **Canonical durable workspace snapshot**（新增，仅 replay/test 层）：以 `ReplayWorkspaceGuard` 的
   `_REPLAY_BUSINESS_TABLES` 为唯一 accepted set，按下面固定顺序、每表全部 durable 列、每行 PostgreSQL primary
   key 排序提取。若任何 canonicalized table 没有可用 deterministic primary key，必须 fail，不得接受隐式 DB 顺序：

   ```text
   market_events, signal_timeline_events, symbol_states, state_transitions,
   strategy_candidates, derived_observations, decision_snapshots, ai_decisions,
   trade_plans, trade_plan_scenarios, execution_intents, paper_orders, fills,
   positions, trades, accounts, ledger_entries, outbox_records, runtime_controls,
   symbol_controls, incidents, position_events
   ```

   这覆盖 durable G2 → G3 → G4/Paper 全链路；`ReplayTradingResult` 不是 canonical source，仅可暴露结果
   digest 供调用方使用。primary/replay DB 名称、primary-count diagnostics、Alembic metadata、process/log/
   `HealthRegistry` timestamps 与测试耗时均不得进入 snapshot。
3. **冻结 canonicalization contract**：递归且无损地规范化值：datetime → UTC fixed-format ISO-8601；Enum →
   `enum.value`；`Decimal` → exact deterministic string；float → lossless `float.hex()`；JSON/JSONB dict → key
   排序的递归值；JSON array 保持原有数组顺序；`None`/bool/int/string 保持其精确类型和值。canonical snapshot
   使用 deterministic UTF-8 JSON 序列化，并计算 SHA-256；严禁 Python 内置 `hash()` 或任何 tolerance rounding。
4. **确定性审计（实际 transitive Replay 路径）**：审计 `uuid4`/uuid、`datetime.now`、`SystemClock`、`random`、
   `secrets`、`time.time`、`os.urandom`、Python `hash()`、会影响业务行为的 unordered set/dict iteration，以及
   DB-generated random/default。每一处必须分类为 `REPLAY REACHABLE`、`REPLAY UNREACHABLE`、
   `REPLAY OVERRIDDEN / INJECTED` 或 `NON-BUSINESS ONLY`。已知 G4 default review `uuid4()` 必须由
   deterministic `snapshot_id_factory` 覆盖；G3 `BoundedAITaskQueue.datetime.now()` 必须以实际 Replay 路径
   不可达为证。若发现任一 business-result-affecting source 在 Replay 中可达，停止并标记 `BLOCKED`；不得
   静默修改已验收的 G2/G3/G4 或 Live 语义。
5. **diagnostic equality 与负向敏感回归**：A/B 必须同时断言 canonical snapshot equality 与 SHA-256 equality。
   不一致时，canonical diff 至少报告 table、row/primary key、column/path、Run A value、Run B value，不能只给
   digest。Run C 使用仅一项获批 fixture mutation（首选 protective-stop `BookTicker.bid: 89 → 88`），并保持
   lifecycle valid；必须 `Digest(A) != Digest(C)`，且 diff 显示可解释的 SELL fill price、realized PnL、final
   account、ledger 或 trade economics 差异。
6. **ReplayTradingResult 增补**：可追加 `workspace_digest`（内存 dataclass，无 schema 变更）。
7. 状态文档同步仅发生在实现完成后：dev_log、PROJECT_STATE、AI_CONTEXT；无 `DECISIONS.md` 变更。

## 4. Out of Scope（禁止）

- **不改 schema / 不加 migration**（无新表、无新列；digest 不进 DB）。
- **不改 live / G2/G3/G4 业务引擎行为**；除第 3.1 条确证的 replay-only 最小注入外零业务改动。
- **不改 recorded provider 语义**；不调用真实 AI / OKX / 网络；不引入 fallback。
- **不做 G5-4 / Performance Analytics / Dashboard**；不实现新的交易或风险行为。
- 不把 digest/回放结果写入 primary DB；不静默吞掉任何确定性断言失败。

## 5. 验收契约（Acceptance Contract，AC）

批准后实现的验收标准（与 G5-1/G5-2 同样的 Reviewer + Formal Acceptance 流程）：

- **AC-01 — Two Independent Replay Runs**：Run A 与 Run B 为两个不同的 clean disposable PostgreSQL workspace，
  从完全相同的 fixture/configuration/recorded responses 与 Alembic head 出发，且每次运行所有 runner/runtime
  对象均新建；`CanonicalSnapshot(A) == CanonicalSnapshot(B)` 并且 `Digest(A) == Digest(B)`。
- **AC-02 — Canonical Durable Workspace Snapshot**：snapshot 严格覆盖第 3.2 节 22 张
  `ReplayWorkspaceGuard` business tables 的 durable state，不以 `ReplayTradingResult` 代替；明确排除环境与
  diagnostic identity。
- **AC-03 — Frozen Canonicalization Contract**：固定 table order、按 PostgreSQL primary key 排 row、无 key fail、
  使用第 3.3 节的递归无损值规范化，以及 deterministic UTF-8 JSON + SHA-256；不得隐式排序、rounding 或
  Python `hash()`。
- **AC-04 — Diagnostic Equality**：除 A/B snapshot 和 digest 相等外，mismatch 必须有 table、row/PK、column/path、
  A value、B value 的 diagnostic diff。
- **AC-05 — Reachability / Non-Determinism Audit**：第 3.4 节所有来源均完成分类与 source/path evidence；若有新的
  replay-reachable business nondeterminism，结果为 `STOP / BLOCKED`，不以修改 accepted G2/G3/G4/Live 规避。
- **AC-06 — Negative Sensitivity**：新 Run C 只有一个获批 meaningful fixture mutation（首选 bid `89 → 88`），
  lifecycle valid，`Digest(A) != Digest(C)`，canonical diff 指向可解释的业务经济事实。
- **AC-07 — Final Determinism Gate**：A/B 的 snapshot、digest 相等；A/C digest 不等；A/B 所有历史业务时间仍在
  fixture timeline；primary DB unchanged；Real AI calls = 0；OKX/network calls = 0；schema migration = 0；
  `replay_run_id` = 0；Live modification = 0；second trading engine = 0；Performance Analytics = 0。必须实际运行
  G5-3 targeted PostgreSQL、G5-2、G5-1、G1/G2、G3、G4、full backend、Ruff、compileall、`git diff --check`、
  Alembic heads/current。`PYTHONHASHSEED` 跨进程测试是有价值的额外证据，但不是 G5-3 V1 acceptance blocker，
  除非审计发现 hash-order dependency。

## 6. 建议实现方式（批准后按此推进）

- 新增实现于 `backend/src/marketpulse/g5/`（如 `canonical.py`）与
  `backend/tests/test_group5_3_determinism.py`；复用一个 G5-2 风格 fixture（新文件内自包含，
  不 import 测试私有函数）。
- branch：`g5-end-to-end-determinism`（新），main 保持 Accepted Baseline；
  实现、自测、regression、commit、push branch、停止等待 Review（遵循 AGENTS.md GitHub Review 流程）。
- 不 merge main、不做 acceptance、不进 G5-4。

## 7. Scope Check（本设计阶段）

- G5-3 code added：NO（本文仅为设计）。
- Schema migration / `replay_run_id`：NO。Real AI / OKX / 网络：NO。Live changed：NO。primary DB written：NO。
- Forbidden：交易规则变更、accepted Live behavior 变更、second Scanner/Strategy/Risk/Execution engine、
  Performance Analytics、Replay UI/API、optimizer、G5-4。
- Next State：`G5-3 DESIGN APPROVED → IMPLEMENTATION`；实施需遵循本记录，完成后只提交当前 Group branch，
  不自行 merge `main` 或自宣 Acceptance。
