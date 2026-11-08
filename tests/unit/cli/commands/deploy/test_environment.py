"""Tests for the deploy environment CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.deploy.environment import (
    _applications_extra_vars_from_wizard,
    _extra_variables_from_scenario,
    _tools_extra_vars_from_wizard,
    deploy_environment,
)
from itbench.utils.runner import PlaybookError


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ``.itbench/runs`` artifacts written by the command out of the working tree."""
    monkeypatch.chdir(tmp_path)


# ---------------------------------------------------------------------------
# _extra_variables_from_scenario
# ---------------------------------------------------------------------------


def test_extra_variables_from_scenario_reads_yaml(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()
    extra_vars = {
        "applications_opentelemetry_demo_enabled": True,
        "tools_gateway_enabled": True,
        "tools_observability_enabled": True,
    }
    (scenario_dir / "extra_variables.yaml").write_text(yaml.dump(extra_vars), encoding="utf-8")

    result = _extra_variables_from_scenario(scenario_dir / "scenario.yaml")

    assert result == extra_vars


def test_extra_variables_from_scenario_returns_empty_when_no_file(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()

    result = _extra_variables_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {}


# ---------------------------------------------------------------------------
# _tools_extra_vars_from_wizard
# ---------------------------------------------------------------------------


def test_tools_extra_vars_from_wizard_checkbox() -> None:
    defaults = {
        "tools_gateway_enabled": False,
        "tools_observability_enabled": False,
        "tools_service_mesh_enabled": False,
        "tools_infrastructure_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        mock_stdin.isatty.return_value = True
        mock_checkbox.return_value.ask.return_value = ["tools_gateway_enabled", "tools_observability_enabled"]

        result = _tools_extra_vars_from_wizard()

    assert result["tools_gateway_enabled"] is True
    assert result["tools_observability_enabled"] is True
    assert result["tools_service_mesh_enabled"] is False
    assert result["tools_infrastructure_enabled"] is False


def test_tools_wizard_preselects_choices_from_role_defaults() -> None:
    defaults = {
        "tools_gateway_enabled": True,
        "tools_observability_enabled": False,
        "tools_service_mesh_enabled": True,
        "tools_infrastructure_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        mock_stdin.isatty.return_value = True
        mock_checkbox.return_value.ask.return_value = []

        _tools_extra_vars_from_wizard()

    choices = mock_checkbox.call_args.kwargs["choices"]
    assert [(c.title, c.value, c.checked) for c in choices] == [
        ("Gateway", "tools_gateway_enabled", True),
        ("Observability", "tools_observability_enabled", False),
        ("Service Mesh", "tools_service_mesh_enabled", True),
        ("Infrastructure", "tools_infrastructure_enabled", False),
    ]


def test_applications_wizard_preselects_choices_from_role_defaults() -> None:
    defaults = {
        "applications_opentelemetry_demo_enabled": True,
    }

    with (
        patch("itbench.cli.commands.deploy.environment._load_applications_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        mock_stdin.isatty.return_value = True
        mock_checkbox.return_value.ask.return_value = []

        _applications_extra_vars_from_wizard()

    choices = mock_checkbox.call_args.kwargs["choices"]
    assert [(c.title, c.value, c.checked) for c in choices] == [
        ("OpenTelemetry Demo", "opentelemetry_demo", True),
    ]


def test_tools_extra_vars_from_wizard_non_tty() -> None:
    defaults = {
        "tools_gateway_enabled": False,
        "tools_observability_enabled": False,
        "tools_service_mesh_enabled": False,
        "tools_infrastructure_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        mock_stdin.isatty.return_value = False

        result = _tools_extra_vars_from_wizard()

    mock_checkbox.assert_not_called()
    assert result == defaults


# ---------------------------------------------------------------------------
# _applications_extra_vars_from_wizard
# ---------------------------------------------------------------------------


def test_applications_extra_vars_from_wizard_checkbox_and_subforms() -> None:
    defaults = {
        "applications_opentelemetry_demo_enabled": False,
        "applications_opentelemetry_demo_kubernetes_autoscaling_enabled": False,
        "applications_opentelemetry_demo_load_generator_browser_enabled": False,
        "applications_opentelemetry_demo_load_generator_users": 50,
        "applications_opentelemetry_demo_load_generator_spawn_rate": 5,
    }

    with (
        patch("itbench.cli.commands.deploy.environment._load_applications_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("questionary.checkbox") as mock_checkbox,
        patch("questionary.confirm"),
        patch("questionary.text"),
        patch("questionary.form") as mock_form,
    ):
        mock_stdin.isatty.return_value = True
        mock_checkbox.return_value.ask.return_value = ["opentelemetry_demo"]
        mock_form.return_value.ask.return_value = {
            "autoscaling": True,
            "browser": False,
            "users": "20",
            "spawn_rate": "4",
        }

        result = _applications_extra_vars_from_wizard()

    assert result["applications_opentelemetry_demo_enabled"] is True
    assert result["applications_opentelemetry_demo_kubernetes_autoscaling_enabled"] is True
    assert result["applications_opentelemetry_demo_load_generator_browser_enabled"] is False
    assert result["applications_opentelemetry_demo_load_generator_users"] == 20
    assert result["applications_opentelemetry_demo_load_generator_spawn_rate"] == 4


def test_applications_extra_vars_from_wizard_non_tty() -> None:
    defaults = {
        "applications_opentelemetry_demo_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.environment._load_applications_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        mock_stdin.isatty.return_value = False

        result = _applications_extra_vars_from_wizard()

    mock_checkbox.assert_not_called()
    assert result == defaults


# ---------------------------------------------------------------------------
# deploy_environment command
# ---------------------------------------------------------------------------


def test_deploy_environment_full_success(tmp_path: Path) -> None:
    runner = CliRunner()
    tools_defaults = {"tools_gateway_enabled": False, "tools_observability_enabled": False}
    apps_defaults = {"applications_opentelemetry_demo_enabled": False}

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=tools_defaults),
        patch("itbench.cli.commands.deploy.environment._load_applications_defaults", return_value=apps_defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_environment, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Environment deployed successfully" in result.output
    mock_run.assert_called_once_with(
        playbook="manage_environment.yaml",
        extra_vars={
            "tools_gateway_enabled": False,
            "tools_observability_enabled": False,
            "applications_opentelemetry_demo_enabled": False,
            "environment_tool_management_enabled": True,
            "environment_application_management_enabled": True,
            "environment_recorder_management_enabled": True,
        },
        tags=["install"],
        run_id=mock_run.call_args.kwargs["run_id"],
        verbose=False,
        kubeconfig="/kube.conf",
    )


def test_deploy_environment_only_tools(tmp_path: Path) -> None:
    runner = CliRunner()
    tools_defaults = {"tools_gateway_enabled": True}

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=tools_defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_environment, ["--only", "tools", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_count == 1
    assert mock_run.call_args.kwargs["playbook"] == "manage_environment.yaml"
    assert mock_run.call_args.kwargs["extra_vars"]["environment_tool_management_enabled"] is True
    assert mock_run.call_args.kwargs["extra_vars"]["environment_application_management_enabled"] is False


def test_deploy_environment_only_applications(tmp_path: Path) -> None:
    runner = CliRunner()
    tools_defaults = {"tools_gateway_enabled": False}
    apps_defaults = {"applications_opentelemetry_demo_enabled": True}

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=tools_defaults),
        patch("itbench.cli.commands.deploy.environment._load_applications_defaults", return_value=apps_defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_environment, ["--only", "applications", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_count == 1
    assert mock_run.call_args.kwargs["playbook"] == "manage_environment.yaml"
    assert mock_run.call_args.kwargs["extra_vars"]["environment_tool_management_enabled"] is True
    assert mock_run.call_args.kwargs["extra_vars"]["environment_application_management_enabled"] is True


def test_deploy_environment_only_recorders(tmp_path: Path) -> None:
    runner = CliRunner()
    tools_defaults = {"tools_gateway_enabled": False}

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=tools_defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_environment, ["--only", "recorders", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_count == 1
    extra_vars = mock_run.call_args.kwargs["extra_vars"]
    assert mock_run.call_args.kwargs["playbook"] == "manage_environment.yaml"
    assert extra_vars["environment_tool_management_enabled"] is True
    assert extra_vars["environment_application_management_enabled"] is False
    assert extra_vars["environment_recorder_management_enabled"] is True


def test_deploy_environment_with_scenario(tmp_path: Path) -> None:
    runner = CliRunner()
    scenario_dir = tmp_path / "library" / "scenarios" / "5"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")
    extra_vars = {
        "tools_gateway_enabled": True,
        "tools_observability_enabled": True,
        "applications_opentelemetry_demo_enabled": True,
    }
    (scenario_dir / "extra_variables.yaml").write_text(yaml.dump(extra_vars), encoding="utf-8")

    with (
        patch.dict("os.environ", {"ITBENCH_LIBRARY_PATH": str(tmp_path / "library")}),
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_run.return_value = MagicMock()

        result = runner.invoke(
            deploy_environment,
            ["--scenario", "5", "--kubeconfig", "/kube.conf"],
        )

    assert result.exit_code == 0
    assert mock_run.call_count == 1
    extra_vars = mock_run.call_args.kwargs["extra_vars"]
    assert mock_run.call_args.kwargs["playbook"] == "manage_environment.yaml"
    assert extra_vars["tools_gateway_enabled"] is True
    assert extra_vars["tools_observability_enabled"] is True
    assert extra_vars["applications_opentelemetry_demo_enabled"] is True
    assert extra_vars["environment_tool_management_enabled"] is True
    assert extra_vars["environment_application_management_enabled"] is True
    assert extra_vars["environment_recorder_management_enabled"] is True


def test_deploy_environment_missing_scenario_suggests_close_matches(tmp_path: Path) -> None:
    runner = CliRunner()
    for scenario_id in ("120", "121"):
        scenario_dir = tmp_path / "library" / "scenarios" / scenario_id
        scenario_dir.mkdir(parents=True)
        (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")

    with (
        patch.dict("os.environ", {"ITBENCH_LIBRARY_PATH": str(tmp_path / "library")}),
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        result = runner.invoke(
            deploy_environment,
            ["--scenario", "12", "--kubeconfig", "/kube.conf"],
        )

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "Did you mean" in result.output
    mock_run.assert_not_called()


def test_deploy_environment_scenario_must_be_an_integer() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        result = runner.invoke(deploy_environment, ["--scenario", "../x", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 2
    mock_run.assert_not_called()


def test_deploy_environment_verbose_streams_ansible_output() -> None:
    runner = CliRunner()
    tools_defaults = {"tools_gateway_enabled": False}

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=tools_defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook") as mock_run,
    ):
        mock_stdin.isatty.return_value = False
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_environment, ["-v", "--only", "tools", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["verbose"] is True


def test_deploy_environment_playbook_failure_aborts_later_steps(tmp_path: Path) -> None:
    runner = CliRunner()
    tools_defaults = {"tools_gateway_enabled": False}
    error = PlaybookError("manage_environment.yaml", 2, tmp_path, output="TASK [boom] fatal")

    with (
        patch("itbench.cli.commands.deploy.environment._load_tools_defaults", return_value=tools_defaults),
        patch("itbench.cli.commands.deploy.environment.sys.stdin") as mock_stdin,
        patch("itbench.cli.playbook.run_playbook", side_effect=error) as mock_run,
    ):
        mock_stdin.isatty.return_value = False

        result = runner.invoke(deploy_environment, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Environment deploy failed" in result.output
    assert "TASK [boom] fatal" in result.output
    assert mock_run.call_count == 1
