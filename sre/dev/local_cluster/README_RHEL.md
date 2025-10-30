# Local Cluster Setup on Red Hat Enterprise Linux (RHEL) Virtual Machine (VM) / Bare-metal instance

The tested configuration uses 16 CPU cores and 16 GB of RAM.

__Note: The following setup guide has been verified and tested on Red Hat Enterprise Linux (RHEL) using the perscribed details. Other components, such as Podman or Minikube on RHEL, can be utilized instead of the recommended software, but is unsupported.__

_Note: The following setup guide presumes that the required software listed [here](./README.md#required-software) has been installed. If it has not, please go back and do so before following this document._

_Note: Please review the [hardware requirements](../../docs/hardware_specification.md) to ensure that the machine matches or exceeds the specifications._

## Recommended Software

1. [make] -- Ensure you have `make` installed or install it via `sudo dnf install make`
2. [lsof] -- Ensure you have `lsof` installed or install it via `sudo dnf install lsof`
3. [Golang - v1.24 and above] -- Ensure you have `go` installed or install it by following the instructions [here](https://go.dev/doc/install)
4. [Docker](https://www.docker.com/) -- See the next sub-section for installation details
5. [Kind](https://kind.sigs.k8s.io/) -- See the next sub-section for installation details

### Setting up the Recommended Software
1. To set up Docker, please follow the instructions [here](https://docs.docker.com/engine/install/rhel/).

2. Complete the post-installation steps for Docker posted [here](https://docs.docker.com/engine/install/linux-postinstall/) if applicable for your environment. Examples of such would be when you run Docker as a non-root user, or to configure Docker to start on boot.

3. Set up `Kind` by following the instructions [here](https://kind.sigs.k8s.io/docs/user/quick-start/#installing-from-release-binaries)

4. To avoid seeing `Pod errors due to “too many open files"` error in the future, edit the file /etc/sysctl.conf and add the following lines:
```
fs.inotify.max_user_watches = 524288
fs.inotify.max_user_instances = 512
```

5. To avoid seeing `vm.max_map_count` error in the future, edit the file /etc/sysctl.conf and add the following lines:
```
vm.max_map_count = 262144
```

6. To apply the change made in the previous step, run
```bash
sudo sysctl -p
```

7. A pre-requisite for Chaos-Mesh-based fault mechanisms is to ensure ebtable-related modules are loaded. Add/edit the file (/etc/modules-load.d/ebtables.conf) and add the following lines:
```bash
ebtable_broute
ebtable_nat
```
The modules will be loaded automatically at the next boot. Until the next boot, run:
```bash
sudo modprobe ebtable_broute
sudo modprobe ebtable_nat
```

## Setup

1. Create a kind cluster. A barebone kind configuration file has been provided [here](./kind-config.yaml).
```shell
make create_single_node_cluster
```
_Note: To delete the cluster, run this command: `make destory_cluster`_

2. Update the `kubeconfig` value in the `../../group_vars/environment/cluster.yaml`, with the absolute path to the kubeconfig (located at `$HOME/.kube/config` e.g. /home/rhel/.kube/config).
```shell
vim ../../group_vars/environment/cluster.yaml
```

```yaml
cluster:
  kubeconfig: "<path to kubeconfig>"
```

3. The cluster has been set up. Now let's head back to the [parent README](../../README.md#running-incident-scenarios---quick-start) to deploy the incidents.

# Troubleshooting
### 1. For other Kind-related issues you may want to take a look [here](https://kind.sigs.k8s.io/docs/user/known-issues/).

### 2. "CrashLoopBackOff" in Chaos-Controller Manager Pods on Red Hat Enterprise Linux (RHEL) 9.5**

**Problem:**  While testing on RHEL OS, the `chaos-controller-manager` pods in kind cluster may enter a `CrashLoopBackOff` state due to the error:
```
"too many files open"
```

This is related to inotify resource limits, which can be exhausted in kind clusters, especially when there are many files being watched. This can impact the RHEL-based deployment of chaos mesh related scenarios.

**Solution:**
Fix for this problem is given in [kind - Known Issues - Pod Errors Due to Too Many Open Files](https://kind.sigs.k8s.io/docs/user/known-issues/#pod-errors-due-to-too-many-open-files).
