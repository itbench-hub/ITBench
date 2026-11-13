"""Tests for itbench check resources localhost."""

import json

from unittest.mock import patch

import pytest

from click.testing import CliRunner

from itbench.cli.commands.check.resources.localhost import (
    ResourceCheck,
    detect_cpus,
    detect_memory_gb,
    evaluate,
    resources_localhost_command,
)

_MODULE = "itbench.cli.commands.check.resources.localhost"


def _invoke(cpus: int, memory_gb: int, args: list[str] | None = None, platform: str = "linux"):
    with (
        patch(f"{_MODULE}.detect_cpus", return_value=cpus),
        patch(f"{_MODULE}.detect_memory_gb", return_value=memory_gb),
        patch(f"{_MODULE}.sys.platform", platform),
    ):
        return CliRunner().invoke(resources_localhost_command, args or [])


def _by_name(checks: list[ResourceCheck]) -> dict[str, ResourceCheck]:
    return {check.resource: check for check in checks}


def test_evaluate_adds_both_clusters_by_default() -> None:
    checks = _by_name(evaluate(12, 24, ["environment", "orchestrator"]))

    assert (checks["CPU"].required, checks["Memory"].required) == (12, 24)


@pytest.mark.parametrize(
    ("selected", "cpu", "memory"),
    [(["environment"], 8, 16), (["orchestrator"], 4, 8)],
)
def test_evaluate_uses_the_requirement_of_a_single_cluster(selected: list[str], cpu: int, memory: int) -> None:
    checks = _by_name(evaluate(64, 128, selected))

    assert (checks["CPU"].required, checks["Memory"].required) == (cpu, memory)


def test_evaluate_accepts_resources_exactly_at_the_requirement() -> None:
    assert all(check.sufficient for check in evaluate(12, 24, ["environment", "orchestrator"]))


def test_evaluate_flags_only_cpu_when_cpu_is_short() -> None:
    checks = _by_name(evaluate(11, 24, ["environment", "orchestrator"]))

    assert not checks["CPU"].sufficient
    assert checks["Memory"].sufficient


def test_evaluate_flags_only_memory_when_memory_is_short() -> None:
    checks = _by_name(evaluate(12, 23, ["environment", "orchestrator"]))

    assert checks["CPU"].sufficient
    assert not checks["Memory"].sufficient


def test_evaluate_flags_both_when_both_are_short() -> None:
    assert not any(check.sufficient for check in evaluate(1, 1, ["environment"]))


def test_detect_cpus_reports_at_least_one_cpu() -> None:
    assert detect_cpus() >= 1


def test_detect_cpus_returns_zero_when_the_count_is_unknown() -> None:
    with patch(f"{_MODULE}.os.process_cpu_count", return_value=None):
        assert detect_cpus() == 0


def test_detect_memory_gb_rounds_down_to_whole_gib() -> None:
    page_size = 4096
    values = {"SC_PAGE_SIZE": page_size, "SC_PHYS_PAGES": 16 * 1024**3 // page_size - 1}
    with patch(f"{_MODULE}.os.sysconf", side_effect=values.__getitem__):
        assert detect_memory_gb() == 15


def test_command_prints_no_warning_when_resources_are_sufficient() -> None:
    result = _invoke(12, 24)

    assert result.exit_code == 0, result.output
    assert "recommended amount" not in result.output


def test_command_warns_about_cpu_and_still_exits_zero() -> None:
    result = _invoke(4, 24)

    assert result.exit_code == 0
    assert "recommended amount of CPU (12+ cores)" in result.output
    assert "recommended amount of Memory" not in result.output


def test_command_warns_about_memory_and_still_exits_zero() -> None:
    result = _invoke(12, 8)

    assert result.exit_code == 0
    assert "recommended amount of Memory (24+ GB)" in result.output
    assert "recommended amount of CPU" not in result.output


def test_command_warns_about_both_when_both_are_short() -> None:
    result = _invoke(2, 2)

    assert result.exit_code == 0
    assert "recommended amount of CPU" in result.output
    assert "recommended amount of Memory" in result.output
    assert "degraded or inconsistent performance" in result.output


def test_command_only_environment_uses_the_environment_requirement() -> None:
    result = _invoke(8, 16, ["--only", "environment"])

    assert result.exit_code == 0
    assert "recommended amount" not in result.output
    assert "Checked for: environment" in result.output


def test_command_only_orchestrator_uses_the_orchestrator_requirement() -> None:
    result = _invoke(3, 8, ["--only", "orchestrator"])

    assert result.exit_code == 0
    assert "recommended amount of CPU (4+ cores)" in result.output
    assert "Checked for: orchestrator" in result.output


def test_command_checks_both_clusters_without_only() -> None:
    result = _invoke(12, 24)

    assert "Checked for: environment, orchestrator" in result.output


def test_command_rejects_an_unknown_cluster_for_only() -> None:
    result = _invoke(12, 24, ["--only", "runner"])

    assert result.exit_code == 2
    assert "Invalid value for '--only'" in result.output


def test_command_json_output_lists_each_resource_with_its_status() -> None:
    result = _invoke(4, 24, ["--format", "json"])

    assert result.exit_code == 0, result.output
    assert json.loads(result.output) == [
        {"resource": "CPU (cores)", "required": 12, "found": 4, "status": "insufficient"},
        {"resource": "Memory (GB)", "required": 24, "found": 24, "status": "sufficient"},
    ]


def test_command_json_output_has_no_warning_text() -> None:
    result = _invoke(1, 1, ["--format", "json"])

    assert "recommended amount" not in result.output


def test_command_mentions_the_container_vm_on_macos() -> None:
    result = _invoke(12, 24, platform="darwin")

    assert "container VM" in result.output


def test_command_omits_the_container_vm_note_on_linux() -> None:
    result = _invoke(12, 24, platform="linux")

    assert "container VM" not in result.output
