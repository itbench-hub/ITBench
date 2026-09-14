"""Scenario access control operations (Kubernetes RBAC, service accounts, and token management)."""
import logging

from pathlib import Path
from typing import Any

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


def discover_namespaces(core: CoreV1Api) -> list[Any]:
    """Return all namespaces labelled ``itbench.io/agent-accessible=true``."""
    return core.list_namespace(label_selector=AGENT_ACCESSIBLE_LABEL).items


def create_service_account(dyn_client: dynamic.DynamicClient, name: str, namespace: str) -> None:
    sa_res = dyn_client.resources.get(api_version="v1", kind="ServiceAccount")
    sa_body = {
        "apiVersion": "v1",
        "kind": "ServiceAccount",
        "metadata": {"name": name, "namespace": namespace, "labels": LABELS},
    }
    sa_res.server_side_apply(
        name=name,
        namespace=namespace,
        body=sa_body,
        field_manager=FIELD_MANAGER,
        force=True,
    )
    logger.debug("ServiceAccount %s/%s applied.", namespace, name)


def create_role_and_binding(dyn_client: dynamic.DynamicClient, name: str, namespace: str) -> None:
    role_name = f"{name}-namespace-access"
    role_res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="Role")
    role_body = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "Role",
        "metadata": {"name": role_name, "namespace": namespace, "labels": LABELS},
        "rules": [{"apiGroups": ["*"], "resources": ["*"], "verbs": ["*"]}],
    }
    role_res.server_side_apply(
        name=role_name,
        namespace=namespace,
        body=role_body,
        field_manager=FIELD_MANAGER,
        force=True,
    )
    logger.debug("Role %s/%s applied.", namespace, role_name)

    rb_res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="RoleBinding")
    for binding_suffix, ref_kind, ref_name in [
        ("admin", "ClusterRole", "admin"),
        ("access", "Role", role_name),
    ]:
        binding_name = f"{name}-namespace-{binding_suffix}"
        rb_body = {
            "apiVersion": "rbac.authorization.k8s.io/v1",
            "kind": "RoleBinding",
            "metadata": {"name": binding_name, "namespace": namespace, "labels": LABELS},
            "subjects": [{"kind": "ServiceAccount", "name": name, "namespace": "default"}],
            "roleRef": {
                "apiGroup": "rbac.authorization.k8s.io",
                "kind": ref_kind,
                "name": ref_name,
            },
        }
        rb_res.server_side_apply(
            name=binding_name,
            namespace=namespace,
            body=rb_body,
            field_manager=FIELD_MANAGER,
            force=True,
        )
        logger.debug("RoleBinding %s/%s applied.", namespace, binding_name)


def request_token(core: CoreV1Api, name: str, namespace: str) -> str:
    body = AuthenticationV1TokenRequest(
        spec={"expirationSeconds": TOKEN_EXPIRY_SECONDS}
    )
    resp = core.create_namespaced_service_account_token(
        name=name, namespace=namespace, body=body
    )
    return resp.status.token


def build_restricted_kubeconfig(
    cluster_name: str,
    server: str,
    ca_data: str | None,
    user_name: str,
    token: str,
    default_namespace: str,
) -> dict:
    cluster_entry: dict = {"server": server}
    if ca_data:
        cluster_entry["certificate-authority-data"] = ca_data
    else:
        cluster_entry["insecure-skip-tls-verify"] = True

    return {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [{"name": cluster_name, "cluster": cluster_entry}],
        "users": [{"name": user_name, "user": {"token": token}}],
        "contexts": [
            {
                "name": "agent-context",
                "context": {
                    "cluster": cluster_name,
                    "user": user_name,
                    "namespace": default_namespace,
                },
            }
        ],
        "current-context": "agent-context",
    }


def create_cluster_role_and_binding(dyn_client: dynamic.DynamicClient, name: str = "agent") -> None:
    cr_res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="ClusterRole")
    cr_body = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRole",
        "metadata": {"name": f"{name}-cluster-access", "labels": LABELS},
        "rules": [
            {"apiGroups": [""], "resources": ["namespaces", "nodes"], "verbs": ["get", "list", "watch"]}
        ],
    }
    cr_res.server_side_apply(
        name=f"{name}-cluster-access",
        body=cr_body,
        field_manager=FIELD_MANAGER,
        force=True,
    )
    logger.debug("ClusterRole %s-cluster-access applied.", name)

    crb_res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="ClusterRoleBinding")
    crb_body = {
        "apiVersion": "rbac.authorization.k8s.io/v1",
        "kind": "ClusterRoleBinding",
        "metadata": {"name": f"{name}-cluster-access", "labels": LABELS},
        "subjects": [{"kind": "ServiceAccount", "name": name, "namespace": "default"}],
        "roleRef": {
            "apiGroup": "rbac.authorization.k8s.io",
            "kind": "ClusterRole",
            "name": f"{name}-cluster-access",
        },
    }
    crb_res.server_side_apply(
        name=f"{name}-cluster-access",
        body=crb_body,
        field_manager=FIELD_MANAGER,
        force=True,
    )
    logger.debug("ClusterRoleBinding %s-cluster-access applied.", name)


