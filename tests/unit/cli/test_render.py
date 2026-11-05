"""Tests for the shared CLI rendering helpers."""

import json

import click
import yaml

from click.testing import CliRunner, Result

from itbench.cli.render import Column, format_option, render_rows


def _invoke(rows: list[dict], output_format: str, **kwargs) -> Result:
    @click.command()
    @format_option
    def cmd(output_format: str) -> None:
        render_rows(
            rows,
            [Column("name", "Name"), Column("tags", "Tags")],
            title="Things",
            footer=f"{len(rows)} thing(s).",
            empty_message="[yellow]Nothing here.[/yellow]",
            output_format=output_format,
            **kwargs,
        )

    return CliRunner().invoke(cmd, ["--format", output_format])


def test_table_escapes_markup_in_cells() -> None:
    result = _invoke([{"name": "[bold]boom[/bold] [unclosed", "tags": ["a", "b"]}], "table")

    assert result.exit_code == 0
    assert "[bold]boom[/bold] [unclosed" in result.output
    assert "a, b" in result.output
    assert "1 thing(s)." in result.output


def test_table_empty_prints_message() -> None:
    result = _invoke([], "table")

    assert result.exit_code == 0
    assert "Nothing here." in result.output


def test_json_empty_is_valid_list() -> None:
    result = _invoke([], "json")

    assert result.exit_code == 0
    assert json.loads(result.output) == []


def test_json_and_yaml_keep_structure() -> None:
    rows = [{"name": "x", "tags": ["a", "b"]}]

    assert json.loads(_invoke(rows, "json").output) == rows
    assert yaml.safe_load(_invoke(rows, "yaml").output) == rows


def test_row_style_applied() -> None:
    result = _invoke([{"name": "x", "tags": []}], "table", row_style=lambda row: "dim")

    assert result.exit_code == 0
    assert "x" in result.output
