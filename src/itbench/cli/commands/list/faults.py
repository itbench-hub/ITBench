"""List faults sub-command for ITBench."""

import click

from rich import box
from rich.console import Console
from rich.table import Table

from itbench.models.fault import FAULT_CATALOG

console = Console()


@click.command(name="faults", help="List all available faults with optional filtering.")
@click.option("--tag", default=None, help="Filter by tag (e.g. Networking, Deployment).")
@click.option("--platform", default=None, help="Filter by platform (e.g. Kubernetes, OpenShift).")
def list_faults(tag: str | None, platform: str | None) -> None:
    """List all available faults."""
    table = Table(
        title="Faults",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        header_style="bold",
    )
    table.add_column("Slug", no_wrap=True)
    table.add_column("Name")
    table.add_column("Platform")
    table.add_column("Tags")
    table.add_column("Alerts")
    table.add_column("Status")

    rows = []
    for slug, fault in sorted(FAULT_CATALOG.items()):
        if platform and fault.platform.lower() != platform.lower():
            continue
        if tag and tag not in fault.tags:
            continue
        rows.append((slug, fault))

    if not rows:
        console.print("[yellow]No faults matched the given filters.[/yellow]")
        return

    for slug, fault in rows:
        retired = fault.status is not None and fault.status.retired is not None
        alerts = ", ".join(fault.alerts) if fault.alerts else ""
        tags = ", ".join(fault.tags)
        if retired:
            reason = fault.status.retired.reason or ""
            status_cell = f"[dim]retired[/dim]" + (f" [dim]— {reason}[/dim]" if reason else "")
            table.add_row(
                f"[dim]{slug}[/dim]",
                f"[dim]{fault.name}[/dim]",
                f"[dim]{fault.platform}[/dim]",
                f"[dim]{tags}[/dim]",
                f"[dim]{alerts}[/dim]",
                status_cell,
            )
        else:
            table.add_row(slug, fault.name, fault.platform, tags, alerts, "[green]active[/green]")

    console.print(table)
    console.print(f"[dim]{len(rows)} fault(s) found.[/dim]")
