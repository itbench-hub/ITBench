# ITBench on Argo Workflows

## Overview

ITBench uses [Argo Workflows](https://github.com/argoproj/argo-workflows) for managing multi-trial benchmark executions across multiple clusters. This is primarily used for SRE and FinOps scenarios, where the results of the agent's diagnosis and remediation attempts are nondeterministic.

## Requirements

The benchmark runner image (`quay.io/it-bench/bench-runner`) is built and supplied by ITBench. The ITBench required software and dependencies still need to be installed on the local machine in order to run the Ansible commands that set up the Argo stack.

For the clusters running the experiments (also referred to as `runners`), please ensure that each node has **at least**: [8 CPUs, 16 GB of memory, 50 GB of disk storage](./hardware-specification.md#local-development-kind-minikube-etc). These are the minimum requirements for running ITBench on a single cluster.

If running both Argo Workflows and a `runner` on the same cluster (i.e. Kind, Minikube, etc.), the machine needs enough resources to handle both workloads simultaneously. Generally, it is not recommended to run both on the same cluster outside of testing purposes.

>[!WARNING]
>When creating an Argo stack with our provided setup for [`Kind`](../../clusters/kind/README.md) or [AWS and `kOps`](../../clusters/kops/README.md), this hardware check is done as part of the creation process. It will produce a warning message in the console when the machine lacks the necessary requirements. **When running on an underprovisioned cluster, poor performance is expected.**

## Set Up

ITBench defines an Argo setup as a stack. This Argo stack has two components: one cluster which acts as the `head` (the orchestrator) and one or more cluster(s) which act as `runners`. When using a local machine, the `head` and the `runner` can be the same, but — as noted in the [requirements](#requirements) section — this requires more resources. The `head` cluster is where Argo Workflows will be installed. The `runners` are used by the `head` cluster to execute the scenarios.

Each scenario step runs as a container in the Argo workflow using the `bench-runner` image. The image contains all ITBench playbooks and scenario manifests baked in. Runner cluster credentials are mounted into each container from a Kubernetes Secret — no credentials are stored in the image or passed over the network at runtime.

### Argo Workflows with SRE and FinOps Scenarios

The playbooks feature a number of [group variables](../../scenarios/sre/inventory/group_vars/). Each one will be described here:

| File Name | Function |
| --- | --- |
| [agent.yaml](../../scenarios/sre/inventory/group_vars/runner/agent.yaml.example) | Configures the agent configuration and version |
| [experiments.yaml](../../scenarios/sre/inventory/group_vars/runner/experiments.yaml.example) | Configures scenarios, number of trials, and workflow type to run |
| [stack.yaml](../../scenarios/sre/inventory/group_vars/runner/stack.yaml.example) | Configures the head and runner clusters |
| [storage.yaml](../../scenarios/sre/inventory/group_vars/all/storage.yaml.example) | Configures the storage options for data files |

>[!NOTE]
>Some of the yaml files have sections commented out. This is to show parameters which are optional. If they are not needed, leave them commented out. Otherwise, uncomment them and fill them out as needed.

#### `experiments.yaml` shape

Each entry in `argo_experiments` defines one set of runs:

```yaml
argo_experiments:
  - scenario: 1
    trials: 2
    workflow: data-collection
```

The `workflow` field controls which steps execute per scenario run:

| Value | Steps executed |
| --- | --- |
| `data-collection` | deploy tools → deploy applications → clear events → deploy recorders → inject faults → remove faults → undeploy recorders → undeploy applications → undeploy tools |
| `start-scenario` | deploy tools → deploy applications → clear events → deploy recorders → inject faults |
| `stop-scenario` | remove faults → undeploy recorders → undeploy applications → undeploy tools |

#### `stack.yaml` shape

```yaml
stack:
  argo:
    kubeconfig: ~/.kube/config   # kubeconfig for the head/orchestrator cluster
  runners:
    kubeconfigs:
      - ~/.kube/config           # one entry per runner cluster
```

After creating an Argo stack, go to the `scenarios/sre` directory.

#### Creation

1. Create and configure the group variables.
```shell
make group-vars
```

>[!TIP]
>If using [our kops setup](../../clusters/kops/README.md), use `make sync-stack-group-vars` to export the kubeconfig files and configure the [`stack.yaml`](../../scenarios/sre/inventory/group_vars/runner/stack.yaml) group variables. If using [our kind setup](../../clusters/kind/README.md), the default group variables made at creation will suffice.

>[!WARNING]
>If the group variables were already created as part of development or running the SRE and FinOps scenarios beforehand, skip this step. Running the command will override the existing files.

2. Install Argo Workflows on the `head` cluster and upload all scenario manifests and runner credentials.
```shell
make deploy-argo
```

This single command performs the full install-and-configure pass:
- Installs the Argo Workflows Helm chart into the `argo` namespace
- Creates a `runner-{N}-kubeconfig` Kubernetes Secret for each runner
- Creates a `scenario-{id}` ConfigMap for each scenario listed in `argo_experiments`
- Applies the `itbench-steps`, `itbench-scenario-execution`, and `itbench-orchestration-runner-{N}` WorkflowTemplates

Installation takes around 5 minutes.

>[!WARNING]
>Ensure that the head cluster has a working storage class available. Without it, the Argo Workflows installation may fail. If using one of [our cluster setups](../../clusters/), then this should be taken care of.

#### Scenario Execution

Once the Argo stack is deployed, workflows are submitted as Argo `Workflow` CRs that reference the orchestration `WorkflowTemplate` for each runner. Each workflow runs the configured scenarios sequentially on that runner, for the requested number of trials.

Multiple runners execute in parallel — each runner is assigned a round-robin subset of the scenarios listed in `argo_experiments`. This allows balancing cost and time for multi-trial benchmark runs.

To monitor progress, use `kubectl`:
```shell
kubectl get workflows -n argo
kubectl describe workflow <workflow-name> -n argo
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name> --prefix
```

1. Launch the workflow
```shell
make launch-data-collection-workflow
```

>[!TIP]
>There are three `launch` workflow make targets:
>
>- `launch-data-collection-workflow` — full scenario lifecycle (deploy, inject, collect, teardown). Used for collecting benchmark data for [ITBench-Lite](https://huggingface.co/spaces/ibm-research/ITBench-Lite).
>- `launch-start-workflow` — deploys the environment and injects faults, leaving the scenario running for an agent to diagnose.
>- `launch-stop-workflow` — removes faults and tears down the environment after an agent run completes.
>
>`launch-start-workflow` and `launch-stop-workflow` are used by the leaderboard system and should not be needed for general use.

#### Deletion

1. Uninstall Argo Workflows from the `head` cluster.
```shell
make undeploy-argo
```

>[!WARNING]
>The runner clusters are not automatically cleaned once Argo Workflows has been uninstalled. If runs were left in an unfinished state, they need to be cleaned up manually. Retrieve the offending runner's kubeconfig path from `stack.yaml`, set it as `cluster.kubeconfig` in [`cluster.yaml`](../../scenarios/sre/inventory/group_vars/environment/cluster.yaml.example), then run `make destroy-environment` to clean the cluster.

## Troubleshooting

>[!TIP]
>Argo Workflows should not be considered a proper development environment for creating or troubleshooting scenarios. Scenarios should be developed and hardened on a standalone cluster using the single-cluster Makefile targets first, before running on the Argo stack.

### Workflow Step Failed

When a workflow step fails, the Argo controller marks that step and any dependent steps as failed and stops the workflow. Use `kubectl` to inspect the failure:

```shell
kubectl get workflows -n argo
kubectl logs -n argo -l workflows.argoproj.io/workflow=<workflow-name> --prefix
```

Once debugged, if the runner cluster was left in a dirty state (e.g. an `undeploy` step did not run), retrieve the runner's kubeconfig from `stack.yaml`, set it as `cluster.kubeconfig` in [`cluster.yaml`](../../scenarios/sre/inventory/group_vars/environment/cluster.yaml.example), and run `make destroy-environment` to clean the cluster before scheduling additional runs.
