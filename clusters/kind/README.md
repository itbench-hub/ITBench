# Kind Cluster Setup

[Kind](https://kind.sigs.k8s.io/) is tool which uses [Docker](https://www.docker.com/) containers to create a [Kubernetes](https://kubernetes.io/) cluster on a local machine.

[Cloud Provider Kind](https://github.com/kubernetes-sigs/cloud-provider-kind) is tool which creates containers to allocate an IP addresses for the [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/) that require [Load Balancers](https://kubernetes.io/docs/concepts/services-networking/service/#loadbalancer). The addresses can be used to reach tools running on the cluster from an Internet browser.

## Required Software

- [mise](https://mise.jdx.dev/)
- [Podman](https://podman.io/) or [Docker](https://www.docker.com/)

>[!NOTE]
>Generally, there are minimal differences between using Podman or Docker for Kind. For simplicity, only instructions for Podman have been provided. However, if one wants to use Docker, the instructions for downloading it are provided [here](https://docs.docker.com/get-started/get-docker/).

>[!IMPORTANT]
>If using a Kind cluster for SRE scenarios, please ensure that the machine has the necessary [hardware requirements](../../documentation/getting-started/awx.md#requirements).

## Installation

>[!NOTE]
>Kind and Cloud Provider Kind are installed and managed by mise. Run the following command from the root of the repository to install them. Neither tool needs to be installed independently of this process.
>```shell
>mise -E kind install
>```
>
>The `kind` environment can be made the default for a shell session with `export MISE_ENV=kind`, which allows the `-E kind` flag to be omitted from the commands below.

### MacOS ([Homebrew](https://brew.sh/))

>[!IMPORTANT]
>Previous versions of ITBench used an older version of Cloud Provider Kind to provide IP addresses on MacOS. Since upgrading to v0.11+ of this tool, this functionality is no longer possible as ITBench can use multiple gateways that ask for the same port (ie, Book Info). Thus, [**Minikube**](../minikube/README.md) is the now recommended development environment for MacOS. However, scenarios involving applications which do not creating additional gateways (ie, OpenTelemetry Demo) can still function as is on MacOS with the following information.

1. Download the following packages
```shell
brew install mise
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

- [environment](./configs/environment.yaml)
- [orchestrator](./configs/orchestrator.yaml)

The `environment` configuration is for basic use cases, such as developing new faults or scenarios or running a single benchmark trial. This cluster will suffice for most needs. For management instructions for a Kind cluster based on the `environment` configuration, please see [here](#environment-cluster).

The `orchestrator` configuration is for advanced use cases which require orchestration to run multi-trial benchmarks across a cluster or clusters. This requires a machine with significantly more resources than the `environment` configuration. For management instructions for a Kind cluster based on the `orchestrator` configuration, please see [here](#orchestrator-cluster).

Each cluster's kubeconfig is written to the `kubeconfigs` directory (ie, `clusters/kind/kubeconfigs/kind-environment`) instead of `~/.kube/config`. The create commands print the `export KUBECONFIG=...` line to run so that kubectl and the `itbench` CLI use the cluster:

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

1. Run the following command from the root of the repository to create a Kind cluster:
```shell
mise -E kind run create:kind:orchestrator
```

2. Open a new terminal window and run the following command to start the Cloud Provider Kind
```shell
mise -E kind run run:kind:provider
```

#### Deletion

1. In the terminal window running the Cloud Provider Kind, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Kind cluster
```shell
mise -E kind run destroy:kind:orchestrator
```

### Environment Cluster

#### Creation

1. Run the following command from the root of the repository to create a Kind cluster:
```shell
mise -E kind run create:kind:environment
```

2. Open a new terminal window and run the following command to start the Cloud Provider Kind
```shell
mise -E kind run run:kind:provider
```

#### Deletion

1. In the terminal window running the Cloud Provider Kind, press `Ctrl` and `C` keys on your keyboard.

2. Run the following command to destroy a Kind cluster
```shell
mise -E kind run destroy:kind:environment
```

## Testing

The Kind integration tests live in [`tests/integration/kind`](../../tests/integration/kind). They need the following:

- A running cluster, with `KUBECONFIG` exported.
- Cloud Provider Kind running in another terminal (`test_load_balancers.py`).
- The tools stack deployed with `uv run itbench deploy environment --only tools` (`test_agent_access.py`).

Run them with:

```shell
uv run --group dev pytest --integration -m integration -v tests/integration/kind
```

## Troubleshooting

This section will mainly highlight key issues that one may encounter when running Kind. Kind already has an [FAQ](https://kind.sigs.k8s.io/docs/user/known-issues/) which contains many more cases.

### MacOS

#### Load Balancer IP Address is unreacheable

**Problem**: The IP address assigned to a Kubernetes service is not reachable via `curl` or the browser.

**Solution**: The cause of this is explained in further detail [here](https://github.com/kubernetes-sigs/cloud-provider-kind?tab=readme-ov-file#enabling-load-balancer-port-mapping). On MacOS the host port mapped to the container operating as the provider must be used, so that the service can be reached via `localhost`.

### RHEL

#### "CrashLoopBackOff" in Chaos-Controller Manager Pods

**Problem:**  The `chaos-controller-manager` pods may enter a `CrashLoopBackOff` state due to the error:
```
"too many files open"
```

**Solution:** Please refer to this [link](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).
