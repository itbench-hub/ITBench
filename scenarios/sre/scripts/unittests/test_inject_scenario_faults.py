import os
import sys
import unittest
from unittest.mock import Mock, mock_open, patch

import yaml

# Add parent directory to path to import the module under test
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import inject_scenario_faults


class TestInjectScenarioFaults(unittest.TestCase):
    """Unit tests for inject_scenario_faults.py script."""

    def setUp(self):
        """Set up test fixtures."""
        self.test_project_dir = "/tmp/test_project"

    @patch('inject_scenario_faults.ansible_runner')
    @patch('builtins.open', new_callable=mock_open)
    @patch('inject_scenario_faults.yaml.safe_load')
    def test_single_fault_group(self, mock_yaml_load, mock_file, mock_ansible_runner):
        """Test execution with single fault injection group."""
        # Setup scenario with single fault group
        single_fault_spec = {
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
        mock_yaml_load.return_value = single_fault_spec

        mock_runner = Mock()
        mock_runner.status = "successful"
        mock_ansible_runner.interface.run_async.return_value = (None, mock_runner)

        test_args = [
            'inject_scenario_faults.py',
            '--private_project_directory', self.test_project_dir,
            '--scenario_id', '1'
        ]

        with patch.object(sys, 'argv', test_args):
            inject_scenario_faults.main()

        # Verify ansible_runner.run_async was called exactly once
        self.assertEqual(mock_ansible_runner.interface.run_async.call_count, 1)

        # Verify the call parameters
        call_args = mock_ansible_runner.interface.run_async.call_args_list[0]
        self.assertEqual(call_args[1]['private_data_dir'], self.test_project_dir)
        self.assertEqual(call_args[1]['playbook'], 'manage_faults.yaml')
        self.assertEqual(call_args[1]['ident'], 'scenario-1-fault-0')
        self.assertIn('--tags inject_faults', call_args[1]['cmdline'])
        self.assertIn('--extra-vars scenario_id=1', call_args[1]['cmdline'])
        self.assertIn('--extra-vars faults_index=0', call_args[1]['cmdline'])

    @patch('inject_scenario_faults.ansible_runner')
    @patch('builtins.open', new_callable=mock_open)
    @patch('inject_scenario_faults.yaml.safe_load')
    def test_multiple_fault_groups(self, mock_yaml_load, mock_file, mock_ansible_runner):
        """Test execution with multiple fault injection groups."""
        # Setup scenario with multiple fault groups (like scenario 60)
        multi_fault_spec = {
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
                    },
                    {
                        "injections": [
                            {
                                "id": "unsupported-architecture-kubernetes-workload-container-image",
                                "args": {
                                    "container": {"name": "checkout"},
                                    "kubernetesObject": {
                                        "apiVersion": "apps/v1",
                                        "kind": "Deployment",
                                        "metadata": {
                                            "name": "checkout",
                                            "namespace": "otel-demo"
                                        }
                                    }
                                }
                            }
                        ],
                        "waitFor": {
                            "postInjection": [
                                {
                                    "id": "delete-workload-pods",
                                    "args": {
                                        "kubernetesObject": {
                                            "apiVersion": "apps/v1",
                                            "kind": "Deployment",
                                            "metadata": {
                                                "name": "checkout",
                                                "namespace": "otel-demo"
                                            }
                                        }
                                    }
                                }
                            ]
                        }
                    },
                    {
                        "injections": [
                            {
                                "id": "third-fault-injection",
                                "args": {}
                            }
                        ]
                    }
                ]
            }
        }
        mock_yaml_load.return_value = multi_fault_spec

        # Create mock runners for each fault group
        mock_runners = [Mock(status="successful") for _ in range(3)]
        mock_ansible_runner.interface.run_async.side_effect = [
            (None, runner) for runner in mock_runners
        ]

        test_args = [
            'inject_scenario_faults.py',
            '--private_project_directory', self.test_project_dir,
            '--scenario_id', '60'
        ]

        with patch.object(sys, 'argv', test_args):
            inject_scenario_faults.main()

        # Verify ansible_runner.run_async was called 3 times (one per fault group)
        self.assertEqual(mock_ansible_runner.interface.run_async.call_count, 3)

        # Verify each call has correct parameters
        for i in range(3):
            call_args = mock_ansible_runner.interface.run_async.call_args_list[i]
            self.assertEqual(call_args[1]['private_data_dir'], self.test_project_dir)
            self.assertEqual(call_args[1]['playbook'], 'manage_faults.yaml')
            self.assertEqual(call_args[1]['ident'], f'scenario-60-fault-{i}')
            self.assertIn('--tags inject_faults', call_args[1]['cmdline'])
            self.assertIn('--extra-vars scenario_id=60', call_args[1]['cmdline'])
            self.assertIn(f'--extra-vars faults_index={i}', call_args[1]['cmdline'])


if __name__ == '__main__':
    unittest.main()
