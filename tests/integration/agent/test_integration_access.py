"""
Integration tests for scripts/agent/grant_access.py and revoke_access.py

Requires a live Kubernetes cluster. Skipped automatically when
KUBECONFIG is not set or the cluster is unreachable.

Run with:
    uv run pytest tests/integration/agent/ -v -m integration
"""
import os
from pathlib import Path

import pytest
import yaml
from kubernetes import client, config, dynamic
from kubernetes.client import ApiClient, CoreV1Api, RbacAuthorizationV1Api
from kubernetes.client.exceptions import ApiException

import grant_access
import revoke_access

pytestmark = pytest.mark.integration

# ---------------------------------------------------------------------------
# Namespaces used by the tests — mirrors the molecule create.yml setup:
#   application  → labelled itbench.io/agent-accessible=true
#   observability → not labelled
# ---------------------------------------------------------------------------
LABELLED_NS = "application"
UNLABELLED_NS = "observability"
LABEL = {grant_access.AGENT_ACCESSIBLE_LABEL.split("=")[0]: grant_access.AGENT_ACCESSIBLE_LABEL.split("=")[1]}


# ---------------------------------------------------------------------------
# Session-scoped skip + cluster setup
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def k8s_clients():
    """Load kubeconfig and return (CoreV1Api, RbacAuthorizationV1Api). Skip if unavailable."""
    if not os.environ.get("KUBECONFIG"):
        pytest.skip("KUBECONFIG is not set.")
    try:
        config.load_kube_config()
        core = CoreV1Api()
        core.list_namespace()  # confirm cluster is reachable
        return core, RbacAuthorizationV1Api()
    except Exception as e:
        pytest.skip(f"Cluster unreachable: {e}")


@pytest.fixture(scope="session")
def cluster_setup(k8s_clients):
    """Create the labelled and unlabelled namespaces once for the session."""
    core, _ = k8s_clients
    for name, labels in [(LABELLED_NS, LABEL), (UNLABELLED_NS, {})]:
        try:
            core.create_namespace(client.V1Namespace(
                metadata=client.V1ObjectMeta(name=name, labels=labels)
            ))
        except ApiException as e:
            if e.status == 409:
                # Already exists — ensure the label state is correct
                core.patch_namespace(name, client.V1Namespace(
                    metadata=client.V1ObjectMeta(labels=labels)
                ))
            else:
                raise
    yield
    for name in (LABELLED_NS, UNLABELLED_NS):
        try:
            core.delete_namespace(name)
        except ApiException as e:
            if e.status != 404:
                raise


# ---------------------------------------------------------------------------
# grant_access integration
# ---------------------------------------------------------------------------

@pytest.fixture()
def grant_output(tmp_path, cluster_setup):
    """Run grant_access.main() and return the path to the written kubeconfig."""
    out = tmp_path / "kubeconfig"
    config.load_kube_config()

    core = CoreV1Api()
    dyn_client = dynamic.DynamicClient(ApiClient())

    namespaces = grant_access.discover_namespaces(core)
    grant_access.apply_all(dyn_client, namespaces)
    token = grant_access.request_token(core)
    restricted = grant_access.build_kubeconfig(Path(kubeconfig), token)
    out.write_text(yaml.safe_dump(restricted, default_flow_style=False), encoding="utf-8")
    return out


def test_grant_kubeconfig_is_written(grant_output):
    """grant_access writes a kubeconfig file to the output path."""
    assert grant_output.exists()
    kc = yaml.safe_load(grant_output.read_text(encoding="utf-8"))
    assert kc["kind"] == "Config"
    assert kc["users"][0]["name"] == "agent"
    assert kc["users"][0]["user"]["token"]


def test_grant_role_created_in_labelled_namespace(k8s_clients, grant_output):
    """grant_access creates the agent Role in the labelled namespace."""
    _, rbac = k8s_clients
    roles = rbac.list_namespaced_role(LABELLED_NS, label_selector=f"app.kubernetes.io/component=access-control")
    assert any(r.metadata.name == "agent-namespace-access" for r in roles.items)


def test_grant_rolebinding_created_in_labelled_namespace(k8s_clients, grant_output):
    """grant_access creates the agent RoleBindings in the labelled namespace."""
    _, rbac = k8s_clients
    rbs = rbac.list_namespaced_role_binding(LABELLED_NS, label_selector=f"app.kubernetes.io/component=access-control")
    names = {rb.metadata.name for rb in rbs.items}
    assert "agent-namespace-admin" in names
    assert "agent-namespace-access" in names


