# Waiters

Built-in waiter primitives used in scenario `waitFor` blocks.

| ID | Name | Platforms | Description |
| -- | ---- | --------- | ----------- |
| `delete-workload-pods` | Delete Workload Pods | Kubernetes, OpenShift | Deletes all the pods associated with a Kubernetes workload. |
| `pause-execution` | Pause Execution | Localhost | Pauses for the requested number of seconds. |
| `restart-kubernetes-workload` | Restart Kubernetes Workload | Kubernetes, OpenShift | Waits for a Kubernetes workload to be restarted. |
| `scale-kubernetes-workload` | Scale Kubernetes Workload | Kubernetes, OpenShift | Waits for a Kubernetes workload to scale to the requested number of replicas. |
| `unassign-workload-container-resource-limits` | Unassign Workload Container Resource Limits | Kubernetes, OpenShift | Removes the resource limits of a container in a Kubernetes workload. |

## Usage

```yaml
# itbench explain waiter <id>
# itbench list waiters
```

### Scenario YAML snippet

```yaml
faults:
  - waitFor:
      postInjection:
        - id: restart-kubernetes-workload
          workload:
            apiVersion: apps/v1
            kind: Deployment
            name: <workload-name>
            namespace: <namespace>
```
