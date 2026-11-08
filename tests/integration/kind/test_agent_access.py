"""Integration tests for agent access: restricted kubeconfigs from ``itbench generate kubeconfig``.

The tests run against a cluster with the tools stack deployed (``itbench deploy environment --only tools``),
which provides the agent ServiceAccounts, ClusterRoles and the ValidatingAdmissionPolicy. They create their
own namespaces, deploy the applications role without any application so that it only creates the
RoleBindings (``install_agent_rbac.yaml``), and then use the generated kubeconfigs against the live API server.
"""

import base64
import json
import os
import stat
import time

from collections.abc import Callable, Generator
from pathlib import Path

import pytest
import yaml

from click.testing import CliRunner
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException

from itbench.cli.commands.generate.kubeconfig import generate_kubeconfig_command
from itbench.utils.runner import run_playbook

pytestmark = pytest.mark.integration

AGENTS_NAMESPACE = "itbench-agents"
ALLOWED_NAMESPACE = "itbench-it-agent-allowed"
DENIED_NAMESPACE = "itbench-it-agent-denied"
DRIFT_NAMESPACE = "itbench-it-agent-drift"
MISSIONS = ("diagnosis", "remediation")
ADMISSION_TIMEOUT_SECONDS = 60

# (verb, API group, resource, subresource)
Permission = tuple[str, str, str, str | None]

DIAGNOSIS_ALLOWED: list[Permission] = [
    ("get", "", "pods", None),
    ("list", "", "pods", None),
    ("watch", "", "pods", None),
    ("get", "", "pods", "log"),
    ("list", "", "events", None),
    ("list", "", "configmaps", None),
    ("list", "", "services", None),
    ("list", "", "endpoints", None),
    ("list", "apps", "deployments", None),
    ("list", "apps", "replicasets", None),
    ("list", "batch", "jobs", None),
    ("list", "autoscaling", "horizontalpodautoscalers", None),
    ("list", "networking.k8s.io", "networkpolicies", None),
    ("list", "security.istio.io", "authorizationpolicies", None),
]

# Only remediation may do these.
REMEDIATION_ONLY: list[Permission] = [
    ("create", "", "configmaps", None),
    ("patch", "", "configmaps", None),
    ("delete", "", "configmaps", None),
    ("patch", "", "services", None),
    ("patch", "", "resourcequotas", None),
    ("delete", "", "pods", None),
    ("get", "", "secrets", None),
    ("update", "", "secrets", None),
    ("patch", "apps", "deployments", None),
    ("update", "apps", "deployments", "scale"),
    ("delete", "apps", "daemonsets", None),
    ("delete", "batch", "jobs", None),
    ("create", "networking.k8s.io", "networkpolicies", None),
    ("delete", "networking.k8s.io", "networkpolicies", None),
    ("patch", "security.istio.io", "peerauthentications", None),
]

# Neither mission may do these, which is what stops an agent from escalating.
NEVER_ALLOWED: list[Permission] = [
    ("list", "", "secrets", None),
    ("watch", "", "secrets", None),
    ("create", "", "pods", None),
    ("create", "", "pods", "exec"),
    ("create", "", "pods", "attach"),
    ("create", "", "pods", "portforward"),
    ("create", "", "serviceaccounts", "token"),
    ("create", "rbac.authorization.k8s.io", "roles", None),
    ("create", "rbac.authorization.k8s.io", "rolebindings", None),
    ("list", "rbac.authorization.k8s.io", "rolebindings", None),
    ("create", "apps", "deployments", None),
    ("delete", "apps", "deployments", None),
    ("create", "apps", "daemonsets", None),
    ("create", "batch", "jobs", None),
]

# Cluster-wide checks: a RoleBinding must never leak access outside its own namespace.
CLUSTER_WIDE: list[Permission] = [
    ("list", "", "pods", None),
    ("list", "", "configmaps", None),
    ("list", "", "namespaces", None),
    ("get", "", "namespaces", None),
    ("patch", "", "namespaces", None),
    ("list", "", "nodes", None),
    ("patch", "", "nodes", None),
    ("list", "", "persistentvolumes", None),
    ("delete", "scheduling.k8s.io", "priorityclasses", None),
    ("list", "rbac.authorization.k8s.io", "clusterroles", None),
    ("create", "rbac.authorization.k8s.io", "clusterrolebindings", None),
    ("list", "apiextensions.k8s.io", "customresourcedefinitions", None),
]

