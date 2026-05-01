# ITBench Scenarios

In ITBench, a `scenario` is some problem which is creating some unwanted effect within a system. The criteria for solving a `scenario` is correctly ascertaining the root cause and providing a solution to resolve the issue. Many scenarios in ITBench are based or simulated from problems that have occured in the real world.

Currently, there are three domains of `scenarios` offered by ITBench:

- CISO (Compliance & Security Operations)
- FinOps (Finacial Operations)
- SRE (Site Reliability Engineering)

Briefly, one could think of a scenario in each domain as such:

- CISO: Ensure the application is running in compiliance with a set of rules or standards (ie, HIPAA)
- FinOps: Ensure that the cost of running an application does not exceed the budget
- SRE: Ensures that an application is running and fully available for customers

There is currently not a unifed running procedure that covers both CISO, FinOps, and SRE scenarios. Since FinOps and SRE are deployed using the same mechanism, the process to run them is described here. For instructions for CISO scenarios, please use the instructions [here](../../scenarios/ciso/README.md).

## Required Software

- [helm](https://helm.sh/docs/intro/install/)
- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [uv](https://docs.astral.sh/uv/getting-started/installation/)

## Installation

### MacOS ([Homebrew](https://brew.sh/))

1. Download the following packages
```shell
brew install helm
brew install kubectl
brew install uv
```

2. Download the following packages **(optional)**
```shell
brew install python@3.14
brew install openshift-cli
```

>![NOTE]
>Installing `python` through Homebrew is not required as `uv` will install a version of Python if one is not provided. However, it can be helpful from a dependency management perspective to just have Homebrew manage the installation.

>![NOTE]
>The OpenShift CLI is only required if using an OpenShift cluster.

### Linux

1. Download the following packages
    - **a.** Install Helm 4 by following the instructions [here](https://helm.sh/docs/intro/install#from-script)
    - **b.** Install kubectl by following the instructions [here](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-using-native-package-management)
    - **c.** Install UV by following the instructions [here](https://docs.astral.sh/uv/getting-started/installation/#standalone-installer)

2. Download the following packages **(optional)**
    - **a.** Install Python by downloading the package [here](https://www.python.org/downloads/source/)
    - **b.** Install the OpenShift CLI by following the instructions [here](https://docs.redhat.com/en/documentation/openshift_container_platform/4.18/html/cli_tools/openshift-cli-oc#cli-installing-cli_cli-developer-commands)

>![NOTE]
>Python 3.14 can be downloaded and managed by various managers on Linux. However, some may not yet offer this version of python through the default package manager. To ensure that the correct version is used, the binary can either be downloaded through the link above or the `uv` version of Python 3.14 can be used. `uv` will automatically download its version of Python if it does not detect an available version on the machine.

>![NOTE]
>The OpenShift CLI is only required if using an OpenShift cluster.

## Set Up

1. From the root directory of this repository, run the following command:
```shell
make deps
```

2. Create a Kubernetes cluster. ITBench offers setup help for running a cluster on a [local machine](../../clusters/kind/README.md) or on [AWS](../../clusters/kops/README.md).

3. Run the following command from the root directory, to go to the scenarios directory:
```shell
cd scenarios/sre
```

## Running Scenarios

ITBench uses [Ansible](https://docs.ansible.com/ansible/latest/getting_started/introduction.html) to manage the sandbox environment on a Kubernetes cluster. The playbooks feature a number of [group variables](../../scenarios/sre/inventory/group_vars/). Each one will be described here:

| File Name | Function |
| --- | --- |
| [applications.yaml](../../scenarios/sre/inventory/group_vars/environment/applications.yaml.example) | Configures applications |
| [cluster.yaml](../../scenarios/sre/inventory/group_vars/environment/cluster.yaml.example) | Configures the cluster |
| [tools.yaml](../../scenarios/sre/inventory/group_vars/environment/tools.yaml.example) | Configures the tool stack |
| [storage.yaml](../../scenarios/sre/inventory/group_vars/all/storage.yaml.example) | Configures the storage options for data files |

>[!NOTE]
>Some of the yaml files have sections commented out. This is to show parameters which are optional. If they are not needed, leave them commented out. Otherwise, uncomment them and fill them out as needed.

This document functions as `quick-start` guide to running scenarios. Thus, it will not go through all the options available to develop them. For more infomation, please consult the `developer` section of the documentation.

>[!NOTE]
>See [scenario library](../library/scenarios/README.md) for a full comprehensive list of runnable scenarios.

1. Create and configure the group variables.
```shell
make group-vars
```

>[!NOTE]
>If using [our kops setup](../../clusters/kops/README.md), use `make sync-cluster-group-vars` to export the kubeconfig files and configure the [`stack.yaml`](../../scenarios/sre/inventory/group_vars/runner/stack.yaml) group variables. If using [our kind setup](../../clusters/kind/README.md), the default group variables made at creation will suffice.

>[!WARNING]
>If the group variables were already created as a part of development or running the SRE and FinOps scenarios beforehand, skip this step. Running the command will override the existing files.

### Starting Scenarios

1. Use the following command to start running a scenario:
```shell
SCENARIO_NUMBER=1 make start-scenario
```

>[!NOTE]
>Switching to a different scenario can be done by changing the value of the `SCENARIO_NUMBER` variable. Documentation for the available scenarios can be found [here](../library/scenarios/README.md).

### Running an Agent

Once a scenario has started, one can begin runnning an agent to pull information from the cluster and the various observability tools so that it can attempt to diagnose and remidiate a problem.

>[!NOTE]
>If you don't have an agent yet, you can use the [SRE-Agent](https://github.com/itbench-hub/itbench-sre-agent) to see how it works.

>[!NOTE]
>A scenario starts once fault injection has begun. Since faults may be injected after [certain conditions](../library/waiters/README.md) have been fulfilled, an agent may be running before one or multiple faults have been injected.

### Stopping Scenarios

1. Use the following command to stop running a scenario:
```shell
SCENARIO_NUMBER=1 make stop-scenario
```

## Observing Scenario Impact

Every fault in ITBench causes a noticeable effect on the application it has been injected to which can be obsevered through observability data.

### Alerts & Metrics

An **alert** is a notification that some threshold (set by the user) has been surpased. These thresholds are defined using **metrics**. When an alert is active, the engineers are notified that something is wrong with an application and that they need to begin invetigating.

ITBench uses [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/) and [Prometheus](https://prometheus.io/docs/introduction/overview/) to collect metrics and configure alerts from an application and Kubernetes cluster. To access the dashboard, follow these steps:

1. Use the following command to show the host address:
```shell
make display-endpoints
```

2. Enter the respective Prometheus address into the browser (`/alerts` for alerts dashboard and `/query` for the query dashboard)

### Traces

A **trace** is a debug tool that - typically - shows the progress of a request as it moves through an application. This information allows engineers to see which services are failing to handle the request.

ITBench uses [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/) and [Jaeger](https://www.jaegertracing.io/docs/latest/) to collect traces from an application. To access the dashboard, follow these steps:

1. Use the following command to show the host address:
```shell
make display-endpoints
```

2. Enter the Jaeger address into the browser

### Logs

A **log** is a tool that show some message. These messages are crafted by the application developer(s) for a variety of purposes (following execution, debuging, etc.). Logs tend to be volumous in nature. Thus, normally only a subset of all possible displayed logs are captured for performance and storage reasons.

ITBench uses [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/) to collect logs from application, which are then stored in Clickhouse. To access the dashboard, follow these steps:

1. Use the following command to show the host address:
```shell
make display-endpoints
```

2. Enter the Clickhouse address into the browser

### Financial Metrics

These metrics are more of a specification of a type of metric, [discussed earlier](#alerts--metrics).

ITBench uses [OpenCost](https://opencost.io/docs/) to collect and analyze cost metrics of an application. These metrics themselves are supplied from [Promethues](https://prometheus.io/docs/introduction/overview/). To access the dashboard, follow these steps:

1. Use the following command to show the host address:
```shell
make display-endpoints
```

2. Enter the OpenCost address into the browser

## Troubleshooting

### Displayed dashboard address is not applicable

When using `make display-endpoints`, sometimes the value of the address given is `N/A`. Generally, this is the result of one of the following:

1. The tool is not installed and thus was not connected to the gateway. To fix this, run `make deploy-tools` with the correct `SCENARIO_NUMBER` or `tools.yaml` group variable configuration.
2. **Kind**: Cloud Provider Kind is not running. Please consult the [Troubleshooting section](../../clusters/kind/README.md#load-balancer-ip-address-is-unreacheable) for more information on how to fix this issue.
3. **Cloud Provider**: Sometimes it takes some time for a cloud provider (ie: AWS, GCP, Azure, etc) to generate a domain name for the new load balancer. This should be made in time, but may need further debuging in their respective dashboards to fix.

### Dashboard is unreachable

When using the endpoints given by `make display-endpoints`, sometimes the address is not reachable or takes some time to reach. Generally, this is due to some slowness in doing the DNS registration. Wait for about two or so minutes after `make deploy-tools` has created the gateway before attempting to access the dashboard even if the address has already been reserved.

### Failure to Deploy Tools or Applications

The `make deploy-tools` and `make deploy-applications` can be subject to temporary failures. Sometimes, the repository where the images for softwares (ie, GitHub, Quay, DockerHub) are having temporary outtages. Having a slow internet connection or strict firewalls can also cause failures in with this step.

There is a subcategory of this failure which are DockerHub specific. Since Docker enforces [rate limits by IP address](https://docs.docker.com/docker-hub/usage/), one can become unable to pull images from that repository for a time. The easiest way to circumvent this issue is to make a Docker account and deploy a secret with the access token to the cluster. To do so, follow these steps:

1. Login or create a DockerHub account at https://www.docker.com/get-started/
2. Create a personal access token (PAT)
    - Log into Docker Hub
    - Go to Account Settings → Security
    - Click `New Access Token`
    - Give it a descriptive name
    - Select appropriate permissions (`Public Repo Read` required as to pull public images)
    - Copy the generated token
3. Create a Kubernetes secret in the following namespaces (`book-info`, `clickhouse`, `clickhouse-operator`,`kube-gateways`, `istio-system`, `opensearch`, `opentelemetry-collectors`, `otel-demo`)
```bash
kubectl create secret docker-registry dockerhub-secret \
    --docker-server=https://index.docker.io/v1/ \
    --docker-username=your-dockerhub-username \
    --docker-password=your-access-token \
    --docker-email=your-email@example.com \
    --namespace=your-namespace
```
