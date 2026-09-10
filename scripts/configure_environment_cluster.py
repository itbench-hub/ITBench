"""
Configure the environment cluster after creation on Kind or Minikube.

Two setup steps that must complete before the metrics server and fault
injection are functional:

  1. Approve pending kubelet-serving CSRs.
  2. Label sandbox worker nodes.

The cluster is identified by the KUBECONFIG environment variable.

Makefile invocation:
  uv run python ../../scripts/configure_environment_cluster.py
"""
import logging
import os

from kubernetes import client, config, watch

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

SANDBOX_LABEL_KEY = "node-role.itbench.io/sandbox"
SANDBOX_LABEL_VALUE = "true"
CONTROL_PLANE_LABEL = "node-role.kubernetes.io/control-plane"
KUBELET_SERVING_SIGNER = "kubernetes.io/kubelet-serving"

# With ≥4 workers, reserve 2 nodes for tools; otherwise reserve 1.
_NON_SANDBOX_THRESHOLD = 4
_NON_SANDBOX_LARGE = 2
_NON_SANDBOX_SMALL = 1

_WATCH_TIMEOUT = 120


def _non_sandbox_count(worker_count: int) -> int:
    return _NON_SANDBOX_LARGE if worker_count >= _NON_SANDBOX_THRESHOLD else _NON_SANDBOX_SMALL


def approve_kubelet_serving_csrs(certs_api: client.CertificatesV1Api) -> None:
    """Approve all pending kubernetes.io/kubelet-serving CSRs.

    Mirrors the Ansible implementation:
      1. Wait until at least one kubelet-serving CSR appears, then list all of them.
      2. Approve each one where status.conditions is absent.
      3. Watch each approved CSR until the Approved condition reflects.
    """
    # Step 1 — wait until at least one kubelet-serving CSR is visible, then
    # snapshot the full list so every pending CSR is captured.
    w = watch.Watch()
    for event in w.stream(
        certs_api.list_certificate_signing_request,
        field_selector=f"spec.signerName={KUBELET_SERVING_SIGNER}",
        timeout_seconds=_WATCH_TIMEOUT,
    ):
        if event["object"] is not None:
            w.stop()

    csr_list = certs_api.list_certificate_signing_request(
        field_selector=f"spec.signerName={KUBELET_SERVING_SIGNER}",
    )
    seen = {csr.metadata.name: csr for csr in csr_list.items}

    if not seen:
        logger.info("No kubelet-serving CSRs found; skipping CSR approval.")
        return

    # Step 2 — approve each pending (no conditions) CSR.
    to_confirm: list[str] = []
    for csr in seen.values():
        if csr.status.conditions:
            logger.info("CSR %s already has conditions; skipping.", csr.metadata.name)
            continue
        csr.status.conditions = [
            client.V1CertificateSigningRequestCondition(
                type="Approved",
                status="True",
                reason="ScriptApproved",
                message="Approved by configure_environment_cluster.py",
            )
        ]
        certs_api.replace_certificate_signing_request_approval(csr.metadata.name, csr)
        logger.info("Approved CSR: %s", csr.metadata.name)
        to_confirm.append(csr.metadata.name)

    # Step 3 — wait for each approval to reflect.
    for name in to_confirm:
        w = watch.Watch()
        for event in w.stream(
            certs_api.list_certificate_signing_request,
            field_selector=f"metadata.name={name}",
            timeout_seconds=_WATCH_TIMEOUT,
        ):
            csr = event["object"]
            if any(c.type == "Approved" and c.status == "True" for c in (csr.status.conditions or [])):
                logger.info("CSR %s confirmed Approved.", name)
                w.stop()


def label_sandbox_nodes(core_api: client.CoreV1Api) -> None:
    """Label all-but-N worker nodes as sandbox targets."""
    all_nodes = core_api.list_node().items
    workers = sorted(
        [n for n in all_nodes if CONTROL_PLANE_LABEL not in (n.metadata.labels or {})],
        key=lambda n: n.metadata.name,
    )

    if not workers:
        logger.warning("No worker nodes found; skipping sandbox labeling.")
        return

    non_sandbox_count = _non_sandbox_count(len(workers))
    non_sandbox = {n.metadata.name for n in workers[:non_sandbox_count]}
    sandbox = [n for n in workers if n.metadata.name not in non_sandbox]

    logger.info(
        "Workers: %d total, %d non-sandbox, %d sandbox.",
        len(workers), len(non_sandbox), len(sandbox),
    )

    for node in sandbox:
        core_api.patch_node(
            node.metadata.name,
            {"metadata": {"labels": {SANDBOX_LABEL_KEY: SANDBOX_LABEL_VALUE}}},
        )
        logger.info("Labeled node as sandbox: %s", node.metadata.name)


def main() -> None:
    kubeconfig = os.environ.get("KUBECONFIG")
    if not kubeconfig:
        raise EnvironmentError("KUBECONFIG environment variable is not set.")

    config.load_kube_config(config_file=kubeconfig)

    approve_kubelet_serving_csrs(client.CertificatesV1Api())
    label_sandbox_nodes(client.CoreV1Api())


if __name__ == "__main__":
    main()
