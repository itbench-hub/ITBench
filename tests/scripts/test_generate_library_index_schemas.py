"""
Tests for generate_library_index_schemas.py

Makefile invocation:
  scripts/generate_library_index_schemas.py
    --library_index_directory=<path>
    --schemas_directory=<path>
    --templates_directory=<path>
"""
import json
from pathlib import Path
from unittest.mock import Mock, patch

import generate_library_index_schemas


ARGV = [
    "generate_library_index_schemas.py",
    "--library_index_directory", "/lib/indexes",
    "--schemas_directory", "/schemas/json",
    "--templates_directory", "/templates/schemas/json/library/index",
]


def _patched_main():
    """Run main() with standard Makefile args, mocking I/O."""
    with patch("sys.argv", ARGV), \
         patch("generate_library_index_schemas.process_library_type", return_value=([], [])) as mock_process, \
         patch("generate_library_index_schemas.Environment") as mock_env_cls:
        mock_env_cls.return_value.get_template.return_value.render.return_value = json.dumps({"type": "object"})
        generate_library_index_schemas.main()
        return mock_process, mock_env_cls.return_value


def test_arguments():
    """main() accepts the argument names the Makefile passes."""
    mock_process, _ = _patched_main()
    assert mock_process.call_count == 3


def test_library_types():
    """main() processes applications, faults, and waiters — in that order."""
    mock_process, _ = _patched_main()
    called_types = [c.args[0] for c in mock_process.call_args_list]
    assert called_types == ["applications", "faults", "waiters"]


def test_subdirectories():
    """main() passes the correct index and schema subdirectories for each library type."""
    mock_process, _ = _patched_main()
    for call, lib_type in zip(mock_process.call_args_list, ["applications", "faults", "waiters"]):
        _, index_dir, schema_dir = call.args
        assert index_dir == Path("/lib/indexes") / lib_type
        assert schema_dir == Path("/schemas/json") / lib_type


def test_scenario_schema_written():
    """main() renders scenario.json.j2 and writes it to schemas/library/index/scenario.json."""
    with patch("sys.argv", ARGV), \
         patch("generate_library_index_schemas.process_library_type", return_value=(["an-id"], [{}])), \
         patch("generate_library_index_schemas.write_json_schema_file") as mock_write, \
         patch("generate_library_index_schemas.Environment") as mock_env_cls:
        mock_env_cls.return_value.get_template.return_value.render.return_value = json.dumps({"type": "object"})
        generate_library_index_schemas.main()

    mock_env_cls.return_value.get_template.assert_called_once_with("scenario.json.j2")
    mock_write.assert_called_once()
    assert mock_write.call_args.args[0] == Path("/schemas/json/library/index/scenario.json")
