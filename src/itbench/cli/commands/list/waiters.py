"""List waiters sub-command for ITBench."""

import click

from rich import box
from rich.console import Console
from rich.table import Table

from itbench.models.waiter import WAITER_CATALOG

console = Console()


@click.command(name="waiters", help="List all built-in waiters.")
def list_waiters() -> None:
    """List all built-in waiters."""
    table = Table(
        title="Waiters",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold",
    )
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Platforms", style="dim")
    table.add_column("Description")

    for waiter_id, entry in WAITER_CATALOG.items():
        table.add_row(waiter_id, entry.name, ", ".join(entry.platforms), entry.description)

    console.print(table)
    console.print(f"[dim]{len(WAITER_CATALOG)} waiter(s) available.[/dim]")
