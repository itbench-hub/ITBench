"""Deploy command group for ITBench."""

import click

from itbench.cli.commands.deploy.environment import deploy_environment
from itbench.cli.commands.deploy.orchestrator import deploy_orchestrator


@click.group(name="deploy", help="Deploy environment or orchestrator stack onto the cluster.")
def deploy_group() -> None: ...


deploy_group.add_command(deploy_environment)
deploy_group.add_command(deploy_orchestrator)
