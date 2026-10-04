# Scenarios

All benchmark scenarios available in ITBench.

| ID | Domains | Applications | Faults |
| -- | ------- | ------------ | ------ |
| 16 | sre | opentelemetry-demo | modified-kubernetes-workload-container-environment-variable |
| 20 | sre | opentelemetry-demo | nonexistent-kubernetes-workload-container-image |
| 23 | sre | opentelemetry-demo | unsupported-architecture-kubernetes-workload-container-image |
| 24 | sre | opentelemetry-demo | modified-kubernetes-workload-container-environment-variable |
| 30 | sre | opentelemetry-demo | modified-target-port-kubernetes-service |
| 31 | sre | opentelemetry-demo | ingress-port-blocking-network-policy |
| 33 | sre | opentelemetry-demo | nonexistent-kubernetes-workload-node, nonexistent-kubernetes-workload-node |
| 34 | sre | opentelemetry-demo | valkey-workload-changed-password |
| 36 | sre | book-info | invalid-kubernetes-service-selector |
| 37 | finops | opentelemetry-demo |  |
| 38 | finops | opentelemetry-demo | misconfigured-kubernetes-horizontal-pod-autoscaler, misconfigured-kubernetes-horizontal-pod-autoscaler, misconfigured-kubernetes-horizontal-pod-autoscaler |
| 39 | sre | opentelemetry-demo | cordoned-kubernetes-worker-node |
| 40 | sre | opentelemetry-demo | valkey-workload-out-of-memory |
| 42 | sre | opentelemetry-demo | priority-kubernetes-workload-priority-preemption |
| 43 | sre | opentelemetry-demo | failing-name-resolution-kubernetes-workload-dns-policy |
| 44 | sre | opentelemetry-demo | unschedulable-kubernetes-workload-pod-anti-affinity-rule |
| 45 | sre | opentelemetry-demo | hanging-kubernetes-workload-init-container |
| 46 | sre | opentelemetry-demo | insufficient-kubernetes-workload-container-resources |
| 47 | sre | book-info | traffic-denying-istio-gateway-authorization-policy |
| 48 | sre | book-info | disabled-istio-ambient-mode-kubernetes-namespace |
| 49 | sre | opentelemetry-demo | misconfigured-kubernetes-workload-container-readiness-probe |
| 50 | sre | book-info | strict-mutual-tls-istio-service-mesh-enforcement |
| 53 | sre | book-info | nonexistent-kubernetes-workload-persistent-volume-claim |
| 56 | sre | opentelemetry-demo | nonexistent-kubernetes-workload-container-image |
| 57 | sre | opentelemetry-demo | unsupported-architecture-kubernetes-workload-container-image |
| 58 | sre | opentelemetry-demo | scaled-to-zero-kubernetes-workload |
| 59 | sre | opentelemetry-demo | crashing-kubernetes-workload-init-container |
| 60 | sre | opentelemetry-demo | crashing-kubernetes-workload-init-container, unsupported-architecture-kubernetes-workload-container-image |
| 63 | sre | opentelemetry-demo | corrupted-kubernetes-secret-credentials |
| 102 | sre | opentelemetry-demo | insufficient-kubernetes-resource-quota |
| 105 | sre | opentelemetry-demo | invalid-kubernetes-workload-container-command |
| 114 | sre | opentelemetry-demo | deleted-kubernetes-service |
| 116 | sre | opentelemetry-demo | degraded-etcd-database-storage |

## Usage

```bash
itbench deploy applications --scenario <id>
itbench list scenarios
```
