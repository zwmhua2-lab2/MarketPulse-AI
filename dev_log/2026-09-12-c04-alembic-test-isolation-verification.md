# 2026-09-12 C04 — Alembic Replay Test Isolation（独立验证记录）

## 0. 本窗口前置发现（必须先读）

本窗口开工时，目标分支 `fix/c04-alembic-test-isolation` **已存在且已推送**：

- 远端 / 本地 tip = `d574e242f3aa7c26658ed6cc780fd8f744dbf503`
  （`test(g5): isolate child alembic migrations`，2026-09-08）
- 该提交已 **恰好基于任务要求的 Task Base** `a9c2cd64bea0c6cc43b1ef8ad890e4db5353b801`，
  且改动集合 = 任务 Scope 允许的三个 G5 测试文件 + `dev_log/2026-09-08-c04-alembic-test-isolation.md`。

即：**C04 的代码修复增量已存在于该分支，非本窗口编写**。
按 CIP-07（Worker 自我报告不是证据）与 CIP-08（Reviewer 隔离），本窗口未采信既有 devlog 的
结论，而是**独立重跑全部 Acceptance Criteria 与回归**，并以本文件记录本窗口的自有证据。

同理，任务书写明的 `Accepted Main = 36401b26478a9892dc2ca0490f5c21ff24663636` 与仓库实时
真值不一致（CIP-02）：实际 `main` = `af81414160248c97f59a63b31fe615ea8ae14bbe`，
`36401b26` 是 `g5-replay-evaluation` 分支 tip，且为 `a9c2cd64` 的祖先。
本 Fix 的 Base 严格按任务 §1 使用 `a9c2cd64`，未受影响。

## Requirement

G5 replay tests 在 process-level `DATABASE_URL` 已指向 isolated primary 时，
disposable child replay database 的 Alembic migration 仍必须明确迁移到 **child DB**，
使 isolated PostgreSQL acceptance environment 可运行。

## Root Cause（本窗口实证，非引用）

`backend/alembic/env.py:12`：

```python
database_url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
```

process-level `DATABASE_URL` 优先于 Alembic Config 的 `sqlalchemy.url`。
三个 G5 helper 只做 `config.set_main_option("sqlalchemy.url", child_url)`，
未覆盖 process environment ⇒ migration 落到 `DATABASE_URL` 指定的库（即 isolated primary），
child replay DB 无 `alembic_version`，随后 workspace validation 报
`UndefinedTableError: relation "alembic_version" does not exist`。

**修复前复现（本窗口实跑）**：把 `backend/tests/test_group5_2_trading_replay.py` 还原为 base
`a9c2cd64` 内容，在 `DATABASE_URL=<isolated primary>` 下运行 standalone 用例
`test_reachable_g2_g3_g4_frame_ordering_without_bookticker_setup`：

```
1 failed in 2.13s
E   asyncpg.exceptions.UndefinedTableError: relation "alembic_version" does not exist
    backend/src/marketpulse/g5/replay.py:386  guard.validate()
```

**目标选择对照实验（本窗口实跑）**：加载 base（无 env override）helper，把 `DATABASE_URL`
指向一次性空库 canary ⇒ canary 获得 24 张表 / revision `20260905_0004`，
而 child replay DB `marketpulse_g52_f9ef7b606623` 得 **0 张表 / revision=None**。
证明 migration 目标完全跟随 `DATABASE_URL`，故在真实场景下 primary 就是被误用的 target。

## Scope

- 仅三个 G5 test helper 的 disposable replay DB migration invocation。
- 本窗口新增：本 devlog（验证记录）。

## Out of Scope

未修改 `backend/alembic/env.py`、production migration behavior、migration revision、
ReplayTradingRunner、ReplayWorkspaceGuard、G3/G4、execution、protection、reconciliation；
未开始 FG-A Closeout、FG-B、F03–F11、C01、N01/N02/N03、G6、Live、Long Soak。

## Implementation（分支既有内容，本窗口审阅确认）

每个 `_replay_database()` helper 在 `command.upgrade(config, "head")` 的最小作用域内：
保存原 `DATABASE_URL`（含“未设置”状态）→ 暂设为该 helper 刚创建的 child replay URL →
执行 migration → `finally` 精确恢复原值或移除变量。

审阅结论：override 作用域最小、异常路径不泄漏、child URL 是本次新建的 disposable DB，
未反转生产 `DATABASE_URL` 与 `sqlalchemy.url` 的优先级（见 AC-07 实证）。

