# SE-02D-CLOSE-D01｜V1 Completion Boundary Reconciliation

> **STATUS: DESIGN CANDIDATE — NOT HUMAN ACCEPTED**
>
> Task: `SE-02D-CLOSE-D01`
>
> Task Type: `DESIGN / GOVERNANCE / REPOSITORY EVIDENCE RECONCILIATION`
>
> Execution Mode: `DESIGN-ONLY / NO IMPLEMENTATION`
>
> Branch: `design/se-02d-close-d01-v1-completion-boundary`
>
> Verified Task Base: `779eaf1ca781d64733c8264b0a06c7601deacdba`

## 1. Baseline / Repository Truth

### 1.1 Live preflight

| Item | Verified value |
|---|---|
| Global Protocol live `main` | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| Global Protocol tag `protocol-v1.1.0` | `07e2df83266d4ecdea46caff5c61f000937b8913` |
| `AI_BOOTSTRAP.md` | Protocol Version `1.1.0`; Protocol Status `ACCEPTED` |
| local `main` | `779eaf1ca781d64733c8264b0a06c7601deacdba` |
| fetched `origin/main` | `779eaf1ca781d64733c8264b0a06c7601deacdba` |
| task worktree HEAD | `779eaf1ca781d64733c8264b0a06c7601deacdba` |
| task worktree before write | clean |
| original shared checkout | unrelated dirty `prb-01-product-requirements-baseline`; preserved and not used for task writes |

`BASELINE MISMATCH = NO`.

### 1.2 Accepted lineage and evidence inputs

| Artifact | Repository truth |
|---|---|
| `SE-02D-D01` | `ACCEPTED / COMPLETE`; Human-Accepted candidate `245b068199b7e6f3d32bf67e3b00163e4804afdf`; accepted contract is `docs/design/SE-02D/SE-02D-D01-Family-Aggregation-Expectancy-Contract.md` |
| `SE-02D-I01` | `ACCEPTED / COMPLETE`; reviewed candidate `13b37dff4b8150dea869ba6257ae9f3df24cc1e5`; current source `backend/src/marketpulse/edge/aggregation.py` |
| `SE-02D-I02` | `ACCEPTED / COMPLETE`; reviewed candidate `9b860437b14f64192d3298d30c0204bed1b118f8`; current source `backend/src/marketpulse/edge/aggregation_snapshot.py` |
| `SE-02D-I03` | `ACCEPTED / COMPLETE`; reviewed HEAD `20a7c333abf81077c409811302331119dff485a5`; current source `backend/src/marketpulse/edge/aggregation_orchestration.py` |
| integrated accepted baseline | `main@779eaf1`; contains the accepted I01 implementation and content-level accepted I02/I03 implementation plus final closeouts |
| `SE-02D-NEXT-R01` | no report/evidence artifact with this identifier was found in the available workspace; it is optional input and is not used to fill any evidence gap |

Current `PROJECT_STATE.md`, `AI_CONTEXT.md`, and `DECISIONS.md` all preserve the sentence that aggregate/API/product integration is not implemented. They are state summaries and routing evidence; the exact V1 completion requirement must be decided from the Human-Accepted D01 contract and actual accepted implementation.

## 2. Question Being Reconciled

Exact question:

> Has the Human-Accepted SE-02D V1 contract already been fully implemented by I01 + I02 + I03?

This reconciliation separates three different statements which must not be collapsed:

1. whether the D01-defined callable current-snapshot capability exists;
2. whether a production consumer/API/UI currently calls it;
3. whether Gate C prerequisites and Live authorization exist.

Only item 1 is the SE-02D V1 completion question.

## 3. Authority / Precedence

1. `AGENTS.md` and the Global Protocol govern execution and evidence discipline.
2. The Human-Accepted D01 artifact is the most specific normative authority for SE-02D V1 responsibilities.
3. `DECISIONS.md` is an accepted decision index and mirrors D01; it does not broaden D01.
4. Current source plus tests prove what I01/I02/I03 implement. Acceptance closeouts prove Human Acceptance status but do not replace source inspection.
5. Accepted PRE-01A-D1 governs the later Real AI experiment and Gate C. Its pair/arm requirements do not silently enlarge D01's later, more specific family-level V1 boundary.
6. `PROJECT_STATE.md`, `AI_CONTEXT.md`, and `dev_log` are state/evidence records. Their natural-language “remaining work” wording cannot create a requirement absent from D01.

