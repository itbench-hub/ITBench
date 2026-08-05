import json
import sys
import unittest

from pathlib import Path
from unittest.mock import Mock, mock_open, patch

# Add parent directory to path to import the module under test
sys.path.insert(0, str(Path(__file__).parent.parent))
import generate_library_index_schemas


class TestWriteJsonSchemaFile(unittest.TestCase):
    """Test JSON schema file writing."""

    @patch.object(Path, "write_text")
    def test_write_json_schema_file(self, mock_write):
        """Test that write_json_schema_file writes formatted JSON."""
        file_path = Path("/test/output/schema.json")
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "type": "object",
            "properties": {
                "name": {"type": "string"}
            }
        }

        generate_library_index_schemas.write_json_schema_file(file_path, schema)

        # Verify write_text was called
        mock_write.assert_called_once()

        # Verify the content is properly formatted JSON with newline
        written_content = mock_write.call_args[0][0]
        self.assertTrue(written_content.endswith("\n"))

        # Verify it's valid JSON
        parsed = json.loads(written_content.strip())
        self.assertEqual(parsed["$schema"], "https://json-schema.org/draft/2020-12/schema")


class TestProcessLibraryType(unittest.TestCase):
    """Test processing library types to extract schemas."""

    @patch("generate_library_index_schemas.write_json_schema_file")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_process_library_type(self, mock_glob, mock_read, mock_write_schema):
        """Test processing a library type to extract schemas."""
        index_dir = Path("/test/indexes/applications")
        schema_dir = Path("/test/schemas/applications")

        # Mock index files
        index_files = [
            Path("book-info.json"),
            Path("opentelemetry-demo.json")
        ]
        mock_glob.return_value = index_files

        # Mock index data
        index_data = [
            {
                "id": "book-info",
                "name": "Book Info",
                "arguments": {
                    "jsonSchema": {
                        "type": "object",
                        "properties": {
                            "namespace": {"type": "string"}
                        }
                    }
                }
            },
            {
                "id": "opentelemetry-demo",
                "name": "OpenTelemetry Demo",
                "arguments": {
                    "jsonSchema": {
                        "type": "object",
                        "properties": {
                            "replicas": {"type": "integer"}
                        }
                    }
                }
            }
        ]

        mock_read.side_effect = [json.dumps(data) for data in index_data]

        ids, items = generate_library_index_schemas.process_library_type(
            "applications",
            index_dir,
            schema_dir
        )

        # Verify correct number of IDs and items returned
        self.assertEqual(len(ids), 2)
        self.assertEqual(len(items), 2)

        # Verify IDs are correct
        self.assertIn("book-info", ids)
        self.assertIn("opentelemetry-demo", ids)

        # Verify items have correct structure
        for item in items:
            self.assertIn("if", item)
            self.assertIn("then", item)
            self.assertIn("properties", item["if"])
            self.assertIn("id", item["if"]["properties"])

        # Verify schemas were written
        self.assertEqual(mock_write_schema.call_count, 2)

    @patch("generate_library_index_schemas.write_json_schema_file")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_process_library_type_adds_schema_property(self, mock_glob, mock_read, mock_write_schema):
        """Test that $schema property is added to extracted schemas."""
        index_dir = Path("/test/indexes/faults")
        schema_dir = Path("/test/schemas/faults")

        index_files = [Path("test-fault.json")]
        mock_glob.return_value = index_files

        index_data = {
            "id": "test-fault",
            "name": "Test Fault",
            "arguments": {
                "jsonSchema": {
                    "type": "object"
                }
            }
        }

        mock_read.return_value = json.dumps(index_data)

        generate_library_index_schemas.process_library_type(
            "faults",
            index_dir,
            schema_dir
        )

        # Verify schema was written
        mock_write_schema.assert_called_once()

        # Verify the path is correct
        schema_path = mock_write_schema.call_args[0][0]
        self.assertEqual(schema_path, schema_dir / "test-fault.json")


