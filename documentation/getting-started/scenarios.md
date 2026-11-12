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

- [mise](https://mise.jdx.dev/) (manages `uv`, `helm`, `kubectl` and runtime environments)

## Installation

1. Install mise following the [official installation guide](https://mise.jdx.dev/getting-started.html):
```shell
# macOS / Linux
curl https://mise.run | sh
# Or via Homebrew on macOS
brew install mise
```

2. Install pinned tools and project dependencies:
```shell
mise install
mise run install:dev
```

## Set Up

1. Create a Kubernetes cluster. ITBench offers setup help for running a cluster on a local machine with [Kind](../../clusters/kind/README.md) or on [AWS](../../clusters/kops/README.md).

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

>[!TIP]
>See [scenario library](../library/scenarios/README.md) for a full comprehensive list of runnable scenarios.

### Deploying and Starting Scenarios

1. Deploy the environment and applications for a scenario:
```shell
uv run itbench deploy environment --scenario 1
```

2. Inject scenario faults:
```shell
uv run itbench inject faults --scenario 1
```

>[!TIP]
>Switching to a different scenario can be done by changing the `--scenario` argument. Documentation for the available scenarios can be found [here](../library/scenarios/README.md).

### Running an Agent

Once a scenario has started, one can begin running an agent to pull information from the cluster and the various observability tools so that it can attempt to diagnose and remediate a problem.

>[!TIP]
>If you don't have an agent yet, you can use the [SRE-Agent](https://github.com/itbench-hub/itbench-sre-agent) to see how it works.

>[!IMPORTANT]
>A scenario starts once fault injection has begun. Since faults may be injected after [certain conditions](../library/waiters/README.md) have been fulfilled, an agent may be running before one or multiple faults have been injected.

### Stopping Scenarios

1. Clean up and undeploy the scenario:
```shell
uv run itbench remove faults
uv run itbench undeploy environment --yes
```

## Observing Scenario Impact

Every fault in ITBench causes a noticeable effect on the application it has been injected to which can be obsevered through observability data.

### Alerts & Metrics

An **alert** is a notification that some threshold (set by the user) has been surpased. These thresholds are defined using **metrics**. When an alert is active, the engineers are notified that something is wrong with an application and that they need to begin invetigating.

ITBench uses [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/) and [Prometheus](https://prometheus.io/docs/introduction/overview/) to collect metrics and configure alerts from an application and Kubernetes cluster. To access the dashboard, follow these steps:

1. Use `kubectl port-forward` to forward the Prometheus pod:
```shell
kubectl -n itbench-observability port-forward pod/prometheus-kube-prometheus-stack-prometheus-0 9090
```

2. Open `http://localhost:9090` in your browser (`/alerts` for alerts dashboard and `/query` for the query dashboard). On OpenShift, the platform console serves as the dashboard.

### Traces

A **trace** is a debug tool that - typically - shows the progress of a request as it moves through an application. This information allows engineers to see which services are failing to handle the request.

ITBench uses [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/) and [Jaeger](https://www.jaegertracing.io/docs/latest/) to collect traces from an application. To access the dashboard, follow these steps:

1. Use `kubectl port-forward` to forward the Jaeger Service:
```shell
kubectl -n itbench-observability port-forward svc/jaeger-collector 16686
```

2. Open `http://localhost:16686/jaeger/` in your browser.

### Logs

A **log** is a tool that show some message. These messages are crafted by the application developer(s) for a variety of purposes (following execution, debuging, etc.). Logs tend to be volumous in nature. Thus, normally only a subset of all possible displayed logs are captured for performance and storage reasons.

ITBench uses [OpenTelemetry](https://opentelemetry.io/docs/what-is-opentelemetry/) to collect logs from application, which are then stored in Clickhouse. To access the dashboard, follow these steps:

1. Use `kubectl port-forward` to forward the ClickHouse Service:
```shell
kubectl -n itbench-observability port-forward svc/clickhouse-observability 8123
```

2. Open `http://localhost:8123/play` in your browser.

### Financial Metrics

These metrics are more of a specification of a type of metric, [discussed earlier](#alerts--metrics).

ITBench uses [OpenCost](https://opencost.io/docs/) to collect and analyze cost metrics of an application. These metrics themselves are supplied from [Prometheus](https://prometheus.io/docs/introduction/overview/). To access the dashboard, follow these steps:

1. Use `kubectl port-forward` to forward the OpenCost Service:
```shell
kubectl -n opencost port-forward svc/opencost 9090
```

2. Open `http://localhost:9090` in your browser.

## Troubleshooting

### Failure to Deploy Tools or Applications

Deploying tools and applications can be subject to temporary failures. Sometimes, the repository where the images for softwares (ie, GitHub, Quay, DockerHub) are having temporary outages. Having a slow internet connection or strict firewalls can also cause failures with this step.

There is a subcategory of this failure which are DockerHub specific. Since Docker enforces [rate limits by IP address](https://docs.docker.com/docker-hub/usage/), one can become unable to pull images from that repository for a time. The easiest way to circumvent this issue is to make a Docker account and deploy a secret with the access token to the cluster. To do so, follow these steps:

1. Login or create a DockerHub account at https://www.docker.com/get-started/
2. Create a personal access token (PAT)
    - Log into Docker Hub
    - Go to Account Settings → Security
    - Click `New Access Token`
    - Give it a descriptive name
    - Select appropriate permissions (`Public Repo Read` required as to pull public images)
    - Copy the generated token
3. Create a Kubernetes secret in the following namespaces (`clickhouse`, `clickhouse-operator`, `kube-gateways`, `istio-system`, `opentelemetry-collectors`, `otel-demo`)
```bash
kubectl create secret docker-registry dockerhub-secret \
    --docker-server=https://index.docker.io/v1/ \
    --docker-username=your-dockerhub-username \
    --docker-password=your-access-token \
    --docker-email=your-email@example.com \
    --namespace=your-namespace
```
