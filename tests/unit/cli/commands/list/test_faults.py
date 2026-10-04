"""Tests for the list faults CLI command."""

from click.testing import CliRunner

from itbench.cli.commands.list.faults import list_faults
from itbench.models.fault import FAULT_CATALOG

_WIDE = {"COLUMNS": "300"}


def test_list_faults_shows_all() -> None:
    runner = CliRunner()

    result = runner.invoke(list_faults, [], env=_WIDE)

    assert result.exit_code == 0
    for slug in FAULT_CATALOG:
        assert slug in result.output


def test_list_faults_count_line() -> None:
    runner = CliRunner()

    result = runner.invoke(list_faults, [], env=_WIDE)

    assert f"{len(FAULT_CATALOG)} fault(s) found" in result.output


def test_list_faults_filter_by_tag_match() -> None:
    runner = CliRunner()
    first = next(iter(FAULT_CATALOG.values()))
    tag = first.tags[0]

    result = runner.invoke(list_faults, ["--tag", tag], env=_WIDE)

    assert result.exit_code == 0
    assert first.name in result.output


def test_list_faults_filter_by_platform_match() -> None:
    runner = CliRunner()
    first = next(iter(FAULT_CATALOG.values()))

    result = runner.invoke(list_faults, ["--platform", first.platform], env=_WIDE)

    assert result.exit_code == 0
    assert first.name in result.output


def test_list_faults_filter_no_match() -> None:
    runner = CliRunner()

    result = runner.invoke(list_faults, ["--tag", "NonExistentTag"])

    assert result.exit_code == 0
    assert "No faults matched" in result.output


def test_list_faults_active_faults_show_active_status() -> None:
    active = [f for f in FAULT_CATALOG.values() if f.status is None or f.status.retired is None]
    runner = CliRunner()

    result = runner.invoke(list_faults, [], env=_WIDE)

    assert result.exit_code == 0
    if active:
        assert "active" in result.output


def test_list_faults_retired_faults_show_retired_status() -> None:
    retired = [f for f in FAULT_CATALOG.values() if f.status is not None and f.status.retired is not None]
    runner = CliRunner()

    result = runner.invoke(list_faults, [], env=_WIDE)

    assert result.exit_code == 0
    if retired:
        assert "retired" in result.output


def test_list_faults_status_column_present() -> None:
    runner = CliRunner()

    result = runner.invoke(list_faults, [], env=_WIDE)

    assert result.exit_code == 0
    assert "Status" in result.output
