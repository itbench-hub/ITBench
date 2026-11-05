"""Undeploy command group for ITBench."""

import click

from itbench.cli.commands.undeploy.environment import undeploy_environment
from itbench.cli.commands.undeploy.orchestrator import undeploy_orchestrator


@click.group(name="undeploy", help="Undeploy environment or orchestrator stack from the cluster.")
def undeploy_group() -> None: ...


undeploy_group.add_command(undeploy_environment)
undeploy_group.add_command(undeploy_orchestrator)
