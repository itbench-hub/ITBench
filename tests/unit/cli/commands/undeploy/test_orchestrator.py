"""Tests for the undeploy orchestrator CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from itbench.cli.commands.undeploy.orchestrator import undeploy_orchestrator
from itbench.utils.runner import PlaybookError


def test_undeploy_orchestrator_with_yes_flag_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_orchestrator, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator undeployed successfully" in result.output
    mock_run.assert_called_once_with(
        playbook="manage_orchestrator.yaml",
        extra_vars={"cluster": {"kubeconfig": "/kube.conf"}},
        tags=["uninstall"],
        run_id=None,
        verbose=False,
    )


def test_undeploy_orchestrator_prompt_confirmed() -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.return_value.ask.return_value = True
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator undeployed successfully" in result.output
    mock_run.assert_called_once()


def test_undeploy_orchestrator_prompt_cancelled() -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.return_value.ask.return_value = False

        result = runner.invoke(undeploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Undeployment cancelled" in result.output
    mock_run.assert_not_called()


def test_undeploy_orchestrator_without_terminal_requires_yes() -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False

        result = runner.invoke(undeploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "--yes" in result.output
    mock_run.assert_not_called()


def test_undeploy_orchestrator_verbose_streams_ansible_output() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_orchestrator, ["-y", "-v", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["verbose"] is True


def test_undeploy_orchestrator_playbook_failure_shows_ansible_output(tmp_path: Path) -> None:
    runner = CliRunner()
    error = PlaybookError("manage_orchestrator.yaml", 2, tmp_path, output="TASK [boom] fatal")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error):
        result = runner.invoke(undeploy_orchestrator, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Orchestrator undeploy failed" in result.output
    assert "TASK [boom] fatal" in result.output
