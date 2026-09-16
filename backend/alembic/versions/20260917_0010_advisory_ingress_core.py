"""advisory ingress core: durable invocation/attempt authority and evidence admission accounting

PRE-01B-I2, schema half of the accepted
``docs/design/PRE-01B/PRE-01B-D2-AdvisoryIngress-G2-G3-Activation-Contract.md``
(D2 §24 "Schema Decision" / §14.2 "Exactly-one authoritative terminal result").

This is deliberately **one** revision. D2 freezes exactly:

* two new minimal tables (``advisory_decision_invocations``,
  ``advisory_decision_attempts``) -- one row per logical invocation and one row per
  provider attempt;
* three minimal extensions of existing accepted tables:
  ``edge_opportunity_evidence`` (durable Advisory admission accounting),
  ``decision_snapshots`` (queryable Shadow binding facts),
  ``ai_decisions`` (Attempt origin linkage).

There is no third "final" table, no supersession marker table and no generic
job/outbox/workflow table: the Invocation row itself is the single terminal authority
(D2 §24.4).

Historical truth is preserved rather than guessed. Every Evidence row that already
exists when this revision runs was written before the Advisory accounting existed, so
it is fixed to ``LEGACY_PRE_I2`` and can never be re-classified as a Gate A member.
Only rows inserted *after* the upgrade take the new-row server default ``UNSTAGED``,
which is a bare marker (no seed, no experiment/pair/arm, no Invocation) -- never a
fabricated binding and never a fabricated deadline.

The two consistency cycles the contract depends on are closed by PostgreSQL itself,
not by service-layer convention:

* ``edge_opportunity_evidence <-> advisory_decision_invocations`` (D2 §24.2) and
* ``advisory_decision_invocations <-> advisory_decision_attempts`` /
  ``ai_decisions`` (D2 §14.2 items 3-4)

are ``DEFERRABLE INITIALLY DEFERRED``, so a single admission SAVEPOINT and a single
finalizer transaction can each commit their half of a cycle atomically instead of
requiring a temporarily half-linked state to be committed.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260917_0010"
down_revision: str | None = "20260913_0009"
branch_labels = None
depends_on = None

_INVOCATIONS = "advisory_decision_invocations"
_ATTEMPTS = "advisory_decision_attempts"
_EVIDENCE = "edge_opportunity_evidence"
_SNAPSHOTS = "decision_snapshots"
_AI_DECISIONS = "ai_decisions"

#: D2 §8.3 durable admission accounting states.
_ADMISSION_STATES = ("LEGACY_PRE_I2", "UNSTAGED", "GATE_A_DISABLED", "INVOCATION_CREATED",
                     "ADMISSION_FAILED_FINAL")
#: D2 §13.2 frozen treatment-participation vocabulary plus §8.3's unbound form.
_PARTICIPATION_VALUES = ("PARTICIPATE_LONG", "NO_LONG", "NO_LONG_UNBOUND")
#: D2 §8.3 / §15 unbound staging-failure reason constant.
_UNBOUND_REASON = "ADMISSION_STAGING_FAILED_UNBOUND"
#: D2 §14.2 item 2 -- the exhaustively enumerated no-provider-Attempt terminals.
_NO_ATTEMPT_FINAL_REASONS = (
    "DEADLINE_EXPIRED_BEFORE_PROVIDER",
    "CAPACITY_BLOCKED",
    "EVIDENCE_SUPERSEDED_BEFORE_PROVIDER",
    "OPPORTUNITY_STALE_BEFORE_PROVIDER",
    "ACTIVATION_DISABLED_BEFORE_PROVIDER",
    "SHUTDOWN_BEFORE_PROVIDER",
)
#: D2 §14.1 invocation execution states (not a `DecisionStatus`).
_INVOCATION_STATES = ("ADMITTED", "ACTIVE", "RETRY_PENDING", "FINAL")
#: D2 §14.3/§14.4/§15 attempt execution lifecycle. Every literal appears verbatim in D2.
_ATTEMPT_STATES = (
    "STARTED",
    "COMPLETED",
    "PROCESS_LOST",
    "ABANDONED",
    "DUPLICATE_SUPPRESSED",
    "LATE_RESULT",
)


def _quote(values: tuple[str, ...]) -> str:
    return ", ".join(f"'{value}'" for value in values)


def upgrade() -> None:
    # --------------------------------------------------------------------------------------
    # 1 -- advisory_decision_invocations: the single logical final-result authority.
    # --------------------------------------------------------------------------------------
    op.create_table(
        _INVOCATIONS,
        sa.Column("decision_invocation_id", sa.String(64), primary_key=True),
        sa.Column("snapshot_id", sa.String(64), nullable=False),
        sa.Column("opportunity_id", sa.String(64), nullable=False),
        sa.Column("evidence_id", sa.String(64), nullable=False),
        sa.Column("evidence_revision", sa.Integer(), nullable=False),
        sa.Column("evidence_hash", sa.String(64), nullable=False),
        sa.Column("feature_snapshot_hash", sa.String(64), nullable=False),
        sa.Column("experiment_id", sa.String(64), nullable=False),
        sa.Column("experiment_definition_digest", sa.String(64), nullable=False),
        sa.Column("pair_id", sa.String(64), nullable=False),
        sa.Column("baseline_arm_id", sa.String(64), nullable=False),
        sa.Column("treatment_arm_id", sa.String(64), nullable=False),
        sa.Column("arm_id", sa.String(64), nullable=False),
        sa.Column("baseline_policy_version", sa.String(64), nullable=False),
        sa.Column("baseline_participation", sa.String(32), nullable=False),
        sa.Column("input_binding_digest", sa.String(64), nullable=False),
        sa.Column("prompt_version", sa.String(64), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("treatment_version", sa.String(64), nullable=False),
        sa.Column("configured_provider_id", sa.String(128), nullable=False),
        sa.Column("configured_model_id", sa.String(128), nullable=False),
        sa.Column("decision_requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision_deadline_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("final_status", sa.String(32), nullable=True),
        sa.Column("final_reason_code", sa.String(64), nullable=True),
        sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_attempt_id", sa.String(64), nullable=True),
        sa.Column("final_decision_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], [f"{_SNAPSHOTS}.snapshot_id"], name="fk_advisory_invocation_snapshot"
        ),
        # D2 §24.2: one half of the Evidence <-> Invocation cycle, deferrable so the
        # admission SAVEPOINT inserts both sides in one transaction.
        sa.ForeignKeyConstraint(
            ["evidence_id", "opportunity_id"],
            [f"{_EVIDENCE}.evidence_id", f"{_EVIDENCE}.opportunity_id"],
            name="fk_advisory_invocation_evidence",
            deferrable=True,
            initially="DEFERRED",
        ),
        sa.UniqueConstraint(
            "experiment_id", "pair_id", "arm_id", name="uq_advisory_invocation_experiment_pair_arm"
        ),
        sa.CheckConstraint(
            f"state IN ({_quote(_INVOCATION_STATES)})", name="ck_advisory_invocation_state"
        ),
        sa.CheckConstraint("evidence_revision >= 1", name="ck_advisory_invocation_revision_positive"),
        sa.CheckConstraint(
            "decision_deadline_at > decision_requested_at",
            name="ck_advisory_invocation_deadline_order",
        ),
        sa.CheckConstraint("updated_at >= created_at", name="ck_advisory_invocation_updated_order"),
        # D2 §14.2 item 1: `state = FINAL` iff the three core final fields are all present.
        sa.CheckConstraint(
            "(state = 'FINAL' AND final_status IS NOT NULL AND final_reason_code IS NOT NULL "
            "AND finalized_at IS NOT NULL) "
            "OR (state <> 'FINAL' AND final_status IS NULL AND final_reason_code IS NULL "
            "AND finalized_at IS NULL AND final_attempt_id IS NULL AND final_decision_id IS NULL)",
            name="ck_advisory_invocation_final_completeness",
        ),
        # D2 §14.2 item 2: a NULL final Attempt is legal only for the enumerated terminals.
        sa.CheckConstraint(
            "final_attempt_id IS NOT NULL OR final_reason_code IS NULL "
            f"OR final_reason_code IN ({_quote(_NO_ATTEMPT_FINAL_REASONS)})",
            name="ck_advisory_invocation_no_attempt_reason",
        ),
        # D2 §14.2 item 4: a final decision can never outlive a missing final Attempt.
        sa.CheckConstraint(
            "final_decision_id IS NULL OR final_attempt_id IS NOT NULL",
            name="ck_advisory_invocation_final_decision_requires_attempt",
        ),
    )
    op.create_index(
        f"ix_{_INVOCATIONS}_state", _INVOCATIONS, ["state", "decision_deadline_at"]
    )
    op.create_index(f"ix_{_INVOCATIONS}_opportunity", _INVOCATIONS, ["opportunity_id"])

    # --------------------------------------------------------------------------------------
    # 2 -- advisory_decision_attempts: durable provenance for every provider attempt.
    # --------------------------------------------------------------------------------------
    op.create_table(
        _ATTEMPTS,
        sa.Column("attempt_id", sa.String(64), primary_key=True),
        sa.Column("decision_invocation_id", sa.String(64), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("attempt_state", sa.String(32), nullable=False),
        sa.Column("retry_class", sa.String(32), nullable=True),
        sa.Column("retry_reason", sa.String(64), nullable=True),
        sa.Column("prior_attempt_id", sa.String(64), nullable=True),
        sa.Column("provider_request_id", sa.String(128), nullable=True),
        sa.Column("provider_response_id", sa.String(128), nullable=True),
        sa.Column("configured_provider_id", sa.String(128), nullable=False),
        sa.Column("configured_model_id", sa.String(128), nullable=False),
        sa.Column("provider_reported_model_id", sa.String(128), nullable=True),
        sa.Column("input_binding_digest", sa.String(64), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("provider_outcome", sa.String(64), nullable=True),
        sa.Column("normalized_status", sa.String(32), nullable=True),
        sa.Column("error_category", sa.String(64), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=True),
        sa.Column("output_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("usage_unavailable_reason", sa.String(64), nullable=True),
        sa.Column("monetary_cost", sa.Numeric(18, 8), nullable=True),
        sa.Column("pricing_version", sa.String(64), nullable=True),
        sa.Column("output_digest", sa.String(64), nullable=True),
        sa.Column("validation_result", sa.String(32), nullable=True),
        sa.Column("validation_errors", postgresql.JSONB(), nullable=True),
        sa.Column("redacted_request_envelope", postgresql.JSONB(), nullable=True),
        sa.Column("redacted_response_envelope", postgresql.JSONB(), nullable=True),
        sa.ForeignKeyConstraint(
            ["decision_invocation_id"],
            [f"{_INVOCATIONS}.decision_invocation_id"],
            name="fk_advisory_attempt_invocation",
        ),
        # Retry lineage must stay inside one Invocation (D2 §14.3/§23: same invocation,
        # same input binding, same original deadline).
        sa.ForeignKeyConstraint(
            ["decision_invocation_id", "prior_attempt_id"],
            [f"{_ATTEMPTS}.decision_invocation_id", f"{_ATTEMPTS}.attempt_id"],
            name="fk_advisory_attempt_prior",
        ),
        sa.UniqueConstraint(
            "decision_invocation_id", "attempt_number", name="uq_advisory_attempt_invocation_number"
        ),
        sa.UniqueConstraint(
            "decision_invocation_id", "attempt_id", name="uq_advisory_attempt_invocation_attempt"
        ),
        sa.CheckConstraint("attempt_number >= 1", name="ck_advisory_attempt_number_positive"),
        sa.CheckConstraint(
            f"attempt_state IN ({_quote(_ATTEMPT_STATES)})", name="ck_advisory_attempt_state"
        ),
        sa.CheckConstraint(
            "prior_attempt_id IS NULL OR attempt_number > 1",
            name="ck_advisory_attempt_prior_number",
        ),
        sa.CheckConstraint(
            "retry_reason IS NULL OR retry_class IS NOT NULL", name="ck_advisory_attempt_retry_pair"
        ),
        sa.CheckConstraint("latency_ms IS NULL OR latency_ms >= 0", name="ck_advisory_attempt_latency"),
        sa.CheckConstraint(
            "(input_tokens IS NULL AND output_tokens IS NULL AND total_tokens IS NULL) "
            "OR usage_unavailable_reason IS NULL",
            name="ck_advisory_attempt_usage_exclusive",
        ),
        sa.CheckConstraint(
            "(input_tokens IS NULL OR input_tokens >= 0) "
            "AND (output_tokens IS NULL OR output_tokens >= 0) "
            "AND (total_tokens IS NULL OR total_tokens >= 0)",
            name="ck_advisory_attempt_usage_non_negative",
        ),
        sa.CheckConstraint(
            "(monetary_cost IS NULL AND pricing_version IS NULL) "
            "OR (monetary_cost IS NOT NULL AND pricing_version IS NOT NULL)",
            name="ck_advisory_attempt_cost_pair",
        ),
        sa.CheckConstraint(
            "monetary_cost IS NULL OR monetary_cost >= 0", name="ck_advisory_attempt_cost_non_negative"
        ),
    )

    # --------------------------------------------------------------------------------------
    # 3 -- Invocation -> Attempt deferred composite FK (D2 §14.2 item 2).
    # --------------------------------------------------------------------------------------
    op.create_foreign_key(
        "fk_advisory_invocation_final_attempt",
        _INVOCATIONS,
        _ATTEMPTS,
        ["decision_invocation_id", "final_attempt_id"],
        ["decision_invocation_id", "attempt_id"],
        deferrable=True,
        initially="DEFERRED",
    )

    # --------------------------------------------------------------------------------------
    # 4 -- ai_decisions: Attempt-origin linkage for Advisory rows only.
    # --------------------------------------------------------------------------------------
    op.add_column(_AI_DECISIONS, sa.Column("decision_invocation_id", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("attempt_id", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("input_binding_digest", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("experiment_id", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("pair_id", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("arm_id", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("provider_id", sa.String(128), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("configured_model_id", sa.String(128), nullable=True))
    op.add_column(
        _AI_DECISIONS, sa.Column("provider_reported_model_id", sa.String(128), nullable=True)
    )
    op.add_column(_AI_DECISIONS, sa.Column("output_digest", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("error_category", sa.String(64), nullable=True))
    op.add_column(_AI_DECISIONS, sa.Column("finalized_at", sa.DateTime(timezone=True), nullable=True))
    # D2 §14.2 item 3: a new Advisory AIDecision always carries both origin facts, so a
    # provider result can never exist without a durable Attempt provenance. Legacy
    # non-Advisory rows carry neither and stay valid.
    op.create_check_constraint(
        "ck_ai_decisions_advisory_origin_pair",
        _AI_DECISIONS,
        "(decision_invocation_id IS NULL AND attempt_id IS NULL) "
        "OR (decision_invocation_id IS NOT NULL AND attempt_id IS NOT NULL)",
    )
    # D2 §14.2 item 3/§14.4: exactly one normalized winner per Invocation, and the Attempt
    # must belong to that same Invocation.
    op.create_unique_constraint(
        "uq_ai_decisions_advisory_origin",
        _AI_DECISIONS,
        ["decision_invocation_id", "decision_id", "attempt_id"],
    )
    op.create_index(
        "uq_ai_decisions_advisory_invocation",
        _AI_DECISIONS,
        ["decision_invocation_id"],
        unique=True,
        postgresql_where=sa.text("decision_invocation_id IS NOT NULL"),
    )
    op.create_foreign_key(
        "fk_ai_decisions_advisory_attempt",
        _AI_DECISIONS,
        _ATTEMPTS,
        ["decision_invocation_id", "attempt_id"],
        ["decision_invocation_id", "attempt_id"],
        deferrable=True,
        initially="DEFERRED",
    )

    # --------------------------------------------------------------------------------------
    # 5 -- Invocation -> AIDecision deferred composite FK (D2 §14.2 item 4).
    # --------------------------------------------------------------------------------------
    op.create_foreign_key(
        "fk_advisory_invocation_final_decision",
        _INVOCATIONS,
        _AI_DECISIONS,
        ["decision_invocation_id", "final_decision_id", "final_attempt_id"],
        ["decision_invocation_id", "decision_id", "attempt_id"],
        deferrable=True,
        initially="DEFERRED",
    )

    # --------------------------------------------------------------------------------------
    # 6 -- decision_snapshots: queryable immutable Shadow binding facts (D2 §24.2).
    # --------------------------------------------------------------------------------------
    op.add_column(_SNAPSHOTS, sa.Column("decision_invocation_id", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("opportunity_id", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("evidence_id", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("evidence_revision", sa.Integer(), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("evidence_hash", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("feature_snapshot_hash", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("market_type", sa.String(16), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("snapshot_payload_hash", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("input_binding_digest", sa.String(64), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("advisory_config_epoch_id", sa.String(64), nullable=True))
    op.add_column(
        _SNAPSHOTS, sa.Column("decision_requested_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(_SNAPSHOTS, sa.Column("deadline_duration_ms", sa.Integer(), nullable=True))
    op.add_column(_SNAPSHOTS, sa.Column("deadline_policy_version", sa.String(64), nullable=True))
    op.add_column(
        _SNAPSHOTS, sa.Column("decision_deadline_at", sa.DateTime(timezone=True), nullable=True)
    )
    # Legacy snapshots carry none of the Shadow binding facts; a Shadow snapshot must carry
    # the complete binding or none of it, so a half-written binding cannot be read as valid.
    op.create_check_constraint(
        "ck_decision_snapshots_advisory_binding_atomic",
        _SNAPSHOTS,
        "(decision_invocation_id IS NULL AND evidence_id IS NULL AND input_binding_digest IS NULL "
        "AND decision_requested_at IS NULL AND decision_deadline_at IS NULL) "
        "OR (decision_invocation_id IS NOT NULL AND evidence_id IS NOT NULL "
        "AND input_binding_digest IS NOT NULL AND decision_requested_at IS NOT NULL "
        "AND decision_deadline_at IS NOT NULL)",
    )
    op.create_check_constraint(
        "ck_decision_snapshots_advisory_evidence_revision",
        _SNAPSHOTS,
        "evidence_revision IS NULL OR evidence_revision >= 1",
    )
    op.create_check_constraint(
        "ck_decision_snapshots_advisory_deadline_positive",
        _SNAPSHOTS,
        "deadline_duration_ms IS NULL OR deadline_duration_ms > 0",
    )
    op.create_check_constraint(
        "ck_decision_snapshots_advisory_deadline_order",
        _SNAPSHOTS,
        "decision_deadline_at IS NULL OR decision_deadline_at > decision_requested_at",
    )

    # --------------------------------------------------------------------------------------
    # 7 -- edge_opportunity_evidence: durable Advisory admission accounting (D2 §24.2).
    # --------------------------------------------------------------------------------------
    op.add_column(
        _EVIDENCE, sa.Column("advisory_admission_state", sa.String(32), nullable=True)
    )
    op.add_column(
        _EVIDENCE, sa.Column("advisory_admission_reason_code", sa.String(64), nullable=True)
    )
    op.add_column(
        _EVIDENCE, sa.Column("advisory_treatment_participation", sa.String(32), nullable=True)
    )
    op.add_column(
        _EVIDENCE, sa.Column("advisory_admission_seed_version", sa.String(64), nullable=True)
    )
    op.add_column(
        _EVIDENCE, sa.Column("advisory_admission_seed_digest", sa.String(64), nullable=True)
    )
    op.add_column(
        _EVIDENCE, sa.Column("advisory_admission_seed", postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        _EVIDENCE, sa.Column("advisory_decision_invocation_id", sa.String(64), nullable=True)
    )
    # Historical truth first: every Evidence row written before this revision predates the
    # Advisory accounting, so it is fixed to LEGACY_PRE_I2 -- never treated as a Gate A
    # member, never backfilled with a fabricated experiment/pair/arm.
    op.execute(
        sa.text(
            f"UPDATE {_EVIDENCE} SET advisory_admission_state = 'LEGACY_PRE_I2' "
            "WHERE advisory_admission_state IS NULL"
        )
    )
    op.alter_column(
        _EVIDENCE,
        "advisory_admission_state",
        nullable=False,
        server_default=sa.text("'UNSTAGED'"),
    )
    op.create_check_constraint(
        "ck_advisory_evidence_state",
        _EVIDENCE,
        f"advisory_admission_state IN ({_quote(_ADMISSION_STATES)})",
    )
    op.create_check_constraint(
        "ck_advisory_evidence_participation",
        _EVIDENCE,
        "advisory_treatment_participation IS NULL OR advisory_treatment_participation IN "
        f"({_quote(_PARTICIPATION_VALUES)})",
    )
    # UNSTAGED is a bare marker: no reason, no participation, no seed, no Invocation.
    op.create_check_constraint(
        "ck_advisory_evidence_unstaged_bare",
        _EVIDENCE,
        "advisory_admission_state <> 'UNSTAGED' OR (advisory_admission_reason_code IS NULL "
        "AND advisory_treatment_participation IS NULL "
        "AND advisory_admission_seed_version IS NULL AND advisory_admission_seed_digest IS NULL "
        "AND advisory_admission_seed IS NULL AND advisory_decision_invocation_id IS NULL)",
    )
    # The two terminal *classifications* are bare as well: a frozen classification never
    # carries experiment/pair/arm/seed/deadline and is never retroactively rebound.
    op.create_check_constraint(
        "ck_advisory_evidence_classification_bare",
        _EVIDENCE,
        "advisory_admission_state NOT IN ('LEGACY_PRE_I2', 'GATE_A_DISABLED') "
        "OR (advisory_admission_reason_code IS NULL "
        "AND advisory_treatment_participation IS NULL "
        "AND advisory_admission_seed_version IS NULL AND advisory_admission_seed_digest IS NULL "
        "AND advisory_admission_seed IS NULL AND advisory_decision_invocation_id IS NULL)",
    )
    # Seed facts are all-or-nothing: a digest without its payload (or vice versa) would be a
    # half-written seed that a reader could mistake for a complete binding.
    op.create_check_constraint(
        "ck_advisory_evidence_seed_atomic",
        _EVIDENCE,
        "(advisory_admission_seed_version IS NULL AND advisory_admission_seed_digest IS NULL "
        "AND advisory_admission_seed IS NULL) "
        "OR (advisory_admission_seed_version IS NOT NULL "
        "AND advisory_admission_seed_digest IS NOT NULL AND advisory_admission_seed IS NOT NULL)",
    )
    # The unbound staging-failure terminal carries exactly the frozen constants and no seed.
    op.create_check_constraint(
        "ck_advisory_evidence_unbound_terminal",
        _EVIDENCE,
        "advisory_admission_state <> 'ADMISSION_FAILED_FINAL' "
        f"OR advisory_admission_reason_code <> '{_UNBOUND_REASON}' "
        "OR (advisory_admission_seed_version IS NULL AND advisory_admission_seed_digest IS NULL "
        "AND advisory_admission_seed IS NULL AND advisory_decision_invocation_id IS NULL "
        "AND advisory_treatment_participation = 'NO_LONG_UNBOUND')",
    )
    # Any other named terminal may only be used once a complete seed is atomically present.
    op.create_check_constraint(
        "ck_advisory_evidence_terminal_requires_seed",
        _EVIDENCE,
        "advisory_admission_state <> 'ADMISSION_FAILED_FINAL' "
        f"OR advisory_admission_reason_code = '{_UNBOUND_REASON}' "
        "OR (advisory_admission_seed_version IS NOT NULL "
        "AND advisory_admission_seed_digest IS NOT NULL AND advisory_admission_seed IS NOT NULL)",
    )
    # INVOCATION_CREATED requires the complete seed and the Invocation linkage.
    op.create_check_constraint(
        "ck_advisory_evidence_invocation_created",
        _EVIDENCE,
        "advisory_admission_state <> 'INVOCATION_CREATED' "
        "OR (advisory_admission_seed_version IS NOT NULL "
        "AND advisory_admission_seed_digest IS NOT NULL AND advisory_admission_seed IS NOT NULL "
        "AND advisory_decision_invocation_id IS NOT NULL)",
    )
    # Only INVOCATION_CREATED may carry an Invocation; the bare/terminal states never do.
    op.create_check_constraint(
        "ck_advisory_evidence_invocation_only_created",
        _EVIDENCE,
        "advisory_decision_invocation_id IS NULL "
        "OR advisory_admission_state = 'INVOCATION_CREATED'",
    )
    op.create_index(
        f"ix_{_EVIDENCE}_advisory_state", _EVIDENCE, ["advisory_admission_state"]
    )
    # The other half of the Evidence <-> Invocation cycle (D2 §24.2).
    op.create_foreign_key(
        "fk_advisory_evidence_invocation",
        _EVIDENCE,
        _INVOCATIONS,
        ["advisory_decision_invocation_id"],
        ["decision_invocation_id"],
        deferrable=True,
        initially="DEFERRED",
    )


def downgrade() -> None:
    op.drop_constraint("fk_advisory_evidence_invocation", _EVIDENCE, type_="foreignkey")
    op.drop_index(f"ix_{_EVIDENCE}_advisory_state", table_name=_EVIDENCE)
    for name in (
        "ck_advisory_evidence_invocation_only_created",
        "ck_advisory_evidence_invocation_created",
        "ck_advisory_evidence_terminal_requires_seed",
        "ck_advisory_evidence_unbound_terminal",
        "ck_advisory_evidence_seed_atomic",
        "ck_advisory_evidence_classification_bare",
        "ck_advisory_evidence_unstaged_bare",
        "ck_advisory_evidence_participation",
        "ck_advisory_evidence_state",
    ):
        op.drop_constraint(name, _EVIDENCE, type_="check")
    for column in (
        "advisory_decision_invocation_id",
        "advisory_admission_seed",
        "advisory_admission_seed_digest",
        "advisory_admission_seed_version",
        "advisory_treatment_participation",
        "advisory_admission_reason_code",
        "advisory_admission_state",
    ):
        op.drop_column(_EVIDENCE, column)

    for name in (
        "ck_decision_snapshots_advisory_deadline_order",
        "ck_decision_snapshots_advisory_deadline_positive",
        "ck_decision_snapshots_advisory_evidence_revision",
        "ck_decision_snapshots_advisory_binding_atomic",
    ):
        op.drop_constraint(name, _SNAPSHOTS, type_="check")
    for column in (
        "decision_deadline_at",
        "deadline_policy_version",
        "deadline_duration_ms",
        "decision_requested_at",
        "advisory_config_epoch_id",
        "input_binding_digest",
        "snapshot_payload_hash",
        "market_type",
        "feature_snapshot_hash",
        "evidence_hash",
        "evidence_revision",
        "evidence_id",
        "opportunity_id",
        "decision_invocation_id",
    ):
        op.drop_column(_SNAPSHOTS, column)

    op.drop_constraint(
        "fk_advisory_invocation_final_decision", _INVOCATIONS, type_="foreignkey"
    )
    op.drop_constraint("fk_ai_decisions_advisory_attempt", _AI_DECISIONS, type_="foreignkey")
    op.drop_index("uq_ai_decisions_advisory_invocation", table_name=_AI_DECISIONS)
    op.drop_constraint("uq_ai_decisions_advisory_origin", _AI_DECISIONS, type_="unique")
    op.drop_constraint("ck_ai_decisions_advisory_origin_pair", _AI_DECISIONS, type_="check")
    for column in (
        "finalized_at",
        "error_category",
        "output_digest",
        "provider_reported_model_id",
        "configured_model_id",
        "provider_id",
        "arm_id",
        "pair_id",
        "experiment_id",
        "input_binding_digest",
        "attempt_id",
        "decision_invocation_id",
    ):
        op.drop_column(_AI_DECISIONS, column)

    op.drop_constraint("fk_advisory_invocation_final_attempt", _INVOCATIONS, type_="foreignkey")
    op.drop_index(f"ix_{_INVOCATIONS}_opportunity", table_name=_INVOCATIONS)
    op.drop_index(f"ix_{_INVOCATIONS}_state", table_name=_INVOCATIONS)
    op.drop_table(_ATTEMPTS)
    op.drop_table(_INVOCATIONS)
