"""Tests for container startup helpers."""

from unittest import mock

from ipam import startup


def test_build_gunicorn_args_uses_defaults():
    args = startup.build_gunicorn_args([])
    assert args == startup.DEFAULT_GUNICORN_ARGS


def test_build_gunicorn_args_uses_argv():
    argv = ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
    args = startup.build_gunicorn_args(argv)
    assert args == argv


def test_main_execs_with_default_args_when_none():
    captured = {}

    def exec_fn(cmd, args):
        captured["cmd"] = cmd
        captured["args"] = args

    startup.main(argv=[], env={"IPAM_RUN_MIGRATIONS": "false"}, exec_fn=exec_fn)

    assert captured["cmd"] == startup.DEFAULT_GUNICORN_ARGS[0]
    assert captured["args"] == startup.DEFAULT_GUNICORN_ARGS


def test_should_run_migrations_default_true():
    """Test that migrations run by default."""
    assert startup.should_run_migrations({})


def test_should_run_migrations_explicit_true():
    """Test various truthy values."""
    for value in ["true", "TRUE", "1", "yes", "on"]:
        assert startup.should_run_migrations(
            {"IPAM_RUN_MIGRATIONS": value}
        ), f"Failed for value: {value}"


def test_should_run_migrations_explicit_false():
    """Test various falsy values."""
    for value in ["false", "FALSE", "0", "no", "off"]:
        assert not startup.should_run_migrations(
            {"IPAM_RUN_MIGRATIONS": value}
        ), f"Failed for value: {value}"


def test_should_run_migrations_whitespace():
    """Test whitespace handling."""
    assert startup.should_run_migrations({"IPAM_RUN_MIGRATIONS": "  true  "})
    assert not startup.should_run_migrations(
        {"IPAM_RUN_MIGRATIONS": "  false  "}
    )


@mock.patch("ipam.startup.run_migrations")
def test_main_runs_migrations_by_default(mock_migrations):
    """Test migrations run by default."""
    captured = {}

    def exec_fn(cmd, args):
        captured["executed"] = True

    startup.main(argv=[], env={}, exec_fn=exec_fn)
    mock_migrations.assert_called_once()
    assert captured["executed"]


@mock.patch("ipam.startup.run_migrations")
def test_main_skips_migrations_when_disabled(mock_migrations):
    """Test migrations can be skipped."""
    captured = {}

    def exec_fn(cmd, args):
        captured["executed"] = True

    startup.main(argv=[], env={"IPAM_RUN_MIGRATIONS": "false"}, exec_fn=exec_fn)
    mock_migrations.assert_not_called()
    assert captured["executed"]


def test_run_migrations_function_exists():
    """Test that run_migrations function exists and is callable."""
    assert hasattr(startup, "run_migrations")
    assert callable(startup.run_migrations)
