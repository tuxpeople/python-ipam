"""Add DHCP ranges table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "c3f2a4b7d9e1"
down_revision = "7b4a1d0f9b2a"
branch_labels = None
depends_on = None


def _table_exists(bind, table_name):
    inspector = inspect(bind)
    return table_name in inspector.get_table_names()


def upgrade():
    bind = op.get_bind()
    if _table_exists(bind, "dhcp_ranges"):
        return

    op.create_table(
        "dhcp_ranges",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "network_id",
            sa.Integer(),
            sa.ForeignKey("networks.id"),
            nullable=False,
        ),
        sa.Column("start_ip", sa.String(length=15), nullable=False),
        sa.Column("end_ip", sa.String(length=15), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )


def downgrade():
    bind = op.get_bind()
    if not _table_exists(bind, "dhcp_ranges"):
        return
    op.drop_table("dhcp_ranges")
