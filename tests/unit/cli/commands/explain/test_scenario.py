"""Tests for the explain scenario CLI command."""

import json

from pathlib import Path
from typing import Any

import yaml

from click.testing import CliRunner

from itbench.cli.commands.explain.scenario import explain_scenario

_SCENARIO: dict[str, Any] = {
    "environment": {"applications": [{"id": "opentelemetry-demo"}], "domains": ["sre"]},
    "faults": [
        {
            "injections": [
                {
                    "id": "crashing-kubernetes-workload-init-container",
                    "targets": [
                        {
                            "kubernetes": {
                                "apiVersion": "apps/v1",
                                "kind": "Deployment",
                                "name": "recommendation",
                                "namespace": "otel-demo",
                            }
                        }
                    ],
                }
            ],
            "waitFor": {
                "preInjection": [{"id": "pause-execution"}],
                "postInjection": [{"id": "delete-workload-pods"}],
            },
        }
    ],
}

_GROUND_TRUTH: dict[str, Any] = {
    "alerts": [{"name": "KubePodNotReady", "labels": {}}],
    "entities": [{"apiVersion": "apps/v1", "kind": "Deployment", "name": "recommendation", "namespace": "otel-demo"}],
    "solutions": [[{"steps": [{"text": "Edit the manifest.", "command": "kubectl edit deployment recommendation"}]}]],
}


def _write_scenario(
    library: Path,
    scenario_id: str,
    scenario: dict[str, Any] | None = None,
    ground_truth: dict[str, Any] | None = None,
) -> None:
    directory = library / "scenarios" / scenario_id
    directory.mkdir(parents=True)
    (directory / "scenario.yaml").write_text(yaml.safe_dump(scenario or _SCENARIO), encoding="utf-8")
    if ground_truth is not None:
        (directory / "ground_truth.yaml").write_text(yaml.safe_dump(ground_truth), encoding="utf-8")


def _invoke(library: Path, args: list[str]) -> Any:
    return CliRunner().invoke(
        explain_scenario,
        args,
        env={"ITBENCH_LIBRARY_PATH": str(library), "COLUMNS": "200"},
    )


