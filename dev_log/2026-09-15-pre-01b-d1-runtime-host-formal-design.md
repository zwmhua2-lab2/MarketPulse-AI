# PRE-01B-D1｜Integrated Runtime Host Formal Design

## Task

- Type：Formal Design / Architecture Contract / docs-only。
- Goal：冻结 `MarketPulse Integrated Runtime Host V1` Candidate Architecture Contract，供后续
  Implementation AI 与 Independent Reviewer 使用。
- Status：`READY FOR INDEPENDENT REVIEW`（仅 Candidate；不是 Human Acceptance）。

## Preflight

- Global Protocol remote `main`：`e92fcc381baaf314a6c0f5687b1353ac6c06a748`。
- Protocol Version / Status：`1.0.0` / `ACCEPTED`；已读取 `AI_BOOTSTRAP.md`、
  `AI_DEVELOPMENT_PROTOCOL.md`、`PROJECT_REGISTRY.md`。
- Project remote/local `main` / `origin/main` / dispatch navigation SHA：均为
  `1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`。
- Baseline Drift：`NO`。
- 根 workspace 位于历史 branch 且 dirty；未触碰。已从 verified `main` 创建独立 clean worktree。
- Duplicate branch/worktree check：无已有 `design/pre-01b-d1-runtime-host-contract`。
- Five-part preflight：Task、Scope、Allowed Changes、Forbidden Changes、Acceptance Criteria 已按任务书确认。

说明：本地 `E:\Documents\ai-dev-protocol` 只有不完整 `.git` 元数据，不能作为事实源；未修复或修改。
通过 authenticated remote `ls-remote` + task-local temporary clone 只读验证 Global Protocol。该临时 clone
不属于任一 repository change。

## Evidence Input

- 读取 current accepted `AI_CONTEXT.md`、`PROJECT_STATE.md`、`PRODUCT_REQUIREMENTS.md`、
  `DECISIONS.md`、N01 overall closeout 与 PRE-01A-D1 Accepted Contract。
- 读取 PRE-01B S2W Research Verdict 和 Reference Research Evidence；仅作为 evidence input。
- 复核实际 source：FastAPI app/runtime/DB session、G2 Runtime/ScannerPipeline/Repository、G3
  queue/workflow/provider、G4 SafetyRuntime/Recovery/State/Control/Reconciliation、OKX provider 和 N01 harness
  wiring。
- 官方 spot verification：FastAPI lifespan、Starlette lifespan/state、AnyIO task group/readiness/cancellation。
- Research gaps blocking design：`NONE`。

## Design Decisions

- Host Placement：Option B；独立 `RuntimeHost` 由 FastAPI lifespan 创建/进入/退出。
- Concurrency：AnyIO TaskGroup / CancelScope 为唯一 Host structured-concurrency model。
- Process：single process、Uvicorn worker=1、reload off；PostgreSQL session advisory lock 防重复 Host。
- Supervisor：RuntimeHost 只管 in-process lifecycle；OS/service layer 管 process restart。WinSW = future task。
- Startup：DB/singleton → recovery-only live BBO warm-up → Recovery + startup reconciliation → bounded
  safety/G2 runtime → readiness conjunction。
- Protection：独立 per-instrument bounded non-lossy safety lanes；scanner overload 不阻塞 protection。
- G2→G3 live handoff：`DEFERRED`；Host Core V1 不构造 AI queue/consumer/provider。
- AI deadline：继承 absolute `decision_deadline_at` propagation/cancellation 语义；不决定新的业务数值。
- Periodic reconciliation：INCLUDED；detector-only，mismatch 使用 accepted safe-mode contract，不 repair。
- Shutdown：30s graceful + 5s shielded disposal reserve；producer-first stop、engine-last dispose。
- Memory P2：提供最小 telemetry hooks；`N01-7-R01-RR-P2-01` 保持 `REMAINS / NON-BLOCKING`。
- Unnecessary infrastructure introduced：`NONE`。

## Files Changed

1. `docs/design/PRE-01B/PRE-01B-D1-Integrated-Runtime-Host-Contract.md`
2. `dev_log/2026-09-15-pre-01b-d1-runtime-host-formal-design.md`

Production / Tests / Migration / Config / Accepted state docs changed：`NO`。

## Validation

- `git diff --check`：PASS（final rerun before commit）。
- changed-file scope check：PASS；exactly two approved paths。
- design required-section check：PASS；30/30 required headings present。
- forbidden-path diff check：PASS；no production/test/migration/config/state/global protocol/Memory/skill diff。
- status wording check：PASS；artifact is `CANDIDATE DESIGN / PENDING INDEPENDENT REVIEW`，not Accepted。
- current remote/local main re-read：PASS；仍为 `1e7eeb2...`。
- Candidate branch verification：PASS；`design/pre-01b-d1-runtime-host-contract`。
- Candidate SHA verification：由 final Git branch ref / Completion Report 记录；不把 commit 自身 SHA 写入其
  内容以避免 self-referential commit。
- Backend/full tests、Runtime、DB、OKX：`NOT RUN / NOT REQUIRED`；本批 docs-only 且任务明确禁止启动。

## Remaining Questions

- Implementation-blocking architecture unknowns：`NONE`。
- Non-blocking deferred：G2→G3 advisory handoff、Real AI Gate A timeout/cost/retry values、SE-02D、WinSW、
  periodic Forward Outcome scheduler、12h Host soak、Memory P2 closure verdict。
- 这些 deferred 项不属于本 Candidate 的实现授权。

## Candidate Branch / SHA

- Branch：`design/pre-01b-d1-runtime-host-contract`。
- Base SHA：`1e7eeb2ab91ec61efa1ddbd2662ab5a44d6ede2b`。
- Candidate SHA：见该 branch pushed tip 与 Completion Report（Git ref 是权威事实）。

## Result

`PRE-01B-D1 = READY FOR INDEPENDENT REVIEW`。

未修改/推送 `main`，未 Human Accept，未开始 Runtime Host Implementation、SE-02D 或 Real AI，未启动
Runtime / PostgreSQL mutation / OKX / soak。
