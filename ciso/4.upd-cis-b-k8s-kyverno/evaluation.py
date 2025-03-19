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
import logging

import yaml

logger = logging.getLogger(__name__)
log_format = '[%(asctime)s %(levelname)s %(name)s] %(message)s'


def load_yaml(filename):
    with open(filename, 'r') as file:
        data = yaml.safe_load(file)
        return data


def load_yaml_docs(filename):
    with open(filename, 'r') as file:
        documents = yaml.safe_load_all(file)
        return list(documents)


def check_violation_in_policy_reports(policy_reports, test, strict_check):

    policy_name = test["policy_name"]
    ignore_policies = test.get("ignore_policies", [])
    resource = test["resource"]
    expected_result = test["expected_result"]
    name = resource["name"]
    namespace = resource.get("namespace", "")
    kind = resource["kind"]
    api_version = resource["api_version"]

    def is_scoped(r):
        s = r.get("scope", {})
        return s.get("namespace", "") == namespace and s.get("name") == name and s.get("kind") == kind and s.get("apiVersion") == api_version

    filtered_by_resource = [r for r in policy_reports if is_scoped(r)]

    for report in filtered_by_resource:
        if strict_check:  # check if other policies hit and do not accept it
            for r in [r for r in report.get("results", []) if not r.get("policy") in [policy_name] + ignore_policies]:
                if r.get("result") == expected_result:
                    return build_check_result(
                        test,
                        False,
                        f"Strict policy strict check failed: Detected expected result '{expected_result}' in a different policy '{policy_name}' for resource '{name}'",
                    )
                elif r.get("result") != expected_result:
                    return build_check_result(
                        test,
                        False,
                        f"Strict policy check failed: Detected result '{r.get('result')}' in a different policy '{policy_name}' for resource '{name}', expected '{expected_result}'",
                    )
        for r in [r for r in report.get("results", []) if r.get("policy") == policy_name]:
            if r.get("result") == expected_result:
                return build_check_result(
                    test, True, f"Policy check passed: Detected expected result '{expected_result}' in policy '{policy_name}' for resource '{name}'"
                )
            elif r.get("result") != expected_result:
                return build_check_result(
                    test,
                    False,
                    f"Policy check failed: Detected result '{r.get('result')}' in policy '{policy_name}' for resource '{name}', expected '{expected_result}'",
                )

    if expected_result == "pass" and not any(r.get("policy") == policy_name for r in filtered_by_resource):
        return build_check_result(
            test, True, f"Policy check passed: Resource '{name}' not found in policy '{policy_name}', as expected for result '{expected_result}'"
        )

    return build_check_result(test, False, f"Policy check failed: Not found the scoped resource '{name}'")


def compare_dicts(expected, actual):
    if isinstance(expected, dict) and isinstance(actual, dict):
        for key, value in expected.items():
            if key not in actual or not compare_dicts(value, actual[key]):
                return False
        return True
    elif isinstance(expected, list) and isinstance(actual, list):
        return all(compare_dicts(e, a) for e, a in zip(expected, actual))
    else:
        return expected == actual


def check_policy_rules_unchanged(existing_policies, current_policies, test):
    policy_name = test["policy_name"]
    filtered = [policy for policy in existing_policies if policy.get("metadata", {}).get("name") == policy_name]
    if len(filtered) == 0:
        return build_check_result(test, False, f"Policy {policy_name} not found in existing policies.")
    existing_policy = filtered[0]

    filtered = [policy for policy in current_policies if policy.get("metadata", {}).get("name") == policy_name]
    if len(filtered) == 0:
        return build_check_result(test, False, f"Policy {policy_name} not found in current policies.")
    current_policy = filtered[0]

    expected_rules = existing_policy.get("spec", {}).get("rules", [])
    actual_rules = current_policy.get("spec", {}).get("rules", [])
    if not compare_dicts(expected_rules, actual_rules):
        message = f"Rules mismatch in policy: {policy_name}"
        return build_check_result(test, False, message)

    return build_check_result(test, True, f"Policy integrity check passed: No modifications detected in rules for policy '{policy_name}'")


def build_check_result(test, result, message, error=None):

    r = {"pass": result, "message": message}
    if error:
        r["error"] = f"{error}"
    logger.info(message)
    return r


def main(config_path, epol, pol, cpol, polr, cpolr, output_path):
    try:
        config_data = load_yaml(config_path)

        policies = load_yaml(pol)["items"] + load_yaml(cpol)["items"]
        policy_reports = load_yaml(polr)["items"] + load_yaml(cpolr)["items"]

        existing_policies = load_yaml_docs(epol)

        check_results = []
        for test in config_data["check_violations"]:
            if test.get("strict_check", False):
                check_result = check_violation_in_policy_reports(policy_reports, test, True)
                check_results.append(check_result)
            check_result = check_violation_in_policy_reports(policy_reports, test, False)
            check_results.append(check_result)

        for test in config_data["check_unchanged_policies"]:
            check_result = check_policy_rules_unchanged(existing_policies, policies, test)
            check_results.append(check_result)

        overall_pass = all(result["pass"] for result in check_results)
        output = {"pass": overall_pass, "details": check_results}
    except Exception as e:
        output = {"pass": False, "details": [], "error": f"{e}"}

    o = json.dumps(output, indent=2)
    if output_path:
        with open(output_path, "w") as f:
            f.write(o)
    else:
        print(json.dumps(output, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate Kyverno policy checks.")
    parser.add_argument("--epol", type=str, help="Path to the existing policies (yaml docs)")
    parser.add_argument("--pol", type=str, help="Path to the all policies in JSON (k get pol -A -o yaml)")
    parser.add_argument("--cpol", type=str, help="Path to the all cluster policies in JSON (k get cpol -o yaml)")
    parser.add_argument("--polr", type=str, help="Path to the all policy reports in JSON (k get polr -A -o yaml)")
    parser.add_argument("--cpolr", type=str, help="Path to the all cluster policy reports in JSON (k get cpolr -o yaml)")
    parser.add_argument("config_path", type=str, help="Path to the JSON configuration file")
    parser.add_argument("-o", "--output", type=str, help="Path to the output JSON file (Default stdout.)")
    args = parser.parse_args()
    main(args.config_path, args.epol, args.pol, args.cpol, args.polr, args.cpolr, args.output)
