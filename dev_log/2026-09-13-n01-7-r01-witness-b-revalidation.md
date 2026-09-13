# N01-7-R01 — Witness B Fix + Latest-Main Revalidation + 2h Acceptance Re-run

- Date: 2026-09-13
- Task: **N01-7-R01**｜Validation Harness Fix + Latest-Main Targeted Revalidation + Formal Acceptance Re-run
  （**非**新实现；**非** production fix；**非**需求变更；**非** N01-8）
- Branch: `n01-7-r01-witness-b-latest-main`
- Worktree: `E:\Documents\MarketPulse-AI-n01-7-r01`（本批唯一作业 worktree；根 worktree
  `E:\Documents\MarketPulse AI` 全程未触碰）
- Status / Result: **`VALIDATED / READY FOR INDEPENDENT RE-REVIEW`**（状态（Validation 完成时）；
  现已由 2026-09-14 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout 取代为
  **`ACCEPTED / COMPLETE`** —— 见本文件 §32）
  （`N01-7 = ACCEPTED / COMPLETE`；`N01 overall = NOT ACCEPTED`；`N01-8 = NOT STARTED`）

## 1. Requirement 与 Review Findings

N01-7 已完成一次正式 2h Medium Runtime Soak，Independent Review 结论为
**`D. CHANGES REQUIRED / REVIEW FAIL`**，理由两条：

### R01（P1）— F01 Witness B 未真实执行

原 harness 的 Witness B 把 **Position durable protection snapshot** 与
**同一个旧/已过期 ACTIVE plan** 作比较：两者 `plan_id` 与 `plan_version` 完全相同，
因此**从未真实建立 `Plan A != Plan B`**。

后果：原 Acceptance Run **没有真正验证**「一个新的 ACTIVE TradePlan 不会在未经
successor snapshot atomic commit 的情况下，自动夺取当前 OPEN Position 的 durable
protection authority」。即使该缺陷（新 ACTIVE plan 自动夺取 authority）真实存在，
原 harness 也可能照样 PASS。

> 分类：**HARNESS DEFECT**（非 PRODUCT DEFECT）。按任务书 §24.A，允许修改
> validation-only harness，且修复后正式 2h clock 必须从 0 重来 —— 本批即从 0 重跑。

### R02 — Latest-Main Baseline Drift

| 项 | SHA / 值 |
|---|---|
| 原 N01-7 Task Base | `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f` |
| 旧 N01-7 candidate | `728197923e11558ee5bbcaf1fcbc075ece2e520a` |
| Review 时 current main | `8a29306d904223f03408fe55538ba6cb05222f15` |

当前 main 已包含 `SE-ARCH-FIX-01`（Stable Evidence Anchor）与 `SE-ARCH-FIX-02`
（Outcome Revision Chain Scope），均 `ACCEPTED / COMPLETE`，migration lineage 已到
`20260913_0009`。

Review 判定：baseline drift **不是** full-soak blocker 本身，但必须在 latest main 上做
**targeted revalidation**。由于本任务本身即要求重跑正式 2h Acceptance，故一次性关闭：
在最新 Accepted Main 上完成 targeted validation **+** 正式 2h re-run。

任务书 §3 明令：**不得**从旧 candidate `7281979` 派生新分支（其 migration head 是旧的
`20260912_0006`）；旧 candidate 仅作 harness / evidence / behavioral reference。

## 2. Task Base / Current Main / Repository Truth（CIP-01/02/03，本批实测）

| 项 | 实测值 | 结论 |
|---|---|---|
| `git ls-remote origin refs/heads/main` | `8a29306d904223f03408fe55538ba6cb05222f15` | 远端真值 |
| 本地 `main` | `8a29306…` | 与远端一致 |
| worktree HEAD | `8a29306…`（branch `n01-7-r01-witness-b-latest-main`） | = Task Base |
| `git status --porcelain`（开工时） | `AM scripts/verify_n01_7_medium_soak.py` / `AM scripts/verify_n01_7_runtime_soak.py` | 承接自前一窗口的移植 |
| **Task Base SHA（本轮 execution baseline，冻结）** | **`8a29306d904223f03408fe55538ba6cb05222f15`** | 任务书 §22 |
| **Accepted Main SHA** | **`8a29306…`** | — |
| **Migration Head（实时）** | **`20260913_0009`**（单 head） | 链 `0001…0005 → 0006(N01-7 protection snapshot) → 0007(FIX-01 anchor) → 0008(FIX-01 review fix) → 0009(FIX-02 scope)` |
| Latest-Main Drift（开工时） | **NO** | 未触发 STOP |

**Worktree 安全**：仅在上表唯一 worktree 内作业；根 worktree `E:\Documents\MarketPulse AI`
（已知 dirty / stale，停在 `prb-01-product-requirements-baseline`）内**未**执行任何
`git add` / `commit` / `reset` / `restore` / `checkout` / `clean`。

**承接说明（透明披露）**：进入本批时该 worktree 已有前一窗口的移植改动
（`scripts/verify_n01_7_*.py` 已 `git add`、另有未暂存实现），其后静默约 21 min。
经与用户确认后由本批**接管**：本批对 harness 做了下述 §5 全部修复，并对全体改动做了
独立复核与重跑；**接管前的实现未被本批自证为正确**，其正确性由本批重跑的
Probe #2 + 正式 Run 独立证明。

## 3. Scope / Out of Scope（任务书 §6 / §26）

**允许**：
1. validation-only harness 修复：**真正实现 Witness B**；
2. 把已通过的 N01-7 validation harness 安全移植/适配到 latest main；
3. 修正 migration/head validation（不再要求 `head == 20260912_0006`，改为证明
   实时 head / single head / `0006` 仍为 ancestor / `0006` protection schema 仍保留）；
