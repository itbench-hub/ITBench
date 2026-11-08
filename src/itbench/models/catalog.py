"""Lazily-loaded, read-only catalog of named models."""

from collections.abc import Callable, Iterator, Mapping
from pathlib import Path
from typing import Any, Protocol

import yaml


class _CatalogModel(Protocol):
    """A Pydantic model that can be validated from parsed YAML and exposes a unique ``id``."""

    @property
    def id(self) -> str: ...

    @classmethod
    def model_validate(cls, obj: Any) -> Any: ...


class CatalogError(ValueError):
    """Raised when one or more library files cannot be loaded into a catalog."""


def load_catalog_directory[T: _CatalogModel](directory: Path, model: type[T], kind: str) -> dict[str, T]:
    """Load every ``*.yaml`` file in *directory* as a *model*, keyed by its ``id``.

    Loading is strict: all files are attempted, and if any fail to parse or validate, or two files
    share an id, a single :class:`CatalogError` naming every problem is raised. Library files are
    curated in the repository, so a bad one is a bug that must not be skipped silently.
    """
    if not directory.exists():
        raise FileNotFoundError(f"{kind.capitalize()} library directory not found: {directory}")

    catalog: dict[str, T] = {}
    source: dict[str, str] = {}
    problems: list[str] = []

    for path in sorted(directory.glob("*.yaml")):
        try:
            entry = model.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))
        except Exception as exc:
            reason = "\n".join(f"    {line}" for line in str(exc).splitlines())
            problems.append(f"  {path.name}:\n{reason}")
            continue

        if entry.id in catalog:
            problems.append(f"  {path.name}: duplicate {kind} id '{entry.id}' (already defined in {source[entry.id]})")
            continue
        catalog[entry.id] = entry
        source[entry.id] = path.name

    if problems:
        raise CatalogError(f"Invalid {kind} file(s) in {directory}:\n" + "\n".join(problems))

    return catalog


class LazyCatalog[T](Mapping[str, T]):
    """A read-only mapping whose contents are loaded on first access.

    Importing a module that defines a catalog does not touch the filesystem; the
    loader runs the first time the catalog is read.
    """

    def __init__(self, loader: Callable[[], dict[str, T]]) -> None:
        self._loader = loader
        self._data: dict[str, T] | None = None

    def _load(self) -> dict[str, T]:
        if self._data is None:
            self._data = self._loader()
        return self._data

    def __getitem__(self, key: str) -> T:
        return self._load()[key]

    def __iter__(self) -> Iterator[str]:
        return iter(self._load())

    def __len__(self) -> int:
        return len(self._load())
