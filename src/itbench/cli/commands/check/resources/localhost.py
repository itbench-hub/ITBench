"""CLI command: itbench check resources localhost"""

import os
import sys

from collections.abc import Sequence
from dataclasses import dataclass

import click

from itbench.cli.render import Column, console, format_option, render_rows

GIB = 1024**3


@dataclass(frozen=True)
class ResourceRequirement:
    """Recommended resources for running one local Kind cluster."""

    cpu: int
    memory_gb: int


REQUIREMENTS: dict[str, ResourceRequirement] = {
    "environment": ResourceRequirement(cpu=8, memory_gb=16),
    "orchestrator": ResourceRequirement(cpu=4, memory_gb=8),
}


@dataclass(frozen=True)
class ResourceCheck:
    """One resource measured against what the selected clusters need."""

    resource: str
    unit: str
    required: int
    found: int

    @property
    def sufficient(self) -> bool:
        return self.found >= self.required


def detect_cpus() -> int:
    """Number of CPUs available to this process."""
    return os.process_cpu_count() or 0


def detect_memory_gb() -> int:
    """Physical memory in whole GiB, rounded down."""
    return os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") // GIB


def evaluate(cpus: int, memory_gb: int, selected: Sequence[str]) -> list[ResourceCheck]:
    """Compare *cpus* and *memory_gb* with the combined needs of the *selected* clusters."""
    return [
        ResourceCheck("CPU", "cores", sum(REQUIREMENTS[name].cpu for name in selected), cpus),
        ResourceCheck("Memory", "GB", sum(REQUIREMENTS[name].memory_gb for name in selected), memory_gb),
    ]


def _print_warnings(checks: Sequence[ResourceCheck]) -> None:
    """Explain each shortfall; print nothing when every resource is sufficient."""
    short = [check for check in checks if not check.sufficient]
    if not short:
        return

    for check in short:
        console.print(
            f"[yellow]This machine does not have the recommended amount of {check.resource} "
            f"({check.required}+ {check.unit}).[/yellow]",
            soft_wrap=True,
        )
    console.print(
        "[yellow]You may experience degraded or inconsistent performance on this machine.[/yellow]",
        soft_wrap=True,
    )


@click.command(
    name="localhost",
    help="Check that this machine has enough CPU and memory for the local Kind clusters. Shortfalls are warnings.",
)
@click.option(
    "--only",
    type=click.Choice(tuple(REQUIREMENTS)),
    default=None,
    help="Check a single cluster instead of both. By default the needs of both clusters are added together.",
)
@format_option
def resources_localhost_command(only: str | None, output_format: str) -> None:
    """Report CPU and memory against the requirements of the environment and orchestrator clusters."""
    selected = [only] if only else list(REQUIREMENTS)
    checks = evaluate(detect_cpus(), detect_memory_gb(), selected)

    rows = [
        {
            "resource": f"{check.resource} ({check.unit})",
            "required": check.required,
            "found": check.found,
            "status": "sufficient" if check.sufficient else "insufficient",
        }
        for check in checks
    ]
    render_rows(
        rows,
        [
            Column("resource", "Resource"),
            Column("required", "Required"),
            Column("found", "Found"),
            Column("status", "Status"),
        ],
        title="Local machine resources",
        footer=f"Checked for: {', '.join(selected)}",
        empty_message="",
        output_format=output_format,
        row_style=lambda row: "yellow" if row["status"] == "insufficient" else "green",
    )

    if output_format != "table":
        return

    _print_warnings(checks)
    if sys.platform == "darwin":
        console.print(
            "[dim]On macOS the clusters run in the container VM, which may have fewer resources than this machine.[/dim]",
            soft_wrap=True,
        )
