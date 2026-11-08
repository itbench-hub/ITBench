"""Remove command group for ITBench."""

import click

from itbench.cli.commands.remove.events import remove_events
from itbench.cli.commands.remove.faults import remove_faults


@click.group(name="remove", help="Remove events or injected faults from the cluster.")
def remove_group() -> None: ...


remove_group.add_command(remove_events)
remove_group.add_command(remove_faults)
