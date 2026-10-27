"""Deploy tools command for ITBench."""

import json
import uuid

from pathlib import Path

import click
import questionary
import yaml

from rich.console import Console

from itbench.utils.runner import run_playbook

console = Console()

_LIBRARY_ROOT = Path(__file__).parents[6] / "library"

_DEFAULTS_DIR = (
    Path(__file__).parents[5]
    / "scenarios" / "sre" / "project"
    / "roles" / "tools" / "defaults" / "main"
)

_TOOLS_VARS = [
    "tools_gateway_enabled",
    "tools_observability_enabled",
    "tools_service_mesh_enabled",
    "tools_infrastructure_enabled",
]


def _load_role_defaults() -> dict:
    """Merge all YAML files under the tools role defaults/main/ directory."""
    defaults: dict = {}
    for path in sorted(_DEFAULTS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        defaults.update(data)
    return defaults


def _extra_vars_from_scenario(scenario_path: Path) -> dict:
    """Build extra_vars from a scenario's extra_variables.yaml, filtered to tools_* keys."""
    extra_vars_path = scenario_path.parent / "extra_variables.yaml"
    if not extra_vars_path.exists():
        return {}

    with extra_vars_path.open(encoding="utf-8") as fh:
        all_vars = yaml.safe_load(fh) or {}

    return {k: v for k, v in all_vars.items() if k in _TOOLS_VARS}


def _extra_vars_from_wizard() -> dict:
    """Interactively build extra_vars via Questionary prompts, pre-filled from role defaults."""
    defaults = _load_role_defaults()
    extra_vars = dict(defaults)

    extra_vars["tools_gateway_enabled"] = bool(
        questionary.confirm(
            "Enable gateway?",
            default=defaults.get("tools_gateway_enabled", False),
        ).ask()
    )

    extra_vars["tools_observability_enabled"] = bool(
        questionary.confirm(
            "Enable observability?",
            default=defaults.get("tools_observability_enabled", False),
        ).ask()
    )

    extra_vars["tools_service_mesh_enabled"] = bool(
        questionary.confirm(
            "Enable service mesh?",
            default=defaults.get("tools_service_mesh_enabled", False),
        ).ask()
    )

    extra_vars["tools_infrastructure_enabled"] = bool(
        questionary.confirm(
            "Enable infrastructure tooling?",
            default=defaults.get("tools_infrastructure_enabled", False),
        ).ask()
    )

    return extra_vars


@click.command(name="tools", help="Deploy the observability and tooling stack onto the cluster.")
@click.option("--scenario", "scenario_id", default=None, metavar="ID", help="Derive tools config from a scenario definition.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
def deploy_tools(scenario_id: str | None, kubeconfig: str) -> None:
    """Deploy the observability and tooling stack onto the cluster.

    When ``--scenario`` is provided the tools configuration is derived from
    the scenario's ``extra_variables.yaml``. Otherwise an interactive wizard
    collects configuration with role defaults pre-filled.

    Examples:

    \b
        itbench deploy tools --scenario 5 --kubeconfig ~/.kube/config
        itbench deploy tools --kubeconfig ~/.kube/config
    """
    run_id = str(uuid.uuid4())
    artifact_dir = Path.cwd() / ".itbench" / "runs" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    if scenario_id:
        scenario_path = _LIBRARY_ROOT / "scenarios" / str(scenario_id) / "scenario.yaml"
        if not scenario_path.exists():
            console.print(f"[red]Scenario '{scenario_id}' not found at {scenario_path}[/red]")
            raise SystemExit(1)
        extra_vars = _extra_vars_from_scenario(scenario_path)
        console.print(f"[dim]Loaded tools config from scenario {scenario_id}[/dim]")
    else:
        extra_vars = _extra_vars_from_wizard()

    extra_vars["cluster"] = {"kubeconfig": kubeconfig}

    extra_vars_file = artifact_dir / "extra_vars.json"
    extra_vars_file.write_text(json.dumps(extra_vars, indent=2), encoding="utf-8")
    console.print(f"[dim]Extra vars written to {extra_vars_file}[/dim]")

    with console.status("Deploying tools…"):
        try:
            run_playbook(
                playbook="manage_tools.yaml",
                extra_vars=extra_vars,
                tags=["install_tools"],
                run_id=run_id,
            )
        except RuntimeError as exc:
            console.print(f"[red]Deploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Tools deployed successfully.[/green]")
