"""Explain scenario sub-command for ITBench."""

from typing import Any

import click
import yaml

from rich import box
from rich.markup import escape
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table

from itbench.cli.render import console, detail_format_option, emit_structured, err_console, exit_not_found
from itbench.paths import repository
from itbench.utils.scenarios import known_scenario_ids


def _load_mapping(path: Any) -> dict[str, Any]:
    """Parse *path* as a YAML mapping, exiting with status 1 on failure."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        err_console.print(f"[red]Failed to parse {escape(path.name)}: {escape(str(exc))}[/red]")
        raise SystemExit(1) from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        err_console.print(f"[red]{escape(path.name)} must contain a YAML mapping.[/red]")
        raise SystemExit(1)
    return data


def _target_label(target: dict[str, Any]) -> str:
    """Format a Kubernetes injection target as ``Kind name (namespace)``."""
    obj = target.get("kubernetes") or {}
    label = f"{obj.get('kind', '?')} {obj.get('name', '?')}"
    if obj.get("namespace"):
        label += f" ({obj['namespace']})"
    return label


def _injection_cell(block: dict[str, Any]) -> str:
    """Format a fault block's injections, each followed by its targets."""
    lines: list[str] = []
    for injection in block.get("injections") or []:
        lines.append(f"[cyan]{escape(str(injection.get('id', '?')))}[/cyan]")
        lines.extend(f"  → {escape(_target_label(target))}" for target in injection.get("targets") or [])
    return "\n".join(lines)


def _waiter_cell(waiters: list[dict[str, Any]]) -> str:
    """Format a list of waiters as one id per line."""
    return "\n".join(escape(str(waiter.get("id", "?"))) for waiter in waiters)


def _render_faults(faults: list[dict[str, Any]]) -> None:
    """Print the fault blocks as a table whose columns follow the execution order.

    The waiter columns are only shown when at least one fault block uses them.
    """
    waiters = [(block.get("waitFor") or {}) for block in faults]
    has_pre = any(w.get("preInjection") for w in waiters)
    has_post = any(w.get("postInjection") for w in waiters)

    table = Table(title="Faults", box=box.SIMPLE_HEAVY, header_style="bold", expand=True)
    table.add_column("#", justify="right")
    if has_pre:
        table.add_column("Wait before", style="dim")
    table.add_column("Injection / targets")
    if has_post:
        table.add_column("Wait after", style="dim")

    for fault_idx, (block, wait_for) in enumerate(zip(faults, waiters, strict=True), 1):
        cells = [str(fault_idx)]
        if has_pre:
            cells.append(_waiter_cell(wait_for.get("preInjection") or []))
        cells.append(_injection_cell(block))
        if has_post:
            cells.append(_waiter_cell(wait_for.get("postInjection") or []))
        table.add_row(*cells)

    console.print(table)


def _render_solution(ground_truth: dict[str, Any]) -> None:
    """Print the ground-truth alerts, affected entities and solution steps."""
    alerts: list[dict[str, Any]] = ground_truth.get("alerts") or []
    entities: list[dict[str, Any]] = ground_truth.get("entities") or []
    solutions: list[list[dict[str, Any]]] = ground_truth.get("solutions") or []

    console.print("[bold magenta]SOLUTION[/bold magenta]\n")

    if alerts:
        console.print("  [bold]Alerts[/bold]")
        for alert in alerts:
            console.print(f"    • {escape(str(alert.get('name', '?')))}")

    if entities:
        console.print("  [bold]Affected entities[/bold]")
        for entity in entities:
            parts = [f"[dim]{escape(str(entity.get('apiVersion', '')))}[/dim]", escape(str(entity.get("kind", "?")))]
            parts.append(escape(str(entity.get("name", "?"))))
            if entity.get("namespace"):
                parts.append(f"({escape(str(entity['namespace']))})")
            console.print(f"    • {' '.join(parts)}")

    if not solutions:
        console.print("  [dim]No solutions recorded for this scenario.[/dim]\n")
        return

    console.print("  [bold]Steps[/bold]")
    multiple_faults = len(solutions) > 1
    for fault_idx, variants in enumerate(solutions, 1):
        if multiple_faults:
            console.print(f"\n    [bold]Fault {fault_idx}[/bold]")

        # Each heading level (fault, variant) pushes its children one level deeper.
        variant_indent = " " * (6 if multiple_faults else 4)
        multiple_variants = len(variants) > 1
        step_indent = variant_indent + ("  " if multiple_variants else "")

        for variant_idx, variant in enumerate(variants, 1):
            if multiple_variants:
                console.print(f"{variant_indent}[dim]Variant {variant_idx}[/dim]")
            for step_idx, step in enumerate(variant.get("steps") or [], 1):
                console.print(f"{step_indent}{step_idx}. {escape(str(step.get('text', '')))}")
                if step.get("command"):
                    console.print(f"{step_indent}   [green]$ {escape(str(step['command']))}[/green]", soft_wrap=True)

        if fault_idx < len(solutions):
            console.print(Rule(style="dim"))
    console.print()


def _render_scenario(scenario_id: str, data: dict[str, Any], ground_truth: dict[str, Any] | None) -> None:
    """Render a scenario as a Rich man-page."""
    env = data.get("environment") or {}
    domains = [str(d) for d in env.get("domains") or []]
    applications = [str(a.get("id", "?")) for a in env.get("applications") or []]

    console.print()
    console.print(
        Panel(
            f"[bold]Scenario {escape(scenario_id)}[/bold]\n\n"
            f"[dim]domains:[/dim] {escape(', '.join(domains))}   "
            f"[dim]applications:[/dim] {escape(', '.join(applications))}",
            title="[bold magenta]SCENARIO[/bold magenta]",
            border_style="magenta",
        )
    )

    faults = data.get("faults") or []
    if faults:
        _render_faults(faults)

    if ground_truth is None:
        console.print("[dim]No ground truth (solution) is available for this scenario.[/dim]\n")
    else:
        _render_solution(ground_truth)


@click.command(name="scenario", help="Explain a scenario by its id, including its solution.")
@click.argument("scenario_id")
@detail_format_option
def explain_scenario(scenario_id: str, output_format: str) -> None:
    """Print a formatted man-page for a scenario."""
    known = known_scenario_ids(repository.scenarios)
    if scenario_id not in known:
        exit_not_found("Scenario", scenario_id, known, "itbench list scenarios")

    scenario_dir = repository.scenarios / scenario_id
    data = _load_mapping(scenario_dir / "scenario.yaml")

    ground_truth_path = scenario_dir / "ground_truth.yaml"
    ground_truth = _load_mapping(ground_truth_path) if ground_truth_path.is_file() else None

    if output_format != "text":
        emit_structured({"id": scenario_id, **data, "ground_truth": ground_truth}, output_format)
        return

    _render_scenario(scenario_id, data, ground_truth)
