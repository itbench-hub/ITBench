"""
Tests for scaffold_scenario.py
"""
import yaml
from pathlib import Path

import scaffold_scenario


def _make_stubs(directory: Path, indexes: list[int]) -> None:
    for i in indexes:
        (directory / f"{i}.yaml.j2").write_text(f"description: Scenario {i}\n", encoding="utf-8")


def test_next_index_empty_directory(tmp_path):
    """next_index returns 1 when no stubs exist yet."""
    assert scaffold_scenario.next_index(tmp_path) == 1


def test_next_index_sequential(tmp_path):
    """next_index returns max existing index + 1."""
    _make_stubs(tmp_path, [1, 2, 3])
    assert scaffold_scenario.next_index(tmp_path) == 4


def test_next_index_with_gaps(tmp_path):
    """next_index uses the numeric maximum, not count, so gaps don't affect it."""
    _make_stubs(tmp_path, [1, 5, 12])
    assert scaffold_scenario.next_index(tmp_path) == 13


def test_create_scenario_stub_filename(tmp_path):
    """create_scenario_stub writes to <index>.yaml.j2."""
    dest = scaffold_scenario.create_scenario_stub("desc", 7, tmp_path)
    assert dest == tmp_path / "7.yaml.j2"
    assert dest.exists()


def test_create_scenario_stub_schema_comment(tmp_path):
    """create_scenario_stub includes the yaml-language-server schema comment on the first line."""
    dest = scaffold_scenario.create_scenario_stub("desc", 1, tmp_path)
    first_line = dest.read_text(encoding="utf-8").splitlines()[0]
    assert "yaml-language-server" in first_line
    assert "scenario.json" in first_line


def test_create_scenario_stub_yaml_content(tmp_path):
    """create_scenario_stub writes valid YAML with the provided description."""
    dest = scaffold_scenario.create_scenario_stub("A description", 1, tmp_path)
    content = "\n".join(dest.read_text(encoding="utf-8").splitlines()[1:])
    data = yaml.safe_load(content)

    assert data["description"] == "A description"
    assert data["id"] == 1


def test_create_scenario_stub_required_keys(tmp_path):
    """create_scenario_stub includes all required stub keys."""
    dest = scaffold_scenario.create_scenario_stub("d", 1, tmp_path)
    content = "\n".join(dest.read_text(encoding="utf-8").splitlines()[1:])
    data = yaml.safe_load(content)

    for key in ("category", "complexity", "disruptions", "environment", "solutionTemplates"):
        assert key in data, f"missing key: {key}"
