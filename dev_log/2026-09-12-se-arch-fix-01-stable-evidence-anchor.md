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

## Independent Review Fix R1｜2026-09-13

> Status: `REVIEW FIX IMPLEMENTED / READY FOR RE-REVIEW`. This is an
> implementation/review-fix record only; it does not accept the change or
> authorize a merge to `main`.

The independent review found F01--F07. The following additive correction is
limited to the Stable Evidence Anchor boundary and its focused PostgreSQL
regressions. `20260912_0006` remains immutable; additive revision
`20260913_0007` is the sole Alembic head.

| Finding | Root cause | R1 resolution and evidence |
|---|---|---|
| F01 | Fresh resume could allow current context/quote to rebuild Formal evidence. | `CaptureAnchor` reconstructs its frozen context, quote, candidates and Formal evidence, recomputes the exact `formal_evidence_hash`, and `capture_opportunity()` rechecks it before append. Real PostgreSQL regression uses a fresh source-B repository with later clock/BBO/provenance and proves source-A frozen hash/T0/BBO are written. |
| F02 | A non-empty session string was caller-controlled, so redelivery could look Forward-live. | Process-local `ForwardAdmissionAuthority` mints HMAC-backed, session- and exact-event-bound proofs at the live-ingress boundary. New Forward anchors require valid proof; no-anchor old redelivery with a new BBO/session and no current proof is rejected (`redelivery_admitted == False`). Existing durable anchors recover from their immutable evidence only; `HISTORICAL_REPLAY` never creates a Forward anchor. |
| F03 | `OK` could lack actual BBO feed provenance. | `OK` now requires source event time and source as well as the existing usable-quote predicates. The ORM/migration enforce `OK ⇔ reference_bbo_observation_id non-null`; incomplete provenance persists as `REFERENCE_STALE` with no BBO id. |
| F04 | Check-then-insert had a concurrent unique-violation race. | BBO and anchor append use PostgreSQL `INSERT ... ON CONFLICT DO NOTHING RETURNING`, then re-read canonical content: equal is idempotent, different is conflict. A real two-writer PostgreSQL regression proves one `INSERTED`, one `IDEMPOTENT`, and a separately valid different hash conflicts. |
| F05 | Top-level/payload facts and caller hash could be trusted after model-copy tampering. | Repository revalidates every append through the canonical model; anchor validation verifies hash version/hash, full frozen Formal evidence, all duplicated causal fields, BBO and ingress-proof facts. Candidate/T0/BBO/source/session tampering regressions all fail closed. |
| F06 | Orphan state was transient and restart could retry it indefinitely. | New append-only `edge_opportunity_capture_anchor_orphans` records identity, `UNVERIFIABLE_ORPHAN`, reason, expected/actual durable precondition, versions/hash and deterministic detected/recorded time. Resume excludes classified anchors; real PostgreSQL test proves one durable orphan, no Formal evidence, and zero subsequent resumptions. |
| F07 | The in-process frozen-anchor map was unbounded. | `pending_capture_anchor_capacity` is explicit (default 2048); capacity exhaustion logs and raises `CaptureAdmissionOverloaded` before silently evicting or replacing an anchor. PostgreSQL regression holds one failed in-flight anchor then proves a second admission fails closed. |

### R1 verification executed so far

All PostgreSQL tests below use newly-created disposable databases serially from
`backend` with `PYTHONPATH=src`; the shared configured database was only read by
`alembic current` and was not migrated.

| Command | Result |
|---|---|
| `py -3.14 -m ruff check src tests` | `All checks passed!` |
| `py -3.14 -m compileall -q src tests` | exit `0` |
| `py -3.14 -m alembic heads` | single head `20260913_0007` |
| `py -3.14 -m pytest tests/test_se_02b_opportunity_capture.py -q` | `25 passed in 70.58s` |
| `py -3.14 -m pytest tests/test_se_02b_attribution.py -q` | `31 passed in 43.47s` |
| `py -3.14 -m pytest tests -q` | `323 passed, 1 warning in 474.01s` |
| R1 focused PostgreSQL regressions (fresh-resume, orphan/restart, no-anchor redelivery, incomplete provenance, tamper, concurrent append, bounded overload) | included in the above capture group and passed |

The first full-suite attempt exposed one required migration-consumer sync:
`ReplayRunner.schema_head` still named `20260912_0006`, so a clean newly-migrated
replay database was rejected before the guard could report its intended dirty
workspace condition. R1 updates that frozen consumer and the existing migration
persistence test to `20260913_0007`; the guard's targeted regression passed and
the final full suite above passed from a fresh run.
