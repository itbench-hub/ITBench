import networkx as nx
import json
import pickle
import time
from typing import Optional, Dict, Any, Tuple, List
import logging
from pathlib import Path
import hashlib
import logging
import time
from typing import Optional
from kubernetes import client, config
from openshift.dynamic import DynamicClient
import logging
import yaml
import os
import sys
from dataclasses import dataclass
import threading

def LINE():
    return sys._getframe(1).f_lineno

# to Node somehow were getting attached to the namespace
# hence we define cluster scoped resources to avoid such connections.
CLUSTER_SCOPED_RESOURCES = {
    'Node', 'Namespace', 'PersistentVolume', 'ClusterRole', 'ClusterRoleBinding',
    'StorageClass', 'CSIDriver', 'CSINode', 'PriorityClass', 'RuntimeClass',
    'VolumeAttachment', 'PodSecurityPolicy', 'CustomResourceDefinition',
    'ValidatingWebhookConfiguration', 'MutatingWebhookConfiguration',
    'PodPreset', 'InitializerConfiguration'
}

@dataclass
class K8sResource:
    """Represents a Kubernetes resource with its basic attributes."""
    group: str
    version: str
    kind: str
    namespace: Optional[str]
    name: str
    owner_refs: List[Dict[str, Any]]
    labels: Dict[str, str]
    spec: Dict[str, Any]
    status: Dict[str, Any]
    uid: str = ""

class ResourceCollector:
    """Phase 1: Collects all raw Kubernetes resources."""
    def __init__(self, k8s_client):
        self.k8s_client = k8s_client
        self.resources: Dict[str, K8sResource] = {}
        self.logger = logging.getLogger("resource_collector")

    def _make_id(self, group: str, version: str, kind: str,
                 namespace: Optional[str], name: str) -> str:
        """Create a stable ID for a resource."""
        key = f"{group}:{version}:{kind}:{namespace or ''}:{name}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def collect_all_resources(self) -> Dict[str, K8sResource]:
        """
        Query cluster for all resources, store raw data (K8sResource objects).
        Returns a dictionary: stable_id -> K8sResource
        """
        for api_version, kind in self.k8s_client.get_api_resources():
            self._collect_resource_type(api_version, kind)
        return self.resources

    def _collect_resource_type(self, api_version: str, kind: str):
        """Collect all resources of a specific type and store them in self.resources."""
        try:
            if '/' in api_version:
                group, version = api_version.split('/')
            else:
                group, version = "", api_version

            resources = self.k8s_client.get_resources(api_version, kind)

            for resource in resources:
                stable_id = self._make_id(
                    group=group,
                    version=version,
                    kind=kind,
                    namespace=getattr(resource.metadata, 'namespace', None),
                    name=resource.metadata.name
                )
                # Populate UID from metadata
                uid_val = getattr(resource.metadata, 'uid', "")

                self.resources[stable_id] = K8sResource(
                    group=group,
                    version=version,
                    kind=kind,
                    namespace=getattr(resource.metadata, 'namespace', None),
                    name=resource.metadata.name,
                    owner_refs=getattr(resource.metadata, 'ownerReferences', []) or [],
                    labels=getattr(resource.metadata, 'labels', {}) or {},
                    spec=resource.spec.to_dict() if hasattr(resource, 'spec') and resource.spec else {},
                    status=resource.status.to_dict() if hasattr(resource, 'status') and resource.status else {},
                    uid=uid_val
                )
        except Exception as e:
            self.logger.error(f"Error collecting {kind}: {e}", exc_info=True)

