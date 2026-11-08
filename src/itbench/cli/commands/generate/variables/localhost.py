"""CLI command: itbench generate variables localhost"""

from pathlib import Path

import click
import questionary
import yaml

from itbench.cli.render import confirm_or_cancel, console
from itbench.paths import repository


def _output_path() -> Path:
    """Location of the local storage group_vars file in the repository."""
    return repository.group_vars / "storage" / "localhost.yaml"


def _prompt() -> dict[str, str]:
    """Interactively collect the local storage directory."""
    console.print("[bold]Configure local storage variables[/bold]\n")

    directory = questionary.text("Local directory for exported records:").ask()
    if directory is None:
        raise click.Abort()

    return {"storage_localhost_directory": directory}


@click.command(name="localhost", help="Generate local storage variables into the SRE group_vars.")
@click.option("-y", "--yes", is_flag=True, default=False, help="Overwrite an existing file without asking.")
def variables_localhost_command(yes: bool) -> None:
    """Prompt for a local storage directory and write the SRE ``group_vars/storage/localhost.yaml``."""
    output = _output_path()
    if output.exists() and not confirm_or_cancel(
        f"{output} already exists. Overwrite it?", yes, cancelled="Existing file kept."
    ):
        return

    doc = _prompt()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(doc, default_flow_style=False, explicit_start=True, sort_keys=False),
        encoding="utf-8",
    )
    console.print(f"\n[green]Local storage variables written → {output}[/green]", soft_wrap=True)
