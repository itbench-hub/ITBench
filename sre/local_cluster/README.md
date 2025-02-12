# Local Cluster Setup

## Pre-requisites
1. [Python3.12](https://www.python.org/downloads/release/python-3120/)
2. [Ansible](https://docs.ansible.com/ansible/latest/installation_guide/intro_installation.html)
3. [Kubectl](https://kubernetes.io/docs/tasks/tools/)
4. [Podman](https://podman.io/) (podman-plugins and podman-machine on Linux)
5. [Helm](https://helm.sh/)
6. [Brew](https://brew.sh/) (Mac)

## Setup

This setup has been tested on MacOS.

Helm version v.3.16 is required: [Installation](https://helm.sh/docs/intro/install/).

### Create an isolated environment 
```bash
python3.12 -m venv venv
source venv/bin/activate
```

#### Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

#### Install Podman
Tested on Podman Desktop. [Installation Instructions can be found here](https://podman.io/docs/installation)

##### Step 1: Initialize Podman Machine

```shell
podman machine init
```
This creates a machine named `podman-machine-default`.

##### Step 2: Tweak Podman machine's resources

```shell
podman machine set --cpus 12 -m 16384
```
The deployment was tested with 12 CPU cores and 16 GB of RAM. 

##### Step 3: Start Podman Machine

```shell
podman machine start
```

#### Install kind
```shell
brew install kind
```

And verify the installation:
```shell
% which kind
/opt/homebrew/bin/kind
% kind version
kind v0.26.0 go1.23.4 darwin/arm64
```

A barebone kind configuration file has been provided [here](./kind-config.yaml).

Let's create a kind cluster using the configuration file by executing:
```shell
$ kind create cluster --config kind-config.yaml
Creating cluster "kind-cluster" ...
 ✓ Ensuring node image (kindest/node:v1.30.0) 🖼
 ✓ Preparing nodes 📦
 ✓ Writing configuration 📜
 ✓ Starting control-plane 🕹️
 ✓ Installing CNI 🔌
 ✓ Installing StorageClass 💾
Set kubectl context to "kind-cluster"
You can now use your cluster with:

kubectl cluster-info --context kind-kind-cluster

Have a question, bug, or feature request? Let us know! https://kind.sigs.k8s.io/#community 🙂
```

Let's verify the status of the clusters with:
```shell
$ kubectl cluster-info --context kind-kind-cluster

Kubernetes control plane is running at https://127.0.0.1:36111
CoreDNS is running at https://127.0.0.1:36111/api/v1/namespaces/kube-system/services/kube-dns:dns/proxy

To further debug and diagnose cluster problems, use 'kubectl cluster-info dump'.
```
```shell
$ kubectl get nodes
NAME                           STATUS   ROLES           AGE     VERSION\
kind-cluster-control-plane   Ready    control-plane   8m22s   v1.30.0
```

####  [Back to the Parent README](../README.md)

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
