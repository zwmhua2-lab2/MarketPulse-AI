# UI-RD01-I03-IMP-01-FIX-02 — PositionEvent Explicit Lineage Coherence Closure

## Result

`IMPLEMENTED / READY FOR INDEPENDENT RE-REVIEW`

This is an implementation handoff only. It does not perform IR-03, Human Acceptance, or `main`
integration.

## Binding

- Authoritative remote `main`: `7a023f99ac44ac744e5a9885fd82f8a87ef51a94`.
- Parent candidate: `5444e96d2d3e6f1c089f7dcfa4a8251a9c21472b` on
  `ui-rd01-i03-fix-01-review-blockers`.
- FIX-02 branch: `ui-rd01-i03-fix-02-position-event-coherence`.
- Frozen Requirement: `docs/design/UI-RD01/UI-RD01-I03-Implementation-Requirements.md`;
  blob `658bd6588f7548379e86a05002cc0dd2c3a62a62`.
- The original dirty workspace was preserved; this task uses an independent clean worktree.

## Changes

- `trading_audit.py` resolves PositionEvent's non-null explicit Plan, Order, and Fill references
  before granting A52/A53 proof. A resolved object must retain exact durable identity and the
  PositionEvent instrument; a Fill's instrument proof is only its exact Order's instrument.
- Coexisting explicit links must agree: `Fill.order_id == event.order_id`, and the resolved
  Order's `plan_id == event.plan_id`. Any existing contradiction raises `SnapshotError`, which
  the Product boundary maps to `503 SNAPSHOT_FAILED`.
- Missing historical references remain unproven trace links; they are not changed into a new
  fatal rule. The all-null PositionEvent control remains `COMPLETE / []`.
- Production-path tests cover valid Plan proof, cross-instrument Plan/Order/Fill, all three
  cross-reference contradictions, coherent all-three proof, all-null control, and a genuinely
  unavailable historical reference.

## Development Verification

- `PYTHONPATH=src py -3.14 -m pytest tests/test_product_trading_audit.py -q`:
  `83 passed, 1 warning`, exit `0`.
- Ruff check and format check for the two changed Python files: pass.
- `compileall backend/src`: pass.
- Final exact-candidate verification, including Product/full-backend regression, isolated
  PostgreSQL/history-heavy evidence, OpenAPI drift, and the immutable evidence manifest, is
  recorded outside the repository after the candidate commit. No repository mutation is permitted
  after that verification begins.

## Finding and Gates

- `UI-RD01-I03-IR-02-BF-01 = REMEDIATED / AWAITING INDEPENDENT RE-REVIEW`.
- `IR-01-NBF-02 = REMAINS / NON-BLOCKING`; `R04-P2-01 = REMAINS / NON-BLOCKING`.
- Performance Human Disposition: `PENDING`; Human Acceptance: `PENDING`; `main` integration:
  `NOT PERFORMED`; `I04` / `I05`: `NOT STARTED`.
- Real AI remains `NOT ACTIVATED`; Gate A/B/C remain unchanged; Live remains `NOT AUTHORIZED`;
  Live Trading remains `DISABLED`.
