#!/usr/bin/env bash
#
# Run the Dynatrace Grail recorder (gather.py) locally, against the Dynatrace
# SaaS API — no Kubernetes cluster needed. This is the manual counterpart to the
# in-cluster recorder Job: identical script, output written to ./dynatrace-records
# on this machine instead of a PVC.
#
# Config resolution (first non-empty wins):
#   1. environment variables (DT_PLATFORM_URL, DT_PLATFORM_TOKEN, ...)
#   2. the recorder block in observability_vendors.yaml (platform_url,
#      platform_token_path, namespace)
#   3. built-in defaults
#
# Usage:
#   ./run_local.sh                       # window = now-1h .. now
#   DT_DQL_FROM=2026-07-30T09:00:00Z ./run_local.sh
#   DT_DQL_FROM=now-6h DT_DQL_FORMAT=csv ./run_local.sh
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# scripts/dynatrace -> scenarios/sre is six levels up
# (dynatrace/scripts/files/recorders/roles/project -> sre).
SRE_ROOT="$(cd "${SCRIPT_DIR}/../../../../../.." && pwd)"
VENDORS_FILE="${SRE_ROOT}/inventory/group_vars/environment/observability_vendors.yaml"

# ── Tiny YAML value reader for observability_vendors.dynatrace.recorder.<key> ──
# Only used as a fallback when the matching env var is unset. Uses python3 (yaml
# is available with the project's uv env) and falls back to empty on any error.
vendor_get() {
  local key="$1"
  python3 - "$VENDORS_FILE" "$key" <<'PY' 2>/dev/null || true
import sys, yaml
path, key = sys.argv[1], sys.argv[2]
try:
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    rec = (((data.get("observability_vendors") or {})
            .get("dynatrace") or {})
            .get("recorder") or {})
    val = rec.get(key, "")
    print("" if val is None else val)
except Exception:
    print("")
PY
}

# ── Resolve config ────────────────────────────────────────────────────────────
DT_PLATFORM_URL="${DT_PLATFORM_URL:-$(vendor_get platform_url)}"
DT_K8S_NAMESPACE="${DT_K8S_NAMESPACE:-$(vendor_get namespace)}"
DT_K8S_NAMESPACE="${DT_K8S_NAMESPACE:-otel-demo}"

# Token: explicit env wins, else read the file referenced by platform_token_path.
if [ -z "${DT_PLATFORM_TOKEN:-}" ]; then
  token_path="$(vendor_get platform_token_path)"
  if [ -n "$token_path" ]; then
    case "$token_path" in
      /*) : ;;                              # absolute
      *)  token_path="${SRE_ROOT}/${token_path}" ;;  # relative to SRE root
    esac
    if [ -f "$token_path" ]; then
      DT_PLATFORM_TOKEN="$(tr -d '\r\n' < "$token_path")"
    fi
  fi
fi

DT_DQL_FROM="${DT_DQL_FROM:-now-1h}"
DT_DQL_TO="${DT_DQL_TO:-now}"
DT_DQL_INTERVAL="${DT_DQL_INTERVAL:-1m}"
DT_DQL_LIMIT="${DT_DQL_LIMIT:-1000}"
DT_DQL_FORMAT="${DT_DQL_FORMAT:-both}"

# Output goes to a local directory the script owns (HOME/records is what
# gather.py writes to, so point HOME at our output dir for this run).
OUTDIR="${DT_LOCAL_OUTDIR:-${SCRIPT_DIR}/dynatrace-records}"

# ── Validate ────────────────────────────────────────────────────────────────
missing=""
[ -z "${DT_PLATFORM_URL}" ]   && missing="${missing} DT_PLATFORM_URL(or recorder.platform_url)"
[ -z "${DT_PLATFORM_TOKEN}" ] && missing="${missing} DT_PLATFORM_TOKEN(or recorder.platform_token_path)"
if [ -n "$missing" ]; then
  echo "error: missing config:${missing}" >&2
  exit 1
fi

# ── Python env ────────────────────────────────────────────────────────────────
VENV="${DT_LOCAL_VENV:-/tmp/dtrec}"
if [ ! -x "${VENV}/bin/python" ]; then
  echo "Creating virtualenv at ${VENV} ..."
  python3 -m venv "${VENV}"
fi
"${VENV}/bin/pip" install --quiet --disable-pip-version-check -r "${SCRIPT_DIR}/requirements.txt"

# ── Run ──────────────────────────────────────────────────────────────────────
mkdir -p "${OUTDIR}/records"
echo "Dynatrace recorder (local)"
echo "  URL       : ${DT_PLATFORM_URL}"
echo "  namespace : ${DT_K8S_NAMESPACE}"
echo "  window    : ${DT_DQL_FROM} -> ${DT_DQL_TO}"
echo "  format    : ${DT_DQL_FORMAT}"
echo "  output    : ${OUTDIR}/records"
echo

# gather.py writes to \$HOME/records; point HOME at OUTDIR just for this process.
HOME="${OUTDIR}" \
DT_PLATFORM_URL="${DT_PLATFORM_URL}" \
DT_PLATFORM_TOKEN="${DT_PLATFORM_TOKEN}" \
DT_K8S_NAMESPACE="${DT_K8S_NAMESPACE}" \
DT_DQL_FROM="${DT_DQL_FROM}" \
DT_DQL_TO="${DT_DQL_TO}" \
DT_DQL_INTERVAL="${DT_DQL_INTERVAL}" \
DT_DQL_LIMIT="${DT_DQL_LIMIT}" \
DT_DQL_FORMAT="${DT_DQL_FORMAT}" \
  "${VENV}/bin/python" "${SCRIPT_DIR}/gather.py"

echo
echo "Done. Files:"
ls -la "${OUTDIR}/records"
