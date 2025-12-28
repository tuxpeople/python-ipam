"""Initial schema.

Revision ID: 7b4a1d0f9b2a
Revises: None
Create Date: 2025-12-28 12:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "7b4a1d0f9b2a"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "networks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("network", sa.String(length=18), nullable=False),
        sa.Column("cidr", sa.Integer(), nullable=False),
        sa.Column("broadcast_address", sa.String(length=15), nullable=True),
        sa.Column("name", sa.String(length=100), nullable=True),
        sa.Column("domain", sa.String(length=100), nullable=True),
        sa.Column("vlan_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("location", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("network"),
    )
    op.create_table(
        "hosts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(length=15), nullable=False),
        sa.Column("hostname", sa.String(length=255), nullable=True),
        sa.Column("cname", sa.String(length=255), nullable=True),
        sa.Column("mac_address", sa.String(length=17), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.String(length=20),
            nullable=True,
            server_default=sa.text("'active'"),
        ),
        sa.Column("last_seen", sa.DateTime(), nullable=True),
        sa.Column("discovery_source", sa.String(length=50), nullable=True),
        sa.Column(
            "is_assigned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("network_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(
            ["network_id"],
            ["networks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_address"),
    )
    op.create_table(
        "dhcp_ranges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("network_id", sa.Integer(), nullable=False),
        sa.Column("start_ip", sa.String(length=15), nullable=False),
        sa.Column("end_ip", sa.String(length=15), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("1"),
        ),
        sa.ForeignKeyConstraint(
            ["network_id"],
            ["networks.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("dhcp_ranges")
    op.drop_table("hosts")
    op.drop_table("networks")
