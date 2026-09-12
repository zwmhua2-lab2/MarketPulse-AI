"""close stable-capture-anchor review findings with proof and orphan evidence

This revision is additive. It preserves already-recorded anchors while enforcing
the new BBO-reference rule for every subsequent write and adds durable orphan
classification without mutating immutable anchor causal facts.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0008"
down_revision: str | None = "20260913_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "edge_opportunity_capture_anchors",
        sa.Column("forward_admission_session_id", sa.String(128), nullable=True),
    )
    op.add_column(
        "edge_opportunity_capture_anchors",
        sa.Column("forward_admission_event_digest", sa.String(64), nullable=True),
    )
    op.add_column(
        "edge_opportunity_capture_anchors",
        sa.Column("forward_admission_proof_hash", sa.String(64), nullable=True),
    )
    # Existing unreviewed 0007 rows are not rewritten. NOT VALID still enforces
    # the invariant for all future INSERT/UPDATE operations.
    op.execute(
        "ALTER TABLE edge_opportunity_capture_anchors "
        "ADD CONSTRAINT ck_edge_capture_anchor_reference_bbo_consistency "
        "CHECK ((reference_data_status = 'OK' AND reference_bbo_observation_id IS NOT NULL) "
        "OR (reference_data_status IN ('REFERENCE_MISSING', 'REFERENCE_STALE') "
        "AND reference_bbo_observation_id IS NULL)) NOT VALID"
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
        "ck_edge_capture_anchor_reference_bbo_consistency",
        "edge_opportunity_capture_anchors",
        type_="check",
    )
    op.drop_column("edge_opportunity_capture_anchors", "forward_admission_proof_hash")
    op.drop_column("edge_opportunity_capture_anchors", "forward_admission_event_digest")
    op.drop_column("edge_opportunity_capture_anchors", "forward_admission_session_id")
