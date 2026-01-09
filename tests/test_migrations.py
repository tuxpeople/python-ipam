"""Tests for Alembic migrations configuration."""

import os
from pathlib import Path


class TestMigrationsStructure:
    """Tests for migrations directory structure."""

    def test_migrations_directory_exists(self):
        """Test that migrations directory exists."""
        assert os.path.exists("migrations")
        assert os.path.isdir("migrations")

    def test_migrations_env_exists(self):
        """Test that migrations/env.py exists."""
        assert os.path.exists("migrations/env.py")

    def test_migrations_env_has_file_check(self):
        """Test that env.py checks for file existence before loading."""
        env_content = Path("migrations/env.py").read_text()

        # Check that env.py has the file existence check
        assert "os.path.exists" in env_content, (
            "env.py should check if config file exists before loading"
        )

        # Check that it handles optional alembic.ini
        assert (
            "config.config_file_name is not None" in env_content
        ), "env.py should check for None config_file_name"

    def test_migrations_versions_exists(self):
        """Test that migrations/versions directory exists."""
        assert os.path.exists("migrations/versions")
        assert os.path.isdir("migrations/versions")

    def test_initial_migrations_exist(self):
        """Test that initial migration files exist."""
        versions_dir = Path("migrations/versions")
        migration_files = list(versions_dir.glob("*.py"))

        # Filter out __pycache__ and __init__.py
        migration_files = [
            f
            for f in migration_files
            if f.name != "__init__.py" and "__pycache__" not in str(f)
        ]

        assert (
            len(migration_files) > 0
        ), "At least one migration file should exist"

    def test_alembic_ini_not_required(self):
        """Test that alembic.ini is not required (container-friendly)."""
        # alembic.ini should not exist in container deployments
        # env.py should work without it
        alembic_ini_path = "migrations/alembic.ini"

        # Read env.py to verify it can handle missing alembic.ini
        env_content = Path("migrations/env.py").read_text()

        # The file check should prevent FileNotFoundError
        if not os.path.exists(alembic_ini_path):
            assert "os.path.exists" in env_content, (
                "env.py must check for file existence when alembic.ini is missing"
            )
