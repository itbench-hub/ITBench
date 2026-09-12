"""
Tests for validate_indexes.py
"""
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from jsonschema.exceptions import ValidationError

import validate_indexes


def test_raises_on_validation_failure():
    """load_and_validate_library_index raises ValidationError when a schema validation fails."""
    mock_registry = Mock()
    index_dir = Path("/lib/indexes/applications")
    schema_file = Path("/schemas/json/library/index/application.json")

    mock_validator = Mock()
    mock_validator.validate.side_effect = ValidationError("missing field")

    with patch("validate_indexes.Draft202012Validator", return_value=mock_validator), \
         patch.object(Path, "glob", return_value=[Path("book-info.json")]), \
         patch.object(Path, "read_text", return_value='{"id": "book-info"}'), \
         pytest.raises(ValidationError):
        validate_indexes.load_and_validate_library_index(mock_registry, index_dir, schema_file)
