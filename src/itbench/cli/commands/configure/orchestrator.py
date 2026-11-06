"""Configure orchestrator command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import console, kubeconfig_option, verbose_option
from itbench.utils.runner import create_run


@click.command(name="orchestrator", help="Configure the orchestrator cluster to run benchmarks.")
@kubeconfig_option
@verbose_option
def configure_orchestrator_command(kubeconfig: str, verbose: bool) -> None:
    """Configure the orchestrator cluster (the cluster that runs Argo Workflows) for ITBench.

    Registers the environment clusters listed in the `stack.environments.kubeconfigs` group variable as
    `environment-<n>-kubeconfig` Secrets, stores the S3 credentials created by
    `itbench generate variables aws`, and applies the `itbench-scenario-execution` WorkflowTemplate.
    Run `itbench deploy orchestrator` first.

    Examples:

    \b
        itbench configure orchestrator --kubeconfig ~/.kube/config
        itbench configure orchestrator -v --kubeconfig ~/.kube/config
    """
    extra_vars: dict = {}

    run_id, extra_vars_file = create_run(extra_vars)
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]", soft_wrap=True)

    run_step(
        playbook="manage_orchestrator.yaml",
        extra_vars=extra_vars,
        tags=["configure"],
        status="Configuring orchestrator…",
        failure="Orchestrator configuration",
        verbose=verbose,
        run_id=run_id,
        kubeconfig=kubeconfig,
    )

    console.print("[bold green]Orchestrator configured successfully.[/bold green]")
