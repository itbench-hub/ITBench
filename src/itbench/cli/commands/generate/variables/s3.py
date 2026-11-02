"""CLI command: itbench generate variables s3"""

from pathlib import Path

import click
import questionary
import yaml

from rich.console import Console

console = Console()

_DEFAULT_OUTPUT = (
    Path(__file__).parents[7] / "scenarios" / "sre" / "inventory" / "group_vars" / "all" / "s3.yaml"
)


def _prompt() -> dict:
    """Interactively collect S3 bucket variables."""
    console.print("[bold]Configure S3 bucket variables[/bold]\n")

    bucket = questionary.text("S3 bucket name:").ask()
    if bucket is None:
        raise click.Abort()

    endpoint = questionary.text("S3 endpoint URL:").ask()
    if endpoint is None:
        raise click.Abort()

    directory = questionary.text(
        "Directory in S3 bucket:", default="itbench"
    ).ask()
    if directory is None:
        raise click.Abort()

    return {
        "s3_bucket": bucket,
        "s3_endpoint": endpoint,
        "s3_directory": directory,
    }


@click.command(name="s3", help="Generate S3 bucket variables into the SRE group_vars.")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=_DEFAULT_OUTPUT,
    show_default=True,
    help="Path to the s3.yaml group_vars file to write.",
)
def variables_s3_command(output: Path) -> None:
    """Prompt for S3 bucket variables and write group_vars."""
    doc = {k: v for k, v in _prompt().items() if v is not None}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(doc, default_flow_style=False, explicit_start=True, sort_keys=False),
        encoding="utf-8",
    )
    console.print(f"\n[green]S3 variables written → {output}[/green]")
