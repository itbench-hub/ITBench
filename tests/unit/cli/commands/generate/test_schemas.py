"""Tests for the generate schemas CLI command."""

import json

from pathlib import Path

import pytest

from click.testing import CliRunner

from itbench.cli.commands.generate.schemas import generate_schemas_command
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG


@pytest.fixture
def schemas_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the repository root at a temporary directory and return where schemas are written."""
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))
    return tmp_path / "schemas" / "json"


def test_generate_schemas_accepts_no_output_location() -> None:
    result = CliRunner().invoke(generate_schemas_command, ["--output-dir", "/elsewhere"])

    assert result.exit_code == 2
    assert "No such option" in result.output


def test_generate_schemas_creates_model_schemas(schemas_dir: Path) -> None:
    result = CliRunner().invoke(generate_schemas_command, [])

    assert result.exit_code == 0
    lib_dir = schemas_dir / "library"
    assert (lib_dir / "application.json").exists()
    assert (lib_dir / "fault.json").exists()
    assert (lib_dir / "ground_truth.json").exists()
    assert (lib_dir / "scenario.json").exists()


def test_generate_schemas_creates_waiter_schemas(schemas_dir: Path) -> None:
    CliRunner().invoke(generate_schemas_command, [])

    for waiter_id in WAITER_CATALOG:
        schema_path = schemas_dir / "library" / "waiters" / f"{waiter_id}.json"
        assert schema_path.exists(), f"Missing waiter schema: {waiter_id}"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "$schema" in data or "properties" in data


def test_generate_schemas_creates_fault_schemas(schemas_dir: Path) -> None:
    CliRunner().invoke(generate_schemas_command, [])

    for fault_id in FAULT_CATALOG:
        schema_path = schemas_dir / "library" / "faults" / f"{fault_id}.json"
        assert schema_path.exists(), f"Missing fault schema: {fault_id}"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "properties" in data


def test_generate_schemas_model_schema_is_valid_json(schemas_dir: Path) -> None:
    CliRunner().invoke(generate_schemas_command, [])

    for name in ("application.json", "fault.json", "ground_truth.json", "scenario.json"):
        content = (schemas_dir / "library" / name).read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
