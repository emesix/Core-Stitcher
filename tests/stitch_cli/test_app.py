"""Tests for the Stitch CLI application scaffold."""
from typer.testing import CliRunner

from stitch.apps.operator.app import app

runner = CliRunner()


def test_version():
    result = runner.invoke(app, ["system", "version"])
    assert result.exit_code == 0
    assert "stitch" in result.stdout.lower() or "0." in result.stdout


def test_health():
    result = runner.invoke(app, ["system", "health"])
    assert result.exit_code == 0


def test_no_args_shows_help():
    result = runner.invoke(app, [])
    # Typer with no_args_is_help=True uses exit code 0 (help shown)
    assert result.exit_code == 0 or "Usage" in result.stdout


def test_global_output_flag():
    result = runner.invoke(app, ["-o", "json", "system", "version"])
    assert result.exit_code == 0


def test_global_quiet_flag():
    result = runner.invoke(app, ["--quiet", "system", "version"])
    assert result.exit_code == 0
