# How to use AWS EKS cluster for scenario environment

When using an AWS EKS cluster for the scenario environment, some additional configurations are required.

## Key Points
- By default, an EKS cluster's kubeconfig file uses `aws` command which requires aws credentials.
- Those credentials are not available in the scenario container.
- You need to get a token by running the command manually and edit the kubeconfig file to use it by the following steps to access your EKS cluster.

## Steps

### 1. Obtain a Kubeconfig File

First, retrieve the kubeconfig file for your EKS cluster using the following command:

```bash
$ aws eks update-kubeconfig --region <AWS_REGION> --name <CLUSTER_NAME>
Added new context arn:aws:eks:(...):cluster/<CLUSTER_NAME> to /Users/<USERNAME>/.kube/config
```

Replace <CLUSTER_NAME> and <AWS_REGION> with the actual values for your cluster. 

Then copy the kubeconfig file to edit.

```bash
$ kubectl config view --minify --raw > ./kubeconfig.yaml
$ cp ~/.kube/config ./kubeconfig.yaml
```

### 2. Run the command to get token

The obtained kubeconfig file should look like this:

```yaml
apiVersion: v1
clusters:
  ...
kind: Config
preferences: {}
users:
- name: arn:aws:eks:(...):cluster/<CLUSTER_NAME>
  user:
    exec:
      apiVersion: client.authentication.k8s.io/v1beta1
      args:
      - --region
      - <AWS_REGION>
      - eks
      - get-token
      - --cluster-name
      - <CLUSTER_NAME>
      - --output
      - json
      command: aws
```

Then, you can manually get token for this cluster by the following command:

```bash
$ aws --region <AWS_REGION> eks get-token --cluster-name <CLUSTER_NAME> --output json
{
    "kind": "ExecCredential",
    "apiVersion": "client.authentication.k8s.io/v1beta1",
    "spec": {},
    "status": {
        "expirationTimestamp": "2025-01-31T09:15:30Z",
        "token": "k8s-aws-v1.a ... Y"
    }
}
```

In the response json, you can find `token` field. This is the token which you will put into the kubeconfig file.

**NOTE**: This token expires in 15 minutes, so if you takes more than 15 minutes during scenario operations, please renew the token.

Modify the following:

1. Remove the `exec` field under `user` in the kubeconfig file.
1. Add a `token` field under `user` instead.
1. Set the token you just obtained to the `token` field.

The final version of your kubeconfig file should look like this:

```bash
$ vim ./kubeconfig.yaml
```

```yaml
apiVersion: v1
clusters:
  ...
kind: Config
preferences: {}
users:
- name: arn:aws:eks:(...):cluster/<CLUSTER_NAME>
  user:
    token: k8s-aws-v1.a ... Y
```

Ensure that you retain the original values for `clusters` and `contexts`. What you need to change is only `user` part.

Now, you are ready to use your AWS EKS cluster!
Place this kubeconfig file in your workding directory.
