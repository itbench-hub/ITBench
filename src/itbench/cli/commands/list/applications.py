"""List apps sub-command for ITBench."""

import click

from rich import box
from rich.console import Console
from rich.table import Table

from itbench.models.application import APPLICATION_CATALOG

console = Console()


@click.command(name="apps", help="List all available applications.")
@click.option("--platform", default=None, help="Filter by platform (e.g. Kubernetes, OpenShift).")
def list_applications(platform: str | None) -> None:
    """List all available applications."""
    table = Table(
        title="Applications",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold",
    )
    table.add_column("Slug", style="cyan", no_wrap=True)
    table.add_column("Name")
    table.add_column("Platforms", style="dim")
    table.add_column("Authors", style="dim")

    rows = [
        (slug, entry.name, ", ".join(entry.platforms), ", ".join(entry.authors))
        for slug, entry in APPLICATION_CATALOG.items()
        if not platform or platform in entry.platforms
    ]

    if not rows:
        console.print("[yellow]No applications matched the given filters.[/yellow]")
        return

    for row in rows:
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(rows)} application(s) found.[/dim]")
