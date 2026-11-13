"""Integration tests for Cloud Provider Kind: every LoadBalancer Service must receive its own external IP.

The tests need Cloud Provider Kind running next to the cluster (``mise -E kind run run:kind:provider``). They do not
need the tools stack.
"""

import time

from collections.abc import Generator

import pytest

from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

pytestmark = pytest.mark.integration

NAMESPACES = ("lb-test-one", "lb-test-two")
SERVICE_NAME = "service"
EXTERNAL_IP_TIMEOUT_SECONDS = 300
POLL_INTERVAL_SECONDS = 5


def _delete_namespace(core_api: client.CoreV1Api, name: str) -> None:
    try:
        core_api.delete_namespace(name)
    except ApiException as exc:
        if exc.status != 404:
            raise


def _external_ip(core_api: client.CoreV1Api, namespace: str) -> str | None:
    service = core_api.read_namespaced_service(SERVICE_NAME, namespace)
    ingress = service.status.load_balancer.ingress
    return ingress[0].ip if ingress and ingress[0].ip else None


def _wait_for_external_ip(core_api: client.CoreV1Api, namespace: str) -> str:
    deadline = time.monotonic() + EXTERNAL_IP_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        ip = _external_ip(core_api, namespace)
        if ip:
            return ip
        time.sleep(POLL_INTERVAL_SECONDS)
    pytest.fail(
        f"Service '{SERVICE_NAME}' in '{namespace}' did not receive an external IP within "
        f"{EXTERNAL_IP_TIMEOUT_SECONDS}s. Is Cloud Provider Kind running?"
    )


@pytest.fixture(scope="module")
def load_balancers(kubeconfig: str) -> Generator[dict[str, str]]:
    """Create one LoadBalancer Service in each namespace and yield the external IP assigned to each."""
    core_api = client.CoreV1Api(config.new_client_from_config(config_file=kubeconfig))

    try:
        for namespace in NAMESPACES:
            core_api.create_namespace(client.V1Namespace(metadata=client.V1ObjectMeta(name=namespace)))
            core_api.create_namespaced_service(
                namespace,
                client.V1Service(
                    metadata=client.V1ObjectMeta(name=SERVICE_NAME),
                    spec=client.V1ServiceSpec(
                        type="LoadBalancer",
                        ports=[client.V1ServicePort(port=80, target_port=8080)],
                    ),
                ),
            )

        yield {namespace: _wait_for_external_ip(core_api, namespace) for namespace in NAMESPACES}
    finally:
        for namespace in NAMESPACES:
            _delete_namespace(core_api, namespace)


@pytest.mark.parametrize("namespace", NAMESPACES)
def test_service_receives_an_external_ip(load_balancers: dict[str, str], namespace: str) -> None:
    assert load_balancers[namespace], f"Service '{SERVICE_NAME}' in '{namespace}' did not receive an external IP"


def test_services_receive_distinct_external_ips(load_balancers: dict[str, str]) -> None:
    ips = list(load_balancers.values())
    assert len(set(ips)) == len(ips), (
        f"Services received the same external IP ({ips[0]}). "
        "Cloud Provider Kind must assign unique IPs per LoadBalancer service."
    )
