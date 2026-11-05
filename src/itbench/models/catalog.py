"""Lazily-loaded, read-only catalog of named models."""

from collections.abc import Callable, Iterator, Mapping


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
