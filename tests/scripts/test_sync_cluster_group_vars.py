"""
Tests for sync_cluster_group_vars.py

Makefile invocation:
  uv run python ../../scripts/sync_cluster_group_vars.py
    --kubeconfig <path>
    --cluster-group-variable <path>
"""
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

import sync_cluster_group_vars


# ---------------------------------------------------------------------------
# sync_cluster_group_vars
# ---------------------------------------------------------------------------

def test_writes_correct_yaml(tmp_path):
    """sync_cluster_group_vars() writes cluster.kubeconfig to the output file."""
    kubeconfig = tmp_path / "kubeconfigs" / "itbench-environment"
    kubeconfig.parent.mkdir()
    kubeconfig.touch()
    output = tmp_path / "group_vars" / "environment" / "cluster.yaml"

    sync_cluster_group_vars.sync_cluster_group_vars(kubeconfig, output)

    content = yaml.safe_load(output.read_text())
    assert content == {"cluster": {"kubeconfig": str(kubeconfig)}}


def test_creates_parent_directories(tmp_path):
    """sync_cluster_group_vars() creates missing parent directories."""
    kubeconfig = tmp_path / "kubeconfig"
    kubeconfig.touch()
    output = tmp_path / "a" / "b" / "c" / "cluster.yaml"

    sync_cluster_group_vars.sync_cluster_group_vars(kubeconfig, output)

    assert output.exists()


def test_output_has_explicit_start(tmp_path):
    """sync_cluster_group_vars() writes a YAML document with an explicit --- start."""
    kubeconfig = tmp_path / "kubeconfig"
    kubeconfig.touch()
    output = tmp_path / "cluster.yaml"

    sync_cluster_group_vars.sync_cluster_group_vars(kubeconfig, output)

    assert output.read_text().startswith("---")


def test_overwrites_existing_file(tmp_path):
    """sync_cluster_group_vars() overwrites an existing output file."""
    kubeconfig = tmp_path / "new-kubeconfig"
    kubeconfig.touch()
    output = tmp_path / "cluster.yaml"
    output.write_text("old content")

    sync_cluster_group_vars.sync_cluster_group_vars(kubeconfig, output)

    content = yaml.safe_load(output.read_text())
    assert content["cluster"]["kubeconfig"] == str(kubeconfig)


# ---------------------------------------------------------------------------
# main — argument parsing
# ---------------------------------------------------------------------------

def test_main_calls_sync_with_correct_args(tmp_path):
    """main() parses arguments and calls sync_cluster_group_vars with Path objects."""
    kubeconfig = tmp_path / "kubeconfig"
    output = tmp_path / "cluster.yaml"

    with patch("sys.argv", [
        "sync_cluster_group_vars.py",
        "--kubeconfig", str(kubeconfig),
        "--cluster-group-variable", str(output),
    ]), patch("sync_cluster_group_vars.sync_cluster_group_vars") as mock_sync:
        sync_cluster_group_vars.main()

    mock_sync.assert_called_once_with(Path(str(kubeconfig)), Path(str(output)))


def test_main_requires_kubeconfig():
    """main() exits when --kubeconfig is missing."""
    with patch("sys.argv", ["sync_cluster_group_vars.py",
                            "--cluster-group-variable", "/out/cluster.yaml"]), \
         pytest.raises(SystemExit) as exc:
        sync_cluster_group_vars.main()
    assert exc.value.code != 0


def test_main_requires_cluster_group_variable():
    """main() exits when --cluster-group-variable is missing."""
    with patch("sys.argv", ["sync_cluster_group_vars.py",
                            "--kubeconfig", "/kube/config"]), \
         pytest.raises(SystemExit) as exc:
        sync_cluster_group_vars.main()
    assert exc.value.code != 0