4. 运行 latest-main targeted verification；
5. 运行新的正式 **≥7200 s** Acceptance Run；
6. 建立新的 evidence package / dev_log。

**Out of Scope（一行未改）**：`backend/src/**`、`backend/alembic/**`、`backend` production
behavior、`frontend/**`、`PRODUCT_REQUIREMENTS.md`、`DECISIONS.md`、`pyproject.toml`、
`docker-compose.yml`、旧 N01-7 evidence（`E:/Temp/n01-7-medium/`，保留只读）、
任何 SE 语义、N01-8、Integrated Runtime Host。

**实际改动文件**：`scripts/verify_n01_7_medium_soak.py`、`scripts/verify_n01_7_runtime_soak.py`
（均 validation-only）、`dev_log/2026-09-13-n01-7-r01-witness-b-revalidation.md`（本文件）、
`PROJECT_STATE.md` / `AI_CONTEXT.md`（最小状态同步）。
**`E:/Temp` 下 raw evidence 不进入仓库**，仓库只保存可复核摘要 / 指纹 / 路径 / 结论。

## 4. Production Code Freeze（任务书 §7）

- `backend/src/**` / `backend/alembic/**` / production config / product semantics = **FROZEN**。
- 本批**未**为关闭 R01 修改任何 production code；正式 Run 报告内
  `production_code_unchanged = true`、`production_status_porcelain` 为空、
  `production_diff_stat` 为空（见 §17）。
- 任务书 §7 明令：若真实 Witness B 发现 production 确实让新 ACTIVE plan 夺取 authority，
  则为 **PRODUCT DEFECT** ⇒ `BLOCKED / FINDING CONFIRMED` + STOP，**不得顺手修**。
  本轮**未**出现该情形（见 §7–§11）。

## 5. Accepted Contract（不得变更，任务书 §5）

N01-7-F01 已批准并冻结：

- **TradePlan TTL 只控制 risk-increasing freshness**（`BUY` / `ADD` / pending `LIMIT` fill）；
- 它**不控制** OPEN Position 的 protection lifetime；
- 对 OPEN Position，**Position durable protection snapshot 是唯一 protection-lifetime authority**；
- authority 只允许两种转移：**(A)** approved successor protection snapshot 原子提交到同一
  Position，或 **(B)** Position becomes flat；
- **新 ACTIVE TradePlan 只是 protection authority source**，不会仅因 `ACTIVE` / `valid` /
  `newer` 就自动成为当前 Position 的 protection authority。

本批**只验证**该契约，**未**修改契约。

## 6. Harness Fix — Real Witness B（本批实际做出的修改）

被改文件：`scripts/verify_n01_7_medium_soak.py`（主 harness）、
`scripts/verify_n01_7_runtime_soak.py`（观察 helper）。全部为 validation-only。

| # | 修改 | 目的 |
|---|---|---|
| 1 | 新增 `_persist_witness_b_plan(harness, bbo, *, plan_version, stop_b, take_profit_b)`：显式构造 `TradePlan`（`plan_id = stable_id("plan","n01-7-r01","f01-witness-b",…)`、`plan_version` 由参数传入、`expires_at = now + WITNESS_B_PLAN_TTL`），经**生产** `persist_trade_plan` 落库 | 产生**真正的 Plan B**：新 `plan_id` + 新 `plan_version`，且仍是 ACTIVE plan（`persist_trade_plan` 会把旧 ACTIVE 置 `REPLACED` 后插入新 plan，**不动 position 行 snapshot**） |
| 2 | `_witness_b_new_active_plan` 改用 `_persist_witness_b_plan(..., plan_version=authority_before.plan_version + 1, …)` | 替换原 `harness.persist_controlled_long(tag="f01-witness-b")`（其 `plan_version` 恒为 1，正是 R01 缺陷来源） |
| 3 | 新增常量 `WITNESS_B_PLAN_TTL = timedelta(hours=6)` | Plan B 必须在 Witness C（第 ~61 min）时**仍未过期**，否则重启见证会退化成"plan 早已过期"这一更弱的问题 |
| 4 | 新鲜报价改用 `n6._wait_until(_fresh_btc_quote, timeout=WITNESS_B_FRESH_QUOTE_MAX_WAIT_SECONDS=45.0)` | `bbo-tbt` 只在价格变动时推送，单次采样可能取到 age > `n6.FRESH_QUOTE_MAX_AGE_SECONDS=2.0` 的旧价 ⇒ 原实现会误报 `no_fresh_quote_strictly_above_snapshot_stop_for_plan_b`（**Probe #1 实测**） |
| 5 | 新增证据 `discriminating_quote`（含 `strictly_between_stops`）与 `counterfactual_if_plan_b_were_authoritative`（用 `PositionProtectionService._trigger` 反证"若 B 是 authority 会 STOP_LOSS"） | 满足任务书 §10 的**行为判别**要求（仅比 DB snapshot 不够） |
| 6 | 证据 `versions_distinct` / `plan_b_expires_at` / `plan_b_unexpired_at_creation` | 让 "Plan A != Plan B" 在 version 维度也可复核 |
| 7 | `_protection_authority_after_restart`（Witness C）删除硬编码 `authority.plan_version == 1` 与 `durable_plan["plan_version"] == 1`，仅保留 `authority.plan_id != durable_plan["plan_id"]` | 原硬编码会在 Plan B 真实 `version != 1` 时误判 |
| 8 | `PROBE_PHASE_SECONDS` 150 → **240** | 保证 Probe 的 schedule 能真正跑到 Witness B 项（含 STALE 停顿持有 + 等新鲜恢复） |
| 9 | `EXPECTED_MIGRATION_HEAD` 由静态 `20260912_0006` 改为 `soak._current_migration_head()`（动态） | 任务书 §13：不得再要求 `head == 0006`，改以实时 head 为准 |
| 10 | 新增 `soak._migration_lineage()`（静态解析 alembic revisions，证明 single head + `0006` 为 ancestor）与 `soak._protection_schema(database_url)`（**只读**读回隔离库 protection 列）+ checks `migration_lineage_single_head` / `f01_protection_migration_is_ancestor_of_head` / `position_protection_columns_present_after_upgrade` | 任务书 §13 的 ancestry / columns 要求 |
| 11 | 新增跨 phase 身份一致性 checks `f01_restart_restored_snapshot_a` / `f01_restart_active_plan_is_plan_b`（`first.witness_b` 与 `second.f01_after_restart` 比对 Plan A / Plan B 身份） | 把 Witness B 与 Witness C 串成同一条跨进程证据链 |
| 12 | `log_dir` → `n01-7-r01-logs`；database prefix / owned / observer `application_name` → `n01-7-r01` 域 | 任务书 §21：不得与旧 N01-7 evidence 共用库名或 `application_name` |

