"""Undeploy command group for ITBench."""

import click

from itbench.cli.commands.undeploy.applications import undeploy_applications
from itbench.cli.commands.undeploy.tools import undeploy_tools


@click.group(name="undeploy", help="Undeploy and teardown applications, tools, or full benchmark scenarios.")
def undeploy_group() -> None: ...


undeploy_group.add_command(undeploy_applications)
undeploy_group.add_command(undeploy_tools)
