"""Tests for itbench.utils.cluster."""

from unittest.mock import MagicMock, patch

import pytest

from itbench.utils.cluster import (
    AGENT_MISSION_LABEL,
    INJECT_NAMESPACE_LABEL_SELECTOR,
    MIN_TOKEN_MINUTES,
    SANDBOX_NODE_TAINT_EFFECT,
    SANDBOX_NODE_TAINT_KEY,
    WORKER_NODE_LABEL_SELECTOR,
    configure_environment,
    create_agent_access,
    delete_events,
    taint_sandbox_nodes,
)


def _make_mock_node(
    name: str,
    labels: dict[str, str] | None = None,
    taints: list[tuple[str, str, str]] | None = None,
) -> MagicMock:
    node = MagicMock()
    node.metadata.name = name
    node.metadata.labels = labels or {}
    mock_taints = []
    for key, value, effect in taints or []:
        taint = MagicMock()
        taint.key = key
        taint.value = value
        taint.effect = effect
        mock_taints.append(taint)
    node.spec.taints = mock_taints or None
    return node


_SANDBOX_TAINT = {"key": SANDBOX_NODE_TAINT_KEY, "value": "true", "effect": SANDBOX_NODE_TAINT_EFFECT}


def _tainted_nodes(count: int) -> tuple[MagicMock, list[MagicMock]]:
    """Return a CoreV1Api mock that lists *count* untainted workers, and those nodes."""
    core_api = MagicMock()
    nodes = [_make_mock_node(f"worker-{i}") for i in range(1, count + 1)]
    core_api.list_node.return_value.items = nodes
    return core_api, nodes


def _patched_taints(core_api: MagicMock) -> dict[str, list[dict[str, str]] | None]:
    return {call.args[0]: call.args[1]["spec"]["taints"] for call in core_api.patch_node.call_args_list}


@pytest.mark.parametrize("node_count", [0, 1])
def test_taint_sandbox_nodes_raises_without_enough_workers(node_count: int) -> None:
    core_api, _ = _tainted_nodes(node_count)

    with patch("itbench.utils.cluster.client.CoreV1Api", return_value=core_api):
        with pytest.raises(RuntimeError, match="Insufficient number of worker nodes detected"):
            taint_sandbox_nodes()

    core_api.list_node.assert_called_once_with(label_selector=WORKER_NODE_LABEL_SELECTOR)
    core_api.patch_node.assert_not_called()


@pytest.mark.parametrize(
    ("node_count", "sandbox_nodes"),
    [
        (2, ["worker-1"]),
        (3, ["worker-1", "worker-2"]),
        (4, ["worker-1", "worker-2"]),
        (6, ["worker-1", "worker-2", "worker-3", "worker-4"]),
    ],
)
def test_taint_sandbox_nodes_partitions_workers(node_count: int, sandbox_nodes: list[str]) -> None:
    core_api, nodes = _tainted_nodes(node_count)

    with patch("itbench.utils.cluster.client.CoreV1Api", return_value=core_api):
        taint_sandbox_nodes()

    patched = _patched_taints(core_api)
    assert set(patched) == {node.metadata.name for node in nodes}
    for name, taints in patched.items():
        assert taints == ([_SANDBOX_TAINT] if name in sandbox_nodes else None)


def test_taint_sandbox_nodes_keeps_foreign_taints_and_removes_stale_sandbox_taint() -> None:
    core_api = MagicMock()
    sandbox = _make_mock_node("worker-1", taints=[("example.com/other", "x", "NoExecute")])
    tool = _make_mock_node("worker-2", taints=[(SANDBOX_NODE_TAINT_KEY, "true", SANDBOX_NODE_TAINT_EFFECT)])
    core_api.list_node.return_value.items = [sandbox, tool]

    with patch("itbench.utils.cluster.client.CoreV1Api", return_value=core_api):
        taint_sandbox_nodes()

    patched = _patched_taints(core_api)
    assert patched["worker-1"] == [{"key": "example.com/other", "value": "x", "effect": "NoExecute"}, _SANDBOX_TAINT]
    assert patched["worker-2"] is None


def test_configure_environment_success() -> None:
    with (
        patch("itbench.utils.cluster.config.load_kube_config") as mock_load_config,
        patch("itbench.utils.cluster.taint_sandbox_nodes") as mock_taint,
    ):
        configure_environment(kubeconfig="/path/to/kubeconfig")

    mock_load_config.assert_called_once_with(config_file="/path/to/kubeconfig")
    mock_taint.assert_called_once()


def test_delete_events_deletes_per_namespace() -> None:
    events_api = MagicMock()
    events = []
    for namespace in ("b", "a", "b"):
        event = MagicMock()
        event.metadata.namespace = namespace
        events.append(event)
    events_api.list_event_for_all_namespaces.return_value.items = events

    with (
        patch("itbench.utils.cluster.config.load_kube_config") as mock_load_config,
        patch("itbench.utils.cluster.client.EventsV1Api", return_value=events_api),
    ):
        count = delete_events(kubeconfig="/path/to/kubeconfig")

    assert count == 2
    mock_load_config.assert_called_once_with(config_file="/path/to/kubeconfig")
    assert [c.args[0] for c in events_api.delete_collection_namespaced_event.call_args_list] == ["a", "b"]


