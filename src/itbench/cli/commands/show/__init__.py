"""Show command group for ITBench."""

import click

from itbench.cli.commands.show.solution import show_solution
from itbench.cli.commands.show.statistics import show_statistics


@click.group(name="show", help="Display aggregated information about the benchmark library.")
def show_group() -> None: ...


show_group.add_command(show_solution)
show_group.add_command(show_statistics)
