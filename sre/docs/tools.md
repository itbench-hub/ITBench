# ITBench: Tools

## Overview

ITBench uses a variety of open-source softwares to inject faults into the environment and collect telemetry data from the applications.

### Observability Tools

An **observability tool** is a technology which collects telemetry data to provide insights on the health and status of application at run time. Generally, this data can fall under one of the following categories:

1. Logs
2. Metrics
3. Traces

ITBench makes use of the following tools to process observability data:

| Tool | Repository | Function | Observability Data Type(s) |
| --- | --- | --- | --- |
| Altinity Clickhouse | https://github.com/Altinity/ClickHouse | Storage | Logs, Traces |
| Altinity Clickhouse Operator | https://github.com/Altinity/clickhouse-operator | Storage | Logs, Traces |
| Jaeger | https://github.com/jaegertracing/jaeger | Collector | Traces |
| OpenSearch | https://github.com/opensearch-project/OpenSearch | Storage | Logs, Traces |
| OpenTelemetry Collector | https://github.com/open-telemetry/opentelemetry-collector | Collector | Logs, Traces, Metrics |
| OpenTelemetry Operator | https://github.com/open-telemetry/opentelemetry-operator | Collector | Logs, Traces, Metrics |
| Prometheus | https://github.com/prometheus/prometheus | Collector | Metrics |
| Prometheus Operator | https://github.com/prometheus-operator/prometheus-operator | Collector | Metrics |

Unless explicitly deactivated, these tools are always deployed in the environment. For more information about each tool, please review the documentation provided in the respective tool's GitHub repository.

**Note:** When deploying Jaeger, OpenSearch is deployed as a storage unit for the traces received by Jaeger, regardless of whether OpenSearch is part of the active install list during an incident.

### Chaos Engineering Tools

A **chaos engineering tool** is a technology which injects faults into an environment. This allows developers to test various cases in the application stack for a variety of conditions.

In ITBench, the following tool is used:

| Tool | Repository |
| --- | --- |
| Chaos Mesh | https://github.com/chaos-mesh/chaos-mesh |

### Service Mesh Tools

A service mesh tool is a technology which manages communication between pods in a Kubernetes environment. This allows developers to control traffic behavior, enforce security policies, and observe interactions between microservices.

| Tool | Repository |
| --- | --- |
| Istio | https://github.com/istio/istio |

**Note:** Istio also supports an ambient mesh architecture, which is not included in the current installation. This setup uses the default configuration with only the ingress gateway enabled. To enable the ambient mesh, the installation must be extended to include additional Istio components such as ztunnel and istio-cni.

### FinOps Tools

A **finops tool** is a technology which provides financial insights on the operational costs of running an application.

In ITBench, the following tool is used:

| Tool | Repository |
| --- | --- |
| OpenCost | https://github.com/opencost/opencost |

**Note:** When deploying OpenCost, Prometheus is deployed as a required dependency, regardless of whether Prometheus is part of the active install list during an incident.

### Kubernetes Tools

ITBench deploys additional Kubernetes tools to enable additional features in a Kubernetes cluster.

| Tool | Repository | Function |
| --- | --- | --- |
| Kubernetes Metric Server | https://github.com/kubernetes-sigs/metrics-server | Autoscaling |
| Kubernetes NGINX Controller | https://github.com/kubernetes/ingress-nginx | Networking |

**Note:** Kubernetes NGINX Controller provides Ingress support which allows a user to externally access an observability tool's UI. This is useful for debugging, but explicitly needed. However, it is still always deployed as part of the tool stack unless deactivated.

**Note:** Due to increasing load being a frequent need in FinOps incidents (to "raise" cost), the Kubernetes Metrics Server is always deployed as part of the tool stack for FinOps scenarios unless deactivated. To install it as part of an SRE scenario, it needs to be explicitly added to the incident spec.

## Additional Notes

### OpenShift

OpenShift provides a variety of Observability and Kubernetes tools out of the box. When deploying on this platform, ITBench will use these provided softwares rather than deploy its own instance of them as it does in a Kubernetes cluster.

The following tools are provided by OpenShift and are not installed by ITBench:

1. Prometheus & Prometheus Operator
2. OpenTelemetry Operator
3. Kubernetes Metrics Server

In addition, when deploying on OpenShift, the Kubernetes NGINX Controller is not installed. Instead, Routes are used to provided external networking access to the observability tools.
