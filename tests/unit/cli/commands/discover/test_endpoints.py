"""Tests for the discover endpoints CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from itbench.cli.commands.discover.endpoints import endpoints
from itbench.utils.endpoints import ToolEndpoint


def test_endpoints_renders_table() -> None:
    runner = CliRunner()
    fake_results = [
        ToolEndpoint(tool="Prometheus", host="http://1.2.3.4", paths=["/alerts"]),
        ToolEndpoint(tool="Jaeger", host="http://1.2.3.4/jaeger", paths=["/"]),
    ]

    with patch("itbench.cli.commands.discover.endpoints.discover_endpoints", return_value=fake_results):
        result = runner.invoke(
            endpoints,
            ["--kubeconfig", "/kube.conf", "--platform", "kubernetes"],
        )

    assert result.exit_code == 0
    assert "Prometheus" in result.output
    assert "Jaeger" in result.output


def test_endpoints_no_results_warns() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.discover.endpoints.discover_endpoints", return_value=[]):
        result = runner.invoke(
            endpoints,
            ["--kubeconfig", "/kube.conf", "--platform", "kubernetes"],
        )

    assert result.exit_code == 0
    assert "No tool endpoints found" in result.output


def test_endpoints_discovery_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.discover.endpoints.discover_endpoints",
        side_effect=RuntimeError("cluster unreachable"),
    ):
        result = runner.invoke(
            endpoints,
            ["--kubeconfig", "/kube.conf", "--platform", "kubernetes"],
        )

    assert result.exit_code == 1
    assert "Endpoint discovery failed" in result.output


def test_endpoints_rejects_invalid_platform() -> None:
    runner = CliRunner()

    result = runner.invoke(
        endpoints,
        ["--kubeconfig", "/kube.conf", "--platform", "invalid"],
    )

    assert result.exit_code != 0


def test_endpoints_openshift_platform() -> None:
    runner = CliRunner()
    fake_results = [
        ToolEndpoint(tool="Prometheus", host="http://prometheus.apps.example.com", paths=["/alerts"]),
    ]

    with patch("itbench.cli.commands.discover.endpoints.discover_endpoints", return_value=fake_results) as mock_disc:
        result = runner.invoke(
            endpoints,
            ["--kubeconfig", "/kube.conf", "--platform", "openshift"],
        )

    assert result.exit_code == 0
    _, kwargs = mock_disc.call_args
    assert kwargs["platform"] == "openshift"
