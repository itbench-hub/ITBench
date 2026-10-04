"""CLI command to create and scaffold a new fault."""

from pathlib import Path

import click
import questionary
import yaml

from jinja2 import Template
from rich.console import Console

from itbench.models.fault import (
    Fault,
    FaultAlerts,
    FaultSolution,
    FaultSolutionStep,
    FaultSolutionTemplates,
    FaultTags,
    FaultTargetReference,
)
from itbench.models.kubernetes import KubernetesObjectKind
from itbench.models.platform import Platform

console = Console()


_INJECT_TASK_TEMPLATE = Template("""\
---
- name: Print message
  ansible.builtin.debug:
    msg: This fault injection ({{ fault_id }}) is unimplemented.
""")

_KIND_TO_MODEL: dict[str, KubernetesObjectKind] = {
    "DaemonSet":                 KubernetesObjectKind.KubernetesWorkload,
    "Deployment":                KubernetesObjectKind.KubernetesWorkload,
    "Gateway":                   KubernetesObjectKind.KubernetesGateway,
    "HorizontalPodAutoscaler":   KubernetesObjectKind.KubernetesHorizontalPodAutoscaler,
    "Namespace":                 KubernetesObjectKind.KubernetesNamespace,
    "Secret":                    KubernetesObjectKind.KubernetesSecret,
    "Service":                   KubernetesObjectKind.KubernetesService,
    "StatefulSet":               KubernetesObjectKind.KubernetesWorkload,
}


def _scaffold_ansible_task(tasks_dir: Path, fault_id: str) -> Path:
    """Write a minimal Ansible injection task stub if it does not already exist."""
    task_path = tasks_dir / f"inject_{fault_id.replace('-', '_')}.yaml"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    if not task_path.exists():
        task_path.write_text(
            _INJECT_TASK_TEMPLATE.render(fault_id=fault_id),
            encoding="utf-8",
        )
    return task_path


@click.command(name="fault", help="Interactively create and scaffold a new fault.")
@click.option(
    "--library-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("library/faults"),
    show_default=True,
    help="Directory containing fault YAML files.",
)
@click.option(
    "--tasks-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("scenarios/sre/project/roles/faults/tasks"),
    show_default=True,
    help="Directory where Ansible injection tasks are stored.",
)
def create_fault_command(library_dir: Path, tasks_dir: Path) -> None:
    """Interactively scaffold a new fault entry and its associated Ansible task."""
    console.print("[bold blue]Create a new ITBench fault[/bold blue]\n")

    name = questionary.text("Fault name:").ask()
    if not name:
        console.print("[red]Fault name is required.[/red]")
        return

    description = questionary.text("Description:").ask() or ""
    expectation = questionary.text("Expectation (symptoms/behavior):").ask() or ""

    platform_choice = questionary.select(
        "Platform:",
        choices=[p.value for p in Platform],
        default=Platform.Kubernetes.value,
    ).ask()

    selected_tags = questionary.checkbox(
        "Select tags:",
        choices=[t.value for t in FaultTags],
    ).ask() or []

    resources_input = questionary.text("Resource links (comma-separated):").ask() or ""
    resources = [r.strip() for r in resources_input.split(",") if r.strip()]

    is_defining_solutions = True
    solution_steps: list[FaultSolutionStep] = []

    console.print("\n[dim]Define troubleshooting steps:[/dim]")

    while is_defining_solutions:
        step_text = questionary.text("Solution step description:").ask()
        if step_text:
            step_command = questionary.text("CLI command for this step (optional):").ask() or None
            solution_steps.append(FaultSolutionStep(text=step_text, command=step_command))
        elif not solution_steps:
            console.print("[yellow]At least one solution step is recommended.[/yellow]")
            continue

        if not questionary.confirm(
            "Add another solution step?", default=False
        ).ask():
            is_defining_solutions = False

    selected_alerts = questionary.checkbox(
        "Alerts (optional):",
        choices=[a.value for a in FaultAlerts],
    ).ask() or []

    selected_kinds = questionary.checkbox(
        "Target kind(s):",
        choices=list(_KIND_TO_MODEL),
    ).ask() or []

    target_refs: list[FaultTargetReference] = [
        FaultTargetReference(kubernetes=_KIND_TO_MODEL[k])
        for k in selected_kinds
    ]

    fault = Fault(
        name=name,
        description=description,
        expectation=expectation,
        platform=Platform(platform_choice),
        tags=[FaultTags(t) for t in selected_tags],
        resources=resources,
        solution_templates=FaultSolutionTemplates(
            templates=[FaultSolution(steps=solution_steps)],
        ),
        alerts=[FaultAlerts(a) for a in selected_alerts],
        targets=target_refs,
    )

    fault_dict: dict = fault.model_dump(
        mode="json",
        by_alias=True,
        exclude={"id"},
        exclude_none=True,
    )

    library_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = library_dir / f"{fault.id}.yaml"

    header = f"# yaml-language-server: $schema=../../schemas/json/library/faults/{fault.id}.json\n"
    yaml_path.write_text(
        header + yaml.dump(fault_dict, sort_keys=False, explicit_start=True, allow_unicode=True),
        encoding="utf-8",
    )
    console.print(f"[green]Created fault at {yaml_path}[/green]")

    task_path = _scaffold_ansible_task(tasks_dir, fault.id)
    console.print(f"[green]Scaffolded Ansible task at {task_path}[/green]")
