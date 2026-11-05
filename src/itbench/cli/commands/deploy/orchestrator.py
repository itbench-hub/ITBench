"""Deploy orchestrator command for ITBench."""

import json
import uuid

from pathlib import Path

import click

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()


@click.command(name="orchestrator", help="Deploy the Argo orchestration stack onto the cluster.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
def deploy_orchestrator(kubeconfig: str) -> None:
    """Deploy the Argo orchestration stack (Argo Workflows and Argo Events) onto the cluster.

    Examples:

    \b
        itbench deploy orchestrator --kubeconfig ~/.kube/config
    """
    extra_vars = {"cluster": {"kubeconfig": kubeconfig}}

    run_id = str(uuid.uuid4())
    artifact_dir = Path.cwd() / ".itbench" / "runs" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    extra_vars_file = artifact_dir / "extra_vars.json"
    extra_vars_file.write_text(json.dumps(extra_vars, indent=2), encoding="utf-8")
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]")

    with console.status("Deploying orchestrator…"):
        try:
            run_playbook(
                playbook="manage_orchestrator.yaml",
                extra_vars=extra_vars,
                tags=["install"],
                run_id=run_id,
            )
        except RuntimeError as exc:
            console.print(f"[red]Orchestrator deploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Orchestrator deployed successfully.[/green]")
