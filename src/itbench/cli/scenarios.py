"""CLI handlers for 'scenario' subcommands."""
import argparse

from pathlib import Path

from rich.console import Console

from itbench.scenarios.access import (
    grant_agent_access,
    revoke_agent_access
)
from itbench.scenarios.faults import (
    inject_faults
)
from itbench.scenarios.lifecycle import (
    deploy_applications,
    deploy_recorders,
    deploy_tools,
    remove_fault_resources,
    start_scenario,
    stop_scenario,
    undeploy_applications,
    undeploy_recorders,
    undeploy_tools,
)

console = Console()


def get_default_paths(root: Path | None = None) -> dict[str, Path]:
    if root is None:
        cur = Path.cwd()
        for parent in [cur] + list(cur.parents):
            if (parent / "pyproject.toml").exists() and (parent / "scenarios").exists():
                root = parent
                break
        if root is None:
            root = Path.cwd()

    return {
        "root": root,
        "project_dir": root / "scenarios" / "sre" / "project",
        "specs_dir": root / "library" / "specs" / "scenarios",
    }


def _get_scenario_specs_dir(paths: dict[str, Path], scenario_id: str | int | None) -> Path | None:
    if scenario_id is None:
        return None
    return paths["specs_dir"] / str(scenario_id)


def handle_scenario_start(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    scenario_specs_dir = _get_scenario_specs_dir(paths, args.scenario_id)
    if not scenario_specs_dir or not scenario_specs_dir.exists():
        console.print(f"[bold red]Scenario spec not found for ID:[/bold red] {args.scenario_id}")
        return 1

    console.print(f"[bold blue]Starting scenario {args.scenario_id}...[/bold blue]")
    start_scenario(paths["project_dir"], scenario_specs_dir)
    console.print(f"[bold green]✓ Scenario {args.scenario_id} started![/bold green]")
    return 0


def handle_scenario_stop(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    scenario_specs_dir = _get_scenario_specs_dir(paths, args.scenario_id)
    console.print(f"[bold blue]Stopping scenario {args.scenario_id or ''}...[/bold blue]")
    stop_scenario(paths["project_dir"], scenario_specs_dir)
    console.print(f"[bold green]✓ Scenario stopped![/bold green]")
    return 0


def handle_scenario_inject_fault(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    scenario_specs_dir = _get_scenario_specs_dir(paths, args.scenario_id)
    if not scenario_specs_dir or not scenario_specs_dir.exists():
        console.print(f"[bold red]Scenario spec not found for ID:[/bold red] {args.scenario_id}")
        return 1

    console.print(f"[bold blue]Injecting faults for scenario {args.scenario_id}...[/bold blue]")
    inject_faults(paths["project_dir"], scenario_specs_dir)
    console.print(f"[bold green]✓ Faults injected![/bold green]")
    return 0


def handle_scenario_grant_access(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    output_path = args.output_path or (paths["root"] / "storage" / "kubeconfig")
    console.print(f"[bold blue]Granting agent access and generating restricted kubeconfig at {output_path}...[/bold blue]")
    grant_agent_access(output_path=output_path)
    console.print(f"[bold green]✓ Agent access granted![/bold green]")
    return 0


def handle_scenario_revoke_access(args: argparse.Namespace) -> int:
    console.print(f"[bold blue]Revoking agent access...[/bold blue]")
    revoke_agent_access()
    console.print(f"[bold green]✓ Agent access revoked![/bold green]")
    return 0


def register_scenario_subparsers(subparsers: argparse._SubParsersAction) -> None:
    start_p = subparsers.add_parser("start", help="Start a scenario (deploy tools, apps, recorders, and inject faults)")
    start_p.add_argument("scenario_id", type=str, help="Scenario number/ID")
    start_p.set_defaults(func=handle_scenario_start)

    stop_p = subparsers.add_parser("stop", help="Stop a scenario (clean up resources, apps, and tools)")
    stop_p.add_argument("scenario_id", type=str, nargs="?", default=None, help="Scenario number/ID (optional)")
    stop_p.set_defaults(func=handle_scenario_stop)

    inject_p = subparsers.add_parser("inject-faults", help="Inject scenario faults directly")
    inject_p.add_argument("scenario_id", type=str, help="Scenario number/ID")
    inject_p.set_defaults(func=handle_scenario_inject_fault)

    grant_p = subparsers.add_parser("grant-access", help="Create agent RBAC and output restricted kubeconfig")
    grant_p.add_argument("--output-path", type=Path, default=None)
    grant_p.set_defaults(func=handle_scenario_grant_access)

    revoke_p = subparsers.add_parser("revoke-access", help="Revoke agent RBAC resources")
    revoke_p.set_defaults(func=handle_scenario_revoke_access)
