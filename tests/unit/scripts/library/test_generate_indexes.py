"""
Tests for generate_indexes.py

Makefile invocation:
  scripts/library/generate_indexes.py
    --templates_directory=<path>
    --library_index_directory=<path>
    --playbooks_directory=<path>
"""
from pathlib import Path
from unittest.mock import patch

import generate_indexes


ARGV = [
    "generate_indexes.py",
    "--templates_directory", "/templates/library/indexes",
    "--library_index_directory", "/lib/indexes",
    "--playbooks_directory", "/scenarios/sre/project",
]


def _patched_main():
    with patch("sys.argv", ARGV), \
         patch("generate_indexes.load_and_write_library_index", return_value={}) as mock_load, \
         patch("generate_indexes.create_scenarios_indexes") as mock_scenarios:
        generate_indexes.main()
        return mock_load, mock_scenarios


def test_arguments():
    """main() accepts the argument names the Makefile passes."""
    mock_load, mock_scenarios = _patched_main()
    assert mock_load.call_count == 3
    assert mock_scenarios.call_count == 1


def test_library_types():
    """main() processes applications, faults, and waiters."""
    mock_load, _ = _patched_main()
    called_types = [c.args[0] for c in mock_load.call_args_list]
    assert called_types == ["applications", "faults", "waiters"]


def test_subdirectories():
    """main() passes the correct template and index subdirectories for each library type."""
    mock_load, _ = _patched_main()
    for call, lib_type in zip(mock_load.call_args_list, ["applications", "faults", "waiters"]):
        lib_type_arg, templates_dir, index_dir, _ = call.args
        assert lib_type_arg == lib_type
        assert templates_dir == Path("/templates/library/indexes") / lib_type
        assert index_dir == Path("/lib/indexes") / lib_type


def test_faults_passed_to_scenarios():
    """main() passes the faults lookup from load_and_write_library_index into create_scenarios_indexes."""
    faults_cache = {"test-fault": {"id": "test-fault"}}
    with patch("sys.argv", ARGV), \
         patch("generate_indexes.load_and_write_library_index", side_effect=[{}, faults_cache, {}]), \
         patch("generate_indexes.create_scenarios_indexes") as mock_scenarios:
        generate_indexes.main()

    passed_faults = mock_scenarios.call_args.args[4]
    assert passed_faults == faults_cache
