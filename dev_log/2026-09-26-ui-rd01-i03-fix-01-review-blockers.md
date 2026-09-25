# UI-RD01-I03-IMP-01-FIX-01 — Blocking Findings Closure

## Result

`IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`

本记录不构成 Independent Re-Review、Human Acceptance 或 `main` integration。

## Binding

- Authoritative remote `main` at resume: `7a023f99ac44ac744e5a9885fd82f8a87ef51a94`.
- Local stale `main` observed in the preserved workspace: `d5cffca491c1742e3e4ee945ca4ad82f35ea5e2b`.
- Baseline resolution: `REMOTE TRUTH CONFIRMED / LOCAL REF STALE`.
- Failed Candidate / immutable parent: `7bbcde0417d9ae526ac41292d4860b80287db5d2`.
- Fix branch: `ui-rd01-i03-fix-01-review-blockers`.
- Frozen Requirement blob: `658bd6588f7548379e86a05002cc0dd2c3a62a62`.
- Original dirty workspace: `PRESERVED / UNTOUCHED`.
- Fix worktree: `E:/Documents/MarketPulse-AI-ui-rd01-i03-fix-01-review-blockers`.

## Changes

- `backend/src/marketpulse/api/product/trading_audit.py`
  - derives A52/A53 proof only from exact projected durable links;
  - restores the Accepted G3 `1e-8` reconciliation tolerance;
  - validates position/fill quantities in both directions;
  - includes current-run `TradeRecord` when an Account is absent;
  - requires no-plan SELL Intent/Order instrument coherence;
  - classifies initial Risk events by durable event timing, not final Intent status.
- `backend/tests/test_product_trading_audit.py`
  - adds production-projection traceability, tolerance, bidirectional reconciliation,
    missing-account trade, no-plan instrument, and risk-timing adverse coverage.

## Blocking Findings Closure

### FIX-BF-01

`_build_timeline()` now passes fact-derived proof sets into `_event_traceability()`.
The focused projection test proves `COMPLETE`, `PARTIAL`, `NOT_PROVABLE`, and the existing
explicit-empty `COMPLETE / []` path without directly testing only `_trace_for()`.

### FIX-BF-02

The Product validator uses `EPSILON = 1e-8`, equal to Accepted G3 reconciliation semantics.
Focused boundary coverage accepts `<= 1e-8` and rejects a larger difference.

### FIX-BF-03

The validator compares every net-fill instrument to a Position-or-zero and every Position to
net-fill-or-zero. Focused coverage includes missing Position, Position mismatch,
multi-instrument mismatch, valid bidirectional reconciliation, and a legal net-zero result.

### FIX-BF-04

Current-run `trades` are included in the account-absent economic-fact guard. Focused adverse
coverage proves `Account absent + Trade present -> SnapshotError`, which the HTTP boundary maps
to `503 SNAPSHOT_FAILED`.

### FIX-BF-05

The accepted empty-plan SELL bundle now requires
`Intent.instrument_id == Order.instrument_id`; mismatch is a strong snapshot failure, not a
traceability gap. The legal bundle control remains valid.

### FIX-BF-06

`RISK_ACCEPTED` at `Intent.created_at` remains initial even when the current Intent status is
`EXECUTED`; later `RISK_REJECTED` remains deferred and requires its exact Order proof.

## Verification

- Finding-focused / TradingAudit focused: `74 passed, 1 warning`, exit `0`.
- Product API regression: `150 passed, 20 warnings`, exit `0`.
- Full backend regression on final executable bytes: `931 passed, 20 warnings`, exit `0`,
  duration `1072.25s`.
- `ruff check backend/src backend/tests`: pass.
- `ruff format --check` for both touched files: pass.
- `compileall backend/src`: pass.
- `git diff --check`: pass.
- OpenAPI regeneration against the current backend: no drift; `generated.ts` matches.
- Isolated PostgreSQL evidence: exit `0`, `harness_errors=[]`, `validation_problems=[]`.
  Environment: `127.0.0.1:5450/marketpulse`, PostgreSQL `16.15`, system identifier
  `7688238732663410723`, `alembic_version=20260917_0010`.
  It proves legal empty workspace, stable repeatable-read/read-only snapshot, global
  reconciliation, orphan detection, run-mode ownership, cleanup/cancellation, and the
  history-heavy population.
- Performance evidence: Orders `5202`, Fills `5201`, Ledgers `5201`, PositionEvents `5200`;
  SQL statements `16` at both small and large populations, no query-per-row evidence, timeline
  `limit+1=101`, large request duration `14918.623ms`, transaction hold `14842.417ms`, Windows
  memory evidence and `EXPLAIN (ANALYZE, BUFFERS)` captured. No SLA or performance acceptance is
  asserted.

External evidence is retained at
`E:/Documents/AI-Developer/codex-data/tmp/ui-rd01-i03-fix-01/postgres-evidence/evidence-20260926-004608.json`.

## Zero-Change Proof

No changes under the Frozen Requirement, `backend/src/marketpulse/g3`,
`backend/src/marketpulse/g4`, `backend/src/marketpulse/runtime`, `backend/src/marketpulse/db`,
`backend/alembic`, `DECISIONS.md`, `PRODUCT_REQUIREMENTS.md`, `AGENTS.md`,
`frontend/src/pages`, dependency manifests, or `frontend/src/api/generated.ts`.

## Human Gates

- Performance Human Disposition: `PENDING`.
- Human Acceptance: `PENDING`.
- Independent Re-Review: `REQUIRED` (`UI-RD01-I03-IMP-01-IR-02 = NEXT`).
- `main` integration: `NOT PERFORMED`.
- `I04` / `I05`: `NOT STARTED`.
