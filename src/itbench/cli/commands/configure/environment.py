"""Configure environment command for ITBench."""

import click

from rich.markup import escape

from itbench.cli.render import console, fail, kubeconfig_option
from itbench.utils.cluster import configure_environment


@click.command(name="environment", help="Taint the sandbox worker nodes of an environment cluster.")
@kubeconfig_option
def configure_environment_command(kubeconfig: str) -> None:
    """Configure an environment cluster (the cluster under test) for ITBench.

    Splits the worker nodes into tool nodes and sandbox nodes and taints the sandbox nodes with
    itbench.io/sandbox=true:NoSchedule. Workloads that should run in the sandbox must tolerate it.
    This acts on one environment cluster; `itbench configure orchestrator` registers environment
    clusters on the orchestrator. Uses the current context of the kubeconfig.

    Examples:

    \b
        itbench configure environment --kubeconfig ~/.kube/config
    """
    with console.status("Configuring environment…"):
        try:
            configure_environment(kubeconfig=kubeconfig)
        except RuntimeError as exc:
            fail(f"[red]Environment configuration failed:[/red] {escape(str(exc))}")

    console.print("[bold green]Environment configured successfully.[/bold green]")
