# ITBench: Observability Tools

## Overview
Depending on the scenario domain (SRE or FinOps), the following tools are deployed:
| Tool | Scenario Domain(s) | Repository |
| --- | --- | --- |
| Altinity Clickhouse | FinOps, SRE | https://github.com/Altinity/ClickHouse |
| Altinity Clickhouse Operator | FinOps, SRE | https://github.com/Altinity/clickhouse-operator |
| Chaos Mesh | SRE | https://github.com/chaos-mesh/chaos-mesh |
| Grafana | FinOps, SRE | https://github.com/grafana/grafana |
| Jaeger | FinOps, SRE | https://github.com/jaegertracing/jaeger |
| Kubernetes Ingress | FinOps, SRE | https://github.com/kubernetes/ingress-nginx |
| Kubernetes Metric Server | FinOps | https://github.com/kubernetes-sigs/metrics-server |
| OpenCost | FinOps | https://github.com/opencost/opencost |
| OpenSearch | FinOps, SRE | https://github.com/opensearch-project/OpenSearch |
| OpenTelemetry Collector | FinOps, SRE | https://github.com/open-telemetry/opentelemetry-collector |
| OpenTelemetry Operator | FinOps, SRE | https://github.com/open-telemetry/opentelemetry-operator |
| Prometheus | FinOps, SRE | https://github.com/prometheus/prometheus |

### Installing Observability stack for SRE scenarios
Run:
```bash
make deploy_observability_stack
```

### Uninstalling Observability stack for SRE scenarios
Run:
```bash
make undeploy_observability_stack
```

### Installing FinOps stack (Observability stack + OpenCost + Metrics Server) for FinOps scenarios
Run:
```bash
make deploy_finops_stack
```

### Uninstalling FinOps stack for FinOps scenarios
Run:
```bash
make undeploy_finops_stack
```
