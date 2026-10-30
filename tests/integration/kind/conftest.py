"""Fixtures for Kind-cluster integration tests.

A single session-scoped ``tools_stack`` fixture deploys the observability and
tooling stack once before any test in this directory runs, then tears it down
in a finalizer — regardless of whether tests pass or fail.  Individual tests
never call deploy/undeploy themselves; they just declare ``tools_stack`` as a
dependency.
"""

import subprocess
from collections.abc import Generator

import pytest


@pytest.fixture(scope="session")
def tools_stack(kubeconfig: str) -> Generator[None, None, None]:
    """Deploy the tools stack once for the session; undeploy on teardown."""
    result = subprocess.run(
        ["uv", "run", "itbench", "deploy", "tools", "--scenario", "20", "--kubeconfig", kubeconfig],
        check=False,
    )
    assert result.returncode == 0, "tools deploy failed"

    yield

    subprocess.run(
        ["uv", "run", "itbench", "undeploy", "tools", "--kubeconfig", kubeconfig],
        check=False,
    )
