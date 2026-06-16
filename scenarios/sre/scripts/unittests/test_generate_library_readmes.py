import json
import sys
import unittest

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# Add parent directory to path to import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import generate_library_readmes


class TestHelperFunctions(unittest.TestCase):
    """Test helper functions in generate_library_readmes.py."""

    @patch.object(Path, "write_text")
    def test_write_markdown_file(self, mock_write):
        """Test that write_markdown_file writes content."""
        file_path = Path("/test/output/README.md")
        content = "# Test README\n\nContent here."

        generate_library_readmes.write_markdown_file(file_path, content)

        # Verify write_text was called with correct content
        mock_write.assert_called_once_with(content, encoding="utf-8")


class TestLoadLibraryIndexes(unittest.TestCase):
    """Test loading library indexes."""

    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_library_indexes(self, mock_glob, mock_read):
        """Test loading library indexes from directory."""
        index_directory = Path("/test/indexes/applications")

        # Mock index files
        index_files = [
            Path("book-info.json"),
            Path("opentelemetry-demo.json")
        ]
        mock_glob.return_value = index_files

        # Mock index data
        indexes_data = [
            {"id": "book-info", "index": 1, "name": "Book Info"},
            {"id": "opentelemetry-demo", "index": 2, "name": "OpenTelemetry Demo"}
        ]

        mock_read.side_effect = [json.dumps(data) for data in indexes_data]

        result = generate_library_readmes.load_library_indexes(index_directory)

        # Verify correct number of indexes loaded
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0]["id"], "book-info")
        self.assertEqual(result[1]["id"], "opentelemetry-demo")

    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_library_indexes_empty_directory(self, mock_glob, mock_read):
        """Test loading from empty directory."""
        index_directory = Path("/test/indexes/empty")

        mock_glob.return_value = []

        result = generate_library_readmes.load_library_indexes(index_directory)

        self.assertEqual(len(result), 0)


class TestCreateLibraryReadme(unittest.TestCase):
    """Test creating library README files."""

    @patch("generate_library_readmes.write_markdown_file")
    def test_create_library_readme(self, mock_write):
        """Test creating a library README."""
        documentation_directory = Path("/test/docs/applications")

        indexes = [
            {"id": "app1", "index": 1, "name": "App 1"},
            {"id": "app2", "index": 2, "name": "App 2"}
        ]

        mock_template = Mock()
        mock_template.render.return_value = "# Applications\n\n- App 1\n- App 2"

        mock_env = Mock()
        mock_env.get_template.return_value = mock_template

        generate_library_readmes.create_library_readme(
            "applications",
            documentation_directory,
            mock_env,
            indexes
        )

        # Verify template was loaded and rendered
        mock_env.get_template.assert_called_once_with("applications/README.md.j2")
        mock_template.render.assert_called_once()

        # Verify render was called with correct context
        render_args = mock_template.render.call_args[0][0]
        self.assertIn("applications", render_args)
        self.assertEqual(render_args["applications"], indexes)

        # Verify output file was written
        mock_write.assert_called_once()
        output_path = mock_write.call_args[0][0]
        self.assertEqual(output_path, documentation_directory / "README.md")


class TestCreateApplicationsDocumentation(unittest.TestCase):
    """Test creating applications documentation."""

    @patch("generate_library_readmes.write_markdown_file")
    @patch("generate_library_readmes.create_library_readme")
    def test_create_applications_documentation(self, mock_create_readme, mock_write):
        """Test creating complete applications documentation."""
        documentation_directory = Path("/test/docs/applications")

        indexes = [
            {
                "id": "book-info",
                "index": 1,
                "name": "Book Info",
                "platforms": ["kubernetes"]
            }
        ]

        mock_template = Mock()
        mock_template.render.return_value = "# Book Info\n\nApplication documentation"

        mock_env = Mock()
        mock_env.get_template.return_value = mock_template

        generate_library_readmes.create_applications_documentation(
            documentation_directory,
            mock_env,
            indexes
        )

        # Verify README was created
        mock_create_readme.assert_called_once()

        # Verify individual documentation was written
        mock_write.assert_called_once()
        output_path = mock_write.call_args[0][0]
        self.assertEqual(output_path, documentation_directory / "book-info.md")


