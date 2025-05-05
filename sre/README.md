# ITBench for Site Reliability Engineering (SRE) and Financial Operations (FinOps)

**[Paper](https://github.com/IBM/ITBench/blob/main/it_bench_arxiv.pdf) | [Incident Scenarios](./docs/incident_scenarios.md) | [Tools](./docs/tools.md)

## Overview
ITBench uses open source technologies to create completely repeatable and reproducible scenarios on a Kubernetes platform. A SRE scenario involves deploying a set of observability tools, a sample application, and triggering an incident (referred to as task) in the environment.

![itbench_sre_task_scenario.png](./docs/itbench_sre_task_scenario.png)
While this repository focuses on scenarios, an open-source Language Model (LM)-based SRE-Agent that aims to diagnose and remediate issues in these scenario environments can be found [here](https://github.com/IBM/ITBench-SRE-Agent).

### Structure

This project uses Ansible to automate the deployment and undeployment of technologies to a Kubernetes cluster and the injection and removal of faults.
The playbook run is configured using variables defined in `group\_vars`.

| Directory                   | Purpose                                                                                                      |
|-----------------------------|--------------------------------------------------------------------------------------------------------------|
| `roles/observability_tools` | Handles  the deployment and removal of observability tools                                                   |
| `roles/sample_applications` | Handles the deployment and removal of sample applications                                                    |
| `roles/fault_injection`     | Provides reusable fault injection mechanisms                                                                 |
| `roles/fault_removal`       | Provides mechanisms to remove (injected) faults from the environment                                         |
| `roles/incident_`           | Contains scenarios that leverage the fault injection and removal mechanisms defined in the directories above |

## Recommended Software

### MacOS

- [Homebrew](https://brew.sh/)

## Required Software

- [Python3](https://www.python.org/downloads/) (v3.12.Z)
- [Helm](https://helm.sh/docs/intro/install/) (v3.16+)
- [Kubectl](https://kubernetes.io/docs/tasks/tools/)

### Installing Required Software via Homebrew (for MacOS)

1. Install [Homebrew](https://brew.sh/)
2. Install required software
```bash
brew install helm
brew install kubectl
brew install python@3.12
```

### Installing Required Software (for Red Hat Enterprise Linux -- RHEL)

1. Install Helm by following the instructions [here](https://helm.sh/docs/intro/install/#from-script)
2. Set up kubectl by following the instructions [here](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/#install-using-native-package-management)
3. Set up Python by running:
```bash
sudo dnf install python3.12
```

## Getting Started – Deploying an Incident Scenario

### Installing Dependencies

1. Create a Python virtual environment
```bash
python3.12 -m venv venv
source venv/bin/activate
```

2. Install Python dependencies
```bash
python -m pip install -r requirements.txt
```

3. Install Ansible collections.
```bash
ansible-galaxy install -r requirements.yaml
```

4. Create the `all.yaml` file from the template.
```bash
cp group_vars/all.yaml.example group_vars/all.yaml
```

_Note: These steps only need to be done once upon the initial set up._
_Note: Depending on what kind of cluster setup is needed, further dependencies may need to be installed. Please see the below section for further details._

### Cluster Setup

#### Local Cluster

For instruction on how to create a kind cluster on MacOS, please see the instructions [here](./local_cluster/README.md).
For instruction on how to create a kind cluster on Red Hat Enterprise Linux (RHEL) virtual machine (VM) or bare-metal instance, please see the instructions [here](./local_cluster/README_RHEL.md).

#### Remote Cluster

For instruction on how to create an cloud provider based Kubernetes cluster, please see the instructions [here](./remote_cluster/README.md).

Currently, only AWS is supported. AWS clusters are provisioned using [kOps](https://kops.sigs.k8s.io/).

### Running the Incident Scenarios

Now that our cluster is up and running, let's proceed with the deployment of the observability tools and application stack, injecting the fault, and monitoring of alerts in the Grafana dashboard.

1. Deploy the observability tools.

```bash
make deploy_observability_stack
```
The observability tools deployment includes Prometheus, Grafana, Loki, Elasticsearch, Jaeger, OpenSearch and K8s-events-exporter. For additional details on the observability tools deployed please head [here](./docs/tools.md).

2. Deploy one of the sample applications. In this case we are deploying OpenTelemetery's Astronomy Shop Demo.

```bash
make deploy_astronomy_shop
```
Currently IT-Bench supports two sample applications--OpenTelemetery's Astronomy Shop Demo and Deathstartbench's Hotel Reservation. For additional details on the sample applications please head [here](./docs/sample_applications.md).

3. Once all pods are running, inject the fault for an incident.

```bash
INCIDENT_NUMBER=1 make inject_incident_fault
```
Currently the incident scenarios open-sourced are incidents 1, 3, 23, 26, 27, and 102. One can leverage any one of these incidents at this point in time in their own environemnts. Additional details on the incident scenarios themselves and the fault mechanisms can be found [here].

4. After fault injection, to view alerts in the Prometheus dashboard, let's use port forwarding.

```bash
kubectl port-forward svc/ingress-nginx-controller -n ingress-nginx 8080:80 &
```

5. Now head over to the following URL:

```bash
http://localhost:8080/prometheus/alerts
```

6. Alerts are defined:
- To track status of deployments across the different namespaces
- To track `latency` across the different services
- To track `error` across the different services
- To track Kafka connection status across the Kafka-related components
An Alert's default `State` is `Inactive`. After few minutes, the fault `State` changes to `Firing`, indicating fault manifestation. The alert definitions are located [here](roles/observability_tools/templates/prometheus-alerting-rules.j2) and have been curated using this [guide](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/).

9. (Optional) You only need to do this if you plan to leverage our [SRE-Agent](https://github.com/IBM/itbench-sre-agent). Leverage the values below for the `.env.tmpl`
```
OBSERVABILITY_STACK_URL=http://localhost:8080
TOPOLOGY_URL=http://localhost:8080/topology
```

9. To remove the injected fault, run the following `make` command:

```bash
INCIDENT_NUMBER=1 make remove_incident_fault
```
After executing the command, the alert's `State` should change back to `Inactive` from `Firing`, indicating that the fault has been removed.

10. Once done you can undeploy the observability, followed by the application stack by running:
```bash
make undeploy_astronomy_shop
make undeploy_observability_stack
```

_Note_: For a full list of `make` commands, run the following command:

```bash
make help
```
