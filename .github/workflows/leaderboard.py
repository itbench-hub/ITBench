import argparse
import json
import os
import re
import urllib.request
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlencode

ITBENCH_API = os.getenv("ITBENCH_API")
ITBENCH_API_TOKEN = os.getenv("ITBENCH_API_TOKEN")
GH_REPO = os.getenv("GH_REPO")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "10"))


def get_leaderboard(benchmark_id: str = None, github_username: str = None):
    url = f"{ITBENCH_API}/gitops/aggregate-results"
    query_params = {}
    if benchmark_id is not None:
        query_params["benchmark_id"] = benchmark_id
    if github_username is not None:
        query_params["github_username"] = github_username
    if query_params:
        url += "?" + urlencode(query_params)
    headers = {"Authorization": f"Bearer {ITBENCH_API_TOKEN}"}
    req = urllib.request.Request(url=url, headers=headers, method="GET")
    res = urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT)

    if res.getcode() != 200:
        print(f"Error requesting leaderboard JSON: {res.status_code}. {res.content}")
        exit(1)

    res_body = res.read()
    res_dict = json.loads(res_body.decode("utf-8"))
    return res_dict


def parse_json_timedelta(delta):
    if not delta:
        return "N/A"

    match = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+(?:\.\d+)?)S)?", delta)
    if not match:
        return "Invalid"

    hours = int(match.group(1)) if match.group(1) else 0
    minutes = int(match.group(2)) if match.group(2) else 0
    seconds = float(match.group(3)) if match.group(3) else 0.0
    return str(int(timedelta(hours=hours, minutes=minutes, seconds=seconds).total_seconds())) + "s"


def get_timestamp(dt: Optional[datetime] = None) -> str:
    if not dt:
        dt = datetime.now(timezone.utc)
    return dt.strftime("%d/%m/%Y %H:%M:%S")


