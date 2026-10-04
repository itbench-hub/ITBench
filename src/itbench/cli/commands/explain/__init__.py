"""Explain command group for ITBench."""

import click

from itbench.cli.commands.explain.application import explain_application
from itbench.cli.commands.explain.fault import explain_fault
from itbench.cli.commands.explain.waiter import explain_waiter


@click.group(name="explain", help="Display man-page style descriptions of benchmark primitives.")
def explain_group() -> None: ...


explain_group.add_command(explain_fault)
explain_group.add_command(explain_application)
explain_group.add_command(explain_waiter)
