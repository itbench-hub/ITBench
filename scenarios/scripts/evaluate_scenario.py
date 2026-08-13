#!/usr/bin/env python3
"""
Unified scenario evaluation script.

Evaluates three types of checks:
  1. Prometheus alerts with label matching
  2. Kubernetes resources with expected state (subset match)
  3. OPA policy evaluation (agent-submitted or integrity checks)

Output: JSON with results grouped by check type.
"""

import argparse
import json
import logging
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
import yaml
from kubernetes import client, config

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format="[%(levelname)s] %(message)s"
)


@dataclass
class CheckResult:
    """Result of a single check."""
    pass_: bool
    message: str

    def to_dict(self):
        return {"pass": self.pass_, "message": self.message}


class AlertsEvaluator:
    """Evaluates Prometheus alerts by name and labels."""

    def __init__(self, prometheus_url: str):
        self.prometheus_url = prometheus_url.rstrip("/")

    def evaluate(self, alerts: List[Dict[str, Any]]) -> tuple[List[Dict], bool]:
        """
        Evaluate alerts from groundtruth against Prometheus.

        Returns: (results_list, overall_pass)
        """
        results = []
        all_pass = True

        if not alerts:
            return results, True

        try:
            response = requests.get(
                f"{self.prometheus_url}/api/v1/alerts",
                timeout=10
            )
            response.raise_for_status()
            prometheus_data = response.json()
            firing_alerts = [
                a for a in prometheus_data.get("data", {}).get("alerts", [])
                if a.get("state") == "firing"
            ]
        except Exception as e:
            logger.error(f"Failed to query Prometheus: {e}")
            for alert in alerts:
                results.append({
                    "name": alert.get("name"),
                    **asdict(CheckResult(False, f"Prometheus query failed: {e}")).to_dict()
                })
            return results, False

        for expected_alert in alerts:
            alert_name = expected_alert.get("name")
            expected_labels = expected_alert.get("labels", {})

            # Find alert with matching name and labels
            matched = False
            for firing_alert in firing_alerts:
                if firing_alert.get("labels", {}).get("alertname") == alert_name:
                    # Check if all expected labels are present (subset match)
                    live_labels = firing_alert.get("labels", {})
                    if all(
                        live_labels.get(k) == v
                        for k, v in expected_labels.items()
                    ):
                        matched = True
                        break

            result = CheckResult(
                matched,
                f"Alert firing with expected labels"
                if matched
                else f"Alert not found or labels don't match"
            )
            results.append({
                "name": alert_name,
                **result.to_dict()
            })
            all_pass = all_pass and result.pass_

        return results, all_pass

    def to_json(self, results: List[Dict]) -> str:
        """Serialize results to JSON."""
        return json.dumps(results, indent=2)


