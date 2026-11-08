"""List scenarios sub-command for ITBench."""

from typing import Any

import click

from itbench.cli.render import Column, format_option, render_rows, warn_skipped_scenario
from itbench.paths import repository
from itbench.utils.scenarios import load_scenario_docs, summarize_scenario

_COLUMNS = [
    Column("id", "ID", style="cyan", no_wrap=True),
    Column("domains", "Domains", style="dim"),
    Column("applications", "Applications", style="dim"),
    Column("faults", "Faults", style="dim"),
]


@click.command(name="scenarios", help="List all benchmark scenarios.")
@format_option
def list_scenarios(output_format: str) -> None:
    """List all benchmark scenarios."""
    rows: list[dict[str, Any]] = [
        summarize_scenario(scenario_id, data)
        for scenario_id, data in load_scenario_docs(repository.scenarios, on_error=warn_skipped_scenario)
    ]

    render_rows(
        rows,
        _COLUMNS,
        title="Scenarios",
        footer=f"{len(rows)} scenario(s) found.",
        empty_message="[yellow]No scenarios found.[/yellow]",
        output_format=output_format,
    )
