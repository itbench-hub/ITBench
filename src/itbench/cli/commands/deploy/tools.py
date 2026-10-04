"""Deploy tools command for ITBench."""

import click

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()


@click.command(name="tools", help="Deploy the observability and tooling stack onto the cluster.")
@click.option("--scenario", "scenario_id", default=None, metavar="ID", help="Derive tools config from a scenario definition.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
def deploy_tools(scenario_id: str | None, kubeconfig: str) -> None:
    """Deploy the observability and tooling stack onto the cluster.

    When ``--scenario`` is provided the tools configuration is derived from
    the scenario definition.

    Examples:

    \b
        itbench deploy tools --scenario 5 --kubeconfig ~/.kube/config
        itbench deploy tools --kubeconfig ~/.kube/config
    """
    extra_vars: dict = {"cluster": {"kubeconfig": kubeconfig}}
    if scenario_id:
        extra_vars["scenario_id"] = scenario_id

    with console.status("Deploying tools…"):
        try:
            run_playbook(
                playbook="manage_tools.yaml",
                extra_vars=extra_vars,
                tags=["install_tools"],
            )
        except RuntimeError as exc:
            console.print(f"[red]Deploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Tools deployed successfully.[/green]")
