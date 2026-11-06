"""Filesystem locations used by ITBench.

The ``library/`` directory (faults, applications, scenarios) and the Ansible project under ``scenarios/``
live at the root of the repository rather than inside the Python package. All lookups go through the
shared :data:`repository` object so each location is resolved in exactly one place.
"""

import os

from pathlib import Path

REPOSITORY_PATH_ENV_VAR = "ITBENCH_REPOSITORY_PATH"
LIBRARY_PATH_ENV_VAR = "ITBENCH_LIBRARY_PATH"

_SOURCE_REPOSITORY = Path(__file__).parents[2]


class ITBenchRepository:
    """Locations of the repository-level files that the CLI reads and writes.

    The repository root is resolved on every access, in this order:

    1. The explicit *root* passed to the constructor.
    2. The ``ITBENCH_REPOSITORY_PATH`` environment variable.
    3. The directory containing ``src/`` in a source checkout.

    The library normally lives in ``<root>/library``. ``ITBENCH_LIBRARY_PATH`` can point it elsewhere, for
    example at a library that was downloaded separately from the repository (such as by an init container).
    """

    def __init__(self, root: Path | None = None) -> None:
        self._root = root

    @property
    def root(self) -> Path:
        """Root of the repository."""
        if self._root is not None:
            return self._root
        override = os.environ.get(REPOSITORY_PATH_ENV_VAR)
        if override:
            return Path(override).expanduser().resolve()
        return _SOURCE_REPOSITORY

    @property
    def library(self) -> Path:
        """Root of the library: ``ITBENCH_LIBRARY_PATH`` if set, otherwise ``<root>/library``."""
        override = os.environ.get(LIBRARY_PATH_ENV_VAR)
        if override:
            return Path(override).expanduser().resolve()
        return self.root / "library"

    @property
    def faults(self) -> Path:
        """Directory containing fault definitions."""
        return self.library / "faults"

    @property
    def applications(self) -> Path:
        """Directory containing application definitions."""
        return self.library / "applications"

    @property
    def scenarios(self) -> Path:
        """Directory containing numbered scenario directories."""
        return self.library / "scenarios"

    @property
    def schemas(self) -> Path:
        """Directory that generated JSON schemas are written to."""
        return self.root / "schemas" / "json"

    @property
    def documentation(self) -> Path:
        """Directory that generated library documentation is written to."""
        return self.root / "documentation" / "library"

    @property
    def ansible_project(self) -> Path:
        """Ansible project containing the ``manage_*.yaml`` playbooks."""
        return self.root / "scenarios" / "sre" / "project"

    @property
    def group_vars(self) -> Path:
        """Ansible inventory ``group_vars`` directory."""
        return self.root / "scenarios" / "sre" / "inventory" / "group_vars"

    @property
    def tools_defaults(self) -> Path:
        """Default variables of the ``tools`` role."""
        return self.ansible_project / "roles" / "tools" / "defaults" / "main"

    @property
    def applications_defaults(self) -> Path:
        """Default variables of the ``applications`` role."""
        return self.ansible_project / "roles" / "applications" / "defaults" / "main"


repository = ITBenchRepository()
