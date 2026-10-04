"""Discover endpoints command for ITBench."""

import click

from rich.console import Console
from rich.table import Table

from itbench.utils.endpoints import discover_endpoints

console = Console()


@click.command(name="endpoints", help="Discover external endpoints for the installed tools stack.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
@click.option("--platform", required=True, type=click.Choice(["kubernetes", "openshift"]), envvar="ITBENCH_PLATFORM", help="Cluster platform.")
def endpoints(kubeconfig: str, platform: str) -> None:
    """Resolve and print external URLs for all installed tools.

    Queries the Kubernetes API directly to resolve endpoints via HTTPRoutes
    (Kubernetes) or Routes (OpenShift). Tools not found on the cluster are
    silently skipped.

    Examples:

    \b
        itbench discover endpoints --kubeconfig ~/.kube/config --platform kubernetes
        itbench discover endpoints --kubeconfig ~/.kube/config --platform openshift
    """
    with console.status("Resolving tool endpoints…"):
        try:
            results = discover_endpoints(kubeconfig=kubeconfig, platform=platform)
        except RuntimeError as exc:
            console.print(f"[red]Endpoint discovery failed:[/red] {exc}")
            raise SystemExit(1) from exc

    if not results:
        console.print("[yellow]No tool endpoints found. Ensure the tools stack is deployed.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Tool", style="cyan", no_wrap=True)
    table.add_column("URL")

    for ep in results:
        for url in ep.urls:
            table.add_row(ep.tool, url)

    console.print(table)