class GraphBuilder:
    """Phase 2: Builds the graph using collected resources."""

    def __init__(self):
        self.graph = nx.DiGraph()
        self.logger = logging.getLogger("graph_builder")

    def build_graph(self, resources: Dict[str, K8sResource]):
        """Build the complete graph in a systematic way."""
        # 1. Create cluster node first
        cluster_node = self._create_cluster_node()

        # 2. Create all nodes (but no edges yet)
        node_mapping = {}
        for stable_id, resource in resources.items():
            node_id = self._create_node(resource)
            node_mapping[stable_id] = node_id

        # 3. Create edges
        self._create_ownership_edges(resources, node_mapping)
        self._create_runtime_edges(resources, node_mapping)
        self._create_network_edges(resources, node_mapping)
        self._create_volume_edges(resources, node_mapping)
        self._create_mount_edges(resources, node_mapping)

        return self.graph

    def _create_cluster_node(self) -> str:
        """Create the root cluster node."""
        node_id = "cluster"
        self.graph.add_node(node_id,
                            kind="K8Cluster",
                            group="",
                            version="v1",
                            namespace="",
                            name="cluster",
                            uid=node_id)
        return node_id

    def _create_node(self, resource: K8sResource) -> str:
        """Create a single node in the graph."""
        node_id = self._make_node_id(resource)
        self.graph.add_node(
            node_id,
            kind=resource.kind,
            group=resource.group,
            version=resource.version,
            namespace=resource.namespace or "",
            name=resource.name,
            labels=resource.labels,
            uid=resource.uid
        )
        return node_id

    def _make_node_id(self, resource: K8sResource) -> str:
        """Generate a stable node ID."""
        key = f"{resource.kind}:" \
              f"{resource.namespace or ''}:{resource.name}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]

    def _get_owner_node_id(self, owner_ref: Dict[str, Any], resource_namespace: str) -> Optional[str]:
        """Get node ID for an owner reference."""
        if '/' in owner_ref['apiVersion']:
            owner_group, owner_version = owner_ref['apiVersion'].split('/')
        else:
            owner_group, owner_version = "", owner_ref['apiVersion']

        owner_namespace = "" if owner_ref['kind'] in CLUSTER_SCOPED_RESOURCES else resource_namespace

        temp_resource = K8sResource(
            group=owner_group,
            version=owner_version,
            kind=owner_ref['kind'],
            namespace=owner_namespace,
            name=owner_ref['name'],
            owner_refs=[],
            labels={},
            spec={},
            status={},
            uid=""
        )
        return self._make_node_id(temp_resource)

    def _create_ownership_edges(self,
                                resources: Dict[str, K8sResource],
                                node_mapping: Dict[str, str]):
        """Create all ownership-based edges."""
        cluster_node = "cluster"

        for stable_id, resource in resources.items():
            node_id = node_mapping[stable_id]

            # 1) Owner references
            if resource.owner_refs:
                for owner_ref in resource.owner_refs:
                    owner_id = self._get_owner_node_id(owner_ref, resource.namespace or "")
                    if owner_id and owner_id in self.graph:
                        self.graph.add_edge(
                            owner_id,
                            node_id,
                            type="OWNS",
                            verbose_type=f"{owner_ref['kind'].upper()}_OWNS_{resource.kind.upper()}"
                        )
                        continue

            # 2) If no owners, cluster or namespace "owns" it
            if not any(self.graph.in_edges(node_id)):
                if resource.kind in CLUSTER_SCOPED_RESOURCES or not resource.namespace:
                    self.graph.add_edge(
                        cluster_node,
                        node_id,
                        type="OWNS",
                        verbose_type="CLUSTER_OWN_RESOURCE"
                    )
                else:
                    if resource.kind not in ("Endpoints", "EndpointSlice"):
                        ns_id = self._get_namespace_node_id(resource.namespace)
                        if ns_id in self.graph:
                            self.graph.add_edge(
                                ns_id,
                                node_id,
                                type="OWNS",
                                verbose_type=f"NAMESPACE_OWNS_{resource.kind.upper()}"
                            )

    def _create_volume_edges(self,
                             resources: Dict[str, K8sResource],
                             node_mapping: Dict[str, str]):
        """Create edges between PVs and PVCs (PV_BOUND_TO_PVC)."""
        for resource_id, resource in resources.items():
            if resource.kind == "PersistentVolume":
                if resource.spec.get('claimRef'):
                    claim = resource.spec['claimRef']
                    pvc_temp = K8sResource(
                        group="",
                        version="v1",
                        kind="PersistentVolumeClaim",
                        namespace=claim.get('namespace', ""),
                        name=claim.get('name', ""),
                        owner_refs=[],
                        labels={},
                        spec={},
                        status={},
                        uid=""
                    )
                    pvc_id = self._make_node_id(pvc_temp)
                    if pvc_id in self.graph:
                        self.graph.add_edge(
                            resource_id,
                            pvc_id,
                            type="OWNS",
                            verbose_type="PV_BOUND_TO_PVC"
                        )

    def _create_runtime_edges(self,
                              resources: Dict[str, K8sResource],
                              node_mapping: Dict[str, str]):
        """Create runtime relationships (e.g. Pod running on Node)."""
        for stable_id, resource in resources.items():
            if resource.kind == "Pod":
                node_name = resource.spec.get("nodeName")
                if node_name:
                    pod_id = node_mapping[stable_id]
                    node_temp = K8sResource(
                        group="",
                        version="v1",
                        kind="Node",
                        namespace=None,
                        name=node_name,
                        owner_refs=[],
                        labels={},
                        spec={},
                        status={},
                        uid=""
                    )
                    node_id = self._make_node_id(node_temp)
                    if node_id in self.graph:
                        self.graph.add_edge(
                            node_id,
                            pod_id,
                            type="OWNS",
                            verbose_type="NODE_RUNS_POD"
                        )

    def _create_network_edges(self,
                              resources: Dict[str, K8sResource],
                              node_mapping: Dict[str, str]):
        """Create networking relationships (Service->Pod->Port, Endpoints->Pod, etc.)."""
        self._process_service_relationships(resources, node_mapping)
        self._process_endpoint_relationships(resources, node_mapping)

    def _get_namespace_node_id(self, namespace: str) -> str:
        """Get node ID for a namespace."""
        tmp_ns_resource = K8sResource(
            group="",
            version="v1",
            kind="Namespace",
            namespace="",
            name=namespace,
            owner_refs=[],
            labels={},
            spec={},
            status={},
            uid=""
        )
        return self._make_node_id(tmp_ns_resource)

    def _process_service_relationships(self,
                                       resources: Dict[str, K8sResource],
                                       node_mapping: Dict[str, str]):
        """Process Service->Pod selection and Service->Port relationships."""
        for stable_id, resource in resources.items():
            if resource.kind != "Service":
                continue
            service_id = node_mapping[stable_id]
            selector = resource.spec.get("selector", {})

            if selector:
                # service->pod edges
                for pod_stable_id, pod_resource in resources.items():
                    if pod_resource.kind == "Pod" and pod_resource.namespace == resource.namespace:
                        # If all labels match
                        if all(pod_resource.labels.get(k) == v for k, v in selector.items()):
                            self.graph.add_edge(
                                service_id,
                                node_mapping[pod_stable_id],
                                type="SELECTS",
                                verbose_type="SERVICE_SELECTS_POD"
                            )

            # create "port nodes" for service ports
            for port in resource.spec.get("ports", []):
                port_node_id = self._create_port_node(
                    namespace=resource.namespace or "",
                    name=f"{resource.name}-{port.get('port')}-{port.get('protocol', 'TCP')}",
                    port_data=port
                )
                # link service -> port
                self.graph.add_edge(
                    service_id,
                    port_node_id,
                    type="OWNS",
                    verbose_type="SERVICE_OWNS_PORT"
                )

    def _process_endpoint_relationships(self,
                                        resources: Dict[str, K8sResource],
                                        node_mapping: Dict[str, str]):
        """Process Endpoints->Pod and related Port relationships."""
        for stable_id, resource in resources.items():
            if resource.kind != "Endpoints":
                continue
            endpoints_id = node_mapping[stable_id]

            # Link Endpoints -> Service
            service_temp = K8sResource(
                group="",
                version="v1",
                kind="Service",
                namespace=resource.namespace,
                name=resource.name,  # Endpoints share name with Service
                owner_refs=[],
                labels={},
                spec={},
                status={},
                uid=""
            )
            service_id = self._make_node_id(service_temp)
            if service_id in self.graph:
                self.graph.add_edge(
                    service_id,
                    endpoints_id,
                    type="OWNS",
                    verbose_type="SERVICE_HAS_ENDPOINTS"
                )

            # Now link endpoints->pods, endpoints->ports
            for subset in resource.spec.get("subsets", []):
                for address in subset.get("addresses", []):
                    target_ref = address.get("targetRef")
                    if target_ref and target_ref.get("kind") == "Pod":
                        pod_temp = K8sResource(
                            group="",
                            version="v1",
                            kind="Pod",
                            namespace=resource.namespace,
                            name=target_ref["name"],
                            owner_refs=[],
                            labels={},
                            spec={},
                            status={},
                            uid=""
                        )
                        pod_id = self._make_node_id(pod_temp)
                        if pod_id in self.graph:
                            self.graph.add_edge(
                                endpoints_id,
                                pod_id,
                                type="OWNS",
                                verbose_type="ENDPOINTS_TARGET_POD"
                            )

                            # ports
                            for port in subset.get("ports", []):
                                # create pod port
                                pod_port_id = self._create_port_node(
                                    resource.namespace or "",
                                    f"{target_ref['name']}-{port.get('port')}-{port.get('protocol', 'TCP')}",
                                    port
                                )
                                # create service port (again)
                                service_port_id = self._create_port_node(
                                    resource.namespace or "",
                                    f"{resource.name}-{port.get('port')}-{port.get('protocol', 'TCP')}",
                                    port
                                )
                                # link pod->port
                                self.graph.add_edge(
                                    pod_id,
                                    pod_port_id,
                                    type="OWNS",
                                    verbose_type="POD_OWNS_PORT"
                                )
                                # link service->port
                                if service_id in self.graph:
                                    self.graph.add_edge(
                                        service_id,
                                        service_port_id,
                                        type="OWNS",
                                        verbose_type="SERVICE_OWNS_PORT"
                                    )
                                # link service port->pod port
                                self.graph.add_edge(
                                    service_port_id,
                                    pod_port_id,
                                    type="OWNS",
                                    verbose_type="SERVICE_TARGETS_PORT"
                                )

    def _create_port_node(self, namespace: str, name: str, port_data: Dict):
        """Create a Port node with standardized attributes, returns the node ID."""
        port_resource = K8sResource(
            group="",
            version="v1",
            kind="Port",
            namespace=namespace,
            name=name,
            owner_refs=[],
            labels={},
            spec={"port": port_data.get("port"), "protocol": port_data.get("protocol", "TCP")},
            status={},
            uid=""
        )
        node_id = self._make_node_id(port_resource)

        if node_id not in self.graph:
            self.graph.add_node(
                node_id,
                kind="Port",
                group="",
                version="v1",
                namespace=namespace,
                name=name,
                port=str(port_data.get("port")),
                protocol=port_data.get("protocol", "TCP")
            )
        return node_id

    def _create_mount_edges(self,
                            resources: Dict[str, K8sResource],
                            node_mapping: Dict[str, str]):
        """
        Create edges from Pod -> (ConfigMap, Secret, PVC, etc.) if the Pod's volumes
        reference any of those resources.
        """
        for stable_id, resource in resources.items():
            if resource.kind != "Pod":
                continue

            pod_id = node_mapping[stable_id]
            volumes = resource.spec.get("volumes", [])
            for vol in volumes:
                # Check for a configMap volume
                if "configMap" in vol:
                    cm_name = vol["configMap"].get("name")
                    if cm_name:
                        cm_res = K8sResource(
                            group="",
                            version="v1",
                            kind="ConfigMap",
                            namespace=resource.namespace or "",
                            name=cm_name,
                            owner_refs=[],
                            labels={},
                            spec={},
                            status={},
                            uid=""
                        )
                        cm_id = self._make_node_id(cm_res)
                        if cm_id in self.graph:
                            self.graph.add_edge(
                                pod_id,
                                cm_id,
                                type="MOUNTS",
                                verbose_type="POD_MOUNTS_CONFIGMAP"
                            )

                # Check for a secret volume
                if "secret" in vol:
                    secret_name = vol["secret"].get("secretName")
                    if secret_name:
                        secret_res = K8sResource(
                            group="",
                            version="v1",
                            kind="Secret",
                            namespace=resource.namespace or "",
                            name=secret_name,
                            owner_refs=[],
                            labels={},
                            spec={},
                            status={},
                            uid=""
                        )
                        secret_id = self._make_node_id(secret_res)
                        if secret_id in self.graph:
                            self.graph.add_edge(
                                pod_id,
                                secret_id,
                                type="MOUNTS",
                                verbose_type="POD_MOUNTS_SECRET"
                            )

                # Check for a PVC volume
                if "persistentVolumeClaim" in vol:
                    claim_name = vol["persistentVolumeClaim"].get("claimName")
                    if claim_name:
                        pvc_res = K8sResource(
                            group="",
                            version="v1",
                            kind="PersistentVolumeClaim",
                            namespace=resource.namespace or "",
                            name=claim_name,
                            owner_refs=[],
                            labels={},
                            spec={},
                            status={},
                            uid=""
                        )
                        pvc_id = self._make_node_id(pvc_res)
                        if pvc_id in self.graph:
                            self.graph.add_edge(
                                pod_id,
                                pvc_id,
                                type="MOUNTS",
                                verbose_type="POD_MOUNTS_PVC"
                            )


