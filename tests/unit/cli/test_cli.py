"""Tests for itbench CLI entry points and argument parsing."""
from unittest.mock import patch

import pytest

from itbench.cli.main import main


def test_cli_localhost_check_resources():
    with patch("sys.argv", ["itbench", "localhost", "check-resources", "--target", "environment-cluster"]), \
         patch("itbench.cli.operations.check_resources", return_value=True) as mock_check:
        code = main()
    mock_check.assert_called_once_with("environment-cluster")
    assert code == 0


def test_cli_localhost_check_resources_invalid_target():
    with patch("sys.argv", ["itbench", "localhost", "check-resources", "--target", "invalid-target"]), \
         pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code != 0


def test_cli_library_validate():
    with patch("sys.argv", ["itbench", "library", "validate"]), \
         patch("itbench.cli.library.validate_all_indexes", return_value=True) as mock_val:
        code = main()
    assert mock_val.called
    assert code == 0


def test_cli_library_generate():
    with patch("sys.argv", ["itbench", "library", "generate", "all"]), \
         patch("itbench.cli.library.generate_indexes") as mock_indexes, \
         patch("itbench.cli.library.generate_index_schemas") as mock_schemas, \
         patch("itbench.cli.library.generate_specs") as mock_specs, \
         patch("itbench.cli.library.generate_readmes") as mock_readmes:
        code = main()
    assert mock_indexes.called
    assert mock_schemas.called
    assert mock_specs.called
    assert mock_readmes.called
    assert code == 0