def test_grant_role_not_created_in_unlabelled_namespace(k8s_clients, grant_output):
    """grant_access does not create any Role in the unlabelled namespace."""
    _, rbac = k8s_clients
    roles = rbac.list_namespaced_role(UNLABELLED_NS, label_selector=f"app.kubernetes.io/component=access-control")
    assert roles.items == []


def test_grant_rolebinding_not_created_in_unlabelled_namespace(k8s_clients, grant_output):
    """grant_access does not create any RoleBinding in the unlabelled namespace."""
    _, rbac = k8s_clients
    rbs = rbac.list_namespaced_role_binding(UNLABELLED_NS, label_selector=f"app.kubernetes.io/component=access-control")
    assert rbs.items == []


def test_grant_cluster_role_created(k8s_clients, grant_output):
    """grant_access creates the agent ClusterRole."""
    _, rbac = k8s_clients
    crs = rbac.list_cluster_role(label_selector="app.kubernetes.io/component=access-control")
    assert any(cr.metadata.name == "agent-cluster-access" for cr in crs.items)


def test_grant_cluster_role_binding_created(k8s_clients, grant_output):
    """grant_access creates the agent ClusterRoleBinding."""
    _, rbac = k8s_clients
    crbs = rbac.list_cluster_role_binding(label_selector="app.kubernetes.io/component=access-control")
    assert any(crb.metadata.name == "agent-cluster-access" for crb in crbs.items)


def test_grant_service_account_created(k8s_clients, grant_output):
    """grant_access creates the agent ServiceAccount in the default namespace."""
    core, _ = k8s_clients
    sas = core.list_namespaced_service_account("default", label_selector="app.kubernetes.io/component=access-control")
    assert any(sa.metadata.name == "agent" for sa in sas.items)


# ---------------------------------------------------------------------------
# revoke_access integration — runs after grant, confirms everything is gone
# ---------------------------------------------------------------------------

@pytest.fixture()
def after_revoke(grant_output, k8s_clients):
    """Run revoke_access after grant and return the kubeconfig path for token checks."""
    dyn_client = dynamic.DynamicClient(ApiClient())
    revoke_access.revoke_all(dyn_client)
    return grant_output


def test_revoke_cluster_role_deleted(k8s_clients, after_revoke):
    """revoke_access deletes the agent ClusterRole."""
    _, rbac = k8s_clients
    crs = rbac.list_cluster_role(label_selector="app.kubernetes.io/component=access-control")
    assert crs.items == []


def test_revoke_cluster_role_binding_deleted(k8s_clients, after_revoke):
    """revoke_access deletes the agent ClusterRoleBinding."""
    _, rbac = k8s_clients
    crbs = rbac.list_cluster_role_binding(label_selector="app.kubernetes.io/component=access-control")
    assert crbs.items == []


def test_revoke_roles_deleted_from_labelled_namespace(k8s_clients, after_revoke):
    """revoke_access deletes all Roles from the labelled namespace."""
    _, rbac = k8s_clients
    roles = rbac.list_namespaced_role(LABELLED_NS, label_selector="app.kubernetes.io/component=access-control")
    assert roles.items == []


def test_revoke_rolebindings_deleted_from_labelled_namespace(k8s_clients, after_revoke):
    """revoke_access deletes all RoleBindings from the labelled namespace."""
    _, rbac = k8s_clients
    rbs = rbac.list_namespaced_role_binding(LABELLED_NS, label_selector="app.kubernetes.io/component=access-control")
    assert rbs.items == []


def test_revoke_service_account_deleted(k8s_clients, after_revoke):
    """revoke_access deletes the agent ServiceAccount."""
    core, _ = k8s_clients
    sas = core.list_namespaced_service_account("default", label_selector="app.kubernetes.io/component=access-control")
    assert sas.items == []


def test_revoke_token_no_longer_valid(k8s_clients, after_revoke):
    """revoke_access invalidates the agent token by deleting the ServiceAccount."""
    core, _ = k8s_clients
    kc = yaml.safe_load(after_revoke.read_text(encoding="utf-8"))
    token = kc["users"][0]["user"]["token"]

    review = client.AuthenticationV1Api().create_token_review(
        client.V1TokenReview(spec=client.V1TokenReviewSpec(token=token))
    )
    assert not review.status.authenticated
