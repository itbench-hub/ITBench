"""Remove faults command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import console, kubeconfig_option, verbose_option
from itbench.utils.runner import create_run


@click.command(name="faults", help="Remove injected faults from the cluster.")
@kubeconfig_option
@verbose_option
def remove_faults(kubeconfig: str, verbose: bool) -> None:
    """Remove injected faults from the cluster and uncordon any cordoned worker nodes.

    Examples:

    \b
        itbench remove faults --kubeconfig ~/.kube/config
        itbench remove faults -v --kubeconfig ~/.kube/config
    """
    extra_vars: dict = {}

    run_id, extra_vars_file = create_run(extra_vars)
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]", soft_wrap=True)

    run_step(
        playbook="manage_faults.yaml",
        extra_vars=extra_vars,
        tags=["remove_faults"],
        status="Removing faults…",
        failure="Fault removal",
        verbose=verbose,
        run_id=run_id,
        kubeconfig=kubeconfig,
    )

    console.print("[bold green]Faults removed successfully.[/bold green]")
