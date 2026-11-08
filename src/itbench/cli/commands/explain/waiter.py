"""Explain waiter sub-command for ITBench."""

import textwrap

import click
import yaml

from rich.markup import escape
from rich.panel import Panel

from itbench.cli.render import console, detail_format_option, emit_structured, exit_not_found
from itbench.models.waiter import WAITER_CATALOG, Waiter

_BASE_FIELD_NAMES = set(Waiter.model_fields)


def _render_fields(entry: Waiter) -> None:
    """Print the waiter's type-specific fields with their descriptions and defaults."""
    fields = {name: field for name, field in type(entry).model_fields.items() if name not in _BASE_FIELD_NAMES}
    if not fields:
        return

    console.print("[bold]FIELDS[/bold]")
    for name, field in fields.items():
        qualifier = "required" if field.is_required() else f"default: {field.default}"
        console.print(f"  [cyan]{escape(field.alias or name)}[/cyan] [dim]({escape(qualifier)})[/dim]")
        if field.description:
            console.print(f"    {escape(field.description)}")
    console.print()


def _render_waiter(entry: Waiter) -> None:
    """Render a waiter as a Rich man-page."""
    console.print()
    console.print(
        Panel(
            f"[bold]{escape(entry.name)}[/bold]\n\n"
            f"[dim]id:[/dim] {escape(entry.id)}   "
            f"[dim]platforms:[/dim] {escape(', '.join(entry.platforms))}",
            title="[bold yellow]WAITER[/bold yellow]",
            border_style="yellow",
        )
    )

    if entry.description:
        console.print("[bold]DESCRIPTION[/bold]")
        console.print(f"  {escape(entry.description)}\n")

    _render_fields(entry)

    type_data = entry.model_dump(mode="json", by_alias=True, exclude_none=True, exclude=_BASE_FIELD_NAMES)
    example = {
        "faults": [
            {
                "injections": [{"id": "<fault-id>"}],
                "waitFor": {
                    "postInjection": [{"id": entry.id} | type_data],
                },
            }
        ],
    }
    console.print("[bold]SCENARIO YAML EXAMPLE[/bold]")
    console.print("  # In library/scenarios/<id>/scenario.yaml", markup=False)
    console.print("  # Waiters can also be listed under preInjection.", markup=False)
    console.print(
        textwrap.indent(yaml.safe_dump(example, sort_keys=False, default_flow_style=False).rstrip(), "  "),
        markup=False,
        highlight=False,
        soft_wrap=True,
    )
    console.print()


@click.command(name="waiter", help="Explain a waiter by its id.")
@click.argument("waiter_id")
@detail_format_option
def explain_waiter(waiter_id: str, output_format: str) -> None:
    """Print a formatted man-page for a waiter."""
    entry = WAITER_CATALOG.get(waiter_id)
    if entry is None:
        exit_not_found("Waiter", waiter_id, WAITER_CATALOG, "itbench list waiters")

    if output_format != "text":
        emit_structured(entry.model_dump(mode="json", by_alias=True), output_format)
        return

    _render_waiter(entry)
