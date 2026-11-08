"""Undeploy orchestrator command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import confirm_or_cancel, console, kubeconfig_option, verbose_option


@click.command(name="orchestrator", help="Undeploy the Argo orchestration stack from the cluster.")
@kubeconfig_option
@verbose_option
@click.option(
    "-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt and proceed with undeployment."
)
def undeploy_orchestrator(kubeconfig: str, verbose: bool, yes: bool) -> None:
    """Undeploy the Argo orchestration stack (Argo Workflows and Argo Events) from the cluster.

    Examples:

    \b
        itbench undeploy orchestrator --kubeconfig ~/.kube/config
        itbench undeploy orchestrator -y --kubeconfig ~/.kube/config
    """
    if not confirm_or_cancel(
        "Are you sure you want to undeploy the orchestrator?", yes, cancelled="Undeployment cancelled."
    ):
        return

    run_step(
        playbook="manage_orchestrator.yaml",
        extra_vars={},
        tags=["uninstall"],
        status="Undeploying orchestrator…",
        failure="Orchestrator undeploy",
        verbose=verbose,
        kubeconfig=kubeconfig,
    )

    console.print("[green]Orchestrator undeployed successfully.[/green]")