> ⚠️ 与 §16 字段名的对应：任务书 §16 举例的 `witness_b.snapshot_unchanged_before_successor_commit`
> 与 `witness_b.protection_followed_position_snapshot` 在本 harness 中对应的证据为
> `position_snapshot_before_plan_b == position_snapshot_after_plan_b` 以及
> checks `f01_witness_b_snapshot_unchanged` / `f01_witness_b_protection_followed_snapshot`
> （语义一致，命名不同）。

## 7. Witness B Design（任务书 §8 / §9）

1. 建立真实 `LIVE_PAPER` OPEN LONG，其 protection snapshot 来自 **Plan A**；
2. 记录 `snapshot.plan_id = A` / `snapshot.plan_version = A.version` / `stop_loss = Stop A` /
   `take_profit = TP A`；
3. 让 Plan A 的 risk-increasing freshness TTL 自然到期（Plan A 保留真实 30 min TTL），
   而 Position 保持 OPEN ⇒ 校验 snapshot 仍为 Plan A；
4. 随后创建**真正新的 ACTIVE Plan B**（`B.plan_id != A.plan_id`，`Stop B != Stop A`），
   **不**执行 approved successor snapshot atomic commit；
5. 校验 Position durable snapshot **仍为 Plan A**；
6. 再加行为判别（§8）与反证（§9）。

## 8. Plan A Facts（正式 Run，`first.witness_b`）

| 字段 | 值 |
|---|---|
| `plan_a_id` | `plan_7d212f0ce53054e676a6e30c` |
| `plan_a_version` | `1` |
| `stop_a` | `72932.355` |
| `take_profit_a` | `80609.44499999999` |
| snapshot（before / after Plan B） | `{plan_id: plan_7d212f0ce53054e676a6e30c, plan_version: 1, stop_loss: 72932.355, take_profit: 80609.44499999999}` |

Plan A 的 TTL 到期事实（`first.f01`）：`plan.expires_at = 2026-09-13T13:09:48.565829+00:00`，
`expired_at_observation = true`，`load_valid_long_active_plan = null`，而同时
`protection.present = true` / `protection.protection_plan_id = plan_7d212f0ce53054e676a6e30c`
⇒ **risk-increasing validity 已消失，protection 仍在**。

## 9. Plan B Facts（正式 Run）

| 字段 | 值 |
|---|---|
| `plan_b_id` | `plan_f9c9560e6a5d22319a490a28` |
| `plan_b_version` | `2` |
| `stop_b` | `74836.5775` |
| `take_profit_b` | `80686.18579999999` |
| `plan_b_expires_at` | `2026-09-13T19:10:55.035723+00:00`（= 创建 + 6 h） |
| `plan_b_unexpired_at_creation` | `true` |
| `ids_distinct` / `stops_distinct` / `versions_distinct` | `true` / `true` / `true` |
| `active_plan_b` | ACTIVE（durable active plan，见 §13） |

⇒ **`A != B` 在 plan_id、plan_version、stop_loss 三个维度同时成立**（满足任务书 §8 的
"必须 A != B" 与 "最好 stops 不同"）。

## 10. Discriminating Quote（任务书 §10）

| 字段 | 值 |
|---|---|
| `discriminating_quote.bid` | `73884.46625` |
| `discriminating_quote.ask` | `73884.56625` |
| `received_at` | `2026-09-13T13:10:55.054140+00:00` |
| `strictly_between_stops` | `true` |

判别式（LONG）：`Stop A (72932.355) < test_bid (73884.46625) <= Stop B (74836.5775)` ✔

- 若系统**错误**使用 Plan B ⇒ 应触发 protection exit；
- 若系统**正确**使用 snapshot Plan A ⇒ 不应触发。

**实际结果**：
- `protection_decision = {"triggered": false, "reason": "HOLD", "trigger": "NONE"}` ⇒ **服从 snapshot A**；
- `counterfactual_if_plan_b_were_authoritative = {"trigger": "STOP_LOSS", "would_exit": true, "stop_loss": 74836.5775, "take_profit": 80686.18579999999}`
  ⇒ 反证该判别价**确实具有区分力**（并非因价格根本不触发而"假 PASS"）；
- `position_after_discriminating_quote`：持仓状态未变，无 new order / fill；
- `economic_counts.before == after` = `{orders: 1, fills: 1, positions: 1, trades: 1, accounts: 1, ledger_entries: 1}`
  ⇒ 判别未产生任何经济事实；
- `reconciliation.ok = true`（13/13 不变量，含 `open_position_protection_survives_plan_ttl`）。

## 11. Protection Authority Evidence（任务书 §9 / §10 / §11）

