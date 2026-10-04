"""Tests for the show solution CLI command."""

from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.show.solution import show_solution


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_ground_truth(scenarios_dir: Path, scenario_id: str, data: dict) -> Path:
    d = scenarios_dir / scenario_id
    d.mkdir(parents=True)
    path = d / "ground_truth.yaml"
    path.write_text(yaml.dump(data), encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Not found
# ---------------------------------------------------------------------------

def test_show_solution_missing_scenario(tmp_path: Path) -> None:
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", tmp_path / "library")
        result = runner.invoke(show_solution, ["999"])
    assert result.exit_code == 1
    assert "No ground truth found" in result.output


# ---------------------------------------------------------------------------
# Basic rendering
# ---------------------------------------------------------------------------

def test_show_solution_renders_panel(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "16", {
        "alerts": [],
        "entities": [{"apiVersion": "apps/v1", "kind": "Deployment", "name": "shipping", "namespace": "otel-demo"}],
        "solutions": [[{"steps": [{"text": "Edit the manifest.", "command": "kubectl edit deployment shipping"}]}]],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["16"])
    assert result.exit_code == 0
    assert "Scenario 16" in result.output
    assert "SOLUTION" in result.output


def test_show_solution_renders_entities(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "16", {
        "alerts": [],
        "entities": [{"apiVersion": "apps/v1", "kind": "Deployment", "name": "shipping", "namespace": "otel-demo"}],
        "solutions": [],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["16"])
    assert result.exit_code == 0
    assert "Deployment" in result.output
    assert "shipping" in result.output
    assert "otel-demo" in result.output


def test_show_solution_renders_alerts(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "16", {
        "alerts": [{"name": "KubePodNotReady", "labels": {}}],
        "entities": [],
        "solutions": [],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["16"])
    assert result.exit_code == 0
    assert "KubePodNotReady" in result.output


def test_show_solution_renders_steps_and_commands(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "16", {
        "alerts": [],
        "entities": [],
        "solutions": [[{"steps": [
            {"text": "Edit the manifest.", "command": "kubectl edit deployment shipping"},
        ]}]],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["16"])
    assert result.exit_code == 0
    assert "Edit the manifest." in result.output
    assert "kubectl edit deployment shipping" in result.output


def test_show_solution_multiple_variants_labeled(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "60", {
        "alerts": [],
        "entities": [],
        "solutions": [[
            {"steps": [{"text": "Fix via ConfigMap.", "command": "kubectl edit configmap foo"}]},
            {"steps": [{"text": "Fix via Deployment.", "command": "kubectl edit deployment bar"}]},
        ]],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["60"])
    assert result.exit_code == 0
    assert "Variant 1" in result.output
    assert "Variant 2" in result.output


def test_show_solution_multiple_faults_labeled(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "60", {
        "alerts": [],
        "entities": [],
        "solutions": [
            [{"steps": [{"text": "Fix fault one."}]}],
            [{"steps": [{"text": "Fix fault two."}]}],
        ],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["60"])
    assert result.exit_code == 0
    assert "Fault 1" in result.output
    assert "Fault 2" in result.output


def test_show_solution_no_solutions_message(tmp_path: Path) -> None:
    lib = tmp_path / "library"
    _write_ground_truth(lib / "scenarios", "1", {
        "alerts": [],
        "entities": [],
        "solutions": [],
    })
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["1"])
    assert result.exit_code == 0
    assert "No solutions recorded" in result.output


def test_show_solution_parses_file_with_schema_comment(tmp_path: Path) -> None:
    """A ground_truth.yaml with a leading yaml-language-server comment should parse cleanly."""
    lib = tmp_path / "library"
    d = lib / "scenarios" / "16"
    d.mkdir(parents=True)
    content = (
        "# yaml-language-server: $schema=../../../schemas/json/library/ground_truth.json\n"
        "---\n"
        "alerts: []\n"
        "entities: []\n"
        "solutions: []\n"
    )
    (d / "ground_truth.yaml").write_text(content, encoding="utf-8")
    runner = CliRunner()
    with pytest.MonkeyPatch().context() as mp:
        mp.setattr("itbench.cli.commands.show.solution._LIBRARY_ROOT", lib)
        result = runner.invoke(show_solution, ["16"])
    assert result.exit_code == 0
    assert "No solutions recorded" in result.output
