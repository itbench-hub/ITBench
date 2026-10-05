"""Tests for itbench.utils.ground_truth."""

from pathlib import Path
from unittest.mock import patch

import yaml

from itbench.models.fault import (
    Fault,
    FaultAlerts,
    FaultSolution,
    FaultSolutionStep,
    FaultSolutionTemplates,
    FaultTags,
    FaultTargetReference,
)
from itbench.models.kubernetes import KubernetesWorkload
from itbench.models.scenario import (
    FaultTarget,
    Scenario,
    ScenarioApplication,
    ScenarioDomain,
    ScenarioEnvironment,
    ScenarioFault,
    ScenarioFaultInjection,
)
from itbench.utils.ground_truth import _resolve_step, generate_ground_truth


def _make_fault(
    name: str = "Test Fault",
    alerts: list[str] | None = None,
    step_text: str = "Fix {{ args.kubernetesObject.metadata.name }} in {{ args.kubernetesObject.metadata.namespace }}",
    step_command: str | None = "kubectl -n {{ args.kubernetesObject.metadata.namespace }} get {{ args.kubernetesObject.kind | lower }} {{ args.kubernetesObject.metadata.name }}",
) -> Fault:
    return Fault.model_construct(
        name=name,
        description="desc",
        expectation="exp",
        alerts=[FaultAlerts(a) for a in (alerts or ["KubePodNotReady"])],
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes="KubernetesWorkload")],
        status=None,
        resources=[],
        solution_templates=FaultSolutionTemplates(
            templates=[
                FaultSolution(steps=[FaultSolutionStep(text=step_text, command=step_command)])
            ]
        ),
    )


def _make_workload(name: str = "my-app", namespace: str = "default") -> KubernetesWorkload:
    return KubernetesWorkload(kind="Deployment", name=name, namespace=namespace)


def _make_scenario(fault_id: str, workload: KubernetesWorkload) -> Scenario:
    return Scenario.model_construct(
        environment=ScenarioEnvironment(
            applications=[ScenarioApplication.model_construct(id="opentelemetry-demo", enabled=True)],
            domains=[ScenarioDomain.SiteReliabilityEngineering],
        ),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection.model_construct(
                        id=fault_id,
                        targets=[FaultTarget(kubernetes=workload)],
                    )
                ]
            )
        ],
    )


def test_resolve_step_substitutes_name_and_namespace() -> None:
    step = FaultSolutionStep(
        text="Check {{ args.kubernetesObject.metadata.name }} in {{ args.kubernetesObject.metadata.namespace }}",
    )
    obj = _make_workload(name="frontend", namespace="prod")
    result = _resolve_step(step, obj)
    assert result["text"] == "Check frontend in prod"


def test_resolve_step_substitutes_kind_lower() -> None:
    step = FaultSolutionStep(text="get {{ args.kubernetesObject.kind | lower }}")
    obj = _make_workload()
    result = _resolve_step(step, obj)
    assert result["text"] == "get deployment"


def test_resolve_step_substitutes_api_version() -> None:
    step = FaultSolutionStep(text="apiVersion={{ args.kubernetesObject.apiVersion }}")
    obj = _make_workload()
    result = _resolve_step(step, obj)
    assert result["text"] == "apiVersion=apps/v1"


def test_resolve_step_includes_command_when_present() -> None:
    step = FaultSolutionStep(
        text="desc",
        command="kubectl get {{ args.kubernetesObject.kind | lower }}",
    )
    obj = _make_workload()
    result = _resolve_step(step, obj)
    assert result["command"] == "kubectl get deployment"


def test_resolve_step_omits_command_key_when_none() -> None:
    step = FaultSolutionStep(text="desc", command=None)
    obj = _make_workload()
    result = _resolve_step(step, obj)
    assert "command" not in result


def test_resolve_step_uses_empty_string_for_missing_namespace() -> None:
    from itbench.models.kubernetes import KubernetesNamespace

    obj = KubernetesNamespace(name="my-ns")
    step = FaultSolutionStep(text="ns={{ args.kubernetesObject.metadata.namespace }}")
    result = _resolve_step(step, obj)
    assert result["text"] == "ns="


def test_generate_ground_truth_creates_file(tmp_path: Path) -> None:
    fault = _make_fault()
    workload = _make_workload()
    scenario = _make_scenario(fault.id, workload)

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    assert out == tmp_path / "ground_truth.yaml"
    assert out.exists()
    content = out.read_text(encoding="utf-8")
    # Verify 2-space indentation on lists
    assert "entities:\n  - apiVersion:" in content


def test_generate_ground_truth_file_starts_with_schema_comment(tmp_path: Path) -> None:
    fault = _make_fault()
    scenario = _make_scenario(fault.id, _make_workload())

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    first_line = out.read_text(encoding="utf-8").splitlines()[0]
    assert first_line.startswith("# yaml-language-server:")


