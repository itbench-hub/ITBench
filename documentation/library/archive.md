# Archive

As an evolving benchmark, technologies and scenarios will be removed from ITBench. In the interest of transparency, those removals are documented here.

Every item below indicates its last supported release: the last release that could run it. Since releases are tagged, the full state of the repository at that point can be checked out with:

```shell
git checkout <tag>
```

Use the release tag to run archived content. Use the links to read it. Each link points to a file at the last commit before it was moved, so it may differ from the release.

## Contents

- [Book Info Scenarios](#book-info-scenarios)
- [Chaos Mesh Faults and Scenarios](#chaos-mesh-faults-and-scenarios)
- [CISO Scenarios](#ciso-scenarios)
- [Kubernetes API Server Request Surge Fault and Scenarios](#kubernetes-api-server-request-surge-fault-and-scenarios)
- [Modified Kubernetes Workload Container Environment Variable Fault and Scenarios](#modified-kubernetes-workload-container-environment-variable-fault-and-scenarios)
- [OpenTelemetry Demo Flagd Fault and Scenarios](#opentelemetry-demo-flagd-fault-and-scenarios)

## Book Info Scenarios

**Last Supported Release:** [`v1.4.1`](https://github.com/itbench-hub/ITBench/releases/tag/v1.4.1)

**Reason:** Book Info scenarios were deprecated because the application they relied on was (1) not complex enough to provide a robust environment for benchmark scenarios and (2) required a custom load generator.

**Related Files:**

- [`book-info.yaml`](https://github.com/itbench-hub/ITBench/blob/9891d5b76016df9579898882cd4ba3e03952ce0c/library/applications/book-info.yaml)
- [`book_info.yaml`](https://github.com/itbench-hub/ITBench/blob/9891d5b76016df9579898882cd4ba3e03952ce0c/scenarios/sre/project/roles/applications/defaults/main/book_info.yaml)
- [`install_book_info.yaml`](https://github.com/itbench-hub/ITBench/blob/9891d5b76016df9579898882cd4ba3e03952ce0c/scenarios/sre/project/roles/applications/tasks/install_book_info.yaml)
- [`book_info/prometheusrules.j2`](https://github.com/itbench-hub/ITBench/blob/9891d5b76016df9579898882cd4ba3e03952ce0c/scenarios/sre/project/roles/applications/templates/kubernetes/book_info/prometheusrules.j2)
- [`namespace.yaml`](https://github.com/itbench-hub/ITBench/blob/9891d5b76016df9579898882cd4ba3e03952ce0c/scenarios/sre/project/roles/applications/vars/main/namespace.yaml)

**Related Scenarios:** [36](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_36), [47](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_47), [48](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_48), [50](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_50), [53](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_53)


## Chaos Mesh Faults and Scenarios

**Last Supported Release:** [`v1.4.1`](https://github.com/itbench-hub/ITBench/releases/tag/v1.4.1)

**Reason:** Chaos Mesh faults were deprecated because (1) the solution to any of them is to remove the Chaos Mesh schedule, and (2) their wide variety made it impossible to determine which alert(s) were going to fire, which added overhead to scenario creation.

**Related Files:**

- [`inject_scheduled_chaos_mesh_experiment.yaml`](https://github.com/itbench-hub/ITBench/blob/50506e936bf628b2fe0a6bd542eeb8c2e677143f/scenarios/sre/project/roles/faults/tasks/inject_scheduled_chaos_mesh_experiment.yaml)
- [`remove_chaos_mesh_schedules.yaml`](https://github.com/itbench-hub/ITBench/blob/50506e936bf628b2fe0a6bd542eeb8c2e677143f/scenarios/sre/project/roles/faults/tasks/remove_chaos_mesh_schedules.yaml)
- [`install_chaos_mesh.yaml`](https://github.com/itbench-hub/ITBench/blob/145b2c4f3cee5ee3ffa22471664f840d79b37aba/scenarios/sre/project/roles/tools/tasks/install_chaos_mesh.yaml)
- [`uninstall_chaos_mesh.yaml`](https://github.com/itbench-hub/ITBench/blob/145b2c4f3cee5ee3ffa22471664f840d79b37aba/scenarios/sre/project/roles/tools/tasks/uninstall_chaos_mesh.yaml)

**Related Scenarios:** [17](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_17), [18](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_18), [19](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_19), [21](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_21), [22](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_22), [25](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_25), [26](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_26), [27](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_27), [29](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_29), [35](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_35), [41](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_41), [54](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_54), [55](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_55), [61](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_61), [62](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_62), [80](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_80), [81](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_81), [83](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_83), [91](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_91)

## CISO Scenarios

**Last Supported Release:** [`v1.4.1`](https://github.com/itbench-hub/ITBench/releases/tag/v1.4.1)

**Reason:** The CISO scenarios were archived because (1) they relied on a bench server calling Makefile targets and on the agent writing policies and scripts that the evaluator then ran, and (2) the agent could not be contained: scenarios 1, 2 and 4 needed broad write access to the cluster, and scenario 3 needed write access to an external RHEL9 host that ITBench never provisioned. They were replaced by CISO faults and scenarios built on the same library as the SRE ones. Scenarios 1 and 4 were reimagined as faults without agent-authored policies, and scenarios 2 and 3 have no replacement.

**Related Files:**

- [`README.md`](https://github.com/itbench-hub/ITBench/blob/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/README.md)
- [`scenario-bundles.json`](https://github.com/itbench-hub/ITBench/blob/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/scenario-bundles.json)
- [`Dockerfile`](https://github.com/itbench-hub/ITBench/blob/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/Dockerfile)
- [`prepare-kubeconfig-eks.md`](https://github.com/itbench-hub/ITBench/blob/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/prepare-kubeconfig-eks.md)
- [`prepare-kubeconfig-kind.md`](https://github.com/itbench-hub/ITBench/blob/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/prepare-kubeconfig-kind.md)

**Related Scenarios:** [1](https://github.com/itbench-hub/ITBench/tree/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/1.gen-cis-b-k8s-kyverno), [2](https://github.com/itbench-hub/ITBench/tree/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/2.gen-cis-b-k8s-kubectl-opa), [3](https://github.com/itbench-hub/ITBench/tree/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/3.gen-cis-b-rhel9-ansible-opa), [4](https://github.com/itbench-hub/ITBench/tree/e0623c4413ef07128ef7e9e9ea494ad68ff2f2b3/scenarios/ciso/4.upd-cis-b-k8s-kyverno)

**Ported to ITBench v2:**

| Archived scenario | Goal | Successor | What carries over |
| --- | --- | --- | --- |
| 1 (`cis-b.5.2.5-gen`) | Write a Kyverno policy that minimizes admission of containers sharing the host network namespace. | [64](../../library/scenarios/64/scenario.yaml) | A Kyverno policy reports on a Kubernetes workload and the agent works from that report. The agent no longer writes the policy, and the control is different (resource limits, not host networking). |
| 2 (`k8s-opa/cis-b-gen/5.2.5`) | The same control as scenario 1, written as OPA with `kubectl`. | None | |
| 3 (`rhel9/cis-b-gen/5.2.12`) | Ensure SSH X11 forwarding is disabled on a RHEL9 host. | None | |
| 4 (`policy-adapt/scenario1`) | Edit the existing Kyverno policies, without renaming or replacing them, to meet new requirements. | [65](../../library/scenarios/65/scenario.yaml) | The agent fixes an existing policy in place instead of creating a new one. The edit is limited to one field of one policy, and the new requirements are replaced by a defect (a policy that never reports). |

## Kubernetes API Server Request Surge Fault and Scenarios

**Last Supported Release:** [`v1.4.1`](https://github.com/itbench-hub/ITBench/releases/tag/v1.4.1)

**Reason:** This fault was archived because it threatens to make the cluster inoperable, preventing the observability tools from working and the orchestrator from interfacing with the cluster.

**Related Files:**

- [`inject_kubernetes_api_server_request_surge.yaml`](https://github.com/itbench-hub/ITBench/blob/50506e936bf628b2fe0a6bd542eeb8c2e677143f/scenarios/sre/project/roles/faults/tasks/inject_kubernetes_api_server_request_surge.yaml)
- [`kubernetes_api_server_request_surge` scripts](https://github.com/itbench-hub/ITBench/tree/50506e936bf628b2fe0a6bd542eeb8c2e677143f/scenarios/sre/project/roles/faults/files/scripts/kubernetes_api_server_request_surge)

**Related Scenarios:** [51](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_51)

## Modified Kubernetes Workload Container Environment Variable Fault and Scenarios

**Last Supported Release:** [`v1.4.1`](https://github.com/itbench-hub/ITBench/releases/tag/v1.4.1)

**Reason:** This fault was archived because its wide variety of possible modifications made it impossible to determine which alert(s) were going to fire, which added overhead to scenario creation.

**Related Files:**

- [`inject_modified_kubernetes_workload_container_environment_variable.yaml`](https://github.com/itbench-hub/ITBench/blob/50506e936bf628b2fe0a6bd542eeb8c2e677143f/scenarios/sre/project/roles/faults/tasks/inject_modified_kubernetes_workload_container_environment_variable.yaml)

**Related Scenarios:** [16](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_16), [24](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_24)

## OpenTelemetry Demo Flagd Fault and Scenarios

**Last Supported Release:** [`v1.4.1`](https://github.com/itbench-hub/ITBench/releases/tag/v1.4.1)

**Reason:** This fault was archived because (1) the solution to any of its variants is to change the flagd configuration, and (2) their wide variety made it impossible to determine which alert(s) were going to fire, which added overhead to scenario creation.

**Related Files:**

- [`inject_opentelemetry_demo_feature_flag.yaml`](https://github.com/itbench-hub/ITBench/blob/50506e936bf628b2fe0a6bd542eeb8c2e677143f/scenarios/sre/project/roles/faults/tasks/inject_opentelemetry_demo_feature_flag.yaml)

**Related Scenarios:** [1](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_1), [2](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_2), [3](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_3), [4](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_4), [5](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_5), [6](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_6), [7](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_7), [8](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_8), [10](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_10), [11](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_11), [12](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_12), [13](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_13), [14](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_14), [15](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_15), [52](https://github.com/itbench-hub/ITBench/tree/b254e32152f91bb33a0a2fa315c74619b494d32c/scenarios/sre/project/roles/scenarios/files/scenario_52)
