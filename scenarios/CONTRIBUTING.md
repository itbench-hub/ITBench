# Contributing to ITBench-Scenarios

ITBench-Scenarios accepts contributions through GitHub pull request.

## Required Software

- [Python3](https://www.python.org/downloads/) (v3.13.z)

## Environment Set Up Guide

1. Create a Python virtual environment.

```shell
python -m venv venv
```

2. Install the Python dependencies

```shell
python -m pip install -r requirements-dev.txt
```

3. Install `pre-commit` to the repo. This only needs to be done once.

```shell
pre-commit install
pre-commit install --hook-type commit-msg --hook-type pre-push
```

## Committing Code

This project requires the use of the following tools:

- [Ansible Lint](https://github.com/ansible/ansible-lint)
- [commitizen](https://github.com/commitizen-tools/commitizen)
- [detect-secrets](https://github.com/Yelp/detect-secrets)
- [pre-commit](https://github.com/pre-commit/pre-commit)

These tools are installed through the process mentioned [here](#environment-set-up-guide).

**All commits submitted to this repository must be signed, pass the pre-commit tests, and formatted through commitizen.**

In order to sign and commit code using commitizen, please run the following command after staging changes via `git add`:

```shell
cz commit -- --signoff
```

## Committing to SRE Scenarios

> [!WARNING]
> Before creating a pull request (PR), please ensure that the capability is not already present within the codebase and that there is not already a PR to add the capability. PRs duplicating features causes slows the reviewing process. Such requests will be closed by the maintainers.

### Add a new tool

**Note:** It is recommended that a tool installed to a Kubernetes cluster use Helm as the deployment mechanism. This helps to simplify the deployment process and keeps the general uniformity of ITBench's deployment.

1. Create tasks files in the tools role which handle the installation and uninstallation of the tool. These files should be titled `install_<tool name>` and `uninstall_<tool name>` respectively.
  - The uninstallation process should remove all traces of the tool, including any CustomResourceDefinition (CRD) objects deployed to the cluster.
2. Import the installation and uninstallation tasks, along with the conditions for their deployment, in the [`install.yaml`](./sre/roles/tools/tasks/install.yaml) and the [`uninstall.yaml`](./sre/roles/tools/tasks/uninstall.yaml).
3. Expand the [tools argument spec](./sre/roles/tools/meta/argument_specs.yaml) and add the tool to the [tools group variables](./sre/group_vars/environment/tools.yaml.example). Also, update the [incident load task](./sre/roles/incidents/tasks/load.yaml).
4. Create a PR titled: `feat: new tool [<tool name>]`

### Add a new application

**Note:** It is recommended that an application installed to a Kubernetes cluster use Helm as the deployment mechanism. This helps to simplify the deployment process and keeps the general uniformity of ITBench's deployment.

**Note:** It is recommended that an application uses OpenTelemetry in order to forward telemetry data to the observability tools. However, other softwares can also be used for this task.

1. Create tasks files in the tools role which handle the installation and uninstallation of the tool. These files should be titled `install_<application name>` and `uninstall_<application name>` respectively.
  - The uninstallation process should remove all traces of the application, including any CustomResourceDefinition (CRD) objects deployed to the cluster.
2. Import the installation and uninstallation tasks, along with the conditions for their deployment, in the [`install.yaml`](./sre/roles/applications/tasks/install.yaml) and the [`uninstall.yaml`](./sre/roles/applications/tasks/uninstall.yaml).
3. Expand the [applications argument spec](./sre/roles/applications/meta/argument_specs.yaml) and add the tool to the [applications group variables](./sre/group_vars/environment/applications.yaml.example). Also, update the [incident load task](./sre/roles/incidents/tasks/main.yaml).
4. Create a PR titled: `feat: new application [<application name>]`

### Add a new fault injection (and removal)

**Note:** When creating tasks, please use the given Ansible modules whenever possible. This reduces the overhead in reviewing the fault and keeps the uniformity of the ITBench codebase. For example, when making a task that creates a Kubernetes object, use the `kubernetes.core.k8s` collection instead of using `ansible.builtin.command` and invoking the kubectl CLI. The collections used in this project can be found [here](./sre/requirements.yaml) and documentation for them can be found [here](https://docs.ansible.com/ansible/latest/collections/index.html).

1. Create task files in the faults role which handle the injection and removal of the fault. These files should be title `inject_<fault type>_<fault name>` and `remove_<fault type>_<fault name>`.
  - The fault type is acts as a grouping mechanism. For instance, `otel_demo` faults only work on the OpenTelementry Demo application and `valkey` faults only work on Valkey workloads. `custom` is the fault type given to generic faults which can be injected into any workload and will be the fault type used for new faults more often than not.
  - The removal mechanism needs only to delete any new objects that were added to the environment as a result of the fault injection (ex: [Custom Fault: Misconfigured Resource Quota](./sre/roles/faults/tasks/remove_custom_misconfigured_resource_quota.yaml)). Removal of the fault does not guarentee that the application will return to a stable state (ex: [Custom Fault: Misconfigured Service Port](./sre/roles/faults/tasks/remove_custom_misconfigured_service_port.yaml))
2. Import the injection to the appropriate file (ie, [inject_custom](./sre/roles/faults/tasks/inject_custom.yaml) for custom faults) and removal tasks for the respective removal tasks.
3. Expand the [faults argument spec](./sre/roles/faults/meta/argument_specs.yaml)
4. Create a new [incident spec](./sre/roles/incidents/files/specs/) and [ground truth file](./sre/roles/incidents/files/ground_truths/) to act as a sample to show how to use the new fault
  - This file is titled `incident_<unique int id>`
5. Create a PR titled: `feat: new fault [<fault name>]`

### Add a new waiter

For more information about existing waiters (and a description of what a waiter), please consult the [documentation](./sre/docs/waiters.md).

1. Add a new element to the JSON list in the waiters' [library index](./sre/roles/documentation/files/library/waiters/index.json). The required JSON fields are described in the [schema](./sre/roles/documentation/files/library/waiters/schema.json).
2. Once the new entry has been added, run the following commands to generate and verify the resulting documenation files.
```shell
make -C sre generate_docs
make -C sre validate_docs
```
3. Run the following command to generate the implementation files of the new waiter:
```shell
make -C sre generate_scenario_files
```
4. Add the implementation for the new waiter.
> [!NOTE]
> Using the `git status` command can help quickly show which files are untracted. The newly created waiter task yaml file will be under the `sre/roles/waiter/tasks` directory.
5. Create a PR with the title, `feat: add waiter <waiter name>`, and leave a description of what it does in the text field of the PR.
6. **Optional:** A scenario showing the capability of the new waiter can be added within the same PR. See the [section on adding new scenarios](#add-a-new-scenario) for more information.

### Add a new scenario

For more information about existing scenarios, please consult the [documentation](./sre/docs/scenarios.md).

1. Add a new element to the JSON list in the scenarios' [library index](./sre/roles/documentation/templates/library/scenarios/index.j2). The required JSON fields are described in the [schema](./sre/roles/documentation/files/library/scenarios/schema.json).
> [!NOTE]
> A scenario element is quite dense. The recommended approach would be copy-pasting a previous element and replacing the values as needed.
2. Once the new entry has been added, run the following commands to generate and verify the resulting documenation files.
```shell
make -C sre generate_docs
make -C sre validate_docs
```
3. Run the following command to generate the files for the new scenario:
```shell
make -C sre generate_scenario_files
```
4. Create a PR with the title, `feat: add scenario <scenario name>`, and leave a description of what it does in the text field of the PR.