class K8sTopologyManager:
    def __init__(self, k8s_client, persistence_dir: str = "./topology_data"):
        self.k8s_client = k8s_client
        self.persistence_dir = Path(persistence_dir)
        self.collector = ResourceCollector(k8s_client)
        self.builder = GraphBuilder()
        self.graph = nx.DiGraph()
        self._node_cache = {}
        self.logger = logging.getLogger("topology_manager")
        self._lock = threading.RLock()

    def refresh_topology(self):
        """Update the entire topology using the two-phase approach."""
        with self._lock:
            # Phase 1: Collect all resources
            resources = self.collector.collect_all_resources()

            # Phase 2: Build the graph
            self.graph = self.builder.build_graph(resources)

    def add_node(self, group: str, version: str, kind: str,
                 namespace: Optional[str], name: str, **attrs) -> str:
        """
        Add (or update) a node in the graph. If the node doesn't exist, it will be created,
        otherwise it will be updated. Also handles default ownership edges like
        CLUSTER_OWN_RESOURCE or NAMESPACE_OWNS_* -- except for Port nodes.
        """
        with self._lock:
            node_id = self._get_stable_node_id(group, version, kind, namespace, name)

            # Sanitize attributes so everything is string-friendly
            sanitized_attrs = {k: str(v) if v is not None else "" for k, v in attrs.items()}
            sanitized_attrs.update({
                'kind': kind,
                'group': group,
                'version': version,
                'namespace': namespace if namespace else "",
                'name': name,
                'last_seen': time.time()
            })

            # Create or update the node
            if node_id not in self.graph:
                self.graph.add_node(node_id, **sanitized_attrs)
            else:
                self.graph.nodes[node_id].update(sanitized_attrs)

            # If there are no in-edges, set ownership unless this node is a Port.
            # That way, we won't get "Namespace -> Port" or "K8Cluster -> Port" edges automatically.
            if kind != 'Port' and not any(self.graph.in_edges(node_id)):
                if kind in CLUSTER_SCOPED_RESOURCES or not namespace:
                    cluster_id = self.get_or_create_cluster_node()
                    self.add_edge(cluster_id, node_id, "CLUSTER_OWN_RESOURCE")
                else:
                    namespace_id = self._ensure_namespace_exists(namespace)
                    self.add_edge(namespace_id, node_id, f"NAMESPACE_OWNS_{kind.upper()}")

            return node_id

    def _remove_namespace_ownership(self, node_id: str):
        """Remove namespace ownership edges for a node."""
        if node_id not in self.graph:
            return

        node_attrs = self.graph.nodes[node_id]
        kind = node_attrs['kind']

        edges_to_remove = []
        for src, _, attrs in self.graph.in_edges(node_id, data=True):
            edge_type = attrs.get('type', '')
            if isinstance(edge_type, list):
                if any(t.startswith('NAMESPACE_OWNS_') for t in edge_type):
                    edges_to_remove.append((src, node_id))
            elif isinstance(edge_type, str) and edge_type.startswith('NAMESPACE_OWNS_'):
                edges_to_remove.append((src, node_id))

        for edge in edges_to_remove:
            self.graph.remove_edge(*edge)

    def _ensure_namespace_exists(self, namespace: str) -> str:
        with self._lock:
            if not namespace:
                return None

            namespace_id = self._get_stable_node_id(
                group="",
                version="v1",
                kind="Namespace",
                namespace="",
                name=namespace
            )

            if namespace_id not in self.graph:
                cluster_id = self.get_or_create_cluster_node()
                self.add_node(
                    group="",
                    version="v1",
                    kind="Namespace",
                    namespace="",
                    name=namespace
                )
                self.add_edge(cluster_id, namespace_id, "CLUSTER_OWN_NAMESPACE")

            return namespace_id

    def get_or_create_cluster_node(self) -> str:
        with self._lock:
            cluster_id = self._get_stable_node_id(
                group="",
                version="v1",
                kind="K8Cluster",
                namespace="",
                name="bench"
            )

            if cluster_id not in self.graph:
                self.graph.add_node(
                    cluster_id,
                    kind="K8Cluster",
                    group="",
                    version="v1",
                    namespace="",
                    name="bench",
                    uid=cluster_id,
                    last_seen=time.time()
                )

            return cluster_id

    def _get_stable_node_id(self, group: str, version: str, kind: str,
                           namespace: Optional[str], name: str) -> str:
        """
        Generate or retrieve a stable node ID for a Kubernetes resource.
        Uses consistent hashing to ensure stability and reduce memory usage.
        """
        # Create a unique key for the resource
        cache_key = f"{group}:{version}:{kind}:{namespace}:{name}"

        if cache_key not in self._node_cache:
            # Create a hash of the key using SHA-256
            # Using only first 16 characters of hexdigest
            node_id = hashlib.sha256(cache_key.encode('utf-8')).hexdigest()[:16]
            self._node_cache[cache_key] = node_id

        return self._node_cache[cache_key]

    def add_edge(self, from_node: str, to_node: str, rel_type: str):
        with self._lock:
            if not all(isinstance(x, str) for x in [from_node, to_node]):
                raise ValueError("Nodes must be strings (hashed IDs)")

            if self.graph.has_edge(from_node, to_node):
                existing_type = self.graph[from_node][to_node].get('type')
                if existing_type == rel_type:
                    return
                if isinstance(existing_type, list):
                    if rel_type not in existing_type:
                        existing_type.append(rel_type)
                else:
                    self.graph[from_node][to_node]['type'] = [existing_type, rel_type]
            else:
                self.graph.add_edge(from_node, to_node, type=rel_type)

            self.graph[from_node][to_node]['last_seen'] = time.time()


    def _serialize_graph(self) -> dict:
        """
        Serialize the graph into a JSON-friendly dictionary format with enhanced type handling.
        """
        def sanitize_attrs(attrs):
            """Helper to sanitize attribute dictionaries"""
            sanitized = {}
            for k, v in attrs.items():
                if isinstance(v, (int, float, str, bool)):
                    sanitized[k] = v
                elif isinstance(v, (list, tuple)):
                    sanitized[k] = [str(x) for x in v]
                elif v is None:
                    sanitized[k] = None
                else:
                    sanitized[k] = str(v)
            return sanitized

        return {
            'nodes': [
                {
                    'id': node_id,
                    'attributes': sanitize_attrs(attrs)
                }
                for node_id, attrs in self.graph.nodes(data=True)
            ],
            'edges': [
                {
                    'source': source,
                    'target': target,
                    'attributes': sanitize_attrs(attrs)
                }
                for source, target, attrs in self.graph.edges(data=True)
            ],
            'node_cache': self._node_cache,
            'metadata': {
                'timestamp': time.time(),
                'version': '1.1'
            }
        }

    def _deserialize_graph(self, data: dict) -> None:
        """
        Reconstruct the graph from a serialized dictionary format.
        """
        # Create a new empty graph
        self.graph = nx.DiGraph()

        # Add nodes
        for node_data in data['nodes']:
            node_id = node_data['id']  # Already a string
            self.graph.add_node(node_id, **node_data['attributes'])

        # Add edges
        for edge_data in data['edges']:
            source = edge_data['source']  # Already a string
            target = edge_data['target']
            self.graph.add_edge(source, target, **edge_data['attributes'])

        # Restore node cache
        self._node_cache = data['node_cache']

    def save_snapshot(self):
        """Save current topology state."""
        with self._lock:
            timestamp = int(time.time())
            filename = f"topology_snapshot_{timestamp}.json"
            filepath = self.persistence_dir / filename

            # Convert the graph to a serializable format
            data = {
                'nodes': [
                    {
                        'id': node_id,
                        'attributes': {k: str(v) for k, v in attrs.items()}  # Convert all values to strings
                    }
                    for node_id, attrs in self.graph.nodes(data=True)
                ],
                'edges': [
                    {
                        'source': source,
                        'target': target,
                        'attributes': {k: str(v) for k, v in attrs.items()}
                    }
                    for source, target, attrs in self.graph.edges(data=True)
                ],
                'node_cache': self._node_cache,
                'metadata': {
                    'timestamp': timestamp,
                    'version': '1.0'
                }
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)

            return str(filepath)

    def load_snapshot(self, filepath: str):
        """
        Load topology state from a JSON snapshot file.
        """
        with self._lock:
            filepath = Path(filepath)
            if not filepath.exists():
                raise FileNotFoundError(f"Snapshot file not found: {filepath}")

            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            self._deserialize_graph(data)
            self.logger.info(f"Loaded topology snapshot from {filepath}")

    def get_latest_snapshot(self) -> Optional[str]:
        """
        Get the path to the most recent snapshot file.
        """
        with self._lock:
            snapshots = list(self.persistence_dir.glob("topology_snapshot_*.json"))
            if not snapshots:
                return None
            return str(max(snapshots, key=lambda p: p.stat().st_mtime))

    # TODO call
    def cleanup_old_nodes(self, max_age_seconds: float = 3600):
        """
        Remove nodes that haven't been seen recently.
        """
        with self._lock:
            current_time = time.time()
            nodes_to_remove = []

            for node, attrs in self.graph.nodes(data=True):
                last_seen = attrs.get('last_seen', 0)
                if current_time - last_seen > max_age_seconds:
                    nodes_to_remove.append(node)

            for node in nodes_to_remove:
                self.graph.remove_node(node)

            return len(nodes_to_remove)

    # TODO call
    def cleanup_old_snapshots(self, max_snapshots: int = 10):
        """
        Keep only the N most recent snapshots.
        """
        with self._lock:
            snapshots = list(self.persistence_dir.glob("topology_snapshot_*.json"))
            if len(snapshots) <= max_snapshots:
                return

            # Sort by modification time
            snapshots.sort(key=lambda p: p.stat().st_mtime)

            # Remove oldest snapshots
            for snapshot in snapshots[:-max_snapshots]:
                snapshot.unlink()
                self.logger.debug(f"Removed old snapshot: {snapshot}")

