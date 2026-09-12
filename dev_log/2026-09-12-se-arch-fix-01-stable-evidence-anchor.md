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
regressions. At this original review-fix point, its unpublished branch-local
chain was `20260912_0006 -> 20260913_0007`; the later Latest Main Integration
records the required pre-acceptance renumbering below.

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
| `py -3.14 -m alembic heads` | original review-fix branch: single head `20260913_0007` |
| `py -3.14 -m pytest tests/test_se_02b_opportunity_capture.py -q` | `25 passed in 70.58s` |
| `py -3.14 -m pytest tests/test_se_02b_attribution.py -q` | `31 passed in 43.47s` |
| `py -3.14 -m pytest tests -q` | `323 passed, 1 warning in 474.01s` |
| R1 focused PostgreSQL regressions (fresh-resume, orphan/restart, no-anchor redelivery, incomplete provenance, tamper, concurrent append, bounded overload) | included in the above capture group and passed |

The first full-suite attempt exposed one required migration-consumer sync:
`ReplayRunner.schema_head` still named `20260912_0006`, so a clean newly-migrated
replay database was rejected before the guard could report its intended dirty
workspace condition. R1 updates that frozen consumer and the existing migration
persistence test to its then-current head `20260913_0007`; the guard's targeted regression passed and
the final full suite above passed from a fresh run.

## Latest Main Integration｜2026-09-13

> Status: `INTEGRATED / READY FOR INDEPENDENT RE-REVIEW`. This integration is
> not an Acceptance decision and does not authorize a `main` merge.

### Drift, collision and decision

- Original FIX-01 Task Base: `1579707eff083007f1ac7ec65e10e6043f32b31e`.
- Reviewed implementation: `51053757e355c5b79858bf099ec1844a562dbf3e`.
- Review Fix: `bdb1af2bf149daca65d7fd3b07105f5a71387e28`.
- Latest Accepted Main integration parent: `71abb07707e9d28e5f2a3a5c5c58c8694f7a3b3f`.

The collision arose because two independent parallel Acceptance Batches both
started at `20260911_0005` and each created an unpublished
`20260912_0006`; it is not an error in accepted history. Latest Main already
owns that identity for N01-7 durable position-protection snapshot, so that file
and its semantics are preserved unchanged. The FIX migrations had never been
accepted into `main`, so their revision identities were reconciled transparently
in this integration commit:

| Original FIX branch identity | Integrated identity | Parent |
|---|---|---|
| `20260912_0006_capture_anchor` | `20260913_0007_capture_anchor` | accepted `20260912_0006` |
| `20260913_0007_capture_anchor_review_fix` | `20260913_0008_capture_anchor_review_fix` | integrated `20260913_0007` |

The resulting single linear schema is:

`20260911_0005 → 20260912_0006 (N01-7) → 20260913_0007 (Capture Anchor) → 20260913_0008 (Review Fix / Orphan)`.

### Semantic conflict resolution

- `db/models.py` retains N01-7 `positions` durable protection authority and
  FIX-01 anchor/orphan records together; neither additive schema is dropped.
- `g5/replay.py::ReplayTradingRunner.schema_head` and the SE-02A migration
  persistence assertion now name the final unique head `20260913_0008`.
- Capture Anchor semantics remain frozen: stable T0/reference BBO, canonical
  anchor/evidence hash, event-bound ingress proof, atomic idempotency, durable
  orphan classification, bounded pending cache, and replay/redelivery fail-close.
- N01-7 protection authority, G3/G4 recovery/reconciliation behavior and its
  accepted `20260912_0006` migration/backfill are retained without alteration.

Independent re-review must inspect the cumulative latest-main-plus-FIX diff,
not only this integration commit. No FIX-02, SE-02C, SE-02D, strategy, Real AI
or Runtime Host work is introduced here.

### Integration verification (executed 2026-09-13)

Verification environment: a **dedicated disposable PostgreSQL instance**
(`postgres:16-alpine`, container `marketpulse-fix01i-pg`, `127.0.0.1:5433`)
plus a worktree-local gitignored `.env` whose *only* override is `DATABASE_URL`.
The shared acceptance database `127.0.0.1:5432/marketpulse` was fingerprinted
before and after and never migrated (`20260905_0004`, 24 tables, unchanged); the
isolated instance was destroyed after the run and left no `.env` behind. The
isolated instance's ambient database was migrated to the integrated head so that
the ambient-database tests see the schema the accepted environment provided.

| Gate | Command (cwd = worktree) | Result |
|---|---|---|
| Revision graph audit | parse all `backend/alembic/versions/*.py` | 8 revisions, **0 duplicate revision ids**, 0 dangling parents, single head `20260913_0008` |
| Alembic heads (isolated) | `py -3.14 -m alembic heads` | `20260913_0008 (head)` — single head |
| SE-02A persistence + migration chain | `py -3.14 -m pytest backend/tests/test_se_02a_edge_persistence.py -q` | `27 passed in 57.48s` |
| SE-02B capture + attribution (F01–F07 regressions) | `py -3.14 -m pytest backend/tests/test_se_02b_opportunity_capture.py backend/tests/test_se_02b_attribution.py -q` | `56 passed in 106.52s` |
| Cross-feature regression (G2/G3/G4/G5 + N01-A/B/C + SE-02A contracts) | `py -3.14 -m pytest backend/tests/test_group4.py test_group3.py test_group2.py test_group5_*.py test_n01_*.py test_se_02a_edge_contracts.py -q` | `261 passed in 311.54s` |
| Full backend suite | `PYTHONPATH=backend/src py -3.14 -m pytest backend/tests -q` | `352 passed, 1 warning in 455.01s` (warning = pre-existing httpx/starlette deprecation) |
| Ruff | `py -3.14 -m ruff check .` | `All checks passed!` |
| Byte-compile | `py -3.14 -m compileall -q backend/src backend/tests scripts` | exit `0` |
| Whitespace | `git diff --check` / `git diff --cached --check` | exit `0` / exit `0` |