def to_datetime(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def build_overall_table(leaderboard):
    bench_summary = []
    prev_score = None
    rank = 0
    count = 0
    for benchmark in leaderboard:
        count += 1
        if benchmark["score"] != prev_score:
            rank = count
        name = benchmark["agent"]
        github_username_link = benchmark["github_username_link"]
        github_username_org = benchmark["github_username_org"]
        score = f'{int(benchmark["score"] * 100)}%'
        agent_type = benchmark["agent_type"]
        checkmarks = "✅" * benchmark["num_of_passed"] if benchmark["num_of_passed"] >= 0 else "N/A"
        notes = f'Related to {benchmark["incident_type"]} scenarios'
        issue_link = benchmark["issue_link"]

        sre = finops = ciso = "N/A"
        if agent_type == "SRE":
            sre = checkmarks
        elif agent_type == "FinOps":
            finops = checkmarks
        elif agent_type == "CISO":
            ciso = checkmarks
        bench_line = [
            rank,
            name,
            github_username_link,
            github_username_org,
            score,
            sre,
            finops,
            ciso,
            issue_link,
            notes,
        ]
        prev_score = benchmark["score"]
        bench_summary.append(bench_line)

    header_str = ['Rank', 'Agent Name', 'Agent Submitter', 'Organization', 'Overall Score', 'SRE', 'FinOps', 'CISO', 'Issue Link', 'Notes']
    line_fmt = '| {:^4} | {:^20} | {:^13} | {:^13} | {:^13} | {:^13} | {:^13} | {:^13} | {:^13} | {:<30} |'
    headers = line_fmt.format(*header_str)
    header_len = len(headers)

    texts = []
    texts.append("## 📊 IT Bench Leaderboard")
    header = """\
This table shows a consolidated view of all agent submissions across different domains (SRE, FinOps, CISO).

For details on how to participate, see the [README](../README.md).

**Column Descriptions:**
- *Overall Score*: Combined performance across available domains
- *SRE / FinOps / CISO*: ✅ if benchmarks in that domain were completed
- *Notes*: Additional context on the evaluated scenarios
"""
    texts.append(header)
    texts.append(f"\n\nUpdated on: {get_timestamp()}\n\n")
    texts.append("-" * header_len)
    texts.append(headers)
    texts.append(line_fmt.format(*("---" * 7)))
    for bench_line in bench_summary:
        texts.append(line_fmt.format(*bench_line))

    return "\n".join(texts)

def build_ciso_table(leaderboard) -> str:
    column_mapping = {
        "id": "Benchmark (ID)",
        "github_username_link": "Agent Submitter",
        "github_username_org": "Organization",
        "agent": "Agent Name",
        "incident_type": "Scenario Category",
        "score": "Score ⬆️",
        "mttr": "Mean Agent Execution Duration",
        "num_of_passed": "#Passed",
        "issue_link": "Issue Link",
        "date": "Date (UTC)",
    }
    columns = ["agent", "github_username_link", "github_username_org", "incident_type", "score", "num_of_passed", "mttr", "date", "issue_link"]
    headers = [column_mapping[col] for col in columns]

    texts = []
    texts.append("## 📊 IT Bench Leaderboard (CISO)")
    header = """\
This leaderboard shows the performance of agents on CISO-related IT automation scenarios.  
For details on how to participate or interpret results, see the [README](../main/README.md).

**Column Descriptions:**
- *Score*: Average benchmark score across scenarios (1.0 = perfect)
- *#Passed*: Number of scenarios successfully passed
- *Mean Agent Execution Duration*: Average time taken across scenarios
- *Scenario Category*: Categories of evaluated tasks (e.g., RHEL, Kyverno, etc.)
"""
    texts.append(header)
    texts.append(f"\n\nUpdated on: {get_timestamp()}\n\n")
    texts.append("---")
    texts.append("| " + " | ".join(headers) + " |")
    texts.append("|" + "|".join(["-" * (len(h) + 2) for h in headers]) + "|")

    for row in leaderboard:
        values = []
        for col in columns:
            val = row.get(col, "")
            if col == "mttr":
                val = parse_json_timedelta(val)
            elif col == "date":
                val = get_timestamp(to_datetime(val))
            elif isinstance(val, float):
                val = f"{val:.2f}"
            values.append(str(val))
        texts.append("| " + " | ".join(values) + " |")
    return "\n".join(texts)

def get_nested_value(metric_name, content) -> dict:
    metric_parent, metric = metric_name.split("__")
    nested_dict = content[metric_parent][metric]

    formatted_dict = {k: (lambda v: f"{v:.2f}" if isinstance(v, float) else v)(val)
                     for k, val in nested_dict.items()}
    return json.dumps(formatted_dict)

def build_sre_table(leaderboard) -> str:
    column_mapping = {
        "id": "Benchmark (ID)",
        "github_username_link": "Agent Submitter",
        "github_username_org": "Organization",
        "name_decorated": "Benchmark (Name)",
        "agent": "Agent (Name)",
        "incident_type": "Scenario Category",
        "trials": "Trials across incidents",
        "percent_agent_submitted_diagnosis_results": "Diagnosis received - % of Trials",
        "diagnosis__ntam_fault_localization": "Diagnosis - NTAM Fault Localization",
        "diagnosis__ntam_fault_propagation": "Diagnosis - NTAM Fault Propagation",
        "diagnosis__time_to_diagnosis": "Diagnosis - Time to Diagnosis",
        "diagnosis__duration_agent_tried_for_diagnosis": "Diagnosis - Duration agent tried for Diagnosis",
        "repair__time_to_repair": "Repair - Time to Repair",
        "percent_resolved": "% Resolved",
        "issue_link": "Issue Link",
        "date": "Date (UTC)",
    }
    columns = ["agent", "github_username_link", "github_username_org",
               "incident_type", "trials",
               "diagnosis__ntam_fault_localization",
               "diagnosis__ntam_fault_propagation",
               "diagnosis__time_to_diagnosis",
               "diagnosis__duration_agent_tried_for_diagnosis",
               "repair__time_to_repair",
               "percent_resolved",
               "date", "issue_link"]
    headers = [column_mapping[col] for col in columns]

    texts = []
    texts.append("## 📊 IT Bench Leaderboard (SRE)")
    header = f"""\
This leaderboard shows the performance of agents on SRE-related IT automation scenarios.  
For details on how to participate or interpret results, see the [README](../main/README.md).

**Column Descriptions:**
- *Diagnosis - NTAM Fault Localization*: Normalized Topology Aware Metric (NTAM) Average Fault Propagation Chain
- *Diagnosis - NTAM Fault Propagation*: NTAM Average Fault Localisation
- *% Resolved*: Percentage of incidents repaired (mitigation efficiency)
"""
    texts.append(header)
    texts.append(f"\n\nUpdated on: {get_timestamp()}\n\n")
    texts.append("---")
    texts.append("| " + " | ".join(headers) + " |")
    texts.append("|" + "|".join(["-" * (len(h) + 2) for h in headers]) + "|")

    for row in leaderboard:
        values = []
        for col in columns:
            val = row.get(col, "")
            if col == "mttr":
                val = parse_json_timedelta(val)
            elif col == "date":
                val = get_timestamp(to_datetime(val))
            elif (col == "diagnosis__ntam_fault_localization" or
                  col == "diagnosis__ntam_fault_propagation" or
                  col == "diagnosis__time_to_diagnosis" or
                  col == "diagnosis__duration_agent_tried_for_diagnosis" or
                  col == "repair__time_to_repair"):
                val = get_nested_value(col, row)
            elif col == "percent_resolved":
                val = row.get("repair", {}).get(col, 0.0)
            elif isinstance(val, float):
                val = f"{val:.2f}"
            values.append(str(val))
        texts.append("| " + " | ".join(values) + " |")
    return "\n".join(texts)

SAMPLE_DATA = [
    {
        'name': 'Run-2',
        'incident_type': 'SRE',
        'agent': 'Agent-104',
        'results': [{}] * 10,
        'mttr': 'PT0S',
        'num_of_passed': 3,
        'score': 0.3,
        'date': '2025-03-11T13:54:23.576999Z',
        'id': 'f324b0ca-5065-435e-a140-1db3f409926d',
        'agent_type': 'SRE',
        'github_username': 'Rohan-Arora',
    },
    {
        'name': 'My CISO Agent Benchmark',
        'incident_type': 'Gen-CIS-b-K8s-Kyverno',
        'agent': 'My CISO Agent (Yana)',
        'results': [{}] * 10,
        'mttr': 'PT1M5.70376S',
        'num_of_passed': 3,
        'score': 0.3,
        'date': '2025-03-17T00:36:52.334468Z',
        'id': '337e85bf-f29d-4b60-b159-6f66c9d6febe',
        'agent_type': 'CISO',
        'github_username': 'yana1205',
    },
    {
        'name': 'Top SRE Benchmark',
        'incident_type': 'SRE',
        'agent': 'Baseline SRE Agent',
        'results': [{}] * 10,
        'mttr': 'PT30S',
        'num_of_passed': 7,
        'score': 0.70,
        'date': '2025-03-20T12:00:00Z',
        'id': 'aaa-bbb',
        'agent_type': 'SRE',
        'github_username': 'sre_star',
    },
    {
        'name': 'Top CISO Benchmark',
        'incident_type': 'Gen-CIS-b-RHEL9-Ansible-OPA',
        'agent': 'Baseline CISO Agentp',
        'results': [{}] * 10,
        'mttr': 'PT1M',
        'num_of_passed': 6,
        'score': 0.6,
        'date': '2025-03-20T12:10:00Z',
        'id': 'ccc-ddd',
        'agent_type': 'CISO',
        'github_username': 'ciso_champ',
    },
]


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Print IT Bench leaderboard")
    parser.add_argument("leaderboard")
    parser.add_argument("-u", "--github_username", type=str)
    parser.add_argument("-b", "--benchmark_id", type=str)
    parser.add_argument("--issues", type=str, required=True)
    parser.add_argument("--users", type=str, required=True)
    parser.add_argument("--out-ciso", type=str, required=True)
    parser.add_argument("--out-sre", type=str, required=True)
    parser.add_argument("--out-overall", type=str, required=True)
    parser.add_argument("--sample", action="store_true", help="Use sample data")
    args = parser.parse_args()
    if args.sample:
        leaderboard = SAMPLE_DATA
        # leaderboard_real = get_leaderboard(args.benchmark_id, args.github_username)
        leaderboard_real = []
        leaderboard = leaderboard + leaderboard_real
    else:
        if args.leaderboard == "global":
            leaderboard = get_leaderboard()
        else:
            leaderboard = get_leaderboard(args.benchmark_id, args.github_username)

    with open(args.issues, "r") as f:
        issues = json.load(f)

    with open(args.users, "r") as f:
        users = json.load(f)

    benchmark_issue_mapping = {issue["benchmark_id"]: issue["number"] for issue in issues}
    for item in leaderboard:
        number = benchmark_issue_mapping.get(item["id"])
        item["issue_link"] = f"[#{number}](https://github.com/{GH_REPO}/issues/{number})" if number else "Not Found"
        username = item.get("github_username")
        item["github_username_link"] = f"[{username}](https://github.com/{username})" if username else "N/A"
        company = users.get(username, {}).get("company")
        item["github_username_org"] = company if company else ""
        # temporal solution for SRE metrics
        if "score" not in item:
            item["score"] = item.get("percent_agent_submitted_diagnosis_results", 0.0) / 100
        if "num_of_passed" not in item:
            item["num_of_passed"] = int(item["score"] * 10)  # treate number of pass as decile of score

    leaderboard = sorted(leaderboard, key=lambda x: x["score"], reverse=True)
    leaderboard_ciso = [x for x in leaderboard if x["agent_type"] == "CISO"]
    leaderboard_sre = [x for x in leaderboard if x["agent_type"] == "SRE"]

    overall_table = build_overall_table(leaderboard)
    with open(args.out_overall, "w") as f:
        f.write(overall_table)

    ciso_table = build_ciso_table(leaderboard_ciso)
    with open(args.out_ciso, "w") as f:
        f.write(ciso_table)

    sre_table = build_sre_table(leaderboard_sre)
    with open(args.out_sre, "w") as f:
        f.write(sre_table)
