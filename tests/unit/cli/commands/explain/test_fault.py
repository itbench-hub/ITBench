"""Tests for the explain fault CLI command."""

from click.testing import CliRunner

from itbench.cli.commands.explain.fault import _placeholder_name, explain_fault
from itbench.models.fault import FAULT_CATALOG


def test_placeholder_name_workload() -> None:
    assert _placeholder_name("KubernetesWorkload") == "<workload-name>"


def test_placeholder_name_service() -> None:
    assert _placeholder_name("KubernetesService") == "<service-name>"


def test_placeholder_name_horizontal_pod_autoscaler() -> None:
    assert _placeholder_name("KubernetesHorizontalPodAutoscaler") == "<horizontal-pod-autoscaler-name>"


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


def test_explain_fault_unknown_slug() -> None:
    runner = CliRunner()

    result = runner.invoke(explain_fault, ["no-such-fault"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "itbench list faults" in result.output