The accepted authorities are consistent when their ownership is preserved:

- D01 §§1.4, 15.1, and 16 define an on-demand, serializable result capability and exclude API/frontend/runtime implementation.
- D01 §15.3 explicitly keeps SE-02D V1 family-level and experiment-arm agnostic.
- PRE-01A-D1 §§13, 17–19 requires explicit pair/arm identity and arm delta before Gate C, so the future Gate C consumer must compose those facts with SE-02D evidence.
- Therefore “SE-02D capability complete” and “Gate C ready” are different states, exactly as D01 §1.5 requires.

## 4. D01 → I01/I02/I03 Complete Coverage Matrix

Status vocabulary is restricted to the task card vocabulary. “Blocks V1” refers only to the D01 current-snapshot V1 capability, not Gate C.

| ID | D01 authoritative requirement | Implementing artifact and exact source symbol | Verification/test evidence | Status | Blocks SE-02D V1 completion? |
|---|---|---|---|---|---|
| A | §§3, 4.1–4.3: one sample is `(population_key, horizon, opportunity_id)` after full canonicalization; no double count | I01 `CanonicalScopeFacts`, `sample_identity()`, `_validate_and_order()`; I02 `_project()`; I03 `aggregate_projection()` | `test_duplicate_sample_identity_fails_closed`; `test_measurement_signature_does_not_create_a_second_sample`; `test_superseded_revision_cannot_remain_in_old_population_key` | `IMPLEMENTED` | No |
| B | §§4.2, 5.1: validate complete visible Evidence chain before membership and select highest valid head | I02 `_fold_evidence_chains()`; `CurrentSnapshotRevisionReader._read_in_session()` loads all Evidence rows before folding | `test_evidence_rev1_to_rev3_canonical_rev3`; `test_evidence_revision_gap_fails_closed`; `test_revision_mutable_source_head_only_determines_population_key`; `test_no_query_time_revision_filtering_resurrects_old_population` | `IMPLEMENTED` | No |
| C | §§4.2, 5.1: validate complete exact-horizon Outcome chain and select its highest valid head | I02 `_fold_outcome_chains()` and `_project()` | `test_outcome_rev1_to_rev2_canonical_rev2`; `test_outcome_revision_gap_fails_closed`; `test_outcome_wrong_supersedes_fails_closed`; `test_folded_outcome_count_correct` | `IMPLEMENTED` | No |
| D | §§5.1, 9.1: one current stable PostgreSQL snapshot owns Evidence, Outcome, membership, counts, and manifest | I02 `CurrentSnapshotRevisionReader.read()` / `_read_in_session()` | `test_snapshot_a_transaction_ordering`; `test_snapshot_b_late_evidence_correction`; `test_snapshot_c_late_outcome_correction`; `test_input_permutation_cannot_change_projection` | `IMPLEMENTED` | No |
| E | §§5.1, 9.1: `as_of` is UTC database `statement_timestamp()` and maturity cutoff, not Python time | I02 `CurrentSnapshotRevisionReader.read()` lines executing `SET TRANSACTION ... REPEATABLE READ READ ONLY` then `SELECT statement_timestamp()`; I03 forwards `projection.as_of`; I01 `aggregate()` uses it | `test_snapshot_d_as_of_is_database_statement_time`; `test_one_population_preserves_identity_horizon_and_as_of` | `IMPLEMENTED` | No |
| F | §6.1: seven-field structural Population Key comes only from canonical Evidence head | I01 `PopulationKey`; I02 `_project()` constructs it from the Evidence head; I03 `_ordered_population_groups()` groups by the dataclass itself | `test_population_key_field_set_and_order_match_accepted_contract`; `test_population_key_equality_and_separation`; `test_exactly_one_i01_call_per_structural_population_key`; `test_population_keys_come_from_the_facts_themselves` | `IMPLEMENTED` | No |
| G | §§3, 6.1: Population Aggregate Identity is `(Population Key, horizon)` | I01 `AggregateIdentity`; `AggregationResult.identity`; I03 invokes one `aggregate()` per population for the projection horizon | `test_result_exposes_the_population_aggregate_identity`; `test_horizon_separation`; `test_one_population_makes_exactly_one_i01_call` | `IMPLEMENTED` | No |
| H | §§3, 6.1–6.2: six-field Measurement Signature is Outcome-derived compatibility only | I01 `MeasurementSignature`; I02 `_project()` derives it from canonical Outcome; I01 `aggregate()` uses structural distinctness | `test_measurement_signature_field_set_and_order_match_accepted_contract`; `test_measurement_signature_does_not_create_a_second_sample`; `test_measurement_signature_uses_canonical_outcome_only`; `test_r1_structural_fields_are_the_signature_equality_authority` | `IMPLEMENTED` | No |
| I | §§4.2, 6.1, 8.2: absence of exact-scope Outcome constructs `NO_OUTCOME` then mature `MISSING_OUTCOME` without guessed Outcome fields | I02 `_project()` creates `CanonicalScopeFacts(outcome_id=None)` and `no_outcome`; I01 `CanonicalScopeFacts.__post_init__()` and `classify_maturity()` | `test_no_outcome_explicit_no_outcome`; `test_i02_manifest_no_outcome_preserves_i01_no_measurement`; `test_no_outcome_marker_must_not_carry_outcome_fields`; `test_missing_outcome_lands_in_its_own_coverage_class` | `IMPLEMENTED` | No |
| J | §8: complete population-based coverage denominator, rates, status/reason/folding counts and integrity visibility | I01 `CoverageReport`, `_reason_token()`, `_histogram()`, and coverage construction inside `aggregate()`; I02 supplies folding/exclusion counts | `test_every_mature_status_is_counted_exactly_once`; `test_zero_mature_denominator_gives_null_coverage_rate`; `test_coverage_diagnostics_are_reported_in_full`; `test_unknown_outcome_reason_is_preserved_not_rewritten`; `test_evidence_lower_revisions_folded`; `test_folded_evidence_outcomes_excluded_not_in_economic_facts`; `test_outcomes_excluded_with_folded_evidence_count_correct`; `test_folded_outcome_count_correct` | `IMPLEMENTED` | No |
| K | §7: deterministic mean of finite canonical COMPLETE `cost_adjusted_forward_return`, plus required descriptive set | I01 `economic_statistics()` and `aggregate()` | `test_expectancy_is_deterministic_fsum_over_cost_adjusted_returns`; `test_descriptive_statistics_values`; `test_median_of_odd_count_is_the_middle_sample`; `test_sample_standard_deviation_uses_n_minus_one_denominator`; `test_sample_standard_deviation_is_null_below_two_samples`; `test_zero_complete_signatures_is_not_calculable` | `IMPLEMENTED` | No |
| L | §§4, 7.1, 9: deterministic ordering, permutation invariance, no database-order dependence | I01 sorting in `build_ordered_input_manifest()`, `_validate_and_order()`, `aggregate()`; I02 ordered projection/manifest; I03 `_ordered_population_groups()` and `_manifest_subset()` | `test_input_permutation_invariance`; `test_sample_ordering_is_lexical_ascending`; `test_input_permutation_cannot_change_projection`; `test_permuted_facts_and_manifest_produce_identical_results`; `test_multi_population_results_are_ordered_by_canonical_key` | `IMPLEMENTED` | No |
| M | §10: deterministic overlap-cluster percentile bootstrap, 10,000 replicates, fixed indices, SHA-256 counter rejection, explicit unavailable cases | I01 `cluster_samples()`, `bootstrap_seed()`, `draw_cluster_index()`, `replicate_means()`, `percentile_interval()` | `test_non_overlapping_intervals_form_separate_clusters`; `test_touching_intervals_form_one_cluster`; `test_transitive_overlap_collapses_into_one_cluster`; `test_rng_golden_vector`; `test_seed_derivation_golden`; `test_bootstrap_reproducibility`; `test_percentile_indices_match_the_frozen_quantile_rule`; `test_too_few_clusters_gives_null_interval`; `test_identical_returns_are_degenerate_not_high_certainty` | `IMPLEMENTED` | No |
| N | §12.1: no fixed raw N; 100% coverage, at least 3 clusters, non-degenerate interval excluding zero, stable LOCO | I01 sufficiency construction in `aggregate()` and `SufficiencyReason` | `test_resolved_positive_case_is_sufficient`; `test_resolved_negative_case_is_sufficient`; `test_coverage_below_one_is_insufficient`; `test_interval_crossing_zero_is_insufficient`; `test_loco_instability_is_insufficient` | `IMPLEMENTED` | No |
| O | §12.1: leave one whole overlap cluster out and require same interval-side classification | I01 `leave_one_cluster_out()` and `LocoResult` | `test_loco_recomputes_uncertainty_for_every_cluster`; `test_loco_is_deterministic`; `test_loco_instability_is_insufficient` | `IMPLEMENTED` | No |
| P | §12.2: `worst_observation` and exact worst-decile mean; no threshold | I01 `worst_decile_k()`, `economic_statistics()`, `TailEvidence` | `test_worst_observation_and_worst_decile_mean`; `test_worst_decile_mean_averages_the_k_smallest`; `test_tail_evidence_has_no_threshold` | `IMPLEMENTED` | No |
| Q | §§9, 15.1, 16: deterministic full manifest/fingerprint and immutable serializable result | I01 `build_ordered_input_manifest()`, `compute_input_fingerprint()`, `AggregationResult.to_dict()`; I02 `_project()` extends the base manifest with every revision identity; I03 passes the revision-aware subset verbatim | `test_fingerprint_reproducibility`; `test_fingerprint_manifest_sensitivity`; `test_fingerprint_binds_the_return_bits`; `test_manifest_includes_all_evidence_revision_identities`; `test_manifest_includes_all_exact_outcome_revision_identities`; `test_i02_manifest_preserves_every_i01_base_key_and_value`; `test_i02_manifest_complete_numeric_hex_bindings_match_i01`; `test_revision_aware_manifest_is_supplied_to_i01_not_rebuilt`; `test_result_object_is_serializable_and_immutable` | `IMPLEMENTED` | No |
| R | §6.3: `source_manifest_id` is provenance/stratification, not population/signature; report manifest concentration | I01 `ManifestDiagnostics` and `PopulationKey`; I02 carries head manifest provenance; I03 grouping excludes manifest | `test_manifest_is_not_a_population_key_field`; `test_source_manifest_id_does_not_split_population`; manifest diagnostic coverage in `test_coverage_diagnostics_are_reported_in_full` | `IMPLEMENTED` | No |
| S | §6.2: mixed COMPLETE signatures keep coverage but fail headline economic statistics closed | I01 status precedence in `aggregate()`; I03 keeps the population together and delegates once | `test_mixed_measurement_signatures_fail_closed_without_losing_coverage`; `test_integrity_conflict_outranks_incompatible_signatures`; `test_mixed_measurement_signature_does_not_split_population` | `IMPLEMENTED` | No |
| T | §6.4 and D01-F05: SPOT applicable; SWAP primary expectancy `NOT_APPLICABLE`, with coverage retained and market types separated | I01 `aggregate()` applicability branch; I03 does not filter and groups by full Population Key | `test_swap_is_not_applicable_but_keeps_coverage`; `test_spot_and_swap_populations_stay_separate`; `test_swap_population_is_not_filtered_and_reaches_i01` | `IMPLEMENTED` | No |
| U | §14: SE-02D V1 emits evidence only and owns no KEEP/DOWNWEIGHT/KILL label or policy | I01 `AggregationResult` deliberately has no K/D/K field; I03 recomputes no policy | `test_no_keep_downweight_kill_output`; `test_module_has_no_direct_database_or_runtime_imports` | `INTENTIONALLY OUT OF SCOPE IN V1` | No |
| V | §15.1: V1 persistence strategy is deterministic on-demand derived aggregate; no table/view/worker/scheduler/daemon | I03 `aggregate_current_snapshot()` composes one read with `aggregate_projection()`; I01 returns frozen `AggregationResult`; I02 is read-only and rolls back | `test_async_wrapper_reads_exactly_once_and_delegates_the_exact_projection`; `test_async_wrapper_end_to_end_matches_the_pure_orchestrator`; `test_result_object_is_serializable_and_immutable`; source inspection shows no write path | `IMPLEMENTED` | No |
| W | §§1.5, 15.2–15.3: Gate C artifact retention and decision policy are separate; capability complete is not Gate C PASS | No SE-02D implementation is required; I01 result is serializable evidence and contains no Gate C action | `test_no_keep_downweight_kill_output`; D01 accepted boundary; PRE-01A-D1 §§17–19 | `INTENTIONALLY OUT OF SCOPE IN V1` | No |
| X | §§5.2–5.3, 18 D01-F01: arbitrary historical revision-as-of is not supported without a future durable visibility/manifest prerequisite | I02 intentionally exposes `read(horizon)` with no historical `as_of`; current-snapshot selection remains implemented | `test_no_historical_as_of_interface`; source inspection of `CurrentSnapshotRevisionReader.read()` | `FUTURE PREREQUISITE` | No, for current-snapshot V1; yes for historical reconstruction claims |
| Y | §§6.4, 15.3, 18 D01-F02: experiment/pair/arm identity and arm-level delta belong to future Real AI/Gate C work | No I01/I02/I03 field or join guesses these identities; PRE-01A-D1 §13 owns the future identity contract | Source/result-shape inspection; D01 explicitly says family-level and experiment-arm agnostic | `FUTURE PREREQUISITE` | No; blocks Gate C, not SE-02D V1 |
| Z | §§10.3, 13, 18 D01-F03: no durable Accepted regime identity; expose limitation and no regime gate | I01 constants `DEPENDENCE_LIMITATIONS`, `REGIME_GATE`, `REGIME_SUFFICIENCY` and `AggregationResult` fields | `test_result_declares_limitations_an_integrity_statement_and_no_regime_gate` | `FUTURE PREREQUISITE` | No; blocks Gate C regime criteria, not SE-02D V1 |
| AA | §§6.4, 11: fixed horizons stay separate; `5m` is primary and `30s/15m/1h` are predeclared secondary views | `ForwardHorizon` is carried through I01/I02/I03; each call handles exactly one requested horizon and never pools horizons. Primary-vs-secondary presentation is a caller/reporting choice, not an extra D01 result field | `test_horizon_separation`; `test_facts_from_another_horizon_are_not_pooled_into_one_aggregate`; `test_projection_carries_requested_horizon` | `IMPLEMENTED` | No |
| AB | §§8.4, 10.3, 16: integrity statement, unobservable coverage limitation, dependence limitations, calculability, versions, and result shape | I01 version/limitation constants, `AggregationResult`, and `to_dict()` | `test_result_declares_limitations_an_integrity_statement_and_no_regime_gate`; `test_result_reports_the_frozen_version_constants`; `test_version_constants_match_the_accepted_literals` | `IMPLEMENTED` | No |
| AC | §7.2: reference/executable return and MFE/MAE aggregates are explicitly allowed diagnostics, not part of the “must report” primary set or §16 minimum result shape | I01 carries these values in `CanonicalScopeFacts` and manifest but does not publish optional aggregate diagnostics | Contract wording distinguishes “同一 C 必报” from “允许的最小诊断”; source/result-shape inspection | `INTENTIONALLY OUT OF SCOPE IN V1` | No |
| AD | §§10.2, 17: no SciPy production dependency | I01 uses Python standard library `hashlib`, `math`, and deterministic local implementation | dependency/import inspection; `test_module_has_no_direct_database_or_runtime_imports`; accepted I01 closeout | `IMPLEMENTED` | No |

