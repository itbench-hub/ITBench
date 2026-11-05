"""Explain application sub-command for ITBench."""

import textwrap

import click
import yaml

from rich.markup import escape
from rich.panel import Panel

from itbench.cli.render import console, detail_format_option, emit_structured, exit_not_found
from itbench.models.application import APPLICATION_CATALOG, Application


def _render_application(slug: str, entry: Application) -> None:
    """Render an application as a Rich man-page."""
    console.print()
    console.print(Panel(
        f"[bold]{escape(entry.name)}[/bold]\n\n"
        f"[dim]slug:[/dim] {escape(slug)}   "
        f"[dim]platforms:[/dim] {escape(', '.join(entry.platforms))}",
        title="[bold green]APPLICATION[/bold green]",
        border_style="green",
    ))

    console.print("[bold]DESCRIPTION[/bold]")
    console.print(f"  {escape(entry.description)}\n")

    console.print("[bold]REPOSITORY[/bold]")
    console.print(f"  {escape(entry.repository)}\n")

    if entry.aliases:
        console.print("[bold]ALIASES[/bold]")
        console.print(f"  {escape(', '.join(entry.aliases))}\n")

    if entry.authors:
        console.print("[bold]AUTHORS[/bold]")
        console.print(f"  {escape(', '.join(entry.authors))}\n")

    if entry.resources:
        console.print("[bold]RESOURCES[/bold]")
        for url in entry.resources:
            console.print(f"  {escape(url)}")
        console.print()

    example = {"environment": {"applications": [{"id": slug}]}}
    console.print("[bold]SCENARIO YAML EXAMPLE[/bold]")
    console.print("  # In library/scenarios/<id>/scenario.yaml", markup=False)
    console.print(
        textwrap.indent(yaml.safe_dump(example, sort_keys=False, default_flow_style=False).rstrip(), "  "),
        markup=False,
        highlight=False,
        soft_wrap=True,
    )
    console.print()


@click.command(name="application", help="Explain an application by its slug.")
@click.argument("slug")
@detail_format_option
def explain_application(slug: str, output_format: str) -> None:
    """Print a formatted man-page for an application."""
    entry = APPLICATION_CATALOG.get(slug)
    if entry is None:
        exit_not_found("Application", slug, APPLICATION_CATALOG, "itbench list applications")

    if output_format != "text":
        emit_structured(entry.model_dump(mode="json"), output_format)
        return

    _render_application(slug, entry)