class KubernetesEvaluator:
    """Evaluates Kubernetes resources with expected state matching."""

    def __init__(self, kubeconfig: str):
        try:
            config.load_kube_config(kubeconfig)
        except Exception as e:
            logger.error(f"Failed to load kubeconfig: {e}")
            raise

        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()
        self.custom_api = client.CustomObjectsApi()

    def _subset_match(self, expected: Any, live: Any, path: str = "") -> tuple[bool, str]:
        """
        Deep subset comparison: every key in expected must exist in live with same value.
        Live can have additional keys.

        Returns: (match: bool, reason: str)
        """
        if isinstance(expected, dict):
            if not isinstance(live, dict):
                return False, f"{path}: expected dict, got {type(live).__name__}"

            for key, expected_val in expected.items():
                if key not in live:
                    return False, f"{path}.{key}: missing in live"
                match, reason = self._subset_match(expected_val, live[key], f"{path}.{key}")
                if not match:
                    return False, reason
            return True, ""

        elif isinstance(expected, list):
            if not isinstance(live, list):
                return False, f"{path}: expected list, got {type(live).__name__}"

            # For lists, we do simple equality (not subset)
            if expected != live:
                return False, f"{path}: list values differ"
            return True, ""

        else:
            # Scalar comparison
            if expected != live:
                return False, f"{path}: expected {expected!r}, got {live!r}"
            return True, ""

    def _fetch_resource(self, resource: Dict[str, Any]) -> Optional[Dict]:
        """Fetch live resource from cluster."""
        api_version = resource.get("apiVersion", "v1")
        kind = resource.get("kind")
        namespace = resource.get("metadata", {}).get("namespace")
        name = resource.get("metadata", {}).get("name")

        try:
            if api_version == "v1":
                if kind == "Pod":
                    return self.v1.read_namespaced_pod(name, namespace).to_dict()
                elif kind == "Service":
                    return self.v1.read_namespaced_service(name, namespace).to_dict()
                elif kind == "ConfigMap":
                    return self.v1.read_namespaced_config_map(name, namespace).to_dict()
                else:
                    return None

            elif api_version == "apps/v1":
                if kind == "Deployment":
                    return self.apps_v1.read_namespaced_deployment(name, namespace).to_dict()
                elif kind == "StatefulSet":
                    return self.apps_v1.read_namespaced_stateful_set(name, namespace).to_dict()
                elif kind == "DaemonSet":
                    return self.apps_v1.read_namespaced_daemon_set(name, namespace).to_dict()
                else:
                    return None

            elif "policy" in api_version.lower() or "kyverno" in api_version.lower():
                # Custom resource: PolicyReport, ClusterPolicyReport, ClusterPolicy
                group, version = api_version.rsplit("/", 1) if "/" in api_version else ("", api_version)
                namespace_param = namespace if kind != "ClusterPolicyReport" else None

                if namespace_param:
                    return self.custom_api.get_namespaced_custom_object(
                        group, version, namespace_param, kind.lower() + "s", name
                    )
                else:
                    return self.custom_api.get_cluster_custom_object(
                        group, version, kind.lower() + "s", name
                    )

        except client.exceptions.ApiException as e:
            logger.debug(f"Failed to fetch {kind}/{name}: {e.status} {e.reason}")
            return None

        return None

    def evaluate(self, resources: List[Dict[str, Any]]) -> tuple[List[Dict], bool]:
        """
        Evaluate resources against cluster.

        Returns: (results_list, overall_pass)
        """
        results = []
        all_pass = True

        if not resources:
            return results, True

        for expected_resource in resources:
            kind = expected_resource.get("kind")
            name = expected_resource.get("metadata", {}).get("name")
            namespace = expected_resource.get("metadata", {}).get("namespace", "default")

            # Special handling for PolicyReport
            if kind in ["PolicyReport", "ClusterPolicyReport"]:
                result = self._evaluate_policy_report(expected_resource)
            else:
                # Standard resource matching
                live_resource = self._fetch_resource(expected_resource)
                if not live_resource:
                    result = CheckResult(
                        False,
                        f"{kind}/{name} ({namespace}): not found or failed to fetch"
                    )
                else:
                    match, reason = self._subset_match(expected_resource, live_resource)
                    result = CheckResult(
                        match,
                        f"{kind}/{name} ({namespace}): expected state matches"
                        if match
                        else f"{kind}/{name} ({namespace}): {reason}"
                    )

            results.append({
                "resource": f"{kind}/{name}" + (f" ({namespace})" if namespace and kind != "ClusterPolicyReport" else ""),
                **result.to_dict()
            })
            all_pass = all_pass and result.pass_

        return results, all_pass

    def _evaluate_policy_report(self, expected_report: Dict) -> CheckResult:
        """Evaluate PolicyReport by checking if expected results exist."""
        namespace = expected_report.get("metadata", {}).get("namespace")
        expected_results = expected_report.get("results", [])

        if not expected_results:
            return CheckResult(True, "PolicyReport: no specific results to check")

        try:
            # Fetch all PolicyReports in namespace
            reports = self.custom_api.list_namespaced_custom_object(
                "wgpolicyk8s.io", "v1alpha2", namespace, "policyreports"
            )
            all_results = []
            for report in reports.get("items", []):
                all_results.extend(report.get("results", []))

            # Check if all expected results exist
            for expected_result in expected_results:
                found = False
                for actual_result in all_results:
                    if (actual_result.get("policy") == expected_result.get("policy") and
                        actual_result.get("result") == expected_result.get("result")):
                        found = True
                        break

                if not found:
                    expected_str = f"policy={expected_result.get('policy')}, result={expected_result.get('result')}"
                    return CheckResult(False, f"PolicyReport: result not found: {expected_str}")

            return CheckResult(True, "PolicyReport: all expected results found")

        except Exception as e:
            return CheckResult(False, f"PolicyReport: failed to fetch: {e}")