Coverage verdict: every D01 current-snapshot V1 responsibility is either implemented or explicitly excluded/deferred by the accepted contract. `ACTUAL GAP` rows: **none**.

## 5. API / Product / Consumer Requirement Analysis

| Candidate item | Accepted SE-02D V1 verdict | Exact basis |
|---|---|---|
| HTTP API | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §1.4 excludes API implementation; §§15.1/16 require an on-demand result object, not transport |
| FastAPI router | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | No D01 endpoint/router/path/auth/serialization transport AC exists |
| frontend | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §1.4 explicitly excludes frontend |
| dashboard | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | No accepted D01 dashboard/reporting surface requirement exists |
| operator panel | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | No accepted D01 operator workflow requirement exists |
| RuntimeHost child | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §1.4 excludes Runtime Host implementation; I03's accepted callable wrapper is request-driven and owns no lifecycle |
| scheduler | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §15.1 explicitly says no scheduler |
| background worker / daemon | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §15.1 explicitly says no worker/daemon |
| aggregate persistence / table | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §15.1 selects deterministic on-demand derived aggregate and no aggregate table/migration |
| materialized aggregate/view | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 §15.1 explicitly excludes materialized view |
| automatic consumer | `NOT REQUIRED BY ACCEPTED SE-02D V1 CONTRACT` | D01 defines a callable evidence capability, not automatic invocation or product ownership |

