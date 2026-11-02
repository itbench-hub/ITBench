"""CLI command: itbench generate variables aws"""

from pathlib import Path

import click
import questionary
import yaml

from rich.console import Console

from itbench.utils.ansible_vault import resolve_vault_password, vault_encrypt

console = Console()

_DEFAULT_OUTPUT = (
    Path(__file__).parents[7] / "scenarios" / "sre" / "inventory" / "group_vars" / "all" / "aws.yaml"
)


def _prompt() -> dict:
    """Interactively collect AWS credentials."""
    console.print("[bold]Configure AWS credentials[/bold]\n")

    region = questionary.text("AWS region:", default="us-east-1").ask()
    if region is None:
        raise click.Abort()

    access_key_id = questionary.text("Access key ID:").ask()
    if access_key_id is None:
        raise click.Abort()

    secret_access_key = questionary.password("Secret access key:").ask()
    if secret_access_key is None:
        raise click.Abort()

    return {
        "aws_region": region,
        "aws_access_key_id": access_key_id,
        "aws_secret_access_key": secret_access_key,
    }


def _build_doc(creds: dict) -> dict:
    """Build the AWS group_vars dict, vault-encrypting the sensitive values."""
    vault_password = resolve_vault_password()
    return {
        "aws_region": creds["aws_region"],
        "aws_access_key_id": vault_encrypt(creds["aws_access_key_id"], vault_password),
        "aws_secret_access_key": vault_encrypt(creds["aws_secret_access_key"], vault_password),
    }


@click.command(name="aws", help="Generate vault-encrypted AWS credentials into the SRE group_vars.")
@click.option(
    "--output",
    type=click.Path(dir_okay=False, path_type=Path),
    default=_DEFAULT_OUTPUT,
    show_default=True,
    help="Path to the aws.yaml group_vars file to write.",
)
def variables_aws_command(output: Path) -> None:
    """Prompt for AWS credentials, vault-encrypt them, and write group_vars."""
    creds = _prompt()
    doc = _build_doc(creds)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        yaml.safe_dump(doc, default_flow_style=False, explicit_start=True, sort_keys=False),
        encoding="utf-8",
    )
    console.print(f"\n[green]AWS credentials written → {output}[/green]")
    console.print("[dim]Tip: commit the file — credentials are vault-encrypted.[/dim]")
