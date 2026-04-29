# Developing Faults with ITBench

As briefly explained [here](../library/faults/README.md), a **fault** is an injectable change with causes some observable issue within an environment. For example, the [`nonexistent-kubernetes-workload-container-image`](../library/faults/nonexistent-kubernetes-workload-container-image.md) fault changes a Kubernetes' workload manifest file to make the resulting pod inoperable. Depending on the workload affected, this causes more errors within an entire application as other workloads will be unable to communicate with the non-working pod.

This document will detail how to create new faults in ITBench which can be used in SRE or FinOps [scenarios](../getting-started/scenarios.md).

>[!NOTE]
>To add new faults to the ITBench project, please follow this guide and make a pull request titled: `feat: add fault <fault id>` (ie: `feat: add fault crashing-kubernetes-workload-init-container`).

## Required Software

Please follow the requirements listed [here](../getting-started/scenarios.md#required-software).

## Installation

Please follow the instructions listed [here](../getting-started/scenarios.md#installation).

## Set Up

Please follow the instructions listed [here](../getting-started/scenarios.md#setup).

## Creating Faults

### Generating Boilerplate

1. Run the following command and respond to the prompts appropriately to create a new index in the fault library:
```shell
make generate-fault-index
```

2. Run the following commands to generate the new files for the fault
```shell
make generate-docs
make generate-resource-files
```

>[!NOTE]
>These commands generate the basics needed to begin developing. One may need to make additional changes or create new files to add scripts (ie: [`crashing-kubernetes-workload-init-container`](../../scenarios/sre/project/roles/faults/tasks/inject_crashing_kubernetes_workload_init_container.yaml)).

>[!NOTE]
>To see a list of all the added and changed files, use `git status`.

### Editing New Fault

**This process is meant to be iterative.** Once the fault is confirmed to work and the index is fully filled out, move to the next phase: [validation](#validating-new-fault).

1. Edit the new fault index. This will be located in the [fault library index directory](../../scenarios/sre/project/roles/documentation/files/library/faults/indexes/). Ensure that all the fields listed have value. Resource links should be provided in the `resources` field and a JSON schema for the fault's arguments should be provided in the `arguments.jsonSchema` field.

>[!NOTE]
>The JSON schema should be valid with the `2020-12` ruleset.

2. Edit the new fault implementation file. This will be located in the [faults role task directory](../../scenarios/sre/project/roles/faults/tasks/). **Please use Ansible modules whenever possible and only use CLI tools when necessary.**

>[!NOTE]
>For Kubernetes or OpenShift related faults, only the namespace of the application should be affected. This allows for easy cleanup of the fault when the application is undeployed (and thus the namespace is deleted). However, if the fault needs to change or add something cluster wide, then the fault will need to do clean up those changes. In such a case, either add a new `remove_x` task file to the directory or modify one of the existing removal tasks files where appropriate to add in the clean up step.

>[!NOTE]
>When adding new files, please create a new directory with the same name as the fault's task file **without the `inject_` prefix**. This allows for easier correlation between what additional resources a fault requires.

3. Create a [Molecule test](../../scenarios/sre/project/roles/faults/molecule/) to test the fault. The name of directory should be the exact same name as the task file. Use the following command to run the fault test suite:
```shell
make test-unit-faults
```

### Validating New Fault

1. Run the following command to generate the documentation for the new fault:
```shell
make generate-docs
```

2. Run the following command to validate the structure of the new fault:
```shell
make validate-docs
```

3. Run your fault in a scenario and ensure that the alerts listed in the new fault configuration are firing appropriately.