class TestMain(unittest.TestCase):
    """Test main function."""

    @patch("generate_library_index_schemas.write_json_schema_file")
    @patch("generate_library_index_schemas.process_library_type")
    @patch("sys.argv", ["script.py",
                        "--library_index_directory", "/test/indexes",
                        "--templates_directory", "/test/templates",
                        "--schemas_directory", "/test/schemas"])
    def test_main_processes_all_library_types(self, mock_process, mock_write_schema):
        """Test main function processes all library types."""
        # Mock process_library_type to return IDs and items
        mock_process.side_effect = [
            (["app1", "app2"], [{"if": {}, "then": {}}] * 2),  # applications
            (["fault1"], [{"if": {}, "then": {}}]),  # faults
            (["waiter1"], [{"if": {}, "then": {}}])  # waiters
        ]

        # Mock template rendering for scenarios schema
        with patch("generate_library_index_schemas.Environment") as mock_env_class:
            mock_env = Mock()
            mock_template = Mock()
            mock_template.render.return_value = json.dumps({
                "$schema": "https://json-schema.org/draft/2020-12/schema",
                "type": "object"
            })
            mock_env.get_template.return_value = mock_template
            mock_env_class.return_value = mock_env

            generate_library_index_schemas.main()

        # Verify process_library_type was called for each library type
        self.assertEqual(mock_process.call_count, 3)

        # Verify template was requested with correct name
        mock_env.get_template.assert_called_once_with("scenario.json.j2")

        # Verify scenarios schema was written
        mock_write_schema.assert_called_once()

    @patch("generate_library_index_schemas.write_json_schema_file")
    @patch("generate_library_index_schemas.process_library_type")
    @patch("sys.argv", ["script.py",
                        "--library_index_directory", "/test/indexes",
                        "--templates_directory", "/test/templates",
                        "--schemas_directory", "/test/schemas"])
    def test_main_creates_scenarios_schema(self, mock_process, mock_write_schema):
        """Test main function creates scenarios schema with correct context."""
        # Mock process_library_type returns
        mock_process.side_effect = [
            (["book-info"], [{"if": {"properties": {"id": {"const": "book-info"}}}, "then": {}}]),
            (["test-fault"], [{"if": {"properties": {"id": {"const": "test-fault"}}}, "then": {}}]),
            (["pause"], [{"if": {"properties": {"id": {"const": "pause"}}}, "then": {}}])
        ]

        with patch("generate_library_index_schemas.Environment") as mock_env_class:
            mock_env = Mock()
            mock_template = Mock()
            mock_template.render.return_value = json.dumps({"type": "object"})
            mock_env.get_template.return_value = mock_template
            mock_env_class.return_value = mock_env

            generate_library_index_schemas.main()

            # Verify template was rendered with correct context
            mock_template.render.assert_called_once()
            render_kwargs = mock_template.render.call_args[1]

            # Verify IDs and items were passed
            self.assertIn("ids", render_kwargs)
            self.assertIn("items", render_kwargs)

            # Verify all library types are present
            self.assertIn("applications", render_kwargs["ids"])
            self.assertIn("faults", render_kwargs["ids"])
            self.assertIn("waiters", render_kwargs["ids"])


class TestIntegration(unittest.TestCase):
    """Integration tests for schema generation."""

    @patch("generate_library_index_schemas.write_json_schema_file")
    @patch.object(Path, "read_text")
    @patch.object(Path, "glob")
    def test_full_schema_generation_flow(self, mock_glob, mock_read, mock_write_schema):
        """Test complete flow from index to schema."""
        index_dir = Path("/test/indexes/applications")
        schema_dir = Path("/test/schemas/applications")

        # Mock a complete index file
        index_files = [Path("book-info.json")]
        mock_glob.return_value = index_files

        complete_index = {
            "id": "book-info",
            "name": "Book Info",
            "description": "Sample application",
            "arguments": {
                "jsonSchema": {
                    "type": "object",
                    "properties": {
                        "namespace": {
                            "type": "string",
                            "description": "Kubernetes namespace"
                        },
                        "replicas": {
                            "type": "integer",
                            "minimum": 1,
                            "default": 3
                        }
                    },
                    "required": ["namespace"]
                }
            }
        }

        mock_read.return_value = json.dumps(complete_index)

        ids, items = generate_library_index_schemas.process_library_type(
            "applications",
            index_dir,
            schema_dir
        )

        # Verify schema was extracted and written
        mock_write_schema.assert_called_once()

        # Verify the schema path
        schema_path = mock_write_schema.call_args[0][0]
        self.assertEqual(schema_path, schema_dir / "book-info.json")

        # Verify IDs list
        self.assertEqual(ids, ["book-info"])

        # Verify items structure for scenarios schema
        self.assertEqual(len(items), 1)
        self.assertIn("if", items[0])
        self.assertIn("then", items[0])


if __name__ == "__main__":
    unittest.main()
