"""Deploy environment command for ITBench."""

import json
import sys
import uuid

from pathlib import Path
from typing import Any

import click
import questionary
import yaml

from rich.console import Console

from itbench.paths import library
from itbench.utils.runner import run_playbook

console = Console()

_TOOLS_DEFAULTS_DIR = (
    Path(__file__).parents[5]
    / "scenarios" / "sre" / "project"
    / "roles" / "tools" / "defaults" / "main"
)

_APPLICATIONS_DEFAULTS_DIR = (
    Path(__file__).parents[5]
    / "scenarios" / "sre" / "project"
    / "roles" / "applications" / "defaults" / "main"
)

_TOOLS_VARS = [
    "tools_gateway_enabled",
    "tools_observability_enabled",
    "tools_service_mesh_enabled",
    "tools_infrastructure_enabled",
]


def _load_tools_defaults() -> dict[str, Any]:
    """Merge all YAML files under the tools role defaults/main/ directory."""
    defaults: dict[str, Any] = {}
    for path in sorted(_TOOLS_DEFAULTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        defaults.update(data)
    return defaults


def _load_applications_defaults() -> dict[str, Any]:
    """Merge all YAML files under the applications role defaults/main/ directory."""
    defaults: dict[str, Any] = {}
    for path in sorted(_APPLICATIONS_DEFAULTS_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        defaults.update(data)
    return defaults


def _extra_variables_from_scenario(scenario_path: Path) -> dict[str, Any]:
    """Read extra_variables.yaml from a scenario directory."""
    extra_vars_path = scenario_path.parent / "extra_variables.yaml"
    if not extra_vars_path.exists():
        return {}
    return yaml.safe_load(extra_vars_path.read_text(encoding="utf-8")) or {}


def _tools_extra_vars_from_wizard() -> dict[str, Any]:
    """Interactively build tools extra_vars via a checkbox prompt."""
    defaults = _load_tools_defaults()
    if not sys.stdin.isatty():
        return dict(defaults)

    choices = [
        questionary.Choice("Gateway", value="tools_gateway_enabled", checked=defaults.get("tools_gateway_enabled", False)),
        questionary.Choice("Observability", value="tools_observability_enabled", checked=defaults.get("tools_observability_enabled", False)),
        questionary.Choice("Service Mesh", value="tools_service_mesh_enabled", checked=defaults.get("tools_service_mesh_enabled", False)),
        questionary.Choice("Infrastructure", value="tools_infrastructure_enabled", checked=defaults.get("tools_infrastructure_enabled", False)),
    ]
    selected = questionary.checkbox("Select tools to deploy:", choices=choices).ask()
    if selected is None:
        raise click.Abort()

    extra_vars = dict(defaults)
    for var in _TOOLS_VARS:
        extra_vars[var] = var in selected
    return extra_vars


def _applications_extra_vars_from_wizard() -> dict[str, Any]:
    """Interactively build applications extra_vars via a selection checkbox followed by per-application forms."""
    defaults = _load_applications_defaults()
    if not sys.stdin.isatty():
        return dict(defaults)

    choices = [
        questionary.Choice("Book Info", value="book_info", checked=defaults.get("applications_book_info_enabled", False)),
        questionary.Choice("OpenTelemetry Demo", value="opentelemetry_demo", checked=defaults.get("applications_opentelemetry_demo_enabled", False)),
    ]
    selected = questionary.checkbox("Select applications to deploy:", choices=choices).ask()
    if selected is None:
        raise click.Abort()

    extra_vars = dict(defaults)
    extra_vars["applications_book_info_enabled"] = "book_info" in selected
    extra_vars["applications_opentelemetry_demo_enabled"] = "opentelemetry_demo" in selected

    if "book_info" in selected:
        console.print("\n[dim]Configure Book Info:[/dim]")
        book_form = questionary.form(
            autoscaling=questionary.confirm(
                "  Enable Kubernetes autoscaling for Book Info?",
                default=defaults.get("applications_book_info_kubernetes_autoscaling_enabled", False),
            ),
        )
        book_answers = book_form.ask()
        if book_answers is None:
            raise click.Abort()
        extra_vars["applications_book_info_kubernetes_autoscaling_enabled"] = bool(book_answers.get("autoscaling"))

    if "opentelemetry_demo" in selected:
        console.print("\n[dim]Configure OpenTelemetry Demo:[/dim]")
        otel_form = questionary.form(
            autoscaling=questionary.confirm(
                "  Enable Kubernetes autoscaling for OpenTelemetry Demo?",
                default=defaults.get("applications_opentelemetry_demo_kubernetes_autoscaling_enabled", False),
            ),
            browser=questionary.confirm(
                "  Enable browser traffic in load generator?",
                default=defaults.get("applications_opentelemetry_demo_load_generator_browser_enabled", False),
            ),
            users=questionary.text(
                "  Load generator users:",
                default=str(defaults.get("applications_opentelemetry_demo_load_generator_users", 50)),
            ),
            spawn_rate=questionary.text(
                "  Load generator spawn rate:",
                default=str(defaults.get("applications_opentelemetry_demo_load_generator_spawn_rate", 5)),
            ),
        )
        otel_answers = otel_form.ask()
        if otel_answers is None:
            raise click.Abort()
        extra_vars["applications_opentelemetry_demo_kubernetes_autoscaling_enabled"] = bool(otel_answers.get("autoscaling"))
        extra_vars["applications_opentelemetry_demo_load_generator_browser_enabled"] = bool(otel_answers.get("browser"))
        extra_vars["applications_opentelemetry_demo_load_generator_users"] = int(otel_answers.get("users", 50))
        extra_vars["applications_opentelemetry_demo_load_generator_spawn_rate"] = int(otel_answers.get("spawn_rate", 5))

    return extra_vars


@click.command(name="environment", help="Deploy the benchmark environment stack onto the cluster.")
@click.option("--scenario", "scenario_id", default=None, metavar="ID", help="Derive configuration from a scenario definition.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
@click.option("--only", type=click.Choice(["tools", "applications", "recorders"]), default=None, help="Limit deployment to a specific subsystem.")
def deploy_environment(scenario_id: str | None, kubeconfig: str, only: str | None) -> None:
    """Deploy the benchmark environment stack (tools, applications, recorders) onto the cluster.

    Examples:

    \b
        itbench deploy environment --kubeconfig ~/.kube/config
        itbench deploy environment --scenario 5 --kubeconfig ~/.kube/config
        itbench deploy environment --only tools --kubeconfig ~/.kube/config
        itbench deploy environment --only applications --kubeconfig ~/.kube/config
    """
    if only == "tools":
        steps = ["tools"]
    elif only == "applications":
        steps = ["tools", "applications"]
    elif only == "recorders":
        steps = ["tools", "recorders"]
    else:
        steps = ["tools", "applications", "recorders"]

    tools_vars: dict[str, Any] = {}
    applications_vars: dict[str, Any] = {}
    recorders_vars: dict[str, Any] = {}

    if scenario_id:
        scenario_path = library.scenarios / str(scenario_id) / "scenario.yaml"
        if not scenario_path.exists():
            console.print(f"[red]Scenario '{scenario_id}' not found at {scenario_path}[/red]")
            raise SystemExit(1)
        scenario_vars = _extra_variables_from_scenario(scenario_path)
        console.print(f"[dim]Loaded configuration from scenario {scenario_id}[/dim]")

        tools_vars = {k: v for k, v in scenario_vars.items() if k in _TOOLS_VARS}
        if "applications" in steps:
            applications_vars = {k: v for k, v in scenario_vars.items() if k.startswith("applications_")}
        if "recorders" in steps:
            recorders_vars = {**tools_vars, "tools_recorders_enabled": True, "scenario_id": scenario_id}
    else:
        tools_vars = _tools_extra_vars_from_wizard()
        if "applications" in steps:
            applications_vars = _applications_extra_vars_from_wizard()
        if "recorders" in steps:
            recorders_vars = {**tools_vars, "tools_recorders_enabled": True}

    run_id = str(uuid.uuid4())
    artifact_dir = Path.cwd() / ".itbench" / "runs" / run_id
    artifact_dir.mkdir(parents=True, exist_ok=True)

    cluster_config = {"cluster": {"kubeconfig": kubeconfig}}
    environment_vars = {
        **tools_vars,
        **applications_vars,
        **cluster_config,
        "environment_tool_management_enabled": True,
        "environment_application_management_enabled": "applications" in steps,
    }
    recorders_vars.update(cluster_config)

    combined_extra_vars = {**environment_vars, **recorders_vars}
    extra_vars_file = artifact_dir / "extra_vars.json"
    extra_vars_file.write_text(json.dumps(combined_extra_vars, indent=2), encoding="utf-8")
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]")

    with console.status("Deploying environment…"):
        try:
            run_playbook(
                playbook="manage_environment.yaml",
                extra_vars=environment_vars,
                tags=["install"],
                run_id=run_id,
            )
        except RuntimeError as exc:
            console.print(f"[red]Environment deploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

        if "recorders" in steps:
            try:
                run_playbook(
                    playbook="manage_environment.yaml",
                    extra_vars={
                        **recorders_vars,
                        "environment_tool_management_enabled": True,
                        "environment_application_management_enabled": False,
                    },
                    tags=["install"],
                    run_id=run_id,
                )
            except RuntimeError as exc:
                console.print(f"[red]Environment deploy failed:[/red] {exc}")
                raise SystemExit(1) from exc

    console.print("[bold green]Environment deployed successfully.[/bold green]")
