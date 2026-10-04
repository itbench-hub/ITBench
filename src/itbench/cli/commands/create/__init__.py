"""Create command group for ITBench."""

import click

from itbench.cli.commands.create.fault import create_fault_command
from itbench.cli.commands.create.scenario import create_scenario_command


@click.group(name="create", help="Create benchmark scenarios, faults, or workload configurations.")
def create_group() -> None: ...


create_group.add_command(create_fault_command)
create_group.add_command(create_scenario_command)
