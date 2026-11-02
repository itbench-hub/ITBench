"""Variables command group — generate Ansible group_vars files."""

import click

from itbench.cli.commands.generate.variables.aws import variables_aws_command
from itbench.cli.commands.generate.variables.s3 import variables_s3_command


@click.group(name="variables", help="Generate Ansible group_vars variable files.")
def variables_group() -> None: ...


variables_group.add_command(variables_aws_command)
variables_group.add_command(variables_s3_command)
