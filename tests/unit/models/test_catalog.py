"""Tests for the lazy catalog mapping and the strict directory loader."""

from pathlib import Path

import pytest

from pydantic import BaseModel

from itbench.models.catalog import CatalogError, LazyCatalog, load_catalog_directory


class _Item(BaseModel):
    name: str

    @property
    def id(self) -> str:
        return self.name.lower()


def _write(directory: Path, filename: str, content: str) -> None:
    (directory / filename).write_text(content, encoding="utf-8")


def test_loader_not_called_until_first_access() -> None:
    calls: list[int] = []

    def loader() -> dict[str, int]:
        calls.append(1)
        return {"a": 1, "b": 2}

    catalog = LazyCatalog(loader)
    assert calls == []

    assert catalog["a"] == 1
    assert len(catalog) == 2
    assert sorted(catalog) == ["a", "b"]
    assert "b" in catalog
    assert calls == [1]


def test_loader_errors_surface_on_access_not_construction() -> None:
    def loader() -> dict[str, int]:
        raise FileNotFoundError("missing")

    catalog = LazyCatalog(loader)

    try:
        len(catalog)
    except FileNotFoundError as exc:
        assert "missing" in str(exc)
    else:
        raise AssertionError("expected FileNotFoundError")


def test_load_catalog_directory_keys_entries_by_id(tmp_path: Path) -> None:
    _write(tmp_path, "a.yaml", "name: Alpha\n")
    _write(tmp_path, "b.yaml", "name: Beta\n")
    _write(tmp_path, "notes.txt", "not yaml, ignored")

    catalog = load_catalog_directory(tmp_path, _Item, "item")

    assert sorted(catalog) == ["alpha", "beta"]
    assert catalog["alpha"].name == "Alpha"


def test_load_catalog_directory_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Item library directory not found"):
        load_catalog_directory(tmp_path / "nope", _Item, "item")


def test_load_catalog_directory_reports_every_invalid_file_at_once(tmp_path: Path) -> None:
    _write(tmp_path, "good.yaml", "name: Good\n")
    _write(tmp_path, "bad-one.yaml", "name: [unclosed\n")
    _write(tmp_path, "bad-two.yaml", "other: value\n")

    with pytest.raises(CatalogError) as excinfo:
        load_catalog_directory(tmp_path, _Item, "item")

    message = str(excinfo.value)
    assert "Invalid item file(s)" in message
    assert "bad-one.yaml" in message
    assert "bad-two.yaml" in message
    assert "good.yaml" not in message


def test_load_catalog_directory_rejects_non_mapping_file(tmp_path: Path) -> None:
    _write(tmp_path, "list.yaml", "- a\n- b\n")

    with pytest.raises(CatalogError, match=r"list\.yaml"):
        load_catalog_directory(tmp_path, _Item, "item")


def test_load_catalog_directory_rejects_duplicate_ids(tmp_path: Path) -> None:
    _write(tmp_path, "a.yaml", "name: Same\n")
    _write(tmp_path, "b.yaml", "name: SAME\n")

    with pytest.raises(CatalogError) as excinfo:
        load_catalog_directory(tmp_path, _Item, "item")

    message = str(excinfo.value)
    assert "b.yaml" in message
    assert "duplicate item id 'same'" in message
    assert "a.yaml" in message


def test_catalog_error_surfaces_through_lazy_catalog(tmp_path: Path) -> None:
    _write(tmp_path, "bad.yaml", "other: value\n")
    catalog = LazyCatalog(lambda: load_catalog_directory(tmp_path, _Item, "item"))

    with pytest.raises(CatalogError):
        len(catalog)
