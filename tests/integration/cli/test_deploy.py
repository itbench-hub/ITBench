"""Integration tests for the ITBench CLI deployment and management commands against a live cluster."""

import subprocess

from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner

from itbench.cli.commands.generate.kubeconfig import generate_kubeconfig_command

pytestmark = pytest.mark.integration


def test_cli_lifecycle_tools_and_kubeconfig(itbench_cli: CliRunner, kubeconfig: str, tmp_path: Path) -> None:
    """Test full CLI lifecycle: deploy agents, generate restricted kubeconfigs, and undeploy."""
    deploy = subprocess.run(
        ["uv", "run", "itbench", "deploy", "environment", "--only", "agents", "--kubeconfig", kubeconfig],
        capture_output=True,
        text=True,
        check=False,
    )
    assert deploy.returncode == 0, f"itbench deploy failed: {deploy.stderr}\n{deploy.stdout}"

    try:
        # The remediation agent is off by default (`agents_remediation_enabled: false`) and the CLI has no
        # flag to enable it, so only the diagnosis agent exists after a default deploy.
        for mission in ("diagnosis",):
            out_dir = tmp_path / mission
            result = itbench_cli.invoke(
                generate_kubeconfig_command,
                ["--mission", mission, "--output", str(out_dir), "--kubeconfig", kubeconfig],
                catch_exceptions=False,
            )
            assert result.exit_code == 0, result.output

            target_file = out_dir / f"kubeconfig-{mission}"
            assert target_file.exists()

            content = yaml.safe_load(target_file.read_text(encoding="utf-8"))
            assert len(content["clusters"]) == 1
            assert len(content["users"]) == 1
            assert len(content["contexts"]) == 1
            assert "token" in content["users"][0]["user"]
    finally:
        undeploy = subprocess.run(
            ["uv", "run", "itbench", "undeploy", "environment", "--yes", "--kubeconfig", kubeconfig],
            capture_output=True,
            text=True,
            check=False,
        )
        assert undeploy.returncode == 0, f"itbench undeploy failed: {undeploy.stderr}\n{undeploy.stdout}"
