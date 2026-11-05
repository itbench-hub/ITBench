"""Shared output helpers for ITBench CLI commands.

Commands build plain row dictionaries once and hand them to :func:`render_rows`, which
renders either a Rich table or machine-readable JSON / YAML.
"""

import difflib
import json

from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any, NoReturn

import click
import yaml

from rich import box
from rich.console import Console
from rich.markup import escape
from rich.table import Table

console = Console()
err_console = Console(stderr=True)

OUTPUT_FORMATS = ("table", "json", "yaml")


DETAIL_FORMATS = ("text", "json", "yaml")


def detail_format_option[F: Callable[..., Any]](func: F) -> F:
    """Add a ``--format`` option for single-item commands (passed as ``output_format``)."""
    return click.option(
        "--format",
        "output_format",
        type=click.Choice(DETAIL_FORMATS),
        default="text",
        show_default=True,
        help="Output format.",
    )(func)


def format_option[F: Callable[..., Any]](func: F) -> F:
    """Add a ``--format`` option (passed to the command as ``output_format``)."""
    return click.option(
        "--format",
        "output_format",
        type=click.Choice(OUTPUT_FORMATS),
        default="table",
        show_default=True,
        help="Output format.",
    )(func)


@dataclass(frozen=True)
class Column:
    """A table column backed by ``row[key]``.

    By default the value is escaped and lists are comma-joined. Supply *cell* to build
    custom Rich markup (the callable is responsible for escaping any untrusted text).
    """

    key: str
    header: str
    style: str | None = None
    no_wrap: bool = False
    cell: Callable[[Mapping[str, Any]], str] | None = None


def _plain(value: object) -> str:
    """Convert a row value to an escaped string safe to use as a Rich table cell."""
    if value is None:
        return ""
    if isinstance(value, (list, tuple, set)):
        return escape(", ".join(str(v) for v in value))
    return escape(str(value))


def dump_structured(data: object, output_format: str) -> str:
    """Serialise *data* as a JSON or YAML string."""
    normalised = json.loads(json.dumps(data, default=str))
    if output_format == "json":
        return json.dumps(normalised, indent=2)
    return yaml.safe_dump(normalised, sort_keys=False, default_flow_style=False).rstrip()


def emit_structured(data: object, output_format: str) -> None:
    """Print *data* as JSON or YAML to stdout without any Rich wrapping."""
    click.echo(dump_structured(data, output_format))


def warn_skipped_scenario(scenario_id: str, exc: Exception) -> None:
    """Report on stderr that a scenario could not be read; suitable as ``load_scenario_docs(on_error=...)``."""
    err_console.print(f"[yellow]Skipped scenario {escape(scenario_id)}: {escape(str(exc))}[/yellow]")


def exit_not_found(kind: str, key: str, known: Iterable[str], list_command: str) -> NoReturn:
    """Report an unknown identifier on stderr, suggest close matches, and exit with status 1."""
    err_console.print(f"[red]{escape(kind)} '[bold]{escape(key)}[/bold]' not found.[/red]")
    matches = difflib.get_close_matches(key, list(known), n=3)
    if matches:
        err_console.print(f"[dim]Did you mean: {escape(', '.join(matches))}?[/dim]")
    err_console.print(f"[dim]Run `{list_command}` to see what is available.[/dim]")
    raise SystemExit(1)


def render_rows(
    rows: Sequence[Mapping[str, Any]],
    columns: Sequence[Column],
    *,
    title: str,
    footer: str,
    empty_message: str,
    output_format: str = "table",
    row_style: Callable[[Mapping[str, Any]], str | None] | None = None,
) -> None:
    """Render *rows* as a table, JSON or YAML.

    Structured formats always print the full list (``[]`` when empty) so output stays
    parseable; the table format prints *empty_message* instead of an empty table.
    """
    if output_format != "table":
        emit_structured(list(rows), output_format)
        return

    if not rows:
        console.print(empty_message)
        return

    table = Table(title=title, box=box.SIMPLE_HEAVY, header_style="bold")
    for column in columns:
        table.add_column(column.header, style=column.style, no_wrap=column.no_wrap)

    for row in rows:
        cells = [column.cell(row) if column.cell else _plain(row.get(column.key)) for column in columns]
        table.add_row(*cells, style=row_style(row) if row_style else None)

    console.print(table)
    console.print(f"[dim]{footer}[/dim]")
