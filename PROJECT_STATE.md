# MarketPulse AI Project State

## Current Group

SE-02A — Contracts + Additive Persistence — ACCEPTED / COMPLETE

SE-02B — Opportunity Capture + Attribution — ACCEPTED / COMPLETE

SE-02C — Forward Outcome Calculator — ACCEPTED / COMPLETE（2026-09-14 Human Acceptance =
`CONFIRMED` + Final Acceptance Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING
FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
`7bb3835d6b14a3fc86becff1881c7f53f1acd567`，branch `se-02c-fix-02-stable-read-snapshot`；
`SE-02C-FIX-01` = `ACCEPTED / CLOSED`（candidate `2f986827`）与 `SE-02C-FIX-02` =
`ACCEPTED / CLOSED`（implementation `6b084595`）；集成方法 = `FAST-FORWARD ONLY`；
遗留 `SE02C-R7` = P3 / NON-BLOCKING / NOT FIXED）

SE-02D — Family Aggregation / Expectancy — ACCEPTED / COMPLETE（2026-09-16 Human Acceptance =
`CONFIRMED` + SE-02D Overall Final Acceptance Closeout；Overall Final Review = `PASS WITH
NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed baseline =
`55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；`SE-02D-I01` = `ACCEPTED / COMPLETE`；
`SE-02D-I02` = `ACCEPTED / COMPLETE`；`SE-02D-I03` = `ACCEPTED / COMPLETE`；
`SE-02D-CLOSE-D01` = `ACCEPTED / COMPLETE`（2026-09-16）；**`SE-02D V1` capability
implementation = `COMPLETE AFTER I03`**；`I04 = NOT REQUIRED FOR SE-02D V1`；
`SE02D-OVERALL-R01-P3-01` / `P3-02` = `CLOSED`；K/D/K 与 `Gate C` / `Live` 仍
`NOT OWNED BY V1` / `NOT PASSED` / `NOT AUTHORIZED`）

SE-02D-I01 — Deterministic Aggregation Core — ACCEPTED / COMPLETE（2026-09-15 Human Acceptance =
`CONFIRMED`；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review =
`PASS`；`SE02D-I01-R1` / `SE02D-I01-R2` / `SE02D-I01-R3` = `CLOSED`；Human-Accepted reviewed
candidate = `13b37dff4b8150dea869ba6257ae9f3df24cc1e5`，branch
`se-02d-i01-aggregation-core`，immutable；集成方法 = `FAST-FORWARD ONLY`。**`I01 Accepted` 当时
≠ `SE-02D Overall Complete`**（该句为 I01 收尾时）：PostgreSQL current-snapshot 加载 / revision-chain folding /
canonical
Evidence-head 与 Outcome-head selection / `REPEATABLE READ` snapshot orchestration 已于
`SE-02D-I02` 实现并验收；population grouping + 调用 I01 `aggregate()` 已于 `SE-02D-I03`
实现并验收；`SE-02D V1` capability 完成边界其后已由 `SE-02D-CLOSE-D01`（2026-09-16 Human
Acceptance = `CONFIRMED`）接受为 `COMPLETE AFTER I03`（aggregate capability =
`IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend / runtime product consumer =
`NOT REQUIRED FOR SE-02D V1 COMPLETION`；`SE-02D Overall` 其后已于 2026-09-16 经
SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）；
详见「SE-02D-I01 Result」、「SE-02D-I02 Result」、「SE-02D-I03 Result」与
「SE-02D-CLOSE-D01 Result」）

SE-02D-I02 — Current-Snapshot Revision Folding — ACCEPTED / COMPLETE（2026-09-15 Human
Acceptance = `CONFIRMED`；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01
Independent Re-Review = `PASS`；`SE02D-I02-R1` / `R2` / `R3` = `CLOSED`；Human-Accepted
reviewed candidate = `9b860437b14f64192d3298d30c0204bed1b118f8`，branch
`se-02d-i02-current-snapshot-folding`，immutable；集成方法 = `FAST-FORWARD ONLY`
（latest-main content-level carry-forward）。**`I02 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I02 收尾时）：
population grouping + 调用 I01 `aggregate()` 已于 `SE-02D-I03` 实现并验收；`SE-02D V1`
capability 完成边界其后已由 `SE-02D-CLOSE-D01`（2026-09-16 Human Acceptance = `CONFIRMED`）
接受为 `COMPLETE AFTER I03`，`SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall
Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；详见「SE-02D-I02 Result」、
「SE-02D-I03 Result」与「SE-02D-CLOSE-D01 Result」）

SE-02D-I03 — Population Grouping + Aggregate Orchestration — ACCEPTED / COMPLETE（2026-09-16
Human Acceptance = `CONFIRMED`；Initial Independent Review = `FAIL — FIX REQUIRED`；
`SE02D-I03-R1`（P1）= `CLOSED`；FIX-01 Independent Re-Review = `PASS — READY FOR HUMAN
ACCEPTANCE`；Human-Accepted reviewed HEAD = `20a7c333abf81077c409811302331119dff485a5`，branch
`se-02d-i03-fix-01-projection-identity-validation`；Original Reviewed Candidate =
`44d0e4b14ba0037de4da8e605d7b04b9f5d721e4`，branch
`se-02d-i03-population-aggregate-orchestration`，immutable；集成方法 = `FAST-FORWARD ONLY`。
**`I03 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I03 收尾时）：aggregate capability 已由 I01 + I02 + I03 实现，
并经 `SE-02D-CLOSE-D01`（2026-09-16 Human Acceptance = `CONFIRMED`）确认为
`IMPLEMENTED / ACCEPTED`；API / frontend / runtime product consumer =
`NOT REQUIRED FOR SE-02D V1 COMPLETION`（defer 至未来 consumer / Gate C 任务）；
historical revision-as-of 仍 `OPEN`；`SE-02D Overall` 其后已于 2026-09-16 转 `ACCEPTED /
COMPLETE`；详见「SE-02D-I03 Result」与「SE-02D-CLOSE-D01 Result」）

SE-02D-CLOSE-D01 — V1 Completion Boundary Reconciliation — ACCEPTED / COMPLETE（2026-09-16 Human
Acceptance = `CONFIRMED`；Independent Review = `PASS — READY FOR HUMAN ACCEPTANCE`；
Human-Accepted candidate = `a9e615726ee964c02a72ea6cbff490d3d74e08f7`，branch
`design/se-02d-close-d01-v1-completion-boundary`，immutable；Accepted Design artifact =
`docs/design/SE-02D/SE-02D-CLOSE-D01-V1-Completion-Boundary-Reconciliation.md`（status =
`ACCEPTED DESIGN`）；closeout branch = `se-02d-close-d01-final-acceptance`；集成方法 =
`FAST-FORWARD ONLY`。**Accepted completion boundary** = `SE-02D V1 CAPABILITY COMPLETE AFTER I03`；
`I04 = NOT REQUIRED FOR SE-02D V1`；API / frontend / runtime consumer =
`NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical revision-as-of 仍 `OPEN`；Gate C
prerequisites 仍 `OPEN`；`SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall
Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；详见「SE-02D-CLOSE-D01 Result」）

SE-02D-D01 — Family Aggregation / Expectancy Contract（设计契约）— ACCEPTED / COMPLETE（2026-09-15 Human
Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Initial Review = `FAIL — FIX
REQUIRED`；FIX-01 Independent Re-Review = `PASS`；`D01-R1` / `D01-R2` = `CLOSED`；`D01-R3` =
`CLARIFIED / NON-BLOCKING`；Human-Accepted candidate =
`245b068199b7e6f3d32bf67e3b00163e4804afdf`，branch
`design/se-02d-d01-family-aggregation-expectancy`，immutable；Accepted Design artifact =
`docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`。本轮为**正交漂移
和解**收尾：PRE-01B-D1 已接受 docs/state 漂移使 candidate 不再是 current `main` 的
ancestor，内容以 latest-main content-level carry-forward 搬运后 `FAST-FORWARD ONLY`
集成。**`SE-02D` production implementation 当时仍 `NOT STARTED`**（SE-02D-D01 收尾时；其后
`SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`，父状态
当时 = `IN PROGRESS`，剩余实现当时仍 `NOT COMPLETE`；其后 `SE-02D-CLOSE-D01` 已于 2026-09-16 经 Human
Acceptance 接受 `SE-02D V1` capability 完成边界 = `COMPLETE AFTER I03`，且 `SE-02D Overall`
其后已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；
详见「SE-02D-D01 Result」、「SE-02D-I01 Result」与「SE-02D-CLOSE-D01 Result」）

SE-ARCH-FIX-01 — Stable Evidence Anchor — ACCEPTED / COMPLETE

SE-ARCH-FIX-02 — Outcome Revision Chain Scope — ACCEPTED / COMPLETE（2026-09-13 Human Acceptance = `APPROVED` + Final Main Integration Closeout）

N01-C — Restart / Recovery / Reconciliation — ACCEPTED / COMPLETE

N01-A — Deterministic Runtime + Resource Lifecycle — ACCEPTED / COMPLETE

N01-6 — 15-minute Short Runtime Smoke — ACCEPTED / COMPLETE

N01-7-F01 — Durable Protection Snapshot（N01-7 前置 Fix）— ACCEPTED / COMPLETE

N01-7 — 2-hour Medium Runtime Soak / N01-7-R01 — Witness B Fix + Latest-Main Revalidation +
2h Acceptance Re-run — ACCEPTED / COMPLETE（2026-09-14 Human Acceptance = `CONFIRMED` +
Final Main Integration Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS —
READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
`559f14be1fb89df58c11dfbea737eba4ac30421e`，branch `n01-7-r01-witness-b-latest-main`；
集成方法 = `FAST-FORWARD ONLY`；`N01-7-R01 = ACCEPTED / COMPLETE` **不**构成
`N01 overall ACCEPTED`）

N01-8 — 12-hour Extended Soak — ACCEPTED / COMPLETE（2026-09-14 Human Acceptance = `CONFIRMED`
+ Final Acceptance Closeout；Independent Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR
HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
`d9306ada663a5cacb86bee26218e298169d82e6b`，branch `n01-8-12h-extended-soak`；正式单轮
`total_active 44401.217 s`、4/4 phase complete、3 fresh-process restart、12 controlled reconnect、
6 受控 STALE→FRESH、24/24 reconciliation checkpoint PASS、99/99 aggregate checks True；集成方法 =
`FAST-FORWARD ONLY`；Memory P2 `N01-7-R01-RR-P2-01` **REMAINS**（NON-BLOCKING））

Integrated Runtime Host — NOT STARTED

N01 overall — ACCEPTED / COMPLETE（2026-09-14 Human Acceptance = `CONFIRMED` + N01 Overall
Final Acceptance Closeout；Overall Final Review = `PASS WITH NON-BLOCKING FINDINGS — READY
FOR HUMAN ACCEPTANCE`；已 fast-forward only 收编 `main`。所含已验收门：`N01-A` / `N01-B` /
`N01-VAL-FIX-01/02/03` / `N01-C` / `N01-6` / `N01-7-F01` / `N01-7`（`N01-7-R01`）/ `N01-8`
全部 `ACCEPTED / COMPLETE`；该总体结论由独立的 Overall Final Review / Acceptance 确立，
不由任何单门 N01 验收自动推断；`Integrated Runtime Host` 仍 `NOT STARTED`；Memory P2
`N01-7-R01-RR-P2-01` = `REMAINS` / NON-BLOCKING；`N01-9 = NOT REQUIRED / NOT CREATED`）

PRE-01A-D1 — Real AI V1 Trade Decision Experiment Contract — ACCEPTED / COMPLETE

（2026-09-14 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Re-Review =
`PASS`；`D1-R1` / `D1-R2` = `CLOSED`；Human-Accepted candidate =
`e3fb721c678e2b3ca0af6fb4663f349c6a641159`，branch `design/pre-01a-d1-real-ai-v1-contract`；
Accepted Design artifact =
`docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`。
本 Acceptance 仅接受设计本身：Real AI runtime activation 仍 `NOT STARTED / NOT ACTIVATED`；
Real AI provider runtime evidence 仍 `NOT PRESENT`；`SE-02D` 当时仍 `NOT STARTED`
（PRE-01A-D1 收尾时；其后 `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为
`ACCEPTED / COMPLETE`）；
`Integrated Runtime Host` 仍 `NOT STARTED`；live Opportunity → G3 integrated handoff 仍
`NOT ACCEPTED / NOT ACTIVE`。**不**构成 Real AI implementation complete / PRE-01 complete /
AI edge proven / Runtime Host complete。详见「PRE-01A-D1 Result」）

PRE-01B-D1 — Integrated Runtime Host Formal Design — ACCEPTED / COMPLETE（2026-09-15 Human
Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Review = `PASS WITH
NON-BLOCKING FINDINGS`；P0 = `NONE` / P1 = `NONE`；Human-Accepted reviewed candidate =
`80cb2babe9f55b3a3b1dc2d3b7913a405607ac22`，branch `design/pre-01b-d1-runtime-host-contract`，
immutable；Accepted Design artifact =
`docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`。
**本 Acceptance 仅接受 Formal Design 本身**：`Integrated Runtime Host
Implementation` 仍 `NOT STARTED`；Real AI runtime activation 仍
`NOT STARTED / NOT ACTIVATED`；live Opportunity → G3 integrated handoff 仍
`NOT ACCEPTED / NOT ACTIVE`；`SE-02D` 当时仍 `NOT STARTED`（PRE-01B-D1 收尾时；其后
`SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）；Live Trading
仍 `DISABLED`；
Memory P2 `N01-7-R01-RR-P2-01` 仍 `REMAINS / NON-BLOCKING`。Implementation carry-ins：
`F-01`（`state_version_for` 实现必须绑定已接受的 durable
state/version authority）/ `F-02`（safety queue capacity `64` 仅为初始可配置
默认值，待 implementation/runtime sizing evidence 验证）。详见
「PRE-01B-D1 Result」）

PRE-01B-I1 — Integrated Runtime Host Core V1 Implementation — ACCEPTED / COMPLETE（2026-09-15 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout & Latest-Main Reconciliation；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS`；P0 = `NONE` / P1 = `NONE`；Human-Accepted reviewed candidate = `68dd7e96cc8547433794b045fa99e1e9dc5b7892`，branch `pre-01b-i1-fix-01-runtime-host-lifecycle`，immutable；Original Candidate = `b66e17d34173156b3797b664dbe09625511a0a11`；集成方法 = `FAST-FORWARD ONLY`（content-level carry-forward onto latest `main` `0ae5b0b…`；drift 正交 = `SE-02D-I01`，未触碰任何 PRE-01B 路径）；Runtime Host Core V1 = `ACCEPTED / COMPLETE`。**本 Acceptance 仅接受 Implementation Core V1 本身**：Real AI runtime activation 仍 `NOT STARTED / NOT ACTIVATED`；live G2→G3 integrated handoff 仍 `NOT ACCEPTED / NOT ACTIVE`；`SE-02D` Production = `IN PROGRESS`（SE-02D-I01 = `ACCEPTED / COMPLETE`）；OS/service / WinSW / Live Trading 仍 `NOT COMPLETE / DISABLED / NOT AUTHORIZED`；Memory P2 `N01-7-R01-RR-P2-01` 仍 `REMAINS / NON-BLOCKING`；RR-P2-01（Alembic URL 优先级 / `DATABASE_URL` 交互）= `NON-BLOCKING TEST-INFRASTRUCTURE DEBT`（本任务不修）；P2-02（历史 process-scope violation）= `REMAINS AS AUDIT FINDING`。详见「PRE-01B-I1 Result」）

PRE-01B-D2 — AdvisoryIngress / durable G2→G3 Activation Contract — ACCEPTED / COMPLETE（2026-09-17 Human
Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Re-Review = `PASS`；P0 = `NONE` /
P1 = `NONE` / P2 = `NONE` / P3 = `NONE`；Human-Accepted reviewed candidate =
`cce1ae7b862b038a99976c802c0985df01b35285`，branch
`design/pre-01b-d2-fix-05-return-completion-authority`，immutable；Accepted Design artifact =
`docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`；集成方法 =
`FAST-FORWARD ONLY`。**本 Acceptance 仅接受 Formal Design 本身**：`PRE-01B-I2` 仍
`NOT STARTED / NOT AUTHORIZED BY THIS CLOSEOUT`；live `G2→G3` 仍 `NOT ACTIVE`；Real AI 仍
`NOT ACTIVATED`；Gate A 仍 `NOT ACTIVATED`；Gate B 仍 `NOT ACTIVATED`；Gate C 仍 `NOT PASSED`；
Live 仍 `NOT AUTHORIZED`；Live Trading 仍 `DISABLED`；Memory P2 `N01-7-R01-RR-P2-01` 仍
`REMAINS / NON-BLOCKING`。Human Decision Pack 未解决项保持：Pack A = `NONE`；Pack B（numeric
provider / model / retry / timeout / deadline / pool / concurrency / shutdown / queue / cost /
retention 数值）与 Pack C（Gate-A observation / sufficiency / acceptance thresholds）仍
`UNRESOLVED`（本收尾**不**发明数值、**不**静默授权 production defaults）。详见「PRE-01B-D2 Result」）

UI-V1-D01 — MarketPulse UI V1 Formal Design — ACCEPTED / FROZEN / REPOSITORY-INTEGRATED
（2026-09-17 Human Acceptance = `CONFIRMED` + Final Acceptance / Main Integration Closeout；
included closure `UI-V1-D01-FIX-01` = `INCLUDED / CLOSED`；Independent Final Review =
`PASS — READY FOR FORMAL FREEZE`；Independent Final Repository Review = `PASS`；P0 = `NONE` /
P1 = `NONE` / P2 = `NONE` / P3 = `NONE`；repository persistence `UI-V1-D01-FINAL-DOC-01` =
`COMPLETE`（documentation fixes `FIX-01` / `FIX-02` = `COMPLETE`）；Human-Accepted /
Reviewer-approved final candidate = `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4`（branch
`design/ui-v1-d01-final-doc-fix-02`，immutable；远端同 SHA、未被移动）；closeout branch =
`ui-v1-d01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`；Accepted Design artifact =
`docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`，Artifact status =
`ACCEPTED / FROZEN`）。产品定位 = **Read-Only Paper Trading Operations & Evidence Terminal**
（只读纸面交易运维与证据终端）；顶层信息架构 = 恰好五页（总览 / 市场与机会 / 策略研究 /
交易与仓位 / 系统），**AI 无独立顶层页**。**本 Acceptance（UI-V1-D01 收尾时）仅接受 Formal
Design；当时 `UI implementation = NOT STARTED`**（当时前端仅 Group 1 占位脚手架，
`frontend/vite.config.ts` 当时尚无 `/api` proxy；其后 Frontend Foundation 已于 2026-09-17 经
Human Acceptance 转为 `ACCEPTED / COMPLETE`，见「UI-F01-I01 Final Acceptance Closeout
Result」）；**不**授权 `UI-F01` / `UI-RD01` 或任何后续实现、**不**激活
`PRE-01B-I2`、**不**激活 Real AI、**不**接通 live `G2→G3`、**不**接通 Forward Outcome
运行时调度、**不**改变任何 schema / migration / config / runtime。前端基础库选型 =
`DEFERRED` 至 `UI-F01`（本 D01 只冻结「需要」，不选库）。详见「UI-V1-D01 Result」与「UI-V1-D01 Final Acceptance Closeout Result」）

UI-F01 — Frontend Foundation — ACCEPTED / COMPLETE（2026-09-17 Human Acceptance = `CONFIRMED` +
Final Acceptance Closeout；其唯一已授权实现批 `UI-F01-I01` 于同日转为 `ACCEPTED / COMPLETE`，
foundation closure fix `UI-F01-I01-FIX-01` = `ACCEPTED / CLOSED`；Human-Accepted reviewed
candidate = `ecc21356851f7deca8fd55ea086ec1007b0675d4`；closeout branch =
`ui-f01-i01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`）。**本 Acceptance 仅接受
Frontend Foundation 本身**：正式业务页面（总览 / 市场与机会 / 策略研究 / 交易与仓位 / 系统）
= 仍为占位 `NOT STARTED`；Product Read API = `NOT STARTED`；`UI-RD01` / `UI-I01..UI-I06` =
**未**实现、**未**授权（`UI-RD01` 为下一计划正式设计任务，**须**另行 Human 授权）。详见
「UI-F01-I01 Result」与「UI-F01-I01 Final Acceptance Closeout Result」）

UI-F01-I01 — Frontend Foundation Implementation — ACCEPTED / COMPLETE（2026-09-17 Human Acceptance =
`CONFIRMED` + Final Acceptance Closeout；Independent Initial Review = `FAIL — FIX REQUIRED`；
Finding = `UI-F01-I01-R1`（generic transport error-normalization boundary 不完整，即原批 `R-02`）；
FIX = `UI-F01-I01-FIX-01`；Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Final
Re-Review severity：P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NON-BLOCKING ONLY`；
`UI-F01-I01-R1` = `CLOSED`；Human-Accepted candidate = `ecc21356851f7deca8fd55ea086ec1007b0675d4`，
branch `ui-f01-i01-fix-01-transport-error-boundary`，immutable 且远端未被移动；原始实现
candidate = `0c9186d2d94450d39754eb40536148a73deb123c`，branch `ui-f01-i01-frontend-foundation`，
immutable；Final Regression = `typecheck` / `7 files / 44 tests` / `build` / `check:api-drift`
全 exit 0）
（Task Type = IMPLEMENTATION + VERIFICATION；Task Base = `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`
= 执行前实读远端 `main` 真值 ⇒ **无** baseline drift；task branch = `ui-f01-i01-frontend-foundation`，
**未** merge `main`）。本批建立前端 Foundation：`react-router` 声明式路由（顶层 IA **恰好五页**、
**无**顶层 `/ai`、`/login` 为 Auth Shell 而非第六页，五页**仅**占位）；单一 application
`QueryClient`（无默认轮询 / 无全局 refetch interval；`401` 与普通 `4xx` 不重试、network 与 `5xx`
有界重试）；`openapi-fetch` typed API client（**未**引入 Axios、**未**自建 HTTP 框架；应用请求
同源相对 `/api/...`、**不**硬编码后端 host）；唯一 Auth Session Boundary（bearer 仅存
`sessionStorage`，**密码永不持久化**；login `401` 保持「凭据错误」且无重定向循环；受保护 `401`
清 session + 清已认证 Query cache 并进入 Login 边界且保留原定安全内部路由）；Vite 开发 `/api`
proxy → `127.0.0.1:8000`（**不** rewrite、**未**引入宽泛 CORS）；`/ready` `503` = 权威 NOT READY
（保留 body，**不是**网络故障、**不是**通用后端故障、**不**被重试）；OpenAPI 生成纪律恢复
（`generate:api` 离线可复现、`check:api-drift` 可执行且漂移即失败）；Vitest + jsdom + RTL + MSW
测试 harness。真实验证：`npm ci` / `npm run typecheck` / `npm run test:run`（7 files / 37 tests
PASS）/ `npm run build` / `npm run generate:api` / `npm run check:api-drift` 全部 exit 0
（另以注入式探针证明 typecheck 与 drift 两个门均**有牙齿**）。**该批交付时状态（Implementation
完成时）**：Independent Review 与 Human Acceptance 均**未**发生，`UI-F01-I01` 当时**不**等于
`ACCEPTED` / `COMPLETE` / `HUMAN ACCEPTED`（其后已于 2026-09-17 经 Independent Review
`FAIL — FIX REQUIRED` → `UI-F01-I01-FIX-01` → Independent Re-Review
`PASS — READY FOR HUMAN ACCEPTANCE` → Human Acceptance `CONFIRMED` 转为 `ACCEPTED / COMPLETE`，
见「UI-F01-I01 Final Acceptance Closeout Result」）；业务页面实现 = `NOT STARTED`（五页仍为占位）；
Product Read API = `NOT STARTED`；**不**构成 `UI-RD01` / `UI-I01..UI-I06` 的授权或进度。
边界保持：`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3`
= `NOT ACTIVE`；Forward Outcome runtime integration = `NOT INTEGRATED`；`Gate C` = `NOT PASSED`；
`Live` = `NOT AUTHORIZED`；Trading Edge = **未证明**。后端 / schema / migration / config =
**ZERO CHANGE**。详见「UI-F01-I01 Result」与
`dev_log/2026-09-17-ui-f01-i01-frontend-foundation.md`、及
`dev_log/2026-09-17-ui-f01-i01-final-acceptance-closeout.md`）

UI-F01-I01-FIX-01 — Transport Error Boundary Closure — ACCEPTED / CLOSED（2026-09-17 Human
Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent Re-Review = `PASS — READY FOR
HUMAN ACCEPTANCE`；`UI-F01-I01-R1` = `CLOSED`；Human-Accepted candidate =
`ecc21356851f7deca8fd55ea086ec1007b0675d4`，branch `ui-f01-i01-fix-01-transport-error-boundary`，
immutable；集成方法 = `FAST-FORWARD ONLY`；Final Regression 全 exit 0）
（Task Type = IMPLEMENTATION + VERIFICATION；关闭独立复审 Finding `UI-F01-I01-R1` = 原批 `R-02` 风险；
Reviewed candidate = `0c9186d2d94450d39754eb40536148a73deb123c`，**未**重写、保留为历史证据；
Fix branch = `ui-f01-i01-fix-01-transport-error-boundary`，**未** merge `main`）。通用网络 / HTTP
错误归一化现由 `frontend/src/api/transport.ts` **单点拥有**（`requestData()`：network →
`NetworkError`；`401` → `UnauthorizedError`；其他非 2xx → `HttpError` 且 status / body 保留；
2xx + 不可解释 body → `UnexpectedResponse`），`transportErrorForStatus()` 由 `readiness.ts` 迁入；
`/ready` `503` 仍是**唯一**显式例外（权威 NOT READY、body 保留、**不是** `HttpError` /
`NetworkError`、**不**被重试）。真实门：`npm run typecheck` / `npm run test:run`（7 files /
**44** tests PASS，既有 37 **未**削弱 + 新增 7）/ `npm run build` / `npm run check:api-drift`
全部 exit 0；另以 3 个注入式探针证明新覆盖**有牙齿**（已逐字节复原）。改动面 =
`frontend/src/api/**` 4 个文件 + `dev_log` / `PROJECT_STATE.md` / `AI_CONTEXT.md` 最小同步；
`frontend/package.json` / `frontend/package-lock.json` / `backend/**` / schema / migration /
`frontend/src/auth/**` / `frontend/src/app/**` = **ZERO CHANGE**；`react` / `react-dom` 按
lockfile 实测 = `19.3.0`（**未**因上一份 Completion Report 的版本笔误改动任何 production
dependency）。**该批交付时状态（Fix 完成时）**：`UI-F01-I01-FIX-01` 当时**不**等于 `ACCEPTED` /
`COMPLETE`；其后已于 2026-09-17 经 Independent Re-Review（`PASS — READY FOR HUMAN ACCEPTANCE`）
与 Human Acceptance（`CONFIRMED`）转为 `ACCEPTED / CLOSED`（见「UI-F01-I01 Final Acceptance
Closeout Result」）；**不**构成 `UI-RD01` / `UI-I01..UI-I06` 的授权或进度。详见
`dev_log/2026-09-17-ui-f01-i01-fix-01-transport-error-boundary.md`）

