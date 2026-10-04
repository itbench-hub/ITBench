"""Explain waiter sub-command for ITBench."""

import textwrap

import click
import yaml

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from itbench.models.waiter import WAITER_CATALOG, Waiter

console = Console()


_BASE_FIELD_NAMES = set(Waiter.model_fields)


def _render_waiter(waiter_id: str) -> None:
    """Render a waiter as a Rich man-page."""
    entry = WAITER_CATALOG.get(waiter_id)
    if entry is None:
        console.print(
            f"[red]Unknown waiter '[bold]{waiter_id}[/bold]'. "
            "Run `itbench list waiters` to see available waiter IDs.[/red]"
        )
        raise SystemExit(1)

    console.print()
    console.print(Panel(
        f"[bold]{escape(entry.name)}[/bold]\n\n"
        f"[dim]id:[/dim] {entry.id}   "
        f"[dim]platforms:[/dim] {', '.join(entry.platforms)}",
        title="[bold yellow]WAITER[/bold yellow]",
        border_style="yellow",
    ))

    console.print("[bold]DESCRIPTION[/bold]")
    console.print(f"  {entry.description}\n")

    type_data = entry.model_dump(exclude=_BASE_FIELD_NAMES)
    if type_data:
        console.print("[bold]FIELDS[/bold]")
        console.print(textwrap.indent(yaml.dump(type_data, default_flow_style=False).rstrip(), "  "))
        console.print()

    example_data = {
        k: {sk: f"<{sk}>" for sk in v} if isinstance(v, dict) else f"<{k}>"
        for k, v in type_data.items()
    }
    example = {
        "faults": [{
            "waitFor": {
                "postInjection": [{"id": entry.id} | example_data],
            },
        }],
    }
    console.print("[bold]SCENARIO YAML EXAMPLE[/bold]")
    console.print("  # In library/scenarios/<id>/scenario.yaml")
    console.print(textwrap.indent(yaml.dump(example, default_flow_style=False).rstrip(), "  "))
    console.print()


@click.command(name="waiter", help="Explain a waiter by its id.")
@click.argument("waiter_id")
def explain_waiter(waiter_id: str) -> None:
    """Print a formatted man-page for a waiter."""
    _render_waiter(waiter_id)
