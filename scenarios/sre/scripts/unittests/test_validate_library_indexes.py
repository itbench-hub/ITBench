import json
import sys
import unittest

from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent directory to path to import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import validate_library_indexes


class TestLoadAndValidateLibraryIndex(unittest.TestCase):
    """Test loading and validating library indexes."""

    @patch("builtins.print")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_and_validate_library_index_success(self, mock_glob, mock_read, mock_print):
        """Test successful validation of library indexes."""
        index_directory = Path("/test/indexes/applications")
        schema_file = Path("/test/schemas/library/index/application.json")

        # Mock index files
        index_files = [Path("book-info.json")]
        mock_glob.return_value = index_files

        # Mock index data
        index_data = {
            "id": "book-info",
            "name": "Book Info",
            "description": "Test application"
        }
        mock_read.return_value = json.dumps(index_data)

        # Mock registry and validator
        mock_registry = Mock()
        mock_validator = Mock()
        mock_validator.validate = Mock()  # No exception means validation passes

        with patch("validate_library_indexes.Draft202012Validator", return_value=mock_validator):
            validate_library_indexes.load_and_validate_library_index(
                mock_registry,
                index_directory,
                schema_file
            )

        # Verify validator was called
        mock_validator.validate.assert_called_once_with(index_data)

        # Verify success message was printed
        mock_print.assert_called_with("Success: The local object matches the local schema copy perfectly!")

    @patch("builtins.print")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_and_validate_library_index_validation_error(self, mock_glob, mock_read, mock_print):
        """Test validation failure with ValidationError."""
        from jsonschema.exceptions import ValidationError

        index_directory = Path("/test/indexes/faults")
        schema_file = Path("/test/schemas/library/index/fault.json")

        # Mock index files
        index_files = [Path("test-fault.json")]
        mock_glob.return_value = index_files

        # Mock invalid index data
        index_data = {
            "id": "test-fault",
            # Missing required fields
        }
        mock_read.return_value = json.dumps(index_data)

        # Mock registry and validator that raises ValidationError
        mock_registry = Mock()
        mock_validator = Mock()
        validation_error = ValidationError("'name' is a required property")
        mock_validator.validate = Mock(side_effect=validation_error)

        with patch("validate_library_indexes.Draft202012Validator", return_value=mock_validator):
            validate_library_indexes.load_and_validate_library_index(
                mock_registry,
                index_directory,
                schema_file
            )

        # Verify error message was printed
        mock_print.assert_called_with("Validation failed: 'name' is a required property")

    @patch("builtins.print")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_load_and_validate_library_index_multiple_files(self, mock_glob, mock_read, mock_print):
        """Test validation of multiple index files."""
        index_directory = Path("/test/indexes/waiters")
        schema_file = Path("/test/schemas/library/index/waiter.json")

        # Mock multiple index files
        index_files = [
            Path("pause-execution.json"),
            Path("restart-workload.json"),
            Path("scale-workload.json")
        ]
        mock_glob.return_value = index_files

        # Mock index data for each file
        indexes_data = [
            {"id": "pause-execution", "name": "Pause Execution"},
            {"id": "restart-workload", "name": "Restart Workload"},
            {"id": "scale-workload", "name": "Scale Workload"}
        ]
        mock_read.side_effect = [json.dumps(data) for data in indexes_data]

        # Mock registry and validator
        mock_registry = Mock()
        mock_validator = Mock()
        mock_validator.validate = Mock()

        with patch("validate_library_indexes.Draft202012Validator", return_value=mock_validator):
            validate_library_indexes.load_and_validate_library_index(
                mock_registry,
                index_directory,
                schema_file
            )

        # Verify validator was called for each index
        self.assertEqual(mock_validator.validate.call_count, 3)

        # Verify success message was printed for each
        self.assertEqual(mock_print.call_count, 3)


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("validate_library_indexes.load_and_validate_library_index")
    @patch.object(Path, "read_text")
    @patch.object(Path, "rglob")
    @patch("sys.argv", ["script.py",
                        "--library_index_directory", "/test/indexes",
                        "--schemas_directory", "/test/schemas"])
    def test_main_builds_registry(self, mock_rglob, mock_read, mock_validate):
        """Test main function builds schema registry."""
        # Mock schema files
        schema_files = [
            Path("/test/schemas/applications/book-info.json"),
            Path("/test/schemas/faults/test-fault.json"),
            Path("/test/schemas/library/index/application.json"),
            Path("/test/schemas/library/index/fault.json"),
            Path("/test/schemas/library/index/scenario.json"),
            Path("/test/schemas/library/index/waiter.json")
        ]
        mock_rglob.return_value = schema_files

        # Mock schema content
        schema_data = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object"
        }
        mock_read.return_value = json.dumps(schema_data)

        with patch("validate_library_indexes.Registry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.with_resource = Mock(return_value=mock_registry)
            mock_registry_class.return_value = mock_registry

            with patch("validate_library_indexes.Resource"):
                validate_library_indexes.main()

        # Verify registry was created
        mock_registry_class.assert_called_once()

        # Verify schemas were added to registry
        self.assertEqual(mock_registry.with_resource.call_count, len(schema_files))

        # Verify validation was called for each library type
        self.assertEqual(mock_validate.call_count, 4)  # applications, faults, scenarios, waiters

    @patch("validate_library_indexes.load_and_validate_library_index")
    @patch.object(Path, "read_text")
    @patch.object(Path, "rglob")
    @patch("sys.argv", ["script.py",
                        "--library_index_directory", "/test/indexes",
                        "--schemas_directory", "/test/schemas"])
    def test_main_validates_all_library_types(self, mock_rglob, mock_read, mock_validate):
        """Test main function validates all library types."""
        # Mock schema files
        mock_rglob.return_value = [Path("/test/schemas/test.json")]
        mock_read.return_value = json.dumps({"type": "object"})

        with patch("validate_library_indexes.Registry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.with_resource = Mock(return_value=mock_registry)
            mock_registry_class.return_value = mock_registry

            with patch("validate_library_indexes.Resource"):
                validate_library_indexes.main()

        # Verify validation was called for each library type
        self.assertEqual(mock_validate.call_count, 4)

        # Verify correct schema file names were used
        call_args_list = mock_validate.call_args_list

        # Extract schema file paths from calls
        schema_paths = [call[0][2] for call in call_args_list]

        # Verify schema file names
        schema_names = [path.name for path in schema_paths]
        self.assertIn("application.json", schema_names)
        self.assertIn("fault.json", schema_names)
        self.assertIn("scenario.json", schema_names)
        self.assertIn("waiter.json", schema_names)

    @patch("validate_library_indexes.load_and_validate_library_index")
    @patch.object(Path, "read_text")
    @patch.object(Path, "rglob")
    @patch("sys.argv", ["script.py",
                        "--library_index_directory", "/test/indexes",
                        "--schemas_directory", "/test/schemas"])
    def test_main_handles_schema_file_name_conversion(self, mock_rglob, mock_read, mock_validate):
        """Test main function correctly converts library type names to schema file names."""
        mock_rglob.return_value = []

        with patch("validate_library_indexes.Registry") as mock_registry_class:
            mock_registry = Mock()
            mock_registry.with_resource = Mock(return_value=mock_registry)
            mock_registry_class.return_value = mock_registry

            with patch("validate_library_indexes.Resource"):
                validate_library_indexes.main()

        # Verify schema file names are singular (removesuffix("s"))
        call_args_list = mock_validate.call_args_list
        schema_paths = [call[0][2] for call in call_args_list]

        for path in schema_paths:
            # Schema file names should be singular
            self.assertNotIn("applications.json", str(path))
            self.assertNotIn("faults.json", str(path))
            self.assertNotIn("waiters.json", str(path))


class TestIntegration(unittest.TestCase):
    """Integration tests for validation."""

    @patch("builtins.print")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_full_validation_flow(self, mock_glob, mock_read, mock_print):
        """Test complete validation flow from index to schema."""
        from jsonschema.exceptions import ValidationError

        index_directory = Path("/test/indexes/scenarios")
        schema_file = Path("/test/schemas/library/index/scenario.json")

        # Mock scenario index files
        index_files = [
            Path("1.json"),
            Path("2.json")
        ]
        mock_glob.return_value = index_files

        # Mock one valid and one invalid index
        valid_index = {
            "id": "1",
            "name": "Valid Scenario",
            "description": "A valid scenario",
            "category": "sre",
            "complexity": "low"
        }
        invalid_index = {
            "id": "2",
            # Missing required 'name' field
            "description": "Invalid scenario"
        }

        mock_read.side_effect = [
            json.dumps(valid_index),
            json.dumps(invalid_index)
        ]

        # Mock registry and validator
        mock_registry = Mock()
        mock_validator = Mock()

        # First call succeeds, second raises ValidationError
        validation_error = ValidationError("'name' is a required property")
        mock_validator.validate = Mock(side_effect=[None, validation_error])

        with patch("validate_library_indexes.Draft202012Validator", return_value=mock_validator):
            validate_library_indexes.load_and_validate_library_index(
                mock_registry,
                index_directory,
                schema_file
            )

        # Verify both indexes were validated
        self.assertEqual(mock_validator.validate.call_count, 2)

        # Verify both success and failure messages were printed
        self.assertEqual(mock_print.call_count, 2)

        # Check for success message
        success_calls = [call for call in mock_print.call_args_list
                        if "Success" in str(call)]
        self.assertEqual(len(success_calls), 1)

        # Check for failure message
        failure_calls = [call for call in mock_print.call_args_list
                        if "Validation failed" in str(call)]
        self.assertEqual(len(failure_calls), 1)


if __name__ == "__main__":
    unittest.main()
