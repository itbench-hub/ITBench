"""CLI handlers for 'cluster', 'localhost', and 'ansible' subcommands."""
import argparse
from pathlib import Path

from rich.console import Console

from itbench.ansible.generate_roles import generate_role_files
from itbench.cli.constants import resolve
from itbench.cluster.configure import configure_cluster
from itbench.localhost.resources import check_resources

console = Console()


def handle_cluster_configure(args: argparse.Namespace) -> int:
    console.print("[bold blue]Configuring environment cluster (CSRs & sandbox nodes)...[/bold blue]")
    try:
        configure_cluster(kubeconfig_path=args.kubeconfig)
        console.print("[bold green]✓ Cluster configured successfully![/bold green]")
        return 0
    except Exception as e:
        console.print(f"[bold red]✗ Cluster configuration failed:[/bold red] {e}")
        return 1


def handle_localhost_check_resources(args: argparse.Namespace) -> int:
    console.print(f"[bold blue]Checking host resources for target '{args.target}'...[/bold blue]")
    ok = check_resources(args.target)
    if ok:
        console.print("[bold green]✓ Host resources meet recommended minimums.[/bold green]")
        return 0
    else:
        console.print("[bold yellow]⚠ Host resources below recommended minimums (see warnings above).[/bold yellow]")
        return 0


def handle_ansible_generate_roles(args: argparse.Namespace) -> int:
    paths = resolve(args.root)
    lib_dir = args.library_index_directory or paths.library_index_directory
    playbooks_dir = args.playbooks_directory or paths.playbooks_directory

    console.print("[bold blue]Generating Ansible role files (faults & waiters)...[/bold blue]")
    try:
        generate_role_files(lib_dir, playbooks_dir)
        console.print("[bold green]✓ Role files generated successfully![/bold green]")
        return 0
    except Exception as e:
        console.print(f"[bold red]✗ Role file generation failed:[/bold red] {e}")
        return 1


def register_cluster_subparsers(subparsers: argparse._SubParsersAction) -> None:
    conf_p = subparsers.add_parser("configure", help="Configure cluster nodes and approve CSRs")
    conf_p.add_argument("--kubeconfig", type=str, default=None, help="Path to kubeconfig")
    conf_p.set_defaults(func=handle_cluster_configure)


def register_localhost_subparsers(subparsers: argparse._SubParsersAction) -> None:
    res_p = subparsers.add_parser("check-resources", help="Check localhost CPU and RAM for cluster target")
    res_p.add_argument("--target", required=True, choices=["argo-stack", "environment-cluster"])
    res_p.set_defaults(func=handle_localhost_check_resources)


def register_ansible_subparsers(subparsers: argparse._SubParsersAction) -> None:
    gen_p = subparsers.add_parser("generate-roles", help="Generate Ansible role files from library indexes")
    gen_p.add_argument("--library_index_directory", type=Path, default=None)
    gen_p.add_argument("--playbooks_directory", type=Path, default=None)
    gen_p.set_defaults(func=handle_ansible_generate_roles)
