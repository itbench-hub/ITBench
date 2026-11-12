"""Approve the kubelet serving certificate requests of a Kind cluster.

The Kind configs set `serverTLSBootstrap: true`, so every kubelet asks for its serving certificate with a
CertificateSigningRequest that nothing signs automatically. Without an approval, metrics-server and Prometheus
cannot scrape the kubelets over TLS. The requests are filed shortly after a node joins, so this waits until
every node has an approved request instead of approving once.
"""

import argparse
import datetime
import sys
import time

from kubernetes import client, config
from kubernetes.client.rest import ApiException


def approve_kubelet_csrs(kubeconfig: str, timeout: int = 120) -> None:
    config.load_kube_config(config_file=kubeconfig)
    core_api = client.CoreV1Api()
    cert_api = client.CertificatesV1Api()
    signer = "kubernetes.io/kubelet-serving"

    deadline = time.time() + timeout

    while True:
        try:
            nodes = core_api.list_node().items
        except ApiException as e:
            nodes = []

        try:
            csrs = cert_api.list_certificate_signing_request().items
        except ApiException as e:
            csrs = []

        approved_nodes: set[str] = set()

        for csr in csrs:
            if csr.spec.signer_name != signer:
                continue

            username = csr.spec.username or ""
            conditions = csr.status.conditions if csr.status else None
            is_approved = any(c.type == "Approved" for c in (conditions or []))

            if not is_approved and not conditions:
                approval_condition = client.V1CertificateSigningRequestCondition(
                    type="Approved",
                    status="True",
                    reason="ApprovedByITBench",
                    message="Approved kubelet serving certificate for ITBench Kind cluster",
                    last_update_time=datetime.datetime.now(datetime.timezone.utc),
                )
                if csr.status is None:
                    csr.status = client.V1CertificateSigningRequestStatus(conditions=[approval_condition])
                else:
                    csr.status.conditions = [approval_condition]

                try:
                    cert_api.replace_certificate_signing_request_approval(
                        name=csr.metadata.name,
                        body=csr,
                    )
                    approved_nodes.add(username)
                except ApiException as e:
                    if e.status == 409:
                        # Conflict: status was modified, re-check on next iteration
                        pass
                    else:
                        print(
                            f"Warning: Failed to approve CSR {csr.metadata.name}: {e.status} {e.reason}",
                            file=sys.stderr,
                        )
            elif is_approved:
                approved_nodes.add(username)

        covered = len(approved_nodes)
        total_nodes = len(nodes)

        if total_nodes > 0 and covered >= total_nodes:
            print(f"Approved the kubelet serving certificates of {covered} node(s).")
            return

        if time.time() >= deadline:
            print(
                f"Timed out after {timeout}s: {covered} of {total_nodes} node(s) have an approved kubelet serving certificate.",
                file=sys.stderr,
            )
            sys.exit(1)

        time.sleep(2)


def main() -> None:
    parser = argparse.ArgumentParser(description="Approve kubelet serving CSRs for Kind")
    parser.add_argument("kubeconfig", help="Path to cluster kubeconfig")
    parser.add_argument("timeout", nargs="?", type=int, default=120, help="Timeout in seconds")
    args = parser.parse_args()
    approve_kubelet_csrs(args.kubeconfig, args.timeout)


if __name__ == "__main__":
    main()
