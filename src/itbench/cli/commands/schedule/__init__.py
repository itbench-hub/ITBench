"""Schedule command group for ITBench."""

import click

from itbench.cli.commands.schedule.benchmark import schedule_benchmark


@click.group(name="schedule", help="Schedule benchmark runs on the orchestrator.")
def schedule_group() -> None: ...


schedule_group.add_command(schedule_benchmark)
