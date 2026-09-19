# UI-RD01-I02-A-RESUME-01｜MarketScannerRead Internal Checkpoint

## Result

`I02-A IMPLEMENTED / INTERNAL CHECKPOINT`。本记录仅表示候选实现和内部验证完成，**不**表示 `UI-RD01-I02 ACCEPTED`、Independent Review 或 Human Acceptance。Parent `UI-RD01-I02 = IMPLEMENTING`；`I02-B = NOT STARTED`。

## Task / Scope

- Task: `UI-RD01-I02-A-RESUME-01`。
- Task Base: `e5476b46d0d84f0bb4e495e9dc806a6adaa390c7`。
- Candidate branch: `ui-rd01-i02-a-market-scanner-read`。
- Isolated clean worktree: `E:\Documents\MarketPulse-AI-ui-rd01-i02-a`。
- Requirement source: `docs/design/UI-RD01/UI-RD01-I02-Implementation-Requirements.md` (`UI-RD01-I02-REQ-01 = ACCEPTED / FROZEN`)。
- Scope: only authenticated `GET /api/v1/product/market-scanner`, Current Market projection, Scanner history projection, range/cursor, typed source/partial failures, OpenAPI generation, and focused regression.

## Out of Scope / Preserved Boundaries

- No I02-B Opportunity endpoint or types; I03–I05 are not started.
- No schema, migration, index, package manifest, frozen requirement/design/amendment, or `DECISIONS.md` change.
- No activation of PRE-01B-I2, Real AI, live G2→G3, Gate, Live, provider, or trading action.
- No `FORWARD_PAPER → HISTORICAL_REPLAY` fallback, no second provider/cache/RuntimeHost/engine, and no business primary database write.
- Original dirty worktree `E:\Documents\MarketPulse AI` remains untouched; this candidate was created from the exact Task Base in an independent sibling worktree.

## Implementation

- `RuntimeHost.product_market_snapshot()` returns frozen scalar quote records only; it borrows existing `LiveMarketState` freshness/age authority and never leaks mutable runtime objects.
- `ProductReadContext.market_snapshot()` remains a non-owning delegate.
- Scanner reads only durable `MarketEventRecord` Product fields, with `event_time` window `[effective_start, effective_end)`, descending `(event_time, event_id)` keyset order, and a cursor bound to endpoint/range/filters/provenance/sort/version.
- PostgreSQL Scanner pages use one `REPEATABLE READ, READ ONLY` transaction and `statement_timestamp()` as authoritative `as_of`; test-only SQLite uses its local SQL clock adapter.
- Current Market and Scanner history retain separate source/snapshot metadata; safe section-local failures return typed legal partial responses. Host absence follows the frozen operational `200 NOT_ACTIVATED / UNAVAILABLE` contract.
- `frontend/src/api/generated.ts` was regenerated from backend OpenAPI; it is not handwritten.

## Changed Files

- `backend/src/marketpulse/runtime_host.py`
- `backend/src/marketpulse/api/product/context.py`
- `backend/src/marketpulse/api/product/cursor.py`
- `backend/src/marketpulse/api/product/models.py`
- `backend/src/marketpulse/api/product/market_scanner.py`
- `backend/src/marketpulse/api/product/system.py`
- `backend/tests/test_product_market_scanner.py`
- `frontend/src/api/generated.ts`
- `PROJECT_STATE.md`
- `AI_CONTEXT.md`
- this dev log

## Verification

| Command / check | Result |
|---|---|
| `py -3.14 -m pytest -q backend/tests/test_product_system.py` with `PYTHONPATH=backend/src` | `22 passed` |
| `py -3.14 -m pytest -q backend/tests/test_product_market_scanner.py` with `PYTHONPATH=backend/src` | `24 passed` |
| disposable PostgreSQL assertion inside focused suite | Passed; random `marketpulse_i02a_*` database migrated, tested, and dropped; validates DB `as_of` rather than fabricated Python DTO time |
| `py -3.14 -m pytest -vv backend/tests/test_runtime_host.py` with `PYTHONPATH=backend/src` | `51 passed` |
| `py -3.14 -m ruff check ...` on changed Product/RuntimeHost/test paths | Passed |
| `npm --prefix frontend run generate:api` | Passed; generated `src/api/generated.ts` |
| `npm --prefix frontend run check:api-drift` | Passed |
| `npm --prefix frontend run typecheck` | Passed |
| `npm --prefix frontend run test:run` | `7 files / 57 tests passed` |
| `npm --prefix frontend run build` | Passed |

Focused coverage includes auth, Host absence and pre-availability validation, current fresh/stale/missing quote projection, event-time boundaries, default/preset/custom range validation, cursor bindings and pagination, zero history, forbidden event fields, partial/503/500 semantics, OpenAPI failures, PostgreSQL `as_of`, and no second engine.

## Self Review / Remaining

- Source review corrected the durable PostgreSQL clock from a generic transaction timestamp to explicit `statement_timestamp()` in the same read-only repeatable-read transaction.
- `I02-B` has not been begun. No acceptance conclusion is declared; the next authorized state transition is independent review of this candidate.
- `git diff --check`, allowed-path audit, candidate commit/push, and fresh remote re-read remain the final closeout actions after this state record is added.

## Timing

- Estimated Run Duration: `00:20:00–00:40:00`.
- Execution Started At: `NOT VERIFIED` (the actual lifecycle start was not captured reliably).
- Completed At: pending candidate commit, push, fresh remote re-read, and completion report.
- Run Duration / Estimate Delta: `NOT VERIFIED`; no inferred timestamp is recorded.
