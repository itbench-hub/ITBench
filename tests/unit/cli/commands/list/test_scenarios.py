"""Tests for the list scenarios CLI command."""

import json

from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.list.scenarios import list_scenarios


def _write_scenario(library: Path, name: str, data: dict | None, raw: str | None = None) -> None:
    scenario_dir = library / "scenarios" / name
    scenario_dir.mkdir(parents=True)
    content = raw if raw is not None else yaml.dump(data)
    (scenario_dir / "scenario.yaml").write_text(content, encoding="utf-8")


def test_list_scenarios_empty_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "scenarios").mkdir()
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "No scenarios found" in result.output


def test_list_scenarios_shows_entries(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(
        tmp_path,
        "1",
        {
            "environment": {"applications": [{"id": "opentelemetry-demo"}], "domains": ["sre"]},
            "faults": [{"injections": [{"id": "scaled-to-zero-kubernetes-workload"}]}],
        },
    )
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, [], env={"COLUMNS": "300"})

    assert result.exit_code == 0
    assert "opentelemetry-demo" in result.output
    assert "scaled-to-zero-kubernetes-workload" in result.output
    assert "1 scenario(s) found" in result.output


def test_list_scenarios_sorted_numerically(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("10", "2", "1"):
        _write_scenario(tmp_path, name, {"environment": {}})
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, ["--format", "json"])

    assert [row["id"] for row in json.loads(result.output)] == ["1", "2", "10"]


def test_list_scenarios_reports_malformed_yaml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path, "1", None, raw=": invalid: yaml: [")
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "Skipped scenario 1" in result.output
    assert "No scenarios found" in result.output


def test_list_scenarios_reports_empty_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path, "1", None, raw="")
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "Skipped scenario 1" in result.output


def test_list_scenarios_json_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(
        tmp_path,
        "7",
        {
            "environment": {"applications": [{"id": "book-info"}], "domains": ["sre"]},
            "faults": [{"injections": [{"id": "some-fault"}]}],
        },
    )
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, ["--format", "json"])

    assert result.exit_code == 0
    assert json.loads(result.output) == [
        {"id": "7", "domains": ["sre"], "applications": ["book-info"], "faults": ["some-fault"]},
    ]


def test_list_scenarios_yaml_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path, "7", {"environment": {"domains": ["sre"]}})
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))

    result = CliRunner().invoke(list_scenarios, ["--format", "yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output)[0]["id"] == "7"