class TestCreateFaultsDocumentation(unittest.TestCase):
    """Test creating faults documentation."""

    @patch("generate_library_readmes.write_markdown_file")
    @patch("generate_library_readmes.create_library_readme")
    def test_create_faults_documentation(self, mock_create_readme, mock_write):
        """Test creating complete faults documentation."""
        documentation_directory = Path("/test/docs/faults")

        indexes = [
            {
                "id": "test-fault",
                "index": 1,
                "name": "Test Fault",
                "platform": "kubernetes",
                "tags": ["networking"]
            }
        ]

        mock_template = Mock()
        mock_template.render.return_value = "# Test Fault\n\nFault documentation"

        mock_env = Mock()
        mock_env.get_template.return_value = mock_template

        generate_library_readmes.create_faults_documentation(
            documentation_directory,
            mock_env,
            indexes
        )

        # Verify README was created
        mock_create_readme.assert_called_once()

        # Verify individual documentation was written
        mock_write.assert_called_once()

        # Verify template render included implementation_file_path
        render_kwargs = mock_template.render.call_args[0][0]
        self.assertIn("implementation_file_path", render_kwargs)


class TestCreateWaitersDocumentation(unittest.TestCase):
    """Test creating waiters documentation."""

    @patch("generate_library_readmes.write_markdown_file")
    @patch("generate_library_readmes.create_library_readme")
    def test_create_waiters_documentation(self, mock_create_readme, mock_write):
        """Test creating complete waiters documentation."""
        documentation_directory = Path("/test/docs/waiters")

        indexes = [
            {
                "id": "pause-execution",
                "index": 1,
                "name": "Pause Execution"
            }
        ]

        mock_template = Mock()
        mock_template.render.return_value = "# Pause Execution\n\nWaiter documentation"

        mock_env = Mock()
        mock_env.get_template.return_value = mock_template

        generate_library_readmes.create_waiters_documentation(
            documentation_directory,
            mock_env,
            indexes
        )

        # Verify README was created
        mock_create_readme.assert_called_once()

        # Verify individual documentation was written
        mock_write.assert_called_once()


class TestCreateScenariosStatistics(unittest.TestCase):
    """Test creating scenarios statistics."""

    @patch("generate_library_readmes.write_markdown_file")
    def test_create_scenarios_statistics(self, mock_write):
        """Test creating scenarios statistics."""
        documentation_directory = Path("/test/docs/scenarios")

        scenarios = [
            {
                "id": "1",
                "category": "sre",
                "complexity": "low",
                "environment": {
                    "applications": [{"id": "book-info"}]
                }
            },
            {
                "id": "2",
                "category": "sre",
                "complexity": "medium",
                "environment": {
                    "applications": [{"id": "opentelemetry-demo"}]
                }
            },
            {
                "id": "3",
                "category": "finops",
                "complexity": "high",
                "environment": {
                    "applications": [{"id": "book-info"}]
                }
            }
        ]

        mock_template = Mock()
        mock_template.render.return_value = "# Statistics\n\nScenario statistics"

        mock_env = Mock()
        mock_env.get_template.return_value = mock_template

        generate_library_readmes.create_scenarios_statistics(
            documentation_directory,
            mock_env,
            scenarios
        )

        # Verify template was rendered
        mock_template.render.assert_called_once()

        # Verify statistics were calculated correctly
        render_kwargs = mock_template.render.call_args[1]
        statistics = render_kwargs["statistics"]

        self.assertEqual(statistics["application"]["book_info"], 2)
        self.assertEqual(statistics["application"]["otel_demo"], 1)
        self.assertEqual(statistics["category"]["sre"], 2)
        self.assertEqual(statistics["category"]["finops"], 1)
        self.assertEqual(statistics["complexity"]["low"], 1)
        self.assertEqual(statistics["complexity"]["medium"], 1)
        self.assertEqual(statistics["complexity"]["high"], 1)

        # Verify output file was written
        mock_write.assert_called_once()
        output_path = mock_write.call_args[0][0]
        self.assertEqual(output_path, documentation_directory / "statistics.md")


