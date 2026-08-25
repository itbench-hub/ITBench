"""
Tests for generate_library_specs.py

Makefile invocation:
  scripts/generate_library_specs.py
    --templates_directory=<path>
    --library_index_directory=<path>
    --specs_directory=<path>
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

import generate_library_specs


ARGV = [
    "generate_library_specs.py",
    "--templates_directory", "/templates/library/specs/scenarios",
    "--library_index_directory", "/lib/indexes",
    "--specs_directory", "/library/specs/scenarios",
]

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


def _patched_main():
    with patch("sys.argv", ARGV), \
         patch("generate_library_specs.load_scenarios", return_value=SCENARIOS) as mock_load, \
         patch("generate_library_specs.generate_scenario_specs") as mock_gen, \
         patch("generate_library_specs.Environment"):
        generate_library_specs.main()
        return mock_load, mock_gen


def test_arguments():
    """main() accepts the argument names expected in the Makefile."""
    mock_load, mock_gen = _patched_main()
    mock_load.assert_called_once_with(Path("/lib/indexes"))
    assert mock_gen.call_count == 2


def test_all_scenarios_processed():
    """main() calls generate_scenario_specs once per scenario."""
    _, mock_gen = _patched_main()
    processed_ids = [c.args[0]["id"] for c in mock_gen.call_args_list]
    assert processed_ids == ["1", "2"]


def test_specs_directory_passed():
    """main() passes --specs_directory to each generate_scenario_specs call."""
    _, mock_gen = _patched_main()
    for c in mock_gen.call_args_list:
        assert c.args[1] == Path("/library/specs/scenarios")


def test_load_scenarios(tmp_path):
    """load_scenarios reads all *.json files from library_index_directory/scenarios/."""
    scenarios_dir = tmp_path / "scenarios"
    scenarios_dir.mkdir()
    for scenario in SCENARIOS:
        (scenarios_dir / f"{scenario['id']}.json").write_text(
            json.dumps(scenario), encoding="utf-8"
        )

    result = generate_library_specs.load_scenarios(tmp_path)

    assert len(result) == 2
    assert {s["id"] for s in result} == {"1", "2"}


_RENDERED_YAML = "apiVersion: itbench.io/v2\nkind: Scenario\nmetadata:\n  name: scenario-1\n"


def test_scenario_directory_created(tmp_path):
    """generate_scenario_specs creates scenario_<id>/ under specs_directory."""
    mock_env = MagicMock()
    mock_env.get_template.return_value.render.return_value = _RENDERED_YAML

    generate_library_specs.generate_scenario_specs(SCENARIOS[0], tmp_path, mock_env)

    assert (tmp_path / "1").is_dir()


def test_spec_files_written(tmp_path):
    """generate_scenario_specs writes scenario.yaml and groundtruth.yaml."""
    mock_env = MagicMock()
    mock_env.get_template.return_value.render.return_value = _RENDERED_YAML

    generate_library_specs.generate_scenario_specs(SCENARIOS[0], tmp_path, mock_env)

    assert (tmp_path / "1" / "scenario.yaml").exists()
    assert (tmp_path / "1" / "groundtruth.yaml").exists()


def test_correct_templates_rendered(tmp_path):
    """generate_scenario_specs renders scenario.yaml.j2 and groundtruth.yaml.j2."""
    mock_env = MagicMock()
    mock_env.get_template.return_value.render.return_value = _RENDERED_YAML

    generate_library_specs.generate_scenario_specs(SCENARIOS[0], tmp_path, mock_env)

    requested = [c.args[0] for c in mock_env.get_template.call_args_list]
    assert "scenario.yaml.j2" in requested
    assert "groundtruth.yaml.j2" in requested
