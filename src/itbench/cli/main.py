"""Main entry points for ITBench CLIs ('itbench' and 'library')."""
import argparse
import sys

from pathlib import Path

from itbench.cli.library import register_library_subparsers
from itbench.cli.operations import (
    register_ansible_subparsers,
    register_cluster_subparsers,
    register_localhost_subparsers,
)
from itbench.cli.scenarios import register_scenario_subparsers
from itbench.utils.logging import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="itbench",
        description="ITBench - Benchmark platform for IT and SRE AI Agents",
    )
    parser.add_argument("--root", type=Path, default=None, help="Root directory of ITBench repository")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug logging")

    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    # 'library' subcommands under 'itbench library ...'
    lib_parser = subparsers.add_parser("library", help="Manage ITBench library (validate, generate, scaffold, search)")
    lib_subparsers = lib_parser.add_subparsers(dest="library_action", required=True)
    register_library_subparsers(lib_subparsers)

    # 'scenario' subcommands under 'itbench scenario ...'
    scen_parser = subparsers.add_parser("scenario", help="Manage scenario lifecycle (start, stop, inject-faults, access)")
    scen_subparsers = scen_parser.add_subparsers(dest="scenario_action", required=True)
    register_scenario_subparsers(scen_subparsers)

    # 'cluster' subcommands under 'itbench cluster ...'
    clust_parser = subparsers.add_parser("cluster", help="Manage and configure environment clusters")
    clust_subparsers = clust_parser.add_subparsers(dest="cluster_action", required=True)
    register_cluster_subparsers(clust_subparsers)

    # 'localhost' subcommands under 'itbench localhost ...'
    local_parser = subparsers.add_parser("localhost", help="Check local machine hardware resources")
    local_subparsers = local_parser.add_subparsers(dest="localhost_action", required=True)
    register_localhost_subparsers(local_subparsers)

    # 'ansible' subcommands under 'itbench ansible ...'
    ans_parser = subparsers.add_parser("ansible", help="Manage Ansible role files and assets")
    ans_subparsers = ans_parser.add_subparsers(dest="ansible_action", required=True)
    register_ansible_subparsers(ans_subparsers)

    return parser


def build_library_parser() -> argparse.ArgumentParser:
    """Standalone parser for the 'library' command directly."""
    parser = argparse.ArgumentParser(
        prog="library",
        description="ITBench Library - Validate, generate, scaffold, and query benchmark items",
    )
    parser.add_argument("--root", type=Path, default=None, help="Root directory of ITBench repository")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose/debug logging")

    subparsers = parser.add_subparsers(dest="library_action", required=True)
    register_library_subparsers(subparsers)
    return parser


def main(args: list[str] | None = None) -> int:
    parser = build_parser()
    parsed_args = parser.parse_args(args)
    level = 10 if getattr(parsed_args, "verbose", False) else 20
    configure_logging(level=level)

    if hasattr(parsed_args, "func"):
        return parsed_args.func(parsed_args)
    parser.print_help()
    return 1


def library_cli_main(args: list[str] | None = None) -> int:
    parser = build_library_parser()
    parsed_args = parser.parse_args(args)
    level = 10 if getattr(parsed_args, "verbose", False) else 20
    configure_logging(level=level)

    if hasattr(parsed_args, "func"):
        return parsed_args.func(parsed_args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
