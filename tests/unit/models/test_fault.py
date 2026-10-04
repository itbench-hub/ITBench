"""Tests for Fault model, lifecycle statuses, and fault catalog."""

import pytest

from pydantic import ValidationError

from itbench.models.fault import (
    FAULT_CATALOG,
    Fault,
    FaultAlerts,
    FaultConvertedStatus,
    FaultRetiredStatus,
    FaultSolution,
    FaultSolutionStep,
    FaultSolutionTemplates,
    FaultStatus,
    FaultTags,
    FaultTargetReference,
)
from itbench.models.kubernetes import KubernetesObjectKind
from itbench.models.platform import Platform


def _sample_solution_templates() -> FaultSolutionTemplates:
    return FaultSolutionTemplates(
        templates=[
            FaultSolution(
                steps=[
                    FaultSolutionStep(
                        text="Inspect pods in error state",
                        command="kubectl get pods -n default",
                    )
                ]
            )
        ]
    )


def test_active_fault_requires_alerts_tags_targets() -> None:
    solution = _sample_solution_templates()

    # Missing alerts
    with pytest.raises(ValidationError, match="Non-retired faults must define at least one alert"):
        Fault(
            name="Test Fault",
            description="Test fault description",
            expectation="Expected pod crash",
            platform=Platform.Kubernetes,
            solution_templates=solution,
            alerts=[],
            tags=[FaultTags.Deployment],
            targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
        )

    # Missing tags
    with pytest.raises(ValidationError, match="Non-retired faults must define at least one tag"):
        Fault(
            name="Test Fault",
            description="Test fault description",
            expectation="Expected pod crash",
            platform=Platform.Kubernetes,
            solution_templates=solution,
            alerts=[FaultAlerts.KubePodCrashLooping],
            tags=[],
            targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
        )

    # Missing targets
    with pytest.raises(ValidationError, match="Non-retired faults must define at least one target"):
        Fault(
            name="Test Fault",
            description="Test fault description",
            expectation="Expected pod crash",
            platform=Platform.Kubernetes,
            solution_templates=solution,
            alerts=[FaultAlerts.KubePodCrashLooping],
            tags=[FaultTags.Deployment],
            targets=[],
        )


def test_active_fault_valid() -> None:
    fault = Fault(
        name="Crashing Init Container",
        description="Workload fails due to init container exit 1",
        expectation="Pod stays in CrashLoopBackOff",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        alerts=[FaultAlerts.KubePodCrashLooping],
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
    )
    assert fault.id == "crashing-init-container"
    assert fault.status is None
    assert fault.resources == []


def test_retired_fault_can_omit_alerts_tags_targets() -> None:
    retired_status = FaultStatus(
        retired=FaultRetiredStatus(version="1.4.0", reason="Replaced by new fault")
    )
    fault = Fault(
        name="Old Retired Fault",
        description="Deprecated fault",
        expectation="None",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        status=retired_status,
    )
    assert fault.id == "old-retired-fault"
    assert fault.alerts == []
    assert fault.tags == []
    assert fault.targets == []


def test_converted_fault_status() -> None:
    converted_status = FaultStatus(
        converted=FaultConvertedStatus(
            id="restart-kubernetes-workload",
            version="1.3.0",
        )
    )
    fault = Fault(
        name="Converted Fault",
        description="Converted fault",
        expectation="None",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        alerts=[FaultAlerts.KubePodCrashLooping],
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
        status=converted_status,
    )
    assert fault.status is not None
    assert fault.status.converted is not None
    assert fault.status.converted.id == "restart-kubernetes-workload"


def test_fault_catalog_loaded() -> None:
    assert isinstance(FAULT_CATALOG, dict)
    for fault_id, fault in FAULT_CATALOG.items():
        assert fault.id == fault_id
        assert isinstance(fault, Fault)
        assert len(fault.solution_templates.templates) > 0
