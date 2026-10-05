"""Tests for the prepare cluster CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from itbench.cli.commands.prepare.cluster import prepare_cluster_command


def test_prepare_cluster_command_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.prepare.cluster.prepare_cluster") as mock_prepare:
        result = runner.invoke(
            prepare_cluster_command,
            ["--kubeconfig", "/kube.conf", "--context", "kind-test"],
        )

    assert result.exit_code == 0
    assert "Cluster prepared successfully" in result.output

    mock_prepare.assert_called_once_with(
        kubeconfig="/kube.conf",
        context="kind-test",
    )


def test_prepare_cluster_command_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.prepare.cluster.prepare_cluster",
        side_effect=RuntimeError("Insufficient number of worker nodes detected ('1')."),
    ):
        result = runner.invoke(
            prepare_cluster_command,
            ["--kubeconfig", "/kube.conf"],
        )

    assert result.exit_code == 1
    assert "Cluster preparation failed" in result.output
    assert "Insufficient number of worker nodes detected" in result.output
