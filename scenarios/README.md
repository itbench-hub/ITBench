# ITBench-Scenarios

This repository contains infrastructure automation scripts for both deploying the environments and configuring the scenarios required to run ITBench.
These scenarios are realistic simulations based on actual IT automation challenges faced by CISO, SRE, and FinOps teams.
For example, one of the SRE scenarios is to resolve a “high error rate on service checkout” while a CISO scenario involves assessing the compliance posture for a “new control rule detected for RHEL 9.”
Every ITBench scenario is deployed in a sandboxed operational Kubernetes (K8s) environment.

## [CISO Scenarios](./ciso)
These scenarios simulate compliance-related misconfigurations. Each scenario provides:
- A pre-configured environment with specific compliance issues
- Tools to detect misconfigurations
- Validation methods to verify successful remediation

CISO scenarios are located [here](./ciso).

### Agent Access for CISO Scenarios

CISO scenarios grant the LLM agent restricted, scoped access to the environment rather than full admin credentials. The method depends on whether the scenario targets a Kubernetes cluster or a RHEL9 virtual machine.

#### Kubernetes-based scenarios (64, 65, 67)

These scenarios inject faults into the `benchmarks` namespace. Run the command below to create a scoped ServiceAccount, namespace-level RBAC, and a short-lived token, then publish a restricted kubeconfig to the configured storage location:

```bash
make enable-agent-access SCENARIO_NUMBER=<64|65|67>
```

The agent receives the restricted kubeconfig via `make generate-agent-bundle`. The bundle reads the kubeconfig from storage — never from the admin kubeconfig.

To revoke access after the scenario:

```bash
make disable-agent-access
```

#### Virtual machine scenario (66)

Scenario 66 has no Kubernetes fault injection. The agent instead needs SSH access to the RHEL9 machine. Run:

```bash
make enable-virtual-machine-access
```

This provisions a dedicated user on the VM, generates an SSH keypair, and writes an Ansible inventory file to local storage for the agent to consume.

To revoke access after the scenario:

```bash
make disable-virtual-machine-access
```

## [SRE Scenarios](./sre)
These scenarios focus on observability and incident response. Each scenario includes:
- A comprehensive observability stack deployment featuring:
  - Prometheus for metrics collection
  - Clickhouse and OpenSearch for search and analytics
  - Jaeger for distributed tracing
  - OpenTelemetry for Kubernetes event logs collection
- Simulated faults that trigger service degradation
- Thereby leading to alerts associated with application performance issues such as increased error rates and latency spikes

SRE scenarios are located [here](./sre).

## [FinOps Scenarios](./sre)
Each scenario includes:
- The core SRE observability stack
- OpenCost integration for cost monitoring
- Simulated faults trigger cost overrun alerts

FinOps scenarios are located [here](./sre) along-side SRE scenarios.

## ITBench Ecosystem and Related Repositories

- [CISO-CAA Agent](https://github.com/ITBench-Hub/ITBench-CISO-CAA-Agent): CISO (Chief Information Security Officer) agents that automate compliance assessments by generating policies from natural language, collecting evidence, integrating with GitOps workflows, and deploying policies for assessment.
- [SRE Agent](https://github.com/ITBench-Hub/ITBench-SRE-Agent): SRE (Site Reliability Engineering) agents designed to diagnose and remediate problems in Kubernetes-based environments. Leverage logs, metrics, traces, and Kubernetes states/events from the IT enviroment.
- [ITBench Utilities](https://github.com/ITBench-Hub/ITBench-Utilities): Collection of supporting tools and utilities for participants in the ITBench ecosystem and leaderboard challenges.
- [ITBench Tutorials](https://github.com/ITBench-Hub/ITBench-Tutorials): Repository containing the latest tutorials, workshops, and educational content for getting started with ITBench.

## Maintainers
- Gerard R. Vanloo - [@Red-GV](https://github.com/Red-GV)
- Takumi Yanagawa  - [@yana1205](https://github.com/yana1205)
- Bekir O. Turkkan - [@oguzhan78](https://github.com/oguzhan78)
- Yuji Watanabe    - [@yuji-watanabe-jp](https://github.com/yuji-watanabe-jp)
- Rohan R. Arora   - [@rohanarora](https://github.com/rohanarora)
