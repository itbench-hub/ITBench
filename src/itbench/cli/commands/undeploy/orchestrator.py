"""Undeploy orchestrator command for ITBench."""

import click
import questionary

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()


@click.command(name="orchestrator", help="Undeploy the Argo orchestration stack from the cluster.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt and proceed with undeployment.")
def undeploy_orchestrator(kubeconfig: str, yes: bool) -> None:
    """Undeploy the Argo orchestration stack (Argo Workflows and Argo Events) from the cluster.

    Examples:

    \b
        itbench undeploy orchestrator --kubeconfig ~/.kube/config
        itbench undeploy orchestrator -y --kubeconfig ~/.kube/config
    """
    if not yes:
        confirmed = questionary.confirm(
            "Are you sure you want to undeploy the orchestrator?",
            default=False,
        ).ask()
        if not confirmed:
            console.print("[dim]Undeployment cancelled.[/dim]")
            return

    extra_vars = {"cluster": {"kubeconfig": kubeconfig}}

    with console.status("Undeploying orchestrator…"):
        try:
            run_playbook(
                playbook="manage_orchestrator.yaml",
                extra_vars=extra_vars,
                tags=["uninstall"],
            )
        except RuntimeError as exc:
            console.print(f"[red]Orchestrator undeploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Orchestrator undeployed successfully.[/green]")
