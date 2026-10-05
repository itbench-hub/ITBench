"""Prepare cluster command for ITBench."""

import click
from rich.console import Console

from itbench.utils.cluster import prepare_cluster

console = Console()


@click.command(name="cluster", help="Prepare Kubernetes cluster by approving kubelet CSRs and partitioning worker nodes.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
@click.option("--context", default=None, metavar="NAME", help="Kubeconfig context to use.")
def prepare_cluster_command(kubeconfig: str, context: str | None) -> None:
    """Prepare a Kubernetes cluster for ITBench scenarios.

    Approves pending kubelet-serving certificate requests and partitions worker nodes
    into tool nodes and sandbox nodes (labeled with node-role.itbench.io/sandbox=true).

    Examples:

    \b
        itbench prepare cluster --kubeconfig ~/.kube/config
        itbench prepare cluster --kubeconfig ~/.kube/config --context kind-itbench
    """
    with console.status("Preparing cluster…"):
        try:
            prepare_cluster(kubeconfig=kubeconfig, context=context)
        except RuntimeError as exc:
            console.print(f"[red]Cluster preparation failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[bold green]Cluster prepared successfully.[/bold green]")
