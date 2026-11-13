"""Cluster utilities for ITBench.

Handles node partitioning for workloads and tools, clearing events, and issuing restricted agent kubeconfigs.
"""

import base64

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from kubernetes import client, config  # type: ignore[import-untyped]

AGENT_MISSION_LABEL = "itbench.io/agent-mission"
INJECT_NAMESPACE_LABEL_SELECTOR = "itbench.io/inject=true"
MIN_TOKEN_MINUTES = 10  # The API server rejects shorter ServiceAccount token lifetimes.
SANDBOX_NODE_TAINT_KEY = "itbench.io/sandbox"
SANDBOX_NODE_TAINT_EFFECT = "NoSchedule"
CONTROL_PLANE_LABEL = "node-role.kubernetes.io/control-plane"
MASTER_LABEL = "node-role.kubernetes.io/master"
WORKER_NODE_LABEL_SELECTOR = f"!{CONTROL_PLANE_LABEL},!{MASTER_LABEL}"


@dataclass(frozen=True)
class ClusterAccessBundle:
    """A restricted kubeconfig for an agent, with its expiry and the namespaces it can reach."""

    kubeconfig: dict[str, Any]
    expires: datetime
    namespaces: list[str]


def taint_sandbox_nodes() -> None:
    """Taint sandbox worker nodes so that only workloads tolerating the taint run on them.

    Rules for worker node partitioning:
      - Less than 2 worker nodes: Raises RuntimeError.
      - 2 worker nodes: 1 tool node, 1 sandbox node.
      - 3 worker nodes: 1 tool node, 2 sandbox nodes.
      - 4+ worker nodes: 2 tool nodes, (N - 2) sandbox nodes.

    Sandbox nodes get the ``itbench.io/sandbox=true:NoSchedule`` taint. Tool nodes have it removed,
    so running this again after the cluster changes converges on the same layout. Taints that
    ITBench does not own are left alone.

    Raises:
        RuntimeError: If there are fewer than 2 worker nodes available.
    """
    core_api = client.CoreV1Api()

    worker_nodes = core_api.list_node(label_selector=WORKER_NODE_LABEL_SELECTOR).items

    node_count = len(worker_nodes)
    if node_count < 2:
        raise RuntimeError(
            f"Insufficient number of worker nodes detected ('{node_count}'). "
            "Please ensure that the cluster has at least 2 worker nodes."
        )

    non_sandbox_node_count = min(2, node_count // 2)

    for index, node in enumerate(worker_nodes):
        taints = [
            {"key": taint.key, "value": taint.value, "effect": taint.effect}
            for taint in (node.spec.taints or [])
            if taint.key != SANDBOX_NODE_TAINT_KEY
        ]
        if index < node_count - non_sandbox_node_count:
            taints.append({"key": SANDBOX_NODE_TAINT_KEY, "value": "true", "effect": SANDBOX_NODE_TAINT_EFFECT})
        core_api.patch_node(node.metadata.name, {"spec": {"taints": taints or None}})


def configure_environment(kubeconfig: str) -> None:
    """Configure an environment cluster by tainting its sandbox worker nodes.

    Args:
        kubeconfig: Path to the kubeconfig file. The current context is used.
    """
    config.load_kube_config(config_file=kubeconfig)

    taint_sandbox_nodes()


def delete_events(kubeconfig: str) -> int:
    """Delete every Kubernetes event in the cluster so that a run starts from a clean slate.

    Args:
        kubeconfig: Path to the kubeconfig file. The current context is used.

    Returns:
        The number of namespaces whose events were deleted.
    """
    config.load_kube_config(config_file=kubeconfig)

    events_api = client.EventsV1Api()
    namespaces = sorted({event.metadata.namespace for event in events_api.list_event_for_all_namespaces().items})
    for namespace in namespaces:
        events_api.delete_collection_namespaced_event(namespace)
    return len(namespaces)


def create_agent_access(kubeconfig: str, mission: str, minutes: int) -> ClusterAccessBundle:
    """Issue a short-lived token for the agent ServiceAccount of *mission* and wrap it in a kubeconfig.

    The ServiceAccount is the one labelled ``itbench.io/agent-mission=<mission>``. The generated
    kubeconfig only contains the server, CA and bearer token of the active context, never the
    credentials used to call this function. The API server enforces a minimum token lifetime, so
    *minutes* is raised to :data:`MIN_TOKEN_MINUTES` when smaller.

    Args:
        kubeconfig: Path to the (administrator) kubeconfig file. The current context is used.
        mission: ``diagnosis`` or ``remediation``.
        minutes: Requested token lifetime in minutes.

    Returns:
        The kubeconfig, the expiry reported by the API server and the namespaces the agent is bound in.

    Raises:
        RuntimeError: If there is not exactly one ServiceAccount for *mission*.
    """
    config.load_kube_config(config_file=kubeconfig)
    settings = client.Configuration.get_default_copy()
    core_api = client.CoreV1Api()

    selector = f"{AGENT_MISSION_LABEL}={mission}"
    service_accounts = core_api.list_service_account_for_all_namespaces(label_selector=selector).items
    if len(service_accounts) != 1:
        raise RuntimeError(
            f"Expected exactly one ServiceAccount labelled '{selector}', found {len(service_accounts)}. "
            "Run `itbench deploy environment` to create it."
        )
    service_account = service_accounts[0]

    token_request = core_api.create_namespaced_service_account_token(
        service_account.metadata.name,
        service_account.metadata.namespace,
        client.AuthenticationV1TokenRequest(
            spec=client.V1TokenRequestSpec(expiration_seconds=max(minutes, MIN_TOKEN_MINUTES) * 60)
        ),
    )

    cluster: dict[str, Any] = {"server": settings.host}
    if not settings.verify_ssl:
        cluster["insecure-skip-tls-verify"] = True
    elif settings.ssl_ca_cert:
        cluster["certificate-authority-data"] = base64.b64encode(Path(settings.ssl_ca_cert).read_bytes()).decode()
    if settings.tls_server_name:
        cluster["tls-server-name"] = settings.tls_server_name

    name = f"itbench-{mission}"
    namespaces = sorted(
        namespace.metadata.name
        for namespace in core_api.list_namespace(label_selector=INJECT_NAMESPACE_LABEL_SELECTOR).items
    )
    return ClusterAccessBundle(
        kubeconfig={
            "apiVersion": "v1",
            "kind": "Config",
            "clusters": [{"name": "itbench", "cluster": cluster}],
            "users": [{"name": name, "user": {"token": token_request.status.token}}],
            "contexts": [{"name": name, "context": {"cluster": "itbench", "user": name}}],
            "current-context": name,
        },
        expires=token_request.status.expiration_timestamp,
        namespaces=namespaces,
    )