The sentence “aggregate / API / product integration = NOT YET IMPLEMENTED” is accurate only as a broad product-integration observation. Applied as an SE-02D V1 completion blocker, it is stale/over-broad because “aggregate” is now implemented by the I02→I03→I01 call chain, while API/product integration was never a D01 V1 requirement.

## 6. Consumer Boundary

SE-02D V1 does **not** own a production consumer.

The accepted callable boundary is sufficient:

```text
CurrentSnapshotRevisionReader.read(horizon)
  -> CurrentSnapshotProjection
  -> aggregate_projection(projection)
  -> tuple[AggregationResult, ...]

aggregate_current_snapshot(reader, horizon)
  = exactly one read + the same pure orchestration
```

`AggregationResult` is frozen, serializable, deterministic, revision-manifest-bound evidence. A current production caller is absent, as confirmed by repository-wide reference inspection, but D01 contains no consumer acceptance criterion. Future operator/API surfaces, Gate C evidence construction, Real AI experiment analysis, or dashboard work must own their own composition and authorization; they are not retroactive SE-02D V1 responsibilities.

## 7. RuntimeHost / Session-Factory Ownership Classification

Verified current facts:

- `backend/src/marketpulse/db/session.py::DatabaseResources` owns one `AsyncEngine` and the `async_sessionmaker` derived from it; `dispose()` releases the owned engine.
- `backend/src/marketpulse/runtime_host.py::RuntimeHost._open_database()` creates/injects `DatabaseResources` and privately binds `self._sessions = self._db.session_factory`.
- RuntimeHost exposes public lifecycle/health/market/lanes/subscription properties, but no accepted public arbitrary-use session-factory accessor.
- `CurrentSnapshotRevisionReader` accepts an `async_sessionmaker` from its composing caller; it does not claim ownership of RuntimeHost or the engine.