| 断言 | 证据 | 结果 |
|---|---|---|
| Position snapshot 未被 Plan B 覆盖 | `position_snapshot_before_plan_b == position_snapshot_after_plan_b`（均 `plan_7d212f0ce53054e676a6e30c v1`） | **PASS** |
| 无未授权 replacement | 同上 + `f01_witness_b_snapshot_unchanged = true` | **PASS** |
| Plan B 是 ACTIVE 却不成为 authority | `f01_active_plan_b_does_not_replace_snapshot = true` | **PASS** |
| 行为服从 snapshot A | `f01_discriminating_quote_follows_snapshot_a = true` + 决策 `HOLD` | **PASS** |
| 判别力非空 | counterfactual `would_exit = true` | **PASS** |

任务书 §11 的"successor atomic commit 前 A / 后 B"加分证据：本批**未**执行该加分项
（属可选加分，非硬要求）；硬要求 `Plan B ACTIVE != Plan B 自动成为 protection authority`
**已由真实执行为证的 Witness B 满足**。

## 12. Witness A Evidence（任务书 §25 AC-10）

正式 Run phase first 的 `f01_*` checks 全 `true`，其中 Witness A 直接证据：

| Check | 值 |
|---|---|
| `f01_plan_expired_observed` | `true` |
| `f01_plan_no_longer_risk_increasing_valid` | `true` |
| `f01_position_still_open_after_expiry` | `true` |
| `f01_protection_snapshot_complete_after_expiry` | `true` |
| `f01_protection_service_uses_snapshot_after_expiry` | `true` |
| `f01_expired_plan_blocks_risk_increasing` | `true` |
| `f01_snapshot_matches_originating_plan` | `true` |
| `f01_witness_harness_ok` | `true` |
| `f01_no_position_unprotected_incident` | `true` |

⇒ **TTL 到期不终止 OPEN Position protection**（Probe 窗口只有 240 s、不足以等到 30 min TTL
到期，故此项在 Probe 中为 false 属预期，仅在正式 Run 转 true）。

## 13. Witness C Evidence — Restart（任务书 §12 / §25 AC-13）

`second.f01_after_restart`（fresh process）：

| 字段 | 值 |
|---|---|
| `position_quantity` | `0.0013019242290383903`（仓位仍 OPEN） |
| `authority.plan_id` / `plan_version` | `plan_7d212f0ce53054e676a6e30c` / `1`（**= snapshot A**） |
| `authority.stop_loss` / `take_profit` | `72932.355` / `80609.44499999999` |
| `durable_active_plan.plan_id` / `plan_version` | `plan_f9c9560e6a5d22319a490a28` / `2`（**= Plan B**） |
| `durable_active_plan.expired` | **`false`**（Plan B 重启时**仍 ACTIVE**） |
| `state.plan_status` | `ACTIVE` |
| `state.protection.protection_plan_id` | `plan_7d212f0ce53054e676a6e30c` |
| `state.protection.protection_updated_at` | `2026-09-13T12:39:48.604025+00:00`（**保持原值 ⇒ 恢复而非重建**） |
| `evaluate` | `{"triggered": false, "reason": "HOLD", "trigger": "NONE"}` |

⇒ 重启后 authority **从 durable Position snapshot 恢复**，且**未**通过 active TradePlan 重新推断；
因重启时 Plan B 仍 ACTIVE，这是任务书 §12 所述"**更强证据**"。

## 14. Migration Ancestry（任务书 §13 / §25 AC-01）

`migration.lineage`（由 `soak._migration_lineage()` 静态解析）：

```
heads: ["20260913_0009"],  single_head: true,  head: "20260913_0009",  revision_count: 9
lineage: 0001 → 0002 → 0003 → 0004 → 0005 → 0006 → 0007 → 0008 → 0009
f01_protection_revision: "20260912_0006",  f01_protection_is_ancestor_of_head: true
```

- `migration.observed_in_run_database = 20260913_0009`（`alembic_version`，disposable DB 内实测）；
- `checkpoints`（checks）：`migration_lineage_single_head = true`、
  `f01_protection_migration_is_ancestor_of_head = true`、
  `position_protection_columns_present_after_upgrade = true`、`single_migration_head = true`；
- `position_protection_columns_present_after_upgrade` 直接读回隔离库 schema，确认
  protection 5 列（`protection_plan_id` / `protection_plan_version` / `protection_stop_loss` /
  `protection_take_profit` / `protection_updated_at`）仍存在；
- `alembic upgrade head` 在 disposable PostgreSQL 上成功；
- **未**将 head 硬编码为永久常量；`0009` 只是实时读到的 current head。

## 15. Targeted Regression（任务书 §14 / §25 AC-03）

- 执行：`pytest backend/tests`（受 `python -m pytest`，cwd = worktree 根，隔离 `.env`
  指向任务专属容器 5434）。
- 结果：**`371 passed, 1 warning`（437.93 s 级别的全量套件，本次 8m19s）**。
- 该全量套件**是**任务书 §14 所列定向集合（`test_group2/3/4.py`、`test_n01_*.py`、
  SE-02A/SE-02B、SE-ARCH-FIX-01/02 focused）的**超集**，故 §14 的定向要求已被覆盖。
- 与 accepted main `8a29306` 的既有基线（full backend `371 passed`）**一致** ⇒ 最新 main
  的 Edge / G2 集成改动**未**改变 N01 runtime semantics / queue lifecycle / protection
  authority / Recovery / Reconciliation。

## 16. Probe（任务书 §15 / §16 / §25 AC-04 / AC-05）

### Probe #1 — FAIL（harness defect，非 product defect）

`result: FAIL`，11 个 `f01_witness_b_*` 失败，`harness_error =
"no_fresh_quote_strictly_above_snapshot_stop_for_plan_b"`。

