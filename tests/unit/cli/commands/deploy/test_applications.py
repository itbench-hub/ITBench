"""Tests for the deploy applications CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

import pytest

from click.testing import CliRunner

from itbench.cli.commands.deploy.applications import (
    _extra_vars_from_scenario,
    _extra_vars_from_wizard,
    deploy_applications,
)


def test_extra_vars_from_scenario_uses_extra_vars_file(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()
    extra_vars_path = scenario_dir / "extra_vars.yaml"
    extra_vars_path.write_text("my_var: true\n", encoding="utf-8")
    (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")

    result = _extra_vars_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {"my_var": True}


def test_extra_vars_from_scenario_derives_flags_from_scenario(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()
    scenario = {
        "environment": {
            "applications": [
                {"id": "opentelemetry-demo", "enabled": True},
                {"id": "book-info", "enabled": False},
            ]
        }
    }
    (scenario_dir / "scenario.yaml").write_text(
        yaml.dump(scenario), encoding="utf-8"
    )

    result = _extra_vars_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {"applications_opentelemetry_demo_enabled": True}


def test_extra_vars_from_scenario_empty_environment(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "1"
    scenario_dir.mkdir()
    (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")

    result = _extra_vars_from_scenario(scenario_dir / "scenario.yaml")

    assert result == {}


def test_extra_vars_from_wizard_builds_vars() -> None:
    defaults = {
        "applications_book_info_enabled": False,
        "applications_book_info_kubernetes_autoscaling_enabled": False,
        "applications_opentelemetry_demo_enabled": False,
        "applications_opentelemetry_demo_kubernetes_autoscaling_enabled": False,
        "applications_opentelemetry_demo_load_generator_browser_enabled": False,
        "applications_opentelemetry_demo_load_generator_users": 50,
        "applications_opentelemetry_demo_load_generator_spawn_rate": 5,
    }

    with (
        patch("itbench.cli.commands.deploy.applications._load_role_defaults", return_value=defaults),
        patch("questionary.confirm") as mock_confirm,
        patch("questionary.text") as mock_text,
    ):
        mock_confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=False)),  # book-info disabled
            MagicMock(ask=MagicMock(return_value=True)),   # otel enabled
            MagicMock(ask=MagicMock(return_value=False)),  # otel autoscaling
            MagicMock(ask=MagicMock(return_value=False)),  # browser traffic
        ]
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="10")),  # users
            MagicMock(ask=MagicMock(return_value="2")),   # spawn rate
        ]

        result = _extra_vars_from_wizard()

    assert result["applications_book_info_enabled"] is False
    assert result["applications_opentelemetry_demo_enabled"] is True
    assert result["applications_opentelemetry_demo_load_generator_users"] == 10
    assert result["applications_opentelemetry_demo_load_generator_spawn_rate"] == 2


def test_deploy_applications_missing_scenario(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.deploy.applications._LIBRARY_ROOT", tmp_path / "library"):
        result = runner.invoke(
            deploy_applications,
            ["--scenario", "999", "--kubeconfig", str(tmp_path / "kube.conf")],
        )

    assert result.exit_code == 1
    assert "not found" in result.output


def test_deploy_applications_with_scenario_success(tmp_path: Path) -> None:
    runner = CliRunner()
    scenario_dir = tmp_path / "library" / "scenarios" / "1"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")

    with (
        patch("itbench.cli.commands.deploy.applications._LIBRARY_ROOT", tmp_path / "library"),
        patch("itbench.cli.commands.deploy.applications._extra_vars_from_scenario", return_value={}),
        patch("itbench.cli.commands.deploy.applications.run_playbook") as mock_run,
    ):
        mock_run.return_value = MagicMock()

        result = runner.invoke(
            deploy_applications,
            ["--scenario", "1", "--kubeconfig", "/kube.conf"],
            catch_exceptions=False,
        )

    assert result.exit_code == 0
    assert "deployed successfully" in result.output


def test_deploy_applications_playbook_failure(tmp_path: Path) -> None:
    runner = CliRunner()
    scenario_dir = tmp_path / "library" / "scenarios" / "1"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.yaml").write_text("{}", encoding="utf-8")

    with (
        patch("itbench.cli.commands.deploy.applications._LIBRARY_ROOT", tmp_path / "library"),
        patch("itbench.cli.commands.deploy.applications._extra_vars_from_scenario", return_value={}),
        patch("itbench.cli.commands.deploy.applications.run_playbook", side_effect=RuntimeError("boom")),
    ):
        result = runner.invoke(deploy_applications, ["--scenario", "1", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Deploy failed" in result.output
