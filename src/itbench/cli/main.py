"""Main CLI entrypoint for ITBench."""

import click

from itbench.cli.commands.check import check_group
from itbench.cli.commands.configure import configure_group
from itbench.cli.commands.create import create_group
from itbench.cli.commands.deploy import deploy_group
from itbench.cli.commands.explain import explain_group
from itbench.cli.commands.export import export_group
from itbench.cli.commands.generate import generate_group
from itbench.cli.commands.inject import inject_group
from itbench.cli.commands.list import list_group
from itbench.cli.commands.remove import remove_group
from itbench.cli.commands.schedule import schedule_group
from itbench.cli.commands.undeploy import undeploy_group


@click.group(
    name="itbench",
    help="ITBench CLI - Command-line interface for IT domain AI agent benchmarks and scenario management.",
)
@click.version_option(package_name="itbench")
def cli() -> None: ...


cli.add_command(deploy_group)
cli.add_command(undeploy_group)
cli.add_command(configure_group)
cli.add_command(check_group)
cli.add_command(inject_group)
cli.add_command(remove_group)
cli.add_command(export_group)
cli.add_command(schedule_group)
cli.add_command(create_group)
cli.add_command(explain_group)
cli.add_command(generate_group)
cli.add_command(list_group)


if __name__ == "__main__":
    cli()
