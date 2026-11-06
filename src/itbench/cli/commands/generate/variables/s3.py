"""CLI command: itbench generate variables s3"""

from pathlib import Path

import click
import questionary
import yaml

from itbench.cli.render import confirm_or_cancel, console
from itbench.paths import repository


def _output_path() -> Path:
    """Location of the S3 group_vars file in the repository."""
    return repository.group_vars / "storage" / "s3.yaml"


def _prompt() -> dict[str, str]:
    """Interactively collect S3 bucket variables."""
    console.print("[bold]Configure S3 bucket variables[/bold]\n")

    bucket = questionary.text("S3 bucket name:").ask()
    if bucket is None:
        raise click.Abort()

    endpoint = questionary.text("S3 endpoint URL:").ask()
    if endpoint is None:
        raise click.Abort()

    directory = questionary.text("Directory in S3 bucket:", default="itbench").ask()
    if directory is None:
        raise click.Abort()

    return {
        "storage_s3_bucket": bucket,
        "storage_s3_endpoint": endpoint,
        "storage_s3_directory": directory,
    }


@click.command(name="s3", help="Generate S3 bucket variables into the SRE group_vars.")
@click.option("-y", "--yes", is_flag=True, default=False, help="Overwrite an existing file without asking.")
def variables_s3_command(yes: bool) -> None:
    """Prompt for S3 bucket variables and write the SRE ``group_vars/storage/s3.yaml``."""
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
    console.print(f"\n[green]S3 variables written → {output}[/green]", soft_wrap=True)
