import csv
import datetime
import json
import logging
import os
import re
import sys
import time

from datetime import datetime, timedelta, timezone

import requests

from requests.adapters import HTTPAdapter
from urllib3.util import Retry

# Logging
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger(__name__)

# NOTE: This recorder is the SaaS counterpart to the in-cluster scrapers
#       (clickhouse/jaeger/prometheus). Dynatrace Grail retains history that is
#       queryable by timeframe, so a single run at teardown back-queries the
#       whole incident window [scenario start -> now] for every dataset. The
#       topology dataset is the exception: it is captured as two point-in-time
#       snapshots (init = scenario start, stop = teardown). It is
#       adapted from dynatrace_scripts/pull_dql_json.py: the CLI, .env, and
#       dotenv dependency are removed and all configuration comes from
#       environment variables injected by the recorder Job.

# ── Config (from environment) ────────────────────────────────────────────────
PLATFORM_TOKEN = os.environ.get("DT_PLATFORM_TOKEN", "")
PLATFORM_URL = os.environ.get("DT_PLATFORM_URL", "").rstrip("/")

NAMESPACE = os.environ.get("DT_K8S_NAMESPACE", "otel-demo").strip()
TIME_FROM = os.environ.get("DT_DQL_FROM", "now-1h")
TIME_TO = os.environ.get("DT_DQL_TO", "now")
INTERVAL = os.environ.get("DT_DQL_INTERVAL", "1m")
LIMIT = os.environ.get("DT_DQL_LIMIT", "1000").strip()
OUTPUT_FORMAT = os.environ.get("DT_DQL_FORMAT", "both").strip()

# Topology snapshots are point-in-time, but a Grail entity query needs a
# non-empty timeframe: each snapshot queries a short window (this many minutes)
# anchored at its timestamp — the scenario start for "init", teardown for "stop".
TOPOLOGY_WINDOW_MIN = int(os.environ.get("DT_TOPOLOGY_WINDOW_MIN", "5"))

# All records are written into the recorder PVC (~/records), matching the
# convention used by the jaeger/prometheus recorders.
OUTDIR = os.path.join(os.path.expanduser("~"), "records")

# ── Kubernetes metric catalog ────────────────────────────────────────────────
# Each entry: (metric_key, aggregation, grouping). These are queried ONE AT A
# TIME and merged into a single output file (see the "k8s-metrics" dataset).
# Querying individually — rather than one combined `timeseries {a, b, c}` — is
# deliberate: in a combined block a single metric with no data collapses the
# whole result to 0 rows. Per-metric queries keep every populated metric.
#
# grouping "pod"       -> by:{k8s.pod.name, k8s.namespace.name}
# grouping "container" -> by:{k8s.pod.name, k8s.container.name, k8s.namespace.name}
K8S_METRICS = [
    # Pod network
    ("dt.kubernetes.pod.network_received_data", "sum", "pod"),
    ("dt.kubernetes.pod.network_received_errors", "sum", "pod"),
    ("dt.kubernetes.pod.network_received_packets_dropped", "sum", "pod"),
    ("dt.kubernetes.pod.network_transmitted_data", "sum", "pod"),
    ("dt.kubernetes.pod.network_transmitted_errors", "sum", "pod"),
    ("dt.kubernetes.pod.network_transmitted_packets_dropped", "sum", "pod"),
    # Pod status
    ("dt.kubernetes.pod.containers_desired", "max", "pod"),
    ("dt.kubernetes.pod.restarts", "max", "pod"),
    # Container resources
    ("dt.kubernetes.container.requests_cpu", "max", "container"),
    ("dt.kubernetes.container.limits_cpu", "max", "container"),
    ("dt.kubernetes.container.requests_memory", "max", "container"),
    ("dt.kubernetes.container.limits_memory", "max", "container"),
    ("dt.kubernetes.container.cpu_usage", "avg", "container"),
    ("dt.kubernetes.container.memory_working_set", "avg", "container"),
]
K8S_GROUP_BY = {
    "pod": "k8s.pod.name, k8s.namespace.name",
    "container": "k8s.pod.name, k8s.container.name, k8s.namespace.name",
}

