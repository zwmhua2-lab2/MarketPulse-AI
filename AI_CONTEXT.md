# AI_CONTEXT — MarketPulse AI 上下文入口

> 本文件是 AI 开发工作的**上下文入口（Context Index）**，不是项目 Spec 的复制。
> 任何新的 AI / Codex 窗口应先读本文件建立上下文，再按下方 Source of Truth 顺序读取真实事实。
> 本文件是入口和索引，**不是**比代码或已批准决策更高的事实源。
> **产品级长期需求基线见 [`PRODUCT_REQUIREMENTS.md`](./PRODUCT_REQUIREMENTS.md)**（Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction）。本文件（AI_CONTEXT）是其下的上下文入口索引，不重复其产品级内容；若二者冲突，以 `PRODUCT_REQUIREMENTS.md` 的产品级定位与 `DECISIONS.md` 的已批准冻结为准。

## 1. Project Identity

| 字段 | 值 |
|---|---|
| Project | MarketPulse AI（BTC/ETH 量化纸面交易终端，Modular Monolith） |
| Current Acceptance Group | SE-02D — Family Aggregation / Expectancy — ACCEPTED / COMPLETE |
| Accepted Main Source | Git `main` / `origin/main`；须在任务 preflight 按 CIP-02 实时读取，不以文档静态 SHA 为准 |
| Current State | `SE-ARCH-FIX-02 = ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance = `APPROVED` + Final Main Integration Closeout，已 fast-forward only 收编 `main`；Human-Accepted reviewed candidate = `15da7c1`；Implementation = `4c83582`）；`SE-ARCH-FIX-01 = ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance = `APPROVED` + Final Main Integration Closeout；reviewed candidate = `1e2738b`）；`SE-02A = ACCEPTED / COMPLETE`；`SE-02B = ACCEPTED / COMPLETE`；**`SE-02C = ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate = `7bb3835d6b14a3fc86becff1881c7f53f1acd567`（branch `se-02c-fix-02-stable-read-snapshot`）；`SE-02C-FIX-01` / `SE-02C-FIX-02` = `ACCEPTED / CLOSED`；集成方法 = `FAST-FORWARD ONLY`；遗留 `SE02C-R7` = P3 / NON-BLOCKING / NOT FIXED）；**`SE-02D = ACCEPTED / COMPLETE`**（`SE-02D Overall = ACCEPTED / COMPLETE`，2026-09-16 Human Acceptance = `CONFIRMED` + SE-02D Overall Final Acceptance Closeout；Overall Final Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed baseline = `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；`SE02D-OVERALL-R01-P3-01` / `SE02D-OVERALL-R01-P3-02` = `CLOSED`；`SE-02D-I01 = ACCEPTED / COMPLETE`、`SE-02D-I02 = ACCEPTED / COMPLETE`，均于 2026-09-15 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；`SE-02D-I03 = ACCEPTED / COMPLETE`，2026-09-16 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；**`SE-02D-CLOSE-D01 = ACCEPTED / COMPLETE`**，2026-09-16 Human Acceptance = `CONFIRMED`，Accepted completion conclusion = `SE-02D V1 CAPABILITY COMPLETE AFTER I03`；**`SE-02D V1` capability implementation = `COMPLETE AFTER I03`**（`I04 = NOT REQUIRED`；API / frontend / runtime consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`）；**`SE-02D-D01` Family Aggregation / Expectancy Contract（设计层）= `ACCEPTED / COMPLETE`**，2026-09-15 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout，见 §6）；`N01-C = ACCEPTED / COMPLETE`；N01-A / N01-B 与 N01 验证修复 `N01-VAL-FIX-01/02/03` 均维持 `ACCEPTED / COMPLETE`；`N01-6 = ACCEPTED / COMPLETE`（Reviewed HEAD `3f591a7`）；**`N01-7-F01 = ACCEPTED / COMPLETE`**（2026-09-13 Human Acceptance = `CONFIRMED` + Final Main Integration；reviewed candidate `7c0ea7d` @ integration merge `ddf39f2`；已 fast-forward only 收编 `main`）；**`N01-7 / N01-7-R01 = ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` + Final Main Integration Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate = `559f14be1fb89df58c11dfbea737eba4ac30421e`（branch `n01-7-r01-witness-b-latest-main`）；集成方法 = `FAST-FORWARD ONLY`）；🚩 遗留 P2 Watch Item `N01-7-R01-RR-P2-01`（Memory Operational Watch / Bounded Retention Growth，slope `≈16.02 MiB/h` > `5.0`、`total_growth ≈14.043 MiB ≤ 64` ⇒ `finding = false`，Acceptance Gate = PASS）**已由 `N01-8` 继续观察并保持开启（`REMAINS`）**（`N01-8` 冻结 AND 门 Formal Finding = `false`；本 Run `RSS growth 77.711 MiB` > `64`、second-half slope `−0.639369 MiB/h`；不得写 `memory resolved` / `memory is fine` / `no memory concern`）；**`N01-8 = ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate = `d9306ada663a5cacb86bee26218e298169d82e6b`（branch `n01-8-12h-extended-soak`）；单轮 `total_active 44401.217 s`、99/99 aggregate checks True、Baseline Drift = `NO MATERIAL IMPACT`、Targeted Revalidation / Full Rerun = `NOT REQUIRED`；集成方法 = `FAST-FORWARD ONLY`）；Integrated Runtime Host 仍 `NOT STARTED`；**N01 overall = `ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` + N01 Overall Final Acceptance Closeout；Overall Final Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS` / NON-BLOCKING；`N01-9 = NOT REQUIRED / NOT CREATED`） |
| Last Accepted Group | SE-02D — Family Aggregation / Expectancy |
| Current Group Branch | `se-02d-overall-final-acceptance-closeout`（SE-02D-OVERALL-FINAL｜Overall Final
  Acceptance Closeout + P3 Documentation Reconciliation；base = Human-Accepted reviewed baseline
  `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；docs/state-only closeout commit，已 fast-forward
  only 收编 `main`）；`se-02d-close-d01-final-acceptance`（SE-02D-CLOSE-D01-FINAL；base = Human-Accepted candidate `a9e615726ee964c02a72ea6cbff490d3d74e08f7`；docs/state-only closeout commit，已 fast-forward only 收编 `main`）；候选分支 `design/se-02d-close-d01-v1-completion-boundary` @ `a9e6157` 保持 immutable（远端未移动，未追加 acceptance commit）；`se-02c-final-acceptance-closeout`（SE-02C-FINAL；base = immutable reviewed candidate `7bb3835d6b14a3fc86becff1881c7f53f1acd567`；docs/state-only closeout commit，已 fast-forward only 收编 `main`）；reviewed candidate branch `se-02c-fix-02-stable-read-snapshot` @ `7bb3835` 保持 immutable（远端未移动）；Fix-01 branch `se-02c-fix-01-review-blockers` @ `2f986827` 保持 immutable；原候选 `se-02c-forward-outcome-calculator` @ `be3aa6c` 保持 immutable；已验收 lineage `n01-7-r01-witness-b-latest-main` 等不变 |

- G1–G4 acceptance 状态：`ACCEPTED` / `ACCEPTED` / `ACCEPTED` / `ACCEPTED`。
- G5-0 / G5-1 / G5-2 / G5-3 / G5-4 acceptance 状态：`ACCEPTED`。
- G5 overall = `ACCEPTED / COMPLETE`。
- **PRE-01A-D1 = `ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` + Final
  Acceptance Closeout；Independent Re-Review = `PASS`；`D1-R1` / `D1-R2` = `CLOSED`；
  Human-Accepted candidate = `e3fb721c678e2b3ca0af6fb4663f349c6a641159`（branch
  `design/pre-01a-d1-real-ai-v1-contract`，immutable）；Accepted Design artifact =
  `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`）。
  **本 Acceptance 仅接受 Real AI V1 设计本身**，不构成 Real AI implementation / activation /
  edge 或 Runtime Host 的任何进度（详见 §3 invariant 11 与 §6）。
- **PRE-01B-D1 = `ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED` + Final
  Acceptance Closeout；Independent Review = `PASS WITH NON-BLOCKING FINDINGS`；P0 = `NONE` /
  P1 = `NONE`；Human-Accepted reviewed candidate =
  `80cb2babe9f55b3a3b1dc2d3b7913a405607ac22`（branch
  `design/pre-01b-d1-runtime-host-contract`，immutable；远端同 SHA、未被移动）；
  Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`）。
  **本 Acceptance 仅接受 Integrated Runtime Host 的 Formal Design**，**不**
  构成 `Integrated Runtime Host Implementation`（仍 `NOT STARTED`）/ Real AI
  activation / live Opportunity → G3 handoff / `SE-02D` / Live Trading 的任何进度。
  Implementation carry-ins：`F-01`（`state_version_for` 必须绑定已接受的 durable
  state/version authority）/ `F-02`（safety queue capacity `64` 仅为初始可配置默认值）。
- **PRE-01B-D2 = `ACCEPTED / COMPLETE`**（2026-09-17 Human Acceptance = `CONFIRMED` + Final
  Acceptance Closeout；Independent Re-Review = `PRE-01B-D2-FIX-05 = PASS`；P0 = `NONE` /
  P1 = `NONE` / P2 = `NONE` / P3 = `NONE`；Human-Accepted reviewed candidate =
  `cce1ae7b862b038a99976c802c0985df01b35285`（branch
  `design/pre-01b-d2-fix-05-return-completion-authority`，immutable；远端同 SHA、未被移动）；
  Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`）。
  **本 Acceptance 仅接受 AdvisoryIngress / durable G2→G3 Activation Contract 的 Formal Design**，
  **不** 构成 `PRE-01B-I2` implementation（仍 `NOT STARTED / NOT AUTHORIZED BY THIS CLOSEOUT`）/
  live `G2→G3` activation / Real AI activation / Gate A / Gate B / Gate C / Live 的任何进度。
  Human Decision Pack：Pack A = `NONE`；Pack B（numeric activation settings）/ Pack C（Gate-A
  observation / sufficiency / acceptance thresholds）仍 `UNRESOLVED`。
- **`UI-V1-D01` = `ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`**（2026-09-17 Human Acceptance =
  `CONFIRMED` + Final Acceptance / Main Integration Closeout；Independent Final Repository
  Review = `PASS`；P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NONE`；Human-Accepted /
  Reviewer-approved final candidate = `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4`（branch
  `design/ui-v1-d01-final-doc-fix-02`，immutable；远端同 SHA、未被移动）；Accepted Design
  artifact = `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`，Artifact
  status = `ACCEPTED / FROZEN`）。**本 Acceptance 仅接受 MarketPulse UI V1 Formal Design**，
  **不**构成 UI implementation（该句为 UI-V1-D01 收尾时；Frontend Foundation 其后已于
  2026-09-17 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`，正式业务页面仍 `NOT STARTED`，
  见 §6）/ Product Read API implementation /
  `UI-F01` / `UI-RD01` / `PRE-01B-I2` implementation / live `G2→G3` activation / Real AI
  activation / Gate A / Gate B / Gate C / Live 的任何进度（见 §6）。
- **`UI-F01-I01`（Frontend Foundation）= `ACCEPTED / COMPLETE`；`UI-F01 = ACCEPTED / COMPLETE`**
  （2026-09-17 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Initial
  Review = `FAIL — FIX REQUIRED`（Finding `UI-F01-I01-R1`）→ FIX `UI-F01-I01-FIX-01` =
  `ACCEPTED / CLOSED` → Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Final
  Re-Review severity：P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NON-BLOCKING ONLY`；
  `UI-F01-I01-R1` = `CLOSED`；Human-Accepted reviewed candidate =
  `ecc21356851f7deca8fd55ea086ec1007b0675d4`（branch
  `ui-f01-i01-fix-01-transport-error-boundary`，immutable；远端未被移动）；original
  implementation candidate = `0c9186d2d94450d39754eb40536148a73deb123c`；closeout branch =
  `ui-f01-i01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`）。
  **本 Acceptance 仅接受 Frontend Foundation 本身**：正式业务页面（五页仍为占位）= `NOT STARTED`；
  Product Read API = `NOT STARTED`；**不**构成 `UI-RD01` / `UI-I01..UI-I06` 的实现或自动授权
  （见 §6）。
- **SE-02D-D01 = `ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED` + Final
  Acceptance Closeout；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent
  Re-Review = `PASS`；`D01-R1` / `D01-R2` = `CLOSED`；`D01-R3` = `CLARIFIED / NON-BLOCKING`；
  Human-Accepted candidate = `245b068199b7e6f3d32bf67e3b00163e4804afdf`（branch
  `design/se-02d-d01-family-aggregation-expectancy`，immutable）；Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`）。
  ⚠️ 本 Acceptance **仅**接受设计契约，**不**构成 `SE-02D` production implementation
  （本句为 SE-02D-D01 收尾时；其后 `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为
  `ACCEPTED / COMPLETE`，父 `SE-02D` 当时 = `IN PROGRESS`，剩余实现当时仍 `NOT COMPLETE`；其后
  `SE-02D-CLOSE-D01` 已于 2026-09-16 经 Human Acceptance 接受 `SE-02D V1` capability 完成边界
  = `COMPLETE AFTER I03`，且 `SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall Final
  Acceptance Closeout 转 `ACCEPTED / COMPLETE`，见 §6）/
  family aggregation / expectancy 实现 / Real AI activation / `Gate C`（`NOT PASSED`）/
  `Live`（`NOT AUTHORIZED`）的任何进度（详见 §4 与 §6）。
- **SE-02D-I01 = `ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED` + Final
  Acceptance Closeout；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent
  Re-Review = `PASS`；`SE02D-I01-R1` / `R2` / `R3` = `CLOSED`；Human-Accepted reviewed
  candidate = `13b37dff4b8150dea869ba6257ae9f3df24cc1e5`（branch
  `se-02d-i01-aggregation-core`，immutable；远端同 SHA、未被移动）；集成方法 =
  `FAST-FORWARD ONLY`）。**纯确定性聚合 / 统计内核已接受**
  （`marketpulse.edge.aggregation`；**不** fold revision chain）。
- **SE-02D-I02 = `ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED`；
  Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS`；
  `SE02D-I02-R1` / `R2` / `R3` = `CLOSED`；Human-Accepted reviewed candidate =
  `9b860437b14f64192d3298d30c0204bed1b118f8`（branch
  `se-02d-i02-current-snapshot-folding`，immutable；远端同 SHA、未被移动）；集成方法 =
  `FAST-FORWARD ONLY`，latest-main content-level carry-forward）。**Current PostgreSQL
  stable-snapshot revision folding / canonical-head projection 已实现**：
  `marketpulse.edge.aggregation_snapshot` 在单个 `REPEATABLE READ` / `READ ONLY` 快照内以
  数据库 `statement_timestamp()` 作 `as_of`，折叠全量可见 Evidence / 精确 horizon Outcome
  修订链、选 canonical head、做 cross-integrity 校验，输出 `CanonicalScopeFacts` +
  revision-aware manifest（**不**调用 `aggregate()`）。
- **SE-02D-I03 = `ACCEPTED / COMPLETE`**（2026-09-16 Human Acceptance = `CONFIRMED`；
  Initial Independent Review = `FAIL — FIX REQUIRED`；`SE02D-I03-R1`（P1）= `CLOSED`；FIX-01
  Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed HEAD =
  `20a7c333abf81077c409811302331119dff485a5`（branch
  `se-02d-i03-fix-01-projection-identity-validation`，immutable；远端同 SHA、未被移动）；
  Original Reviewed Candidate = `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4`（branch
  `se-02d-i03-population-aggregate-orchestration`，immutable）；集成方法 = `FAST-FORWARD
  ONLY`）。**Population grouping + I01 `aggregate()` 编排已实现**：
  `marketpulse.edge.aggregation_orchestration` 消费一份 I02 `CurrentSnapshotProjection`，
  经 facts ↔ revision-aware manifest 一一对应完整性门（fail closed）后按完整结构
  `PopulationKey` 分组，每个 population **恰好一次** I01 `aggregate()` 调用，输出确定性有序
  `tuple[AggregationResult, ...]`（**不** own 统计 / revision folding / DB snapshot 语义 /
  新 Population Key 语义 / Measurement Signature 语义 / API & product 集成）。
- ✅ **`SE-02D Overall = ACCEPTED / COMPLETE`**（2026-09-16 Human Acceptance = `CONFIRMED` +
  SE-02D Overall Final Acceptance Closeout；Overall Final Review = `PASS WITH NON-BLOCKING
  FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed baseline =
  `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；`SE02D-OVERALL-R01-P3-01` / `P3-02` = `CLOSED`）；
  **`SE-02D V1` capability implementation = `COMPLETE AFTER I03`**（经 `SE-02D-CLOSE-D01`
  2026-09-16 Human Acceptance = `CONFIRMED` 确认）；`I04 = NOT REQUIRED FOR SE-02D V1`；**aggregate capability =
  `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`**；**API / frontend / runtime product consumer =
  `NOT REQUIRED FOR SE-02D V1 COMPLETION`**（`DEFERRED` 至未来 consumer / product / Gate C
  任务；**不存在**且**不**属 V1 完成范围，**不**写“已完成”）；**historical revision-as-of =
  `OPEN`**；**Gate C prerequisites = `OPEN`**。
- SE-ARCH-FIX-01 Stable Evidence Anchor = `ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance =
  `APPROVED`）：Second Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；
  Human-Accepted reviewed candidate = `1e2738b09a4e4a62d91cfa8a6ffd6fcec3c71a21`；
  reviewed lineage `51053757 → bdb1af2 → 513689a（true merge，未 rebase / squash / force）
  → 5ba78af → 1e2738b → Human Acceptance → Final Closeout` 完整保留；
  其 branch-local migration collision 已透明重编号为 `20260913_0007 → 20260913_0008`，而 accepted
  N01-7 `20260912_0006` 保持不变（单 head `20260913_0008`）。P2 保留项 `TEST-ISO-01` /
  `RRF-03`（`DEFERRED`）/ `RRF-04` 均 `NON-BLOCKING`。本验收**不**构成
  `SE-ARCH-FIX-02`（`NOT STARTED`）/ `SE-02C`（`BLOCKED / NOT STARTED`）/ `SE-02D` /
  Real AI Edge / Live / N01 的任何进度（括号内状态为 SE-ARCH-FIX-01 收尾时；其后
  `SE-ARCH-FIX-02` 与 `SE-02C` 均已 `ACCEPTED / COMPLETE`，`SE-02D-I01` 亦已于 2026-09-15
  经 Human Acceptance 转为 `ACCEPTED / COMPLETE`、父 `SE-02D` = `IN PROGRESS`）。详见
  `dev_log/2026-09-12-se-arch-fix-01-stable-evidence-anchor.md`
  「Human Acceptance + Final Main Integration Closeout」。

