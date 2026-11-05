"""CLI command to generate a usage statistics report for the ITBench library."""

import tempfile

from pathlib import Path

import click

from itbench.cli.render import console, dump_structured, warn_skipped_scenario
from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.waiter import WAITER_CATALOG
from itbench.paths import library
from itbench.utils.scenarios import load_scenario_docs
from itbench.utils.statistics import build_report


@click.command(
    name="statistics",
    help="Write a library usage report (faults, applications, waiters, domains) to a temporary file.",
)
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["yaml", "json"]),
    default="yaml",
    show_default=True,
    help="File format of the report.",
)
def generate_statistics_command(output_format: str) -> None:
    """Write a statistics report for the whole library to the system temporary directory."""
    scenarios = load_scenario_docs(library.scenarios, on_error=warn_skipped_scenario)
    report = build_report(
        scenarios,
        {"faults": FAULT_CATALOG, "applications": APPLICATION_CATALOG, "waiters": WAITER_CATALOG},
        inactive_faults=[
            slug
            for slug, fault in FAULT_CATALOG.items()
            if fault.status is not None and (fault.status.retired or fault.status.converted)
        ],
    )

    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        prefix="itbench-statistics-",
        suffix=f".{output_format}",
        delete=False,
    ) as handle:
        handle.write(dump_structured(report, output_format) + "\n")

    console.print(f"[green]Generated statistics → {Path(handle.name)}[/green]", soft_wrap=True)
    console.print("[dim]This is a temporary file the operating system may delete; move it to keep it.[/dim]")
