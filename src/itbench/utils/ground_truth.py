"""Ground truth generation utility for ITBench scenarios."""

from pathlib import Path

import yaml

from itbench.models.fault import FAULT_CATALOG, FaultSolutionStep, PrometheusAlertState
from itbench.models.kubernetes import KubernetesObject
from itbench.models.scenario import Scenario, ScenarioFaultInjection


class _IndentedYamlDumper(yaml.SafeDumper):
    """Custom YAML dumper that preserves 2-space indent on list items."""

    def increase_indent(self, flow: bool = False, indentless: bool = False) -> None:
        return super().increase_indent(flow=flow, indentless=False)


def _resolve_step(step: FaultSolutionStep, obj: KubernetesObject) -> dict:
    """Return a step dict with Jinja placeholders replaced by concrete target values."""
    ns = obj.namespace or ""

    def _sub(text: str) -> str:
        return (
            text.replace("{{ args.kubernetesObject.metadata.namespace }}", ns)
            .replace("{{ args.kubernetesObject.metadata.name }}", obj.name)
            .replace("{{ args.kubernetesObject.kind | lower }}", obj.kind.lower())
            .replace("{{ args.kubernetesObject.apiVersion }}", obj.api_version)
        )

    resolved: dict = {"text": _sub(step.text)}
    if step.command is not None:
        resolved["command"] = _sub(step.command)
    return resolved


def generate_ground_truth(scenario: Scenario, scenario_dir: Path) -> Path:
    """Write ``ground_truth.yaml`` next to ``scenario.yaml`` in *scenario_dir*.

    Derives all content from the scenario's fault injections and the
    :data:`FAULT_CATALOG`:

    - **signals** — union of every ``fault.signals`` entry across all injections,
      deduplicated in first-seen order. Alert states are written only when they are not ``firing``.
    - **entities** — ``faulted.kubernetes`` lists one object per injection target in order, plus
      the companion objects a fault creates or changes. ``impacted`` and ``unchanged`` are not
      generated.
    - **solutions** — one group per injection; each group is a list of alternative
      remediation paths (one per solution template), with Jinja placeholders resolved
      against the first target of that injection.

    Returns the path of the written file.
    """
    injections: list[tuple[ScenarioFaultInjection, list[KubernetesObject]]] = [
        (injection, [t.kubernetes for t in injection.targets])
        for fault_block in scenario.faults
        for injection in fault_block.injections
    ]

    seen_alerts: set[tuple[str, str]] = set()
    alerts_out: list[dict] = []
    seen_reports: set[tuple[str, str]] = set()
    reports_out: list[dict] = []
    for injection, _ in injections:
        fault = FAULT_CATALOG.get(injection.id)
        if fault is None:
            continue
        for alert in fault.signals.prometheus.alerts:
            key = (str(alert.name), str(alert.state))
            if key not in seen_alerts:
                seen_alerts.add(key)
                alert_entry = {"name": key[0]}
                if alert.state != PrometheusAlertState.Firing:
                    alert_entry["state"] = key[1]
                alerts_out.append(alert_entry)
        for report in fault.signals.kubernetes.policy_reports:
            key = (report.policy, str(report.status))
            if key not in seen_reports:
                seen_reports.add(key)
                reports_out.append({"policy": key[0], "status": key[1]})

    signals_out: dict = {}
    if reports_out:
        signals_out["kubernetes"] = {"policy_reports": reports_out}
    if alerts_out:
        signals_out["prometheus"] = {"alerts": alerts_out}

    faulted_out: list[dict] = []
    for injection, targets in injections:
        for obj in targets:
            entry: dict = {"apiVersion": obj.api_version, "kind": obj.kind, "name": obj.name}
            if obj.namespace is not None:
                entry["namespace"] = obj.namespace
            faulted_out.append(entry)

            # Add companion objects created/targeted by specific fault injections
            ns = obj.namespace or "default"
            match injection.id:
                case "crashing-kubernetes-workload-init-container":
                    faulted_out.append(
                        {"apiVersion": "v1", "kind": "ConfigMap", "name": f"{obj.name}-config", "namespace": ns}
                    )
                case "ingress-port-blocking-network-policy":
                    faulted_out.append(
                        {
                            "apiVersion": "networking.k8s.io/v1",
                            "kind": "NetworkPolicy",
                            "name": f"{obj.name}-ingress",
                            "namespace": ns,
                        }
                    )
                case "insufficient-kubernetes-resource-quota":
                    faulted_out.append(
                        {"apiVersion": "v1", "kind": "ResourceQuota", "name": "strict-resource-quota", "namespace": ns}
                    )
                case "strict-mutual-tls-istio-service-mesh-enforcement":
                    faulted_out.append(
                        {
                            "apiVersion": "security.istio.io/v1",
                            "kind": "PeerAuthentication",
                            "name": "application",
                            "namespace": ns,
                        }
                    )
                case "traffic-denying-istio-gateway-authorization-policy":
                    faulted_out.append(
                        {
                            "apiVersion": "security.istio.io/v1",
                            "kind": "AuthorizationPolicy",
                            "name": f"{obj.name}-policy",
                            "namespace": ns,
                        }
                    )

    solutions_out: list[list[dict]] = []
    for injection, targets in injections:
        fault = FAULT_CATALOG.get(injection.id)
        if fault is None or not targets:
            continue
        group = [
            {"steps": [_resolve_step(step, targets[0]) for step in template.steps]}
            for template in fault.solution_templates.templates
        ]
        if group:
            solutions_out.append(group)

    doc: dict = {
        "signals": signals_out,
        "entities": {"faulted": {"kubernetes": faulted_out}},
        "solutions": solutions_out,
    }

    schema_comment = "# yaml-language-server: $schema=../../../schemas/json/library/ground_truth.json"
    out_path = scenario_dir / "ground_truth.yaml"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(schema_comment + "\n")
        yaml.dump(
            doc,
            f,
            Dumper=_IndentedYamlDumper,
            default_flow_style=False,
            explicit_start=True,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )

    return out_path
