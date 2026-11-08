"""List waiters sub-command for ITBench."""

import click

from itbench.cli.commands.list._usage import USAGE_COLUMN, add_usage, usage_option
from itbench.cli.render import Column, format_option, render_rows
from itbench.models.waiter import WAITER_CATALOG

_COLUMNS = [
    Column("id", "ID", style="cyan", no_wrap=True),
    Column("name", "Name"),
    Column("platforms", "Platforms", style="dim"),
    Column("description", "Description"),
]


@click.command(name="waiters", help="List all built-in waiters.")
@usage_option
@format_option
def list_waiters(show_usage: bool, output_format: str) -> None:
    """List all built-in waiters."""
    rows = [
        {
            "id": waiter_id,
            "name": entry.name,
            "platforms": list(entry.platforms),
            "description": entry.description,
        }
        for waiter_id, entry in sorted(WAITER_CATALOG.items())
    ]
    if show_usage:
        add_usage(rows, "id", "waiters")

    render_rows(
        rows,
        [*_COLUMNS, USAGE_COLUMN] if show_usage else _COLUMNS,
        title="Waiters",
        footer=f"{len(rows)} waiter(s) available.",
        empty_message="[yellow]No waiters available.[/yellow]",
        output_format=output_format,
    )
