"""Tests for the interactive create scenario CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.create.scenario import (
    _ask_target,
    _get_next_index,
    create_scenario_command,
)
from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.kubernetes import KubernetesWorkload


def test_get_next_index_scenario(tmp_path: Path) -> None:
    scenarios_dir = tmp_path / "scenarios"
    assert _get_next_index(scenarios_dir) == 1

    scenarios_dir.mkdir(parents=True)
    (scenarios_dir / "1").mkdir()
    (scenarios_dir / "3").mkdir()
    (scenarios_dir / "non-digit").mkdir()

    assert _get_next_index(scenarios_dir) == 4


def test_ask_target_returns_fault_target() -> None:
    first_fault_id = next(iter(FAULT_CATALOG.keys()))
    fault = FAULT_CATALOG[first_fault_id]

    if not fault.targets:
        target = _ask_target(first_fault_id)
        assert target is None
    else:
        with (
            patch("questionary.select") as mock_select,
            patch("questionary.text") as mock_text,
        ):
            mock_select.return_value.ask.return_value = "Deployment"
            mock_text.side_effect = [
                MagicMock(ask=MagicMock(return_value="target-service")),
                MagicMock(ask=MagicMock(return_value="default")),
            ]
            target = _ask_target(first_fault_id)
            assert target is not None
            assert isinstance(target.kubernetes, KubernetesWorkload)
            assert target.kubernetes.name == "target-service"
            assert target.kubernetes.namespace == "default"


def test_create_scenario_command_abort_no_apps(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("questionary.checkbox") as mock_checkbox:
        mock_checkbox.return_value.ask.return_value = []

        result = runner.invoke(
            create_scenario_command,
            ["--scenarios-dir", str(tmp_path / "scenarios")],
        )

        assert result.exit_code == 0
        assert "At least one application is required" in result.output


def test_create_scenario_command_success(tmp_path: Path) -> None:
    runner = CliRunner()
    scenarios_dir = tmp_path / "scenarios"
    first_app_id = next(iter(APPLICATION_CATALOG.keys()))
    first_fault_id = next(iter(FAULT_CATALOG.keys()))

    with (
        patch("questionary.checkbox") as mock_checkbox,
        patch("questionary.select") as mock_select,
        patch("questionary.autocomplete") as mock_autocomplete,
        patch("questionary.confirm") as mock_confirm,
        patch("questionary.text") as mock_text,
        patch("itbench.cli.commands.create.scenario.generate_ground_truth") as mock_gt,
    ):
        mock_checkbox.return_value.ask.return_value = [first_app_id]
        mock_select.side_effect = [
            MagicMock(ask=MagicMock(return_value="sre")),  # tools domain
            MagicMock(ask=MagicMock(return_value="Deployment")),  # target kind
        ]
        mock_autocomplete.side_effect = [
            MagicMock(ask=MagicMock(return_value=first_fault_id)),  # fault injection 1
        ]
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="app-deployment")),  # target name
            MagicMock(ask=MagicMock(return_value="default")),  # target namespace
            MagicMock(ask=MagicMock(return_value="replicas")),  # extra var key
            MagicMock(ask=MagicMock(return_value="3")),  # extra var value
        ]
        mock_confirm.side_effect = [
            MagicMock(ask=MagicMock(return_value=False)),  # no extra target for this injection
            MagicMock(ask=MagicMock(return_value=False)),  # no extra injection in block
            MagicMock(ask=MagicMock(return_value=False)),  # no extra fault blocks
            MagicMock(ask=MagicMock(return_value=True)),  # add extra_vars
            MagicMock(ask=MagicMock(return_value=False)),  # no extra variable
        ]
        mock_gt.return_value = scenarios_dir / "1" / "ground_truth.yaml"

        result = runner.invoke(
            create_scenario_command,
            ["--scenarios-dir", str(scenarios_dir)],
        )

        assert result.exit_code == 0
        assert "Created scenario →" in result.output

        created_scenario = scenarios_dir / "1" / "scenario.yaml"
        assert created_scenario.exists()
        data = yaml.safe_load(created_scenario.read_text(encoding="utf-8"))
        assert len(data["environment"]["applications"]) == 1
        assert data["environment"]["applications"][0]["id"] == first_app_id
        assert "sre" in data["environment"]["domains"]
        assert len(data["faults"]) == 1

        extra_vars_file = scenarios_dir / "1" / "extra_vars.yaml"
        assert extra_vars_file.exists()
        ev_data = yaml.safe_load(extra_vars_file.read_text(encoding="utf-8"))
        assert ev_data["replicas"] == 3
