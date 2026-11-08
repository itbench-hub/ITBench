"""List applications sub-command for ITBench."""

import click

from itbench.cli.commands.list._usage import USAGE_COLUMN, add_usage, usage_option
from itbench.cli.render import Column, format_option, render_rows
from itbench.models.application import APPLICATION_CATALOG

_COLUMNS = [
    Column("slug", "Slug", style="cyan", no_wrap=True),
    Column("name", "Name"),
    Column("platforms", "Platforms", style="dim"),
    Column("authors", "Authors", style="dim"),
]


@click.command(name="applications", help="List all available applications.")
@click.option("--platform", default=None, help="Filter by platform (e.g. Kubernetes, OpenShift).")
@usage_option
@format_option
def list_applications(platform: str | None, show_usage: bool, output_format: str) -> None:
    """List all available applications."""
    rows = [
        {
            "slug": slug,
            "name": entry.name,
            "platforms": list(entry.platforms),
            "authors": list(entry.authors),
        }
        for slug, entry in sorted(APPLICATION_CATALOG.items())
        if not platform or platform in entry.platforms
    ]
    if show_usage:
        add_usage(rows, "slug", "applications")

    render_rows(
        rows,
        [*_COLUMNS, USAGE_COLUMN] if show_usage else _COLUMNS,
        title="Applications",
        footer=f"{len(rows)} application(s) found.",
        empty_message="[yellow]No applications matched the given filters.[/yellow]",
        output_format=output_format,
    )
