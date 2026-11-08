"""Tests for the generate documentation CLI command."""

from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.documentation import _table, generate_documentation_command
from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG


@pytest.fixture
def docs_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the repository root at a temporary directory and return where documentation is written."""
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))
    return tmp_path / "documentation" / "library"


def test_table_renders_header_separator_and_rows() -> None:
    assert _table(["Slug", "ID"], [["`a`", "1"], ["`b`", "2"]]) == [
        "| Slug | ID |",
        "| ---- | -- |",
        "| `a` | 1 |",
        "| `b` | 2 |",
    ]


def test_table_without_rows_is_header_and_separator_only() -> None:
    assert _table(["A"], []) == ["| A |", "| - |"]


def test_generate_documentation_accepts_no_output_location() -> None:
    result = CliRunner().invoke(generate_documentation_command, ["--output-dir", "/elsewhere"])

    assert result.exit_code == 2
    assert "No such option" in result.output


def test_generate_documentation_creates_all_files(docs_dir: Path) -> None:
    result = CliRunner().invoke(generate_documentation_command, [])

    assert result.exit_code == 0
    assert (docs_dir / "applications.md").exists()
    assert (docs_dir / "faults.md").exists()
    assert (docs_dir / "waiters.md").exists()
    assert (docs_dir / "scenarios.md").exists()


def test_generate_applications_documentation_content(docs_dir: Path) -> None:
    CliRunner().invoke(generate_documentation_command, [])

    content = (docs_dir / "applications.md").read_text(encoding="utf-8")
    slug = next(iter(APPLICATION_CATALOG))
    assert slug in content
    assert APPLICATION_CATALOG[slug].name in content


def test_generate_faults_documentation_content(docs_dir: Path) -> None:
    CliRunner().invoke(generate_documentation_command, [])

    content = (docs_dir / "faults.md").read_text(encoding="utf-8")
    slug = next(iter(sorted(FAULT_CATALOG.keys())))
    assert slug in content


def test_generate_waiters_documentation_content(docs_dir: Path) -> None:
    CliRunner().invoke(generate_documentation_command, [])

    content = (docs_dir / "waiters.md").read_text(encoding="utf-8")
    waiter_id = next(iter(WAITER_CATALOG))
    assert waiter_id in content
    assert WAITER_CATALOG[waiter_id].name in content


def test_generate_scenarios_documentation_with_scenarios(
    tmp_path: Path, docs_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    scenario_dir = tmp_path / "library" / "scenarios" / "1"
    scenario_dir.mkdir(parents=True)
    scenario = {
        "environment": {"applications": [{"id": "opentelemetry-demo"}]},
        "faults": [{"injections": [{"id": "scaled-to-zero-kubernetes-workload"}]}],
    }
    (scenario_dir / "scenario.yaml").write_text(yaml.dump(scenario), encoding="utf-8")
    monkeypatch.setenv("ITBENCH_LIBRARY_PATH", str(tmp_path / "library"))

    result = CliRunner().invoke(generate_documentation_command, [])

    assert result.exit_code == 0
    content = (docs_dir / "scenarios.md").read_text(encoding="utf-8")
    assert "opentelemetry-demo" in content
    assert "scaled-to-zero-kubernetes-workload" in content
