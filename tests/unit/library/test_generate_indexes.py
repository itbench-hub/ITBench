"""Tests for itbench.library.generate (indexes)."""
from pathlib import Path
from unittest.mock import patch

import itbench.library.generate as generate_indexes


def test_faults_passed_to_scenarios():
    """generate_indexes() passes the faults lookup returned for 'faults' into create_scenarios_indexes."""
    faults_cache = {"test-fault": {"id": "test-fault"}}
    with patch("itbench.library.generate.load_and_write_library_index", side_effect=[{}, faults_cache, {}]), \
         patch("itbench.library.generate.create_scenarios_indexes") as mock_scenarios:
        generate_indexes.generate_indexes(
            Path("/templates/library/indexes"),
            Path("/lib/indexes"),
            Path("/scenarios/sre/project"),
        )

    passed_faults = mock_scenarios.call_args.args[3]
    assert passed_faults == faults_cache