## Files Changed

本窗口提交：仅新增本 devlog。
分支相对 base 的代码增量（既有提交 `d574e24`）：

- `backend/tests/test_group5_2_trading_replay.py`
- `backend/tests/test_group5_3_determinism.py`
- `backend/tests/test_group5_4_evaluation.py`
- `dev_log/2026-09-08-c04-alembic-test-isolation.md`

## Isolated DB Evidence

环境：docker `mp-c04-isolated`（`postgres:16-alpine`，`127.0.0.1:55432->5432`，**无命名卷**），
库**名仍为** `marketpulse`（`test_group5_2:481` 断言 `result.primary_database == "marketpulse"`）。
interpreter `py -3.14`，`PYTHONPATH=backend/src`。

### AC-01 Child Migration Authority — PASS

在 `DATABASE_URL=<isolated primary>` 下，用 **真实 helper**（`importlib` 直接加载三个测试模块）
创建 child replay DB：

| helper | child DB | child tables | child `alembic_version` |
| --- | --- | --- | --- |
| G5-2 | `marketpulse_g52_0a17fb9ff342` | 24 | `20260905_0004` |
| G5-3 | `marketpulse_g53_c04probe_593b64bdff26` | 24 | `20260905_0004` |
| G5-4 | `marketpulse_g54_c04probe_50d5650e4a7e` | 24 | `20260905_0004` |

### AC-02 Primary Isolation — PASS

- isolated primary 在 child migration **前 / 中 / 后** 三次指纹完全一致：
  `revision=20260905_0004`、`tables=24`、`digest=cfe9d1055844354b`（三次相同）。
- 三个 helper 执行期间与执行后 `os.environ["DATABASE_URL"]` 均等于原 primary URL
  （override 已恢复，无泄漏到后续 primary connection / 其它 tests）。
- 运行结束 `pg_database LIKE 'marketpulse%'` = 仅 `marketpulse`（**residue 0**）。
- 配合上文 canary 对照实验：修复前 target 确为 `DATABASE_URL` 指向库；修复后 child 才是 target。

## G5-2 Result — AC-03 PASS

```
test_reachable_g2_g3_g4_frame_ordering_without_bookticker_setup  -> 1 passed in 5.75s
test_group5_2_trading_replay.py (full)                           -> 7 passed in 21.95s
```

## G5 Determinism Result — AC-04 PASS

```
test_group5_3_determinism.py -> 5 passed in 19.81s
```

## G5 Evaluation Result — AC-05 PASS

```
test_group5_4_evaluation.py -> 10 passed in 57.10s
```

## Normal Environment Regression — AC-06 PASS

普通环境（**不设置** process-level `DATABASE_URL`，落回 `alembic.ini` / `Settings` 默认
`127.0.0.1:5432/marketpulse`）：

```
test_group5_2_trading_replay.py -> 7 passed in 20.08s
test_group5_3_determinism.py    -> 5 passed in 17.59s
test_group5_4_evaluation.py     -> 10 passed in 62.16s
```

共享主库 `marketpulse`(5432) 指纹在本次运行前后完全一致：
`revision=20260905_0004`、`tables=24`、`digest=1c101524e21a9152`，
业务行数逐表未变（`accounts:3 / execution_intents:134 / positions:3 / strategy_candidates:28 /
trades:3 / fills:4 …`），且无新增残留库。
⇒ 修复不依赖 55432 端口，不依赖特定 isolated setup。

## Full Backend Result

isolated 实例（55432），`PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -ra -q`：

```
109 tests collected
109 passed, 1 warning in 150.69s
```

warning 为既有 `StarletteDeprecationWarning`（`fastapi/testclient.py:1`），与本 Fix 无关。
无新失败项。

## Alembic Production Semantics — AC-07 PASS

- **未修改任何 production Alembic 代码**：`backend/alembic/env.py` blob 在 base 与 HEAD 均为
  `d3ec6980b1a4b71b56dd3e4abef0f0492671f6f3` ⇒ `UNCHANGED BY CONSTRUCTION`；
  `git diff a9c2cd64 d574e24 -- backend/alembic/ backend/src/` 为空。
