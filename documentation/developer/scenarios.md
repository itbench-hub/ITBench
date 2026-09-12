# Developing Scenarios with ITBench

This document will detail how to create new SRE and FinOps scenarios in ITBench which can be used in SRE or FinOps [scenarios](../getting-started/scenarios.md).

>[!IMPORTANT]
>To add new scenarios to the ITBench project, please follow this guide and make a pull request titled: `feat: add scenario <scenario id>` (ie: `feat: add scenario 1`).

## Required Software

Please follow the requirements listed [here](../getting-started/scenarios.md#required-software).

## Installation

Please follow the instructions listed [here](../getting-started/scenarios.md#installation).

## Set Up

Please follow the instructions listed [here](../getting-started/scenarios.md#set-up).

## Creating Scenarios

### Generating Boilerplate

1. Run the following command from the **root directory** and respond to the prompts appropriately to create a new scenario index stub:
```shell
make scaffold-scenario
```

>[!TIP]
>To see a list of all the added and changed files, use `git status`.

### Editing New Scenario

1. Edit the new scenario index template. This will be located in the [scenario library index template directory](../../templates/library/indexes/scenarios/). If using an [ITBench supported application](../library/applications/README.md), please ensure that [proper template variables are used](../../scenarios/sre/project/roles/applications/defaults/main/managers.yaml).

>[!TIP]
>Use the existing templates to see how to add the variables for templating.

2. Once the index template is complete, run the following command to generate the Ansible role files (scenario manifests, groundtruth stubs, etc.) from `scenarios/sre`:
```shell
make generate-resource-files
```

### Validating New Scenario

1. Run the following command to generate the library outputs (documentation, indexes, specs):
```shell
make generate-library
```

2. Run the following command to validate the structure of the new scenario:
```shell
make validate-library
```
