"""Generate kubeconfig command for ITBench."""

import os

from pathlib import Path

import click
import yaml

from kubernetes.client.exceptions import ApiException  # type: ignore[import-untyped]
from rich.markup import escape

from itbench.cli.render import console, err_console, exit_not_found, fail, kubeconfig_option
from itbench.paths import repository
from itbench.utils.cluster import create_agent_access
from itbench.utils.scenarios import known_scenario_ids

MISSIONS = ("diagnosis", "remediation")
DURATION_VARIABLE = "tools_benchmark_duration_minutes"
MIN_DURATION_MINUTES = 15
MAX_DURATION_MINUTES = 60


def _read_variables(path: Path) -> dict:
    """Return the mapping in the YAML file at *path*, or an empty one when the file does not exist."""
    if not path.is_file():
        return {}
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _benchmark_minutes(scenario_id: int | None) -> int:
    """Return the benchmark duration: the scenario's extra variable if set, otherwise the role default.

    The result is never below :data:`MIN_DURATION_MINUTES`. It may exceed :data:`MAX_DURATION_MINUTES`,
    because a scenario can set a longer benchmark than ``--duration`` accepts.
    """
    minutes = _read_variables(repository.tools_defaults / "benchmark.yaml")[DURATION_VARIABLE]
    if scenario_id is not None:
        scenario_variables = _read_variables(repository.scenarios / str(scenario_id) / "extra_variables.yaml")
        minutes = scenario_variables.get(DURATION_VARIABLE, minutes)
    return max(MIN_DURATION_MINUTES, int(minutes))


def _write_private(path: Path, content: str) -> None:
    """Write *content* to *path* so that only the owner can read it, even when the file already existed."""
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    path.chmod(0o600)


@click.command(name="kubeconfig", help="Generate a short-lived, restricted kubeconfig for an AI agent.")
@click.option(
    "--mission",
    type=click.Choice(MISSIONS),
    required=True,
    help="Access level: diagnosis is read-only, remediation can also change the faulted objects.",
)
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
    help="Directory to write kubeconfig-<mission> to. Defaults to printing the kubeconfig on stdout.",
)
@kubeconfig_option
def generate_kubeconfig_command(
    mission: str, duration: int | None, scenario_id: int | None, output: Path | None, kubeconfig: str
) -> None:
    """Generate a short-lived kubeconfig for the agent ServiceAccount of a mission.

    Talks to the live cluster in the current context of --kubeconfig. The agent can only act in the
    namespaces labelled itbench.io/inject=true. The token cannot be revoked, it stops working when
    it expires. The generated file holds a bearer token, so it is written readable by you only.

    Examples:

    \b
        itbench generate kubeconfig --mission diagnosis --kubeconfig ~/.kube/config > agent.kubeconfig
        itbench generate kubeconfig --mission remediation --duration 30 --kubeconfig ~/.kube/config
        itbench generate kubeconfig --mission remediation --scenario 5 --output ./agent --kubeconfig ~/.kube/config
    """
    if scenario_id is not None:
        known = known_scenario_ids(repository.scenarios)
        if str(scenario_id) not in known:
            exit_not_found("Scenario", str(scenario_id), known, "itbench list scenarios")
        scenario_path = repository.scenarios / str(scenario_id) / "scenario.yaml"
        if not scenario_path.is_file():
            fail(f"[red]Scenario {scenario_id} has no scenario.yaml at {scenario_path}[/red]")
        # stderr, so that the kubeconfig printed on stdout stays valid YAML.
        err_console.print(f"[dim]Loaded configuration from scenario {scenario_id}[/dim]")

    minutes = duration if duration is not None else _benchmark_minutes(scenario_id)

    with console.status("Generating kubeconfig…"):
        try:
            access = create_agent_access(kubeconfig=kubeconfig, mission=mission, minutes=minutes)
        except RuntimeError as exc:
            fail(f"[red]Kubeconfig generation failed:[/red] {escape(str(exc))}")
        except ApiException as exc:
            fail(f"[red]Kubeconfig generation failed:[/red] {escape(str(exc.reason))}")

    content = yaml.safe_dump(access.kubeconfig, sort_keys=False)
    if output is None:
        click.echo(content, nl=False)
        report = err_console
    else:
        output.mkdir(parents=True, exist_ok=True)
        destination = output / f"kubeconfig-{mission}"
        _write_private(destination, content)
        report = console
        report.print(f"[bold green]Kubeconfig written to {escape(str(destination))}.[/bold green]", soft_wrap=True)

    report.print(f"[dim]Mission: {mission}. Expires: {access.expires.isoformat()}.[/dim]")
    report.print(f"[dim]Namespaces: {escape(', '.join(access.namespaces)) or 'none'}.[/dim]")