def test_explain_scenario_renders_header_and_faults(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16", ground_truth=_GROUND_TRUTH)

    result = _invoke(tmp_path, ["16"])

    assert result.exit_code == 0
    assert "SCENARIO" in result.output
    assert "Scenario 16" in result.output
    assert "sre" in result.output
    assert "opentelemetry-demo" in result.output
    assert "crashing-kubernetes-workload-init-container" in result.output
    assert "Deployment recommendation (otel-demo)" in result.output


def test_explain_scenario_renders_waiters(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16", ground_truth=_GROUND_TRUTH)

    result = _invoke(tmp_path, ["16"])

    assert "pause-execution" in result.output
    assert "delete-workload-pods" in result.output


def test_explain_scenario_hides_unused_waiter_columns(tmp_path: Path) -> None:
    scenario = {
        "environment": {"applications": [{"id": "opentelemetry-demo"}], "domains": ["sre"]},
        "faults": [{"injections": [{"id": "some-fault"}]}],
    }
    _write_scenario(tmp_path, "16", scenario=scenario)

    result = _invoke(tmp_path, ["16"])

    assert result.exit_code == 0
    assert "Injection / targets" in result.output
    assert "Wait before" not in result.output
    assert "Wait after" not in result.output


def test_explain_scenario_shows_only_used_waiter_column(tmp_path: Path) -> None:
    scenario = {
        "environment": {"applications": [], "domains": []},
        "faults": [{"injections": [{"id": "some-fault"}], "waitFor": {"postInjection": [{"id": "pause-execution"}]}}],
    }
    _write_scenario(tmp_path, "16", scenario=scenario)

    result = _invoke(tmp_path, ["16"])

    assert "Wait after" in result.output
    assert "Wait before" not in result.output


def test_explain_scenario_indents_variants_under_faults(tmp_path: Path) -> None:
    ground_truth = {
        "solutions": [
            [{"steps": [{"text": "Step A.", "command": "cmd-a"}]}, {"steps": [{"text": "Step B."}]}],
            [{"steps": [{"text": "Step C."}]}],
        ],
    }
    _write_scenario(tmp_path, "60", ground_truth=ground_truth)

    lines = _invoke(tmp_path, ["60"]).output.splitlines()

    def indent_of(text: str) -> int:
        line = next(line for line in lines if text in line)
        return len(line) - len(line.lstrip())

    assert indent_of("Variant 1") > indent_of("Fault 1")
    assert indent_of("1. Step A.") > indent_of("Variant 1")
    assert indent_of("$ cmd-a") > indent_of("1. Step A.")
    assert indent_of("1. Step C.") > indent_of("Fault 2")


def test_explain_scenario_renders_solution(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16", ground_truth=_GROUND_TRUTH)

    result = _invoke(tmp_path, ["16"])

    assert "SOLUTION" in result.output
    assert "KubePodNotReady" in result.output
    assert "Edit the manifest." in result.output
    assert "kubectl edit deployment recommendation" in result.output


def test_explain_scenario_multiple_variants_and_faults_labeled(tmp_path: Path) -> None:
    ground_truth = {
        "solutions": [
            [{"steps": [{"text": "Fix via ConfigMap."}]}, {"steps": [{"text": "Fix via Deployment."}]}],
            [{"steps": [{"text": "Fix fault two."}]}],
        ],
    }
    _write_scenario(tmp_path, "60", ground_truth=ground_truth)

    result = _invoke(tmp_path, ["60"])

    assert "Fault 1" in result.output
    assert "Fault 2" in result.output
    assert "Variant 1" in result.output
    assert "Variant 2" in result.output


def test_explain_scenario_no_solutions_recorded(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "1", ground_truth={"alerts": [], "entities": [], "solutions": []})

    result = _invoke(tmp_path, ["1"])

    assert result.exit_code == 0
    assert "No solutions recorded" in result.output


def test_explain_scenario_without_ground_truth_file(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "1")

    result = _invoke(tmp_path, ["1"])

    assert result.exit_code == 0
    assert "No ground truth" in result.output


def test_explain_scenario_ground_truth_with_schema_comment(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")
    (tmp_path / "scenarios" / "16" / "ground_truth.yaml").write_text(
        "# yaml-language-server: $schema=../../../schemas/json/library/ground_truth.json\n"
        "---\n"
        "alerts: []\n"
        "entities: []\n"
        "solutions: []\n",
        encoding="utf-8",
    )

    result = _invoke(tmp_path, ["16"])

    assert result.exit_code == 0
    assert "No solutions recorded" in result.output


def test_explain_scenario_escapes_markup(tmp_path: Path) -> None:
    ground_truth = {"solutions": [[{"steps": [{"text": "Run [bold]this[/bold] now."}]}]]}
    _write_scenario(tmp_path, "16", ground_truth=ground_truth)

    result = _invoke(tmp_path, ["16"])

    assert "[bold]this[/bold]" in result.output


def test_explain_scenario_json_output(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16", ground_truth=_GROUND_TRUTH)

    result = _invoke(tmp_path, ["16", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "16"
    assert data["environment"]["domains"] == ["sre"]
    assert data["ground_truth"]["alerts"][0]["name"] == "KubePodNotReady"


def test_explain_scenario_yaml_output_without_ground_truth(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")

    result = _invoke(tmp_path, ["16", "--format", "yaml"])

    assert result.exit_code == 0
    data = yaml.safe_load(result.output)
    assert data["id"] == "16"
    assert data["ground_truth"] is None


def test_explain_scenario_unknown_id(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")

    result = _invoke(tmp_path, ["999"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "itbench list scenarios" in result.output


def test_explain_scenario_unknown_id_suggests_close_match(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")

    result = _invoke(tmp_path, ["160"])

    assert result.exit_code == 1
    assert "Did you mean" in result.output
    assert "16" in result.output


def test_explain_scenario_rejects_path_traversal(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")

    result = _invoke(tmp_path, ["../.."])

    assert result.exit_code == 1
    assert "not found" in result.output


def test_explain_scenario_invalid_yaml(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")
    (tmp_path / "scenarios" / "16" / "scenario.yaml").write_text("a: [unclosed", encoding="utf-8")

    result = _invoke(tmp_path, ["16"])

    assert result.exit_code == 1
    assert "Failed to parse scenario.yaml" in result.output


def test_explain_scenario_non_mapping_yaml(tmp_path: Path) -> None:
    _write_scenario(tmp_path, "16")
    (tmp_path / "scenarios" / "16" / "scenario.yaml").write_text("- a\n- b\n", encoding="utf-8")

    result = _invoke(tmp_path, ["16"])

    assert result.exit_code == 1
    assert "must contain a YAML mapping" in result.output
