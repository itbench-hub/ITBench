# Minikube Cluster Setup

[Minikube](https://minikube.sigs.k8s.io/) is tool which uses [Docker](https://www.docker.com/) containers to create a [Kubernetes](https://kubernetes.io/) cluster on a local machine.

## Required Software

- [Minikube](https://minikube.sigs.k8s.io/)
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/)

>[!NOTE]
>Generally, there are minimal differences between using Podman or Docker for Minikube. For simplicity, only instructions for Podman have been provided. However, if one wants to use Docker, the instructions for downloading it are provided [here](https://docs.docker.com/get-started/get-docker/).

>[!IMPORTANT]
>If using a Minikube cluster for SRE scenarios, please ensure that the machine has the necessary [hardware requirements](../../documentation/getting-started/awx.md#requirements).

## Installation

### MacOS ([Homebrew](https://brew.sh/))

1. Download the following packages
```shell
brew install minikube
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

2. Follow the instructions listed [here](https://minikube.sigs.k8s.io/docs/start/) to install `minikube`

3. Edit the `/etc/sysctl.conf` to avoid common errors (ie, `Pod errors due to “too many open files"`, `vm.max_map_count`, etc.) by adding the following lines:
```
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
vm.max_map_count = 262144
```

4. Run the following command to apply the changes made in the previous step:
```shell
sudo sysctl -p
```

5. If the cluster will be used to run Chaos Mesh faults, edit the `/etc/modules-load.d/ebtables.conf` file by adding the following lines:
```
ebtable_broute
ebtable_nat
```

6. Run the following command to apply the changes made in the previous step. **This only has to be done if the machine has not been rebooted as the changes will be applied automatically the next time it boots**:
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

3. Set the machine to root user
```shell
podman machine set --rootful
```

>[!IMPORTANT]
>Root access is needed because generate IPs for port 80 (used for external access via the Kubernetes Gateway). These ports are protected and without the sufficient priveleges, the tunnel will fail to provision the addresses.

4. Start the Machine
```shell
podman machine start
```

## Cluster Management

Once the cluster has been started, it can be accessed with kubectl using the following command:

```shell
export KUBECONFIG=~/.kube/config
kubectl cluster-info
```

### AWX Cluster

#### Creation

1. Run the following command to create a Minikube cluster:
```shell
make create-awx-cluster
```

2. Open a new terminal window and run the following command to start the Minikube tunnel
```shell
make start-awx-tunnel
```

#### Deletion

1. In the terminal window running the Minikube tunnel, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Minikube cluster
```shell
make destroy-awx-cluster
```

### Simple Cluster

#### Creation

1. Run the following command to create a Minikube cluster:
```shell
make create-simple-cluster
```

2. Open a new terminal window and run the following command to start the Minikube tunnel
```shell
make start-simple-tunnel
```

#### Deletion

1. In the terminal window running the Minikube tunnel, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Minikube cluster
```shell
make destroy-simple-cluster
```

## Troubleshooting

This section will mainly highlight key issues that one may encounter when running Minikube. Minikube already has an [FAQ](https://minikube.sigs.k8s.io/docs/handbook/troubleshooting/) which contains many more cases.

### RHEL

#### "CrashLoopBackOff" in Chaos-Controller Manager Pods

**Problem:**  The `chaos-controller-manager` pods may enter a `CrashLoopBackOff` state due to the error:
```
"too many files open"
```

**Solution:** Please refer to this [link](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).
