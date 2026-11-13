"""Resources command group — check that the machine or account can host the clusters."""

import click

from itbench.cli.commands.check.resources.localhost import resources_localhost_command


@click.group(name="resources", help="Check that there are enough resources to run the clusters.")
def resources_group() -> None: ...


resources_group.add_command(resources_localhost_command)