ALLOWED = {"diagnosis": DIAGNOSIS_ALLOWED, "remediation": DIAGNOSIS_ALLOWED + REMEDIATION_ONLY}
DENIED = {"diagnosis": REMEDIATION_ONLY + NEVER_ALLOWED, "remediation": NEVER_ALLOWED}


def _cases(permissions: dict[str, list[Permission]]) -> list:
    return [
        pytest.param(mission, permission, id=f"{mission}-{permission[0]}-{'/'.join(filter(None, permission[2:]))}")
        for mission, mission_permissions in permissions.items()
        for permission in mission_permissions
    ]


def _namespace(name: str, *, inject: bool) -> client.V1Namespace:
    labels = {"itbench.io/ansible-role": "applications", "itbench.io/inject": str(inject).lower()}
    return client.V1Namespace(metadata=client.V1ObjectMeta(name=name, labels=labels))


def _create_if_missing(create: Callable[[], object]) -> None:
    try:
        create()
    except ApiException as exc:
        if exc.status != 409:
            raise


def _can(
    api_client: client.ApiClient,
    verb: str,
    resource: str,
    *,
    group: str = "",
    subresource: str | None = None,
    namespace: str | None = None,
) -> bool:
    """Ask the API server whether the user of *api_client* may perform the request."""
    review = client.V1SelfSubjectAccessReview(
        spec=client.V1SelfSubjectAccessReviewSpec(
            resource_attributes=client.V1ResourceAttributes(
                verb=verb, group=group, resource=resource, subresource=subresource, namespace=namespace
            )
        )
    )
    return client.AuthorizationV1Api(api_client).create_self_subject_access_review(review).status.allowed


def _token(kubeconfig_path: Path) -> str:
    return yaml.safe_load(kubeconfig_path.read_text(encoding="utf-8"))["users"][0]["user"]["token"]


def _claims(token: str) -> dict:
    payload = token.split(".")[1]
    return json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))


@pytest.fixture(scope="module")
def admin(kubeconfig: str) -> client.ApiClient:
    return config.new_client_from_config(config_file=kubeconfig)


@pytest.fixture(scope="module")
def agent_environment(
    kubeconfig: str, admin: client.ApiClient, tmp_path_factory: pytest.TempPathFactory
) -> Generator[None]:
    """Create the test namespaces and let the applications role bind the agents in the injectable ones."""
    core_api = client.CoreV1Api(admin)

    service_accounts = core_api.list_service_account_for_all_namespaces(label_selector="itbench.io/agent-mission").items
    found = {service_account.metadata.name for service_account in service_accounts}
    assert {"agent-diagnosis", "agent-remediation"} <= found, (
        "Agent ServiceAccounts not found, deploy the tools first (`itbench deploy environment --only tools`)."
    )

    namespaces = {ALLOWED_NAMESPACE: True, DRIFT_NAMESPACE: True, DENIED_NAMESPACE: False}
    try:
        for name, inject in namespaces.items():
            _create_if_missing(
                lambda name=name, inject=inject: core_api.create_namespace(_namespace(name, inject=inject))
            )
            _create_if_missing(
                lambda name=name: core_api.create_namespaced_config_map(
                    name, client.V1ConfigMap(metadata=client.V1ObjectMeta(name="seed"), data={"phase": "seed"})
                )
            )
        _create_if_missing(
            lambda: core_api.create_namespaced_secret(
                ALLOWED_NAMESPACE,
                client.V1Secret(metadata=client.V1ObjectMeta(name="seed"), string_data={"password": "seed"}), # pragma: allowlist secret
            )
        )

        # The applications role binds the agents in every injectable application namespace. With both
        # applications disabled that is all it does, so this stays quick.
        kubeconfig_path = os.path.abspath(kubeconfig)
        with pytest.MonkeyPatch.context() as patch:
            patch.chdir(tmp_path_factory.mktemp("runs"))
            run_playbook(
                playbook="manage_environment.yaml",
                extra_vars={
                    "environment_tool_management_enabled": False,
                    "environment_application_management_enabled": True,
                    "environment_recorder_management_enabled": False,
                    "applications_opentelemetry_demo_enabled": False,
                },
                tags=["install"],
                kubeconfig=kubeconfig_path,
            )

        yield
    finally:
        for name in namespaces:
            try:
                core_api.delete_namespace(name)
            except ApiException as exc:
                if exc.status != 404:
                    raise