class OPAEvaluator:
    """Evaluates OPA policies (agent-submitted or integrity checks)."""

    def __init__(self, kubeconfig: str, agent_output_path: Optional[str] = None, vm_inventory: Optional[str] = None):
        try:
            config.load_kube_config(kubeconfig)
        except Exception as e:
            logger.error(f"Failed to load kubeconfig: {e}")
            raise

        self.custom_api = client.CustomObjectsApi()
        self.agent_output_path = agent_output_path
        self.vm_inventory = vm_inventory

    def _extract_opa_result(self, json_output: str) -> Optional[Any]:
        """Extract result value from OPA JSON output."""
        try:
            data = json.loads(json_output)
            result = data.get("result", [{}])[0]
            expressions = result.get("expressions", [{}])
            return expressions[0].get("value")
        except Exception as e:
            logger.error(f"Failed to extract OPA result: {e}")
            return None

    def _run_opa_eval(self, data_file: str, input_file: str, output_format: str = "json") -> Optional[str]:
        """Run OPA eval and return output."""
        try:
            result = subprocess.run(
                ["opa", "eval", "--data", data_file, "--input", input_file,
                 "data.check.result", "--format", output_format],
                capture_output=True,
                text=True,
                timeout=30,
                check=False
            )
            if result.returncode != 0:
                logger.error(f"OPA eval failed: {result.stderr}")
                return None
            return result.stdout.strip()
        except Exception as e:
            logger.error(f"OPA eval error: {e}")
            return None

    def evaluate(self, checks: List[Dict[str, Any]]) -> tuple[List[Dict], bool]:
        """
        Evaluate OPA checks.

        Returns: (results_list, overall_pass)
        """
        results = []
        all_pass = True

        if not checks:
            return results, True

        for check in checks:
            check_name = check.get("name")
            expected_output = check.get("expectedOutput")

            if "expectedRules" in check:
                # Integrity path
                result = self._evaluate_integrity_check(check)
            else:
                # Agent-submitted path
                result = self._evaluate_agent_check(check)

            results.append({
                "check": check_name,
                **result.to_dict()
            })
            all_pass = all_pass and result.pass_

        return results, all_pass

    def _evaluate_agent_check(self, check: Dict[str, Any]) -> CheckResult:
        """Evaluate agent-submitted OPA check."""
        expected_files = check.get("expectedFiles", [])
        expected_output = check.get("expectedOutput")

        if not self.agent_output_path:
            return CheckResult(False, "Agent output archive not provided")

        agent_file = Path(self.agent_output_path)
        if not agent_file.exists():
            return CheckResult(False, f"Agent archive not found: {self.agent_output_path}")

        # Extract archive
        with tempfile.TemporaryDirectory() as tmpdir:
            try:
                with tarfile.open(agent_file, "r") as tar:
                    tar.extractall(tmpdir)
            except Exception as e:
                return CheckResult(False, f"Failed to extract archive: {e}")

            tmpdir_path = Path(tmpdir)

            # Pre-flight: check expected files
            for expected_file in expected_files:
                file_path = tmpdir_path / expected_file
                if not file_path.exists():
                    return CheckResult(
                        False,
                        f"Expected file missing: {expected_file}"
                    )

            # Find and run fetcher
            fetcher_files = list(tmpdir_path.glob("fetcher.*"))
            if not fetcher_files:
                return CheckResult(False, "Fetcher file not found in agent archive")

            fetcher_path = fetcher_files[0]
            fetcher_ext = fetcher_path.suffix

            try:
                if fetcher_ext == ".sh":
                    subprocess.run(
                        ["bash", str(fetcher_path)],
                        cwd=tmpdir,
                        check=True,
                        capture_output=True,
                        timeout=30
                    )
                elif fetcher_ext == ".yml":
                    if not self.vm_inventory:
                        return CheckResult(False, "VM inventory not provided for ansible fetcher")
                    subprocess.run(
                        ["ansible-playbook", str(fetcher_path), "-i", self.vm_inventory],
                        cwd=tmpdir,
                        check=True,
                        capture_output=True,
                        timeout=60
                    )
                else:
                    return CheckResult(False, f"Unknown fetcher type: {fetcher_ext}")
            except subprocess.CalledProcessError as e:
                return CheckResult(False, f"Fetcher execution failed: {e.stderr}")

            # Run OPA eval
            policy_file = tmpdir_path / "policy.rego"
            data_file = tmpdir_path / "collected_data.json"

            if not policy_file.exists() or not data_file.exists():
                return CheckResult(False, "policy.rego or collected_data.json not found after fetcher")

            opa_output = self._run_opa_eval(str(policy_file), str(data_file))
            if opa_output is None:
                return CheckResult(False, "OPA eval failed")

            opa_value = self._extract_opa_result(opa_output)
            if opa_value != expected_output:
                return CheckResult(
                    False,
                    f"OPA output mismatch: expected {expected_output}, got {opa_value}"
                )

            return CheckResult(True, f"OPA eval returned {expected_output}")

    def _evaluate_integrity_check(self, check: Dict[str, Any]) -> CheckResult:
        """Evaluate policy integrity check via expectedRules."""
        policy_name = check.get("policyName")
        expected_rules = check.get("expectedRules", [])
        expected_output = check.get("expectedOutput", True)

        try:
            # Fetch live ClusterPolicy
            policy = self.custom_api.get_cluster_custom_object(
                "kyverno.io", "v1", "clusterpolicies", policy_name
            )
        except client.exceptions.ApiException as e:
            return CheckResult(False, f"ClusterPolicy not found: {policy_name}")

        live_rules = policy.get("spec", {}).get("rules", [])

        with tempfile.TemporaryDirectory() as tmpdir:
            tmpdir_path = Path(tmpdir)

            # Write expected_rules.rego
            expected_rego = f"""package check

import rego.v1

expected_rules := {json.dumps(expected_rules)}

result if {{
    input.spec.rules == expected_rules
}}
"""
            rego_file = tmpdir_path / "expected_rules.rego"
            rego_file.write_text(expected_rego)

            # Write policy_input.json
            input_data = {"spec": {"rules": live_rules}}
            input_file = tmpdir_path / "policy_input.json"
            input_file.write_text(json.dumps(input_data))

            # Run OPA eval
            opa_output = self._run_opa_eval(str(rego_file), str(input_file))
            if opa_output is None:
                return CheckResult(False, "OPA integrity check failed")

            opa_value = self._extract_opa_result(opa_output)
            if opa_value != expected_output:
                return CheckResult(
                    False,
                    f"Policy rules mismatch: expected {expected_output}, got {opa_value}"
                )

            return CheckResult(True, f"{policy_name} rules unchanged")


