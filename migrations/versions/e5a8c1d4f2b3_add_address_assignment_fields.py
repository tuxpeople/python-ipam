"""Add address assignment, lease and observation fields to hosts.

All new columns are nullable; existing data is preserved. Assignment
types are not inferred from ``is_assigned`` or ``status``. The only
backfill is for rows the UDM reservation collector created
(``discovery_source='udm-reservations'``, ``is_assigned=1``,
``status='reserved'``): these become ``assignment_type='reservation'``
with ``assignment_source='udm-reservations'``. Their
``assignment_last_confirmed_at`` stays NULL, because the migration
does not confirm anything; the next collector run does.

Revision ID: e5a8c1d4f2b3
Revises: c3f2a4b7d9e1
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "e5a8c1d4f2b3"
down_revision = "c3f2a4b7d9e1"
branch_labels = None
depends_on = None

NEW_COLUMNS = (
    ("assignment_type", sa.String(length=20)),
    ("assignment_source", sa.String(length=50)),
    ("assignment_last_confirmed_at", sa.DateTime()),
    ("lease_expires_at", sa.DateTime()),
    ("lease_source", sa.String(length=50)),
    ("lease_observed_at", sa.DateTime()),
    ("last_seen_source", sa.String(length=50)),
)


def _existing_columns(bind):
    return {c["name"] for c in inspect(bind).get_columns("hosts")}


def upgrade():
    bind = op.get_bind()
    existing = _existing_columns(bind)
    missing = [(n, t) for n, t in NEW_COLUMNS if n not in existing]
    if missing:
        with op.batch_alter_table("hosts") as batch_op:
            for name, type_ in missing:
                batch_op.add_column(sa.Column(name, type_, nullable=True))

    op.execute(
        sa.text(
            "UPDATE hosts "
            "SET assignment_type = 'reservation', "
            "    assignment_source = 'udm-reservations' "
            "WHERE assignment_type IS NULL "
            "  AND discovery_source = 'udm-reservations' "
            "  AND is_assigned = 1 "
            "  AND status = 'reserved'"
        )
    )


def downgrade():
    bind = op.get_bind()
    existing = _existing_columns(bind)
    present = [n for n, _ in NEW_COLUMNS if n in existing]
    if present:
        with op.batch_alter_table("hosts") as batch_op:
            for name in reversed(present):
                batch_op.drop_column(name)
