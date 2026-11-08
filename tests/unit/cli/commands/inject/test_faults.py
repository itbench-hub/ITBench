"""Tests for the inject faults CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.inject.faults import inject_faults
from itbench.paths import ITBenchRepository
from itbench.utils.runner import PlaybookError


def _write_scenario(root: Path, scenario_id: int, fault_groups: int) -> ITBenchRepository:
    scenario_dir = root / "library" / "scenarios" / str(scenario_id)
    scenario_dir.mkdir(parents=True)
    faults = [
        {
            "injections": [{"id": f"fault-{i}", "args": {}}],
            "waitFor": {
                "preInjection": [{"id": f"pre-{i}", "args": {}}],
                "postInjection": [{"id": f"post-{i}", "args": {}}],
            },
        }
        for i in range(fault_groups)
    ]
    (scenario_dir / "scenario.yaml").write_text(yaml.dump({"faults": faults}), encoding="utf-8")
    return ITBenchRepository(root)


def test_inject_faults_injects_every_group(tmp_path: Path) -> None:
    repo = _write_scenario(tmp_path, 5, fault_groups=2)

    with (
        patch("itbench.cli.commands.inject.faults.repository", repo),
        patch("itbench.cli.commands.inject.faults.run_playbook") as mock_run,
    ):
        mock_run.return_value = MagicMock()
        result = CliRunner().invoke(inject_faults, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Faults injected successfully" in result.output
    assert mock_run.call_count == 2
    extra_vars = sorted(
        (c.kwargs["extra_vars"] for c in mock_run.call_args_list),
        key=lambda ev: ev["injection_tasks"][0]["id"],
    )
    assert extra_vars == [
        {
            "injection_tasks": [{"id": f"fault-{i}", "args": {}}],
            "pre_injection_tasks": [{"id": f"pre-{i}", "args": {}}],
            "post_injection_tasks": [{"id": f"post-{i}", "args": {}}],
        }
        for i in range(2)
    ]
    for call_ in mock_run.call_args_list:
        assert call_.kwargs["playbook"] == "manage_faults.yaml"
        assert call_.kwargs["tags"] == ["inject_faults"]
        assert call_.kwargs["kubeconfig"] == "/kube.conf"


def test_inject_faults_defaults_missing_wait_for(tmp_path: Path) -> None:
    scenario_dir = tmp_path / "library" / "scenarios" / "5"
    scenario_dir.mkdir(parents=True)
    (scenario_dir / "scenario.yaml").write_text(yaml.dump({"faults": [{}]}), encoding="utf-8")
    repo = ITBenchRepository(tmp_path)

    with (
        patch("itbench.cli.commands.inject.faults.repository", repo),
        patch("itbench.cli.commands.inject.faults.run_playbook") as mock_run,
    ):
        mock_run.return_value = MagicMock()
        result = CliRunner().invoke(inject_faults, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert mock_run.call_args.kwargs["extra_vars"] == {
        "injection_tasks": [],
        "pre_injection_tasks": [],
        "post_injection_tasks": [],
    }


def test_inject_faults_reports_failed_group(tmp_path: Path) -> None:
    repo = _write_scenario(tmp_path, 5, fault_groups=2)
    error = PlaybookError("manage_faults.yaml", 2, tmp_path)

    def run(**kwargs: object) -> MagicMock:
        if kwargs["extra_vars"]["injection_tasks"][0]["id"] == "fault-1":  # type: ignore[index]
            raise error
        return MagicMock()

    with (
        patch("itbench.cli.commands.inject.faults.repository", repo),
        patch("itbench.cli.commands.inject.faults.run_playbook", side_effect=run),
    ):
        result = CliRunner().invoke(inject_faults, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Fault group 1 failed" in result.output
    assert "Fault group 0 failed" not in result.output


def test_inject_faults_unknown_scenario(tmp_path: Path) -> None:
    repo = _write_scenario(tmp_path, 5, fault_groups=1)

    with (
        patch("itbench.cli.commands.inject.faults.repository", repo),
        patch("itbench.cli.commands.inject.faults.run_playbook") as mock_run,
    ):
        result = CliRunner().invoke(inject_faults, ["--scenario", "99", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "not found" in result.output
    mock_run.assert_not_called()


def test_inject_faults_scenario_without_faults(tmp_path: Path) -> None:
    repo = _write_scenario(tmp_path, 5, fault_groups=0)

    with (
        patch("itbench.cli.commands.inject.faults.repository", repo),
        patch("itbench.cli.commands.inject.faults.run_playbook") as mock_run,
    ):
        result = CliRunner().invoke(inject_faults, ["--scenario", "5", "--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "does not define any faults" in result.output
    mock_run.assert_not_called()


@pytest.mark.parametrize("args", [["--kubeconfig", "/kube.conf"], ["--scenario", "5"]])
def test_inject_faults_requires_scenario_and_kubeconfig(args: list[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KUBECONFIG", raising=False)

    result = CliRunner().invoke(inject_faults, args)

    assert result.exit_code == 2
