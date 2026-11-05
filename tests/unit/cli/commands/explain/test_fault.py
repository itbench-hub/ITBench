"""Tests for the explain fault CLI command."""

import json

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.explain.fault import _placeholder_name, _render_fault, _target_example, explain_fault
from itbench.models.fault import (
    FAULT_CATALOG,
    Fault,
    FaultAlerts,
    FaultConvertedStatus,
    FaultRetiredStatus,
    FaultSolution,
    FaultSolutionStep,
    FaultSolutionTemplates,
    FaultStatus,
    FaultTags,
    FaultTargetReference,
)
from itbench.models.kubernetes import KubernetesObjectKind
from itbench.models.platform import Platform


def _fault(**overrides: object) -> Fault:
    values: dict[str, object] = {
        "name": "Sample Fault",
        "description": "Does something.",
        "expectation": "Something breaks.",
        "platform": Platform.Kubernetes,
        "alerts": [FaultAlerts.KubePodNotReady],
        "tags": [FaultTags.Code],
        "targets": [FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
        "solution_templates": FaultSolutionTemplates(
            templates=[FaultSolution(steps=[FaultSolutionStep(text="Check pods", command="kubectl get pods")])],
        ),
    }
    values.update(overrides)
    return Fault.model_validate(values)


def test_placeholder_name_workload() -> None:
    assert _placeholder_name("KubernetesWorkload") == "<workload-name>"


def test_placeholder_name_service() -> None:
    assert _placeholder_name("KubernetesService") == "<service-name>"


def test_placeholder_name_horizontal_pod_autoscaler() -> None:
    assert _placeholder_name("KubernetesHorizontalPodAutoscaler") == "<horizontal-pod-autoscaler-name>"


def test_target_example_namespaced_object() -> None:
    assert _target_example("KubernetesWorkload") == {
        "kubernetes": {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "name": "<workload-name>",
            "namespace": "<namespace>",
        },
    }


def test_target_example_cluster_scoped_object_has_no_namespace() -> None:
    example = _target_example("KubernetesNamespace")

    assert example is not None
    assert "namespace" not in example["kubernetes"]


def test_target_example_unknown_class() -> None:
    assert _target_example("KubernetesNope") is None


def test_explain_fault_known_slug() -> None:
    runner = CliRunner()
    slug = next(iter(FAULT_CATALOG))

    result = runner.invoke(explain_fault, [slug])

    assert result.exit_code == 0
    assert FAULT_CATALOG[slug].name in result.output


def test_explain_fault_shows_sections() -> None:
    runner = CliRunner()
    slug = next(iter(FAULT_CATALOG))

    result = runner.invoke(explain_fault, [slug])

    assert "DESCRIPTION" in result.output
    assert "EXPECTATION" in result.output
    assert "SCENARIO YAML EXAMPLE" in result.output
    assert "SOLUTIONS" in result.output


def test_explain_fault_example_includes_slug_and_targets() -> None:
    slug = next(s for s, f in FAULT_CATALOG.items() if f.targets)

    result = CliRunner().invoke(explain_fault, [slug], env={"COLUMNS": "200"})

    assert f"id: {slug}" in result.output
    assert "targets:" in result.output
    assert "apiVersion:" in result.output


def test_explain_fault_shows_retired_status() -> None:
    retired = [s for s, f in FAULT_CATALOG.items() if f.status is not None and f.status.retired is not None]
    if not retired:
        pytest.skip("No retired faults in the catalog")
    slug = retired[0]

    result = CliRunner().invoke(explain_fault, [slug], env={"COLUMNS": "200"})

    assert "STATUS" in result.output
    assert "Retired in" in result.output


def test_explain_fault_without_status_has_no_status_section() -> None:
    active = [s for s, f in FAULT_CATALOG.items() if f.status is None]
    if not active:
        pytest.skip("No faults without a status in the catalog")
    slug = active[0]

    result = CliRunner().invoke(explain_fault, [slug])

    assert "STATUS" not in result.output


def test_render_fault_converted_status_points_to_waiter(capsys: pytest.CaptureFixture[str]) -> None:
    fault = _fault(
        alerts=[],
        tags=[],
        targets=[],
        status=FaultStatus(
            converted=FaultConvertedStatus(id="pause-execution", version="1.0.0"),
            retired=FaultRetiredStatus(reason="Replaced.", version="1.0.0"),
        ),
    )

    _render_fault("sample-fault", fault)

    out = capsys.readouterr().out
    assert "Retired in 1.0.0: Replaced." in out
    assert "Converted to waiter pause-execution" in out
    assert "itbench explain waiter pause-execution" in out


def test_render_fault_does_not_interpret_markup(capsys: pytest.CaptureFixture[str]) -> None:
    fault = _fault(
        description="[bold]oops[/bold] [unclosed",
        expectation="expects [red]red[/red]",
        solution_templates=FaultSolutionTemplates(
            templates=[FaultSolution(steps=[FaultSolutionStep(text="run [it]", command="echo [a]")])],
        ),
        resources=["https://example.com/[x]"],
    )

    _render_fault("sample-fault", fault)

    out = capsys.readouterr().out
    assert "[bold]oops[/bold] [unclosed" in out
    assert "expects [red]red[/red]" in out
    assert "run [it]" in out
    assert "$ echo [a]" in out
    assert "https://example.com/[x]" in out


def test_render_fault_example_is_valid_yaml(capsys: pytest.CaptureFixture[str]) -> None:
    _render_fault("sample-fault", _fault())

    out = capsys.readouterr().out
    block = out.split("SCENARIO YAML EXAMPLE", 1)[1].split("SOLUTIONS", 1)[0]
    body = "\n".join(line for line in block.splitlines() if not line.strip().startswith("#"))
    data = yaml.safe_load(body)
    injection = data["faults"][0]["injections"][0]
    assert injection["id"] == "sample-fault"
    assert injection["targets"][0]["kubernetes"]["name"] == "<workload-name>"


def test_explain_fault_json_output() -> None:
    slug = next(iter(FAULT_CATALOG))

    result = CliRunner().invoke(explain_fault, [slug, "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == slug
    assert data["name"] == FAULT_CATALOG[slug].name


def test_explain_fault_yaml_output() -> None:
    slug = next(iter(FAULT_CATALOG))

    result = CliRunner().invoke(explain_fault, [slug, "--format", "yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output)["id"] == slug


def test_explain_fault_unknown_slug() -> None:
    runner = CliRunner()

    result = runner.invoke(explain_fault, ["no-such-fault"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "itbench list faults" in result.output


def test_explain_fault_unknown_slug_suggests_close_match() -> None:
    slug = next(iter(FAULT_CATALOG))

    result = CliRunner().invoke(explain_fault, [slug[:-1]])

    assert result.exit_code == 1
    assert "Did you mean" in result.output
    assert slug in result.output
