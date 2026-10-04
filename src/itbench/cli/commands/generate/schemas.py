"""CLI command to generate JSON schemas for ITBench."""

from pathlib import Path

import click

from rich.console import Console

from itbench.models.application import Application
from itbench.models.fault import Fault, FAULT_CATALOG
from itbench.models.ground_truth import GroundTruth
from itbench.models.scenario import Scenario
from itbench.models.waiter import WAITER_CATALOG
from itbench.utils.schema import export_fault_schema, export_json_schema

console = Console()


@click.command(name="schemas", help="Compile and export JSON schemas for ITBench library files.")
@click.option(
    "--output-dir",
    type=click.Path(file_okay=False, dir_okay=True, path_type=Path),
    default=Path("schemas/json"),
    show_default=True,
    help="Root directory where JSON schemas will be written.",
)
def generate_schemas_command(output_dir: Path) -> None:
    """Compile and export JSON schemas for all ITBench library files."""
    faults_dir = output_dir / "library" / "faults"
    waiters_dir = output_dir / "library" / "waiters"

    for model, path in [
        (Application, output_dir / "library" / "application.json"),
        (Fault, output_dir / "library" / "fault.json"),
        (GroundTruth, output_dir / "library" / "ground_truth.json"),
        (Scenario, output_dir / "library" / "scenario.json"),
    ]:
        export_json_schema(model, path)
        console.print(f"[green]Exported {model.__name__} schema → {path}[/green]")

    for slug, waiter in sorted(WAITER_CATALOG.items()):
        path = waiters_dir / f"{slug}.json"
        export_json_schema(type(waiter), path)
        console.print(f"[green]Exported waiter schema → {path}[/green]")

    for slug, fault in sorted(FAULT_CATALOG.items()):
        path = faults_dir / f"{slug}.json"
        export_fault_schema(fault, path)
        console.print(f"[green]Exported fault schema → {path}[/green]")
