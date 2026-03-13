# kOps Cluster Setup

[kOps](https://kops.sigs.k8s.io/) is a tool which create a [Kubernetes](https://kubernetes.io/) cluster using resources offered by cloud providers.

> [!NOTE]
> As of the time writing (**03/09/2026**) these playbooks in this directory use [Amazon Web Services (AWS)](https://docs.aws.amazon.com/#products) as the provisoner. While other cloud providers may supported by kOps, orchestrating the additional pieces from those provides is not instrumented here.

## Required Software

- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (v2)
- [kOps](https://kops.sigs.k8s.io/getting_started/install/)

## Installation

### MacOS ([Homebrew](https://brew.sh/))

1. Download the following packages
```shell
brew install awscli
brew install kops
```

### RHEL

1. Download the following packages
```shell
sudo dnf install awscli
sudo dnf install curl
sudo dnf install jq
```

2. Follow the instructions listed [here](https://kops.sigs.k8s.io/getting_started/install/#linux) to install `kops`

## Set Up

The playbooks feature a number of [group variables](./inventory/group_vars/). Each one will be described here:

| File Name | Function |
| --- | --- |
| [aws.yaml](./inventory/group_vars/all/aws.yaml.example) | Configures region, vpc, and s3 storage |
| [cluster.yaml](./inventory/group_vars/all/cluster.yaml.example) | Configures the cluster itself |
| [docker.yaml](./inventory/group_vars/all/docker.yaml.example) | Configures the registry secret |
| [runner.yaml](./inventory/group_vars/single/runner.yaml.example) | Configures the name prefix for a single cluster |
| [ssh_keys.yaml](./inventory/group_vars/all/ssh_keys.yaml.example) | Configured the ssh key to access the cluster |
| [stack.yaml](./inventory/group_vars/awx/stack.yaml) | Configures the name prefix and number of clusters in AWX stack |

> [!NOTE]
> Some of the yaml files have sections commented out. This is to show parameters which are optional. If they are not needed, leave them commented out. Otherwise, uncomment them and fill them out as needed.

1. Create the playbooks' group variables from the templates
```shell
make group-vars
```

2. Edit the group variables files accordingly

> [!NOTE]
> Before or during this step, one should create an SSH key. This will allow ssh access to the cluster after creation. A guide to making an ssh key can be found [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent).

3. Configure the AWS CLI tool
```shell
aws configure
```

## Cluster Management

There are two management targets that are controlled by these playbooks: **AWX Stack** and **Single Cluster**.

An AWX stack requires multiple clusters (one per scenario) and a controller cluster. The controller cluster is called the `head` and any cluster running a scenario is called a `runner`. To reduce resource complexity, only one [virtual private cloud (VPC)](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html) object is created. From that VPC, several [subnets](https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html) (one per cluster) are created.

A single cluster is only one `runner` cluster.

For general development, most users will require only the single cluster target. The AWX stack is only recommended for running multiple scenarios with multiple trials simulatenously due to the intense amount of resources required.

> [!NOTE]
> If one requires a cluster have access to a private Docker registry, please configure the `inventory/group_vars/all/docker.yaml` file. Once deployed, [Kyverno](https://kyverno.io/) ensures that all the namespaces on the cluster will also be updated with the secret information.

### AWX Stack

#### Creation

1. Run the following command to create a "stack" of clusters
```shell
make create-awx-stack
```

2. Once the previous command successfully completes, run the following command to export the kubeconfig:
```shell
make get-stack-kubeconfigs
```

3. To access the cluster from a terminal window, use the following command:
```shell
export KUBECONFIG=$(pwd)/kubeconfigs/<cluster name>
kubectl cluster-info
```

### Deletion

1. Run the following command to delete a cluster
```shell
make destroy-awx-stack
```

### Single Cluster

#### Creation

1. Run the following command to create a cluster
```shell
make create-cluster
```

2. Once the previous command successfully completes, run the following command to export the kubeconfig:
```shell
make get-cluster-kubeconfig
```

3. To access the cluster from a terminal window, use the following command:
```shell
export KUBECONFIG=$(pwd)/kubeconfigs/<cluster name>
kubectl cluster-info
```

### Deletion

1. Run the following command to delete a cluster
```shell
make destroy-cluster
```

## Troubleshooting

### AWS Resource Limits

While the playbooks have some checking to avoid unclear gaps in execution, sometimes resource creation or deletion failures occur. Often times, this is because of a [lack of resources available](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html) (ie, no VPCs availabilty in a region). In order to fix this, one must either [increase the service quotas](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html) for a given resource or remove unused resources.

### Cluster Validation Errors

Before use, kOps cluster must pass a validation step. This step is run as part of the creation process. After the cluster is built, the results of the validation can be checked using the following command:
```shell
CLUSTER_NAME=<cluster name> make validate-cluster
```

> [!NOTE]
> Generally speaking, the validation results only need to be checked in the case of a validation failure. This will result in the creation command failing.


Clusters may fail to validate for a variety of reasons. While not complete, the following command can be used to attempt remidiation of a cluster with validation failures. **This command is not guarenteed to result in a working cluster, but may help recover the cluster in response to a known validation failure.**
```shell
CLUSTER_NAME=<cluster name> make fix-cluster
```
