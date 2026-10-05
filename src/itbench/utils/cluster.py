"""Cluster preparation utilities for ITBench.

Handles automatic CertificateSigningRequest (CSR) approvals and node partitioning
for workloads and tools.
"""

from datetime import datetime, timezone

from kubernetes import client, config  # type: ignore[import-untyped]

SANDBOX_NODE_LABEL = "node-role.itbench.io/sandbox"
KUBELET_SERVING_SIGNER = "kubernetes.io/kubelet-serving"
CONTROL_PLANE_LABEL = "node-role.kubernetes.io/control-plane"
MASTER_LABEL = "node-role.kubernetes.io/master"
WORKER_NODE_LABEL_SELECTOR = f"!{CONTROL_PLANE_LABEL},!{MASTER_LABEL}"


def approve_pending_kublet_certificate_requests() -> None:
    """Approve all pending CertificateSigningRequests matching kubelet-serving signer."""
    cert_api = client.CertificatesV1Api()

    requests = cert_api.list_certificate_signing_request(
        field_selector=f"spec.signerName={KUBELET_SERVING_SIGNER}"
    )

    for request in requests.items:
        conditions = request.status.conditions or []
        if any(c.type in ("Approved", "Denied") for c in conditions):
            continue

        request.status.conditions = [
            client.V1CertificateSigningRequestCondition(
                type="Approved",
                status="True",
                reason="AutoApproved",
                message="Automatically approved by ITBench",
                last_update_time=datetime.now(timezone.utc),
            )
        ]

        cert_api.replace_certificate_signing_request_approval(
            name=request.metadata.name,
            body=request,
        )


def partition_cluster_nodes() -> None:
    """Partition worker nodes into tool nodes and sandbox nodes.

    Rules for worker node partitioning:
      - Less than 2 worker nodes: Raises RuntimeError.
      - 2 worker nodes: 1 tool node, 1 sandbox node.
      - 3 worker nodes: 1 tool node, 2 sandbox nodes.
      - 4+ worker nodes: 2 tool nodes, (N - 2) sandbox nodes.

    Tool nodes will not have the ``node-role.itbench.io/sandbox`` label.
    Sandbox nodes will have the ``node-role.itbench.io/sandbox=true`` label.

    Raises:
        RuntimeError: If there are fewer than 2 worker nodes available.
    """
    core_api = client.CoreV1Api()

    worker_nodes = core_api.list_node(label_selector=WORKER_NODE_LABEL_SELECTOR).items

    node_count = len(worker_nodes)
    non_sandbox_node_count = min(2, node_count // 2)

    if node_count < 2:
        raise RuntimeError(
            f"Insufficient number of worker nodes detected ('{node_count}'). "
            "Please ensure that the cluster has at least 2 worker nodes."
        )

    for i in range(node_count):
        if i < node_count - non_sandbox_node_count:
            patch = {"metadata": {"labels": {SANDBOX_NODE_LABEL: "true"}}}
            core_api.patch_node(worker_nodes[i].metadata.name, patch)
        else:
            patch = {"metadata": {"labels": {SANDBOX_NODE_LABEL: None}}}
            core_api.patch_node(worker_nodes[i].metadata.name, patch)


def prepare_cluster(kubeconfig: str, context: str | None = None) -> None:
    """Prepare a Kubernetes cluster for ITBench scenarios and tooling.

    Approves kubelet-serving CSRs and labels worker nodes for tools and sandbox workloads.

    Args:
        kubeconfig: Path to the kubeconfig file.
        context: Optional kubeconfig context name.
    """
    config.load_kube_config(config_file=kubeconfig, context=context)

    partition_cluster_nodes()
    approve_pending_kublet_certificate_requests()
