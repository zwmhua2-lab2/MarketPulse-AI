# UI-RD01-I01｜System Product Read

## Task

- Task ID：`UI-RD01-I01`。
- Task Type：IMPLEMENTATION + VERIFICATION；基于已接受并冻结的 `UI-RD01` formal design。
- Task Base / `origin/main`：`2cabc7311e041566011be59fb139cac9a082fe24`。
- Result：**`UI-RD01-I01 = IMPLEMENTED / READY FOR INDEPENDENT REVIEW`**，不等于 `ACCEPTED`、`COMPLETE` 或 Human Acceptance。

## Scope

- Shared Product Read Pydantic contracts and nullable, non-owning `ProductReadContext`。
- Authenticated `GET /api/v1/product/system` (`SystemIncidentRead`) vertical slice。
- Host-owned, sanitized immutable Product read snapshots; section-local incident read and opaque keyset cursor。
- OpenAPI → `frontend/src/api/generated.ts` integration and direct tests。

## Out of Scope / Unchanged

- `MarketScannerRead`、`OpportunityTraceRead`、`TradingAuditRead`、`EdgeAggregateRead` and all later I01–I05 work.
- Schema, migration, index, provider activation, Real AI, live G2→G3, Live Trading, mutation/repair/recovery authority.
- `PRODUCT_REQUIREMENTS.md` and frozen UI-RD01 design/task card.
- No merge/push to `main`.

## Changes

- Added `marketpulse.api.product` contracts, cursor codec, context facade and `system` router.
- Registered the Product router in the FastAPI application.
- Added a narrow `RuntimeHost.product_runtime_snapshot()` and immutable recovery completion snapshot; the Product endpoint borrows rather than owns the Host session factory.
- Generated the Product endpoint TypeScript OpenAPI contract.
- Added System Product tests covering authentication, host absence, non-owning session borrowing, sanitized/keyset-paginated incidents, section-local source failure, and recovery snapshot immutability.

## Verification

| Command | Result |
|---|---|
| `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_product_system.py -q` | 6 passed (2 deprecation warnings) |
| `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_runtime_host.py -q` | 51 passed (1 deprecation warning, 77.61s) |
| `py -3.14 -m ruff check backend/src/marketpulse/api/product backend/src/marketpulse/api/app.py backend/src/marketpulse/runtime_host.py backend/tests/test_product_system.py` | passed |
| `npm run typecheck` | passed |
| `npm run check:api-drift` | passed; `generated.ts` matches backend contract |
| `npm run test:run` | 7 files / 44 tests passed |
| `npm run build` | passed |
| `git diff --check` | passed; Git emits only pre-existing LF→CRLF advisory for `frontend/src/api/generated.ts` |

## Full Backend Regression

- 前次裸命令 `py -3.14 -m pytest backend/tests` 的 `6 failed, 685 passed, 2 warnings`（`626.57s`）**INVALIDATED BY INVOCATION ENVIRONMENT**：失败全为 `backend/tests/test_n01_restart_recovery.py` 的 6 个 child-process 场景，统一为 `ModuleNotFoundError: No module named 'marketpulse'`。该调用未在 `os.environ` 设置 `PYTHONPATH=backend/src`；N01-C 子进程使用 `env=os.environ.copy()`，因此这不是 Product/I01 regression。仓库同类先例见 `dev_log/2026-09-12-se-02b-opportunity-capture-attribution.md` §11.1–§11.2。
- Accepted rerun preflight：worktree clean；`HEAD` / remote Candidate = `9716cc2737b6278b573246e43673ba6b7dbe6288`；remote `main` = `2cabc7311e041566011be59fb139cac9a082fe24`；`DATABASE_URL` = UNSET；未检测到 foreign/concurrent pytest process；shared DB `alembic current` / `alembic heads` 均为 `20260913_0009 (head)`。
- Accepted command（PowerShell，环境级、可由 child process 继承）：`$env:PYTHONPATH = 'backend/src'; py -3.14 -m pytest backend/tests -q`。执行前在同一 shell 实测 `os.environ['PYTHONPATH'] = 'backend/src'`。
- Accepted result：**`691 passed, 0 failed, 2 warnings, 0 skipped, 0 xfailed`**；pytest duration = `771.57s`（`0:12:51`）；outer stopwatch = `775.549s`；exit code = `0`。此前 N01-C `ModuleNotFoundError` 签名未复现。
- This verification amendment = documentation/evidence only；backend implementation source / tests / frontend / schema / migration / index / package manifests = **ZERO CHANGE**。

