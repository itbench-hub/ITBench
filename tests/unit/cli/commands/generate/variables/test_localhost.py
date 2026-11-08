"""Tests for itbench generate variables localhost."""

import io

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.variables.localhost import variables_localhost_command

_QUESTIONARY = "itbench.cli.commands.generate.variables.localhost.questionary"
_OLD_CONTENT = "---\nstorage_localhost_directory: /old\n"


@pytest.fixture
def output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the repository root at a temporary directory and return the file the command writes."""
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))
    return tmp_path / "scenarios" / "sre" / "inventory" / "group_vars" / "storage" / "localhost.yaml"


def _mock_prompt(directory: str = "/data/records") -> MagicMock:
    return MagicMock(ask=MagicMock(return_value=directory))


def test_command_writes_localhost_yaml_to_the_repository_group_vars(output: Path) -> None:
    with patch(_QUESTIONARY) as mock_q:
        mock_q.text.return_value = _mock_prompt()

        result = CliRunner().invoke(variables_localhost_command, [])

    assert result.exit_code == 0, result.output
    assert yaml.safe_load(output.read_text(encoding="utf-8")) == {"storage_localhost_directory": "/data/records"}


def test_command_starts_with_yaml_document_marker(output: Path) -> None:
    with patch(_QUESTIONARY) as mock_q:
        mock_q.text.return_value = _mock_prompt()

        CliRunner().invoke(variables_localhost_command, [])

    assert output.read_text(encoding="utf-8").startswith("---\n")


def test_command_does_not_accept_an_output_path(output: Path) -> None:
    result = CliRunner().invoke(variables_localhost_command, ["--output", "/elsewhere/localhost.yaml"])

    assert result.exit_code == 2
    assert "No such option" in result.output
    assert not output.exists()


def test_command_aborts_when_prompt_is_cancelled(output: Path) -> None:
    with patch(_QUESTIONARY) as mock_q:
        mock_q.text.return_value = MagicMock(ask=MagicMock(return_value=None))

        result = CliRunner().invoke(variables_localhost_command, [])

    assert result.exit_code == 1
    assert not output.exists()


def test_command_overwrites_existing_file_with_yes(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text(_OLD_CONTENT, encoding="utf-8")

    with patch(_QUESTIONARY) as mock_q:
        mock_q.text.return_value = _mock_prompt("/new")

        CliRunner().invoke(variables_localhost_command, ["-y"])

    assert yaml.safe_load(output.read_text(encoding="utf-8"))["storage_localhost_directory"] == "/new"


def test_command_overwrites_existing_file_when_confirmed(output: Path, terminal_input: io.BytesIO) -> None:
    output.parent.mkdir(parents=True)
    output.write_text(_OLD_CONTENT, encoding="utf-8")

    with (
        patch(_QUESTIONARY) as mock_q,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_confirm.return_value.ask.return_value = True
        mock_q.text.return_value = _mock_prompt("/new")

        CliRunner().invoke(variables_localhost_command, [], input=terminal_input)

    assert mock_confirm.call_args.args[0] == f"{output} already exists. Overwrite it?"
    assert yaml.safe_load(output.read_text(encoding="utf-8"))["storage_localhost_directory"] == "/new"


def test_command_keeps_existing_file_when_overwrite_declined(output: Path, terminal_input: io.BytesIO) -> None:
    output.parent.mkdir(parents=True)
    output.write_text(_OLD_CONTENT, encoding="utf-8")

    with (
        patch(_QUESTIONARY) as mock_q,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_confirm.return_value.ask.return_value = False

        result = CliRunner().invoke(variables_localhost_command, [], input=terminal_input)

    assert result.exit_code == 0
    assert "Existing file kept" in result.output
    assert output.read_text(encoding="utf-8") == _OLD_CONTENT
    mock_q.text.assert_not_called()


def test_command_requires_yes_to_overwrite_without_terminal(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text(_OLD_CONTENT, encoding="utf-8")

    with patch("itbench.cli.render.sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False

        result = CliRunner().invoke(variables_localhost_command, [])

    assert result.exit_code == 1
    assert "--yes" in result.output
    assert output.read_text(encoding="utf-8") == _OLD_CONTENT
