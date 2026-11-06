"""Inject faults command for ITBench."""

from concurrent.futures import ThreadPoolExecutor

import click
import yaml

from rich.markup import escape

from itbench.cli.render import console, err_console, exit_not_found, fail, kubeconfig_option, verbose_option
from itbench.paths import repository
from itbench.utils.runner import PlaybookError, run_playbook
from itbench.utils.scenarios import known_scenario_ids


def _fault_group_count(scenario_id: int) -> int:
    """Return the number of fault groups in the scenario, exiting if the scenario is unknown or unreadable."""
    known = known_scenario_ids(repository.scenarios)
    if str(scenario_id) not in known:
        exit_not_found("Scenario", str(scenario_id), known, "itbench list scenarios")

    scenario_path = repository.scenarios / str(scenario_id) / "scenario.yaml"
    if not scenario_path.is_file():
        fail(f"[red]Scenario {scenario_id} has no scenario.yaml at {escape(str(scenario_path))}[/red]")

    data = yaml.safe_load(scenario_path.read_text(encoding="utf-8")) or {}
    return len(data.get("faults") or [])


def _inject_group(scenario_id: int, index: int, kubeconfig: str, verbose: bool) -> PlaybookError | None:
    """Inject one fault group, returning the error instead of raising it so groups can run side by side."""
    try:
        run_playbook(
            playbook="manage_faults.yaml",
            extra_vars={"scenario_id": scenario_id, "faults_index": index},
            tags=["inject_faults"],
            verbose=verbose,
            kubeconfig=kubeconfig,
        )
    except PlaybookError as exc:
        return exc
    return None


@click.command(name="faults", help="Inject all faults of a scenario into the cluster.")
@click.option(
    "--scenario",
    "scenario_id",
    type=click.INT,
    required=True,
    metavar="ID",
    help="Scenario whose faults are injected.",
)
@kubeconfig_option
@verbose_option
def inject_faults(scenario_id: int, kubeconfig: str, verbose: bool) -> None:
    """Inject all faults of a scenario into the cluster.

    The fault groups of the scenario are injected concurrently, because the pre and post injection
    waiters of one group can block while another group is being injected.

    Examples:

    \b
        itbench inject faults --scenario 5 --kubeconfig ~/.kube/config
        itbench inject faults -v --scenario 5 --kubeconfig ~/.kube/config
    """
    group_count = _fault_group_count(scenario_id)
    if group_count == 0:
        fail(f"[red]Scenario {scenario_id} does not define any faults.[/red]")

    console.print(f"[dim]Injecting {group_count} fault group(s)…[/dim]")
    with ThreadPoolExecutor(max_workers=group_count) as pool:
        futures = [pool.submit(_inject_group, scenario_id, index, kubeconfig, verbose) for index in range(group_count)]
        errors = [future.result() for future in futures]

    failed = [(index, exc) for index, exc in enumerate(errors) if exc is not None]
    for index, exc in failed:
        if exc.output:
            err_console.print(exc.output, markup=False, highlight=False, soft_wrap=True)
        err_console.print(f"[red]Fault group {index} failed:[/red] {escape(str(exc))}")
    if failed:
        raise SystemExit(1)

    console.print("[bold green]Faults injected successfully.[/bold green]")
