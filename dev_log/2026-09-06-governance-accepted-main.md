# 2026-09-06 Governance — Accepted Main Self-Reference Normalization

## Task

- 类型：纯 Governance / Context 修正（G5 Governance Fix）。
- Scope：修正 `AI_CONTEXT.md` / `PROJECT_STATE.md` 中「当前 Accepted Main SHA 硬编码」产生的 self-reference 问题。
- 禁止：G5-2、Replay trading code、G3/G4 修改、schema、AI、Execution、Position、Live、其它架构重构。

## Baseline（preflight 实测）

- `git branch --show-current`：`main`
- `git rev-parse HEAD` / `git rev-parse main`：`8d78d1d7e284e35d2f3487cbbc8d1f93468d8008`
- `git ls-remote origin refs/heads/main`：`8d78d1d7e284e35d2f3487cbbc8d1f93468d8008`（与本地 main 一致）
- `git status --short`：仅 `?? .workbuddy/`（保留未触碰）

## Change

- 正式废除「状态文档把当前 HEAD / main SHA 当作静态自引用字段」。
- Canonical Rule：Current Accepted Main 唯一可信来源 = `git rev-parse main` / `git rev-parse origin/main`（或对应 remote truth），执行任务必须在 preflight 实际读取。
- `AI_CONTEXT.md`：`Accepted Main SHA` 行 → `Accepted Main Source`（Git `main` / `origin/main` + preflight 实时读取指令）；G5-1 implementation acceptance basis `34da62a0...` 保留。
- `PROJECT_STATE.md`：GitHub Repository 段与 Branch / Source 段的静态 Accepted Main SHA 字段改为动态 Accepted Main Source；Branch / Source 区分 `Current Accepted Branch: main` 与 `Last Accepted Group Branch: g5-deterministic-replay-foundation`（历史证据）；记录 `G5-1 Implementation Acceptance Basis`。
- `AGENTS.md`：CIP-02 极小补充——Accepted Main SHA 必须从 Git 实时读取，文档中的 SHA 只是 Task Base / historical evidence，不覆盖实际 Git ref。
- 历史 dev_log（G5-0 / G5-1）中的 SHA 记录属于历史证据，未改写。

## Result

- G5-1 Acceptance 没有变化（`ACCEPTED`）。
- `8d78d1d7e284e35d2f3487cbbc8d1f93468d8008` 是修正开始前的 accepted main truth。
- 本次 governance commit 完成后，新的 main SHA 由 Git truth 决定，不再要求文档自引用当前 commit SHA。
- 状态保持：G5-1 = `ACCEPTED`；G5-2 = `NOT STARTED`；next state = `READY FOR G5-2 DESIGN`。
