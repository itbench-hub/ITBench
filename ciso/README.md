# CISO (Chief Information Security Officer) Sample Task Scenarios

Here is an example of Task Scenario used in an automation package to benchmark Agent for CISOs.

This repository contains following 4 category of scenarios:

```
.
├── 1.gen-cis-b-k8s-kyverno
├── 2.gen-cis-b-k8s-kubectl-opa
├── 3.gen-cis-b-rhel9-ansible-opa
├── 4.upd-cis-b-k8s-kyvernoz
└── README.md
```

Each scenario includes a setup for a compliance misconfigured environment and tools to check and address if the misconfiguration is resolved or not.

## Table of Contents

1. [Scenarios](#scenarios)
    - [1. gen-cis-b-k8s-kyverno](#1-gen-cis-b-k8s-kyverno)
    - [2. gen-cis-b-k8s-kubectl-opa](#2-gen-cis-b-k8s-kubectl-opa)
    - [3. gen-cis-b-rhel9-ansible-opa](#3-gen-cis-b-rhel9-ansible-opa)
    - [4. upd-cis-b-k8s-kyverno](#4-upd-cis-b-k8s-kyverno)
2. [Manual Benchmarking Process for the CISO Task Scenario](#manual-benchmarking-process-for-the-ciso-task-scenario)
    - [1. Outline](#1-outline)
    - [2. Prerequisites](#2-prerequisites)
    - [3a. Task Scenario for Targeting a Kubernetes Cluster](#3a-task-scenario-for-targeting-kubernetes-cluster)
    - [3b. Task Scenario for Targeting Red Hat Enterprise Linux 9](#3b-task-scenario-for-targeting-red-hat-enterprise-linux-9)

## Scenarios

### 1. gen-cis-b-k8s-kyverno
**Description**: This scenario expects to deploy Kyverno policies to detect injected compliance issues in a Kubernetes environment for the compliance requirement "Minimize the admission of containers wishing to share the host network namespace".

#### 1.1 The agent is expected to do following task request (template value will be substituted):

```
I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`
Minimize the admission of containers wishing to share the host network namespace

To check the condition, do the following steps.
- deploy a Kyverno policy to the cluster
- chcek if the policy is correctly deployed.

If deploying the policy failed and if you can fix the issue, you will do it and try deploying again.
Once you get a final answer, you can quit the work.

The cluster's kubeconfig is at `{{ kubeconfig }}`.
```

When an agent is invoked, an input is provided about this scenario. The input is the json following schema. (You can get the exact value by `make get`)

```json
{
    "metadata": {
        "name": "cis-b.5.2.5-gen",  // Scenario Name
        "description": "CIS Benchmark for K8S 5.2.5 (Kyverno)", // Scenario Description
        "scenario_type": "Gen-CIS-b-K8s-Kyverno" // Scenario Type
    },
    // The above goal description
    "goal_template": "I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`\n    Minimize the admission of containers wishing to share the host network namespace.\n\nTo check the condition, do the following steps. \n- deploy a Kyverno policy to the cluster\n- chcek if the policy is correctly deployed. \n\nIf deploying the policy failed and if you can fix the issue, you will do it and try deploying again.\nOnce you get a final answer, you can quit the work.\n\nThe cluster's kubeconfig is at `{{ kubeconfig }}`.\n",
    "vars": {
        "kubeconfig": "apiVersion: v1\ncluster...="  // kubeconfig.yaml contents for access to the target Kubernetes
    }
}
```

#### 1.2 How it is evaluated

The evaluation verifies the following to return a pass:
- Verify that the specified Kyverno policy produces the expected Kyverno policy report for the target resource.

Please refer to [evaluation/main.py](/ciso/1.gen-cis-b-k8s-kyverno/evaluation/main.py) for the details.

#### The contents of the directory**:
```
├── 1.k8s-kyverno
│   ├── evaluation  # Tools or scripts to check if the injected security issues are detected or not in this scenario
│   ├── manifests   # Kubernetes resources to be deployed for compliance violation
│   ├── playbooks   # Ansible playbooks to set up the scenario environment
│   ├── examples    # Example Kyverno Policy to detect the compliance violation
│   └── Makefile    # Commands to simplify setup and execution for the scenario
```

### 2. gen-cis-b-k8s-kubectl-opa
**Description**: This scenario expects to use kubectl to collect the Kubernetes resources and OPA (Open Policy Agent) to check if the injected compliance issues are detected or not for the compliance requirement "Minimize the admission of containers wishing to share the host network namespace".

#### 2.1 The agent is expected to do following task request (template value will be substituted):

```
I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`
    Minimize the admission of containers wishing to share the host network namespace

To check the condition, do the following steps.
- get related resource(s) on the cluster by kubectl command
- chcek if the conditions are satisfied by OPA Rego policy

for those steps, you need to create an OPA Rego policy `policy.rego`.
Also, save the kubectl command as `script.sh` with the following design.
- The script should output the collected related resources to a file named `collected_data.json` in the current working directory.
- Please remove any kubeconfig configuration (e.g. --kubeconfig args) from the script, as users will configure the kubeconfig using environment variables or other methods.

If running the policy failed and if you can fix the issue, you will do it and try running again.

Once you get a final answer, you can quit the work.

The cluster's kubeconfig is at `{{ kubeconfig }}`.
```

When an agent is invoked, an input is provided about this scenario. The input is the json following schema. (You can get the exact value by `make get`)
```json
{
    "metadata": {
        "name": "k8s-opa/cis-b-gen/5.2.5", // Scenario Name
        "description": "CIS Benchmark for K8S 5.2.5 (OPA)", // Scenario Description
        "scenario_type": "Gen-CIS-b-K8s-Kubectl-OPA" // Scenario Type
    },
    // The above goal description
    "goal_template": "I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`\n    Minimize the admission of containers wishing to share the host network namespace. \n\nTo check the condition, do the following steps. \n- get related resource(s) on the cluster by kubectl command\n- chcek if the conditions are satisfied by OPA Rego policy\n\nfor those steps, you need to create an OPA Rego policy `policy.rego`. \nAlso, save the kubectl command as `script.sh` with the following design. \n- The script should output the collected related resources to a file named `collected_data.json` in the current working directory.\n- Please remove any kubeconfig configuration (e.g. --kubeconfig args) from the script, as users will configure the kubeconfig using environment variables or other methods.\n\nIf running the policy failed and if you can fix the issue, you will do it and try running again.\n\nOnce you get a final answer, you can quit the work.\n\nThe cluster's kubeconfig is at `{{ kubeconfig }}`.\n",
    "vars": {
        "kubeconfig": "apiVersion: v1\nclusters:\n- ..." // kubeconfig.yaml contents for access to the target Kubernetes
    }
}
```

#### 2.2 How it is evaluated

The evaluation verifies the following to return a pass:
- Confirm that the script.sh and policy.rego are produced.
- Ensure that script.sh runs successfuly and verify that the collected_data.json is produced.
- Ensure that OPA command runs successfully with the policy.rego against the collected_data.json.
- Verify that the OPA outputs expected result.

Please refer to [evaluate.yml](/ciso/2.gen-cis-b-k8s-kubectl-opa/playbooks/evaluate.yml) for the details.

#### The contents of the directory
```
├── 2.k8s-kubectl-opa
│   ├── evaluation  # Tools or scripts to check if the injected security issues are detected or not in this scenario
│   ├── manifests   # Kubernetes resources to be deployed for compliance violation
│   ├── playbooks   # Ansible playbooks to set up the scenario environment
│   ├── examples    # Example scripts to fetch Kubernetes resources and OPA Rego policy to check if the statuses complies or not
│   └── Makefile    # Commands to simplify setup and execution for the scenario
```

### 3. gen-cis-b-rhel9-ansible-opa
**Description**: This scenario expects to use Ansible Playbooks to collect system status from RHEL9 and OPA to check if the injected compliance issues are detected or not for the compliance requirement "Ensure SSH X11 forwarding is disabled".

#### 3.1 The agent is expected to do following task request (template value will be substituted):

```
I would like to check if the following condition is satisfiled, given a host name `rhel9_servers`, on RHEL by using Ansible Playbook and OPA Rego policy
    Ensure SSH X11 forwarding is disabled

To check the condition, do the following steps.
- collect configuration from the RHEL host and save it locally. you can use ansible-playbook to do that.
- chcek if the condition is met by using rego policy with the input given by the step above.

for those steps, you need to create ansible playbook `playbook.yml` and OPA rego policy `policy.rego`.
The playbook is implemented to locate the collected data to a file named `collected_data.json` in the current working directory.

If you can fix the generated code, do it and run the fixed code again.
Once you get a final answer, you can quit the work.

The Ansible inventory file (inventory.ansible.ini) for the target RHEL server is located at `{{ path_to_inventory }}`.
```

When an agent is invoked, an input is provided about this scenario. The input is the json following schema. (You can get the exact value by `make get`)
```json
{
"metadata": {
    "name": "rhel9/cis-b-gen/5.2.12", // Scenario Name
    "description": "CIS Benchmark for RHEL9 5.2.12", // Scenario Description
    "scenario_type": "Gen-CIS-b-RHEL9-Ansible-OPA" // Scenario Type
    },
    // The above goal description
    "goal_template": "I would like to check if the following condition is satisfiled, given a host name `rhel9_servers`, on RHEL by using Ansible Playbook and OPA Rego policy\n    Ensure SSH X11 forwarding is disabled \n\nTo check the condition, do the following steps. \n- collect configuration from the RHEL host and save it locally. you can use ansible-playbook to do that. \n- chcek if the condition is met by using rego policy with the input given by the step above. \n\nfor those steps, you need to create ansible playbook `playbook.yml` and OPA rego policy `policy.rego`.\nIf you can fix the generated code, do it and run the fixed code again.\nOnce you get a final answer, you can quit the work.\n\nThe Ansible inventory file (inventory.ansible.ini) for the target RHEL server is located at `{{ path_to_inventory }}`.\n",
    "vars": {
        "ansible_ini": "[rhel9_servers]\nrhel9 ansible_host=...", // Ansible Ini file to acceess to the target RHEL system
        "ansible_user_key": "***" // SSH Key
    }
}
```

#### 3.2 How it is evaluated

The evaluation verifies the following to return a pass:
- Confirm that the playbook.yml and policy.rego are produced.
- Ensure that playbook.yml runs successfuly and verify that the collected_data.json is produced.
- Ensure that OPA command runs successfully with the policy.rego against the collected_data.json.
- Verify that the OPA outputs expected result.

Please refer to [evaluate.yml](/ciso/3.gen-cis-b-rhel9-ansible-opa/playbooks/evaluate.yml) for the details.

#### The contents of the directory
```
├── 3.rhel9-ansible-opa
│   ├── evaluation  # Tools or scripts to check if the injected security issues are detected or not in this scenario
│   ├── playbooks   # Ansible playbooks to set up the scenario environment
│   ├── examples    # Example Ansible Playbook to fetch system statuses and OPA Rego policy to check if the statuses complies or not
│   └── Makefile    # Commands to simplify setup and execution for the scenario
│   └── tasks
│       ├── fault_inject.yml # Ansible task to make the RHEL system compliance violation
```

### 4. upd-cis-b-k8s-kyvernoz
**Description**: This scenario expects to inspect the current Kyvero policies and Kubernetes resources, then update the existing policies to comply the new compliance requirements.

#### 4.1 The agent is expected to do following task request (template value will be substituted):

```
Currently, the following Kyverno policies are deployed in the Kubernetes cluster. Review these existing policies and edit them to meet additional security requirements. Please avoid creating new policy resources; instead, make the necessary changes directly to the existing resources.

    Prohibit the use of the default service account
    Prohibit privilege escalation

However, the new internal security policy now requires the following additional conditions:

    Prohibit running as the root user
    Only allow signed images from a trusted registry (trusted-registry.com)

Your task is to review the existing Kyverno policies and directly edit the existing policies to meet these new requirements. Do not change the resource names. Once you have completed the edits, update the existing resources in the Kubernetes cluster.
Steps

    Review and Edit Kyverno Policies
    Directly modify the existing policy resources to meet the new requirements. Ensure that you do not change the names of the resources.

The cluster's kubeconfig is at `{{ kubeconfig }}`.
```

When an agent is invoked, an input is provided about this scenario. The input is the json following schema. (You can get the exact value by `make get`)
```json
{
    "metadata": {
        "name": "policy-adapt/scenario1", // Scenario Name
        "description": "Kyverno Policy Adapting: Enhancing Policies for Root and Trusted Registry Requirements", // Scenario Description
        "scenario_type": "Upd-CIS-b-K8s-Kyverno" // Scenario Type
    },
    // The above goal description
    "goal_template": "Currently, the following Kyverno policies are deployed in the Kubernetes cluster. Review these existing policies and edit them to meet additional security requirements. Please avoid creating new policy resources; instead, make the necessary changes directly to the existing resources.\n\n    Prohibit the use of the default service account\n    Prohibit privilege escalation\n\nHowever, the new internal security policy now requires the following additional conditions:\n\n    Prohibit running as the root user\n    Only allow signed images from a trusted registry (trusted-registry.com)\n\nYour task is to review the existing Kyverno policies and directly edit the existing policies to meet these new requirements. Do not change the resource names. Once you have completed the edits, update the existing resources in the Kubernetes cluster.\nSteps\n\n    Review and Edit Kyverno Policies\n    Directly modify the existing policy resources to meet the new requirements. Ensure that you do not change the names of the resources. \n\nThe cluster's kubeconfig is at `{{ kubeconfig }}`.\n",
    "vars": {
        "kubeconfig": "apiVersion: v1\nclusters..." // kubeconfig.yaml contents for access to the target Kubernetes
    }
}
```


#### 4.2 How it is evaluated

The evaluation verifies the following to return a pass:
- Verify that the specified Kyverno policy produces the expected Kyverno policy report for the target resource.
- Ensure that no modifications have been made to policies that should not be updated, and that no new policies have been created.

Please refer to [evaluation.py](/ciso/4.upd-cis-b-k8s-kyverno/evaluation.py) for the details.

#### The contents of the directory
```
├── 4.updating-k8s-kyverno
│   ├── evaluation  # Tools or scripts to check if the injected security issues are detected or not in this scenario
│   ├── manifests   # Kubernetes resources to be deployed for compliance violation
│   ├── playbooks   # Ansible playbooks to set up the scenario environment
│   ├── examples    # Example Kyverno Policy to detect the compliance violation
│   └── Makefile    # Commands to simplify setup and execution for the scenario
```

## Manual Benchmarking Process for the CISO Task Scenario
In this process, you will prepare a base environment, configure it to intentionally violate compliance requirements, run the Agent to address these issues, and evaluate the results.

**Important: Perform all steps in a secure, non-production environment to prevent any impact on live systems, as the process involves configuring the environment to intentionally violate compliance requirements.**

### 1. Outline

![Outline](/ciso//images/overview-step.png)

1. Prepare a target environment for benchmarking your Agent based on the CISO Scenario
    - Since the scenario configuration process involves creating temporary users and applying various configurations that violate compliance requirements, **ensure that the Kubernetes cluster or RHEL machine used is a test or sandbox environment. Do not use production systems.**
1. Configure the environment to violate the provided compliance requirements.
1. Provide the required information (task goal, credentials, etc.) to the Agent once the environment setup is complete.
1. Run the Agent to complete the task.
1. Evaluate the target environment to verify if the task was properly completed after the Agent has finished.
1. Clean up the environment to restore it to its original state.

### 2. Prerequisites

Before starting the task scenario, ensure that all necessary tools and environments are set up correctly to maintain security and stability throughout the process.

1. Build a Docker Image for the Task Scenario Makefile Runner Securely

    **To execute the task scenario in a controlled and secure manner, build the Docker image for the Makefile runner using the following steps. This ensures that the environment is isolated and minimizes security risks during the execution of compliance-related tasks.**

    ```
    cd ciso
    docker build . -f Dockerfile -t ciso-task-scenarios:latest
    ```

2. Use the following syntax to invoke a `make` command via the Docker image:

    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/SCENARIO_WORKDIR>:/tmp/scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/KUBECONFIG>:/etc/ciso-task-scenarios/kubeconfig.yaml \
        ciso-task-scenarios:latest \
        make -C <scenario directory name (e.g. 1.gen-cis-b-k8s-kyverno)> \
        <make target (e.g. deploy_bundle)>
    ```

    **Notes on Input Values**
    - Replace `<PATH/TO/SCENARIO_WORKDIR>` with the actual path for your workdir for scenario
    - Replace `<PATH/TO/AGENT_WORKDIR>` with the actual path for your workdir for agent, which must be consistent with the `<PATH/TO/WORKDIR>` used in [ciso-caa-agent](https://github.com/itbench-hub/itbench-ciso-caa-agent).
    - Replace `<PATH/TO/KUBECONFIG>` with the actual path for your kubeconfig file


    Makefile targets for task scenarios.

    - deploy_bundle: setup the target environment
    - inject_fault: deploy or configure the target environment so it violates the compliance requirement
    - get: get the scenario details that would be passed as the input for Agent
    - evaluate: valuate
    - get_status: get status
    - revert_bundle: revert the target environment
    - destroy_bundle: delete the target environment

### 3a. Task Scenario for Targeting Kubernetes Cluster

The following steps apply to the scenario targting Kubernetes Cluster. The corresponding `<scenario directory name>` values are as follows:
- 1.gen-cis-b-k8s-kyverno
- 2.gen-cis-b-k8s-kubectl-opa
- 4.upd-cis-b-k8s-kyvern

The example below demonstrates the steps for `1.gen-cis-b-k8s-kyverno`. When trying other scenarios, replace `<scenario directory name>` accordingly.

#### Prerequisites
1. Prepare kubeconfig file for Kubernetes cluster used this benchmark
    - For Kind, [prepare-kubeconfig-kind.md](/ciso/prepare-kubeconfig-kind.md)
    - For EKS, [prepare-kubeconfig-eks.md](/ciso/prepare-kubeconfig-eks.md)
1. Prepare two working directories to be mounted by the Docker container
    - One directory will be used for the Task Scenario (referenced as `<PATH/TO/SCENARIO_WORKDIR>` in later steps).
    - The other will be used for the Agent (referenced as `<PATH/TO/AGENT_WORKDIR>`).

    **These directories will be actively accessed during the benchmark, so make sure to use directories that are safe to modify.**
    - Examples:
        - `/tmp/ciso-scenario` for `<PATH/TO/SCENARIO_WORKDIR>`
        - `/tmp/ciso-agent` for `<PATH/TO/AGENT_WORKDIR>`

#### Steps
1. Setup a scenario environment against the Kubernetes cluster.
    This command installs Kyverno to the provided kubeconfig.yaml cluster. It takes few minutes to finish.

    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/SCENARIO_WORKDIR>:/tmp/scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/KUBECONFIG>:/etc/ciso-task-scenarios/kubeconfig.yaml \
        ciso-task-scenarios:latest \
        make -C 1.gen-cis-b-k8s-kyverno \
        deploy_bundle
    ```

    Example output
    ```
    ...
    TASK [Prepare updated JSON data with kubeconfig] **************************************************************************************
    ok: [localhost]

    TASK [Write updated status (with or without kubeconfig) back to JSON file] ************************************************************
    changed: [localhost]

    PLAY RECAP ****************************************************************************************************************************
    localhost                  : ok=55   changed=7    unreachable=0    failed=0    skipped=8    rescued=0    ignored=0
    ```
1. Inject compliance issues into the environment
    This command deploys nginx that violates the given policy, for example, "minimize the admission of containers wishing to share the host network namespace" in the case of `1.gen-cis-b-k8s-kyverno`, where hostNetwork in the pod manifest is set to true.

    ```
    docker run --rm -ti --name ciso-task-scenario \
    -v <PATH/TO/SCENARIO_WORKDIR>:/tmp/scenario \
    -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
    -v <PATH/TO/KUBECONFIG>:/etc/ciso-task-scenarios/kubeconfig.yaml \
    ciso-task-scenarios:latest \
    make -C 1.gen-cis-b-k8s-kyverno \
    inject_fault
    ```

    Example output

    ```
    PLAY [Execute fault injection] *******************************************************************************************
    ...
    PLAY RECAP ***************************************************************************************************************
    localhost                  : ok=29   changed=3    unreachable=0    failed=0    skipped=2    rescued=0    ignored=0
    ```
    - Now a pod that violates the policy to minimize the admission of containers wishing to share the host network namespace. (Check that hostNetwork is set to true)
        ```
        $ kubectl get pod -n paa
        NAME                                READY   STATUS    RESTARTS   AGE
        nginx-deployment-7cb5b996ff-vb8mz   1/1     Running   0          1m
        ```
        ```
        $ kubectl get pod -n paa nginx-deployment-7cb5b996ff-vb8mz -o yaml
          apiVersion: v1
          kind: Pod
          metadata:
            creationTimestamp: "2025-01-17T06:26:41Z"
          spec:
            containers:
            - image: nginx:1.14.2
              imagePullPolicy: IfNotPresent
              ...
            hostNetwork: true
          ...
        ```
1. Get the goal description for the Agent
    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/SCENARIO_WORKDIR>:/tmp/scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent \
        -v <PATH/TO/KUBECONFIG>:/etc/ciso-task-scenarios/kubeconfig.yaml \
        ciso-task-scenarios:latest \
        sh -c \
        "make -s -C 1.gen-cis-b-k8s-kyverno \
        get \
        2>/dev/null | jq -r .goal_template"
    ```

    Example output
    ```
    I would like to check if the following condition is satisfiled, given a Kubernetes cluster with `kubeconfig.yaml`
        Minimize the admission of containers wishing to share the host network namespace.

    To check the condition, do the following steps.
    - deploy a Kyverno policy to the cluster
    - chcek if the policy is correctly deployed.

    If deploying the policy failed and if you can fix the issue, you will do it and try deploying again.
    Once you get a final answer, you can quit the work.

    The cluster's kubeconfig is at `{{ kubeconfig }}`.
    ```
1. Run your Agent with the goal description to achieve the objective. You can also use the CISO CAA agent (https://github.com/itbench-hub/itbench-ciso-caa-agent) as an example.
    - For the scenario [2.gen-cis-b-k8s-kubectl-opa](#2-gen-cis-b-k8s-kubectl-opa), the goal requires the Agent to submit generated policy and scripts. In that case, please place the Agent's output files in `<PATH/TO/AGENT_WORKDIR>` (The CISO CAA agent is already configured to place its output files in this directory by adding a single sentence `You can use "/tmp/agent" as your workdir."`. See [ciso-caa-agent#4-start-the-agent](https://github.com/itbench-hub/itbench-ciso-caa-agent?tab=readme-ov-file#4-start-the-agent) for the details.) These files will be used in the next step, "Evaluation".
1. Once your agent is finished, run evaluation.
    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent \
        -v <PATH/TO/SCENARIO_WORKDIR>:/tmp/scenario \
        -v <PATH/TO/KUBECONFIG>:/etc/ciso-task-scenarios/kubeconfig.yaml \
        ciso-task-scenarios:latest \
        make -C 1.gen-cis-b-k8s-kyverno \
        evaluate
    ```

    Example output
    ```
    ansible-playbook ./playbooks/evaluate.yml --extra-vars "path_to_output=/tmp/scenario-ciso-1/evaluation.json " &> /tmp/scenario-ciso-1/evaluate.log
        {
        "pass": true,
        "tasks": {
            "generate_assessment_posture": true,
            "generate_policy": false,
            "evidence_available": false
        }
    }
    ```
    - If the `pass` is `true`, the CISO CAA Agent has successfully deployed the correct Kyverno Policy. You can check the Kyverno Policy that the CISO CAA Agent created.
        ```
        $ kubectl get clusterpolicy
        NAME                          ADMISSION   BACKGROUND   READY   AGE     MESSAGE
        deny-host-network-namespace   true        true         True    5m39s   Ready
        ```
    - Also, you can check that Kyverno reports the policy alert based againt the injected fault deployment on this policy.
        ```
        $ kubectl get policyreport -n paa
        NAME                                   KIND         NAME                                PASS   FAIL   WARN   ERROR   SKIP   AGE
        2f6bbe6e-4f1c-4381-b5c8-b1ff4adb7121   ReplicaSet   nginx-deployment-7cb5b996ff         0      1      0      0       0      6m45s
        335b8723-9c40-41ce-acc1-5cad0f5bdfb7   Deployment   nginx-deployment                    0      1      0      0       0      6m45s
        4868fc81-2b55-4981-9bc7-def313f74619   Pod          nginx-deployment-7cb5b996ff-vb8mz   0      1      0      0       0      6m45s
        ```
1. Now you successfully finished a single evaluation of the Agent. You can cleanup the scenario environment by `revert` command, which removes all the injected fault resources and Kyverno policies/policy reports.
    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/SCENARIO_WORKDIR>:/tmp/scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/KUBECONFIG>:/etc/ciso-task-scenarios/kubeconfig.yaml \
        ciso-task-scenarios:latest \
        make -C 1.gen-cis-b-k8s-kyverno \
        revert
    ```

    Example output
    ```
    Using default input file with override by parameters
    Using default input file with override by parameters
    ansible-playbook -i dynamic_inventory.py ./playbooks/revert.yml

    PLAY [Revert the environment] *********************************************************************************************************
    ...
    TASK [Write updated status back to JSON file] *****************************************************************************************
    changed: [RHEL9 Machine -> localhost]

    PLAY RECAP ****************************************************************************************************************************
    RHEL9 Machine              : ok=28   changed=6    unreachable=0    failed=0    skipped=2    rescued=0    ignored=0
    ```

### 3b. Task Scenario for Targeting Red Hat Enterprise Linux 9

#### Prerequisites
1. Prepare a Red Hat Enterprise Linux 9 machine with administrative access
    - The task scenario requires permission to create a temporary user.
1. The access information to the RHEL machine is passed through json file so please create `input.json` by referring to [3.gen-cis-b-rhel9-ansible-opa/input.json](/ciso/3.gen-cis-b-rhel9-ansible-opa/input.json)
    - Fill in the following fields:
        - `<IP address or hostname of the RHEL9 machine>`
        - `<Username to access the RHEL9 machine>`
    - Save the completed `input.json` in a designated location (e.g., /tmp/input.json).
1. Prepare SSH Key to access the RHEL machine
1. Prepare working directories to be mounted by the Docker container
    These directories will be actively accessed during the benchmark, so make sure to use directories that are safe to modify.
    - For example: /tmp/ciso-agent for `<PATH/TO/AGENT_WORKDIR>`
    - Unlike to [3a. Task Scenario for Targeting Kubernetes Cluster](#3a-task-scenario-for-targeting-kubernetes-cluster), `<PATH/TO/SCENARIO_WORKDIR>` is not required.

#### Steps
1. Setup a scenario environment
    The following command creates a temporal user for the scenario. It takes few minutes to finish. (Replace `<PPATH/TO/INPUT_JSON>` and `<PATH/TO/SSHKEY>` with the path input.json and the ssh key.)

    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/INPUT_JSON>:/etc/ciso-task-scenarios/3.gen-cis-b-rhel9-ansible-opa/input.json \
        -v <PATH/TO/SSHKEY>:/etc/ciso-task-scenarios/ssh_key \
        ciso-task-scenarios:latest \
        make -C 3.gen-cis-b-rhel9-ansible-opa \
        deploy_bundle
    ```

    Example output
    ```
    ...
    TASK [Prepare updated JSON data with kubeconfig] **************************************************************************************
    ok: [RHEL9 Machine -> localhost]

    TASK [Write updated status back to JSON file] *****************************************************************************************
    changed: [RHEL9 Machine -> localhost]

    PLAY RECAP ****************************************************************************************************************************
    RHEL9 Machine              : ok=32   changed=6    unreachable=0    failed=0    skipped=2    rescued=0    ignored=0
    ```
1. Inject compliance issues into the environment
    This command applies non-compliant settings to the system to simulate compliance issues. Please see [3.gen-cis-b-rhel9-ansible-opa/tasks/fault_inject.yml](/ciso/3.gen-cis-b-rhel9-ansible-opa/tasks/fault_inject.yml) for what is injected.

    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/INPUT_JSON>:/etc/ciso-task-scenarios/3.gen-cis-b-rhel9-ansible-opa/input.json \
        -v <PATH/TO/SSHKEY>:/etc/ciso-task-scenarios/ssh_key \
        ciso-task-scenarios:latest \
        make -C 3.gen-cis-b-rhel9-ansible-opa \
        inject_fault
    ```

    Example output
    ```
    PLAY [Execute fault injection] *******************************************************************************************
    ...
    PLAY RECAP ****************************************************************************************************************************
    RHEL9 Machine              : ok=24   changed=4    unreachable=0    failed=0    skipped=2    rescued=0    ignored=0
    ```
    - Now the target RHEL machine is configured as hitting the required compliance issue (X11Forwarding is enabled.)
        - Login to your RHEL machine and check the /etc/ssh/sshd_config.
        ```
        cat /etc/ssh/sshd_config | grep X11Forwarding
        #X11Forwarding no
        #       X11Forwarding no
        # Conflicting X11Forwarding setting
        X11Forwarding yes
        ```
1. Get the goal description for the Agent
    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/INPUT_JSON>:/etc/ciso-task-scenarios/3.gen-cis-b-rhel9-ansible-opa/input.json \
        -v <PATH/TO/SSHKEY>:/etc/ciso-task-scenarios/ssh_key \
        ciso-task-scenarios:latest \
        sh -c \
        "make -C 3.gen-cis-b-rhel9-ansible-opa \
        get \
        2>/dev/null | jq -r .goal_template"
    ```

    Example output
    ```
    I would like to check if the following condition is satisfiled, given a host name `rhel9_servers`, on RHEL by using Ansible Playbook and OPA Rego policy
        Ensure SSH X11 forwarding is disabled

    To check the condition, do the following steps.
    - collect configuration from the RHEL host and save it locally. you can use ansible-playbook to do that.
    - chcek if the condition is met by using rego policy with the input given by the step above.

    for those steps, you need to create ansible playbook `playbook.yml` and OPA rego policy `policy.rego`.
    If you can fix the generated code, do it and run the fixed code again.
    Once you get a final answer, you can quit the work.

    The Ansible inventory file (inventory.ansible.ini) for the target RHEL server is located at `{{ path_to_inventory }}`.
    ```
1. Run your Agent with the goal description to achieve the objective. You can also use the CISO CAA agent (https://github.com/itbench-hub/itbench-ciso-caa-agent) as an example.
    - Please place `playbook.yml` and `policy.rego` in `<PATH/TO/AGENT_WORKDIR>` (The CISO CAA agent is already configured to place its output files in this directory by adding a single sentence `You can use "/tmp/agent" as your workdir."`. See [ciso-caa-agent#4-start-the-agent](https://github.com/itbench-hub/itbench-ciso-caa-agent?tab=readme-ov-file#4-start-the-agent) for the details.) These files will be used in the next step, "Evaluation".
    1. To run the CISO CAA agent (https://github.com/itbench-hub/itbench-ciso-caa-agent).
        - Replace `{{ path_to_inventory }}` with `/tmp/agent/inventory.ansible.ini` in the above goal description.
        - Add on sentence "You can use `/tmp/agent` as your workdir."
        ```
        docker run --rm -ti --name ciso-agent \
            -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent \
            -v <PATH/TO/YOUR .env File>:/etc/ciso-agent/.env \
            ciso-agent:latest \
            python src/ciso_agent/main.py \
            --goal "$(cat /tmp/goal.txt)" \
            --auto-approve
        ```
1. Once your agent is finished, run evaluation.
    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/INPUT_JSON>:/etc/ciso-task-scenarios/3.gen-cis-b-rhel9-ansible-opa/input.json \
        -v <PATH/TO/SSHKEY>:/etc/ciso-task-scenarios/ssh_key \
        ciso-task-scenarios:latest \
        make -C 3.gen-cis-b-rhel9-ansible-opa \
        evaluate
    ```

    Example output
    ```
    {"pass": true, "details": "[fetcher] cmd: ['ansible-playbook', '/tmp/agent/playbook.yml', '-i', '/tmp/agent/inventory.ansible.ini'], stdout: \nPLAY [Collect SSH configuration to check X11 forwarding] ***********************\n\nTASK [Gathering Facts] *********************************************************\nok: [rhel9]\n\nTASK [Check if X11 forwarding is disabled in SSH configuration] ****************\nchanged: [rhel9]\n\nTASK [Save the SSH configuration check result] *********************************\nchanged: [rhel9 -> localhost]\n\nTASK [Collect additional information if X11 forwarding is enabled] *************\nchanged: [rhel9]\n\nTASK [Save additional information if X11 forwarding is enabled] ****************\nchanged: [rhel9 -> localhost]\n\nPLAY RECAP *********************************************************************\nrhel9                      : ok=5    changed=4    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0   , stderr: \n[checker] cmd: ['opa', 'eval', '--data', '/tmp/agent/policy.rego', '--input', '/tmp/agent/collected_data.json', 'data.check.result', '--format', 'raw'], stdout: false, stderr: \n"}
    ```
    - If the `pass` is `true`, the CISO CAA Agent has successfully created playbook for status collection and OPA policy for compliance checking aganst the collected data.
1. Now you successfully finished a single evaluation of the Agent. You can cleanup the scenario environment by `revert` command, which revert all the injected fault configuration and remove a temporary created user (the username is ansible_user).
    ```
    docker run --rm -ti --name ciso-task-scenario \
        -v <PATH/TO/AGENT_WORKDIR>:/tmp/agent\
        -v <PATH/TO/INPUT_JSON>:/etc/ciso-task-scenarios/3.gen-cis-b-rhel9-ansible-opa/input.json \
        -v <PATH/TO/SSHKEY>:/etc/ciso-task-scenarios/ssh_key \
        ciso-task-scenarios:latest \
        make -C 3.gen-cis-b-rhel9-ansible-opa \
        revert
    ```

    Example output
    ```
    Using default input file with override by parameters
    Using default input file with override by parameters
    ansible-playbook -i dynamic_inventory.py ./playbooks/revert.yml

    PLAY [Revert the environment] *********************************************************************************************************
    ...
    TASK [Write updated status back to JSON file] *****************************************************************************************
    changed: [RHEL9 Machine -> localhost]

    PLAY RECAP ****************************************************************************************************************************
    RHEL9 Machine              : ok=28   changed=6    unreachable=0    failed=0    skipped=2    rescued=0    ignored=0
    ```
