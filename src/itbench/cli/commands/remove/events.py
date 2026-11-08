"""Remove events command for ITBench."""

import click

from kubernetes.client.exceptions import ApiException  # type: ignore[import-untyped]
from rich.markup import escape

from itbench.cli.render import console, fail, kubeconfig_option
from itbench.utils.cluster import delete_events


@click.command(name="events", help="Remove all Kubernetes events from the cluster.")
@kubeconfig_option
def remove_events(kubeconfig: str) -> None:
    """Remove all Kubernetes events from the cluster so that a run starts from a clean slate.

    Uses the current context of the kubeconfig.

    Examples:

    \b
        itbench remove events --kubeconfig ~/.kube/config
    """
    with console.status("Removing events…"):
        try:
            namespaces = delete_events(kubeconfig=kubeconfig)
        except ApiException as exc:
            fail(f"[red]Event removal failed:[/red] {escape(str(exc.reason))}")

    console.print(f"[bold green]Events removed from {namespaces} namespace(s).[/bold green]")
