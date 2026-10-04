"""Tests for the undeploy applications CLI command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from itbench.cli.commands.undeploy.applications import undeploy_applications


def test_undeploy_applications_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.undeploy.applications.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_applications, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "undeployed successfully" in result.output
    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "manage_applications.yaml"
    assert "uninstall_applications" in kwargs["tags"]
    assert kwargs["extra_vars"]["cluster"]["kubeconfig"] == "/kube.conf"


def test_undeploy_applications_playbook_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.undeploy.applications.run_playbook",
        side_effect=RuntimeError("boom"),
    ):
        result = runner.invoke(undeploy_applications, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Undeploy failed" in result.output
