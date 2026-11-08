"""Tests for itbench generate variables aws."""

import io
import os

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.variables.aws import (
    _build_doc,
    variables_aws_command,
)

# ---------------------------------------------------------------------------
# _build_doc
# ---------------------------------------------------------------------------

_CREDS = {
    "aws_region": "us-east-1",
    "aws_access_key_id": "AKIATEST",
    "aws_secret_access_key": "supersecret",  # pragma: allowlist secret
}


def test_build_doc_region_is_plaintext() -> None:
    with patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"):
        doc = _build_doc(_CREDS)
    assert doc["aws_region"] == "us-east-1"


def test_build_doc_access_key_id_is_encrypted() -> None:
    with patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"):
        doc = _build_doc(_CREDS)
    assert "$ANSIBLE_VAULT;" in doc["aws_access_key_id"]


def test_build_doc_secret_access_key_is_encrypted() -> None:
    with patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"):
        doc = _build_doc(_CREDS)
    assert "$ANSIBLE_VAULT;" in doc["aws_secret_access_key"]


# ---------------------------------------------------------------------------
# variables_aws_command (CLI integration)
# ---------------------------------------------------------------------------


@pytest.fixture
def output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """Point the repository root at a temporary directory and return the file the command writes."""
    monkeypatch.setenv("ITBENCH_REPOSITORY_PATH", str(tmp_path))
    return tmp_path / "scenarios" / "sre" / "inventory" / "group_vars" / "all" / "aws.yaml"


def _mock_prompts(
    mock_q: MagicMock, region: str = "us-east-1", key_id: str = "AKIATEST", secret: str = "supersecret"
) -> None:
    mock_q.text.side_effect = [
        MagicMock(ask=MagicMock(return_value=region)),
        MagicMock(ask=MagicMock(return_value=key_id)),
    ]
    mock_q.password.side_effect = [MagicMock(ask=MagicMock(return_value=secret))]


def test_command_writes_aws_yaml_to_the_repository_group_vars(output: Path) -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q,
        patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"),
    ):
        _mock_prompts(mock_q)

        result = runner.invoke(variables_aws_command, [])

    assert result.exit_code == 0, result.output
    assert output.exists()
    content = yaml.safe_load(output.read_text())
    assert content["aws_region"] == "us-east-1"
    assert "$ANSIBLE_VAULT;" in content["aws_access_key_id"]
    assert "$ANSIBLE_VAULT;" in content["aws_secret_access_key"]


def test_command_does_not_accept_an_output_path(output: Path) -> None:
    result = CliRunner().invoke(variables_aws_command, ["--output", "/elsewhere/aws.yaml"])

    assert result.exit_code == 2
    assert "No such option" in result.output
    assert not output.exists()


def test_command_starts_with_yaml_document_marker(output: Path) -> None:
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q,
        patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"),
    ):
        _mock_prompts(mock_q, region="eu-west-1")
        runner.invoke(variables_aws_command, [])

    assert output.read_text(encoding="utf-8").startswith("---\n")


def test_command_overwrites_existing_file_with_yes(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\naws_region: old-region\n", encoding="utf-8")
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q,
        patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"),
    ):
        _mock_prompts(mock_q, region="us-west-2", key_id="AKIANEW", secret="newsecret")  # pragma: allowlist secret
        runner.invoke(variables_aws_command, ["--yes"])

    content = yaml.safe_load(output.read_text())
    assert content["aws_region"] == "us-west-2"


def test_command_overwrites_existing_file_when_confirmed(output: Path, terminal_input: io.BytesIO) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\naws_region: old-region\n", encoding="utf-8")
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q,
        patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"),
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_confirm.return_value.ask.return_value = True
        _mock_prompts(mock_q, region="us-west-2")

        runner.invoke(variables_aws_command, [], input=terminal_input)

    assert mock_confirm.call_args.args[0] == f"{output} already exists. Overwrite it?"
    assert yaml.safe_load(output.read_text())["aws_region"] == "us-west-2"


def test_command_keeps_existing_file_when_overwrite_declined(output: Path, terminal_input: io.BytesIO) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\naws_region: old-region\n", encoding="utf-8")
    runner = CliRunner()

    with (
        patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q,
        patch("itbench.cli.render.questionary.confirm") as mock_confirm,
    ):
        mock_confirm.return_value.ask.return_value = False

        result = runner.invoke(variables_aws_command, [], input=terminal_input)

    assert result.exit_code == 0
    assert "Existing file kept" in result.output
    assert output.read_text(encoding="utf-8") == "---\naws_region: old-region\n"
    mock_q.text.assert_not_called()


def test_command_requires_yes_to_overwrite_without_terminal(output: Path) -> None:
    output.parent.mkdir(parents=True)
    output.write_text("---\naws_region: old-region\n", encoding="utf-8")
    runner = CliRunner()

    with patch("itbench.cli.render.sys.stdin") as mock_stdin:
        mock_stdin.isatty.return_value = False

        result = runner.invoke(variables_aws_command, [])

    assert result.exit_code == 1
    assert "--yes" in result.output
    assert output.read_text(encoding="utf-8") == "---\naws_region: old-region\n"


def test_command_fails_when_no_vault_password_source(output: Path) -> None:
    runner = CliRunner()

    env = {k: v for k, v in os.environ.items() if k != "ANSIBLE_VAULT_PASSWORD_FILE"}
    with (
        patch.dict(os.environ, env, clear=True),
        patch("itbench.utils.ansible_vault.DEFAULT_VAULT_PASSWORD_FILE", None),
        patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q,
    ):
        _mock_prompts(mock_q)
        result = runner.invoke(variables_aws_command, [])

    assert result.exit_code != 0
    assert "No Ansible Vault password source found" in result.output
    assert not output.exists()
