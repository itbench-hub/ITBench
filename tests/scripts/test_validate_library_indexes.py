"""
Tests for validate_library_indexes.py

Makefile invocation:
  scripts/validate_library_indexes.py
    --library_index_directory=<path>
    --schemas_directory=<path>
"""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

import validate_library_indexes


ARGV = [
    "validate_library_indexes.py",
    "--library_index_directory", "/lib/indexes",
    "--schemas_directory", "/schemas/json",
]


def _patched_main():
    with patch("sys.argv", ARGV), \
         patch("validate_library_indexes.load_and_validate_library_index") as mock_validate, \
         patch.object(Path, "rglob", return_value=[]), \
         patch("validate_library_indexes.Registry") as mock_registry_cls:
        mock_registry = Mock()
        mock_registry.with_resource.return_value = mock_registry
        mock_registry_cls.return_value = mock_registry
        validate_library_indexes.main()
        return mock_validate, mock_registry


def test_arguments():
    """main() accepts the argument names the Makefile passes."""
    mock_validate, _ = _patched_main()
    assert mock_validate.call_count == 4


def test_library_types():
    """main() validates applications, faults, scenarios, and waiters."""
    mock_validate, _ = _patched_main()
    called_dirs = [c.args[1] for c in mock_validate.call_args_list]
    assert Path("/lib/indexes/applications") in called_dirs
    assert Path("/lib/indexes/faults") in called_dirs
    assert Path("/lib/indexes/scenarios") in called_dirs
    assert Path("/lib/indexes/waiters") in called_dirs


def test_schema_files():
    """main() uses singular schema file names (application, fault, scenario, waiter)."""
    mock_validate, _ = _patched_main()
    schema_names = [c.args[2].name for c in mock_validate.call_args_list]
    assert "application.json" in schema_names
    assert "fault.json" in schema_names
    assert "scenario.json" in schema_names
    assert "waiter.json" in schema_names


def test_exits_on_validation_failure():
    """load_and_validate_library_index calls sys.exit(1) when a schema validation fails."""
    from jsonschema.exceptions import ValidationError

    mock_registry = Mock()
    index_dir = Path("/lib/indexes/applications")
    schema_file = Path("/schemas/json/library/index/application.json")

    mock_validator = Mock()
    mock_validator.validate.side_effect = ValidationError("missing field")

    with patch("validate_library_indexes.Draft202012Validator", return_value=mock_validator), \
         patch.object(Path, "glob", return_value=[Path("book-info.json")]), \
         patch.object(Path, "read_text", return_value='{"id": "book-info"}'), \
         pytest.raises(SystemExit) as exc:
        validate_library_indexes.load_and_validate_library_index(mock_registry, index_dir, schema_file)

    assert exc.value.code == 1
