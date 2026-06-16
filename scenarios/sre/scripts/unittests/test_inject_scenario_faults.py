import sys
import unittest

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# Add parent directory to path to import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import inject_scenario_faults


class TestLoadScenarioSpec(unittest.TestCase):
    """Test loading scenario specifications."""

    @patch("builtins.open", new_callable=mock_open)
    @patch("inject_scenario_faults.yaml.safe_load")
    def test_load_scenario_spec_success(self, mock_yaml_load, mock_file):
        """Test successful loading of scenario spec."""
        private_project_dir = Path("/test/project")
        scenario_id = 1

        spec_data = {
            "spec": {
                "faults": [
                    {
                        "injections": [
                            {
                                "id": "test-fault",
                                "args": {}
                            }
                        ]
                    }
                ]
            }
        }
        mock_yaml_load.return_value = spec_data

        result = inject_scenario_faults.load_scenario_spec(private_project_dir, scenario_id)

        self.assertEqual(result, spec_data)
        self.assertEqual(len(result["spec"]["faults"]), 1)

    @patch("builtins.open", side_effect=FileNotFoundError)
    @patch("sys.exit")
    def test_load_scenario_spec_file_not_found(self, mock_exit, mock_file):
        """Test handling of missing scenario spec file."""
        private_project_dir = Path("/test/project")
        scenario_id = 999

        inject_scenario_faults.load_scenario_spec(private_project_dir, scenario_id)

        # Verify sys.exit was called with error code
        mock_exit.assert_called_once_with(1)

    @patch("builtins.open", new_callable=mock_open)
    @patch("inject_scenario_faults.yaml.safe_load")
    @patch("sys.exit")
    def test_load_scenario_spec_yaml_error(self, mock_exit, mock_yaml_load, mock_file):
        """Test handling of YAML parsing errors."""
        import yaml

        private_project_dir = Path("/test/project")
        scenario_id = 1

        mock_yaml_load.side_effect = yaml.YAMLError("Invalid YAML")

        inject_scenario_faults.load_scenario_spec(private_project_dir, scenario_id)

        mock_exit.assert_called_once_with(1)


class TestInjectFaultGroup(unittest.TestCase):
    """Test fault group injection."""

    @patch("inject_scenario_faults.ansible_runner.interface.run_async")
    def test_inject_fault_group(self, mock_run_async):
        """Test injecting a single fault group."""
        private_project_dir = Path("/test/project")
        scenario_id = 1
        faults_index = 0

        mock_runner = Mock()
        mock_run_async.return_value = (None, mock_runner)

        result = inject_scenario_faults.inject_fault_group(
            private_project_dir,
            scenario_id,
            faults_index
        )

        # Verify ansible_runner was called with correct parameters
        mock_run_async.assert_called_once_with(
            private_data_dir=str(private_project_dir),
            playbook="manage_faults.yaml",
            ident=f"scenario-{scenario_id}-fault-{faults_index}",
            cmdline=f"--tags inject_faults --extra-vars scenario_id={scenario_id} --extra-vars faults_index={faults_index}"
        )

        # Verify runner is returned
        self.assertEqual(result, mock_runner)

    @patch("inject_scenario_faults.ansible_runner.interface.run_async")
    def test_inject_fault_group_multiple_indexes(self, mock_run_async):
        """Test injecting multiple fault groups with different indexes."""
        private_project_dir = Path("/test/project")
        scenario_id = 60

        mock_runner = Mock()
        mock_run_async.return_value = (None, mock_runner)

        for faults_index in range(3):
            inject_scenario_faults.inject_fault_group(
                private_project_dir,
                scenario_id,
                faults_index
            )

        # Verify ansible_runner was called 3 times
        self.assertEqual(mock_run_async.call_count, 3)

        # Verify each call had correct faults_index
        for i, call in enumerate(mock_run_async.call_args_list):
            self.assertIn(f"faults_index={i}", call[1]["cmdline"])


