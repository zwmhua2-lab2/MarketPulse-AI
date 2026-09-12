# SE-ARCH-FIX-01｜Stable Evidence Anchor

> Status: `IMPLEMENTED / READY FOR INDEPENDENT REVIEW` after the required
> verification evidence below. This is not an Acceptance decision and does not
> authorize merge, SE-02C, SE-02D, FIX-02, Real AI, Live, N01 work or a Runtime
> Host redesign.

## Repository truth and scope

- Task Base / remote `main` / `origin/main` / implementation `HEAD` at start:
  `1579707eff083007f1ac7ec65e10e6043f32b31e`.
- Branch: `se-arch-fix-01-stable-evidence-anchor`.
- Only additive Edge capture-admission persistence, its minimal G2 wiring,
  focused tests, migration and this record are in scope.
- Existing `G2 State + Formal Edge Evidence` remains one PostgreSQL transaction.
  No Strategy, risk, execution, economic, outcome-calculation or Runtime Host
  semantics are changed.

## Original finding and human decision

F01 showed that a failed Formal transaction could be retried ten seconds later
with the same logical Opportunity/Evidence identity but a new
`candidate.created_at`, a later BBO and a different evidence hash. The approved
`Option 2 + Hybrid A+B` freezes an append-only durable Capture Anchor as the
Forward Paper admission boundary:

```text
qualifying candidate → frozen causal payload → durable anchor
→ admitted FORWARD_PAPER cohort → atomic G2 + Formal Evidence transaction
```

If anchor durability itself fails and the process subsequently dies, the sample
is `NOT ADMITTED / UNVERIFIABLE / NO FORWARD EVIDENCE`. This is a
Human-approved V1 capture-coverage limitation; it must never be repaired by
inventing a new clock/BBO after restart.

## Architecture and schema delta

- Reuses `edge_bbo_observations` and `record_bbo_observation()`; no second BBO
  identity/archive exists.
- Adds `edge_opportunity_capture_anchors` in additive revision
  `20260912_0006` (`20260911_0005` parent).
- Anchor identity is `(opportunity_id, evidence_revision)`: same hash is
  idempotent; different hash fails closed.
- The anchor stores the event, timeline, prepared/resulting state and transition,
  qualifying plus full candidate list, feature snapshot, supplied quote
  diagnostics, source provenance, `evidence_at`, BBO observation id and complete
  deterministic payload/hash needed for Formal Evidence reconstruction.
- A usable quote only becomes a BBO observation when its source,
  source-event-time and optional sequence are actually supplied. Missing/stale
  or non-provenanced inputs remain correctly diagnosable without a fabricated
  observation.

## Failure, retry, restart and orphan semantics

- Anchor admission is a separate small transaction: BBO append and anchor append
  commit or roll back together.
- A same-process admission write failure retains only the frozen in-flight anchor
  object; retry reuses it and never re-runs clock/BBO lookup for that event. The
  object is not a queue/WAL and disappears on crash.
- Formal transaction failure leaves the anchor intact and no G2/Formal Evidence
  facts committed. Retry consumes anchor facts only.
- `resume_pending_capture_anchors()` permits a fresh repository/process startup
  path to find durable unformalized anchors from PostgreSQL alone. It fences the
  stored precondition against durable G2 state before writing Formal facts.
- A mismatched durable precondition raises `CaptureAnchorOrphan`; no Formal
  Evidence is written, and the anchor remains auditable.
- New `FORWARD_PAPER` admission requires explicit
  `forward_admission_session_id`; an old/replayed input without that proof is
  rejected rather than inferred live from time proximity. `HISTORICAL_REPLAY`
  does not create a Forward anchor.
- Anchor attempt/failure/admitted events are emitted through the module logger as
  minimal operational coverage evidence. SE-02D aggregation is intentionally
  not implemented.

## Verification

All PostgreSQL suites below ran serially from `backend` with `PYTHONPATH=src`
against disposable databases; they do not claim any shared operator database
state.

| Command | Result |
|---|---|
| `py -3.14 -m pytest tests/test_se_02b_opportunity_capture.py -q` | `20 passed in 40.87s` |
| `py -3.14 -m alembic heads` | single head `20260912_0006` |
| `py -3.14 -m pytest tests/test_se_02a_edge_contracts.py tests/test_se_02a_edge_persistence.py tests/test_se_02b_attribution.py tests/test_group2.py tests/test_n01_runtime_resource_lifecycle.py -q` | `155 passed in 85.03s` |
| `py -3.14 -m pytest tests -q` | `318 passed, 1 warning in 346.87s` |
| `py -3.14 -m ruff check …` | `All checks passed!` |
| `py -3.14 -m compileall -q backend/src backend/tests` | exit `0` |
| `git diff --check` | exit `0` (Windows LF/CRLF warnings only) |

The focused capture suite proves original-F01 retry stability, durable-anchor
recovery using a new repository instance with no current quote, same-process
anchor write failure reuse, incompatible-precondition orphan behavior, and
Forward admission rejection without explicit live-session proof.

## Known limitations and remaining risks

- A database failure followed by a pre-anchor crash loses that sample's durable
  identity by approved design; exact post-crash reconstruction would require a
  separately approved durable upstream boundary.
- Orphans are queryable from anchors lacking Formal Evidence and are never
  auto-deleted or converted into outcomes. This task does not add an orphan UI or
  cleanup framework.
- The runtime must provide real live-session provenance and complete BBO source
  facts before a usable quote can be bound to an observation; this task does not
  redesign the upstream market-data host.
