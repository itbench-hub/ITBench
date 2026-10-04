"""Explain app sub-command for ITBench."""

import click

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from itbench.models.application import APPLICATION_CATALOG

console = Console()


def _render_application(slug: str, entry) -> None:
    """Render an application as a Rich man-page."""
    console.print()
    console.print(Panel(
        f"[bold]{escape(entry.name)}[/bold]\n\n"
        f"[dim]slug:[/dim] {slug}   "
        f"[dim]platforms:[/dim] {escape(', '.join(entry.platforms))}",
        title="[bold green]APPLICATION[/bold green]",
        border_style="green",
    ))

    console.print("[bold]DESCRIPTION[/bold]")
    console.print(f"  {entry.description}\n")

    console.print("[bold]REPOSITORY[/bold]")
    console.print(f"  {entry.repository}\n")

    if entry.authors:
        console.print("[bold]AUTHORS[/bold]")
        console.print(f"  {', '.join(entry.authors)}\n")

    if entry.resources:
        console.print("[bold]RESOURCES[/bold]")
        for url in entry.resources:
            console.print(f"  {url}")
        console.print()


@click.command(name="app", help="Explain an application by its slug.")
@click.argument("slug")
def explain_application(slug: str) -> None:
    """Print a formatted man-page for an application."""
    entry = APPLICATION_CATALOG.get(slug)
    if entry is None:
        console.print(f"[red]Application '[bold]{slug}[/bold]' not found.[/red]")
        console.print("[dim]Run `itbench list apps` to see available application slugs.[/dim]")
        raise SystemExit(1)
    _render_application(slug, entry)
