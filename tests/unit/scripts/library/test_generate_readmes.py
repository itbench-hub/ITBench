"""
Tests for generate_readmes.py

Makefile invocation:
  scripts/library/generate_readmes.py
    --templates_directory=<path>
    --library_index_directory=<path>
    --documentation_directory=<path>
"""
from pathlib import Path
from unittest.mock import patch

import generate_readmes


ARGV = [
    "generate_readmes.py",
    "--templates_directory", "/templates/documentation/library",
    "--library_index_directory", "/lib/indexes",
    "--documentation_directory", "/documentation/library",
]

_INDEXES = [{"id": "item-1", "name": "Item 1"}]


def _patched_main():
    with patch("sys.argv", ARGV), \
         patch("generate_readmes.load_library_indexes", return_value=_INDEXES) as mock_load, \
         patch("generate_readmes.create_applications_documentation") as mock_apps, \
         patch("generate_readmes.create_faults_documentation") as mock_faults, \
         patch("generate_readmes.create_waiters_documentation") as mock_waiters, \
         patch("generate_readmes.create_scenarios_documentation") as mock_scenarios, \
         patch("generate_readmes.Environment"):
        generate_readmes.main()
        return mock_load, mock_apps, mock_faults, mock_waiters, mock_scenarios


def test_arguments():
    """main() accepts the argument names the Makefile passes."""
    mock_load, mock_apps, mock_faults, mock_waiters, mock_scenarios = _patched_main()
    assert mock_load.call_count == 4


def test_all_doc_functions_called():
    """main() calls all four documentation creation functions."""
    _, mock_apps, mock_faults, mock_waiters, mock_scenarios = _patched_main()
    mock_apps.assert_called_once()
    mock_faults.assert_called_once()
    mock_waiters.assert_called_once()
    mock_scenarios.assert_called_once()


def test_documentation_subdirectories():
    """main() passes the correct documentation subdirectory to each function."""
    _, mock_apps, mock_faults, mock_waiters, mock_scenarios = _patched_main()
    assert mock_apps.call_args.args[0] == Path("/documentation/library/applications")
    assert mock_faults.call_args.args[0] == Path("/documentation/library/faults")
    assert mock_waiters.call_args.args[0] == Path("/documentation/library/waiters")
    # scenarios documentation_directory
    assert mock_scenarios.call_args.args[1] == Path("/documentation/library/scenarios")


def test_index_subdirectories():
    """main() loads indexes from the correct subdirectories."""
    mock_load, *_ = _patched_main()
    loaded_dirs = [c.args[0] for c in mock_load.call_args_list]
    assert Path("/lib/indexes/applications") in loaded_dirs
    assert Path("/lib/indexes/faults") in loaded_dirs
    assert Path("/lib/indexes/waiters") in loaded_dirs
    assert Path("/lib/indexes/scenarios") in loaded_dirs
