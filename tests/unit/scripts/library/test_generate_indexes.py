"""
Tests for generate_indexes.py
"""
from unittest.mock import patch

import generate_indexes


ARGV = [
    "generate_indexes.py",
    "--templates_directory", "/templates/library/indexes",
    "--library_index_directory", "/lib/indexes",
    "--playbooks_directory", "/scenarios/sre/project",
]


def test_faults_passed_to_scenarios():
    """main() passes the faults lookup returned for 'faults' into create_scenarios_indexes."""
    faults_cache = {"test-fault": {"id": "test-fault"}}
    with patch("sys.argv", ARGV), \
         patch("generate_indexes.load_and_write_library_index", side_effect=[{}, faults_cache, {}]), \
         patch("generate_indexes.create_scenarios_indexes") as mock_scenarios:
        generate_indexes.main()

    passed_faults = mock_scenarios.call_args.args[3]
    assert passed_faults == faults_cache
