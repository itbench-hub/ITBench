# Local Cluster Setup

__Note: The following setup guide has been verified and tested on MacOS using the perscribed details. Other components, such as Docker or Minikube, can be utilized instead of the recommended software, but is unsupported.__

_Note: The following setup guide presumes that the required software listed [here](./README.md#required-software) has been installed. If it has not, please go back and do so before following this document._

## Recommended Software

1. [Podman](https://podman.io/)
2. [Kind](https://kind.sigs.k8s.io/)
3. [Cloud Provider Kind](https://github.com/kubernetes-sigs/cloud-provider-kind)

### Installing Recommended Software via Homebrew (MacOS)

```bash
brew install podman
brew install kind
brew install cloud-provider-kind
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
kind create cluster --config kind-config.yaml
```

_Note: To delete the cluster, run this command: `kind delete cluster --name kind-cluster`_

The kubeconfig will be placed at `$HOME/.kube/config`

5. Open a second terminal window and run the cloud provider.
```shell
sudo cloud-provider-kind -enable-lb-port-mapping
```

6. The cluster has been set up. Now let's head back to the [parent README](../README.md) to deploy the incidents.

# Troubleshooting
### 1. Running kind cluster on Red Hat Enterprise Linux (RHEL) 9.5 with Podman:**

During our test, we found that running kind with rootless provider on RHEL with podman will require some special setup which cannot be covered here.
We used **sudo** privilege to create a kind cluster and ran the test successfully.
Please see [instructions](https://kubernetes.io/docs/tasks/tools/install-kubectl-linux/) for the installation and setup kubectl on Linux if you don't have one installed.

`$ sudo kind create cluster --config kind-config.yaml`

Once the kind cluster is up and running, please run the following commands before using kubectl:
```
$ sudo cp /root/.kube/config /tmp
$ sudo chmod 644 /tmp/config
$ export KUBECONFIG=/tmp/config
```
```
$ kubectl get nodes
NAME                         STATUS   ROLES           AGE    VERSION
kind-cluster-control-plane   Ready    control-plane   7d1h   v1.30.0
```
### 2. "CrashLoopBackOff" in Chaos-Controller Manager Pods on Red Hat Enterprise Linux (RHEL) 9.5**

**Problem:**  While testing on RHEL OS, the `chaos-controller-manager` pods in kind cluster may enter a `CrashLoopBackOff` state due to the error:  
```
"too many files open"
```

This is related to inotify resource limits, which can be exhausted in kind clusters, especially when there are many files being watched. This can impact the RHEL-based deployment of chaos mesh related scenarios. 

**Solution:** 
Fix for this problem is given in [kind - Known Issues - Pod Errors Due to Too Many Open Files](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files). 

**Note:**
This issue has been observed specifically on RHEL OS while working within the chaos-mesh namespace. No such issue has been observed during testing on macOS.
