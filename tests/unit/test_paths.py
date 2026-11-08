"""Tests for the ITBench repository path resolver."""

from pathlib import Path

import pytest

from itbench.paths import ITBenchRepository


def test_explicit_root_wins_over_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path / "env"))
    monkeypatch.delenv("ITBENCH_LIBRARY_PATH", raising=False)

    repo = ITBenchRepository(tmp_path / "explicit")

    assert repo.root == tmp_path / "explicit"
    assert repo.library == tmp_path / "explicit" / "library"
    assert repo.faults == tmp_path / "explicit" / "library" / "faults"
    assert repo.applications == tmp_path / "explicit" / "library" / "applications"
    assert repo.scenarios == tmp_path / "explicit" / "library" / "scenarios"
    assert repo.schemas == tmp_path / "explicit" / "schemas" / "json"
    assert repo.documentation == tmp_path / "explicit" / "documentation" / "library"
    assert repo.ansible_project == tmp_path / "explicit" / "scenarios" / "sre" / "project"
    assert repo.group_vars == tmp_path / "explicit" / "scenarios" / "sre" / "inventory" / "group_vars"


def test_repository_path_env_var_is_read_on_every_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = ITBenchRepository()

    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path / "a"))
    first = repo.root
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path / "b"))

    assert first != repo.root


def test_default_is_source_checkout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ITBENCH_REPOSITORY_PATH", raising=False)
    monkeypatch.delenv("ITBENCH_LIBRARY_PATH", raising=False)

    repo = ITBenchRepository()

    assert repo.ansible_project.is_dir()
    assert repo.group_vars.is_dir()
    assert repo.tools_defaults.is_dir()
    assert repo.applications_defaults.is_dir()
    assert repo.faults.is_dir()
    assert repo.applications.is_dir()
    assert repo.scenarios.is_dir()


def test_library_follows_repository_path_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ITBENCH_LIBRARY_PATH", raising=False)
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))

    assert ITBenchRepository().library == tmp_path.resolve() / "library"


def test_library_path_env_var_overrides_repository_library(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path / "repo"))
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "downloaded"))

    repo = ITBenchRepository()

    assert repo.library == (tmp_path / "downloaded").resolve()
    assert repo.scenarios == (tmp_path / "downloaded").resolve() / "scenarios"
    assert repo.schemas == (tmp_path / "repo").resolve() / "schemas" / "json"


def test_library_path_env_var_is_read_on_every_access(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    repo = ITBenchRepository()

    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "a"))
    first = repo.library
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "b"))

    assert first != repo.library
