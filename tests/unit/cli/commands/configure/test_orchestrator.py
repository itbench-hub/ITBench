"""Tests for the configure orchestrator CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from itbench.cli.commands.configure.orchestrator import configure_orchestrator_command
from itbench.utils.runner import PlaybookError


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ``.itbench/runs`` artifacts written by the command out of the working tree."""
    monkeypatch.chdir(tmp_path)


def test_configure_orchestrator_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(configure_orchestrator_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator configured successfully" in result.output
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["playbook"] == "manage_orchestrator.yaml"
    assert kwargs["tags"] == ["configure"]
    assert kwargs["extra_vars"] == {}
    assert kwargs["kubeconfig"] == "/kube.conf"
    assert kwargs["verbose"] is False


def test_configure_orchestrator_uses_kubeconfig_environment_variable() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(configure_orchestrator_command, [], env={"KUBECONFIG": "/env.conf"})

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["kubeconfig"] == "/env.conf"


def test_configure_orchestrator_requires_a_kubeconfig() -> None:
    result = CliRunner().invoke(configure_orchestrator_command, [], env={"KUBECONFIG": None})

    assert result.exit_code != 0


def test_configure_orchestrator_verbose_streams_ansible_output() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(configure_orchestrator_command, ["-v", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["verbose"] is True


def test_configure_orchestrator_playbook_failure_shows_ansible_output(tmp_path: Path) -> None:
    runner = CliRunner()
    error = PlaybookError("manage_orchestrator.yaml", 2, tmp_path, output="TASK [boom] fatal")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error):
        result = runner.invoke(configure_orchestrator_command, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Orchestrator configuration failed" in result.output
    assert "TASK [boom] fatal" in result.output
