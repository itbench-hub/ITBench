"""Tests for the generate kubeconfig CLI command."""

import stat

from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from click.testing import CliRunner
from kubernetes.client.exceptions import ApiException

from itbench.cli.commands.generate.kubeconfig import generate_kubeconfig_command
from itbench.utils.cluster import ClusterAccessBundle

KUBECONFIG = {"apiVersion": "v1", "kind": "Config", "users": [{"name": "u", "user": {"token": "secret-token"}}]}
EXPIRES = datetime(2026, 1, 1, tzinfo=UTC)


@pytest.fixture
def mock_access():
    bundle = ClusterAccessBundle(kubeconfig=KUBECONFIG, expires=EXPIRES, namespaces=["book-info", "otel-demo"])
    with patch("itbench.cli.commands.generate.kubeconfig.create_agent_access", return_value=bundle) as mock:
        yield mock


@pytest.fixture
def scenarios(tmp_path: Path):
    """Scenarios 1-4 with a default, 30, 10 and 120 minute benchmark, and 5 without a scenario.yaml."""
    for scenario, minutes in {"1": None, "2": 30, "3": 10, "4": 120}.items():
        (tmp_path / scenario).mkdir()
        (tmp_path / scenario / "scenario.yaml").write_text("faults: []\n", encoding="utf-8")
        if minutes is not None:
            (tmp_path / scenario / "extra_variables.yaml").write_text(
                f"tools_benchmark_duration_minutes: {minutes}\n", encoding="utf-8"
            )
    (tmp_path / "5").mkdir()
    with patch("itbench.cli.commands.generate.kubeconfig.repository") as repository:
        repository.scenarios = tmp_path
        repository.tools_defaults = tmp_path / "defaults"
        (tmp_path / "defaults").mkdir()
        (tmp_path / "defaults" / "benchmark.yaml").write_text(
            "tools_benchmark_duration_minutes: 15\n", encoding="utf-8"
        )
        yield tmp_path


def test_prints_kubeconfig_on_stdout_by_default(mock_access, scenarios) -> None:
    result = CliRunner().invoke(generate_kubeconfig_command, ["--mission", "diagnosis", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.stdout) == KUBECONFIG
    assert "book-info, otel-demo" in result.stderr
    mock_access.assert_called_once_with(kubeconfig="/kube.conf", mission="diagnosis", minutes=15)


def test_writes_private_file_into_the_output_directory(mock_access, scenarios, tmp_path: Path) -> None:
    output = tmp_path / "out" / "agent"

    result = CliRunner().invoke(
        generate_kubeconfig_command,
        ["--mission", "remediation", "--output", str(output), "--kubeconfig", "/kube.conf"],
    )

    written = output / "kubeconfig-remediation"
    assert result.exit_code == 0
    assert "secret-token" not in result.output
    assert yaml.safe_load(written.read_text(encoding="utf-8")) == KUBECONFIG
    assert stat.S_IMODE(written.stat().st_mode) == 0o600


def test_tightens_permissions_of_an_existing_file(mock_access, scenarios, tmp_path: Path) -> None:
    existing = tmp_path / "kubeconfig-diagnosis"
    existing.write_text("old", encoding="utf-8")
    existing.chmod(0o644)

    result = CliRunner().invoke(
        generate_kubeconfig_command,
        ["--mission", "diagnosis", "--output", str(tmp_path), "--kubeconfig", "/kube.conf"],
    )

    assert result.exit_code == 0
    assert stat.S_IMODE(existing.stat().st_mode) == 0o600


def test_duration_comes_from_the_scenario_extra_variables(mock_access, scenarios) -> None:
    CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "2", "--kubeconfig", "/kube.conf"]
    )

    assert mock_access.call_args.kwargs["minutes"] == 30


def test_duration_falls_back_to_the_role_default_for_a_scenario_without_it(mock_access, scenarios) -> None:
    CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "1", "--kubeconfig", "/kube.conf"]
    )

    assert mock_access.call_args.kwargs["minutes"] == 15


def test_scenario_duration_is_raised_to_the_minimum(mock_access, scenarios) -> None:
    CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "3", "--kubeconfig", "/kube.conf"]
    )

    assert mock_access.call_args.kwargs["minutes"] == 15


def test_scenario_duration_may_exceed_the_duration_option_maximum(mock_access, scenarios) -> None:
    CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "4", "--kubeconfig", "/kube.conf"]
    )

    assert mock_access.call_args.kwargs["minutes"] == 120


def test_scenario_message_does_not_pollute_the_kubeconfig_on_stdout(mock_access, scenarios) -> None:
    result = CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "2", "--kubeconfig", "/kube.conf"]
    )

    assert yaml.safe_load(result.stdout) == KUBECONFIG
    assert "Loaded configuration from scenario 2" in result.stderr


def test_scenario_without_a_scenario_file_fails(mock_access, scenarios) -> None:
    result = CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "5", "--kubeconfig", "/kube.conf"]
    )

    assert result.exit_code == 1
    assert "has no scenario.yaml" in result.output
    mock_access.assert_not_called()


def test_duration_option_overrides_the_scenario(mock_access, scenarios) -> None:
    CliRunner().invoke(
        generate_kubeconfig_command,
        ["--mission", "diagnosis", "--scenario", "2", "--duration", "45", "--kubeconfig", "/kube.conf"],
    )

    assert mock_access.call_args.kwargs["minutes"] == 45


@pytest.mark.parametrize("duration", ["0", "10", "14", "61"])
def test_rejects_durations_outside_the_supported_range(mock_access, scenarios, duration: str) -> None:
    result = CliRunner().invoke(
        generate_kubeconfig_command,
        ["--mission", "diagnosis", "--duration", duration, "--kubeconfig", "/kube.conf"],
    )

    assert result.exit_code == 2
    mock_access.assert_not_called()


def test_requires_a_valid_mission(mock_access, scenarios) -> None:
    result = CliRunner().invoke(generate_kubeconfig_command, ["--mission", "admin", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 2
    mock_access.assert_not_called()


def test_unknown_scenario_fails(mock_access, scenarios) -> None:
    result = CliRunner().invoke(
        generate_kubeconfig_command, ["--mission", "diagnosis", "--scenario", "9", "--kubeconfig", "/kube.conf"]
    )

    assert result.exit_code == 1
    assert "not found" in result.output
    mock_access.assert_not_called()


def test_reports_missing_service_account(scenarios) -> None:
    with patch(
        "itbench.cli.commands.generate.kubeconfig.create_agent_access",
        side_effect=RuntimeError("Expected exactly one ServiceAccount, found 0."),
    ):
        result = CliRunner().invoke(
            generate_kubeconfig_command, ["--mission", "diagnosis", "--kubeconfig", "/kube.conf"]
        )

    assert result.exit_code == 1
    assert "found 0" in result.output


def test_reports_api_errors(scenarios) -> None:
    with patch(
        "itbench.cli.commands.generate.kubeconfig.create_agent_access",
        side_effect=ApiException(status=403, reason="Forbidden"),
    ):
        result = CliRunner().invoke(
            generate_kubeconfig_command, ["--mission", "diagnosis", "--kubeconfig", "/kube.conf"]
        )

    assert result.exit_code == 1
    assert "Forbidden" in result.output
