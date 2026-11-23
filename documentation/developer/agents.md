# Giving AI Agents Access to an ITBench Environment

The [`agents`](../../project/roles/agents) role holds everything that exists only for the AI agents: their cluster access, the MCP servers they query, and the containment that limits what they can change. This document describes the access model, the MCP endpoints, the bundle that hands both to an agent runner, and the end-of-run procedure.

>[!NOTE]
>The role is part of `itbench deploy environment` (the `agents` step) and `itbench undeploy environment`. It only runs when the environment is deployed with agent management enabled.

## Agents

Which agents exist is chosen with two role variables. They can be set in a scenario's `extra_variables.yaml` (keys starting with `agents_` are forwarded by `deploy environment --scenario`).

| Variable | Default | Effect |
| --- | --- | --- |
| `agents_diagnosis_enabled` | `true` | Creates the read-only `agent-diagnosis` ServiceAccount. |
| `agents_remediation_enabled` | `false` | Creates the `agent-remediation` ServiceAccount and turns on the containment layer below. |

Both ServiceAccounts live in the `itbench-agents` namespace, carry the `itbench.io/agent-mission` label (the CLI finds them by it), and never mount a token automatically.

## Access model

- **Diagnosis** is read-only. Its ClusterRole is bound only by RoleBindings in the namespaces labelled `itbench.io/inject=true`, so every namespaced read is limited to those namespaces. It cannot read Secrets, and has no `pods/exec`, `pods/portforward`, `pods/proxy` or `services/proxy`.
- **Remediation** has the same reads plus the writes the faults need, again only in the inject namespaces. `secrets` allows `get`, `patch` and `update`, but not `list` or `watch`. It also has `patch` and `update` on `nodes`, which only exists to uncordon a node (see the node guard below).
- **Both** are bound to the `agent-cluster-read` ClusterRole: `get`, `list` and `watch` on `namespaces`, `nodes`, `persistentvolumes` and `storageclasses`, and `nodes` in `metrics.k8s.io`. Listing namespaces shows the names of the infrastructure namespaces. Reading inside them is forbidden.
- Neither agent has any RBAC in `itbench-mcp-servers`, `itbench-observability` or `itbench-agents`.

### Containment

Policies that only matter if an agent can write install with `agents_remediation_enabled`. All of them match only requests from `system:serviceaccount:itbench-agents:agent-*`.

| Object | Purpose |
| --- | --- |
| `itbench-agent-inject-namespaces-only` (always) | Denies agent writes outside the inject namespaces. Nodes are exempt, they are handled by the node guard. |
| `itbench-agent-node-guard` | A node update is only allowed when it leaves the node schedulable. Labels, annotations and taints must stay unchanged, so the agent can only uncordon. |
| `itbench-agent-network-policy-guard` | Denies creating or updating a NetworkPolicy with egress rules, and changing or deleting one labelled `itbench.io/protected=true`. |
| `itbench-agent-service-guard` | Services must be `ClusterIP` without `externalIPs`. |
| `itbench-agent-images-allowlist` | Container images may only be ones already in the workload or in the ConfigMap `itbench-agent-images` (a snapshot of the images in use in the inject namespaces). Without the ConfigMap, every image change is denied. |
| `itbench-agent-egress` NetworkPolicy | Per inject namespace, egress only to the inject namespaces, DNS in `kube-system` and the OTLP gateway collectors. |
| `itbench-agent-dns-egress` CiliumNetworkPolicy | Restricts DNS to `*.cluster.local`. Only when the Cilium CRD exists. |

The inject namespaces are also labelled with Pod Security `baseline` (`enforce`, `warn` and `audit`) when the `applications` role creates them. The agents cannot write Namespaces, so they cannot change the labels.

>[!WARNING]
>Egress policies only work when the CNI enforces NetworkPolicy. The kind and Minikube tasks install Cilium for this reason. OpenShift and EKS use their own CNI, and the DNS restriction does not apply there.

## MCP servers

All servers are reached through one HTTPS Gateway, `itbench-mcp` in `itbench-mcp-servers` (port 8443, certificates issued by cert-manager). It is created by the `agents` role. The servers themselves are installed by the `tools` role, and only when what they front exists and `tools_observability_enabled` is set.

