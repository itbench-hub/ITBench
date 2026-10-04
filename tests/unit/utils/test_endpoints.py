"""Tests for itbench.utils.endpoints."""

from unittest.mock import MagicMock, patch

import pytest

from itbench.utils.endpoints import (
    ToolEndpoint,
    _build_tool_definitions,
    _resolve_gateway_host,
    _resolve_k8s_endpoints,
    _resolve_ocp_endpoints,
)


# ---------------------------------------------------------------------------
# Minimal releases fixture that satisfies _build_tool_definitions
# ---------------------------------------------------------------------------

_RELEASES: dict = {
    "tools_releases": {
        "kube_prometheus_stack": {
            "name": "prometheus",
            "namespace": {"kubernetes": "monitoring"},
        },
        "opencost": {"name": "opencost", "namespace": "opencost"},
        "kubernetes_topology_monitor": {
            "name": "ktm",
            "namespace": "ktm-ns",
        },
    },
    "tools_operands": {
        "opentelemetry_collector": {
            "jaeger": {"name": "jaeger"},
        },
        "alinity_clickhouse": {
            "main": {"name": "clickhouse"},
        },
    },
    "tools_namespaces": {
        "opentelemetry_collector": "otel-ns",
        "alinity_clickhouse": "ch-ns",
        "kubernetes_gateway": "gw-ns",
    },
    "tools_kubernetes_gateways": {
        "istio": {"name": "istio-gw"},
    },
}


def test_tool_endpoint_urls_with_paths() -> None:
    ep = ToolEndpoint(tool="Prometheus", host="http://1.2.3.4", paths=["/alerts", "/query"])
    assert ep.urls == ["http://1.2.3.4/alerts", "http://1.2.3.4/query"]


def test_tool_endpoint_urls_strips_trailing_slash_from_host() -> None:
    ep = ToolEndpoint(tool="T", host="http://1.2.3.4/", paths=["/path"])
    assert ep.urls == ["http://1.2.3.4/path"]


def test_tool_endpoint_urls_falls_back_to_host_when_no_paths() -> None:
    ep = ToolEndpoint(tool="T", host="http://host.example.com")
    assert ep.urls == ["http://host.example.com"]


def test_tool_endpoint_urls_empty_paths_list_falls_back_to_host() -> None:
    ep = ToolEndpoint(tool="T", host="http://host.example.com", paths=[])
    assert ep.urls == ["http://host.example.com"]


def test_build_tool_definitions_returns_expected_keys() -> None:
    tools = _build_tool_definitions(_RELEASES)
    assert set(tools.keys()) == {
        "Prometheus",
        "Jaeger",
        "ClickHouse",
        "OpenCost",
        "Kubernetes Topology Monitor",
    }


def test_build_tool_definitions_prometheus_k8s_ref() -> None:
    tools = _build_tool_definitions(_RELEASES)
    assert tools["Prometheus"]["k8s"]["name"] == "prometheus"
    assert tools["Prometheus"]["k8s"]["namespace"] == "monitoring"


def test_build_tool_definitions_prometheus_ocp_ref() -> None:
    tools = _build_tool_definitions(_RELEASES)
    assert tools["Prometheus"]["ocp"]["name"] == "prometheus-k8s"
    assert tools["Prometheus"]["ocp"]["namespace"] == "openshift-monitoring"


def test_build_tool_definitions_all_tools_have_paths() -> None:
    tools = _build_tool_definitions(_RELEASES)
    for name, cfg in tools.items():
        assert isinstance(cfg["paths"], list), f"{name} missing paths"
        assert len(cfg["paths"]) > 0, f"{name} has empty paths"


def test_resolve_gateway_host_ip_address() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {
        "status": {"addresses": [{"type": "IPAddress", "value": "10.0.0.1"}]}
    }
    host = _resolve_gateway_host(custom, name="gw", namespace="ns")
    assert host == "http://10.0.0.1:80"


def test_resolve_gateway_host_hostname() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {
        "status": {"addresses": [{"type": "Hostname", "value": "gw.example.com"}]}
    }
    host = _resolve_gateway_host(custom, name="gw", namespace="ns")
    assert host == "http://gw.example.com"


def test_resolve_gateway_host_raises_when_no_addresses() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {"status": {"addresses": []}}

    with pytest.raises(RuntimeError, match="no addresses"):
        _resolve_gateway_host(custom, name="gw", namespace="ns")