def grant_agent_access(
    output_path: Path,
    source_kubeconfig_path: Path | None = None,
    service_account_name: str = "agent",
) -> None:
    """Grant agent access to accessible namespaces and write restricted kubeconfig."""
    if source_kubeconfig_path:
        config.load_kube_config(config_file=str(source_kubeconfig_path))
    else:
        config.load_kube_config()

    core = CoreV1Api()
    dyn_client = dynamic.DynamicClient(ApiClient())

    # Create primary service account in default namespace
    create_service_account(dyn_client, service_account_name, "default")
    create_cluster_role_and_binding(dyn_client, service_account_name)

    namespaces = discover_namespaces(core)
    if not namespaces:
        logger.warning("No namespaces found with label %s.", AGENT_ACCESSIBLE_LABEL)
        return

    primary_ns = namespaces[0].metadata.name
    for ns in namespaces:
        ns_name = ns.metadata.name
        create_role_and_binding(dyn_client, service_account_name, ns_name)

    token = request_token(core, service_account_name, "default")

    # Read current kubeconfig for cluster metadata
    raw = {}
    if source_kubeconfig_path and source_kubeconfig_path.exists():
        raw = yaml.safe_load(source_kubeconfig_path.read_text(encoding="utf-8"))

    current_ctx_name = raw.get("current-context", "default")
    cluster_entry = raw.get("clusters", [{}])[0].get("cluster", {})
    server = cluster_entry.get("server", "https://kubernetes.default.svc")
    ca_data = cluster_entry.get("certificate-authority-data")

    restricted = build_restricted_kubeconfig(
        cluster_name=current_ctx_name,
        server=server,
        ca_data=ca_data,
        user_name=service_account_name,
        token=token,
        default_namespace=primary_ns,
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(yaml.safe_dump(restricted, default_flow_style=False), encoding="utf-8")
    logger.info("Restricted kubeconfig written to %s.", output_path)


def revoke_agent_access(service_account_name: str = "agent", source_kubeconfig_path: Path | None = None) -> None:
    """Revoke agent RBAC resources from all namespaces."""
    if source_kubeconfig_path:
        config.load_kube_config(config_file=str(source_kubeconfig_path))
    else:
        config.load_kube_config()

    core = CoreV1Api()
    dyn_client = dynamic.DynamicClient(ApiClient())

    # 1. Delete cluster-scoped RBAC resources (ClusterRoleBinding, ClusterRole)
    for kind in ("ClusterRoleBinding", "ClusterRole"):
        res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind=kind)
        target_name = f"{service_account_name}-cluster-access"
        try:
            res.delete(name=target_name)
            logger.info("Deleted %s %s", kind, target_name)
        except Exception as e:
            logger.debug("Could not delete %s %s: %s", kind, target_name, e)

    # 2. Delete namespace-scoped RBAC resources across all agent-accessible namespaces
    namespaces = discover_namespaces(core)
    rb_res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="RoleBinding")
    role_res = dyn_client.resources.get(api_version="rbac.authorization.k8s.io/v1", kind="Role")

    for ns in namespaces:
        ns_name = ns.metadata.name
        for binding_suffix in ("admin", "access"):
            binding_name = f"{service_account_name}-namespace-{binding_suffix}"
            try:
                rb_res.delete(name=binding_name, namespace=ns_name)
                logger.info("Deleted RoleBinding %s/%s", ns_name, binding_name)
            except Exception as e:
                logger.debug("Could not delete RoleBinding %s/%s: %s", ns_name, binding_name, e)

        role_name = f"{service_account_name}-namespace-access"
        try:
            role_res.delete(name=role_name, namespace=ns_name)
            logger.info("Deleted Role %s/%s", ns_name, role_name)
        except Exception as e:
            logger.debug("Could not delete Role %s/%s: %s", ns_name, role_name, e)

    # 3. Delete primary ServiceAccount in default namespace
    sa_res = dyn_client.resources.get(api_version="v1", kind="ServiceAccount")
    try:
        sa_res.delete(name=service_account_name, namespace="default")
        logger.info("Deleted ServiceAccount default/%s", service_account_name)
    except Exception as e:
        logger.debug("Could not delete ServiceAccount default/%s: %s", service_account_name, e)

    logger.info("Revocation complete.")