Classification: **FUTURE CONSUMER COMPOSITION QUESTION — NOT AN SE-02D V1 BLOCKER**.

Because no Accepted SE-02D V1 consumer is required, completion does not require changing RuntimeHost ownership. This task neither proposes nor implements an accessor. A future API/runtime consumer must separately define lawful session-factory composition without weakening the accepted RuntimeHost DB ownership contract.

## 8. Persistence Classification

Accepted D01 V1 persistence is already satisfied as **deterministic on-demand derived aggregate**:

- I02 performs read-only current-snapshot projection;
- I03 performs a thin deterministic orchestration;
- I01 returns a frozen serializable `AggregationResult` with manifest and fingerprint;
- no SE-02D write, table, migration, materialized view, worker, scheduler, or daemon exists or is required.

Gate C immutable artifact retention is a separate future consumer/evidence task under D01 §15.2. Its absence is not an SE-02D V1 persistence gap.

## 9. Historical Revision-As-Of Classification

`historical arbitrary revision-as-of = OPEN / NOT SUPPORTED`.

D01 §§5.2–5.3 states that current durable timestamps cannot prove correction visibility at an arbitrary past instant. I02 correctly implements only `CURRENT_STABLE_SNAPSHOT` and has no caller-supplied historical `as_of` parameter.

