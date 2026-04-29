# Developing Scenarios with ITBench

This document will detail how to create new SRE and FinOps scenarios in ITBench which can be used in SRE or FinOps [scenarios](../getting-started/scenarios.md).

>[!NOTE]
>To add new scenarios to the ITBench project, please follow this guide and make a pull request titled: `feat: add scenario <scenario id>` (ie: `feat: add scenario 1`).

## Required Software

Please follow the requirements listed [here](../getting-started/scenarios.md#required-software).

## Installation

Please follow the instructions listed [here](../getting-started/scenarios.md#installation).

## Set Up

Please follow the instructions listed [here](../getting-started/scenarios.md#setup).

## Creating Scenarios

### Generating Boilerplate

1. Run the following command and respond to the prompts appropriately to create a new index in the fault library:
```shell
make generate-scenario-index
```

>[!NOTE]
>To see a list of all the added and changed files, use `git status`.

### Editing New Scenario

1. Edit the new scenario index template. This will be located in the [scenario library index template directory](../../scenarios/sre/project/roles/documentation/templates/library/scenarios/indexes/). If using an [ITBench supported application](../library/applications/README.md), please ensure that [proper template variables are used](../../scenarios/sre/project/roles/applications/defaults/main/managers.yaml).

>[!NOTE]
>Use the existing templates to see how to add the variables for templating.


### Validating New Scenario

1. Run the following command to generate the documentation for the new scenario:
```shell
make generate-docs
```

2. Run the following command to validate the structure of the new scenario:
```shell
make validate-docs
```
