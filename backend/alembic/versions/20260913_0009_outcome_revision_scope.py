"""scope the forward-outcome revision chain to (opportunity, evidence, horizon)

The accepted SE-02A schema let a forward-outcome revision name any predecessor of the
same opportunity: `fk_edge_outcome_supersedes` only carried `(supersedes_outcome_id,
opportunity_id)`. A revision 2 of one horizon could therefore supersede the revision 1
of *another* horizon, and a revision 2 of one evidence revision could supersede the
revision 1 of another -- an invalid correction lineage that PostgreSQL could not refuse.

This revision narrows that foreign key to the frozen identity scope
`(outcome_id, opportunity_id, evidence_id, horizon)`, so the database itself guarantees
"same opportunity + same evidence + same horizon". Revision *adjacency* stays a
service-layer rule; no trigger or stored procedure is introduced.

Like `20260913_0008`, the revision is deliberately **fail-closed for existing data**: it
refuses to run at all when a durable row already carries a cross-scope supersedes link.
It may not rewrite `supersedes_outcome_id`, renumber a chain, drop an outcome row or
guess which predecessor was meant, because the illegal shape proves only that the
recorded lineage is invalid -- not what the correct predecessor was. A human audits
those rows.
"""

import sqlalchemy as sa
from alembic import op

revision: str = "20260913_0009"
down_revision: str | None = "20260913_0008"
branch_labels = None
depends_on = None

_OUTCOME_TABLE = "edge_forward_outcomes"
_SUPERSEDES_FK = "fk_edge_outcome_supersedes"
_ID_ONLY_UNIQUE = "uq_edge_outcome_id_opportunity"
_SCOPED_UNIQUE = "uq_edge_outcome_id_scope"
_SCOPE_COLUMNS = ("outcome_id", "opportunity_id", "evidence_id", "horizon")


def _refuse_invalid_existing_outcome_scope_rows() -> None:
    """Abort the upgrade before any change when a supersedes link crosses its scope.

    A cross-evidence or cross-horizon link proves the recorded revision chain is not a
    valid immutable correction, but it cannot prove which predecessor the row should
    have named: re-pointing it would fabricate lineage. The upgrade therefore stops and
    the transaction (including ``alembic_version``) rolls back untouched, leaving the
    rows exactly as recorded for manual audit.
    """

    invalid = int(
        op.get_bind()
        .execute(
            sa.text(
                f"SELECT count(*) FROM {_OUTCOME_TABLE} AS child "
                f"LEFT JOIN {_OUTCOME_TABLE} AS predecessor "
                "ON predecessor.outcome_id = child.supersedes_outcome_id "
                "WHERE child.supersedes_outcome_id IS NOT NULL "
                "AND (predecessor.outcome_id IS NULL "
                "OR predecessor.opportunity_id <> child.opportunity_id "
                "OR predecessor.evidence_id <> child.evidence_id "
                "OR predecessor.horizon <> child.horizon)"
            )
        )
        .scalar_one()
    )
    if invalid:
        raise RuntimeError(
            "SE-ARCH-FIX-02 refuses to upgrade to 20260913_0009: "
            f"{invalid} existing row(s) in {_OUTCOME_TABLE} supersede a predecessor "
            "outside their own (opportunity_id, evidence_id, horizon) scope. That shape "
            "proves the recorded lineage is not a valid immutable correction, but it "
            "does not prove which predecessor the row should have named, so re-pointing "
            "it automatically would fabricate lineage. This upgrade was rolled back and "
            "alembic_version is unchanged (20260913_0008); the rows remain exactly as "
            "recorded for manual audit. Resolve them, then re-run the upgrade."
        )


def upgrade() -> None:
    # Fail closed first: never replace the constraint while durable data already
    # violates the scope this revision is about to enforce.
    _refuse_invalid_existing_outcome_scope_rows()
    op.drop_constraint(_SUPERSEDES_FK, _OUTCOME_TABLE, type_="foreignkey")
    # The identity-only unique constraint existed solely to back the old, too-broad
    # foreign key. The scoped four-column constraint replaces it.
    op.drop_constraint(_ID_ONLY_UNIQUE, _OUTCOME_TABLE, type_="unique")
    op.create_unique_constraint(_SCOPED_UNIQUE, _OUTCOME_TABLE, list(_SCOPE_COLUMNS))
    op.create_foreign_key(
        _SUPERSEDES_FK,
        _OUTCOME_TABLE,
        _OUTCOME_TABLE,
        ["supersedes_outcome_id", "opportunity_id", "evidence_id", "horizon"],
        list(_SCOPE_COLUMNS),
    )


def downgrade() -> None:
    op.drop_constraint(_SUPERSEDES_FK, _OUTCOME_TABLE, type_="foreignkey")
    op.drop_constraint(_SCOPED_UNIQUE, _OUTCOME_TABLE, type_="unique")
    op.create_unique_constraint(_ID_ONLY_UNIQUE, _OUTCOME_TABLE, ["outcome_id", "opportunity_id"])
    op.create_foreign_key(
        _SUPERSEDES_FK,
        _OUTCOME_TABLE,
        _OUTCOME_TABLE,
        ["supersedes_outcome_id", "opportunity_id"],
        ["outcome_id", "opportunity_id"],
    )