UI-RD01-I02-REQ-01 — Market Scanner & Opportunity Product Read Implementation Requirements（UI-RD01-I02｜需求冻结 / 需求持久化）— `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（2026-09-19；Task = `UI-RD01-I02-REQ-01-PERSIST`；Task type = `DOCUMENT PERSISTENCE + STATE SYNC ONLY`；formal task_state 仍 = `IMPLEMENTING`；Human Content Confirmation = `CONFIRMED — 2026-09-19`；Artifact = `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`，Artifact status = `CANDIDATE / PENDING INDEPENDENT REVIEW`（**未** 声明 `ACCEPTED` / `FROZEN`）；Protocol Baseline = `v1.4.0 / ACCEPTED`；Repository Baseline at Requirement Confirmation = `08b6c5d6eebb5339756378ace80cb97d504ee25d`，Task Base = 执行前实读远端 `main` 真值 ⇒ **无** baseline drift；branch = `design/ui-rd01-i02-requirements`，**未** merge `main`、**未** reset / rebase / squash / force push）。

PRE-01B-I2-AUTH-D01-AMEND-01 — Recovery Authority Amendment — `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（2026-09-19；Task type = `DOCS / DESIGN PERSISTENCE + STATE SYNC ONLY`；Human Content Confirmation = `CONFIRMED`；Independent Review / Formal Acceptance = `PENDING`；artifact = `docs/design/PRE-01B/PRE-01B-I2-AUTH-D01-Recovery-Authority-Amendment.md`，status = `CANDIDATE / PENDING INDEPENDENT REVIEW`）。本次仅持久化 DF-01 `APPROVED` 的 DISABLED provider-free startup recovery 窄例外、DF-02 `APPROVED WITH TRANSACTION-ADMISSION AUTHORITY` 与 D1–D7；不重写 accepted D2，不恢复 FIX-02 implementation。`PRE-01B-I2 = IMPLEMENTING`；`P1-03` / `P1-04` / `P1-05` / `P1-06 = OPEN`；`FIX-02 = BLOCKED PENDING AUTHORITY AMENDMENT ACCEPTANCE`。Real AI / Gate A / Gate B / Gate C / live G2→G3 / Live 均保持未激活、未通过或未授权；schema / migration / runtime = ZERO CHANGE。
（本批仅持久化已 Human-Confirmed 的需求语义，**不做任何实现**：`Implementation Authorization = NOT GRANTED`；`UI-RD01-I02 implementation = NOT STARTED / NOT AUTHORIZED`；执行拆分为 `I02-A｜市场扫描读取`（`GET /api/v1/product/market-scanner`）与 `I02-B｜机会追踪读取`（`GET /api/v1/product/opportunities`、`GET /api/v1/product/opportunities/{opportunity_id}`），`I02-A → I02-B` 串行，两者均 `NOT STARTED`；`CR-03`（Current Canonical Evidence vs Decision-Bound Evidence）与 `CR-05`（`NOT_REACHED` vs `NOT_YET_DUE`）= **未来** I02-B 实现要求，本 persistence 任务**未实现**任何 CR-03 / CR-05；`Schema` / `Migration` / `Index` = `ZERO CHANGE`；`backend/**` / `frontend/**` / `frontend/src/api/generated.ts` = **ZERO CHANGE**；`I03`–`I05` 维持 `NOT STARTED / NOT AUTHORIZED` **不变**；`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Gate A/B/C = `NOT ACTIVATED` / `NOT PASSED`；Live = `NOT AUTHORIZED`；Live Trading = `DISABLED`。详见「UI-RD01-I02 Requirement Persistence Result」与 `dev_log/2026-09-19-ui-rd01-i02-requirements.md`。⚠ **2026-09-19 Independent Review = `FAIL — R1 REQUIRED`**（blocking finding = `I02REQ-RR-P1-01`：Global Protocol v1.4.0 execution-timing evidence）⇒ 本条的 `IMPLEMENTED / READY FOR INDEPENDENT REVIEW` 标记与文末「UI-RD01-I02 Requirement Persistence Result」段的状态标记**已被 R1 取代**；当前状态 = `UI-RD01-I02-REQ-01-PERSIST-R1 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`，权威段 = 「UI-RD01-I02 Requirement Persistence — Independent Review R1」；Requirement artifact 状态仍 = `CANDIDATE / PENDING INDEPENDENT REVIEW`，`Implementation Authorization = NOT GRANTED`，`I02-A` / `I02-B` = `NOT STARTED`）

UI-RD01-I02-REQ-01 — Market Scanner & Opportunity Product Read Implementation Requirements（UI-RD01-I02｜需求冻结·R1 / Final Acceptance Closeout）— `ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`（2026-09-19 Human Freeze = `CONFIRMED — 2026-09-19`；Independent Re-Review = `PASS — READY FOR HUMAN FREEZE`；Human-Frozen Reviewed Candidate = `b91d635de04c7444257fcc17069f418e3d3919e7`，branch `design/ui-rd01-i02-requirements`，immutable；Finding `I02REQ-RR-P1-01 = CLOSED / PASS`；review severity after R1：P0 = 0 / P1 = 0 / blocking P2 = 0；Requirement semantics = `NO SEMANTIC BLOCKER FOUND`；Acceptance Closeout = `COMPLETE`；closeout branch = `ui-rd01-i02-requirements-final-freeze`；集成方法 = `FAST-FORWARD ONLY`）。Artifact = `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`，final status = `ACCEPTED / FROZEN`（仅 acceptance / lifecycle metadata 变更；59 个编号章节语义零变更；reviewed artifact blob = `f3bec0140870fb25b0f536eeb7617677b20f5dd7`）。**本条取代上一条 `UI-RD01-I02-REQ-01` 的 `IMPLEMENTED / READY FOR INDEPENDENT REVIEW` 与文末「UI-RD01-I02 Requirement Persistence Result」/「UI-RD01-I02 Requirement Persistence — Independent Review R1」两段的**当前状态含义（两段作为历史记录保留，**不**改写）。**
（**本 Freeze 仅接受需求本身，不启动任何实现**：`Implementation Authorization = NOT GRANTED BY THIS CLOSEOUT`；`UI-RD01-I02 implementation = NOT STARTED`；`I02-A` = `NOT STARTED`；`I02-B` = `NOT STARTED`；`I03`–`I05` = `NOT STARTED / NOT AUTHORIZED` **不变**；`CR-03` / `CR-05` = future I02-B implementation requirement（accepted contract 已在 `UI-V1-D01-AMEND-01` 冻结，I02-B 必须 comply，本批**未实现**任何 CR-03 / CR-05 代码）；`CR-04` / `CR-06` = `NOT APPLICABLE YET`；改动面 = 仅 5 个授权 docs/state 路径；实现面（`backend/**` / `frontend/**` / `frontend/src/api/generated.ts` / `Schema` / `Migration` / `Index` / package manifests / `RuntimeHost` / `ProductReadContext` / Product DTO / Product router）与 frozen UI-RD01 design / Post-Freeze Amendment / `PRODUCT_REQUIREMENTS.md` = `ZERO CHANGE`（`DECISIONS.md` 仅新增一条 compact 摘要条目）；`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Gate A/B/C = `NOT ACTIVATED` / `NOT PASSED`；Live = `NOT AUTHORIZED`；Live Trading = `DISABLED`。详见「UI-RD01-I02 Requirement Final Freeze Result」与 `dev_log/2026-09-19-ui-rd01-i02-requirements-final-freeze.md`）

## GitHub Repository

- GitHub Repository Full Name: `zwmhua2-lab2/MarketPulse-AI`
- GitHub Repository URL: https://github.com/zwmhua2-lab2/MarketPulse-AI
- Visibility: `PRIVATE`
- Default Branch: `main`
- Accepted Main Source: Git `main` / `origin/main` — read actual SHA at task preflight（CIP-02）
- Current Development Status: `SE-ARCH-FIX-01 ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance
  = `APPROVED` + Final Main Integration Closeout，已 fast-forward only 收编 `main`）；
  `SE-02B ACCEPTED / COMPLETE`（2026-09-12 Human Acceptance &
  Final Acceptance Closeout，已 fast-forward only 收编 `main`）；`SE-02A ACCEPTED / COMPLETE`；
  `N01-7-F01 ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance Confirmed + Final Main
  Integration，已 fast-forward only 收编 `main`）；`N01-C ACCEPTED / COMPLETE`；
  `N01-6 ACCEPTED / COMPLETE`；N01-A / N01-B 与
  `N01-VAL-FIX-01/02/03` 均维持已验收结论；`N01 overall = ACCEPTED / COMPLETE`
  （2026-09-14 Human Acceptance = `CONFIRMED` + N01 Overall Final Acceptance Closeout）；
  **`N01-7` / `N01-7-R01 ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` +
  Final Acceptance Closeout，已 fast-forward only 收编 `main`）；
  **`N01-8 ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` + Final
  Acceptance Closeout，已 fast-forward only 收编 `main`；`Integrated Runtime Host` 仍
  `NOT STARTED`）；`N01 overall = ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance =
  `CONFIRMED` + N01 Overall Final Acceptance Closeout；Overall Final Review = `PASS WITH
  NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`）；
  `SE-ARCH-FIX-02 ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance = `APPROVED` + Final Main
  Integration Closeout，已 fast-forward only 收编 `main`）；
  `SE-02C = ACCEPTED / COMPLETE`
  （2026-09-14 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Independent
  Re-Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted
  reviewed candidate = `7bb3835…`（branch `se-02c-fix-02-stable-read-snapshot`）；原实现窗口
  branch `se-02c-forward-outcome-calculator` @ `be3aa6c`、Fix-01 candidate `2f986827`、
  Fix-02 implementation `6b084595` 均保持 immutable；`SE-02C-FIX-01` / `SE-02C-FIX-02` =
  `ACCEPTED / CLOSED`；已 fast-forward only 收编 `main`；`SE02C-R7` = P3 / NON-BLOCKING /
  NOT FIXED；`Schema Changed = NO`、`Migration Added = NO`，单 head 仍 `20260913_0009`）；
  **`SE-02D = ACCEPTED / COMPLETE`；`SE-02D Overall = ACCEPTED / COMPLETE`**（2026-09-16 Human
  Acceptance = `CONFIRMED` + SE-02D Overall Final Acceptance Closeout；Overall Final Review =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed
  baseline = `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；`SE02D-OVERALL-R01-P3-01` / `P3-02` =
  `CLOSED`；`SE-02D-I01` = `ACCEPTED / COMPLETE`、`SE-02D-I02` =
  `ACCEPTED / COMPLETE`，均于 2026-09-15 Human Acceptance = `CONFIRMED` + Final Acceptance
  Closeout；`SE-02D-I03` = `ACCEPTED / COMPLETE`，2026-09-16 Human Acceptance = `CONFIRMED`
  + Final Acceptance Closeout；**`SE-02D-CLOSE-D01` = `ACCEPTED / COMPLETE`**，2026-09-16
  Human Acceptance = `CONFIRMED`，Accepted completion conclusion = `SE-02D V1 CAPABILITY
  COMPLETE AFTER I03`，`I04 = NOT REQUIRED`，API / frontend / runtime product consumer =
  `NOT REQUIRED FOR SE-02D V1 COMPLETION`；**`SE-02D V1` capability implementation =
  `COMPLETE AFTER I03`**；**`SE-02D-D01` 设计契约 = `ACCEPTED / COMPLETE`**，2026-09-15 Human
  Acceptance = `CONFIRMED` + Final Acceptance Closeout）

## Branch / Source

- Current Accepted Branch: `main`
- Current Group Branch: `se-02d-overall-final-acceptance-closeout`（SE-02D-OVERALL-FINAL｜Overall
  Final Acceptance Closeout + P3 Documentation Reconciliation + Fast-Forward Main Integration；
  base = Human-Accepted reviewed baseline `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；
  docs/state-only closeout commit，已 fast-forward only 收编 `main`）；更早
  `se-02d-close-d01-final-acceptance`（SE-02D-CLOSE-D01-FINAL；base = Human-Accepted candidate
  `a9e615726ee964c02a72ea6cbff490d3d74e08f7`）；更早 `se-02c-final-acceptance-closeout`（SE-02C-FINAL｜Acceptance Closeout &
  Main Integration；base = immutable reviewed candidate
  `7bb3835d6b14a3fc86becff1881c7f53f1acd567`；docs/state-only closeout commit，已 fast-forward
  only 收编 `main`）；reviewed candidate branch `se-02c-fix-02-stable-read-snapshot` @ `7bb3835`
  保持 immutable 且远端 ref 未被移动；Fix-01 branch
  `se-02c-fix-01-review-blockers` @ `2f986827` 保持 immutable；原已复审候选 branch
  `se-02c-forward-outcome-calculator` @ `be3aa6c`（**immutable，保留未改写**）；已验收 lineage
  `n01-7-r01-witness-b-latest-main`（N01-7 / N01-7-R01；closeout 直接在已复审候选 tip
  `559f14b` 上线性 +1 docs/state-only commit，仅 fast-forward 收编至 `main`，历史分支保留）；
  更早 `n01-c-restart-recovery-reconciliation`（N01-C）、`se-02a-final-integration-refresh`、
  `n01-6-15m-runtime-smoke`、`se-02b-opportunity-capture-attribution`、
  `n01-7-f01-latest-main-integration`、`se-arch-fix-01-latest-main-integration` 与
  `se-arch-fix-02-outcome-revision-chain-scope` 均仅 fast-forward 收编至 `main`，历史分支保留
- N01-8 Final Acceptance Closeout Branch: `n01-8-final-acceptance-closeout`（N01-8｜Final
  Acceptance Closeout；Closeout Base = latest accepted main `e0a5d2a2`；docs/state-only
  closeout commit，仅 fast-forward 收编 `main`）；Human-Accepted candidate branch
  `n01-8-12h-extended-soak` @ `d9306ada` 保持 immutable（远端 ref 未移动）
- Last Accepted Group Branch: `se-02c-final-acceptance-closeout`（SE-02C-FINAL；历史证据，保留未删）；更早 `n01-7-r01-witness-b-latest-main`、`se-arch-fix-02-outcome-revision-chain-scope`、`se-arch-fix-01-latest-main-integration`、`n01-7-f01-latest-main-integration`、`n01-6-15m-runtime-smoke`、`se-02b-opportunity-capture-attribution`、`se-02a-final-integration-refresh`、`n01-c-restart-recovery-reconciliation`、`n01-a-runtime-resource-lifecycle`、`n01-b-okx-paper-safety-continuity`（均保留未删）
- Accepted Main Source: Git `main` / `origin/main` — read actual SHA at task preflight（CIP-02）
- G5-1 Implementation Acceptance Basis: `34da62a0cc9dbe95b95faadb770fbd06179a6975`
- Migration Head: `20260913_0009`（SE-02A `20260911_0005` Edge evidence + N01-7-F01
  `20260912_0006` Position Protection Snapshot + SE-ARCH-FIX-01 `20260913_0007` Capture
  Anchor + `20260913_0008` Review Fix / Orphan + SE-ARCH-FIX-02 `20260913_0009` Outcome
  Revision Chain Scope；SE-02C / SE-02C-FIX-01 / SE-02C-FIX-02 / SE-02C-FINAL 均**未**新增
  migration；集成验证须保持单 head）
- Real AI Provider Status: `DEFERRED`（`OPENAI_API_KEY=MISSING`；测试用 deterministic Fake Provider）

## Completed

- 空工作区 Git 初始化。
- Foundation、Provider boundary、标准化模型、Universe 初版实现已建立。
- Backend/Frontend、PostgreSQL Docker、Alembic migration cycle、Auth、OpenAPI/type generation 已真实验证。
- OKX Spot/Swap REST identity、Trade/BBO/Kline WebSocket、OI/Funding、freshness、重连与 Universe 已真实验证。
- Group 1 已完成人工 Acceptance Review #1，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 2 已完成人工 Acceptance Review #2，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- Group 3 已完成人工 Acceptance Review #3，正式结果为 `PASS WITH NON-BLOCKING NOTES`。
- G3 Post-Acceptance Fix 与 Fix2 已人工验收，`PASS WITH NON-BLOCKING NOTES`。
- FG-A — G3 Execution Authority & Freshness：`ACCEPTED / COMPLETE`（accepted implementation
  `a9c2cd64bea0c6cc43b1ef8ad890e4db5353b801`；C04 accepted unblocker
  `d574e242f3aa7c26658ed6cc780fd8f744dbf503`；isolated Final Gate PASS）。
- C04 — Alembic Replay Test Isolation Fix：`ACCEPTED / COMPLETE`；无 production Alembic
  behavior 或 migration revision 修改。
- FG-B — Protection Concurrency：`ACCEPTED / COMPLETE`（accepted implementation
  `1c292b28e8e453b3c2e349b6b3b4f76c542341b1`；F03 / F06 = `ACCEPTED / FIXED`；
  FG-C = `NOT STARTED`）。
- FG-C — Safety Recovery Validity：`ACCEPTED / COMPLETE`（accepted implementation
  `39388acdd313d631e887a3d1786352bbee51caca`；F04 / F05 / C01 = `ACCEPTED / FIXED`；
  Acceptance Fix #2 已验证 C01 Case G 的 OPEN-position 三方保护生命周期与 F05 Case 2/3/4
  crash-boundary durable 证据；`state_version` 仅作为 risk-increasing freshness authority，
  不参与 open-position protection lifetime）。
- FG-E — Reconciliation Snapshot Consistency：`ACCEPTED / COMPLETE`（Human Acceptance
  confirmed；accepted implementation `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`；N02-1～N02-14
  evidence PASS；无 schema/migration 或 Control/Recovery/execution-accounting semantic change）。
- N01-FIX-01 — G2 EventRuntime Lifecycle Safety：`ACCEPTED / COMPLETE`（Task Base
  `d47313a1cb41996410606fe92b286a5046ed4fce`；accepted implementation
  `fc234b99dcbbd4f8dc2059a415b1b44d9f7f0a2b`；R01/R02/R03 与 PostgreSQL durable duplicate
  TOCTOU 已修复；无 schema/migration、Runtime Host、G3–G5 或业务语义修改）。
- N01-A — Deterministic Runtime + Resource Lifecycle：`ACCEPTED / COMPLETE`（Task Base /
  verified `origin/main` = `bc635787eafdf88fdc8e5810109452b5e394a076`；仅新增 deterministic
  validation；20 个 disposable PostgreSQL lifecycle、queue/backpressure、finite worker、同标的串行、
  BTC/ETH 并行、dedupe/retry/cancellation、task/queue/inflight/retention/session 证据均通过；无
  `backend/src`、schema/migration、Runtime Host、OKX 或 long-soak 改动）。
- N01-A Final Acceptance Closeout：`ACCEPTED / COMPLETE`；N01-A-F01/F02 = `CLOSED / PASS`；accepted
  validation lineage = `6321efb` → `facac1f` → `d67ffc2`；Final Closeout commit documented below。
- N01-B — OKX Reconnect / Freshness + Paper Safety Continuity：`ACCEPTED / COMPLETE`
  （Independent Review `PASS`；Human Acceptance `CONFIRMED`；Task Base / verified
  `refs/heads/main` = `a48673404abe256d0adb07c8139b129a54b4e7ce`；accepted validation lineage =
  `fc168c1` → `26688a2`；`N01-3 = ACCEPTED`、`N01-4 = ACCEPTED`）。真实 OKX SPOT metadata、真实
  `bbo-tbt` / `trades`、BTC-USDT 与 ETH-USDT 受控真实重连、FRESH → CONTROLLED STALE → FRESH 边界、
  `LIVE_PAPER` paper safety continuity（disposable PostgreSQL）均已真实验证；`Production code
  changed = NO`（`backend/src` / `backend/alembic` diff 为空）。Final Gate 重跑全绿：focused
  `3 passed`、G2 `30` / G3 `16` / G4 `77`、full backend `171 passed` ×2、Ruff / compileall /
  `git diff --check` PASS。详见 `dev_log/2026-09-10-n01-b-okx-paper-safety-continuity.md`
  「Final Acceptance Closeout」。
- N01-C — Restart / Recovery / Reconciliation：`ACCEPTED / COMPLETE`（Independent Review =
  `PASS / READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED`；Task Base / verified
  remote `main` = `6cc4c36e11c380f638872598e4766a4436d0d255`；branch
  `n01-c-restart-recovery-reconciliation`；isolated worktree
  `E:\Documents\MarketPulse-AI-n01-c`）。新增离网 deterministic cross-process validation：每个
  disposable PostgreSQL scenario 以 Process A durable `LIVE_PAPER` BTC-USDT LONG / plan /
  pending BUY / old heartbeat 后完全退出，再由 fresh Process B 从 PostgreSQL重建 RecoveryManager。
  覆盖 EXECUTION_GAP、official detector-only reconciliation、valid/invalid recovered BUY、HOLD /
  current-BBO SL exit、SAFE_MODE、PAUSED operator intent、BBO failure fail-closed、second-recovery
  economic idempotency，以及 client ownership cleanup / database drop。Final Gate：focused `6 passed`、
  lifecycle `6`、N01-B `4`、G2 `30`、G3 `16`、G4 `77`、full backend `179 passed, 1 warning`
  （exclusive writer evidence）；Ruff / compileall / diff-check PASS。`Production Code Changed = NO`。
  仅 fast-forward 收编至 `main`；不构成 N01 overall 或 N01-6/7/8 / Integrated Runtime Host 结论。详见
  `dev_log/2026-09-11-n01-c-restart-recovery-reconciliation.md`。
- N01-VAL-FIX-01 — PostgreSQL Lifecycle Evidence Stability：`ACCEPTED / COMPLETE`
  （Task Base / verified `refs/heads/main` = `e0dab188e55c32b7607c18a66644d25449dc2236`；
  branch `fix/n01-val-postgres-lifecycle-evidence`）。Finding `N01-VAL-F01` 已在当前 accepted
  `main` 上复现（40 次文件级执行中 2 次），并**证伪**"连接泄漏 / 服务端关闭可见窗口"假设：
  捕获到的多余 `pg_stat_activity` 行是 `backend_type='autovacuum worker'`、`usename=null`、
  `application_name=''` 的**服务端维护进程**（`last_query='autovacuum: ANALYZE
  pg_catalog.pg_class'`），不是任何 harness 连接。lifecycle gate 改为：每 cycle 唯一
  `application_name` 归属 + 按 `backend_type` 拆分 client/server + 有界最终条件等待
  （`client_sessions == 0`，hard deadline 1.0 s，实测最长关闭可见时间 8.3 ms）；新增注入泄漏
  负向对照（可检出、可安全释放）。`Production code changed = NO`。详见
  `dev_log/2026-09-10-n01-val-fix-01-postgres-lifecycle-stability.md`。
- N01-VAL-FIX-02 — N01-B PostgreSQL Activity Evidence Stability：`ACCEPTED / COMPLETE`
  （Task Base = `N01-VAL-FIX-01` 已评审 commit `67b0cb5e03bd6cb85e2df3ed873de10bed3325d2`，
  其 parent = Accepted Main `e0dab188e55c32b7607c18a66644d25449dc2236`；branch
  `fix/n01-val-n01b-postgres-activity-evidence`）。Finding `N01-VAL-F02`：N01-B 两个
  PostgreSQL 测试用 `datname`-only 聚合（`SELECT count(*) ... FROM pg_stat_activity WHERE
  datname = ...`）与 `activity_after == baseline` 证明 client connection cleanup，属错误
  ownership model。修复：每个测试唯一 `application_name` 归属（`marketpulse-n01-b-owned-*`）
  + observer 连接 primary 库不污染被测库 + 按 `backend_type` 拆分 client/server +
  有界最终条件等待（`client_sessions == 0`，hard deadline 1.0 s，尺度沿用 FIX-01 实测
  ≤8.3 ms）+ 极小注入泄漏负向对照；未引入 `baseline + 1` 容差，未用 sleep/retry 伪造清理证明。
  历史 8 次 full-suite 中的 1 次 `test_n01_b_freshness_boundary_...` 失败**无 traceback**，
  本窗口 12 次文件级 + 1 次 full suite 有界复现**未再捕获**，故明确记录为
  `single historical full-suite failure not independently recaptured`；Fix 依据为源码缺陷 +
  FIX-01 的既有捕获证据。`Production code changed = NO`。详见
  `dev_log/2026-09-10-n01-val-fix-02-n01b-postgres-activity-evidence.md`。
- N01-VAL-FIX-03 — G4 Protection / Limit-Fill Assertion Uniqueness：`ACCEPTED / COMPLETE`
  （Task Base = `14f387ac88af1ecd377fcd181c90b109ee361754`，即 N01-VAL-FIX-02 已评审 commit；
  branch `fix/n01-val-g4-order-assertion-uniqueness`）。Finding `N01-G4-F01`（Classification =
  Case B — Test Assertion Scope / Ambiguous Read Defect，**未**确认 production concurrency defect）：
  `test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen` 用非唯一谓词
  `PaperOrderRecord.plan_id == <pending plan>` + `Session.scalar()` 读取 pending BUY 状态；protective
  exit SELL 与 pending LIMIT BUY 合法共享同一 `plan_id`（`persist_trade_plan` REPLACE 旧 ACTIVE plan ⇒
  待成交 BUY plan 为唯一 ACTIVE ⇒ `_close_position_in` 以该 plan_id 建 SELL），`Result.scalar()`
  多行时静默返回首行、query 无 `ORDER BY` ⇒ 行序依赖物理堆序，负载相关。修复：pending BUY 改用
  唯一 identity `order_id`（以 `plan_id + side=BUY + order_type=LIMIT` 唯一谓词取得一次，断言
  `len == 1` 后一律 `session.get(PaperOrderRecord, order_id)`），并强化为 exact pending BUY
  (`side/order_type/status= CANCELLED/reserved_cash == 0`) + protective SELL (`side=SELL/status=FILLED`)
  + `protection.cancelled_order_ids` + `position.quantity == 0` + `fills == []` + 仅原始 BUY entry fill +
  reconciliation PASS；并发 witness（`after_risk_reducing_orders_lock` / `assert not fill.done()`）
  完整保留；**未**用 `ORDER BY` / `LIMIT 1` 规避。同构 tests-only ambiguity 一并最小修正
  `test_stop_loss_cancels_pending_add`（read 发生在 protective exit 之后），其余 13 处 `plan_id` 读取
  经审计为 Safe（读取窗口内该 plan 下只可能有一笔）未改。验证：目标测试 20/20；`test_group4.py`
  `77 passed` ×2；FIX-01 `6 passed`、N01-B `4 passed`、G2 `30`、G3 `16`；full backend
  `173 passed` ×2（**带 DB 客户端会话监控**，全程无外来写者）；Ruff / compileall /
  `git diff --check` PASS。`Production code changed = NO`。详见
  `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md`。
- N01 验证修复 Consolidated Final Acceptance Closeout：`ACCEPTED / COMPLETE`（2026-09-11；
  Independent Review = `PASS`；Human Acceptance = `CONFIRMED`）。N01-VAL-FIX-01 / FIX-02 / FIX-03
  的最终收尾门在本窗口重新执行：lifecycle `6 passed`、N01-B `4 passed`、G2 `30`、G3 `16`、
  G4 `77`、目标并发测试连续 `10/10`、full backend `173 passed` ×2（**带进程 + `pg_stat_activity`
  客户端会话采样 exclusivity 证据，全程无外来写者**）；Ruff / compileall / `git diff --check`
  （工作树 + range）PASS；`Production code changed = NO`。三个 Fix 的 devlog 均已追加
  `Consolidated Final Acceptance Closeout` 章节。accepted lineage（仅 fast-forward）：
  `e0dab188 → 67b0cb5 → 14f387a → 13049a0 → Consolidated Closeout Commit`；investigation branch
  `investigate/n01-g4-protection-limit-fill-race`（`201d9a8`）**保留、不 merge**。
- Group 4（持仓安全与恢复）已实现：Position Protection（SL/TP/Protective Exit/幂等）、Position Re-evaluation（HOLD/ADD/REDUCE/CLOSE/CANCEL_ADD/UPDATE_STOP/UPDATE_TP/UPDATE_INVALIDATION/REPLACE_PLAN）、System Safety State、Control（Pause/Resume/Emergency Stop/Emergency Recovery/Symbol Block/Manual Close/Safe Mode）、Recovery Manager（PostgreSQL SoT + Restart Recovery + Reconciliation Gate + Plan/Order Revalidation + EXECUTION_GAP）、Health Registry 与 Incident Manager。
- SE-02A｜Contracts + Additive Persistence：`ACCEPTED / COMPLETE`（2026-09-11/12；专项
  SE｜Strategy & Trading Edge 的第一个 Implementation Acceptance Batch；Independent Review =
  `PASS`；Human Acceptance = `CONFIRMED`）。只落地 Edge domain contracts 与 4 张 additive Edge 表
  + Alembic `20260911_0005`；**未**接 runtime capture、**未**实现 forward outcome calculator、
  **未**修改 G2/G3/G4/G5 业务语义。Final Acceptance Closeout 为 docs-only；accepted lineage
  （仅 fast-forward）：`b3ac21b → 2e7bf6a → 134aec5 → Final Closeout Commit`。
  Closeout 阶段 `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO`
  / `Contract changed = NO`。详见 `dev_log/2026-09-11-se-02a-edge-contracts-persistence.md`
  与本文「SE-02A Result」。
- N01-6｜15-minute Short Runtime Smoke：`ACCEPTED / COMPLETE`（Task Base / Accepted Main
  = `ab4bf297dff42a673d8dbf204dee8e4c0574aff9`；branch `n01-6-15m-runtime-smoke`；isolated worktree
  `E:\Documents\MarketPulse-AI-n01-6`；Independent Review = `PASS`；post-review docs-only
  Incremental Re-Review（`db3a0dc..3f591a7`）= `PASS`；Human Acceptance = `CONFIRMED`；
  Reviewed HEAD = `3f591a7694bf9e03dda53708a92c048dcea75fb3`）。以真实 OKX 公共行情（BTC-USDT +
  ETH-USDT SPOT，`trades` + `bbo-tbt`）+ 真实 disposable PostgreSQL（`marketpulse_n01_6_05c4a7071a16`，
  drop 后残留 0）让**已验收生产运行时组件**（`ScannerPipeline → OpportunityScanner → EventRuntime →
  PostgresG2Repository` + `SafetyRuntime`/`PositionProtectionService`/`SystemRiskGate`）连续运行
  **`900.143 s`**；normalized 事件 `24540`；queue 高水位 `0`、inflight 高水位 `1`、dedupe 峰值
  `4250`（cap 8192）、worker_exceptions `0`；RSS 峰值 `114.758 MB`（+3.18 MB）；max other client
  sessions `0`；`stale_periods=[]`；通过正式路径完成一笔受控 `LIVE_PAPER` BTC-USDT SPOT LONG 并
  在关停前 `MANUAL_CLOSE` 平仓（entry ask `77793.8` + 5 bps = `77832.6969`；exit bid `77838.6` −
  5 bps = `77799.6807`；trade `CLOSED`；cash `9999.7576`；reserved `0`）；reconciliation 12/12
  invariants PASS。Final Acceptance Closeout 复验门：focused `16 passed`、collect `267`、
  full backend `267 passed, 1 warning`（连续 PG 会话采样 114 样本 + 前后进程扫描，无外来写者）；
  Ruff `All checks passed!` / compileall rc=0 / `git diff --check`（工作树 + `ab4bf29..HEAD`）rc=0。
  Closeout 四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Harness changed = NO` / `Migration changed = NO`。accepted lineage（仅 fast-forward）：
  `ab4bf29 → db3a0dc → 3f591a7 → Final Closeout Commit`；evidence branch
  `n01-6-15m-runtime-smoke` 保留。详见
  `dev_log/2026-09-12-n01-6-15m-runtime-smoke.md`。

- SE-02B｜Opportunity Capture + Attribution：`ACCEPTED / COMPLETE`（2026-09-12 Human Acceptance &
  Final Acceptance Closeout；Independent Review = `PASS`；Human Acceptance = `CONFIRMED`；
  Human-Accepted reviewed tip = `6ce0c9214f552c0173e1f925315102506c3e9078`；branch
  `se-02b-opportunity-capture-attribution`；isolated worktree `E:\Documents\MarketPulse-AI-se-02b`；
  Task Base / Accepted Main before = `af81414160248c97f59a63b31fe615ea8ae14bbe`）。落地
  ① G2 SETUP Opportunity Capture（与 durable G2 facts **同一 PostgreSQL 事务**、atomic /
  fail-closed、immutable / append-only，遵循 SE-02A identity + hash + revision 契约）与
  ② Attribution（`Opportunity → AI → Plan → Risk → Execution → Economic Result`；append-only；
  exact authority / reason；显式 AI family selection；deferred LIMIT per-order restart-safe 归因）；
  新增 `backend/src/marketpulse/edge/capture.py` / `edge/attribution.py`，对 `g2/repository.py` /
  `g3/service.py` 仅做纯增量接线。**无新 migration**（head 仍 `20260911_0005`）。
  Acceptance blocker 由 SE-02B-FIX-01（P0-2 / P0-3 / P0-4 + P1）与 SE-02B-FIX-02
  （P0-1 Reference Quote Quality & Provenance，payload `se02b-runtime-capture-v2 → v3`）闭合后
  Independent Review = `PASS`。accepted lineage（仅 fast-forward）：
  `af81414 → f261766 → 7e86757 → b8a5fe3 → 0b8a275 → 6ce0c92 → Final Closeout Commit`。
  Closeout 阶段四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Contract changed = NO`。
  ⚠️ 本验收**不**构成 SE-02C / SE-02D / Forward Outcome Calculator / MFE-MAE / expectancy /
  Real AI Edge / Live / N01-7 / N01-8 / Integrated Runtime Host 的任何进度。
  详见 `dev_log/2026-09-12-se-02b-final-acceptance-closeout.md` 与本文「SE-02B Result」。

- N01-7-F01｜Durable Protection Snapshot（N01-7 前置 Fix）：`ACCEPTED / COMPLETE`（2026-09-13
  Human Acceptance = `CONFIRMED`（人工原文「确认 N01-7-F01 Human Acceptance，并执行 Final Main
  Integration」）+ Final Main Integration）。Reviewed candidate =
  `7c0ea7dd88c55fff301bfeef795088f44313c7d8`（branch `n01-7-f01-latest-main-integration`）；
  integration merge = `ddf39f2`（true merge：parent1 = 最新 main `1579707`，parent2 = 已复审
  F01 源 `c0ce0af`；`Reviewed Source Preserved = YES`）；Final Independent Review = `PASS`；
  R2 Independent Re-Review = `PASS`；Integration Review = `PASS`；
  E1 Writer Attribution = `FOREIGN WRITER CONFIRMED`；原始 shared-primary 指纹门
  = `INVALIDATED BY ENVIRONMENT / NON-BLOCKING`（**非** product failure）。
  既有验证据（**未**重跑）：F01 migration gate `PASS`、集成定向 `271 passed`、full backend
  `341 passed, 1 warning`、ruff / compileall / `git diff --check` `PASS`。
  Final Acceptance Closeout 为 docs/state-only：`Production code changed = NO` /
  `Tests changed = NO` / `Migration changed = NO`；`alembic heads` 单 head `20260912_0006`；
  accepted lineage 仅 fast-forward（`ddf39f2 → 7c0ea7d → Final Acceptance Closeout Commit`）。
  ⚠️ 本验收**不**构成 N01-7 2h soak / N01-8 / Integrated Runtime Host / Continuous Runtime /
  7×24 / Real AI Edge / Live 的任何进度（本验收不构成 `N01 overall` Acceptance；其后
  `N01 overall` 已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`）。详见
  `dev_log/2026-09-13-n01-7-f01-final-acceptance-closeout.md` 与
  `dev_log/2026-09-12-n01-7-f01-latest-main-integration.md`。

- N01-7 / N01-7-R01｜2-hour Medium Runtime Soak（含 Witness B Fix + Latest-Main Revalidation）：
  `ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance = `CONFIRMED` + Final Main Integration
  Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted reviewed candidate =
  `559f14be1fb89df58c11dfbea737eba4ac30421e`（branch `n01-7-r01-witness-b-latest-main`）；
  Accepted Main before = `8a29306d904223f03408fe55538ba6cb05222f15`；集成方法 =
  `FAST-FORWARD ONLY`（`8a29306 → 559f14b → docs-only closeout`，无 merge commit / squash /
  rebase / cherry-pick / force push；reviewed candidate identity 未改写）。真实 OKX 公共行情 +
  一次性 disposable PostgreSQL 单轮连续 `total_active 7320.252 s`（两独立进程 `3600.140` +
  `3720.113`、pid `11720 → 768`、`restart_gap 6.375 s`）、**84/84 checks true**、5 次受控重连 +
  2 次受控 STALE→FRESH + 7 checkpoint 全 ok + 跨进程 Recovery 15 步 + Witness A/B/C 全成立 +
  经济不变量全绿；`production_code_unchanged = true`、shared primary before == after、residue 0、
  起止两次 `ls-remote` 相同（run 期间 main drift = NO）；`alembic heads` 单 head
  `20260913_0009`。Closeout 四项不变：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`。
  🚩 P2 保留项 `N01-7-R01-RR-P2-01`（Memory Operational Watch / Bounded Retention Growth；
  slope `≈16.02 MiB/h` > `5.0`，`total_growth ≈14.043 MiB ≤ 64` ⇒ `finding = false`，
  Acceptance Gate = PASS）**必须**留给未来 `N01-8`；不得写 `memory resolved` / `memory is
  fine` / `no memory concern`。
  ⚠️ 本验收**不**构成 `N01 overall` Acceptance，也**不**自动解锁 `N01-8`；`N01-8` /
  `Integrated Runtime Host` 当时仍 `NOT STARTED`（N01-7 收尾时；其后 N01-8 已于 2026-09-14
  经 Human Acceptance 转 `ACCEPTED / COMPLETE`，见「N01-8 Result」）。详见
  `dev_log/2026-09-14-n01-7-final-acceptance-closeout.md` 与
  `dev_log/2026-09-13-n01-7-r01-witness-b-revalidation.md`。

- SE-ARCH-FIX-01｜Stable Evidence Anchor：`ACCEPTED / COMPLETE`（2026-09-13 Human Acceptance =
  `APPROVED` + Final Main Integration Closeout；Second Independent Re-Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
  `1e2738b09a4e4a62d91cfa8a6ffd6fcec3c71a21`；branch
  `se-arch-fix-01-latest-main-integration`；Accepted Main before =
  `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`）。落地 append-only
  `edge_opportunity_capture_anchors` + orphan 分类表，以 frozen causal payload / 稳定 T0 与
  reference BBO 作为 FORWARD_PAPER admission boundary；RRF-01（live-ingress ownership +
  session-start causal fence，proof `v1 → v2`）与 RRF-02（migration `20260913_0008`
  fail-closed abort + validated constraint）闭合后 Independent Re-Review = `PASS`。
  Closeout 为 docs-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`；accepted lineage 仅 fast-forward
  （`1e2738b → Human Acceptance（2026-09-13）→ Final Closeout Commit`）。P2 保留项
  `TEST-ISO-01` / `RRF-03` / `RRF-04` 仍 `NON-BLOCKING / DEFERRED`。
  ⚠️ 本验收**不**构成 `SE-ARCH-FIX-02` / `SE-02C` / `SE-02D` / Real AI Edge / Live / N01
  任何进度；`SE-ARCH-FIX-02 = NOT STARTED`、`SE-02C = BLOCKED / NOT STARTED`（SE-ARCH-FIX-01
  收尾时；二者其后均已经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）。
  详见 `dev_log/2026-09-12-se-arch-fix-01-stable-evidence-anchor.md`
  「Human Acceptance + Final Main Integration Closeout」。

- SE-ARCH-FIX-02｜Outcome Revision Chain Scope = `ACCEPTED / COMPLETE`（2026-09-13 Human
  Acceptance = `APPROVED` + Final Main Integration Closeout；Independent Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
  `15da7c1bac719d17271c7df9fcccbf80535b6d1b`；branch
  `se-arch-fix-02-outcome-revision-chain-scope`；Accepted Main before =
  `fc619242c99a794a2eb2b87ee02b8b72aa782f05`；Implementation Commit =
  `4c835828f482875d1d7ce934f8808d3953a9105b`）。Accepted semantic：outcome revision chain
  scope = `(opportunity_id, evidence_id, horizon)`；**数据库负责 scope integrity**
  （`uq_edge_outcome_id_scope` + 4 列 `fk_edge_outcome_supersedes`），**service 同时负责
  scope integrity 与 revision adjacency**（未引入 trigger）。Migration `20260913_0009`
  对存量 cross-scope 行 fail-closed abort。集成方法 = `FAST-FORWARD ONLY`
  （`fc619242 → 4c835828 → 15da7c1 → docs-only closeout`，无 merge commit / squash /
  rebase / cherry-pick / force push）。Closeout 四项不变：`Production code changed = NO` /
  `Tests changed = NO` / `Migration changed = NO` / `Runtime config changed = NO`；
  `alembic heads` 单 head `20260913_0009`。P2 保留项 `TEST-ISO-01` / `RRF-03` / `RRF-04`
  仍 `NON-BLOCKING`（`RRF-03` `DEFERRED`）。⚠️ 本验收**不**构成 `SE-02C` / `SE-02D` /
  Forward Outcome Calculator / MFE-MAE / expectancy / Real AI Edge / Live / N01 任何进度。
  详见 `dev_log/2026-09-13-se-arch-fix-02-outcome-revision-chain-scope.md`
  「Human Acceptance + Final Main Integration Closeout」。

- SE-02C｜Forward Outcome Calculator：`ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance =
  `CONFIRMED` + Final Acceptance Closeout；Independent Re-Review = `PASS WITH NON-BLOCKING
  FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
  `7bb3835d6b14a3fc86becff1881c7f53f1acd567`（branch `se-02c-fix-02-stable-read-snapshot`，
  远端同 SHA 未被移动）；Accepted Main before = `dd78a979…`；集成方法 = `FAST-FORWARD ONLY`
  （accepted lineage 仅 fast-forward：`dd78a979` → `51891c7`（true merge：`dd78a979` ×
  `be3aa6c`）→ `7ab1d42` → `2f98682` → `6b08459` → `7bb3835` → docs-only closeout commit；
  无 merge commit 到 `main` / squash / rebase / cherry-pick / force push）。已验收能力：
  Forward Outcome Calculator（30s / 5m / 15m / 1h 四 horizon）+
  stable Capture Anchor reference + complete Forward BBO path + deterministic endpoint +
  MFE / MAE + reference return + executable LONG return + paper cost-adjusted return +
  仅 `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID` 终态 + revision-1 immutable normal outcome +
  retry / restart determinism + concurrent exactly-one + stable `REPEATABLE READ` calculation
  snapshot + same-scope PostgreSQL advisory coordination + tradability authority +
  Replay / Forward provenance separation。Closeout 四项不变：`Production code changed = NO` /
  `Tests changed = NO` / `Migration changed = NO` / `Runtime config changed = NO`；
  `alembic heads` 单 head `20260913_0009`。遗留 `SE02C-R7` = `P3 / NON-BLOCKING / NOT FIXED`
  （Human Accepted non-blocking finding；**未**在本窗口修改
  `backend/src/marketpulse/edge/forward_service.py`）。⚠️ 本验收**不**构成 `SE-02D` /
  Family Aggregation / Expectancy / Real AI Edge / Live / N01-8 / Integrated Runtime Host
  的任何进度。详见 `dev_log/2026-09-14-se-02c-final-acceptance-closeout.md`。

- N01-8｜12-hour Extended Runtime Soak：`ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance =
  `CONFIRMED` + Final Acceptance Closeout；Independent Review = `PASS WITH NON-BLOCKING
  FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed candidate =
  `d9306ada663a5cacb86bee26218e298169d82e6b`（branch `n01-8-12h-extended-soak`，远端同 SHA
  未被移动）；Frozen Task Base = `dd78a979…`；Closeout Base = `e0a5d2a2…`；集成方法 =
  `FAST-FORWARD ONLY`（`e0a5d2a2 → docs/state-only Final Acceptance Closeout Commit`，单
  parent；无 merge commit / squash / rebase / cherry-pick / force push；**未**把 `main` 回退到
  `dd78a979`，**未**丢失 SE-02C / PRE-01A-D1 已接受状态）。验收依据（单轮全新正式 Run）：
  真实 OKX 公共行情 + 一次性 disposable PostgreSQL + detached supervisor 连续
  `total_active 44401.217470 s`（≥ 43200）、4/4 phase complete、3 次 fresh-process restart、
  12 次受控重连、6 次受控 STALE→FRESH、24/24 reconciliation checkpoint PASS、**99/99 aggregate
  checks True**、`failures = []`；`production_code_unchanged = true`；shared primary before ==
  after；disposable residue `0`；Power Loss = `RUN COMPLETED BEFORE POWER LOSS`（power-loss
  invalidation = `NO`）。Independent Review 裁定 Baseline Drift = `NO MATERIAL IMPACT`，
  Targeted Revalidation = `NOT REQUIRED`，Full Rerun = `NOT REQUIRED`。Closeout 五项不变：
  `Production code changed = NO` / `Migration changed = NO` / `Tests changed = NO` /
  `Frontend changed = NO` / `Runtime config changed = NO`；`alembic heads` 单 head
  `20260913_0009`；`DECISIONS.md changed = NO`（无新增产品 / 架构决策）。
  🚩 P2 保留项 `N01-7-R01-RR-P2-01` = **`REMAINS`**（P2 / NON-BLOCKING / Memory Operational
  Watch / Bounded Retention Growth）：本 Run 冻结 AND contract（`growth > 64 MiB` **AND**
  second-half `slope > 5 MiB/h`）Formal Finding = `FALSE`（`RSS growth 77.711 MiB`、second-half
  slope `−0.639369 MiB/hour`）⇒ Formal Acceptance **不**被 Memory Finding 阻塞，但
  operational watch **未**闭合；**不得**写 `memory resolved` / `memory is fine` /
  `no memory concern`。P3 findings（`N01-8-IR-P3-01` / `P3-02` / `P3-03`）保留为
  `NON-BLOCKING`，**未**升级 P1/P0。
  ⚠️ 本验收**不**构成 `Integrated Runtime Host` / Continuous Runtime / 7×24 / `SE-02D` /
  Real AI Edge / Live 的任何进度（`N01-8` 收尾时 `N01 overall` 尚未验收；其后已于
  2026-09-14 经 N01 Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）。
  详见 `dev_log/2026-09-14-n01-8-extended-soak.md`（§47 Final Acceptance Closeout）。

## In Progress

- **SE-ARCH-FIX-01｜Stable Evidence Anchor = `ACCEPTED / COMPLETE`**（2026-09-13 Human Acceptance
  = `APPROVED` + Final Main Integration Closeout）。该 `INTEGRATED / READY FOR INDEPENDENT
  RE-REVIEW` 状态已由本次 Human Acceptance 取代：Second Independent Re-Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`（无 P0/P1；AC 全 PASS；Integration AC 全 PASS；
  RRF-01 PASS；RRF-02 PASS；full backend `363 passed`；Ruff / compileall / `git diff --check`
  PASS；`alembic heads` 单 head `20260913_0008`；accepted N01-7 `20260912_0006` preserved；
  Historical Replay 未获得 Forward issuer）。Human-Accepted reviewed candidate =
  `1e2738b`（branch `se-arch-fix-01-latest-main-integration`）；已 fast-forward only 收编 `main`。
  参见 Completed、Acceptance Record 与「SE-ARCH-FIX-01 Result」。
- **SE-ARCH-FIX-02 = `ACCEPTED / COMPLETE`**（2026-09-13 Human Acceptance = `APPROVED` + Final
  Main Integration Closeout；Human-Accepted reviewed candidate = `15da7c1`，implementation
  `4c83582`；branch `se-arch-fix-02-outcome-revision-chain-scope`；已 fast-forward only 收编
  `main`。forward-outcome revision chain scope 收敛为 `(opportunity_id, evidence_id, horizon)`：
  service 校验 + migration `20260913_0009` scoped FK 双层 fail closed；DB 负责 scope integrity，
  service 负责 scope integrity + adjacency。**不**因此启动 SE-02C，见 Completed / Acceptance
  Record / 「SE-ARCH-FIX-02 Result」）。
- **SE-02C｜Forward Outcome Calculator = `ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance
  = `CONFIRMED` + Final Acceptance Closeout；Human-Accepted reviewed candidate = `7bb3835`；
  已 fast-forward only 收编 `main`；见 Completed、Acceptance Record 与本文「SE-02C Result」）。
  其实现在 2026-09-13 实现 + 验证窗口落地（branch `se-02c-forward-outcome-calculator` @
  `7a68bf0`，worktree `E:\Documents\MarketPulse-AI-se-02c`，base `8a29306`；当时**未**
  merge `main`、**未** push `main`、**未**自行 Acceptance）：纯确定性计算核心
  `edge/forward.py`（冻结 V1 mid/return/MFE-MAE 公式 + 精确乘性
  `SPOT_LONG_TAKER_ROUND_TRIP` 成本模型 + `due_at = evidence_at + duration` +
  FIX-01 anchor 参考权威 + 5 s endpoint TTL + 仅 COMPLETE/INSUFFICIENT_DATA/INVALID 终态 +
  `created_at` 冻结为 `due_at`）、durable orchestration `edge/forward_service.py`
  （Forward BBO path recorder 复用 `record_bbo_observation`、durable due discovery、
  bounded evaluation API，永不写 revision > 1）、`g2/runtime.py` 最小 opt-in live-ingress hook。
  **无新增 migration、无 schema 变更**：`alembic heads` 仍单 head `20260913_0009`。
  历史验证门（实现窗口）：SE-02C focused 46 passed、SE-02A/SE-02B/G5 命名回归 196 passed、
  full backend 417 passed、`ruff check` 全绿。
  见 `dev_log/2026-09-13-se-02c-forward-outcome-calculator.md` 与
  `dev_log/2026-09-14-se-02c-final-acceptance-closeout.md`。
- **SE-02D｜Family Aggregation / Expectancy = `ACCEPTED / COMPLETE`**（2026-09-16 Human
  Acceptance = `CONFIRMED` + SE-02D Overall Final Acceptance Closeout；Overall Final Review =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed
  baseline = `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`；`SE-02D Overall = ACCEPTED / COMPLETE`；
  `SE02D-OVERALL-R01-P3-01` / `P3-02` = `CLOSED`）。**`SE-02D-I01｜Deterministic Aggregation
  Core`（纯确定性聚合 / 统计内核）= `ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance =
  `CONFIRMED` + Final Acceptance Closeout；Independent Initial Review = `FAIL — FIX
  REQUIRED`；FIX-01 Independent Re-Review = `PASS`；`SE02D-I01-R1` / `R2` / `R3` =
  `CLOSED`；Human-Accepted reviewed candidate = `13b37df…`（branch
  `se-02d-i01-aggregation-core`，immutable）；集成方法 = `FAST-FORWARD ONLY`）。
  - **I01 own 的范围**：pure deterministic aggregation / statistics core
    （`marketpulse.edge.aggregation`；**不** fold revision chain，只消费已 canonicalize 的
    scope facts）。
  **`SE-02D-I02｜Current-Snapshot Revision Folding` = `ACCEPTED / COMPLETE`**（2026-09-15
  Human Acceptance = `CONFIRMED`；Independent Initial Review = `FAIL — FIX REQUIRED`；
  FIX-01 Independent Re-Review = `PASS`；`SE02D-I02-R1` / `R2` / `R3` = `CLOSED`；
  Human-Accepted reviewed candidate = `9b86043…`（branch
  `se-02d-i02-current-snapshot-folding`，immutable）；latest-main content-level
  carry-forward + `FAST-FORWARD ONLY`）。
  - **I02 own 的范围（已实现 / 已验收）**：`marketpulse.edge.aggregation_snapshot` ——
    单个 PostgreSQL `REPEATABLE READ` / `READ ONLY` 快照；数据库 `statement_timestamp()`
    作 `as_of`；全量可见 Evidence revision-chain 校验 / 折叠；canonical Evidence head
    selection；精确 horizon Outcome revision-chain 校验 / 折叠；canonical Outcome head /
    `NO_OUTCOME`；canonical Evidence ↔ Outcome cross-integrity；`CanonicalScopeFacts`
    projection；扩展 I01 canonical manifest 的 revision-aware manifest。
  **`SE-02D-I03｜Population Grouping + Aggregate Orchestration` = `ACCEPTED / COMPLETE`**（2026-09-16
  Human Acceptance = `CONFIRMED`；Initial Independent Review = `FAIL — FIX REQUIRED`；
  `SE02D-I03-R1`（P1）= `CLOSED`；FIX-01 Independent Re-Review = `PASS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted reviewed HEAD = `20a7c33…`（branch
  `se-02d-i03-fix-01-projection-identity-validation`，immutable）；Original Reviewed Candidate
  = `44d0e4b…`（branch `se-02d-i03-population-aggregate-orchestration`，immutable）；
  `FAST-FORWARD ONLY`）。
  - **I03 own 的范围（已实现 / 已验收）**：`marketpulse.edge.aggregation_orchestration` ——
    消费一份 I02 `CurrentSnapshotProjection`；facts ↔ revision-aware manifest 一一对应完整性门
    （fail closed）；按完整结构 `PopulationKey` 分组；每个 population **恰好一次** I01
    `aggregate()` 调用；确定性 population 排序；薄 async 单次读 wrapper。**不** own 统计 /
    revision folding / DB snapshot 语义 / 新 Population Key 语义 / Measurement Signature
    语义 / API & product 集成。
  - **剩余工作措辞（2026-09-16 经 `SE-02D-CLOSE-D01` 调和）**：aggregate capability =
    `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`（**不**再写 “NOT YET IMPLEMENTED”）；
    API / frontend / runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`
    （`DEFERRED` 至未来 consumer / product / Gate C 任务；**不存在**且**有意**在 V1 完成范围之外）；
    historical arbitrary revision-as-of support = `OPEN`；`I04 = NOT REQUIRED FOR SE-02D V1`；
    `SE-02D V1` capability implementation = `COMPLETE AFTER I03`。
  - ✅ **`SE-02D Overall = ACCEPTED / COMPLETE`**（2026-09-16 Human Acceptance = `CONFIRMED` +
    SE-02D Overall Final Acceptance Closeout）：**`I01 / I02 / I03 / CLOSE-D01 Accepted` 当时
    ≠ `SE-02D Overall Complete`**（各批收尾时；其后整体验收已于 2026-09-16 完成）；
    `SE-02D` **不**构成 KEEP / DOWNWEIGHT / KILL（V1 不输出任何 label）
    / `Gate C = PASS` / `Live` 授权。
- **`SE-02D-D01`（Family Aggregation / Expectancy Contract，设计层）= `ACCEPTED / COMPLETE`**
  （2026-09-15 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Human-Accepted
  candidate = `245b068…`，immutable；Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`；该 Acceptance
  **仅**接受设计契约）。
- SE-02C 的**验收**（`ACCEPTED / COMPLETE`）**不**构成 SE-02D 的启动授权；SE-02D /
  Integrated Runtime Host 仍须另开窗口并经批准的门执行（该句写于 SE-02C 收尾时；N01-8 其后
  已另行获批并执行完毕，见 Completed 与「N01-8 Result」；SE-02D 亦已于 2026-09-16 经 SE-02D
  Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）。
- **SE-02B 已关闭**：`ACCEPTED / COMPLETE` 并已 fast-forward only 收编 `main`（见 Completed、
  Acceptance Record 与「SE-02B Result」）；其 3 个历史状态项
  （`IMPLEMENTED / WAITING HUMAN ACCEPTANCE`、SE-02B-FIX-01 / FIX-02
  `READY FOR INDEPENDENT RE-REVIEW`）已由本次 Final Acceptance Closeout 取代。
- **SE-02A｜Contracts + Additive Persistence 已完成验收收尾
  （`ACCEPTED / COMPLETE`；见 Completed 与本文「SE-02A Result」）**。其 reviewed implementation
  source = branch `se-02a-contracts-additive-persistence` @ `0c206c9`；最终收编经 refresh
  integration branch `se-02a-final-integration-refresh`（`b3ac21b → 2e7bf6a → 134aec5 →
  Final Closeout Commit`，仅 fast-forward）。SE-02C / SE-02D / Forward Outcome Calculator /
  Real AI Edge / Live 当时仍 **NOT STARTED**（SE-02A 收尾时；其后 SE-02C 已于 2026-09-14 经
  Human Acceptance 转为 `ACCEPTED / COMPLETE`）；runtime opportunity capture 已由 SE-02B 落地
  （`ACCEPTED / COMPLETE`，见上）。
- **N01-7-F01｜Durable Protection Snapshot（N01-7 前置 Fix）= `ACCEPTED / COMPLETE`**
  （2026-09-13 Human Acceptance = `CONFIRMED` + Final Main Integration；branch
  `n01-7-f01-latest-main-integration`；integration merge commit `ddf39f2` = 最新 main `1579707` ×
  已复审 F01 源 `c0ce0af`，true merge、`Reviewed Source Preserved = YES`；已 fast-forward only
  收编 `main`；见 Completed、Acceptance Record 与
  `dev_log/2026-09-13-n01-7-f01-final-acceptance-closeout.md`）。
- **`N01-7 / N01-7-R01 = ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance = `CONFIRMED` +
  Final Main Integration Closeout；Human-Accepted reviewed candidate = `559f14b`；Accepted Main
  before = `8a29306`；已 fast-forward only 收编 `main`；见 Completed、Acceptance Record 与本文
  「N01-7 / N01-7-R01 Result」）。该项本身不单独构成 `N01 overall` Acceptance（`N01 overall`
  已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）。
- **`N01-8｜12-hour Extended Soak = ACCEPTED / COMPLETE`**（2026-09-14 Human Acceptance =
  `CONFIRMED` + Final Acceptance Closeout；Human-Accepted reviewed candidate = `d9306ada`；
  已 fast-forward only 收编 `main`；见 Completed、Acceptance Record 与本文「N01-8 Result」）。
  该项本身不单独构成 `N01 overall` Acceptance（`N01 overall` 已于 2026-09-14 经 N01 Overall
  Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`）。
- **`PRE-01B-D1｜Integrated Runtime Host Formal Design = ACCEPTED / COMPLETE`**（2026-09-15 Human
  Acceptance = `CONFIRMED` + Final Acceptance Closeout；Human-Accepted reviewed candidate =
  `80cb2ba`，branch `design/pre-01b-d1-runtime-host-contract`，immutable；Independent
  Review = `PASS WITH NON-BLOCKING FINDINGS`；已 fast-forward only 收编 `main`；
  见 Current Group 与本文「PRE-01B-D1 Result」）。该 Acceptance **仅**
  接受 Formal Design，**不** 构成 `Integrated Runtime Host Implementation`
  的任何进度。
- **`PRE-01B-I1｜Integrated Runtime Host Core V1 Implementation = ACCEPTED / COMPLETE`**（2026-09-15 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout & Latest-Main Reconciliation；Human-Accepted reviewed candidate = `68dd7e9`，branch `pre-01b-i1-fix-01-runtime-host-lifecycle`，immutable；Original Candidate = `b66e17d…`；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS`；已 content-level carry-forward 收编 latest `main` `0ae5b0b…`（drift 正交 = `SE-02D-I01`，未触碰任何 PRE-01B 路径）；见 Current Group 与本文「PRE-01B-I1 Result」）。该 Acceptance 接受 **Implementation Core V1**，**不** 构成 OS/service deployment / Real AI activation / G2→G3 activation / `SE-02D` Production complete / Live Trading 的任何进度。
- **`Integrated Runtime Host Core V1 Implementation = ACCEPTED / COMPLETE`**（PRE-01B-I1，2026-09-15 Human Acceptance = `CONFIRMED`；content-level carry-forward 收编 latest `main` `0ae5b0b…`；集成方法 = `FAST-FORWARD ONLY`）。**不** 构成 OS/service / WinSW process supervision / Real AI activation / G2→G3 live handoff / `SE-02D` Production complete / Live Trading 的任何进度（这些仍 `NOT COMPLETE / DISABLED / NOT AUTHORIZED`）。
- **`PRE-01B-D2｜AdvisoryIngress / durable G2→G3 Activation Contract Formal Design = ACCEPTED / COMPLETE`**（2026-09-17 Human Acceptance = `CONFIRMED` + Final Acceptance Closeout；Human-Accepted reviewed candidate = `cce1ae7`，branch `design/pre-01b-d2-fix-05-return-completion-authority`，immutable；Independent Re-Review = `PASS`；P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NONE`；已 fast-forward only 收编 `main`；见 Current Group 与本文「PRE-01B-D2 Result」）。该 Acceptance 接受 **AdvisoryIngress / durable G2→G3 Activation Contract 的 Formal Design**，**不** 构成 `PRE-01B-I2` implementation / live G2→G3 activation / Real AI activation / Gate A / Gate B / Gate C / Live 的任何进度。
- **`UI-V1-D01｜MarketPulse UI V1 Formal Design = ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`**（2026-09-17 Human Acceptance = `CONFIRMED` + Final Acceptance / Main Integration Closeout；Independent Final Repository Review = `PASS`，P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NONE`；Human-Accepted / Reviewer-approved final candidate = `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4`，branch `design/ui-v1-d01-final-doc-fix-02`，immutable；已 fast-forward only 收编 `main`；见 Current Group 与本文「UI-V1-D01 Result」/「UI-V1-D01 Final Acceptance Closeout Result」）。该 Acceptance 接受 **MarketPulse UI V1 Formal Design**，**不** 构成 UI implementation（仍 `NOT STARTED`）/ Product Read API implementation / `UI-F01` / `UI-RD01` / `PRE-01B-I2` implementation / live G2→G3 activation / Real AI activation / Gate A / Gate B / Gate C / Live 的任何进度。
- **`UI-F01-I01｜Frontend Foundation = ACCEPTED / COMPLETE`**（2026-09-17 Human Acceptance =
  `CONFIRMED` + Final Acceptance Closeout；Independent Initial Review = `FAIL — FIX REQUIRED`；
  Finding `UI-F01-I01-R1` → FIX `UI-F01-I01-FIX-01`（`ACCEPTED / CLOSED`）；Independent Re-Review
  = `PASS — READY FOR HUMAN ACCEPTANCE`；Final Re-Review severity：P0 = `NONE` / P1 = `NONE` /
  P2 = `NONE` / P3 = `NON-BLOCKING ONLY`；Human-Accepted reviewed candidate = `ecc213568`，branch
  `ui-f01-i01-fix-01-transport-error-boundary`，immutable；original implementation candidate =
  `0c9186d2`，branch `ui-f01-i01-frontend-foundation`，immutable；closeout branch =
  `ui-f01-i01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`；Final Regression =
  `typecheck` / `7 files / 44 tests` / `build` / `check:api-drift` 全 exit 0；见 Current Group
  与本文「UI-F01-I01 Result」/「UI-F01-I01 Final Acceptance Closeout Result」）。
  **本 Acceptance 仅接受 Frontend Foundation 本身**：正式业务页面（五页仍为占位）=
  `NOT STARTED`；Product Read API = `NOT STARTED`；`UI-F01 = ACCEPTED / COMPLETE` **不**构成
  `UI-RD01` / `UI-I01..UI-I06` 的实现或自动授权。
- **N01-A / N01-B / N01-C / N01-6 / N01-7-F01 / N01-7（N01-7-R01）/ N01-8 均已
  `ACCEPTED / COMPLETE`**（见 Completed）；`N01 overall` 亦已于 2026-09-14 经 N01 Overall
  Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`（该总体结论由独立的 Overall Final
  Review / Acceptance 确立，不由任何单门 N01 验收自动推断）。
- N01 Continuous Runtime / Soak 线（`N01 overall`）= `ACCEPTED / COMPLETE`（2026-09-14）；
  其 claim 边界见「N01 Overall Result」与 N01 Overall Final Acceptance Closeout dev_log。
- N01-6 15m Runtime Smoke、N01-7（含 N01-7-R01）与 N01-8 12h Extended Soak 均已完成 Final
  Acceptance Closeout 并 `ACCEPTED / COMPLETE`（见 Completed 与
  `dev_log/2026-09-12-n01-6-15m-runtime-smoke.md` /
  `dev_log/2026-09-14-n01-7-final-acceptance-closeout.md` /
  `dev_log/2026-09-14-n01-8-extended-soak.md`）。`Integrated Runtime Host` 仍 `NOT STARTED`，
  须另开窗口并按各自批准的门执行。N01 Overall Final Review / Acceptance 已完成
  （2026-09-14；见「N01 Overall Result」）；下一步的 Runtime 边界为 `Integrated Runtime Host`
  （`NOT STARTED`，**不得**自动启动）。

## Blocked

- 无阻塞。

## Current Architecture Baseline

- Python/FastAPI/asyncio backend；React/TypeScript/Vite frontend；PostgreSQL via Docker；SQLAlchemy/Alembic。
- Raw Adapter → Normalized Data → 后续 Derived Features。
- 默认 `LOCAL_ONLY=true`，默认 `RUN_MODE=TEST`。
- OKX Spot 与 Swap 使用不同 `market_type` 和 `instrument_id`。
- G4 增加：System/Operator State 分离；统一 Risk Gate；PostgreSQL 为 Restart Recovery 唯一事实源；Protective Exit 一律以当前 Fresh Best Bid − slippage 成交（Stop/TP 仅触发价）；Position Event 追加审计；Trade.exit_reason。

## Current Runtime Facts

- G2 Event Runtime 使用有界 asyncio 优先队列与有限 worker pool；同 `instrument_id` 串行。
- G3 不可变 Decision Snapshot、Provider-neutral AI boundary、Account Row Lock 事务内写 Order/Fill/Position/Account/Ledger/Outbox。
- G4 运行时：SL/TP 不经 AI Queue；同 Symbol 串行（asyncio lock + DB row lock）；Risk Gate 锁定 runtime_control 行后决定风险增加动作是否放行；EMERGENCY_STOP 原子取消 OPEN BUY 并释放 Reservation（≠ Close All）；SAFE_MODE 锁存需显式恢复 → PAUSED → 人工 Resume。
- G4 stale core data（N01-B verified）：`CORE_MARKET_DATA = UNAVAILABLE`，`CORE_DATA_STALE`
  incident OPEN，风险增加 BUY 经 `SystemRiskGate` fail-closed（`RUNTIME_STATE_DATA_DEGRADED`，
  standalone 与 G3 事务内一致）；SELL 风险降低**不**因 stale 被禁止，但保护性成交仍要求
  executable fresh BBO，stale 下不 fabricate fill；fresh 恢复后 health HEALTHY 且
  `CORE_DATA_STALE` 按既有语义 RESOLVED。

## Known Issues

- 原「Pre-existing flaky test」（`N01-G4-F01`）**根因已定位、已修复、已验收、已收入 `main`**：
  `backend/tests/test_group4.py::test_fg_b_protection_wins_against_concurrent_limit_fill_without_reopen`
  在负载下的 full-suite 上下文中可能失败（`assert order.status == OrderStatus.CANCELLED ... got
  FILLED`，`test_group4.py:1709`）。分类 = **Case B — Test Assertion Scope / Ambiguous Read
  Defect**（**非** production concurrency defect）：pending LIMIT BUY 与 protective exit SELL
  合法共享同一 `plan_id`，而断言用非唯一 `plan_id` 谓词 + `Session.scalar()`（多行静默取首行）+
  无 `ORDER BY`，故结果依赖物理堆序。N01-G4-INV-01 已以 PostgreSQL lock evidence 确证；N01-VAL-FIX-03
  改为按唯一 `order_id` 读取并强化断言，`N01-VAL-FIX-03 = ACCEPTED / COMPLETE`（目标测试 20/20 + 收尾门连续 10/10、full backend
  监控下 `173 passed` ×2），并已随 Consolidated Final Acceptance Closeout fast-forward 收入
  `main`。证据见
  `dev_log/2026-09-11-n01-val-fix-03-g4-order-assertion-uniqueness.md`。
- **环境级约束（`KNOWN TEST-ENVIRONMENT CONSTRAINT` / NON-PRODUCTION / NON-BLOCKING）**：本仓库
  全量套件使用**单一共享 PostgreSQL 数据库**，且
  `Harness.clean()` 会整表清空 `RunMode.REPLAY` 行 ⇒ **任何两个并发会话在全量套件层面必然互相
  破坏**（观测签名：`open_position()` 得到 `PLAN_REPLACED`，因另一写者替换了同
  `(run_mode, instrument_id)` 的 ACTIVE plan）。N01-VAL-FIX-03 的 full-suite 门首次尝试即被另一
  WorkBuddy 会话通过 Bash 发起的 `pytest backend/tests` 污染（`10 failed, 163 passed`），
  在 N01-VAL-FIX-03 与 Consolidated Closeout 中均以「进程扫描 + `pg_stat_activity` 客户端会话
  采样」建立 exclusivity 证据后才采信；运行期间若监测到外来 writer，该 run 标记
  `INVALIDATED BY ENVIRONMENT` 并在恢复 exclusivity 后重跑（不「重试至通过」）。建议后续另开
  窗口评估（例如按会话隔离数据库或加互斥），**不在**本次 Scope 内。
- 真实 AI Provider 集成 = `DEFERRED`（`OPENAI_API_KEY=MISSING`）。Position Re-evaluation contract 以 deterministic Fake Provider 验证，未伪造真实 AI 结果。
- Real OKX Paper Protection / Restart Recovery smoke 已用真实 BTC-USDT BBO 完成（`LIVE_PAPER`，无 Live 下单）。
- FastAPI TestClient 上游 deprecation warning 仍存在（2 处，不影响结果）。

## Group 4 Result

- G4 PostgreSQL 场景测试（`test_group4.py`）覆盖 A–U、失败注入、Post-Review Fix #1–#4 回归：`45 passed`。
- 全量 `pytest backend/tests`：`72 passed`，1 个既有 FastAPI/Starlette deprecation warning。
- `ruff check backend/src backend/tests scripts` / `compileall` / `git diff --check`：PASS。
- `alembic current` / `alembic heads`：`20260905_0004 (head)`。
- Restart smoke（`scripts/g4_verify_runtime.py setup/recover`）：两进程 PostgreSQL 重建 → `RUNNING`、`active_symbols=['BTC-USDT']`、`reconciliation_ok=True`。

### Post-Review Fix #1

- P0-1：AI 重估值在 provider 返回后、dispatch 前重验 DB 的 state_version / active plan(plan_id+version) / position lifecycle，变化判 STALE，记 `AIDecisionRecord.status=STALE_DECISION` + `PositionEvent(AI_REEVALUATION)`，返回 HOLD 零副作用。
- P0-2：Recovery 捕获重启前 `system_state` 锁存 SAFE_MODE；未解决 blocking incident 不得进入 RUNNING。
- P0-3：Recovery `_revalidate` 严格 §33（TTL / state_version / entry / stop-invalidation / BBO freshness），final state 非 RUNNING（SAFE_MODE/EMERGENCY_STOP/ERROR）取消残留 OPEN BUY 并释放 Reservation。
- P1-1：Recovery 与 Orchestrator 的 BBO 新鲜度判断加入 `DataQuality.FRESH`。
- P1-2：`active_symbols` 仅来自 OPEN Order / quantity>0 Position / ACTIVE Plan。
- P1-3：Reconciliation 不变量 #10 增测 closed lifecycle 后残留的风险增加 BUY（`BUY_AFTER_CLOSED_LIFECYCLE`）。

### Post-Review Fix #2

- P0-1 Recovery §33：OPEN BUY 在恢复事务内重验 current Fresh Best Ask、entry zone、stop breach、persisted symbol block 与 G3 cash/capacity；失效订单原子 cancel 并释放 Reservation，不 retroactive fill。
- P0-2 AI TOCTOU：provider 后使用 action-time clock 与重新获取的 executable BBO；最终 stale facts（state_version、expected active plan/version、position/trade lifecycle）在 PostgreSQL 行锁事务内校验并保持到 mutation commit。
- `PlanManager.replace()` 改为 expected-current conditional update；旧 plan 非当前 ACTIVE 时返回 stale，保留 `uq_trade_plans_one_active`，不再 replace symbol 下所有 ACTIVE plan。
- P1 Recovery BBO failure：OPEN Position 的 exception/missing/unusable BBO 持久化 `CORE_DATA_STALE` Incident，Health 标记 UNAVAILABLE，恢复落在非 RUNNING。
- 修复 SAFE_MODE recovery 的 blocking-incident 可达性：仅在 health/reconciliation 与 position protection durable facts 通过后，于同一控制事务 resolve 并落到 PAUSED。
- 新增 8 个真实 PostgreSQL 回归测试；真实 AI Provider 因 `OPENAI_API_KEY=MISSING` 为 `DEFERRED / NOT VERIFIED`。

### Post-Review Fix #3

- `load_active_plan()` 现只在恰好一条 ACTIVE row、payload 可由 `TradePlan.model_validate` 加载，且 payload 与 durable row 的 plan identity / run_mode / instrument / version / status / timestamps 一致时返回计划；否则 fail closed。
- 共用的 plan business validation 检查 entry-zone、SL/TP 与当前 LONG `average_cost` 的保护关系（`stop_loss < average_cost < take_profit`）；Safe Mode Recovery 与普通 Resume 都以此证明 OPEN Position 真实受保护，不能以 raw/corrupt row 或错误 RESOLVED Incident 放行。
- `safe_mode_recovery()` 仅在 durable protection、reconciliation、health 与 fresh core-data gate 均通过后，resolve blocking incident 并落到 `PAUSED`；随后 manual Resume 才可进入 `RUNNING`。
- 新增 4 个真实 PostgreSQL 回归：corrupt payload / payload identity mismatch 拒绝、可解析但 LONG protection relationship 非法拒绝、修复为有效 plan 后恢复到 `PAUSED` 并 resolve incident、错误手工 resolve Incident 后 Resume 仍拒绝直至有效保护和健康条件恢复。
- PENDING PRODUCT DECISION：V1 是否正式定义 `TradePlan.invalidation` 为 AI/human-readable advisory text，而 `stop_loss` 为唯一 machine-enforceable hard invalidation；本轮保持冻结现状，未开发自然语言 invalidation parser。

### Post-Review Fix #4

- OPEN LONG durable protection 不再要求 `stop_loss < average_cost < take_profit`；利润锁定止损（例如 cost=100、stop=110、TP=140）在 Fresh bid=120 时是有效保护。
- 保持 fail-closed：ACTIVE row 必须唯一、payload 可解析且身份一致、TTL 有效、entry zone 合法、SL/TP 有限且 `stop_loss < take_profit`。
- 新增 PostgreSQL 回归覆盖利润锁定止损的 Safe Mode Recovery → `PAUSED`、随后 manual Resume → `RUNNING`，以及 `stop_loss >= take_profit` 仍拒绝；corrupt payload、identity mismatch、expired、duplicate ACTIVE 行为不变。
- 本次验证：G4 `45 passed`、G3 `10 passed`、全量 `72 passed, 1 warning`；Ruff、compileall、`git diff --check`、Alembic current/heads 与 paper-only Restart Smoke 均通过。

## Group 5-0 Result

- G5-0（Repository Context + Context Isolation Protocol）已完成。
- 落地 `AI_CONTEXT.md`（上下文入口 / Context Index）；`AGENTS.md` 为工程工作纪律与 Context Isolation Protocol（CIP-01～CIP-10）的正式入口。
- Accepted Main SHA = `c366d078e86d2ee5637c81a88cc7773686646556`（当前 main HEAD）；G4 implementation acceptance basis = `534dfad0f072553f18b8b687c20a48bf9914ee14`（G4 源码）。
- 无业务代码 / schema / API / UI / Runtime 修改；未实现 Replay / ReplayClock Engine。
- 状态：`G5-0 ACCEPTED`；G5 feature implementation 尚未开始（NOT STARTED）。

## Acceptance Record

- Group 1 = `ACCEPTED`；Group 2 = `ACCEPTED`；Group 3 = `ACCEPTED`；Group 4 = `ACCEPTED`。
- G3 Post-Acceptance Fix = `ACCEPTED`。
- FG-A — G3 Execution Authority & Freshness = `ACCEPTED / COMPLETE`（implementation
  `a9c2cd64bea0c6cc43b1ef8ad890e4db5353b801`；C04
  `d574e242f3aa7c26658ed6cc780fd8f744dbf503`；isolated Final Gate PASS）。
- C04 — Alembic Replay Test Isolation Fix = `ACCEPTED / COMPLETE`。
- Group 5-0 = `ACCEPTED`（G5 feature implementation NOT STARTED）。
- Group 5-3 = `ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Implementation Acceptance Basis = `f4c07333600f605cbcc5e34b591659feb1b1f318`；Review Fix #1 = VERIFIED）。
- G5-4 = `ACCEPTED`（Formal Acceptance Closeout 2026-09-06；Production Implementation Basis = `8678b2927a2d029ac0767e49acc9e0732c329bfa`；Self Review Fix #1 Evidence = `fe610c1f23457ff11f2d5c8654e9de0aec4ff289`）。
- G5 overall = `ACCEPTED / COMPLETE`。
- FG-E / N02 = `ACCEPTED / COMPLETE`（Human Acceptance confirmed；accepted implementation
  `2d5f3dde430c56cfbd4516bfdfdff8c513a07cff`；N02-1～N02-14 evidence PASS；Final Acceptance
  Closeout 已将 accepted lineage fast-forward 至 `main`）。
- N01-6｜15-minute Short Runtime Smoke = `ACCEPTED / COMPLETE`（2026-09-12；Independent Review =
  `PASS`；post-review docs-only Incremental Re-Review `db3a0dc..3f591a7` = `PASS`；Human
  Acceptance = `CONFIRMED`；Reviewed HEAD = `3f591a7694bf9e03dda53708a92c048dcea75fb3`；
  accepted lineage 仅 fast-forward：`ab4bf29 → db3a0dc → 3f591a7 → Final Closeout Commit`）。
  Closeout 期间 `Production code changed = NO` / `Tests changed = NO` / `Harness changed = NO` /
  `Migration changed = NO`。**不得**由本验收推断 2h soak / 12h soak / Continuous Runtime 全量验收 /
  7×24 Runtime / Integrated Runtime Host。
- SE-02B｜Opportunity Capture + Attribution = `ACCEPTED / COMPLETE`（2026-09-12；Independent Review =
  `PASS`；Human Acceptance = `CONFIRMED`；Human-Accepted reviewed tip = `6ce0c92…`；accepted lineage
  仅 fast-forward：`af81414 → f261766 → 7e86757 → b8a5fe3 → 0b8a275 → 6ce0c92 → Final Closeout
  Commit`）。Closeout 期间 `Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Contract changed = NO`。**不得**由本验收推断 SE-02C / SE-02D /
  Forward Outcome Calculator / MFE-MAE / expectancy / Real AI Edge / Live / N01-7 / N01-8 /
  Integrated Runtime Host。
- N01-7-F01｜Durable Protection Snapshot（N01-7 前置 Fix）= `ACCEPTED / COMPLETE`（2026-09-13；
  Human Acceptance = `CONFIRMED`（人工原文「确认 N01-7-F01 Human Acceptance，并执行 Final Main
  Integration」）；Final Independent Review = `PASS`；R2 Independent Re-Review = `PASS`；
  Integration Review = `PASS`；Reviewed candidate = `7c0ea7d…`；integration merge = `ddf39f2…`
  （true merge：`1579707` × `c0ce0af`，`Reviewed Source Preserved = YES`）；accepted lineage 仅
  fast-forward：`ddf39f2 → 7c0ea7d → Final Acceptance Closeout Commit`）。Closeout 期间
  `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO`；
  E1 = `FOREIGN WRITER CONFIRMED`（原始 shared-primary 指纹门 `INVALIDATED BY ENVIRONMENT /
  NON-BLOCKING`）。**不得**由本验收推断 N01-7 2h soak / N01-8 / Integrated Runtime Host /
  Continuous Runtime / 7×24 / Real AI Edge / Live；本验收不构成 `N01 overall` Acceptance
  （`N01 overall` 其后已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`）。
- N01-7 / N01-7-R01｜2-hour Medium Runtime Soak（含 Witness B Fix + Latest-Main Revalidation）
  = `ACCEPTED / COMPLETE`（2026-09-14；Human Acceptance = `CONFIRMED`；Independent Re-Review =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed
  candidate = `559f14be1fb89df58c11dfbea737eba4ac30421e`；branch
  `n01-7-r01-witness-b-latest-main`；Accepted Main before = `8a29306…`；accepted lineage 仅
  fast-forward：`8a29306 → 559f14b → docs/state-only Final Closeout Commit`，无 merge commit /
  squash / rebase / cherry-pick / force push）。Closeout 期间四项不变：`Production code
  changed = NO` / `Tests changed = NO` / `Migration changed = NO` / `Runtime config
  changed = NO`；`alembic heads` 单 head `20260913_0009`。
  🚩 P2 保留项（必须在 `N01-8` 继续观察）：`N01-7-R01-RR-P2-01` Memory Operational Watch /
  Bounded Retention Growth（slope `≈16.02 MiB/h` > `5.0`，`total_growth ≈14.043 MiB ≤ 64` ⇒
  `finding = false`，Acceptance Gate = PASS）。**不得**写 `memory resolved` / `memory is
  fine` / `no memory concern`。**不得**由本验收推断 `N01 overall` Acceptance、`N01-8` /
  Integrated Runtime Host / Continuous Runtime / 7×24 / Real AI Edge / Live 的任何进度。
- N01-8｜12-hour Extended Runtime Soak = `ACCEPTED / COMPLETE`（2026-09-14；Human Acceptance =
  `CONFIRMED`；Independent Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted reviewed candidate =
  `d9306ada663a5cacb86bee26218e298169d82e6b`（branch `n01-8-12h-extended-soak`）；Frozen Task
  Base = `dd78a979…`；Closeout Base = `e0a5d2a2…`；accepted lineage 仅 fast-forward：
  `e0a5d2a2 → docs/state-only Final Acceptance Closeout Commit`，单 parent，无 merge commit /
  squash / rebase / cherry-pick / force push）。正式 Run：`total_active 44401.217470 s`、
  99/99 aggregate checks True、`failures = []`、4/4 phase complete、3 fresh-process restart、
  12 controlled reconnect、6 受控 STALE→FRESH、24/24 reconciliation checkpoint；Power Loss =
  `RUN COMPLETED BEFORE POWER LOSS`（invalidation = `NO`）；Baseline Drift = `NO MATERIAL
  IMPACT`；Targeted Revalidation = `NOT REQUIRED`；Full Rerun = `NOT REQUIRED`。
  Closeout 五项不变：`Production code changed = NO` / `Migration changed = NO` /
  `Tests changed = NO` / `Frontend changed = NO` / `Runtime config changed = NO`；
  `alembic heads` 单 head `20260913_0009`；`DECISIONS.md changed = NO`（无新增产品 / 架构决策）。
  🚩 P2 `N01-7-R01-RR-P2-01` = `REMAINS`（NON-BLOCKING；冻结 AND 门 Formal Finding = `false`，
  但 operational watch 未闭合；**不得**写 `memory resolved` / `memory is fine` /
  `no memory concern`）。P3 `N01-8-IR-P3-01` / `P3-02` / `P3-03` = `NON-BLOCKING`（**未**升级）。
  **不得**由本验收推断 `Integrated Runtime Host` / Continuous Runtime / 7×24 / `SE-02D` /
  Real AI Edge / Live 的任何进度（本验收不构成 `N01 overall` Acceptance）；`N01 overall` 已于
  2026-09-14 经 N01 Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；
  `Integrated Runtime Host` = `NOT STARTED`。
- SE-ARCH-FIX-01｜Stable Evidence Anchor = `ACCEPTED / COMPLETE`（2026-09-13；Human Acceptance =
  `APPROVED`（日期 2026-09-13）；Second Independent Re-Review = `PASS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted reviewed candidate = `1e2738b09a4e4a62d91cfa8a6ffd6fcec3c71a21`；
  Accepted Main before = `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`；accepted lineage 仅
  fast-forward：`51053757 → bdb1af2 → 513689a → 5ba78af → 1e2738b → Human Acceptance
  → Final Closeout Commit`，`513689a` 的 integration merge lineage 未被重写）。
  Closeout 期间 `Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`；`alembic heads` 单 head
  `20260913_0008`；accepted N01-7 `20260912_0006` 未改写。P2 保留项 `TEST-ISO-01` /
  `RRF-03` / `RRF-04` = `NON-BLOCKING`（RRF-03 `DEFERRED`）。**不得**由本验收推断
  `SE-ARCH-FIX-02` / `SE-02C` / `SE-02D` / Forward Outcome Calculator / MFE-MAE /
  expectancy / Real AI Edge / Live / N01-7 / N01-8 / Integrated Runtime Host 的任何进度；
  `SE-ARCH-FIX-02 = NOT STARTED`、`SE-02C = BLOCKED / NOT STARTED`（SE-ARCH-FIX-01 收尾时；
  二者其后均已经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）。
- SE-ARCH-FIX-02｜Outcome Revision Chain Scope = `ACCEPTED / COMPLETE`（2026-09-13；Human
  Acceptance = `APPROVED`；Independent Review = `PASS — READY FOR HUMAN ACCEPTANCE`；
  Human-Accepted reviewed candidate = `15da7c1bac719d17271c7df9fcccbf80535b6d1b`；
  Implementation Commit = `4c835828f482875d1d7ce934f8808d3953a9105b`；branch
  `se-arch-fix-02-outcome-revision-chain-scope`；Accepted Main before =
  `fc619242c99a794a2eb2b87ee02b8b72aa782f05`；accepted lineage 仅 fast-forward：
  `fc619242 → 4c835828 → 15da7c1 → docs-only closeout`）。Closeout 期间四项不变：
  `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO` /
  `Runtime config changed = NO`；`alembic heads` 单 head `20260913_0009`；
  `20260912_0006` / `20260913_0007` / `20260913_0008` 的 revision identity 未被重写。
  P2 保留项 `TEST-ISO-01` / `RRF-03` / `RRF-04` = `NON-BLOCKING`（`RRF-03` `DEFERRED`）。
  ⚠️ 本验收**不**构成 `SE-02C` / `SE-02D` / Forward Outcome Calculator / MFE-MAE /
  expectancy / Real AI Edge / Live / N01-7 / N01-8 / Integrated Runtime Host 的任何进度；
  `SE-02C = BLOCKED / NOT STARTED`（SE-ARCH-FIX-02 收尾时；FIX-02 Accepted **不**使其
  MAY START，仍需 Pre-SE-02C Re-Gate。其后 SE-02C 已于 2026-09-14 经 Human Acceptance 转为
  `ACCEPTED / COMPLETE`，见下条）。
- SE-02C｜Forward Outcome Calculator = `ACCEPTED / COMPLETE`（2026-09-14；Human Acceptance =
  `CONFIRMED`；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN
  ACCEPTANCE`；Human-Accepted reviewed candidate =
  `7bb3835d6b14a3fc86becff1881c7f53f1acd567`（branch `se-02c-fix-02-stable-read-snapshot`）；
  `SE-02C-FIX-01` = `ACCEPTED / CLOSED`（candidate `2f9868278ab1652c4e338ffb01337c6e736545d9`）、
  `SE-02C-FIX-02` = `ACCEPTED / CLOSED`（implementation
  `6b084595cde9c3e3257046b4694b134954923a4d`）；Accepted Main before = `dd78a979…`；accepted
  lineage 仅 fast-forward：`dd78a979 → 51891c7`（true merge）× `be3aa6c`
  `→ 7ab1d42 → 2f98682 → 6b08459 → 7bb3835 → docs/state-only Acceptance Closeout Commit`，
  无 merge commit 到 `main` / squash / rebase / cherry-pick / force push）。Closeout 四项不变：
  `Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO` /
  `Runtime config changed = NO`；`alembic heads` 单 head `20260913_0009`。
  `C-01..C-29 = ALL PASS`、`F02-01..F02-24 = ALL PASS`（source = Independent Re-Review，
  **非**本 Closeout 重跑）。遗留 `SE02C-R7` = `P3 / NON-BLOCKING / NOT FIXED`（Human Accepted
  non-blocking finding；**未**修改 `edge/forward_service.py` 注释）。
  ⚠️ 本验收**不**构成 `SE-02D` / Family Aggregation / Expectancy / Real AI Edge / Live /
  N01-8 / Integrated Runtime Host 的任何进度；`SE-02D = NOT STARTED`（SE-02C 收尾时；其后
  `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）。

## Group 5-1 Result

- G5-1（Deterministic Replay Foundation）实现：已验证 ordered normalized input，以 `received_time` 推进 `ReplayClock`，并复用既有 G2 Rolling → Scanner → Lifecycle → State Machine → Strategy → EventRuntime 链路。
- 每次 replay 使用全新的 `InMemoryG2Repository`；未修改 PostgreSQL schema，未向 PostgreSQL G2 tables 写入 replay 数据。
- `OpportunityScanner`、`ScannerPipeline` 与 `StrategyEngine` 允许注入 Clock，默认仍使用 `SystemClock`；Replay business timestamps 使用同一个 `ReplayClock`。
- 新增 G5-1 定向测试，覆盖 received-time clock、稳定同时间顺序、回退 fail-fast、三种 Normalized event、双跑 canonical trace、历史 timestamp、真实 G2 非空链路与 processing timeline 变化。
- 验证：G5-1 `9 passed`；G1/G2 `15 passed`；G3 `10 passed`；G4 `45 passed`；full backend `81 passed, 1 warning`；Ruff、compileall、`git diff --check` 通过。
- 状态：`G5-1 IMPLEMENTED / WAITING REVIEW`（未自行 Acceptance，未 merge `main`）。

## Group 5-2 Result

- G5-2（Trading Replay Integration）实现：独立 PostgreSQL Replay workspace、`RunMode.REPLAY`、`ReplayWorkspaceGuard`、`ReplayMarketState` 与 Recorded G3/G4 provider；复用 Postgres G2、G3 Decision/Plan/Paper Execution、G4 Risk Gate/Safety/Protection/Re-evaluation。
- Replay Workspace Guard 真实比较 primary/replay `current_database()`、验证 `alembic_version=20260905_0004`，并对关键 G2/G3/G4 business tables 的残留数据 fail closed；runner 在前后比较 primary row counts。
- Replay business timestamps 通过 `ReplayClock` 注入 G3 Snapshot/Decision/Plan/Execution 与既有 G4 path；G4 默认随机 review snapshot ID 保持不变，Replay path 单独注入稳定 ID factory 以严格匹配 recorded review。
- 定向真实 PostgreSQL 集成覆盖 primary identity/dirty workspace 拒绝、未来 BBO 不可见、G3 缺失 record fail-closed、真实 Kline G2 SETUP 完成后才进入 G3、已有 Position 的 BookTicker G2→G4 且不触发 G3、最近 20 条 Timeline 的截断/正序、真实 G2 SETUP→G3→Risk→BUY Fill→G4 HOLD→SL protective SELL→closed Trade/Ledger、G2/G3/G4 历史业务时间及 outbound HTTP construction guard。
- 验证：G5-2 `7 passed`；full backend `88 passed, 1 warning`；Ruff、compileall、`git diff --check` 通过；Alembic current/heads=`20260905_0004 (head)`。
- Schema migration：未新增；Live、OKX、真实 AI、Performance Analytics、G5-3：未实现/未调用。
- 状态：`G5-2 ACCEPTED`（人工 Acceptance 正式确认；Implementation Acceptance Basis = `2a7d0c858c70f21215a090ee3b583d341cfd84b4`）。
- Acceptance Closeout（2026-09-06）：Reviewer Result = `ACCEPTED`；Review Fix #1 = `VERIFIED`。详见 `dev_log/2026-09-06-group5-2.md`「Formal Acceptance Record」。
- 当前 Accepted Baseline：以 Git `main` / `origin/main` 为准（CIP-02 preflight 实时读取），不以本文静态 SHA 为准。

### Group 4 Acceptance

- Acceptance Result = `PASS WITH NON-BLOCKING NOTES`。
- G4 implementation acceptance basis = `534dfad0f072553f18b8b687c20a48bf9914ee14`。
- Position Safety + Recovery 已正式 `ACCEPTED`。
- Real AI Provider = `DEFERRED / NOT VERIFIED`（原因：`OPENAI_API_KEY` 缺失，无 `.env`；测试用 deterministic Fake Provider）。此项 non-blocking。
- Current next state = `G5 initialized / G5-0 complete`（G5 feature implementation not started）。

## Group 5-3 Result

- G5-3（End-to-End Determinism）实现：新增 `g5/canonical.py`（22 表 canonical durable workspace snapshot + SHA-256 digest + 诊断 diff）、`ReplayTradingResult.workspace_digest` 增补；三独立 PostgreSQL workspace（Run A/B/C）证明 `snapshot(A)==snapshot(B)`、`Digest(A)==Digest(B)`、`Digest(A)!=Digest(C)`（C 变异 protective-stop bid 89→88），经济差异定位到 `fills.fee` 与 SELL fill price。
- 本批同时按 Reviewer 授权对已验收 G4 做最小确定性修正：SignalTimeline `event_time DESC, timeline_id DESC LIMIT 20`（reversed 后 `event_time ASC, timeline_id ASC`）、OPEN orders `created_at ASC, order_id ASC`；并修正 G5-2 fixture t6 review 触发器为 `state_version_changed`、加固 recorded G4 HOLD 消费断言。
- 验证：G5-3 `3 passed`、G5-2 `7 passed`、G4 `46 passed`、full backend `92 passed, 2 warnings`；Ruff / compileall / `git diff --check` 通过；Alembic primary 与 disposable replay `current`/`heads` = `20260905_0004`；PYTHONHASHSEED 0/12345 跨进程 digest 一致。
- 审计残留已关闭（Review Fix #1 = VERIFIED）：
  - Review Fix #1 已解决三处 Replay-reachable OPEN BUY cancellation ordering（`g4/protection.py`、`g4/reevaluation.py`、`g4/planning.py`）；
  - 三处均使用 `ORDER BY created_at ASC, order_id ASC`；
  - canonical representation collision（typed value→string 折叠）已以无歧义类型标记编码解决；
  - 无 remaining G5-3 determinism blocker。
- Schema migration：未新增；Live、OKX、真实 AI、Performance Analytics、G5-4：未实现/未调用。
- 状态：`G5-3 ACCEPTED`（2026-09-06 Formal Acceptance Closeout；Implementation Acceptance Basis = `f4c07333600f605cbcc5e34b591659feb1b1f318`；Review Fix #1 = VERIFIED）。详见 `dev_log/2026-09-06-group5-3.md`「Formal Acceptance Record」。

### G5-3 Review Fix #1（Reviewer = CORRECTION REQUIRED）

- P0-1：三处 Replay 可达取消 OPEN BUY 路径补 `ORDER BY created_at ASC, order_id ASC`（`g4/protection.py::_cancel_risk_increasing`、`g4/reevaluation.py::_cancel_adds`、`g4/planning.py::cancel_stale_risk_increasing`），仅确定性排序，不改取消资格/订单语义/reservation 释放/G4 业务规则/Risk。新增 3 个 PostgreSQL 回归验证持久化 `PositionEventRecord.payload["cancelled_order_ids"]` 稳定排序。
- P0-2：`g5/canonical.py::canonicalize_value` 从「typed value 折叠 string」改为无歧义类型标记编码（`["null"]`/`["bool",v]`/`["int",v]`/`["str",v]`/`["float",hex]`/`["decimal",str]`/`["datetime",UTC ISO]`/`["enum",...]`/`["object",[[k,v]...]]`/`["array",[...]]`），`first_snapshot_difference` 感知 tagged 结构保持语义 path，主键列值保持原始可哈希标量。新增碰撞回归（float vs 相同 hex 文本、Decimal vs 相同串、datetime vs 相同 ISO 文本、`["float",...]` vs 真实 float、shape-like-marker object vs 真实值）。无 schema 变更。
- 验证：G5-3 `5 passed`、G4 `49 passed`、G5-2 `7 passed`、全量 `97 passed, 2 warnings`；Ruff/compileall/`git diff --check` 通过；Alembic primary=`20260905_0004 (head)`；DigestA=`487c96806b7666ab565f26f2796a42ec689d82eec36b68e799d090dea18b4694`、DigestC=`171c2ff9dafe836744997ab4f5f621c1f4d09c5c2c9c7e18e16a772a2f13ab97`（A==B、A!=C）；recorded G4 HOLD 真实消费（`model=replay-recorded-g4`、`error=None`）；PYTHONHASHSEED 0/12345 跨进程 digest 一致。
- 状态：Review Fix #1 = `VERIFIED`；G5-3 已随 2026-09-06 Formal Acceptance Closeout 整体 `ACCEPTED`（见上）。

## Group 5-4 Result

- G5-4（Deterministic Replay Evaluation）实现：新增 `g5/evaluation.py`（`ReplayEvaluationReport`、
  `ReplayEvaluationError`、`evaluate_replay_workspace(...)`）；`ReplayTradingResult` additive 增补
  `evaluation` 字段；`ReplayTradingRunner.run()` 增补
  `capture workspace → workspace_digest → evaluate durable workspace → verify primary unchanged`。
- Evaluation 只从 Replay PostgreSQL durable facts 读取；所有 float 聚合为 primary-key 排序 +
  `math.fsum()`；读取事务为 `REPEATABLE READ, READ ONLY`；`evaluation_digest` 复用 G5-3
  `canonicalize_value()`，输入排除 `workspace_digest` 与自身。
- 会计语义：`account_realized_pnl`（仅 SELL realized，已扣 SELL fee）、`total_fees`（BUY+SELL fill fee）、
  `ledger_cash_delta`（全部 ledger cash 变动）三项分别报告，未创建 `profit` / `net_profit` 合并字段；
  未修改 G3 settlement semantics。
- 验证：G5-4 `7 passed`；G5-3+G5-2+G5-1 `21 passed`；G1/G2+G3 `25 passed`；G4 `49 passed`；
  全量 `104 passed, 1 warning`；Ruff / compileall / `git diff --check` 通过；
  Alembic primary `current`/`heads` = `20260905_0004 (head)`。
- Determinism：三独立 PostgreSQL workspace A(89)/B(89)/C(88) 证明
  `Evaluation(A)==Evaluation(B)`、`EvaluationDigest(A)==EvaluationDigest(B)`、
  `WorkspaceDigest(A)==WorkspaceDigest(B)`、`EvaluationDigest(A)!=EvaluationDigest(C)`；
  workspace digest 与 G5-3 文档值一致（说明未改变 G5-3 行为）。
- 经济敏感性（A/C）：`sell_filled_notional`、`total_fees`、`ledger_cash_delta`、
  `account_realized_pnl`、`final_cash_balance` 五项均真实变化；A/B/C 生命周期仍合法
  （`closed_trade_count=1`、`open_trade_count=0`、`exit_reason=(('STOP_LOSS', 1),)`）。
- Fail-closed 证据：test-local 篡改 fill fee → `ReplayEvaluationError`
  （`accounting inconsistency: fill fees do not match ledger fees`）。
- Open-position 证据：protective exit 前结束的独立场景 `open_position_count=1`、
  `open_quantity=9.995002498750624`、`open_trade_count=1`、`closed_trade_count=0`、`is_flat=False`。
- 隔离证据：primary counts 前后一致；outbound HTTP client 构造 `0`；Real AI / OKX 调用 `0`。
- Schema migration：未新增；`replay_run_id` / `backtest_id`：未引入；Evaluation Report：未持久化。
- 状态：`G5-4 ACCEPTED`（2026-09-06 Formal Acceptance Closeout；G5 overall = `ACCEPTED / COMPLETE`）。
  详见 `dev_log/2026-09-06-group5-4.md`。

## Product Requirements Baseline（PRB-01）

- 任务：PRB-01 — Establish Stable Product Requirements Baseline（Documentation / Governance Only）。
- 新建根目录 `PRODUCT_REQUIREMENTS.md`：长期产品需求基线（Product Goal / Trading Philosophy / Stable Product Boundaries / Core responsibility model / Long-term capability direction）。
- 同步入口：`AI_CONTEXT.md` 增加 `PRODUCT_REQUIREMENTS.md` 产品基线指针；`AGENTS.md` 开工检查加入 `PRODUCT_REQUIREMENTS.md`。
- 本任务 Scope：仅文档；不修改 Backend / Frontend / Tests / Schema / Migration / 交易行为 / Risk / Scanner / AI Provider / G2–G5 Runtime；不把未来能力写成当前已完成；不静默覆盖 `DECISIONS.md`。
- 状态：`ACCEPTED / COMPLETE`（Independent Re-Review = `PASS / READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED`；Acceptance Fix #1 = `CLOSED`）。
- 分支：`prb-01-product-requirements-baseline`（基于 `main` = `ac3eaf9…`）；Acceptance Fix #1 Commit = `28de04a5b86e84840fb79d0774957f8312b6144e`；Final Acceptance / Baseline Commit = 其后继 commit（SHA 见本任务 dev_log 与 Closeout Report）。
- Accepted Main before = `ac3eaf911b9841f353db53d4ae21e7336af90e37`；Accepted Main after = PRB Final Accepted Commit（`main` 已 fast-forward，仅 fast-forward）。
- Product behavior changed = `NO`；Repository baseline established = `YES`。

## SE-02A Result

- 任务：SE-02A｜Contracts + Additive Persistence（专项 SE｜Strategy & Trading Edge 的第一个
  Implementation Acceptance Batch）。
- **reviewed implementation source** = branch `se-02a-contracts-additive-persistence` @
  `0c206c9c598c735d8f708db6603c02fc4d5a3fa3`（Task Base / verified Accepted Main at authoring
  time = `e0dab188e55c32b7607c18a66644d25449dc2236`）。
- **historical integration candidate**（仅作 evidence / 对照，**不**作为本次 implementation source）
  = branch `se-02a-final-integration` @ `9998e1b`（建于旧 `main` `6cc4c36`）。
- **此次 refresh integration** = branch `se-02a-final-integration-refresh`，以最新 Accepted Main
  `b3ac21b` 为基，merge reviewed source `0c206c9`（保留正常 lineage；未 rebase / 未 squash /
  未 rewrite reviewed source）。
- 新增 `backend/src/marketpulse/edge/`（`hashing.py` / `identity.py` / `models.py` /
  `repository.py`）：Opportunity / Evidence Revision / Evidence Source & Status / Forward Horizon
  （仅 `30s` / `5m` / `15m` / `1h`）/ Outcome contract types / Attribution 的 domain contracts；
  identity 采用任务规定公式；canonical hashing 复用 G5 `canonicalize_value`，未引入第二套 serializer。
- 新增 4 张 additive Edge 表与 Alembic revision `20260911_0005`
  （`edge_opportunity_evidence` / `edge_bbo_observations` / `edge_forward_outcomes` /
  `edge_attribution_events`），含 Edge 专属 index 与约束（UNIQUE、复合 supersedes FK、
  frozen family / horizon / status CHECK）。
- 语义与 immutability：同 revision 同 hash 幂等；同 revision 不同 hash `EdgeEvidenceConflict`
  fail closed；`revision > 1` 必须 supersedes 恰为 `R-1` 的同 opportunity revision，跨机会 /
  悬空 / 跳号一律拒绝；`calculation_digest` 与 `outcome_record_hash` 分离，Replay 与 Forward Paper
  provenance 不同可共享同一 calculation digest。
- 边界：**未接 runtime capture**（`SE-02B` 未开始）、**未实现 forward outcome calculator**
  （`SE-02C` 未开始）、未实现 family aggregation / expectancy（`SE-02D`）；未修改 G2/G3/G4/G5
  既有表 semantics、Risk、Execution、State Machine、G3 accounting semantics。
- 唯一 G5 改动：`g5/replay.py` 的 `schema_head` 常量
  `20260905_0004 → 20260911_0005`（migration head 派生事实，本批新 revision 使其必然过期，
  属阻塞当前 AC 的最小修复；guard 行为未变）。
- Acceptance Fix #1（关闭 3 个 contract blocker）：参考报价改为**可选**
  （`reference_bid` / `reference_ask` / `reference_received_at` 可 NULL；`OK` 要求三字段
  非 NULL 且正/有序，`REFERENCE_MISSING` / `REFERENCE_STALE` 要求三者全 NULL 且禁止 0 占位；
  `ReferenceDataReason` 删除，状态收敛为三态）；forward outcome 恢复 Approved 终态
  `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID`（**无 `PENDING` 行**，`calculation_status` 必填）
  与 `ACTIVE` / `EXPIRED` lifecycle；BBO 强制 V1 因果规则 `available_at == received_at`，
  `observation_id` 纳入 `available_at`，同 identity 但 `data_quality` / `tradable` 冲突时
  `EdgeBboObservationConflict` fail closed。migration **就地修正 `20260911_0005`**（无 0006）。
- 历史验证（reviewed source 窗口，base `e0dab188`）：SE-02A contracts **`62 passed`**、
  SE-02A persistence **`26 passed`**（真实 disposable PostgreSQL）、定向 G5-2/G5-3 + G2
  **`62 passed`**、full backend **`259 passed`**（= baseline `171` + 本批 `88`）、
  migration `0004 → upgrade head(0005) → downgrade 0004 → upgrade head(0005)` PASS、
  无残留 disposable DB、primary `marketpulse` 仍为 `20260905_0004`（未被本批升级）。
- 本次 Latest-Main Integration Refresh 的验证结果与其逐条边界见
  `dev_log/2026-09-11-se-02a-edge-contracts-persistence.md` 末尾
  「Latest-Main Final Integration Refresh」章节（含 N01-A/B/C 在 `20260911_0005` integration
  tree 下共同成立的证据）。
- **Final Acceptance Closeout（2026-09-11/12，docs-only）**：Independent Review = `PASS`；
  Human Acceptance = `CONFIRMED`。在 reviewed refresh HEAD `134aec5` 之上创建 docs-only
  closeout commit（仅 `PROJECT_STATE.md` / `AI_CONTEXT.md` / SE-02A dev_log），随后
  **fast-forward only** 将 `main` 从 `b3ac21b` 收编 `2e7bf6a → 134aec5 → Final Closeout Commit`
  （无 rebase / squash / force / history rewrite）。Closeout 最小充分复验：SE-02A focused `88 passed`
  （62 + 26）、N01-C focused `6 passed`（规范解释器 `py -3.14`）、full backend `267 passed`
  （独占窗口）、`alembic heads` 单 head `20260911_0005` 且 `g5/replay.py::schema_head` 同值、
  Ruff `All checks passed!` / compileall rc=0 / `git diff --check`（工作树 + `b3ac21b..HEAD`）rc=0。
- **Accepted Main before** = `b3ac21b89e11490a0760f560bc099b9acf91ff48`；
  **Accepted Main after** = Final Closeout Commit（`main` 已 fast-forward，仅 fast-forward）。
- Closeout 阶段四项不变：`Production code changed = NO`、`Tests changed = NO`、
  `Migration changed = NO`、`Contract changed = NO`。
- 状态：`ACCEPTED / COMPLETE`（SE-02B / SE-02C / SE-02D / runtime capture / Real AI / Live
  仍未开始，不在本批 claim 边界内）。
- 备注（Repository Truth 差异）：仓库中不存在 SE-02 设计 / approved contract 文档，本批契约依据
  为任务书与既有仓库约定；本批自行确定的契约决策已在上述 dev_log §3 逐条列出。
- 备注（主库）：本地 `marketpulse` 主库仍在 `20260905_0004`，本批**未**对其执行 migration
  （避免未经授权修改外部系统状态）；如需与 head 一致，由 Operator 执行 `alembic upgrade head`。
- 备注（基线漂移，CIP-03，非本批所致）：本 branch 的 Task Base（Accepted Main）为 `b3ac21b`
  （N01-C 已验收收尾）；此前 SE-02A 作者期的 `e0dab188` / `6cc4c36` 均已为其祖先。

## SE-02B Result

- 任务：SE-02B｜Opportunity Capture + Attribution（专项 SE｜Strategy & Trading Edge 的第二个
  Implementation Acceptance Batch）。
- **Human-Accepted reviewed branch tip** = `6ce0c9214f552c0173e1f925315102506c3e9078`
  （branch `se-02b-opportunity-capture-attribution`）。
- **Task Base / Accepted Main before** = `af81414160248c97f59a63b31fe615ea8ae14bbe`；
  **Accepted Main after** = Final Closeout Commit（`main` 已 fast-forward，仅 fast-forward）。
- **Independent Review（final）** = `PASS`；**Human Acceptance** = `CONFIRMED`。
- 交付能力：
  ① **G2 SETUP Opportunity Capture** — qualifying `BREAKOUT_RETEST` Opportunity Evidence 与 durable
  G2 facts 在**同一 PostgreSQL 事务**内写入；atomic / fail-closed；immutable / append-only；
  遵循已验收 SE-02A identity + hash + revision 契约。
  ② **Attribution** — `Opportunity → AI → Plan → Risk → Execution → Economic Result` 全链
  append-only 归因；exact authority / reason；**显式 AI family selection**
  （`selected_strategy_ids` 必须显式包含 `BREAKOUT_RETEST`，不依赖 snapshot fallback）；
  deferred LIMIT 经 durable `ORDER_OPEN` 事实做 **per-order restart-safe** 归因。
- 主要变更：新增 `backend/src/marketpulse/edge/capture.py`（含 opt-in `EdgeCaptureContext`）与
  `backend/src/marketpulse/edge/attribution.py`；`edge/__init__.py` docstring；
  `backend/src/marketpulse/g2/repository.py` 与 `backend/src/marketpulse/g3/service.py`
  仅做**纯增量**接线（keyword-only 参数 + `None` 守卫，legacy 行为不变）；新增
  `backend/tests/test_se_02b_opportunity_capture.py`（15）与
  `backend/tests/test_se_02b_attribution.py`（31）。
- **无新 migration**：`backend/alembic/` 零改动，head 仍 `20260911_0005`；
  SE-02A 冻结契约文件 `edge/{models,identity,hashing,repository}.py` / `db/models.py` 零 diff。
- Acceptance blocker 闭合链：**SE-02B-FIX-01** 关闭 P0-2（`evidence_at` 因果锚点
  = `candidate.created_at`）、P0-3（显式 AI family selection）、P0-4（deferred LIMIT per-order
  restart-safe 归因）、P1（cross-fact consistency，5 项 + negative admission matrix）；
  P0-1 判 `CHANGES REQUIRED` ⇒ 由 **SE-02B-FIX-02** 终局闭合（`ReferenceDataStatus.OK` 现要求
  `data_quality == FRESH`；不可变 payload 拆为 `supplied_quote`（被拒报价原始输入逐字保留）
  + `accepted_reference`（仅 OK 非空）；payload version `se02b-runtime-capture-v2 → v3`）。
- 验证证据（历史门，均真实执行）：SE-02B `focused 46`（capture 15 + attribution 31）；
  SE-02A 契约 + 持久化 `88`；G2 / G3 / G4 `123`；full backend `313 passed, 1 warning`
  （独占写者窗口 + 进程/PG 会话双证据）；Ruff `All checks passed!` / compileall rc=0 /
  `git diff --check` rc=0；`alembic heads` 单 head `20260911_0005`。
- **Final Acceptance Closeout（2026-09-12，docs-only）**：在 reviewed HEAD `6ce0c92` 之上创建
  docs-only closeout commit（仅 `dev_log/2026-09-12-se-02b-final-acceptance-closeout.md` /
  `PROJECT_STATE.md` / `AI_CONTEXT.md`），随后 **fast-forward only** 收编 `main`
  （无 rebase / squash / cherry-pick / force / history rewrite）。Closeout 最小充分复验：
  `git diff 6ce0c92..HEAD` 仅含上述文档 / 状态文件；`git diff --check` rc=0；
  SE-02B 定向 smoke `46 passed`；`alembic heads` 单 head `20260911_0005`。
- Closeout 阶段四项不变：`Production code changed = NO`、`Tests changed = NO`、
  `Migration changed = NO`、`Contract changed = NO`。
- 边界：**SE-02C / SE-02D = `NOT STARTED`**（SE-02B 收尾时；其后 `SE-02C` 已于 2026-09-14、
  `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）；
  Forward Outcome Calculator / MFE-MAE / forward
  returns / family aggregation / expectancy / KEEP-DOWNWEIGHT-KILL / Real AI Edge / Live /
  N01-7 / N01-8 / Integrated Runtime Host 均不在本批 claim 边界内。
- 备注：本批次**未**对共享 primary PostgreSQL 库执行任何 migration / downgrade（保留其它窗口状态）。

## SE-ARCH-FIX-01 Result

- 任务：SE-ARCH-FIX-01A｜Human Acceptance + Main Integration Closeout（Human Acceptance
  Integration / Final Closeout；**非**新实现、**非**重新 Review）。
- **Human Acceptance** = `APPROVED`（2026-09-13）。
- **Second Independent Re-Review Verdict** = `PASS — READY FOR HUMAN ACCEPTANCE`：无 P0/P1；
  AC 全 PASS；Integration AC 全 PASS；RRF-01 PASS；RRF-02 PASS；full backend `363 passed`；
  Ruff PASS；compileall PASS；`git diff --check` PASS；`alembic heads` 单 head；
  accepted N01-7 migration `20260912_0006` preserved；Historical Replay 未获得 Forward issuer。
- **Human-Accepted reviewed candidate** = `1e2738b09a4e4a62d91cfa8a6ffd6fcec3c71a21`
  （branch `se-arch-fix-01-latest-main-integration`；远端同名 branch 未改写）。
- **Accepted Main before** = `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`；
  **Accepted Main after** = Final Closeout Commit（`main` 已 fast-forward，仅 fast-forward）。
- **完整 lineage（保留）**：

  `51053757 → bdb1af2 → 513689a → 5ba78af → 1e2738b → Human Acceptance（2026-09-13）
  → Final Closeout Commit`

  其中 `513689a` 为 true merge（`71abb07` × `bdb1af2`），其集成 lineage **未**被 rebase /
  squash / cherry-pick / 重写；`main` 的 `20260912_0006`（N01-7）未被改写。
- **集成方法** = `FAST-FORWARD ONLY`（未创建 merge commit 到 `main`、未 squash、未 rebase、
  未 cherry-pick reconstructed history、未 force push）。
- Closeout 为 docs-only：`Production code changed = NO` / `Tests changed = NO` /
  `Migration changed = NO` / `Runtime config changed = NO`。
- **P2 保留项（NON-BLOCKING）**：
  - `TEST-ISO-01` — Alembic test helper 的 `DATABASE_URL` routing 可复现性问题（记录，未修）。
  - `RRF-03` — Historical N01 migration gate head-pin drift（`DEFERRED`；accepted N01
    historical gate **未被修改**）。
  - `RRF-04` — Shared DB historical isolation evidence 仅为 revision + table inventory
    fingerprint，**不是** row-level proof（证据措辞边界保持）。
- **验收后状态（SE-ARCH-FIX-01 收尾时）**：`SE-02A = ACCEPTED`、`SE-02B = ACCEPTED`、
  `SE-ARCH-FIX-01 = ACCEPTED / COMPLETE`；`SE-ARCH-FIX-02` 当时为 `IMPLEMENTED /
  READY FOR INDEPENDENT REVIEW`，其后于 2026-09-13 经 Human Acceptance = `APPROVED` 转为
  `ACCEPTED / COMPLETE`（见「SE-ARCH-FIX-02 Result」）；`SE-02C = BLOCKED / NOT STARTED`；
  `SE-02D = NOT STARTED`。该段为 SE-ARCH-FIX-01 收尾时状态；`N01 overall` 其后已于
  2026-09-14 经 N01 Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`。
- 详见 `dev_log/2026-09-12-se-arch-fix-01-stable-evidence-anchor.md`
  「Human Acceptance + Final Main Integration Closeout｜2026-09-13」。

## SE-ARCH-FIX-02 Result

- 任务：SE-ARCH-FIX-02｜Outcome Revision Chain Scope（SE-02C 启动前第二个 Architecture
  Blocker；**非** SE-02C 实现）。
- Task Base / Accepted Main = `fc619242c99a794a2eb2b87ee02b8b72aa782f05`；branch
  `se-arch-fix-02-outcome-revision-chain-scope`；Implementation Commit =
  `4c835828f482875d1d7ce934f8808d3953a9105b`。
- 修复内容：outcome revision chain identity scope 冻结为
  `(opportunity_id, evidence_id, horizon)`。
  - Service：`append_forward_outcome()` predecessor 校验补齐 `evidence_id` 与 `horizon`，
    跨 scope 一律 `EdgeInvalidOutcomeSupersedes`。
  - DB：`fk_edge_outcome_supersedes` 扩为
    `(supersedes_outcome_id, opportunity_id, evidence_id, horizon)`，配合新
    `uq_edge_outcome_id_scope`；`uq_edge_outcome_id_opportunity` 被替换。
  - Migration：`20260913_0009_outcome_revision_scope`（fail-closed preflight；存量
    cross-scope 行 ⇒ `RuntimeError` + rollback，`alembic_version` 保持 `20260913_0008`；
    不自动改写 / 重编号 / 删除任何行）。
- 既有语义保持：`revision = 1` 无 supersedes；idempotency（同 scope + 同 revision + 同 hash
  ⇒ `IDEMPOTENT`）；conflict（同 logical revision + 不同 hash ⇒ `EdgeOutcomeConflict`）；
  adjacency（只能 supersede `revision - 1`，仍在 service 层，**未**引入 trigger）。
- 验证：FIX-02 focused `8 passed`；定向回归 `196 passed`；full backend `371 passed, 1 warning`；
  Ruff / compileall / `git diff --check` PASS；`alembic heads` 单 head `20260913_0009`；
  `ReplayTradingRunner.schema_head` = `20260913_0009`。
- 隔离：独立 disposable PostgreSQL（`postgres:16-alpine` @ `127.0.0.1:5437`）+ gitignored
  `.env`；共享 5432 只读指纹 `20260905_0004` / 24 表，**未**被本批升级；无 disposable 残留。
- 状态（Implementation 完成时）：`SE-ARCH-FIX-02 = IMPLEMENTED / READY FOR INDEPENDENT
  REVIEW`（当时未 Human Accept、未 merge `main`、未启动 SE-02C）。
- 边界：**SE-02C / SE-02D = `NOT STARTED`**（SE-ARCH-FIX-02 收尾时；其后 `SE-02C` 已于
  2026-09-14、`SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）；
  Forward Outcome Calculator / MFE-MAE / forward
  returns / family aggregation / expectancy / Real AI Edge / Live / N01-7 / N01-8 /
  Integrated Runtime Host 均不在本批 claim 边界内。`TEST-ISO-01` / `RRF-03` / `RRF-04`
  保持独立 P2，**未**顺手修改。
- 详见 `dev_log/2026-09-13-se-arch-fix-02-outcome-revision-chain-scope.md`。
- **Human Acceptance + Final Main Integration Closeout（2026-09-13，docs-only）**：
  Human Acceptance = `APPROVED`；Human-Accepted reviewed candidate =
  `15da7c1bac719d17271c7df9fcccbf80535b6d1b`（implementation `4c835828…`）；Accepted Main
  before = `fc619242c99a794a2eb2b87ee02b8b72aa782f05`；Accepted Main after = Final Closeout
  Commit。集成方法 = `FAST-FORWARD ONLY`（`fc619242 → 4c835828 → 15da7c1 → docs-only
  closeout`；无 merge commit 到 `main` / squash / rebase / cherry-pick / force push）。
  Closeout 轻量复验（不重跑 371 backend tests）：`git diff --check` PASS、docs consistency、
  ancestry check、remote `main` read-back、changed-path scope check（仅 docs/state）；
  `alembic heads` 单 head `20260913_0009`；`20260912_0006` / `20260913_0007` /
  `20260913_0008` / `20260913_0009` 全部保留、revision identity 未重写。
  四项不变：`Production code changed = NO` / `Tests changed = NO` / `Migration changed = NO` /
  `Runtime config changed = NO`。
  ⚠️ FIX-02 Accepted **≠** SE-02C MAY START：`SE-02C` 保持 `BLOCKED / NOT STARTED`，启动前
  必须另开独立获批的 Pre-SE-02C Re-Gate，且仅当返回 `PASS — SE-02C MAY START` 才允许启动。
- 最终状态：`SE-ARCH-FIX-02 = ACCEPTED / COMPLETE`。

## N01-7 / N01-7-R01 Result

- 任务：N01-7｜2-hour Medium Runtime Soak → N01-7-R01｜Witness B Fix + Latest-Main
  Revalidation + 2h Acceptance Re-run（**非**新实现；**非** production fix；**非** N01-8）。
- Human Acceptance = `CONFIRMED`；Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS —
  READY FOR HUMAN ACCEPTANCE`；**Human-Accepted reviewed candidate =
  `559f14be1fb89df58c11dfbea737eba4ac30421e`**（branch `n01-7-r01-witness-b-latest-main`，
  远端同 SHA、未被改写）。
- Accepted Main before = `8a29306d904223f03408fe55538ba6cb05222f15`；Accepted Main after =
  docs/state-only Final Acceptance Closeout Commit。
- 集成方法 = `FAST-FORWARD ONLY`：`8a29306 → 559f14b → docs-only closeout`；无 merge commit 到
  `main` / squash / rebase / cherry-pick / force push。
- 验收依据（单轮全新正式 Run）：真实 OKX 公共行情 + 一次性 disposable PostgreSQL 连续
  `total_active 7320.252 s`、**84/84 checks true**、`failures = []`；5 次受控重连、2 次受控
  STALE→FRESH、7 checkpoint 全 ok、跨进程 Recovery 15 步、Witness A/B/C 全成立、经济不变量
  全绿；`production_code_unchanged = true`；shared primary before == after；residue `0`；
  起止两次 `ls-remote` 相同 ⇒ run 期间 main drift = **NO**。
- R01（原 Witness B 未真实建立 `Plan A != Plan B`，**HARNESS DEFECT**）与 R02（latest-main
  baseline drift ⇒ targeted revalidation）均已关闭，且**未**发现 PRODUCT DEFECT。
- 遗留 P2：`N01-7-R01-RR-P2-01`（Memory Operational Watch / Bounded Retention Growth）——
  按冻结 AND contract（`growth > 64 MiB` **AND** `slope > 5 MiB/h`）本 Run `finding = false`
  ⇒ Acceptance Gate = PASS；但 slope 分支单支越线（`≈16.02 MiB/h`），**保留给 `N01-8`**；
  不得宣称内存已解决 / 无问题（禁写 `memory resolved` / `memory is fine` /
  `no memory concern`）。
- 环境遗留（**未授权清理，原样保留**）：隔离容器 `marketpulse-n01-7-r01-pg` @
  `127.0.0.1:5434` 与 worktree 内 gitignored `.env`（指向 5434）；释放命令
  `docker rm -f -v marketpulse-n01-7-r01-pg`。副作用：在该 worktree 内跑 pytest 会走 5434。
- ⚠️ `N01-7` / `N01-7-R01` Accepted **≠** `N01 overall` Accepted（N01-7 收尾时 `N01 overall`
  尚未验收；其后已于 2026-09-14 经 N01 Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`），也**≠** `N01-8` MAY START（N01-7 收尾时仍 `NOT STARTED`；其后
  N01-8 已另行获批执行并于 2026-09-14 经 Human Acceptance 转 `ACCEPTED / COMPLETE`，见
  「N01-8 Result」）；`Integrated Runtime Host` 仍 `NOT STARTED`。
- 详见 `dev_log/2026-09-14-n01-7-final-acceptance-closeout.md` 与
  `dev_log/2026-09-13-n01-7-r01-witness-b-revalidation.md`。
## N01-8 Result

- 任务：N01-8｜12-hour Extended Runtime Soak → `N01-8`｜Final Acceptance Closeout（Closeout /
  Integration Task；**非**新 Runtime Validation、**非**新 Independent Review、**非**新实现）。
- Human Acceptance = `CONFIRMED`（2026-09-14）；Independent Review Final Verdict =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；**Human-Accepted reviewed
  candidate = `d9306ada663a5cacb86bee26218e298169d82e6b`**（branch `n01-8-12h-extended-soak`，
  远端同 SHA、未被改写）。
- Frozen Task Base = `dd78a979d128dee385c7a8ddc2254a53366af714`（= candidate parent）；
  candidate **不是**当时 `main` 的 descendant（run 期间 `main` 已继续收编 SE-02C 与
  PRE-01A-D1）；Closeout Base = 任务 preflight 实测 remote `main` =
  `e0a5d2a2aa554415d0fe4e18b1f36be740dca3b7`。
- Accepted Main before = `e0a5d2a2…`；Accepted Main after = docs/state-only Final Acceptance
  Closeout Commit。集成方法 = `FAST-FORWARD ONLY`（单 parent；无 merge commit / squash /
  rebase / cherry-pick / force push）；**未**把 `main` 回退到 `dd78a979`，**未**用旧 candidate
  的 `PROJECT_STATE.md` / `AI_CONTEXT.md` 覆盖 latest-main（以 latest-main 版本为基础做最小
  状态同步），SE-02C / PRE-01A-D1 已接受状态完整保留。closeout branch =
  `n01-8-final-acceptance-closeout`，worktree =
  `E:\Documents\MarketPulse-AI-n01-8-final-closeout`。
- 验收依据（单轮全新正式 Run；真实 OKX 公共行情 + 一次性 disposable PostgreSQL + detached
  supervisor）：`total_active = 44401.217470 s`（≥ 43200）、4/4 phase complete（open → continue
  → continue → close）、3 次 fresh-process restart、12 次受控重连、6 次受控 STALE→FRESH、
  24/24 reconciliation checkpoint PASS、**99/99 aggregate checks True**、`failures = []`；
  `production_code_unchanged = true`；shared primary before == after；disposable residue `0`。
- Power Loss：`RUN COMPLETED BEFORE POWER LOSS`；Power-loss invalidation = `NO`。
- Baseline Drift（run 期间 `dd78a979 → b77c803`）classification = `NO MATERIAL IMPACT`
  （Independent Review 裁定）；Targeted Revalidation = `NOT REQUIRED`；Full Rerun = `NOT REQUIRED`。
- Carry-forward artifacts（integrated content 与 Human-Accepted candidate blob 一致）：
  `scripts/verify_n01_8_extended_soak.py`（blob `9e58c832`）、`scripts/n01_8_detach.py`
  （blob `7c5c9893`）、`scripts/n01_8_detach_probe.py`（blob `0d291a2e`）、
  `dev_log/2026-09-14-n01-8-extended-soak.md`（在 candidate 内容后追加 Final Acceptance
  Closeout 章节，不改写原始 Formal Evidence / 数值 / Verdict 历史）。
- Closeout 五项不变：`Production code changed = NO` / `Migration changed = NO` /
  `Tests changed = NO` / `Frontend changed = NO` / `Runtime config changed = NO`；
  `alembic heads` 单 head `20260913_0009`（未新增 / 未重写）；`DECISIONS.md changed = NO`
  （本 Acceptance 无新增产品 / 架构决策）。
- 🚩 P2 保留项 `N01-7-R01-RR-P2-01` = **`REMAINS`**（P2 / NON-BLOCKING / Memory Operational
  Watch / Bounded Retention Growth）：N01-8 冻结 AND contract（`growth > 64 MiB` **AND**
  second-half `slope > 5 MiB/h`）Formal Finding = `FALSE`（本 Run `RSS growth 77.711 MiB`、
  second-half slope `−0.639369 MiB/hour`）⇒ Formal Acceptance **不**被 Memory Finding 阻塞，
  但 operational watch **未**闭合。**禁止**写 `memory resolved` / `memory is fine` /
  `no memory concern`。
- P3 findings（保留、`NON-BLOCKING`、**未**升级 P1/P0）：`N01-8-IR-P3-01`
  （`companion_structures_bounded=false` 属 diagnostic；cleanup evidence 显示 bounded
  lifecycle）；`N01-8-IR-P3-02`（dev_log EOF whitespace hygiene；已由本次 closeout 追加章节后
  的格式自然消除，未改写 Human-Accepted candidate commit）；`N01-8-IR-P3-03`（无单独
  supervisor process exit-code artifact；由 phase exit 0、`FINISHED/PASS` 与完整
  raw/stdout/error evidence 补强）。
- ⚠️ `N01-8 = ACCEPTED / COMPLETE` **≠** `N01 overall` Accepted：本 Task（N01-8）**未**自动
  接受 `N01 overall`、**未**启动 Integrated Runtime Host、**未**启动 SE-02D。`N01 overall`
  其后已于 2026-09-14 经独立的 **N01 Overall Final Acceptance Closeout** 转
  `ACCEPTED / COMPLETE`（见「N01 Overall Result」），该结论**不**由此 N01-8 Task 推断。
  `Integrated Runtime Host = NOT STARTED`（不构成 Integrated Runtime Host implemented /
  7×24 formal application runtime / production daemon / Live enabled）。
- 环境遗留（**未授权清理，原样保留**）：容器 `marketpulse-n01-8-pg` @ `127.0.0.1:5440` 与
  worktree `E:\Documents\MarketPulse-AI-n01-8` 内 gitignored `.env`（指向 5440）；释放命令
  `docker rm -f -v marketpulse-n01-8-pg`。
- 详见 `dev_log/2026-09-14-n01-8-extended-soak.md`（§47 Final Acceptance Closeout）。

## N01 Overall Result

- 任务：`N01`｜Overall Final Acceptance Closeout（Closeout / Integration Task；**非**新 Runtime
  Validation、**非**新 Independent Review、**非**新实现、**非** N01-9）。
- Human Acceptance = `CONFIRMED`（2026-09-14）；Overall Independent Review Verdict =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`（P0 = `NONE`、P1 = `NONE`）。
- Closeout Base（= 任务 preflight 实测 remote `main`）=
  `3f51ac7388627f09a96aeb05419dcfb4492b69f8`（与任务书导航值一致 ⇒ **无** `BASELINE MOVED
  AFTER TASK DISPATCH`）；closeout branch = `n01-overall-final-acceptance-closeout`；worktree =
  `E:\Documents\MarketPulse-AI-n01-overall-final-closeout`（clean；会话 cwd 的 dirty 历史
  branch worktree **未**参与）。
- Accepted Gate Inventory（全部 `ACCEPTED / COMPLETE`，内容不变）：`N01-A`、`N01-B`、
  `N01-VAL-FIX-01`、`N01-VAL-FIX-02`、`N01-VAL-FIX-03`、`N01-C`、`N01-6`、`N01-7-F01`、
  `N01-7`、`N01-7-R01`、`N01-8`。
- Accepted Claim Boundary：`N01 overall` 仅证明在批准的 validation harness、真实 PostgreSQL、
  真实 OKX public market data 与 Paper boundary 下，冻结范围内已有的 deterministic runtime
  lifecycle / task-worker-queue lifecycle / PostgreSQL session lifecycle / reconnect /
  freshness / stale fail-closed / Paper economic safety / restart / durable recovery /
  reconciliation / no fabricated historical economics / exactly-once economic safety /
  durable Position protection authority / 15-minute runtime smoke / 2-hour medium soak /
  12-hour extended soak / 冻结 resource-memory acceptance checks 已完成并验收；**不得**扩大为
  其它产品能力。
- Explicitly NOT Proven / Out of Scope：`Integrated Runtime Host`、FastAPI integrated 7×24
  daemon、deployment、unattended production supervisor、Live Trading readiness、Real AI runtime
  activation、Trading Edge、`SE-02D`、SWAP runtime、长期盈利能力 —— 均**未**由本 Acceptance
  推进（N01 Overall 收尾时）：`Integrated Runtime Host = NOT STARTED`、`SE-02D = NOT STARTED`
  （其后 `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）、
  Real AI runtime activation = `NOT STARTED / NOT ACTIVATED`、`Live = NOT ENABLED`。
- 🚩 Memory P2 `N01-7-R01-RR-P2-01` = `REMAINS`（P2 / NON-BLOCKING / Memory Operational Watch /
  Bounded Retention Growth）：N01-8 冻结 AND contract（`growth > 64 MiB` **AND** second-half
  `slope > 5 MiB/h`）Formal Finding = `FALSE`（`RSS growth 77.711 MiB`、second-half slope
  `−0.639369 MiB/hour`）⇒ 不阻塞 N01 Overall Acceptance，但 operational watch **未**闭合；
  **禁止**写 `memory resolved` / `memory is fine` / `memory problem closed` /
  `no memory concern`。未来观察面 = `Integrated Runtime Host` + 更长无人值守 Paper 运行；
  **不得**因此创建 `N01-9`。
- P3 findings（保留、`NON-BLOCKING`、**未**修复 / 关闭 / 升级 / 重分类）：`N01-8-IR-P3-01`
  （`companion_structures_bounded=false` 属 diagnostic）、`N01-8-IR-P3-02`（candidate EOF
  whitespace hygiene，historical）、`N01-8-IR-P3-03`（无独立 supervisor exit-code artifact，
  evidence gap）、`SE02C-R7`（MVCC comment accuracy，Human-Accepted P3 / NON-BLOCKING /
  NOT FIXED）。
- Migration Head = `20260913_0009`（单 head，未新增 / 未重写 revision identity）。
- 集成方法 = `FAST-FORWARD ONLY`（Closeout Base `3f51ac73 → docs/state-only N01 Overall Final
  Acceptance Closeout Commit`；单 parent；无 merge commit / squash / rebase / cherry-pick /
  force push）；closeout branch 已推送远端并验证；`main` 以 fast-forward only 更新。
- 变更面（docs/state-only）：`Production code changed = NO` / `Migration changed = NO` /
  `Tests changed = NO` / `Frontend changed = NO` / `Runtime config changed = NO` /
  `PRODUCT_REQUIREMENTS.md changed = NO` / `DECISIONS.md changed = NO`。
- 最终状态：`N01 overall = ACCEPTED / COMPLETE`；`Human Acceptance = CONFIRMED`；
  `Overall Final Review = PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；
  `Integrated Runtime Host = NOT STARTED`；`N01-9 = NOT REQUIRED / NOT CREATED`。
- 详见 `dev_log/2026-09-14-n01-overall-final-acceptance-closeout.md`。
- 下一步：`Integrated Runtime Host`（**NOT STARTED**；须由总进度窗口另开独立获批的窗口与门，
  **不得**自动启动）。本窗口**未**启动 `Integrated Runtime Host` / `SE-02D` / Real AI
  implementation，**未**创建 `N01-9`，**未**删除 / 清理任何 historical evidence branch 或
  N01 raw evidence。

## SE-02C Result

- 任务：SE-02C｜Forward Outcome Calculator（Deterministic Forward Outcome Calculator；
  Implementation + Verification 窗口）。
- 前置授权：Pre-SE-02C Re-Gate = `PASS — SE-02C MAY START`（**外部任务书内容**，本仓库无副本；
  本窗口未自行签发该 gate）。
- Base / Branch / Worktree：base `8a29306`（Accepted Main，`origin/main` read-back 一致，无 drift）
  → branch `se-02c-forward-outcome-calculator` @ `7a68bf0`（implementation `721c488`、
  test coverage `7a68bf0`）；worktree `E:\Documents\MarketPulse-AI-se-02c`。
  **未** merge `main`、**未** push `main`。
- Scope（新增 2 + 最小修改 2 + 测试 2）：`edge/forward.py`（纯计算核心）、
  `edge/forward_service.py`（path recorder / durable due discovery / bounded evaluation API）、
  `edge/__init__.py`（包内清单）、`g2/runtime.py`（opt-in live-ingress hook）、
  `tests/test_se_02c_forward_outcome_calculator.py`（37 项）、
  `tests/test_se_02c_forward_outcome_service.py`（9 项）。
- 关键不变量：`due_at = evidence_at + horizon.duration`；reference 权威 = FIX-01 durable
  capture anchor BBO；endpoint = 合格观测总序最大值；5 s endpoint TTL；仅
  `COMPLETE` / `INSUFFICIENT_DATA` / `INVALID` 落库，PENDING 仅派生；不可计算指标一律 NULL；
  `created_at` 冻结为 `due_at`；成本为精确乘性模型；`calculation_digest` 排除 provenance、
  `outcome_record_hash` 包含 provenance；评估者永不写 revision > 1。
- `Migration changed = NO`：`alembic heads` 单 head `20260913_0009`（**未**新增迁移、未改 ORM）。
- 验证：SE-02C focused `47 passed`；SE-02A/SE-02B/G5 命名回归 `196 passed`；full backend
  `418 passed, 1 warning`（相对 FIX-02 的 371 基线 = +47 / 回归 0）；`ruff check` /
  `compileall` / `git diff --check` PASS；C-01 ～ C-29 全部 PASS。隔离 disposable PostgreSQL
  `postgres:16-alpine` @ `127.0.0.1:5438`；共享 5432 **未**被触碰。
- 状态（收尾于 SE-02C-FIX-01 窗口时）：`SE-02C = IMPLEMENTED / FIXED / NOT ACCEPTED`；
  第一次 Independent Review = `FAIL — FIX REQUIRED`（`SE02C-R1` / `R2` / `R3` = P1
  BLOCKING，`SE02C-R4` = P2 NON-BLOCKING）。
- 未决语义点 (a)「窗口内只有 anchor BBO 自身时 reason 为 `ENDPOINT_STALE`」已由
  SE-02C-FIX-01 按 Approved semantics 关闭为 `ENDPOINT_MISSING`（anchor 只作 reference
  authority，不得作 endpoint）；原未决语义点 (b)「已结算 scope 事实变化后强制重评估抛
  `EdgeOutcomeConflict`」已由 SE-02C-FIX-02 的冻结语义取代：normal evaluator 先取得 scope lock，
  锁后发现 revision-1 即直接 return existing，不重算、不冲突、不写 revision 2。
- 详见 `dev_log/2026-09-13-se-02c-forward-outcome-calculator.md`。
- **Human Acceptance + Final Main Integration Closeout（2026-09-14，docs/state-only）**：
  Human Acceptance = `CONFIRMED`（接受 `SE-02C` 与 `SE-02C-FIX-02`）；Independent Re-Review =
  `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`；Human-Accepted reviewed
  candidate = `7bb3835d6b14a3fc86becff1881c7f53f1acd567`（branch
  `se-02c-fix-02-stable-read-snapshot`，远端同 SHA 未被移动）；Accepted Main before =
  `dd78a979d128dee385c7a8ddc2254a53366af714`；Accepted Main after = docs/state-only Acceptance
  Closeout Commit。集成方法 = `FAST-FORWARD ONLY`；closeout 直接在已复审候选 tip `7bb3835` 上
  线性 +1 docs/state-only commit（**不**新建 merge commit 到 `main`、**不**改写 reviewed
  candidate branch）。closeout branch = `se-02c-final-acceptance-closeout`，worktree =
  `E:\Documents\MarketPulse-AI-se-02c-final`。
  - `SE02C-R1` ～ `R6` = `CLOSED / PASS`（`R1` / `R2` / `R3` / `R4` 由 SE-02C-FIX-01，
    `R5` / `R6` 由 SE-02C-FIX-02）。
  - `SE02C-R7` = `P3 / NON-BLOCKING / NOT FIXED`（Human Accepted；如需清理另开独立
    `P3 docs/comment cleanup task`；**未**修改
    `backend/src/marketpulse/edge/forward_service.py`）。
  - `C-01..C-29 = ALL PASS`、`F02-01..F02-24 = ALL PASS`（**source = Independent Re-Review
    evidence**，**非**本 Closeout 重跑；本窗口只做 docs/state + fast-forward）。
  - Closeout 轻量门：`git diff --check` rc=0、docs consistency、changed-path scope check
    （仅 `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md` + 本批 dev_log）、ancestry
    check、remote `main` / closeout branch / reviewed candidate 三方 read-back、
    `alembic heads` 单 head `20260913_0009`（只读，**未**修改 DB/schema）。**未**重跑
    425 backend tests（Human Acceptance 已基于独立完整 Review）。
  - 四项不变：`Production code changed = NO` / `Tests changed = NO` /
    `Migration changed = NO` / `Runtime config changed = NO`。
  - ⚠️ `SE-02C` Accepted **≠** `SE-02D` MAY START：`SE-02D = NOT STARTED`，须另开独立获批的
    窗口与门（该句为 SE-02C 收尾时；其后 `SE-02D-D01` 与 `SE-02D-I01` 已分别于 2026-09-15
    经 Human Acceptance 转为 `ACCEPTED / COMPLETE`，父 `SE-02D` = `IN PROGRESS`）；
    `N01-8` / Integrated Runtime Host 当时亦仍 `NOT STARTED`（SE-02C 收尾时；其后
    N01-8 已于 2026-09-14 经 Human Acceptance 转 `ACCEPTED / COMPLETE`，见「N01-8 Result」）。
  - 详见 `dev_log/2026-09-14-se-02c-final-acceptance-closeout.md`。

## SE-02C-FIX-01 Result

- 任务：SE-02C-FIX-01｜Review Blockers（修复 SE-02C 第一次 Independent Review 发现的
  Acceptance Blockers，并把已复审 SE-02C candidate 安全集成到最新 Accepted Main）——
  Implementation + Verification 窗口（**非** Review、**非** Human Acceptance）。
- 关闭的 Findings：`SE02C-R1`（>50,000 observations 被读取上限静默截断 ⇒ endpoint / MFE /
  MAE 不完整且可能误判 COMPLETE）、`SE02C-R2`（live ingress 无条件硬编码
  `tradable=True`）、`SE02C-R3`（旧候选未建立在最新 Accepted Main lineage 上）、
  `SE02C-R4`（anchor 被误当 endpoint ⇒ 应报 `ENDPOINT_MISSING`）。
- Latest Accepted Main = `dd78a979d128dee385c7a8ddc2254a53366af714`；Original Candidate =
  `be3aa6c817582f6161ea9903f7824200b7f5c843`（**immutable，未被改写**）；Fix Branch =
  `se-02c-fix-01-review-blockers`；Worktree = `E:\Documents\MarketPulse-AI-se-02c-fix-01`。
- Lineage：`dd78a979`（第一父系 = 最新 Accepted Main）× `be3aa6c`（第二父系 = 原已复审
  SE-02C 候选）经**真实 merge**（`git merge --no-ff`）集成，两条历史均保留；**无** rebase /
  squash / cherry-pick / force push。
- Integration Merge SHA = `51891c7d3f74429b2d6ef29d166a3f57617a57fe`（parents = `dd78a979` +
  `be3aa6c`）；Fix Implementation SHA = `7ab1d42ca248310f3857a4087d7ecfdfc14fa6ca`
  （parent = `51891c7`）。
- `Schema Changed = NO` / `Migration Added = NO`：`alembic heads` 单 head `20260913_0009`；
  `G5 schema_head = 20260913_0009`。
- 验证（真实 disposable PostgreSQL `127.0.0.1:5441`，`postgres:16-alpine` /
  `PostgreSQL 16.15`）：SE-02C focused `49 passed`、market_data `7`、SE-02A `102`、
  SE-02B `62`、G2 `30`、G5 `32`（指定回归合计 `282 passed` / `0 failed`）+
  full backend `421 passed` / `0 failed`；`ruff` `All checks passed!`、`compileall` rc 0、
  `git diff --check` rc 0。
- 状态（SE-02C-FIX-01 窗口时）：`SE-02C-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT
  RE-REVIEW`；`SE-02C = IMPLEMENTED / FIXED / NOT ACCEPTED`；`SE-02D = NOT STARTED`。
  其后 `SE-02C-FIX-01 = ACCEPTED / CLOSED`（2026-09-14 SE-02C-FINAL Human Acceptance +
  Final Acceptance Closeout）。
- 详见 `dev_log/2026-09-14-se-02c-fix-01-review-blockers.md`。

## SE-02C-FIX-02 Result

- 任务：SE-02C-FIX-02｜Stable Read Snapshot（Implementation + Verification；非 Review、非
  Human Acceptance）。关闭 `SE02C-R5`（P1 / BLOCKING：分页 SELECT 不共享稳定 snapshot）与
  `SE02C-R6`（P3 / NON-BLOCKING：pagination/endpoint order docstring 错误）。
- Latest Accepted Main = `dd78a979d128dee385c7a8ddc2254a53366af714`；Fix-01 Candidate =
  `2f9868278ab1652c4e338ffb01337c6e736545d9`（immutable）；Fix-02 branch =
  `se-02c-fix-02-stable-read-snapshot`；worktree =
  `E:\Documents\MarketPulse-AI-se-02c-fix-02`；Implementation SHA =
  `6b084595cde9c3e3257046b4694b134954923a4d`。
- normal evaluator 使用 deterministic same-scope PostgreSQL advisory xact lock；锁后复查
  revision-1。若不存在，reference + 全部 keyset pages 在同一个独立 `REPEATABLE READ READ
  ONLY` transaction 中读取；仍持 coordinator lock append/commit。等待者得锁后 return existing，
  不建立第二 snapshot。
- 真实 PostgreSQL `postgres:16-alpine` / `PostgreSQL 16.15` @ `127.0.0.1:5443`：cursor-after、
  cursor-before、fresh snapshot control、two-evaluator + concurrent ForwardPathRecorder 全部通过；
  B 实测等待 advisory lock，A/B same id/digest/hash，durable revision-1 row = 1，无 conflict。
- regression：SE-02C service `16 passed`（含真实 50,001）；SE-02A/B + pure calculator/revision
  `201 passed`；G2 + G5 `62 passed`；G4/N01-7 preservation `105 passed`；full backend
  `425 passed, 1 warning`；Ruff / compileall / diff-check PASS。
- `Schema Changed = NO` / `Migration Added = NO`；Alembic / G5 schema head 均为
  `20260913_0009`。
- 状态（SE-02C-FIX-02 窗口时）：`SE-02C-FIX-02 = IMPLEMENTED / READY FOR INDEPENDENT
  RE-REVIEW`；`SE-02C = IMPLEMENTED / FIXED / NOT ACCEPTED`；`SE-02D = NOT STARTED`。
  其后 `SE-02C-FIX-02 = ACCEPTED / CLOSED`、`SE-02C = ACCEPTED / COMPLETE`（2026-09-14
  SE-02C-FINAL Human Acceptance + Final Acceptance Closeout）。
- 详见 `dev_log/2026-09-14-se-02c-fix-02-stable-read-snapshot.md`。

## PRE-01A-D1 Result

- 任务：PRE-01A-D1｜Real AI V1 Trade Decision Experiment Contract → `PRE-01A-D1-FINAL`｜
  Acceptance Closeout & Main Integration（**非** Implementation、**非** New Design、
  **非** New Review、**非** Real AI activation、**非** Runtime Host design、**非** SE-02D）。
  本轮为 docs/state-only 收尾。
- Acceptance lineage：`PRE-01A Research → S1 Context Pack → DS1 External Evidence → FIX-01
  → S2 Final Research Verdict → D1 Candidate → Human Review FAIL / FIX REQUIRED → D1-R1
  → D1-R2 → FIX-01 → Independent Re-Review PASS → Human Acceptance CONFIRMED → Final
  Acceptance Closeout`。
- Human-Accepted reviewed candidate（**immutable、远端未移动**）=
  `e3fb721c678e2b3ca0af6fb4663f349c6a641159`（branch
  `design/pre-01a-d1-real-ai-v1-contract`）；其父系 = `f612f0afbc5b0e17135364335261345cfe0f6e19`
  （parent = `b77c80333b85d6e3f1095ac7da9b13e9bf08163a`）；lineage 为线性单 parent。
- 状态 = `PRE-01A-D1 = ACCEPTED / COMPLETE`（2026-09-14 Human Acceptance = `CONFIRMED`；
  Independent Re-Review = `PASS`；`D1-R1` / `D1-R2` = `CLOSED`）。
- Accepted Design artifact =
  `docs/design/PRE-01A/PRE-01A-D1-Real-AI-V1-Trade-Decision-Experiment-Contract.md`
  （Artifact status = `ACCEPTED DESIGN`）。
- 已接受语义（只列已 Human-Accepted 内容）：Real AI V1 placement = `C. Trade Decision` only；
  `AI = Advisory` / `Deterministic System = Authority`；WITHOUT-AI selection benchmark =
  `ALL_ELIGIBLE_LONG_SHADOW_V1`；V1 causal claim = Real AI Trade-Decision selection /
  participation edge only（`PARTICIPATE_LONG` vs `NO_LONG`）；one `decision_invocation_id`
  → exactly one collision-free logical durable final decision；Single Primary Provider /
  No automatic fallback / No model voting；Gate A = Provider Shadow Activation、Gate B =
  Paper Economic Activation、Gate C = Selection / Participation Edge Evidence；
  `SE-02C = REUSE`；`SE-02D = required before Gate C edge declaration`；
  `Runtime Host = separate future design / research boundary`。
- Closeout 后仍**不得**声称：Real AI implemented / Real AI activated / AI edge proven /
  SE-02D complete / Runtime Host complete / Live Trading enabled；Real AI runtime activation
  仍 `NOT STARTED / NOT ACTIVATED`；Real AI provider runtime evidence 仍 `NOT PRESENT`；
  `SE-02D` 与 `Integrated Runtime Host` 当时仍 `NOT STARTED`（PRE-01A-D1 收尾时；其后
  `SE-02D-I01` 已于 2026-09-15 经 Human Acceptance 转为 `ACCEPTED / COMPLETE`）；
  live Opportunity → G3 integrated
  handoff 仍 `NOT ACCEPTED / NOT ACTIVE`。
- 本收尾为 docs/state-only：`Production Code = ZERO CHANGE` / `Tests = ZERO CHANGE` /
  `Schema / Migration = ZERO CHANGE` / `Runtime Impact = ZERO`。
- 详见 `dev_log/2026-09-14-pre-01a-d1-real-ai-v1-experiment-contract.md`。

## PRE-01B-D1 Result

- 任务：`PRE-01B-D1`｜Integrated Runtime Host Formal Design →
  `PRE-01B-D1-CLOSE`｜Acceptance Closeout & Main Integration（docs/state-only、
  **非** Implementation、**非** New Design、**非** New Review、
  **非** Runtime validation、**非** Real AI activation、**非** `SE-02D`）。
- 状态 = `PRE-01B-D1 = ACCEPTED / COMPLETE`（2026-09-15 Human Acceptance = `CONFIRMED`）。
- Independent Review = `PASS WITH NON-BLOCKING FINDINGS`；P0 = `NONE`；P1 = `NONE`。
- Human-Accepted reviewed candidate（**immutable、远端未移动**）=
  `80cb2babe9f55b3a3b1dc2d3b7913a405607ac22`（branch
  `design/pre-01b-d1-runtime-host-contract`）；其 parent = `1e7eeb2a…`，
  lineage 为线性单 parent（仅 +1 docs commit）。
- Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`（Artifact status =
  `ACCEPTED / COMPLETE`）。
- 已接受架构语义（摘要；完整决策见 `DECISIONS.md`
  「PRE-01B-D1 V1」条目）：`RuntimeHost` = 唯一 production composition
  owner；FastAPI lifespan = lifecycle anchor（**不**是 process supervisor）；
  structured concurrency = AnyIO TaskGroup / CancelScope；TaskGroup ≠ 自动 restart
  supervisor；single process / one Uvicorn worker / reload off；PostgreSQL session advisory
  lock = duplicate-host defense-in-depth；Host 拥有 DB engine/session lifecycle 与
  disposal；latest market/BBO observation 可为 ephemeral、durable business/state-version
  authority 仍为已接受 durable state；recovery-only fresh-BBO warm-up 先于
  new-risk readiness；Protection path 与 Scanner / 未来 AI backpressure 隔离；
  G2→G3 live advisory handoff `DEFERRED`；periodic reconciliation = detector-only；
  OS/service process supervision 在 Host Core 之外。
- Implementation carry-ins（**必须**带入实现窗口；**不**表示设计
  有缺陷或未被接受）：`F-01` — `state_version_for` 实现必须显式
  绑定已接受的 durable state/version authority，`RuntimeHost` /
  `LiveMarketState` **不得** 自造并行 `state_version` authority；`F-02` —
  safety queue capacity `64` 仅为**初始可配置默认值**，
  Implementation Acceptance **必须**用 queue high-water / runtime evidence 验证 sizing，
  **不是**免证据的永久架构常量。`F-03..F-08` = P3 /
  NON-BLOCKING 历史 findings，**不**为其单独开 Fix batch。
- 本 Acceptance **仅**接受 Formal Design，**不**证明 / **不**授权：
  `Integrated Runtime Host Implementation`（仍 `NOT STARTED`）、runtime validation、
  Real AI activation、G2→G3 activation、`SE-02D`、Live Trading、profitability / edge。
- 本收尾为 docs/state-only：`Production Code = ZERO CHANGE` / `Tests = ZERO CHANGE` /
  `Schema / Migration = ZERO CHANGE` / `Config = ZERO CHANGE` / `Runtime Impact = ZERO`。
- 集成方法 = `FAST-FORWARD ONLY`；closeout branch =
  `pre-01b-d1-final-acceptance-closeout`。
- 详见 `dev_log/2026-09-15-pre-01b-d1-final-acceptance-closeout.md`。

## PRE-01B-I1 Result

- 任务：`PRE-01B-I1`｜Integrated Runtime Host Core V1 Implementation → `PRE-01B-I1-CLOSE`｜Human Acceptance Closeout & Latest-Main Reconciliation（content-level carry-forward、**非** 重新设计、**非** 第二份实现、**非** New Review、**非** Runtime validation、**非** Real AI activation、**非** `SE-02D`）。
- 状态 = `PRE-01B-I1 = ACCEPTED / COMPLETE`（2026-09-15 Human Acceptance = `CONFIRMED`）。Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent Re-Review = `PASS WITH NON-BLOCKING FINDINGS`；P0 = `NONE`；P1 = `NONE`。
- Human-Accepted reviewed candidate（**immutable、远端未移动**）= `68dd7e96cc8547433794b045fa99e1e9dc5b7892`（branch `pre-01b-i1-fix-01-runtime-host-lifecycle`）；lineage = `b66e17d… → 596b04e… → 68dd7e9…`，单 parent 线性。Original Candidate = `b66e17d34173156b3797b664dbe09625511a0a11`（branch `pre-01b-i1-runtime-host-core`）。
- Accepted Design pointer = `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`（`PRE-01B-D1 = ACCEPTED / COMPLETE`）。
- Latest-Main drift 裁定：review-time `main` = `f887981…`；current `main` = `0ae5b0b…`；drift = `SE-02D-I01` production + tests + docs/state（正交）。`git diff --name-only f887981 0ae5b0b` **未** 触碰任何 §7 PRE-01B 路径（仅 `edge/`、`AI_CONTEXT`/`DECISIONS`/`PROJECT_STATE`、`SE-02D` dev_log）；因此 `68dd7e9` 内容级搬运到 latest `main` 不覆盖任何 SE-02D 已接受内容。
- Content-level reconciliation：closeout branch = `pre-01b-i1-final-acceptance-reconciliation`（从 `0ae5b0b…` 建立）；`git checkout 68dd7e9 -- <9 个 §7 实现/测试/脚本路径 + 2 个历史 dev_log>` 逐字节搬运；blob 身份比对 `git rev-parse :0:<path>` 全部 == `68dd7e9`（11/11 MATCH）。
- Files carried forward（blob == 68dd7e9）：`backend/requirements.txt`、`backend/src/marketpulse/api/app.py`、`backend/src/marketpulse/config.py`、`backend/src/marketpulse/db/session.py`、`backend/src/marketpulse/g2/runtime.py`、`backend/src/marketpulse/runtime.py`、`backend/src/marketpulse/runtime_host.py`（新增）、`backend/tests/test_runtime_host.py`（新增）、`scripts/verify_pre_01b_runtime_host.py`（新增）、`dev_log/2026-09-15-pre-01b-i1-runtime-host-core.md`、`dev_log/2026-09-15-pre-01b-i1-fix-01-runtime-host-lifecycle.md`。
- Latest-Main SE-02D 状态保留：`SE-02D-I01 = ACCEPTED / COMPLETE`；`SE-02D` Production = `IN PROGRESS`；`N01 overall = ACCEPTED / COMPLETE`；Memory P2 `N01-7-R01-RR-P2-01 = REMAINS / NON-BLOCKING`；Real AI = `NOT ACTIVATED`；live G2→G3 = `NOT ACTIVE / NOT ACCEPTED`；Live Trading = `DISABLED / NOT AUTHORIZED`。
- Non-blocking findings（诚实保留，不膨胀为 blocker）：`P2-02`（历史 process-scope violation）= `REMAINS AS AUDIT FINDING`；`RR-P2-01`（Alembic URL 优先级 / `DATABASE_URL` 交互）= `NON-BLOCKING TEST-INFRASTRUCTURE DEBT`（本任务**不**修，未触碰 `backend/alembic/**`）。
- 验证状态（本执行环境）：`git diff --check` 干净；`ruff check backend/src backend/tests scripts` 通过；focused `test_runtime_host.py` 与 `test_se_02d_aggregation.py` 已运行；**full backend 回幒因本环境无隔离 PostgreSQL 实例（Docker 不可达）无法合规运行 ⇒ `NOT VERIFIED`**，`main` 集成按 §18 在 full backend 闸门前 STOP（closeout 分支已 push 供后续窗口接力）。
- 集成方法 = `FAST-FORWARD ONLY`（closeout commit 单 parent = `0ae5b0b…`；无 merge commit / squash / rebase / cherry-pick / force push）。
- 本 Acceptance **证明**：Integrated Runtime Host Core V1 implementation 已 **接受**。
- 本 Acceptance **不**证明 / **不**授权：Real AI activation、G2→G3 live handoff、`SE-02D` Production complete、Forward Outcome scheduler、OS/service / WinSW packaging、Live Trading、profitability / edge、Memory P2 `N01-7-R01-RR-P2-01` resolution。
- 详见 `dev_log/2026-09-15-pre-01b-i1-final-acceptance-reconciliation.md`。

## SE-02D-D01 Result

- 任务：`SE-02D-D01`｜Family Aggregation / Expectancy Contract → `SE-02D-D01-FINAL`｜Acceptance
  Closeout（首次尝试 = `BLOCKED — BASELINE MISMATCH`，零仓库改动）→
  `SE-02D-D01-FINAL-REC-01`｜Final Acceptance Closeout / 正交漂移和解（docs/state-only、
  **非** Implementation、**非** New Design、**非** New Review、**非** Gate C、**非** Live）。
- 状态 = `SE-02D-D01 = ACCEPTED / COMPLETE`（2026-09-15 Human Acceptance = `CONFIRMED` +
  Final Acceptance Closeout）；Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01
  Independent Re-Review = `PASS`；`D01-R1` / `D01-R2` = `CLOSED`；`D01-R3` =
  `CLARIFIED / NON-BLOCKING`。
- Human-Accepted candidate（**immutable、远端未移动**）=
  `245b068199b7e6f3d32bf67e3b00163e4804afdf`（branch
  `design/se-02d-d01-family-aggregation-expectancy`）；其 lineage = `1e7eeb2a → 1b2494c →
  245b068`，单 parent 线性。
- Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md`（Artifact status =
  `ACCEPTED DESIGN`；与 candidate 版差异仅 Acceptance-state / closeout metadata，实质契约语义
  未改）。
- 正交漂移和解：首次 `SE-02D-D01-FINAL` 在 preflight 命中 `BASELINE MISMATCH`（remote `main`
  由 `1e7eeb2a` 前进到 `9e0553f5`；drift = PRE-01B-D1 Formal Design + 其 Final Acceptance
  Closeout，docs/state-only，不含任何 D01 路径）⇒ 当次 **STOP、零仓库改动**。本轮经 Human 授权
  以 latest-main content-level carry-forward 和解：closeout branch =
  `se-02d-d01-final-acceptance-closeout`（从 `9e0553f5` 建立），`git checkout 245b068 -- <3 个
  exact approved paths>` 精确搬运 2 个 D01 dev_log（与 candidate 字节一致）+ design artifact
  （随后仅 Acceptance-state 收口）；状态文档以 `9e0553f5` 版为基础做最小同步。**`245b068`
  **不是**、也**不**被宣称成为 new `main` 的 ancestor —— 它只是 immutable Human-Accepted
  evidence identity。
- 集成方法 = `FAST-FORWARD ONLY`（closeout commit 单 parent = `9e0553f5…`；无 merge commit /
  squash / rebase / cherry-pick / force push；`main` 由 `9e0553f5` fast-forward 到 closeout
  commit）。
- 本收尾为 docs/state-only：`Production Code = ZERO CHANGE` / `Tests = ZERO CHANGE` /
  `Schema / Migration = ZERO CHANGE` / `Config = ZERO CHANGE` / `Runtime Impact = ZERO`；
  `alembic heads` 单 head 仍 `20260913_0009`（只读，**未**触碰 DB）。
- 边界：本 Acceptance **仅**接受设计契约本身，**不**构成 `SE-02D` production implementation /
  family aggregation 实现 / expectancy 实现 / Real AI activation / Gate C PASS / Live 授权；
  `SE-02D = NOT STARTED`（SE-02D-D01 收尾时；其后 `SE-02D-I01` 已于 2026-09-15 经 Human
  Acceptance 转为 `ACCEPTED / COMPLETE`，父状态 = `IN PROGRESS`）、
  `Integrated Runtime Host = NOT STARTED`、Real AI =
  `NOT ACTIVATED`、Live Trading = `DISABLED`。实现前仍存三项独立 prerequisite：historical
  revision-as-of = `OPEN`、experiment/pair/arm identity = `OPEN`、durable regime = `OPEN`。
- 详见 `dev_log/2026-09-15-se-02d-d01-final-acceptance-closeout.md`。

## SE-02D-I01 Result

- 任务：`SE-02D-I01`｜Deterministic Aggregation Core → `SE-02D-I01-FINAL`｜Human-Accepted Final
  Acceptance Closeout / State Sync / Main Integration（docs/state-only、**非**新实现、**非**
  新 Review、**非** I02、**非** DB / revision-folding 实现、**非** Gate C、**非** Live）。
- 状态 = `SE-02D-I01 = ACCEPTED / COMPLETE`（2026-09-15 Human Acceptance = `CONFIRMED`）。
- Independent Review 历史：Independent Initial Review = `FAIL — FIX REQUIRED`；`SE02D-I01-R1` /
  `R2` / `R3`（全部 P1）= 由 `SE-02D-I01-FIX-01` 修复；FIX-01 Independent Re-Review = `PASS`；
  Human Acceptance = `CONFIRMED — 2026-09-15` —— 至此三者记为 `CLOSED`（Worker 不自行宣告
  `CLOSED`）。
- Human-Accepted reviewed candidate（**immutable、远端未移动**）=
  `13b37dff4b8150dea869ba6257ae9f3df24cc1e5`（branch `se-02d-i01-aggregation-core`）。
- 已接受实现：`backend/src/marketpulse/edge/aggregation.py`（`marketpulse.edge.aggregation`，
  1549 行）+ `backend/tests/test_se_02d_aggregation.py`；纯确定性（无 DB / runtime / 新
  dependency / KEEP-DOWNWEIGHT-KILL / threshold）。I01 **不** fold revision chain —— 它消费
  已 canonicalize 的 scope facts。
- Human Design Clarification（2026-09-15，已正式同步至 `DECISIONS.md`）：
  `UNCERTAINTY_METHOD_VERSION = "se02d-overlap-cluster-percentile-bootstrap-v1"` ——
  Accepted `SE-02D-D01` §10.1 要求该 version identifier 进入 deterministic bootstrap seed，
  却未冻结其字面量；本次**仅**补齐 version identifier，**不**改变 bootstrap / RNG 语义、
  95% 区间、10,000 replicates、clustering、LOCO、coverage、sufficiency、tail evidence 或
  Gate C 边界；Accepted D01 design artifact 逐字**未**修改。
- 最终回归（closeout 窗口实测，cwd = closeout worktree、未导出 `DATABASE_URL`）：focused
  `108 passed`；SE-02A/SE-02C 命名回归 `99 passed`；
  `ruff check backend/src backend/tests scripts` = `All checks passed!`；
  `git diff --check` rc=0。`FULL BACKEND SUITE = NOT VERIFIED — isolated DB environment
  unavailable`（本批次为纯模块，已接受范围不需要 DB；不制造 PASS）。
- 集成：Accepted Main before = `f887981d18fd7fc696d99cde702d0fec3e72a16c`；closeout branch =
  `se-02d-i01-final-acceptance-closeout`（base = `13b37dff…`）；集成方法 = `FAST-FORWARD
  ONLY`（单 parent、无 merge commit / squash / rebase / cherry-pick / force push /
  candidate branch movement）。lineage：
  `f887981 → 0c8c095 → 9cb361a → 7745795 → 13b37df → I01 Final Closeout`。
- 本收尾为 docs/state-only：`Production Code Changed After Review = NO` / `Tests Changed
  After Review = NO` / `Schema Changed = NO` / `Migration Added = NO` / `Production
  Dependency Changed = NO` / `Runtime Impact of Closeout = ZERO`；`alembic heads` 单 head 仍
  `20260913_0009`。
- 剩余 `SE-02D` 工作（I01 **未** own）：PostgreSQL loading、full Evidence / Outcome
  revision-chain discovery、canonical Evidence-head / Outcome-head selection from DB、
  `REPEATABLE READ` current-snapshot orchestration、final revision manifest construction
  from DB —— 以上已于 `SE-02D-I02` 实现并验收（见「SE-02D-I02 Result」）；population
  grouping + 调用 I01 `aggregate()` 已于 `SE-02D-I03` 实现并验收（见「SE-02D-I03 Result」）；
  **剩余工作措辞已于 2026-09-16 经 `SE-02D-CLOSE-D01` 调和**：aggregate capability =
  `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend / runtime product consumer =
  `NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical revision-as-of support = `OPEN`。
  **`I01 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I01 收尾时）：`SE-02D V1`
  capability implementation = `COMPLETE AFTER I03`；`SE-02D Overall` 其后已于 2026-09-16 经
  SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`。
- 边界：`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；
  `Integrated Runtime Host = NOT STARTED`；三项 prerequisite（historical revision-as-of /
  experiment/pair/arm identity / durable regime）仍 `OPEN`。本收尾**不**解锁 `I02`。
- 详见 `dev_log/2026-09-15-se-02d-i01-final-acceptance-closeout.md`。
## SE-02D-I02 Result

- 任务：`SE-02D-I02`｜Current-Snapshot Revision Folding → `SE-02D-I02-FINAL`｜Latest-Main
  Acceptance Reconciliation / State Sync / Main Integration（docs/state-only；**非**新实现、
  **非**新 Review、**非** I03、**非** Gate C、**非** Live）。
- 状态 = `SE-02D-I02 = ACCEPTED / COMPLETE`（2026-09-15 Human Acceptance = `CONFIRMED`）。
- Accepted 能力：**CURRENT-SNAPSHOT REVISION FOLDING = IMPLEMENTED / ACCEPTED**：
  单个 PostgreSQL `REPEATABLE READ` / `READ ONLY` 快照；数据库 `statement_timestamp()` 作
  `as_of`；全量可见 Evidence revision-chain 校验 / 折叠；canonical Evidence head selection；
  精确 horizon Outcome revision-chain 校验 / 折叠；canonical Outcome head / `NO_OUTCOME`；
  canonical Evidence ↔ Outcome cross-integrity；`CanonicalScopeFacts` projection；
  扩展 I01 canonical manifest 的 revision-aware manifest。
- Review 历史：Independent Initial Review = `FAIL — FIX REQUIRED`；FIX-01 Independent
  Re-Review = `PASS`；`SE02D-I02-R1` / `R2` / `R3` = `CLOSED`；Human Acceptance =
  `CONFIRMED — 2026-09-15`（Worker 不自行宣告 `CLOSED`）。
- Human-Accepted reviewed candidate（**immutable、远端未移动**）=
  `9b860437b14f64192d3298d30c0204bed1b118f8`（branch
  `se-02d-i02-current-snapshot-folding`）。
- 集成：Original I02 Base = `0ae5b0b44e28db4c8c81c1a64057467d199954cb`；Latest Accepted
  Main before reconciliation = `664207a9caba0c3f5c2589cfca2a10af24f89108`；reconciliation
  branch = `se-02d-i02-final-acceptance-reconciliation`（base = latest `main`）；集成方法 =
  `FAST-FORWARD ONLY`（单 parent、无 merge commit / squash / rebase / cherry-pick /
  force push / candidate branch movement）。production source 与 tests 以 byte-identical
  blob 搬运（git blob identity 验证）。
- 最终回归（closeout 窗口实测，cwd = reconciliation worktree、未导出 `DATABASE_URL`）：
  I02 focused `44 passed`；I01 `108 passed`；SE-02A / SE-02C `155 passed`；
  `ruff check backend/src backend/tests scripts` = `All checks passed!`；
  `git diff --check` rc=0。DB-backed 测试使用 disposable PostgreSQL（`marketpulse_se02d_*`
  现场建 / 删），未触碰 accepted / shared 应用库。`FULL BACKEND SUITE = NOT REQUIRED FOR
  I02 CLOSEOUT / NOT VERIFIED`。
- 本收尾为 docs/state-only：`Production Code Changed After Review = NO` / `Tests Changed
  After Review = NO` / `Schema Changed = NO` / `Migration Added = NO` / `Production
  Dependency Changed = NO` / `API / UI = NO` / `Runtime Activation = NO`；单 head
  `20260913_0009`。
- ⚠️ **`I02 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I02 收尾时）：population
  grouping + orchestration that invokes I01 `aggregate()` 已于 `SE-02D-I03` 实现并验收
  （见「SE-02D-I03 Result」）；剩余工作措辞已于 2026-09-16 经 `SE-02D-CLOSE-D01` 调和：
  aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend /
  runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical arbitrary
  revision-as-of = `OPEN`。`SE-02D V1` capability implementation = `COMPLETE AFTER I03`；
  `SE-02D Overall` 其后已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转
  `ACCEPTED / COMPLETE`。
- 边界：`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；
  三项 prerequisite（historical revision-as-of / experiment-pair-arm identity / durable
  regime）仍 `OPEN`。本收尾**不**解锁 `I03`。
- 详见 `dev_log/2026-09-15-se-02d-i02-final-acceptance-reconciliation.md` 与
  `dev_log/2026-09-15-se-02d-i02-current-snapshot-folding.md`。

## SE-02D-I03 Result

- 任务：`SE-02D-I03`｜Population Grouping + Aggregate Orchestration → `SE-02D-I03-FINAL`｜
  Human Acceptance + State Sync + Main Integration（docs/state-only；**非**新实现、**非**新
  Review、**非** Gate C、**非** Live）。
- 状态 = `SE-02D-I03 = ACCEPTED / COMPLETE`（2026-09-16 Human Acceptance = `CONFIRMED`）。
- Independent Review 历史：Initial Independent Review = `FAIL — FIX REQUIRED`；Finding
  `SE02D-I03-R1`（P1）= `CLOSED`；FIX-01 Independent Re-Review = `PASS — READY FOR HUMAN
  ACCEPTANCE`；Human Acceptance = `CONFIRMED — 2026-09-16`（Worker 不自行宣告 `CLOSED`）。
- Human-Accepted reviewed HEAD（**immutable、远端未移动**）=
  `20a7c333abf81077c409811302331119dff485a5`（branch
  `se-02d-i03-fix-01-projection-identity-validation`）；Original Reviewed Candidate
  （**immutable**）= `44d0e4b14ba0037de4da8e605d7b04b9f5d721e4`（branch
  `se-02d-i03-population-aggregate-orchestration`）。
- Accepted 能力：**POPULATION GROUPING + I01 `aggregate()` ORCHESTRATION = IMPLEMENTED /
  ACCEPTED**：`marketpulse.edge.aggregation_orchestration` 消费一份 I02
  `CurrentSnapshotProjection`；facts ↔ revision-aware manifest 一一对应完整性门（fail
  closed）；按完整结构 `PopulationKey` 分组；每个 population **恰好一次** I01 `aggregate()`
  调用；确定性 population 排序；薄 async 单次读 wrapper。**不** own 统计 / revision
  folding / DB snapshot 语义 / 新 Population Key 语义 / Measurement Signature 语义 /
  API & product 集成。
- 集成：Accepted Main before = `44df66603e6bdba1f3f80c21be5b30c295e4a20a`；closeout branch =
  `se-02d-i03-final-acceptance-closeout`（base = `20a7c333…`）；集成方法 = `FAST-FORWARD
  ONLY`（单 parent、无 merge commit / squash / rebase / cherry-pick / force push /
  candidate branch movement）。lineage：
  `44df666 → 0bf139e → 44d0e4b → 1631f25 → 20a7c33 → I03 Final Closeout`。
- 最终回归（closeout 窗口实测，cwd = FIX lineage worktree、未导出 `DATABASE_URL`）：
  I03 focused `57 passed`；I01 `108 passed`；I02 `44 passed`；I01+I02+I03 合并 `209 passed`；
  `ruff check backend/src backend/tests scripts` = `All checks passed!`；
  `git diff --check` rc=0。`FULL BACKEND SUITE = NOT REQUIRED FOR I03 CLOSEOUT / NOT
  VERIFIED`。
- 本收尾为 docs/state-only：`Production Code Changed After Human Review = NO` /
  `Tests Changed After Human Review = NO` / `Schema Changed = NO` / `Migration Added = NO` /
  `Production Dependency Changed = NO` / `Runtime Behavior Changed By Closeout = NO`；
  单 head `20260913_0009`。
- ⚠️ **`I03 Accepted` 当时 ≠ `SE-02D Overall Complete`**（该句为 I03 收尾时）：aggregate
  capability 其后已由 `SE-02D-CLOSE-D01`（2026-09-16 Human Acceptance = `CONFIRMED`）确认为
  `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；API / frontend / runtime product consumer =
  `NOT REQUIRED FOR SE-02D V1 COMPLETION`；historical arbitrary revision-as-of 仍 `OPEN`。
  `SE-02D V1` capability implementation = `COMPLETE AFTER I03`；`SE-02D Overall` 其后已于
  2026-09-16 转 `ACCEPTED / COMPLETE`。
- 边界：`Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；
  三项 prerequisite（historical revision-as-of / experiment-pair-arm identity / durable
  regime）仍 `OPEN`。本收尾**不**解锁 `I04`（也未定义 I04）。
- 详见 `dev_log/2026-09-16-se-02d-i03-final-acceptance-closeout.md` 与
  `dev_log/2026-09-16-se-02d-i03-population-aggregate-orchestration.md`。

## SE-02D-CLOSE-D01 Result

- 任务：`SE-02D-CLOSE-D01`｜V1 Completion Boundary Reconciliation →
  `SE-02D-CLOSE-D01-FINAL`｜Human Acceptance + State Reconciliation + Main Integration
  （docs/state-only；**非**新实现、**非**新 Review、**非** I04、**非** Gate C、**非** Live）。
- 状态 = `SE-02D-CLOSE-D01 = ACCEPTED / COMPLETE`（2026-09-16 Human Acceptance =
  `CONFIRMED`）；Independent Review = `PASS — READY FOR HUMAN ACCEPTANCE`。
- Human-Accepted candidate（**immutable、远端未移动**）=
  `a9e615726ee964c02a72ea6cbff490d3d74e08f7`（branch
  `design/se-02d-close-d01-v1-completion-boundary`）；Accepted Design artifact =
  `docs/design/SE-02D/SE-02D-CLOSE-D01-V1-Completion-Boundary-Reconciliation.md`
  （Artifact status = `ACCEPTED DESIGN`；§4 A–AD 覆盖矩阵与 §5–§11 分类结论逐字未改，
  **仅**变更 acceptance-state / closeout metadata）。
- **Accepted completion conclusion** = `SE-02D V1 CAPABILITY COMPLETE AFTER I03`。Human 接受
  §15 全部六项结论：V1 capability 于 I03 后完成；API / frontend / runtime consumer **不是**
  V1 完成要求；陈旧 “aggregate / API / product integration = NOT YET IMPLEMENTED” 措辞须调和；
  historical revision-as-of 仍 `OPEN` 但不阻塞 current-snapshot V1 完成；Gate C prerequisites
  仍 `OPEN`；**不需要** I04 implementation batch，下一阶段 = `SE-02D Overall Final Review`
  （已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 完成并转 `ACCEPTED / COMPLETE`）。
- Accepted callable 边界（`docs/design` §6）：
  `CurrentSnapshotRevisionReader.read(horizon)` → `CurrentSnapshotProjection` →
  `aggregate_projection(projection)` → `tuple[AggregationResult, ...]`；
  `aggregate_current_snapshot(reader, horizon)` = 恰好一次读 + 同一纯编排。
  SE-02D V1 **不** own production consumer；RuntimeHost session-factory ownership 未改变
  （未来 consumer composition question，非 V1 blocker）。
- 措辞调和（真值）：aggregate capability = `IMPLEMENTED / ACCEPTED via I01 + I02 + I03`；
  API / frontend / runtime product consumer = `NOT REQUIRED FOR SE-02D V1 COMPLETION` /
  `DEFERRED` 至未来 consumer / product / Gate C 任务（**不**写“已完成”）；historical
  arbitrary revision-as-of = `OPEN / NOT SUPPORTED / FUTURE PREREQUISITE`。
- 集成：Accepted Main before = `779eaf1ca781d64733c8264b0a06c7601deacdba`；closeout branch =
  `se-02d-close-d01-final-acceptance`（base = Human-Accepted candidate）；集成方法 =
  `FAST-FORWARD ONLY`（单 parent、无 merge commit / squash / rebase / cherry-pick / force push /
  candidate branch movement）。lineage：
  `779eaf1 → a9e6157 → SE-02D-CLOSE-D01 Final Closeout`。
- 本收尾为 docs/state-only：`Production Code Changed = NO` / `Tests Changed = NO` /
  `Schema Changed = NO` / `Migration Added = NO` / `Production Dependency Changed = NO` /
  `Runtime Behavior Changed By Closeout = NO`；`pytest` / `ruff = NOT REQUIRED / NOT RUN`；
  单 head 仍 `20260913_0009`。
- ⚠️ **`SE-02D-CLOSE-D01 Accepted` 当时 ≠ `SE-02D Overall Acceptance`**（该句为 CLOSE-D01
  收尾时）：`SE-02D V1` capability implementation = `COMPLETE AFTER I03`，`SE-02D Overall` 其后
  已于 2026-09-16 经 SE-02D Overall Final Acceptance Closeout 转 `ACCEPTED / COMPLETE`；
  `SE-02D = ACCEPTED / COMPLETE` **≠** `Gate C PASS`，`Gate C PASS` **≠** `Live` 授权。
- 边界：`I04 = NOT REQUIRED FOR SE-02D V1`（未定义、未启动）；`Gate C = NOT PASSED`；
  `Live = NOT AUTHORIZED`；Real AI = `NOT ACTIVATED`；KEEP / DOWNWEIGHT / KILL =
  `NOT OWNED BY SE-02D V1`；四个未来边界（historical revision-as-of / experiment-pair-arm
  identity / arm-level selection expectancy-delta / durable regime + Gate C artifact
  retention）仍 `OPEN`。`Gate C PASS != Live authorization`；
  `SE-02D V1 capability complete != Gate C PASS`。
- 详见 `dev_log/2026-09-16-se-02d-close-d01-final-acceptance.md` 与
  `dev_log/2026-09-16-se-02d-close-d01-v1-completion-boundary-reconciliation.md`。

## SE-02D Overall Final Acceptance Closeout Result

- 任务：`SE-02D-OVERALL-FINAL`｜SE-02D Overall Final Acceptance Closeout + P3 Documentation
  Reconciliation + Fast-Forward Main Integration（docs/state-only + package docstring；**非**新实现、
  **非**新 Design、**非**新 Review、**非** I04、**非** Gate C、**非** Live）。
- 状态 = `SE-02D = ACCEPTED / COMPLETE`；`SE-02D Overall = ACCEPTED / COMPLETE`
  （2026-09-16 Human Acceptance = `CONFIRMED`）。
- Overall Final Review = `PASS WITH NON-BLOCKING FINDINGS — READY FOR HUMAN ACCEPTANCE`
  （P0 = `NONE` / P1 = `NONE` / P2 = `NONE`；P3 = `SE02D-OVERALL-R01-P3-01` /
  `SE02D-OVERALL-R01-P3-02`）。
- Human-Accepted reviewed baseline = `55db91ad4c92ef5456b87f9810cf9ec73353d7b2`（immutable
  Git evidence，**未**重建 / **未**改写）；closeout branch =
  `se-02d-overall-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`。
- accepted lineage（均 `ACCEPTED / COMPLETE`）：`SE-02D-D01` / `SE-02D-I01` / `SE-02D-I02` /
  `SE-02D-I03` / `SE-02D-CLOSE-D01`。
- Review 继承证据（来自 Human-Accepted baseline，**非**本收尾实测）：I01 `108 passed`、
  I02 `44 passed`、I03 `57 passed`、合并 `209 passed`；本收尾另行实测复跑，两组证据分列。
- P3 closure：`SE02D-OVERALL-R01-P3-01` = `CLOSED`（`marketpulse.edge` package docstring 仅
  文档级修正）；`SE02D-OVERALL-R01-P3-02` = `CLOSED`（`PRODUCT_REQUIREMENTS.md` /
  `AI_CONTEXT.md` / `PROJECT_STATE.md` capability / group metadata 调和）。两者均为
  documentation / metadata finding，在 Human Acceptance 时为 `NON-BLOCKING`；**未**发现
  P0 / P1 / P2 finding。
- 本收尾为 docs/state-only + 一个 package docstring 修正：`Aggregation / Snapshot /
  Orchestration Implementation Changed = NO` / `Tests Changed = NO` / `Schema Changed = NO` /
  `Migration Added = NO` / `Runtime Behavior Changed = NO` / `Dependency Changed = NO`；
  单 head 仍 `20260913_0009`。
- 边界：historical arbitrary revision-as-of = `OPEN`；Gate C prerequisites = `OPEN`；
  `Gate C = NOT PASSED`；`Live = NOT AUTHORIZED`；Real AI = `NOT AUTHORIZED / NOT ACTIVATED`；
  `KEEP / DOWNWEIGHT / KILL = NOT OWNED BY SE-02D V1`；下一 Acceptance Group =
  `NOT STARTED`。
- 详见 `dev_log/2026-09-16-se-02d-overall-final-acceptance-closeout.md`。

## PRE-01B-D2 Result

- 任务：`PRE-01B-D2`｜AdvisoryIngress / G2→G3 Activation Contract Formal Design →
  `PRE-01B-D2-CLOSE`｜Final Acceptance Closeout & Fast-Forward Main Integration（docs/state-only、
  **非** Implementation、**非** New Design、**非** New Review、**非** Runtime validation、
  **非** Real AI activation、**非** `PRE-01B-I2`）。
- 状态 = `PRE-01B-D2 = ACCEPTED / COMPLETE`（2026-09-17 Human Acceptance = `CONFIRMED`）。
- Independent Re-Review = `PRE-01B-D2-FIX-05 = PASS`；P0 = `NONE`；P1 = `NONE`；P2 = `NONE`；P3 = `NONE`。
- Human-Accepted reviewed candidate（**immutable、远端未移动**）=
  `cce1ae7b862b038a99976c802c0985df01b35285`（branch
  `design/pre-01b-d2-fix-05-return-completion-authority`）；accepted lineage 为线性单 parent：
  `a90c5968… → b5767d1… → 4548920… → d3922dd… → cce1ae7…`（`FIX-02` / `FIX-03` / `FIX-04` 为
  historical failed reviewed candidates，保持 immutable 且**不**改写为 PASS）。
- Accepted Design artifact =
  `docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md`（Artifact status =
  `ACCEPTED / COMPLETE`；normative design 正文逐字未改，仅状态级最小同步）。
- 已接受架构决策（摘要；完整决策见 `DECISIONS.md`「PRE-01B-D2 V1」条目，完整契约见 Accepted
  Design artifact）：host-owned `AdvisoryIngress` boundary；exact admission Evidence revision
  binding；immutable decision invocation identity；bounded in-process advisory dispatch；
  PostgreSQL durable correctness authority；shadow-safe Gate A boundary；provider / DB separation；
  Protection isolation；已接受 DB timeout / SAVEPOINT 语义；已接受 connection-return completion
  authority（完整 positive predicate；callback-only **不**释放容量）；Gate A / Gate B 分离。
- 明确非声称（本 Acceptance **仅**接受 Formal Design）：**不**证明 / **不**授权 `PRE-01B-I2`
  implementation、live `G2→G3` activation、Real AI activation、provider configuration、真实
  provider 调用、Gate A activation、Gate B activation、Gate C PASS、Live authorization、
  profitability / trading edge。Design Acceptance 是前置条件，**不是** runtime activation。
- Human Decision Pack carry-forward：Pack A = `NONE`；Pack B = numeric production activation
  settings 仍 `UNRESOLVED`（本收尾**未**发明数值、**未**静默授权 production defaults）；
  Pack C = Gate-A observation / sufficiency / acceptance thresholds 仍 `UNRESOLVED`。
- 本收尾为 docs/state-only：`Production Code = ZERO CHANGE` / `Tests = ZERO CHANGE` /
  `Schema = ZERO CHANGE` / `Migration = ZERO CHANGE` / `Runtime = ZERO` / `Config = ZERO CHANGE` /
  `Product Requirements = ZERO CHANGE`。
- 集成方法 = `FAST-FORWARD ONLY`；closeout branch = `pre-01b-d2-final-acceptance-closeout`。
- 详见 `dev_log/2026-09-17-pre-01b-d2-final-acceptance-closeout.md`。

## UI-V1-D01 Result

- 任务：`UI-V1-D01-FINAL-DOC-01`｜MarketPulse UI V1 Formal Design — Repository Persistence
  （DOCS / STATE ONLY、`NO PRODUCTION IMPLEMENTATION`；**非** New Design、**非** 实现、
  **非** `UI-F01`、**非** `UI-RD01`、**非** `PRE-01B-I2`、**非** Real AI activation）。
- 状态（Repository Persistence 完成时）= `UI-V1-D01 = HUMAN-ACCEPTED / FROZEN`（2026-09-17
  Human Acceptance = `CONFIRMED`）；**`Implementation = NOT STARTED`**。该状态其后已于
  2026-09-17 经 UI-V1-D01 Final Acceptance Closeout 转 `ACCEPTED / FROZEN /
  REPOSITORY-INTEGRATED` 并以 `FAST-FORWARD ONLY` 收编 `main`（见文末「UI-V1-D01 Final
  Acceptance Closeout Result」）。
- Included closure：`UI-V1-D01-FIX-01｜Formal Contract Closure` = `INCLUDED / CLOSED`
  （其语义已并入正式设计 artifact；FIX-01 不产生独立 artifact）。
- Independent Final Review = `PASS — READY FOR FORMAL FREEZE`；P0 = `NONE`；P1 = `NONE`；
  P2 = `NONE`；P3 = `NONE`。
- Accepted Design artifact =
  `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（Artifact status =
  `ACCEPTED / FROZEN`）。
- Task Base SHA = `547095f6705ce651272363676e2a2b51a66bb8b6`（= 实测 `origin/main`，
  无 baseline drift）；task branch = `design/ui-v1-d01-formal-freeze`；**不** merge `main`。
- Human Acceptance 时点实读：`docs/design/UI-V1/` 此前不存在；全仓库 `UI-V1` 与五个
  Product Read Projection 名称此前均为零命中，属首次写入。
- 冻结要点（摘要；完整契约见 Accepted Design artifact，本条目**不**复制全文）：
  产品定位 = 只读纸面交易运维与证据终端（**非**手工交易终端 / **非**运行时控制面板 /
  **非** Live Trading UI / **非** AI 自主控制界面）；顶层 IA = 恰好五页且 **AI 无独立顶层页**；
  主语言简体中文、desktop-first；业务行为 read-only 且**无** mutation 控制项；
  `LOADING` / `EMPTY` / `FRESH` / `STALE` / `UNAVAILABLE` / `CAPABILITY_NOT_INTEGRATED`
  互不相同且 unavailable **不**渲染为 zero / empty；Scanner Event **不**成为 BUY/SELL
  Trading Signal；Opportunity trace 使用双分支模型且 **Forward Outcome ≠ Economic Result**；
  Edge Primary horizon = `5m` 且使用 **Exact Population identity**（前端不池化人口）；
  不展示未支持的策略指标与未接受的账户指标；Account 现金语义正确
  （`cash_balance` / `reserved_cash` / `available_cash` / `realized_pnl`）；
  支持多标的 / 多经济对象同时存在；**Fill 是交易已发生的必要条件**；
  Position Protection 仅来自 durable Position authority 且 Plan 过期不使其失效；
  `Live` / `Ready` / `Health` 互不相同且 `/ready` 503 解析为合法权威状态；
  Real AI disabled 渲染为 `U0 未激活`；Product boundary 与 Runtime Mode 分离；
  historical / replay 数据**不**伪装成 live operational truth；认证后的 Product Read 边界；
  Edge aggregation 的 CPU 工作不阻塞主 event loop；`1440×900` 与 `1280×720` 布局验收；
  状态**不**单靠颜色传达。
- 明确非声称（本 Acceptance **仅**接受 Formal Design）：**不**证明 / **不**授权
  UI 实现、前端实现、Product Read API 实现、`PRE-01B-I2` implementation、live `G2→G3`
  activation、Real AI activation、provider configuration、Gate A / Gate B activation、
  Gate C PASS、Live authorization、profitability / trading edge。设计层实施顺序
  （`UI-F01 → UI-RD01 → UI-I01..UI-I06`）**仅**为排序，**不**自动授权实现。
- 本任务为 docs/state-only：`Production Code = ZERO CHANGE` / `Frontend Code = ZERO CHANGE` /
  `Backend Code = ZERO CHANGE` / `Tests = ZERO CHANGE` / `Schema = ZERO CHANGE` /
  `Migration = ZERO CHANGE` / `Config = ZERO CHANGE` / `Runtime = ZERO` /
  `PRODUCT_REQUIREMENTS.md = ZERO CHANGE`。
- 详见 `dev_log/2026-09-17-ui-v1-d01-formal-design-freeze.md`。

## UI-V1-D01 Final Acceptance Closeout Result

- 任务：`UI-V1-D01-FINAL-ACCEPTANCE-CLOSEOUT`｜MarketPulse UI V1 Formal Design — Final
  Acceptance / Main Integration Closeout（DOCS / STATE / GIT INTEGRATION ONLY；
  `NO PRODUCT IMPLEMENTATION`；**非** New Design、**非** 实现、**非** `UI-F01` / `UI-RD01`、
  **非** `PRE-01B-I2`、**非** Real AI activation）。
- Human Acceptance = `CONFIRMED — 2026-09-17`；Independent Final Repository Review = `PASS`
  （P0 = `NONE`；P1 = `NONE`；P2 = `NONE`；P3 = `NONE`）。
- 最终状态 = `UI-V1-D01 = ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`；`UI-V1-D01-FIX-01` =
  `CLOSED`；`UI-V1-D01-FINAL-DOC-01` = `COMPLETE`；documentation fixes `FIX-01` = `COMPLETE` /
  `FIX-02` = `COMPLETE`。
- Human-Accepted / Reviewer-approved final candidate =
  `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4`（branch `design/ui-v1-d01-final-doc-fix-02`，
  远端同 SHA、immutable、未被移动）。
- Accepted lineage（线性单 parent，`FAST-FORWARD ONLY` 收编 `main`）= `547095f6705ce651272363676e2a2b51a66bb8b6`
  → `1919832a5d9ddbcbec6ea535d178e3d21795b539` → `e7d69ae38f8a24bdecb4780661342d5cfda734f7`
  → `b2d1af0c7388fe2bbfe52fb85a1c78ee269d10e4` → 本次 docs/state-only closeout commit。
- closeout branch = `ui-v1-d01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`
  （无 merge commit / 无 squash / 无 rebase / 无 cherry-pick / 无 force push）。
- Accepted Design artifact（现已在 `main`）=
  `docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md`（Artifact status =
  `ACCEPTED / FROZEN`）；本收尾**未**修改该 artifact —— 实读未发现需要修改的真实矛盾。
- **`Implementation = NOT STARTED`**；Product Read API implementation = `NOT STARTED`。
  下一计划任务 = `UI-F01`（Frontend Foundation），**但本收尾既不实现、也不自动授权** `UI-F01`；
  任何后续设计 / 实现均需另开独立获批窗口。
- 明确非声称（本收尾**仅**完成设计的接受与仓库集成）：`PRE-01B-I2` =
  `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；
  Forward Outcome runtime integration = `NOT INTEGRATED`；`Gate C` = `NOT PASSED`；`Live` =
  `NOT AUTHORIZED`；Trading Edge = `NOT PROVEN`。
- 本收尾为 docs/state-only：`Production Code = ZERO CHANGE` / `Frontend Code = ZERO CHANGE` /
  `Backend Code = ZERO CHANGE` / `Tests = ZERO CHANGE` / `Schema = ZERO CHANGE` /
  `Migration = ZERO CHANGE` / `Config = ZERO CHANGE` / `Runtime = ZERO` /
  `PRODUCT_REQUIREMENTS.md = ZERO CHANGE`。
- 详见 `dev_log/2026-09-17-ui-v1-d01-final-acceptance-closeout.md`。

## UI-F01-I01 Result

- 任务：`UI-F01-I01`｜Frontend Foundation（IMPLEMENTATION + VERIFICATION）。本批**仅**建立
  Foundation，**不**实现任何正式业务页面。
- Task Base（任务卡声明）= `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`；执行前**实读**远端真值
  `git ls-remote origin refs/heads/main` = 同 SHA ⇒ **无 baseline drift**（CIP-02）。
  task branch = `ui-f01-i01-frontend-foundation`，**未** merge `main`、**未** push `main`。
- Result（Implementation 完成时）= **`UI-F01-I01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`**；
  当时**不**等于 `ACCEPTED` / `COMPLETE`（Independent Review 与 Human Acceptance 当时另开独立
  窗口）。该状态其后已于 2026-09-17 经 Independent Review（`FAIL — FIX REQUIRED`）→
  `UI-F01-I01-FIX-01` → Independent Re-Review（`PASS — READY FOR HUMAN ACCEPTANCE`）→ Human
  Acceptance（`CONFIRMED`）转为 **`UI-F01-I01 = ACCEPTED / COMPLETE`**（见文末「UI-F01-I01
  Final Acceptance Closeout Result」）。
- 冻结复用决策**按实际安装结果**落地：`react-router@8.4.0`（Declarative，非 Framework Mode / 非
  SSR）、`@tanstack/react-query@5.103.1`、`openapi-fetch@0.17.0`、既有
  `openapi-typescript@7.13.0`、`vitest@5.0.1` + `jsdom@30.1.0` +
  `@testing-library/react@16.3.3` / `dom@10.4.2` / `jest-dom@7.0.1` / `user-event@14.6.7` +
  `msw@2.15.0`、`vite@8.3.0` + `@vitejs/plugin-react@6.1.1` + `typescript@5.9.3`。
  **未**引入 Axios；**未**引入 Redux / Redux Toolkit / Zustand / MobX / XState；
  **未**引入 SSR / PWA / service worker / WebSocket 框架 / offline cache / refresh token /
  Remember Me / 多标签页 auth 协调 / design system / UI 组件框架。
- 工具链：Node `v22.22.2` / npm `10.9.7`；全部选中依赖 `engines` 均满足。
  TypeScript 版本为**证据驱动**的兼容性收敛：`latest` 解析到 `typescript@7.0.2` 时
  `openapi-typescript@7.13.0` 的 peer `typescript@^5.x` 未被满足（`ERESOLVE overriding peer
  dependency`）⇒ 改为 `typescript@^5.9.3`（`^5.x` 最新稳定版）后树一致、无 override。
- 生成纪律：`frontend/src/api/generated.ts` 已由当前后端 OpenAPI 重新生成（408 行，含
  `/api/v1/live` 与 `/api/v1/ready`）；生成链路为 `scripts/export-openapi.py`（直接导入 FastAPI
  app 对象，无需运行服务 / 数据库 / `.env`）+ `generate:api` + `check:api-drift`
  （重新导出 + 重生成并逐字节比对，漂移即 exit 1）。**未**手写任何重复后端权威 DTO。
- 验证（全部真实执行、全部 exit 0）：`npm ci`；`npm run typecheck`（`tsc -b`）；
  `npm run test:run` = **7 files / 37 tests PASS**；`npm run build`；`npm run generate:api`；
  `npm run check:api-drift`。另以注入式探针证明两个门**有牙齿**：临时类型错误使
  `typecheck` exit 1，人为向 `generated.ts` 追加一行使 `check:api-drift` exit 1
  （两者均已复原/删除，未进入提交）。
- 冻结语义落点：`/ready` `503` = 权威 NOT READY 且 **body 原样保留**，**不**成为 `NetworkError`、
  **不**成为通用后端故障、**不**被重试；`Readiness != Risk Admission`（代码中无任何由 ready
  推断 `risk_admission_open` 的路径）；Query cache `stale` 与 MarketPulse 业务 `FRESH / STALE`
  **无**映射；无全局高频轮询；`Unavailable != zero` 的六态模型属后续页面范围、本批**未**实现。
- 明确非声称：业务页面（总览 / 市场与机会 / 策略研究 / 交易与仓位 / 系统）= 仍为占位，
  `NOT STARTED`；Product Read API（`MarketScannerRead` / `OpportunityTraceRead` /
  `EdgeAggregateRead` / `TradingAuditRead` / `SystemIncidentRead`）= `NOT STARTED`；
  `PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` =
  `NOT ACTIVE`；Forward Outcome runtime integration = `NOT INTEGRATED`；`Gate C` = `NOT PASSED`；
  `Live` = `NOT AUTHORIZED`；Trading Edge = **未证明**。
- 改动面：`frontend/**` + `dev_log/` + `PROJECT_STATE.md` / `AI_CONTEXT.md` / `DECISIONS.md`
  最小同步。`backend/**` = ZERO CHANGE；`schema` / `migration` = ZERO CHANGE；
  `frontend/tsconfig.json` = **零改动**（`strict: true` 保持）。
- 非阻塞 Finding（本批**不**修，CIP-05）：`F-01` 后端 `/live` `/ready` `/health` `/runtime`
  等仍为 `dict[str, object]` ⇒ 生成类型为 `{[key: string]: unknown}`，typed DTO 属 `UI-RD01`；
  `F-02` `vite.config.ts` / `vitest.config.ts` 不在 `tsconfig.json` `include` 内；
  `F-03` `generate:api` / `check:api-drift` 依赖本机 `py -3.14` 可导入后端运行时。
- 详见 `dev_log/2026-09-17-ui-f01-i01-frontend-foundation.md`。

## UI-F01-I01-FIX-01 Result

- 任务：`UI-F01-I01-FIX-01`｜Transport Error Boundary Closure（IMPLEMENTATION + VERIFICATION）；
  关闭独立复审 Finding `UI-F01-I01-R1`（generic transport error-normalization boundary 不完整，
  表现为通用调用方仍需自行复现「catch 网络异常 / 检查 `response.ok` / 映射 `401` / 映射普通
  `4xx` / 映射普通 `5xx`」，且归一化逻辑大部分由 `readReadiness()` 拥有；原批 `R-02` 已预置该风险）。
- Reviewed candidate = `0c9186d2d94450d39754eb40536148a73deb123c`（单 parent = main
  `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`；执行前实读远端 `main` 同 SHA ⇒ **无** baseline
  drift；candidate **未**重写、**未** reset / rebase / amend）。Fix branch =
  `ui-f01-i01-fix-01-transport-error-boundary`（独立 clean worktree），**未** merge `main`、
  **未** push `main`。
- 实现边界：新增 `frontend/src/api/transport.ts` 作为**唯一** Foundation-owned 通用传输解释路径
  ——`requestData()`：network failure → `NetworkError`、`401` → `UnauthorizedError`、其他非 2xx →
  `HttpError`（status + body 保留）、2xx + 可解释 body → typed data（生成类型的成功 body）、
  2xx + 不可解释 body → `UnexpectedResponse`；`transportErrorForStatus()` 由 `readiness.ts`
  **迁入**本模块；`sendRequest()` 只为 `/ready` 的 503 前置拦截提供网络层归一化，不做 HTTP 分类。
  **未**引入 Repository / Gateway / RequestFactory / BaseService / 第二个 HTTP client / Axios。
- 唯一显式例外：`/ready` —— 先取原始 outcome，`503` → 权威 `NOT_READY`（body 原样保留、**不**成为
  `HttpError` / `NetworkError` / 通用后端故障、**不**被重试）；其余状态复用与通用路径**同一**实现。
  该例外已被新用例 6 反向固定：`/api/v1/runtime` 的 `503` 是普通 `HttpError`，其权威语义**只**
  属于 `/ready`。
- 真实验证（全部在 Fix worktree 内执行、全部 exit 0）：`npm run typecheck`；
  `npm run test:run` = **7 files / 44 tests PASS**（既有 37 个逐字保留 + 新增 7 个，无删除 /
  削弱 / skip）；`npm run build`；`npm run check:api-drift`。基线对照：改动前同一 worktree 为
  `7 files / 37 tests PASS` ⇒ delta 精确为 `+7 tests`。
- 牙齿证据（注入式探针，脚本在仓库外，探针后逐字节复原并复核 sha256）：P-1 停用通用非 2xx 解释 ⇒
  4 个新用例 fail；P-2 停用「body 无法解析 ≠ 网络故障」的区分 ⇒ 1 个新用例 fail；P-3 移除
  `/ready` 的 `503` 拦截 ⇒ 5 个用例 fail（含既有 readiness 用例）。复原后重跑 exit 0。
- 改动面：`frontend/src/api/**` 4 个文件（`transport.ts` 新增；`readiness.ts` / `errors.ts` /
  `transport.test.ts` 修改）+ `dev_log/2026-09-17-ui-f01-i01-fix-01-transport-error-boundary.md` +
  本文件与 `AI_CONTEXT.md` 最小同步。`frontend/package.json` / `frontend/package-lock.json` /
  `frontend/tsconfig.json` / `generated.ts` / `backend/**` / schema / migration /
  `frontend/src/auth/**` / `frontend/src/app/**` = **ZERO CHANGE**。
- 版本真值（按实际 lockfile 报告）：`react` = `19.3.0`、`react-dom` = `19.3.0`、
  `react-router` = `8.4.0`、`@tanstack/react-query` = `5.103.1`、`openapi-fetch` = `0.17.0`、
  `msw` = `2.15.0`、`vitest` = `5.0.1`、`vite` = `8.3.0`、`typescript` = `5.9.3`。
  上一份 Completion Report 的 `react` / `react-dom` 版本笔误**未**通过改动任何 production
  dependency 来"修正"。
- 明确非声称：业务页面（五页仍为占位）= `NOT STARTED`；Product Read API = `NOT STARTED`；
  `UI-RD01` / `UI-I01..UI-I06` = **未**实现、**未**授权；`PRE-01B-I2` =
  `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；
  Forward Outcome runtime integration = `NOT INTEGRATED`；`Gate C` = `NOT PASSED`；`Live` =
  `NOT AUTHORIZED`；Trading Edge = **未证明**。`PRE-01B-I2` 未被本批激活。
- 本批**未**执行 `npm ci`（`package.json` / `package-lock.json` 零改动，依赖树与 candidate 一致；
  `frontend/node_modules` 由 candidate worktree 同盘整体 rename 迁移复用，该目录被 `.gitignore`
  忽略、不属 repository truth）；**未**做浏览器真机联调、**未**连接真实 backend。
- Result（Fix 完成时）= **`UI-F01-I01-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`**；
  当时**不**等于 `ACCEPTED` / `COMPLETE`（Independent Re-Review 与 Human Acceptance 当时另开
  独立窗口）。该状态其后已于 2026-09-17 经 Independent Re-Review（`PASS — READY FOR HUMAN
  ACCEPTANCE`）与 Human Acceptance（`CONFIRMED`）转为 **`UI-F01-I01-FIX-01 = ACCEPTED /
  CLOSED`**（见文末「UI-F01-I01 Final Acceptance Closeout Result」）。
- 遗留（非阻塞，**未**写 resolved）：`F-01` `auth/AuthSessionProvider.tsx` 的 `signIn()` 仍自行
  catch / 检查 `response.ok`（Scope 只允许 `frontend/src/api/**`，本批**未**改 auth 边界；login
  `401` = 凭据判决而非传输类别）；原批 `R-01` / `R-03` 状态**不变**；原批 `R-02` 由本批关闭。
- 详见 `dev_log/2026-09-17-ui-f01-i01-fix-01-transport-error-boundary.md`。

## UI-F01-I01 Final Acceptance Closeout Result

- 任务：`UI-F01-I01-FINAL`｜Frontend Foundation — Final Acceptance Closeout + Main Integration
  （DOCS / STATE / GIT INTEGRATION ONLY；`NO PRODUCT IMPLEMENTATION`；**非** New Design、**非** 实现、
  **非** Product Read API、**非** `UI-RD01`、**非** `PRE-01B-I2`、**非** Real AI activation）。
- Human Acceptance = `CONFIRMED — 2026-09-17`；Independent Initial Review = `FAIL — FIX REQUIRED`；
  FIX = `UI-F01-I01-FIX-01`（`ACCEPTED / CLOSED`）；Independent Re-Review =
  `PASS — READY FOR HUMAN ACCEPTANCE`；`UI-F01-I01-R1` = `CLOSED`；Final Re-Review severity：
  P0 = `NONE` / P1 = `NONE` / P2 = `NONE` / P3 = `NON-BLOCKING ONLY`。
- 最终状态 = `UI-F01-I01 = ACCEPTED / COMPLETE`；`UI-F01-I01-FIX-01` = `ACCEPTED / CLOSED`；
  `UI-F01 = ACCEPTED / COMPLETE`（**仅**接受 Frontend Foundation 本身）。
- Human-Accepted reviewed candidate = `ecc21356851f7deca8fd55ea086ec1007b0675d4`（branch
  `ui-f01-i01-fix-01-transport-error-boundary`；远端同 SHA、immutable、未被移动）；original
  implementation candidate = `0c9186d2d94450d39754eb40536148a73deb123c`（branch
  `ui-f01-i01-frontend-foundation`，immutable）。
- Accepted lineage（线性单 parent，`FAST-FORWARD ONLY` 收编 `main`）= `2c95cc21cc99d85c5692c5f9b276c5805cc32b13`
  → `0c9186d2d94450d39754eb40536148a73deb123c` → `ecc21356851f7deca8fd55ea086ec1007b0675d4`
  → 本次 docs/state-only closeout commit。
- closeout branch = `ui-f01-i01-final-acceptance-closeout`；集成方法 = `FAST-FORWARD ONLY`
  （无 merge commit / 无 squash / 无 rebase / 无 cherry-pick / 无 force push）。
- Final Regression（收尾前在候选 lineage 上重新执行，全部 exit 0）：`npm run typecheck` /
  `npm run test:run` = **7 files / 44 tests PASS** / `npm run build` / `npm run check:api-drift`。
- **本 Acceptance 仅接受 Frontend Foundation**：正式业务页面（五页仍为占位）= `NOT STARTED`；
  Product Read API（`MarketScannerRead` / `OpportunityTraceRead` / `EdgeAggregateRead` /
  `TradingAuditRead` / `SystemIncidentRead`）= `NOT STARTED`；`UI-RD01` / `UI-I01..UI-I06` =
  **未**实现、**未**授权（`UI-RD01` = 下一计划正式设计任务，**须**另行 Human 授权）。
- 明确非声称（本收尾**仅**完成 Frontend Foundation 的接受与仓库集成）：`PRE-01B-I2` =
  `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；
  Forward Outcome runtime integration = `NOT INTEGRATED`；`Gate C` = `NOT PASSED`；`Live` =
  `NOT AUTHORIZED`；Trading Edge = `NOT PROVEN`。
- 保留的非阻塞 finding（**未** resolved）：`F-01`（后端 system / read endpoint 部分返回
  `dict[str, object]` ⇒ 生成 body typing 偏弱，正式 Product Read DTO 属 `UI-RD01`）；`F-02`
  （`vite.config.ts` / `vitest.config.ts` 不在 frontend tsconfig `include` 内）；`F-03`（OpenAPI
  生成依赖仓库兼容的 Python 运行时调用，Windows = `py -3.14`）；`R-03` 等价项（真实浏览器 +
  真实 backend 的端到端 proxy 集成**不**属 UI-F01 验收证据）；`UI-F01-I01-FIX-01 F-01`（`auth/`
  的 `signIn()` 仍自行 `try/catch`）。
- 本收尾为 docs/state-only：`Production Code = ZERO CHANGE` / `Frontend Code = ZERO CHANGE` /
  `Backend Code = ZERO CHANGE` / `Tests = ZERO CHANGE` / `Schema = ZERO CHANGE` /
  `Migration = ZERO CHANGE` / `Config = ZERO CHANGE` / `Runtime = ZERO` /
  `PRODUCT_REQUIREMENTS.md = ZERO CHANGE`。
- 详见 `dev_log/2026-09-17-ui-f01-i01-final-acceptance-closeout.md`。

## UI-RD01 Final Design Acceptance Closeout

- Current Final Acceptance state: `UI-V1-D01-AMEND-01-CR02-FIX-01 = ACCEPTED / COMPLETE`；closure candidate `UI-V1-D01-AMEND-01-CR02-FIX-01-R2 = ACCEPTED / CLOSED`；CR-02 Foundation remediation = `ACCEPTED / COMPLETE`；Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED — 2026-09-18`；Human-Accepted Reviewed Candidate = `b82076102b45a780a9c2bb44e00923fa768bfe91`。`CR02-IR-P1-01 = CLOSED`；`CR02-RR-P1-01 = CLOSED`；`CR01-IR-P2-01 = RESOLVED INCIDENTALLY / TEST-FIXTURE ONLY`（`HOST_DISABLED` / `MARKET_DATA_STALE` fixtures；CR-01 production behavior = ZERO CHANGE）。CR-01 = `ACCEPTED / COMPLETE`；CR-05 = `ACCEPTED / COMPLETE`；`CR05-IR-P2-01 = CLOSED`；CR-03 / CR-04 / CR-06 = `NOT APPLICABLE YET`；`UI-RD01-I01 = ACCEPTED / COMPLETE`；`UI-RD01-I02–I05 = NOT STARTED / NOT AUTHORIZED`。Final integration is fast-forward-only; no production/test/backend/generated/dependency/router changes after the reviewed candidate.

- Current CR-02 R2 update (supersedes the R1 record below): `UI-V1-D01-AMEND-01-CR02-FIX-01-R2 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`（Parent Reviewed Candidate = `5684b657cbecd28573174fd73de7963a384900ca`；Task Base = `dd6dce564122a7ad8ea912ba1291f2d3625a3a46`；branch = `ui-amend-cr02-session-ownership`）。`CR02-RR-P1-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`：不改变 generation semantics、request-id ownership 或 Provider active separation；仅将 active/disposed fence 从 passive `useEffect` 改为同步 commit lifecycle 的 `useLayoutEffect`。真实 Provider unmount 回归在 `rerender()` commit 后、等待新 UI 前立即释放旧 `401`，并证明新 Provider token、Query cache 与认证路由不受影响；StrictMode current-401 仍具权威性。CR-02 Foundation remediation = `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`; CR-05 = `REQUIRED / NOT STARTED`; no backend/OpenAPI/generated.ts/dependency/router change.

- Current CR-05 update: `UI-V1-D01-AMEND-01-CR05-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`；CR-05 shared Product Read contract remediation = `IMPLEMENTED / READY FOR INDEPENDENT REVIEW`（Task Base = `71f8c4ec52323c07f21c6c8434f9010ea04cf935`；branch = `ui-amend-cr05-trace-node-state`）。`TraceNodeState` now has the exact six frozen values, including `NOT_YET_DUE`; focused contract regression proves `NOT_REACHED != NOT_YET_DUE` and `TraceNodeDTO` JSON serialization. No classifier, endpoint, consumer, frontend trace/maturity, OpenAPI/generated.ts, schema, or dependency change. CR-01 = `ACCEPTED / COMPLETE`；CR-02 = `ACCEPTED / COMPLETE`；CR-03 / CR-04 / CR-06 = `NOT APPLICABLE YET`；`UI-RD01-I01 = ACCEPTED / COMPLETE`；`I02–I05 = NOT STARTED / NOT AUTHORIZED`；this is not an acceptance/complete declaration.

- CR-05 Final Human Acceptance Closeout: `UI-V1-D01-AMEND-01-CR05-FIX-01 = ACCEPTED / COMPLETE`；`UI-V1-D01-AMEND-01-CR05-FIX-01-R1 = ACCEPTED / CLOSED`；CR-05 shared Product Read contract remediation = `ACCEPTED / COMPLETE`；`CR05-IR-P2-01 = CLOSED`；Independent Re-Review = `PASS — READY FOR HUMAN ACCEPTANCE`；Human Acceptance = `CONFIRMED — 2026-09-19`；Human-Accepted Reviewed Candidate = `125af5e62ab3d67171c06617c7701bfd0f94e37d`；Final Closeout commit is docs/state-only and integrated fast-forward-only into `main`. Frozen semantics remain the exact six `TraceNodeState` values with `NOT_REACHED != NOT_YET_DUE`; no classifier, endpoint, consumer, frontend trace/maturity, OpenAPI/generated.ts, schema, or dependency change. CR-01 / CR-02 = `ACCEPTED / COMPLETE`；CR-03 / CR-04 / CR-06 = `NOT APPLICABLE YET`；`UI-RD01-I01 = ACCEPTED / COMPLETE`；`I02–I05 = NOT STARTED / NOT AUTHORIZED`。

- Current CR-02 update (supersedes the earlier historical CR-02 planning record in this section): `UI-V1-D01-AMEND-01-CR02-FIX-01-R1 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`（Task Base = `dd6dce564122a7ad8ea912ba1291f2d3625a3a46`；Parent Reviewed Candidate = `edf07d7d52c64e9c633f64603d887acccf7c9bfe`；branch = `ui-amend-cr02-session-ownership`）。CR-02 Foundation remediation now separates local ephemeral `Symbol` session generation from Provider active/disposed state: generation advances only on successful sign-in and current-session teardown; unmount only marks its client lifetime inactive. `createApiClient` captures protected-request generation by openapi-fetch request `id`, then permits a protected `401` teardown only when that generation is current and the owning Provider remains active; bookkeeping remains response/error-local. The production-representative StrictMode regression proves synthetic Effect cleanup/setup does not stale-fence a held current-session `401`, which still clears token and authenticated Query cache, enters Login, and returns `UnauthorizedError`. G1 → sign-out → G2 → late G1 `401`, successful-sign-in replacement, and real old-Provider-lifetime races preserve G2/new-lifetime token, route, and Query cache while old requests still produce `UnauthorizedError`. `CR01-IR-P2-01 = RESOLVED INCIDENTALLY / TEST-FIXTURE ONLY` (`READINESS_HOST_DISABLED` → `HOST_DISABLED`; DEGRADED fixture uses `MARKET_DATA_STALE`); CR-01 production behavior unchanged. CR-05 = `REQUIRED / NOT STARTED`; `UI-RD01-I01 = ACCEPTED / COMPLETE`; `I02–I05 = NOT STARTED / NOT AUTHORIZED`; no backend/OpenAPI/generated.ts/RuntimeHost/router/dependency change.

- `UI-RD01 = ACCEPTED / FROZEN`；Human Design Acceptance = `CONFIRMED — 2026-09-17`；Final Design Re-Review = `PASS`。
- `UI-V1-D01-AMEND-01 = ACCEPTED / FROZEN`（Human-confirmed post-freeze amendment）；`UI-V1-D01-AMEND-01-PERSIST = ACCEPTED / COMPLETE`（Independent Re-Review = `PASS`；Human Acceptance = `CONFIRMED — 2026-09-18`；Human-Accepted Reviewed Candidate = `73cae6a47e147ec655f660cecf235864ffdbbb9c`，immutable）。`UI-V1-D01` / `UI-RD01` = `ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`。artifact：`docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md`；`UI-V1-D01-AMEND-01-CR01-FIX-01 = ACCEPTED / COMPLETE`（Independent Review = `PASS WITH NON-BLOCKING FINDING`；Human Acceptance = `CONFIRMED — 2026-09-18`；Human-Accepted Reviewed Candidate = `42a707a587b3b6b8cb2dd48830753a8a53bda2f0`，immutable）；CR-01 typed readiness Foundation remediation = `ACCEPTED / COMPLETE`；`CR01-IR-P2-01 = REMAINS / NON-BLOCKING`（本 closeout 不修复）。CR-02 session-generation current Foundation remediation = `REQUIRED / NOT STARTED`；CR-03 / CR-04 / CR-06 current remediation = `NOT APPLICABLE YET` and future relevant implementation must comply；CR-05 current shared Product Read contract remediation = `REQUIRED / NOT STARTED` because I01's already-implemented `backend/src/marketpulse/api/product/models.py::TraceNodeState` lacks `NOT_YET_DUE`。`UI-RD01-I01 = ACCEPTED / COMPLETE` remains historically accepted; the post-freeze remediation does not revoke it；`I02–I05` remain `NOT STARTED / NOT AUTHORIZED` and this closeout does not activate PRE-01B-I2, Real AI, Gate, or Live。
- `UI-RD01-DESIGN-FIX-02 = ACCEPTED / CLOSED`；`UI-RD01-R1`–`R8 = CLOSED`；`Open Decisions = NONE`。
- Accepted artifact：`docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md`。
- `UI-RD01-I01 = ACCEPTED / COMPLETE`（Human Acceptance = `CONFIRMED — 2026-09-18`；Independent Re-Review = `PASS`；Human-Accepted reviewed candidate = `e0fceafdb8cc35498144929ac2f4295327071bfb`）。范围仅为 shared Product Read contracts、nullable/non-owning `ProductReadContext`、`SystemIncidentRead` vertical slice 与 OpenAPI/generated.ts integration；`I02–I05` = NOT STARTED / NOT AUTHORIZED，Real AI = NOT ACTIVATED，live G2→G3 = NOT ACTIVE，Gate A/B/C = NOT ACTIVATED / NOT PASSED，Live = NOT AUTHORIZED。
- `UI-RD01-I01-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`（2026-09-18；parent = Reviewed Candidate `2b47b8fae7c47e53f73bfe3a7e75884bb615d221`，同一 candidate branch，**未**合并 `main`、**未**获 Human Acceptance）。收口 Independent Review findings：`RR-P1-01` 非法 Incident 过滤 → 422（复用权威枚举 `IncidentStatus` / `IncidentType`）、`RR-P1-02` 端点级 snapshot 失败 → 正式 typed `503 SNAPSHOT_FAILED`（section-local 仍为 `200` + `is_partial` + `SOURCE_UNAVAILABLE`）、`RR-P1-03` `ProductRuntimeSnapshot.snapshot_at` 权威化（同一 Host snapshot 只发布一个 section 时刻）、`RR-P1-04` Health 段 checks 与 overall 同一次采集、`RR-P2-01` 未分类错误 → 脱敏 `500` correlation id。schema/migration/index/manifest/frozen design/`I02–I05`/Live = ZERO CHANGE；focused `19 passed`、RuntimeHost `51 passed`、完整 Backend regression `704 passed`（环境级 `PYTHONPATH=backend/src`）。
- Review history remains: initial review `FAIL`, Revision 01 review `FAIL`, Revision 02 final re-review `PASS`。
- `UI-RD01-I01-FIX-02 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`；RR2-P1-01 / RR2-P1-02 / RR2-P2-01 closed on branch `ui-rd01-i01-system-product-read` after `706 passed` full Backend regression. Independent Re-Review and Human Acceptance remain pending; `main` unchanged.

## PRE-01B-D2-CLAR-01 Reconciliation Acceptance

- `PRE-01B-D2-CLAR-01 = ACCEPTED / COMPLETE`；Human Acceptance = `CONFIRMED — 2026-09-17`；Independent Re-Review = `PASS`；Human-Accepted reviewed candidate = `bdf691bf52bbb0706f497b9d1920349588c7c0b4`，Final Fix = `PRE-01B-D2-CLAR-01-FIX-04`，P0/P1/P2/P3 = `NONE`。
- `PRE-01B-D2 = ACCEPTED / COMPLETE — AS AMENDED`；`PRE-01B-I2 = NOT RESUMED / NOT ACTIVATED`。Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Gate A/B/C = `NOT ACTIVATED / NOT PASSED`；Live = `NOT AUTHORIZED`。

## UI-RD01-I02 Requirement Persistence Result

- 任务：`UI-RD01-I02-REQ-01-PERSIST`｜`UI-RD01-I02｜需求冻结` → `DOCUMENT PERSISTENCE + STATE SYNC ONLY`（**非** `UI-RD01-I02 implementation`、**非** I02-A coding、**非** I02-B coding、**非** Product endpoint implementation、**非** schema change、**非** runtime change）。
- 状态：`UI-RD01-I02-REQ-01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`；formal task_state 仍 = `IMPLEMENTING`（Independent Review **尚未**开始；`REVIEW` / `ACCEPTED` 均未发生）。Artifact = `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`；Artifact status = `CANDIDATE / PENDING INDEPENDENT REVIEW`（**未** 声明 `ACCEPTED` / `FROZEN`）。
- Human Content Confirmation = `CONFIRMED — 2026-09-19`；Implementation Authorization = `NOT GRANTED`；Protocol Baseline = `v1.4.0 / ACCEPTED`（协议仓 main = `c6023356a02b23866d805c30f9fed08a0fabdfce`）；Repository Baseline at Requirement Confirmation = `08b6c5d6eebb5339756378ace80cb97d504ee25d`；Parent Design = `UI-RD01 = ACCEPTED / FROZEN — AS AMENDED BY UI-V1-D01-AMEND-01`。
- Task Base / remote `main` before work = `08b6c5d6eebb5339756378ace80cb97d504ee25d` = 任务卡期望值 ⇒ **无** baseline drift，**未** reset / rebase；branch = `design/ui-rd01-i02-requirements`（单 parent = Task Base），**未** merge `main`。
- `UI-RD01-I02 implementation = NOT STARTED / NOT AUTHORIZED`；执行拆分 = `I02-A｜市场扫描读取`（`GET /api/v1/product/market-scanner`）→ `I02-B｜机会追踪读取`（`GET /api/v1/product/opportunities`、`GET /api/v1/product/opportunities/{opportunity_id}`）；`I02-A` = `NOT STARTED`；`I02-B` = `NOT STARTED`。
- `CR-03`（Current Canonical Evidence vs Decision-Bound Evidence，于 I02-B 实现开始时才成为 `ACTIVE IMPLEMENTATION REQUIREMENT`）与 `CR-05`（`NOT_REACHED` vs `NOT_YET_DUE`）为**未来** I02-B 实现要求；本 persistence 任务**未实现**任何 CR-03 / CR-05 代码；`Schema = ZERO CHANGE` / `Migration = ZERO CHANGE` / `Index = ZERO CHANGE`。
- `I03`（`TradingAuditRead`）/ `I04`（`EdgeAggregateRead`）/ `I05`（Overall Product Read Acceptance）= **不变**，维持 `NOT STARTED / NOT AUTHORIZED`；`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Gate A/B/C = `NOT ACTIVATED` / `NOT PASSED`；Live = `NOT AUTHORIZED`；Live Trading = `DISABLED`。
- 本批为 docs/state-only：`Production Code = ZERO CHANGE` / `Backend Code = ZERO CHANGE` / `Backend Tests = ZERO CHANGE` / `Frontend Code = ZERO CHANGE` / `frontend/src/api/generated.ts = ZERO CHANGE` / `Schema = ZERO CHANGE` / `Migration = ZERO CHANGE` / `Index = ZERO CHANGE` / `Package Manifests = ZERO CHANGE` / `PRODUCT_REQUIREMENTS.md = ZERO CHANGE` / `DECISIONS.md = ZERO CHANGE`（任务卡明确列为 `ZERO CHANGE`）/ frozen UI-RD01 artifact = `ZERO CHANGE` / Post-Freeze Amendment artifact = `ZERO CHANGE` / `RuntimeHost` = `ZERO CHANGE` / `ProductReadContext` = `ZERO CHANGE`。
- 无实现面变更 ⇒ `ruff` / `pytest` / `frontend typecheck` / `frontend tests` / `frontend build` = `NOT REQUIRED / NOT RUN`（**不**据此声称任何运行时行为已验证）。
- 详见 `dev_log/2026-09-19-ui-rd01-i02-requirements.md`。

## UI-RD01-I02 Requirement Persistence — Independent Review R1（Timing Evidence Fix）

- 本段取代上文「UI-RD01-I02 Requirement Persistence Result」中 `IMPLEMENTED / READY FOR INDEPENDENT REVIEW` 的当前状态含义（该批已进入 Independent Review 并被判定 `FAIL — R1 REQUIRED`）。
- Independent Review（针对 `UI-RD01-I02-REQ-01-PERSIST`，reviewed candidate = `256bb0052be53f16177ee69b43068c56763a5a90`）= `FAIL — R1 REQUIRED`。
- Blocking finding = `I02REQ-RR-P1-01`（Severity `P1 / BLOCKING FORMAL FREEZE`；Finding Type = `Global Protocol v1.4.0 Execution Timing Evidence`）。
- Requirement 语义独立复审 = `NO SEMANTIC BLOCKER FOUND`（未发现语义 blocker）；blocker 仅为 **timing evidence**。
- Formal Human Freeze = `BLOCKED`（pending R1 / Independent Re-Review）。
- Requirement artifact = `ZERO CHANGE`：`docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md` 的 blob 在父候选 `256bb00` 与 R1 commit 上均为 `f3bec0140870fb25b0f536eeb7617677b20f5dd7`。
- Requirement artifact status 维持 `CANDIDATE / PENDING INDEPENDENT REVIEW`；Implementation Authorization = `NOT GRANTED`；`UI-RD01-I02 = NOT STARTED / NOT AUTHORIZED`；`I02-A = NOT STARTED`；`I02-B = NOT STARTED`。
- 时间证据更正：原批记录的 `Completed At = 2026-09-19T01:18:01+08:00` 为 **INVALID AS FINAL TASK TIMING / SUPERSEDED BY R1**（该读数早于 commit `2026-09-19T01:18:24+08:00`、push 与远端复读 ⇒ 不满足 Global Protocol v1.4.0 §41.1 的 final verification + result preparation 边界）；原批 `Estimate Delta = -00:02:51 vs lower bound` 另有算术错误（正确值应为 `-00:02:52`）。原批最终完成时点不可可靠恢复 ⇒ `Original Attempt Completed At = NOT AVAILABLE` / `Run Duration = NOT VERIFIED` / `Estimate Delta = NOT VERIFIED`（**未** 伪造任何时间戳）。
- Task = `UI-RD01-I02-REQ-01-PERSIST-R1`；状态 = `IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`；formal task_state = `IMPLEMENTING`；branch = `design/ui-rd01-i02-requirements`（**未** merge `main`、**未** reset / rebase / squash / force push）。
- 本 R1 为 docs/state-only：`Production Code` / `Backend Code` / `Backend Tests` / `Frontend Code` / `frontend/src/api/generated.ts` / `Schema` / `Migration` / `Index` / `Package Manifests` / `DECISIONS.md` / `PRODUCT_REQUIREMENTS.md` / frozen UI-RD01 artifact / Post-Freeze Amendment artifact / `RuntimeHost` / `ProductReadContext` / Product DTO / Product router = 全部 `ZERO CHANGE`；授权改动仅 3 个路径：`dev_log/2026-09-19-ui-rd01-i02-requirements.md`、`PROJECT_STATE.md`、`AI_CONTEXT.md`。
- 无实现面变更 ⇒ `ruff` / `pytest` / frontend typecheck / frontend tests / frontend build = `NOT REQUIRED / NOT RUN`（**不** 据此声称任何运行时行为已验证）。
- 边界保持（未解锁）：`I02 implementation = NOT AUTHORIZED`；`I03`–`I05` = `NOT STARTED / NOT AUTHORIZED`；`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Gate A/B/C = `NOT ACTIVATED` / `NOT PASSED`；Live = `NOT AUTHORIZED`；Live Trading = `DISABLED`。
- 详见 `dev_log/2026-09-19-ui-rd01-i02-requirements.md`「UI-RD01-I02-REQ-01-PERSIST-R1｜Independent Review Timing Evidence Fix」。

## UI-RD01-I02 Requirement Final Freeze Result

- 任务：`UI-RD01-I02-REQ-01-FINAL-FREEZE`｜`UI-RD01-I02｜需求冻结·R1` → Final Acceptance / Human Freeze Closeout + `FAST-FORWARD ONLY` 集成（**非** I02 implementation、**非** I02-A coding、**非** I02-B coding、**非** Product endpoint implementation、**非** schema change、**非** runtime change）。
- 最终状态：`UI-RD01-I02-REQ-01 = ACCEPTED / FROZEN / REPOSITORY-INTEGRATED`；Human Freeze = `CONFIRMED — 2026-09-19`；Independent Re-Review = `PASS — READY FOR HUMAN FREEZE`；Human-Frozen Reviewed Candidate = `b91d635de04c7444257fcc17069f418e3d3919e7`；Finding `I02REQ-RR-P1-01 = CLOSED / PASS`；Acceptance Closeout = `COMPLETE`。
- Artifact = `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md`，final status = `ACCEPTED / FROZEN`。相对 reviewed candidate，**仅** Artifact Status（acceptance / lifecycle metadata）变更；59 个编号章节**语义零变更**；reviewed blob = `f3bec0140870fb25b0f536eeb7617677b20f5dd7`。
- 前序（历史，保留不改写）：`UI-RD01-I02-REQ-01-PERSIST` = `256bb0052be53f16177ee69b43068c56763a5a90`（`IMPLEMENTED / READY FOR INDEPENDENT REVIEW`）→ Independent Review = `FAIL — R1 REQUIRED`（blocking finding = `I02REQ-RR-P1-01`：v1.4.0 execution-timing evidence；语义审 = `NO SEMANTIC BLOCKER FOUND`）→ `UI-RD01-I02-REQ-01-PERSIST-R1` = `b91d635de04c7444257fcc17069f418e3d3919e7`（仅更正 timing evidence，artifact blob 零变更）→ Independent Re-Review = `PASS — READY FOR HUMAN FREEZE`。
- Repository baseline：previous accepted main = `08b6c5d6eebb5339756378ace80cb97d504ee25d`；lineage = `08b6c5d6` → `256bb005` → `b91d635` → Acceptance Baseline（closeout branch tip）；reviewed candidate 分支 `design/ui-rd01-i02-requirements` 保持 `b91d635` **immutable**（closeout commit **未**追加其上）。
- `Implementation Authorization = NOT GRANTED BY THIS CLOSEOUT`；**本 Freeze 仅接受需求本身，不启动任何实现**：`UI-RD01-I02 implementation = NOT STARTED`；`I02-A` = `NOT STARTED`；`I02-B` = `NOT STARTED`；下一个**可**执行任务 = `UI-RD01-I02-A｜市场扫描读取`，但**必须**另开独立 Formal Task（本 closeout **未**创建、**未**执行、**未**启动）。
- `I03`（`TradingAuditRead`）/ `I04`（`EdgeAggregateRead`）/ `I05`（Overall Product Read Acceptance）= **不变**，维持 `NOT STARTED / NOT AUTHORIZED`。
- `CR-03`（Current Canonical Evidence vs Decision-Bound Evidence）与 `CR-05`（`NOT_REACHED` vs `NOT_YET_DUE`，六值 `TraceNodeState`）= 已在 `UI-V1-D01-AMEND-01` 接受并冻结的 shared/future contract；其 I02-B implementation obligation 仍**未实现**（I02-B `NOT STARTED`）；`CR-04` / `CR-06` = `NOT APPLICABLE YET`。
- 本批为 docs/state-only：`Production Code = ZERO CHANGE` / `Backend Code = ZERO CHANGE` / `Backend Tests = ZERO CHANGE` / `Frontend Code = ZERO CHANGE` / `frontend/src/api/generated.ts = ZERO CHANGE` / `Schema = ZERO CHANGE` / `Migration = ZERO CHANGE` / `Index = ZERO CHANGE` / `Package Manifests = ZERO CHANGE` / `PRODUCT_REQUIREMENTS.md = ZERO CHANGE` / `AGENTS.md = ZERO CHANGE` / frozen UI-RD01 artifact = `ZERO CHANGE` / Post-Freeze Amendment artifact = `ZERO CHANGE` / `RuntimeHost` = `ZERO CHANGE` / `ProductReadContext` = `ZERO CHANGE`；`DECISIONS.md` 仅新增一条 compact 摘要决策条目（**未**复制 Requirement 正文）。
- 无实现面变更 ⇒ `ruff` / `pytest` / frontend typecheck / frontend tests / frontend build = `NOT REQUIRED / NOT RUN`（**不**据此声称任何运行时行为已验证）。
- 边界保持（未解锁）：`PRE-01B-I2` = `NOT STARTED / NOT ACTIVATED`；Real AI = `NOT ACTIVATED`；live `G2→G3` = `NOT ACTIVE`；Gate A/B/C = `NOT ACTIVATED` / `NOT PASSED`；Live = `NOT AUTHORIZED`；Live Trading = `DISABLED`。
- 详见 `dev_log/2026-09-19-ui-rd01-i02-requirements-final-freeze.md`。
