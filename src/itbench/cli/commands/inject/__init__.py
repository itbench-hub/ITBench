"""Inject command group for ITBench."""

import click

from itbench.cli.commands.inject.faults import inject_faults


@click.group(name="inject", help="Inject faults into the cluster.")
def inject_group() -> None: ...


inject_group.add_command(inject_faults)
