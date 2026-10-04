"""Discover targets command for ITBench."""

import click

from rich.console import Console
from rich.table import Table

from itbench.utils.manifests import discover_workloads

console = Console()


@click.command(name="targets", help="Discover targetable workloads for all applications.")
@click.option("--app", "app_id", default=None, metavar="SLUG", help="Limit discovery to a single application slug.")
def targets(app_id: str | None) -> None:
    """Run the discovery playbook and print all targetable workloads as a table.

    Invokes ``discover_applications.yaml`` via ansible-runner, which renders
    each application's Helm chart / manifests into ``.itbench/discovery/``.
    Results are printed as a Rich table grouped by application.

    Examples:

    \b
        itbench discover targets
        itbench discover targets --app opentelemetry-demo
    """
    with console.status("Running discovery playbook…"):
        try:
            workloads_by_app = discover_workloads(app_id=app_id)
        except RuntimeError as exc:
            console.print(f"[red]Discovery failed:[/red] {exc}")
            raise SystemExit(1) from exc

    if not workloads_by_app:
        console.print("[yellow]No workloads discovered.[/yellow]")
        return

    for slug, workloads in sorted(workloads_by_app.items()):
        table = Table(title=slug, show_header=True, header_style="bold")
        table.add_column("Kind", style="cyan", no_wrap=True)
        table.add_column("Name")
        table.add_column("Namespace", style="dim")

        for w in workloads:
            table.add_row(w.kind, w.name, w.namespace or "")

        console.print(table)