def test_resolve_gateway_host_raises_when_status_missing() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {}

    with pytest.raises(RuntimeError):
        _resolve_gateway_host(custom, name="gw", namespace="ns")


def _api_exception(status: int) -> Exception:
    from kubernetes import client

    exc = client.exceptions.ApiException(status=status)
    exc.status = status
    return exc


def test_resolve_k8s_endpoints_returns_endpoint_for_found_route() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {
        "spec": {
            "rules": [{"matches": [{"path": {"value": "/prometheus"}}]}]
        }
    }
    tools = {
        "Prometheus": {
            "k8s": {"name": "prometheus", "namespace": "monitoring"},
            "paths": ["/alerts"],
        }
    }
    results = _resolve_k8s_endpoints(custom, "http://1.2.3.4", tools)

    assert len(results) == 1
    assert results[0].tool == "Prometheus"
    assert results[0].host == "http://1.2.3.4/prometheus"


def test_resolve_k8s_endpoints_skips_404() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.side_effect = _api_exception(404)
    tools = {
        "Prometheus": {
            "k8s": {"name": "prometheus", "namespace": "monitoring"},
            "paths": ["/alerts"],
        }
    }
    results = _resolve_k8s_endpoints(custom, "http://1.2.3.4", tools)
    assert results == []


def test_resolve_k8s_endpoints_reraises_non_404() -> None:
    from kubernetes import client

    custom = MagicMock()
    custom.get_namespaced_custom_object.side_effect = _api_exception(500)
    tools = {
        "Prometheus": {
            "k8s": {"name": "prometheus", "namespace": "monitoring"},
            "paths": ["/alerts"],
        }
    }
    with pytest.raises(client.exceptions.ApiException):
        _resolve_k8s_endpoints(custom, "http://1.2.3.4", tools)


def test_resolve_k8s_endpoints_path_prefix_stripped_of_trailing_slash() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {
        "spec": {"rules": [{"matches": [{"path": {"value": "/prom/"}}]}]}
    }
    tools = {"T": {"k8s": {"name": "t", "namespace": "ns"}, "paths": ["/"]}}
    results = _resolve_k8s_endpoints(custom, "http://gw", tools)
    assert results[0].host == "http://gw/prom"


def test_resolve_ocp_endpoints_returns_endpoint_for_found_route() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {
        "status": {"ingress": [{"host": "prometheus.apps.example.com"}]},
        "spec": {"path": "/"},
    }
    tools = {
        "Prometheus": {
            "ocp": {"name": "prometheus-k8s", "namespace": "openshift-monitoring"},
            "paths": ["/alerts"],
        }
    }
    results = _resolve_ocp_endpoints(custom, tools)

    assert len(results) == 1
    assert results[0].host == "http://prometheus.apps.example.com"


def test_resolve_ocp_endpoints_skips_404() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.side_effect = _api_exception(404)
    tools = {
        "Prometheus": {
            "ocp": {"name": "prometheus-k8s", "namespace": "openshift-monitoring"},
            "paths": ["/alerts"],
        }
    }
    results = _resolve_ocp_endpoints(custom, tools)
    assert results == []


def test_resolve_ocp_endpoints_skips_route_with_no_ingress() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {"status": {"ingress": []}}
    tools = {
        "Prometheus": {
            "ocp": {"name": "prometheus-k8s", "namespace": "openshift-monitoring"},
            "paths": ["/alerts"],
        }
    }
    results = _resolve_ocp_endpoints(custom, tools)
    assert results == []


def test_resolve_ocp_endpoints_reraises_non_404() -> None:
    from kubernetes import client

    custom = MagicMock()
    custom.get_namespaced_custom_object.side_effect = _api_exception(503)
    tools = {
        "Prometheus": {
            "ocp": {"name": "prometheus-k8s", "namespace": "openshift-monitoring"},
            "paths": ["/alerts"],
        }
    }
    with pytest.raises(client.exceptions.ApiException):
        _resolve_ocp_endpoints(custom, tools)


def test_resolve_ocp_endpoints_includes_route_path_in_host() -> None:
    custom = MagicMock()
    custom.get_namespaced_custom_object.return_value = {
        "status": {"ingress": [{"host": "apps.example.com"}]},
        "spec": {"path": "/prometheus"},
    }
    tools = {"T": {"ocp": {"name": "t", "namespace": "ns"}, "paths": ["/"]}}
    results = _resolve_ocp_endpoints(custom, tools)
    assert results[0].host == "http://apps.example.com/prometheus"
