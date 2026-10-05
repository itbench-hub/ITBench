"""Prepare command group for ITBench."""

import click

from itbench.cli.commands.prepare.cluster import prepare_cluster_command


@click.group(name="prepare", help="Prepare cluster and infrastructure for ITBench scenarios.")
def prepare_group() -> None: ...


prepare_group.add_command(prepare_cluster_command)
