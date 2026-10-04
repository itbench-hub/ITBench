"""Deploy applications command for ITBench."""

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
    / "roles" / "applications" / "defaults" / "main"
)

_SCENARIO_APP_MAP: dict[str, str] = {
    "book-info": "applications_book_info_enabled",
    "opentelemetry-demo": "applications_opentelemetry_demo_enabled",
}


def _load_role_defaults() -> dict:
    """Merge all YAML files under the applications role defaults/main/ directory."""
    defaults: dict = {}
    for path in sorted(_DEFAULTS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        defaults.update(data)
    return defaults


def _extra_vars_from_scenario(scenario_path: Path) -> dict:
    """Build extra_vars from a scenario definition, or from extra_vars.yaml if present."""
    extra_vars_path = scenario_path.parent / "extra_vars.yaml"
    if extra_vars_path.exists():
        with extra_vars_path.open(encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}

    with scenario_path.open(encoding="utf-8") as fh:
        scenario = yaml.safe_load(fh)

    extra_vars: dict = {}
    for app in (scenario.get("environment") or {}).get("applications", []):
        flag = _SCENARIO_APP_MAP.get(app.get("id", ""))
        if flag and app.get("enabled", True):
            extra_vars[flag] = True

    return extra_vars


def _extra_vars_from_wizard() -> dict:
    """Interactively build extra_vars via Questionary prompts, pre-filled from role defaults."""
    defaults = _load_role_defaults()
    extra_vars = dict(defaults)

    book_info = questionary.confirm(
        "Enable Book Info?",
        default=defaults.get("applications_book_info_enabled", False),
    ).ask()
    extra_vars["applications_book_info_enabled"] = bool(book_info)
    if book_info:
        extra_vars["applications_book_info_kubernetes_autoscaling_enabled"] = bool(
            questionary.confirm(
                "  Enable Kubernetes autoscaling for Book Info?",
                default=defaults.get("applications_book_info_kubernetes_autoscaling_enabled", False),
            ).ask()
        )

    otel = questionary.confirm(
        "Enable OpenTelemetry Demo?",
        default=defaults.get("applications_opentelemetry_demo_enabled", False),
    ).ask()
    extra_vars["applications_opentelemetry_demo_enabled"] = bool(otel)
    if otel:
        extra_vars["applications_opentelemetry_demo_kubernetes_autoscaling_enabled"] = bool(
            questionary.confirm(
                "  Enable Kubernetes autoscaling for OTel Demo?",
                default=defaults.get("applications_opentelemetry_demo_kubernetes_autoscaling_enabled", False),
            ).ask()
        )
        extra_vars["applications_opentelemetry_demo_load_generator_browser_enabled"] = bool(
            questionary.confirm(
                "  Enable browser traffic in load generator?",
                default=defaults.get("applications_opentelemetry_demo_load_generator_browser_enabled", False),
            ).ask()
        )
        extra_vars["applications_opentelemetry_demo_load_generator_users"] = int(
            questionary.text(
                "  Load generator users:",
                default=str(defaults.get("applications_opentelemetry_demo_load_generator_users", 50)),
            ).ask()
        )
        extra_vars["applications_opentelemetry_demo_load_generator_spawn_rate"] = int(
            questionary.text(
                "  Load generator spawn rate:",
                default=str(defaults.get("applications_opentelemetry_demo_load_generator_spawn_rate", 5)),
            ).ask()
        )

    return extra_vars


@click.command(name="applications", help="Deploy sample applications onto the cluster.")
@click.option("--scenario", "scenario_id", default=None, metavar="ID", help="Derive application config from a scenario definition.")
@click.option("--kubeconfig", required=True, envvar="KUBECONFIG", metavar="PATH", help="Path to kubeconfig file.")
def deploy_applications(scenario_id: str | None, kubeconfig: str) -> None:
    """Deploy sample applications onto the cluster.

    When ``--scenario`` is provided the application set is derived from the
    scenario definition. Otherwise an interactive wizard collects configuration
    with role defaults pre-filled.

    Examples:

    \b
        itbench deploy applications --scenario 5 --kubeconfig ~/.kube/config
        itbench deploy applications --kubeconfig ~/.kube/config
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
        console.print(f"[dim]Loaded application config from scenario {scenario_id}[/dim]")
    else:
        extra_vars = _extra_vars_from_wizard()

    extra_vars["cluster"] = {"kubeconfig": kubeconfig}

    extra_vars_file = artifact_dir / "extra_vars.json"
    extra_vars_file.write_text(json.dumps(extra_vars, indent=2), encoding="utf-8")
    console.print(f"[dim]Extra vars written to {extra_vars_file}[/dim]")

    with console.status("Deploying applications…"):
        try:
            run_playbook(
                playbook="manage_applications.yaml",
                extra_vars=extra_vars,
                tags=["install_applications"],
                run_id=run_id,
            )
        except RuntimeError as exc:
            console.print(f"[red]Deploy failed:[/red] {exc}")
            raise SystemExit(1) from exc

    console.print("[green]Applications deployed successfully.[/green]")
