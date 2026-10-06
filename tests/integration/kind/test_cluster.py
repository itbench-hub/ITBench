"""Integration tests for ``itbench prepare cluster``."""

import pytest

from click.testing import CliRunner
from kubernetes import client, config

from itbench.cli.commands.prepare.cluster import prepare_cluster_command
from itbench.utils.cluster import SANDBOX_NODE_LABEL, WORKER_NODE_LABEL_SELECTOR


@pytest.mark.integration
def test_prepare_cluster_partitions_worker_nodes(
    kubeconfig: str, itbench_cli: CliRunner
) -> None:
    """prepare cluster should succeed and correctly label worker nodes."""
    result = itbench_cli.invoke(
        prepare_cluster_command,
        ["--kubeconfig", kubeconfig],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Cluster prepared successfully" in result.output

    # Verify actual node labels on the live cluster
    config.load_kube_config(config_file=kubeconfig)
    core_api = client.CoreV1Api()
    workers = core_api.list_node(label_selector=WORKER_NODE_LABEL_SELECTOR).items

    node_count = len(workers)
    assert node_count >= 2, "Test cluster should have at least 2 worker nodes"

    non_sandbox_node_count = min(2, node_count // 2)
    sandbox_node_count = node_count - non_sandbox_node_count

    sandbox_workers = workers[:sandbox_node_count]
    tool_workers = workers[sandbox_node_count:]

    for node in sandbox_workers:
        labels = node.metadata.labels or {}
        assert labels.get(SANDBOX_NODE_LABEL) == "true", (
            f"Sandbox node '{node.metadata.name}' should have sandbox label"
        )

    for node in tool_workers:
        labels = node.metadata.labels or {}
        assert SANDBOX_NODE_LABEL not in labels, (
            f"Tool node '{node.metadata.name}' should not have sandbox label"
        )


@pytest.mark.integration
def test_prepare_cluster_is_idempotent(
    kubeconfig: str, itbench_cli: CliRunner
) -> None:
    """Running prepare cluster repeatedly should succeed without errors."""
    result = itbench_cli.invoke(
        prepare_cluster_command,
        ["--kubeconfig", kubeconfig],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "Cluster prepared successfully" in result.output
