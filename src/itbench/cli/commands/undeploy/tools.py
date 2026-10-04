"""Undeploy tools command for ITBench."""

import click

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()


@click.command(name="tools", help="Undeploy the observability and tooling stack from the cluster.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
def undeploy_tools(kubeconfig: str) -> None:
    """Undeploy the observability and tooling stack from the cluster.

    Examples:

    \b
        itbench undeploy tools --kubeconfig ~/.kube/config
    """
    with console.status("Undeploying tools…"):
        try:
            run_playbook(
                playbook="manage_tools.yaml",
                extra_vars={"cluster": {"kubeconfig": kubeconfig}},
                tags=["uninstall_tools"],
            )
        except RuntimeError as exc:
            console.print(f"[red]Undeploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Tools undeployed successfully.[/green]")