- **优先级未被反转（正向实证）**：`backend/alembic.ini` 固定
  `sqlalchemy.url = ...@127.0.0.1:5432/marketpulse`。新建一个空库后执行普通 CLI
  `DATABASE_URL=<空库> py -3.14 -m alembic upgrade head` ⇒
  该**空库**被迁移到 `20260905_0004` / 24 张表，
  而 `alembic.ini` 指向的 5432 `marketpulse` 指纹逐字节不变（`1c101524e21a9152`）。
  若优先级被反转，结果将相反。⇒ 普通 `DATABASE_URL=<target> alembic upgrade head` 语义保持。
- `alembic heads` = 单一 head `20260905_0004`；`alembic current` 普通环境与 isolated 环境均为
  `20260905_0004 (head)`。

## No Replay Behavior Change — AC-08 PASS

- `git diff --stat a9c2cd64 d574e24`：仅 3 个 `backend/tests/test_group5_*.py` + 1 个 dev_log，
  131 insertions / 3 deletions，无其它文件。
- `backend/src/marketpulse/g5/replay.py` blob base 与 HEAD 均为
  `bab1ae910a72e25851b05c9c79a4968343ac622d` ⇒ ReplayTradingRunner / ReplayWorkspaceGuard 未变。
- 未触碰 G3 / G4 / execution / protection / reconciliation。

## Static Verification

- `py -3.14 -m ruff check backend/src backend/tests scripts` → `All checks passed!`（rc=0）
- `py -3.14 -m compileall -q backend/src backend/tests` → rc=0
- `git diff --check` → rc=0（工作树干净，无空白错误）
- `git status --porcelain`（提交前）→ 仅本 devlog 为新增文件

## Self-Check

- override 仅覆盖 `command.upgrade()`，`finally` 恢复，异常路径不泄漏（实证：前/中/后三态一致）。
- child URL 是 helper 刚创建的 disposable DB；primary 不成为 child migration target（AC-01/AC-02）。
- 无业务 / schema / production Alembic / replay behavior 改动。
- 本窗口未采信既有 devlog 结论：所有 AC 均由本窗口独立实跑得出。
- 未触碰 FG-A 原工作树、未 merge `main`、未修改 FG-A 分支、未开始 FG-B。

## Result

`C04 FIX COMPLETE — WAITING ACCEPTANCE`

（代码修复增量位于分支既有提交 `d574e24`；本窗口贡献 = 独立复现 + 全量 AC/回归验证 + 本证据记录。）

## Remaining

- 独立 Acceptance Review 仍需要。
- 任务书 `Accepted Main` 标记（`36401b26`）与仓库实时 `main`（`af81414`）不一致，建议在
  Closeout 前按 CIP-02 重新 pin。

## FG-A Closeout Status

`STILL BLOCKED — WAITING C04 ACCEPTANCE`

本 test infrastructure fix 不构成 FG-A Closeout authorization。

## Evidence

- 复现（修复前失败）：`1 failed in 2.13s`，`UndefinedTableError: relation "alembic_version" does not exist`
  @ `backend/src/marketpulse/g5/replay.py:386`
- canary 对照：`marketpulse_c04_canary_1ec18bda57f5` 得 24 表 / `20260905_0004`；
  child `marketpulse_g52_f9ef7b606623` 得 0 表 / `None`
- isolated primary 指纹三次一致：`cfe9d1055844354b`
- 共享 5432 指纹全程不变：`1c101524e21a9152`（真实数据，未被任何门触碰）
- G5：1 / 7 / 5 / 10 passed（isolated），7 / 5 / 10 passed（normal）
- full backend：109 collected / 109 passed
- AC-07 CLI 判别：空库被迁移，`alembic.ini` 指向库逐字节不变
- 静态门：ruff rc=0 / compileall rc=0 / `git diff --check` rc=0 / 单一 head `20260905_0004`

## Context For Next AI

1. 审查本 C04 时请以本文件的自有证据为准，不要只读 `2026-09-08-c04-alembic-test-isolation.md`
   的自述（CIP-07）。
2. 本 Fix 的代码增量在 `d574e24`，不在 Closeout 窗口；若要复核 diff，使用
   `git diff a9c2cd64 d574e24`。
3. isolated 环境复现方式：docker `postgres:16-alpine` + `POSTGRES_DB=marketpulse`（库名不可改）
   + process-level `DATABASE_URL`，interpreter `py -3.14`，`PYTHONPATH=backend/src`。
4. **不得**将本 test infrastructure fix 视为 FG-A Closeout authorization。
