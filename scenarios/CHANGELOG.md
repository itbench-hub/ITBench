## v0.0.3 (2025-05-08)

### Feat

- add OpenShift deployment functionality for observability stack and sample applications (https://github.com/itbench-hub/ITBench-Scenarios/pull/110)
- replace Bitnami Elasticsearch and Grafana Loki with Altinity Clickhouse (https://github.com/itbench-hub/ITBench-Scenarios/pull/10)
- switch from kube-prometheus-stack chart to prometheus chart (https://github.com/itbench-hub/ITBench-Scenarios/pull/7)

### Fix

- add Content-Security-Policy headers to Ingress traffic (https://github.com/itbench-hub/ITBench-Scenarios/pull/121)
- correct load-generator service/container name in Prometheus alerting rules (https://github.com/itbench-hub/ITBench-Scenarios/pull/100)
- making the alert IDs consistent with Prometheus rules (https://github.com/itbench-hub/ITBench-Scenarios/pull/85)
- update file locations for e2e tasks (https://github.com/itbench-hub/ITBench-Scenarios/pull/79)
- making the `observability_url` consistent with the ITBench-SRE-Agent (https://github.com/itbench-hub/ITBench-Scenarios/pull/71)
- add Prometheus metric scrape jobs configurations (https://github.com/itbench-hub/ITBench-Scenarios/pull/68)
- choose unsupported architecture for incident 23 (https://github.com/itbench-hub/ITBench-Scenarios/pull/67)
- update jaeger reference in hotel reservation installation (https://github.com/itbench-hub/ITBench-Scenarios/pull/69)
- correct alert retrievals when ingress is not available (https://github.com/itbench-hub/ITBench-Scenarios/pull/45)

## v0.0.2 (2025-04-07)

### Fix

- increase Astronomy Shop resource limits to avoid OOM errors (https://github.com/itbench-hub/ITBench-Scenarios/pull/39)
- correct LLMConfigModelAgent class variables (https://github.com/itbench-hub/ITBench-Scenarios/pull/24)
- update e2e environment variables and scripts (https://github.com/itbench-hub/ITBench-Scenarios/pull/21)
- correct s3_endpoint_url references (https://github.com/itbench-hub/ITBench-Scenarios/pull/16)
- correct typo (https://github.com/itbench-hub/ITBench-Scenarios/pull/12)

## v0.0.1 (2025-03-20)

This pre-release is the version (with fixes) used for in the ICML paper described [here](https://github.com/IBM/ITBench).

### Feat

- add CODEOWNERS (https://github.com/itbench-hub/ITBench-Scenarios/pull/2)
- add CISO incidents (https://github.com/itbench-hub/ITBench-Scenarios/pull/1)
- add SRE incidents (https://github.com/itbench-hub/ITBench-Scenarios/pull/6)
