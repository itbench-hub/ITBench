"""List faults sub-command for ITBench."""

from collections.abc import Mapping
from typing import Any

import click

from rich.markup import escape

from itbench.cli.commands.list._usage import USAGE_COLUMN, add_usage, usage_option
from itbench.cli.render import Column, format_option, render_rows
from itbench.models.fault import FAULT_CATALOG


def _status_cell(row: Mapping[str, Any]) -> str:
    if row["status"] != "retired":
        return "[green]active[/green]"
    reason = row["retired_reason"]
    return f"retired — {escape(reason)}" if reason else "retired"


_COLUMNS = [
    Column("slug", "Slug", no_wrap=True),
    Column("name", "Name"),
    Column("platform", "Platform"),
    Column("tags", "Tags"),
    Column("alerts", "Alerts"),
    Column("status", "Status", cell=_status_cell),
]


@click.command(name="faults", help="List all available faults with optional filtering.")
@click.option("--tag", default=None, help="Filter by tag (e.g. Networking, Deployment).")
@click.option("--platform", default=None, help="Filter by platform (e.g. Kubernetes, OpenShift).")
@usage_option
@format_option
def list_faults(tag: str | None, platform: str | None, show_usage: bool, output_format: str) -> None:
    """List all available faults."""
    rows: list[dict[str, Any]] = []
    for slug, fault in sorted(FAULT_CATALOG.items()):
        if platform and fault.platform.lower() != platform.lower():
            continue
        if tag and tag not in fault.tags:
            continue
        retired = fault.status.retired if fault.status is not None else None
        rows.append({
            "slug": slug,
            "name": fault.name,
            "platform": fault.platform,
            "tags": list(fault.tags),
            "alerts": list(fault.alerts),
            "status": "retired" if retired is not None else "active",
            "retired_reason": retired.reason if retired is not None else None,
        })
    if show_usage:
        add_usage(rows, "slug", "faults")

    render_rows(
        rows,
        [*_COLUMNS, USAGE_COLUMN] if show_usage else _COLUMNS,
        title="Faults",
        footer=f"{len(rows)} fault(s) found.",
        empty_message="[yellow]No faults matched the given filters.[/yellow]",
        output_format=output_format,
        row_style=lambda row: "dim" if row["status"] == "retired" else None,
    )
