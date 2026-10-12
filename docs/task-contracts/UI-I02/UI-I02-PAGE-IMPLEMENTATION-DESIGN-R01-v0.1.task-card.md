# Human Context｜UI-I02 独立设计审核任务卡候选

Human 已确定 **UI-I02 为当前优先调度工作项**，仅允许 C 线在 Designer／STRICT READ_ONLY 权限内完成展示型制卡。本文件**不是**执行指令，不含 Review Dispatch 或实施授权；原六组语义 JSON、原前端设计、十项 AC 与既有证据保持精确原字节不变。由于原 JSON 尚非 S3 三段式的完整可读 Review Task Card，故只新增本独立展示候选。

```text
C｜UI-I02 市场与机会｜独立设计审核｜v0.1

MARKETPULSE-AI | STRUCTURED REVIEW TASK CARD | DISPLAY CANDIDATE
Contract State: DRAFT / NOT_REGISTERED / NOT_DISPATCHABLE
Activity State: PREPARATION_ONLY / INDEPENDENT_REVIEW_NOT_STARTED
Authority: NON-AUTHORITATIVE PRESENTATION / NO FORMAL TASK CREATION
No execution by receipt of this file. This file is NOT a Review Dispatch Card.

==================================================
1. IDENTITY
==================================================
Human-facing Work Name: C｜UI-I02 市场与机会｜独立设计审核｜v0.1
Proposed Review Task ID: UI-I02-PAGE-IMPLEMENTATION-DESIGN-R01
Proposed Review Task Version: v0.1
Proposed Subject Page Task ID: UI-I02-PAGE-IMPLEMENTATION-01
Project: MarketPulse-AI
Product Repository: zwmhua2-lab2/MarketPulse-AI
Governance Repository: zwmhua2-lab2/ai-dev-workflow
Workline: C / UI-I02 / Frontend Market & Opportunity
Role (proposed future task): INDEPENDENT DESIGN REVIEWER; not current Designer
Current author: C Designer / READ_ONLY TASK CARD RENDERING
Task ID / Version Formal Assignment: NOT_BOUND / UNREGISTERED
Contract ID / Content Seal: UNASSIGNED / UNSEALED
Registry / Sequence: NOT_ASSIGNED / AWB REGISTRY NOT APPLICABLE AUTOMATICALLY
Review Subject Identity: existing exact-byte component set, indexed below;
  formal composite subject seal = NOT_ESTABLISHED
Current observed MarketPulse source main:
  b959b3a472e4bcd7ca400ef285f2406aef8b6438
Current observed MarketPulse source tree:
  2b615322d4b666cbce567f256375766a41737ed8
Future Review execution baseline: PENDING_CURRENTNESS_CHECK_AT_FORMAL_DISPATCH
Parent Design Lineage: UI-V1-D01, ACCEPTED / FROZEN; UI-V1-D01-AMEND-01
Parent Work Package / Contract: APPLICABILITY_UNRESOLVED (KERNEL-05: if applicable)
  If a formal Parent exists, future qualified Control must bind exact ID/version/content.
  If none applies, qualified Control must record an authorized NOT_APPLICABLE reason.
  DO NOT treat UI-V1-D01 Frozen Design as a registered Parent TaskContract.
  DO NOT inherit AWB L3 Parent / AWB Creation Registry / Sequence.
Frontend order in Frozen UI-V1-D01 §42:
  UI-F01 -> UI-RD01 -> UI-I01 -> UI-I02 -> UI-I03 -> UI-I04 -> UI-I05 -> UI-I06
  Sequencing only; does not authorize implementation or block current independent design prep.

==================================================
2. GOVERNANCE
==================================================
Workflow Authority: AI Development Workflow / SELF_HOSTED
Governance Version: 0.1.0
Rule Pack Version: 0.1.0
Manifest: fd00-rule-manifest/0.1.0
Observed Workflow main: 165b1cad65fdd4949a7cf283681006c68ff249e5
Observed Workflow PROJECT_STATE Git blob:
  0ed18f174ee0149eb97bc196caa5b3c995c66f30
Mandatory rules: current Bootstrap / Manifest / 6 REQUIRED_ACTIVE / PROJECT_STATE
Historical protocol: REFERENCE ONLY / NO IMPLICIT FALLBACK
S3 presentation: GLOBAL-TASKCARD-RULES-REVISION-01 v0.1 + Workspace increment;
  non-authoritative display preference, not second governance framework.
Source authority for UI: UI-V1-D01 / AMEND-01 / UI-RD01 frozen designs;
  backend I02 accepted read surfaces are an input, not acceptance of this UI page.
Frozen Truth identities: individual Git blobs PINNED; new task-specific
  Frozen Truth bundle/manifest identity = NOT_BOUND / NO TASK-SPECIFIC FREEZE.
Proposed Risk Tier: L2 (DESIGN PROPOSAL; risk uncertainty defaults >= L2).
Proposed Risk Tags: PUBLIC_CONTRACT / AUTHORIZATION / STATE_MACHINE
Protected subsystem proposal: PAGE_READ_PRESENTATION_AND_AUTH_SESSION_BOUNDARY
Protected subsystem classification: NOT_FORMALLY_APPROVED
Parent Tier Floor: UNKNOWN / PARENT_APPLICABILITY_UNRESOLVED
Risk authority: NOT_GRANTED; cannot silently lower any applicable parent floor.
Human priority decision: UI-I02 FIRST FOR SCHEDULING / DESIGN_ONLY
H01: UI-I01 unresolved DOES NOT BLOCK I02 independent DESIGN preparation;
  future implementation sequence remains frozen.
G04: router.tsx + router.test.tsx future ONE unique Executor / principle HUMAN_CONFIRMED;
  executor identity / task path grant / exclusive write window = NOT_OPEN.
Independence: reviewer MUST NOT be C Designer or future code Executor;
  Reviewer adjudication is separate from Official Verification and Acceptance.
Review Dispatch Authorization: NOT_GRANTED / NOT_DISPATCHED
Human Gate / Freeze / Implementation Authorization: NOT_PERFORMED / NOT_GRANTED

==================================================
3. BOUNDARY / REVIEW OBJECTIVE (FUTURE AUTHORIZED REVIEW ONLY)
==================================================
Objective: independent design evaluation of the EXISTING UI-I02 Market & Opportunity
  page implementation draft against accepted UI and API contracts and existing AC mapping.
In scope only after valid independent Review task dispatch:
  A. Verify exact source identities / current Frozen Truth / Parent decision.
  B. Check original C-I02-01..10 against frozen design, accepted DTO and M01..M10.
  C. Evaluate source/absence/provenance, range/cursor, two-branch trace,
     causal/temporal semantics, errors/session fencing, no inferred trading action.
  D. Check G04 shared router + router test single future Executor constraint.
  E. Produce findings (blocking/nonblocking), unresolved obligations, exact evidence.
Out of scope / forbidden now AND during read-only review:
  - Rewrite original Implementation draft, 10 AC or M01..M10; redesign UI architecture.
  - Edit frontend, backend, router, router.test, tests, docs or any repo ref.
  - Run tests, browser automation, DB, Provider, benchmark, paid API or migrations.
  - Formal registration, ledger/budget authorization, Task ID assignment, Review dispatch.
  - Requirement Freeze, Human Gate decision, implementation, official verification,
    code integration, WRITE_MAIN, production API/schema or Acceptance.
  - Create a new AWB/MarketPulse Registry, allocate Sequence or expand scope.
  - Reopen accepted backend UI-RD01-I02 review without formal reason/authorization.
Allowed product/governance repository writes: NONE.
Stop if required authority, baseline, source bytes, parent/floor, independent reviewer,
  budget, data policy or allowed input access is missing, stale, inconsistent or truncated.

==================================================
4. EXECUTION / SOURCE INPUTS / ATTACHMENTS
==================================================
Mode for any future authorized Review: STRICT_READ_ONLY / FRESH_CONTEXT.
Dispatch NOW: PROHIBITED; these steps are a candidate verification specification.
Review Profile Identity / Version: NOT_BOUND / NOT_CREATED
Actual Reviewer identity and independence proof: NOT_BOUND / NOT_VERIFIED
Reviewer count: ONE independent external reviewer PROPOSAL ONLY;
  final profile may require otherwise; Independence != Heterogeneity.
Provider: UNBOUND
Model: UNBOUND / NO FORMAL RECOMMENDATION
Reasoning: UNBOUND
Harness: UNBOUND
Routing tier: NOT_APPLICABLE_TO_EXTERNAL_REVIEWER (human-facing label only)
Resolved Review/Execution Profile: NOT_RESOLVED
Routing authority note: EMRP-1.1 active for applicable Executor routing,
  not an independent Reviewer Profile and not a preselected reviewer model.
Data policy: NO_SECRETS / NO_RAW_AI_PROVIDER_PAYLOAD / NO_EXTERNAL_PAID_API.
Tool permissions (after formal approval only): pinned Git read; exact Library read;
  NO MUTATING TOOL; reviewer output only at separately authorized destination.

Review Budget: PROPOSAL ONLY / NOT ALLOCATED / NOT SPENDABLE
  max_dispatch_attempts = 1 (proposal)
  max_fix_rounds = 1 (proposal)
  max_invalid_verification_runs = 0 (proposal)
  max_minor_amendments = 0 (proposal)
  external_billed_micro_USD = 0 (proposal; NOT historical measured spend)
  BudgetContract / Ledger ID: NOT_CREATED / NOT_BOUND
  consumed: UNKNOWN_UNREGISTERED; remaining: NOT_CALCULABLE
  pending/in-flight attempts: NOT_VERIFIED for future exact formal identity.
  No authorized capacity arises from any number above.

Exact Library inputs (Web C readable; future reviewer harness NOT VERIFIED):
  Review semantic JSON draft: C-UI-I02-Independent-Design-Review-Task-DRAFT-v0.1.json | Library libfile_dc61dade8cd881918200fbaa48aaabab | 7120 bytes | SHA-256 2e6c4e18cdaa511e87da1f389534b03f6459d230e88a378ced1214eb0e2ba265
  Detached exact review source index: C-I02-I03-Exact-Review-Subject-Index-v0.2.json | Library libfile_607285023d008191bfe5f5d8e388fa33 | 10063 bytes | SHA-256 55cf7a604a3c7619fa4c0c4b379525f84230dde12882e827688bf0b6543f4ef3
  Previous design-admission continuation: C-I02-I03-Design-Review-Continuation-Result-v0.2.md | Library libfile_a73e516c4b14819188c4b0552b4b914f | 10892 bytes | SHA-256 2bec884c43bdf2f53dda13c1f9602c44a1356bde10a5f38e24a482232e644c7d
  Latest coordinator authority intake: MarketPulse-C-I02-Priority-ReadOnly-Authority-Intake-20261012-v0.1.md | Library libfile_b0e0d5cc51a08191ac2016fefcc8007d | 9761 bytes | SHA-256 999095a95d1533daee7ff5bfafc395518e10df6ada5a4cb57edb50f681f59de8
  Original 14-member source ZIP (transport; NOT formal exact bundle): MarketPulse-C-Design-Clarification-20261011-v0.1.zip | Library libfile_de72deedc55c8191999e5441de8c9088 | 65916 bytes | SHA-256 395c38c68321ab172aa92790b95cba45ac48752e5e77937db5fb2fab6415294a

Required original I02 members of the ORIGINAL ZIP; member identities do not
substitute ZIP identity or future formal review subject seal:
  Original UI-I02 Implementation design: originals-v0.1/UI-I02-Implementation-Contract-DRAFT.md | 13881 bytes | SHA-256 7094dee0ae25c0e3a99e954358ce08c89c1cab11e85075ff0d08e4f1f15ebe40 | container: libfile_de72deedc55c8191999e5441de8c9088
  10 AC source-to-test map: I02-Source-AC-Test-Traceability.md | 5018 bytes | SHA-256 227e60bb897ef52c24d47ebd2c43299e40f04e8a5fa5ae8a422edb67fc648391 | container: libfile_de72deedc55c8191999e5441de8c9088
  M01-M10 and future verification plan: Acceptance-Test-Design.md | 5229 bytes | SHA-256 0d122b18b5883775b3d93124a48afb8990aa178fe05622beb802875bb3bac872 | container: libfile_de72deedc55c8191999e5441de8c9088
  Existing display-only delta: UI-I02-Implementation-Contract-DRAFT-v0.1.1-display.md | 15724 bytes | SHA-256 f39959b7400ab2de0cdd6eba2edefe6e3987e6c4fa792f82f1f240377d762cef | container: libfile_de72deedc55c8191999e5441de8c9088
Prior I02 formalization delta, separately preserved:
  C-UI-I02-Formal-Task-Preparation-Delta-v0.1.md
  Library libfile_141671f14e5c819190a1787d059f16db
  13393 bytes | SHA-256 e8b65fc16665ff087b2ff0129f58b0384c298c282dc5e080b50f3d34fb60a7cb

Pinned MarketPulse frozen/read sources at current observed main (Git blob = SHA-1):
  Frozen UI-V1 Design: docs/design/UI-V1/UI-V1-D01-MarketPulse-UI-V1-Formal-Design.md | Git blob SHA-1 62173554e3824418326a9f782e1f9c7e971ca25a
  Accepted Amendment CR-01..06: docs/design/UI-V1/UI-V1-D01-AMEND-01-Post-Freeze-Amendment.md | Git blob SHA-1 b3af9d9aa0ee4ac7152216761a57974217935a88
  Frozen Product Read Design: docs/design/UI-RD01/UI-RD01-Product-Read-API-Formal-Design.md | Git blob SHA-1 f98dd6e92695aa9e56237d1c7fa6000b7368aff5
  Frozen backend I02 requirement: docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md | Git blob SHA-1 1fe9959d7476ef1d424276751e2a5e160088df61
  Current generated API types: frontend/src/api/generated.ts | Git blob SHA-1 50640c81352843c2e5acb88db5f23e447d0ad8bb
  Accepted I02 backend closeout: dev_log/2026-09-20-ui-rd01-i02-final-acceptance-closeout.md | Git blob SHA-1 902b604a013e6125ad59206d935cef46538e67d1
  5 product routes: frontend/src/app/routes.ts | Git blob SHA-1 6f0a2aea89efff5f620f6c9d041a8972e67b044e
  Shared router: frontend/src/app/router.tsx | Git blob SHA-1 2b031a9cf9d18fb814fe994b2017547dfbe78529
  Shared router tests: frontend/src/app/router.test.tsx | Git blob SHA-1 9ddc9cf8eb977ff6e35d0c0cea5d60b903a3eb24
Git exact commit for the above: b959b3a472e4bcd7ca400ef285f2406aef8b6438
Do not confuse Git blob SHA-1 with SHA-256 file content digests.

Input Transfer Preference: SEPARATE_FILES / BUNDLE_REQUIRED_NO unless later
  formal contract specifically binds an EXACT_BUNDLE. Existing ZIP is reusable
  unchanged; do not repackage, substitute, or re-hash it merely for rendering.
Current access: ALL listed Library objects accessible to C Web;
  local Reviewer/HUA/Codex/WorkBuddy file paths = NOT_VERIFIED.
Future reviewer must record real readable local absolute paths or authorized
  Library/connector access and bytes/hashes; do not invent E:\ drive paths.
Fresh Context for future reviewer must independently read current Bootstrap,
  Manifest, 6 active Rules, PROJECT_STATE and actual formal Review Contract,
  exact Frozen and design inputs. This C-window check is NOT reviewer Fresh Context.

==================================================
5. VERIFICATION / ACCEPTANCE / STOP CONDITIONS
==================================================
Original UI-I02 Implementation ACs below are copied VERBATIM from the original
  DRAFT for reference; original bytes and authority remain in the original ZIP.
  These are design-review subject obligations, NOT already-passed checks.

Original AC entries (C-I02-01 .. C-I02-10):
| C-I02-01 | 正式路径 `/market` 渲染真实三栏，只有五个顶层路由，无 AI 页；不误改其他页面 |
| C-I02-02 | 针对 backend typed fixtures 的 range/default/custom/timezone/cursor/边界 `detected_at` vs `event_time` 正确；同一时间 tie 不丢不重；翻页不重设 effective window |
| C-I02-03 | 读面/运行可用性/ProjectionState 三维分别呈现；Unavailable≠0/[]，Stale 有文本/age，Partial保留健康 section |
| C-I02-04 | 非 Forward 场景不伪装为 live；Replay 只有显式选择；scanner event 无 BUY/SELL badge，新 family 不出现 |
| C-I02-05 | Opportunity detail 顺序/双分支准确；Outcome 与 Economic Result 明确分离；`5m` 不是跨 horizon 均值 |
| C-I02-06 | current canonical rev2 / Decision bound rev1 的 exact identity 同时可见；不可证明时留空状态；不向前端泄漏原始 Evidence/AI payload |
| C-I02-07 | NOT_YET_DUE、NOT_REACHED、NOT_OCCURRED、NO_PROVABLE_RECORD、CAPABILITY_NOT_INTEGRATED 互异；浏览器时钟变化不改变后端事实 |
| C-I02-08 | `401` current vs stale session generation 有真实跨会话测试；422/503/500 与 network error 分类不会误显示 Empty 或登出新 session |
| C-I02-09 | 1440×900、1280×720 布局、中文读屏文本、键盘和非颜色表达；无 mutation 控件 |
| C-I02-10 | Frontend typecheck/lint/必要测试/build/API drift 与本任务影响面回归均合格；独立 Review/Official Verification 不使用作者 self-check 当结论 |

Future test matrix: M01..M10, exact original member I02-Source-AC-Test-Traceability.md.
  M01: five routes, /market three-column/six sections, no top-level AI/no mutation.
  M02: range/UTC/effective window/cursor tie & stale-filter rejection.
  M03: distinct LOADING/EMPTY/STALE/UNAVAILABLE/CNI & section-local partial.
  M04: Forward vs explicit Replay, scanner source, no BUY/SELL fabrication.
  M05: two-branch trace, four horizons, no invented economic PnL.
  M06: current canonical and decision-bound evidence rev identity separation.
  M07: six trace states, backend as_of, not browser-time recomputation.
  M08: current/old-generation 401 and typed 422/503/500/network failures.
  M09: 1440x900 & 1280x720 browser, a11y, keyboard, local/UTC time labels.
  M10: existing typecheck/test:run/build/check:api-drift and independent evidence.
  C-I02-10 original mentions lint. Current frontend/package.json does NOT
  expose npm run lint; this is an explicit TEST-COMMAND GAP, not an AC rewrite.
  A later authorized VC/VP must establish actual lint tool/command or report
  NOT_VERIFIABLE; neither this card nor current Designer installs/runs anything.

Design Review checks after authorized dispatch: complete Frozen-to-AC matrix,
  negative-case coverage, provenance/security, exact scope/paths, independence,
  verified reviewer input access, blocking/non-blocking findings.
Verification Profile / Assets / content seal: NOT_BOUND / NOT_EXECUTED.
Current test result, Browser evidence, review verdict: NONE / NOT_EXECUTED.
Expected Review evidence (if later authorized): exact subject identity and
  hash checks, independent finding matrix, rule/context read coverage, reviewer
  actual model/harness/profile, current baseline, blocking disposition, no mutation,
  unknown/unverifiable obligations, required human gate requests.
Acceptance Boundary: Design Review PASS (if later obtained) is NOT Human Freeze,
  NOT Implementation Authorization, NOT Official Verification, NOT product Acceptance.
Stop conditions (proposed):
  RULE_LOAD_PARTIAL_OR_STALE; REQUIRED_INPUT_UNREADABLE_OR_HASH_MISMATCH;
  MISSING_OR_CONFLICTING_AUTHORIZATION; PARENT_FLOOR_CONFLICT;
  UNSUPPORTED_PAID_EXTERNAL_ACTION; ROLE_INDEPENDENCE_UNPROVEN;
  REVIEW_SCOPE_EXPANSION; MAIN_DRIFT; REVIEW_PROFILE_UNRESOLVED.

==================================================
WORKSPACE / FILESYSTEM SCOPE (NON-AUTHORITATIVE NAVIGATION)
==================================================
Recommended Workspace Root: NOT_RESOLVED (future Reviewer harness not selected)
Task Working Directory: NOT_APPLICABLE until actual independent Review dispatch
Canonical Repository: zwmhua2-lab2/MarketPulse-AI (GitHub pinned, not a local path)
Allowed Read Scope: only current authorized repository and exact review inputs
Allowed Write Scope: NONE in product/governance repositories
Evidence Output: NOT_ASSIGNED / requires formal Review authorization
Review Input Scope: NOT_ASSIGNED / actual local readability NOT_VERIFIED
Forbidden / Avoid: other projects, legacy/noncanonical roots, backend mutation,
  ANY repo ref mutation, unapproved file writes, inherited cross-project profiles.
Legacy Root Use: NO
Scope Rule: Workspace visibility does NOT equal Authorization.
  Need wider read/write scope? STOP / REPORT / REQUEST AUTHORIZATION.

==================================================
6. RESULT / RESPONSE / NEXT LEGAL GATE
==================================================
Required Structured Result from any FUTURE AUTHORIZED Reviewer:
  Result; ExactTaskID/Version/Contract; Currentness; ReadCoverage;
  ExactReviewedSubject; AC01..AC10 mapping/verdict; ReviewProfile;
  Reviewer identity and independence; ChangeScope (expect NONE);
  Blocking/NonBlocking/Unverifiable; Budget attempt & ledger receipt;
  Required Human Gates; Evidence references; Remaining; Stop Condition.
Current factual result: CARD_RENDERING_CANDIDATE_ONLY
Candidate page implementation code: NONE
Independent Design Review: NOT_PERFORMED / NOT_DISPATCHED
Official Verification: NOT_PERFORMED
Human Freeze / Acceptance: NOT_ESTABLISHED
Repository/Registry mutation: NONE BY THIS CANDIDATE
Result Return Target (proposed): MarketPulse-AI｜C｜后续 UI 设计;
  C to MarketPulse-AI 主协调／总控 under actual authorization.
File delivery: if a future formal Review executes, only use its actual approved
  evidence root and current adopted delivery instructions; refer to
  ai-dev-artifact-bridge/docs/FILE-DELIVERY-GUIDE.md, historical adoption entry
  665c1d5e8ede62404a11a22a91756d43ffc5baba; guide itself does not grant
  write/transport authorization. Record bytes/SHA-256 and receiver read receipt.
Next legal gate: qualified MarketPulse task/control authority must establish
  exact parent applicability + formal ID/version/contract identity + frozen bundle
  and risk floor, then separate budget/ledger, Review Profile/Reviewer, actual
  input readability and explicit Design Review Dispatch Authorization.
  AWB Registry/Sequence does not automatically apply to MarketPulse.
  H01 does not block independent design; G04 principle already Human confirmed.
NO NEW SEQUENCE / NO REVIEW EXECUTION / NO CODE / NO REPOSITORY WRITE.

==================================================
END OF CODEX TASK CARD
==================================================
```

