"""Tests for the shared playbook step runner."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from itbench.cli.playbook import run_step
from itbench.utils.runner import PlaybookError


def _run(verbose: bool = False) -> None:
    run_step(
        playbook="my.yaml",
        extra_vars={"k": "v"},
        tags=["install"],
        status="Working…",
        failure="My step",
        verbose=verbose,
        run_id="abc",
    )


def test_run_step_passes_arguments_to_the_runner() -> None:
    with patch("itbench.cli.playbook.run_playbook", return_value=MagicMock()) as mock_run:
        _run(verbose=True)

    mock_run.assert_called_once_with(
        playbook="my.yaml", extra_vars={"k": "v"}, tags=["install"], run_id="abc", verbose=True
    )


def test_run_step_shows_spinner_unless_verbose() -> None:
    with (
        patch("itbench.cli.playbook.run_playbook", return_value=MagicMock()),
        patch("itbench.cli.playbook.console") as mock_console,
    ):
        _run(verbose=False)

    mock_console.status.assert_called_once_with("Working…")
    mock_console.print.assert_not_called()


def test_run_step_replaces_spinner_with_a_plain_line_when_verbose() -> None:
    with (
        patch("itbench.cli.playbook.run_playbook", return_value=MagicMock()),
        patch("itbench.cli.playbook.console") as mock_console,
    ):
        _run(verbose=True)

    mock_console.status.assert_not_called()
    mock_console.print.assert_called_once()


def test_run_step_prints_captured_output_and_exits_on_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    error = PlaybookError("my.yaml", 2, tmp_path, output="TASK [boom] [not markup]")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error), pytest.raises(SystemExit) as excinfo:
        _run()

    assert excinfo.value.code == 1
    stderr = capsys.readouterr().err
    assert "TASK [boom] [not markup]" in stderr
    assert "My step failed" in stderr


def test_run_step_does_not_repeat_streamed_output_on_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    error = PlaybookError("my.yaml", 2, tmp_path, output="")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error), pytest.raises(SystemExit):
        _run(verbose=True)

    assert "My step failed" in capsys.readouterr().err
