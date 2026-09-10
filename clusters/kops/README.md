# kOps Cluster Setup

[kOps](https://kops.sigs.k8s.io/) is a tool which creates a [Kubernetes](https://kubernetes.io/) cluster using resources offered by cloud providers.

[Kyverno](https://kyverno.io/) ensures that registry secrets (used to access private Docker registries) are configured in every namespace on the cluster.

>[!NOTE]
>As of the time of writing (**03/09/2026**) these playbooks use [Amazon Web Services (AWS)](https://docs.aws.amazon.com/#products) as the provisioner. While other cloud providers may be supported by kOps, orchestrating the additional pieces from those providers is not instrumented here.

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

The playbooks use a set of [group variables](./inventory/group_vars/all/) to configure AWS resources and the clusters themselves:

| File | Description |
| --- | --- |
| [aws.yaml](./inventory/group_vars/all/aws.yaml.example) | AWS region, VPC CIDR, S3 state bucket, and availability zones |
| [cluster.yaml](./inventory/group_vars/all/cluster.yaml.example) | Kubernetes version, networking mode, and node sizes/counts |
| [docker.yaml](./inventory/group_vars/all/docker.yaml.example) | Private Docker registry secret (optional) |
| [ssh_keys.yaml](./inventory/group_vars/all/ssh_keys.yaml.example) | SSH public key path for cluster node access |

>[!NOTE]
>Some YAML files contain commented-out sections for optional parameters. Leave them commented out if not needed; otherwise uncomment and fill them in.

1. Create the group variable files from the provided templates
```shell
make group-vars
```

2. Edit the generated group variable files accordingly

>[!IMPORTANT]
>Before or during this step, create an SSH key pair. This allows SSH access to cluster nodes after creation. A guide to generating an SSH key can be found [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent).

3. Configure the AWS CLI
```shell
aws configure
```

## Cluster Management

There are two management targets: **Environment Cluster** and **Argo Stack**.

An **Argo stack** provisions one orchestrator cluster and one or more environment clusters, all sharing a single [VPC](https://docs.aws.amazon.com/vpc/latest/userguide/what-is-amazon-vpc.html) with one subnet per cluster. It is intended for running multiple scenarios with multiple trials simultaneously. Due to the resources required, the Argo stack is not recommended for general development.

An **environment cluster** is a single cluster for local development or running individual benchmark trials.

Both targets use the `CLUSTER_NAME_PREFIX` Makefile variable (default: `itbench-dev`) to namespace all AWS and cluster resources. Override it on the command line if sharing an S3 state bucket with other users:

```shell
CLUSTER_NAME_PREFIX=my-prefix make create-environment-cluster
```

### Environment Cluster

#### Creation

1. Run the following command to create a cluster
```shell
make create-environment-cluster
```

2. Once the clusters are ready (kOps validation can take up to 20 minutes), run the following command to export the kubeconfig, configure the cluster, and write the `.env` file for the SRE scenarios:
```shell
make get-cluster-kubeconfig
```

3. To access the cluster from a terminal window, use the following command printed at the end of the previous step:
```shell
export KUBECONFIG=$(pwd)/kubeconfigs/<cluster name>
kubectl cluster-info
```

4. **(Optional)**: To install a Docker registry secret into the cluster, use the following command:
```shell
make install-cluster-docker-registry
```

#### Deletion

1. Run the following command to delete the cluster
```shell
make destroy-environment-cluster
```

### Argo Stack

The number of environment clusters in the stack is controlled by the `ENVIRONMENTS_COUNT` Makefile variable (default: `1`). Override it as needed:

```shell
ENVIRONMENTS_COUNT=20 make create-argo-stack
```

#### Creation

1. Run the following command to create the Argo stack
```shell
make create-argo-stack
```

2. Once the clusters are ready (kOps validation can take up to 20 minutes per cluster, running in parallel), run the following command to export kubeconfigs, configure the environment clusters, write the `.env` file, and sync the stack group variables for the SRE scenarios:
```shell
make get-stack-kubeconfigs
```

3. To access the orchestrator cluster from a terminal window, use the following command printed at the end of the previous step:
```shell
export KUBECONFIG=$(pwd)/kubeconfigs/<cluster name>
kubectl cluster-info
```

4. **(Optional)**: To install a Docker registry secret into all Argo stack clusters, use the following command:
```shell
make install-stack-docker-registry
```

#### Deletion

1. Run the following command to destroy the Argo stack
```shell
make destroy-argo-stack
```

## Troubleshooting

### AWS Resource Limits

While the playbooks include checks to surface clear errors, resource creation or deletion failures can still occur. Often this is caused by [service quota limits](https://docs.aws.amazon.com/servicequotas/latest/userguide/intro.html) being reached (e.g. no VPC capacity in a region). To resolve this, either [request a quota increase](https://docs.aws.amazon.com/servicequotas/latest/userguide/request-quota-increase.html) or remove unused resources.

### Cluster Validation Errors

kOps clusters must pass a validation step before they can be used. This is run automatically during the `get-cluster-kubeconfig` / `get-stack-kubeconfigs` steps. After the cluster is built, the validation results can also be checked manually:
```shell
CLUSTER_NAME=<cluster name> make validate-cluster
```

>[!NOTE]
>Validation only needs to be checked manually in the case of a failure, which will cause the relevant `get-*` command to error.

The following command can attempt to remediate a cluster with validation failures. **This is not guaranteed to produce a working cluster, but may help recover from known failure modes.**
```shell
CLUSTER_NAME=<cluster name> make fix-cluster
```
