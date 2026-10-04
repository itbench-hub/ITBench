"""Tests for the deploy tools CLI command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from itbench.cli.commands.deploy.tools import deploy_tools


def test_deploy_tools_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.deploy.tools.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_tools, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "deployed successfully" in result.output
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "manage_tools.yaml"
    assert "install_tools" in kwargs["tags"]


def test_deploy_tools_with_scenario_id() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.deploy.tools.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_tools, ["--scenario", "3", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    _, kwargs = mock_run.call_args
    assert kwargs["extra_vars"]["scenario_id"] == "3"


def test_deploy_tools_playbook_failure() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.deploy.tools.run_playbook", side_effect=RuntimeError("bad")):
        result = runner.invoke(deploy_tools, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Deploy failed" in result.output