根因：原实现只在单次采样取 `feed["latest_bbo"]`。`bbo-tbt` 只在价格变动时推送，
瞬时采样到的 quote 可能已超 `n6.FRESH_QUOTE_MAX_AGE_SECONDS = 2.0`（实测 bid `76837.4` 其实
**高于** `stop_a`，问题在**新鲜度**而非价格）。⇒ 属 §24.A HARNESS DEFECT，按 §24.A
修复 harness 并**从 0 重来**。

### Probe #2 — PASS

| 项 | 值 |
|---|---|
| `result` | **`PROBE_OK`** |
| `failures` | `[]` |
| `migration_head_observed` | `20260913_0009` |
| database | `marketpulse_n01_7_r01_50d39b6655a6` @ `127.0.0.1:5434` |
| phase first / second active | `240.138 s` / `240.102 s` |
| pids | `1204` → `31568`（两个独立 OS 进程） |
| `restart_gap_seconds` | `6.599` |

Probe #2 的 Witness B（任务书 §16 全部满足）：`plan_a_id = plan_7d212f0ce53054e676a6e30c v1`、
`plan_b_id = plan_f9c9560e6a5d22319a490a28 v2`、`ids_distinct = true`、`stops_distinct = true`、
`position_snapshot_before_plan_b == position_snapshot_after_plan_b`、
`protection_followed_position_snapshot = true`（决策 HOLD）、判别 bid `73968.02875` 严格介于
`73007.405` 与 `74928.6525` 之间、counterfactual `would_exit = true`。

⇒ 任务书 §16 "禁止启动正式 2h" 的前置条件**已满足**，故启动正式 Run。
Probe raw：`E:/Temp/n01-7-r01/probe2_raw.json`。

## 17. Formal Runtime Timeline（任务书 §17 / §18 / §25 AC-06）

`verify_n01_7_medium_soak.py`（default `--mode acceptance`，**无** `--probe`），**单轮全新**
（未复用旧 N01-7 7320 s，未拼接）：

| 项 | 值 |
|---|---|
| `result` | **PASS**（mode `ACCEPTANCE`） |
| database | `marketpulse_n01_7_r01_856000935929` @ `127.0.0.1:5434` |
| `started_at` / `finished_at` | `2026-09-13T12:38:40.403724+00:00` / `2026-09-13T14:40:56.030669+00:00` |
| `wall_clock_seconds` | `7335.627` |
| phase first active | **`3600.140 s`**，pid `11720` |
| phase second active | **`3720.113 s`**，pid `768` |
| **`total_active_seconds`** | **`7320.252` ≥ 7200** ✔ |
| `restart_gap_seconds` | `6.375`（两个独立 OS 进程，`no_python_memory_carried_over = true`） |
| `reconnects` | **5**（目标 5） |
| `stale_cycles` | **2**（目标 2） |
| `checkpoints` | **7** |
| checks | **84 项全 `true`**，`false = []` |
| `failures` / `phase_process_errors` / `phase_failures` / `harness_errors` / `shutdown_errors` | 全 `[]` |
| `production_code_unchanged` | `true` |
| `production_status_porcelain` / `production_diff_stat` | 空 / 空 |

> §17 合规：单轮全新 Acceptance Run，**未**复用旧 N01-7 7320 s、**未**拼接；旧 raw artifacts
> （`E:/Temp/n01-7-medium/`）保留只读、未被覆盖。

## 18. Reconciliation Checkpoints（任务书 §18 / §25 AC-14）

7/7 `ok = true`：

| label | absolute_elapsed_seconds |
|---|---|
| `start` | `0.21` |
| `abs_30m` | `1800.156` |
| `before_restart` | `3540.05` |
| `final_before_stop` | `3600.14` |
| `after_restart` | `3600.217` |
| `abs_90m` | `5340.142` |
| `final` | `7320.585` |

`checkpoints_cover_required_points = true`（≥7 + `before_restart`/`after_restart` +
start/~30m/~60m/~90m 四个覆盖带均被命中）、`all_checkpoints_ok = true`、
`reconciliation_ok = true`。13/13 不变量（含 `open_position_protection_survives_plan_ttl`）。

## 19. Reconnect（任务书 §18 / §25 AC-07）

5/5 受控重连，每项均 `disconnect_observed = true` + `fresh_event_after_reconnect = true`
+ `reconciliation_ok = true`；`controlled_reconnects_recovered_fresh = true`、
`reconnect_reconciliation_ok = true`、`reconnects_ge_5 = true`。

## 20. Stale → Fresh（任务书 §18 / §25 AC-08）

2/2 受控停顿（`stall_seconds ≈ 60.0`；phase first @ `900.175 s`、phase second @ `1200.327 s`）：

- 停顿前 `health = HEALTHY`、`risk_gate.admitted = true`；停顿投递"停顿前最后一条**已投递**报价"
  （H-1 铁律），使 quote 真正超生产 5.0 s freshness TTL；
- 停顿中：`health = UNAVAILABLE`、risk-increasing **fail-closed**、**无** fabricated economic fact、
  durable protection facts **保全**；
- 恢复新鲜后：`stale_cycles_fresh_recovered = true`、`stale_cycles_fresh_protection_hold = true`、
  `stale_cycles_quote_genuinely_stale = true`、`stale_cycles_reconciliation_ok = true`。

## 21. Restart（任务书 §18 / §25 AC-09）

