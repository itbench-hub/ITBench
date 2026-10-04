"""Explain fault sub-command for ITBench."""

import re

from typing import get_args

import click

from rich.console import Console
from rich.markup import escape
from rich.panel import Panel

from itbench.models.fault import FAULT_CATALOG
from itbench.models.kubernetes import KubernetesObject, KubernetesObjects

console = Console()


def _placeholder_name(class_name: str) -> str:
    """Derive a YAML placeholder name from a KubernetesObject class name.

    E.g. ``KubernetesWorkload`` -> ``<workload-name>``,
         ``KubernetesService``  -> ``<service-name>``.
    """
    suffix = class_name.removeprefix("Kubernetes")
    kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", suffix).lower()
    return f"<{kebab}-name>"


_KUBERNETES_OBJECT_CLASSES: dict[str, type[KubernetesObject]] = {
    cls.__name__: cls
    for cls in get_args(get_args(KubernetesObjects)[0])
}


def _render_fault(slug: str) -> None:
    """Render a fault as a Rich man-page."""
    fault = FAULT_CATALOG[slug]

    console.print()
    console.print(Panel(
        f"[bold]{escape(fault.name)}[/bold]\n\n"
        f"[dim]slug:[/dim] {slug}   "
        f"[dim]platform:[/dim] {escape(fault.platform)}   "
        f"[dim]tags:[/dim] {escape(', '.join(fault.tags))}",
        title="[bold blue]FAULT[/bold blue]",
        border_style="blue",
    ))

    console.print("[bold]DESCRIPTION[/bold]")
    console.print(f"  {fault.description}\n")

    console.print("[bold]EXPECTATION[/bold]")
    console.print(f"  {fault.expectation}\n")

    if fault.alerts:
        console.print("[bold]ALERTS[/bold]")
        console.print(f"  {', '.join(fault.alerts)}\n")

    if fault.targets:
        console.print("[bold]TARGETS[/bold]")
        for t in fault.targets:
            console.print(f"  kubernetes: {t.kubernetes}")
        console.print()

    if fault.targets:
        target_lines = "        targets:\n"
        for t in fault.targets:
            cls = _KUBERNETES_OBJECT_CLASSES.get(t.kubernetes)
            if cls is None:
                continue
            fields = cls.model_fields
            api_version = fields["api_version"].default
            kind = fields["kind"].default
            placeholder = _placeholder_name(t.kubernetes)
            target_lines += (
                f"          - kubernetes:\n"
                f"              apiVersion: {api_version}\n"
                f"              kind: {kind}\n"
                f"              name: {placeholder}\n"
            )
            ns_field = fields.get("namespace")
            if ns_field and ns_field.annotation is not type(None):
                target_lines += "              namespace: <namespace>\n"
    else:
        target_lines = "        targets: []\n"

    console.print("[bold]SCENARIO YAML EXAMPLE[/bold]")
    console.print(
        f"  # In library/scenarios/<id>/scenario.yaml\n"
        f"  faults:\n"
        f"    - injections:\n"
        f"        - id: {slug}\n"
        f"{target_lines}"
    )

    if fault.solution_templates.templates:
        console.print("[bold]SOLUTIONS[/bold]")
        for i, template in enumerate(fault.solution_templates.templates, 1):
            console.print(f"  [dim]Template {i}:[/dim]")
            for step in template.steps:
                console.print(f"    • {step.text}")
                if step.command:
                    console.print(f"      [green]$ {step.command}[/green]")
        console.print()

    if fault.resources:
        console.print("[bold]RESOURCES[/bold]")
        for url in fault.resources:
            console.print(f"  {url}")
        console.print()


@click.command(name="fault", help="Explain a fault by its slug.")
@click.argument("slug")
def explain_fault(slug: str) -> None:
    """Print a formatted man-page for a fault."""
    if slug not in FAULT_CATALOG:
        console.print(f"[red]Fault '[bold]{slug}[/bold]' not found.[/red]")
        console.print("[dim]Run `itbench list faults` to see available fault slugs.[/dim]")
        raise SystemExit(1)
    _render_fault(slug)
