"""Fixtures for Kind-cluster integration tests.

A single session-scoped ``tools_stack`` fixture deploys the observability and
tooling stack once before any test in this directory runs, then tears it down
in a finalizer — regardless of whether tests pass or fail.  Individual tests
never call deploy/undeploy themselves; they just declare ``tools_stack`` as a
dependency.
"""

from collections.abc import Generator

import pytest
from click.testing import CliRunner

from itbench.cli.commands.deploy.tools import deploy_tools
from itbench.cli.commands.undeploy.tools import undeploy_tools


@pytest.fixture(scope="session")
def tools_stack(kubeconfig: str) -> Generator[None, None, None]:
    """Deploy the tools stack once for the session; undeploy on teardown."""
    runner = CliRunner()

    result = runner.invoke(deploy_tools, ["--kubeconfig", kubeconfig], catch_exceptions=False)
    assert result.exit_code == 0, f"tools deploy failed:\n{result.output}"

    yield

    result = runner.invoke(undeploy_tools, ["--kubeconfig", kubeconfig])
    assert result.exit_code == 0, f"tools undeploy failed:\n{result.output}"
