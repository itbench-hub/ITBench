## v0.0.3 (2025-05-08)

### Feat

- add OpenShift deployment functionality for observability stack and sample applications (#110)
- replace Bitnami Elasticsearch and Grafana Loki with Altinity Clickhouse (#10)
- switch from kube-prometheus-stack chart to prometheus chart (#7)

### Fix

- add Content-Security-Policy headers to Ingress traffic (#121)
- correct load-generator service/container name in Prometheus alerting rules (#100)
- making the alert IDs consistent with Prometheus rules (#85)
- update file locations for e2e tasks (#79)
- making the `observability_url` consistent with the ITBench-SRE-Agent (#71)
- add Prometheus metric scrape jobs configurations (#68)
- choose unsupported architecture for incident 23 (#67)
- update jaeger reference in hotel reservation installation (#69)
- correct alert retrievals when ingress is not available (#45)

## v0.0.2 (2025-04-07)

### Fix

- increase Astronomy Shop resource limits to avoid OOM errors (#39)
- correct LLMConfigModelAgent class variables (#24)
- update e2e environment variables and scripts (#21)
- correct s3_endpoint_url references (#16)
- correct typo (#12)

## v0.0.1 (2025-03-20)

This pre-release is the version (with fixes) used for in the ICML paper described [here](https://github.com/IBM/ITBench).

### Feat

- add CODEOWNERS (#2)
- add CISO incidents (#1)
- add SRE incidents (#6)
