# Faults

All benchmark faults available in ITBench.

| Slug | Name | Platform | Tags | Alerts | Description |
| ---- | ---- | -------- | ---- | ------ | ----------- |
| `cordoned-kubernetes-worker-node` | Cordoned Kubernetes Worker Node | Kubernetes | Deployment, Performance | KubePodNotReady | This fault places a workload on a node and prevents it from scaling by blocking all new scheduling attempts. |
| `corrupted-kubernetes-secret-credentials` | Corrupted Kubernetes Secret Credentials | Kubernetes | Authentication, Deployment | HighRequestErrorRate | This fault corrupts a Kubernetes Secret by replacing its data with invalid credentials,  simulating real-world incidents where secret rotation failures, registry authentication issues,  or Vault access problems cause service outages. |
| `crashing-kubernetes-workload-init-container` | Crashing Kubernetes Workload Init Container | Kubernetes | Code, Deployment, Performance | KubeContainerWaiting | This fault injects an init container that crashes due to a bad script. |
| `degraded-etcd-database-storage` | Degraded Etcd Database Storage | Kubernetes | Performance | HighRequestLatency | This fault creates etcd storage pressure by writing a large number of ConfigMaps,  causing increased API server latency and degraded cluster performance.  This simulates real-world incidents where etcd storage growth causes progressive degradation of cluster operations. |
| `deleted-kubernetes-service` | Deleted Kubernetes Service | Kubernetes | Deployment, Networking | HighRequestErrorRate | This fault deletes the services attached to a Kubernetes workload, preventing other workloads from being able to communicate with it. |
| `disabled-istio-ambient-mode-kubernetes-namespace` | Disabled Istio Ambient Mode Kubernetes Namespace | Kubernetes | Deployment, Networking | NoRequestsReceived | This fault modifies a namespace, disabling it from being included in Istio's Ambient Mode service mesh. |
| `failing-name-resolution-kubernetes-workload-dns-policy` | Failing Name Resolution Kubernetes Workload DNS Policy | Kubernetes | Deployment, Networking | HighRequestErrorRate | This fault injects an DNS policy which results in the workload being unable to resolve the name of outgoing services. |
| `hanging-kubernetes-workload-init-container` | Hanging Kubernetes Workload Init Container | Kubernetes | Deployment, Performance | KubeContainerWaiting | This fault injects an init container which will hang into a workload. |
| `ingress-port-blocking-network-policy` | Ingress Port Blocking Network Policy | Kubernetes | Deployment, Networking | NoRequestsReceived, HighRequestErrorRate | This fault injects a network policy which blocks traffic on all ingress ports of a given workload. |
| `insufficient-kubernetes-resource-quota` | Insufficient Kubernetes Resource Quota | Kubernetes | Deployment, Performance | KubePodNotReady | This fault injects a resource quota with hard resource requirements that are underprovisioned for the namespace. |
| `insufficient-kubernetes-workload-container-resources` | Insufficient Kubernetes Workload Container Resources | Kubernetes | Deployment, Performance | KubePodCrashLooping | This fault injects a insufficient resource configuration into a designated Kubernetes workload's container. |
| `invalid-kubernetes-service-selector` | Invalid Kubernetes Service Selector | Kubernetes | Deployment, Networking | HighRequestErrorRate | This fault modifies an existing service's selector, causing the service to be unable to find its intended workload. |
| `invalid-kubernetes-workload-container-command` | Invalid Kubernetes Workload Container Command | Kubernetes | Deployment, Performance | KubePodCrashLooping | This fault injects an invalid command into a designated Kubernetes workload's container. |
| `kubernetes-api-server-request-surge` | Kubernetes API Server Request Surge | Kubernetes | Deployment, Performance | HighRequestLatency | This fault injects a workload which causes a surge in requests to the API server, causing performance degredation. |
| `misconfigured-kubernetes-horizontal-pod-autoscaler` | Misconfigured Kubernetes Horizontal Pod Autoscaler | Kubernetes | Deployment, Performance | KubeHpaMaxedOut | This fault injects a configuration into a horizontal pod autoscaler that causes it to react to low resource usage |
| `misconfigured-kubernetes-workload-container-readiness-probe` | Misconfigured Kubernetes Workload Container Readiness Probe | Kubernetes | Deployment, Performance | KubePodNotReady | This fault injects a misconfigured readiness probe into a workload container. This probe blocks the pod from starting up. |
| `modified-kubernetes-workload-container-environment-variable` | Modified Kubernetes Workload Container Environment Variable | Kubernetes | Deployment, Performance |  | This fault overwrites an environment variable value with one provided in the argument. |
| `modified-target-port-kubernetes-service` | Modified Target Port Kubernetes Service | Kubernetes | Deployment, Networking | HighRequestErrorRate | This fault overwrites the designated target port with a different number. |
| `nonexistent-kubernetes-workload-container-image` | Nonexistent Kubernetes Workload Container Image | Kubernetes | Deployment, Performance | KubePodNotReady | This fault injects an nonexistent image into a designated Kubernetes workload's container. |
| `nonexistent-kubernetes-workload-node` | Nonexistent Kubernetes Workload Node | Kubernetes | Deployment, Performance | KubePodNotReady | This fault injects a node selector for an nonexistent node into a designated Kubernetes workload. |
| `nonexistent-kubernetes-workload-persistent-volume-claim` | Nonexistent Kubernetes Workload Persistent Volume Claim | Kubernetes | Deployment | KubePodNotReady | This fault injects a workload with a nonexistent volume. |
| `opentelemetry-demo-feature-flag` | OpenTelemetry Demo Feature Flag | Kubernetes | Deployment, Performance |  | This fault activates an implemented fault in the OpenTelemetry Demo. |
| `priority-kubernetes-workload-priority-preemption` | Priority Kubernetes Workload Priority Preemption | Kubernetes | Deployment, Performance | KubePodNotReady | This fault causes a workload to be a lower priority than another. This causes the pod to be evicted when the higher priority workload needs more resources. |
| `scaled-to-zero-kubernetes-workload` | Scaled To Zero Kubernetes Workload | Kubernetes | Deployment, Performance | NoRequestsReceived, HighRequestErrorRate | This fault scales a Kubernetes workload to 0. |
| `scheduled-chaos-mesh-experiment` | Scheduled Chaos Mesh Experiment | Kubernetes | Deployment, Performance |  | This fault injects a Chaos Mesh experiment into the environment. The experiment is [scheduled](https://chaos-mesh.org/docs/define-scheduling-rules/) to repeated fire so that the behavior persists. |
| `strict-mutual-tls-istio-service-mesh-enforcement` | Strict Mutual TLS Istio Service Mesh Enforcement | Kubernetes | Deployment, Networking | HighRequestErrorRate | This fault injects a policy which causes the affected workload to be unable to communicate with other pods in the service mesh. |
| `traffic-denying-istio-gateway-authorization-policy` | Traffic Denying Istio Gateway Authorization Policy | Kubernetes | Deployment, Networking | NoRequestsReceived | This fault injects an authorization policy which denies all HTTP requests to a Kubernetes Gateway. |
| `unassigned-kubernetes-workload-container-resource-limits` | Unassigned Kubernetes Workload Container Resource Limits | Kubernetes | Deployment, Performance |  | This fault removes the resource limits of an indicated workload container. |
| `unschedulable-kubernetes-workload-pod-anti-affinity-rule` | Unschedulable Kubernetes Workload Pod Anti Affinity Rule | Kubernetes | Deployment, Performance | KubePodNotReady | This fault injects an Inter-Pod Anti-Affinity which causes Kubernetes to be unable to schedule the pod. |
| `unsupported-architecture-kubernetes-workload-container-image` | Unsupported Architecture Kubernetes Workload Container Image | Kubernetes | Deployment, Performance | KubePodNotReady | This fault injects an image with an unsupported architecture into a designated Kubernetes workload's container and assigns it to a node. |
| `valkey-workload-changed-password` | Valkey Workload Changed Password | Kubernetes | Deployment, Authentication | HighRequestLatency | This fault changes the password of a Valkey workload. |
| `valkey-workload-out-of-memory` | Valkey Workload Out of Memory | Kubernetes | Deployment, Code | KubePodCrashLooping | This fault adds a code change to a Valkey workload. This modifies the container to also contain a process which will consume memory. |

## Usage

```yaml
# itbench explain fault <slug>
# itbench list faults --tag Networking
# itbench list faults --platform Kubernetes
```

### Scenario YAML snippet

```yaml
environment:
  applications:
    - id: <application-slug>
  domains:
    - sre
faults:
  - injections:
      - id: <fault-slug>
        targets:
          - kubernetes:
              apiVersion: apps/v1
              kind: Deployment
              name: <workload-name>
              namespace: <namespace>
```
