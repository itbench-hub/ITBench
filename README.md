# ITBench-Scenarios
Code repository for scenarios and environment setup as part of ITBench

ITBench incorporates a collection of problems that we call scenarios. For example, one of the SRE scenarios in ITBench is to resolve a “High error rate on service order-management” in a Kubernetes environment. Another scenario that is relevant for the CISO persona involves assessing the compliance posture for a “new control rule detected for RHEL 9.” Each of the ITBench scenarios are deployed in an operational environment in which problem(s) occur. 

## [CISO Scenarios](./ciso)
These scenarios simulate compliance-related misconfigurations. Each scenario provides:
- A pre-configured environment with specific compliance issues
- Tools to detect misconfigurations
- Validation methods to verify successful remediation
CISO scenarios are located [here](./ciso).

## [SRE Scenarios](./sre)
These scenarios focus on observability and incident response. Each scenario includes:
- A comprehensive observability stack deployment featuring:
  - Prometheus for metrics collection
  - Grafana for visualization and single mode of API interactions for agents 
  - Loki for log aggregation
  - Elasticsearch and OpenSearch for search and analytics
  - Jaeger for distributed tracing
  - Kubernetes events exporter
- Simulated faults that trigger service degradation
- Thereby leading to alerts associated with application performance issues such as increased error rates and latency spikes
  SRE scenarios are located [here](./sre).

## [FinOps Scenarios](./sre)
Each scenario includes:
- The core SRE observability stack
- OpenCost integration for cost monitoring
- Simulated faults trigger cost overrun alerts
 FinOps scenarios are located [here](./sre) along-side SRE scenarios.
