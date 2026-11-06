"""Tests for the remove events CLI command."""

from unittest.mock import patch

from click.testing import CliRunner
from kubernetes.client.exceptions import ApiException

from itbench.cli.commands.remove.events import remove_events


def test_remove_events_success() -> None:
    with patch("itbench.cli.commands.remove.events.delete_events", return_value=3) as mock_delete:
        result = CliRunner().invoke(remove_events, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 0
    assert "Events removed from 3 namespace(s)" in result.output
    mock_delete.assert_called_once_with(kubeconfig="/kube.conf")


def test_remove_events_failure() -> None:
    with patch(
        "itbench.cli.commands.remove.events.delete_events",
        side_effect=ApiException(status=403, reason="Forbidden"),
    ):
        result = CliRunner().invoke(remove_events, ["--kubeconfig", "/kube.conf"])

    assert result.exit_code == 1
    assert "Event removal failed" in result.output
    assert "Forbidden" in result.output