`shared` 与 `fresh_process_restart_performed = true`；`after_restart` checkpoint 于
`3600.217 s` 记录；RecoveryManager 15 步全绿（`0.13 s`）：
`STARTING → RECOVERING → LOAD_RUNTIME_CONTROL → LOAD_ACCOUNT → LOAD_OPEN_ORDERS →
LOAD_POSITIONS → LOAD_ACTIVE_PLANS → LOAD_SYMBOL_STATES → FIND_ACTIVE_SYMBOLS →
FETCH_FRESH_MARKET_DATA → EXECUTION_GAP_RECORDED → RECONCILIATION → REVALIDATE_PLANS_ORDERS →
RESTORE_POSITION_PROTECTION → FINAL_STATE:RUNNING`；
`recovery_ok = true`、`recovery_final_state_running = true`、`recovery_position_recovered = true`、
`recovery_protection_snapshot_recovered = true`、`no_fabricated_fill_across_restart = true`。

## 22. Resources（任务书 §18 / §25 AC-15）

| 指标 | first | last | max | 净增长（first / second phase） |
|---|---|---|---|---|
| sockets | `5` | `5` | `6` | `+1` / `+1`（`socket_band_delta_across_reconnects = -1`） |
| handles | `195` | `184` | `197` | `-10` / `-10`（`handle_band_delta_across_reconnects = -1`） |

`sockets_not_accumulating = true`、`handles_not_accumulating = true`、
`no_detached_runtime_tasks = true`、`final_no_owned_tasks = true`、
`worker_count_stable = true`、`worker_exceptions_zero = true`、
`queue_drained = true`、`inflight_empty = true`（AC-15）。

## 23. Memory（任务书 §19 / §25 AC-16）

冻结 AND 契约（**本批未修改任何 threshold**）：`RSS total growth > 64 MiB` **AND**
`second-half slope > 5 MiB/h` 同时成立才算 Finding。

| 字段 | 本 Run 实测 |
|---|---|
| `points` | `656` |
| `warmup_baseline_mb` / `peak_mb` / `final_mb` | `117.5` / `131.543` / `124.715` |
| `total_growth_mib` | `14.043`（阈值 `64.0`） |
| `second_half_trend_mib_per_hour` | **`16.019965`**（阈值 `5.0`） |
| `overall_trend_mib_per_hour` | `2.699123` |
| **`finding`** | **`false`** |

⇒ **Memory Gate = PASS**（AND 判据第二支不成立：`total_growth 14.043 MiB ≤ 64 MiB`）。
`memory_within_approved_condition = true`、`memory_series_present = true`。

> 🚩 **P2 Watch Item（如实记录，不得据此宣称"内存无问题"）**：`second_half_trend = 16.02 MiB/h`
> **再次越线**（上一 N01-7 Run 为 `5.255 MiB/h`，本次更高），仅因 `total_growth 14.043 MiB ≪ 64 MiB`
> 而不构成 Finding。按任务书 §19，本次**未**修改 threshold，slope 继续作为 **N01-8 Watch Item**。
> 另：本批**未**运行 external monitor（任务书 §20 为"如果继续使用"的可选项），故本 Run **无**
> 进程外 cross-check 视图；Memory Gate 的 Acceptance basis 仍是 Harness 全程 RSS samples
> （§20 明令不得改变 Acceptance basis），故不构成 blocker，但需 Reviewer 知晓。

## 24. DB Isolation（任务书 §21 / §25 AC-18 / AC-19）

| 要求 | 实测 |
|---|---|
| unique database | `marketpulse_n01_7_r01_856000935929`（disposable，运行后 `DROP`） |
| unique application_name | owned / observer 均落在 `n01-7-r01` 域（`owned_application_name` / `observer_application_name`） |
| separate observer | `n6._observer_engine()`（连 **primary** 库，独立 `application_name`，不计入 owned 会话） |
| explicit DATABASE_URL | `.env` → `postgresql+asyncpg://marketpulse:marketpulse@127.0.0.1:5434/marketpulse` |
| 容器 | `marketpulse-n01-7-r01-pg`（`postgres:16-alpine`）@ `127.0.0.1:5434` |

**未**使用 primary / SE / shared Acceptance DB。

| 断言 | 结果 |
|---|---|
| `leftover_databases`（disposable residue） | **`0`** |
| `disposable_database_residue_zero` | `true` |
| shared primary `before` | `{revision: 20260905_0004, protection_columns: [], owned_sessions: 0}` |
| shared primary `after` | `{revision: 20260905_0004, protection_columns: [], owned_sessions: 0}` |
| `shared_primary_unchanged` / `shared_primary_no_owned_sessions` | `true` / `true` |
| `runtime_dsn_points_at_task_owned_instance` | `true` |
| `pg_other_sessions_zero_all_samples` / `pg_owned_clients_zero` / `pg_idle_in_transaction_zero` | `true` / `true` / `true` |

⇒ **primary DB unchanged**（AC-19），**residue = 0**（AC-18）。

## 25. Economic Invariants（任务书 §25 AC-17）

`final_position_flat = true`、`final_no_open_buy = true`、`final_exactly_one_exit_fill = true`、
`final_single_trade_lifecycle = true`、`final_no_duplicate_facts = true`、
`final_reserved_cash_zero = true`、`final_cash_non_negative = true`、
`final_protection_snapshot_cleared_when_flat = true`、`reconciliation_ok = true`
⇒ **无 duplicate / fabricated economic fact**（AC-17）。Witness B 判别过程的经济计数
`before == after`（`orders/fills/positions/trades/accounts/ledger_entries` 各不变）。

## 26. Baseline Drift（任务书 §22）

| 时点 | `origin/main`（`git ls-remote` 实测） |
|---|---|
| 本轮开始（Task Base，冻结） | `8a29306d904223f03408fe55538ba6cb05222f15` |
| **本轮结束（运行完成后重新读取）** | **`8a29306d904223f03408fe55538ba6cb05222f15`**（**相同**） |

⇒ **`main drift during run = NO`**。本轮结论对实时 `origin/main` = `8a29306` 成立。
（若发生 drift，按 §22 只记录 BASELINE DRIFT + delta，**不**自行 merge/rebase；
由 Independent Re-Review 决定 no action / targeted revalidation / full rerun。）

