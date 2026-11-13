"""Check command group for ITBench."""

import click

from itbench.cli.commands.check.resources import resources_group


@click.group(name="check", help="Check that the machine or account is ready to run ITBench clusters.")
def check_group() -> None: ...


check_group.add_command(resources_group)
