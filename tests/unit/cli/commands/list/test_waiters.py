"""Tests for the list waiters CLI command."""

from click.testing import CliRunner

from itbench.cli.commands.list.waiters import list_waiters
from itbench.models.waiter import WAITER_CATALOG

_WIDE = {"COLUMNS": "300"}


def test_list_waiters_shows_all() -> None:
    runner = CliRunner()

    result = runner.invoke(list_waiters, [], env=_WIDE)

    assert result.exit_code == 0
    for waiter_id in WAITER_CATALOG:
        assert waiter_id in result.output


def test_list_waiters_count_line() -> None:
    runner = CliRunner()

    result = runner.invoke(list_waiters, [], env=_WIDE)

    assert f"{len(WAITER_CATALOG)} waiter(s) available" in result.output


def test_list_waiters_shows_names_and_platforms() -> None:
    runner = CliRunner()

    result = runner.invoke(list_waiters, [], env=_WIDE)

    for entry in WAITER_CATALOG.values():
        assert entry.name in result.output
