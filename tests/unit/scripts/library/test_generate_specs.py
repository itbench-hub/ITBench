"""
Tests for generate_specs.py
"""
from pathlib import Path
from unittest.mock import MagicMock

import generate_specs


SCENARIOS = [
    {
        "id": "1",
        "category": "sre",
        "alerts": [],
        "disruptions": [
            {"injections": [{"id": "test-fault", "args": {}}]}
        ],
        "environment": {"applications": [{"id": "opentelemetry-demo"}]},
        "solutions": [],
    },
    {
        "id": "2",
        "category": "finops",
        "alerts": ["KubePodNotReady"],
        "disruptions": [
            {"injections": [{"id": "other-fault", "args": {}}]}
        ],
        "environment": {"applications": [{"id": "book-info"}]},
        "solutions": [],
    },
]

_RENDERED_YAML = "apiVersion: itbench.io/v2\nkind: Scenario\nmetadata:\n  name: scenario-1\n"


def _mock_env():
    mock_env = MagicMock()
    mock_env.get_template.return_value.render.return_value = _RENDERED_YAML
    return mock_env


def test_load_scenarios(tmp_path):
    """load_scenarios reads all *.json files from library_index_directory/scenarios/."""
    import json
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    for scenario in SCENARIOS:
        (scenarios_dir / f"{scenario['id']}.json").write_text(
            json.dumps(scenario), encoding="utf-8"
        )

    result = generate_specs.load_scenarios(tmp_path)

    assert len(result) == 2
    assert {s["id"] for s in result} == {"1", "2"}


def test_scenario_directory_created(tmp_path):
    """generate_scenario_specs creates a subdirectory named after the scenario id."""
    generate_specs.generate_scenario_specs(SCENARIOS[0], tmp_path, _mock_env())
    assert (tmp_path / "1").is_dir()


def test_spec_files_written(tmp_path):
    """generate_scenario_specs writes scenario.yaml and groundtruth.yaml."""
    generate_specs.generate_scenario_specs(SCENARIOS[0], tmp_path, _mock_env())
    assert (tmp_path / "1" / "scenario.yaml").exists()
    assert (tmp_path / "1" / "groundtruth.yaml").exists()


def test_correct_templates_rendered(tmp_path):
    """generate_scenario_specs renders scenario.yaml.j2 and groundtruth.yaml.j2."""
    mock_env = _mock_env()
    generate_specs.generate_scenario_specs(SCENARIOS[0], tmp_path, mock_env)
    requested = [c.args[0] for c in mock_env.get_template.call_args_list]
    assert "scenario.yaml.j2" in requested
    assert "groundtruth.yaml.j2" in requested
