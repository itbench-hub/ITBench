"""Tests for the undeploy orchestrator CLI command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from itbench.cli.commands.undeploy.orchestrator import undeploy_orchestrator


def test_undeploy_orchestrator_with_yes_flag_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.undeploy.orchestrator.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_orchestrator, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator undeployed successfully" in result.output
    mock_run.assert_called_once_with(
        playbook="manage_orchestrator.yaml",
        extra_vars={"cluster": {"kubeconfig": "/kube.conf"}},
        tags=["uninstall"],
    )


def test_undeploy_orchestrator_prompt_confirmed() -> None:
    runner = CliRunner()

    with (
        patch("questionary.confirm") as mock_confirm,
        patch("itbench.cli.commands.undeploy.orchestrator.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = True
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator undeployed successfully" in result.output
    mock_run.assert_called_once()


def test_undeploy_orchestrator_prompt_cancelled() -> None:
    runner = CliRunner()

    with (
        patch("questionary.confirm") as mock_confirm,
        patch("itbench.cli.commands.undeploy.orchestrator.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = False

        result = runner.invoke(undeploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Undeployment cancelled" in result.output
    mock_run.assert_not_called()


def test_undeploy_orchestrator_playbook_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.undeploy.orchestrator.run_playbook",
        side_effect=RuntimeError("argo uninstall failed"),
    ):
        result = runner.invoke(undeploy_orchestrator, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Orchestrator undeploy failed" in result.output
