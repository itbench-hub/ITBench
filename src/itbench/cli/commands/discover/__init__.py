"""Discover command group for ITBench."""

import click

from itbench.cli.commands.discover.targets import targets


@click.group(name="discover", help="Discover benchmark primitives from live sources.")
def discover_group() -> None: ...


discover_group.add_command(targets)
