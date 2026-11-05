"""Tests for the shared ``--usage`` option of the list commands."""

import json

from pathlib import Path
from typing import Any

import pytest
import yaml

from click import Command
from click.testing import CliRunner

from itbench.cli.commands.list.applications import list_applications
from itbench.cli.commands.list.faults import list_faults
from itbench.cli.commands.list.waiters import list_waiters
from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG

_WIDE = {"COLUMNS": "300"}

_FAULT = next(iter(FAULT_CATALOG))
_APPLICATION = next(iter(APPLICATION_CATALOG))
_WAITER = next(iter(WAITER_CATALOG))

# (command, key of the id field in each row, id used by the scenarios below)
_COMMANDS = [
    pytest.param(list_faults, "slug", _FAULT, id="faults"),
    pytest.param(list_applications, "slug", _APPLICATION, id="applications"),
    pytest.param(list_waiters, "id", _WAITER, id="waiters"),
]

# Scenarios that reference the id above, per command: the waiter is only used in scenario 2.
_EXPECTED_SCENARIOS = {"slug": [2, 10], "id": [2]}


@pytest.fixture
def library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    scenarios: dict[str, dict[str, Any]] = {
        "2": {
            "environment": {"applications": [{"id": _APPLICATION}]},
            "faults": [
                {
                    "injections": [{"id": _FAULT}],
                    "waitFor": {"postInjection": [{"id": _WAITER}]},
                }
            ],
        },
        "10": {
            "environment": {"applications": [{"id": _APPLICATION}]},
            "faults": [{"injections": [{"id": _FAULT}, {"id": _FAULT}]}],
        },
    }
    for name, data in scenarios.items():
        directory = tmp_path / "scenarios" / name
        directory.mkdir(parents=True)
        (directory / "scenario.yaml").write_text(yaml.safe_dump(data), encoding="utf-8")
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path))
    return tmp_path


@pytest.mark.parametrize(("command", "key", "item_id"), _COMMANDS)
def test_usage_adds_uses_and_sorted_scenarios_to_json(
    library: Path, command: Command, key: str, item_id: str
) -> None:
    result = CliRunner().invoke(command, ["--usage", "--format", "json"])

    assert result.exit_code == 0
    rows = {row[key]: row for row in json.loads(result.output)}
    assert rows[item_id]["scenarios"] == _EXPECTED_SCENARIOS[key]
    assert rows[item_id]["uses"] >= len(rows[item_id]["scenarios"])


@pytest.mark.parametrize(("command", "key", "item_id"), _COMMANDS)
def test_usage_unreferenced_entries_report_zero(library: Path, command: Command, key: str, item_id: str) -> None:
    result = CliRunner().invoke(command, ["--usage", "--format", "json"])

    unreferenced = [row for row in json.loads(result.output) if row[key] != item_id]
    assert unreferenced
    assert all(row["uses"] == 0 and row["scenarios"] == [] for row in unreferenced)


def test_usage_counts_references_and_scenarios_separately(library: Path) -> None:
    result = CliRunner().invoke(list_faults, ["--usage", "--format", "json"])

    row = next(row for row in json.loads(result.output) if row["slug"] == _FAULT)
    assert row["uses"] == 3
    assert row["scenarios"] == [2, 10]


@pytest.mark.parametrize(("command", "key", "item_id"), _COMMANDS)
def test_usage_table_has_used_in_column(library: Path, command: Command, key: str, item_id: str) -> None:
    result = CliRunner().invoke(command, ["--usage"], env=_WIDE)

    assert result.exit_code == 0
    assert "Used in" in result.output
    assert "scenario(s)" in result.output


@pytest.mark.parametrize(("command", "key", "item_id"), _COMMANDS)
def test_without_usage_nothing_is_added(library: Path, command: Command, key: str, item_id: str) -> None:
    table = CliRunner().invoke(command, [], env=_WIDE)
    structured = CliRunner().invoke(command, ["--format", "json"])

    assert "Used in" not in table.output
    assert all("uses" not in row and "scenarios" not in row for row in json.loads(structured.output))


def test_usage_reports_skipped_scenarios(library: Path) -> None:
    broken = library / "scenarios" / "3"
    broken.mkdir()
    (broken / "scenario.yaml").write_text(": invalid: yaml: [", encoding="utf-8")

    result = CliRunner().invoke(list_waiters, ["--usage", "--format", "json"])

    assert result.exit_code == 0
    assert "Skipped scenario 3" in result.output


def test_usage_respects_filters(library: Path) -> None:
    result = CliRunner().invoke(list_faults, ["--usage", "--platform", "no-such-platform", "--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == []
