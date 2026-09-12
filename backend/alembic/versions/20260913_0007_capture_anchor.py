"""add durable SE-ARCH-FIX-01 Forward Paper capture anchors

The anchor is an append-only admission fact written before the existing atomic
G2 + Edge evidence transaction. It neither changes G2 state semantics nor
creates outcomes/economic facts.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0007"
down_revision: str | None = "20260912_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "edge_opportunity_capture_anchors",
        sa.Column("opportunity_id", sa.String(64), primary_key=True),
        sa.Column("evidence_revision", sa.Integer(), primary_key=True),
        sa.Column("event_id", sa.String(64), nullable=False),
        sa.Column("candidate_id", sa.String(64), nullable=False),
        sa.Column("evidence_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("reference_data_status", sa.String(32), nullable=False),
        sa.Column("reference_bbo_observation_id", sa.String(64), nullable=True),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("source_identity", sa.String(128), nullable=False),
        sa.Column("source_manifest_id", sa.String(64), nullable=False),
        sa.Column("anchor_payload_version", sa.String(64), nullable=False),
        sa.Column("anchor_payload", sa.JSON(), nullable=False),
        sa.Column("anchor_hash", sa.String(64), nullable=False),
        sa.Column("anchor_hash_version", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["reference_bbo_observation_id"],
            ["edge_bbo_observations.observation_id"],
            name="fk_edge_capture_anchor_reference_bbo",
        ),
        sa.CheckConstraint("evidence_revision >= 1", name="ck_edge_capture_anchor_revision_positive"),
        sa.CheckConstraint(
            "source_type = 'FORWARD_PAPER'", name="ck_edge_capture_anchor_forward_paper"
        ),
        sa.CheckConstraint(
            "reference_data_status IN ('OK', 'REFERENCE_MISSING', 'REFERENCE_STALE')",
            name="ck_edge_capture_anchor_reference_status",
        ),
        sa.UniqueConstraint(
            "opportunity_id", "evidence_revision", name="uq_edge_capture_anchor_opportunity_revision"
        ),
    )
    op.create_index(
        "ix_edge_capture_anchor_event_id", "edge_opportunity_capture_anchors", ["event_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_edge_capture_anchor_event_id", table_name="edge_opportunity_capture_anchors")
    op.drop_table("edge_opportunity_capture_anchors")