Classification: **FUTURE PREREQUISITE**, not an `ACTUAL GAP` in the current-snapshot V1 contract. It must remain visible and unresolved. It blocks historical reconstruction claims, but does not block completion of the explicitly accepted current-snapshot capability.

## 10. Gate C Prerequisite Separation

The following remain open without becoming SE-02D V1 implementation responsibilities:

| Item | Classification |
|---|---|
| `experiment_id` | Future Real AI/Gate C identity prerequisite |
| `pair_id` | Future Real AI/Gate C identity prerequisite |
| `arm_id` | Future Real AI/Gate C identity prerequisite |
| arm-level selection Expectancy/delta | Future consumer/policy output after explicit identities exist |
| immutable Gate C artifact retention implementation | Future Gate C evidence task |
| durable regime identity/criteria | Future Gate C prerequisite |
| Real AI activation | Separate activation gate; not authorized |
| KEEP/DOWNWEIGHT/KILL policy | Separate versioned Human-Accepted policy, if ever retained |
| Live authorization | Separate future gate; not authorized |

The boundary remains:

```text
SE-02D capability complete != Gate C PASS
Gate C PASS != Live authorization
```

## 11. Actual Remaining Gaps, If Any

`ACTUAL SE-02D V1 IMPLEMENTATION GAPS = NONE FOUND`.