# ── Dataset registry ─────────────────────────────────────────────────────────
# Each dataset maps to an output file stem. A timestamp is appended at write
# time so a run produces e.g. dynatrace_logs_2026-07-30T12-00-00.000000.json.
DATASETS = {
    "responsetime":      {"stem": "dynatrace_responsetime"},
    "errorrate":         {"stem": "dynatrace_errorrate"},
    "span-responsetime": {"stem": "dynatrace_span_responsetime"},
    "span-errorrate":    {"stem": "dynatrace_span_errorrate"},
    "logs":              {"stem": "dynatrace_logs"},
    "events":            {"stem": "dynatrace_events"},
    "traces":            {"stem": "dynatrace_traces"},
    "problems":          {"stem": "dynatrace_problems"},
    # Special: runs every K8S_METRICS key and merges them into one file.
    "k8s-metrics":       {"stem": "dynatrace_k8s_metrics", "multi": True},
    # Special: Smartscape topology (service graph + infra edges) for the ns.
    # Captured as two point-in-time snapshots (see export_topology): "init" at
    # the scenario start time and "stop" at teardown.
    "topology":          {"stem": "dynatrace_topology", "topology": True},
}
# The recorder always exports the full set (metrics, spans, traces, logs,
# events, problems, k8s, topology).
ALL_DATASETS = [
    "responsetime", "errorrate", "span-responsetime", "span-errorrate",
    "logs", "events", "traces", "problems", "k8s-metrics", "topology",
]
# ─────────────────────────────────────────────────────────────────────────────


def build_session():
    retries = Retry(total=3, backoff_factor=0.3)
    adapter = HTTPAdapter(max_retries=retries)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def validate_config():
    missing = [
        name
        for name, val in [
            ("DT_PLATFORM_TOKEN", PLATFORM_TOKEN),
            ("DT_PLATFORM_URL", PLATFORM_URL),
        ]
        if not val
    ]
    if missing:
        sys.exit(
            "error: missing required environment variable(s): {0}".format(
                ", ".join(missing)
            )
        )


def build_dql(dataset, namespace, interval, limit):
    """Return the DQL for a dataset, scoped to the namespace.

    logs/events fetch RAW rows (no projection) so the output keeps every field.
    The metric/span datasets aggregate, which is intrinsic to the measurement.
    """
    ns_filter = f'filter: {{ k8s.namespace.name == "{namespace}" }}'
    if dataset == "errorrate":
        return (
            "timeseries {"
            "  total  = sum(dt.service.request.count),"
            "  failed = sum(dt.service.request.failure_count)"
            f" }}, by:{{dt.entity.service}}, {ns_filter}, interval:{interval}"
            "| fieldsAdd error_rate = if(arraySum(total) > 100,"
            " (failed[] / total[]) * 100, else: 0)"
        )
    if dataset == "responsetime":
        return (
            "timeseries responsetime = avg(dt.service.request.response_time),"
            f" by:{{dt.entity.service}}, {ns_filter}, interval:{interval}"
        )
    if dataset == "span-responsetime":
        return (
            f'fetch spans | filter k8s.namespace.name == "{namespace}"'
            " and request.is_root_span == true"
            f" | makeTimeseries rt_ns = avg(duration), by:{{service.name}},"
            f" interval:{interval}"
            " | fieldsAdd responsetime_ms = rt_ns[] / 1000000.0"
        )
    if dataset == "span-errorrate":
        return (
            f'fetch spans | filter k8s.namespace.name == "{namespace}"'
            " and request.is_root_span == true"
            " | fieldsAdd failed_num = if(request.is_failed == true, 1, else: 0)"
            f" | makeTimeseries err = avg(failed_num), by:{{service.name}},"
            f" interval:{interval}"
            " | fieldsAdd error_rate = err[] * 100.0"
        )
    if dataset == "logs":
        return (
            f'fetch logs | filter k8s.namespace.name == "{namespace}"'
            f" | sort timestamp desc | limit {limit}"
        )
    if dataset == "events":
        return (
            f'fetch events | filter k8s.namespace.name == "{namespace}"'
            f" | sort timestamp desc | limit {limit}"
        )
    if dataset == "traces":
        # Raw spans (distributed traces); no projection so the output keeps every
        # span attribute. Sorted newest-first by span start_time.
        return (
            f'fetch spans | filter k8s.namespace.name == "{namespace}"'
            f" | sort start_time desc | limit {limit}"
        )
    if dataset == "problems":
        # Davis problems; no projection so the output keeps every field. Scoped to
        # the namespace via the record's k8s.namespace.name ARRAY field (resolved
        # from affected entities): in(<ns>, k8s.namespace.name). Duplicates dropped.
        return (
            "fetch dt.davis.problems | filter not(dt.davis.is_duplicate)"
            f' and in("{namespace}", k8s.namespace.name)'
            f" | sort event.start desc | limit {limit}"
        )
    raise ValueError(f"Unknown dataset '{dataset}'")