## Remaining / Blockers

- Independent review and Human Acceptance remain required. This branch must not be merged to `main` before that acceptance.
- No real browser-to-running-backend integration or real provider/runtime activation was performed or claimed.

## Evidence

- Branch: `ui-rd01-i01-system-product-read`.
- Preflight observed `HEAD` and `origin/main` both at `2cabc7311e041566011be59fb139cac9a082fe24`; no baseline drift.
- I01 change inventory: `backend/src/marketpulse/api/app.py`, `backend/src/marketpulse/runtime_host.py`, `backend/src/marketpulse/api/product/**`, `backend/tests/test_product_system.py`, and `frontend/src/api/generated.ts`, plus this minimal state sync.

## UI-RD01-I01-FIX-01｜Product Read 契约收口

### Task

- Task ID：`UI-RD01-I01-FIX-01`（FIX 批，从 Reviewed Candidate 派生；不 merge `main`）。
- Reviewed Candidate（= 本 FIX 的 parent）/ Task Base：`2b47b8fae7c47e53f73bfe3a7e75884bb615d221` / `2cabc7311e041566011be59fb139cac9a082fe24`。
- Independent Review Verdict：`FAIL — FIX REQUIRED`，findings = `RR-P1-01` / `RR-P1-02` / `RR-P1-03` / `RR-P2-01`（P1-04 = Health 段一致性随 `RR-P1-03` 同批收口）。
- Result：**`UI-RD01-I01-FIX-01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`**，不等于 `ACCEPTED` / `COMPLETE` / Human Acceptance。

### Findings Closed