@pytest.fixture(scope="module")
def kubeconfig_files(
    agent_environment: None, kubeconfig: str, tmp_path_factory: pytest.TempPathFactory
) -> dict[str, Path]:
    """Generate one restricted kubeconfig per mission with the CLI, as a user would."""
    files = {}
    for mission in MISSIONS:
        directory = tmp_path_factory.mktemp(mission)
        result = CliRunner().invoke(
            generate_kubeconfig_command,
            ["--mission", mission, "--output", str(directory), "--kubeconfig", kubeconfig],
            catch_exceptions=False,
        )
        assert result.exit_code == 0, result.output
        files[mission] = directory / f"kubeconfig-{mission}"
    return files


@pytest.fixture(scope="module")
def agents(kubeconfig_files: dict[str, Path]) -> dict[str, client.ApiClient]:
    return {mission: config.new_client_from_config(config_file=str(path)) for mission, path in kubeconfig_files.items()}


@pytest.mark.parametrize("mission", MISSIONS)
def test_kubeconfig_only_holds_the_agent_token(
    mission: str, kubeconfig_files: dict[str, Path], agents: dict[str, client.ApiClient]
) -> None:
    path = kubeconfig_files[mission]
    content = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert stat.S_IMODE(path.stat().st_mode) == 0o600
    assert len(content["clusters"]) == len(content["users"]) == len(content["contexts"]) == 1
    assert set(content["users"][0]["user"]) == {"token"}

    review = client.AuthenticationV1Api(agents[mission]).create_self_subject_review(client.V1SelfSubjectReview())
    assert review.status.user_info.username == f"system:serviceaccount:{AGENTS_NAMESPACE}:agent-{mission}"


def test_token_lives_for_the_default_duration(kubeconfig_files: dict[str, Path]) -> None:
    claims = _claims(_token(kubeconfig_files["diagnosis"]))

    assert claims["exp"] - claims["iat"] == 15 * 60


@pytest.mark.parametrize(("mission", "permission"), _cases(ALLOWED))
def test_agent_is_allowed_in_injectable_namespaces(
    mission: str, permission: Permission, agents: dict[str, client.ApiClient]
) -> None:
    verb, group, resource, subresource = permission

    assert _can(agents[mission], verb, resource, group=group, subresource=subresource, namespace=ALLOWED_NAMESPACE), (
        f"{mission} should be able to {verb} {resource}"
    )


@pytest.mark.parametrize(("mission", "permission"), _cases(DENIED))
def test_agent_is_denied_what_it_does_not_need(
    mission: str, permission: Permission, agents: dict[str, client.ApiClient]
) -> None:
    verb, group, resource, subresource = permission

    assert not _can(
        agents[mission], verb, resource, group=group, subresource=subresource, namespace=ALLOWED_NAMESPACE
    ), f"{mission} should not be able to {verb} {resource}"


@pytest.mark.parametrize("mission", MISSIONS)
@pytest.mark.parametrize("namespace", [DENIED_NAMESPACE, AGENTS_NAMESPACE, "kube-system", "default"])
def test_agent_has_no_access_outside_injectable_namespaces(
    mission: str, namespace: str, agents: dict[str, client.ApiClient]
) -> None:
    for verb, resource in (("list", "pods"), ("list", "configmaps"), ("get", "secrets"), ("patch", "configmaps")):
        assert not _can(agents[mission], verb, resource, namespace=namespace), f"{mission} can {verb} {resource}"


@pytest.mark.parametrize(("mission", "permission"), [(m, p) for m in MISSIONS for p in CLUSTER_WIDE])
def test_agent_has_no_cluster_wide_access(
    mission: str, permission: Permission, agents: dict[str, client.ApiClient]
) -> None:
    verb, group, resource, subresource = permission

    assert not _can(agents[mission], verb, resource, group=group, subresource=subresource)