def build_metric_dql(metric_key, agg, grouping, namespace, interval):
    """DQL for a single k8s metric timeseries, scoped to the namespace."""
    by = K8S_GROUP_BY[grouping]
    return (
        f"timeseries value = {agg}({metric_key}), by:{{{by}}},"
        f' filter:{{ k8s.namespace.name == "{namespace}" }}, interval:{interval}'
    )


def to_iso(value):
    """Convert `now` / `now-<N><m|h|d>` to ISO-8601 UTC (Grail rejects relative
    strings in defaultTimeframeStart/End). ISO input is passed through, so a
    scenario-start timestamp supplied via DT_DQL_FROM works directly."""
    value = value.strip()
    now = datetime.now(timezone.utc)
    if value == "now":
        dt = now
    else:
        m = re.fullmatch(r"now-(\d+)([mhd])", value)
        if not m:
            return value
        n, unit = int(m.group(1)), m.group(2)
        delta = {"m": "minutes", "h": "hours", "d": "days"}[unit]
        dt = now - timedelta(**{delta: n})
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _raise_with_body(resp):
    """raise_for_status but surface the API error body (Grail puts the reason —
    INVALID_TIMEFRAME, token/permission errors — in the JSON)."""
    if resp.status_code >= 400:
        try:
            detail = resp.json()
        except ValueError:
            detail = resp.text
        logger.warning("HTTP %s from %s\n%s", resp.status_code, resp.url, detail)
        resp.raise_for_status()


