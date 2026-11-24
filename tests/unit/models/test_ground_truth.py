"""Tests for GroundTruth model and components."""

import pytest

from pydantic import ValidationError

from itbench.models.fault import (
    FaultSignals,
    FaultSolution,
    FaultSolutionStep,
    PrometheusAlertNames,
    PrometheusAlertSignal,
    PrometheusSignals,
)
from itbench.models.ground_truth import (
    GroundTruth,
    GroundTruthEntities,
    GroundTruthEntityGroup,
    GroundTruthField,
    GroundTruthUnchangedEntityGroup,
    GroundTruthUnchangedKubernetesObject,
)
from itbench.models.kubernetes import KubernetesWorkload


def test_ground_truth_valid() -> None:
    gt = GroundTruth(
        signals=FaultSignals(
            prometheus=PrometheusSignals(alerts=[PrometheusAlertSignal(name=PrometheusAlertNames.KubePodCrashLooping)])
        ),
        entities=GroundTruthEntities(
            faulted=GroundTruthEntityGroup(
                kubernetes=[
                    KubernetesWorkload(
                        kind="Deployment",
                        name="frontend",
                        namespace="default",
                    )
                ]
            )
        ),
        solutions=[
            [
                FaultSolution(
                    steps=[
                        FaultSolutionStep(
                            text="Rollback deployment",
                            command="kubectl rollout undo deployment frontend -n default",
                        )
                    ]
                )
            ]
        ],
    )
    assert len(gt.signals.prometheus.alerts) == 1
    assert gt.signals.prometheus.alerts[0].name == PrometheusAlertNames.KubePodCrashLooping
    assert len(gt.entities.faulted.kubernetes) == 1
    assert gt.entities.impacted.kubernetes == []
    assert gt.entities.unchanged.kubernetes == []
    assert len(gt.solutions) == 1


def test_ground_truth_signals_from_dict() -> None:
    gt = GroundTruth.model_validate(
        {
            "signals": {
                "prometheus": {"alerts": [{"name": "KubePodNotReady", "state": "pending"}]},
                "kubernetes": {"policy_reports": [{"policy": "require-limits", "status": "fail"}]},
            },
            "entities": {"faulted": {"kubernetes": []}},
            "solutions": [],
        }
    )
    assert gt.signals.prometheus.alerts[0].state == "pending"
    assert gt.signals.kubernetes.policy_reports[0].status == "fail"


def test_ground_truth_legacy_alerts_key_rejected() -> None:
    with pytest.raises(ValidationError):
        GroundTruth.model_validate(
            {"alerts": [{"name": "KubePodNotReady"}], "entities": {"faulted": {"kubernetes": []}}, "solutions": []}
        )


def test_ground_truth_entities_from_dict() -> None:
    gt = GroundTruth.model_validate(
        {
            "entities": {
                "faulted": {
                    "kubernetes": [
                        {"apiVersion": "apps/v1", "kind": "Deployment", "name": "frontend", "namespace": "default"}
                    ]
                },
                "impacted": {"kubernetes": []},
            },
            "solutions": [],
        }
    )
    assert gt.entities.faulted.kubernetes[0].api_version == "apps/v1"
    assert gt.entities.impacted.kubernetes == []


def test_ground_truth_entities_requires_faulted() -> None:
    with pytest.raises(ValidationError):
        GroundTruth.model_validate({"entities": {}, "solutions": []})


def test_ground_truth_flat_entity_list_rejected() -> None:
    with pytest.raises(ValidationError):
        GroundTruth.model_validate(
            {
                "entities": [{"apiVersion": "apps/v1", "kind": "Deployment", "name": "frontend"}],
                "solutions": [],
            }
        )


def test_ground_truth_entities_extra_group_forbidden() -> None:
    with pytest.raises(ValidationError):
        GroundTruth.model_validate(
            {
                "entities": {"faulted": {"kubernetes": []}, "primary": {"kubernetes": []}},
                "solutions": [],
            }
        )


def test_ground_truth_entity_group_unknown_type_forbidden() -> None:
    with pytest.raises(ValidationError):
        GroundTruthEntityGroup.model_validate({"host": []})


def test_ground_truth_unchanged_fields() -> None:
    group = GroundTruthUnchangedEntityGroup.model_validate(
        {
            "kubernetes": [
                {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": "frontend",
                    "namespace": "default",
                    "fields": [{"path": "spec.template.spec.containers[0].name", "value": "server"}],
                },
                {"apiVersion": "v1", "kind": "ConfigMap", "name": "settings", "namespace": "default"},
            ]
        }
    )
    with_fields, without_fields = group.kubernetes
    assert with_fields.fields == [GroundTruthField(path="spec.template.spec.containers[0].name", value="server")]
    assert without_fields.fields == []


def test_ground_truth_unchanged_field_accepts_json_values() -> None:
    obj = GroundTruthUnchangedKubernetesObject.model_validate(
        {
            "kind": "Deployment",
            "name": "frontend",
            "fields": [{"path": "spec.selector", "value": {"matchLabels": {"app": "frontend"}}}],
        }
    )
    assert obj.fields[0].value == {"matchLabels": {"app": "frontend"}}


def test_ground_truth_unchanged_field_requires_path_and_value() -> None:
    with pytest.raises(ValidationError):
        GroundTruthField.model_validate({"path": "spec.replicas"})


def test_ground_truth_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        PrometheusAlertSignal(
            name=PrometheusAlertNames.KubePodCrashLooping,
            extra_field="invalid",
        )
