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


def _generated_path(output: str) -> Path:
    line = next(line for line in output.splitlines() if "Generated statistics" in line)
    return Path(line.split("→", 1)[1].strip())


@pytest.fixture
def temp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    directory = tmp_path / "tmp"
    directory.mkdir()
    monkeypatch.setattr("tempfile.tempdir", str(directory))
    return directory


def test_generate_statistics_writes_yaml_to_temp_dir(tmp_path: Path, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fault_id = next(iter(FAULT_CATALOG))
    _write_scenario(
        tmp_path / "library",
        "1",
        yaml.safe_dump({"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": fault_id}]}]}),
    )
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, [], env={"COLUMNS": "300"})

    assert result.exit_code == 0
    path = _generated_path(result.output)
    assert path.parent == temp_dir
    assert path.suffix == ".yaml"
    report = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert report["totals"]["scenarios"] == 1
    assert report["faults"][fault_id] == {"uses": 1, "scenarios": [1]}
    assert report["domains"]["sre"] == {"uses": 1, "scenarios": [1]}
    assert fault_id not in report["unused"]["faults"]


def test_generate_statistics_json_format(tmp_path: Path, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path / "library", "1", yaml.safe_dump({"faults": [{"injections": [{"id": "not-in-catalog"}]}]}))
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, ["--format", "json"], env={"COLUMNS": "300"})

    assert result.exit_code == 0
    path = _generated_path(result.output)
    assert path.suffix == ".json"
    report = json.loads(path.read_text(encoding="utf-8"))
    assert report["unknown"]["faults"] == {"not-in-catalog": {"uses": 1, "scenarios": [1]}}


def test_generate_statistics_mentions_how_to_keep_file(tmp_path: Path, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, [], env={"COLUMNS": "300"})

    assert result.exit_code == 0
    assert "temporary file" in result.output
    assert "move it to keep it" in result.output


def test_generate_statistics_lists_retired_and_converted_faults_as_inactive(
    tmp_path: Path, temp_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "library"))
    expected = sorted(
        slug
        for slug, fault in FAULT_CATALOG.items()
        if fault.status is not None and (fault.status.retired or fault.status.converted)
    )

    result = CliRunner().invoke(generate_statistics_command, [], env={"COLUMNS": "300"})

    report = yaml.safe_load(_generated_path(result.output).read_text(encoding="utf-8"))
    assert expected
    assert report["inactive"]["faults"] == expected
    assert not set(expected) & set(report["unused"]["faults"])


def test_generate_statistics_reports_skipped_scenarios(tmp_path: Path, temp_dir: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _write_scenario(tmp_path / "library", "1", ": invalid: yaml: [")
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_statistics_command, [], env={"COLUMNS": "300"})

    assert result.exit_code == 0
    assert "Skipped scenario 1" in result.output
    report = yaml.safe_load(_generated_path(result.output).read_text(encoding="utf-8"))
    assert report["totals"]["scenarios"] == 0
