"""CLI command to create and scaffold a new fault."""

import sys

from pathlib import Path
from typing import Any

import click
import questionary
import yaml

from jinja2 import Template

from itbench.cli.render import console, fail
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
from itbench.paths import repository

_INJECT_TASK_TEMPLATE = Template("""\
---
- name: Print message
  ansible.builtin.debug:
    msg: This fault injection ({{ fault_id }}) is unimplemented.
""")

_KIND_TO_MODEL: dict[str, KubernetesObjectKind] = {
    "DaemonSet": KubernetesObjectKind.KubernetesWorkload,
    "Deployment": KubernetesObjectKind.KubernetesWorkload,
    "Gateway": KubernetesObjectKind.KubernetesGateway,
    "HorizontalPodAutoscaler": KubernetesObjectKind.KubernetesHorizontalPodAutoscaler,
    "Namespace": KubernetesObjectKind.KubernetesNamespace,
    "Secret": KubernetesObjectKind.KubernetesSecret,
    "Service": KubernetesObjectKind.KubernetesService,
    "StatefulSet": KubernetesObjectKind.KubernetesWorkload,
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
def create_fault_command() -> None:
    """Interactively scaffold a new fault entry and its associated Ansible task."""
    library_dir = repository.faults
    tasks_dir = repository.ansible_project / "roles" / "faults" / "tasks"
    if not sys.stdin.isatty():
        fail("[red]Input is not interactive. This command must be run in a terminal.[/red]")

    console.print("[bold blue]Create a new ITBench fault[/bold blue]\n")

    name = questionary.text("Fault name:").ask()
    if name is None:
        raise click.Abort()
    if not name:
        raise click.UsageError("Fault name is required.")

    description = questionary.text("Description:").ask()
    if description is None:
        raise click.Abort()
    if not description:
        raise click.UsageError("Fault description is required.")

    expectation = questionary.text("Expectation (symptoms/behavior):").ask()
    if expectation is None:
        raise click.Abort()
    if not expectation:
        raise click.UsageError("Fault expectation is required.")

    platform_choice = questionary.select(
        "Platform:",
        choices=[p.value for p in Platform],
        default=Platform.Kubernetes.value,
    ).ask()
    if platform_choice is None:
        raise click.Abort()

    selected_tags = questionary.checkbox(
        "Select tags:",
        choices=[t.value for t in FaultTags],
        validate=lambda choices: True if len(choices) > 0 else "At least one tag must be selected.",
    ).ask()
    if selected_tags is None:
        raise click.Abort()

    resources: list[str] = []
    console.print("\n[dim]Enter resource links (e.g. documentation, GitHub issues):[/dim]")
    while True:
        link = questionary.text("Link URL (leave empty to finish):").ask()
        if link is None:
            raise click.Abort()
        link = link.strip()
        if not link:
            break
        resources.append(link)

    solution_steps: list[FaultSolutionStep] = []
    console.print("\n[dim]Define troubleshooting steps (leave description empty to finish):[/dim]")
    while True:
        step_text = questionary.text(f"Step {len(solution_steps) + 1} description:").ask()
        if step_text is None:
            raise click.Abort()
        step_text = step_text.strip()
        if not step_text:
            if not solution_steps:
                console.print("[yellow]At least one solution step is recommended.[/yellow]")
                continue
            break

        step_command = questionary.text("  CLI command (optional):").ask()
        if step_command is None:
            raise click.Abort()
        step_command = step_command.strip()
        solution_steps.append(FaultSolutionStep(text=step_text, command=step_command or None))

    selected_alerts = questionary.checkbox(
        "Select alerts:",
        choices=[a.value for a in FaultAlerts],
        validate=lambda choices: True if len(choices) > 0 else "At least one alert must be selected.",
    ).ask()
    if selected_alerts is None:
        raise click.Abort()

    selected_kinds = questionary.checkbox(
        "Select target kind(s):",
        choices=list(_KIND_TO_MODEL),
        validate=lambda choices: True if len(choices) > 0 else "At least one target kind must be selected.",
    ).ask()
    if selected_kinds is None:
        raise click.Abort()

    target_refs: list[FaultTargetReference] = [
        FaultTargetReference(kubernetes=_KIND_TO_MODEL[k]) for k in selected_kinds
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

    fault_dict: dict[str, Any] = fault.model_dump(
        mode="json",
        by_alias=True,
        exclude={"id"},
        exclude_none=True,
    )

    library_dir.mkdir(parents=True, exist_ok=True)
    yaml_path = library_dir / f"{fault.id}.yaml"

    header = f"# yaml-language-server: $schema=../../schemas/json/library/faults/{fault.id}.json\n"
    yaml_path.write_text(
        f"{header}{yaml.dump(fault_dict, sort_keys=False, explicit_start=True, allow_unicode=True)}",
        encoding="utf-8",
    )
    console.print(f"[green]Created fault at {yaml_path}[/green]")

    task_path = _scaffold_ansible_task(tasks_dir, fault.id)
    console.print(f"[green]Scaffolded Ansible task at {task_path}[/green]")
