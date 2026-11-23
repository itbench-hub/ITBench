"""Generate bundle command for ITBench."""

import json

from pathlib import Path

import click

from kubernetes.client.exceptions import ApiException  # type: ignore[import-untyped]
from rich.markup import escape

from itbench.cli.commands.generate.kubeconfig import (
    DURATION_VARIABLE,
    MAX_DURATION_MINUTES,
    MIN_DURATION_MINUTES,
    MISSIONS,
    _benchmark_minutes,
    _write_private,
)
from itbench.cli.render import console, err_console, exit_not_found, fail, kubeconfig_option
from itbench.paths import repository
from itbench.utils.cluster import create_agent_access, read_agent_endpoints
from itbench.utils.scenarios import known_scenario_ids

BUNDLE_FILE = "bundle.json"


@click.command(name="bundle", help="Generate the MCP endpoints and agent kubeconfigs for the agent runner.")
@click.option(
    "--duration",
    type=click.IntRange(MIN_DURATION_MINUTES, MAX_DURATION_MINUTES),
    default=None,
    metavar="MINUTES",
    help=(
        f"Token lifetime in minutes ({MIN_DURATION_MINUTES}-{MAX_DURATION_MINUTES}). "
        f"Defaults to {DURATION_VARIABLE} from the scenario, then from the tools role (15)."
    ),
)
@click.option(
    "--scenario",
    "scenario_id",
    type=click.INT,
    default=None,
    metavar="ID",
    help="Derive configuration from a scenario definition.",
)
@click.option(
    "--output",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    metavar="DIRECTORY",
    help=f"Directory to write {BUNDLE_FILE} to. Defaults to printing the bundle on stdout.",
)
@kubeconfig_option
def generate_bundle_command(
    duration: int | None, scenario_id: int | None, output: Path | None, kubeconfig: str
) -> None:
    """Generate the bundle an agent runner needs: MCP endpoints, authentication and kubeconfigs.

    Reads the MCP server addresses, the CA certificate and the bearer token that `deploy environment`
    stored in the cluster, and issues a short-lived kubeconfig for each agent that was deployed. A server
    that is not installed, or an agent that was not deployed, is null. The bundle holds credentials, so
    it is written readable by you only. The tokens cannot be revoked, they stop working when they expire.

    Examples:

    \b
        itbench generate bundle --kubeconfig ~/.kube/config > bundle.json
        itbench generate bundle --duration 30 --output ./agent --kubeconfig ~/.kube/config
    """
    if scenario_id is not None:
        known = known_scenario_ids(repository.scenarios)
        if str(scenario_id) not in known:
            exit_not_found("Scenario", str(scenario_id), known, "itbench list scenarios")
        # stderr, so that the bundle printed on stdout stays valid JSON.
        err_console.print(f"[dim]Loaded configuration from scenario {scenario_id}[/dim]")

    minutes = duration if duration is not None else _benchmark_minutes(scenario_id)

    with console.status("Generating bundle…"):
        try:
            endpoints = read_agent_endpoints(kubeconfig=kubeconfig)
        except RuntimeError as exc:
            fail(f"[red]Bundle generation failed:[/red] {escape(str(exc))}")
        except ApiException as exc:
            fail(f"[red]Bundle generation failed:[/red] {escape(str(exc.reason))}")

        kubeconfigs: dict[str, dict | None] = {}
        for mission in MISSIONS:
            try:
                access = create_agent_access(kubeconfig=kubeconfig, mission=mission, minutes=minutes)
                kubeconfigs[mission] = access.kubeconfig
            except RuntimeError as exc:
                kubeconfigs[mission] = None
                err_console.print(f"[yellow]No {mission} agent:[/yellow] {escape(str(exc))}")
            except ApiException as exc:
                fail(f"[red]Bundle generation failed:[/red] {escape(str(exc.reason))}")

    content = json.dumps(
        {
            "mcp_servers": endpoints.mcp_servers,
            "headers": {"Authorization": f"Bearer {endpoints.token}"},
            "ca_certificate": endpoints.ca_certificate,
            "kubeconfigs": kubeconfigs,
        },
        indent=2,
    )
    if output is None:
        click.echo(content)
        report = err_console
    else:
        output.mkdir(parents=True, exist_ok=True)
        destination = output / BUNDLE_FILE
        _write_private(destination, content + "\n")
        report = console
        report.print(f"[bold green]Bundle written to {escape(str(destination))}.[/bold green]", soft_wrap=True)

    report.print(f"[dim]Tokens expire in {minutes} minutes.[/dim]")
