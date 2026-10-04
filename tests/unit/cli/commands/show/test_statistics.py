"""Tests for the show statistics CLI command."""

from pathlib import Path
from unittest.mock import patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.show.statistics import show_statistics


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_scenario(scenarios_dir: Path, name: str, data: dict) -> None:
    d = scenarios_dir / name
    d.mkdir(parents=True)
    (d / "scenario.yaml").write_text(yaml.dump(data), encoding="utf-8")


def _library(tmp_path: Path) -> Path:
    return tmp_path / "library"


def _make_library(tmp_path: Path, scenarios: list[tuple[str, dict]]) -> Path:
    lib = _library(tmp_path)
    for name, data in scenarios:
        _write_scenario(lib / "scenarios", name, data)
    return lib


# ---------------------------------------------------------------------------
# No subject flag
# ---------------------------------------------------------------------------

def test_statistics_no_subject_exits_nonzero() -> None:
    runner = CliRunner()
    result = runner.invoke(show_statistics, [])
    assert result.exit_code != 0
    assert "Specify a subject" in result.output


# ---------------------------------------------------------------------------
# --faults
# ---------------------------------------------------------------------------

def test_statistics_faults_counts(tmp_path: Path) -> None:
    fault_a = "fault-alpha"
    fault_b = "fault-beta"
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": fault_a}]}]}),
        ("2", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": fault_a}]}]}),
        ("3", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": fault_b}]}]}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--faults"])
    assert result.exit_code == 0
    assert fault_a in result.output
    assert fault_b in result.output
    assert "2" in result.output  # count for fault_a
    assert "3 scenario(s)" in result.output


def test_statistics_faults_full_shows_scenario_ids(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("42", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": "some-fault"}]}]}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--faults", "--full"])
    assert result.exit_code == 0
    assert "42" in result.output


def test_statistics_faults_percentage_shown(tmp_path: Path) -> None:
    # 2 out of 3 total usages = 66.7%
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": "fault-a"}]}]}),
        ("2", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": "fault-a"}]}]}),
        ("3", {"environment": {"domains": ["sre"]}, "faults": [{"injections": [{"id": "fault-b"}]}]}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--faults"])
    assert result.exit_code == 0
    assert "66.7%" in result.output
    assert "33.3%" in result.output


def test_statistics_faults_empty(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"domains": ["sre"]}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--faults"])
    assert result.exit_code == 0
    assert "No fault usage found" in result.output


# ---------------------------------------------------------------------------
# --applications
# ---------------------------------------------------------------------------

def test_statistics_applications_counts(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"applications": [{"id": "opentelemetry-demo"}], "domains": ["sre"]}, "faults": []}),
        ("2", {"environment": {"applications": [{"id": "opentelemetry-demo"}], "domains": ["sre"]}, "faults": []}),
        ("3", {"environment": {"applications": [{"id": "book-info"}], "domains": ["sre"]}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--applications"])
    assert result.exit_code == 0
    assert "opentelemetry-demo" in result.output
    assert "book-info" in result.output
    assert "2 unique application(s)" in result.output


def test_statistics_applications_full_shows_scenario_ids(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("7", {"environment": {"applications": [{"id": "opentelemetry-demo"}], "domains": ["sre"]}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--applications", "--full"])
    assert result.exit_code == 0
    assert "7" in result.output


def test_statistics_applications_empty(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"applications": [], "domains": ["sre"]}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--applications"])
    assert result.exit_code == 0
    assert "No application usage found" in result.output


# ---------------------------------------------------------------------------
# --waiters
# ---------------------------------------------------------------------------

def test_statistics_waiters_counts(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {
            "environment": {"domains": ["sre"]},
            "faults": [{"waitFor": {"postInjection": [{"id": "pause-execution"}]}, "injections": []}],
        }),
        ("2", {
            "environment": {"domains": ["sre"]},
            "faults": [{"waitFor": {"preInjection": [{"id": "pause-execution"}]}, "injections": []}],
        }),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--waiters"])
    assert result.exit_code == 0
    assert "pause-execution" in result.output
    assert "2" in result.output


def test_statistics_waiters_empty(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"domains": ["sre"]}, "faults": [{"injections": []}]}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--waiters"])
    assert result.exit_code == 0
    assert "No waiter usage found" in result.output


# ---------------------------------------------------------------------------
# --scenarios
# ---------------------------------------------------------------------------

def test_statistics_scenarios_counts_by_domain(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"domains": ["sre"]}, "faults": []}),
        ("2", {"environment": {"domains": ["sre"]}, "faults": []}),
        ("3", {"environment": {"domains": ["finops"]}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--scenarios"])
    assert result.exit_code == 0
    assert "sre" in result.output
    assert "finops" in result.output
    assert "3 scenario(s) total" in result.output


def test_statistics_scenarios_full_shows_ids(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("99", {"environment": {"domains": ["ciso"]}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--scenarios", "--full"])
    assert result.exit_code == 0
    assert "ciso" in result.output
    assert "99" in result.output


def test_statistics_scenarios_empty_domains(tmp_path: Path) -> None:
    lib = _make_library(tmp_path, [
        ("1", {"environment": {"domains": []}, "faults": []}),
    ])
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", lib):
        result = runner.invoke(show_statistics, ["--scenarios"])
    assert result.exit_code == 0
    assert "No domain assignments found" in result.output


# ---------------------------------------------------------------------------
# No scenarios directory
# ---------------------------------------------------------------------------

def test_statistics_no_library_directory(tmp_path: Path) -> None:
    runner = CliRunner()
    with patch("itbench.cli.commands.show.statistics._LIBRARY_ROOT", tmp_path / "nonexistent"):
        result = runner.invoke(show_statistics, ["--faults"])
    assert result.exit_code == 0
    assert "No fault usage found" in result.output
