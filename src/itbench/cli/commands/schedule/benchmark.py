"""Schedule benchmark command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import console, exit_not_found, kubeconfig_option, verbose_option
from itbench.paths import repository
from itbench.utils.runner import create_run
from itbench.utils.scenarios import known_scenario_ids

WORKFLOW_VARIANTS = ("full", "setup", "teardown")


@click.command(name="benchmark", help="Schedule trials of a scenario on the orchestrator.")
@click.option("--scenario", type=click.INT, required=True, metavar="ID", help="Scenario to run.")
@click.option(
    "--trials",
    type=click.IntRange(min=1),
    default=1,
    show_default=True,
    help="Number of trials. Trials are spread round-robin over the registered environments.",
)
@click.option(
    "--variant",
    type=click.Choice(WORKFLOW_VARIANTS),
    default=WORKFLOW_VARIANTS[0],
    show_default=True,
    help="Which stages of the benchmark to run.",
)
@kubeconfig_option
@verbose_option
def schedule_benchmark(scenario: int, trials: int, variant: str, kubeconfig: str, verbose: bool) -> None:
    """Schedule trials of a scenario on the orchestrator cluster.

    Creates one Argo Workflow per trial from the itbench-scenario-execution WorkflowTemplate. The
    environments are the `environment-<n>-kubeconfig` Secrets registered by
    `itbench configure orchestrator`; trials are assigned to them round-robin. The command does not
    wait for the Workflows to finish.

    Examples:

    \b
        itbench schedule benchmark --scenario 5 --kubeconfig ~/.kube/config
        itbench schedule benchmark --scenario 5 --trials 3 --kubeconfig ~/.kube/config
    """
    known = known_scenario_ids(repository.scenarios)
    if str(scenario) not in known:
        exit_not_found("Scenario", str(scenario), known, "itbench list scenarios")

    extra_vars = {
        "argo_benchmark_scenario": str(scenario),
        "argo_benchmark_trials": trials,
        "argo_benchmark_variant": variant,
    }

    run_id, extra_vars_file = create_run(extra_vars)
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]", soft_wrap=True)

    run_step(
        playbook="manage_orchestrator.yaml",
        extra_vars=extra_vars,
        tags=["schedule"],
        status="Scheduling benchmark…",
        failure="Benchmark scheduling",
        verbose=verbose,
        run_id=run_id,
        kubeconfig=kubeconfig,
    )

    console.print(f"[bold green]Scheduled {trials} trial(s) of scenario {scenario}.[/bold green]")
