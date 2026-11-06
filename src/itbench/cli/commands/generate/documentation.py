"""CLI command to generate Markdown documentation for ITBench primitives."""

from collections.abc import Iterable, Sequence
from pathlib import Path

import click

from itbench.cli.render import console
from itbench.models.waiter import WAITER_CATALOG
from itbench.paths import repository
from itbench.utils.scenarios import load_scenario_docs, summarize_scenario


def _table(headers: Sequence[str], rows: Iterable[Sequence[str]]) -> list[str]:
    """Render a Markdown table: a header row, a separator row, then one line per row."""
    return [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("-" * len(header) for header in headers) + " |",
        *("| " + " | ".join(row) + " |" for row in rows),
    ]


def _write(output_dir: Path, name: str, lines: list[str]) -> Path:
    """Write *lines* to ``output_dir/name`` (creating the directory) and return the path."""
    doc_path = output_dir / name
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


def _generate_applications_documentation(output_dir: Path) -> Path:
    from itbench.models.application import APPLICATION_CATALOG

    table = _table(
        ["Slug", "Name", "Platforms", "Description", "Repository"],
        (
            [
                f"`{slug}`",
                entry.name,
                ", ".join(entry.platforms),
                entry.description,
                f"[{entry.repository}]({entry.repository})",
            ]
            for slug, entry in APPLICATION_CATALOG.items()
        ),
    )

    lines = [
        "# Applications",
        "",
        "All benchmark applications available in ITBench.",
        "",
        *table,
        "",
        "## Usage",
        "",
        "```yaml",
        "# itbench explain application <slug>",
        "# itbench list applications",
        "```",
        "",
    ]
    return _write(output_dir, "applications.md", lines)


def _generate_faults_documentation(output_dir: Path) -> Path:
    from itbench.models.fault import FAULT_CATALOG

    table = _table(
        ["Slug", "Name", "Platform", "Tags", "Alerts", "Description"],
        (
            [
                f"`{slug}`",
                fault.name,
                fault.platform,
                ", ".join(fault.tags),
                ", ".join(fault.alerts) if fault.alerts else "",
                fault.description,
            ]
            for slug, fault in sorted(FAULT_CATALOG.items())
        ),
    )

    lines = [
        "# Faults",
        "",
        "All benchmark faults available in ITBench.",
        "",
        *table,
        "",
        "## Usage",
        "",
        "```yaml",
        "# itbench explain fault <slug>",
        "# itbench list faults --tag Networking",
        "# itbench list faults --platform Kubernetes",
        "```",
        "",
        "### Scenario YAML snippet",
        "",
        "```yaml",
        "environment:",
        "  applications:",
        "    - id: <application-slug>",
        "  domains:",
        "    - sre",
        "faults:",
        "  - injections:",
        "      - id: <fault-slug>",
        "        targets:",
        "          - kubernetes:",
        "              apiVersion: apps/v1",
        "              kind: Deployment",
        "              name: <workload-name>",
        "              namespace: <namespace>",
        "```",
        "",
    ]
    return _write(output_dir, "faults.md", lines)


def _generate_waiters_documentation(output_dir: Path) -> Path:
    table = _table(
        ["ID", "Name", "Platforms", "Description"],
        (
            [f"`{waiter_id}`", entry.name, ", ".join(entry.platforms), entry.description]
            for waiter_id, entry in WAITER_CATALOG.items()
        ),
    )

    lines = [
        "# Waiters",
        "",
        "Built-in waiter primitives used in scenario `waitFor` blocks.",
        "",
        *table,
        "",
        "## Usage",
        "",
        "```yaml",
        "# itbench explain waiter <id>",
        "# itbench list waiters",
        "```",
        "",
        "### Scenario YAML snippet",
        "",
        "```yaml",
        "faults:",
        "  - waitFor:",
        "      postInjection:",
        "        - id: restart-kubernetes-workload",
        "          workload:",
        "            apiVersion: apps/v1",
        "            kind: Deployment",
        "            name: <workload-name>",
        "            namespace: <namespace>",
        "```",
        "",
    ]
    return _write(output_dir, "waiters.md", lines)


def _generate_scenarios_documentation(output_dir: Path) -> Path:
    summaries = [
        summarize_scenario(scenario_id, data) for scenario_id, data in load_scenario_docs(repository.scenarios)
    ]
    table = _table(
        ["ID", "Domains", "Applications", "Faults"],
        ([s["id"], ", ".join(s["domains"]), ", ".join(s["applications"]), ", ".join(s["faults"])] for s in summaries),
    )

    lines = [
        "# Scenarios",
        "",
        "All benchmark scenarios available in ITBench.",
        "",
        *table,
        "",
        "## Usage",
        "",
        "```bash",
        "itbench deploy environment --scenario <id>",
        "itbench list scenarios",
        "```",
        "",
    ]
    return _write(output_dir, "scenarios.md", lines)


@click.command(name="documentation", help="Generate Markdown documentation for ITBench library primitives.")
def generate_documentation_command() -> None:
    """Generate Markdown documentation for all benchmark primitives into the repository's ``documentation/library``."""
    output_dir = repository.documentation

    path = _generate_applications_documentation(output_dir)
    console.print(f"[green]Generated applications documentation → {path}[/green]", soft_wrap=True)

    path = _generate_faults_documentation(output_dir)
    console.print(f"[green]Generated faults documentation → {path}[/green]", soft_wrap=True)

    path = _generate_waiters_documentation(output_dir)
    console.print(f"[green]Generated waiters documentation → {path}[/green]", soft_wrap=True)

    path = _generate_scenarios_documentation(output_dir)
    console.print(f"[green]Generated scenarios documentation → {path}[/green]", soft_wrap=True)
