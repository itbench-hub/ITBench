"""
Tests for check_localhost_resources.py

Makefile invocation:
  uv run python ../../scripts/check_localhost_resources.py --target <target>
"""
from unittest.mock import patch

import pytest

import check_localhost_resources


# ---------------------------------------------------------------------------
# get_cpu_count
# ---------------------------------------------------------------------------

def test_get_cpu_count_returns_physical_cores():
    """get_cpu_count() returns the physical (non-logical) core count."""
    with patch("check_localhost_resources.psutil.cpu_count", return_value=8) as mock_cpu:
        result = check_localhost_resources.get_cpu_count()
    mock_cpu.assert_called_once_with(logical=False)
    assert result == 8


def test_get_cpu_count_falls_back_to_zero_when_none():
    """get_cpu_count() returns 0 when psutil cannot determine the count."""
    with patch("check_localhost_resources.psutil.cpu_count", return_value=None):
        assert check_localhost_resources.get_cpu_count() == 0


# ---------------------------------------------------------------------------
# get_memory_gb
# ---------------------------------------------------------------------------

def test_get_memory_gb_converts_bytes_to_gb():
    """get_memory_gb() floors total bytes to whole gigabytes."""
    with patch("check_localhost_resources.psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 17_179_869_184  # 16 GiB exactly
        assert check_localhost_resources.get_memory_gb() == 16


def test_get_memory_gb_floors_fractional_gb():
    """get_memory_gb() floors, so 15.9 GB reports as 15."""
    with patch("check_localhost_resources.psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 15_900_000_000
        assert check_localhost_resources.get_memory_gb() == 14


# ---------------------------------------------------------------------------
# check_resources — warning logic
# ---------------------------------------------------------------------------

def test_check_resources_warns_on_low_cpu(caplog):
    """check_resources() logs a warning when CPU is below the recommended threshold."""
    with patch("check_localhost_resources.get_cpu_count", return_value=4), \
         patch("check_localhost_resources.get_memory_gb", return_value=32):
        with caplog.at_level("WARNING"):
            check_localhost_resources.check_resources("argo-stack")
    assert "CPU" in caplog.text
    assert "Memory" not in caplog.text.title()


def test_check_resources_warns_on_low_memory(caplog):
    """check_resources() logs a warning when memory is below the recommended threshold."""
    with patch("check_localhost_resources.get_cpu_count", return_value=16), \
         patch("check_localhost_resources.get_memory_gb", return_value=8):
        with caplog.at_level("WARNING"):
            check_localhost_resources.check_resources("argo-stack")
    assert "memory" in caplog.text.lower()
    assert "CPU" not in caplog.text


def test_check_resources_no_warnings_when_sufficient(caplog):
    """check_resources() logs no warnings when both CPU and memory meet the threshold."""
    with patch("check_localhost_resources.get_cpu_count", return_value=12), \
         patch("check_localhost_resources.get_memory_gb", return_value=16):
        with caplog.at_level("WARNING"):
            check_localhost_resources.check_resources("argo-stack")
    assert caplog.text == ""


def test_check_resources_simple_cluster_threshold(caplog):
    """check_resources() applies the correct (lower) thresholds for environment-cluster."""
    with patch("check_localhost_resources.get_cpu_count", return_value=8), \
         patch("check_localhost_resources.get_memory_gb", return_value=16):
        with caplog.at_level("WARNING"):
            check_localhost_resources.check_resources("environment-cluster")
    assert caplog.text == ""


# ---------------------------------------------------------------------------
# main — argument parsing
# ---------------------------------------------------------------------------

def test_main_calls_check_resources_with_target():
    """main() parses --target and passes it to check_resources."""
    with patch("sys.argv", ["check_localhost_resources.py", "--target", "environment-cluster"]), \
         patch("check_localhost_resources.check_resources") as mock_check:
        check_localhost_resources.main()
    mock_check.assert_called_once_with("environment-cluster")


def test_main_rejects_invalid_target():
    """main() exits with an error for an unrecognised target."""
    with patch("sys.argv", ["check_localhost_resources.py", "--target", "invalid-target"]), \
         pytest.raises(SystemExit) as exc:
        check_localhost_resources.main()
    assert exc.value.code != 0
