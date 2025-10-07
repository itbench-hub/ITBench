# Remote Cluster Setup

__Note: The following setup guide has been verified and tested on MacOS, Ubuntu, and Fedora using the perscribed details.__

_Note: The following guide has been largely based on this [blog](https://aws.amazon.com/blogs/compute/kubernetes-clusters-aws-kops/)._

_Note: The following setup guide presumes that the required software listed [here](../../README.md#required-software) has been installed along with [creating the virtual environment and installing the dependencies](../../README.md#installing-dependencies). If it has not, please go back and do so before following this document._

## Recommended Software

### MacOS

- [Homebrew](https://brew.sh/)

## Required Software

- [awscli](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html) (v2)
- [kOps](https://kops.sigs.k8s.io/getting_started/install/)

### Installing Required Software via Homebrew (for MacOS)

1. Install required software
```bash
brew install awscli
brew install kops
```

### Installing Required Software (for Red Hat Enterprise Linux -- RHEL)

1. Install the AWS CLI v2, curl, and jq by running:
```bash
sudo dnf install awscli
sudo dnf install curl
sudo dnf install jq
```
2. Set up kops by following the instructions [here](https://kops.sigs.k8s.io/getting_started/install/#linux)


## First Time Setup

1. Install Python dependencies. (Working directory is `remote_cluster`.)
```bash
python -m pip install -r ../../requirements-dev.txt
```

2. Create the group variables for the development host. The `kops_cluster.yaml` file contains the configuration needed to customize the kops deployment.
```bash
make group_vars
```

3. The following variables are to be set in `group_vars/development/kops_cluster.yaml`
```
cluster:
  s3:
    bucket_name: "" # Bucket to which kOps will post cluster configurations in; bucket will be created if it does not exist
  ssh:
    public_key_path: "" # Public SSH key to be placed on the cluster nodes allowing for the nodes to be SSHed into; must be set if clusters are to be created.
```
A guide to creating SSH keys can be found [here](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent).

4. Set up AWS credentials by running the following command. Enter the AWS access key ID and security access key when requested.
```bash
aws configure
```

To create a single cluster head to the next section [here](#cluster-management---single-cluster). If you are here to create multiple identical clusters to orchestrate a large-scale AWX experiment head [here](#cluster-management---multiple-cluster)

## Cluster Management - Single Cluster

### 1. Create the Cluster
Create a new Kubernetes cluster using EC2 resources. Skip this step if you already have a cluster running.

The cluster configuration is defined in `group_vars/development/kops_cluster.yaml`.

```bash
make create_kops_cluster
```

### 2. Export Kubeconfig
Export the cluster's kubeconfig to access the remote Kubernetes cluster:

```bash
make export_kops_kubeconfig
```

To export a cluster other than the one defined in `group_vars/development/kops_cluster.yaml`, get the full name of the cluster by running the following command:

```bash
make list_kops_clusters
```

Then, run the following command with the CLUSTER_NAME argument:

```bash
CLUSTER_NAME=<full name of cluster> make export_kops_kubeconfig
```

### 3. Verify Cluster Access
Test your connection to the cluster:

```bash
export KUBECONFIG=/tmp/<cluster_name>.yaml
kubectl get pods --all-namespaces
```

**Example:**
```bash
export KUBECONFIG="/tmp/development-m5.xlarge-aws.k8s.local.yaml"
kubectl get pods --all-namespaces
```

### 4. Update Global Configuration
Update the `kubeconfig` path in your global configuration:

```bash
vim ../../group_vars/environment/cluster.yaml
```

Set the absolute path where the kubeconfig should be downloaded:
```yaml
kubeconfig: "/absolute/path/to/kubeconfig.yaml"
```

**Example:**
```yaml
kubeconfig: "/tmp/development-m5-xlarge-aws.k8s.local.yaml"
```

### 5. The cluster has been set up. Now let's head back to the [parent README](../../README.md#running-incident-scenarios---quick-start) to deploy the incidents.

### Delete the Cluster
To delete the cluster, run the following command:

```bash
make destroy_kops_cluster
```

To delete a cluster other than the one defined in `group_vars/development/kops_cluster.yaml`, get the full name of the cluster by running the following command:

```bash
make list_kops_clusters
```

Then, run the following command with the CLUSTER_NAME argument:

```bash
CLUSTER_NAME=<full name of cluster> make destroy_kops_cluster
```

## Cluster Management - Multiple Clusters

Continuing from the first-time setup (#first-time-setup) section this is primarily intended for AWX-based runs spanning the run of multiple scenarios in parallel.

In addition to the variables set in the first time setup section, thhe following variables are to be set in `group_vars/development/awx_stack.yaml`
```
stack:
  name_prefix: awx-exp-runner # an identifier name for the set of kOps cluster(s) which are to be orchestrated as a part of the experiment
  runners:
    aws:
      vpc:
        cidr: "10.0.0.0/16"
      subnet:
        public_base: "10.0"
    count: 20 # number of scenarios which are going to be run.
```

### 1. Create the clusters

Let's say the count value in the above set was set to 20. This creation step leads to the creation of 21 clustes. One Kubernetes cluster referred to as the `head` cluster to which AWX would be installed to and then a cluster per scenario.

```bash
make create_awx_stack
```

### 2. Export the Kubeconfigs

Exports the kubeconfig associated with the clusters orchestrated for the AWX run.

### 3. Delete the clusters

```bash
make destroy_awx_stack
```