def run_query(session, dql, time_from, time_to):
    """Execute DQL with the platform token; poll until the query completes.
    Returns the full `result` object (records + metadata)."""
    headers = {
        "Authorization": "Bearer {0}".format(PLATFORM_TOKEN),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    exec_resp = session.post(
        "{0}/platform/storage/query/v1/query:execute".format(PLATFORM_URL),
        headers=headers,
        json={"query": dql, "defaultTimeframeStart": to_iso(time_from),
              "defaultTimeframeEnd": to_iso(time_to)},
        timeout=60,
    )
    _raise_with_body(exec_resp)
    body = exec_resp.json()

    if body.get("state") == "SUCCEEDED" and "result" in body:
        return body["result"]

    request_token = body["requestToken"]
    poll_url = "{0}/platform/storage/query/v1/query:poll".format(PLATFORM_URL)
    while True:
        poll = session.get(
            poll_url, headers=headers,
            params={"request-token": request_token}, timeout=60,
        )
        _raise_with_body(poll)
        pbody = poll.json()
        state = pbody.get("state")
        if state == "SUCCEEDED":
            return pbody["result"]
        if state in ("FAILED", "CANCELLED"):
            raise RuntimeError("Query {0}: {1}".format(state, pbody))
        time.sleep(2)


def grail_notifications(result):
    return [
        n.get("message", "")
        for n in result.get("metadata", {}).get("grail", {}).get("notifications", [])
        if n.get("message")
    ]


# ── CSV flattening ───────────────────────────────────────────────────────────
def _parse_iso(s):
    """Parse Grail ISO-8601 (nanosecond precision) into a UTC datetime."""
    m = re.match(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(?:\.(\d+))?", s)
    base = datetime.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S")
    if m.group(2):
        base = base.replace(microsecond=int(m.group(2)[:6].ljust(6, "0")))
    return base.replace(tzinfo=timezone.utc)


def _series_timestamps(rec, n):
    """Per-bucket timestamps for a timeseries record: use explicit timestamps[]
    if present, else derive from timeframe.start + interval."""
    tf = rec.get("timeframe", {}) or {}
    if tf.get("timestamps"):
        return tf["timestamps"]
    start, interval_ns = tf.get("start"), rec.get("interval")
    if start and interval_ns:
        base = _parse_iso(start)
        step = timedelta(microseconds=int(interval_ns) / 1000)
        return [(base + i * step).strftime("%Y-%m-%dT%H:%M:%S.000Z")
                for i in range(n)]
    return list(range(n))


def flatten_result(result, extra=None):
    """Flatten a Grail result into a list of flat dict rows for CSV.

    - Flat records (logs/events): one row per record, scalar fields as-is.
    - Timeseries records (value arrays + timeframe/interval): expanded to one
      row per bucket with a reconstructed `timestamp` column.
    `extra` adds constant columns to every row (e.g. the metric key)."""
    rows = []
    extra = extra or {}
    for rec in result.get("records", []):
        array_fields = {k: v for k, v in rec.items()
                        if isinstance(v, list) and k != "timestamps"}
        scalar_fields = {k: v for k, v in rec.items()
                         if k not in array_fields and k not in
                         ("timeframe", "interval")}

        if array_fields:
            length = max((len(v) for v in array_fields.values()), default=0)
            timestamps = _series_timestamps(rec, length)
            for i in range(length):
                if all(v[i] is None for v in array_fields.values()
                       if i < len(v)):
                    continue  # skip buckets where every series is null
                row = dict(extra)
                row["timestamp"] = timestamps[i] if i < len(timestamps) else i
                row.update(scalar_fields)
                for k, v in array_fields.items():
                    row[k] = v[i] if i < len(v) else None
                rows.append(row)
        else:
            row = dict(extra)
            row.update(scalar_fields)
            rows.append(row)
    return rows


def write_csv_rows(rows, path):
    """Write flat dict rows to CSV; columns = union of keys across rows."""
    columns = []
    for r in rows:
        for k in r:
            if k not in columns:
                columns.append(k)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)
    return len(rows)


def out_paths(dataset, timestamp):
    """(json_path, csv_path) for a dataset, with the run timestamp appended."""
    stem = "{0}_{1}".format(DATASETS[dataset]["stem"], timestamp)
    base = os.path.join(OUTDIR, stem)
    return base + ".json", base + ".csv"


def _shift_iso(iso, minutes):
    """Shift an ISO-8601 UTC timestamp by a number of minutes (may be negative)."""
    shifted = _parse_iso(iso) + timedelta(minutes=minutes)
    return shifted.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _resolve_namespace_entity(session, namespace, time_from, time_to):
    """Look up the CLOUD_APPLICATION_NAMESPACE entity id for a k8s namespace
    name. Smartscape scopes services by their `belongs_to` relationship to this
    entity — so we need its id to filter the topology to one namespace."""
    dql = (
        "fetch dt.entity.cloud_application_namespace"
        f' | filter entity.name == "{namespace}"'
        " | fields id, entity.name"
    )
    recs = run_query(session, dql, time_from, time_to).get("records", [])
    return recs[0]["id"] if recs else None


def _topology_snapshot(session, ns_id, time_from, time_to):
    """One point-in-time Smartscape snapshot over [time_from, time_to].

    Fetch every service that `belongs_to` the namespace along with its
    relationship columns, then derive directed edges: service->service `calls`,
    and service->host / service->process_group `runs_on`. Returns
    (dql, services, nodes, edges)."""
    dql = (
        "fetch dt.entity.service"
        " | fieldsAdd ns = belongs_to[dt.entity.cloud_application_namespace]"
        f' | filter in("{ns_id}", ns)'
        " | fields id, entity.name,"
        " calls[dt.entity.service],"
        " runs_on[dt.entity.host],"
        " runs_on[dt.entity.process_group]"
    )
    result = run_query(session, dql, time_from, time_to)
    for msg in grail_notifications(result):
        logger.info("[topology] Grail notice: %s", msg)

    services = result.get("records", [])
    # Set of in-namespace service ids: we keep call edges to any service, but
    # tag whether the callee is inside the namespace (target_in_namespace).
    ns_service_ids = {s.get("id") for s in services}
    # id -> service name, so the edge list is readable without a separate join.
    names = {s.get("id"): s.get("entity.name") for s in services}

    nodes, edges = [], []
    for svc in services:
        sid = svc.get("id")
        sname = svc.get("entity.name")
        nodes.append({"id": sid, "name": sname, "type": "SERVICE"})
        # service -> service call edges
        for tgt in (svc.get("calls[dt.entity.service]") or []):
            edges.append({"source": sid, "source_name": sname,
                          "target": tgt, "target_name": names.get(tgt, ""),
                          "type": "CALLS",
                          "target_in_namespace": tgt in ns_service_ids})
        # service -> host / process_group placement edges (targets are infra
        # entities outside the service set, so no name is resolved here)
        for host in (svc.get("runs_on[dt.entity.host]") or []):
            edges.append({"source": sid, "source_name": sname, "target": host,
                          "target_name": "", "type": "RUNS_ON_HOST"})
        for pg in (svc.get("runs_on[dt.entity.process_group]") or []):
            edges.append({"source": sid, "source_name": sname, "target": pg,
                          "target_name": "", "type": "RUNS_ON_PROCESS_GROUP"})
    return dql, services, nodes, edges


def export_topology(session, dataset, timestamp):
    """Export the Smartscape topology as TWO point-in-time snapshots:

      * init  — anchored at the scenario start time (DT_DQL_FROM)
      * stop  — anchored at teardown (DT_DQL_TO)

    Each snapshot queries a short window around its anchor (an entity query
    needs a non-empty timeframe) and is written to its own files, e.g.
    dynatrace_topology_init_<ts>.json / dynatrace_topology_stop_<ts>.json.
    Mirrors dynatrace_scripts/pull_dql_json.py's export_topology graph shape."""
    # Resolve each snapshot's [from, to] window around its anchor timestamp.
    init_from = to_iso(TIME_FROM)
    init_to = _shift_iso(init_from, TOPOLOGY_WINDOW_MIN)
    stop_to = to_iso(TIME_TO)
    stop_from = _shift_iso(stop_to, -TOPOLOGY_WINDOW_MIN)
    snapshots = [
        ("init", init_from, init_to),
        ("stop", stop_from, stop_to),
    ]

    any_data = False
    for phase, snap_from, snap_to in snapshots:
        stem = "{0}_{1}_{2}".format(DATASETS[dataset]["stem"], phase, timestamp)
        base = os.path.join(OUTDIR, stem)
        json_path, csv_path = base + ".json", base + ".csv"

        try:
            ns_id = _resolve_namespace_entity(session, NAMESPACE,
                                              snap_from, snap_to)
            if not ns_id:
                logger.warning("[topology/%s] no namespace entity for '%s'",
                               phase, NAMESPACE)
                continue
            dql, services, nodes, edges = _topology_snapshot(
                session, ns_id, snap_from, snap_to)
        except Exception as exc:
            logger.warning("[topology/%s] ERROR: %s", phase, exc)
            continue

        written = []
        if OUTPUT_FORMAT in ("json", "both"):
            payload = {
                "dataset": dataset,
                "phase": phase,
                "namespace": NAMESPACE,
                "namespace_entity_id": ns_id,
                "timeframe": {"from": snap_from, "to": snap_to},
                "query": dql,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "graph": {"nodes": nodes, "edges": edges},
                "services": services,  # raw records, all relationship columns
            }
            with open(json_path, "w") as f:
                json.dump(payload, f, indent=2)
            written.append(json_path)

        if OUTPUT_FORMAT in ("csv", "both"):
            # Flatten to an edge list — the natural tabular view of a graph.
            write_csv_rows(edges, csv_path)
            written.append(csv_path)

        logger.info("[topology/%s] %d services, %d edges -> %s",
                    phase, len(nodes), len(edges), ", ".join(written))
        any_data = any_data or bool(nodes)

    return any_data


def export_k8s_metrics(session, dataset, timestamp):
    """Query every K8S_METRICS key individually and merge them into ONE file —
    so a single run exports many metrics together. Each metric is a separate
    query (a combined `timeseries {..}` would zero out if any one metric had no
    data), and each metric's full result is kept under its key."""
    json_path, csv_path = out_paths(dataset, timestamp)
    metrics_out = []
    ok = 0
    for metric_key, agg, grouping in K8S_METRICS:
        entry = {"metric": metric_key, "aggregation": agg, "grouping": grouping}
        dql = build_metric_dql(metric_key, agg, grouping, NAMESPACE, INTERVAL)
        try:
            result = run_query(session, dql, TIME_FROM, TIME_TO)
        except Exception as exc:
            logger.warning("[%s] %s: ERROR: %s", dataset, metric_key, exc)
            entry.update(query=dql, error=str(exc), record_count=0, result=None)
            metrics_out.append(entry)
            continue

        for msg in grail_notifications(result):
            logger.info("[%s] %s: Grail notice: %s", dataset, metric_key, msg)
        n = len(result.get("records", []))
        if n:
            ok += 1
        logger.info("[%s] %s: %d records", dataset, metric_key, n)
        entry.update(query=dql, record_count=n, result=result)
        metrics_out.append(entry)

    written = []

    if OUTPUT_FORMAT in ("json", "both"):
        payload = {
            "dataset": dataset,
            "namespace": NAMESPACE,
            "timeframe": {"from": TIME_FROM, "to": TIME_TO},
            "interval": INTERVAL,
            "metric_count": len(metrics_out),
            "metrics_with_data": ok,
            "metrics": metrics_out,
        }
        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)
        written.append(json_path)

    if OUTPUT_FORMAT in ("csv", "both"):
        # Merge every metric into one CSV, tagging each row with its metric key.
        rows = []
        for entry in metrics_out:
            if entry.get("result"):
                rows.extend(flatten_result(entry["result"],
                                           extra={"metric": entry["metric"]}))
        write_csv_rows(rows, csv_path)
        written.append(csv_path)

    logger.info("[%s] wrote %d metrics (%d with data) -> %s",
                dataset, len(metrics_out), ok, ", ".join(written))
    return ok > 0