class K8sClient:
    def __init__(self, kubeconfig_path: Optional[str] = None):
       self.logger = logging.getLogger("k8s_client")
       self.kubeconfig_path = kubeconfig_path
       self._initialize_client()

    def _initialize_client(self):
       try:
           if os.getenv('KUBERNETES_SERVICE_HOST'):
               config.load_incluster_config()
           else:
               config.load_kube_config(config_file=self.kubeconfig_path)

           self._api_client = client.ApiClient()
           self.dynamic_client = DynamicClient(self._api_client)
           self.logger.info(f"Initialized client with kubeconfig: {self.kubeconfig_path}")
       except Exception as e:
           raise Exception(f"Failed to initialize Kubernetes client: {str(e)}") from e

    def _initialize_from_kubeconfig(self):
        """Fallback initialization using kubeconfig file."""
        try:
            config_file = os.environ.get('KUBECONFIG', os.path.expanduser('~/.kube/config'))

            if not os.path.exists(config_file):
                raise config.config_exception.ConfigException(
                    "No valid kubeconfig file found")

            # Load the config and get current context
            with open(config_file) as f:
                config_dict = yaml.safe_load(f)

            current_context = config_dict.get('current-context')
            if not current_context:
                raise config.config_exception.ConfigException(
                    "No current-context found in kubeconfig")

            config.load_kube_config(config_file=config_file, context=current_context)

            self._api_client = client.ApiClient()
            self.dynamic_client = DynamicClient(self._api_client)

            self.logger.info("Successfully initialized Kubernetes client using kubeconfig")

        except Exception as e:
            raise Exception(
                f"Failed to initialize Kubernetes client: {str(e)}"
            ) from e

    def get_namespaces(self) -> List[str]:
        """Get list of all namespaces."""
        try:
            namespaces = self.dynamic_client.resources.get(
                api_version='v1',
                kind='Namespace'
            ).get()
            return [ns.metadata.name for ns in namespaces.items]
        except Exception as e:
            self.logger.error(f"Error getting namespaces: {e}")
            return []

    def get_api_resources(self):
        """Get all API resources."""
        # Core API (v1)
        core_resources = {
            'Pod', 'Service', 'ConfigMap', 'Secret', 'PersistentVolumeClaim',
            'PersistentVolume', 'Node', 'Namespace', 'ServiceAccount', 'Endpoints'
        }

        for kind in core_resources:
            yield "v1", kind

        # API Groups
        api_groups = client.ApisApi(self._api_client).get_api_versions()
        for group in api_groups.groups:
            group_name = group.name
            version = group.preferred_version.version
            api_version = f"{group_name}/{version}"

            try:
                resources = self.dynamic_client.resources.search(api_version=api_version)
                for resource in resources:
                    if not self._is_valid_resource(resource):
                        continue
                    yield api_version, resource.kind
            except Exception as e:
                self.logger.debug(f"Error processing API group {api_version}: {e}")

    def _is_valid_resource(self, resource) -> bool:
        """Check if a resource should be processed."""
        if not (hasattr(resource, 'kind') and
                hasattr(resource, 'name') and
                hasattr(resource, 'verbs')):
            return False

        # Skip List types and special resources
        if (resource.kind.endswith('List') or
            resource.name.lower() in {
                "events", "bindings", "tokenreviews",
                "selfsubjectreviews", "selfsubjectaccessreviews",
                "selfsubjectrulesreviews", "subjectaccessreviews",
                "localsubjectaccessreviews", "componentstatuses"
            }):
            return False

        # Skip if resource only supports special verbs
        if not {'list', 'get'}.intersection(resource.verbs):
            return False

        # Skip subresources
        if "/" in resource.name:
            return False

        return True

    def get_resources(self, api_version: str, kind: str, namespace: Optional[str] = None):
        """Get resources of specified type."""
        try:
            resource = self.dynamic_client.resources.get(api_version=api_version, kind=kind)

            # Only use namespace if the resource is namespaced
            try:
                if namespace and resource.namespaced and kind not in CLUSTER_SCOPED_RESOURCES:
                    response = resource.get(namespace=namespace)
                else:
                    response = resource.get()

                # Ensure we return a list of items
                if hasattr(response, 'items'):
                    return response.items
                elif isinstance(response, list):
                    return response
                else:
                    # If single item returned, wrap in list
                    return [response]

            except Exception as e:
                # Check if resource type exists but returns error
                if "404" in str(e):
                    return []
                raise

        except Exception as e:
            self.logger.debug(f"Error getting resources {kind} in {namespace}: {e}")
            return []
