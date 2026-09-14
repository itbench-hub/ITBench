"""Tests for itbench.scenarios.faults."""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import yaml

import itbench.scenarios.faults as faults

_SPEC = {
    "spec": {
        "faults": [
            {"injections": [{"id": "fault-a", "args": {}}]},
            {"injections": [{"id": "fault-b", "args": {}}]},
        ]
    }
}


def test_load_scenario_spec_returns_parsed_dict():
    with patch.object(Path, "read_text", return_value="spec: {}"), \
         patch("itbench.scenarios.faults.yaml.safe_load", return_value=_SPEC):
        result = faults.load_scenario_spec(Path("/specs"))
    assert result == _SPEC


def test_load_scenario_spec_raises_on_missing_file():
    with patch.object(Path, "read_text", side_effect=FileNotFoundError), \
         pytest.raises(FileNotFoundError):
        faults.load_scenario_spec(Path("/nonexistent"))


def test_load_scenario_spec_raises_on_invalid_yaml():
    with patch.object(Path, "read_text", return_value="spec: {}"), \
         patch("itbench.scenarios.faults.yaml.safe_load", side_effect=yaml.YAMLError("bad")), \
         pytest.raises(yaml.YAMLError):
        faults.load_scenario_spec(Path("/specs"))


def test_wait_for_runners_returns_immediately_for_successful_status():
    with patch("itbench.scenarios.faults.time.sleep") as mock_sleep:
        faults.wait_for_runners([Mock(status="successful")])
    mock_sleep.assert_not_called()


@pytest.mark.parametrize("status", ["failed", "canceled", "timeout"])
def test_wait_for_runners_raises_on_failed_terminal_status(status):
    with patch("itbench.scenarios.faults.time.sleep") as mock_sleep, \
         pytest.raises(RuntimeError):
        faults.wait_for_runners([Mock(status=status)])


def test_wait_for_runners_polls_until_terminal():
    runner = Mock()
    runner.status = "running"

    def flip(*_):
        runner.status = "successful"

    with patch("itbench.scenarios.faults.time.sleep", side_effect=flip) as mock_sleep:
        faults.wait_for_runners([runner])

    mock_sleep.assert_called_once_with(1)
