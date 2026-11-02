"""Ansible Vault helpers — password resolution and string encryption."""

import os
from pathlib import Path

import click

from ansible.constants import DEFAULT_VAULT_PASSWORD_FILE
from ansible.parsing.vault import VaultLib, VaultSecret


def resolve_vault_password() -> str:
    """Return the vault password from the environment.

    Resolution order (mirrors standard Ansible behaviour):
    1. ``ANSIBLE_VAULT_PASSWORD_FILE`` env var → read file contents.
    2. ``DEFAULT_VAULT_PASSWORD_FILE`` from ``ansible.constants`` (set via
       ``ansible.cfg``).

    Raises ``click.ClickException`` when no source can be found.
    """
    password_file: str | None = os.environ.get(
        "ANSIBLE_VAULT_PASSWORD_FILE",
        str(DEFAULT_VAULT_PASSWORD_FILE) if DEFAULT_VAULT_PASSWORD_FILE else None,
    )
    if password_file:
        path = Path(password_file).expanduser()
        if not path.exists():
            raise click.ClickException(
                f"Vault password file not found: {path}\n"
                "Set ANSIBLE_VAULT_PASSWORD_FILE to a valid path."
            )
        return path.read_text(encoding="utf-8").strip()

    raise click.ClickException(
        "No Ansible Vault password source found.\n"
        "Set the ANSIBLE_VAULT_PASSWORD_FILE environment variable to a password file."
    )


def vault_encrypt(plaintext: str, vault_password: str) -> str:
    """Return a ``$ANSIBLE_VAULT`` encrypted string for *plaintext*.

    Uses the ansible-core Python API directly — no subprocess required.
    """
    secret = VaultSecret(vault_password.encode())
    vault = VaultLib(secrets=[("default", secret)])
    return vault.encrypt(plaintext).decode()
