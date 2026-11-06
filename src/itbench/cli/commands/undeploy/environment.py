"""Undeploy environment command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import confirm_or_cancel, console, kubeconfig_option, verbose_option


@click.command(name="environment", help="Undeploy the benchmark environment stack from the cluster.")
@kubeconfig_option
@click.option(
    "--only",
    type=click.Choice(["applications"]),
    default=None,
    help="Remove only the applications and leave the tools deployed.",
)
@verbose_option
@click.option(
    "-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt and proceed with undeployment."
)
def undeploy_environment(kubeconfig: str, only: str | None, verbose: bool, yes: bool) -> None:
    """Undeploy the benchmark environment stack (applications and tools) from the cluster.

    Applications are always removed first. Tools (and the recorders that run with them) cannot be
    removed on their own, so they are only removed when `--only` is not given.

    Examples:

    \b
        itbench undeploy environment --kubeconfig ~/.kube/config
        itbench undeploy environment -y --kubeconfig ~/.kube/config
        itbench undeploy environment --only applications --kubeconfig ~/.kube/config
    """
    tools_enabled = only is None
    target = "the environment" if tools_enabled else "the environment applications"

    if not confirm_or_cancel(f"Are you sure you want to undeploy {target}?", yes, cancelled="Undeployment cancelled."):
        return

    cluster_config = {"cluster": {"kubeconfig": kubeconfig}}

    run_step(
        playbook="manage_environment.yaml",
        extra_vars={
            **cluster_config,
            "environment_tool_management_enabled": False,
            "environment_application_management_enabled": True,
        },
        tags=["uninstall"],
        status="Undeploying applications…",
        failure="Environment undeploy",
        verbose=verbose,
    )

    if tools_enabled:
        run_step(
            playbook="manage_environment.yaml",
            extra_vars={
                **cluster_config,
                "environment_tool_management_enabled": True,
                "environment_application_management_enabled": False,
            },
            tags=["uninstall"],
            status="Undeploying tools…",
            failure="Environment undeploy",
            verbose=verbose,
        )

    console.print("[bold green]Environment undeployed successfully.[/bold green]")
