"""Tests for the discover targets CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from itbench.cli.commands.discover.targets import targets
from itbench.models.kubernetes import KubernetesObject


def test_targets_renders_table() -> None:
    runner = CliRunner()
    fake_workloads = {
        "opentelemetry-demo": [
            KubernetesObject(kind="Deployment", name="frontend", namespace="otel"),
            KubernetesObject(kind="Service", name="frontend-svc", namespace="otel"),
        ],
    }

    with patch("itbench.cli.commands.discover.targets.discover_workloads", return_value=fake_workloads):
        result = runner.invoke(targets, [])

    assert result.exit_code == 0
    assert "opentelemetry-demo" in result.output
    assert "frontend" in result.output
    assert "Deployment" in result.output


def test_targets_no_workloads_warns() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.discover.targets.discover_workloads", return_value={}):
        result = runner.invoke(targets, [])

    assert result.exit_code == 0
    assert "No workloads discovered" in result.output


def test_targets_discovery_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.discover.targets.discover_workloads",
        side_effect=RuntimeError("playbook failed"),
    ):
        result = runner.invoke(targets, [])

    assert result.exit_code == 1
    assert "Discovery failed" in result.output


def test_targets_filtered_by_app() -> None:
    runner = CliRunner()
    fake_workloads = {
        "book-info": [
            KubernetesObject(kind="Deployment", name="productpage", namespace="book-info"),
        ],
    }

    with patch(
        "itbench.cli.commands.discover.targets.discover_workloads", return_value=fake_workloads
    ) as mock_disc:
        result = runner.invoke(targets, ["--app", "book-info"])

    assert result.exit_code == 0
    mock_disc.assert_called_once_with(app_id="book-info")
    assert "productpage" in result.output