| Finding | Closure |
|---|---|
| `UI-RD01-I01-RR-P1-01` | `GET /api/v1/product/system` 的 `incident_status` / `incident_type` 改为既有权威枚举 `IncidentStatus` / `IncidentType`（`marketpulse.g4.models`；**未**新增 enum authority）。`incident_status=INVALID` / `incident_type=INVALID` → HTTP `422`（由 FastAPI 查询参数校验给出）；OpenAPI 参数由 `string` 变为 `{"$ref": "#/components/schemas/IncidentStatus"|"IncidentType"}`，`generated.ts` 相应变为 `components["schemas"]["IncidentStatus"｜"IncidentType"]` 枚举而非任意 string。cursor filter fingerprint 改为以 `.value` 稳定序列化（同一取值 ⇒ 同一 fingerprint，既有 cursor 兼容）；keyset/排序/limit/next_cursor 语义未变。 |
| `UI-RD01-I01-RR-P1-02` | 端点级 Product 失败恢复为**正式 typed 契约**：新增 `ProductFailureResponse`（`api/product/models.py`，字段 = surface identity + `read_failure_reason` + `correlation_id`，**无**自由文本诊断字段）；取得所需 Host Product snapshot 失败（抛异常或返回 `None`）→ HTTP `503` + `ReadFailureReason.SNAPSHOT_FAILED`，不再返回 `detail="product snapshot unavailable"` 这类非正式字符串；OpenAPI `responses[503]` 与 `generated.ts` 均已暴露，且 503/500 共用同一 schema；`SOURCE_UNAVAILABLE` / `SNAPSHOT_FAILED` 的冻结区分保留。section-local 语义不变：Incident DB 段失败而其它 System truth 可用时仍为 HTTP `200` + `is_partial=true` + `incidents.state=UNAVAILABLE` + `incidents.read_failure_reason=SOURCE_UNAVAILABLE`。 |
| `UI-RD01-I01-RR-P1-03` | `ProductRuntimeSnapshot` 新增 `snapshot_at`，在 `product_runtime_snapshot()` 的**同步采集入口**捕获一次（`datetime.now(UTC)`），作为该 Host snapshot 的权威时刻；`_section()` 改为**必须**接收 `snapshot_at`（不再内部 `_now()`），`live` / `ready` / `health` / `runtime` / `market_provider` / `lanes` / `database_singleton` / `recovery` / `reconciliation` / `operator_system_state` / `ai_activation` 全部使用该时刻，故同一 Host snapshot 只发布**一个** section 时刻；`meta.snapshot_at` / `meta.observed_at` / `operational_context.context_snapshot_at` / `ReconciliationDTO.snapshot_at` 同源（不再采集后再 `_now()`）。Incident DB 段使用其**自身查询采集时刻**（`_IncidentRead.snapshot_at`，与 `incidents.source.snapshot_at` 一致）；Recovery 仍来自不可变的 process-lifetime `RecoverySnapshot`。未声称 global ACID consistency。 |
| `UI-RD01-I01-RR-P1-04`（Health 段一致性，随 P1-03 同批） | `ProductRuntimeSnapshot` 新增 `readiness`：`health_checks` 与 readiness 评估在 `product_runtime_snapshot()` 的**同一次同步采集**中读取并写入 snapshot；端点不再另行调用 `host.readiness()`，因此 Product health 段不可能把「某次采集的 checks」与「其后一次独立 readiness 评估的 overall status」拼接。`Live != Ready != Health` 保持；`/live`、`/ready`、`/health` 行为 ZERO CHANGE（`app.py` 未改）。 |
| `UI-RD01-I01-RR-P2-01` | 未分类 Product 内部错误 → HTTP `500` + `ProductFailureResponse`：仅返回 `projection` / `contract_version` / `read_surface_class` / `correlation_id`（`correlation_id = marketpulse.ids.new_id().hex`），响应体不含 traceback、异常文本、SQL、DSN、provider 细节或 secret；服务端以既有结构化日志记录同一 correlation id 与 traceback（仅日志）。未引入外部 tracing/logging 服务。OpenAPI `responses[500]` 与 `generated.ts` 已文档化。实现方式 = 端点内单一错误边界（`HTTPException` 直通，其余异常归一），未改动 `app.py` 的全局异常处理。 |

### Changes

- `backend/src/marketpulse/api/product/models.py`（+16/-0）：新增 `ProductFailureResponse`。
- `backend/src/marketpulse/api/product/system.py`（+175/-32）：枚举过滤、正式 503/500 契约与 correlation id、权威 `snapshot_at` 传递、`_IncidentRead` 查询时刻、health 一致性。
- `backend/src/marketpulse/runtime_host.py`（+19/-1）：`ProductRuntimeSnapshot.snapshot_at` / `.readiness`，采集时一次捕获并同源读取。
- `backend/tests/test_product_system.py`（+370/-12）：6 → 19 tests，逐 finding 回归（含 OpenAPI 契约断言与 500/503 脱敏断言）。
- `frontend/src/api/generated.ts`（+58/-2，`npm run generate:api` 产物，未手工编辑）。
- 本 dev_log 与 `PROJECT_STATE.md` / `AI_CONTEXT.md` 最小状态同步。

### Verification

