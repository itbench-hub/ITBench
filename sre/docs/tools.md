# ITBench: Observability Tools

## Overview
Depending on the scenario domain (SRE or FinOps), the following tools are deployed:
| Tool | Scenario Domain(s) | Repository |
| --- | --- | --- |
| Altinity Clickhouse | FinOps, SRE | https://github.com/Altinity/ClickHouse |
| Altinity Clickhouse Operator | FinOps, SRE | https://github.com/Altinity/clickhouse-operator |
| Chaos Mesh | SRE | https://github.com/chaos-mesh/chaos-mesh |
| Jaeger | FinOps, SRE | https://github.com/jaegertracing/jaeger |
| Kubernetes Ingress | FinOps, SRE | https://github.com/kubernetes/ingress-nginx |
| Kubernetes Metric Server | FinOps | https://github.com/kubernetes-sigs/metrics-server |
| OpenCost | FinOps | https://github.com/opencost/opencost |
| OpenSearch | FinOps, SRE | https://github.com/opensearch-project/OpenSearch |
| OpenTelemetry Collector | FinOps, SRE | https://github.com/open-telemetry/opentelemetry-collector |
| OpenTelemetry Operator | FinOps, SRE | https://github.com/open-telemetry/opentelemetry-operator |
| Prometheus | FinOps, SRE | https://github.com/prometheus/prometheus |
| Prometheus Operator | FinOps, SRE | https://github.com/prometheus-operator/prometheus-operator |

### Installing observability tools for SRE scenarios
Run:
```bash
make deploy_tools
```

### Uninstalling observability tools for SRE scenarios
Run:
```bash
make undeploy_tools
```
