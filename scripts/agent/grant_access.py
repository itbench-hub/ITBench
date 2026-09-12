#!/usr/bin/env python3
"""Create agent RBAC, request a token, and write a restricted kubeconfig to a given path.

Namespaces are discovered automatically by the label ``itbench.io/agent-accessible=true``.

"""

import argparse
import logging
import os
import sys
from pathlib import Path

import yaml

from kubernetes import config, dynamic
from kubernetes.client import ApiClient, AuthenticationV1TokenRequest, CoreV1Api

AGENT_ACCESSIBLE_LABEL = "itbench.io/agent-accessible=true"
FIELD_MANAGER = "itbench"
LABELS = {
    "app.kubernetes.io/component": "access-control",
    "app.kubernetes.io/managed-by": "ITBench",
}
TOKEN_EXPIRY_SECONDS = 64800  # 18 h

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def discover_namespaces(core: CoreV1Api):
    """Return all namespaces labelled ``itbench.io/agent-accessible=true``."""
    return core.list_namespace(label_selector=AGENT_ACCESSIBLE_LABEL).items


def _meta(name: str, namespace: str | None = None) -> dict:
    m: dict = {"name": name, "labels": LABELS}
    if namespace is not None:
        m["namespace"] = namespace
    return m


def apply_all(dyn: dynamic.DynamicClient, namespaces) -> None:
    sa_res = dyn.resources.get(api_version="v1", kind="ServiceAccount")
    role_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="Role")
    rb_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="RoleBinding")
    cr_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="ClusterRole")
    crb_res = dyn.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="ClusterRoleBinding")

    # ServiceAccount
    sa_res.server_side_apply(
        body={
            "apiVersion": "v1",
            "kind": "ServiceAccount",
            "metadata": _meta("agent", namespace="default"),
        },
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    )

    # Namespace-scoped RBAC
    for ns in namespaces:
        role_res.server_side_apply(
            body={
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "Role",
                "metadata": _meta("agent-namespace-access", namespace=ns.metadata.name),
                "rules": [{"apiGroups": [""], "resources": ["resourcequotas"], "verbs": ["*"]}],
            },
            field_manager=FIELD_MANAGER,
            force_conflicts=True,
        )

        rb_res.server_side_apply(
            body={
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": _meta("agent-namespace-admin", namespace=ns.metadata.name),
                "subjects": [{"kind": "ServiceAccount", "name": "agent", "namespace": "default"}],
                "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": "admin"},
            },
            field_manager=FIELD_MANAGER,
            force_conflicts=True,
        )

        rb_res.server_side_apply(
            body={
                "apiVersion": "rbac.authorization.k8s.io/v1",
                "kind": "RoleBinding",
                "metadata": _meta("agent-namespace-access", namespace=ns.metadata.name),
                "subjects": [{"kind": "ServiceAccount", "name": "agent", "namespace": "default"}],
                "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "Role", "name": "agent-namespace-access"},
            },
            field_manager=FIELD_MANAGER,
            force_conflicts=True,
        )

    # Cluster-scoped RBAC
    cr_res.server_side_apply(
        body={
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRole",
            "metadata": _meta("agent-cluster-access"),
            "rules": [
                {"apiGroups": [""], "resources": ["nodes"], "verbs": ["patch"]},
                {"apiGroups": ["scheduling.k8s.io"], "resources": ["priorityclasses"], "verbs": ["create", "delete"]},
            ],
        },
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    )

    crb_res.server_side_apply(
        body={
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "ClusterRoleBinding",
            "metadata": _meta("agent-cluster-access"),
            "subjects": [{"kind": "ServiceAccount", "name": "agent", "namespace": "default"}],
            "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": "agent-cluster-access"},
        },
        field_manager=FIELD_MANAGER,
        force_conflicts=True,
    )


def request_token(core: CoreV1Api) -> str:
    response = core.create_namespaced_service_account_token(
        name="agent",
        namespace="default",
        body=AuthenticationV1TokenRequest(
            spec={"expirationSeconds": TOKEN_EXPIRY_SECONDS}
        ),
    )
    return response.status.token


def build_kubeconfig(source_kubeconfig_path: Path, token: str) -> dict:
    """Read the active context from *source_kubeconfig_path* and return a restricted kubeconfig dict."""
    raw = yaml.safe_load(source_kubeconfig_path.read_text(encoding="utf-8"))
    active_context = raw["current-context"]

    cluster_name = next(
        (ctx["context"]["cluster"] for ctx in raw["contexts"] if ctx["name"] == active_context),
        None,
    )
    if cluster_name is None:
        logger.error("Active context '%s' not found in kubeconfig.", active_context)
        sys.exit(2)

    cluster_entry = next((c for c in raw["clusters"] if c["name"] == cluster_name), None)
    if cluster_entry is None:
        logger.error("Cluster '%s' not found in kubeconfig.", cluster_name)
        sys.exit(2)

    return {
        "apiVersion": "v1",
        "kind": "Config",
        "current-context": cluster_name,
        "clusters": [
            {
                "name": cluster_name,
                "cluster": {
                    "server": cluster_entry["cluster"]["server"],
                    "certificate-authority-data": cluster_entry["cluster"].get("certificate-authority-data", ""),
                },
            }
        ],
        "contexts": [
            {"name": cluster_name, "context": {"cluster": cluster_name, "user": "agent"}}
        ],
        "users": [{"name": "agent", "user": {"token": token}}],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output_path", type=Path, help="Path where the restricted kubeconfig will be written.")
    args = parser.parse_args()

    kubeconfig = os.environ.get("KUBECONFIG")
    if not kubeconfig:
        raise EnvironmentError("KUBECONFIG environment variable is not set.")

    config.load_kube_config()

    core = CoreV1Api()
    dyn_client = dynamic.DynamicClient(ApiClient())

    namespaces = discover_namespaces(core)
    if not namespaces:
        logger.error("No namespaces found with label '%s'.", AGENT_ACCESSIBLE_LABEL)
        sys.exit(1)

    logger.info("Discovered %d namespace(s): %s", len(namespaces), [ns.metadata.name for ns in namespaces])
    apply_all(dyn_client, namespaces)
    logger.info("RBAC applied.")

    token = request_token(core)
    restricted = build_kubeconfig(Path(kubeconfig), token)

    args.output_path.write_text(
        yaml.safe_dump(restricted, default_flow_style=False), encoding="utf-8"
    )
    logger.info("Restricted kubeconfig written to %s.", args.output_path)


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.logging import configure_logging
    configure_logging()
    main()
