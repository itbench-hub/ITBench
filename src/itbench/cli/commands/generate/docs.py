"""CLI command to generate Markdown documentation for ITBench primitives."""

from pathlib import Path

import click
import yaml

from rich.console import Console

from itbench.models.waiter import WAITER_CATALOG

console = Console()

_LIBRARY_ROOT = Path(__file__).parents[5] / "library"
_DOCS_ROOT = Path("documentation/library")


def _generate_applications_doc(output_dir: Path) -> Path:
    from itbench.models.application import APPLICATION_CATALOG

    rows: list[dict] = [
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
        "# itbench explain app <slug>",
        "# itbench list apps",
        "```",
        "",
    ]

    doc_path = output_dir / "applications.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


def _generate_faults_doc(output_dir: Path) -> Path:
    from itbench.models.fault import FAULT_CATALOG

    rows: list[dict] = [
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


def _generate_waiters_doc(output_dir: Path) -> Path:
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


def _generate_scenarios_doc(output_dir: Path) -> Path:
    scenarios_dir = _LIBRARY_ROOT / "scenarios"

    rows: list[dict] = []
    if scenarios_dir.exists():
        for scenario_dir in sorted(
            scenarios_dir.iterdir(),
            key=lambda p: int(p.name) if p.name.isdigit() else p.name,
        ):
            scenario_file = scenario_dir / "scenario.yaml"
            if not scenario_file.exists():
                continue
            try:
                data = yaml.safe_load(scenario_file.read_text(encoding="utf-8"))
            except Exception:
                continue

            env = data.get("environment") or {}
            apps = [a.get("id", "?") for a in env.get("applications", [])]
            domains = env.get("domains", [])
            fault_ids = [
                inj.get("id", "?")
                for fault in (data.get("faults") or [])
                for inj in fault.get("injections", [])
            ]
            rows.append(
                {
                    "id": scenario_dir.name,
                    "apps": ", ".join(apps),
                    "domains": ", ".join(domains),
                    "faults": ", ".join(fault_ids),
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
        lines.append(f"| {r['id']} | {r['domains']} | {r['apps']} | {r['faults']} |")

    lines += [
        "",
        "## Usage",
        "",
        "```bash",
        "itbench deploy applications --scenario <id>",
        "itbench list scenarios",
        "```",
        "",
    ]

    doc_path = output_dir / "scenarios.md"
    doc_path.parent.mkdir(parents=True, exist_ok=True)
    doc_path.write_text("\n".join(lines), encoding="utf-8")
    return doc_path


@click.command(name="docs", help="Generate Markdown documentation for ITBench library primitives.")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=_DOCS_ROOT,
    show_default=True,
    help="Target directory where Markdown files will be written.",
)
def generate_docs_command(output_dir: Path) -> None:
    """Generate Markdown documentation for all benchmark primitives."""
    path = _generate_applications_doc(output_dir)
    console.print(f"[green]Generated applications doc → {path}[/green]")

    path = _generate_faults_doc(output_dir)
    console.print(f"[green]Generated faults doc → {path}[/green]")

    path = _generate_waiters_doc(output_dir)
    console.print(f"[green]Generated waiters doc → {path}[/green]")

    path = _generate_scenarios_doc(output_dir)
    console.print(f"[green]Generated scenarios doc → {path}[/green]")
