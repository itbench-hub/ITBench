"""Export command group for ITBench."""

import click

from itbench.cli.commands.export.records import export_records


@click.group(name="export", help="Export data collected from the cluster.")
def export_group() -> None: ...


export_group.add_command(export_records)
