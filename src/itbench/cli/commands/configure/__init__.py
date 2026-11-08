"""Configure command group for ITBench."""

import click

from itbench.cli.commands.configure.environment import configure_environment_command
from itbench.cli.commands.configure.orchestrator import configure_orchestrator_command


@click.group(name="configure", help="Configure environment clusters and the orchestrator cluster.")
def configure_group() -> None: ...


configure_group.add_command(configure_environment_command)
configure_group.add_command(configure_orchestrator_command)