def export_dataset(session, dataset, timestamp):
    """Run one dataset and write its output. Returns True if it produced data.
    Never raises — failures are captured so a multi-dataset run continues."""
    if DATASETS[dataset].get("multi"):
        return export_k8s_metrics(session, dataset, timestamp)
    if DATASETS[dataset].get("topology"):
        return export_topology(session, dataset, timestamp)

    json_path, csv_path = out_paths(dataset, timestamp)
    try:
        dql = build_dql(dataset, NAMESPACE, INTERVAL, LIMIT)
        logger.info("[%s] %s", dataset, dql)
        result = run_query(session, dql, TIME_FROM, TIME_TO)
    except Exception as exc:
        logger.warning("[%s] ERROR: %s", dataset, exc)
        return False

    for msg in grail_notifications(result):
        logger.info("[%s] Grail notice: %s", dataset, msg)

    records = result.get("records", [])
    written = []

    if OUTPUT_FORMAT in ("json", "both"):
        # Persist the full response verbatim: query context + records + metadata.
        payload = {
            "dataset": dataset,
            "query": dql,
            "timeframe": {"from": TIME_FROM, "to": TIME_TO},
            "record_count": len(records),
            "result": result,
        }
        with open(json_path, "w") as f:
            json.dump(payload, f, indent=2)
        written.append(json_path)

    if OUTPUT_FORMAT in ("csv", "both"):
        rows = flatten_result(result)
        write_csv_rows(rows, csv_path)
        written.append(csv_path)

    logger.info("[%s] wrote %d records -> %s",
                dataset, len(records), ", ".join(written))
    return len(records) > 0


def main():
    validate_config()

    if OUTPUT_FORMAT not in ("json", "csv", "both"):
        sys.exit("error: DT_DQL_FORMAT must be one of json, csv, both")

    os.makedirs(OUTDIR, exist_ok=True)
    session = build_session()

    timestamp = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H-%M-%S.%f')
    logger.info("Datasets: %s  |  namespace=%s  |  %s -> %s  |  format=%s",
                ", ".join(ALL_DATASETS), NAMESPACE, TIME_FROM, TIME_TO,
                OUTPUT_FORMAT)

    results = [export_dataset(session, ds, timestamp) for ds in ALL_DATASETS]

    if not any(results):
        logger.warning("no datasets returned any records")


if __name__ == "__main__":
    main()
