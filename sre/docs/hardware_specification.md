# ITBench: Hardware Specification

ITBench executes its scenarios in a live environment ([Kubernetes](https://kubernetes.io/docs/concepts/overview/)). As such, one needs significant resources in order to run the benchmarks.

## Local Development (Kind, Minikube, etc.)

We recommend the following hardware requirements for good performance on a virtual or physical machine. Using a machine that has the below the recommended amount may result in sub-optimal performance or failures within ITBench.

| CPU | Memory | Storage |
| --- | --- | --- |
| 8 | 16 GB | 50 GB |

### Development on AWX

When using AWX locally, one needs significate resources to ensure good performance. This is because a single cluster is responsible for running both AWX and the benchmark at the same time.

Generally, it is not recommended to run AWX locally outside of testing purposes.

| CPU | Memory | Storage |
| --- | --- | --- |
| 24 | 32 GB | 100 GB |

## Remote Development (AWS, Azure, GCP, etc.)

We recommend that the machines used for the cluster's worker nodes adhear to the same requirements as described in the [previous section](#local-development-kind-minikube-etc). For example, on AWS, the [`m5.2xlarge`](https://docs.aws.amazon.com/ec2/latest/instancetypes/gp.html#gp_hardware) is recommended for worker nodes.

There is no hardware requirement for the local machine when using cloud resources to create a Kubernetes cluster.
