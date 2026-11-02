"""Tests for itbench.utils.ansible_vault."""

import os

from pathlib import Path
from unittest.mock import patch

import pytest

from itbench.utils.ansible_vault import resolve_vault_password, vault_encrypt


# ---------------------------------------------------------------------------
# resolve_vault_password
# ---------------------------------------------------------------------------


def test_resolve_from_env_var(tmp_path: Path) -> None:
    pw_file = tmp_path / ".vault_pass"
    pw_file.write_text("mysecretpassword\n", encoding="utf-8")

    with patch.dict(os.environ, {"ANSIBLE_VAULT_PASSWORD_FILE": str(pw_file)}):
        assert resolve_vault_password() == "mysecretpassword"


def test_resolve_strips_whitespace(tmp_path: Path) -> None:
    pw_file = tmp_path / ".vault_pass"
    pw_file.write_text("  padded  \n", encoding="utf-8")

    with patch.dict(os.environ, {"ANSIBLE_VAULT_PASSWORD_FILE": str(pw_file)}):
        assert resolve_vault_password() == "padded"


def test_resolve_missing_file_raises(tmp_path: Path) -> None:
    from click import ClickException

    with patch.dict(os.environ, {"ANSIBLE_VAULT_PASSWORD_FILE": str(tmp_path / "nonexistent")}):
        with pytest.raises(ClickException, match="not found"):
            resolve_vault_password()


def test_resolve_no_source_raises() -> None:
    from click import ClickException

    env = {k: v for k, v in os.environ.items() if k != "ANSIBLE_VAULT_PASSWORD_FILE"}
    with patch.dict(os.environ, env, clear=True), \
         patch("itbench.utils.ansible_vault.DEFAULT_VAULT_PASSWORD_FILE", None):
        with pytest.raises(ClickException, match="No Ansible Vault password source found"):
            resolve_vault_password()


def test_resolve_falls_back_to_ansible_constants(tmp_path: Path) -> None:
    pw_file = tmp_path / ".vault_pass"
    pw_file.write_text("constantspass", encoding="utf-8")

    env = {k: v for k, v in os.environ.items() if k != "ANSIBLE_VAULT_PASSWORD_FILE"}
    with patch.dict(os.environ, env, clear=True), \
         patch("itbench.utils.ansible_vault.DEFAULT_VAULT_PASSWORD_FILE", str(pw_file)):
        assert resolve_vault_password() == "constantspass"


# ---------------------------------------------------------------------------
# vault_encrypt
# ---------------------------------------------------------------------------


def test_vault_encrypt_returns_ansible_vault_header() -> None:
    assert vault_encrypt("mysecret", "vaultpass").startswith("$ANSIBLE_VAULT;")


def test_vault_encrypt_different_passwords_differ() -> None:
    assert vault_encrypt("mysecret", "password1") != vault_encrypt("mysecret", "password2")


def test_vault_encrypt_is_decryptable() -> None:
    from ansible.parsing.vault import VaultLib, VaultSecret

    plaintext = "my-access-key"
    password = "strongpass" # pragma: allowlist secret
    ciphertext = vault_encrypt(plaintext, password)

    secret = VaultSecret(password.encode())
    vault = VaultLib(secrets=[("default", secret)])
    assert vault.decrypt(ciphertext).decode() == plaintext
