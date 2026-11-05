"""List applications sub-command for ITBench."""

import click

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
@format_option
def list_applications(platform: str | None, output_format: str) -> None:
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

    render_rows(
        rows,
        _COLUMNS,
        title="Applications",
        footer=f"{len(rows)} application(s) found.",
        empty_message="[yellow]No applications matched the given filters.[/yellow]",
        output_format=output_format,
    )