Open work exists, but belongs to different boundaries:

- historical revision-as-of prerequisite;
- Real AI experiment/pair/arm identity and arm-level analysis;
- durable regime identity/criteria;
- Gate C artifact retention and policy;
- any API/UI/operator/runtime consumer;
- Real AI and Live activation gates.

None is an Accepted D01 current-snapshot V1 completion requirement.

## 12. Candidate Completion Verdict

```text
Candidate A

SE-02D V1 CAPABILITY COMPLETE AFTER I03
```

Reason: the accepted I02→I03→I01 path implements the complete D01 current-snapshot contract from authoritative PostgreSQL snapshot through revision folding, population grouping, deterministic aggregation, uncertainty/sufficiency, manifest/fingerprint, and immutable result. No accepted D01 clause requires a production consumer or transport.

This is a **design candidate conclusion only**. It does not itself change the repository's formal SE-02D state and does not declare official completion before Independent Review and Human Acceptance.

## 13. Consequences of This Verdict

If Human accepts Candidate A:

1. no `I04` implementation batch is required for SE-02D V1;
2. the next SE-02D batch is Overall Final Review / Human Acceptance / Closeout;
3. only after Human Acceptance may state documents reconcile the stale/over-broad “aggregate / API / product integration” wording;
4. consumer work begins only under the future product/Gate C task that actually needs it;
5. historical as-of and Gate C prerequisites remain open and must not be marked resolved;
6. neither Gate C nor Live is unlocked.

## 14. Explicit Non-Claims

This artifact does **not** claim or authorize:

- official SE-02D completion before Human Acceptance;
- Gate C PASS, Real AI activation, Paper economic activation, or Live authorization;
- historical as-of support;
- experiment/pair/arm or regime implementation;
- any API, frontend, dashboard, operator panel, RuntimeHost child/accessor, worker, scheduler, daemon, persistence table, schema, migration, cache, or monitoring;
- a KEEP/DOWNWEIGHT/KILL decision;
- profitability, Trading Edge, entry/stop/target/sizing superiority, or executed-trade edge;
- state synchronization or `main` integration;
- repair of the stale `backend/src/marketpulse/edge/__init__.py` package docstring.

## 15. Human Decision Package

Human is asked to accept or reject all six conclusions:

1. `SE-02D V1` capability is complete after I03.
2. API, frontend, and runtime consumer are **not** SE-02D V1 completion requirements.
3. The existing “aggregate / API / product integration = NOT YET IMPLEMENTED” wording should later be reconciled to a deferred/future-consumer boundary.
4. Historical revision-as-of stays `OPEN` but does not block V1 current-snapshot completion.
5. Gate C prerequisites remain `OPEN`.
6. The next batch is Overall Final Review / Closeout, not an I04 implementation batch.

```text
SE-02D-CLOSE-D01 =
DESIGN CANDIDATE — READY FOR INDEPENDENT REVIEW
Candidate Verdict = SE-02D V1 CAPABILITY COMPLETE AFTER I03
```

**STATUS: DESIGN CANDIDATE — NOT HUMAN ACCEPTED**
