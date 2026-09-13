"""close stable-capture-anchor review findings with proof and orphan evidence

This revision is additive for the schema, but it is deliberately **fail-closed for
existing data**: it refuses to run at all when a durable anchor row already
contradicts the formal reference invariant. It may not silently drop, rewrite or
reclassify such a row, because the illegal shape proves only that the row is
invalid -- not which reference status or which BBO observation it should have
carried.

Applied to a clean database it preserves already-recorded anchors, enforces the
BBO-reference rule as a validated constraint, and adds durable orphan
classification without mutating immutable anchor causal facts.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0008"
down_revision: str | None = "20260913_0007"
branch_labels = None
depends_on = None

_ANCHOR_TABLE = "edge_opportunity_capture_anchors"
_REFERENCE_CONSISTENCY_CONSTRAINT = "ck_edge_capture_anchor_reference_bbo_consistency"
_INVALID_REFERENCE_SHAPE = (
    "reference_data_status = 'OK' AND reference_bbo_observation_id IS NULL"
)


def _refuse_invalid_existing_reference_rows() -> None:
    """Abort the upgrade before any change when a durable anchor is already invalid.

    ``OK`` with no BBO observation id proves the row violates the frozen formal
    invariant, but it cannot prove whether the quote was really ``STALE`` or
    ``MISSING``, which observation it should bind, or what its original
    provenance was. Every automatic conversion would therefore be a guess, so
    this migration stops instead: a human audits the rows, and the transaction
    (including ``alembic_version``) rolls back untouched.
    """

    invalid = int(
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT count(*) FROM {_ANCHOR_TABLE} "
                f"WHERE {_INVALID_REFERENCE_SHAPE}"
            )
        )
        .scalar_one()
    )
    if invalid:
        raise RuntimeError(
            "SE-ARCH-FIX-01 R2 refuses to upgrade to 20260913_0008: "
            f"{invalid} existing row(s) in {_ANCHOR_TABLE} satisfy "
            f"({_INVALID_REFERENCE_SHAPE}). That shape proves the row does not "
            "satisfy the formal reference invariant, but it does not prove which "
            "reference status or BBO observation the row should have carried, so "
            "reclassifying it automatically would fabricate provenance. This "
            "upgrade was rolled back and alembic_version is unchanged "
            "(20260913_0007); the rows remain exactly as recorded for manual "
            "audit. Resolve them, then re-run the upgrade."
        )


def upgrade() -> None:
    # Fail closed first: never touch the schema while durable data already
    # contradicts the invariant this revision is about to enforce.
    _refuse_invalid_existing_reference_rows()
    op.add_column(
        _ANCHOR_TABLE,
        sa.Column("forward_admission_session_id", sa.String(128), nullable=True),
    )
    op.add_column(
        _ANCHOR_TABLE,
        sa.Column("forward_admission_event_digest", sa.String(64), nullable=True),
    )
    op.add_column(
        _ANCHOR_TABLE,
        sa.Column("forward_admission_proof_hash", sa.String(64), nullable=True),
    )
    # Validated on purpose. The pre-flight above turns an invalid existing row into
    # an explicit abort; adding the constraint without NOT VALID then makes
    # PostgreSQL itself refuse to leave any such row behind, so the invariant is
    # enforced for past and future rows alike rather than only for new INSERTs.
    op.execute(
        f"ALTER TABLE {_ANCHOR_TABLE} "
        f"ADD CONSTRAINT {_REFERENCE_CONSISTENCY_CONSTRAINT} "
        "CHECK ((reference_data_status = 'OK' AND reference_bbo_observation_id IS NOT NULL) "
        "OR (reference_data_status IN ('REFERENCE_MISSING', 'REFERENCE_STALE') "
        "AND reference_bbo_observation_id IS NULL))"
    )
    op.create_table(
        "edge_opportunity_capture_anchor_orphans",
        sa.Column("opportunity_id", sa.String(64), primary_key=True),
        sa.Column("evidence_revision", sa.Integer(), primary_key=True),
        sa.Column("classification", sa.String(64), nullable=False),
        sa.Column("reason", sa.String(256), nullable=False),
        sa.Column("expected_precondition", sa.JSON(), nullable=False),
        sa.Column("actual_precondition", sa.JSON(), nullable=False),
        sa.Column("orphan_version", sa.String(64), nullable=False),
        sa.Column("classification_hash", sa.String(64), nullable=False),
        sa.Column("classification_hash_version", sa.String(64), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["opportunity_id", "evidence_revision"],
            [
                "edge_opportunity_capture_anchors.opportunity_id",
                "edge_opportunity_capture_anchors.evidence_revision",
            ],
            name="fk_edge_capture_anchor_orphan_anchor",
        ),
        sa.CheckConstraint(
            "classification = 'UNVERIFIABLE_ORPHAN'",
            name="ck_edge_capture_anchor_orphan_classification",
        ),
        sa.CheckConstraint(
            "evidence_revision >= 1", name="ck_edge_capture_anchor_orphan_revision_positive"
        ),
    )


def downgrade() -> None:
    op.drop_table("edge_opportunity_capture_anchor_orphans")
    op.drop_constraint(
        _REFERENCE_CONSISTENCY_CONSTRAINT,
        _ANCHOR_TABLE,
        type_="check",
    )
    op.drop_column(_ANCHOR_TABLE, "forward_admission_proof_hash")
    op.drop_column(_ANCHOR_TABLE, "forward_admission_event_digest")
    op.drop_column(_ANCHOR_TABLE, "forward_admission_session_id")
