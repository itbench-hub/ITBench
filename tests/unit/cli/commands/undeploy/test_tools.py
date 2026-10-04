"""Tests for the undeploy tools CLI command."""

from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from itbench.cli.commands.undeploy.tools import undeploy_tools


def test_undeploy_tools_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.undeploy.tools.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_tools, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "undeployed successfully" in result.output
    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "manage_tools.yaml"
    assert "uninstall_tools" in kwargs["tags"]
    assert kwargs["extra_vars"]["cluster"]["kubeconfig"] == "/kube.conf"


def test_undeploy_tools_playbook_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.undeploy.tools.run_playbook",
        side_effect=RuntimeError("boom"),
    ):
        result = runner.invoke(undeploy_tools, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Undeploy failed" in result.output
