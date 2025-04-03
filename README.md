# ITBench

**[📄 Paper](./it_bench_arxiv.pdf) | [🚀 Getting started](#getting-started) | [📦 Scenarios](#scenarios) | [🤖 Agents](#agents) | [📚 Cite](#how-to-cite) | [🧑‍💻 Contribute](#contribute) | [📬 Contacts](#contacts)**

---

## 📢 Announcements

### Updates
- **[February 28, 2025]** Limited access beta 🏆  
  Invite-only access to hosted ITBench scenario environments. ITBench handles scenario deployment, agent evaluation, and leaderboard updates. To request access, email us at [agent-bench-automation@ibm.com](mailto:agent-bench-automation@ibm.com).
  
- **[February 7, 2025]** Initial release 🎉  
  Includes the research paper, self-hosted environment setup tooling, sample scenarios, and baseline agents.

### Coming soon
- **[April 2025]** Public launch 🚀  
  Complete ITBench platform access opens to all.

As of February 2025, we are open-sourcing:

- Push-button deployment tooling for environment setup  
- A scenario framework for:
  - 6 SRE scenarios
  - 1 FinOps scenario
  - 4 categories of CISO scenarios  
- Two reference agents:
  - CISO (Chief Information Security Officer) agent
  - SRE (Site Reliability Engineering) agent

---

## Overview

**ITBench** measures the performance of AI agents across a wide variety of complex, real-world IT automation tasks. These tasks span three key IT personas:

- **Site Reliability Engineering (SRE):** Focused on availability and resiliency  
- **Financial Operations (FinOps):** Focused on cost-efficiency and optimizing ROI  
- **Compliance and Security Operations (CISO):** Focused on security and compliance posture

![Sample IT tasks](./images/sample_it_tasks.png)

Through push-button workflows and interpretable metrics, ITBench helps AI researchers and developers explore both the challenges and potential of IT automation.

ITBench is built on two core principles:

1. **Realistic environments** that emulate actual IT infrastructure and incidents  
2. **Open, extensible framework** with comprehensive IT coverage

---

## Getting started

- **Explore scenarios**: Check out [ITBench-Scenarios](https://github.com/IBM/ITBench-Scenarios) for setup and available [scenarios](#scenarios).
- **Choose an agent**: Try the [SRE agent](https://github.com/IBM/ITBench-SRE-Agent) or the [CISO agent](https://github.com/IBM/ITBench-CISO-CAA-Agent).  
- **Run and evaluate**: Deploy a scenario, let the agent attempt to solve it, and compare results on the [leaderboard](https://github.com/IBM/ITBench-Leaderboard).  

### Agent onboarding

To onboard your agent and begin benchmarking, follow these steps:

#### 1. Create a private GitHub repository

You may create an empty repository or use an existing one. Note:

- The repository **must be set to private**.
- ITBench automation will create a file named `agent_manifest.json` at the **root** of the repository.  
  Make sure this won’t conflict with existing files if you're using an existing project.

#### 2. Install the ITBench GitHub App

Install the [`ibm-itbench`](https://github.com/apps/ibm-itbench) GitHub App into the repository you created in step 1.

#### 3. Submit an onboarding request

Fill out and submit [this onboarding issue template](https://github.com/jpwsutton/itbenchautomation/issues/new?template=onboarding.yaml) with:

- Agent details
- The URL of your GitHub repository (e.g. `https://github.com/your-org/your-agent-repo`)

#### 4. Receive your agent manifest

Once your request is approved, the onboarding workflow will generate an `agent_manifest.json` file and commit it to your repository.

You can now download this manifest and use it with the agent harness to initiate a benchmark run.

## Scenarios

ITBench scenarios simulate realistic IT problems in live environments. For example:

- **SRE:** Resolve a "high error rate on service `order-management`" in a Kubernetes cluster  
- **CISO:** Assess the compliance posture for a "new control rule detected for RHEL 9"

Scenarios are deployed in operational environments where issues can be injected and remediated.

👉 Explore the scenarios in the [ITBench-Scenarios repo](https://github.com/IBM/ITBench-Scenarios)

---

## Agents

ITBench includes two open-source baseline agents:

- **SRE-FinOps agent**
- **CISO compliance agent**

Agents are built using the open-source [CrewAI](https://github.com/joaomdmoura/crewAI) framework and can be configured to run with LLMs via [Watsonx](https://www.ibm.com/watsonx), Azure OpenAI, or [vLLM](https://github.com/vllm-project/vllm).

Each agent is initialized with a prompt that defines:

- The goal of the task  
- Context and environment information  
- Expected output format  

In-context examples are used to guide reasoning and tool usage. Agents use natural language to interact with available tools and the environment for information gathering and remediation.

### CISO compliance agent (CAA)
- Source code: [github.com/IBM/itbench-ciso-caa-agent](https://github.com/IBM/itbench-ciso-caa-agent)

### SRE agent
- Source code: [github.com/IBM/itbench-sre-agent](https://github.com/IBM/itbench-sre-agent)

---

## Contribute

We welcome contributions!

- **Fork and branch**: Create a feature branch from your fork, then open a pull request.  
- **Document changes**: Update relevant READMEs or docs. 
- **License compliance**: By submitting changes, you agree to license them under Apache 2.0.

For big features or ideas, open an issue first to discuss approaches. Thank you for helping improve ITBench!

### Contributors

- Saurabh Jha
- Rohan Arora
- Yuji Watanabe
- Takumi Yanagawa
- Yinfang Chen (UIUC - University of Illinois at Urbana-Champaign)
- Jackson Clark (UIUC - University of Illinois at Urbana-Champaign)
- Bhavya Bhavya
- Mudit Verma
- Harshit Kumar
- Hirokuni Kitahara
- Noah Zheutlin
- Saki Takano
- Divya Pathak
- Felix George
- Xinbo Wu (UIUC - University of Illinois at Urbana-Champaign)
- Bekir O Turkkan
- Gerard Vanloo
- Michael Nidd
- Ting Dai
- Oishik Chatterjee
- Pranjal Gupta
- Suranjana Samanta
- Pooja Aggarwal
- Rong Lee
- Pavankumar Murali
- Jae-wook Ahn
- Debanjana Kar
- Ameet Rahane
- Carlos Fonseca
- Amit Paradkar
- Yu Deng
- Pratibha Moogi
- Prateeti Mohapatra
- Naoki Abe
- Chandrasekhar Narayanaswami
- Tianyin Xu (UIUC - University of Illinois at Urbana-Champaign)
- Lav R. Varshney (UIUC - University of Illinois at Urbana-Champaign)
- Ruchi Mahindru
- Anca Sailer
- Laura Shwartz
- Daby Sow
- Nicholas C. M. Fuller
- Ruchir Puri

---

## How to cite

```bibtex
@misc{jha2025itbench,
      title={ITBench: Evaluating AI Agents across Diverse Real-World IT Automation Tasks},
      author={Jha, Saurabh and Arora, Rohan and Watanabe, Yuji and others},
      year={2025},
      url={https://github.com/IBM/itbench-sample-scenarios/blob/main/it_bench_arxiv.pdf}
}
```
---

## Contacts

- agent-bench-automation@ibm.com
- Saurabh Jha (saurabh.jha@ibm.com)
- Yuji Wantabe (muew@jp.ibm.com)
- Ruchi Mahindru (rmahindr@us.ibm.com)
- Anca Sailer (ancas@us.ibm.com)

