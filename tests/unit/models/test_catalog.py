"""Tests for the lazy catalog mapping."""

from itbench.models.catalog import LazyCatalog


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
