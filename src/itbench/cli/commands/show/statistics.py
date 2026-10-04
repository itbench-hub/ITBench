"""Show statistics sub-command for ITBench."""

from collections import Counter, defaultdict
from pathlib import Path

import click
import yaml

from rich import box
from rich.console import Console
from rich.table import Table

from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG

console = Console()

_LIBRARY_ROOT = Path(__file__).parents[5] / "library"
_BAR_WIDTH = 20


def _bar(count: int, total: int) -> str:
    """Return a fixed-width block bar showing count as a percentage of total, with a label."""
    if total == 0:
        return ""
    pct = count / total * 100
    filled = round(_BAR_WIDTH * count / total)
    bar = "█" * filled + "░" * (_BAR_WIDTH - filled)
    return f"{bar} {pct:5.1f}%"


def _load_scenarios() -> list[dict]:
    """Return parsed YAML dicts for every scenario in the library."""
    scenarios_dir = _LIBRARY_ROOT / "scenarios"
    results = []
    if not scenarios_dir.exists():
        return results
    for scenario_dir in sorted(
        scenarios_dir.iterdir(),
        key=lambda p: int(p.name) if p.name.isdigit() else p.name,
    ):
        f = scenario_dir / "scenario.yaml"
        if not f.exists():
            continue
        try:
            data = yaml.safe_load(f.read_text(encoding="utf-8"))
        except Exception:
            continue
        if isinstance(data, dict):
            data["_id"] = scenario_dir.name
            results.append(data)
    return results


def _stats_faults(full: bool) -> None:
    scenarios = _load_scenarios()
    usage: Counter[str] = Counter()
    scenarios_by_fault: defaultdict[str, list[str]] = defaultdict(list)

    for data in scenarios:
        seen = set()
        for fault_block in data.get("faults") or []:
            for inj in fault_block.get("injections") or []:
                fault_id = inj.get("id", "?")
                usage[fault_id] += 1
                if data["_id"] not in seen:
                    scenarios_by_fault[fault_id].append(data["_id"])
                    seen.add(data["_id"])

    if not usage:
        console.print("[yellow]No fault usage found in scenarios.[/yellow]")
        return

    total = sum(usage.values())
    table = Table(
        title="Fault Usage Across Scenarios",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Fault", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right")
    table.add_column("Distribution (% of total)")
    if full:
        table.add_column("Scenarios", style="dim")

    for fault_id, count in sorted(usage.items()):
        known = fault_id in FAULT_CATALOG
        label = fault_id if known else f"[dim]{fault_id}[/dim]"
        row = [label, str(count), _bar(count, total)]
        if full:
            ids = sorted(scenarios_by_fault[fault_id], key=lambda x: int(x) if x.isdigit() else x)
            row.append(", ".join(ids))
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(usage)} unique fault(s) across {len(scenarios)} scenario(s).[/dim]")


def _stats_applications(full: bool) -> None:
    scenarios = _load_scenarios()
    usage: Counter[str] = Counter()
    scenarios_by_app: defaultdict[str, list[str]] = defaultdict(list)

    for data in scenarios:
        env = data.get("environment") or {}
        for app in env.get("applications") or []:
            app_id = app.get("id", "?")
            usage[app_id] += 1
            scenarios_by_app[app_id].append(data["_id"])

    if not usage:
        console.print("[yellow]No application usage found in scenarios.[/yellow]")
        return

    total = sum(usage.values())
    table = Table(
        title="Application Usage Across Scenarios",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Application", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right")
    table.add_column("Distribution (% of total)")
    if full:
        table.add_column("Scenarios", style="dim")

    for app_id, count in sorted(usage.items()):
        row = [app_id, str(count), _bar(count, total)]
        if full:
            ids = sorted(scenarios_by_app[app_id], key=lambda x: int(x) if x.isdigit() else x)
            row.append(", ".join(ids))
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(usage)} unique application(s) across {len(scenarios)} scenario(s).[/dim]")