class TestWaitForRunners(unittest.TestCase):
    """Test waiting for runners to complete."""

    @patch("inject_scenario_faults.time.sleep")
    def test_wait_for_runners_all_successful(self, mock_sleep):
        """Test waiting for all runners to complete successfully."""
        mock_runners = [
            Mock(status="successful"),
            Mock(status="successful"),
            Mock(status="successful")
        ]

        inject_scenario_faults.wait_for_runners(mock_runners)

        # No assertions needed - just verify it completes without error

    @patch("inject_scenario_faults.time.sleep")
    def test_wait_for_runners_with_pending_status(self, mock_sleep):
        """Test waiting for runners that start in pending state."""
        mock_runner = Mock()
        # Simulate runner transitioning from running to successful
        mock_runner.status = "running"

        def change_status(*args):
            mock_runner.status = "successful"

        mock_sleep.side_effect = change_status

        inject_scenario_faults.wait_for_runners([mock_runner])

        # Verify sleep was called at least once
        mock_sleep.assert_called()

    @patch("inject_scenario_faults.time.sleep")
    def test_wait_for_runners_mixed_statuses(self, mock_sleep):
        """Test waiting for runners with different completion statuses."""
        mock_runners = [
            Mock(status="successful"),
            Mock(status="failed"),
            Mock(status="canceled"),
            Mock(status="timeout")
        ]

        inject_scenario_faults.wait_for_runners(mock_runners)

        # Verify function completes for all terminal statuses


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("inject_scenario_faults.wait_for_runners")
    @patch("inject_scenario_faults.inject_fault_group")
    @patch("inject_scenario_faults.load_scenario_spec")
    @patch("sys.argv", ["script.py",
                        "--private_project_directory", "/test/project",
                        "--scenario_id", "1"])
    def test_main_single_fault_group(self, mock_load_spec, mock_inject, mock_wait):
        """Test main function with single fault group."""
        spec_data = {
            "spec": {
                "faults": [
                    {
                        "injections": [
                            {
                                "id": "test-fault",
                                "args": {}
                            }
                        ]
                    }
                ]
            }
        }
        mock_load_spec.return_value = spec_data

        mock_runner = Mock()
        mock_inject.return_value = mock_runner

        inject_scenario_faults.main()

        # Verify spec was loaded
        mock_load_spec.assert_called_once()

        # Verify inject was called once
        mock_inject.assert_called_once()

        # Verify wait was called with list of runners
        mock_wait.assert_called_once()
        call_args = mock_wait.call_args[0][0]
        self.assertEqual(len(call_args), 1)

    @patch("inject_scenario_faults.wait_for_runners")
    @patch("inject_scenario_faults.inject_fault_group")
    @patch("inject_scenario_faults.load_scenario_spec")
    @patch("sys.argv", ["script.py",
                        "--private_project_directory", "/test/project",
                        "--scenario_id", "60"])
    def test_main_multiple_fault_groups(self, mock_load_spec, mock_inject, mock_wait):
        """Test main function with multiple fault groups."""
        spec_data = {
            "spec": {
                "faults": [
                    {"injections": [{"id": "fault1", "args": {}}]},
                    {"injections": [{"id": "fault2", "args": {}}]},
                    {"injections": [{"id": "fault3", "args": {}}]}
                ]
            }
        }
        mock_load_spec.return_value = spec_data

        mock_runners = [Mock(), Mock(), Mock()]
        mock_inject.side_effect = mock_runners

        inject_scenario_faults.main()

        # Verify inject was called 3 times
        self.assertEqual(mock_inject.call_count, 3)

        # Verify correct parameters for each call
        for i, call in enumerate(mock_inject.call_args_list):
            self.assertEqual(call[0][1], 60)  # scenario_id
            self.assertEqual(call[0][2], i)   # faults_index

        # Verify wait was called with all runners
        mock_wait.assert_called_once()
        call_args = mock_wait.call_args[0][0]
        self.assertEqual(len(call_args), 3)


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    @patch("inject_scenario_faults.time.sleep")
    @patch("inject_scenario_faults.ansible_runner.interface.run_async")
    @patch("builtins.open", new_callable=mock_open)
    @patch("inject_scenario_faults.yaml.safe_load")
    @patch("sys.argv", ["script.py",
                        "--private_project_directory", "/test/project",
                        "--scenario_id", "1"])
    def test_full_injection_flow(self, mock_yaml_load, mock_file, mock_run_async, mock_sleep):
        """Test complete fault injection flow."""
        spec_data = {
            "spec": {
                "faults": [
                    {
                        "injections": [
                            {
                                "id": "crashing-kubernetes-workload-init-container",
                                "args": {
                                    "configMapName": "features",
                                    "kubernetesObject": {
                                        "apiVersion": "apps/v1",
                                        "kind": "Deployment",
                                        "metadata": {
                                            "name": "recommendation",
                                            "namespace": "otel-demo"
                                        }
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
        }
        mock_yaml_load.return_value = spec_data

        mock_runner = Mock(status="successful")
        mock_run_async.return_value = (None, mock_runner)

        inject_scenario_faults.main()

        # Verify the complete flow executed
        mock_yaml_load.assert_called_once()
        mock_run_async.assert_called_once()

        # Verify correct ansible parameters
        call_args = mock_run_async.call_args[1]
        self.assertEqual(call_args["playbook"], "manage_faults.yaml")
        self.assertEqual(call_args["ident"], "scenario-1-fault-0")
        self.assertIn("--tags inject_faults", call_args["cmdline"])
        self.assertIn("--extra-vars scenario_id=1", call_args["cmdline"])
        self.assertIn("--extra-vars faults_index=0", call_args["cmdline"])


if __name__ == "__main__":
    unittest.main()
