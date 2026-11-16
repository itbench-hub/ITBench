# Minikube Cluster Setup

[Minikube](https://minikube.sigs.k8s.io/) is tool which uses [Docker](https://www.docker.com/) containers to create a [Kubernetes](https://kubernetes.io/) cluster on a local machine.

## Required Software

- [mise](https://mise.jdx.dev/)
- [Minikube](https://minikube.sigs.k8s.io/)
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/)

>[!NOTE]
>Generally, there are minimal differences between using Podman or Docker for Minikube. For simplicity, only instructions for Podman have been provided. However, if one wants to use Docker, the instructions for downloading it are provided [here](https://docs.docker.com/get-started/get-docker/).

>[!IMPORTANT]
>If using a Minikube cluster for SRE scenarios, please ensure that the machine has the necessary [hardware requirements](../../documentation/getting-started/awx.md#requirements).

## Installation

>[!NOTE]
>Minikube is installed and managed by mise. Run the following command from the root of the repository to install it. It does not need to be installed independently of this process.
>```shell
>mise -E minikube install
>```
>
>The `minikube` environment can be made the default for a shell session with `export MISE_ENV=minikube`, which allows the `-E minikube` flag to be omitted from the commands below.

### MacOS ([Homebrew](https://brew.sh/))

1. Download the following packages
```shell
brew install mise
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

Each cluster's kubeconfig is written to the `kubeconfigs` directory (ie, `clusters/minikube/kubeconfigs/minikube-environment`) instead of `~/.kube/config`. The create commands print the `export KUBECONFIG=...` line to run so that kubectl and the `itbench` CLI use the cluster:

```shell
export KUBECONFIG=<path printed by the create command>
kubectl cluster-info
```

### Resource Check

The create commands first run `itbench check resources localhost` to compare the machine's CPUs and memory with the cluster's requirements. A shortfall is reported as a warning and does not stop the cluster from being created. The check can also be run on its own:

```shell
uv run itbench check resources localhost
uv run itbench check resources localhost --only environment
```

### Orchestrator Cluster

#### Creation

1. Run the following command from the root of the repository to create a Minikube cluster:
```shell
mise -E minikube run create:minikube:orchestrator
```

2. Open a new terminal window and run the following command to start the Minikube tunnel
```shell
mise -E minikube run run:minikube:tunnel
```

#### Deletion

1. In the terminal window running the Minikube tunnel, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Minikube cluster
```shell
mise -E minikube run destroy:minikube:orchestrator
```

### Environment Cluster

#### Creation

1. Run the following command from the root of the repository to create a Minikube cluster:
```shell
mise -E minikube run create:minikube:environment
```

2. Open a new terminal window and run the following command to start the Minikube tunnel
```shell
mise -E minikube run run:minikube:tunnel
```

#### Deletion

1. In the terminal window running the Minikube tunnel, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Minikube cluster
```shell
mise -E minikube run destroy:minikube:environment
```

## Testing

The Minikube integration tests live in [`tests/integration/minikube`](../../tests/integration/minikube). They need the following:

- A running cluster, with `KUBECONFIG` exported.
- Minikube tunnel running in another terminal (`test_load_balancers.py`).

Run them with:

```shell
mise -E minikube run test:integration:minikube
```

## Troubleshooting

This section will mainly highlight key issues that one may encounter when running Minikube. Minikube already has an [FAQ](https://minikube.sigs.k8s.io/docs/handbook/troubleshooting/) which contains many more cases.

### RHEL

#### "CrashLoopBackOff" in Chaos-Controller Manager Pods

**Problem:**  The `chaos-controller-manager` pods may enter a `CrashLoopBackOff` state due to the error:
```
"too many files open"
```

**Solution:** Please ensure that you have following the instructions during the RHEL set up highlighted [here](#installation).
