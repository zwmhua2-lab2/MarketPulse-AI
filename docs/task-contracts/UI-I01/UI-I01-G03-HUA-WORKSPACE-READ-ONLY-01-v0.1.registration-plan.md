# G03 正式登记/派发最小办理说明（候选；NOT DISPATCHABLE）

**候选任务** `UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01@v0.1`。不复用旧 HRR / Snapshot Qualification Task ID。User Human G03 只读 Scope 已批准，G04 A 原则已确认，不重复申请。

## 当前静态注册发现
- MarketPulse main `b959b3a472e4bcd7ca400ef285f2406aef8b6438`, tree `2b615322d4b666cbce567f256375766a41737ed8`。
- Workflow main `165b1cad65fdd4949a7cf283681006c68ff249e5`, tree `353bf882e0d7b7049ec239bb2deb483abdfcf161`。
- S3 main `b601ef7c3ddaed5dfc8f52d2d049e38ffbc6c4d5`；S3 非授权。
- 只读检视 MarketPulse main `docs/task-contracts/UI-RD01/` 当前项目本地 TaskContract / registration record 范例；没有检索到 G03 同任务身份的载体。
- 搜索 `g03` / `workspace` 分支结果为空，`ui-i01` 返回其他历史任务分支。此结论限定当前可见 GitHub/Library，不证明任意私有 Control Plane 里绝无相同任务。
- AWB Task Contract Creation Registry / Sequence 不是 MarketPulse 的已证明正式注册机关；**不得直接借用**。

## EXACT TARGET（只作为待批准的登记候选）
- Target repo: `zwmhua2-lab2/MarketPulse-AI`
- Proposed create-only branch: `ui-i01-g03-hua-workspace-read-only-01-register`
- Proposed **branch parent / registration base**: `b959b3a472e4bcd7ca400ef285f2406aef8b6438`
- Allowed mutation if and only if authorized: **create the above branch from exact parent; ADD only seven paths enumerated below; commit once; push the exact branch; remote readback; no modification of main**.
- On any main drift, branch-name conflict, already-registered duplicate, ownership conflict, unknown cost/attempt or missing control authorization: STOP. Do not rebase/reset/force.

## Exact seven candidate paths (must be reviewed against branch scope before any write)
1. `docs/task-contracts/UI-I01/UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01-v0.1.task-contract.json` — complete structured semantics
2. `docs/task-contracts/UI-I01/UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01-v0.1.verification-contract.json` — verification obligations and fail conditions
3. `docs/task-contracts/UI-I01/UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01-v0.1.verification-profile.json` — verification method / asset/role candidates
4. `docs/task-contracts/UI-I01/UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01-v0.1.execution-profile-candidate.json` — model/harness routing candidate only (not resolved profile)
5. `docs/task-contracts/UI-I01/UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01-v0.1.budget-ledger-candidate.json` — budget proposal with UNKNOWN consumption
6. `docs/task-contracts/UI-I01/UI-I01-G03-HUA-WORKSPACE-READ-ONLY-01-v0.1.registration-plan.md` — exact registration plan and authority gate
7. `dev_log/2026-10-12-ui-i01-g03-hua-workspace-read-only-01-registration-candidate.md` — candidate registration preparation dev_log (not registration receipt)

**NOT authorized**: Project `main`, Workflow repo, GitHub PR/merge, project `PROJECT_STATE.md`, Registry/Sequence, actual user Windows workspace, any old HRR operation.

## Required control-plane sequence (new Human authority distinct from already approved READ scope)
1. Control Plane checks no duplicate effective G03, resolves MarketPulse project-local registration authority and L2/parent floor. Confirm the proposed ID/version and exact paths and branch; check current refs and existing owners.
2. Human grants **one-shot branch creation + the exact seven file ADDs + one commit/push + readback** (not granted yet). No main integration. If registration requires main, stop and seek separately scoped exact WRITE_MAIN authorization *after reviewed candidate identity exists*.
3. Authorized registrar materializes verified source bytes on exact branch; records content SHA-256/blob/commit and branch parent. Any independent registration review dictated by applicable Workflow must complete; no self-approval.
4. Control Plane determines registration effectiveness / receipt, resolves an actual ResolvedExecutionProfile and binds final VC/VP, confirms attempt ledger and pending/duplicate guard. Candidate profile/ledger here cannot be marked effective by formatting.
5. Human grants task-specific **one read-only G03 formal dispatch + one attempt budget**, only after exact binding identity can be named. Scope approval from previous User message remains in force; do NOT repeat it.
6. Control Plane issues exact Dispatch ID and receipt and verified HUA-readable inputs; only then release a fully resolved S3 three-part execution card to HUA Codex Desktop. This candidate MUST NOT be pasted as an Executor card.

## Pending Human decision (one combined exact request)
- APPROVE or REJECT branch-only candidate materialization on the exact `MarketPulse-AI` repo/branch/7 paths/parent and one non-force commit+push, no main or other files.
- APPROVE or REJECT a **proposed budget ceiling** of one G03 read-only dispatch attempt, zero retries and zero external paid API budget, conditional on actual effective ledger, pending check, and separate formal Dispatch binding. Any formal dispatch authorization must cite effective Task ID, ResolvedProfile/VC/VP/ledger first; do not treat this contingent request as an already issued Dispatch.
- Source/read-only scope already APPROVED; G04 Owner Principle A CONFIRMED. If formal project-local registration cannot be branch-only, main write remains unapproved and exact review carrier SHA must be provided before such an authorization request.

Result Route: HUA Codex → A original window → MarketPulse-AI coordinator continuation 02 → dot (no automatic cross-window delivery claimed).
