"""Tests for the generate docs CLI command."""

from pathlib import Path
from unittest.mock import patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.docs import generate_docs_command
from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG


def test_generate_docs_creates_all_files(tmp_path: Path) -> None:
    runner = CliRunner()

    result = runner.invoke(generate_docs_command, ["--output-dir", str(tmp_path)])

    assert result.exit_code == 0
    assert (tmp_path / "applications.md").exists()
    assert (tmp_path / "faults.md").exists()
    assert (tmp_path / "waiters.md").exists()
    assert (tmp_path / "scenarios.md").exists()


def test_generate_applications_doc_content(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(generate_docs_command, ["--output-dir", str(tmp_path)])

    content = (tmp_path / "applications.md").read_text(encoding="utf-8")
    slug = next(iter(APPLICATION_CATALOG))
    assert slug in content
    assert APPLICATION_CATALOG[slug].name in content


def test_generate_faults_doc_content(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(generate_docs_command, ["--output-dir", str(tmp_path)])

    content = (tmp_path / "faults.md").read_text(encoding="utf-8")
    slug = next(iter(sorted(FAULT_CATALOG.keys())))
    assert slug in content


def test_generate_waiters_doc_content(tmp_path: Path) -> None:
    runner = CliRunner()
    runner.invoke(generate_docs_command, ["--output-dir", str(tmp_path)])

    content = (tmp_path / "waiters.md").read_text(encoding="utf-8")
    waiter_id = next(iter(WAITER_CATALOG))
    assert waiter_id in content
    assert WAITER_CATALOG[waiter_id].name in content


def test_generate_scenarios_doc_with_scenarios(tmp_path: Path) -> None:
    output_dir = tmp_path / "docs"
    library_dir = tmp_path / "library" / "scenarios" / "1"
    library_dir.mkdir(parents=True)
    scenario = {
        "environment": {"applications": [{"id": "opentelemetry-demo"}]},
        "faults": [{"injections": [{"id": "scaled-to-zero-kubernetes-workload"}]}],
    }
    (library_dir / "scenario.yaml").write_text(yaml.dump(scenario), encoding="utf-8")

    with patch("itbench.cli.commands.generate.docs._LIBRARY_ROOT", tmp_path / "library"):
        runner = CliRunner()
        result = runner.invoke(generate_docs_command, ["--output-dir", str(output_dir)])

    assert result.exit_code == 0
    content = (output_dir / "scenarios.md").read_text(encoding="utf-8")
    assert "opentelemetry-demo" in content
    assert "scaled-to-zero-kubernetes-workload" in content
