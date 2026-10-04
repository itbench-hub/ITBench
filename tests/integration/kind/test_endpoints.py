"""Integration tests for ``itbench discover endpoints``.

Requires a live Kind cluster with the tools stack deployed.  The
``tools_stack`` session fixture (``kind/conftest.py``) handles that.
"""

import pytest

from click.testing import CliRunner

from itbench.cli.commands.discover.endpoints import endpoints


@pytest.mark.integration
def test_discover_endpoints_finds_all_tools(
    kubeconfig: str, itbench_cli: CliRunner, tools_stack: None
) -> None:
    """All five tool endpoints should resolve after the tools stack is deployed."""
    result = itbench_cli.invoke(
        endpoints,
        ["--kubeconfig", kubeconfig, "--platform", "kubernetes"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    for tool in ("Prometheus", "Jaeger", "ClickHouse", "OpenCost", "Kubernetes Topology Monitor"):
        assert tool in result.output, f"Expected '{tool}' in endpoint output"


@pytest.mark.integration
def test_discover_endpoints_surfaces_expected_paths(
    kubeconfig: str, itbench_cli: CliRunner, tools_stack: None
) -> None:
    """Key URL paths (/alerts, /healthz) must appear in the resolved table."""
    result = itbench_cli.invoke(
        endpoints,
        ["--kubeconfig", kubeconfig, "--platform", "kubernetes"],
        catch_exceptions=False,
    )
    assert result.exit_code == 0, result.output
    assert "/alerts" in result.output
    assert "/healthz" in result.output


@pytest.mark.integration
def test_discover_endpoints_bad_kubeconfig_exits_nonzero(
    itbench_cli: CliRunner, tools_stack: None
) -> None:
    """A kubeconfig pointing at a non-existent file should fail gracefully."""
    result = itbench_cli.invoke(
        endpoints,
        ["--kubeconfig", "/tmp/does-not-exist.yaml", "--platform", "kubernetes"],
    )
    assert result.exit_code == 1
