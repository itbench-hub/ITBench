# Kind Cluster Setup

[Kind](https://kind.sigs.k8s.io/) is tool which uses [Docker](https://www.docker.com/) containers to create a [Kubernetes](https://kubernetes.io/) cluster on a local machine.

[Cloud Provider Kind](https://github.com/kubernetes-sigs/cloud-provider-kind) is tool which creates containers to allocate an IP addresses for the [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/) that require [Load Balancers](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer). The addresses can be used to reach tools running on the cluster from an Internet browser.

## Required Software

- [Golang](https://go.dev/) **v1.24+**
- [Podman](https://podman.io/)

> [!NOTE]
> Generally, there are minimal differences between using Podman or Docker for Kind. For simplicity, only instructions for Podman have been provided. However, if one wants to use Docker, the instructions for downloading it are provided [here](https://docs.docker.com/get-started/get-docker/).

> [!WARNING]
> If using a Kind cluster for SRE scenarios, please ensure that the machine has the necessary [hardware requirements](../../scenarios/sre/docs/hardware_specification.md).

## Installation

> [!NOTE]
> Kind and Cloud Provider Kind are installed and managed by Golang. Thus, neither tool needs to be installed independently of this process.

### MacOS ([Homebrew](https://brew.sh/))

1. Download the following packages
```shell
brew install go
brew install podman
```

2. Download the following packages **(optional)**
```shell
brew install --cask podman-desktop
```

### RHEL

1. Download the following packages
```shell
dnf install lsof
dnf install make
dnf install podman
```

2. Edit the `/etc/sysctl.conf` to avoid common errors (ie, `Pod errors due to “too many open files"`, `vm.max_map_count`, etc.) by adding the following lines:
```
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
vm.max_map_count = 262144
```

3. Run the following command to apply the changes made in the previous step:
```shell
sudo sysctl -p
```

4. If the cluster will be used to run Chaos Mesh faults, edit the `/etc/modules-load.d/ebtables.conf` file by adding the following lines:
```
ebtable_broute
ebtable_nat
```

5. Run the following command to apply the changes made in the previous step. **This only has to be done if the machine has not been rebooted as the changes will be applied automatically the next time it boots**:
```bash
sudo modprobe ebtable_broute
sudo modprobe ebtable_nat
```

## Set Up

### Podman

1.  Initialize a Podman machine. Using the following command to generate a machine called `podman-machine-default`.
```shell
podman machine init
```

2. Set the machine's resources.
```shell
podman machine set --cpus 8 -m 16384
```

3. Start the Machine
```shell
podman machine start
```

## Cluster Management

Two configuration templates are provided in the `configs` directory:

- [awx](./configs/awx.yaml)
- [simple](./configs/simple.yaml)

The `simple` configuration is for basic use cases, such as developing new faults or scenarios or running a single benchmark trial. This cluster will suffice for most needs. For management instructions for a Kind cluster based on the `simple` configuration, please see [here](#simple-cluster).

The `AWX` configuration is for advanced use cases which require orchestration to run multi-trial benchmarks across a cluster or clusters. This requires a machine with significantly more resources than the `simple` configuration. For management instructions for a Kind cluster based on the `awx` configuration, please see [here](#awx-cluster).

Regardless of the configuration used, once the cluster has been started, it can be accessed with kubectl using the following command:

```shell
export KUBECONFIG=~/.kube/config
kubectl cluster-info
```

### AWX Cluster

#### Creation

1. Run the following command to create a Kind cluster:
```shell
make create-awx-cluster
```

2. Open a new terminal window and run the following command to start the Cloud Provider Kind
```shell
sudo make run-service-provider
```

#### Deletion

1. In the terminal window running the Cloud Provider Kind, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Kind cluster
```shell
make destroy-awx-cluster
```

### Simple Cluster

#### Creation

1. Run the following command to create a Kind cluster:
```shell
make create-simple-cluster
```

2. Open a new terminal window and run the following command to start the Cloud Provider Kind
```shell
sudo make run-service-provider
```

#### Deletion

1. In the terminal window running the Cloud Provider Kind, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Kind cluster
```shell
make destroy-simple-cluster
```

## Troubleshooting

This section will mainly highlight key issues that one may encounter when running Kind. Kind already has an [FAQ](https://kind.sigs.k8s.io/docs/user/known-issues/) which contains many more cases.

### RHEL

#### "CrashLoopBackOff" in Chaos-Controller Manager Pods

**Problem:**  The `chaos-controller-manager` pods may enter a `CrashLoopBackOff` state due to the error:
```
"too many files open"
```

**Solution:** Please refer to this [link](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).
