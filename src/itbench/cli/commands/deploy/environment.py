"""Deploy environment command for ITBench."""

import sys

from pathlib import Path
from typing import Any

import click
import questionary
import yaml

from itbench.cli.playbook import run_step
from itbench.cli.render import console, exit_not_found, fail, kubeconfig_option, verbose_option
from itbench.models.application import APPLICATION_CATALOG
from itbench.paths import repository
from itbench.utils.runner import create_run
from itbench.utils.scenarios import known_scenario_ids

_TOOL_CHOICES = (
    ("Gateway", "tools_gateway_enabled"),
    ("Observability", "tools_observability_enabled"),
    ("Service Mesh", "tools_service_mesh_enabled"),
    ("Infrastructure", "tools_infrastructure_enabled"),
)
_TOOLS_VARS = [var for _, var in _TOOL_CHOICES]


def _application_choices() -> list[tuple[str, str]]:
    """Return (name, ansible_var_slug) for all applications registered in the catalog."""
    return [
        (app.name, app.id.replace("-", "_"))
        for app in sorted(APPLICATION_CATALOG.values(), key=lambda a: a.name)
    ]

# Which subsystems each ``--only`` value deploys, in order. Applications and recorders both need the tools.
_STEPS: dict[str | None, tuple[str, ...]] = {
    None: ("tools", "applications", "recorders"),
    "tools": ("tools",),
    "applications": ("tools", "applications"),
    "recorders": ("tools", "recorders"),
}


def _load_tools_defaults() -> dict[str, Any]:
    """Merge all YAML files under the tools role defaults/main/ directory."""
    defaults: dict[str, Any] = {}
    for path in sorted(repository.tools_defaults.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        defaults.update(data)
    return defaults


def _load_applications_defaults() -> dict[str, Any]:
    """Merge all YAML files under the applications role defaults/main/ directory."""
    defaults: dict[str, Any] = {}
    for path in sorted(repository.applications_defaults.glob("*.yaml")):
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

    choices = [questionary.Choice(title, value=var, checked=defaults.get(var, False)) for title, var in _TOOL_CHOICES]
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

    app_choices = _application_choices()
    choices = [
        questionary.Choice(title, value=slug, checked=defaults.get(f"applications_{slug}_enabled", False))
        for title, slug in app_choices
    ]
    selected = questionary.checkbox("Select applications to deploy:", choices=choices).ask()
    if selected is None:
        raise click.Abort()

    extra_vars = dict(defaults)
    for _, slug in app_choices:
        extra_vars[f"applications_{slug}_enabled"] = slug in selected

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
        extra_vars["applications_opentelemetry_demo_kubernetes_autoscaling_enabled"] = bool(
            otel_answers.get("autoscaling")
        )
        extra_vars["applications_opentelemetry_demo_load_generator_browser_enabled"] = bool(otel_answers.get("browser"))
        extra_vars["applications_opentelemetry_demo_load_generator_users"] = int(otel_answers.get("users", 50))
        extra_vars["applications_opentelemetry_demo_load_generator_spawn_rate"] = int(otel_answers.get("spawn_rate", 5))

    return extra_vars


@click.command(name="environment", help="Deploy the benchmark environment stack onto the cluster.")
@click.option(
    "--scenario",
    "scenario_id",
    type=click.INT,
    default=None,
    metavar="ID",
    help="Derive configuration from a scenario definition.",
)
@kubeconfig_option
@click.option(
    "--only",
    type=click.Choice(["tools", "applications", "recorders"]),
    default=None,
    help="Limit deployment to a specific subsystem.",
)
@verbose_option
def deploy_environment(scenario_id: int | None, kubeconfig: str, only: str | None, verbose: bool) -> None:
    """Deploy the benchmark environment stack (tools, applications, recorders) onto the cluster.

    Examples:

    \b
        itbench deploy environment --kubeconfig ~/.kube/config
        itbench deploy environment --scenario 5 --kubeconfig ~/.kube/config
        itbench deploy environment --only tools --kubeconfig ~/.kube/config
        itbench deploy environment --only applications --kubeconfig ~/.kube/config
        itbench deploy environment -v --kubeconfig ~/.kube/config
    """
    steps = _STEPS[only]

    tools_vars: dict[str, Any] = {}
    applications_vars: dict[str, Any] = {}

    if scenario_id is not None:
        known = known_scenario_ids(repository.scenarios)
        if str(scenario_id) not in known:
            exit_not_found("Scenario", str(scenario_id), known, "itbench list scenarios")
        scenario_path = repository.scenarios / str(scenario_id) / "scenario.yaml"
        if not scenario_path.is_file():
            fail(f"[red]Scenario {scenario_id} has no scenario.yaml at {scenario_path}[/red]")
        scenario_vars = _extra_variables_from_scenario(scenario_path)
        console.print(f"[dim]Loaded configuration from scenario {scenario_id}[/dim]")

        tools_vars = {k: v for k, v in scenario_vars.items() if k in _TOOLS_VARS}
        if "applications" in steps:
            applications_vars = {k: v for k, v in scenario_vars.items() if k.startswith("applications_")}
    else:
        tools_vars = _tools_extra_vars_from_wizard()
        if "applications" in steps:
            applications_vars = _applications_extra_vars_from_wizard()

    environment_vars = {
        **tools_vars,
        **applications_vars,
        "environment_tool_management_enabled": True,
        "environment_application_management_enabled": "applications" in steps,
        "environment_recorder_management_enabled": "recorders" in steps,
    }

    run_id, extra_vars_file = create_run(environment_vars)
    console.print(f"[dim]Extra variables written to {extra_vars_file}[/dim]", soft_wrap=True)

    run_step(
        playbook="manage_environment.yaml",
        extra_vars=environment_vars,
        tags=["install"],
        status="Deploying environment…",
        failure="Environment deploy",
        verbose=verbose,
        run_id=run_id,
        kubeconfig=kubeconfig,
    )

    console.print("[bold green]Environment deployed successfully.[/bold green]")