## 27. Verification / Self-Check（任务书 §25 AC-01…AC-20）

| AC | 内容 | 证据 | 结果 |
|---|---|---|---|
| AC-01 | Latest-main Repository Truth / migration lineage PASS | 起止两次 `ls-remote` = `8a29306`；`single_head` + `0006` ancestor + protection 5 列读回 | **PASS** |
| AC-02 | Production Code Changed = NO | `production_code_unchanged = true`；`backend/` `frontend/` diff 空 | **PASS** |
| AC-03 | Targeted latest-main regression PASS | `pytest backend/tests` = **371 passed**（§14 定向集合的超集） | **PASS** |
| AC-04 | Real-OKX Probe PASS | Probe #2 `PROBE_OK`，real OKX BTC/ETH（REST 经本机代理、WS 直连） | **PASS** |
| AC-05 | Probe 真正执行 Plan A != Plan B 的 Witness B | Probe #2 `ids_distinct`/`stops_distinct` = true（§16 字段全部命中） | **PASS** |
| AC-06 | Formal Acceptance active runtime ≥7200 s | **`7320.252 s`** | **PASS** |
| AC-07 | 5 reconnect PASS | 5/5（§19） | **PASS** |
| AC-08 | 2 STALE→FRESH PASS | 2/2（§20） | **PASS** |
| AC-09 | fresh-process restart PASS | pid `11720 → 768`，Recovery 15 步（§21） | **PASS** |
| AC-10 | Witness A PASS | `f01_plan_ttl_expired_while_position_open` 等 9 项全 true（§12） | **PASS** |
| AC-11 | Witness B PASS | snapshot 前后恒为 Plan A（§11） | **PASS** |
| AC-12 | Behavioral discriminating-price evidence PASS | bid `73884.46625` ∈ (StopA, StopB]，决策 **HOLD**，counterfactual **STOP_LOSS**（§10） | **PASS** |
| AC-13 | Witness C PASS | restart 后 authority = snapshot A 且 Plan B 仍 ACTIVE（§13） | **PASS** |
| AC-14 | 全部 reconciliation checkpoints PASS | 7/7 ok，`checkpoints_cover_required_points = true`（§18） | **PASS** |
| AC-15 | 无 task/socket/handle/DB leak | socket/handle 无累积，无 detached task（§22） | **PASS** |
| AC-16 | Memory Gate 按冻结 AND contract PASS | `finding = false`（growth 14.043 ≤ 64）（§23，含 P2 watch item） | **PASS** |
| AC-17 | 无 duplicate/fabricated economic fact | §25 | **PASS** |
| AC-18 | DB cleanup / residue = 0 | `leftover_databases = 0` | **PASS** |
| AC-19 | primary DB unchanged | before == after（`20260905_0004`） | **PASS** |
| AC-20 | final worktree/evidence state 可复核 | branch + commit SHA + 本 dev_log + `E:/Temp/n01-7-r01/`；raw 未入库 | **PASS** |

**§28 Completion Report 必须回答项**（逐条）：

| 问题 | 回答 |
|---|---|
| R01 CLOSED? | **YES** —— Witness B 现真实建立 `Plan A != Plan B` 并行为判别 |
| R02 targeted revalidation PASS? | **YES** —— 在 latest main `8a29306` 上跑通 migration lineage + 371 passed + Probe + 正式 2h |
| Plan A ID? | `plan_7d212f0ce53054e676a6e30c`（v1） |
| Plan B ID? | `plan_f9c9560e6a5d22319a490a28`（v2） |
| Are IDs different? | **YES** |
| Are stops different? | **YES**（`72932.355` vs `74836.5775`） |
| Did Plan B remain ACTIVE? | **YES**（`durable_active_plan.expired = false`，重启时仍 ACTIVE） |
| Did Position snapshot remain A? | **YES**（before == after，恒为 Plan A） |
| Did discriminating quote follow A? | **YES**（决策 `HOLD`，未触发 exit；counterfactual 证明若用 B 会 `STOP_LOSS`） |
| Was unauthorized replacement absent? | **YES**（无 successor commit，snapshot 未变，无新 order/fill） |
| Did restart restore snapshot authority? | **YES**（authority = snapshot A，`protection_updated_at` 保持原值） |
| Formal active duration? | **`7320.252 s`**（≥7200） |
| Latest-main SHA? | **`8a29306d904223f03408fe55538ba6cb05222f15`** |
| Migration head? | **`20260913_0009`**（单 head；`20260912_0006` 为 ancestor） |
| Did main drift during run? | **NO** |
| Production Code Changed? | **NO** |
| N01-8 ready after review? | **不由本批判定** —— 本批只交 `VALIDATED / READY FOR INDEPENDENT RE-REVIEW`；是否启动 N01-8 属 Independent Re-Review / Human 决策；本批**未**启动 N01-8 |

## 28. Result

**`VALIDATED / READY FOR INDEPENDENT RE-REVIEW`**（状态（Validation 完成时）；2026-09-14
Human Acceptance = `CONFIRMED` + Final Acceptance Closeout 后，本批最终状态为
**`N01-7-R01 = ACCEPTED / COMPLETE`**、**`N01-7 = ACCEPTED / COMPLETE`** —— 见 §32）

- R01 = CLOSED（真实 Witness B，`Plan A != Plan B`，行为判别 + 反证齐备）；
- R02 = targeted revalidation PASS（latest main `8a29306`，migration `20260913_0009`，371 passed）；
- 正式 Run = 单轮全新 `7320.252 s`，**84/84 checks true**，所有 failure 列表为空；
- **非** `BLOCKED / FINDING CONFIRMED`（未发现 PRODUCT DEFECT）；
- **非** `INVALIDATED BY ENVIRONMENT`（primary 库 before == after，residue 0，无外来写者污染）。