## Human Execution Summary

| 执行项 | 本候选配置／状态 |
|---|---|
| 当前窗口 | C｜MarketPulse-AI 后续 UI 设计，生成展示候选 |
| 建议窗口名 | C｜UI-I02 市场与机会｜独立设计审核｜v0.1（未来候选，未派发） |
| 模型 | 未绑定；不从原 Designer 或 Executor 配置继承 |
| 推理档位 | 待正式 Review Profile 解析 |
| 执行工具 | 未选定；目标 Review Harness 可读性未验证 |
| 路由等级 | 不适用（External Reviewer）；实际 Profile 待定 |
| 角色 | 未来独立 Reviewer（待指派）；本轮为 Designer 文档展示 |
| Fresh Context | 未来 Reviewer 须自行完成；本轮不代替 |
| 附件 | 原 ZIP + 独立文件保留精确身份；未来执行端可达性未验证 |
| 传递方式 | 默认独立原件，既有 ZIP 仅复用为非权威 transport 包 |
| Workspace | 未解析；不虚构 Windows 路径 |
| 任务完成后反馈到 | MarketPulse-AI C 线，再依适用授权回总控 |

**下一步（非执行指令）：**仅由合格控制方闭合真实 Task 身份、Parent applicability、Risk/Frozen binding、Review Budget/Ledger、Review Profile 和正式 Dispatch；本文件不能自行跨越这些缺口。