- SE-ARCH-FIX-02 Outcome Revision Chain Scope = `ACCEPTED / COMPLETE`（2026-09-13 Human
  Acceptance = `APPROVED` + Final Main Integration Closeout；Independent Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
  `15da7c1bac719d17271c7df9fcccbf80535b6d1b`，implementation `4c835828…`，branch
  `se-arch-fix-02-outcome-revision-chain-scope`；Accepted Main before = `fc61924`；已
  fast-forward only 收编 `main`）。outcome revision chain identity scope 收敛为
  `(opportunity_id, evidence_id, horizon)`：**DB 负责 scope integrity**（`uq_edge_outcome_id_scope`
  + 4 列 `fk_edge_outcome_supersedes`），**service 同时负责 scope integrity 与 revision
  adjacency**（未引入 trigger）；migration `20260913_0009` 对存量 cross-scope 行 fail-closed
  abort。**当前 migration head = `20260913_0009`（单 head）**，
  `ReplayTradingRunner.schema_head = 20260913_0009`。⚠️ FIX-02 Accepted **≠** SE-02C MAY START：
  `SE-02C` 保持 `BLOCKED / NOT STARTED`（仍需 Pre-SE-02C Re-Gate）。详见
  `dev_log/2026-09-13-se-arch-fix-02-outcome-revision-chain-scope.md`。
  （历史记录：以上为 FIX-02 收尾时的边界表述；`SE-02C` 其后已由 2026-09-13 实现窗口推进，
  并经 `SE-02C-FIX-01` / `SE-02C-FIX-02` 于 2026-09-14 Human Acceptance 转为
  `ACCEPTED / COMPLETE`，见下条。）

- SE-02C Forward Outcome Calculator = `ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance =
  `CONFIRMED` + Final Acceptance Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING
  FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
  `7bb3835d6b14a3fc86becff1881c7f53f1acd567`（branch `se-02c-fix-02-stable-read-snapshot`）；
  `SE-02C-FIX-01` / `SE-02C-FIX-02` = `ACCEPTED / CLOSED`；集成方法 = `FAST-FORWARD ONLY`；
  遗留 `SE02C-R7` = P3 / NON-BLOCKING / NOT FIXED）。实现落地于 2026-09-13 实现 + 验证窗口
  （原 branch `se-02c-forward-outcome-calculator` @ `be3aa6c`，base `8a29306`，worktree
  `E:\Documents\MarketPulse-AI-se-02c`；当时**未** merge `main`、**未** push `main`、
  **未**自行 Acceptance；前置授权 = 外部任务书声明的 Pre-SE-02C
  Re-Gate `PASS — SE-02C MAY START`）。落地：纯计算核心 `edge/forward.py`
  （冻结 V1 mid/return/MFE-MAE 公式 + 精确乘性 `SPOT_LONG_TAKER_ROUND_TRIP` 成本 +
  `due_at = evidence_at + duration` + FIX-01 anchor 参考权威 + 5 s endpoint TTL +
  仅 `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID` 终态 + `created_at` 冻结为 `due_at`）、
  durable orchestration `edge/forward_service.py`（`ForwardPathRecorder` 复用
  `record_bbo_observation`、`discover_due_scopes`、`ForwardOutcomeService` /
  `evaluate_due_outcomes`，永不写 revision > 1）、`g2/runtime.py` 最小 opt-in
  live-ingress hook。`Migration changed = NO`（单 head 仍 `20260913_0009`）。
  原窗口验证：focused `47 passed`、命名回归 `196 passed`、full backend `418 passed`；
  C-01 ～ C-29 全部 PASS。
  第一次 Independent Review = `FAIL — FIX REQUIRED`：`SE02C-R1`（>50,000 observations 被
  `MAX_FORWARD_PATH_OBSERVATIONS` 读取上限静默截断 ⇒ endpoint 可能不是真实 latest、
  MFE / MAE / `reference_return` / `executable_long_return` /
  `cost_adjusted_forward_return` 可能错误、不完整 path 仍可能落 `COMPLETE`；P1 BLOCKING）、
  `SE02C-R2`（live ingress 以 `DEFAULT_INGRESS_TRADABLE = True` 无条件把 Forward BBO 记为
  `tradable=True`，丢失真实 instrument tradable 状态；P1 BLOCKING）、`SE02C-R3`（remote
  `main` 已从 `8a29306` 推进到 `dd78a979`，旧候选不再建立于最新 Accepted Main lineage；
  P1 BLOCKING）、`SE02C-R4`（anchor-only 情况应报 `ENDPOINT_MISSING` 而非
  `ENDPOINT_STALE`：Capture Anchor 只作 reference authority，不是 Forward endpoint；
  P2 NON-BLOCKING）。
- SE-02C-FIX-01｜Review Blockers = `ACCEPTED / CLOSED`（2026-09-14 Implementation +
  Verification 窗口；该窗口收尾时状态为 `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`，
  其后经 Independent Re-Review 与 2026-09-14 Human Acceptance 转为 `ACCEPTED / CLOSED`；
  branch `se-02c-fix-01-review-blockers`，
  worktree `E:\Documents\MarketPulse-AI-se-02c-fix-01`）。Lineage：以最新 Accepted Main
  `dd78a979d128dee385c7a8ddc2254a53366af714` 为第一父系，经**真实 merge**（`git merge
  --no-ff be3aa6c…`）集成原已复审候选 `be3aa6c817582f6161ea9903f7824200b7f5c843`，两条历史
  均保留；**无** rebase / squash / cherry-pick / force push；原候选 **immutable** 未被改写。
  `Schema Changed = NO` / `Migration Added = NO`（单 head `20260913_0009`）。
  详见 `dev_log/2026-09-14-se-02c-fix-01-review-blockers.md`。

- SE-02C-FIX-02｜Stable Read Snapshot = `ACCEPTED / CLOSED`（2026-09-14 Implementation +
  Verification；该窗口收尾时状态为 `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`，其后经
  Independent Re-Review 与 2026-09-14 Human Acceptance 转为 `ACCEPTED / CLOSED`；其 tip
  `7bb3835` 即 Human-Accepted reviewed candidate；branch
  `se-02c-fix-02-stable-read-snapshot`；base / immutable Fix-01 candidate = `2f986827…`；
  Implementation SHA = `6b084595cde9c3e3257046b4694b134954923a4d`）。
  normal evaluator 以 canonical scope SHA-256 signed-int64 取得 PostgreSQL advisory xact lock，
  lock 后复查 revision-1；reference + 全 keyset pages 共享独立 `REPEATABLE READ READ ONLY`
  snapshot，coordinator 持锁至 append/commit。cursor-before/after late commit、fresh snapshot、
  two evaluator + concurrent recorder 的真实 PostgreSQL race 均通过；B 锁后 return existing，
  durable row = 1，A/B same id/digest/hash，无 conflict/revision 2。full backend `425 passed,
  1 warning`；无 schema/migration change，head/G5 schema_head 仍 `20260913_0009`。详见
  `dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md`。

⚠️ 跑 SE-02C / 任何集成测试的窗口注意：**不要导出 `DATABASE_URL`**。
`backend/alembic/env.py` 为 `os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))`
—— 环境变量优先于测试传入的 `sqlalchemy.url`，导出后会把迁移打到环境变量指向的库，
disposable 库保持空表（症状 `relation "edge_opportunity_evidence" does not exist`）。
正确姿势：`PYTHONPATH=backend/src py -3.14 -m pytest backend/tests`，仅靠 worktree 根
`.env` 提供隔离库地址。

⚠️ 新建 disposable PostgreSQL 后，**primary 库自身也必须 `alembic upgrade head`**
（2026-09-14 SE-02C-FIX-01 实测）：G5 的 `ReplayWorkspaceGuard.counts(primary)`
（`g5/replay.py:485`）会对 **primary** 库执行 `SELECT count(*) FROM <table>`，primary 空 schema
会让 G5-2 / G5-3 / G5-4 整批报 `relation "market_events" does not exist`（15 个假失败，
极易误判为代码回归）。另：`alembic` CLI 的 `script_location` 相对 **cwd** 解析 —— 须
`cd backend && py -3.14 -m alembic -c alembic.ini upgrade head`（在仓库根用
`-c backend/alembic.ini` 会报 `Path doesn't exist: alembic.`）。

- N01-7 / N01-7-R01 2-hour Medium Runtime Soak（含 Witness B Fix + Latest-Main Revalidation）
  = `ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance = `CONFIRMED` + Final Main Integration
  Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted reviewed candidate =
  `559f14be1fb89df58c11dfbea737eba4ac30421e`，branch `n01-7-r01-witness-b-latest-main`；
  Accepted Main before = `8a29306`；accepted lineage 仅 fast-forward：
  `8a29306 → 559f14b → docs/state-only Final Closeout Commit`）。验收依据：真实 OKX 公共行情 +
  一次性 disposable PostgreSQL 单轮连续 `total_active 7320.252 s`、**84/84 checks true**、
  5 次受控重连 + 2 次受控 STALE→FRESH + 7 checkpoint 全 ok + 跨进程 Recovery 15 步 +
  Witness A/B/C 全成立 + 经济不变量全绿；`production_code_unchanged = true`；shared primary
  before == after；`alembic heads` 单 head `20260913_0009`。Closeout 四项不变：
  `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO` /
  `Runtime config changed = NO`。
  - 🚩 P2 保留项 `N01-7-R01-RR-P2-01`：Memory Operational Watch / Bounded Retention Growth
    （slope `≈16.02 MiB/h` > `5.0`，`total_growth ≈14.043 MiB ≤ 64` ⇒ `finding = false`，
    Acceptance Gate = PASS）——**保留给未来 `N01-8`**，不得写 `memory resolved` /
    `memory is fine` / `no memory concern`。
- ⚠️ `N01-7` / `N01-7-R01` Accepted **≠** `N01 overall` Accepted（N01-7 收尾时尚未总体验收；
  其后 `N01 overall` 已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`，见 §6），也
  **≠** `N01-8` MAY START（N01-7 收尾时；其后 N01-8 已另行获批执行并于 2026-09-14 经 Human
  Acceptance 转 `ACCEPTED / COMPLETE`，见 §6「N01-8 12-hour Extended Runtime Soak」条目）；
  `Integrated Runtime Host` 仍 `NOT STARTED`。详见
  `dev_log/2026-09-14-n01-7-final-acceptance-closeout.md`。

## 2. Source of Truth（事实源优先级，从高到低）

1. 当前真实代码 / schema / migrations / tests
2. `PROJECT_STATE.md`
3. `DECISIONS.md`
4. `PRODUCT_REQUIREMENTS.md`（产品级长期需求基线：Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction；不覆盖 `DECISIONS.md` 的已批准冻结，也不改变本列表的 repository truth 优先级）
5. 已批准的当前 Group Spec / Acceptance Contract
6. `dev_log/` / acceptance evidence
7. `AI_CONTEXT.md`（本文件）
8. 聊天记录 / AI 历史回答

**核心原则：聊天内容不能覆盖 repository truth。** 旧聊天、模型记忆、人工转述只能作为导航信息，不能直接作为实现依据。

## 3. Frozen Architecture / Invariants（G5 不得静默修改）

以下边界已从当前 accepted repository 核实，G5 实现不得静默改变：

1. **Paper Trading only**；不启用 Live Trading。
2. **AI 为 advisory（建议层）**：AI 仅输出分析建议；Paper execution 只能由程序化 Trade Plan / Execution Intent 驱动，AI 不得直接绕过 Risk / Execution。
3. **Risk Engine 保持 authoritative**：所有风险增加动作（BUY / ADD / OPEN BUY Limit Fill）必须经过唯一程序化 `SystemRiskGate`；SELL 风险降低动作不受此限。
4. **责任边界不得被 G5 静默重构**：
   `Market Data → Scanner → Candidate/Watchlist → AI Analyst → Trade Plan → Risk Engine → Execution → Position Manager → Ledger`。
5. **SPOT / SWAP 语义不得混淆**：二者是严格不同的 market type，使用不同 `market_type` / `instrument_id`。
6. **当前 Spot Paper 能力边界不得扩大**：V1 仅支持 Spot Paper 的 LONG 风险计划；`SHORT_BIAS` 只保留分析记录，绝不产生 Short Execution。
7. **G4 Position Safety / Recovery 语义不得被回归破坏**：Operator Intent 与 System Derived State 分离；PostgreSQL 为 Restart Recovery 唯一事实源；SL/TP 为 Trigger Price；Protective Exit 一律以 Fresh Best Bid − slippage 成交；不伪造停机期间历史 Fill。
8. **`TradePlan.invalidation` = advisory text**（AI/human-readable，非 machine-executable condition；Runtime 不得解析其自然语言）。
9. **`stop_loss` = 唯一 machine-enforceable hard invalidation**。
10. **架构冻结**：Python/FastAPI/asyncio backend + React/TypeScript/Vite frontend + PostgreSQL（Docker）；Modular Monolith；默认 `LOCAL_ONLY=true`、`RUN_MODE=TEST`、监听 `127.0.0.1`；Secret 不进入 Git / Frontend / API 返回。
11. **Real AI V1 设计边界（PRE-01A-D1 ACCEPTED DESIGN，2026-09-14）**：Real AI V1 placement = `C. Trade Decision` only；`AI = Advisory`、`Deterministic System = Authority`（AI 无 repository/risk/execution/accounting/protection handle）；WITHOUT-AI selection benchmark = `ALL_ELIGIBLE_LONG_SHADOW_V1`；V1 causal claim = **Real AI Trade-Decision selection / participation edge only**（treatment = `PARTICIPATE_LONG` vs `NO_LONG`），**不得**扩展为 entry / stop / target / sizing / full `AIAnalysis` package / executed-trade edge；one `decision_invocation_id` → exactly one collision-free logical durable final decision；Single Primary Provider / No automatic fallback / No model voting；Gate A = Provider Shadow Activation、Gate B = Paper Economic Activation、Gate C = Selection / Participation Edge Evidence。指针：`docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`。

> 若后续仓库事实已明确改变上述任一边界：以仓库事实为准并报告差异，不把本文件文本当成高于 repository truth 的事实源。

## 4. Current Group Boundary

| 字段 | 值 |
|---|---|
| Current Group | SE-02D — Family Aggregation / Expectancy — `ACCEPTED / COMPLETE`（2026-09-16 Human Acceptance = `CONFIRMED` + SE-02D Overall Final Acceptance Closeout） |
| Last accepted subgroup | **N01 overall**（`ACCEPTED / COMPLETE`，2026-09-14 Human Acceptance = `CONFIRMED` + N01 Overall Final Acceptance Closeout）；SE-02C / N01-8 / N01-7 / N01-7-R01 / SE-ARCH-FIX-02 / SE-ARCH-FIX-01 / SE-02A / SE-02B / N01-6 / N01-7-F01 / N01-C / N01-A / N01-B 亦维持 `ACCEPTED / COMPLETE` |
| Next Group Design | `NOT STARTED / REQUIRES SEPARATE HUMAN-AUTHORIZED DECISION`（须另开窗口）；`SE-02D` 已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`，本收尾 **不**选择、**不**启动下一个 Acceptance Group；已明确**不**自动开始 `Integrated Runtime Host`。`N01 Overall Final Review / Acceptance` 已完成（2026-09-14；见 §6「N01 Overall Final Acceptance Closeout — ACCEPTED / COMPLETE」）；下一 Runtime 边界 = `Integrated Runtime Host`（`NOT STARTED`，须由总进度窗口另开独立获批窗口与门，**不得**自动启动） |
| Next Group name/number | `SE-02C = ACCEPTED / COMPLETE`（2026-09-14 Final Acceptance Closeout；`SE-02C-FIX-01` / `SE-02C-FIX-02` = `ACCEPTED / CLOSED`；`SE02C-R7` = P3 / NON-BLOCKING / NOT FIXED）；`SE-02D｜Family Aggregation / Expectancy = ACCEPTED / COMPLETE`（2026-09-16 Human Acceptance = `CONFIRMED` + SE-02D Overall Final Acceptance Closeout；`SE-02D-I01` / `I02` / `I03` / `CLOSE-D01` 均 = `ACCEPTED / COMPLETE`；`SE-02D V1` capability implementation = `COMPLETE AFTER I03`；`I04 = NOT REQUIRED`；**`SE-02D-D01` 设计契约 = `ACCEPTED / COMPLETE`**，2026-09-15，见 §6）；`N01-7 / N01-7-R01 = ACCEPTED / COMPLETE`（遗留 P2 `N01-7-R01-RR-P2-01` 见 §1）；`N01-8｜12-hour Extended Soak = ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Human-Accepted reviewed candidate = `d9306ada`；P2 `N01-7-R01-RR-P2-01` = `REMAINS`，见 §6）；Integrated Runtime Host = `NOT STARTED`；`SE-ARCH-FIX-02 = ACCEPTED / COMPLETE` |

