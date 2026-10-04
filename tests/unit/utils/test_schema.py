"""Tests for itbench.utils.schema."""

import json

from pathlib import Path

from pydantic import BaseModel, Field

from itbench.models.fault import FAULT_CATALOG
from itbench.utils.schema import export_fault_schema, export_json_schema


class _Simple(BaseModel):
    name: str = Field(description="A name.")
    value: int = Field(default=0)


def test_export_json_schema_writes_file(tmp_path: Path) -> None:
    out = tmp_path / "sub" / "simple.json"
    export_json_schema(_Simple, out)
    assert out.exists()


def test_export_json_schema_creates_parent_dirs(tmp_path: Path) -> None:
    out = tmp_path / "a" / "b" / "c" / "schema.json"
    export_json_schema(_Simple, out)
    assert out.exists()


def test_export_json_schema_file_is_valid_json(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    export_json_schema(_Simple, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_export_json_schema_injects_draft_2020_12(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    export_json_schema(_Simple, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["$schema"] == "https://json-schema.org/draft/2020-12/schema"


def test_export_json_schema_contains_model_properties(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    schema = export_json_schema(_Simple, out)
    assert "name" in schema.get("properties", {})
    assert "value" in schema.get("properties", {})


def test_export_json_schema_returns_schema_dict(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    result = export_json_schema(_Simple, out)
    assert isinstance(result, dict)
    assert "$schema" in result


def test_export_json_schema_file_ends_with_newline(tmp_path: Path) -> None:
    out = tmp_path / "schema.json"
    export_json_schema(_Simple, out)
    assert out.read_text(encoding="utf-8").endswith("\n")


def test_export_fault_schema_writes_file(tmp_path: Path) -> None:
    fault = next(iter(FAULT_CATALOG.values()))
    out = tmp_path / "fault.json"
    export_fault_schema(fault, out)
    assert out.exists()


def test_export_fault_schema_is_valid_json(tmp_path: Path) -> None:
    fault = next(iter(FAULT_CATALOG.values()))
    out = tmp_path / "fault.json"
    export_fault_schema(fault, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_export_fault_schema_sets_title_and_description(tmp_path: Path) -> None:
    fault = next(iter(FAULT_CATALOG.values()))
    out = tmp_path / "fault.json"
    export_fault_schema(fault, out)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["title"] == fault.name
    assert data["description"] == fault.description


def test_export_fault_schema_constrains_kubernetes_enum(tmp_path: Path) -> None:
    fault = next(f for f in FAULT_CATALOG.values() if f.targets)
    out = tmp_path / "fault.json"
    export_fault_schema(fault, out)
    data = json.loads(out.read_text(encoding="utf-8"))

    enum = (
        data["$defs"]["FaultTargetReference"]["properties"]["kubernetes"]["enum"]
    )
    expected = [t.kubernetes for t in fault.targets]
    assert enum == expected


def test_export_fault_schema_merges_kube_defs(tmp_path: Path) -> None:
    fault = next(f for f in FAULT_CATALOG.values() if f.targets)
    out = tmp_path / "fault.json"
    export_fault_schema(fault, out)
    data = json.loads(out.read_text(encoding="utf-8"))

    for target in fault.targets:
        assert target.kubernetes in data["$defs"]


def test_export_fault_schema_creates_parent_dirs(tmp_path: Path) -> None:
    fault = next(iter(FAULT_CATALOG.values()))
    out = tmp_path / "nested" / "dir" / "fault.json"
    export_fault_schema(fault, out)
    assert out.exists()