## 29. Remaining / Known Risks

1. 🚩 **P2（Memory slope）**：`second_half_trend = 16.02 MiB/h > 5.0`，再次单支越线（上轮 `5.255`）；
   `finding = false` 仅因 growth 未过 64 MiB。**不得**据此宣称内存无问题；建议作为 N01-8 Watch Item。
2. ℹ️ **无 external monitor**（§20 可选）：本 Run 缺少进程外 cross-check；Acceptance basis（harness
   RSS）不变，故非 blocker。
3. ℹ️ **`§11` 加分证据未做**：successor snapshot atomic commit 前 A / 后 B 的对照属"加分证据"，
   本批未执行（硬要求已由 Witness B 真实执行满足）。
4. ℹ️ **基线漂移风险**：本轮结论**仅覆盖** `8a29306`。若 Re-Review 期间 main 继续前进，按 §22
   由 Re-Review 决定是否需 latest-main targeted revalidation。
5. ℹ️ **环境遗留**：隔离容器 `marketpulse-n01-7-r01-pg`（`127.0.0.1:5434`）与 worktree 内
   gitignored `.env`（指向 5434）**保留**，供 Reviewer 复现；释放方式
   `docker rm -f -v marketpulse-n01-7-r01-pg`。⚠️ 副作用：该 worktree 内跑 pytest 会走 5434。
   另：`marketpulse-se-fix-02-pg`（`127.0.0.1:5437`）仍 Up，系上一 SE 窗口有意遗留，本批**未**触碰。

## 30. Evidence

| 路径 | 内容 |
|---|---|
| `E:/Temp/n01-7-r01/acceptance_raw.json` | 正式 Run 完整报告（唯一权威） |
| `E:/Temp/n01-7-r01/n01-7-r01-logs/` | phase first/second stdout、raw、progress、checkpoints |
| `E:/Temp/n01-7-r01/probe2_raw.json` / `probe_raw.json` | Probe #2（OK）/ #1（FAIL）原始输出 |
| `E:/Temp/n01-7-r01/probe2_stdout.txt` | Probe #2 compact stdout |
| `E:/Temp/n01-7-r01-docs/` | 本批工作区：任务卡全文、核验/报告脚本、临时 helper |
| `E:/Temp/n01-7-medium/` | **旧 N01-7 evidence，只读保留，未被覆盖** |

> 仓库内**只**保存本 dev_log 的可复核摘要 / 指纹 / 路径 / 结论；`E:/Temp` raw artifact
> **不**进入 Git（任务书 §26 + 用户 scope 决策）。

## 31. Context For Next AI

- 本批 Task Base = `8a29306d904223f03408fe55538ba6cb05222f15`；结论**仅覆盖**该 SHA，
  以及运行结束时重新读到的 `origin/main`（见 §17 BASELINE DRIFT）。
- 复现入口：worktree `E:\Documents\MarketPulse-AI-n01-7-r01`；
  `py -3.14 scripts/verify_n01_7_medium_soak.py`（default acceptance，7320 s）；
  probe 用 `--probe`（240 s × 2）。
- 隔离要求：`.env` 必须指向任务专属容器 `marketpulse-n01-7-r01-pg` @ `127.0.0.1:5434`；
  `Settings` 读 **cwd** 的 `.env`，`alembic/env.py` 优先读 `os.environ["DATABASE_URL"]`。
- **未做**：Human Acceptance、merge main、N01-8、Integrated Runtime Host、production fix、SE 改动。
  按任务书 §29 **STOP**，等 Independent Re-Review。

## 32. Human Acceptance + Final Main Integration Closeout（2026-09-14，追加章节）

本批最终收尾（**只追加**，不改动上述历史条目）：

- **Human Acceptance = `CONFIRMED`**；**Independent Re-Review =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`**。
- **Human-Accepted reviewed candidate = `559f14be1fb89df58c11dfbea737eba4ac30421e`**
  （branch `n01-7-r01-witness-b-latest-main`，远端同 SHA，**未被改写**）。
- **Accepted Main before** = `8a29306d904223f03408fe55538ba6cb05222f15`；
  **Accepted Main after** = docs/state-only Final Acceptance Closeout Commit。
- **集成方法 = `FAST-FORWARD ONLY`**：`8a29306 → 559f14b → docs-only closeout`；无 merge commit
  到 `main` / squash / rebase / cherry-pick / force push；reviewed candidate identity 不变。
- Closeout 为 docs/state-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`；`alembic heads` 单 head
  `20260913_0009`，`20260912_0006` / `20260913_0007` / `20260913_0008` / `20260913_0009`
  的 revision identity 未被重写。
- **最终状态**：`N01-7-R01 = ACCEPTED / COMPLETE`；`N01-7 = ACCEPTED / COMPLETE`；
  `N01 overall` 仍 `NOT ACCEPTED`；`N01-8` 与 `Integrated Runtime Host` 仍 `NOT STARTED`。
- 🚩 **P2 Watch Item 保留**：`N01-7-R01-RR-P2-01`（Memory Operational Watch / Bounded Retention
  Growth；slope `≈16.02 MiB/h` > `5.0`，`total_growth ≈14.043 MiB ≤ 64` ⇒ `finding = false`，
  Acceptance Gate = PASS）**必须**留给未来 `N01-8`；**不得**写 `memory resolved` /
  `memory is fine` / `no memory concern`。
- ⚠️ FIX/收尾语义：N01-7 Accepted **≠** `N01 overall` Accepted，也**≠** N01-8 MAY START。
  详见 `dev_log/2026-09-14-n01-7-final-acceptance-closeout.md`。
