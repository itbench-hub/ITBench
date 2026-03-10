# kOps Cluster Setup

[kOps](https://kops.sigs.k8s.io/) is a tool which create a [Kubernetes](https://kubernetes.io/) cluster using resources offered by cloud providers.

> [!NOTE]
> As of the time writing (**03/09/2026**) these playbooks in this directory use [Amazon Web Services (AWS)](https://docs.aws.amazon.com/#products) as the provisoner. While other cloud providers may supported by kOps, orchestrating the additional pieces from those provides is in instrumented here.

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
| [runner.yaml](./inventory/group_vars/basic/runner.yaml.example) | Configures the name prefix for a single cluster |
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
