#!/usr/bin/env python3
"""
Unit tests for evaluate_scenario.py

Uses mocking to test each evaluator class in isolation.
"""

import json
import tempfile
import tarfile
from pathlib import Path
from unittest import mock
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Import the evaluators
import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from evaluate_scenario import (
    AlertsEvaluator,
    KubernetesEvaluator,
    OPAEvaluator,
    CheckResult,
    load_groundtruth
)


class TestAlertsEvaluator:
    """Test AlertsEvaluator class."""

    @patch("evaluate_scenario.requests.get")
    def test_evaluate_alert_found_with_matching_labels(self, mock_get):
        """Test alert found with exact label match."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "alerts": [
                    {
                        "state": "firing",
                        "labels": {
                            "alertname": "KubePodNotReady",
                            "severity": "critical"
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        evaluator = AlertsEvaluator("http://prometheus:9090")
        results, all_pass = evaluator.evaluate([
            {
                "name": "KubePodNotReady",
                "labels": {"severity": "critical"}
            }
        ])

        assert all_pass is True
        assert len(results) == 1
        assert results[0]["name"] == "KubePodNotReady"
        assert results[0]["pass"] is True

    @patch("evaluate_scenario.requests.get")
    def test_evaluate_alert_not_found(self, mock_get):
        """Test alert not found."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {"alerts": []}
        }
        mock_get.return_value = mock_response

        evaluator = AlertsEvaluator("http://prometheus:9090")
        results, all_pass = evaluator.evaluate([
            {
                "name": "NonExistent",
                "labels": {}
            }
        ])

        assert all_pass is False
        assert len(results) == 1
        assert results[0]["pass"] is False

    @patch("evaluate_scenario.requests.get")
    def test_evaluate_alert_with_subset_labels(self, mock_get):
        """Test alert found with subset of labels."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "data": {
                "alerts": [
                    {
                        "state": "firing",
                        "labels": {
                            "alertname": "KubePodNotReady",
                            "severity": "critical",
                            "team": "platform"
                        }
                    }
                ]
            }
        }
        mock_get.return_value = mock_response

        evaluator = AlertsEvaluator("http://prometheus:9090")
        results, all_pass = evaluator.evaluate([
            {
                "name": "KubePodNotReady",
                "labels": {"severity": "critical"}
            }
        ])

        assert all_pass is True
        assert results[0]["pass"] is True

    @patch("evaluate_scenario.requests.get")
    def test_evaluate_no_alerts(self, mock_get):
        """Test when no alerts are expected."""
        evaluator = AlertsEvaluator("http://prometheus:9090")
        results, all_pass = evaluator.evaluate([])

        assert all_pass is True
        assert len(results) == 0


class TestKubernetesEvaluator:
    """Test KubernetesEvaluator class."""

    def test_subset_match_identical_dicts(self):
        """Test subset match with identical dicts."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"a": 1, "b": {"c": 2}}
        live = {"a": 1, "b": {"c": 2}}

        match, reason = evaluator._subset_match(expected, live)
        assert match is True

    def test_subset_match_expected_subset(self):
        """Test subset match where expected is subset of live."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"a": 1}
        live = {"a": 1, "b": 2, "c": {"d": 3}}

        match, reason = evaluator._subset_match(expected, live)
        assert match is True

    def test_subset_match_nested_subset(self):
        """Test subset match with nested dict."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"spec": {"template": {"spec": {"hostNetwork": False}}}}
        live = {
            "spec": {
                "template": {
                    "spec": {
                        "hostNetwork": False,
                        "containers": [{"name": "app"}]
                    }
                },
                "replicas": 3
            }
        }

        match, reason = evaluator._subset_match(expected, live)
        assert match is True

    def test_subset_match_value_mismatch(self):
        """Test subset match with value mismatch."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"hostNetwork": False}
        live = {"hostNetwork": True}

        match, reason = evaluator._subset_match(expected, live)
        assert match is False
        assert "hostNetwork" in reason

    def test_subset_match_missing_key(self):
        """Test subset match with missing key."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"a": 1, "b": 2}
        live = {"a": 1}

        match, reason = evaluator._subset_match(expected, live)
        assert match is False
        assert "missing" in reason

    def test_subset_match_list_equality(self):
        """Test subset match with lists (exact equality required)."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"containers": [{"name": "app"}]}
        live = {"containers": [{"name": "app"}]}

        match, reason = evaluator._subset_match(expected, live)
        assert match is True

    def test_subset_match_list_mismatch(self):
        """Test subset match with list mismatch."""
        evaluator = KubernetesEvaluator.__new__(KubernetesEvaluator)
        expected = {"containers": [{"name": "app"}]}
        live = {"containers": [{"name": "app"}, {"name": "sidecar"}]}

        match, reason = evaluator._subset_match(expected, live)
        assert match is False


class TestOPAEvaluator:
    """Test OPAEvaluator class."""

    def test_extract_opa_result_simple_bool(self):
        """Test extracting simple boolean from OPA output."""
        evaluator = OPAEvaluator.__new__(OPAEvaluator)
        opa_output = json.dumps({
            "result": [
                {
                    "expressions": [
                        {"value": True}
                    ]
                }
            ]
        })

        value = evaluator._extract_opa_result(opa_output)
        assert value is True

    def test_extract_opa_result_false(self):
        """Test extracting false from OPA output."""
        evaluator = OPAEvaluator.__new__(OPAEvaluator)
        opa_output = json.dumps({
            "result": [
                {
                    "expressions": [
                        {"value": False}
                    ]
                }
            ]
        })

        value = evaluator._extract_opa_result(opa_output)
        assert value is False

    def test_extract_opa_result_complex_object(self):
        """Test extracting complex object from OPA output."""
        evaluator = OPAEvaluator.__new__(OPAEvaluator)
        expected_obj = {"passed": 3, "failed": 0}
        opa_output = json.dumps({
            "result": [
                {
                    "expressions": [
                        {"value": expected_obj}
                    ]
                }
            ]
        })

        value = evaluator._extract_opa_result(opa_output)
        assert value == expected_obj

    def test_extract_opa_result_invalid_json(self):
        """Test extracting from invalid JSON."""
        evaluator = OPAEvaluator.__new__(OPAEvaluator)
        value = evaluator._extract_opa_result("invalid json")
        assert value is None

    @patch("evaluate_scenario.subprocess.run")
    def test_run_opa_eval_success(self, mock_run):
        """Test successful OPA eval run."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"result": [{"expressions": [{"value": true}]}]}'
        mock_run.return_value = mock_result

        evaluator = OPAEvaluator.__new__(OPAEvaluator)
        output = evaluator._run_opa_eval("/path/to/data.rego", "/path/to/input.json")

        assert output == '{"result": [{"expressions": [{"value": true}]}]}'
        mock_run.assert_called_once()

    @patch("evaluate_scenario.subprocess.run")
    def test_run_opa_eval_failure(self, mock_run):
        """Test OPA eval failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "OPA error"
        mock_run.return_value = mock_result

        evaluator = OPAEvaluator.__new__(OPAEvaluator)
        output = evaluator._run_opa_eval("/path/to/data.rego", "/path/to/input.json")

        assert output is None


class TestCheckResult:
    """Test CheckResult dataclass."""

    def test_to_dict_pass(self):
        """Test CheckResult to_dict for passing check."""
        result = CheckResult(True, "All good")
        d = result.to_dict()

        assert d["pass"] is True
        assert d["message"] == "All good"

    def test_to_dict_fail(self):
        """Test CheckResult to_dict for failing check."""
        result = CheckResult(False, "Something went wrong")
        d = result.to_dict()

        assert d["pass"] is False
        assert d["message"] == "Something went wrong"


class TestLoadGroundtruth:
    """Test load_groundtruth function."""

    def test_load_valid_groundtruth(self):
        """Test loading valid groundtruth file."""
        groundtruth_data = """
apiVersion: itbench.io/v2
kind: GroundTruth
metadata:
  name: scenario-64
spec:
  alerts:
    - name: TestAlert
  kubernetes:
    resources:
      - kind: Deployment
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(groundtruth_data)
            f.flush()

            try:
                spec = load_groundtruth(f.name)
                assert "alerts" in spec
                assert spec["alerts"][0]["name"] == "TestAlert"
            finally:
                Path(f.name).unlink()

    def test_load_missing_file(self):
        """Test loading non-existent file."""
        with pytest.raises(Exception):
            load_groundtruth("/nonexistent/path/groundtruth.yaml")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
