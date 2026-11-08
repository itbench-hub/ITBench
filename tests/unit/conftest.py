"""Shared fixtures for unit tests."""

import io

import pytest

from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG


class _TerminalInput(io.BytesIO):
    """An empty input stream that reports itself as an interactive terminal."""

    def isatty(self) -> bool:
        return True


@pytest.fixture(scope="session", autouse=True)
def _preload_catalogs() -> None:
    """Load the lazy catalogs from the real library before any test overrides ITBENCH_LIBRARY_PATH.

    The catalogs are cached on first access, so a test that points ITBENCH_LIBRARY_PATH at a temporary
    directory must not be the first to touch them.
    """
    len(FAULT_CATALOG)
    len(APPLICATION_CATALOG)


@pytest.fixture
def terminal_input() -> io.BytesIO:
    """Pass as ``CliRunner.invoke(..., input=terminal_input)`` to make ``sys.stdin.isatty()`` true.

    ``CliRunner`` replaces ``sys.stdin`` while a command runs, so patching ``sys.stdin`` beforehand has no effect.
    Its replacement delegates ``isatty()`` to the input stream, which is what this fixture overrides.
    """
    return _TerminalInput()
