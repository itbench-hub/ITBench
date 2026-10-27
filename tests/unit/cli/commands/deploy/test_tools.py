"""Tests for the deploy tools CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.deploy.tools import (
    _extra_vars_from_scenario,
    _extra_vars_from_wizard,
    deploy_tools,
)


# ---------------------------------------------------------------------------
# _extra_vars_from_scenario
# ---------------------------------------------------------------------------

def test_extra_vars_from_scenario_reads_tools_vars(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()
    ev = {
        "applications_opentelemetry_demo_enabled": True,
        "tools_gateway_enabled": True,
        "tools_observability_enabled": True,
    }
    (scenario_dir / "extra_variables.yaml").write_text(yaml.dump(ev), encoding="utf-8")

    result = _extra_vars_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {"tools_gateway_enabled": True, "tools_observability_enabled": True}


def test_extra_vars_from_scenario_returns_empty_when_no_file(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()

    result = _extra_vars_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {}


def test_extra_vars_from_scenario_includes_service_mesh(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()
    ev = {
        "applications_book_info_enabled": True,
        "tools_gateway_enabled": True,
        "tools_observability_enabled": True,
        "tools_service_mesh_enabled": True,
    }
    (scenario_dir / "extra_variables.yaml").write_text(yaml.dump(ev), encoding="utf-8")

    result = _extra_vars_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {
        "tools_gateway_enabled": True,
        "tools_observability_enabled": True,
        "tools_service_mesh_enabled": True,
    }


# ---------------------------------------------------------------------------
# _extra_vars_from_wizard
# ---------------------------------------------------------------------------

def test_extra_vars_from_wizard_builds_vars() -> None:
    defaults = {
        "tools_gateway_enabled": False,
        "tools_observability_enabled": False,
        "tools_service_mesh_enabled": False,
        "tools_infrastructure_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.tools._load_role_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.tools.sys.stdin") as mock_stdin,
        patch("questionary.confirm") as mock_confirm,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=True)),   # gateway
            MagicMock(ask=MagicMock(return_value=True)),   # observability
            MagicMock(ask=MagicMock(return_value=False)),  # service mesh
            MagicMock(ask=MagicMock(return_value=False)),  # infrastructure
        ]

        result = _extra_vars_from_wizard()

    assert result["tools_gateway_enabled"] is True
    assert result["tools_observability_enabled"] is True
    assert result["tools_service_mesh_enabled"] is False
    assert result["tools_infrastructure_enabled"] is False


def test_extra_vars_from_wizard_non_tty_returns_defaults() -> None:
    defaults = {
        "tools_gateway_enabled": False,
        "tools_observability_enabled": False,
        "tools_service_mesh_enabled": False,
        "tools_infrastructure_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.tools._load_role_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.tools.sys.stdin") as mock_stdin,
        patch("questionary.confirm") as mock_confirm,
    ):
        mock_stdin.isatty.return_value = False

        result = _extra_vars_from_wizard()

    mock_confirm.assert_not_called()
    assert result == defaults


# ---------------------------------------------------------------------------
# deploy_tools command
# ---------------------------------------------------------------------------

def test_deploy_tools_success_no_scenario(tmp_path: Path) -> None:
    """Without --scenario and non-TTY stdin, wizard skips prompts and uses role defaults."""
    runner = CliRunner()
    defaults = {
        "tools_gateway_enabled": False,
        "tools_observability_enabled": False,
        "tools_service_mesh_enabled": False,
        "tools_infrastructure_enabled": False,
    }

    with (
        patch("itbench.cli.commands.deploy.tools._load_role_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.tools.run_playbook") as mock_run,
    ):
        mock_run.return_value = MagicMock()
        result = runner.invoke(deploy_tools, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "deployed successfully" in result.output
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "manage_tools.yaml"
    assert "install" in kwargs["tags"]


def test_deploy_tools_with_scenario_id(tmp_path: Path) -> None:
    runner = CliRunner()
    scenario_dir = tmp_path / "library" / "scenarios" / "5"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")
    ev = {"tools_gateway_enabled": True, "tools_observability_enabled": True}
    (scenario_dir / "extra_variables.yaml").write_text(yaml.dump(ev), encoding="utf-8")

    with (
        patch("itbench.cli.commands.deploy.tools._LIBRARY_ROOT", tmp_path / "library"),
        patch("itbench.cli.commands.deploy.tools.run_playbook") as mock_run,
    ):
        mock_run.return_value = MagicMock()
        result = runner.invoke(deploy_tools, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    _, kwargs = mock_run.call_args
    assert kwargs["extra_vars"]["tools_gateway_enabled"] is True
    assert kwargs["extra_vars"]["tools_observability_enabled"] is True


def test_deploy_tools_missing_scenario(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.deploy.tools._LIBRARY_ROOT", tmp_path / "library"):
        result = runner.invoke(
            deploy_tools,
            ["--scenario", "999", "--kubeconfig", "/kube.conf"],
        )

    assert result.exit_code == 1
    assert "not found" in result.output


def test_deploy_tools_playbook_failure(tmp_path: Path) -> None:
    runner = CliRunner()
    defaults = {k: False for k in [
        "tools_gateway_enabled", "tools_observability_enabled",
        "tools_service_mesh_enabled", "tools_infrastructure_enabled",
    ]}

    with (
        patch("itbench.cli.commands.deploy.tools._load_role_defaults", return_value=defaults),
        patch("itbench.cli.commands.deploy.tools.run_playbook", side_effect=RuntimeError("bad")),
    ):
        result = runner.invoke(deploy_tools, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Deploy failed" in result.output
