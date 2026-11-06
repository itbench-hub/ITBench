"""Tests for the remove faults CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from itbench.cli.commands.remove.faults import remove_faults
from itbench.utils.runner import PlaybookError


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ``.itbench/runs`` artifacts written by the command out of the working tree."""
    monkeypatch.chdir(tmp_path)


def test_remove_faults_success() -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()
        result = CliRunner().invoke(remove_faults, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Faults removed successfully" in result.output
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["playbook"] == "manage_faults.yaml"
    assert kwargs["tags"] == ["remove_faults"]
    assert kwargs["kubeconfig"] == "/kube.conf"
    assert kwargs["verbose"] is False


def test_remove_faults_playbook_failure(tmp_path: Path) -> None:
    error = PlaybookError("manage_faults.yaml", 2, tmp_path)

    with patch("itbench.cli.playbook.run_playbook", side_effect=error):
        result = CliRunner().invoke(remove_faults, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Fault removal failed" in result.output
