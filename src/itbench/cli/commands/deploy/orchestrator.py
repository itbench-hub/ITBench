"""Deploy orchestrator command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import console, kubeconfig_option, verbose_option
from itbench.utils.runner import create_run


@click.command(name="orchestrator", help="Deploy the Argo orchestration stack onto the cluster.")
@kubeconfig_option
@verbose_option
def deploy_orchestrator(kubeconfig: str, verbose: bool) -> None:
    """Deploy the Argo orchestration stack (Argo Workflows and Argo Events) onto the cluster.

    Examples:

    \b
        itbench deploy orchestrator --kubeconfig ~/.kube/config
        itbench deploy orchestrator -v --kubeconfig ~/.kube/config
    """
    extra_vars = {}

    run_id, extra_vars_file = create_run(extra_vars)
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]", soft_wrap=True)

    run_step(
        playbook="manage_orchestrator.yaml",
        extra_vars=extra_vars,
        tags=["install"],
        status="Deploying orchestrator…",
        failure="Orchestrator deploy",
        verbose=verbose,
        run_id=run_id,
        kubeconfig=kubeconfig,
    )

    console.print("[green]Orchestrator deployed successfully.[/green]")
