"""Tests for the ITBench library path resolver."""

from pathlib import Path

import pytest

from itbench.paths import ITBenchLibrary


def test_explicit_root_wins_over_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "env"))

    lib = ITBenchLibrary(tmp_path / "explicit")

    assert lib.root == tmp_path / "explicit"
    assert lib.faults == tmp_path / "explicit" / "faults"
    assert lib.applications == tmp_path / "explicit" / "applications"
    assert lib.scenarios == tmp_path / "explicit" / "scenarios"


def test_env_var_overrides_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path))

    assert ITBenchLibrary().root == tmp_path.resolve()


def test_env_var_is_read_on_every_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    lib = ITBenchLibrary()

    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "a"))
    first = lib.root
    monkeypatch.setenv("ITBENCH_LIBRARY", str(tmp_path / "b"))

    assert first != lib.root


def test_default_is_source_checkout_library(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ITBENCH_LIBRARY", raising=False)

    root = ITBenchLibrary().root

    assert root.name == "library"
    assert (root / "faults").is_dir()
    assert (root / "applications").is_dir()
    assert (root / "scenarios").is_dir()
