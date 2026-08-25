"""
Integration tests for external LoadBalancer IP assignment on a local cluster.

Requires a running local cluster with a LoadBalancer provider active:
  - Kind:     cloud-provider-kind
  - Minikube: minikube tunnel

Run with: uv run pytest tests/clusters/local/
"""
import pytest
from kubernetes import client, config, watch


NAMESPACE_ONE = "lb-test-one"
NAMESPACE_TWO = "lb-test-two"
SERVICE_ONE = "service-one"
SERVICE_TWO = "service-two"
TIMEOUT_SECONDS = 300


def _create_namespace(name: str) -> client.V1Namespace:
    return client.V1Namespace(metadata=client.V1ObjectMeta(name=name))


def _create_lb_service(name: str, namespace: str) -> client.V1Service:
    return client.V1Service(
        metadata=client.V1ObjectMeta(name=name, namespace=namespace),
        spec=client.V1ServiceSpec(
            type="LoadBalancer",
            ports=[client.V1ServicePort(port=80, target_port=8080)],
        ),
    )


def _wait_for_external_ip(v1: client.CoreV1Api, name: str, namespace: str) -> str:
    """Stream service events until an external IP is assigned, then return it."""
    w = watch.Watch()
    for event in w.stream(
        v1.list_namespaced_service,
        namespace=namespace,
        timeout_seconds=TIMEOUT_SECONDS,
    ):
        svc = event["object"]
        if svc.metadata.name != name:
            continue
        ingress = svc.status.load_balancer.ingress
        if ingress and ingress[0].ip:
            w.stop()
            return ingress[0].ip
    raise TimeoutError(f"Service {namespace}/{name} did not receive an external IP within {TIMEOUT_SECONDS}s")


@pytest.fixture(scope="module")
def v1() -> client.CoreV1Api:
    config.load_kube_config()
    return client.CoreV1Api()


@pytest.fixture(scope="module", autouse=True)
def load_balancer_services(v1: client.CoreV1Api):
    for ns in (NAMESPACE_ONE, NAMESPACE_TWO):
        v1.create_namespace(_create_namespace(ns))

    v1.create_namespaced_service(NAMESPACE_ONE, _create_lb_service(SERVICE_ONE, NAMESPACE_ONE))
    v1.create_namespaced_service(NAMESPACE_TWO, _create_lb_service(SERVICE_TWO, NAMESPACE_TWO))

    yield

    for ns in (NAMESPACE_ONE, NAMESPACE_TWO):
        v1.delete_namespace(ns)


def test_service_one_gets_external_ip(v1: client.CoreV1Api):
    """service-one in lb-test-one receives a non-empty external IP."""
    ip = _wait_for_external_ip(v1, SERVICE_ONE, NAMESPACE_ONE)
    assert ip


def test_service_two_gets_external_ip(v1: client.CoreV1Api):
    """service-two in lb-test-two receives a non-empty external IP."""
    ip = _wait_for_external_ip(v1, SERVICE_TWO, NAMESPACE_TWO)
    assert ip


def test_services_get_distinct_ips(v1: client.CoreV1Api):
    """service-one and service-two are assigned different external IPs."""
    ip_one = _wait_for_external_ip(v1, SERVICE_ONE, NAMESPACE_ONE)
    ip_two = _wait_for_external_ip(v1, SERVICE_TWO, NAMESPACE_TWO)
    assert ip_one != ip_two, (
        f"Both services received the same external IP ({ip_one}). "
        "The LoadBalancer provider must assign unique IPs per LoadBalancer service."
    )
