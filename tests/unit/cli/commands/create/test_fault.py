"""Tests for the interactive create fault CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.create.fault import (
    _scaffold_ansible_task,
    create_fault_command,
)


def test_scaffold_ansible_task(tmp_path: Path) -> None:
    tasks_dir = tmp_path / "tasks"
    task_path = _scaffold_ansible_task(tasks_dir, "test-fault-id")

    assert task_path.exists()
    assert task_path.name == "inject_test_fault_id.yaml"
    content = task_path.read_text(encoding="utf-8")
    assert "test-fault-id" in content

    # Should not overwrite if already exists
    task_path.write_text("custom content", encoding="utf-8")
    _scaffold_ansible_task(tasks_dir, "test-fault-id")
    assert task_path.read_text(encoding="utf-8") == "custom content"


def test_create_fault_command_abort_on_empty_name(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))

    with (
        patch("itbench.cli.commands.create.fault.sys.stdin") as mock_stdin,
        patch("questionary.text") as mock_text,
    ):
        mock_stdin.isatty.return_value = True
        mock_text.return_value.ask.return_value = ""

        result = runner.invoke(create_fault_command, [])

        assert result.exit_code == 2
        assert "Fault name is required" in result.output


def test_create_fault_command_success(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))

    library_dir = tmp_path / "library" / "faults"

    with (
        patch("itbench.cli.commands.create.fault.sys.stdin") as mock_stdin,
        patch("questionary.text") as mock_text,
        patch("questionary.select") as mock_select,
        patch("questionary.checkbox") as mock_checkbox,
    ):
        mock_stdin.isatty.return_value = True
        mock_text.side_effect = [
            MagicMock(ask=MagicMock(return_value="Crash Pods")),  # name
            MagicMock(ask=MagicMock(return_value="Crashes all pods")),  # description
            MagicMock(ask=MagicMock(return_value="Pods in CrashLoop")),  # expectation
            MagicMock(ask=MagicMock(return_value="https://example.com/docs")),  # resources link 1
            MagicMock(ask=MagicMock(return_value="")),  # empty to finish resources
            MagicMock(ask=MagicMock(return_value="Check pod status")),  # solution step 1 description
            MagicMock(ask=MagicMock(return_value="kubectl get pods")),  # solution step 1 command
            MagicMock(ask=MagicMock(return_value="")),  # empty to finish solutions
        ]
        mock_select.return_value.ask.return_value = "Kubernetes"
        mock_checkbox.side_effect = [
            MagicMock(ask=MagicMock(return_value=["Deployment"])),  # tags
            MagicMock(ask=MagicMock(return_value=["KubePodCrashLooping"])),  # alerts
            MagicMock(ask=MagicMock(return_value=["Deployment"])),  # target kinds
        ]

        result = runner.invoke(create_fault_command, [])

        assert result.exit_code == 0
        assert "Created fault at" in result.output

        created_yaml = library_dir / "crash-pods.yaml"
        assert created_yaml.exists()
        data = yaml.safe_load(created_yaml.read_text(encoding="utf-8"))
        assert data["name"] == "Crash Pods"
        assert data["platform"] == "Kubernetes"
        assert data["tags"] == ["Deployment"]
        assert data["alerts"] == ["KubePodCrashLooping"]
        assert data["targets"] == [{"kubernetes": "KubernetesWorkload"}]
        assert len(data["solution_templates"]["templates"][0]["steps"]) == 1


def test_create_fault_command_non_tty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path))
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))

    with patch("itbench.cli.commands.create.fault.sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False
        result = runner.invoke(create_fault_command, [])
        assert result.exit_code == 1
        assert "Input is not interactive" in result.output
