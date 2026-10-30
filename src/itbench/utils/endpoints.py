"""Endpoint discovery utilities for ITBench tools stack.

Resolves external URLs for each installed tool by querying the Kubernetes API
directly via HTTPRoute resources attached to the managed Gateway.

Supports both Kubernetes (NGINX Gateway Fabric) and OpenShift (OpenShift Gateway).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from kubernetes import client, config  # type: ignore[import-untyped]


_VARS_DIR = (
    Path(__file__).parents[3]
    / "scenarios"
    / "sre"
    / "project"
    / "roles"
    / "tools"
    / "vars"
    / "main"
)


def _load_vars() -> dict[str, Any]:
    """Merge all YAML files under the tools role vars/main/ directory."""
    merged: dict[str, Any] = {}
    for path in sorted(_VARS_DIR.glob("*.yaml")):
        with path.open(encoding="utf-8") as fh:
            merged.update(yaml.safe_load(fh) or {})
    return merged


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


def _build_tool_definitions(vars: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build tool lookup table from role vars.

    Returns a dict keyed by human-readable tool name, each with:
      - ``name``: HTTPRoute resource name
      - ``namespace``: HTTPRoute resource namespace
      - ``paths``: list of significant URL paths
    """
    obs_ns = vars["tools_namespace_itbench_observability"]

    return {
        "Prometheus": {
            "name": vars["tools_helm_release_kube_prometheus_stack"],
            "namespace": obs_ns,
            "paths": ["/observability/prometheus/alerts", "/observability/prometheus/query"],
        },
        "Jaeger": {
            "name": "jaeger",
            "namespace": obs_ns,
            "paths": ["/observability/jaeger/"],
        },
        "ClickHouse": {
            "name": "clickhouse",
            "namespace": obs_ns,
            "paths": ["/observability/clickhouse/play"],
        },
        "OpenCost": {
            "name": vars["tools_helm_release_opencost"],
            "namespace": obs_ns,
            "paths": ["/"],
        },
    }


def discover_endpoints(kubeconfig: str, platform: str) -> list[ToolEndpoint]:
    """Resolve external endpoints for all installed tools.

    Args:
        kubeconfig: Path to the kubeconfig file.
        platform: Either ``"kubernetes"`` or ``"openshift"``.

    Returns:
        List of :class:`ToolEndpoint` for each tool that was found.
        Tools whose HTTPRoutes are not present are silently skipped.
    """
    vars = _load_vars()
    tools = _build_tool_definitions(vars)

    config.load_kube_config(config_file=kubeconfig)
    custom = client.CustomObjectsApi()

    gateway_name = vars["tools_gateway"]
    if platform == "openshift":
        gateway_namespace = vars["tools_namespace_kubernetes_gateway_openshift"]
    else:
        gateway_namespace = vars["tools_namespace_itbench_kubernetes_gateway"]

    gateway_host = _resolve_gateway_host(custom, name=gateway_name, namespace=gateway_namespace)
    return _resolve_httproute_endpoints(custom, gateway_host, tools)


def _resolve_gateway_host(
    custom: client.CustomObjectsApi,
    name: str,
    namespace: str,
) -> str:
    """Return the base HTTP address of the managed Gateway."""
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
    suffix = ":8080" if addr.get("type") == "IPAddress" else ""
    return f"http://{addr['value']}{suffix}"


def _resolve_httproute_endpoints(
    custom: client.CustomObjectsApi,
    gateway_host: str,
    tools: dict[str, dict[str, Any]],
) -> list[ToolEndpoint]:
    """Resolve endpoints via HTTPRoute resources."""
    endpoints: list[ToolEndpoint] = []

    for tool_name, cfg in tools.items():
        try:
            custom.get_namespaced_custom_object(
                group="gateway.networking.k8s.io",
                version="v1",
                namespace=cfg["namespace"],
                plural="httproutes",
                name=cfg["name"],
            )
        except client.exceptions.ApiException as exc:
            if exc.status == 404:
                continue
            raise

        endpoints.append(ToolEndpoint(tool=tool_name, host=gateway_host, paths=cfg["paths"]))

    return endpoints
