## v1.4.1 (2026-01-12)

### Feat

- autogeneration of scenario files (https://github.com/itbench-hub/ITBench-Scenarios/pull/457)
- create scenario library json for indexing and search (https://github.com/itbench-hub/ITBench-Scenarios/pull/429)

### Fix

- update incident 20, 23, 27, 31, 105 ground truths (https://github.com/itbench-hub/ITBench-Scenarios/pull/472)

## v1.4.0 (2025-12-11)

### Feat

- add cordoned node fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/427)
- add pod priority eviction fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/428)
- add dns policy misconfiguration fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/398)
- add mutual tls enforcement fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/358)
- add misconfigured readiness probe fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/401)
- add disable ambient mode fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/431)
- add exhaust node memory scenario (https://github.com/itbench-hub/ITBench-Scenarios/pull/329)
- add misconfigured istio authorization policy fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/432)
- add database resource limit fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/336)
- add hanging init container fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/389)
- add unscheduleable pod anti-affinity rule fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/430)
- add Istio's bookinfo application (https://github.com/itbench-hub/ITBench-Scenarios/pull/386)

### Fix

- ensure valkey fill storage fault persists (https://github.com/itbench-hub/ITBench-Scenarios/pull/455)
- disable firing alerts and correct otel-demo telemetry metric configuration (https://github.com/itbench-hub/ITBench-Scenarios/pull/445)

### Refactor

- consolidate deployment of application prometheus rules (https://github.com/itbench-hub/ITBench-Scenarios/pull/454)

## v1.3.0 (2025-11-23)

### Feat

- add Kubernetes Gateway API (https://github.com/itbench-hub/ITBench-Scenarios/pull/402)
- create fault library json for indexing and search (https://github.com/itbench-hub/ITBench-Scenarios/pull/382)

### Refactor

- reorganize tool installation and uninstallation tasks; remove tool reinitialization tasks (https://github.com/itbench-hub/ITBench-Scenarios/pull/414)

## v1.2.0 (2025-11-12)

### Feat

- configure duration for AWX pipeline pauses (https://github.com/itbench-hub/ITBench-Scenarios/pull/387)
- enable NAT-based setup with ElasticIPs in AWX stack (https://github.com/itbench-hub/ITBench-Scenarios/pull/375)
- enable BYOM or custom models hosted on watsonx.ai (https://github.com/itbench-hub/ITBench-Scenarios/pull/374)
- add full storage database fault (https://github.com/itbench-hub/ITBench-Scenarios/pull/345)
- use custom otel-collector in stack (https://github.com/itbench-hub/ITBench-Scenarios/pull/341)
- add istio tool (https://github.com/itbench-hub/ITBench-Scenarios/pull/338)

### Fix

- pin versions for AWX execution environment (EE) image dependencies (https://github.com/itbench-hub/ITBench-Scenarios/pull/384)
- correct issues identified during E2E runs (https://github.com/itbench-hub/ITBench-Scenarios/pull/361)
- disable CGO_ENABLED during Docker builds (https://github.com/itbench-hub/ITBench-Scenarios/pull/355)

### Refactor

- deploy Istio in ambient mode (https://github.com/itbench-hub/ITBench-Scenarios/pull/385)
- creating version schema for incident spec (https://github.com/itbench-hub/ITBench-Scenarios/pull/369)
- update reinit process to not need `tools_required` inputs (https://github.com/itbench-hub/ITBench-Scenarios/pull/371)

## v1.1.0 (2025-10-24)

### Feat

- add custom opentelemetry collector (https://github.com/itbench-hub/ITBench-Scenarios/pull/337)
- remake issue templates (https://github.com/itbench-hub/ITBench-Scenarios/pull/294)
- add AWX smoke tests (https://github.com/itbench-hub/ITBench-Scenarios/pull/310)
- add Kind support for AWX setup (https://github.com/itbench-hub/ITBench-Scenarios/pull/269)
- refactor AWX CronJobs as StatefulSets (https://github.com/itbench-hub/ITBench-Scenarios/pull/208)
- add agent role for telemetry access (https://github.com/itbench-hub/ITBench-Scenarios/pull/224)
- add new sample incidents (https://github.com/itbench-hub/ITBench-Scenarios/pull/183)

### Fix

- **runner**: complete corrections to AWX pipeline (https://github.com/itbench-hub/ITBench-Scenarios/pull/327)
- correct copy path for otel collector binary (https://github.com/itbench-hub/ITBench-Scenarios/pull/354)
- correct entrypoint of opentelemetry collector image (https://github.com/itbench-hub/ITBench-Scenarios/pull/352)
- correct opentelemetry-collector-merge job (https://github.com/itbench-hub/ITBench-Scenarios/pull/339)
- revert changes made to AWX playbook (https://github.com/itbench-hub/ITBench-Scenarios/pull/331)
- **awx**: update manage_awx.yaml to use experiments.incidents (https://github.com/itbench-hub/ITBench-Scenarios/pull/323)
- correct invocation of topology recorder in AWX pipeline (https://github.com/itbench-hub/ITBench-Scenarios/pull/312)
- create separate commands for creating a kind cluster (https://github.com/itbench-hub/ITBench-Scenarios/pull/309)
- update runner github group vars (https://github.com/itbench-hub/ITBench-Scenarios/pull/252)
- ensure all architectures are pushed to Quay (https://github.com/itbench-hub/ITBench-Scenarios/pull/251)
- update role tasks to pass lint tests (https://github.com/itbench-hub/ITBench-Scenarios/pull/180)
- use Clickhouse Installation objects instead of Helm chart (https://github.com/itbench-hub/ITBench-Scenarios/pull/173)
- remove login requirements for build test (https://github.com/itbench-hub/ITBench-Scenarios/pull/177)
- update path filtering for workflows (https://github.com/itbench-hub/ITBench-Scenarios/pull/174)

### Refactor

- implement assertion JSON tasks as leaderboard role tasks (https://github.com/itbench-hub/ITBench-Scenarios/pull/212)
- update implementation of bundle info command (https://github.com/itbench-hub/ITBench-Scenarios/pull/221)

## v1.0.0 (2025-07-23)

### Fix

- correct unexpected line break error (https://github.com/itbench-hub/ITBench-Scenarios/pull/139)
- allow chaos-mesh faults to affect all pods (https://github.com/itbench-hub/ITBench-Scenarios/pull/136)

### Refactor

- clean sre scenario runner codebase (https://github.com/itbench-hub/ITBench-Scenarios/pull/107)

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
