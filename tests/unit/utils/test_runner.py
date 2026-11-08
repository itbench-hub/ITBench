"""Tests for itbench.utils.runner."""

import json

from pathlib import Path
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from ansible_runner.exceptions import AnsibleRunnerException

from itbench.paths import repository
from itbench.utils.runner import PlaybookError, create_run, run_directory, run_playbook


def _make_runner(rc: int = 0, output: str = "") -> MagicMock:
    runner = MagicMock()
    runner.rc = rc
    runner.stdout.read.return_value = output
    return runner


def test_playbooks_run_from_the_sre_project() -> None:
    with patch("ansible_runner.run", return_value=_make_runner()) as mock_run:
        run_playbook(playbook="my.yaml")

    assert mock_run.call_args.kwargs["private_data_dir"] == str(repository.ansible_project)
    assert repository.ansible_project.parts[-3:] == ("scenarios", "sre", "project")


def test_playbooks_use_the_sre_inventory_so_group_vars_apply() -> None:
    with patch("ansible_runner.run", return_value=_make_runner()) as mock_run:
        run_playbook(playbook="my.yaml")

    assert mock_run.call_args.kwargs["inventory"] == str(repository.inventory)
    assert repository.inventory.parts[-3:] == ("scenarios", "sre", "inventory")
    assert repository.group_vars == repository.inventory / "group_vars"


def test_run_playbook_passes_correct_args() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner) as mock_run:
        run_playbook(playbook="my.yaml", extra_vars={"k": "v"}, tags=["t1", "t2"], run_id="abc")

    _, kwargs = mock_run.call_args
    assert kwargs["playbook"] == "my.yaml"
    assert kwargs["extravars"] == {"k": "v"}
    assert kwargs["cmdline"] == "--tags t1,t2"
    assert kwargs["artifact_dir"].endswith("abc")


def test_run_playbook_passes_kubeconfig_as_envvars() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner) as mock_run:
        run_playbook(playbook="my.yaml", kubeconfig="/kube.conf")

    _, kwargs = mock_run.call_args
    assert "envvars" in kwargs
    assert kwargs["envvars"].get("K8S_AUTH_KUBECONFIG") == "/kube.conf"


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


def test_run_playbook_is_quiet_by_default() -> None:
    with patch("ansible_runner.run", return_value=_make_runner()) as mock_run:
        run_playbook(playbook="my.yaml")

    assert mock_run.call_args.kwargs["quiet"] is True


def test_run_playbook_streams_output_when_verbose() -> None:
    with patch("ansible_runner.run", return_value=_make_runner()) as mock_run:
        run_playbook(playbook="my.yaml", verbose=True)

    assert mock_run.call_args.kwargs["quiet"] is False


def test_run_playbook_raises_on_nonzero_rc() -> None:
    mock_runner = _make_runner(rc=2)

    with patch("ansible_runner.run", return_value=mock_runner):
        with pytest.raises(RuntimeError, match="my.yaml"):
            run_playbook(playbook="my.yaml")


def test_playbook_error_carries_captured_output() -> None:
    mock_runner = _make_runner(rc=2, output="TASK [boom] failed")

    with patch("ansible_runner.run", return_value=mock_runner):
        with pytest.raises(PlaybookError) as excinfo:
            run_playbook(playbook="my.yaml", run_id="abc")

    assert excinfo.value.rc == 2
    assert excinfo.value.playbook == "my.yaml"
    assert excinfo.value.output == "TASK [boom] failed"
    assert excinfo.value.artifact_dir == run_directory("abc")
    mock_runner.stdout.close.assert_called_once()


def test_playbook_error_output_is_empty_when_verbose() -> None:
    mock_runner = _make_runner(rc=2, output="already streamed")

    with patch("ansible_runner.run", return_value=mock_runner):
        with pytest.raises(PlaybookError) as excinfo:
            run_playbook(playbook="my.yaml", verbose=True)

    assert excinfo.value.output == ""


def test_playbook_error_output_is_empty_when_stdout_missing() -> None:
    mock_runner = _make_runner(rc=2)
    type(mock_runner).stdout = PropertyMock(side_effect=AnsibleRunnerException("stdout missing"))

    with patch("ansible_runner.run", return_value=mock_runner):
        with pytest.raises(PlaybookError) as excinfo:
            run_playbook(playbook="my.yaml")

    assert excinfo.value.output == ""


def test_run_playbook_returns_runner_on_success() -> None:
    mock_runner = _make_runner(rc=0)

    with patch("ansible_runner.run", return_value=mock_runner):
        result = run_playbook(playbook="my.yaml")

    assert result is mock_runner


def test_create_run_writes_extra_vars(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    run_id, extra_vars_file = create_run({"cluster": {"kubeconfig": "/kube.conf"}, "scenario_id": 5})

    assert extra_vars_file == tmp_path / ".itbench" / "runs" / run_id / "extra_vars.json"
    assert json.loads(extra_vars_file.read_text(encoding="utf-8")) == {
        "cluster": {"kubeconfig": "/kube.conf"},
        "scenario_id": 5,
    }