def test_generate_ground_truth_alerts_present(tmp_path: Path) -> None:
    fault = _make_fault(alerts=["KubePodNotReady", "KubePodCrashLooping"])
    scenario = _make_scenario(fault.id, _make_workload())

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    data = yaml.safe_load(out.read_text(encoding="utf-8"))
    alert_names = [a["name"] for a in data["alerts"]]
    assert "KubePodNotReady" in alert_names
    assert "KubePodCrashLooping" in alert_names


def test_generate_ground_truth_deduplicates_alerts(tmp_path: Path) -> None:
    fault = _make_fault(alerts=["KubePodNotReady"])
    workload = _make_workload()
    # Two injections of the same fault → alert must appear only once.
    scenario = Scenario.model_construct(
        environment=ScenarioEnvironment(applications=[]),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection.model_construct(
                        id=fault.id,
                        targets=[FaultTarget(kubernetes=workload)],
                    ),
                    ScenarioFaultInjection.model_construct(
                        id=fault.id,
                        targets=[FaultTarget(kubernetes=workload)],
                    ),
                ]
            )
        ],
    )

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert len(doc["alerts"]) == 1


def test_generate_ground_truth_entities_contain_target(tmp_path: Path) -> None:
    fault = _make_fault()
    workload = _make_workload(name="frontend", namespace="prod")
    scenario = _make_scenario(fault.id, workload)

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    entity = doc["entities"][0]
    assert entity["name"] == "frontend"
    assert entity["namespace"] == "prod"
    assert entity["kind"] == "Deployment"


def test_generate_ground_truth_companion_entities(tmp_path: Path) -> None:
    fault = _make_fault(name="Resource Quota Fault")
    workload = _make_workload(name="ad", namespace="otel-demo")
    scenario = Scenario.model_construct(
        environment=ScenarioEnvironment(applications=[]),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection.model_construct(
                        id="insufficient-kubernetes-resource-quota",
                        targets=[FaultTarget(kubernetes=workload)],
                    )
                ]
            )
        ],
    )

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {"insufficient-kubernetes-resource-quota": fault}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert len(doc["entities"]) == 2
    assert doc["entities"][0] == {"apiVersion": "apps/v1", "kind": "Deployment", "name": "ad", "namespace": "otel-demo"}
    assert doc["entities"][1] == {"apiVersion": "v1", "kind": "ResourceQuota", "name": "strict-resource-quota", "namespace": "otel-demo"}


def test_generate_ground_truth_horizontal_pod_autoscaler_companion_entity(tmp_path: Path) -> None:
    from itbench.models.kubernetes import KubernetesHorizontalPodAutoscaler

    fault = _make_fault(name="HPA Fault")
    hpa = KubernetesHorizontalPodAutoscaler(name="frontend", namespace="otel-demo")
    scenario = Scenario.model_construct(
        environment=ScenarioEnvironment(applications=[]),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection.model_construct(
                        id="misconfigured-kubernetes-horizontal-pod-autoscaler",
                        targets=[FaultTarget(kubernetes=hpa)],
                    )
                ]
            )
        ],
    )

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {"misconfigured-kubernetes-horizontal-pod-autoscaler": fault}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["entities"] == [
        {"apiVersion": "autoscaling/v2", "kind": "HorizontalPodAutoscaler", "name": "frontend", "namespace": "otel-demo"},
        {"apiVersion": "apps/v1", "kind": "Deployment", "name": "frontend", "namespace": "otel-demo"},
    ]


def test_generate_ground_truth_entities_omit_namespace_when_none(tmp_path: Path) -> None:
    from itbench.models.kubernetes import KubernetesNamespace

    fault = _make_fault()
    ns_obj = KubernetesNamespace(name="my-ns")
    scenario = Scenario.model_construct(
        environment=ScenarioEnvironment(applications=[]),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection.model_construct(
                        id=fault.id,
                        targets=[FaultTarget(kubernetes=ns_obj)],
                    )
                ]
            )
        ],
    )

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert "namespace" not in doc["entities"][0]


def test_generate_ground_truth_solutions_resolve_placeholders(tmp_path: Path) -> None:
    fault = _make_fault(
        step_text="Edit {{ args.kubernetesObject.metadata.name }}",
        step_command="kubectl -n {{ args.kubernetesObject.metadata.namespace }} get {{ args.kubernetesObject.kind | lower }} {{ args.kubernetesObject.metadata.name }}",
    )
    workload = _make_workload(name="svc", namespace="ns")
    scenario = _make_scenario(fault.id, workload)

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {fault.id: fault}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    step = doc["solutions"][0][0]["steps"][0]
    assert step["text"] == "Edit svc"
    assert step["command"] == "kubectl -n ns get deployment svc"


def test_generate_ground_truth_unknown_fault_id_skipped(tmp_path: Path) -> None:
    scenario = Scenario.model_construct(
        environment=ScenarioEnvironment(applications=[]),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection.model_construct(id="nonexistent-fault", targets=[])
                ]
            )
        ],
    )

    with patch("itbench.utils.ground_truth.FAULT_CATALOG", {}):
        out = generate_ground_truth(scenario, tmp_path)

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert doc["alerts"] == []
    assert doc["entities"] == []
    assert doc["solutions"] == []
