"""Tests for Waiter models, discriminated union, and waiter catalog."""

import pytest

from pydantic import TypeAdapter, ValidationError

from itbench.models.kubernetes import KubernetesWorkload
from itbench.models.platform import Platform
from itbench.models.waiter import (
    WAITER_CATALOG,
    WaiterDeleteWorkloadPods,
    WaiterPauseExecution,
    WaiterRestartKubernetesWorkload,
    WaiterScaleKubernetesWorkload,
    WaiterUnassignWorkloadContainerResourceLimits,
    Waiters,
)


def _sample_workload() -> KubernetesWorkload:
    return KubernetesWorkload(
        kind="Deployment",
        name="test-deployment",
        namespace="default",
    )


def test_waiter_pause_execution() -> None:
    waiter = WaiterPauseExecution(
        description="Pause test",
        name="Pause",
        seconds=15,
    )
    assert waiter.id == "pause-execution"
    assert waiter.seconds == 15
    assert waiter.platforms == [Platform.Localhost]


def test_waiter_pause_execution_gt_zero() -> None:
    with pytest.raises(ValidationError):
        WaiterPauseExecution(
            description="Pause test",
            name="Pause",
            seconds=0,
        )


def test_waiter_scale_kubernetes_workload() -> None:
    waiter = WaiterScaleKubernetesWorkload(
        description="Scale test",
        name="Scale",
        workload=_sample_workload(),
        replicas=3,
    )
    assert waiter.id == "scale-kubernetes-workload"
    assert waiter.replicas == 3
    assert waiter.platforms == [Platform.Kubernetes, Platform.OpenShift]


def test_waiter_delete_workload_pods() -> None:
    waiter = WaiterDeleteWorkloadPods(
        description="Delete pods",
        name="Delete Pods",
        workload=_sample_workload(),
    )
    assert waiter.id == "delete-workload-pods"


def test_waiter_restart_kubernetes_workload() -> None:
    waiter = WaiterRestartKubernetesWorkload(
        description="Restart workload",
        name="Restart",
        workload=_sample_workload(),
    )
    assert waiter.id == "restart-kubernetes-workload"


def test_waiter_unassign_limits() -> None:
    waiter = WaiterUnassignWorkloadContainerResourceLimits(
        description="Remove limits",
        name="Unassign Limits",
        container="main-container",
        workload=_sample_workload(),
    )
    assert waiter.id == "unassign-workload-container-resource-limits"
    assert waiter.container == "main-container"


def test_waiters_discriminated_union() -> None:
    adapter = TypeAdapter(Waiters)
    pause_data = {
        "id": "pause-execution",
        "description": "Pause step",
        "name": "Pause",
        "seconds": 20,
    }
    validated = adapter.validate_python(pause_data)
    assert isinstance(validated, WaiterPauseExecution)
    assert validated.seconds == 20


def test_waiter_catalog_completeness() -> None:
    expected_waiters = {
        "delete-workload-pods",
        "pause-execution",
        "restart-kubernetes-workload",
        "scale-kubernetes-workload",
        "unassign-workload-container-resource-limits",
    }
    assert set(WAITER_CATALOG.keys()) == expected_waiters