def _stats_waiters(full: bool) -> None:
    scenarios = _load_scenarios()
    usage: Counter[str] = Counter()
    scenarios_by_waiter: defaultdict[str, list[str]] = defaultdict(list)

    for data in scenarios:
        for fault_block in data.get("faults") or []:
            wait_for = fault_block.get("waitFor") or {}
            for phase in ("preInjection", "postInjection"):
                for waiter in wait_for.get(phase) or []:
                    waiter_id = waiter.get("id", "?")
                    usage[waiter_id] += 1
                    scenarios_by_waiter[waiter_id].append(data["_id"])

    if not usage:
        console.print("[yellow]No waiter usage found in scenarios.[/yellow]")
        return

    total = sum(usage.values())
    table = Table(
        title="Waiter Usage Across Scenarios",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Waiter", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right")
    table.add_column("Distribution (% of total)")
    if full:
        table.add_column("Scenarios", style="dim")

    for waiter_id, count in sorted(usage.items()):
        known = waiter_id in WAITER_CATALOG
        label = waiter_id if known else f"[dim]{waiter_id}[/dim]"
        row = [label, str(count), _bar(count, total)]
        if full:
            ids = sorted(scenarios_by_waiter[waiter_id], key=lambda x: int(x) if x.isdigit() else x)
            row.append(", ".join(ids))
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(usage)} unique waiter(s) across {len(scenarios)} scenario(s).[/dim]")


def _stats_scenarios(full: bool) -> None:
    scenarios = _load_scenarios()
    usage: Counter[str] = Counter()
    scenarios_by_domain: defaultdict[str, list[str]] = defaultdict(list)

    for data in scenarios:
        env = data.get("environment") or {}
        for domain in env.get("domains") or []:
            usage[domain] += 1
            scenarios_by_domain[domain].append(data["_id"])

    if not usage:
        console.print("[yellow]No domain assignments found in scenarios.[/yellow]")
        return

    total = sum(usage.values())
    table = Table(
        title="Scenario Distribution by Domain",
        box=box.SIMPLE_HEAVY,
        header_style="bold",
        show_lines=False,
    )
    table.add_column("Domain", style="cyan", no_wrap=True)
    table.add_column("Count", justify="right")
    table.add_column("Distribution (% of total)")
    if full:
        table.add_column("Scenarios", style="dim")

    for domain, count in sorted(usage.items()):
        row = [domain, str(count), _bar(count, total)]
        if full:
            ids = sorted(scenarios_by_domain[domain], key=lambda x: int(x) if x.isdigit() else x)
            row.append(", ".join(ids))
        table.add_row(*row)

    console.print(table)
    console.print(f"[dim]{len(scenarios)} scenario(s) total across {len(usage)} domain(s).[/dim]")


@click.command(name="statistics", help="Show usage statistics for benchmark library primitives.")
@click.option("--faults",       "subject", flag_value="faults",       help="Fault usage across scenarios.")
@click.option("--applications", "subject", flag_value="applications",  help="Application usage across scenarios.")
@click.option("--waiters",      "subject", flag_value="waiters",       help="Waiter usage across scenarios.")
@click.option("--scenarios",    "subject", flag_value="scenarios",     help="Scenario count per domain.")
@click.option("--full", is_flag=True, default=False, help="Show scenario IDs alongside each count.")
def show_statistics(subject: str | None, full: bool) -> None:
    """Show usage statistics across the benchmark library."""
    if subject is None:
        console.print("[yellow]Specify a subject: --faults, --applications, --waiters, or --scenarios.[/yellow]")
        console.print("[dim]Add --full for a detailed breakdown.[/dim]")
        raise SystemExit(1)

    dispatch = {
        "faults": _stats_faults,
        "applications": _stats_applications,
        "waiters": _stats_waiters,
        "scenarios": _stats_scenarios,
    }
    dispatch[subject](full)
