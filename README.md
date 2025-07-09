# ITBench

**[Paper](./it_bench_arxiv.pdf) | [Scenarios](#scenarios) | [Agents](#agents) | [How to Cite](#how-to-cite) |  [Contributors](#contributors) | [Contacts](#contacts)**

# 📢 Announcements

## Latest Updates
- **[May 2, 2025]** ITBench now provides fully-managed scenario environments for everyone! Our platform handles the complete workflow — from scenario deployment to agent evaluation and leaderboard updates. Visit our GitHub repository [here](https://github.com/ibm/ITBench-Leaderboard) for guidelines and get started today.
- **[February 28, 2025]** Limited Access Beta 🏆: Invite-only access to the ITBench hosted scenario environments. ITBench handles scenario deployment, agent evaluation, and leaderboard updates. To request access, e-mail us [here](agent-bench-automation@ibm.com).
- **[February 7, 2025]** Initial release! 🎉 Includes research paper, self-hosted environment setup tooling, sample scenarios, and baseline agents.

# Overview
The goal of ITBench is to measure the performance of AI agents across a wide variety of complex and real-life IT automation tasks targetting three key use cases:
- Site Reliability Engineering (SRE) - focusing on availability and resiliency
- Financial Operations (FinOps) - focusing on enforcing cost efficiencies and optimizing return on investment
- Compliance and Security Operations (CISO) - focusing on ensuring compliance and security of IT implementations

![sample_tasks](./images/sample_it_tasks.png)
Through push-button workflows and interpretable metrics, it helps AI researchers and developers explore both the challenges and potential of IT automation.

ITBench centers on two core principles:
1. Real-world representation of IT environments and incident scenarios that happen in such environments
2. Open, extensible framework with comprehensive IT coverage

ITBench enables researchers and developers to replicate real-world incidents in Kubernetes environments (scenarios) and develop AI agents to address them.
As of February 2025, we are open-sourcing:
1. Push-button deployment tooling for environment setup
2. Framework for recreating:
   * 6 SRE scenarios
   * 1 FinOps scenario
   * 4 categories of CISO scenarios
3. Two reference AI agents:
   * CISO (Chief Information Security Officer) Agent
   * SRE (Site Reliability Engineering) Agent

# Leaderboard
The ITBench Leaderboard tracks agent performance across SRE, FinOps, and CISO scenarios. We provide fully-managed scenario environments while researchers run their agents on their own systems and submit their outputs for evaluation.

| Domain | Leaderboard |
|--------|-------------|
| 🔐 **CISO**    | 👉 [View CISO Leaderboard](https://github.com/IBM/ITBench-Leaderboard/blob/main/LEADERBOARD_CISO.md) |
| ⚙️ **SRE**     | 👉 [View SRE Leaderboard](https://github.com/IBM/ITBench-Leaderboard/blob/main/LEADERBOARD_SRE.md) |

To get started with our hosted environments, visit our [leaderboard repository](https://github.com/ibm/ITBench-Leaderboard) for access and evaluation guidelines.

# Scenarios
ITBench incorporates a collection of problems that we call scenarios. For example, one of the SRE scenarios in ITBench is to resolve a “High error rate on service checkout” in a Kubernetes environment. Another scenario that is relevant for the CISO use case involves assessing the compliance posture for a “new control rule detected for RHEL 9.” Each of the ITBench scenarios are deployed in an operational environment in which problem(s) occur.

The scenarios can be found [here](https://github.com/IBM/ITBench-Scenarios).

# Agents
Two baseline agents (SRE-FinOps and CISO) are being open-sourced with the ITBench.
We use the open-source CrewAI framework to create and manage agents.
The agents can be configured to use various LLMs either through watsonx, Azure, or vLLM.
Each agent is initialized with a prompt that describes its goal, the context, the tasks, and the expected output format.
In-context learning examples are included to guide the agent and demonstrate tool usage.
Agents use natural language to access tools to interact with the environment for information gathering.

## CAA Agent
Source code repository [here](https://github.com/IBM/itbench-ciso-caa-agent).

## SRE Agent
Source code repository [here](https://github.com/IBM/itbench-sre-agent).

# How to Cite
```
@misc{jha2025itbench,
      title={ITBench: Evaluating AI Agents across Diverse Real-World IT Automation Tasks},
      author={Jha, Saurabh and Arora, Rohan and Watanabe, Yuji and others},
      year={2025},
      url={https://github.com/IBM/itbench-sample-scenarios/blob/main/it_bench_arxiv.pdf}
}
```

# Join the discussion
Have questions or need help getting started with ITBench?
- [Create a GitHub issue](https://github.com/IBM/ITBench/issues/new) for bug reports or feature requests
- Join our [Discord community](https://discord.gg/6fzy3JRHmt) for real-time discussions
- For formal inquiries, please see the [contacts section](#contacts)

# Contacts
- agent-bench-automation@ibm.com
- Saurabh Jha (saurabh.jha@ibm.com)
- Yuji Wantabe (muew@jp.ibm.com)
