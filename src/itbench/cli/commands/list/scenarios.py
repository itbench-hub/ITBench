"""List scenarios sub-command for ITBench."""

from pathlib import Path

import click
import yaml

from rich import box
from rich.console import Console
from rich.table import Table

console = Console()

_LIBRARY_ROOT = Path(__file__).parents[5] / "library"


@click.command(name="scenarios", help="List all benchmark scenarios.")
def list_scenarios() -> None:
    """List all benchmark scenarios."""
    scenarios_dir = _LIBRARY_ROOT / "scenarios"
    if not scenarios_dir.exists():
        console.print("[yellow]No scenarios directory found at library/scenarios/.[/yellow]")
        return

    table = Table(
        title="Scenarios",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Domains", style="dim")
    table.add_column("Applications", style="dim")
    table.add_column("Faults", style="dim")

    rows = []
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

        rows.append((scenario_dir.name, ", ".join(domains), ", ".join(apps), ", ".join(fault_ids)))

    if not rows:
        console.print("[yellow]No scenarios found.[/yellow]")
        return

    for row in rows:
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(rows)} scenario(s) found.[/dim]")
