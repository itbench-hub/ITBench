# Kind Cluster Setup

[Kind](https://kind.sigs.k8s.io/) is tool which uses [Docker](https://www.docker.com/) containers to create a [Kubernetes](https://kubernetes.io/) cluster on a local machine.

[Cloud Provider Kind](https://github.com/kubernetes-sigs/cloud-provider-kind) is tool which creates containers to allocate an IP addresses for the [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/) that require [Load Balancers](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer). The addresses can be used to reach tools running on the cluster from an Internet browser.

## Required Software

- [Golang](https://go.dev/) **v1.24+**
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/)

>[!NOTE]
>Generally, there are minimal differences between using Podman or Docker for Kind. For simplicity, only instructions for Podman have been provided. However, if one wants to use Docker, the instructions for downloading it are provided [here](https://docs.docker.com/get-started/get-docker/).

>[!IMPORTANT]
>If using a Kind cluster for SRE scenarios, please ensure that the machine has the necessary [hardware requirements](../../documentation/getting-started/argo.md#requirements).

## Installation

>[!NOTE]
>Kind and Cloud Provider Kind are installed and managed by Golang. Thus, neither tool needs to be installed independently of this process.

### MacOS ([Homebrew](https://brew.sh/))

>[!IMPORTANT]
>Previous versions of ITBench used an older version of Cloud Provider Kind to provide IP addresses on MacOS. Since upgrading to v0.11+ of this tool, this functionality is no longer possible as ITBench can use multiple gateways that ask for the same port (ie, Book Info). Thus, [**Minikube**](../minikube/README.md) is the now recommended development environment for MacOS. However, scenarios involving applications which do not creating additional gateways (ie, OpenTelemetry Demo) can still function as is on MacOS with the following information.

1. Download the following packages
```shell
brew install go
brew install podman
```

2. Download the following packages **(optional)**
```shell
brew install --cask podman-desktop
```

### Linux

#### RHEL

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

- [argo](./configs/argo.yaml) — for Argo Workflows orchestration (multi-cluster, multi-trial benchmarks)
- [environment](./configs/environment.yaml) — for basic use cases such as developing faults or scenarios or running a single benchmark trial

Regardless of the configuration used, once the cluster has been started, it can be accessed with kubectl using the following command:

```shell
export KUBECONFIG=~/.kube/config
kubectl cluster-info
```

### Argo Stack

#### Creation

1. Run the following command to create a two-cluster Kind stack for Argo Workflows orchestration:
```shell
make create-argo-stack
```

2. Open a new terminal window and run the following command to start the Cloud Provider Kind
```shell
make run-service-provider
```

#### Deletion

1. In the terminal window running the Cloud Provider Kind, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy the Argo stack
```shell
make destroy-argo-stack
```

### Environment Cluster

#### Creation

1. Run the following command to create a Kind cluster:
```shell
make create-environment-cluster
```

2. Open a new terminal window and run the following command to start the Cloud Provider Kind
```shell
make run-service-provider
```

#### Deletion

1. In the terminal window running the Cloud Provider Kind, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy the Kind cluster
```shell
make destroy-environment-cluster
```

## Troubleshooting

This section will mainly highlight key issues that one may encounter when running Kind. Kind already has an [FAQ](https://kind.sigs.k8s.io/docs/user/known-issues/) which contains many more cases.

### MacOS

#### Load Balancer IP Address is unreacheable

**Problem**: The IP address assigned to a Kubernetes service is not reachable via `curl` or the browser.

**Solution**: The cause of this is explained in further detail [here](https://github.com/kubernetes-sigs/cloud-provider-kind?tab=readme-ov-file#enabling-load-balancer-port-mapping). After installing the service on the Kubernetes cluster (ie, after running `make deploy-tools` for the SRE scenarios), run the `make sync-network-group-vars` command. This will retrieve the host port from the container operating as the provider so that the service can be reached via `localhost`.

### RHEL

#### "CrashLoopBackOff" in Chaos-Controller Manager Pods

**Problem:**  The `chaos-controller-manager` pods may enter a `CrashLoopBackOff` state due to the error:
```
"too many files open"
```

**Solution:** Please refer to this [link](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).
