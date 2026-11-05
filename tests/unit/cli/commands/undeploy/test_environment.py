"""Tests for the undeploy environment CLI command."""

from unittest.mock import MagicMock, call, patch

from click.testing import CliRunner

from itbench.cli.commands.undeploy.environment import undeploy_environment


def test_undeploy_environment_with_yes_flag_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.undeploy.environment.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Environment undeployed successfully" in result.output
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0] == call(
        playbook="manage_environment.yaml",
        extra_vars={
            "cluster": {"kubeconfig": "/kube.conf"},
            "environment_tool_management_enabled": False,
            "environment_application_management_enabled": True,
        },
        tags=["uninstall"],
    )
    assert mock_run.call_args_list[1] == call(
        playbook="manage_environment.yaml",
        extra_vars={
            "cluster": {"kubeconfig": "/kube.conf"},
            "environment_tool_management_enabled": True,
            "environment_application_management_enabled": False,
        },
        tags=["uninstall"],
    )


def test_undeploy_environment_prompt_confirmed() -> None:
    runner = CliRunner()

    with (
        patch("questionary.confirm") as mock_confirm,
        patch("itbench.cli.commands.undeploy.environment.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = True
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Environment undeployed successfully" in result.output
    assert mock_run.call_count == 2


def test_undeploy_environment_prompt_cancelled() -> None:
    runner = CliRunner()

    with (
        patch("questionary.confirm") as mock_confirm,
        patch("itbench.cli.commands.undeploy.environment.run_playbook") as mock_run,
    ):
        mock_confirm.return_value.ask.return_value = False

        result = runner.invoke(undeploy_environment, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Undeployment cancelled" in result.output
    mock_run.assert_not_called()


def test_undeploy_environment_only_applications() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.undeploy.environment.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["--only", "applications", "-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_count == 1
    assert mock_run.call_args == call(
        playbook="manage_environment.yaml",
        extra_vars={
            "cluster": {"kubeconfig": "/kube.conf"},
            "environment_tool_management_enabled": False,
            "environment_application_management_enabled": True,
        },
        tags=["uninstall"],
    )


def test_undeploy_environment_only_tools_runs_applications_then_tools() -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.undeploy.environment.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(undeploy_environment, ["--only", "tools", "-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_count == 2
    assert mock_run.call_args_list[0] == call(
        playbook="manage_environment.yaml",
        extra_vars={
            "cluster": {"kubeconfig": "/kube.conf"},
            "environment_tool_management_enabled": False,
            "environment_application_management_enabled": True,
        },
        tags=["uninstall"],
    )
    assert mock_run.call_args_list[1] == call(
        playbook="manage_environment.yaml",
        extra_vars={
            "cluster": {"kubeconfig": "/kube.conf"},
            "environment_tool_management_enabled": True,
            "environment_application_management_enabled": False,
        },
        tags=["uninstall"],
    )


def test_undeploy_environment_applications_failure_aborts_tools() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.undeploy.environment.run_playbook",
        side_effect=RuntimeError("apps uninstall failed"),
    ) as mock_run:
        result = runner.invoke(undeploy_environment, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Environment undeploy failed" in result.output
    assert mock_run.call_count == 1


def test_undeploy_environment_tools_failure() -> None:
    runner = CliRunner()

    with patch(
        "itbench.cli.commands.undeploy.environment.run_playbook",
        side_effect=[MagicMock(), RuntimeError("tools uninstall failed")],
    ) as mock_run:
        result = runner.invoke(undeploy_environment, ["-y", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Environment undeploy failed" in result.output
    assert mock_run.call_count == 2
