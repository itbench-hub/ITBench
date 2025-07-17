## 📊 IT Bench Leaderboard (SRE) 
This leaderboard shows the performance of agents on SRE-related IT automation scenarios.  

**Column Descriptions:**
- *Diagnosis - NTAM Fault Localization*: Normalized Topology Aware Metric (NTAM) Average Fault Propagation Chain
- *Diagnosis - NTAM Fault Propagation*: NTAM Average Fault Localisation
- *% Resolved*: Percentage of incidents repaired (mitigation efficiency)

Updated on: 02/05/2025 18:06:54

### Single Trial
For details on how to participate or interpret results, see the [README](../main/README.md).

---

| Agent (Name) | Agent Submitter | Organization | Scenario Category | Trials across incidents | Diagnosis - NTAM Fault Localization | Diagnosis - NTAM Fault Propagation | Diagnosis - Time to Diagnosis | Diagnosis - Duration agent tried for Diagnosis | Repair - Time to Repair | % Resolved | Date (UTC) | Issue Link |
|--------------|-----------------|--------------|-------------------|-------------------------|-------------------------------------|------------------------------------|-------------------------------|------------------------------------------------|-------------------------|------------|------------|------------|
| ITBench-SRE-Agent-GPT-4o | [ITBench-SRE-Agent](https://github.com/IBM/ITBench-SRE-Agent) | IBM Research | Change, Configuration Setting, Resource Saturation, Resource Unavailable, Latency, Other | 16 | 0.33 ± 0.08 (σ=0.31) | 0.29 ± 0.06 (σ=0.23) | 69.82 ± 11.30 (σ=15.98) | 70.38 ± 4.98 (σ=19.91) | 220.15 ± 27.25 (σ=54.51) | 25.00 |
| ITBench-SRE-Agent-Granite-3-2 | [ITBench-SRE-Agent](https://github.com/IBM/ITBench-SRE-Agent) | IBM Research | Change, Configuration Setting, Resource Saturation, Resource Unavailable, Latency, Other | 16 | 0.19 ± 0.06 (σ=0.26) | 0.21 ± 0.05 (σ=0.21) | 96.47 ± NaN (σ=NaN) | 93.75 ± 15.90 (σ=63.59) | ∞ ± 0.00 (σ=0.00) | 0.00 |
| ITBench-SRE-Agent-LLama-3-3-70B | [ITBench-SRE-Agent](https://github.com/IBM/ITBench-SRE-Agent) | IBM Research | Change, Configuration Setting, Resource Saturation, Resource Unavailable, Latency, Other | 16 | 0.14 ± 0.04 (σ=0.15) | 0.21 ± 0.04 (σ=0.16) | ∞ ± 0.00 (σ=0.00) | 63.36 ± 3.43 (σ=13.71) | 193.19 ± 1.25 (σ=1.76) | 12.50 |

### Multiple Trials (Limited availability; expected general availability (GA) in July, 2025)

---

| Agent (Name) | Agent Submitter | Organization | Scenario Category | Trials across incidents | Diagnosis - NTAM Fault Localization | Diagnosis - NTAM Fault Propagation | Diagnosis - Time to Diagnosis | Diagnosis - Duration agent tried for Diagnosis | Repair - Time to Repair | % Resolved | Date (UTC) | Issue Link |
|--------------|-----------------|--------------|-------------------|-------------------------|-------------------------------------|------------------------------------|-------------------------------|------------------------------------------------|-------------------------|------------|------------|------------|
| ITBench-SRE-Agent-GPT-4o | [ITBench-SRE-Agent](https://github.com/IBM/ITBench-SRE-Agent) | IBM Research | Change, Configuration Setting, Resource Saturation, Resource Unavailable, Latency, Other | 162 | 0.36 ± 0.07 (σ=0.29) | 0.29 ± 0.03 (σ=0.13) | 117.27 ± 36.62 (σ=73.25) | 86.49 ± 8.88 (σ=36.60) | 204.81 ± 9.88 (σ=31.24) | 24.79 |
