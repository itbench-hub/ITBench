"""Tests for Kubernetes data models and discriminated union."""

import pytest

from pydantic import TypeAdapter, ValidationError

from itbench.models.kubernetes import (
    KubernetesGateway,
    KubernetesHorizontalPodAutoscaler,
    KubernetesNamespace,
    KubernetesObject,
    KubernetesObjectKind,
    KubernetesObjects,
    KubernetesSecret,
    KubernetesService,
    KubernetesWorkload,
)


def test_kubernetes_object_defaults() -> None:
    obj = KubernetesObject(kind="ConfigMap", name="my-config")
    assert obj.api_version == "v1"
    assert obj.kind == "ConfigMap"
    assert obj.name == "my-config"
    assert obj.namespace is None


def test_kubernetes_object_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        KubernetesObject(kind="ConfigMap", name="my-config", extra_field="forbidden")


def test_kubernetes_horizontal_pod_autoscaler() -> None:
    hpa = KubernetesHorizontalPodAutoscaler(
        name="test-hpa",
        namespace="default",
    )
    assert hpa.api_version == "autoscaling/v2"
    assert hpa.kind == "HorizontalPodAutoscaler"
    assert hpa.name == "test-hpa"
    assert hpa.namespace == "default"


def test_kubernetes_gateway() -> None:
    gw = KubernetesGateway(name="test-gateway", namespace="istio-system")
    assert gw.api_version == "gateway.networking.k8s.io/v1"
    assert gw.kind == "Gateway"
    assert gw.name == "test-gateway"
    assert gw.namespace == "istio-system"


def test_kubernetes_namespace() -> None:
    ns = KubernetesNamespace(name="production")
    assert ns.api_version == "v1"
    assert ns.kind == "Namespace"
    assert ns.name == "production"
    assert ns.namespace is None


def test_kubernetes_secret() -> None:
    secret = KubernetesSecret(name="db-credentials", namespace="default")
    assert secret.api_version == "v1"
    assert secret.kind == "Secret"
    assert secret.name == "db-credentials"
    assert secret.namespace == "default"


def test_kubernetes_service() -> None:
    svc = KubernetesService(name="frontend-svc", namespace="default")
    assert svc.api_version == "v1"
    assert svc.kind == "Service"
    assert svc.name == "frontend-svc"
    assert svc.namespace == "default"


def test_kubernetes_workload_defaults() -> None:
    wl = KubernetesWorkload(name="api-server", namespace="default")
    assert wl.api_version == "apps/v1"
    assert wl.kind == "Deployment"
    assert wl.name == "api-server"
    assert wl.namespace == "default"


@pytest.mark.parametrize("kind", ["DaemonSet", "Deployment", "StatefulSet"])
def test_kubernetes_workload_valid_kinds(kind: str) -> None:
    wl = KubernetesWorkload(kind=kind, name="worker", namespace="default")
    assert wl.kind == kind


def test_kubernetes_workload_invalid_kind() -> None:
    with pytest.raises(ValidationError):
        KubernetesWorkload(kind="Job", name="worker", namespace="default")


def test_kubernetes_objects_discriminated_union() -> None:
    adapter = TypeAdapter(KubernetesObjects)

    data = {
        "kind": "Gateway",
        "name": "edge-gw",
        "namespace": "ingress",
    }
    validated = adapter.validate_python(data)
    assert isinstance(validated, KubernetesGateway)
    assert validated.api_version == "gateway.networking.k8s.io/v1"

    workload_data = {
        "kind": "StatefulSet",
        "name": "redis",
        "namespace": "database",
    }
    validated_workload = adapter.validate_python(workload_data)
    assert isinstance(validated_workload, KubernetesWorkload)
    assert validated_workload.kind == "StatefulSet"


def test_kubernetes_object_kind_enum_sync() -> None:
    expected_kinds = {
        "KubernetesGateway",
        "KubernetesHorizontalPodAutoscaler",
        "KubernetesNamespace",
        "KubernetesSecret",
        "KubernetesService",
        "KubernetesWorkload",
    }
    actual_kinds = {member.value for member in KubernetesObjectKind}
    assert actual_kinds == expected_kinds
