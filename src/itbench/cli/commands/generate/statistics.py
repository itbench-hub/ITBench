"""CLI command to generate a usage statistics report for the ITBench library."""

from pathlib import Path

import click

from itbench.cli.render import console, dump_structured, emit_structured, warn_skipped_scenario
from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG
from itbench.paths import repository
from itbench.utils.scenarios import load_scenario_docs
from itbench.utils.statistics import build_report


@click.command(
    name="statistics",
    help="Print a library usage report (faults, applications, waiters, domains), or write it to a file.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    show_default=True,
    help="Format of the report.",
)
@click.option(
    "--output",
    "output_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Write the report to this file instead of printing it.",
)
def generate_statistics_command(output_format: str, output_path: Path | None) -> None:
    """Print a statistics report for the whole library, or write it to --output."""
    scenarios = load_scenario_docs(repository.scenarios, on_error=warn_skipped_scenario)
    report = build_report(
        scenarios,
        {"faults": FAULT_CATALOG, "applications": APPLICATION_CATALOG, "waiters": WAITER_CATALOG},
        inactive_faults=[slug for slug, fault in FAULT_CATALOG.items() if fault.is_inactive],
    )

    if output_path is None:
        emit_structured(report, output_format)
        return

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(dump_structured(report, output_format) + "\n", encoding="utf-8")
    console.print(f"[green]Generated statistics → {output_path}[/green]", soft_wrap=True)
