# Local Cluster Setup

__Note: The following setup guide has been verified and tested on MacOS using the perscribed details. Other components, such as Docker or Minikube, can be utilized instead of the recommended software, but is unsupported.__

_Note: The following setup guide presumes that the required software listed [here](./README.md#required-software) has been installed. If it has not, please go back and do so before following this document._

## Recommended Software

1. [Podman](https://podman.io/)
2. [Golang - v1.24 and above](https://go.dev/)
2. [Kind](https://kind.sigs.k8s.io/)
3. [Cloud Provider Kind](https://github.com/kubernetes-sigs/cloud-provider-kind)

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

2. Set the machine's resources. The tested configuration uses 12 CPU cores and 16 GB of RAM.
```shell
podman machine set --cpus 12 -m 16384
```

3. Start the Machine
```shell
podman machine start
```

4. Create a kind cluster. A barebone kind configuration file has been provided [here](./kind-config.yaml).
```shell
make create_cluster
```

_Note: To delete the cluster, run this command: `make delete_cluster`_

5. Once the cluster is running, we need to run the `cloud-provider-kind` in a *second* terminal and keep it running.
```shell
make start_provider
```

6. Update the value of the `kubeconfig` key in the `../group_vars/all.yaml`, with the absolute path to the kubeconfig (located at `$HOME/.kube/config`).
```shell
vim ../group_vars/all.yaml
```

```yaml
kubeconfig: "<path to kubeconfig>"
```

7. Run the following command to create a new StorageClass named "default" using the local-path provisioner from Rancher (aimed to mimic the standard storage class from Kind).
```shell
kubectl apply -f rancher-storageclass.yaml
```

8. The cluster has been set up. Now let's head back to the [parent README](../README.md) to deploy the incidents.
