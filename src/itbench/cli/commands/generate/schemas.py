"""CLI command to generate JSON schemas for ITBench."""

import click

from itbench.cli.render import console
from itbench.models.application import Application
from itbench.models.fault import FAULT_CATALOG, Fault
from itbench.models.ground_truth import GroundTruth
from itbench.models.scenario import Scenario
from itbench.models.waiter import WAITER_CATALOG
from itbench.paths import repository
from itbench.utils.schema import export_fault_schema, export_json_schema


@click.command(name="schemas", help="Compile and export the JSON schemas for the ITBench library files.")
def generate_schemas_command() -> None:
    """Compile and export JSON schemas for all ITBench library files into the repository's ``schemas/json``."""
    output_dir = repository.schemas
    faults_dir = output_dir / "library" / "faults"
    waiters_dir = output_dir / "library" / "waiters"

    for model, path in [
        (Application, output_dir / "library" / "application.json"),
        (Fault, output_dir / "library" / "fault.json"),
        (GroundTruth, output_dir / "library" / "ground_truth.json"),
        (Scenario, output_dir / "library" / "scenario.json"),
    ]:
        export_json_schema(model, path)
        console.print(f"[green]Exported {model.__name__} schema → {path}[/green]", soft_wrap=True)

    for slug, waiter in sorted(WAITER_CATALOG.items()):
        path = waiters_dir / f"{slug}.json"
        export_json_schema(type(waiter), path)
        console.print(f"[green]Exported waiter schema → {path}[/green]", soft_wrap=True)

    for slug, fault in sorted(FAULT_CATALOG.items()):
        path = faults_dir / f"{slug}.json"
        export_fault_schema(fault, path)
        console.print(f"[green]Exported fault schema → {path}[/green]", soft_wrap=True)
