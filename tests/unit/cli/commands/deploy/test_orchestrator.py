"""Tests for the deploy orchestrator CLI command."""

from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from itbench.cli.commands.deploy.orchestrator import deploy_orchestrator


def test_deploy_orchestrator_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.deploy.orchestrator.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator deployed successfully" in result.output
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "manage_orchestrator.yaml"
    assert kwargs["tags"] == ["install"]
    assert kwargs["extra_vars"]["cluster"]["kubeconfig"] == "/kube.conf"


def test_deploy_orchestrator_playbook_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.deploy.orchestrator.run_playbook",
        side_effect=RuntimeError("orchestrator install failed"),
    ):
        result = runner.invoke(deploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Orchestrator deploy failed" in result.output
