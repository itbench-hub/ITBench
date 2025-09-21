# ITBench: Faults

A fault is a solvable issue injected into an environment to create an incident.

| Name | Allows Force Restart | Removable Without Application Re-Install |
| --- | --- | --- |
| [Astronomy Shop - Feature Flags](#astronomy-shop---feature-flags-flagd) | No | Yes |
| [Chaos Mesh](#chaos-mesh-experiments) | No | Yes |
| [Custom - Invalid Workload Command](#custom---invalid-workload-command) | Yes | No |
| [Custom - Invalid Workload Image](#custom---invalid-workload-image) | Yes | No |
| [Custom - Invalid Node Selector](#custom---invalid-node-selector) | No | No |
| [Custom - Misconfigured Horizontal Pod Autoscaler](#custom---misconfigured-horizontal-pod-autoscaler) | No | No |
| [Custom - Misconfigured Network Policy](#custom---misconfigured-network-policy) | No | No |
| [Custom - Misconfigured Resource Quota](#custom---misconfigured-resource-quota) | No | No |
| [Custom - Misconfigured Service Port](#custom---misconfigured-service-port) | No | No |
| [Custom - Modify Environment Variables](#custom---modify-environment-variables) | No | No |
| [Custom - Unsupported Image](#custom---unsupported-image) | Yes | No |
| [Valkey - Invalid Password](#valkey---invalid-password) | No | No |

_Note:_ `Allows Force Restart` refers to how a workload is restarted after the fault is injected. In faults where the option is available, if the `restart_policy` is not set to `force`, the workload will only be updated with the fault. This means that the old pod will still be active and the new pod will experience the fault. This changes which alerts fire in relation to the fault. If the old pod is to be removed, the workload will be scaled down to 0 and then back up to the original count. This ensures that only the pods in the environment are those with the injected fault.

_Note:_ Properly removing faults is sometimes non-trivial, especially when agents may be trying a variety of techniques to fix the issue. Due to this, many faults - during their removal phase - suggest to uninstall the application and re-install it in order to ensure that the environment has been properly reset. The faults which do not require a step are indicated in the chart above. This does not mean that `make remove_incident_fault` should not be called as there are sometimes additional objects which can and should be removed.

## Astronomy Shop - Feature Flags (Flagd)

Astronomy Shop contains faults which are triggered through feature flag usage. The flags themselves are documented [here](https://opentelemetry.io/docs/demo/feature-flags/).

Injection tasks are described [here](../roles/faults/tasks/inject_otel_demo_flagd.yaml) and removal tasks are described [here](../roles/faults/tasks/remove_otel_demo_flagd.yaml).

**Example:** [Incident 3](../roles/incidents/files/specs/incident_3.yaml)

## Chaos Mesh Experiments

Chaos Mesh has many faults which can be configured to target many workloads. In ITBench, the faults are injected via a [`Schedule`](https://chaos-mesh.org/docs/define-scheduling-rules/) in order to ensure continuous nature of the problem until it is removed. The [Chaos Mesh docs](https://chaos-mesh.org/docs/) can be consulted for creating new faults.

Injection tasks are described [here](../roles/faults/tasks/inject_chaos_mesh.yaml) and removal tasks are described [here](../roles/faults/tasks/remove_chaos_mesh.yaml).

**Examples:** [Incident 26](../roles/incidents/files/specs/incident_26.yaml), [Incident 27](../roles/incidents/files/specs/incident_27.yaml)

## Custom - Invalid Node Selector

This fault changes the node selector of a given workload. This node does not exist and thus causes the pod to never be scheduled.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_invalid_node_selector.yaml).

**Example:** [Incident 33](../roles/incidents/files/specs/incident_33.yaml)

## Custom - Invalid Workload Command

This fault changes the command of a given workload's container. This command is not actionable and thus causes a pod to fail.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_invalid_command.yaml).

**Example:** [Incident 105](../roles/incidents/files/specs/incident_105.yaml)

## Custom - Invalid Workload Image

This fault changes the image of a given workload's container. This image does not exist and thus causes a pod to fail.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_invalid_image.yaml).

**Example:** [Incident 20](../roles/incidents/files/specs/incident_20.yaml)

## Custom - Misconfigured Horizontal Pod Autoscaler

This fault changes the `metrics` parameters of a given HPA uses in order to [scale workloads](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale-walkthrough/). This causes the HPA to be unnecessarily aggressive and scale up pods faster than necessary.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_misconfigured_horizontal_pod_autoscaler.yaml).

**Example:** [Incident 38](../roles/incidents/files/specs/incident_38.yaml)

## Custom - Misconfigured Network Policy

This fault adds a network policy to the application's namespace. This policy is configured to [block access to a given workload](https://kubernetes.io/docs/concepts/services-networking/network-policies/). This should result in communication errors to that pod.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_misconfigured_network_policy.yaml).

**Example:** [Incident 31](../roles/incidents/files/specs/incident_31.yaml)

## Custom - Misconfigured Persistent Volume Claim

This fault creates a persistent volume claim with an invalid storage class and assigns it to a given workload. This prevents a pod from starting because the volume will never be made ready.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_misconfigured_persistent_volume_claim.yaml).

## Custom - Misconfigured Resource Quota

This fault adds a resource quota to the application's namesapce. This [quota](https://kubernetes.io/docs/concepts/policy/resource-quotas/) is designed to be very small and thus block any new pods from being scheduled. This causes the given workload to be blocked when it is force restarted.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_misconfigured_resource_quota.yaml).

**Example:** [Incident 102](../roles/incidents/files/specs/incident_102.yaml)

## Custom - Misconfigured Service Port

This fault changes the `targetPort` of a given service. This should result in communication failures with the pod as the expected port is no longer available.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_misconfigured_service_port.yaml).

**Example:** [Incident 30](../roles/incidents/files/specs/incident_30.yaml)

## Custom - Modify Environment Variables

This fault changes the matching environment variable(s) of a given workload's container. Many workloads use environment variables to configure or change their behavior. Thus the expression of this change is dynamic.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_modify_environment_variables.yaml).

**Example:** [Incident 16](../roles/incidents/files/specs/incident_16.yaml)

## Custom - Unsupported Image

This fault changes the image of a given workload's container. This image is in an architecture that cannot be run on the node and thus causes a pod to fail.

Injection tasks are described [here](../roles/faults/tasks/inject_custom_unsupported_image.yaml).

**Example:** [Incident 23](../roles/incidents/files/specs/incident_23.yaml)

## Valkey - Invalid Password

This fault changes the password of a given Valkey workload to cause unauthorized access issues within an application. It assumes that the original password is an empty string (no password).

Injection tasks are described [here](../roles/faults/tasks/inject_valkey_invalid_password.yaml).

**Example:** [Incident 34](../roles/incidents/files/specs/incident_34.yaml)
