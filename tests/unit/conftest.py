"""Shared fixtures for unit tests."""

import pytest

from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG


@pytest.fixture(scope="session", autouse=True)
def _preload_catalogs() -> None:
    """Load the lazy catalogs from the real library before any test overrides ITBENCH_LIBRARY_PATH.

    The catalogs are cached on first access, so a test that points ITBENCH_LIBRARY_PATH at a temporary
    directory must not be the first to touch them.
    """
    len(FAULT_CATALOG)
    len(APPLICATION_CATALOG)
