"""Tests for the explain waiter CLI command."""

from click.testing import CliRunner

from itbench.cli.commands.explain.waiter import explain_waiter
from itbench.models.waiter import WAITER_CATALOG


def test_explain_waiter_known_id() -> None:
    runner = CliRunner()
    waiter_id = next(iter(WAITER_CATALOG))

    result = runner.invoke(explain_waiter, [waiter_id])

    assert result.exit_code == 0
    assert WAITER_CATALOG[waiter_id].name in result.output


def test_explain_waiter_shows_sections() -> None:
    runner = CliRunner()
    waiter_id = next(iter(WAITER_CATALOG))

    result = runner.invoke(explain_waiter, [waiter_id])

    assert "DESCRIPTION" in result.output
    assert "SCENARIO YAML EXAMPLE" in result.output


def test_explain_waiter_unknown_id() -> None:
    runner = CliRunner()

    result = runner.invoke(explain_waiter, ["no-such-waiter"])

    assert result.exit_code == 1
    assert "Unknown waiter" in result.output
    assert "itbench list waiters" in result.output