def load_groundtruth(groundtruth_path: str) -> Dict[str, Any]:
    """Load and parse groundtruth YAML."""
    try:
        with open(groundtruth_path, "r") as f:
            data = yaml.safe_load(f)
        return data.get("spec", {})
    except Exception as e:
        logger.error(f"Failed to load groundtruth: {e}")
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Unified scenario evaluation script"
    )
    parser.add_argument(
        "--groundtruth",
        required=True,
        help="Path to groundtruth.yaml file"
    )
    parser.add_argument(
        "--kubeconfig",
        default=None,
        help="Path to kubeconfig (default: ~/.kube/config)"
    )
    parser.add_argument(
        "--prometheus-url",
        default="http://prometheus:9090",
        help="Prometheus URL (default: http://prometheus:9090)"
    )
    parser.add_argument(
        "--agent-output",
        default=None,
        help="Path to agent output archive"
    )
    parser.add_argument(
        "--vm-inventory",
        default=None,
        help="Path to VM inventory for ansible fetcher"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output file (default: stdout)"
    )

    args = parser.parse_args()

    try:
        groundtruth = load_groundtruth(args.groundtruth)
    except Exception as e:
        print(json.dumps({"error": str(e)}, indent=2), file=sys.stderr)
        sys.exit(1)

    # Normalize kubeconfig
    if args.kubeconfig is None:
        args.kubeconfig = str(Path.home() / ".kube" / "config")

    results = {
        "alerts": [],
        "kubernetes": [],
        "opa": []
    }
    all_pass = True

    # Evaluate alerts
    if groundtruth.get("alerts"):
        try:
            alerts_eval = AlertsEvaluator(args.prometheus_url)
            alert_results, alerts_pass = alerts_eval.evaluate(groundtruth["alerts"])
            results["alerts"] = alert_results
            all_pass = all_pass and alerts_pass
        except Exception as e:
            logger.error(f"Alerts evaluation failed: {e}")
            results["alerts"] = [{"error": str(e)}]
            all_pass = False

    # Evaluate Kubernetes resources
    if groundtruth.get("kubernetes", {}).get("resources"):
        try:
            k8s_eval = KubernetesEvaluator(args.kubeconfig)
            k8s_results, k8s_pass = k8s_eval.evaluate(groundtruth["kubernetes"]["resources"])
            results["kubernetes"] = k8s_results
            all_pass = all_pass and k8s_pass
        except Exception as e:
            logger.error(f"Kubernetes evaluation failed: {e}")
            results["kubernetes"] = [{"error": str(e)}]
            all_pass = False

    # Evaluate OPA checks
    if groundtruth.get("opa", {}).get("checks"):
        try:
            opa_eval = OPAEvaluator(args.kubeconfig, args.agent_output, args.vm_inventory)
            opa_results, opa_pass = opa_eval.evaluate(groundtruth["opa"]["checks"])
            results["opa"] = opa_results
            all_pass = all_pass and opa_pass
        except Exception as e:
            logger.error(f"OPA evaluation failed: {e}")
            results["opa"] = [{"error": str(e)}]
            all_pass = False

    # Output results
    output_data = {
        "alerts": results["alerts"],
        "kubernetes": results["kubernetes"],
        "opa": results["opa"]
    }

    output_json = json.dumps(output_data, indent=2)

    if args.output:
        Path(args.output).write_text(output_json)
        print(output_json)
    else:
        print(output_json)

    sys.exit(0 if all_pass else 1)


if __name__ == "__main__":
    main()
