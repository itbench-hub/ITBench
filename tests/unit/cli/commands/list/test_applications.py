"""Tests for the list applications CLI command."""

from click.testing import CliRunner

from itbench.cli.commands.list.applications import list_applications
from itbench.models.application import APPLICATION_CATALOG


def test_list_applications_shows_all() -> None:
    runner = CliRunner()

    result = runner.invoke(list_applications, [])

    assert result.exit_code == 0
    for slug in APPLICATION_CATALOG:
        assert slug in result.output


def test_list_applications_count_line() -> None:
    runner = CliRunner()

    result = runner.invoke(list_applications, [])

    assert f"{len(APPLICATION_CATALOG)} application(s) found" in result.output


def test_list_applications_filter_by_platform_match() -> None:
    runner = CliRunner()
    first = next(iter(APPLICATION_CATALOG.values()))
    platform = first.platforms[0]

    result = runner.invoke(list_applications, ["--platform", platform])

    assert result.exit_code == 0
    assert first.name in result.output


def test_list_applications_filter_no_match() -> None:
    runner = CliRunner()

    result = runner.invoke(list_applications, ["--platform", "NonExistentPlatform"])

    assert result.exit_code == 0
    assert "No applications matched" in result.output
