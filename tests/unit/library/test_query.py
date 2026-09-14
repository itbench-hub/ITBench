"""Tests for itbench.library.query."""
import json
from pathlib import Path

from itbench.library.query import (
    get_resource,
    get_scenario_statistics,
    list_resources,
    search_resources,
)


def test_query_and_search(tmp_path):
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    sample = {
        "id": "test-scen-1",
        "name": "Test Scenario",
        "description": "High memory heap leak in Valkey",
        "category": "sre",
        "complexity": "medium",
        "environment": {"applications": [{"id": "opentelemetry-demo"}]},
    }
    (scenarios_dir / "1.json").write_text(json.dumps(sample), encoding="utf-8")

    items = list_resources(tmp_path, "scenarios")
    assert len(items) == 1
    assert items[0]["id"] == "test-scen-1"

    found = get_resource(tmp_path, "scenarios", "test-scen-1")
    assert found is not None
    assert found["name"] == "Test Scenario"

    search_res = search_resources(tmp_path, "valkey")
    assert len(search_res["scenarios"]) == 1

    stats = get_scenario_statistics(tmp_path)
    assert stats["categories"]["sre"] == 1
    assert stats["complexities"]["medium"] == 1
    assert stats["applications"]["opentelemetry-demo"] == 1
