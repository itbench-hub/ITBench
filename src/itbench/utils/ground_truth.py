"""Ground truth generation utility for ITBench scenarios."""

from pathlib import Path

import yaml

from itbench.models.fault import FAULT_CATALOG, FaultSolutionStep
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
            text
            .replace("{{ args.kubernetesObject.metadata.namespace }}", ns)
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

    - **alerts** — union of every ``fault.alerts`` value across all injections,
      deduplicated in first-seen order, each written as ``{name: <alert>, labels: {}}``.
    - **entities** — one entry per injection target in order.
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

    seen_alerts: set[str] = set()
    alerts_out: list[dict] = []
    for injection, _ in injections:
        fault = FAULT_CATALOG.get(injection.id)
        if fault is None:
            continue
        for alert in fault.alerts:
            alert_name = str(alert)
            if alert_name not in seen_alerts:
                seen_alerts.add(alert_name)
                alerts_out.append({"name": alert_name, "labels": {}})

    entities_out: list[dict] = []
    for injection, targets in injections:
        for obj in targets:
            entry: dict = {"apiVersion": obj.api_version, "kind": obj.kind, "name": obj.name}
            if obj.namespace is not None:
                entry["namespace"] = obj.namespace
            entities_out.append(entry)

            # Add companion entities created/targeted by specific fault injections
            ns = obj.namespace or "default"
            match injection.id:
                case "crashing-kubernetes-workload-init-container":
                    entities_out.append({"apiVersion": "v1", "kind": "ConfigMap", "name": f"{obj.name}-config", "namespace": ns})
                case "ingress-port-blocking-network-policy":
                    entities_out.append({"apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy", "name": f"{obj.name}-ingress", "namespace": ns})
                case "insufficient-kubernetes-resource-quota":
                    entities_out.append({"apiVersion": "v1", "kind": "ResourceQuota", "name": "strict-resource-quota", "namespace": ns})
                case "strict-mutual-tls-istio-service-mesh-enforcement":
                    entities_out.append({"apiVersion": "security.istio.io/v1", "kind": "PeerAuthentication", "name": "strict-mtls-mode", "namespace": ns})
                case "traffic-denying-istio-gateway-authorization-policy":
                    entities_out.append({"apiVersion": "security.istio.io/v1", "kind": "AuthorizationPolicy", "name": f"{obj.name}-deny", "namespace": ns})

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
        "alerts": alerts_out,
        "entities": entities_out,
        "solutions": solutions_out,
    }

    schema_comment = "# yaml-language-server: $schema=../../../schemas/json/library/ground_truth.json"
    out_path = scenario_dir / "ground_truth.yaml"
    with out_path.open("w", encoding="utf-8") as f:
        f.write(schema_comment + "\n")
        yaml.dump(
            doc, f,
            Dumper=_IndentedYamlDumper,
            default_flow_style=False,
            explicit_start=True,
            allow_unicode=True,
            sort_keys=False,
            indent=2,
        )

    return out_path
