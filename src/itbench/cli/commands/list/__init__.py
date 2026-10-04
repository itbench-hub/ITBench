"""List command group for ITBench."""

import click

from itbench.cli.commands.list.applications import list_applications
from itbench.cli.commands.list.faults import list_faults
from itbench.cli.commands.list.scenarios import list_scenarios
from itbench.cli.commands.list.waiters import list_waiters


@click.group(name="list", help="List and search benchmark primitives (faults, waiters, apps, scenarios).")
def list_group() -> None: ...


list_group.add_command(list_faults)
list_group.add_command(list_applications)
list_group.add_command(list_waiters)
list_group.add_command(list_scenarios)
