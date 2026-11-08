"""Tests for the shared scenario loading helpers."""

from pathlib import Path

from itbench.utils.scenarios import known_scenario_ids, load_scenario_docs, summarize_scenario


def _scenario(root: Path, name: str, content: str) -> None:
    d = root / name
    d.mkdir(parents=True)
    (d / "scenario.yaml").write_text(content, encoding="utf-8")


def test_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert load_scenario_docs(tmp_path / "nope") == []


def test_numeric_order_and_non_numeric_ignored(tmp_path: Path) -> None:
    for name in ("10", "2", "1"):
        _scenario(tmp_path, name, "environment: {}\n")
    _scenario(tmp_path, "notes", "environment: {}\n")

    assert [sid for sid, _ in load_scenario_docs(tmp_path)] == ["1", "2", "10"]


def test_directory_without_scenario_file_is_ignored(tmp_path: Path) -> None:
    (tmp_path / "3").mkdir()

    assert load_scenario_docs(tmp_path) == []


def test_invalid_and_non_mapping_files_reported(tmp_path: Path) -> None:
    _scenario(tmp_path, "1", ": invalid: yaml: [")
    _scenario(tmp_path, "2", "")
    _scenario(tmp_path, "3", "- a\n- b\n")
    _scenario(tmp_path, "4", "environment: {}\n")
    errors: list[str] = []

    docs = load_scenario_docs(tmp_path, on_error=lambda sid, exc: errors.append(sid))

    assert [sid for sid, _ in docs] == ["4"]
    assert errors == ["1", "2", "3"]


def test_known_scenario_ids_numeric_order_and_non_numeric_ignored(tmp_path: Path) -> None:
    for name in ("10", "2", "1", "notes"):
        (tmp_path / name).mkdir()

    assert known_scenario_ids(tmp_path) == ["1", "2", "10"]


def test_known_scenario_ids_missing_directory_returns_empty(tmp_path: Path) -> None:
    assert known_scenario_ids(tmp_path / "nope") == []


def test_summarize_scenario_handles_missing_keys() -> None:
    assert summarize_scenario("1", {}) == {"id": "1", "domains": [], "applications": [], "faults": []}


def test_summarize_scenario_extracts_fields() -> None:
    data = {
        "environment": {"applications": [{"id": "a"}, {}], "domains": ["sre"]},
        "faults": [{"injections": [{"id": "f1"}, {"id": "f2"}]}, {"injections": None}],
    }

    assert summarize_scenario("9", data) == {
        "id": "9",
        "domains": ["sre"],
        "applications": ["a", "?"],
        "faults": ["f1", "f2"],
    }
