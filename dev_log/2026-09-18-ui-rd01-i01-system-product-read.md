# UI-RD01-I01｜System Product Read

## Task

- Task ID：`UI-RD01-I01`。
- Task Type：IMPLEMENTATION + VERIFICATION；基于已接受并冻结的 `UI-RD01` formal design。
- Task Base / `origin/main`：`2cabc7311e041566011be59fb139cac9a082fe24`。
- Result：**`UI-RD01-I01 = IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`**，不等于 `ACCEPTED`、`COMPLETE` 或 Human Acceptance。

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

## Remaining / Blockers

- Independent review and Human Acceptance remain required. This branch must not be merged to `main` before that acceptance.
- No real browser-to-running-backend integration or real provider/runtime activation was performed or claimed.

## Evidence

- Branch: `ui-rd01-i01-system-product-read`.
- Preflight observed `HEAD` and `origin/main` both at `2cabc7311e041566011be59fb139cac9a082fe24`; no baseline drift.
- I01 change inventory: `backend/src/marketpulse/api/app.py`, `backend/src/marketpulse/runtime_host.py`, `backend/src/marketpulse/api/product/**`, `backend/tests/test_product_system.py`, and `frontend/src/api/generated.ts`, plus this minimal state sync.
