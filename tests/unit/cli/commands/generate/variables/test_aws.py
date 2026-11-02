"""Tests for itbench generate variables aws."""

import os

from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.variables.aws import (
    _build_doc,
    _prompt,
    variables_aws_command,
)


# ---------------------------------------------------------------------------
# _build_doc
# ---------------------------------------------------------------------------

_CREDS = {
    "aws_region": "us-east-1",
    "aws_access_key_id": "AKIATEST",
    "aws_secret_access_key": "supersecret", # pragma: allowlist secret
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


def test_command_writes_aws_yaml(tmp_path: Path) -> None:
    output = tmp_path / "aws.yaml"
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q, \
         patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"):
        mock_q.text.side_effect = [
            MagicMock(ask=MagicMock(return_value="us-east-1")),  # region
            MagicMock(ask=MagicMock(return_value="AKIATEST")),   # access_key_id
        ]
        mock_q.password.side_effect = [
            MagicMock(ask=MagicMock(return_value="supersecret")),  # secret_access_key
        ]

        result = runner.invoke(variables_aws_command, ["--output", str(output)])

    assert result.exit_code == 0, result.output
    assert output.exists()
    content = yaml.safe_load(output.read_text())
    assert content["aws_region"] == "us-east-1"
    assert "$ANSIBLE_VAULT;" in content["aws_access_key_id"]
    assert "$ANSIBLE_VAULT;" in content["aws_secret_access_key"]


def test_command_starts_with_yaml_document_marker(tmp_path: Path) -> None:
    output = tmp_path / "aws.yaml"
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q, \
         patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"):
        mock_q.text.side_effect = [
            MagicMock(ask=MagicMock(return_value="eu-west-1")),
            MagicMock(ask=MagicMock(return_value="AKIATEST")),
        ]
        mock_q.password.side_effect = [
            MagicMock(ask=MagicMock(return_value="supersecret")),
        ]
        runner.invoke(variables_aws_command, ["--output", str(output)])

    assert output.read_text(encoding="utf-8").startswith("---\n")


def test_command_overwrites_existing_file(tmp_path: Path) -> None:
    output = tmp_path / "aws.yaml"
    output.write_text("---\naws_region: old-region\n", encoding="utf-8")
    runner = CliRunner()

    with patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q, \
         patch("itbench.cli.commands.generate.variables.aws.resolve_vault_password", return_value="vaultpass"):
        mock_q.text.side_effect = [
            MagicMock(ask=MagicMock(return_value="us-west-2")),
            MagicMock(ask=MagicMock(return_value="AKIANEW")),
        ]
        mock_q.password.side_effect = [
            MagicMock(ask=MagicMock(return_value="newsecret")),
        ]
        runner.invoke(variables_aws_command, ["--output", str(output)])

    content = yaml.safe_load(output.read_text())
    assert content["aws_region"] == "us-west-2"


def test_command_fails_when_no_vault_password_source(tmp_path: Path) -> None:
    output = tmp_path / "aws.yaml"
    runner = CliRunner()

    env = {k: v for k, v in os.environ.items() if k != "ANSIBLE_VAULT_PASSWORD_FILE"}
    with patch.dict(os.environ, env, clear=True), \
         patch("itbench.utils.ansible_vault.DEFAULT_VAULT_PASSWORD_FILE", None), \
         patch("itbench.cli.commands.generate.variables.aws.questionary") as mock_q:
        mock_q.text.side_effect = [
            MagicMock(ask=MagicMock(return_value="us-east-1")),
            MagicMock(ask=MagicMock(return_value="AKIATEST")),
        ]
        mock_q.password.side_effect = [
            MagicMock(ask=MagicMock(return_value="supersecret")),
        ]
        result = runner.invoke(variables_aws_command, ["--output", str(output)])

    assert result.exit_code != 0
    assert "No Ansible Vault password source found" in result.output
