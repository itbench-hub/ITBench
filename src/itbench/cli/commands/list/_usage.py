"""Shared ``--usage`` support for the ``list`` commands."""

from collections.abc import Callable
from typing import Any

import click

from itbench.cli.render import Column, warn_skipped_scenario
from itbench.paths import repository
from itbench.utils.scenarios import load_scenario_docs
from itbench.utils.statistics import compute_usage

USAGE_COLUMN = Column("scenarios", "Used in", style="dim", cell=lambda row: f"{len(row['scenarios'])} scenario(s)")


def usage_option[F: Callable[..., Any]](func: F) -> F:
    """Add a ``--usage`` flag that includes how many scenarios reference each entry."""
    return click.option(
        "--usage",
        "show_usage",
        is_flag=True,
        default=False,
        help="Include how many scenarios use each entry.",
    )(func)


def add_usage(rows: list[dict[str, Any]], key: str, subject: str) -> None:
    """Add ``uses`` and ``scenarios`` to each row, matching ``row[key]`` against scenario references.

    *subject* is ``faults``, ``applications`` or ``waiters``.
    """
    usage = compute_usage(subject, load_scenario_docs(repository.scenarios, on_error=warn_skipped_scenario))
    for row in rows:
        entry = usage.get(row[key])
        row["uses"] = entry.uses if entry else 0
        row["scenarios"] = entry.sorted_scenarios() if entry else []
