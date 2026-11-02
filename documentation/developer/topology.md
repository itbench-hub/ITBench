# Topology in ITBench

This document describes how topology data is collected, derived live, and queried in ITBench.

## Overview

ITBench uses an in-cluster event-driven pipeline to build live topology graphs in ClickHouse:

```
┌─────────────────────────────────────────────────────────────┐
│ 1. Collection Stage (recorders setup)                       │
│                                                             │
│  Kubernetes API Server                                      │
│         │ (watch events for labelled namespaces & cluster)  │
│         ▼                                                   │
│  OpenTelemetry Collector (k8sobjects receiver)              │
│         │ (writes raw ADDED/MODIFIED/DELETED events)        │
│         ▼                                                   │
│  ClickHouse (kubernetes.topology table)                     │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ 2. Live Graph Derivation
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Topology Writer (Go service in itbench-observability)      │
│         │ (polls new events, maintains state, derives       │
│         │  15 edge types, writes deltas)                    │
│         ▼                                                   │
│  ClickHouse (kubernetes.topology_graph table)               │
└─────────────────────────────────────────────────────────────┘
                               │
                               │ 3. Agent & Recorder Access
                               ▼
┌─────────────────────────────────────────────────────────────┐
│  Agent / Consumer SQL Access (HTTPRoute /clickhouse/)        │
│  ClickHouse Recorder Export -> k8s_topology_graph_raw.tsv.gz │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Collection and Export

### 1. In-Cluster Collection

During the `install` stage of the scenario lifecycle:
- The `tools` Ansible role (with `tools_recorders_enabled`) discovers all namespaces labeled with `itbench.io/record=true` (such as `bookinfo` and `otel-demo`).
- A dedicated, short-lived `OpenTelemetryCollector` instance is deployed into the `itbench-observability` namespace with RBAC permissions to watch resources.
- The collector streams Kubernetes resource events through the OTLP gateway into the `kubernetes.topology` table.
- A `topology-writer` deployment in `itbench-observability` polls `kubernetes.topology`, derives the topology graph, and writes delta rows into `kubernetes.topology_graph`.

### 2. Export Phase

During the `export` stage:
- The ClickHouse data recorder queries `kubernetes.topology` and `kubernetes.topology_graph` filtered between `RECORDING_START_TIMESTAMP` and `RECORDING_END_TIMESTAMP`.
- It exports the snapshot rows to `snapshots/<timestamp>/k8s_topology_objects.tsv.gz` and `snapshots/<timestamp>/k8s_topology_graph.tsv.gz`.

### 3. Teardown Phase

During the `uninstall` stage:
- The recorder resources are removed together with the rest of the tools when the `tools` role is uninstalled.

---

## Relationship Rules & Edge Types

The Go topology builder applies the following 15 relationship rules:

| Edge Type | Source Kind | Target Kind | Criteria / Relationship |
| :--- | :--- | :--- | :--- |
| `OWNS` | Controller / Parent | Child Resource | Defined by `metadata.ownerReferences[].uid`. |
| `OWNS` | `K8Cluster` | Cluster Resource / Namespace | Top-level ownership for cluster-scoped resources (`Node`, `Namespace`, `PV`, `StorageClass`, etc.). |
| `OWNS` | `Namespace` | Namespaced Resource | Namespace ownership for resources without an explicit `ownerReference`. |
| `NODE_RUNS_POD` | `Node` | `Pod` | Node placement matching `pod.spec.nodeName`. |
| `SERVICE_SELECTS_POD` | `Service` | `Pod` | Service matching all selector labels in `service.spec.selector` within the same namespace. |
| `SERVICE_HAS_ENDPOINTS` | `Service` | `Endpoints` | Matching name and namespace. |
| `ENDPOINTS_TARGET_POD` | `Endpoints` | `Pod` | Endpoints subset address targeting pod `subsets[].addresses[].targetRef`. |
| `POD_OWNS_PORT` | `Pod` | `Port` | `pod.spec.containers[].ports[].containerPort`, plus ports from the `Endpoints` subset targeting the pod. |
| `SERVICE_OWNS_PORT` | `Service` | `Port` | `service.spec.ports[].port`, plus ports from the service's `Endpoints` subsets. Declared ports exist even when no pod is ready. |
| `SERVICE_TARGETS_PORT` | `Port` *(Service)* | `Port` *(Pod)* | Mapping service port to backend pod port. |
| `POD_MOUNTS_CONFIGMAP` | `Pod` | `ConfigMap` | Volume reference in `pod.spec.volumes[].configMap.name`. |
| `POD_MOUNTS_SECRET` | `Pod` | `Secret` | Volume reference in `pod.spec.volumes[].secret.secretName`. |
| `POD_MOUNTS_PVC` | `Pod` | `PersistentVolumeClaim` | Volume reference in `pod.spec.volumes[].persistentVolumeClaim.claimName`. |
| `PV_BOUND_TO_PVC` | `PersistentVolume` | `PersistentVolumeClaim` | Bound volume reference in `pv.spec.claimRef`. |
| `HPA_SCALES` | `HorizontalPodAutoscaler` | Workload (e.g. `Deployment`) | Scale target reference in `hpa.spec.scaleTargetRef`. |
| `HTTPROUTE_ATTACHES_GATEWAY` | `HTTPRoute` | `Gateway` | Gateway reference in `httproute.spec.parentRefs`. |
| `HTTPROUTE_ROUTES_SERVICE` | `HTTPRoute` | `Service` | Backend service reference in `httproute.spec.rules[].backendRefs`. |
