# ITBench-Scenarios

This repository contains infrastructure automation scripts for both deploying the environments and configuring the scenarios required to run [ITBench](https://github.com/IBM/ITBench).
These scenarios are realistic simulations based on actual IT automation challenges faced by CISO, SRE, and FinOps teams.
For example, one of the SRE scenarios is to resolve a “high error rate on service checkout” while a CISO scenario involves assessing the compliance posture for a “new control rule detected for RHEL 9.”
Every ITBench scenario is deployed in a sandboxed operational Kubernetes (K8s) environment.

## [CISO Scenarios](./ciso)
These scenarios simulate compliance-related misconfigurations. Each scenario provides:
- A pre-configured environment with specific compliance issues
- Tools to detect misconfigurations
- Validation methods to verify successful remediation

CISO scenarios are located [here](./ciso).

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

- [ITBench](https://github.com/IBM/ITBench): Central repository providing an overview of the ITBench ecosystem, related announcements, and publications.
- [CISO-CAA Agent](https://github.com/IBM/ITBench-CISO-CAA-Agent): CISO (Chief Information Security Officer) agents that automate compliance assessments by generating policies from natural language, collecting evidence, integrating with GitOps workflows, and deploying policies for assessment.
- [SRE Agent](https://github.com/IBM/ITBench-SRE-Agent): SRE (Site Reliability Engineering) agents designed to diagnose and remediate problems in Kubernetes-based environments. Leverage logs, metrics, traces, and Kubernetes states/events from the IT enviroment.
- [ITBench Leaderboard](https://github.com/IBM/ITBench-Leaderboard): Service that handles scenario deployment, agent evaluation, and maintains a public leaderboard for comparing agent performance on ITOps use cases.
- [ITBench Utilities](https://github.com/IBM/ITBench-Utilities): Collection of supporting tools and utilities for participants in the ITBench ecosystem and leaderboard challenges.
- [ITBench Tutorials](https://github.com/IBM/ITBench-Tutorials): Repository containing the latest tutorials, workshops, and educational content for getting started with ITBench.

## Maintainers
- Gerard R. Vanloo - [@Red-GV](https://github.com/Red-GV)
- Takumi Yanagawa  - [@yana1205](https://github.com/yana1205)
- Bekir O. Turkkan - [@oguzhan78](https://github.com/oguzhan78)
- Yuji Watanabe    - [@yuji-watanabe-jp](https://github.com/yuji-watanabe-jp)
- Rohan R. Arora   - [@rohanarora](https://github.com/rohanarora)
