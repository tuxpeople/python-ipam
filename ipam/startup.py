"""Container startup entrypoint for migrations and Gunicorn."""

import os
import sys


DEFAULT_GUNICORN_ARGS = [
    "gunicorn",
    "--bind",
    "0.0.0.0:5000",
    "--workers",
    "4",
    "--timeout",
    "120",
    "app:app",
]


def should_run_migrations(env):
    """Return True when database migrations should run."""
    value = env.get("IPAM_RUN_MIGRATIONS", "true")
    return value.strip().lower() in {"1", "true", "yes", "on"}


def build_gunicorn_args(argv):
    """Return gunicorn arguments from argv or defaults."""
    return argv if argv else list(DEFAULT_GUNICORN_ARGS)


def run_migrations():
    """Run Alembic migrations within the Flask app context."""
    from flask_migrate import upgrade

    from ipam import create_app

    app = create_app()
    with app.app_context():
        upgrade()


def main(argv=None, env=None, exec_fn=None):
    """Run migrations once, then exec Gunicorn."""
    if argv is None:
        argv = sys.argv[1:]
    if env is None:
        env = os.environ
    if exec_fn is None:
        exec_fn = os.execvp

    if should_run_migrations(env):
        run_migrations()

    args = build_gunicorn_args(argv)
    exec_fn(args[0], args)


if __name__ == "__main__":
    main()