#### Adversarial reproductions after integration

| Reviewer attack | Where it was re-run | Result |
|---|---|---|
| R1 provenance (Process A `source-A`/`manifest-A`, Process B `source-B`/`manifest-B` + later BBO) | **cross-process harness** (each phase its own `py -3.14` interpreter, sharing only PostgreSQL) | 12/12 checks: resume = 1 anchor; evidence keeps A's `source_identity`/`manifest`, `evidence_at` = frozen A T0 `09:30:00`, `evidence_hash == anchor.formal_evidence_hash`, reference quote stays `99.5/100.5`, durable BBO rows contain **only** the frozen A quote, later `101.5/102.5` never persisted, exactly one anchor + one evidence revision, Process B had no current-quote accessor |
| R2 replay/redelivery protection | `test_old_redelivery_after_pre_anchor_crash_is_not_admitted_by_a_new_session` | `redelivery_admitted == False`, 0 anchors, 0 evidence |
| R3 reference provenance | `test_incomplete_bbo_provenance_is_stale_and_never_binds_an_observation` | `REFERENCE_STALE`, `bbo_id = None`, 0 BBO rows |
| R4 concurrency (real PostgreSQL) | `test_concurrent_capture_anchor_append_is_atomic_for_idempotency_and_conflict` | two writers: `INSERTED` + `IDEMPOTENT` for the same hash, different hash fails closed, 1 row |
| R5 hash tampering (candidate / T0 / BBO / source / session) | `test_anchor_tampering_of_any_duplicated_causal_fact_fails_closed` | all five tampered variants fail closed |
| R6 durable orphan (fresh process) | in-suite test + **cross-process harness** | 7/7 checks: Process B classifies the orphan, writes 1 orphan row and no evidence; a third fresh interpreter sees `UNVERIFIABLE_ORPHAN` (`durable_g2_precondition_incompatible`), resume = 0, evidence = 0, anchor still single |

#### N01-7 accepted migration gate

`scripts/verify_n01_7_f01_r1_migration_gate.py` is accepted-batch evidence and is
**frozen**, so it was not edited. Run unchanged it now stops at its own
head-pinned assertion (line 808): `heads = ['20260913_0008']`,
`single_head = False`, `f01_down_revision = '20260911_0005'`. That is the
expected consequence of the schema head legitimately moving; it is not a
regression of N01-7 semantics. Re-running the *unmodified* script with only
`_single_head` replaced by a head-aware equivalent ("exactly one head, and
`20260912_0006` is its ancestor") returned `result = PASS` with every semantic
step intact: `0005` has no protection columns; `0005 -> 0006` adds exactly the
five protection columns and three CHECK constraints with unchanged row counts;
the legacy conversion matrix and the R1-gap teeth witness reproduce; `0006 ->
0005` removes only the F01 delta with identical legacy fingerprints; re-upgrade
reproduces byte-identical values; the simulated shared primary stayed at
`20260905_0004` with 0 disposable residue.

#### Preservation evidence

- **Reviewed FIX-01 source is byte-identical** to `bdb1af2` for every
  production/test file it owns: `edge/capture.py`, `edge/hashing.py`,
  `edge/repository.py`, `g2/repository.py`, `g2/runtime.py`,
  `test_se_02b_attribution.py`, `test_se_02b_opportunity_capture.py`.
- Files that intentionally differ from the branch: the two migrations
  (renamed/reparented), `db/models.py` (+N01-7 side only), `g5/replay.py`
  (schema head), `test_se_02a_edge_persistence.py` (schema head + new integrated
  chain test), and the three state/dev_log documents.
- **Accepted Main is preserved**: of the 21 paths changed by main since the task
  base, 16 are byte-identical in the integration index; the only five that differ
  are the intended semantic-union/head/test/doc files above. Every N01-7
  production file (`g3/models.py`, `g3/protection_snapshot.py`, `g3/service.py`,
  `g4/control.py`, `g4/planning.py`, `g4/protection.py`, `g4/reconciliation.py`,
  `20260912_0006_position_protection_snapshot.py`, `test_group4.py`, the
  N01-7 migration gate script and its dev_logs) is byte-identical to `main`.

#### Remaining risks / open items

1. `scripts/verify_n01_7_f01_r1_migration_gate.py` remains head-pinned to
   `20260912_0006`. It cannot pass again until a human decides to re-baseline its
   expected head or supersede it; it must not be silently edited, because it is
   accepted-batch evidence.
2. `test_group3.py`, `test_group4.py` and the `test_group5_*` files read
   `Settings().database_url` directly and have no scoped override, so they
   require the ambient database to already carry the schema (migrated to head).
   Pointing `DATABASE_URL` at an isolated instance *that has not been migrated*
   makes them fail with `relation ... does not exist`. This is a pre-existing
   project hazard, not something this integration introduces.
3. FIX-01 stays `NOT ACCEPTED`. Independent re-review must inspect the cumulative
   `main..HEAD` diff, not only the integration commit, and must re-check the six
   original P1 findings, F07, the migration integration and the N01-7 regression.
4. Scope of the shared-database isolation evidence: it is a **revision and table
   inventory fingerprint** (`20260905_0004`, 24 tables, identical before and
   after), not a row-level data fingerprint. A second, unrelated window was
   observed running its own isolated instance on `:5435` during this batch, so
   the re-reviewer should treat "the shared acceptance database was not written
   by this batch" as bounded by that measurement, exactly as the earlier
   `FOREIGN WRITER CONFIRMED` adjudication taught for a shared primary.

