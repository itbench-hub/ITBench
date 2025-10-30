# Local Cluster Setup

__Note: The following setup guide has been verified and tested on MacOS using the perscribed details. Other components, such as Docker or Minikube, can be utilized instead of the recommended software, but is unsupported.__

_Note: The following setup guide presumes that the required software listed [here](./README.md#required-software) has been installed. If it has not, please go back and do so before following this document._

_Note: Please review the [hardware requirements](../../docs/hardware_specification.md) to ensure that the machine matches or exceeds the specifications._

## Recommended Software

1. [Podman](https://podman.io/)
2. [Golang - v1.24 and above](https://go.dev/)
2. [Kind](https://kind.sigs.k8s.io/)

### Installing Recommended Software via Homebrew (MacOS)

```bash
brew install podman
brew install go
```

## Setup

1.  Initialize a Podman machine. Using the following command as is will generate a machine called `podman-machine-default`.
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

4. Create a kind cluster. A barebone kind configuration file has been provided [here](./kind-config.yaml).
```shell
make create_single_node_cluster
```

_Note: To delete the cluster, run this command: `make destory_cluster`_

5. Update the value of the `kubeconfig` key in the `../../group_vars/environment/cluster.yaml`, with the absolute path to the kubeconfig (located at `$HOME/.kube/config`).
```shell
vim ../../group_vars/environment/cluster.yaml
```

```yaml
cluster:
  kubeconfig: "<path to kubeconfig>"
```

6. The cluster has been set up. Now let's head back to the [parent README](../../README.md#running-incident-scenarios---quick-start) to deploy the incidents.
