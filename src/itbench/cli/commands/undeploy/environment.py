"""Undeploy environment command for ITBench."""

import click
import questionary

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()


@click.command(name="environment", help="Undeploy the benchmark environment stack from the cluster.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
@click.option("--only", type=click.Choice(["applications", "tools"]), default=None, help="Limit undeployment to a specific subsystem.")
@click.option("-y", "--yes", is_flag=True, default=False, help="Skip confirmation prompt and proceed with undeployment.")
def undeploy_environment(kubeconfig: str, only: str | None, yes: bool) -> None:
    """Undeploy the benchmark environment stack (applications and tools) from the cluster.

    Examples:

    \b
        itbench undeploy environment --kubeconfig ~/.kube/config
        itbench undeploy environment -y --kubeconfig ~/.kube/config
        itbench undeploy environment --only applications --kubeconfig ~/.kube/config
        itbench undeploy environment --only tools --kubeconfig ~/.kube/config
    """
    tools_enabled = (only == "tools") or (only is None)
    applications_enabled = True

    if not yes:
        confirmed = questionary.confirm(
            "Are you sure you want to undeploy the environment?",
            default=False,
        ).ask()
        if not confirmed:
            console.print("[dim]Undeployment cancelled.[/dim]")
            return

    cluster_config = {"cluster": {"kubeconfig": kubeconfig}}

    with console.status("Undeploying environment…"):
        try:
            run_playbook(
                playbook="manage_environment.yaml",
                extra_vars={
                    **cluster_config,
                    "environment_tool_management_enabled": False,
                    "environment_application_management_enabled": True,
                },
                tags=["uninstall"],
            )
        except RuntimeError as exc:
            console.print(f"[red]Environment undeploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

        if tools_enabled:
            try:
                run_playbook(
                    playbook="manage_environment.yaml",
                    extra_vars={
                        **cluster_config,
                        "environment_tool_management_enabled": True,
                        "environment_application_management_enabled": False,
                    },
                    tags=["uninstall"],
                )
            except RuntimeError as exc:
                console.print(f"[red]Environment undeploy failed:[/red] {exc}")
                raise SystemExit(1) from exc

    console.print("[bold green]Environment undeployed successfully.[/bold green]")
