"""
Tests for scripts/scenarios/inject_scenario_faults.py

This script is invoked by the Makefile or inside the Argo Docker container;
we only test the logic that can meaningfully fail in isolation.
"""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

import inject_scenario_faults


_SPEC = {
    "spec": {
        "faults": [
            {"injections": [{"id": "fault-a", "args": {}}]},
            {"injections": [{"id": "fault-b", "args": {}}]},
        ]
    }
}


# ---------------------------------------------------------------------------
# load_scenario_spec
# ---------------------------------------------------------------------------

def test_load_scenario_spec_returns_parsed_dict():
    with patch.object(Path, "read_text", return_value="spec: {}"), \
         patch("inject_scenario_faults.yaml.safe_load", return_value=_SPEC):
        result = inject_scenario_faults.load_scenario_spec(Path("/specs"))
    assert result == _SPEC


def test_load_scenario_spec_exits_on_missing_file():
    with patch.object(Path, "read_text", side_effect=FileNotFoundError), \
         patch("sys.exit") as mock_exit:
        inject_scenario_faults.load_scenario_spec(Path("/nonexistent"))
    mock_exit.assert_called_once_with(1)


def test_load_scenario_spec_exits_on_invalid_yaml():
    with patch.object(Path, "read_text", return_value="spec: {}"), \
         patch("inject_scenario_faults.yaml.safe_load", side_effect=yaml.YAMLError("bad")), \
         patch("sys.exit") as mock_exit:
        inject_scenario_faults.load_scenario_spec(Path("/specs"))
    mock_exit.assert_called_once_with(1)


# ---------------------------------------------------------------------------
# wait_for_runners
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("status", ["successful", "failed", "canceled", "timeout"])
def test_wait_for_runners_returns_immediately_for_terminal_status(status):
    with patch("inject_scenario_faults.time.sleep") as mock_sleep:
        inject_scenario_faults.wait_for_runners([Mock(status=status)])
    mock_sleep.assert_not_called()


def test_wait_for_runners_polls_until_terminal():
    runner = Mock()
    runner.status = "running"

    def flip(*_):
        runner.status = "successful"

    with patch("inject_scenario_faults.time.sleep", side_effect=flip) as mock_sleep:
        inject_scenario_faults.wait_for_runners([runner])

    mock_sleep.assert_called_once_with(1)
