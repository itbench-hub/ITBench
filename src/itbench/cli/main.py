"""Main CLI entrypoint for ITBench."""

import click

from itbench.cli.commands.create import create_group
from itbench.cli.commands.deploy import deploy_group
from itbench.cli.commands.discover import discover_group
from itbench.cli.commands.explain import explain_group
from itbench.cli.commands.generate import generate_group
from itbench.cli.commands.list import list_group
from itbench.cli.commands.show import show_group
from itbench.cli.commands.undeploy import undeploy_group


@click.group(
    name="itbench",
    help="ITBench CLI - Command-line interface for IT domain AI agent benchmarks and scenario management.",
)
@click.version_option(package_name="itbench")
def cli() -> None: ...


cli.add_command(deploy_group)
cli.add_command(undeploy_group)
cli.add_command(create_group)
cli.add_command(discover_group)
cli.add_command(explain_group)
cli.add_command(generate_group)
cli.add_command(list_group)
cli.add_command(show_group)


if __name__ == "__main__":
    cli()
