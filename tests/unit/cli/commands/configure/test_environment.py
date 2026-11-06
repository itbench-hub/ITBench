"""Tests for the configure environment CLI command."""

from unittest.mock import patch

from click.testing import CliRunner

from itbench.cli.commands.configure.environment import configure_environment_command


def test_configure_environment_command_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.configure.environment.configure_environment") as mock_configure:
        result = runner.invoke(configure_environment_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Environment configured successfully" in result.output
    mock_configure.assert_called_once_with(kubeconfig="/kube.conf")


def test_configure_environment_command_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.configure.environment.configure_environment",
        side_effect=RuntimeError("Insufficient number of worker nodes detected ('1')."),
    ):
        result = runner.invoke(configure_environment_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Environment configuration failed" in result.output
    assert "Insufficient number of worker nodes detected" in result.output
