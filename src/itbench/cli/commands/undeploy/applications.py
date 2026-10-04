"""Undeploy applications command for ITBench."""

import click

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()


@click.command(name="applications", help="Undeploy sample applications from the cluster.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
def undeploy_applications(kubeconfig: str) -> None:
    """Undeploy sample applications from the cluster.

    Examples:

    \b
        itbench undeploy applications --kubeconfig ~/.kube/config
    """
    with console.status("Undeploying applications…"):
        try:
            run_playbook(
                playbook="manage_applications.yaml",
                extra_vars={"cluster": {"kubeconfig": kubeconfig}},
                tags=["uninstall_applications"],
            )
        except RuntimeError as exc:
            console.print(f"[red]Undeploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Applications undeployed successfully.[/green]")
