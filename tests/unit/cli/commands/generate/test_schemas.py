"""Tests for the generate schemas CLI command."""

import json

from pathlib import Path

from click.testing import CliRunner

from itbench.cli.commands.generate.schemas import generate_schemas_command
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG


def test_generate_schemas_creates_model_schemas(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(generate_schemas_command, ["--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    lib_dir = tmp_path / "library"
    assert (lib_dir / "application.json").exists()
    assert (lib_dir / "fault.json").exists()
    assert (lib_dir / "ground_truth.json").exists()
    assert (lib_dir / "scenario.json").exists()


def test_generate_schemas_creates_waiter_schemas(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(generate_schemas_command, ["--output-dir", str(tmp_path)])

    for waiter_id in WAITER_CATALOG:
        schema_path = tmp_path / "library" / "waiters" / f"{waiter_id}.json"
        assert schema_path.exists(), f"Missing waiter schema: {waiter_id}"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "$schema" in data or "properties" in data


def test_generate_schemas_creates_fault_schemas(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(generate_schemas_command, ["--output-dir", str(tmp_path)])

    for fault_id in FAULT_CATALOG:
        schema_path = tmp_path / "library" / "faults" / f"{fault_id}.json"
        assert schema_path.exists(), f"Missing fault schema: {fault_id}"
        data = json.loads(schema_path.read_text(encoding="utf-8"))
        assert "properties" in data


def test_generate_schemas_model_schema_is_valid_json(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(generate_schemas_command, ["--output-dir", str(tmp_path)])

    for name in ("application.json", "fault.json", "ground_truth.json", "scenario.json"):
        content = (tmp_path / "library" / name).read_text(encoding="utf-8")
        parsed = json.loads(content)
        assert isinstance(parsed, dict)