- G4 **没有**提前实现完整 Replay / ReplayClock Engine。
- 仓库中仅存在：`Clock` Protocol 的 `ReplayClock` 实现（`backend/src/marketpulse/clock.py`）与 `RunMode.REPLAY` 枚举（`config.py`）——这是既有 Clock 边界，**不是**完整回放引擎。
- 完整 Replay 工作从 G5 才允许开始。
- **G5-0 本身仍然禁止实现 Replay。**

## 5. Required Context Pack（每个任务开始前必须建立）

每个执行任务开始前必须知道：

- Group / Task / Acceptance Batch
- Accepted Main SHA + Task Base SHA
- Current Branch
- Current Scope / Out of Scope
- 已批准的 Spec / Acceptance Contract
- 相关 frozen decisions（见 `DECISIONS.md`）
- 相关架构 invariants（见本文件第 3 节）
- 必需 source files / docs
- Acceptance Criteria

**禁止依赖**：「上一个聊天应该知道」「前一个 AI 说已经做了」「我记得这个功能是……」。

## 6. Next Step Entry（下一步工作入口）

### UI-F01-I01 Frontend Foundation — ACCEPTED / COMPLETE

- 任务：`UI-F01-I01`｜Frontend Foundation（IMPLEMENTATION + VERIFICATION；**非** New Design、
  **非** Product Read API、**非** `UI-RD01`、**非** 业务页面实现、**非** `PRE-01B-I2`、
  **非** Real AI activation）。
