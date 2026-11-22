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
    help="Remove only the applications and leave the agents and tools deployed.",
)
@verbose_option
@click.option(
    "-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt and proceed with undeployment."
)
def undeploy_environment(kubeconfig: str, only: str | None, verbose: bool, yes: bool) -> None:
    """Undeploy the benchmark environment stack (applications, agents and tools) from the cluster.

    Applications are always removed first. The agents (their access controls, admission policies and
    MCP servers) and the tools (and the recorders that run with them) cannot be removed on their own,
    so they are only removed, agents first, when `--only` is not given.

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

    run_step(
        playbook="manage_environment.yaml",
        extra_vars={
            "environment_application_management_enabled": True,
        },
        tags=["uninstall"],
        status="Undeploying applications…",
        failure="Environment undeploy",
        verbose=verbose,
        kubeconfig=kubeconfig,
    )

    if tools_enabled:
        run_step(
            playbook="manage_environment.yaml",
            extra_vars={
                "environment_agent_management_enabled": True,
            },
            tags=["uninstall"],
            status="Undeploying agents…",
            failure="Environment undeploy",
            verbose=verbose,
            kubeconfig=kubeconfig,
        )

        run_step(
            playbook="manage_environment.yaml",
            extra_vars={
                "environment_recorder_management_enabled": True,
            },
            tags=["uninstall"],
            status="Undeploying recorders…",
            failure="Environment undeploy",
            verbose=verbose,
            kubeconfig=kubeconfig,
        )

        run_step(
            playbook="manage_environment.yaml",
            extra_vars={
                "environment_tool_management_enabled": True,
            },
            tags=["uninstall"],
            status="Undeploying tools…",
            failure="Environment undeploy",
            verbose=verbose,
            kubeconfig=kubeconfig,
        )

    console.print("[bold green]Environment undeployed successfully.[/bold green]")
