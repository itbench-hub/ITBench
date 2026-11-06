"""Tests for itbench generate variables s3."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.variables.s3 import variables_s3_command

# ---------------------------------------------------------------------------
# variables_s3_command (CLI integration)
# ---------------------------------------------------------------------------


@pytest.fixture
def output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the repository root at a temporary directory and return the file the command writes."""
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))
    return tmp_path / "scenarios" / "sre" / "inventory" / "group_vars" / "storage" / "s3.yaml"


def _mock_prompts(bucket="my-bucket", endpoint="https://s3.example.com", directory="/custom/dir"):
    return [
        MagicMock(ask=MagicMock(return_value=bucket)),
        MagicMock(ask=MagicMock(return_value=endpoint)),
        MagicMock(ask=MagicMock(return_value=directory)),
    ]


def test_command_writes_s3_yaml_to_the_repository_group_vars(output: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts()

        result = runner.invoke(variables_s3_command, [])

    assert result.exit_code == 0, result.output
    assert output.exists()
    content = yaml.safe_load(output.read_text())
    assert content["storage_s3_bucket"] == "my-bucket"
    assert content["storage_s3_endpoint"] == "https://s3.example.com"
    assert content["storage_s3_directory"] == "/custom/dir"


def test_command_does_not_accept_an_output_path(output: Path) -> None:
    result = CliRunner().invoke(variables_s3_command, ["--output", "/elsewhere/s3.yaml"])

    assert result.exit_code == 2
    assert "No such option" in result.output
    assert not output.exists()


def test_command_defaults_directory_to_itbench(output: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts(directory="itbench")

        result = runner.invoke(variables_s3_command, [])

    assert result.exit_code == 0, result.output
    content = yaml.safe_load(output.read_text())
    assert content["storage_s3_directory"] == "itbench"


def test_command_starts_with_yaml_document_marker(output: Path) -> None:
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts()
        runner.invoke(variables_s3_command, [])

    assert output.read_text(encoding="utf-8").startswith("---\n")


def test_command_overwrites_existing_file_with_yes(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\ns3_bucket: old-bucket\n", encoding="utf-8")
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts(bucket="new-bucket")
        runner.invoke(variables_s3_command, ["-y"])

    content = yaml.safe_load(output.read_text())
    assert content["storage_s3_bucket"] == "new-bucket"
    assert content["storage_s3_endpoint"] == "https://s3.example.com"
    assert content["storage_s3_directory"] == "/custom/dir"


def test_command_overwrites_existing_file_when_confirmed(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\ns3_bucket: old-bucket\n", encoding="utf-8")
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q,
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.return_value.ask.return_value = True
        mock_q.text.side_effect = _mock_prompts(bucket="new-bucket")

        runner.invoke(variables_s3_command, [])

    assert mock_confirm.call_args.args[0] == f"{output} already exists. Overwrite it?"
    assert yaml.safe_load(output.read_text())["storage_s3_bucket"] == "new-bucket"


def test_command_keeps_existing_file_when_overwrite_declined(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\ns3_bucket: old-bucket\n", encoding="utf-8")
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q,
        patch("itbench.cli.render.sys.stdin") as mock_stdin,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_stdin.isatty.return_value = True
        mock_confirm.return_value.ask.return_value = False

        result = runner.invoke(variables_s3_command, [])

    assert result.exit_code == 0
    assert "Existing file kept" in result.output
    assert output.read_text(encoding="utf-8") == "---\ns3_bucket: old-bucket\n"
    mock_q.text.assert_not_called()


def test_command_requires_yes_to_overwrite_without_terminal(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\ns3_bucket: old-bucket\n", encoding="utf-8")
    runner = CliRunner()

    with patch("itbench.cli.render.sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False

        result = runner.invoke(variables_s3_command, [])

    assert result.exit_code == 1
    assert "--yes" in result.output
    assert output.read_text(encoding="utf-8") == "---\ns3_bucket: old-bucket\n"
