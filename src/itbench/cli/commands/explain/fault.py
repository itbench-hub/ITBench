"""Explain fault sub-command for ITBench."""

import re
import textwrap

from typing import Any, get_args

import click
import yaml

from rich.markup import escape
from rich.panel import Panel

from itbench.cli.render import console, detail_format_option, emit_structured, exit_not_found
from itbench.models.fault import FAULT_CATALOG, Fault
from itbench.models.kubernetes import KubernetesObject, KubernetesObjects


def _placeholder_name(class_name: str) -> str:
    """Derive a YAML placeholder name from a KubernetesObject class name.

    E.g. ``KubernetesWorkload`` -> ``<workload-name>``,
         ``KubernetesService``  -> ``<service-name>``.
    """
    suffix = class_name.removeprefix("Kubernetes")
    kebab = re.sub(r"(?<!^)(?=[A-Z])", "-", suffix).lower()
    return f"<{kebab}-name>"


_KUBERNETES_OBJECT_CLASSES: dict[str, type[KubernetesObject]] = {
    cls.__name__: cls for cls in get_args(get_args(KubernetesObjects)[0])
}


def _target_example(class_name: str) -> dict[str, Any] | None:
    """Build an example ``kubernetes`` target for a KubernetesObject class name."""
    cls = _KUBERNETES_OBJECT_CLASSES.get(class_name)
    if cls is None:
        return None

    fields = cls.model_fields
    target: dict[str, Any] = {
        "apiVersion": fields["api_version"].default,
        "kind": fields["kind"].default,
        "name": _placeholder_name(class_name),
    }
    namespace = fields.get("namespace")
    if namespace is not None and namespace.annotation is not type(None):
        target["namespace"] = "<namespace>"
    return {"kubernetes": target}


def _print_yaml(data: object) -> None:
    """Print *data* as an indented YAML block without Rich markup interpretation."""
    text = yaml.safe_dump(data, sort_keys=False, default_flow_style=False).rstrip()
    console.print(textwrap.indent(text, "  "), markup=False, highlight=False, soft_wrap=True)


def _render_status(fault: Fault) -> None:
    if fault.status is None:
        return

    console.print("[bold]STATUS[/bold]")
    retired = fault.status.retired
    if retired is not None:
        reason = f": {escape(retired.reason)}" if retired.reason else ""
        console.print(f"  Retired in {escape(retired.version)}{reason}")
    converted = fault.status.converted
    if converted is not None:
        console.print(
            f"  Converted to waiter [cyan]{escape(converted.id)}[/cyan] in {escape(converted.version)} "
            f"[dim](run `itbench explain waiter {escape(converted.id)}`)[/dim]",
            soft_wrap=True,
        )
    console.print()


def _render_solutions(fault: Fault) -> None:
    if not fault.solution_templates.templates:
        return

    console.print("[bold]SOLUTIONS[/bold]")
    for i, template in enumerate(fault.solution_templates.templates, 1):
        console.print(f"  [dim]Template {i}:[/dim]")
        for step in template.steps:
            console.print(f"    • {escape(step.text)}")
            if step.command:
                console.print(f"      [green]$ {escape(step.command)}[/green]", soft_wrap=True)
    console.print()


def _render_fault(slug: str, fault: Fault) -> None:
    """Render a fault as a Rich man-page."""
    console.print()
    console.print(
        Panel(
            f"[bold]{escape(fault.name)}[/bold]\n\n"
            f"[dim]slug:[/dim] {escape(slug)}   "
            f"[dim]platform:[/dim] {escape(fault.platform)}   "
            f"[dim]tags:[/dim] {escape(', '.join(fault.tags))}",
            title="[bold blue]FAULT[/bold blue]",
            border_style="blue",
        )
    )

    _render_status(fault)

    console.print("[bold]DESCRIPTION[/bold]")
    console.print(f"  {escape(fault.description)}\n")

    console.print("[bold]EXPECTATION[/bold]")
    console.print(f"  {escape(fault.expectation)}\n")

    if fault.alerts:
        console.print("[bold]ALERTS[/bold]")
        console.print(f"  {escape(', '.join(fault.alerts))}\n")

    if fault.targets:
        console.print("[bold]TARGETS[/bold]")
        for target in fault.targets:
            console.print(f"  kubernetes: {escape(target.kubernetes)}")
        console.print()

    targets = [example for target in fault.targets if (example := _target_example(target.kubernetes)) is not None]
    example = {"faults": [{"injections": [{"id": slug, "targets": targets}]}]}
    console.print("[bold]SCENARIO YAML EXAMPLE[/bold]")
    console.print("  # In library/scenarios/<id>/scenario.yaml", markup=False)
    _print_yaml(example)
    console.print()

    _render_solutions(fault)

    if fault.resources:
        console.print("[bold]RESOURCES[/bold]")
        for url in fault.resources:
            console.print(f"  {escape(url)}")
        console.print()


@click.command(name="fault", help="Explain a fault by its slug.")
@click.argument("slug")
@detail_format_option
def explain_fault(slug: str, output_format: str) -> None:
    """Print a formatted man-page for a fault."""
    fault = FAULT_CATALOG.get(slug)
    if fault is None:
        exit_not_found("Fault", slug, FAULT_CATALOG, "itbench list faults")

    if output_format != "text":
        emit_structured(fault.model_dump(mode="json"), output_format)
        return

    _render_fault(slug, fault)
