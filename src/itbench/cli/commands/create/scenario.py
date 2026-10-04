"""CLI command to create and scaffold a new scenario."""

from pathlib import Path

import click
import questionary
import yaml

from rich.console import Console

from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.kubernetes import (
    KubernetesGateway,
    KubernetesHorizontalPodAutoscaler,
    KubernetesNamespace,
    KubernetesSecret,
    KubernetesService,
    KubernetesWorkload,
)
from itbench.models.scenario import (
    FaultTarget,
    Scenario,
    ScenarioApplication,
    ScenarioDomain,
    ScenarioEnvironment,
    ScenarioFault,
    ScenarioFaultInjection,
)
from itbench.utils.ground_truth import generate_ground_truth

console = Console()

_LIBRARY_ROOT = Path(__file__).parents[5] / "library" / "scenarios"

_DOMAINS: list[str] = [domain.value for domain in ScenarioDomain]

_KIND_TO_CONSTRUCTOR = {
    "DaemonSet":               lambda name, ns: KubernetesWorkload(kind="DaemonSet", name=name, namespace=ns),
    "Deployment":              lambda name, ns: KubernetesWorkload(kind="Deployment", name=name, namespace=ns),
    "Gateway":                 lambda name, ns: KubernetesGateway(name=name, namespace=ns),
    "HorizontalPodAutoscaler": lambda name, ns: KubernetesHorizontalPodAutoscaler(name=name, namespace=ns),
    "Namespace":               lambda name, _:  KubernetesNamespace(name=name),
    "Secret":                  lambda name, ns: KubernetesSecret(name=name, namespace=ns),
    "Service":                 lambda name, ns: KubernetesService(name=name, namespace=ns),
    "StatefulSet":             lambda name, ns: KubernetesWorkload(kind="StatefulSet", name=name, namespace=ns),
}


def _get_next_index(scenarios_dir: Path) -> int:
    """Return the next sequential integer ID for a new scenario directory."""
    if not scenarios_dir.exists():
        return 1

    indices = [
        int(d.name)
        for d in scenarios_dir.iterdir()
        if d.is_dir() and d.name.isdigit()
    ]

    return max(indices, default=0) + 1


def _ask_target(fault_id: str) -> FaultTarget | None:
    """Prompt for a single concrete Kubernetes target for *fault_id*."""
    fault = FAULT_CATALOG[fault_id]
    if not fault.targets:
        # Targetless fault — no target prompt needed.
        return None

    suggested_kind = fault.targets[0].kubernetes
    kind = questionary.select(
        "    Target kind:",
        choices=list(_KIND_TO_CONSTRUCTOR),
        default=suggested_kind if suggested_kind in _KIND_TO_CONSTRUCTOR else "Deployment",
    ).ask()

    name = questionary.text("    Resource name:").ask() or "<name>"
    namespace: str | None = None
    if kind != "Namespace":
        namespace = questionary.text("    Namespace:").ask() or "<namespace>"

    return FaultTarget(kubernetes=_KIND_TO_CONSTRUCTOR[kind](name, namespace))


def _ask_fault_block() -> ScenarioFault | None:
    """Interactively build one ScenarioFault (a block of injections)."""
    fault_ids = sorted(FAULT_CATALOG.keys())
    injections: list[ScenarioFaultInjection] = []
    is_collecting_injections = True

    while is_collecting_injections:
        fault_id = questionary.autocomplete(
            "  Fault ID:",
            choices=fault_ids,
            match_middle=True,
        ).ask()

        if not fault_id:
            if injections:
                is_collecting_injections = False
            else:
                console.print("[yellow]At least one fault injection is required.[/yellow]")
            continue

        if fault_id not in FAULT_CATALOG:
            console.print(f"[red]Unknown fault '{fault_id}'. Try again.[/red]")
            continue

        fault = FAULT_CATALOG[fault_id]
        console.print(f"  [dim]{fault.name} — {fault.description}[/dim]")

        targets: list[FaultTarget] = []
        if fault.targets:
            target = _ask_target(fault_id)
            if target:
                targets.append(target)
                while questionary.confirm(
                    "  Add another target for this injection?", default=False
                ).ask():
                    extra = _ask_target(fault_id)
                    if extra:
                        targets.append(extra)

        injections.append(ScenarioFaultInjection(id=fault_id, targets=targets))

        if not questionary.confirm(
            "  Add another injection to this fault block?", default=False
        ).ask():
            is_collecting_injections = False

    return ScenarioFault(injections=injections) if injections else None


