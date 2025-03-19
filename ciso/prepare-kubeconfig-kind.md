# How to use KinD cluster for scenario environment

When using a KinD cluster for the scenario environment, some additional configurations are required.

## Key Points
- By default, a KinD cluster's kubeconfig file uses `127.0.0.1` as its API endpoint.
- This address is not accessible from the scenario container.
- You need to edit the kubeconfig file by the following steps to allow the container to access your KinD cluster.

## Steps

### 1. Obtain a Kubeconfig File

First, retrieve the kubeconfig file for your KinD cluster using the following command:

```bash
$ kind get kubeconfig --name <CLUSTER_NAME> > ./kubeconfig.yaml
```

Replace <CLUSTER_NAME> with the actual name of your cluster. You can find the correct name by running:
 
```bash
$ kind get clusters
```

### 2. Edit the Kubeconfig file

```
$ vim ./kubeconfig.yaml
```

The kubeconfig file should look like this:

```yaml
apiVersion: v1
clusters:
- cluster:
    certificate-authority-data: LS0t ... LS0K
    server: https://127.0.0.1:<PORT_NUMBER>
  name: kind-<CLUSTER_NAME>
...
```

Modify the following:

1. Replace `127.0.0.1` with `host.docker.internal`. This address is accessible from the scenario container.
1. Remove the line containing `certificate-authority-data`:.
1. Add `insecure-skip-tls-verify: true` instead.

The final version of your kubeconfig file should look like this:


```yaml
apiVersion: v1
clusters:
- cluster:
    server: https://host.docker.internal:<PORT_NUMBER>
    insecure-skip-tls-verify: true
  name: kind-<CLUSTER_NAME>
...
```

Ensure that you retain the original values for `<PORT_NUMBER>` and `<CLUSTER_NAME>`.

Now, you are ready to use your KinD cluster!
Place this kubeconfig file in your workding directory.
