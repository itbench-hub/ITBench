import json
import sys
import unittest

from pathlib import Path
from unittest.mock import Mock, mock_open, patch, MagicMock

# Add parent directory to path to import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import generate_library_indexes


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions in generate_library_indexes.py."""

    def test_extract_index_from_filename(self):
        """Test extracting numeric index from filename."""
        self.assertEqual(generate_library_indexes.extract_index_from_filename("1.json.j2"), 1)
        self.assertEqual(generate_library_indexes.extract_index_from_filename("42.json.j2"), 42)
        self.assertEqual(generate_library_indexes.extract_index_from_filename("105.json.j2"), 105)

    def test_generate_id_from_name(self):
        """Test ID generation from name."""
        self.assertEqual(
            generate_library_indexes.generate_id_from_name("Book Info"),
            "book-info"
        )
        self.assertEqual(
            generate_library_indexes.generate_id_from_name("OpenTelemetry Demo"),
            "opentelemetry-demo"
        )
        self.assertEqual(
            generate_library_indexes.generate_id_from_name("Crashing Kubernetes Workload Init Container"),
            "crashing-kubernetes-workload-init-container"
        )


class TestLoadManagers(unittest.TestCase):
    """Test manager loading functionality."""

    def test_load_managers(self):
        """Test loading managers from YAML files."""
        applications_path = Path("/test/applications/managers.yaml")
        tools_path = Path("/test/tools/managers.yaml")

        # Mock YAML content
        applications_data = {
            "applications_managers": {
                "book_info": {"version": "1.0"},
                "otel_demo": {"version": "2.0"}
            }
        }
        tools_data = {
            "tools_managers": {
                "prometheus": {"version": "3.0"},
                "grafana": {"version": "4.0"}
            }
        }

        with patch.object(Path, "read_text") as mock_read:
            mock_read.side_effect = [
                "applications_managers:\n  book_info:\n    version: '1.0'\n",
                "tools_managers:\n  prometheus:\n    version: '3.0'\n"
            ]

            with patch("generate_library_indexes.yaml.safe_load") as mock_yaml:
                mock_yaml.side_effect = [applications_data, tools_data]

                result = generate_library_indexes.load_managers(applications_path, tools_path)

        self.assertIn("applications", result)
        self.assertIn("tools", result)
        self.assertEqual(result["applications"], applications_data["applications_managers"])
        self.assertEqual(result["tools"], tools_data["tools_managers"])


class TestWriteJsonFile(unittest.TestCase):
    """Test JSON file writing."""

    @patch.object(Path, "write_text")
    def test_write_json_file(self, mock_write):
        """Test that write_json_file writes formatted JSON."""
        file_path = Path("/test/output/file.json")
        content = {"key": "value", "number": 42}

        generate_library_indexes.write_json_file(file_path, content)

        # Verify write_text was called
        mock_write.assert_called_once()

        # Verify the content is properly formatted JSON with newline
        written_content = mock_write.call_args[0][0]
        self.assertTrue(written_content.endswith("\n"))

        # Verify it's valid JSON
        parsed = json.loads(written_content.strip())
        self.assertEqual(parsed["key"], "value")
        self.assertEqual(parsed["number"], 42)


class TestLoadAndWriteLibraryIndex(unittest.TestCase):
    """Test loading and writing library indexes."""

    @patch("generate_library_indexes.write_json_file")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_and_write_library_index_applications(self, mock_glob, mock_read, mock_write):
        """Test loading and writing application indexes."""
        templates_dir = Path("/test/templates/applications")
        index_dir = Path("/test/indexes/applications")
        generator_dir = Path("/test/generator")

        # Mock template files
        template_files = [
            Path("1.json.j2"),
            Path("2.json.j2")
        ]
        mock_glob.return_value = template_files

        # Mock template content
        mock_read.side_effect = [
            json.dumps({"name": "Book Info", "description": "Test app 1"}),
            json.dumps({"name": "OpenTelemetry Demo", "description": "Test app 2"})
        ]

        result = generate_library_indexes.load_and_write_library_index(
            "applications",
            templates_dir,
            index_dir,
            generator_dir
        )

        # Verify write was called for each index plus consolidated file
        self.assertEqual(mock_write.call_count, 3)

        # For applications, result should be empty dict (only faults return lookup)
        self.assertEqual(result, {})

    @patch("generate_library_indexes.write_json_file")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_and_write_library_index_faults(self, mock_glob, mock_read, mock_write):
        """Test loading and writing fault indexes with lookup dict."""
        templates_dir = Path("/test/templates/faults")
        index_dir = Path("/test/indexes/faults")
        generator_dir = Path("/test/generator")

        # Mock template files
        template_files = [Path("1.json.j2")]
        mock_glob.return_value = template_files

        # Mock template content
        mock_read.return_value = json.dumps({
            "name": "Test Fault",
            "platform": "kubernetes",
            "tags": ["networking"]
        })

        result = generate_library_indexes.load_and_write_library_index(
            "faults",
            templates_dir,
            index_dir,
            generator_dir
        )

        # Verify write was called
        self.assertGreater(mock_write.call_count, 0)

        # For faults, result should contain lookup dict
        self.assertIsInstance(result, dict)
        self.assertIn("test-fault", result)


class TestCreateScenariosIndexes(unittest.TestCase):
    """Test scenario index creation with fault aggregation."""

    @patch("generate_library_indexes.write_json_file")
    @patch("generate_library_indexes.load_managers")
    @patch.object(Path, "glob")
    def test_create_scenarios_indexes(self, mock_glob, mock_load_managers, mock_write):
        """Test creating scenario indexes with fault aggregation."""
        templates_dir = Path("/test/templates/scenarios")
        index_dir = Path("/test/indexes/scenarios")
        playbooks_dir = Path("/test/scenarios/sre")
        generator_dir = Path("/test/generator")

        mock_load_managers.return_value = {
            "applications": {"book_info": {"version": "1.0"}},
            "tools": {"prometheus": {"version": "2.0"}}
        }

        # Mock fault lookup
        faults = {
            "test-fault": {
                "id": "test-fault",
                "name": "Test Fault",
                "platform": "kubernetes",
                "tags": ["networking", "service"],
                "alerts": {
                    "application": ["HighErrorRate"],
                    "goldenSignal": ["LatencyHigh"]
                },
                "solutions": {
                    "templates": [
                        {
                            "command": "kubectl get service {{ args.serviceName }}"
                        }
                    ]
                }
            }
        }

        # Mock scenario template
        scenario_template_content = {
            "name": "Test Scenario",
            "tags": ["troubleshooting"],
            "platforms": ["kubernetes"],
            "disruptions": [
                {
                    "injections": [
                        {
                            "id": "test-fault",
                            "args": {"serviceName": "my-service"}
                        }
                    ]
                }
            ],
            "solutionTemplates": [
                {
                    "disruptionIndex": 0,
                    "injectionIndex": 0
                }
            ]
        }

        # Mock template files
        template_files = [Path("1.json.j2")]
        mock_glob.return_value = template_files

        with patch("generate_library_indexes.Environment") as mock_env_class:
            mock_env = Mock()
            mock_template = Mock()
            mock_template.render.return_value = json.dumps(scenario_template_content)
            mock_env.get_template.return_value = mock_template
            mock_env.from_string.return_value = mock_template
            mock_env_class.return_value = mock_env

            generate_library_indexes.create_scenarios_indexes(
                templates_dir,
                index_dir,
                playbooks_dir,
                generator_dir,
                faults
            )

        # Verify managers were loaded
        mock_load_managers.assert_called_once()

        # Verify write was called (once for individual index, once for consolidated)
        self.assertGreaterEqual(mock_write.call_count, 2)


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("generate_library_indexes.create_scenarios_indexes")
    @patch("generate_library_indexes.load_and_write_library_index")
    @patch("sys.argv", ["script.py",
                        "--templates_directory", "/test/templates",
                        "--library_index_directory", "/test/indexes",
                        "--playbooks_directory", "/test/playbooks"])
    def test_main(self, mock_load_write, mock_create_scenarios):
        """Test main function orchestration."""
        # Mock load_and_write_library_index to return empty dict for apps/waiters, faults dict for faults
        mock_load_write.side_effect = [
            {},  # applications
            {"fault1": {"id": "fault1"}},  # faults
            {}   # waiters
        ]

        generate_library_indexes.main()

        # Verify load_and_write_library_index was called 3 times (apps, faults, waiters)
        self.assertEqual(mock_load_write.call_count, 3)

        # Verify create_scenarios_indexes was called once
        mock_create_scenarios.assert_called_once()


if __name__ == "__main__":
    unittest.main()
