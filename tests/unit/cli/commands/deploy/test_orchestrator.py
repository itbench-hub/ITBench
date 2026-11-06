"""Tests for the deploy orchestrator CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from itbench.cli.commands.deploy.orchestrator import deploy_orchestrator
from itbench.utils.runner import PlaybookError


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ``.itbench/runs`` artifacts written by the command out of the working tree."""
    monkeypatch.chdir(tmp_path)


def test_deploy_orchestrator_success() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Orchestrator deployed successfully" in result.output
    mock_run.assert_called_once()
    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "manage_orchestrator.yaml"
    assert kwargs["tags"] == ["install"]
    assert kwargs["extra_vars"] == {}
    assert kwargs["kubeconfig"] == "/kube.conf"
    assert kwargs["verbose"] is False


def test_deploy_orchestrator_writes_extra_vars_into_the_run_directory(tmp_path: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        runner.invoke(deploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    run_id = mock_run.call_args.kwargs["run_id"]
    assert (tmp_path / ".itbench" / "runs" / run_id / "extra_vars.json").is_file()


def test_deploy_orchestrator_verbose_streams_ansible_output() -> None:
    runner = CliRunner()

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = runner.invoke(deploy_orchestrator, ["-v", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["verbose"] is True


def test_deploy_orchestrator_playbook_failure_shows_ansible_output(tmp_path: Path) -> None:
    runner = CliRunner()
    error = PlaybookError("manage_orchestrator.yaml", 2, tmp_path, output="TASK [boom] fatal")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error):
        result = runner.invoke(deploy_orchestrator, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Orchestrator deploy failed" in result.output
    assert "TASK [boom] fatal" in result.output
