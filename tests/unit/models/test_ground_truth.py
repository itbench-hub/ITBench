"""Tests for GroundTruth model and components."""

import pytest

from pydantic import ValidationError

from itbench.models.fault import (
    FaultAlerts,
    FaultSolution,
    FaultSolutionStep,
)
from itbench.models.ground_truth import (
    GroundTruth,
    GroundTruthAlert,
    GroundTruthEntity,
)
from itbench.models.kubernetes import KubernetesWorkload


def test_ground_truth_valid() -> None:
    gt = GroundTruth(
        alerts=[
            GroundTruthAlert(
                name=FaultAlerts.KubePodCrashLooping,
                labels={"namespace": "default", "app": "frontend"},
            )
        ],
        entities=[
            GroundTruthEntity(
                kubernetes=[
                    KubernetesWorkload(
                        kind="Deployment",
                        name="frontend",
                        namespace="default",
                    )
                ]
            )
        ],
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
    assert len(gt.alerts) == 1
    assert gt.alerts[0].name == FaultAlerts.KubePodCrashLooping
    assert len(gt.entities) == 1
    assert len(gt.solutions) == 1


def test_ground_truth_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        GroundTruthAlert(
            name=FaultAlerts.KubePodCrashLooping,
            extra_field="invalid",
        )
