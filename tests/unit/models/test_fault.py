"""Tests for Fault model, lifecycle statuses, and fault catalog."""

from collections.abc import Mapping

import pytest

from pydantic import ValidationError

from itbench.models.fault import (
    FAULT_CATALOG,
    Fault,
    FaultConvertedStatus,
    FaultRetiredStatus,
    FaultSignals,
    FaultSolution,
    FaultSolutionStep,
    FaultSolutionTemplates,
    FaultStatus,
    FaultTags,
    FaultTargetReference,
    PrometheusAlertNames,
    PrometheusAlertSignal,
    PrometheusSignals,
)
from itbench.models.kubernetes import KubernetesObjectKind
from itbench.models.platform import Platform


def _crash_looping_signals() -> FaultSignals:
    return FaultSignals(
        prometheus=PrometheusSignals(alerts=[PrometheusAlertSignal(name=PrometheusAlertNames.KubePodCrashLooping)])
    )


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


def test_active_fault_requires_tags_targets() -> None:
    solution = _sample_solution_templates()

    # Missing tags
    with pytest.raises(ValidationError, match="Non-retired faults must define at least one tag"):
        Fault(
            name="Test Fault",
            description="Test fault description",
            expectation="Expected pod crash",
            platform=Platform.Kubernetes,
            solution_templates=solution,
            signals=_crash_looping_signals(),
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
            signals=_crash_looping_signals(),
            tags=[FaultTags.Deployment],
            targets=[],
        )


def test_active_fault_without_signals_is_valid() -> None:
    fault = Fault(
        name="Signal Free Fault",
        description="d",
        expectation="e",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
    )
    assert fault.alert_names == []
    assert fault.signals.kubernetes.policy_reports == []


def test_alert_signal_state_defaults_to_firing() -> None:
    signal = PrometheusAlertSignal(name=PrometheusAlertNames.KubePodCrashLooping)
    assert signal.state == "firing"


def test_policy_report_signal() -> None:
    signals = FaultSignals.model_validate(
        {"kubernetes": {"policy_reports": [{"policy": "require-limits", "status": "pass"}]}}
    )
    assert signals.kubernetes.policy_reports[0].policy == "require-limits"
    assert signals.kubernetes.policy_reports[0].status == "pass"


def test_policy_report_signal_has_no_resource_field() -> None:
    with pytest.raises(ValidationError):
        FaultSignals.model_validate(
            {"kubernetes": {"policy_reports": [{"policy": "p", "status": "pass", "resource": "x"}]}}
        )


def test_policy_report_signal_absent() -> None:
    signals = FaultSignals.model_validate(
        {"kubernetes": {"policy_reports": [{"policy": "require-limits", "absent": True}]}}
    )
    assert signals.kubernetes.policy_reports[0].absent is True
    assert signals.kubernetes.policy_reports[0].status is None


def test_policy_report_signal_absent_defaults_to_false() -> None:
    signals = FaultSignals.model_validate(
        {"kubernetes": {"policy_reports": [{"policy": "require-limits", "status": "fail"}]}}
    )
    assert signals.kubernetes.policy_reports[0].absent is False


def test_policy_report_signal_absent_forbids_status() -> None:
    with pytest.raises(ValidationError, match="must not be set when 'absent' is true"):
        FaultSignals.model_validate(
            {"kubernetes": {"policy_reports": [{"policy": "p", "absent": True, "status": "fail"}]}}
        )


def test_policy_report_signal_requires_status_unless_absent() -> None:
    with pytest.raises(ValidationError, match="required unless 'absent' is true"):
        FaultSignals.model_validate({"kubernetes": {"policy_reports": [{"policy": "p"}]}})


def test_active_fault_valid() -> None:
    fault = Fault(
        name="Crashing Init Container",
        description="Workload fails due to init container exit 1",
        expectation="Pod stays in CrashLoopBackOff",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        signals=_crash_looping_signals(),
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
    )
    assert fault.id == "crashing-init-container"
    assert fault.status is None
    assert fault.resources == []


def test_retired_fault_can_omit_signals_tags_targets() -> None:
    retired_status = FaultStatus(retired=FaultRetiredStatus(version="1.4.0", reason="Replaced by new fault"))
    fault = Fault(
        name="Old Retired Fault",
        description="Deprecated fault",
        expectation="None",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        status=retired_status,
    )
    assert fault.id == "old-retired-fault"
    assert fault.alert_names == []
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
        signals=_crash_looping_signals(),
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
        status=converted_status,
    )
    assert fault.status is not None
    assert fault.status.converted is not None
    assert fault.status.converted.id == "restart-kubernetes-workload"


def test_fault_without_status_is_active() -> None:
    fault = Fault(
        name="Plain Fault",
        description="d",
        expectation="e",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        signals=_crash_looping_signals(),
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
    )

    assert not fault.is_retired
    assert not fault.is_converted
    assert not fault.is_inactive
    assert fault.retired_reason is None


def test_retired_fault_status_properties() -> None:
    fault = Fault(
        name="Old Retired Fault",
        description="d",
        expectation="e",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        status=FaultStatus(retired=FaultRetiredStatus(version="1.4.0", reason="Replaced by new fault")),
    )

    assert fault.is_retired
    assert not fault.is_converted
    assert fault.is_inactive
    assert fault.retired_reason == "Replaced by new fault"


def test_retired_fault_without_reason_has_no_retired_reason() -> None:
    fault = Fault(
        name="Old Retired Fault",
        description="d",
        expectation="e",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        status=FaultStatus(retired=FaultRetiredStatus(version="1.4.0")),
    )

    assert fault.is_retired
    assert fault.retired_reason is None


def test_converted_fault_status_properties() -> None:
    fault = Fault(
        name="Converted Fault",
        description="d",
        expectation="e",
        platform=Platform.Kubernetes,
        solution_templates=_sample_solution_templates(),
        signals=_crash_looping_signals(),
        tags=[FaultTags.Deployment],
        targets=[FaultTargetReference(kubernetes=KubernetesObjectKind.KubernetesWorkload)],
        status=FaultStatus(converted=FaultConvertedStatus(id="restart-kubernetes-workload", version="1.3.0")),
    )

    assert not fault.is_retired
    assert fault.is_converted
    assert fault.is_inactive
    assert fault.retired_reason is None


def test_status_properties_are_not_serialised() -> None:
    fault = next(iter(FAULT_CATALOG.values()))

    dumped = fault.model_dump(mode="json")

    assert not {"is_retired", "is_converted", "is_inactive", "retired_reason"} & dumped.keys()


def test_fault_catalog_loaded() -> None:
    assert isinstance(FAULT_CATALOG, Mapping)
    for fault_id, fault in FAULT_CATALOG.items():
        assert fault.id == fault_id
        assert isinstance(fault, Fault)
        assert len(fault.solution_templates.templates) > 0
