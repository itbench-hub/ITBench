#!/usr/bin/env bash
# Throwaway experiment helper. Polls the PolicyReports of a namespace every 2 seconds and prints the entries of one
# policy whenever they change.
# Usage: poll.sh <namespace> <policy name> <max seconds> <stop regex on result, or "none">
set -u

namespace=$1
policy=$2
limit=$3
stop=$4

start=$(date +%s)
last=""
stopped="no"

while :; do
  elapsed=$(($(date +%s) - start))
  entries=$(kubectl get policyreports.wgpolicyk8s.io -n "$namespace" -o json 2>/dev/null |
    jq -c --arg p "$policy" '
      [.items[].results[]? | select(.policy | endswith($p))
        | {policy, result, message, process: .properties.process, resource: .resources[0].name}]
      | sort_by(.result, .message, .resource) | unique') || entries=""
  entries=${entries:-"kubectl or jq failed"}

  if [ "$entries" != "$last" ]; then
    echo "t=${elapsed}s entries=$entries"
    last=$entries
  fi

  if [ "$stop" != "none" ] && echo "$entries" | jq -e --arg re "$stop" 'any(.[]?; .result | test($re))' >/dev/null 2>&1; then
    stopped="yes"
    break
  fi

  if [ "$elapsed" -ge "$limit" ]; then
    break
  fi
  sleep 2
done

echo "end t=$(($(date +%s) - start))s stop_condition_met=$stopped"
echo "all results in namespace:"
kubectl get policyreports.wgpolicyk8s.io -n "$namespace" -o json 2>/dev/null |
  jq -c '[.items[].results[]? | {policy, result, process: .properties.process}]' || true
