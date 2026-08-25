"""
Tests for sync_stack_group_vars.py

Makefile invocation:
  uv run python ../../scripts/sync_stack_group_vars.py
    --orchestrator-kubeconfig <path>
    --runner-kubeconfigs <path> [<path> ...]
    --stack-group-variable <path>
"""
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import sync_stack_group_vars


# ---------------------------------------------------------------------------
# sync_stack_group_vars
# ---------------------------------------------------------------------------

def test_writes_correct_yaml(tmp_path):
    """sync_stack_group_vars() writes stack.argo.kubeconfig and runner kubeconfigs."""
    orchestrator = tmp_path / "kubeconfigs" / "itbench-orchestrator"
    runner_one = tmp_path / "kubeconfigs" / "itbench-runner-1"
    runner_two = tmp_path / "kubeconfigs" / "itbench-runner-2"
    for p in (orchestrator, runner_one, runner_two):
        p.parent.mkdir(exist_ok=True)
        p.touch()
    output = tmp_path / "group_vars" / "runner" / "stack.yaml"

    sync_stack_group_vars.sync_stack_group_vars(orchestrator, [runner_one, runner_two], output)

    content = yaml.safe_load(output.read_text())
    assert content["stack"]["argo"]["kubeconfig"] == str(orchestrator)
    assert content["stack"]["runners"]["kubeconfigs"] == [str(runner_one), str(runner_two)]


def test_creates_parent_directories(tmp_path):
    """sync_stack_group_vars() creates missing parent directories."""
    orchestrator = tmp_path / "orchestrator"
    runner = tmp_path / "runner"
    orchestrator.touch()
    runner.touch()
    output = tmp_path / "a" / "b" / "c" / "stack.yaml"

    sync_stack_group_vars.sync_stack_group_vars(orchestrator, [runner], output)

    assert output.exists()


def test_output_has_explicit_start(tmp_path):
    """sync_stack_group_vars() writes a YAML document with an explicit --- start."""
    orchestrator = tmp_path / "orchestrator"
    runner = tmp_path / "runner"
    orchestrator.touch()
    runner.touch()
    output = tmp_path / "stack.yaml"

    sync_stack_group_vars.sync_stack_group_vars(orchestrator, [runner], output)

    assert output.read_text().startswith("---")


def test_single_runner(tmp_path):
    """sync_stack_group_vars() handles a single runner kubeconfig."""
    orchestrator = tmp_path / "orchestrator"
    runner = tmp_path / "runner"
    orchestrator.touch()
    runner.touch()
    output = tmp_path / "stack.yaml"

    sync_stack_group_vars.sync_stack_group_vars(orchestrator, [runner], output)

    content = yaml.safe_load(output.read_text())
    assert len(content["stack"]["runners"]["kubeconfigs"]) == 1


def test_overwrites_existing_file(tmp_path):
    """sync_stack_group_vars() overwrites an existing output file."""
    orchestrator = tmp_path / "new-orchestrator"
    runner = tmp_path / "new-runner"
    orchestrator.touch()
    runner.touch()
    output = tmp_path / "stack.yaml"
    output.write_text("old content")

    sync_stack_group_vars.sync_stack_group_vars(orchestrator, [runner], output)

    content = yaml.safe_load(output.read_text())
    assert content["stack"]["argo"]["kubeconfig"] == str(orchestrator)


# ---------------------------------------------------------------------------
# main — argument parsing
# ---------------------------------------------------------------------------

def test_main_calls_sync_with_correct_args(tmp_path):
    """main() parses arguments and calls sync_stack_group_vars with Path objects."""
    orchestrator = tmp_path / "orchestrator"
    runner_one = tmp_path / "runner-1"
    runner_two = tmp_path / "runner-2"
    output = tmp_path / "stack.yaml"

    with patch("sys.argv", [
        "sync_stack_group_vars.py",
        "--orchestrator-kubeconfig", str(orchestrator),
        "--runner-kubeconfigs", str(runner_one), str(runner_two),
        "--stack-group-variable", str(output),
    ]), patch("sync_stack_group_vars.sync_stack_group_vars") as mock_sync:
        sync_stack_group_vars.main()

    mock_sync.assert_called_once_with(
        Path(str(orchestrator)),
        [Path(str(runner_one)), Path(str(runner_two))],
        Path(str(output)),
    )


def test_main_requires_orchestrator_kubeconfig():
    """main() exits when --orchestrator-kubeconfig is missing."""
    with patch("sys.argv", [
        "sync_stack_group_vars.py",
        "--runner-kubeconfigs", "/runner",
        "--stack-group-variable", "/out/stack.yaml",
    ]), pytest.raises(SystemExit) as exc:
        sync_stack_group_vars.main()
    assert exc.value.code != 0


def test_main_requires_runner_kubeconfigs():
    """main() exits when --runner-kubeconfigs is missing."""
    with patch("sys.argv", [
        "sync_stack_group_vars.py",
        "--orchestrator-kubeconfig", "/orchestrator",
        "--stack-group-variable", "/out/stack.yaml",
    ]), pytest.raises(SystemExit) as exc:
        sync_stack_group_vars.main()
    assert exc.value.code != 0


def test_main_requires_stack_group_variable():
    """main() exits when --stack-group-variable is missing."""
    with patch("sys.argv", [
        "sync_stack_group_vars.py",
        "--orchestrator-kubeconfig", "/orchestrator",
        "--runner-kubeconfigs", "/runner",
    ]), pytest.raises(SystemExit) as exc:
        sync_stack_group_vars.main()
    assert exc.value.code != 0
