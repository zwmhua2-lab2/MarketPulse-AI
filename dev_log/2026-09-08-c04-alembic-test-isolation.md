# 2026-09-08 C04 — Alembic Replay Test Isolation Fix

## Requirement

C04 修复 G5 replay tests 在 process-level `DATABASE_URL` 已指向 isolated primary
时，disposable child replay database 的 Alembic migration 仍必须明确迁移到 child 的
portability 问题。

## Root Cause

`backend/alembic/env.py` 有意以 `DATABASE_URL` 优先于 Alembic Config 的
`sqlalchemy.url`。三份 G5 test helper 虽将 Config URL 设置为 child DB，但在
`command.upgrade()` 期间没有覆盖 process environment。因此 migration 落到 primary，
child 缺少 `alembic_version`，随后 Replay workspace validation 报
`UndefinedTableError`。

## Scope

- 仅修改 G5-2、G5-3、G5-4 tests 中现有 disposable replay DB migration invocation。
- 新增本 C04 dev_log。

## Out of Scope

- 未修改 `backend/alembic/env.py`、production migration behavior、migration revision、
  ReplayTradingRunner、ReplayWorkspaceGuard、G3/G4、execution、protection 或
  reconciliation。
- 未开始 FG-A Closeout、FG-B 或后续 Group。

## Implementation

每个 `_replay_database()` helper 在 `command.upgrade(config, "head")` 的最小作用域内：

1. 保存原 `DATABASE_URL`（含未设置状态）；
2. 暂时设为该 helper 创建的 child replay URL；
3. 执行 migration；
4. 在 `finally` 中精确恢复原值或移除变量。

因此正式 Alembic 的既有优先级没有变化，而 test migration invocation 与
`backend/alembic/env.py` 的现有 target selection 保持一致。

## Files Changed

- `backend/tests/test_group5_2_trading_replay.py`
- `backend/tests/test_group5_3_determinism.py`
- `backend/tests/test_group5_4_evaluation.py`
- `dev_log/2026-09-08-c04-alembic-test-isolation.md`

## Isolated DB Evidence

- 先以 process-level `DATABASE_URL=.../marketpulse` 复现：G5-2 standalone ordering
  test 在 child 查询 `alembic_version` 时失败，`UndefinedTableError`。
- 修复后同一 isolated primary：G5-2 `7 passed`、G5-3 `5 passed`、G5-4 `10 passed`
  （G5-4 为避免 terminal output truncation 串行分为 `3 + 4 + 3`）。
- TEMP-only child probe：`marketpulse_c04_probe_6a0870bf4fd0` migration 后
  `child_revision='20260905_0004'`；primary before/after 均为
  `accounts=3, trades=3, fills=4, revision='20260905_0004'`，`primary_unchanged=True`。
  Probe child 已 `DROP DATABASE`。

## Normal Regression

未设置 process-level `DATABASE_URL` 的普通环境：G5-2 `7 passed`、G5-3 `5 passed`、
G5-4 `10 passed`（`3 + 4 + 3`）。

## Full Backend Result

`PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -ra`：
`109 passed, 1 warning in 185.83s`。warning 为既有 FastAPI/Starlette TestClient
deprecation。

## Production Alembic Semantics

`backend/alembic/env.py` 未变更，故 ordinary process-level `DATABASE_URL` target
priority 为 `UNCHANGED BY CONSTRUCTION`。`git diff -- backend/alembic/env.py` 为空。
普通环境 `PYTHONPATH=src py -3.14 -m alembic current` 与 `heads` 均为
`20260905_0004 (head)`。

## Static Verification

- `py -3.14 -m ruff check backend/src backend/tests scripts`：PASS。
- `py -3.14 -m compileall -q backend/src backend/tests`：PASS。
- `git diff --check`：PASS（仅 Windows LF-to-CRLF warning，exit 0）。

## Self-Check

- Override 仅覆盖 `command.upgrade()`，并由 `finally` 恢复，异常路径不泄漏。
- Child URL 是 helper 刚创建的 disposable replay DB；primary URL 不作为 migration target。
- 无业务、schema、production Alembic 或 replay behavior 改动。

## Result

C04 FIX COMPLETE — WAITING ACCEPTANCE

## Remaining

独立 Acceptance Review 仍需要。FG-A Closeout 状态：
`STILL BLOCKED — WAITING C04 ACCEPTANCE`。

## Context For Next AI

从 `fix/c04-alembic-test-isolation` 审查三处 scoped environment restore 与 C04
evidence；不得将本 test infrastructure fix 视为 FG-A Closeout authorization。