class TestCreateScenariosDocumentation(unittest.TestCase):
    """Test creating scenarios documentation."""

    @patch("generate_library_readmes.write_markdown_file")
    @patch("generate_library_readmes.create_scenarios_statistics")
    @patch("generate_library_readmes.create_library_readme")
    def test_create_scenarios_documentation(self, mock_create_readme, mock_create_stats, mock_write):
        """Test creating complete scenarios documentation with cross-references."""
        index_directory = Path("/test/indexes")
        documentation_directory = Path("/test/docs/scenarios")

        scenarios_indexes = [
            {
                "id": "1",
                "index": 1,
                "name": "Scenario 1",
                "category": "sre",
                "platforms": ["kubernetes"],
                "tags": ["networking"],
                "environment": {"applications": [{"id": "book-info"}]},
                "disruptions": [{"injections": [{"id": "test-fault"}]}],
                "solutions": []
            }
        ]

        application_indexes = [
            {"id": "book-info", "name": "Book Info"}
        ]

        faults_indexes = [
            {"id": "test-fault", "name": "Test Fault"}
        ]

        mock_template = Mock()
        mock_template.render.return_value = "# Scenario 1\n\nScenario documentation"

        mock_env = Mock()
        mock_env.get_template.return_value = mock_template

        generate_library_readmes.create_scenarios_documentation(
            index_directory,
            documentation_directory,
            mock_env,
            scenarios_indexes,
            application_indexes,
            faults_indexes
        )

        # Verify README was created
        mock_create_readme.assert_called_once()

        # Verify statistics were created
        mock_create_stats.assert_called_once()

        # Verify individual documentation was written
        mock_write.assert_called_once()

        # Verify output path includes category subdirectory
        output_path = mock_write.call_args[0][0]
        self.assertEqual(output_path, documentation_directory / "sre" / "1.md")

        # Verify template render included cross-reference lookups
        render_kwargs = mock_template.render.call_args[0][0]
        self.assertIn("applications", render_kwargs)
        self.assertIn("faults", render_kwargs)
        self.assertIn("book-info", render_kwargs["applications"])
        self.assertIn("test-fault", render_kwargs["faults"])


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("generate_library_readmes.create_scenarios_documentation")
    @patch("generate_library_readmes.create_waiters_documentation")
    @patch("generate_library_readmes.create_faults_documentation")
    @patch("generate_library_readmes.create_applications_documentation")
    @patch("generate_library_readmes.load_library_indexes")
    @patch("sys.argv", ["script.py",
                        "--templates_directory", "/test/templates",
                        "--library_index_directory", "/test/indexes",
                        "--documentation_directory", "/test/docs"])
    def test_main(self, mock_load, mock_apps, mock_faults, mock_waiters, mock_scenarios):
        """Test main function orchestration."""
        # Mock load_library_indexes to return different data for each call
        # IMPORTANT: All indexes must have "name" field for sorting
        mock_load.side_effect = [
            [{"id": "app1", "name": "App 1"}],  # applications
            [{"id": "fault1", "name": "Fault 1"}],  # faults
            [{"id": "waiter1", "name": "Waiter 1"}],  # waiters
            [{"id": "scenario1", "name": "Scenario 1"}]  # scenarios
        ]

        with patch("generate_library_readmes.Environment"):
            generate_library_readmes.main()

        # Verify all indexes were loaded
        self.assertEqual(mock_load.call_count, 4)

        # Verify all documentation functions were called
        mock_apps.assert_called_once()
        mock_faults.assert_called_once()
        mock_waiters.assert_called_once()
        mock_scenarios.assert_called_once()


if __name__ == "__main__":
    unittest.main()
