"""Tests for container startup helpers."""

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
