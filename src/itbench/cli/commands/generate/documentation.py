"""CLI command to generate Markdown documentation for ITBench primitives."""

from pathlib import Path

import click

from rich.console import Console

from itbench.models.waiter import WAITER_CATALOG
from itbench.paths import library
from itbench.utils.scenarios import load_scenario_docs, summarize_scenario

console = Console()

_DOCS_ROOT = Path("documentation/library")


def _generate_applications_documentation(output_dir: Path) -> Path:
    from itbench.models.application import APPLICATION_CATALOG

    rows: list[dict[str, str]] = [
        {
            "slug": slug,
            "name": entry.name,
            "description": entry.description,
            "platforms": ", ".join(entry.platforms),
            "repository": entry.repository,
        }
        for slug, entry in APPLICATION_CATALOG.items()
    ]

    lines = [
        "# Applications",
        "",
        "All benchmark applications available in ITBench.",
        "",
        "| Slug | Name | Platforms | Description | Repository |",
        "| ---- | ---- | --------- | ----------- | ---------- |",
    ]
    for r in rows:
        lines.append(
            f"| `{r['slug']}` | {r['name']} | {r['platforms']} | {r['description']} | [{r['repository']}]({r['repository']}) |"
        )

    lines += [
        "",
        "## Usage",
        "",
        "```yaml",
        "# itbench explain application <slug>",
        "# itbench list applications",
        "```",
        "",
    ]

    doc_path = output_dir / "applications.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


def _generate_faults_documentation(output_dir: Path) -> Path:
    from itbench.models.fault import FAULT_CATALOG

    rows: list[dict[str, str]] = [
        {
            "slug": slug,
            "name": fault.name,
            "tags": ", ".join(fault.tags),
            "platform": fault.platform,
            "alerts": ", ".join(fault.alerts) if fault.alerts else "",
            "description": fault.description,
        }
        for slug, fault in sorted(FAULT_CATALOG.items())
    ]

    lines = [
        "# Faults",
        "",
        "All benchmark faults available in ITBench.",
        "",
        "| Slug | Name | Platform | Tags | Alerts | Description |",
        "| ---- | ---- | -------- | ---- | ------ | ----------- |",
    ]
    for r in rows:
        lines.append(
            f"| `{r['slug']}` | {r['name']} | {r['platform']} | {r['tags']} | {r['alerts']} | {r['description']} |"
        )

    lines += [
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

    doc_path = output_dir / "faults.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


def _generate_waiters_documentation(output_dir: Path) -> Path:
    lines = [
        "# Waiters",
        "",
        "Built-in waiter primitives used in scenario `waitFor` blocks.",
        "",
        "| ID | Name | Platforms | Description |",
        "| -- | ---- | --------- | ----------- |",
    ]
    for waiter_id, entry in WAITER_CATALOG.items():
        lines.append(f"| `{waiter_id}` | {entry.name} | {', '.join(entry.platforms)} | {entry.description} |")

    lines += [
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

    doc_path = output_dir / "waiters.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


def _generate_scenarios_documentation(output_dir: Path) -> Path:
    rows: list[dict[str, str]] = []
    for scenario_id, data in load_scenario_docs(library.scenarios):
        summary = summarize_scenario(scenario_id, data)
        rows.append(
            {
                "id": summary["id"],
                "applications": ", ".join(summary["applications"]),
                "domains": ", ".join(summary["domains"]),
                "faults": ", ".join(summary["faults"]),
            }
        )

    lines = [
        "# Scenarios",
        "",
        "All benchmark scenarios available in ITBench.",
        "",
        "| ID | Domains | Applications | Faults |",
        "| -- | ------- | ------------ | ------ |",
    ]
    for r in rows:
        lines.append(f"| {r['id']} | {r['domains']} | {r['applications']} | {r['faults']} |")

    lines += [
        "",
        "## Usage",
        "",
        "```bash",
        "itbench deploy environment --scenario <id>",
        "itbench list scenarios",
        "```",
        "",
    ]

    doc_path = output_dir / "scenarios.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


@click.command(name="documentation", help="Generate Markdown documentation for ITBench library primitives.")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=_DOCS_ROOT,
    show_default=True,
    help="Target directory where Markdown files will be written.",
)
def generate_documentation_command(output_dir: Path) -> None:
    """Generate Markdown documentation for all benchmark primitives."""
    path = _generate_applications_documentation(output_dir)
    console.print(f"[green]Generated applications documentation → {path}[/green]")

    path = _generate_faults_documentation(output_dir)
    console.print(f"[green]Generated faults documentation → {path}[/green]")

    path = _generate_waiters_documentation(output_dir)
    console.print(f"[green]Generated waiters documentation → {path}[/green]")

    path = _generate_scenarios_documentation(output_dir)
    console.print(f"[green]Generated scenarios documentation → {path}[/green]")