@click.command(name="scenario", help="Interactively create and scaffold a new scenario.")
@click.option(
    "--scenarios-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=_LIBRARY_ROOT,
    show_default=True,
    help="Directory where numbered scenario subdirectories will be created.",
)
def create_scenario_command(scenarios_dir: Path) -> None:
    """Interactively scaffold a new scenario, its ground truth, and an optional extra_vars file."""
    console.print("[bold blue]Create a New ITBench Scenario[/bold blue]\n")

    selected_apps = questionary.checkbox(
        "Select applications:",
        choices=sorted(APPLICATION_CATALOG.keys()),
    ).ask() or []

    if not selected_apps:
        console.print("[red]At least one application is required.[/red]")
        return

    applications = [ScenarioApplication(id=app_id) for app_id in selected_apps]

    domain_value = questionary.select(
        "Domain:",
        choices=_DOMAINS,
        default="sre",
    ).ask()
    domains = [ScenarioDomain(domain_value)]

    fault_blocks: list[ScenarioFault] = []
    console.print("\n[dim]Define fault blocks. Each block is a set of injections applied together.[/dim]")
    is_adding_fault_blocks = True

    while is_adding_fault_blocks:
        console.print(f"\n[bold]Fault block {len(fault_blocks) + 1}[/bold]")
        block = _ask_fault_block()
        if block:
            fault_blocks.append(block)
        else:
            console.print("[yellow]Empty block skipped.[/yellow]")

        is_adding_fault_blocks = questionary.confirm("Add another fault block?", default=False).ask()

    scenario = Scenario(
        environment=ScenarioEnvironment(applications=applications, domains=domains),
        faults=fault_blocks,
    )

    scenario_dict: dict = scenario.model_dump(
        mode="json",
        by_alias=True,
        exclude_none=True,
        exclude={"environment": {"applications": {"__all__": {"enabled"}}}},
    )

    next_id = _get_next_index(scenarios_dir)
    scenario_dir = scenarios_dir / str(next_id)
    scenario_dir.mkdir(parents=True, exist_ok=True)

    scenario_path = scenario_dir / "scenario.yaml"
    header = "# yaml-language-server: $schema=../../../schemas/json/library/scenario.json\n"
    scenario_path.write_text(
        header + yaml.dump(scenario_dict, sort_keys=False, explicit_start=True, allow_unicode=True),
        encoding="utf-8",
    )
    console.print(f"\n[green]Created scenario → {scenario_path}[/green]")

    gt_path = generate_ground_truth(scenario, scenario_dir)
    console.print(f"[green]Generated ground truth → {gt_path}[/green]")

    if questionary.confirm(
        "\nDo you want to add custom application settings (extra_vars)?", default=False
    ).ask():
        console.print("[dim]Enter Ansible variable overrides as key: value pairs.[/dim]")
        extra_vars: dict = {}
        is_adding_vars = True

        while is_adding_vars:
            key = questionary.text("  Variable name:").ask()
            if not key:
                if extra_vars:
                    is_adding_vars = False
                continue
            value = questionary.text(f"  Value for '{key}':").ask()
            if value is not None:
                if value.lower() == "true":
                    extra_vars[key] = True
                elif value.lower() == "false":
                    extra_vars[key] = False
                elif value.isdigit():
                    extra_vars[key] = int(value)
                else:
                    extra_vars[key] = value

            if not questionary.confirm("  Add another variable?", default=False).ask():
                is_adding_vars = False

        if extra_vars:
            ev_path = scenario_dir / "extra_vars.yaml"
            ev_path.write_text(
                yaml.dump(extra_vars, sort_keys=False, explicit_start=True, allow_unicode=True),
                encoding="utf-8",
            )
            console.print(f"[green]Written extra vars → {ev_path}[/green]")
