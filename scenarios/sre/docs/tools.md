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

> [!NOTE]
> With the exception of Jaeger and OpenSearch, all of the observability tools are installed during a SRE or FinOps live scenario. The installation of Jaeger - and its backend storage OpenSearch by proxy - can be disabled via the scenario specification by setting `spec.observability.traces.enabled` to `false`.

### Chaos Engineering Tools

A **chaos engineering tool** is a technology which injects faults into an environment. This allows developers to test various cases in the application stack for a variety of conditions.

In ITBench, the following tool is used:

| Tool | Repository |
| --- | --- |
| Chaos Mesh | https://github.com/chaos-mesh/chaos-mesh |

> [!NOTE]
> Unless a Chaos Mesh fault defined, Chaos Mesh is not installed during a SRE or FinOps live scenario. While not recommened - as to save on resources - Chaos Mesh can be installed via the scenario specification by setting `spec.chaosEngineering.chaosMesh.enabled` to `true`. When a Chaos Mesh fault is defined within the spec, this field is set to true.

### Service Mesh Tools

A service mesh tool is a technology which manages communication between pods in a Kubernetes environment. This allows developers to control traffic behavior, enforce security policies, and observe interactions between microservices.

| Tool | Repository |
| --- | --- |
| Istio | https://github.com/istio/istio |

> [!NOTE]
> In order to provide external access to the observability tools and their dashboards, Istio is always installed during a SRE or FinOps live scenario. ITBench runs Istio in `ambient` mode in order to make [better use of resources](https://istio.io/latest/docs/overview/dataplane-modes/).

### Cost Management Tools

A **cost management** is a technology which provides financial insights on the operational costs of running an application.

In ITBench, the following tool is used:

| Tool | Repository |
| --- | --- |
| OpenCost | https://github.com/opencost/opencost |

> [!NOTE]
> OpenCost is installed during a FinOps live scenario only. While not recommened - as to save on resources - OpenCost can be installed via the scenario specification by setting `spec.costManagement.opencost.enabled` to `true`.

### Kubernetes Tools

ITBench deploys additional Kubernetes tools to enable additional features in a Kubernetes cluster.

| Tool | Repository | Function |
| --- | --- | --- |
| Kubernetes Gateway API | https://github.com/kubernetes-sigs/gateway-api | Networking |
| Kubernetes Metric Server | https://github.com/kubernetes-sigs/metrics-server | Autoscaling |

## Additional Notes

### OpenShift

OpenShift provides a variety of Observability and Kubernetes tools out of the box. When deploying on this platform, ITBench will use these provided softwares rather than deploy its own instance of them as it does in a Kubernetes cluster.

The following tools are provided by OpenShift and are not installed by ITBench:

1. Prometheus & Prometheus Operator
2. OpenTelemetry Operator
3. Kubernetes Metrics Server

In addition, when deploying on OpenShift, OpenShift routes are used instead of a Kubernetes Gateway to provided external networking access to the observability tools.
