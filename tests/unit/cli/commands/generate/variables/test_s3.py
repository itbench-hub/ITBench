"""Tests for itbench generate variables s3."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.variables.s3 import variables_s3_command


# ---------------------------------------------------------------------------
# variables_s3_command (CLI integration)
# ---------------------------------------------------------------------------


def _mock_prompts(bucket="my-bucket", endpoint="https://s3.example.com", directory="/custom/dir"):
    return [
        MagicMock(ask=MagicMock(return_value=bucket)),
        MagicMock(ask=MagicMock(return_value=endpoint)),
        MagicMock(ask=MagicMock(return_value=directory)),
    ]


def test_command_writes_s3_yaml(tmp_path: Path) -> None:
    output = tmp_path / "s3.yaml"
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts()

        result = runner.invoke(variables_s3_command, ["--output", str(output)])

    assert result.exit_code == 0, result.output
    assert output.exists()
    content = yaml.safe_load(output.read_text())
    assert content["s3_bucket"] == "my-bucket"
    assert content["s3_endpoint"] == "https://s3.example.com"
    assert content["s3_directory"] == "/custom/dir"


def test_command_defaults_directory_to_itbench(tmp_path: Path) -> None:
    output = tmp_path / "s3.yaml"
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts(directory="itbench")

        result = runner.invoke(variables_s3_command, ["--output", str(output)])

    assert result.exit_code == 0, result.output
    content = yaml.safe_load(output.read_text())
    assert content["s3_directory"] == "itbench"


def test_command_starts_with_yaml_document_marker(tmp_path: Path) -> None:
    output = tmp_path / "s3.yaml"
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts()
        runner.invoke(variables_s3_command, ["--output", str(output)])

    assert output.read_text(encoding="utf-8").startswith("---\n")


def test_command_overwrites_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "s3.yaml"
    output.write_text("---\ns3_bucket: old-bucket\n", encoding="utf-8")
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.s3.questionary") as mock_q:
        mock_q.text.side_effect = _mock_prompts(bucket="new-bucket")
        runner.invoke(variables_s3_command, ["--output", str(output)])

    content = yaml.safe_load(output.read_text())
    assert content["s3_bucket"] == "new-bucket"
    assert content["s3_endpoint"] == "https://s3.example.com"
    assert content["s3_directory"] == "/custom/dir"
