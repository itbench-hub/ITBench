"""Filesystem locations used by ITBench.

The ``library/`` directory (faults, applications, scenarios) lives at the root of the
repository rather than inside the Python package. All lookups go through the shared
:data:`library` object so the location is resolved in exactly one place.
"""

import os

from pathlib import Path

LIBRARY_ENV_VAR = "ITBENCH_LIBRARY"

_SOURCE_LIBRARY = Path(__file__).parents[2] / "library"


class ITBenchLibrary:
    """Locations of the faults, applications and scenarios that make up the library.

    The root is resolved on every access, in this order:

    1. The explicit *root* passed to the constructor.
    2. The ``ITBENCH_LIBRARY`` environment variable.
    3. The ``library/`` directory next to ``src/`` in a source checkout.
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        """Root of the library."""
        if self._root is not None:
            return self._root
        override = os.environ.get(LIBRARY_ENV_VAR)
        if override:
            return Path(override).expanduser().resolve()
        return _SOURCE_LIBRARY

    @property
    def faults(self) -> Path:
        """Directory containing fault definitions."""
        return self.root / "faults"

    @property
    def applications(self) -> Path:
        """Directory containing application definitions."""
        return self.root / "applications"

    @property
    def scenarios(self) -> Path:
        """Directory containing numbered scenario directories."""
        return self.root / "scenarios"


library = ITBenchLibrary()