def test_diagnosis_reads_but_cannot_write(agents: dict[str, client.ApiClient]) -> None:
    core_api = client.CoreV1Api(agents["diagnosis"])

    assert "seed" in [item.metadata.name for item in core_api.list_namespaced_config_map(ALLOWED_NAMESPACE).items]
    with pytest.raises(ApiException) as exc_info:
        core_api.patch_namespaced_config_map("seed", ALLOWED_NAMESPACE, {"data": {"phase": "changed"}})
    assert exc_info.value.status == 403
    with pytest.raises(ApiException) as exc_info:
        core_api.list_namespaced_config_map(DENIED_NAMESPACE)
    assert exc_info.value.status == 403
    with pytest.raises(ApiException) as exc_info:
        core_api.list_namespace()
    assert exc_info.value.status == 403


def test_remediation_changes_objects_but_cannot_enumerate_secrets(agents: dict[str, client.ApiClient]) -> None:
    core_api = client.CoreV1Api(agents["remediation"])

    patched = core_api.patch_namespaced_config_map("seed", ALLOWED_NAMESPACE, {"data": {"phase": "remediated"}})
    assert patched.data["phase"] == "remediated"
    assert core_api.read_namespaced_secret("seed", ALLOWED_NAMESPACE).metadata.name == "seed"
    with pytest.raises(ApiException) as exc_info:
        core_api.list_namespaced_secret(ALLOWED_NAMESPACE)
    assert exc_info.value.status == 403
    with pytest.raises(ApiException) as exc_info:
        client.RbacAuthorizationV1Api(agents["remediation"]).create_namespaced_role_binding(
            ALLOWED_NAMESPACE,
            client.V1RoleBinding(
                metadata=client.V1ObjectMeta(name="escalate"),
                role_ref=client.V1RoleRef(
                    api_group="rbac.authorization.k8s.io", kind="ClusterRole", name="cluster-admin"
                ),
            ),
        )
    assert exc_info.value.status == 403


def test_agents_are_only_bound_in_injectable_namespaces(admin: client.ApiClient, agent_environment: None) -> None:
    bindings = (
        client.RbacAuthorizationV1Api(admin)
        .list_role_binding_for_all_namespaces(label_selector="itbench.io/agent-mission")
        .items
    )
    bound = {}
    for binding in bindings:
        bound.setdefault(binding.metadata.namespace, []).append(binding)

    assert ALLOWED_NAMESPACE in bound
    assert DENIED_NAMESPACE not in bound
    assert AGENTS_NAMESPACE not in bound
    assert sorted(binding.role_ref.name for binding in bound[ALLOWED_NAMESPACE]) == [
        "agent-diagnosis",
        "agent-remediation",
    ]
    for binding in bound[ALLOWED_NAMESPACE]:
        assert binding.role_ref.kind == "ClusterRole"
        assert [(s.kind, s.namespace) for s in binding.subjects] == [("ServiceAccount", AGENTS_NAMESPACE)]


def test_agents_have_no_cluster_role_bindings(admin: client.ApiClient, agent_environment: None) -> None:
    bindings = client.RbacAuthorizationV1Api(admin).list_cluster_role_binding().items

    assert [
        binding.metadata.name
        for binding in bindings
        for subject in binding.subjects or []
        if subject.kind == "ServiceAccount" and subject.namespace == AGENTS_NAMESPACE
    ] == []


def test_admission_policy_blocks_writes_once_the_inject_label_is_removed(
    admin: client.ApiClient, agents: dict[str, client.ApiClient]
) -> None:
    """RoleBindings outlive the label, so the policy is what stops a drifted namespace."""
    agent_core_api = client.CoreV1Api(agents["remediation"])
    agent_core_api.patch_namespaced_config_map("seed", DRIFT_NAMESPACE, {"data": {"phase": "labeled"}})

    client.CoreV1Api(admin).patch_namespace(DRIFT_NAMESPACE, {"metadata": {"labels": {"itbench.io/inject": "false"}}})

    deadline = time.monotonic() + ADMISSION_TIMEOUT_SECONDS
    while True:
        try:
            agent_core_api.patch_namespaced_config_map("seed", DRIFT_NAMESPACE, {"data": {"phase": "unlabeled"}})
        except ApiException as exc:
            # RBAC still allows the write, so this refusal can only come from the admission policy.
            assert exc.status == 403
            assert "itbench.io/inject=true" in str(exc.body)
            break
        assert time.monotonic() < deadline, "The admission policy never blocked the write."
        time.sleep(2)

    # Reads are not covered by the policy, so diagnosis style access keeps working.
    assert agent_core_api.read_namespaced_config_map("seed", DRIFT_NAMESPACE).metadata.name == "seed"
