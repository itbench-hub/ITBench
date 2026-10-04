"""Deploy command group for ITBench."""

import click

from itbench.cli.commands.deploy.applications import deploy_applications
from itbench.cli.commands.deploy.tools import deploy_tools


@click.group(name="deploy", help="Deploy applications, tools, or full benchmark scenarios.")
def deploy_group() -> None: ...


deploy_group.add_command(deploy_applications)
deploy_group.add_command(deploy_tools)
