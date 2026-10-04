"""Show solution sub-command for ITBench."""

from pathlib import Path

import click
import yaml

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule

console = Console()

_LIBRARY_ROOT = Path(__file__).parents[5] / "library"


def _render_solution(scenario_id: str, data: dict) -> None:
    """Render a scenario's ground truth solution as a Rich man-page."""
    alerts: list[dict] = data.get("alerts") or []
    entities: list[dict] = data.get("entities") or []
    solutions: list[list[dict]] = data.get("solutions") or []

    console.print()
    console.print(Panel(
        f"[bold]Scenario {escape(scenario_id)}[/bold]",
        title="[bold magenta]SOLUTION[/bold magenta]",
        border_style="magenta",
    ))

    if alerts:
        console.print("[bold]ALERTS[/bold]")
        for alert in alerts:
            console.print(f"  • {alert.get('name', '?')}")
        console.print()

    if entities:
        console.print("[bold]AFFECTED ENTITIES[/bold]")
        for entity in entities:
            parts = [
                entity.get("kind", "?"),
                entity.get("name", "?"),
            ]
            if entity.get("namespace"):
                parts.append(f"({entity['namespace']})")
            parts.insert(0, f"[dim]{entity.get('apiVersion', '')}[/dim]")
            console.print(f"  • {' '.join(parts)}")
        console.print()

    if not solutions:
        console.print("[dim]No solutions recorded for this scenario.[/dim]")
        return

    console.print("[bold]SOLUTIONS[/bold]")
    for fault_idx, variants in enumerate(solutions, 1):
        if len(solutions) > 1:
            console.print(f"\n  [bold]Fault {fault_idx}[/bold]")

        for variant_idx, variant in enumerate(variants, 1):
            steps: list[dict] = variant.get("steps") or []
            if len(variants) > 1:
                console.print(f"  [dim]Variant {variant_idx}[/dim]")
            for step_idx, step in enumerate(steps, 1):
                text = step.get("text", "")
                command = step.get("command")
                console.print(f"    {step_idx}. {escape(text)}")
                if command:
                    console.print(f"       [green]$ {escape(command)}[/green]")

        if fault_idx < len(solutions):
            console.print(Rule(style="dim"))

    console.print()


@click.command(name="solution", help="Show the solution guide for a scenario.")
@click.argument("scenario_id")
def show_solution(scenario_id: str) -> None:
    """Print the ground truth solution for a scenario."""
    ground_truth_path = _LIBRARY_ROOT / "scenarios" / scenario_id / "ground_truth.yaml"

    if not ground_truth_path.exists():
        console.print(f"[red]No ground truth found for scenario '[bold]{scenario_id}[/bold]'.[/red]")
        console.print("[dim]Run `itbench list scenarios` to see available scenario IDs.[/dim]")
        raise SystemExit(1)

    try:
        data = yaml.safe_load(ground_truth_path.read_text(encoding="utf-8"))
    except Exception as exc:
        console.print(f"[red]Failed to parse ground truth: {exc}[/red]")
        raise SystemExit(1)

    _render_solution(scenario_id, data or {})
