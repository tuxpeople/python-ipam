"""Application configuration."""

import os


def _get_bool_env(name, default):
    """Return a boolean from an environment variable."""
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key")
    HOST_ASSIGN_ON_CREATE = _get_bool_env("HOST_ASSIGN_ON_CREATE", True)

    # Use absolute path for SQLite database in project root
    BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL", f"sqlite:///{os.path.join(BASE_DIR, 'ipam.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    BACKUP_DIR = os.environ.get("BACKUP_DIR", os.path.join(BASE_DIR, "backups"))
    API_TOKENS = [
        token.strip()
        for token in os.environ.get("API_TOKENS", "").split(",")
        if token.strip()
    ]
    API_RATE_LIMIT = os.environ.get("API_RATE_LIMIT", "200 per minute")
    RATELIMIT_STORAGE_URI = os.environ.get(
        "RATELIMIT_STORAGE_URI", "memory://"
    )
    RATELIMIT_ENABLED = _get_bool_env("RATELIMIT_ENABLED", True)


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


config = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
