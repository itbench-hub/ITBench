"""Export records command for ITBench."""

import click

from itbench.cli.playbook import run_step
from itbench.cli.render import console, kubeconfig_option, verbose_option
from itbench.utils.runner import create_run


@click.command(name="records", help="Export the recorded telemetry data to storage.")
@kubeconfig_option
@verbose_option
def export_records(kubeconfig: str, verbose: bool) -> None:
    """Export the data collected by the recorders to the configured storage.

    S3 storage is configured with the ITBENCH_S3_BUCKET, ITBENCH_S3_DIRECTORY, ITBENCH_S3_ENDPOINT,
    ITBENCH_S3_USERNAME and ITBENCH_S3_PASSWORD environment variables. These are read by the
    playbook directly, so credentials are never written to disk by this command.

    Examples:

    \b
        itbench export records --kubeconfig ~/.kube/config
        ITBENCH_S3_DIRECTORY=5/1 itbench export records -v --kubeconfig ~/.kube/config
    """
    extra_vars = {
        "environment_tool_management_enabled": False,
        "environment_application_management_enabled": False,
        "environment_recorder_management_enabled": True,
    }

    run_id, extra_vars_file = create_run(extra_vars)
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]", soft_wrap=True)

    run_step(
        playbook="manage_environment.yaml",
        extra_vars=extra_vars,
        tags=["export"],
        status="Exporting records…",
        failure="Record export",
        verbose=verbose,
        run_id=run_id,
        kubeconfig=kubeconfig,
    )

    console.print("[bold green]Records exported successfully.[/bold green]")
