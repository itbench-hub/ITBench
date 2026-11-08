"""Tests for the schedule benchmark CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from click.testing import CliRunner

from itbench.cli.commands.schedule.benchmark import schedule_benchmark
from itbench.utils.runner import PlaybookError


@pytest.fixture(autouse=True)
def _run_in_tmp_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep the ``.itbench/runs`` artifacts written by the command out of the working tree."""
    monkeypatch.chdir(tmp_path)


@pytest.fixture(autouse=True)
def _known_scenarios():
    with patch("itbench.cli.commands.schedule.benchmark.known_scenario_ids", return_value=["1", "5"]):
        yield


def test_schedule_benchmark_success_with_defaults() -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = CliRunner().invoke(schedule_benchmark, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Scheduled 1 trial(s) of scenario 5" in result.output
    mock_run.assert_called_once()
    kwargs = mock_run.call_args.kwargs
    assert kwargs["playbook"] == "manage_orchestrator.yaml"
    assert kwargs["tags"] == ["schedule"]
    assert kwargs["extra_vars"] == {
        "argo_benchmark_scenario": "5",
        "argo_benchmark_trials": 1,
        "argo_benchmark_variant": "full",
    }
    assert kwargs["kubeconfig"] == "/kube.conf"
    assert kwargs["verbose"] is False


def test_schedule_benchmark_passes_trials_and_variant() -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = CliRunner().invoke(
            schedule_benchmark,
            ["--scenario", "1", "--trials", "3", "--variant", "setup", "--kubeconfig", "/kube.conf"],
        )

    assert result.exit_code == 0
    assert "Scheduled 3 trial(s) of scenario 1" in result.output
    extra_vars = mock_run.call_args.kwargs["extra_vars"]
    assert extra_vars["argo_benchmark_trials"] == 3
    assert extra_vars["argo_benchmark_variant"] == "setup"


def test_schedule_benchmark_writes_extra_vars_into_the_run_directory(tmp_path: Path) -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        CliRunner().invoke(schedule_benchmark, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    run_id = mock_run.call_args.kwargs["run_id"]
    assert (tmp_path / ".itbench" / "runs" / run_id / "extra_vars.json").is_file()


def test_schedule_benchmark_verbose_streams_ansible_output() -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        mock_run.return_value = MagicMock()

        result = CliRunner().invoke(schedule_benchmark, ["-v", "--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["verbose"] is True


def test_schedule_benchmark_rejects_unknown_scenario() -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        result = CliRunner().invoke(schedule_benchmark, ["--scenario", "99", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "not found" in result.output
    mock_run.assert_not_called()


@pytest.mark.parametrize("trials", ["0", "-1"])
def test_schedule_benchmark_rejects_non_positive_trials(trials: str) -> None:
    with patch("itbench.cli.playbook.run_playbook") as mock_run:
        result = CliRunner().invoke(
            schedule_benchmark, ["--scenario", "5", "--trials", trials, "--kubeconfig", "/kube.conf"]
        )

    assert result.exit_code != 0
    mock_run.assert_not_called()


def test_schedule_benchmark_rejects_unknown_variant() -> None:
    result = CliRunner().invoke(
        schedule_benchmark, ["--scenario", "5", "--variant", "Nope", "--kubeconfig", "/kube.conf"]
    )

    assert result.exit_code != 0


def test_schedule_benchmark_requires_a_scenario() -> None:
    result = CliRunner().invoke(schedule_benchmark, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code != 0


def test_schedule_benchmark_playbook_failure_shows_ansible_output(tmp_path: Path) -> None:
    error = PlaybookError("manage_orchestrator.yaml", 2, tmp_path, output="TASK [boom] fatal")

    with patch("itbench.cli.playbook.run_playbook", side_effect=error):
        result = CliRunner().invoke(schedule_benchmark, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Benchmark scheduling failed" in result.output
    assert "TASK [boom] fatal" in result.output
