"""Tests for the undeploy environment CLI command."""

import io

from pathlib import Path
from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from itbench.cli.commands.undeploy.environment import undeploy_environment
from itbench.utils.runner import PlaybookError

_APPLICATIONS_STEP = call(
    playbook="manage_environment.yaml",
    extra_vars={
        "environment_tool_management_enabled": False,
        "environment_application_management_enabled": True,
    },
    tags=["uninstall"],
    run_id=None,
    verbose=False,
    kubeconfig="/kube.conf",
)

_TOOLS_STEP = call(
    playbook="manage_environment.yaml",
    extra_vars={
        "environment_tool_management_enabled": True,
        "environment_application_management_enabled": False,
    },
    tags=["uninstall"],
    run_id=None,
    verbose=False,
    kubeconfig="/kube.conf",
)


def test_undeploy_environment_with_yes_flag_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Environment undeployed successfully" in result.output
    assert mock_run.call_args_list == [_APPLICATIONS_STEP, _TOOLS_STEP]


def test_undeploy_environment_prompt_confirmed(terminal_input: io.BytesIO) -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = True
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["--kubeconfig", "/kube.conf"], input=terminal_input)

    assert result.exit_code == 0
    assert "Environment undeployed successfully" in result.output
    assert mock_run.call_count == 2
    assert mock_confirm.call_args.args[0] == "Are you sure you want to undeploy the environment?"


def test_undeploy_environment_prompt_cancelled(terminal_input: io.BytesIO) -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = False

        result = runner.invoke(undeploy_environment, ["--kubeconfig", "/kube.conf"], input=terminal_input)

    assert result.exit_code == 0
    assert "Undeployment cancelled" in result.output
    mock_run.assert_not_called()


def test_undeploy_environment_without_terminal_requires_yes() -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False

        result = runner.invoke(undeploy_environment, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "--yes" in result.output
    mock_run.assert_not_called()


def test_undeploy_environment_only_applications_leaves_tools(terminal_input: io.BytesIO) -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = True
        mock_run.return_value = MagicMock()

        result = runner.invoke(
            undeploy_environment,
            ["--only", "applications", "--kubeconfig", "/kube.conf"],
            input=terminal_input,
        )

    assert result.exit_code == 0
    assert mock_run.call_args_list == [_APPLICATIONS_STEP]
    assert mock_confirm.call_args.args[0] == "Are you sure you want to undeploy the environment applications?"


def test_undeploy_environment_does_not_offer_only_tools() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        result = runner.invoke(undeploy_environment, ["--only", "tools", "-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_undeploy_environment_verbose_streams_ansible_output() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["-y", "-v", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert [c.kwargs["verbose"] for c in mock_run.call_args_list] == [True, True]


def test_undeploy_environment_applications_failure_aborts_tools(tmp_path: Path) -> None:
    runner = CliRunner()
    error = PlaybookError("manage_environment.yaml", 2, tmp_path, output="TASK [boom] fatal")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error) as mock_run:
        result = runner.invoke(undeploy_environment, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Environment undeploy failed" in result.output
    assert "TASK [boom] fatal" in result.output
    assert mock_run.call_count == 1


def test_undeploy_environment_tools_failure(tmp_path: Path) -> None:
    runner = CliRunner()
    error = PlaybookError("manage_environment.yaml", 2, tmp_path)

    with patch("itbench.cli.playbook.run_playbook", side_effect=[MagicMock(), error]) as mock_run:
        result = runner.invoke(undeploy_environment, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Environment undeploy failed" in result.output
    assert mock_run.call_count == 2
