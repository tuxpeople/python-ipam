"""Alembic environment configuration."""

import os
from logging.config import fileConfig

from alembic import context
from flask import current_app

from ipam.extensions import db

config = context.config

# Configure logging only if alembic.ini exists (optional for containers)
if config.config_file_name is not None and os.path.exists(
    config.config_file_name
):
    fileConfig(config.config_file_name)

target_metadata = db.metadata


def get_url():
    """Return database URL from Flask config."""
    return current_app.config.get("SQLALCHEMY_DATABASE_URI")


def run_migrations_offline():
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    connectable = db.engine

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
