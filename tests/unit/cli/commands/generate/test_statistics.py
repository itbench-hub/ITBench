"""Tests for the generate statistics CLI command."""

import json

from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.statistics import generate_statistics_command
from itbench.models.fault import FAULT_CATALOG


def _write_scenario(library: Path, name: str, content: str) -> None:
    directory = library / "scenarios" / name
    directory.mkdir(parents=True)
    (directory / "scenario.yaml").write_text(content, encoding="utf-8")


def test_generate_statistics_prints_yaml_to_stdout(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fault_id = next(iter(FAULT_CATALOG))
    _write_scenario(
        tmp_path / "library",
        "1",
        yaml.safe_dump({"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": fault_id}]}]}),
    )
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, [])

    assert result.exit_code == 0
    report = yaml.safe_load(result.stdout)
    assert report["totals"]["scenarios"] == 1
    assert report["faults"][fault_id] == {"uses": 1, "scenarios": [1]}
    assert report["domains"]["sre"] == {"uses": 1, "scenarios": [1]}
    assert fault_id not in report["unused"]["faults"]


def test_generate_statistics_json_format(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path / "library", "1", yaml.safe_dump({"faults": [{"injections": [{"id": "not-in-catalog"}]}]}))
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, ["--format", "json"])

    assert result.exit_code == 0
    report = json.loads(result.stdout)
    assert report["unknown"]["faults"] == {"not-in-catalog": {"uses": 1, "scenarios": [1]}}


def test_generate_statistics_output_writes_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path / "library", "1", yaml.safe_dump({"environment": {"domains": ["sre"]}}))
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "library"))
    target = tmp_path / "nested" / "report.json"

    result = CliRunner().invoke(
        generate_statistics_command, ["--format", "json", "--output", str(target)], env={"COLUMNS": "300"}
    )

    assert result.exit_code == 0
    assert "Generated statistics" in result.stdout
    report = json.loads(target.read_text(encoding="utf-8"))
    assert report["totals"]["scenarios"] == 1
    assert report["domains"]["sre"] == {"uses": 1, "scenarios": [1]}


def test_generate_statistics_lists_retired_and_converted_faults_as_inactive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "library"))
    expected = sorted(slug for slug, fault in FAULT_CATALOG.items() if fault.is_inactive)

    result = CliRunner().invoke(generate_statistics_command, [])

    report = yaml.safe_load(result.stdout)
    assert expected
    assert report["inactive"]["faults"] == expected
    assert not set(expected) & set(report["unused"]["faults"])


def test_generate_statistics_reports_skipped_scenarios_on_stderr(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _write_scenario(tmp_path / "library", "1", ": invalid: yaml: [")
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, [], env={"COLUMNS": "300"})

    assert result.exit_code == 0
    assert "Skipped scenario 1" in result.stderr
    assert "Skipped scenario" not in result.stdout
    assert yaml.safe_load(result.stdout)["totals"]["scenarios"] == 0