| Server | Path | Notes |
| --- | --- | --- |
| Jaeger | `/mcp/jaeger` | A separate `jaeger-mcp` collector in `itbench-observability`, reading ClickHouse as the `agent` user (`SELECT` only). |
| OpenCost | `/mcp/opencost` | Part of the OpenCost Helm release. |
| Prometheus | `/mcp/prometheus` | Helm release in `itbench-mcp-servers` with an explicit list of read-only tools, never `all`. |

Every route requires the header `Authorization: Bearer <token>`. A request without it gets a 404 from the Gateway and never reaches a server. The token is `itbench_kubernetes_gateways.mcp.token`, derived from `random_password_creation_seed`, so it only changes when the seed does.

>[!NOTE]
>Prometheus returns series for every namespace, including the infrastructure ones. This is accepted.

## The bundle

`itbench generate bundle` reads what the `agents` role stored in the Secret `itbench-agent-bundle` (`itbench-mcp-servers`), issues a short-lived kubeconfig for each agent that was deployed, and prints one JSON document:

```json
{
  "mcp_servers": {
    "jaeger": "https://<address>:8443/mcp/jaeger",
    "opencost": null,
    "prometheus": "https://<address>:8443/mcp/prometheus"
  },
  "headers": {"Authorization": "Bearer <token>"},
  "ca_certificate": "-----BEGIN CERTIFICATE-----...",
  "kubeconfigs": {"diagnosis": "<kubeconfig>", "remediation": null}
}
```

A server that was not installed is `null`, and so is the kubeconfig of an agent that was not deployed.

```shell
uv run itbench generate bundle --kubeconfig ~/.kube/config > bundle.json
uv run itbench generate bundle --scenario 5 --duration 30 --output ./agent --kubeconfig ~/.kube/config
```

- The MCP half is written at deploy time. The kubeconfig half is minted when the command runs, because the tokens expire (15 to 60 minutes, `--duration`, or `recorders_benchmark_duration_minutes` of the scenario).
- The bundle holds credentials. With `--output` the file is written readable by the owner only.
- To get a single kubeconfig, use `itbench generate kubeconfig --mission diagnosis|remediation`.
- On macOS the Gateway address is not usable with `cloud-provider-kind`. See [`clusters/kind/README.md`](../../clusters/kind/README.md).

## Kubernetes MCP server

A Kubernetes MCP server is **not** deployed into the cluster. If an agent needs one, run an upstream Kubernetes MCP server (for example [`containers/kubernetes-mcp-server`](https://github.com/containers/kubernetes-mcp-server)) next to the agent, outside the cluster, and point it at the agent's kubeconfig from the bundle. It then has exactly the access of that agent and nothing more. Follow the upstream documentation for the exact commands.

## End of a run

Tokens cannot be revoked, they stop working when they expire. Removing access therefore means removing what they are tied to:

1. Undeploying the applications deletes the inject namespaces, and with them every RoleBinding and NetworkPolicy.
2. The ClusterRoleBindings for `agent-cluster-read` and node uncordoning persist until the agents are removed.
3. Deleting the ServiceAccounts invalidates the tokens issued for them, because bound tokens are tied to the ServiceAccount's UID.

So undeploy the whole environment (`itbench undeploy environment`), not only the applications. `--only applications` leaves the agents in place.

## Verifying access

`kubectl auth can-i` only checks RBAC. To check the admission policies, write as the ServiceAccount with a server-side dry run, and expect a denial:

```shell
kubectl create configmap x -n kube-system --dry-run=server \
  --as system:serviceaccount:itbench-agents:agent-remediation
```

These must answer `no`, for both ServiceAccounts:

```shell
kubectl auth can-i get secrets -n itbench-observability --as system:serviceaccount:itbench-agents:agent-remediation
kubectl auth can-i list secrets -n itbench-mcp-servers --as system:serviceaccount:itbench-agents:agent-remediation
kubectl auth can-i get configmaps -n itbench-mcp-servers --as system:serviceaccount:itbench-agents:agent-remediation
kubectl auth can-i create pods/portforward -n <inject namespace> --as system:serviceaccount:itbench-agents:agent-remediation
```
