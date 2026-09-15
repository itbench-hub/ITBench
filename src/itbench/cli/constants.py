"""Repository-root discovery and well-known path constants for CLI modules."""
from dataclasses import dataclass
from pathlib import Path


def find_repo_root(explicit: Path | None = None) -> Path:
    """Return the ITBench repository root.

    If *explicit* is given it is returned as-is.  Otherwise the function walks
    upward from the current working directory until it finds a directory that
    contains ``pyproject.toml``, ``library/``, and ``scenarios/``.  Falls back
    to the current working directory when no such ancestor exists.
    """
    if explicit is not None:
        return explicit
    cur = Path.cwd()
    for parent in [cur] + list(cur.parents):
        if (
            (parent / "pyproject.toml").exists()
            and (parent / "library").exists()
            and (parent / "scenarios").exists()
        ):
            return parent
    return cur


@dataclass(frozen=True)
class RepoPaths:
    """Well-known paths derived from the repository root.

    Use :func:`resolve` to construct an instance from an optional explicit root.
    All paths are properties so they are computed lazily and never stale.
    """

    root: Path

    @property
    def playbooks_directory(self) -> Path:
        return self.root / "scenarios" / "sre" / "project"

    @property
    def specs_dir(self) -> Path:
        return self.root / "library" / "specs" / "scenarios"

    @property
    def library_index_directory(self) -> Path:
        return self.root / "library" / "indexes"

    @property
    def templates_directory(self) -> Path:
        return self.root / "templates" / "library" / "indexes"

    @property
    def schemas_directory(self) -> Path:
        return self.root / "schemas" / "json"

    @property
    def specs_templates_directory(self) -> Path:
        return self.root / "templates" / "library" / "specs" / "scenarios"

    @property
    def docs_templates_directory(self) -> Path:
        return self.root / "templates" / "documentation" / "library"

    @property
    def documentation_directory(self) -> Path:
        return self.root / "documentation" / "library"

    @property
    def schemas_templates_directory(self) -> Path:
        return self.root / "templates" / "schemas" / "json" / "library" / "index"


def resolve(explicit_root: Path | None = None) -> RepoPaths:
    """Find the repo root and return a :class:`RepoPaths` for it."""
    return RepoPaths(root=find_repo_root(explicit_root))
