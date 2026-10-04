"""Tests for the list scenarios CLI command."""

from pathlib import Path
from unittest.mock import patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.list.scenarios import list_scenarios


def test_list_scenarios_no_directory(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.list.scenarios._LIBRARY_ROOT", tmp_path / "library"):
        result = runner.invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "No scenarios directory found" in result.output


def test_list_scenarios_empty_directory(tmp_path: Path) -> None:
    runner = CliRunner()
    library = tmp_path / "library"
    (library / "scenarios").mkdir(parents=True)

    with patch("itbench.cli.commands.list.scenarios._LIBRARY_ROOT", library):
        result = runner.invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "No scenarios found" in result.output


def test_list_scenarios_shows_entries(tmp_path: Path) -> None:
    runner = CliRunner()
    library = tmp_path / "library"
    scenario_dir = library / "scenarios" / "1"
    scenario_dir.mkdir(parents=True)
    scenario = {
        "environment": {"applications": [{"id": "opentelemetry-demo"}]},
        "faults": [{"injections": [{"id": "scaled-to-zero-kubernetes-workload"}]}],
    }
    (scenario_dir / "scenario.yaml").write_text(yaml.dump(scenario), encoding="utf-8")

    with patch("itbench.cli.commands.list.scenarios._LIBRARY_ROOT", library):
        result = runner.invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "1" in result.output
    assert "opentelemetry-demo" in result.output
    assert "scaled-to-zero-kubernetes-workload" in result.output
    assert "1 scenario(s) found" in result.output


def test_list_scenarios_skips_malformed_yaml(tmp_path: Path) -> None:
    runner = CliRunner()
    library = tmp_path / "library"
    scenario_dir = library / "scenarios" / "1"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.yaml").write_text(": invalid: yaml: [", encoding="utf-8")

    with patch("itbench.cli.commands.list.scenarios._LIBRARY_ROOT", library):
        result = runner.invoke(list_scenarios, [])

    assert result.exit_code == 0
    assert "No scenarios found" in result.output
