# ITBench

**[Paper](./it_bench_arxiv.pdf) | [Scenarios](#scenarios) | [Agents](#agents) | [How to Cite]()| [Contributors](#contributors) | [Contacts](#contacts)**

# 📢 Announcements

## Latest Updates
- **[February 7, 2025]** Initial release 0.1.0! 🎉 Includes research paper, self-hosted environment setup tooling, sample scenarios, and baseline agents

## Coming Soon
- **[March 2025]** Limited Access Beta 🏆
Get invite-only access to the ITBench hosted scenario evnironments and be one of the first participants on our leaderboard. You register your SRE, FinOps, or CISO AI agent and prep it for interacting with the ITBench-hosted scenario environments.  ITBench automatically handles scenario deployment, agent evaluation, and leaderboard updates. To request access, e-mail us [here](agent-bench-automation@ibm.com).

- **[April 2025]** Public Launch 🚀
Complete ITBench platform access opens to all.

## Overview

The goal of ITBench is to measure the performance of AI agents across a wide variety of complex and real-life IT automation tasks targetting three key personas:
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
   * 4 categories of CISO scenarios
3. Two reference AI agents:
   * CISO (Chief Information Security Officer) Agent
   * SRE (Site Reliability Engineering) Agent

## Scenarios
ITBench incorporates a collection of problems that we call scenarios. For example, one of the SRE scenarios in ITBench is to resolve a “High error rate on service order-management” in a Kubernetes environment. Another scenario that is relevant for the CISO persona involves assessing the compliance posture for a “new control rule detected for RHEL 9.” Each of the ITBench scenarios are deployed in an operational environment in which problem(s) occur.

The scenarios can be found [here](https://github.com/IBM/ITBench-Scenarios).

## Agents
Two baseline agents (SRE-FinOps and CISO) are being open-sourced with the ITBench.
We use the open-source CrewAI framework to create and manage agents.
The agents can be configured to use various LLMs either through watsonx, Azure, or vLLM.
Each agent is initialized with a prompt that describes its goal, the context, the tasks, and the expected output format.
In-context learning examples are included to guide the agent and demonstrate tool usage.
Agents use natural language to access tools to interact with the environment for information gathering.

### CAA Agent
Source code repository [here](https://github.com/IBM/itbench-ciso-caa-agent).

### SRE Agent
Source code repository [here](https://github.com/IBM/itbench-sre-agent).

### How to Cite
```
@misc{jha2025itbench,
      title={ITBench: Evaluating AI Agents across Diverse Real-World IT Automation Tasks},
      author={Jha, Saurabh and Arora, Rohan and Watanabe, Yuji and others},
      year={2025},
      url={https://github.com/IBM/itbench-sample-scenarios/blob/main/it_bench_arxiv.pdf}
}
```

## Contributors
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

## Contacts
- agent-bench-automation@ibm.com
- Saurabh Jha (saurabh.jha@ibm.com)
- Yuji Wantabe (muew@jp.ibm.com)
- Ruchi Mahindru (rmahindr@us.ibm.com)
- Anca Sailer (ancas@us.ibm.com)