def test_delete_events_without_events() -> None:
    events_api = MagicMock()
    events_api.list_event_for_all_namespaces.return_value.items = []

    with (
        patch("itbench.utils.cluster.config.load_kube_config"),
        patch("itbench.utils.cluster.client.EventsV1Api", return_value=events_api),
    ):
        count = delete_events(kubeconfig="/path/to/kubeconfig")

    assert count == 0
    events_api.delete_collection_namespaced_event.assert_not_called()


def _agent_core_api(service_accounts: list[MagicMock], namespaces: list[str] | None = None) -> MagicMock:
    core_api = MagicMock()
    core_api.list_service_account_for_all_namespaces.return_value.items = service_accounts
    core_api.list_namespace.return_value.items = [MagicMock(**{"metadata.name": name}) for name in namespaces or []]
    core_api.create_namespaced_service_account_token.return_value.status.token = "secret-token"
    core_api.create_namespaced_service_account_token.return_value.status.expiration_timestamp = "2026-01-01T00:00:00Z"
    return core_api


def _agent_service_account() -> MagicMock:
    service_account = MagicMock()
    service_account.metadata.name = "agent-diagnosis"
    service_account.metadata.namespace = "itbench-agents"
    return service_account


def _client_settings(**overrides: object) -> MagicMock:
    settings = MagicMock(host="https://api.example:6443", verify_ssl=True, ssl_ca_cert=None, tls_server_name=None)
    for key, value in overrides.items():
        setattr(settings, key, value)
    return settings


def _create_agent_access(core_api: MagicMock, settings: MagicMock, minutes: int = 15):
    with (
        patch("itbench.utils.cluster.config.load_kube_config") as mock_load_config,
        patch("itbench.utils.cluster.client.Configuration.get_default_copy", return_value=settings),
        patch("itbench.utils.cluster.client.CoreV1Api", return_value=core_api),
    ):
        access = create_agent_access(kubeconfig="/path/to/kubeconfig", mission="diagnosis", minutes=minutes)
    mock_load_config.assert_called_once_with(config_file="/path/to/kubeconfig")
    return access


def test_create_agent_access_requests_token_and_builds_minimal_kubeconfig(tmp_path) -> None:
    ca_file = tmp_path / "ca.crt"
    ca_file.write_bytes(b"CERT")
    core_api = _agent_core_api([_agent_service_account()], ["otel-demo"])

    access = _create_agent_access(core_api, _client_settings(ssl_ca_cert=str(ca_file), tls_server_name="api.internal"))

    core_api.list_service_account_for_all_namespaces.assert_called_once_with(
        label_selector=f"{AGENT_MISSION_LABEL}=diagnosis"
    )
    core_api.list_namespace.assert_called_once_with(label_selector=INJECT_NAMESPACE_LABEL_SELECTOR)
    name, namespace, body = core_api.create_namespaced_service_account_token.call_args.args
    assert (name, namespace) == ("agent-diagnosis", "itbench-agents")
    assert body.spec.expiration_seconds == 15 * 60
    assert body.spec.audiences is None
    assert access.namespaces == ["otel-demo"]
    assert access.expires == "2026-01-01T00:00:00Z"
    assert access.kubeconfig == {
        "apiVersion": "v1",
        "kind": "Config",
        "clusters": [
            {
                "name": "itbench",
                "cluster": {
                    "server": "https://api.example:6443",
                    "certificate-authority-data": "Q0VSVA==",
                    "tls-server-name": "api.internal",
                },
            }
        ],
        "users": [{"name": "itbench-diagnosis", "user": {"token": "secret-token"}}],
        "contexts": [{"name": "itbench-diagnosis", "context": {"cluster": "itbench", "user": "itbench-diagnosis"}}],
        "current-context": "itbench-diagnosis",
    }


def test_create_agent_access_raises_token_lifetime_to_the_api_minimum() -> None:
    core_api = _agent_core_api([_agent_service_account()])

    _create_agent_access(core_api, _client_settings(), minutes=1)

    body = core_api.create_namespaced_service_account_token.call_args.args[2]
    assert body.spec.expiration_seconds == MIN_TOKEN_MINUTES * 60


def test_create_agent_access_skips_tls_verification_when_the_context_does() -> None:
    core_api = _agent_core_api([_agent_service_account()])

    access = _create_agent_access(core_api, _client_settings(verify_ssl=False))

    assert access.kubeconfig["clusters"][0]["cluster"] == {
        "server": "https://api.example:6443",
        "insecure-skip-tls-verify": True,
    }


@pytest.mark.parametrize("count", [0, 2])
def test_create_agent_access_requires_exactly_one_service_account(count: int) -> None:
    core_api = _agent_core_api([_agent_service_account() for _ in range(count)])

    with pytest.raises(RuntimeError, match=f"found {count}"):
        _create_agent_access(core_api, _client_settings())

    core_api.create_namespaced_service_account_token.assert_not_called()
