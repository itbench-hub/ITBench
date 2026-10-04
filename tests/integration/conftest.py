"""Shared fixtures and markers for ITBench integration tests.

Integration tests are marked with ``@pytest.mark.integration`` and require a
live Kind cluster with the full ITBench tools stack deployed.  They are
**skipped** by default when ``--integration`` is not passed to pytest so that
the normal unit-test run stays fast and cluster-free.

Prerequisites (handled by the CI workflow or the developer):
- A reachable kubeconfig path supplied via the ``KUBECONFIG`` env var.
- The tools stack already deployed (``itbench deploy tools``).

Fixtures:
  kubeconfig  -- path string from ``KUBECONFIG``; skips entire test if unset.
  itbench_cli -- pre-configured :class:`click.testing.CliRunner` instance.
"""

import os

import pytest

from click.testing import CliRunner


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (require a live Kind cluster)",
    )


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """Skip integration tests unless --integration flag is passed."""
    if config.getoption("--integration", default=False):
        return
    skip_marker = pytest.mark.skip(reason="pass --integration to run integration tests")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_marker)


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--integration",
        action="store_true",
        default=False,
        help="Run integration tests against a live Kind cluster.",
    )


@pytest.fixture(scope="session")
def kubeconfig() -> str:
    """Return the kubeconfig path from the environment, skipping if absent."""
    path = os.environ.get("KUBECONFIG")
    if not path:
        pytest.skip("KUBECONFIG environment variable is not set")
    return path


@pytest.fixture
def itbench_cli() -> CliRunner:
    """Return a Click test runner for integration tests."""
    return CliRunner()
