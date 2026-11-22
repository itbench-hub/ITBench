"""Tests for the generate bundle CLI command."""

import json
import stat

from pathlib import Path
from unittest.mock import patch

import pytest

from click.testing import CliRunner
from kubernetes.client.exceptions import ApiException

from itbench.cli.commands.generate.bundle import generate_bundle_command
from itbench.utils.cluster import AgentEndpoints, ClusterAccessBundle

DIAGNOSIS = {"kind": "Config", "users": [{"name": "d", "user": {"token": "diagnosis-token"}}]}
REMEDIATION = {"kind": "Config", "users": [{"name": "r", "user": {"token": "remediation-token"}}]}
ENDPOINTS = AgentEndpoints(
    mcp_servers={"jaeger": "https://10.0.0.1:8443/mcp/jaeger", "opencost": None, "prometheus": None},
    ca_certificate="-----BEGIN CERTIFICATE-----",
    token="mcp-token",  # noqa: S106
)
EXPECTED_HEADERS = {"Authorization": "Bearer mcp-token"}


def _access(kubeconfig: dict) -> ClusterAccessBundle:
    return ClusterAccessBundle(kubeconfig=kubeconfig, expires=None, namespaces=["otel-demo"])  # type: ignore[arg-type]


@pytest.fixture
def mock_endpoints():
    with patch("itbench.cli.commands.generate.bundle.read_agent_endpoints", return_value=ENDPOINTS) as mock:
        yield mock


@pytest.fixture
def mock_access():
    kubeconfigs = {"diagnosis": DIAGNOSIS, "remediation": REMEDIATION}

    def create(kubeconfig: str, mission: str, minutes: int) -> ClusterAccessBundle:
        return _access(kubeconfigs[mission])

    with patch("itbench.cli.commands.generate.bundle.create_agent_access", side_effect=create) as mock:
        yield mock


@pytest.fixture
def scenarios(tmp_path: Path):
    (tmp_path / "scenarios" / "1").mkdir(parents=True)
    (tmp_path / "scenarios" / "2").mkdir()
    (tmp_path / "scenarios" / "2" / "extra_variables.yaml").write_text(
        "recorders_benchmark_duration_minutes: 30\n", encoding="utf-8"
    )
    (tmp_path / "defaults").mkdir()
    (tmp_path / "defaults" / "benchmark.yaml").write_text(
        "recorders_benchmark_duration_minutes: 15\n", encoding="utf-8"
    )
    with (
        patch("itbench.cli.commands.generate.bundle.repository") as bundle_repository,
        patch("itbench.cli.commands.generate.kubeconfig.repository") as kubeconfig_repository,
    ):
        for repository in (bundle_repository, kubeconfig_repository):
            repository.scenarios = tmp_path / "scenarios"
            repository.recorders_defaults = tmp_path / "defaults"
        yield tmp_path


def test_prints_the_bundle_on_stdout(mock_endpoints, mock_access, scenarios) -> None:
    result = CliRunner().invoke(generate_bundle_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert json.loads(result.stdout) == {
        "mcp_servers": ENDPOINTS.mcp_servers,
        "headers": EXPECTED_HEADERS,
        "ca_certificate": ENDPOINTS.ca_certificate,
        "kubeconfigs": {"diagnosis": DIAGNOSIS, "remediation": REMEDIATION},
    }
    mock_endpoints.assert_called_once_with(kubeconfig="/kube.conf")
    assert [call.kwargs["mission"] for call in mock_access.call_args_list] == ["diagnosis", "remediation"]
    assert all(call.kwargs["minutes"] == 15 for call in mock_access.call_args_list)


def test_agent_that_was_not_deployed_is_null(mock_endpoints, scenarios) -> None:
    def create(kubeconfig: str, mission: str, minutes: int) -> ClusterAccessBundle:
        if mission == "remediation":
            raise RuntimeError("Expected exactly one ServiceAccount, found 0.")
        return _access(DIAGNOSIS)

    with patch("itbench.cli.commands.generate.bundle.create_agent_access", side_effect=create):
        result = CliRunner().invoke(generate_bundle_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert json.loads(result.stdout)["kubeconfigs"] == {"diagnosis": DIAGNOSIS, "remediation": None}
    assert "No remediation agent" in result.stderr


def test_writes_a_private_file_into_the_output_directory(
    mock_endpoints, mock_access, scenarios, tmp_path: Path
) -> None:
    output = tmp_path / "out" / "agent"

    result = CliRunner().invoke(generate_bundle_command, ["--output", str(output), "--kubeconfig", "/kube.conf"])

    written = output / "bundle.json"
    assert result.exit_code == 0
    assert "mcp-token" not in result.output
    assert json.loads(written.read_text(encoding="utf-8"))["headers"] == EXPECTED_HEADERS
    assert stat.S_IMODE(written.stat().st_mode) == 0o600


def test_duration_comes_from_the_scenario(mock_endpoints, mock_access, scenarios) -> None:
    CliRunner().invoke(generate_bundle_command, ["--scenario", "2", "--kubeconfig", "/kube.conf"])

    assert all(call.kwargs["minutes"] == 30 for call in mock_access.call_args_list)


def test_duration_option_overrides_the_scenario(mock_endpoints, mock_access, scenarios) -> None:
    CliRunner().invoke(generate_bundle_command, ["--scenario", "2", "--duration", "45", "--kubeconfig", "/kube.conf"])

    assert all(call.kwargs["minutes"] == 45 for call in mock_access.call_args_list)


def test_scenario_message_does_not_pollute_the_bundle_on_stdout(mock_endpoints, mock_access, scenarios) -> None:
    result = CliRunner().invoke(generate_bundle_command, ["--scenario", "1", "--kubeconfig", "/kube.conf"])

    assert json.loads(result.stdout)
    assert "Loaded configuration from scenario 1" in result.stderr


def test_unknown_scenario_fails(mock_endpoints, mock_access, scenarios) -> None:
    result = CliRunner().invoke(generate_bundle_command, ["--scenario", "9", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "not found" in " ".join(result.output.split())
    mock_endpoints.assert_not_called()


@pytest.mark.parametrize("duration", ["0", "14", "61"])
def test_rejects_durations_outside_the_supported_range(mock_endpoints, mock_access, scenarios, duration: str) -> None:
    result = CliRunner().invoke(generate_bundle_command, ["--duration", duration, "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 2
    mock_endpoints.assert_not_called()


def test_reports_a_missing_bundle_secret(mock_access, scenarios) -> None:
    with patch(
        "itbench.cli.commands.generate.bundle.read_agent_endpoints",
        side_effect=RuntimeError("Secret 'itbench-mcp-servers/itbench-agent-bundle' not found."),
    ):
        result = CliRunner().invoke(generate_bundle_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "not found" in " ".join(result.output.split())
    mock_access.assert_not_called()


def test_reports_api_errors(mock_endpoints, scenarios) -> None:
    with patch(
        "itbench.cli.commands.generate.bundle.create_agent_access",
        side_effect=ApiException(status=403, reason="Forbidden"),
    ):
        result = CliRunner().invoke(generate_bundle_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Forbidden" in result.output