| Command | Result |
|---|---|
| `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_product_system.py -q` | **19 passed**, 2 warnings, `1.51s` |
| `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests/test_runtime_host.py -q` | **51 passed**, 1 warning, `71.69s`（RuntimeHost 已改，故执行） |
| `py -3.14 -m ruff check backend/src/marketpulse/api/product backend/src/marketpulse/runtime_host.py backend/src/marketpulse/api/app.py backend/tests/test_product_system.py` | `All checks passed!` |
| `npm run generate:api` / `npm run check:api-drift` | `no OpenAPI drift`；`generated.ts` 与后端契约逐字节一致 |
| `npm run typecheck` / `npm run test:run` / `npm run build` | `tsc -b` 通过；`7 files / 44 tests passed`；`vite build` 通过（150 modules） |
| 完整后端回归（PowerShell，环境级 `$env:PYTHONPATH='backend/src'`） | **704 passed, 0 failed, 3 warnings**，`819.73s`（`0:13:39`）；基线 691 passed + 本批新增 13 tests = 704，计数自洽 |
| 变异探针（自愿附加证据） | P1 权威 snapshot 时刻 / P2 枚举过滤 422 / P3 503 SNAPSHOT_FAILED 形式契约 / P4 500 边界：4/4 `TEETH OK`（破机制必红）；探针后 `system.py` sha256 复原一致 |

- 回归 preflight：worktree 唯一 cwd；`DATABASE_URL` = UNSET；`PYTHONPATH=backend/src` 于 shell 环境级设置（N01-C 子进程可继承）；执行窗口内无外来 pytest/python 进程。
- 完整回归在**最终树**上执行（docs 同步为其后唯一增量，不参与测试收集）。

### Forbidden Area Check

- ZERO CHANGE：schema / migration / index / `backend/alembic/**` / package manifests / Product frozen design（`docs/design/UI-RD01/**`）/ `PRE-01B-D2` / `I02–I05` / Product UI / trading-risk-recovery 业务语义 / provider-AI activation / Live。
- 未执行：redesign `UI-RD01`、改 accepted enums、加基础设施、reset / rebase / squash、merge `main`。
- `git diff --name-only 2b47b8fa`（提交前）= 上述 5 个代码/契约文件；`git diff --check` 通过。

### Remaining / Blockers

- **Independent Re-Review pending；Human Acceptance pending；`main` integration forbidden。**
- 非阻塞观察（既有行为，未在本 fix 范围内改动）：`system.py` 中 `HTTP_422_UNPROCESSABLE_ENTITY` 常量触发 Starlette 弃用告警；`_source()` 现仅由 `_section()` 调用。

## UI-RD01-I01-FIX-02｜Independent Re-Review Finding Closure

- Reviewed Candidate：`99e59b06135ef92cb690edb761ddbc4650c2fb78`；Task Base / remote `main`：`2cabc7311e041566011be59fb139cac9a082fe24`。
- Closed `RR2-P1-01`：503 uses required `ProductUnavailableResponse` including `read_failure_reason`; snapshot failure = `503 SNAPSHOT_FAILED`. Closed `RR2-P2-01`：500 uses `ProductInternalErrorResponse` with only `correlation_id`. Closed `RR2-P1-02`：cursor validation precedes session availability; `sessions=None` malformed/mismatch = 422, valid/no cursor remains partial 200 `SOURCE_UNAVAILABLE`.
- Verification：focused `21 passed, 3 warnings`; ruff PASS; generate/drift/typecheck/frontend `44` tests/build PASS; exclusive-window full backend `$env:PYTHONPATH='backend/src'; py -3.14 -m pytest backend/tests -q` = **`706 passed, 3 warnings, exit 0, 637.22s`** (outer `640.896s`); `DATABASE_URL` UNSET; DB current/heads = `20260913_0009`; `git diff --check` PASS.
- Scope integrity：only allowed Product models/system/tests, generated API and state/dev-log changed; RuntimeHost, migrations/schema/index/manifests, I02-I05 and main = ZERO CHANGE. Result：**`UI-RD01-I01-FIX-02 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`**；Independent Re-Review / Human Acceptance pending；main integration forbidden。

### Evidence

- Parent（Reviewed Candidate）：`2b47b8fae7c47e53f73bfe3a7e75884bb615d221`；Task Base / `origin/main`：`2cabc7311e041566011be59fb139cac9a082fe24`（提交前复读，未变）。
- 探针复原校验：`backend/src/marketpulse/api/product/system.py` sha256 = `d572d51953796a735cb441d551a327889eb8a3f0f580b9fa57d2c7aa428e1690`（baseline == restored）。
