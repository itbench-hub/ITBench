"""Tests for itbench.utils.cluster."""

from unittest.mock import MagicMock, patch

import pytest

from itbench.utils.cluster import (
    KUBELET_SERVING_SIGNER,
    SANDBOX_NODE_LABEL,
    WORKER_NODE_LABEL_SELECTOR,
    approve_pending_kublet_certificate_requests,
    partition_cluster_nodes,
    prepare_cluster,
)


def _make_mock_csr(name: str, conditions: list | None = None) -> MagicMock:
    csr = MagicMock()
    csr.metadata.name = name
    csr.status.conditions = conditions
    return csr


def _make_mock_node(name: str, labels: dict[str, str] | None = None) -> MagicMock:
    node = MagicMock()
    node.metadata.name = name
    node.metadata.labels = labels or {}
    return node


def test_approve_pending_csrs_approves_unconditioned_csr() -> None:
    with patch("itbench.utils.cluster.client.CertificatesV1Api") as mock_cert_cls:
        cert_api = MagicMock()
        mock_cert_cls.return_value = cert_api

        csr1 = _make_mock_csr("csr-pending", conditions=None)
        cert_api.list_certificate_signing_request.return_value.items = [csr1]

        approve_pending_kublet_certificate_requests()

        cert_api.list_certificate_signing_request.assert_called_once_with(
            field_selector=f"spec.signerName={KUBELET_SERVING_SIGNER}"
        )
        cert_api.replace_certificate_signing_request_approval.assert_called_once()
        assert csr1.status.conditions[0].type == "Approved"
        assert csr1.status.conditions[0].status == "True"


def test_approve_pending_csrs_skips_already_processed_csrs() -> None:
    with patch("itbench.utils.cluster.client.CertificatesV1Api") as mock_cert_cls:
        cert_api = MagicMock()
        mock_cert_cls.return_value = cert_api

        approved_cond = MagicMock()
        approved_cond.type = "Approved"

        denied_cond = MagicMock()
        denied_cond.type = "Denied"

        csr_approved = _make_mock_csr("csr-1", conditions=[approved_cond])
        csr_denied = _make_mock_csr("csr-2", conditions=[denied_cond])
        csr_pending = _make_mock_csr("csr-3", conditions=[])

        cert_api.list_certificate_signing_request.return_value.items = [
            csr_approved,
            csr_denied,
            csr_pending,
        ]

        approve_pending_kublet_certificate_requests()

        cert_api.replace_certificate_signing_request_approval.assert_called_once()


def test_approve_pending_csrs_no_csrs() -> None:
    with patch("itbench.utils.cluster.client.CertificatesV1Api") as mock_cert_cls:
        cert_api = MagicMock()
        mock_cert_cls.return_value = cert_api
        cert_api.list_certificate_signing_request.return_value.items = []

        approve_pending_kublet_certificate_requests()

        cert_api.replace_certificate_signing_request_approval.assert_not_called()


def test_partition_cluster_nodes_raises_when_no_workers() -> None:
    with patch("itbench.utils.cluster.client.CoreV1Api") as mock_core_cls:
        core_api = MagicMock()
        mock_core_cls.return_value = core_api
        core_api.list_node.return_value.items = []

        with pytest.raises(RuntimeError, match="Insufficient number of worker nodes detected"):
            partition_cluster_nodes()

        core_api.list_node.assert_called_once_with(label_selector=WORKER_NODE_LABEL_SELECTOR)


def test_partition_cluster_nodes_raises_when_only_one_worker() -> None:
    with patch("itbench.utils.cluster.client.CoreV1Api") as mock_core_cls:
        core_api = MagicMock()
        mock_core_cls.return_value = core_api
        core_api.list_node.return_value.items = [_make_mock_node("worker-1")]

        with pytest.raises(RuntimeError, match="Insufficient number of worker nodes detected"):
            partition_cluster_nodes()


def test_partition_cluster_nodes_two_workers() -> None:
    with patch("itbench.utils.cluster.client.CoreV1Api") as mock_core_cls:
        core_api = MagicMock()
        mock_core_cls.return_value = core_api
        w1 = _make_mock_node("worker-1")
        w2 = _make_mock_node("worker-2")
        core_api.list_node.return_value.items = [w1, w2]

        partition_cluster_nodes()

        # w1 gets sandbox: true, w2 gets sandbox: None
        core_api.patch_node.assert_any_call(
            "worker-1",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: "true"}}},
        )
        core_api.patch_node.assert_any_call(
            "worker-2",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: None}}},
        )


def test_partition_cluster_nodes_three_workers() -> None:
    with patch("itbench.utils.cluster.client.CoreV1Api") as mock_core_cls:
        core_api = MagicMock()
        mock_core_cls.return_value = core_api
        w1 = _make_mock_node("worker-1")
        w2 = _make_mock_node("worker-2")
        w3 = _make_mock_node("worker-3")
        core_api.list_node.return_value.items = [w1, w2, w3]

        partition_cluster_nodes()

        # w1, w2 get sandbox: true, w3 gets sandbox: None
        core_api.patch_node.assert_any_call(
            "worker-1",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: "true"}}},
        )
        core_api.patch_node.assert_any_call(
            "worker-2",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: "true"}}},
        )
        core_api.patch_node.assert_any_call(
            "worker-3",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: None}}},
        )


def test_partition_cluster_nodes_four_workers() -> None:
    with patch("itbench.utils.cluster.client.CoreV1Api") as mock_core_cls:
        core_api = MagicMock()
        mock_core_cls.return_value = core_api
        w1 = _make_mock_node("worker-1")
        w2 = _make_mock_node("worker-2")
        w3 = _make_mock_node("worker-3")
        w4 = _make_mock_node("worker-4")
        core_api.list_node.return_value.items = [w1, w2, w3, w4]

        partition_cluster_nodes()

        # w1, w2 get sandbox: true, w3, w4 get sandbox: None
        core_api.patch_node.assert_any_call(
            "worker-1",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: "true"}}},
        )
        core_api.patch_node.assert_any_call(
            "worker-2",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: "true"}}},
        )
        core_api.patch_node.assert_any_call(
            "worker-3",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: None}}},
        )
        core_api.patch_node.assert_any_call(
            "worker-4",
            {"metadata": {"labels": {SANDBOX_NODE_LABEL: None}}},
        )


def test_prepare_cluster_success() -> None:
    with (
        patch("itbench.utils.cluster.config.load_kube_config") as mock_load_config,
        patch("itbench.utils.cluster.approve_pending_kublet_certificate_requests") as mock_approve,
        patch("itbench.utils.cluster.partition_cluster_nodes") as mock_partition,
    ):
        prepare_cluster(kubeconfig="/path/to/kubeconfig", context="kind-test")

        mock_load_config.assert_called_once_with(
            config_file="/path/to/kubeconfig", context="kind-test"
        )
        mock_approve.assert_called_once()
        mock_partition.assert_called_once()
