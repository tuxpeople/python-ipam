"""Test fixtures for IPAM."""

import os
import tempfile

# The database URI is read when ipam.config is imported and the engine is
# bound in create_app(); setting app.config afterwards does not rebind it.
# Without this, the test suite would run against (and drop the tables of)
# the developer's ./ipam.db.
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import pytest  # noqa: E402

from ipam import create_app  # noqa: E402
from ipam.extensions import db  # noqa: E402


@pytest.fixture
def app():
    """Create application for testing."""
    db_fd, db_path = tempfile.mkstemp()

    app = create_app("default")
    app.config.update(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "API_TOKENS": ["test-token"],
            "RATELIMIT_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def client(app):
    """Create test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Create application context."""
    with app.app_context():
        yield app
