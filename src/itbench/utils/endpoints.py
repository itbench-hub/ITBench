"""Endpoint discovery utilities for ITBench tools stack.

Resolves external URLs for each installed tool by querying the Kubernetes API
directly — replacing the Ansible ``set_external_endpoints`` task family.

Supports both Kubernetes (HTTPRoute via Istio Gateway) and OpenShift (Route).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kubernetes import client, config  # type: ignore[import-untyped]


_RELEASES_FILE = (
    Path(__file__).parents[3]
    / "scenarios"
    / "sre"
    / "project"
    / "roles"
    / "tools"
    / "vars"
    / "main"
    / "releases.yaml"
)


def _load_releases() -> dict[str, Any]:
    """Load the tools role releases vars."""
    with _RELEASES_FILE.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


@dataclass
class ToolEndpoint:
    """Resolved external endpoint for a single tool."""

    tool: str
    host: str
    paths: list[str] = field(default_factory=list)

    @property
    def urls(self) -> list[str]:
        """Return fully qualified URLs for each path."""
        if not self.paths:
            return [self.host]
        return [f"{self.host.rstrip('/')}{p}" for p in self.paths]


def _build_tool_definitions(releases: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build tool lookup table from releases vars.

    Returns a dict keyed by human-readable tool name, each with:
      - ``k8s``: ``{name, namespace}`` for HTTPRoute lookup
      - ``ocp``: ``{name, namespace}`` for Route lookup
      - ``paths``: list of significant URL paths
    """
    r = releases["tools_releases"]
    operands = releases["tools_operands"]
    namespaces = releases["tools_namespaces"]

    return {
        "Prometheus": {
            "k8s": {
                "name": r["kube_prometheus_stack"]["name"],
                "namespace": r["kube_prometheus_stack"]["namespace"]["kubernetes"],
            },
            "ocp": {
                "name": "prometheus-k8s",
                "namespace": "openshift-monitoring",
            },
            "paths": ["/alerts", "/query"],
        },
        "Jaeger": {
            "k8s": {
                "name": operands["opentelemetry_collector"]["jaeger"]["name"],
                "namespace": namespaces["opentelemetry_collector"],
            },
            "ocp": {
                "name": operands["opentelemetry_collector"]["jaeger"]["name"],
                "namespace": namespaces["opentelemetry_collector"],
            },
            "paths": ["/"],
        },
        "ClickHouse": {
            "k8s": {
                "name": operands["alinity_clickhouse"]["main"]["name"],
                "namespace": namespaces["alinity_clickhouse"],
            },
            "ocp": {
                "name": operands["alinity_clickhouse"]["main"]["name"],
                "namespace": namespaces["alinity_clickhouse"],
            },
            "paths": ["/play"],
        },
        "OpenCost": {
            "k8s": {
                "name": r["opencost"]["name"],
                "namespace": r["opencost"]["namespace"],
            },
            "ocp": {
                "name": r["opencost"]["name"],
                "namespace": r["opencost"]["namespace"],
            },
            "paths": ["/"],
        },
        "Kubernetes Topology Monitor": {
            "k8s": {
                "name": r["kubernetes_topology_monitor"]["name"],
                "namespace": r["kubernetes_topology_monitor"]["namespace"],
            },
            "ocp": {
                "name": r["kubernetes_topology_monitor"]["name"],
                "namespace": r["kubernetes_topology_monitor"]["namespace"],
            },
            "paths": ["/healthz"],
        },
    }


def discover_endpoints(kubeconfig: str, platform: str) -> list[ToolEndpoint]:
    """Resolve external endpoints for all installed tools.

    Args:
        kubeconfig: Path to the kubeconfig file.
        platform: Either ``"kubernetes"`` or ``"openshift"``.

    Returns:
        List of :class:`ToolEndpoint` for each tool that was found.
        Tools whose routes/HTTPRoutes are not present are silently skipped.
    """
    releases = _load_releases()
    tools = _build_tool_definitions(releases)
    gateways = releases["tools_kubernetes_gateways"]

    config.load_kube_config(config_file=kubeconfig)
    custom = client.CustomObjectsApi()

    if platform == "kubernetes":
        gateway_host = _resolve_gateway_host(
            custom,
            name=gateways["istio"]["name"],
            namespace=releases["tools_namespaces"]["kubernetes_gateway"],
        )
        return _resolve_k8s_endpoints(custom, gateway_host, tools)
    return _resolve_ocp_endpoints(custom, tools)


def _resolve_gateway_host(
    custom: client.CustomObjectsApi,
    name: str,
    namespace: str,
) -> str:
    """Return the base HTTP address of the Istio-managed Gateway."""
    gw = custom.get_namespaced_custom_object(
        group="gateway.networking.k8s.io",
        version="v1",
        namespace=namespace,
        plural="gateways",
        name=name,
    )
    addresses = gw.get("status", {}).get("addresses", [])
    if not addresses:
        raise RuntimeError(
            f"Gateway '{name}' in namespace '{namespace}' has no addresses. "
            "Ensure the tools stack is fully deployed."
        )
    addr = addresses[0]
    suffix = ":80" if addr.get("type") == "IPAddress" else ""
    return f"http://{addr['value']}{suffix}"


def _resolve_k8s_endpoints(
    custom: client.CustomObjectsApi,
    gateway_host: str,
    tools: dict[str, dict[str, Any]],
) -> list[ToolEndpoint]:
    """Resolve endpoints via HTTPRoute resources (Kubernetes platform)."""
    endpoints: list[ToolEndpoint] = []

    for tool_name, cfg in tools.items():
        ref = cfg["k8s"]
        try:
            route = custom.get_namespaced_custom_object(
                group="gateway.networking.k8s.io",
                version="v1",
                namespace=ref["namespace"],
                plural="httproutes",
                name=ref["name"],
            )
        except client.exceptions.ApiException as exc:
            if exc.status == 404:
                continue
            raise

        path_prefix = (
            route.get("spec", {})
            .get("rules", [{}])[0]
            .get("matches", [{}])[0]
            .get("path", {})
            .get("value", "")
            .rstrip("/")
        )
        host = f"{gateway_host}{path_prefix}"
        endpoints.append(ToolEndpoint(tool=tool_name, host=host, paths=cfg["paths"]))

    return endpoints


def _resolve_ocp_endpoints(
    custom: client.CustomObjectsApi,
    tools: dict[str, dict[str, Any]],
) -> list[ToolEndpoint]:
    """Resolve endpoints via OpenShift Route resources."""
    endpoints: list[ToolEndpoint] = []

    for tool_name, cfg in tools.items():
        ref = cfg["ocp"]
        try:
            route = custom.get_namespaced_custom_object(
                group="route.openshift.io",
                version="v1",
                namespace=ref["namespace"],
                plural="routes",
                name=ref["name"],
            )
        except client.exceptions.ApiException as exc:
            if exc.status == 404:
                continue
            raise

        ingress = route.get("status", {}).get("ingress", [])
        if not ingress:
            continue

        route_path = route.get("spec", {}).get("path", "").rstrip("/")
        host = f"http://{ingress[0]['host']}{route_path}"
        endpoints.append(ToolEndpoint(tool=tool_name, host=host, paths=cfg["paths"]))

    return endpoints
