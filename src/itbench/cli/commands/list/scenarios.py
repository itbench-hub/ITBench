"""List scenarios sub-command for ITBench."""

from typing import Any

import click

from rich.markup import escape

from itbench.cli.render import Column, err_console, format_option, render_rows
from itbench.paths import library
from itbench.utils.scenarios import load_scenario_docs, summarize_scenario

_COLUMNS = [
    Column("id", "ID", style="cyan", no_wrap=True),
    Column("domains", "Domains", style="dim"),
    Column("applications", "Applications", style="dim"),
    Column("faults", "Faults", style="dim"),
]


def _warn_invalid(scenario_id: str, exc: Exception) -> None:
    err_console.print(f"[yellow]Skipped scenario {escape(scenario_id)}: {escape(str(exc))}[/yellow]")


@click.command(name="scenarios", help="List all benchmark scenarios.")
@format_option
def list_scenarios(output_format: str) -> None:
    """List all benchmark scenarios."""
    rows: list[dict[str, Any]] = [
        summarize_scenario(scenario_id, data)
        for scenario_id, data in load_scenario_docs(library.scenarios, on_error=_warn_invalid)
    ]

    render_rows(
        rows,
        _COLUMNS,
        title="Scenarios",
        footer=f"{len(rows)} scenario(s) found.",
        empty_message="[yellow]No scenarios found.[/yellow]",
        output_format=output_format,
    )
