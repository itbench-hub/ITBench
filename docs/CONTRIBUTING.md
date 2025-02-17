# Contributing

## Incidents

To contribute an incident to the testbed, follow these steps:

1. Create an incident directory.
```bash
mkdir roles/incident_<number>
mkdir roles/incident_<number>/tasks
touch roles/incident_<number>/tasks/main.yaml
mkdir roles/incident_<number>/vars
touch roles/incident_<number>/vars/main.yaml
```

2. Populate the `vars/main.yaml` file.
    a. Add the scenario domain (opts: `sre`, `finops`)
    ```yaml
    scenario_domain: sre
    ```

    b. Add the sample application (opts: `otel_astronomy_shop`, `dsb_hotel_reservation`)
    ```yaml
    sample_application: otel_astronomy_shop
    ```

    c. Add the chaos mesh installation flag (opts: bool)
    ```yaml
    is_install_chaos_mesh: false
    ```

    _Note:_ The chaos mesh is particularly useful when introducing unstable networking incidents. For these scenarios, this flag should be set to `true`.

    d. (Optional) Add the fault(s).
    ```yaml
    fault_injected:
    ```

    e. (Optional) Add the targets of the fault. This is dependent of the fault needing to be introduced. Please see the variables used in the fault to determine which fields are needed.
    ```yaml
    target_namespace_name:
    target_deployments:
    target_label_name1:
    ```

    f. Add the documenation (see [here](../roles/documentation/defaults/main/incidents_schema.yaml) for the schema)
    ```yaml
    docs_incident_<number>: {}
    ```

3. Add the tasks to the `tasks/main.yaml` file for fault injection and fault removal.

The existing Ansible playbooks can be used as an example, but all should adhere to the following rules:

- All tasks should be tagged with `incident_<number>`.
- Fault injection tasks should only be executed when `is_fault_injection` is true.
- Fault removal tasks should only be exuted when `is_fault_removal` is true.


4. Run the following commands to add the validate the documentation for the new incident and regenerate the documentation for all incidents:
```bash
INCIDENT_NUMBER=<number> make validate_docs
make documentation
```

Need examples of a specific type of scenario? Here are some recommended scenarios that one can start with as a base:

- Incident 4: FlagD based (native) scenario
- Incident 17: Chaos Mesh based scenario
- Incident 37: FinOps scenario

## Observability Tools

Before adding a new tool to the stack, please create a feature request issue. Once the feature has been approved, please follow the following steps.

1. Create the installation Ansible playbook and modify the uninstallation playbook.
```bash
touch roles/observability_tools/install_<tool>.yaml
vim roles/observability_tools/uninstall_observabilty_stack.yaml
```

The existing Ansible playbooks can be used as an example, but all should adhere to the following rules:

- Installation tasks should be tagged with the `install_tools` tag and only executed when the `domain` variable is either `sre` or `finops`.
- Uninstallation tasks should be tagged with the `install_tools` tag and only executed when the `domain` variable is either `sre` or `finops`.
- Uninstallation tasks should completely remove all traces of the tool on the cluster (including namespace).
- If using Helm or Kubernetes to deploy or undeploy resources, the `wait` field should be used in order to confirm the successful installation or uninstallation respectively.

2. Update the `main.yaml` in `roles/observability_tools` to include the newly added playbooks.

3. Update the `Makefile` to include commands for deploying and undeploying the application. This includes specifying which incidents requires the application and modifying the `deploy_scenario_tools` and `undeploy_scenario_tools` commands. The existing commands can be used as an example for this extension.

## Sample Applications

Before adding a new sample application to the stack, please create a feature request issue. Once the feature has been approved, please follow the following steps.

1. Create the installation and uninstallation Ansible playbooks.
```bash
touch roles/sample_applications/install_<application>.yaml
touch roles/sample_applications/uninstall_<application>.yaml
```

The existing Ansible playbooks can be used as an example, but all should adhere to the following rules:

- Installation tasks should be tagged with the `install_sample_applications` tag and only executed when the `sample_application` variable is the name of the application.
- Uninstallation tasks should be tagged with the `uninstall_sample_applications` tag and only executed when the `sample_application` variable is the name of the application.
- Uninstallation tasks should completely remove all traces of the application on the cluster (including namespace).
- If using Helm or Kubernetes to deploy or undeploy resources, the `wait` field should be used in order to confirm the successful installation or uninstallation respectively.

2. Update the `main.yaml` in `roles/sample_applications` to include the newly added playbooks.

3. Update the `Makefile` to include commands for deploying and undeploying the application. This includes specifying which incidents requires the application and modifying the `deploy_scenario_application` and `undeploy_scenario_application` commands. The existing commands can be used as an example for this extension.
