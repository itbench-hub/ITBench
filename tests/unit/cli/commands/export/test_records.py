"""Tests for the export records CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from itbench.cli.commands.export.records import export_records
from itbench.utils.runner import PlaybookError


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ``.itbench/runs`` artifacts written by the command out of the working tree."""
    monkeypatch.chdir(tmp_path)


def test_export_records_success() -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()
        result = CliRunner().invoke(export_records, ["--kubeconfig", "/kube.conf", "-v"])

    assert result.exit_code == 0
    assert "Records exported successfully" in result.output
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["playbook"] == "manage_environment.yaml"
    assert kwargs["tags"] == ["export"]
    assert kwargs["extra_vars"] == {
        "environment_tool_management_enabled": False,
        "environment_application_management_enabled": False,
        "environment_recorder_management_enabled": True,
    }
    assert kwargs["kubeconfig"] == "/kube.conf"
    assert kwargs["verbose"] is True


def test_export_records_does_not_record_credentials(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ITBENCH_S3_PASSWORD", "super-secret")  # pragma: allowlist secret

    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()
        result = CliRunner().invoke(export_records, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    written = "".join(path.read_text(encoding="utf-8") for path in tmp_path.rglob("extra_vars.json"))
    assert "super-secret" not in written
    assert "super-secret" not in result.output


def test_export_records_playbook_failure(tmp_path: Path) -> None:
    error = PlaybookError("manage_environment.yaml", 2, tmp_path)

    with patch("itbench.cli.playbook.run_playbook", side_effect=error):
        result = CliRunner().invoke(export_records, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Record export failed" in result.output
