# Copyright contributors to the ITBench project. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import argparse
import json
import yaml
import logging
from pathlib import Path

logger = logging.getLogger(__name__)
log_format = '[%(asctime)s %(levelname)s %(name)s] %(message)s'


def main():
    parser = argparse.ArgumentParser(
        description="Evaluate if the Playbook to check the provided CIS Kubernetes Benchmark issue(s) exists and is working."
    )
    parser.add_argument(
        "-polr", "--policy-reports", type=str, help="Path to the aggregated policy report in JSON format (kubectl get polr -A -o json)", required=True
    )
    parser.add_argument(
        "-cpolr",
        "--cluster-policy-reports",
        type=str,
        help="Path to the aggregated cluster policy report in JSON format (kubectl get cpolr -A -o json)",
        required=True,
    )
    parser.add_argument(
        "--api-version",
        type=str,
        help="Resource Api Version",
        required=True,
    )
    parser.add_argument(
        "--kind",
        type=str,
        help="Resource Kind",
        required=True,
    )
    parser.add_argument(
        "--namespace",
        type=str,
        help="Resource Namespace",
        required=True,
    )
    parser.add_argument(
        "--name",
        type=str,
        help="Resource Name",
        required=True,
    )
    parser.add_argument(
        "--agent-output",
        type=str,
        help="Directory of Agent Output",
        required=True,
    )
    parser.add_argument("-o", "--out", type=str, help="Path to output JSON file (default: stdout)")

    args = parser.parse_args()

    polr_path = Path(args.policy_reports)
    with polr_path.open("r") as f:
        polr = json.load(f)

    cpolr_path = Path(args.cluster_policy_reports)
    with cpolr_path.open("r") as f:
        cpolr = json.load(f)

    target = {
        "apiVersion": args.api_version,
        "kind": args.kind,
        "namespace": args.namespace,
        "name": args.name,
    }
    logger.info(f"Checking ApiVersion: {json.dumps(target)}")
    policy_reports = polr["items"] + cpolr["items"]
    summaries = []
    for p in policy_reports:
        scope = p["scope"]
        if (
            scope["apiVersion"] == target["apiVersion"]
            and scope["kind"] == target["kind"]
            and (scope["namespace"] == target["namespace"] if "namespace" in scope else True)
            and scope["name"] == target["name"]
        ):
            summaries.append(p["summary"])

    failures = [x for x in summaries if x["fail"] > 0]
    detected = len(failures) > 0

    is_generate_policy = False
    is_evidence_available = False
    agent_output = Path(args.agent_output)
    if agent_output.exists():
        is_evidence_available = True
        yaml_files = list(agent_output.glob("*.yaml")) + list(agent_output.glob("*.yml"))
        for yaml_file in yaml_files:
            try:
                yaml_data = yaml.safe_load(yaml_file.open("r"))
                if yaml_data.get("kind") in ["Policy", "ClusterPolicy"]:
                    is_generate_policy = True
            except Exception as e:
                logger.error(f"{e}")
    tasks = {
        "generate_assessment_posture": detected,
        "generate_policy": is_generate_policy,
        "evidence_available": is_evidence_available,
    }
    output = json.dumps({"pass": detected, "tasks": tasks}, indent=2)
    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
    else:
        print(output)


if __name__ == "__main__":
    main()
