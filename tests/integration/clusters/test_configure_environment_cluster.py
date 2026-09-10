"""
Integration tests for configure_environment_cluster.py.

Requires a running local cluster (Kind or Minikube) with KUBECONFIG set.

Run with: uv run pytest tests/integration/clusters/ -v -m integration
"""
import os

import pytest
from kubernetes import client, config

import configure_environment_cluster as cec

pytestmark = pytest.mark.integration

SANDBOX_LABEL_KEY = cec.SANDBOX_LABEL_KEY
SANDBOX_LABEL_VALUE = cec.SANDBOX_LABEL_VALUE
CONTROL_PLANE_LABEL = cec.CONTROL_PLANE_LABEL
KUBELET_SERVING_SIGNER = cec.KUBELET_SERVING_SIGNER


@pytest.fixture(scope="module")
def k8s_clients() -> tuple[client.CertificatesV1Api, client.CoreV1Api]:
    if not os.environ.get("KUBECONFIG"):
        pytest.skip("KUBECONFIG is not set.")
    try:
        config.load_kube_config()
    except Exception as e:
        pytest.skip(f"Cluster unreachable: {e}")
    return client.CertificatesV1Api(), client.CoreV1Api()


@pytest.fixture(scope="module", autouse=True)
def run_configure(k8s_clients: tuple[client.CertificatesV1Api, client.CoreV1Api]) -> None:
    """Run the full configure script once before all tests in this module."""
    certs_api, core_api = k8s_clients
    cec.approve_kubelet_serving_csrs(certs_api)
    cec.label_sandbox_nodes(core_api)


# ---------------------------------------------------------------------------
# CSR approval
# ---------------------------------------------------------------------------

def test_no_pending_kubelet_serving_csrs(
    k8s_clients: tuple[client.CertificatesV1Api, client.CoreV1Api],
) -> None:
    """After the script runs, no kubelet-serving CSR should remain pending."""
    certs_api, _ = k8s_clients
    csrs = certs_api.list_certificate_signing_request(
        field_selector=f"spec.signerName={KUBELET_SERVING_SIGNER}",
    )
    pending = [
        csr for csr in csrs.items
        if not any(
            c.type in ("Approved", "Denied")
            for c in (csr.status.conditions or [])
        )
    ]
    assert pending == [], (
        f"Found {len(pending)} pending kubelet-serving CSR(s): "
        + ", ".join(c.metadata.name for c in pending)
    )


def test_kubelet_serving_csrs_are_approved(
    k8s_clients: tuple[client.CertificatesV1Api, client.CoreV1Api],
) -> None:
    """Every kubelet-serving CSR should carry an Approved condition."""
    certs_api, _ = k8s_clients
    csrs = certs_api.list_certificate_signing_request(
        field_selector=f"spec.signerName={KUBELET_SERVING_SIGNER}",
    )
    for csr in csrs.items:
        approved = any(
            c.type == "Approved" and c.status == "True"
            for c in (csr.status.conditions or [])
        )
        assert approved, f"CSR {csr.metadata.name} is not Approved."


# ---------------------------------------------------------------------------
# Sandbox node labeling
# ---------------------------------------------------------------------------

def _worker_nodes(core_api: client.CoreV1Api) -> list[client.V1Node]:
    all_nodes = core_api.list_node().items
    return sorted(
        [n for n in all_nodes if CONTROL_PLANE_LABEL not in (n.metadata.labels or {})],
        key=lambda n: n.metadata.name,
    )


def test_correct_number_of_sandbox_nodes(
    k8s_clients: tuple[client.CertificatesV1Api, client.CoreV1Api],
) -> None:
    """The number of sandbox-labeled nodes equals worker_count minus non_sandbox_count."""
    _, core_api = k8s_clients
    workers = _worker_nodes(core_api)
    expected_sandbox = len(workers) - cec._non_sandbox_count(len(workers))
    actual_sandbox = [
        n for n in workers
        if (n.metadata.labels or {}).get(SANDBOX_LABEL_KEY) == SANDBOX_LABEL_VALUE
    ]
    assert len(actual_sandbox) == expected_sandbox, (
        f"Expected {expected_sandbox} sandbox node(s), found {len(actual_sandbox)}: "
        + ", ".join(n.metadata.name for n in actual_sandbox)
    )


def test_first_workers_are_not_sandbox(
    k8s_clients: tuple[client.CertificatesV1Api, client.CoreV1Api],
) -> None:
    """The first N workers (by name sort) should not carry the sandbox label."""
    _, core_api = k8s_clients
    workers = _worker_nodes(core_api)
    non_sandbox_count = cec._non_sandbox_count(len(workers))
    for node in workers[:non_sandbox_count]:
        label_val = (node.metadata.labels or {}).get(SANDBOX_LABEL_KEY)
        assert label_val is None, (
            f"Node {node.metadata.name} should not be labeled sandbox but has "
            f"{SANDBOX_LABEL_KEY}={label_val}."
        )


def test_last_workers_are_sandbox(
    k8s_clients: tuple[client.CertificatesV1Api, client.CoreV1Api],
) -> None:
    """The last workers (after reserving N) should all carry the sandbox label."""
    _, core_api = k8s_clients
    workers = _worker_nodes(core_api)
    non_sandbox_count = cec._non_sandbox_count(len(workers))
    for node in workers[non_sandbox_count:]:
        label_val = (node.metadata.labels or {}).get(SANDBOX_LABEL_KEY)
        assert label_val == SANDBOX_LABEL_VALUE, (
            f"Node {node.metadata.name} should be labeled sandbox but has "
            f"{SANDBOX_LABEL_KEY}={label_val!r}."
        )
