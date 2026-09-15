"""Tests for itbench.localhost.resources."""
from unittest.mock import patch

import pytest

import itbench.localhost.resources as resources


def test_get_cpu_count_returns_physical_cores():
    """get_cpu_count() returns the physical (non-logical) core count."""
    with patch("itbench.localhost.resources.psutil.cpu_count", return_value=8) as mock_cpu:
        result = resources.get_cpu_count()
    mock_cpu.assert_called_once_with(logical=False)
    assert result == 8


def test_get_cpu_count_falls_back_to_zero_when_none():
    """get_cpu_count() returns 0 when psutil cannot determine the count."""
    with patch("itbench.localhost.resources.psutil.cpu_count", return_value=None):
        assert resources.get_cpu_count() == 0


def test_get_memory_gb_converts_bytes_to_gb():
    """get_memory_gb() floors total bytes to whole gigabytes."""
    with patch("itbench.localhost.resources.psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 17_179_869_184  # 16 GiB exactly
        assert resources.get_memory_gb() == 16


def test_get_memory_gb_floors_fractional_gib():
    """get_memory_gb() uses integer division by 1024³ (GiB), so 15_900_000_000 bytes → 14."""
    with patch("itbench.localhost.resources.psutil.virtual_memory") as mock_mem:
        mock_mem.return_value.total = 15_900_000_000
        assert resources.get_memory_gb() == 14


def test_check_resources_warns_on_low_cpu(caplog):
    """check_resources() logs a warning when CPU is below the recommended threshold."""
    with patch("itbench.localhost.resources.get_cpu_count", return_value=4), \
         patch("itbench.localhost.resources.get_memory_gb", return_value=32):
        with caplog.at_level("WARNING"):
            ok = resources.check_resources("argo-stack")
    assert "CPU" in caplog.text
    assert "memory" not in caplog.text.lower()
    assert ok is False


def test_check_resources_warns_on_low_memory(caplog):
    """check_resources() logs a warning when memory is below the recommended threshold."""
    with patch("itbench.localhost.resources.get_cpu_count", return_value=16), \
         patch("itbench.localhost.resources.get_memory_gb", return_value=8):
        with caplog.at_level("WARNING"):
            ok = resources.check_resources("argo-stack")
    assert "memory" in caplog.text.lower()
    assert "CPU" not in caplog.text
    assert ok is False


def test_check_resources_no_warnings_when_sufficient(caplog):
    """check_resources() logs no warnings when both CPU and memory meet the threshold."""
    with patch("itbench.localhost.resources.get_cpu_count", return_value=12), \
         patch("itbench.localhost.resources.get_memory_gb", return_value=16):
        with caplog.at_level("WARNING"):
            ok = resources.check_resources("argo-stack")
    assert caplog.text == ""
    assert ok is True


def test_check_resources_simple_cluster_threshold(caplog):
    """check_resources() applies the correct (lower) thresholds for environment-cluster."""
    with patch("itbench.localhost.resources.get_cpu_count", return_value=8), \
         patch("itbench.localhost.resources.get_memory_gb", return_value=16):
        with caplog.at_level("WARNING"):
            ok = resources.check_resources("environment-cluster")
    assert caplog.text == ""
    assert ok is True
