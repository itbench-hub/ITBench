"""Generate command group for ITBench."""

import click

from itbench.cli.commands.generate.docs import generate_docs_command
from itbench.cli.commands.generate.schemas import generate_schemas_command


@click.group(name="generate", help="Generate schemas, documentation, and asset artifacts.")
def generate_group() -> None: ...


generate_group.add_command(generate_schemas_command)
generate_group.add_command(generate_docs_command)
