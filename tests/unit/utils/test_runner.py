"""Tests for itbench.utils.runner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from itbench.utils.runner import _PROJECT_DIR, run_playbook


def _make_runner(rc: int = 0) -> MagicMock:
    runner = MagicMock()
    runner.rc = rc
    return runner


def test_project_dir_points_at_sre_project() -> None:
    assert _PROJECT_DIR.parts[-3:] == ("scenarios", "sre", "project")


def test_run_playbook_passes_correct_args() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner) as mock_run:
        run_playbook(playbook="my.yaml", extra_vars={"k": "v"}, tags=["t1", "t2"], run_id="abc")

    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "my.yaml"
    assert kwargs["extravars"] == {"k": "v"}
    assert kwargs["cmdline"] == "--tags t1,t2"
    assert kwargs["artifact_dir"].endswith("abc")


def test_run_playbook_no_tags_passes_none_cmdline() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner) as mock_run:
        run_playbook(playbook="my.yaml")

    _, kwargs = mock_run.call_args
    assert kwargs["cmdline"] is None


def test_run_playbook_empty_extra_vars_defaults_to_dict() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner) as mock_run:
        run_playbook(playbook="my.yaml")

    _, kwargs = mock_run.call_args
    assert kwargs["extravars"] == {}


def test_run_playbook_generates_uuid_when_run_id_omitted() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner) as mock_run:
        run_playbook(playbook="my.yaml", run_id=None)

    _, kwargs = mock_run.call_args
    artifact_dir = Path(kwargs["artifact_dir"])
    # UUID segment is the last directory name
    run_id_segment = artifact_dir.name
    assert len(run_id_segment) == 36  # standard UUID string length


def test_run_playbook_raises_on_nonzero_rc() -> None:
    mock_runner = _make_runner(rc=2)

    with patch("ansible_runner.run", return_value=mock_runner):
        with pytest.raises(RuntimeError, match="my.yaml"):
            run_playbook(playbook="my.yaml")


def test_run_playbook_returns_runner_on_success() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner):
        result = run_playbook(playbook="my.yaml")

    assert result is mock_runner
