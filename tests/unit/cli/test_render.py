"""Tests for the shared CLI rendering helpers."""

import json

from unittest.mock import patch

import click
import pytest
import yaml

from click.testing import CliRunner, Result

from itbench.cli.render import (
    Column,
    confirm_or_cancel,
    fail,
    format_option,
    kubeconfig_option,
    render_rows,
    verbose_option,
)


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


def test_kubeconfig_option_is_required_and_reads_env() -> None:
    @click.command()
    @kubeconfig_option
    def cmd(kubeconfig: str) -> None:
        click.echo(kubeconfig)

    assert CliRunner().invoke(cmd, []).exit_code == 2

    result = CliRunner().invoke(cmd, [], env={"KUBECONFIG": "/from/env"})
    assert result.exit_code == 0
    assert result.output.strip() == "/from/env"

    result = CliRunner().invoke(cmd, ["--kubeconfig", "/explicit"], env={"KUBECONFIG": "/from/env"})
    assert result.output.strip() == "/explicit"


def test_verbose_option_defaults_to_false_and_accepts_short_flag() -> None:
    @click.command()
    @verbose_option
    def cmd(verbose: bool) -> None:
        click.echo(str(verbose))

    assert CliRunner().invoke(cmd, []).output.strip() == "False"
    assert CliRunner().invoke(cmd, ["-v"]).output.strip() == "True"
    assert CliRunner().invoke(cmd, ["--verbose"]).output.strip() == "True"


def test_fail_exits_with_status_one() -> None:
    with pytest.raises(SystemExit) as excinfo:
        fail("[red]boom[/red]")

    assert excinfo.value.code == 1


def test_confirm_or_cancel_skips_prompt_with_yes() -> None:
    with patch("itbench.cli.render.questionary.confirm") as mock_confirm:
        assert confirm_or_cancel("Sure?", yes=True) is True

    mock_confirm.assert_not_called()


def test_confirm_or_cancel_fails_without_terminal() -> None:
    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
        pytest.raises(SystemExit) as excinfo,
    ):
        mock_stdin.isatty.return_value = False
        confirm_or_cancel("Sure?", yes=False)

    assert excinfo.value.code == 1
    mock_confirm.assert_not_called()


@pytest.mark.parametrize("answer", [False, None])
def test_confirm_or_cancel_returns_false_when_declined(answer: bool | None) -> None:
    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.return_value.ask.return_value = answer

        assert confirm_or_cancel("Sure?", yes=False) is False


def test_confirm_or_cancel_returns_true_when_accepted() -> None:
    with (
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.return_value.ask.return_value = True

        assert confirm_or_cancel("Sure?", yes=False) is True