- 状态：**`UI-F01-I01 = ACCEPTED / COMPLETE`**；**`UI-F01 = ACCEPTED / COMPLETE`**（2026-09-17
  Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Initial Review =
  `FAIL — FIX REQUIRED`（Finding `UI-F01-I01-R1`，即原批 `R-02`）→ FIX `UI-F01-I01-FIX-01` =
  `ACCEPTED / CLOSED` → Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Final
  Re-Review severity：P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NON-BLOCKING ONLY`）。
  Human-Accepted reviewed candidate = `ecc21356851f7deca8fd55ea086ec1007b0675d4`（branch
  `ui-f01-i01-fix-01-transport-error-boundary`，immutable；远端未被移动）；original
  implementation candidate = `0c9186d2d94450d39754eb40536148a73deb123c`（immutable）；closeout
  branch = `ui-f01-i01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`；Final
  Regression（收尾前在候选 lineage 上重跑，全部 exit 0）= `typecheck` / `7 files / 44 tests` /
  `build` / `check:api-drift`。**本 Acceptance 仅接受 Frontend Foundation 本身。**
- Task Base（任务卡声明）= `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`；执行前**实读**远端真值
  `git ls-remote origin refs/heads/main` = 同 SHA ⇒ **无** baseline drift。task branch =
  `ui-f01-i01-frontend-foundation`，**未** merge `main`。
- 已实现（`frontend/**`）：`react-router` 声明式路由（顶层 IA **恰好五页**、**无**顶层 `/ai`、
  `/login` = Auth Shell 非第六页、五页**仅**占位）；单一 application `QueryClient`（无默认轮询 /
  无全局 refetch interval；`401` 与普通 `4xx` 不重试、network 与 `5xx` 有界重试）；`openapi-fetch`
  typed client（**未**引入 Axios、**未**自建 HTTP 框架；同源相对 `/api/...`，**不**硬编码后端
  host）；唯一 Auth Session Boundary（bearer 仅存 `sessionStorage`、**密码永不持久化**、login
  `401` 保持凭据错误且无重定向循环、受保护 `401` 清 session + 清已认证 Query cache + 保留原定
  路由）；Vite 开发 `/api` proxy → `127.0.0.1:8000`（**不** rewrite、**未**引入宽泛 CORS）；
  `/ready` `503` = 权威 NOT READY（保留 body、**不是**网络故障、**不**被重试）；OpenAPI 生成纪律
  恢复（`generate:api` 离线可复现、`check:api-drift` 漂移即失败）；Vitest + jsdom + RTL + MSW
  harness。
- 真实验证（全部 exit 0）：`npm ci`；`npm run typecheck`；`npm run test:run` = **7 files /
  37 tests PASS**；`npm run build`；`npm run generate:api`；`npm run check:api-drift`。
- ⚠️ **本条目更新上文 `UI-V1-D01` 条目中的 `Implementation = NOT STARTED` 与
  `前端库选型 = DEFERRED 至 UI-F01` 两项状态**：前端 Foundation 已实现并已于 2026-09-17 经
  Human Acceptance = `CONFIRMED` + Final Acceptance Closeout 转为 `ACCEPTED / COMPLETE`；
  库选型已按任务卡冻结决策落地（见「UI-F01-I01 Result」）。`UI-V1-D01` 条目其余内容
  （设计本身、五页 IA、权威边界、非声称清单）**仍然有效**。
- 明确非声称：业务页面 = 仍为占位 `NOT STARTED`；Product Read API = `NOT STARTED`；
  `PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` =
  `NOT ACTIVE`；Forward Outcome runtime integration = `NOT INTEGRATED`；`Gate C` =
  `NOT PASSED`；`Live` = `NOT AUTHORIZED`；Trading Edge = **未证明**。
- 边界保持：Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS / NON-BLOCKING`（**禁止**写
  `memory resolved` / `memory is fine` / `no memory concern`）。
- 详见 `dev_log/2026-09-17-ui-f01-i01-frontend-foundation.md`（Implementation）、
  `dev_log/2026-09-17-ui-f01-i01-fix-01-transport-error-boundary.md`（FIX-01）与
  `dev_log/2026-09-17-ui-f01-i01-final-acceptance-closeout.md`（Final Acceptance Closeout）；
  状态摘要见 `PROJECT_STATE.md`「UI-F01-I01 Result」/「UI-F01-I01 Final Acceptance Closeout
  Result」；决策压缩见 `DECISIONS.md`「UI-F01-I01 V1」。
- 下一计划正式设计任务 = `UI-RD01`（Product Read API Formal Design）→ `UI-I01..UI-I06`；
  `UI-RD01` = **`NOT STARTED` / `NOT AUTOMATICALLY AUTHORIZED`**（本 Acceptance 与本收尾**均不**
  实现、**不**自动授权它们）；任何后续设计 / 实现均需另开独立获批窗口。

- `UI-F01-I01-FIX-01`｜Transport Error Boundary Closure = **ACCEPTED / CLOSED**（2026-09-17 Human
  Acceptance = `CONFIRMED` + Final Acceptance Closeout；关闭独立复审 Finding `UI-F01-I01-R1` =
  原批 `R-02` 风险；reviewed candidate
  `0c9186d2d94450d39754eb40536148a73deb123c` **未**重写、保留为历史证据；Fix branch =
  `ui-f01-i01-fix-01-transport-error-boundary`，**未** merge `main`；实测远端 `main` =
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13` ⇒ **无** baseline drift）。通用网络 / HTTP 错误归一化
  现由 `frontend/src/api/transport.ts` **单点拥有**：`requestData()` → network = `NetworkError`、
  `401` = `UnauthorizedError`、其他非 2xx = `HttpError`（status / body 保留）、2xx + 不可解释 body
  = `UnexpectedResponse`；`/ready` `503` 仍是**唯一**显式例外（权威 NOT READY、body 保留、**不是**
  `HttpError` / `NetworkError`、**不**被重试），并已由新用例反向固定（非 `/ready` 端点的 `503` =
  普通 `HttpError`）。真实门（全部 exit 0）：`typecheck` / `test:run` = **7 files / 44 tests
  PASS**（既有 37 **未**削弱 + 新增 7）/ `build` / `check:api-drift`；另以 3 个注入式探针证明新
  覆盖**有牙齿**（已逐字节复原）。改动面 = `frontend/src/api/**` 4 个文件 + 最小状态文档同步；
  `frontend/package.json` / `frontend/package-lock.json` / `backend/**` / schema / migration /
  `frontend/src/auth/**` / `frontend/src/app/**` = **ZERO CHANGE**；`react` / `react-dom` 按
  lockfile 实测 = `19.3.0`。**该批交付时状态（Fix 完成时）= IMPLEMENTED / READY FOR INDEPENDENT
  RE-REVIEW；其后已于 2026-09-17 经 Independent Re-Review 与 Human Acceptance 转为 `ACCEPTED /
  CLOSED`**；**不**构成 `UI-RD01` / `UI-I01..UI-I06` 的授权。详见
  `dev_log/2026-09-17-ui-f01-i01-fix-01-transport-error-boundary.md`。

### UI-V1-D01 MarketPulse UI V1 Formal Design — ACCEPTED / FROZEN / REPOSITORY-INTEGRATED

- 任务：`UI-V1-D01-FINAL-DOC-01`｜MarketPulse UI V1 Formal Design — Repository Persistence
  （DOCS / STATE ONLY；**非** New Design、**非** 实现、**非** `UI-F01` / `UI-RD01`、
  **非** `PRE-01B-I2`、**非** Real AI activation）。
- 状态：**`UI-V1-D01 = ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`**（2026-09-17 Human
  Acceptance = `CONFIRMED` + Final Acceptance / Main Integration Closeout；
  `UI-V1-D01-FIX-01｜Formal Contract Closure` = `INCLUDED / CLOSED`）。
  Independent Final Review = `PASS — READY FOR FORMAL FREEZE`；Independent Final Repository
  Review = `PASS`；P0 = `NONE`、P1 = `NONE`、P2 = `NONE`、P3 = `NONE`。repository persistence
  `UI-V1-D01-FINAL-DOC-01` = `COMPLETE`（documentation fixes `FIX-01` / `FIX-02` = `COMPLETE`）；
  Human-Accepted / Reviewer-approved final candidate =
  `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4`（branch `design/ui-v1-d01-final-doc-fix-02`，
  immutable；远端同 SHA、未被移动）；closeout branch = `ui-v1-d01-final-acceptance-closeout`；
  集成方法 = `FAST-FORWARD ONLY`。
- **Formal artifact**：`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`
  （Artifact status = `ACCEPTED / FROZEN`）。
- **Implementation（UI-V1-D01 收尾时）= `NOT STARTED`**（当时前端仅 Group 1 占位脚手架；
  `frontend/vite.config.ts` 当时尚无 `/api` proxy）；Product Read API implementation =
  `NOT STARTED`；前端库选型 = `DEFERRED` 至 `UI-F01`。**其后 Frontend Foundation 已于
  2026-09-17 经 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout 转为
  `ACCEPTED / COMPLETE`（`UI-F01 = ACCEPTED / COMPLETE`）；正式业务页面 / Product Read API
  仍 `NOT STARTED`**（见上「UI-F01-I01 Frontend Foundation — ACCEPTED / COMPLETE」）。
- 产品定位 = **Read-Only Paper Trading Operations & Evidence Terminal**（只读纸面交易运维与
  证据终端，**非**手工交易终端 / **非**运行时控制面板 / **非** Live Trading UI / **非** AI
  自主控制界面）；顶层 IA = **恰好五页**（总览 / 市场与机会 / 策略研究 / 交易与仓位 / 系统），
  **AI 无独立顶层页**。
- 下一计划设计任务（UI-V1-D01 收尾时）：`UI-F01`（Frontend Foundation）→ `UI-RD01`（Product
  Read API Formal Design）序列；`UI-F01` 其后已于 2026-09-17 经 Human Acceptance 转为
  `ACCEPTED / COMPLETE`，故当前下一计划正式设计任务 = `UI-RD01`；**本 docs 任务、UI-V1-D01
  Final Acceptance Closeout 与 UI-F01-I01 Final Acceptance Closeout 均不授权、也不实现**
  `UI-RD01`；任何后续设计 / 实现均需另开独立获批窗口。
- ⚠️ 本 Acceptance **只**接受 Formal Design，**不**证明 / 不授权：UI 实现、`PRE-01B-I2`
  implementation、live `G2→G3` activation、Real AI activation、Gate A / Gate B activation、
  `Gate C`（`NOT PASSED`）、`Live`（`NOT AUTHORIZED`）、profitability / edge。
- 边界保持：`N01 overall = ACCEPTED / COMPLETE`；Memory P2
  `N01-7-R01-RR-P2-01` = `REMAINS / NON-BLOCKING`（**禁止**写 `memory resolved` /
  `memory is fine` / `no memory concern`）；Real AI = `NOT ACTIVATED`；live G2→G3 =
  `NOT ACTIVE`；Live Trading = `DISABLED`。
- 详见 `dev_log/2026-09-17-ui-v1-d01-formal-design-freeze.md`（Repository Persistence）、
  `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-01.md`（FIX-01）、
  `dev_log/2026-09-17-ui-v1-d01-final-doc-fix-02.md`（FIX-02）与
  `dev_log/2026-09-17-ui-v1-d01-final-acceptance-closeout.md`（Final Acceptance Closeout）。

### SE-02D-I01 Deterministic Aggregation Core — ACCEPTED / COMPLETE

### SE-02D Overall Final Acceptance Closeout — ACCEPTED / COMPLETE

- 任务：`SE-02D-OVERALL-FINAL`｜SE-02D Overall Final Acceptance Closeout + P3 Documentation
  Reconciliation + Fast-Forward Main Integration（docs/state-only；**非**新实现、**非**新
  Design、**非**新 Review、**非** I04、**非** Gate C、**非** Live）。
- Overall Final Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`
  （P0 = `NONE` / P1 = `NONE` / P2 = `NONE`；P3 = `SE02D-OVERALL-R01-P3-01` /
  `SE02D-OVERALL-R01-P3-02`）。
- **Human Acceptance = `CONFIRMED — 2026-09-16`**；Human-Accepted reviewed baseline =
  `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`（该 reviewed baseline commit 本身为 immutable
  Git evidence，**未**被重建或改写）；closeout branch =
  `se-02d-overall-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`。
- **最终状态：`SE-02D = ACCEPTED / COMPLETE`；`SE-02D Overall = ACCEPTED / COMPLETE`。**
  accepted lineage（均 `ACCEPTED / COMPLETE`）：`SE-02D-D01` / `SE-02D-I01` / `SE-02D-I02` /
  `SE-02D-I03` / `SE-02D-CLOSE-D01`；`SE-02D V1` capability implementation =
  `COMPLETE AFTER I03`；`I04 = NOT REQUIRED FOR SE-02D V1`。
- **Review 继承证据（来自 Human-Accepted baseline，非本收尾实测）**：I01 `108 passed`、
  I02 `44 passed`、I03 `57 passed`、合并 `209 passed`；本收尾另行实测复跑，证据分列。
- P3 closure：`SE02D-OVERALL-R01-P3-01`（陈旧 `marketpulse.edge` package docstring）=
  `CLOSED BY OVERALL FINAL CLOSEOUT`；`SE02D-OVERALL-R01-P3-02`（`PRODUCT_REQUIREMENTS.md` /
  `AI_CONTEXT.md` / `PROJECT_STATE.md` 陈旧 capability / group metadata）= `CLOSED`。
  两者均为 documentation / metadata finding，在 Human Acceptance 时为 `NON-BLOCKING`。
  **未**发现 P0 / P1 / P2 finding。
- P3-02 capability 调和真值：**Family-level current-snapshot Forward Outcome Expectancy =
  `SUPPORTED / ACCEPTED via SE-02D V1`**；**不**声称 Trading Edge / executed-trade edge /
  Real AI edge / `Gate C` PASS / generic strategy profitability 已证明。
- 边界：historical arbitrary revision-as-of = `OPEN / NOT SUPPORTED / FUTURE PREREQUISITE`；
  experiment / pair / arm identity = `OPEN GATE C PREREQUISITE`；arm-level selection
  Expectancy / delta = `FUTURE CONSUMER`；durable regime identity / criteria = `OPEN GATE C
  PREREQUISITE`；Gate C immutable evidence artifact retention = `FUTURE GATE C EVIDENCE TASK`；
  Real AI = `NOT AUTHORIZED / NOT ACTIVATED`；`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；
  `KEEP / DOWNWEIGHT / KILL = NOT OWNED BY SE-02D V1`。
- 不变量：`SE-02D ACCEPTED / COMPLETE` **≠** `Gate C PASS`；`Gate C PASS` **≠** `Live`
  授权；`SE-02D Expectancy capability` **≠** Trading Edge Proof。
- 下一 Acceptance Group：`NOT STARTED / REQUIRES SEPARATE HUMAN-AUTHORIZED DECISION`（本收尾
  **不**选择、**不**启动）。
- 详见 `dev_log/2026-09-16-se-02d-overall-final-acceptance-closeout.md`。


- 任务：`SE-02D-I01`｜Deterministic Aggregation Core → `SE-02D-I01-FINAL`｜Human-Accepted Final
  Acceptance Closeout / State Sync / Main Integration（docs/state-only；**非**新实现、**非**
  新 Review、**非** I02、**非** DB 实现、**非** Gate C、**非** Live）。
- 状态：**`SE-02D-I01 = ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED`）；
  Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS`；
  `SE02D-I01-R1` / `R2` / `R3` = `CLOSED`。
- **Human-Accepted reviewed candidate = `13b37dff4b8150dea869ba6257ae9f3df24cc1e5`**
  （branch `se-02d-i01-aggregation-core`，immutable evidence pointer；远端未被移动）；
  closeout branch = `se-02d-i01-final-acceptance-closeout`；Accepted Main before =
  `f887981d18fd7fc696d99cde702d0fec3e72a16c`；集成方法 = `FAST-FORWARD ONLY`。
- 已接受范围：**pure deterministic aggregation / statistics core**（population key /
  measurement signature / maturity / coverage / expectancy / descriptive statistics /
  overlap clustering / deterministic cluster bootstrap / sufficiency / LOCO / tail evidence /
  manifest diagnostics / deterministic fingerprint；**无** KEEP / DOWNWEIGHT / KILL、
  **无** economic threshold、**无** new production dependency）。I01 **不** fold revision
  chain —— 它消费已 canonicalize 的 scope facts。
- ⚠️ **`I01 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I01 收尾时；其后 `SE-02D Overall` 已于
  2026-09-16 转 `ACCEPTED / COMPLETE`）：**PostgreSQL loading / full Evidence &
  Outcome revision-chain discovery / canonical head selection from DB / `REPEATABLE READ`
  current-snapshot orchestration / final revision manifest construction from DB** 已于
  **`SE-02D-I02`** 实现并验收（见下）；**population grouping + 调用 I01 `aggregate()`** 已于
  **`SE-02D-I03`** 实现并验收（见下）；`SE-02D V1` capability 完成边界其后已由
  **`SE-02D-CLOSE-D01`**（2026-09-16 Human Acceptance = `CONFIRMED`）接受为
  `COMPLETE AFTER I03`（见下）：aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 +
  I03`；API / frontend / runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`；
  historical revision-as-of 仍 `OPEN`；`SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall
  Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`。
- 三项独立 prerequisite 仍 `OPEN`：**historical revision-as-of**、**experiment/pair/arm
  identity**、**durable regime**。`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；
  Real AI = `NOT ACTIVATED`；Memory P2 `N01-7-R01-RR-P2-01` 保持
  `REMAINS / NON-BLOCKING`。
- 详见 `dev_log/2026-09-15-se-02d-i01-final-acceptance-closeout.md` 与
  `dev_log/2026-09-15-se-02d-i01-aggregation-core.md`。

### SE-02D-I02 Current-Snapshot Revision Folding — ACCEPTED / COMPLETE

- 任务：`SE-02D-I02`｜Current-Snapshot Revision Folding → `SE-02D-I02-FINAL`｜Latest-Main
  Acceptance Reconciliation / State Sync / Main Integration（docs/state-only；**非**新实现、
  **非**新 Review、**非** I03、**非** Gate C、**非** Live）。
- 状态：**`SE-02D-I02 = ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED`）；
  Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS`；
  `SE02D-I02-R1` / `R2` / `R3` = `CLOSED`。
- **Human-Accepted reviewed candidate = `9b860437b14f64192d3298d30c0204bed1b118f8`**
  （branch `se-02d-i02-current-snapshot-folding`，immutable evidence pointer；远端未被移动）；
  reconciliation branch = `se-02d-i02-final-acceptance-reconciliation`（base = latest `main`
  `664207a9…`）；集成方法 = `FAST-FORWARD ONLY`（content-level carry-forward）。
- 已接受范围：**current PostgreSQL stable-snapshot revision folding / canonical-head
  projection**（`marketpulse.edge.aggregation_snapshot`）—— 单个 `REPEATABLE READ` /
  `READ ONLY` 快照拥有整个 projection；`as_of` 权威 = 数据库 `statement_timestamp()`；
  全量可见 Evidence revision-chain 校验 / 折叠；canonical Evidence-head selection；精确
  horizon Outcome revision-chain 校验 / 折叠；canonical Outcome head / `NO_OUTCOME`；
  canonical Evidence ↔ Outcome cross-integrity；`CanonicalScopeFacts` projection；
  扩展 I01 canonical manifest 的 revision-aware manifest。**无** historical caller-supplied
  `as_of`；**未**引入新统计语义（I01 仍为 canonical manifest base fields / fingerprint /
  bootstrap / statistics / uncertainty / sufficiency 的权威）。
- ⚠️ **`I02 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I02 收尾时；其后 `SE-02D Overall` 已于
  2026-09-16 转 `ACCEPTED / COMPLETE`）：**population grouping + invocation of I01
  `aggregate()` 已于 `SE-02D-I03` 实现并验收**（见下）；`SE-02D V1` capability 完成边界其后
  已由 **`SE-02D-CLOSE-D01`**（2026-09-16 Human Acceptance = `CONFIRMED`）接受为
  `COMPLETE AFTER I03`（见下）：aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 +
  I03`；API / frontend / runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`；
  historical revision-as-of 仍 `OPEN`；`SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall
  Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`。
- 边界：`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；
  **historical revision-as-of = `OPEN`**、**experiment/pair/arm identity = `OPEN`**、
  **durable regime identity = `OPEN`**；Memory P2 `N01-7-R01-RR-P2-01` 保持
  `REMAINS / NON-BLOCKING`。
- 详见 `dev_log/2026-09-15-se-02d-i02-final-acceptance-reconciliation.md` 与
  `dev_log/2026-09-15-se-02d-i02-current-snapshot-folding.md`。

### SE-02D-I03 Population Grouping + Aggregate Orchestration — ACCEPTED / COMPLETE

- 任务：`SE-02D-I03`｜Population Grouping + Aggregate Orchestration → `SE-02D-I03-FINAL`｜
  Human Acceptance + State Sync + Main Integration（docs/state-only；**非**新实现、**非**新
  Review、**非** Gate C、**非** Live）。
- 状态：**`SE-02D-I03 = ACCEPTED / COMPLETE`**（2026-09-16 Human Acceptance = `CONFIRMED`）；
  Initial Independent Review = `FAIL — FIX REQUIRED`；`SE02D-I03-R1`（P1）= `CLOSED`；FIX-01
  Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`。
- **Human-Accepted reviewed HEAD = `20a7c333abf81077c409811302331119dff485a5`**
  （branch `se-02d-i03-fix-01-projection-identity-validation`，immutable evidence pointer；
  远端未被移动）；Original Reviewed Candidate = `44d0e4b…`（branch
  `se-02d-i03-population-aggregate-orchestration`，immutable）；closeout branch =
  `se-02d-i03-final-acceptance-closeout`；Accepted Main before =
  `44df66603e6bdba1f3f80c21be5b30c295e4a20a`；集成方法 = `FAST-FORWARD ONLY`。
- 已接受范围：**population grouping + I01 `aggregate()` orchestration**
  （`marketpulse.edge.aggregation_orchestration`）—— 消费一份 I02
  `CurrentSnapshotProjection`；facts ↔ revision-aware manifest 一一对应完整性门（fail
  closed）；按完整结构 `PopulationKey` 分组；每个 population **恰好一次** I01 `aggregate()`
  调用；确定性 population 排序；薄 async 单次读 wrapper。**不** own 统计 / revision
  folding / DB snapshot 语义 / 新 Population Key 语义 / Measurement Signature 语义 /
  API & product 集成。
- ⚠️ **`I03 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I03 收尾时）：aggregate capability 其后已由
  `SE-02D-CLOSE-D01`（2026-09-16 Human Acceptance = `CONFIRMED`）确认为
  `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend / runtime product consumer =
  `NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical revision-as-of 仍 `OPEN`；
  `SE-02D V1` capability implementation = `COMPLETE AFTER I03`；`SE-02D Overall` 其后已于
  2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`。
- 边界：`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；
  Memory P2 `N01-7-R01-RR-P2-01` 保持 `REMAINS / NON-BLOCKING`。本收尾**不**定义 / 启动 I04。
- 详见 `dev_log/2026-09-16-se-02d-i03-final-acceptance-closeout.md` 与
  `dev_log/2026-09-16-se-02d-i03-population-aggregate-orchestration.md`。

### SE-02D-CLOSE-D01 V1 Completion Boundary Reconciliation — ACCEPTED / COMPLETE

- 任务：`SE-02D-CLOSE-D01`｜V1 Completion Boundary Reconciliation →
  `SE-02D-CLOSE-D01-FINAL`｜Human Acceptance + State Reconciliation + Main Integration
  （docs/state-only；**非**新实现、**非**新 Review、**非** I04、**非** Gate C、**非** Live）。
- 状态：**`SE-02D-CLOSE-D01 = ACCEPTED / COMPLETE`**（2026-09-16 Human Acceptance =
  `CONFIRMED`）；Independent Review = `PASS — READY FOR HUMAN ACCEPTANCE`。
- **Human-Accepted candidate = `a9e615726ee964c02a72ea6cbff490d3d74e08f7`**
  （branch `design/se-02d-close-d01-v1-completion-boundary`，immutable evidence pointer；
  远端未被移动、未追加 acceptance commit）；Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-CLOSE-D01-V1-Completion-Boundary-Reconciliation.md`
  （status = `ACCEPTED DESIGN`；§4 A–AD 覆盖矩阵与 §5–§11 分类结论逐字未改，**仅**变更
  acceptance-state / closeout metadata）；closeout branch =
  `se-02d-close-d01-final-acceptance`；Accepted Main before =
  `779eaf1ca781d64733c8264b0a06c7601deacdba`；集成方法 = `FAST-FORWARD ONLY`。
- **Accepted completion conclusion = `SE-02D V1 CAPABILITY COMPLETE AFTER I03`**：Accepted D01
  current-snapshot V1 责任已由 I01 + I02 + I03 完整实现（该 batch 的 coverage verdict =
  `ACTUAL GAP = NONE FOUND`）。Human 接受全部六项结论：V1 capability 于 I03 后完成；
  API / frontend / runtime consumer **不是** V1 完成要求；陈旧 “aggregate / API / product
  integration = NOT YET IMPLEMENTED” 措辞调和为 future-consumer 边界；historical
  revision-as-of 仍 `OPEN` 但不阻塞 current-snapshot V1 完成；Gate C prerequisites 仍 `OPEN`；
  **不需要** I04 implementation batch，下一阶段 = `SE-02D Overall Final Review`（已于
  2026-09-16 经 SE-02D Overall Final Acceptance Closeout 完成并转 `ACCEPTED / COMPLETE`）。
- Accepted callable 边界：`CurrentSnapshotRevisionReader.read(horizon)` →
  `CurrentSnapshotProjection` → `aggregate_projection(projection)` →
  `tuple[AggregationResult, ...]`；`aggregate_current_snapshot(reader, horizon)` = 恰好一次读 +
  同一纯编排。SE-02D V1 **不** own production consumer；RuntimeHost session-factory ownership
  **未**改变（属未来 consumer composition question，非 V1 blocker）。
- ⚠️ **`SE-02D-CLOSE-D01 Accepted` 当时 ≠ `SE-02D Overall Acceptance`**（该句为 CLOSE-D01
  收尾时）：`SE-02D V1` capability implementation = `COMPLETE AFTER I03`，`SE-02D Overall` 其后
  已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；
  `SE-02D = ACCEPTED / COMPLETE` **≠** `Gate C PASS`，`Gate C PASS` **≠** `Live` 授权。
- 边界：`I04 = NOT REQUIRED FOR SE-02D V1`（未定义、未启动）；`Gate C = NOT PASSED`；
  `Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；`KEEP / DOWNWEIGHT / KILL = NOT OWNED BY
  SE-02D V1`；`SE-02D V1 capability complete != Gate C PASS`、`Gate C PASS != Live
  authorization`；四个未来边界（historical revision-as-of / experiment-pair-arm identity /
  arm-level selection expectancy-delta / durable regime + Gate C artifact retention）仍 `OPEN`；
  Memory P2 `N01-7-R01-RR-P2-01` 保持 `REMAINS / NON-BLOCKING`。
- 详见 `dev_log/2026-09-16-se-02d-close-d01-final-acceptance.md` 与
  `dev_log/2026-09-16-se-02d-close-d01-v1-completion-boundary-reconciliation.md`。

### SE-02D-D01 Family Aggregation / Expectancy Contract — ACCEPTED / COMPLETE

- 任务：`SE-02D-D01`｜Family Aggregation / Expectancy Contract →
  `SE-02D-D01-FINAL-REC-01`｜Final Acceptance Closeout / 正交漂移和解（docs/state-only；
  **非** Implementation、**非** New Design、**非** New Review、**非** Gate C、**非** Live）。
- 状态：**`SE-02D-D01 = ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED`）；
  Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS`；
  `D01-R1` / `D01-R2` = `CLOSED`；`D01-R3` = `CLARIFIED / NON-BLOCKING`。
- **Human-Accepted candidate = `245b068199b7e6f3d32bf67e3b00163e4804afdf`**
  （branch `design/se-02d-d01-family-aggregation-expectancy`，immutable evidence pointer；
  该 branch **不是** current `main` 的 ancestor —— 本轮以 latest-main content-level
  carry-forward 收编，`main` 由 `9e0553f5…` fast-forward）。
- Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`；
  closeout branch = `se-02d-d01-final-acceptance-closeout`；Closeout Reconciliation Base =
  `9e0553f5…`；集成方法 = `FAST-FORWARD ONLY`。
- 已接受 V1 决策摘要见 `DECISIONS.md` 「SE-02D-D01 V1」条目；完整契约见 Accepted Design
  artifact（本文件**不**复制契约全文）。
- ⚠️ **`SE-02D` production implementation 当时 = `NOT STARTED`**（SE-02D-D01 收尾时；其后
  `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`，父
  `SE-02D` 当时 = `IN PROGRESS`，剩余实现当时仍 `NOT COMPLETE`；`SE-02D` 本身其后已于
  2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）；本 Acceptance **不**构成
  family aggregation / expectancy 实现；`Gate C = NOT PASSED`、`Live = NOT AUTHORIZED`、
  Real AI = `NOT ACTIVATED`。实现前仍存三项独立 prerequisite：**historical revision-as-of =
  `OPEN`**、**experiment/pair/arm identity = `OPEN`**、**durable regime = `OPEN`**。
- 边界保持：`PRE-01B-D1 = ACCEPTED / COMPLETE`；`PRE-01B-I1 = ACCEPTED / COMPLETE`（`Integrated Runtime Host Core V1 Implementation`，2026-09-15 Human Acceptance = `CONFIRMED`；**不** 构成 OS/service deployment / Real AI activation / G2→G3 / `SE-02D` Production / Live Trading）；Memory P2 `N01-7-R01-RR-P2-01` 保持 `REMAINS / NON-BLOCKING`。
- 详见 `dev_log/2026-09-15-se-02d-d01-final-acceptance-closeout.md`。

### PRE-01B-D1 Integrated Runtime Host Formal Design — ACCEPTED / COMPLETE

- 任务：`PRE-01B-D1`｜Integrated Runtime Host Formal Design →
  `PRE-01B-D1-CLOSE`｜Acceptance Closeout & Main Integration（docs/state-only；
  **非** Implementation、**非** New Design、**非** New Review、
  **非** Runtime activation、**非** `SE-02D`）。
- 状态：**`PRE-01B-D1 = ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance =
  `CONFIRMED`）。Independent Review = `PASS WITH NON-BLOCKING FINDINGS`；
  P0 = `NONE`、P1 = `NONE`。
- **Human-Accepted reviewed candidate = `80cb2babe9f55b3a3b1dc2d3b7913a405607ac22`**
  （branch `design/pre-01b-d1-runtime-host-contract`，远端同 SHA、immutable、
  未被移动）。
- Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`；closeout branch =
  `pre-01b-d1-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`。
- 已接受架构决策摘要见 `DECISIONS.md` 「PRE-01B-D1 V1」条目；
  完整契约见 Accepted Design artifact（本文件**不**复制契约全文）。
- Implementation carry-ins（**必须**带入实现窗口）：`F-01` —
  `state_version_for` 实现必须显式绑定已接受的 durable state/version
  authority，`RuntimeHost` / `LiveMarketState` **不得**自造并行 `state_version`
  authority；`F-02` — safety queue capacity `64` 仅为**初始可配置默认值**，
  Implementation Acceptance **必须**用 queue high-water / runtime evidence 验证 sizing。
  `F-03..F-08` = P3 / NON-BLOCKING，**不**为其单独开 Fix batch。
- ⚠️ 本 Acceptance **只**接受 Formal Design，**不**证明 / 不授权：
  `Integrated Runtime Host Implementation`（仍 `NOT STARTED`）、runtime validation、
  Real AI activation、G2→G3 activation、`SE-02D`、Live Trading、profitability / edge。

### PRE-01B-I1 Integrated Runtime Host Core V1 Implementation — ACCEPTED / COMPLETE

- 任务：`PRE-01B-I1`｜Integrated Runtime Host Core V1 Implementation → `PRE-01B-I1-CLOSE`｜Human Acceptance Closeout & Latest-Main Reconciliation（content-level carry-forward；**非** 重新设计、**非** 第二份实现、**非** New Review、**非** Runtime validation、**非** Real AI activation、**非** `SE-02D`）。
- 状态：**`PRE-01B-I1 = ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED`）。Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS`；P0 = `NONE`、P1 = `NONE`。
- **Human-Accepted reviewed candidate = `68dd7e96cc8547433794b045fa99e1e9dc5b7892`**（branch `pre-01b-i1-fix-01-runtime-host-lifecycle`，远端同 SHA、immutable、未被移动）。
- Accepted Design pointer = `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`（`PRE-01B-D1 = ACCEPTED / COMPLETE`）；closeout branch = `pre-01b-i1-final-acceptance-reconciliation`；集成方法 = `FAST-FORWARD ONLY`（content-level carry-forward onto latest `main` `0ae5b0b…`）。
- 已接受实现层 Runtime 属性（摘要；完整实现见 `68dd7e9` 与 Review/Re-Review 报告；本文件**不** 复制实现全文）：`RuntimeHost` = 唯一 production composition owner；FastAPI `lifespan` = activation boundary；session advisory-lock fence；无 idle-in-transaction singleton leak；fatal critical child propagates to lifecycle/process failure；mandatory cleanup failure 是 truthful；cancellation 不能绕过 final disposal；explicit DB ownership；bounded retention；enabled V1 需 BTC-USDT + ETH-USDT；`F-01` durable `state_version` authority 保留；`F-02` safety queue `64` 仍 configurable / evidence-based。
- ⚠️ 本 Acceptance **只**接受 Implementation Core V1，**不**证明 / 不授权：Real AI activation、G2→G3 activation、`SE-02D` Production complete、OS/service packaging、Live Trading、profitability / edge。
- 边界保持：`N01 overall = ACCEPTED / COMPLETE`；Memory P2
  `N01-7-R01-RR-P2-01` = `REMAINS / NON-BLOCKING`（**禁止**写 `memory resolved` /
  `memory is fine` / `no memory concern`）；`SE-02D = NOT STARTED`（PRE-01B-D1 收尾时；其后
  `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）；Real AI =
  `NOT ACTIVATED`；live Opportunity → G3 = `NOT ACTIVE`；Live Trading = `DISABLED`。
- 详见 `dev_log/2026-09-15-pre-01b-d1-final-acceptance-closeout.md`。

### PRE-01B-D2 AdvisoryIngress / G2→G3 Activation Contract — ACCEPTED / COMPLETE

- 任务：`PRE-01B-D2`｜AdvisoryIngress / G2→G3 Activation Contract Formal Design →
  `PRE-01B-D2-CLOSE`｜Final Acceptance Closeout & Fast-Forward Main Integration（docs/state-only；
  **非** Implementation、**非** New Design、**非** New Review、**非** Runtime activation、
  **非** `PRE-01B-I2`）。
- 状态：**`PRE-01B-D2 = ACCEPTED / COMPLETE`**（2026-09-17 Human Acceptance = `CONFIRMED`）。
  Independent Re-Review = `PRE-01B-D2-FIX-05 = PASS`；P0 = `NONE`、P1 = `NONE`、P2 = `NONE`、
  P3 = `NONE`。
- **Human-Accepted reviewed candidate = `cce1ae7b862b038a99976c802c0985df01b35285`**
  （branch `design/pre-01b-d2-fix-05-return-completion-authority`，远端同 SHA、immutable、
  未被移动）。accepted lineage（线性单 parent）=
  `a90c5968… → b5767d1… → 4548920… → d3922dd… → cce1ae7…`（`FIX-02` / `FIX-03` / `FIX-04`
  为 historical failed reviewed candidates，保持 immutable、**不**改写为 PASS）。
- Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`；closeout branch =
  `pre-01b-d2-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`。
- 已接受架构决策摘要见 `DECISIONS.md`「PRE-01B-D2 V1」条目；完整契约见 Accepted Design artifact
  （本文件**不**复制契约全文）。
- Human Decision Pack carry-forward（**不**表示设计有缺陷或未被接受）：Pack A = `NONE`；
  Pack B = numeric production activation settings 仍 `UNRESOLVED`；Pack C = Gate-A observation /
  sufficiency / acceptance thresholds 仍 `UNRESOLVED`。
- ⚠️ 本 Acceptance **只**接受 Formal Design，**不**证明 / 不授权：`PRE-01B-I2` implementation、
  live `G2→G3` activation、Real AI activation、provider configuration、真实 provider 调用、
  Gate A activation、Gate B activation、`Gate C`（`NOT PASSED`）、`Live`（`NOT AUTHORIZED`）、
  profitability / edge。Design Acceptance 是前置条件，**不是** runtime activation。
- 边界保持：`N01 overall = ACCEPTED / COMPLETE`；Memory P2
  `N01-7-R01-RR-P2-01` = `REMAINS / NON-BLOCKING`（**禁止**写 `memory resolved` /
  `memory is fine` / `no memory concern`）；Real AI = `NOT ACTIVATED`；live G2→G3 =
  `NOT ACTIVE`；Live Trading = `DISABLED`。
- 详见 `dev_log/2026-09-17-pre-01b-d2-final-acceptance-closeout.md`。

### N01-8 12-hour Extended Runtime Soak — ACCEPTED / COMPLETE

- 任务：`N01-8`｜12-hour Extended Runtime Soak → `N01-8-FINAL`｜Final Acceptance Closeout
  （Closeout / Integration Task；**非**新 Runtime Validation、**非**新 Independent Review、
  **非**新实现）。
- Human Acceptance = `CONFIRMED`（2026-09-14）；Independent Review Final Verdict =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；**Human-Accepted reviewed
  candidate = `d9306ada663a5cacb86bee26218e298169d82e6b`**（branch `n01-8-12h-extended-soak`，
  远端同 SHA、未被改写）；Frozen Task Base = `dd78a979…`；Closeout Base（latest accepted main）=
  `e0a5d2a2…`。
- 集成方法 = `FAST-FORWARD ONLY`：`e0a5d2a2 → docs/state-only Final Acceptance Closeout Commit`，
  单 parent；无 merge commit / squash / rebase / cherry-pick / force push；**未**把 `main` 回退到
  `dd78a979`，**未**丢失任何 SE-02C / PRE-01A-D1 已接受状态。closeout branch =
  `n01-8-final-acceptance-closeout`。
- 12h evidence 摘要：真实 OKX 公共行情 + 一次性 disposable PostgreSQL + detached supervisor，
  单轮 `total_active 44401.217470 s`（≥ 43200）、4/4 phase complete、3 次 fresh-process restart、
  12 次受控重连、6 次受控 STALE→FRESH、24/24 reconciliation checkpoint PASS、**99/99 aggregate
  checks True**、`failures = []`；`production_code_unchanged = true`、shared primary before ==
  after、disposable residue `0`；Power Loss = `RUN COMPLETED BEFORE POWER LOSS`（invalidation =
  `NO`）；Baseline Drift = `NO MATERIAL IMPACT`；Targeted Revalidation = `NOT REQUIRED`；
  Full Rerun = `NOT REQUIRED`。
- Closeout 五项不变：`Production code changed = NO` / `Migration changed = NO` /
  `Tests changed = NO` / `Frontend changed = NO` / `Runtime config changed = NO`；
  `alembic heads` 单 head `20260913_0009`；`DECISIONS.md changed = NO`（无新增产品 / 架构决策）。
- 🚩 **Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS`**（P2 / NON-BLOCKING / Memory Operational
  Watch / Bounded Retention Growth）：冻结 AND contract（`growth > 64 MiB` **AND** second-half
  `slope > 5 MiB/h`）Formal Finding = `FALSE`（`RSS growth 77.711 MiB`、second-half slope
  `−0.639369 MiB/h`）⇒ Formal Acceptance **不**被 Memory Finding 阻塞，但 operational watch
  **未**闭合。**禁止**写 `memory resolved` / `memory is fine` / `no memory concern`。
- P3 findings（全部 `NON-BLOCKING`、**未**升级）：`N01-8-IR-P3-01`
  （`companion_structures_bounded=false` 属 diagnostic；cleanup evidence 显示 bounded
  lifecycle）；`N01-8-IR-P3-02`（dev_log EOF whitespace hygiene；由 closeout 追加章节后的格式
  自然消除）；`N01-8-IR-P3-03`（无单独 supervisor process exit-code artifact；由 phase exit 0 /
  `FINISHED/PASS` + 完整 raw/stdout/error evidence 补强）。
- ⚠️ `N01-8 = ACCEPTED / COMPLETE` **≠** `Integrated Runtime Host` / Continuous Runtime /
  7×24 / `SE-02D` / Real AI Edge / Live 的任何进度；`Integrated Runtime Host = NOT STARTED`。
  （`N01-8` 收尾时 `N01 overall` 尚未验收；其后已于 2026-09-14 经 N01 Overall Final
  Acceptance Closeout 转 `ACCEPTED / COMPLETE`，见下条。）
- 收尾后的下一步：`N01 Overall Final Review / Acceptance`（已由总进度窗口另开并于 2026-09-14
  完成，见下条；本窗口**未**自动启动 `N01-8` 之外的任何阶段）。
- 详见 `dev_log/2026-09-14-n01-8-extended-soak.md`（§47 Final Acceptance Closeout）。

### N01 Overall Final Acceptance Closeout — ACCEPTED / COMPLETE

- 任务：`N01`｜Final Acceptance Closeout（docs/state-only；**非**新 Runtime Validation、
  **非**新 Independent Review、**非**新实现、**非** N01-9、**非** Integrated Runtime Host、
  **非** SE-02D、**非** Real AI implementation）。
- 状态：**`N01 overall = ACCEPTED / COMPLETE`**（2026-09-14）。
- Human Acceptance = `CONFIRMED`；Overall Final Review Verdict =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`（P0 = `NONE`、P1 = `NONE`）。
- Closeout Base（任务 preflight 实测 remote `main`，与导航值一致 ⇒ 无 `BASELINE MOVED`）=
  `3f51ac7388627f09a96aeb05419dcfb4492b69f8`；closeout branch =
  `n01-overall-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`。
- Accepted Gate Inventory（全部 `ACCEPTED / COMPLETE`）：`N01-A` / `N01-B` /
  `N01-VAL-FIX-01/02/03` / `N01-C` / `N01-6` / `N01-7-F01` / `N01-7`（`N01-7-R01`）/
  `N01-8`。
- Accepted Claim Boundary：仅证明冻结范围内已有的 deterministic runtime lifecycle / restart /
  durable recovery / reconciliation / economic safety / protection authority 与 15m smoke、
  2h medium soak、12h extended soak 在批准 harness + 真实 PostgreSQL + 真实 OKX public data +
  Paper boundary 下完成；**不**证明 Integrated Runtime Host / 7×24 daemon / deployment /
  Live readiness / Real AI runtime active / Trading Edge / `SE-02D` / 长期盈利能力 / SWAP
  runtime。
- Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS`（P2 / NON-BLOCKING）；P3 `N01-8-IR-P3-01/02/03`
  与 `SE02C-R7` 保持 `NON-BLOCKING`、**未**修复 / 关闭 / 升级 / 重分类。
- `Integrated Runtime Host = NOT STARTED`；`SE-02D = NOT STARTED`（N01 Overall 收尾时；其后
  `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）；
  `N01-9 = NOT REQUIRED / NOT CREATED`；`Live = NOT ENABLED`。
- Next Runtime Boundary：**`Integrated Runtime Host`**（须另开独立获批窗口；**不得**自动启动）。
- 详见 `dev_log/2026-09-14-n01-overall-final-acceptance-closeout.md`。

### PRE-01A-D1 Real AI V1 Trade Decision Experiment Contract — ACCEPTED / COMPLETE

- 任务：PRE-01A-D1｜Real AI V1 Trade Decision Experiment Contract → `PRE-01A-D1-FINAL`｜
  Acceptance Closeout & Main Integration（docs/state-only 收尾；**非**新实现 / 新设计 /
  新 Review / Real AI activation / Runtime Host design / SE-02D）。
- Human Acceptance = `CONFIRMED`（2026-09-14）；Independent Re-Review = `PASS`；
  `D1-R1` / `D1-R2` = `CLOSED`；**Human-Accepted candidate =
  `e3fb721c678e2b3ca0af6fb4663f349c6a641159`**（branch `design/pre-01a-d1-real-ai-v1-contract`，
  远端同 SHA、未被移动）；Accepted Design artifact =
  `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`。
- 已接受边界：placement = `C. Trade Decision` only；AI advisory / deterministic authority；
  baseline = `ALL_ELIGIBLE_LONG_SHADOW_V1`；V1 claim = selection / participation edge only；
  Single Primary Provider / no fallback / no voting；`SE-02C = REUSE`；
  `SE-02D = required before Gate C edge declaration`；`Runtime Host = separate future boundary`。
- 当前 blockers / prerequisites（**均未**由本 Acceptance 解锁）：
  `SE-02D = NOT STARTED`（PRE-01A-D1 收尾时；其后 `SE-02D-I01` 已于 2026-09-15 经
  Human Acceptance 转为 `ACCEPTED / COMPLETE`）；`Integrated Runtime Host = NOT STARTED`；
  live Opportunity → G3 integrated handoff = `NOT ACCEPTED / NOT ACTIVE`；
  Real AI provider runtime evidence = `NOT PRESENT`（Real AI runtime activation =
  `NOT STARTED / NOT ACTIVATED`）。
- ⚠️ `PRE-01A-D1 = ACCEPTED` **≠** Real AI implementation / activation / edge /
  `SE-02D` / Runtime Host / Live 的任何进度。
- 收尾后的下一步：**PRE-01A-D1 CLOSED. Do not start Real AI implementation or SE-02D
  automatically.**
- 详见 `dev_log/2026-09-14-pre-01a-d1-real-ai-v1-experiment-contract.md`。

### SE-02C Forward Outcome Calculator — ACCEPTED / COMPLETE

- 任务：`SE-02C`｜Forward Outcome Calculator → `SE-02C-FIX-01`｜Review Blockers →
  `SE-02C-FIX-02`｜Stable Read Snapshot；收尾轮 = `SE-02C-FINAL`｜Acceptance Closeout &
  Main Integration（**非**新实现、**非**重新 Review、**非**新 Acceptance）。
- 关闭的 Review Finding：`SE02C-R1` / `R2` / `R3` / `R4`（由 FIX-01）与 `R5` / `R6`
  （由 FIX-02）全部 `CLOSED / PASS`。
- Human Acceptance = `CONFIRMED`（2026-09-14）；Independent Re-Review = `PASS WITH
  NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；**Human-Accepted reviewed candidate =
  `7bb3835d6b14a3fc86becff1881c7f53f1acd567`**（branch `se-02c-fix-02-stable-read-snapshot`，
  远端同 SHA、未被移动）；Accepted Main before = `dd78a979…`；集成方法 = `FAST-FORWARD ONLY`
  （`dd78a979 → 51891c7`（true merge）× `be3aa6c` `→ 7ab1d42 → 2f98682 → 6b08459 → 7bb3835
  → docs/state-only Acceptance Closeout Commit`；无 merge commit 到 `main` / squash / rebase /
  cherry-pick / force push）。
- 已验收能力：Forward Outcome Calculator（30s / 5m / 15m / 1h 四个 horizon）+ stable Capture
  Anchor reference + complete Forward BBO path + deterministic endpoint + MFE / MAE +
  reference return + executable LONG return + paper cost-adjusted return + `COMPLETE` /
  `INSUFFICIENT_DATA` / `INVALID` 终态 + revision-1 immutable normal outcome +
  retry / restart determinism + concurrent exactly-one + stable `REPEATABLE READ`
  calculation snapshot + same-scope PostgreSQL advisory coordination + tradability authority +
  Replay / Forward provenance separation。
- `C-01..C-29 = ALL PASS`、`F02-01..F02-24 = ALL PASS`（**source = Independent Re-Review
  evidence**，**非**本收尾窗口重跑）。
- Closeout 四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`；`alembic heads` 单 head
  `20260913_0009`（`20260911_0005` / `20260912_0006` / `20260913_0007` / `20260913_0008` /
  `20260913_0009` 的 revision identity 未重写）。
- 遗留 `SE02C-R7` = `P3 / NON-BLOCKING / NOT FIXED`（Human Accepted non-blocking finding；
  如需清理另开独立 `P3 docs/comment cleanup task`；**未**修改
  `backend/src/marketpulse/edge/forward_service.py`）。
- ⚠️ `SE-02C` Accepted **≠** `SE-02D` MAY START：`SE-02D｜Family Aggregation / Expectancy`
  仍 `NOT STARTED`，须另开独立获批的窗口与门；也**不**构成 `N01-8` / Integrated Runtime Host
  的任何进度。
- 收尾后的下一步：**SE-02C CLOSED. Do not start SE-02D automatically. Return to the SE
  control window for the next task.**
- 详见 `dev_log/2026-09-14-se-02c-final-acceptance-closeout.md`、
  `dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md` 与
  `dev_log/2026-09-14-se-02c-fix-01-review-blockers.md`。

### N01-7 / N01-7-R01 2-hour Medium Runtime Soak（含 Witness B Fix + Latest-Main Revalidation）— ACCEPTED / COMPLETE

- 任务：`N01-7`｜2-hour Medium Runtime Soak → `N01-7-R01`｜Validation Harness Fix + Latest-Main
  Targeted Revalidation + Formal Acceptance Re-run（**非**新实现、**非** production fix、
  **非**需求变更、**非** N01-8）。收尾轮 = `N01-7 Final Human Acceptance + Main Integration +
  Final Acceptance Closeout`（**非**新实现、**非**重新 Review）。
- 关闭的 Review Finding：**R01**（F01 Witness B 原比较同一 plan，未真实建立 `Plan A != Plan B`
  ⇒ 属 HARNESS DEFECT）+ **R02**（latest-main baseline drift ⇒ targeted revalidation）。
- Task Base / Accepted Main before = `8a29306d904223f03408fe55538ba6cb05222f15`（起止两次
  `ls-remote` 相同 ⇒ **main drift = NO**）；migration head = `20260913_0009`（单 head，
  `20260912_0006` 为 ancestor）。
- Human Acceptance = `CONFIRMED`；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS —
  READY FOR HUMAN ACCEPTANCE`；**Human-Accepted reviewed candidate =
  `559f14be1fb89df58c11dfbea737eba4ac30421e`**（branch `n01-7-r01-witness-b-latest-main`，
  远端同 SHA、未被改写）；集成方法 = `FAST-FORWARD ONLY`（`8a29306 → 559f14b → docs/state-only
  Final Closeout Commit`，无 merge commit / squash / rebase / cherry-pick / force push）。
- 关键证据：正式单轮 `total_active 7320.252 s`（pid `11720 → 768`，gap `6.375 s`）、**84/84 checks
  true**、reconnects 5 / stale 2 / checkpoints 7、Witness A/B/C 全成立（Plan A
  `plan_7d212f0ce53054e676a6e30c v1`、Plan B `plan_f9c9560e6a5d22319a490a28 v2`、判别 bid
  `73884.46625` ∈ (StopA, StopB] → 决策 **HOLD**、counterfactual **STOP_LOSS**）、
  `production_code_unchanged = true`、shared primary before == after、residue `0`。
- Closeout 四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`；`alembic heads` 单 head
  `20260913_0009`（`20260912_0006` / `20260913_0007` / `20260913_0008` 的 revision identity 未重写）。
- 🚩 P2 Watch Item（**必须**留待 `N01-8`）：`N01-7-R01-RR-P2-01` — Memory Operational Watch /
  Bounded Retention Growth；slope `≈16.02 MiB/h > 5.0`（`finding = false` 仅因
  `total_growth ≈14.043 MiB ≤ 64`，按冻结 AND contract Acceptance Gate = PASS）⇒ **不得**据此
  宣称内存无问题（禁写 `memory resolved` / `memory is fine` / `no memory concern`）。
- ⚠️ `N01-7` / `N01-7-R01` Accepted **≠** `N01 overall` Accepted（N01-7 收尾时尚未总体验收；
  其后 `N01 overall` 已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`）；`N01-8` / `Integrated Runtime Host` 当时仍 `NOT STARTED`（N01-7
  收尾时；其后 N01-8 已于 2026-09-14 经 Human Acceptance 转 `ACCEPTED / COMPLETE`，见本节顶部
  N01-8 条目）。
- 收尾后的下一步（N01-7 收尾时）：**N01-7 CLOSED. Do not start N01-8 automatically.** 等待总
  进度窗口决定 `N01-8｜12-hour Extended Soak`（其后已另行获批执行完毕）。
- 详见 `dev_log/2026-09-14-n01-7-final-acceptance-closeout.md` 与
  `dev_log/2026-09-13-n01-7-r01-witness-b-revalidation.md`；原始证据在外部
  `E:/Temp/n01-7-r01/`（**未**入库）。

### SE-ARCH-FIX-02 Outcome Revision Chain Scope — ACCEPTED / COMPLETE

- 任务：SE-ARCH-FIX-02A｜Human Acceptance Closeout（Human Acceptance Integration / Final
  Closeout；**非**新实现、**非**重新 Review）。
- Human Acceptance = `APPROVED`（2026-09-13）；Independent Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`（F2-01～F2-15 全 PASS；无 P0/P1/P2/P3 Finding）。
- Human-Accepted reviewed candidate = `15da7c1bac719d17271c7df9fcccbf80535b6d1b`（implementation
  `4c835828f482875d1d7ce934f8808d3953a9105b`；branch
  `se-arch-fix-02-outcome-revision-chain-scope`）；Accepted Main before =
  `fc619242c99a794a2eb2b87ee02b8b72aa782f05`；Accepted Main after = Final Closeout Commit。
- accepted lineage（仅 fast-forward，无 merge commit 到 `main` / squash / rebase /
  cherry-pick / force）：`fc619242 → 4c835828 → 15da7c1 → Final Closeout Commit`；evidence
  branch `se-arch-fix-02-outcome-revision-chain-scope` 保留。
- Accepted semantic：revision chain scope = `(opportunity_id, evidence_id, horizon)`；**DB 负责
  scope integrity**（`uq_edge_outcome_id_scope` + 4 列 `fk_edge_outcome_supersedes`），
  **service 同时负责 scope integrity 与 revision adjacency**（未引入 trigger）。
- Closeout 为 docs-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`；`alembic heads` 单 head
  `20260913_0009`；`20260912_0006` / `20260913_0007` / `20260913_0008` / `20260913_0009`
  全部保留、revision identity 未重写。
- P2 保留项（`NON-BLOCKING`）：`TEST-ISO-01`；`RRF-03`（`DEFERRED`）；`RRF-04`。
- Claim 边界：本验收**不得**推断 `SE-02C` / `SE-02D` / Forward Outcome Calculator / MFE-MAE /
  forward returns / expectancy / Real AI Edge / Live / N01-7 / N01-8 / Integrated Runtime Host
  的任何进度。
- ⚠️ **FIX-02 Accepted ≠ SE-02C MAY START**：`SE-02C` 保持 `BLOCKED / NOT STARTED`
  （SE-ARCH-FIX-02 收尾时；其后 `SE-02C` 已于 2026-09-14 经 Human Acceptance 转为
  `ACCEPTED / COMPLETE`，见 `### SE-02C Forward Outcome Calculator — ACCEPTED / COMPLETE`）；
  启动前必须另开独立获批的 **Pre-SE-02C Re-Gate**，且仅当该 Gate 返回
  `PASS — SE-02C MAY START` 才允许启动。
  本窗口**未**启动该 Gate、**未**启动 SE-02C。
- 详见 `dev_log/2026-09-13-se-arch-fix-02-outcome-revision-chain-scope.md`
  「Human Acceptance + Final Main Integration Closeout」与 `PROJECT_STATE.md`
  「SE-ARCH-FIX-02 Result」。
- 收尾后的下一步：**SE-ARCH-FIX-02 CLOSED. Do not start Pre-SE-02C Re-Gate or SE-02C
  automatically. Return to the SE control window for the next task.**

### SE-ARCH-FIX-01 Stable Evidence Anchor — ACCEPTED / COMPLETE

- Human Acceptance = `APPROVED`（2026-09-13）；Second Independent Re-Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`（无 P0/P1；AC 全 PASS；Integration AC 全 PASS；
  RRF-01 PASS；RRF-02 PASS；full backend `363 passed`；Ruff / compileall /
  `git diff --check` PASS；`alembic heads` 单 head `20260913_0008`；accepted N01-7
  `20260912_0006` preserved；Historical Replay 未获得 Forward issuer）。
- Human-Accepted reviewed candidate = `1e2738b09a4e4a62d91cfa8a6ffd6fcec3c71a21`（branch
  `se-arch-fix-01-latest-main-integration`）；Accepted Main before =
  `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`；Accepted Main after = Final Closeout Commit。
- accepted lineage（仅 fast-forward，无 merge commit 到 `main` / rebase / squash /
  cherry-pick / force）：`51053757 → bdb1af2 → 513689a（true merge：
  `71abb07` × `bdb1af2`，lineage 未重写）→ 5ba78af → 1e2738b → Human Acceptance（2026-09-13）
  → Final Closeout Commit`；evidence branch `se-arch-fix-01-stable-evidence-anchor` /
  `n01-7-f01-latest-main-integration` 均保留。
- Closeout 为 docs-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`。
- P2 保留项（`NON-BLOCKING`）：`TEST-ISO-01`（Alembic test helper `DATABASE_URL` routing
  可复现性，仅记录未修）；`RRF-03`（Historical N01 migration gate head-pin drift，`DEFERRED`，
  accepted N01 historical gate **未被修改**）；`RRF-04`（shared-DB isolation evidence 仅为
  revision + table inventory fingerprint，不是 row-level proof，措辞边界保持）。
- Claim 边界：本验收**不得**推断 `SE-ARCH-FIX-02`（`NOT STARTED`）/ `SE-02C`
  （`BLOCKED / NOT STARTED`，FIX-02 尚未完成）/ `SE-02D` / Forward Outcome Calculator /
  MFE-MAE / expectancy / Real AI Edge / Live / N01-7 / N01-8 / Integrated Runtime Host 的任何进度
  （括号内状态为 SE-ARCH-FIX-01 收尾时；其后二者均已 `ACCEPTED / COMPLETE`）。
- 详见 `dev_log/2026-09-12-se-arch-fix-01-stable-evidence-anchor.md`
  「Human Acceptance + Final Main Integration Closeout｜2026-09-13」与 `PROJECT_STATE.md`
  「SE-ARCH-FIX-01 Result」。
- 收尾后的下一步：**SE-ARCH-FIX-01 CLOSED. Do not start SE-ARCH-FIX-02 / SE-02C
  automatically. Return to the SE control window for the next task.**

### SE-02B Opportunity Capture + Attribution — ACCEPTED / COMPLETE

- 专项 SE｜Strategy & Trading Edge 的第二个 Implementation Acceptance Batch。
- Independent Review（final）= `PASS`；Human Acceptance = `CONFIRMED`（2026-09-12）；
  Human-Accepted reviewed branch tip = `6ce0c9214f552c0173e1f925315102506c3e9078`。
- Task Base / Accepted Main before = `af81414160248c97f59a63b31fe615ea8ae14bbe`；
  Accepted Main after = Final Closeout Commit。
- accepted lineage（仅 fast-forward，无 rebase / squash / force）：
  `af81414 → f261766（feat）→ 7e86757（FIX-01 fix）→ b8a5fe3（FIX-01 docs）
  → 0b8a275（FIX-02 fix）→ 6ce0c92（FIX-02 docs）→ Final Closeout Commit`；
  evidence branch `se-02b-opportunity-capture-attribution` 保留、未删除。
- 已验收能力：① G2 SETUP Opportunity Capture（与 durable G2 facts 同一 PostgreSQL 事务；
  atomic / fail-closed；immutable / append-only；遵循 SE-02A identity + hash + revision 契约）；
  ② Attribution（`Opportunity → AI → Plan → Risk → Execution → Economic Result`；append-only；
  exact authority / reason；显式 AI family selection；deferred LIMIT per-order restart-safe 归因）。
- Acceptance blocker 闭合链：SE-02B-FIX-01 关闭 P0-2 / P0-3 / P0-4 + P1（P0-1 判 CHANGES
  REQUIRED）⇒ SE-02B-FIX-02 终局关闭 P0-1（`OK` 要求 `data_quality == FRESH`；payload 拆
  `supplied_quote` + `accepted_reference`；`RUNTIME_CAPTURE_PAYLOAD_VERSION` `v2 → v3`）。
- 验证证据（历史门）：SE-02B `focused 46`（capture 15 + attribution 31）；SE-02A `88`；
  G2/G3/G4 `123`；full backend `313 passed, 1 warning`；Ruff / compileall / `git diff --check` PASS；
  无新 migration（head 仍 `20260911_0005`）。Final Closeout 复验：`git diff 6ce0c92..HEAD`
  仅文档 / 状态文件、`git diff --check` rc=0、定向 smoke `46 passed`、`alembic heads` 单 head。
- Closeout 为 docs-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Contract changed = NO`。
- Claim 边界：**不得**由此声明 SE-02C / SE-02D / Forward Outcome Calculator / MFE-MAE / forward
  returns / family aggregation / expectancy / KEEP-DOWNWEIGHT-KILL / Real AI Edge / Live 完成
  （均 `NOT STARTED`）。
- 详见 `dev_log/2026-09-12-se-02b-final-acceptance-closeout.md` 与 `PROJECT_STATE.md`
  「SE-02B Result」。
- 收尾后的下一步：**SE-02B CLOSED. Do not start SE-02C automatically. Return to the SE control
  window for the next task.**

### SE-02A Contracts + Additive Persistence — ACCEPTED / COMPLETE

- 专项 SE｜Strategy & Trading Edge 的第一个 Implementation Acceptance Batch。
- Independent Review = `PASS`；Human Acceptance = `CONFIRMED`（2026-09-11/12）。
- reviewed implementation source = branch `se-02a-contracts-additive-persistence` @ `0c206c9`
  （**未改写**，远端保留）；历史集成候选 `se-02a-final-integration` @ `9998e1b`（**保留、未 merge**）；
  最终收编经 refresh integration branch `se-02a-final-integration-refresh`。
- accepted lineage（仅 fast-forward）：
  `b3ac21b → 2e7bf6a（merge reviewed source）→ 134aec5（refresh 文档）→ Final Closeout Commit`。
- Accepted Main before = `b3ac21b89e11490a0760f560bc099b9acf91ff48`；Accepted Main after = Final
  Closeout Commit。
- Final Closeout 最小充分复验（规范解释器 `py -3.14`）：SE-02A focused `88 passed`（contracts 62 +
  persistence 26）、N01-C focused `6 passed`、full backend `267 passed`（独占窗口）、
  `alembic heads` 单 head `20260911_0005` 且 `g5/replay.py::schema_head` 同值、
  Ruff `All checks passed!` / compileall rc=0 / `git diff --check`（工作树 + `b3ac21b..HEAD`）rc=0。
- Closeout 为 docs-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Contract changed = NO`。
- Claim 边界：**不得**由此声明 SE-02B / runtime opportunity capture / Forward Outcome Calculator /
  MFE/MAE / Expectancy / KEEP-DOWNWEIGHT-KILL / Real AI Edge 完成（均 `NOT STARTED`）。
- 详见 `dev_log/2026-09-11-se-02a-edge-contracts-persistence.md` 与 `PROJECT_STATE.md`
  「SE-02A Result」。
- 收尾后的下一步：**RETURN TO N01 MAIN WINDOW → N01-6｜15-minute Short Runtime Smoke**
  （本 Closeout 不开始 N01-6）。

### N01-6 15-minute Short Runtime Smoke — ACCEPTED / COMPLETE

- Task Base / Accepted Main before = `ab4bf297dff42a673d8dbf204dee8e4c0574aff9`；branch =
  `n01-6-15m-runtime-smoke`；isolated worktree = `E:\Documents\MarketPulse-AI-n01-6`。
- Independent Review = `PASS`；post-review docs-only Incremental Re-Review（`db3a0dc..3f591a7`，
  devlog-only）= `PASS`；Human Acceptance = `CONFIRMED`；Reviewed HEAD =
  `3f591a7694bf9e03dda53708a92c048dcea75fb3`。
- Validation-only harness `scripts/verify_n01_6_runtime_smoke.py`（1309 行，不进 pytest 默认集合）：
  真实 OKX 公共行情（BTC-USDT + ETH-USDT SPOT，`trades` + `bbo-tbt`）+ 真实 disposable PostgreSQL
  （`marketpulse_n01_6_05c4a7071a16`，drop 后残留 `0`），让已验收生产运行时组件
  （`ScannerPipeline → OpportunityScanner → EventRuntime → PostgresG2Repository` +
  `SafetyRuntime` / `PositionProtectionService` / `SystemRiskGate`，`reevaluation_enabled=False`）
  连续运行 **`900.143 s`**。
- Acceptance Gate（ACCEPTANCE）：`result=PASS`、`failures=[]`、checks `37/37 true`；normalized 事件
  `24540`（BTC 2376 trades / 8203 bbos；ETH 2883 trades / 11078 bbos）；queue 高水位 `0`、
  inflight 高水位 `1`、dedupe 峰值 `4250`（cap 8192）、worker_exceptions `0`；RSS 峰值
  `114.758 MB`；`stale_periods=[]`；max other client sessions `0`；primary 未被升级
  （`20260905_0004`）。受控 `LIVE_PAPER` BTC-USDT SPOT LONG：entry ask `77793.8` + 5 bps =
  `77832.6969`，exit bid `77838.6` − 5 bps = `77799.6807`（`MANUAL_CLOSE`），trade `CLOSED`，
  cash `9999.7576`，reserved `0`，reconciliation `12/12` invariants true。
- Final Acceptance Closeout Gate：focused `16 passed`；collect `267`；full backend
  `267 passed, 1 warning`（连续 PG 会话采样 **114** 样本 + 前后进程扫描，无外来写者）；
  Ruff `All checks passed!` / compileall rc=0 / `git diff --check`（工作树 + `ab4bf29..HEAD`）rc=0。
  四项不变：`Production Changed = NO` / `Tests Changed = NO` / `Harness Changed = NO` /
  `Migration Changed = NO`。
- Accepted lineage（仅 fast-forward，无 rebase / squash / force）：`ab4bf29 → db3a0dc → 3f591a7
  → Final Closeout Commit`；Accepted Main after = Final Closeout Commit；evidence branch
  `n01-6-15m-runtime-smoke` 保留、未删除。
- Claim 边界：N01-6 验收**不等于** Continuous Runtime 全量验收 / 2h soak / 12h soak / 7×24 Runtime /
  Integrated Runtime Host。`N01-7` / `N01-8` / Integrated Runtime Host 当时仍 `NOT STARTED`
  （N01-6 收尾时；其后 `N01-7` / `N01-7-R01` 与 `N01-8` 均已分别于 2026-09-14 经 Human
  Acceptance 收编为 `ACCEPTED / COMPLETE`，Integrated Runtime Host 仍 `NOT STARTED`；
  `N01 overall` 其后亦已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`）。详见
  `dev_log/2026-09-12-n01-6-15m-runtime-smoke.md`。

### N01-7-F01 Durable Protection Snapshot — ACCEPTED / COMPLETE

- Task: `N01-7-F01-I1-C1`｜Integration Evidence Closeout（**非**新实现；docs/state-only）。
- branch = `n01-7-f01-latest-main-integration`；isolated worktree =
  `E:\Documents\MarketPulse-AI-n01-7-f01-latest-main-integration`；integration merge commit =
  `ddf39f2ac11ae53fb18c493f5bcc91974779bc3a`（**true merge**；parent1 = 最新 main `1579707`，
  parent2 = 已复审 F01 源 `c0ce0af`；`Reviewed Source Preserved = YES`，无 rebase / squash）。
- 唯一冲突文件 `backend/src/marketpulse/g3/service.py` 按 **语义并集** 解决（SE-02B attribution
  接线 + F01 protection 接线共存，无冲突残留）；migration head = `20260912_0006`（单 head，
  `down_revision = 20260911_0005`）。
- I1 集成验证（既有证据，本批**未**重跑）：F01 migration gate = `PASS`；N01/G3/G4 + SE-02A/SE-02B
  定向 = `271 passed`；full backend = `341 passed, 1 warning`；ruff / compileall /
  `git diff --check` = PASS。集成测试跑在隔离 PostgreSQL `:5433`。
- **E1 归因 = `FOREIGN WRITER CONFIRMED`**：原始 I1 shared-primary `before == after` 指纹门
  = **`INVALIDATED BY ENVIRONMENT`**（并发外来窗口 `se-arch-fix-01` 无 `DATABASE_URL`/`.env`，
  静默写共享主库 `:5432/marketpulse`）；**既非 PASS，也非 product failure**，且未放松该门规则。
  原始证据在外部 `E:\Temp\n01-7-f01-i1-e1\`，**未**入库。
- Task（本批）：`N01-7-F01-A1`｜Final Human Acceptance + Main Integration（Final Acceptance
  Closeout；**非**新实现；docs/state-only）。
- Human Acceptance = **`CONFIRMED`**（人工原文「确认 N01-7-F01 Human Acceptance，并执行 Final
  Main Integration」）；Final Independent Review = `PASS`；R2 Independent Re-Review = `PASS`；
  Integration Review = `PASS`。
- 状态：**`N01-7-F01-I1 = INTEGRATED / VERIFIED`**（历史）；**`N01-7-F01 = ACCEPTED /
  COMPLETE`**（2026-09-13；已 fast-forward only 收编 `main`）；**`N01-7 = NOT STARTED / READY
  TO RESUME`**（N01-7-F01 收尾时；其后 `N01-7` / `N01-7-R01` 已于 2026-09-14 经 Human
  Acceptance + Final Main Integration Closeout 转为 `ACCEPTED / COMPLETE`）；**`N01-8 = ACCEPTED /
  COMPLETE`**（N01-7-F01 收尾时仍 `NOT STARTED`；其后于 2026-09-14 经 Human Acceptance + Final
  Acceptance Closeout 收编，见本节顶部 N01-8 条目）；**`Integrated Runtime Host = NOT STARTED`**。
- accepted lineage（仅 fast-forward，无 merge commit / rebase / squash / force）：
  `ddf39f2 → 7c0ea7d → Final Acceptance Closeout Commit`。
- `Production Code Changed after ddf39f2 = NO` / `Tests Changed = NO` / `Migration Changed = NO`;
  Final Acceptance Closeout delta = docs/state only（本 devlog + `PROJECT_STATE.md` +
  `AI_CONTEXT.md` + `DECISIONS.md` 最小决策引用）。详见
  `dev_log/2026-09-13-n01-7-f01-final-acceptance-closeout.md` 与
  `dev_log/2026-09-12-n01-7-f01-latest-main-integration.md`。
- 边界：本验收 **不**启动 N01-7 2h soak / N01-8 / Integrated Runtime Host；本验收不构成
  `N01 overall` Acceptance（`N01 overall` 其后已于 2026-09-14 经 N01 Overall Final
  Acceptance Closeout 转 `ACCEPTED / COMPLETE`）。重启 N01-7 前须做一次全新 Repository
  Truth rebuild。

### N01-C Restart / Recovery / Reconciliation — ACCEPTED / COMPLETE

- Task Base / verified remote `main` = `6cc4c36e11c380f638872598e4766a4436d0d255`；branch =
  `n01-c-restart-recovery-reconciliation`；isolated worktree =
  `E:\Documents\MarketPulse-AI-n01-c`。
- Validation uses a disposable real PostgreSQL database plus separate Process A / Process B Python
  processes. Process B rebuilds engine/session/services only from durable PostgreSQL facts; it does
  not receive Process A objects or memory. It covers execution-gap audit, detector-only official
  reconciliation, recovered BUY revalidation, protection HOLD/current-BBO SL exit, SAFE_MODE,
  PAUSED intent, BBO failure fail-closed, idempotency and resource cleanup.
- Final Gate: Independent Review = `PASS / READY FOR HUMAN ACCEPTANCE`; Human Acceptance =
  `CONFIRMED`; focused `6 passed`; lifecycle `6`; N01-B `4`; G2 `30`; G3 `16`; G4 `77`; full
  backend `179 passed, 1 warning` under exclusive writer evidence; Ruff / compileall / diff-check PASS.
  `Production Code Changed = NO`.
- At N01-C closeout, N01 overall remained unaccepted（其后已于 2026-09-14 经 N01 Overall
  Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）. N01-7 2h, N01-8 12h, Continuous Runtime and
  Integrated Runtime Host were `NOT STARTED` / unproven at N01-C closeout（N01-6 15m 已完成
  Final Acceptance Closeout = `ACCEPTED / COMPLETE`；其后 `N01-7` / `N01-7-R01` 与 `N01-8` 均已
  分别于 2026-09-14 经 Human Acceptance 收编为 `ACCEPTED / COMPLETE`，`Integrated Runtime
  Host` 仍 `NOT STARTED`）。See
  `dev_log/2026-09-11-n01-c-restart-recovery-reconciliation.md`.

### N01-B OKX Reconnect / Freshness + Paper Safety Continuity

- Task Base / verified remote `refs/heads/main` = `a48673404abe256d0adb07c8139b129a54b4e7ce`；
  branch = `n01-b-okx-paper-safety-continuity`；accepted validation lineage =
  `fc168c1` → `26688a2`；isolated worktree = `E:\Documents\MarketPulse-AI-n01-b`。
- `N01-B = ACCEPTED / COMPLETE`（Independent Review `PASS`；Human Acceptance `CONFIRMED`；
  `N01-3 = ACCEPTED`、`N01-4 = ACCEPTED`；accepted lineage 已 fast-forward 至 `main`）。
  N01-3 真实 OKX SPOT metadata / 真实 `bbo-tbt` + `trades` / BTC-USDT 与 ETH-USDT 受控真实重连 /
  FRESH → CONTROLLED STALE → FRESH 三段边界；N01-4 `LIVE_PAPER` paper safety continuity
  （disposable PostgreSQL）：stale 下 `CORE_MARKET_DATA = UNAVAILABLE` + `CORE_DATA_STALE`
  incident，risk-increasing BUY 经 `SystemRiskGate` fail-closed（`RUNTIME_STATE_DATA_DEGRADED`），
  无 fabricated Fill / exit / position mutation，SELL 风险降低语义保持不被 stale 禁止但要求
  executable fresh BBO；post-reconnect real fresh BBO 恢复 HEALTHY 并 RESOLVE incident；
  final reconciliation PASS。
- Validation-only 产物：`backend/tests/test_n01_okx_paper_safety.py`（离网 deterministic）
  与 `scripts/verify_n01_b_okx_paper_safety.py`（真实 OKX，需显式执行）。两者均**不是**产品
  入口，不得被当作 Runtime Host 或 Smoke 使用。
- `Production code changed = NO`；无 schema / migration / Runtime Host / G3–G5 业务语义修改。
- 环境提示：本机 sandbox 注入的 `HTTP(S)_PROXY` 无法隧道到 OKX（502），本地 DNS 对
  `www.okx.com` 返回链路本地黑洞；真实 OKX 脚本在自身进程内清空 proxy env 后可正常验证。
  该现象属环境（`N01-B-E01`），不是产品缺陷，也未修改任何 production code。
- Final Gate Observation（非阻塞）：N01-A 既有测试
  `test_n01_twenty_real_postgres_lifecycles_...` 在 `engine.dispose()` 后立即断言
  PostgreSQL `sessions == baseline`，存在偶发假失败（当日 5 次执行中 1 次；单独 3/3、
  全量 2/2 PASS）。该现象已由 N01-VAL-FIX-01 复现并定位（`N01-VAL-F01`），见下节；
  "测试侧时序抖动"为其**修正前**的假设性分类。

### N01-VAL-FIX-01 PostgreSQL Lifecycle Evidence Stability

- 状态：`ACCEPTED / COMPLETE`（Consolidated Final Acceptance Closeout 2026-09-11 完成；
  Independent Review = `PASS`；Human Acceptance = `CONFIRMED`）；
  branch = `fix/n01-val-postgres-lifecycle-evidence`；commit = `67b0cb5`；
  Task Base / verified `refs/heads/main` = `e0dab188e55c32b7607c18a66644d25449dc2236`；
  isolated worktree = `E:\Documents\MarketPulse-AI-n01-val-fix-01`。
- `N01-VAL-F01` 根因（已在 accepted `main` 上复现，并捕获到具体身份）：原 gate 只按
  `datname` 统计 `pg_stat_activity`，把**服务端维护进程**当成了 harness 连接——捕获行是
  `backend_type='autovacuum worker'`、`usename=null`、`application_name=''`、
  `last_query='autovacuum: ANALYZE pg_catalog.pg_class'`。既**不是**连接泄漏，也**不是**
  服务端连接关闭可见窗口（实测客户端连接关闭可见窗口 ≤8.3 ms，160+ cycle 无残留）。
- 修复：每 cycle 唯一 `application_name` 归属 + 按 `backend_type` 拆分 client/server +
  有界最终条件等待（`client_sessions == 0`，hard deadline 1.0 s）+ 注入泄漏负向对照。
  **未**重新引入 `baseline + 1` 容差，**未**用 sleep 代替清理证明；EventRuntime
  task/queue/inflight/dedupe/worker_exception gate 强度不变。
- `Production code changed = NO`；仅改
  `backend/tests/test_n01_runtime_resource_lifecycle.py` 与 dev_log，外加 `PROJECT_STATE.md` /
  `AI_CONTEXT.md` 最小状态同步。详见
  `dev_log/2026-09-10-n01-val-fix-01-postgres-lifecycle-stability.md`。
- 边界：本 Fix **不构成** N01-C 开窗，也**不改变** `N01-A` / `N01-B` 的 `ACCEPTED` 结论。

### N01-VAL-FIX-02 N01-B PostgreSQL Activity Evidence Stability

- 状态：`ACCEPTED / COMPLETE`（Consolidated Final Acceptance Closeout 2026-09-11 完成）；
  branch = `fix/n01-val-n01b-postgres-activity-evidence`；
  Task Base = `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2`（FIX-01 已评审 commit，其 parent =
  Accepted Main `e0dab188e55c32b7607c18a66644d25449dc2236`，形成
  `e0dab188 → 67b0cb5 → FIX-02 → Final Closeout` 线性）；
  isolated worktree = `E:\Documents\MarketPulse-AI-n01-val-fix-02`。
- `N01-VAL-F02` 缺陷：`backend/tests/test_n01_okx_paper_safety.py` 的两个 PostgreSQL lifecycle
  测试用 `datname`-only 聚合（`SELECT count(*) ... FROM pg_stat_activity WHERE datname = ...`）
  配合 `activity_after == baseline` 证明 client connection cleanup，属错误 ownership model
  （`datname` 无法区分 harness client 与 server-owned maintenance backend）。
- 修复：每个测试唯一 `application_name`（`marketpulse-n01-b-owned-*`）+ observer
  （`marketpulse-n01-b-observer`）连接 **primary 库**不污染被测库 + 按 `backend_type` 拆分
  `client_sessions` / `server_sessions` + 有界最终条件等待（`client_sessions == 0`，
  hard deadline 1.0 s，poll 2 ms；尺度**沿用** FIX-01 实测 ≤8.3 ms，未新造尺度）+
  极小 tests-only 注入泄漏负向对照。**未**引入 `baseline + 1`，**未**用 sleep/retry 代替清理证明。
- 历史失败边界（必须准确）：8 次 full suite 中 1 次
  `test_n01_b_freshness_boundary_...` FAIL 且**无 traceback**；本窗口 12 次文件级 + 1 次 full
  suite 有界复现**未再捕获** → `single historical full-suite failure not independently
  recaptured`。Fix 依据是**源码缺陷 + FIX-01 的既有捕获身份**，不主张该断言已被复现。
- `Production code changed = NO`；`scripts/verify_n01_b_okx_paper_safety.py` 未改动
  （`_database_activity` 保留为 ownership-aware 诊断接口，返回键向后兼容）。
- 本 Fix 已随 Consolidated Final Acceptance Closeout 收尾：`N01-VAL-FIX-01/02/03` 三者
  `ACCEPTED / COMPLETE` 并 fast-forward 收入 `main`；**未**开 N01-C，也**不改变**
  `N01-A` / `N01-B` 的 `ACCEPTED` 结论。详见
  `dev_log/2026-09-10-n01-val-fix-02-n01b-postgres-activity-evidence.md`。

### N01-VAL-FIX-03 G4 Protection / Limit-Fill Assertion Uniqueness

- 状态：`ACCEPTED / COMPLETE`（Consolidated Final Acceptance Closeout 2026-09-11 完成）；
  branch = `fix/n01-val-g4-order-assertion-uniqueness`；
  Task Base = `14f387ac88af1ecd377fcd181c90b109ee361754`（FIX-02 已评审 commit），形成
  `e0dab188 → 67b0cb5 → 14f387a → 13049a0 → Consolidated Final Acceptance Closeout` 线性；
  isolated worktree = `E:\Documents\MarketPulse-AI-n01-val-fix-03`。
- `N01-G4-F01`（原「既有 flake」）分类 = **Case B — Test Assertion Scope / Ambiguous Read
  Defect**，**非** production concurrency defect。缺陷：目标测试
  (`test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`)
  用非唯一谓词 `PaperOrderRecord.plan_id == <pending plan>` + `Session.scalar()` 读取 pending BUY
  状态；protective exit SELL 与 pending LIMIT BUY 合法共享同一 `plan_id`
  （`persist_trade_plan` REPLACE 旧 ACTIVE plan ⇒ 待成交 BUY plan 为唯一 ACTIVE ⇒
  `_close_position_in` 以该 plan_id 建 MARKET SELL），`Result.scalar()` 多行静默取首行、query 无
  `ORDER BY` ⇒ 行序=物理堆序，负载相关。
- 修复：pending BUY 改用唯一 identity **`order_id`**（先以 `plan_id + side=BUY +
  order_type=LIMIT` 唯一谓词取得一次并断言 `len == 1`，随后一律
  `session.get(PaperOrderRecord, order_id)`），断言强化为 exact pending BUY
  (`side=BUY` / `order_type=LIMIT` / `status=CANCELLED` / `reserved_cash==0`) + protective SELL
  (`side=SELL` / `status=FILLED`) + `protection.cancelled_order_ids` + `position.quantity==0` +
  `fills==[]` + 仅原始 BUY entry fill + reconciliation PASS。**未**用 `ORDER BY` / `LIMIT 1`
  规避，**未**改 production code / schema / locking。同构 tests-only ambiguity 一并最小修正
  `test_stop_loss_cancels_pending_add`；并发 witness 完整保留。
- 验证：目标测试 `20/20`；`test_group4.py` `77 passed` ×2；FIX-01 `6 passed`、N01-B `4 passed`、
  G2 `30`、G3 `16`；full backend `173 passed` ×2（**带 DB 客户端会话监控**，全程无外来写者）；
  Ruff / compileall / `git diff --check` PASS。`Production code changed = NO`。
- 环境级约束（`KNOWN TEST-ENVIRONMENT CONSTRAINT` / NON-PRODUCTION / NON-BLOCKING）：全量套件
  共用**单一 PostgreSQL 库**且测试整表清空 `REPLAY` 行 ⇒ 并发会话必互相破坏（签名
  `PLAN_REPLACED`）；本窗口 full-suite 门首跑被另一 WorkBuddy 会话的 `pytest backend/tests`
  污染，收尾门已以「进程扫描 + `pg_stat_activity` 客户端会话采样」建立 exclusivity 证据后
  取 2 次连续 PASS。
- 本 Fix 已随 Consolidated Final Acceptance Closeout 收尾：`N01-VAL-FIX-03 = ACCEPTED / COMPLETE`，
  与 FIX-01 / FIX-02 一并 fast-forward 收入 `main`；**未**开 N01-C，也**不改变**
  `N01-A` / `N01-B` 的 `ACCEPTED` 结论。详见
  `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md`。

### N01-A Deterministic Runtime + Resource Lifecycle

- Task Base / verified `origin/main` = `bc635787eafdf88fdc8e5810109452b5e394a076`；branch =
  `n01-a-runtime-resource-lifecycle`。
- `N01-A = ACCEPTED / COMPLETE`：N01-A-F01 的 deterministic
  same-instrument queue-get / persist-boundary witness 保留；N01-A-F02 恢复每 cycle / final activity
  strict baseline equality；F01/F02 = `CLOSED / PASS`；其余 validation-only test 覆盖 bounded queue/backpressure、
  finite worker、同 `instrument_id` 串行、BTC/ETH bounded parallelism、recent/evicted/concurrent
  duplicate、failure retry、cancellation、20 个 real PostgreSQL lifecycle、task/queue/inflight/retained
  collection/session evidence。`backend/src` / schema / migration / Runtime Host 均未修改。
- R01 / R02 / R03 与 PostgreSQL durable duplicate TOCTOU 在 verified Accepted Main 上保持关闭。
  未执行真实 OKX reconnect 或 15m / 2h / 12h Soak；N01 Continuous Runtime / Soak 仍未证明、未验收。
  N01-B 未由本 Closeout 提前开始。（Historical N01-A closeout statement; N01-B 后续已单独开窗，
  经 Independent Review `PASS` + Human Acceptance 后为 `ACCEPTED / COMPLETE`，见第 6 节。）

### FG-E Reconciliation Snapshot Consistency

- FG-A、FG-B、FG-C、FG-D = `ACCEPTED / COMPLETE`；FG-A～FG-E Fix Program = `COMPLETE`。
- FG-D — G2 Runtime Determinism & Failure Atomicity：F07、F09、F10、F11 =
  `ACCEPTED / FIXED`；Accepted Implementation =
  `b08c2ea1eef4e2780a98b68dfaa2d5954af7d42b`。
- FG-E = `ACCEPTED / COMPLETE`；N02 = `ACCEPTED / FIXED`：Human Acceptance confirmed；accepted implementation
  `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`。G4 `reconcile()` 在同一 read-only
  `REPEATABLE READ` PostgreSQL transaction 内调用 G3 accounting，并加载 G4 extended
  facts；standalone G3 reconciliation 也使用自己的同类只读 snapshot。真实 PostgreSQL
  并发回归已验证报告不会跨 `ACTIVE → REPLACED` plan commit 撕裂。未改 schema、migration、
  SystemControlService / RecoveryManager transaction boundary 或 G3 accounting semantics。
  Initial Formal Review = `CHANGES_REQUIRED / NOT ACCEPTED`（historical; superseded by
  Acceptance Fix #1/#2/#3, Independent Review PASS and Human Acceptance）。Acceptance Fix #1 仅关闭 real G4
  transaction-state evidence：production G4 → G3 session 参数路径内断言
  `transaction_isolation=repeatable read` 与 `transaction_read_only=on`。其余 acceptance
  evidence 包括 account/order torn-read race、standalone G3 RR/RO、standalone G3 torn-read
  race、true durable corruption detection，以及 transaction identity / failure cleanup
  evidence。Acceptance Fix #2 已补 G4→G3 same-session/same-transaction identity、G4
  account/order torn-read race，以及 standalone G3 RR/RO、account/order torn-read race、
  true durable corruption detection、failure cleanup evidence。Acceptance Fix #3 已验证 G4
  durable corruption detector-only propagation，以及 actual G4 outer transaction 的 failure
  cleanup、immediate independent writer 与同生命周期 fresh reconciliation。N02-1～N02-14
  evidence 已完成，N02-1～N02-14 = PASS；Final Acceptance Closeout 已将 accepted lineage
  fast-forward 至 `main`。FG-E historical branch 保留为证据。
- N01-A = `ACCEPTED / COMPLETE`；N01-B = `ACCEPTED / COMPLETE`；N01-C = `ACCEPTED / COMPLETE`；
  N01-6 = `ACCEPTED / COMPLETE`（见第 6 节）；N01 overall = `ACCEPTED / COMPLETE`（2026-09-14）；N03 = `DEFERRED`，G6 = `NOT STARTED`。
- C02 / C03 = `UNMAPPED / NOT AUDITABLE`；repository 中无法恢复原始 finding，需原始
  master audit source 后才能重新分类；不属于当前已证明的 P0/P1 blocker。

- G5-0 `ACCEPTED`：`AI_CONTEXT.md` 为上下文入口；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- G5-1 `ACCEPTED`：Deterministic Replay Foundation 已验收，implementation acceptance basis = `34da62a0cc9dbe95b95faadb770fbd06179a6975`。
- G5-2 Trading Replay Integration = `ACCEPTED`（Implementation Acceptance Basis = `2a7d0c858c70f21215a090ee3b583d341cfd84b4`；详见 `dev_log/2026-09-06-group5-2.md`「Formal Acceptance Record」）。
- G5-3 End-to-End Determinism = `ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Implementation Acceptance Basis = `f4c07333600f605cbcc5e34b591659feb1b1f318`；Review Fix #1 = VERIFIED；详见 `dev_log/2026-09-06-group5-3.md`「Formal Acceptance Record」）。
- G5-4 Deterministic Replay Evaluation = `ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Production Implementation Basis = `8678b2927a2d029ac0767e49acc9e0732c329bfa`；Self Review Fix #1 Evidence = `fe610c1f23457ff11f2d5c8654e9de0aec4ff289`；branch `g5-replay-evaluation` = historical accepted branch；详见 `dev_log/2026-09-06-group5-4.md`）。
  - 关键事实源：`backend/src/marketpulse/g5/evaluation.py`（新增）、`backend/src/marketpulse/g5/replay.py`（additive `evaluation` 字段与评估步骤）、`backend/src/marketpulse/g5/canonical.py`（未修改）。
  - G5-4 冻结边界：不持久化 Evaluation Report、不引入 `replay_run_id` / `backtest_id`、不新增 schema、
    不修改 G3 accounting semantics、不做 MFE/MAE/drawdown/equity curve/win rate/expectancy/R-multiple/Sharpe/Sortino/profit factor。
- G5 overall = `ACCEPTED / COMPLETE`（G5-4 已于 2026-09-06 Formal Acceptance Closeout）。Next Group Design = `NOT STARTED`；Next Group name/number = `NOT YET APPROVED`。
- 具体 In Progress / Blocked 状态见 `PROJECT_STATE.md`。

## UI-RD01 Accepted Design Pointer

- Current I02 requirement final freeze: `UI-RD01-I02-REQ-01 = ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`（Human Freeze = `CONFIRMED — 2026-09-19`；Independent Re-Review = `PASS`；Human-Frozen Reviewed Candidate = `b91d635de04c7444257fcc17069f418e3d3919e7`；Finding `I02REQ-RR-P1-01 = CLOSED / PASS`；本条目**取代**上文 R1 / persistence pointer 的当前状态含义）。artifact = `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`（final status = `ACCEPTED / FROZEN`；59 个编号章节语义零变更）；final accepted baseline = 集成后 `main`（closeout branch = `ui-rd01-i02-requirements-final-freeze`，`FAST-FORWARD ONLY`）。I02 拆分 = `I02-A` MarketScanner（`GET /api/v1/product/market-scanner`）/ `I02-B` Opportunity（`GET /api/v1/product/opportunities`、`/api/v1/product/opportunities/{opportunity_id}`）；`UI-RD01-I02 implementation = NOT STARTED`、`I02-A = NOT STARTED`、`I02-B = NOT STARTED`；**本 Freeze 不启动实现**，I02-A 需另开独立 Formal Task。边界：`CR-03` / `CR-05` 仅在 **I02-B** 生效（accepted contract 已冻结，尚未实现）；`Schema` / `Migration` / `Index = ZERO CHANGE`；**禁**静默 `FORWARD_PAPER → HISTORICAL_REPLAY` fallback。`I03–I05 = NOT STARTED / NOT AUTHORIZED` 不变；`PRE-01B-I2` / Real AI / live `G2→G3` / Gate A/B/C / Live 均未激活。完整语义见 artifact；详见 `PROJECT_STATE.md`「UI-RD01-I02 Requirement Final Freeze Result」。

- Current Final Acceptance state: `UI-V1-D01-AMEND-01-CR02-FIX-01 = ACCEPTED / COMPLETE`；`UI-V1-D01-AMEND-01-CR02-FIX-01-R2 = ACCEPTED / CLOSED`；CR-02 Foundation remediation = `ACCEPTED / COMPLETE`；Independent Re-Review = `PASS`；Human Acceptance = `CONFIRMED — 2026-09-18`；Human-Accepted Reviewed Candidate = `b82076102b45a780a9cbb44e00923fa768bfe91`。`CR02-IR-P1-01 = CLOSED`；`CR02-RR-P1-01 = CLOSED`；`CR01-IR-P2-01 = RESOLVED INCIDENTALLY / TEST-FIXTURE ONLY`（CR-01 production behavior unchanged）。CR-01 = `ACCEPTED / COMPLETE`；CR-03 / CR-04 / CR-06 = `NOT APPLICABLE YET`；CR-05 = `REQUIRED / NOT STARTED`；`UI-RD01-I01 = ACCEPTED / COMPLETE`；`UI-RD01-I02–I05 = NOT STARTED / NOT AUTHORIZED`。No implementation/test/backend/generated/dependency/router changes after the reviewed candidate; main integration is fast-forward-only.

- Current CR-02 R2 update (supersedes the R1 record below): `UI-V1-D01-AMEND-01-CR02-FIX-01-R2 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`（Parent Reviewed Candidate = `5684b657cbecd28573174fd73de7963a384900ca`；Task Base = `dd6dce564122a7ad8ea912ba1291f2d3625a3a46`；branch = `ui-amend-cr02-session-ownership`）。`CR02-RR-P1-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`：provider active/disposed fence now uses `useLayoutEffect`, so real unmount commit synchronously deactivates the old client without altering local `Symbol` generation semantics or transport ownership. The cross-Provider regression releases old `401` immediately after rerender commit and preserves the new token, route and Query cache; StrictMode current `401` remains authoritative. CR-02 Foundation remediation = `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`; CR-05 = `REQUIRED / NOT STARTED`; no backend/OpenAPI/generated.ts/dependency/router change.

- Current CR-05 update: `UI-V1-D01-AMEND-01-CR05-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`；CR-05 shared Product Read contract remediation = `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（Task Base = `71f8c4ec52323c07f21c6c8434f9010ea04cf935`；branch = `ui-amend-cr05-trace-node-state`）。`TraceNodeState` now contains exactly `PRESENT`, `NOT_OCCURRED`, `NOT_REACHED`, `NOT_YET_DUE`, `NO_PROVABLE_RECORD`, and `CAPABILITY_NOT_INTEGRATED`; focused regression proves distinct `NOT_REACHED` / `NOT_YET_DUE` values and `TraceNodeDTO` JSON serialization. No classifier, endpoint, consumer, frontend trace/maturity, OpenAPI/generated.ts, schema, or dependency change. CR-01 = `ACCEPTED / COMPLETE`；CR-02 = `ACCEPTED / COMPLETE`；CR-03 / CR-04 / CR-06 = `NOT APPLICABLE YET`；`UI-RD01-I01 = ACCEPTED / COMPLETE`；`I02–I05 = NOT STARTED / NOT AUTHORIZED`；not an acceptance/complete declaration.

- Current CR-02 update (supersedes the earlier historical CR-02 planning record in this section): `UI-V1-D01-AMEND-01-CR02-FIX-01-R1 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`（Task Base = `dd6dce564122a7ad8ea912ba1291f2d3625a3a46`；Parent Reviewed Candidate = `edf07d7d52c64e9c633f64603d887acccf7c9bfe`；branch = `ui-amend-cr02-session-ownership`）。Provider-local ephemeral `Symbol` generation advances only on sign-in and current-session teardown. Provider active/disposed state is separate: an unmount only deactivates its client lifetime, while transport-local request-id ownership permits protected `401` teardown only for current generation plus an active Provider. Thus StrictMode synthetic Effect cleanup/setup cannot stale-fence a held current-session request, but a real old Provider cannot mutate a new shared QueryClient. StrictMode current-session, G1 → G2 late-401, successful-sign-in, and cross-Provider-lifetime regressions preserve the required token/route/cache behavior and originating `UnauthorizedError`; no generation/lifecycle value is persisted or sent to backend. `CR01-IR-P2-01 = RESOLVED INCIDENTALLY / TEST-FIXTURE ONLY`; CR-01 production behavior unchanged. CR-05 = `REQUIRED / NOT STARTED`; `UI-RD01-I01 = ACCEPTED / COMPLETE`; `I02–I05 = NOT STARTED / NOT AUTHORIZED`; no backend/OpenAPI/generated.ts/RuntimeHost/router/dependency change.

- `UI-RD01 = ACCEPTED / FROZEN`；artifact：`docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md`。
- `UI-V1-D01-AMEND-01 = ACCEPTED / FROZEN`（Human-confirmed post-freeze amendment）；`UI-V1-D01-AMEND-01-PERSIST = ACCEPTED / COMPLETE`（Independent Re-Review = `PASS`；Human Acceptance = `CONFIRMED — 2026-09-18`；Human-Accepted Reviewed Candidate = `73cae6a47e147ec655f660cecf235864ffdbbb9c`，immutable）。`UI-V1-D01` / `UI-RD01` = `ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`。权威 Amendment：`docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md`。`UI-V1-D01-AMEND-01-CR01-FIX-01 = ACCEPTED / COMPLETE`（Independent Review = `PASS WITH NON-BLOCKING FINDING`；Human Acceptance = `CONFIRMED — 2026-09-18`；Human-Accepted Reviewed Candidate = `42a707a587b3b6b8cb2dd48830753a8a53bda2f0`，immutable）；CR-01 typed readiness Foundation remediation = `ACCEPTED / COMPLETE`；`CR01-IR-P2-01 = REMAINS / NON-BLOCKING`（本 closeout 不修复）。CR-02 session-generation 的 current Foundation remediation = `REQUIRED / NOT STARTED`；CR-03 / CR-04 / CR-06 current remediation = `NOT APPLICABLE YET`，future relevant implementation must comply；CR-05 current shared Product Read contract remediation = `REQUIRED / NOT STARTED`，因为 I01 已实现的 `backend/src/marketpulse/api/product/models.py::TraceNodeState` 缺少 `NOT_YET_DUE`。`UI-RD01-I01 = ACCEPTED / COMPLETE` 保持历史 accepted，post-freeze remediation 不撤销该状态；`I02–I05 = NOT STARTED / NOT AUTHORIZED`，本 closeout 不激活 PRE-01B-I2、Real AI、Gate 或 Live；原 frozen artifacts 不被重写。
- Human Design Acceptance = `CONFIRMED — 2026-09-17`；Final Design Re-Review = `PASS`；R1–R8 = `CLOSED`；Open Decisions = `NONE`。
- Frozen invariants include independent `ReadSurfaceClass` A/B/C and `OperationalAvailability`, distinct projection/trace states and NONE semantics, explicit provenance/range contracts, typed Pydantic DTOs, and no silent Replay fallback；详见 accepted artifact。
- `UI-RD01-I01 = ACCEPTED / COMPLETE`（Human Acceptance = `CONFIRMED — 2026-09-18`；Independent Re-Review = `PASS`；Human-Accepted reviewed candidate = `e0fceafdb8cc35498144929ac2f4295327071bfb`）。`I02–I05` = NOT STARTED / NOT AUTHORIZED；Real AI / live G2→G3 / Gate A/B/C / Live 均未获激活授权。
- `UI-RD01-I01-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`（2026-09-18；parent = Reviewed Candidate `2b47b8fae7c47e53f73bfe3a7e75884bb615d221`，同一 candidate branch，**未**合并 `main`、**未**获 Human Acceptance）。冻结要点：非法 Incident 过滤 → `422`（`IncidentStatus` / `IncidentType` 为唯一 enum authority，OpenAPI/generated.ts 为枚举而非 `string`）；端点级 snapshot 失败 → `503` + `read_failure_reason=SNAPSHOT_FAILED`（正式 `ProductFailureResponse`，503/500 共用），section-local 失败仍 `200` + `is_partial` + `SOURCE_UNAVAILABLE`；`ProductRuntimeSnapshot.snapshot_at` 为该 Host snapshot 的权威采集时刻（同一 snapshot 只发布一个 section 时刻；Incident DB 段用自身查询时刻；Recovery 仍用不可变 process-lifetime snapshot）；Health 段 checks 与 overall status 同一次同步采集（`Live != Ready != Health` 不变）；未分类内部错误 → 脱敏 `500` correlation id。schema/migration/index/manifest/frozen design/`I02–I05`/Live = ZERO CHANGE。

## PRE-01B-D2-CLAR-01 Accepted Clarification Pointer

- `PRE-01B-D2-CLAR-01 = ACCEPTED / COMPLETE`（Human Acceptance = `CONFIRMED — 2026-09-17`；candidate `bdf691bf52bbb0706f497b9d1920349588c7c0b4`；Independent Re-Review = `PASS`；artifact = `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`）。冻结：arm domain = `pre01a-arm-v1`；§14.2 exact no-terminal-producing-Attempt pair contract；retry gap 可有历史 Attempt 而无当前 terminal-producing Attempt 时 `final_attempt_id=NULL`；`PROCESS_LOST` = restart/recovery-only；`ABANDONED` = live durable shutdown-cancellation-only；process-loss exhaustion 引用 exact `PROCESS_LOST` Attempt。本 Acceptance 不恢复/激活 PRE-01B-I2、Real AI、provider、Gate A/B/C、live `G2→G3` 或 Live。

## PRE-01B-I2 Recovery Authority Amendment Pointer

- `PRE-01B-I2-AUTH-D01-AMEND-01 = ACCEPTED / COMPLETE`（R3）；Human-Accepted candidate = `64407bec418ccd32791f200d12caf74f5ac0975a` on `design/pre-01b-i2-auth-d01-amend-01-r3`; R3 Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`; Human Acceptance = `CONFIRMED — 2026-09-20`; `IR-P1-01` / `IR-P3-01` / `IR-P3-02` / `R1IR-P1-01` / `R1IR-P1-02` / `R2IR-P1-01 = CLOSED / PASS`; P0 / P1 / P2 / P3 = `NONE`。R3 freezes FINAL OWNER-SESSION PROOF as the only singleton admission authority; the existing RuntimeHost + dedicated PostgreSQL owner session + existing advisory lock remain the one cross-process fence; `SingletonOwnerSessionGate` is coordination only; successful proof = admission = linearization. `PRE-01B-I2 = IMPLEMENTING`; `P1-03`–`P1-06 = OPEN`; `FIX-02 = UNBLOCKED / READY FOR FORMAL IMPLEMENTATION TASK`, implementation `NOT STARTED BY THIS CLOSEOUT`; no implementation/Gate/Real-AI/live activation is authorized.

- CR-05 Final Human Acceptance Closeout: `UI-V1-D01-AMEND-01-CR05-FIX-01 = ACCEPTED / COMPLETE`；`UI-V1-D01-AMEND-01-CR05-FIX-01-R1 = ACCEPTED / CLOSED`；CR-05 shared Product Read contract remediation = `ACCEPTED / COMPLETE`；`CR05-IR-P2-01 = CLOSED`；Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED — 2026-09-19`；Human-Accepted Reviewed Candidate = `125af5e62ab3d67171c06617c7701bfd0f94e37d`；Final Closeout commit is docs/state-only and integrated fast-forward-only into `main`. Exact six-value `TraceNodeState` semantics and the `NOT_REACHED != NOT_YET_DUE` distinction remain frozen; no classifier, endpoint, consumer, frontend trace/maturity, OpenAPI/generated.ts, schema, or dependency change. CR-01 / CR-02 = `ACCEPTED / COMPLETE`；CR-03 / CR-04 / CR-06 = `NOT APPLICABLE YET`；`UI-RD01-I01 = ACCEPTED / COMPLETE`；`I02–I05 = NOT STARTED / NOT AUTHORIZED`。

## UI-RD01-I02 Current Implementation Pointer

- `UI-RD01-I02-FIX-04 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW` on
  `ui-rd01-i02-fix-04-review-blockers`, direct descendant of Fix-03
  `764cdb2b4ed0695deb6da4e9b1412908f61831da` and accepted main
  `df02073521140e7ae599e03f2e04190b6a5ae590`. It closes `RR3-P2-01` by preserving a body primary
  Product/Snapshot/source/cancellation failure through transaction and session cleanup failures,
  while preserving success-path cleanup source errors. It closes `RR3-P2-02` with structural
  parsed-URL auth/refused probes that have no fixed credentials or port dependency. Parent
  task_state = `REVIEW`; Human Acceptance and main integration are `NOT PERFORMED`; I03/I04/I05
  remain `NOT STARTED`. See `dev_log/2026-09-20-ui-rd01-i02-fix-04-review-blockers.md`.
