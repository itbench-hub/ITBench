"""ClickHouse Event Streamer for OpenTelemetry and Kubernetes data.

This module provides a client for querying ClickHouse databases containing
OpenTelemetry traces, logs, metrics, and Kubernetes events/objects.
"""

import json
import logging
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import clickhouse_connect
import pandas as pd

logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

logger = logging.getLogger(__name__)


class ClickHouseEventStreamer:
    """Client for streaming and querying OpenTelemetry and Kubernetes data from ClickHouse.

    This class provides methods to query events, logs, traces, metrics, and Kubernetes
    objects from ClickHouse databases and save them to TSV files.

    Attributes:
        default_client: ClickHouse client for the default database.
        prometheus_client: ClickHouse client for the prometheus database.
        records_dir: Directory path where query results are saved.
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 8123,
        username: str = "default",
        password: str = "",
        secure: bool = False,
        verify: bool = True,
        proxy_path: Optional[str] = None,
    ):
        """Initialize ClickHouse clients and setup records directory.

        Args:
            host: ClickHouse server hostname.
            port: ClickHouse server port.
            username: Username for authentication.
            password: Password for authentication.
            secure: Whether to use HTTPS connection.
            verify: Whether to verify SSL certificates.
            proxy_path: Optional proxy path for connection.
        """
        base_settings = {
            "host": host,
            "port": port,
            "username": username,
            "password": password,
            "secure": secure,
            "verify": verify,
        }

        if proxy_path:
            base_settings["proxy_path"] = proxy_path

        self.default_client = clickhouse_connect.get_client(
            database="default", **base_settings
        )

        self.prometheus_client = clickhouse_connect.get_client(
            database="prometheus", **base_settings
        )

        self.records_dir = os.path.join(os.path.expanduser("~"), "records")
        os.makedirs(self.records_dir, exist_ok=True)

        self._metric_table_ids = None

    def _get_metric_table_ids(self) -> Dict[str, Optional[str]]:
        """Discover and cache metric table IDs from ClickHouse system tables.

        Returns:
            Dictionary mapping table types ('data', 'tags', 'metrics') to table names.
        """
        if self._metric_table_ids is None:
            self._metric_table_ids = {"data": None, "tags": None, "metrics": None}

            try:
                df = self.prometheus_client.query_df(
                    """
                    SELECT name
                    FROM system.tables
                    WHERE database = 'prometheus'
                    AND name LIKE '.inner_id%'
                """
                )

                if df.empty or "name" not in df.columns:
                    logger.warning("No prometheus metric tables found")
                    return self._metric_table_ids

                for table_name in df["name"]:
                    if ".inner_id.data." in table_name:
                        self._metric_table_ids["data"] = table_name
                    elif ".inner_id.tags." in table_name:
                        self._metric_table_ids["tags"] = table_name
                    elif ".inner_id.metrics." in table_name:
                        self._metric_table_ids["metrics"] = table_name

                logger.info(f"Found metric tables: {self._metric_table_ids}")

            except Exception as e:
                logger.warning(f"Could not discover prometheus metric tables: {e}")

        return self._metric_table_ids

    def _save_to_records(
        self,
        data: pd.DataFrame,
        prefix: str,
        subdir: Optional[str] = None,
        raw: bool = False,
    ) -> str:
        """Save DataFrame to TSV file in records directory.

        Args:
            data: DataFrame to save.
            prefix: Filename prefix for the saved file.
            subdir: Optional subdirectory within records_dir.
            raw: If True, save under 'raw/' base directory; otherwise under 'lite/'.

        Returns:
            Path to the saved file.
        """
        # Determine base directory
        base_dir = "raw" if raw else "lite"

        if subdir:
            save_dir = os.path.join(self.records_dir, base_dir, subdir)
        else:
            save_dir = os.path.join(self.records_dir, base_dir)

        os.makedirs(save_dir, exist_ok=True)
        file_path = os.path.join(save_dir, f"{prefix}.tsv")

        data.to_csv(file_path, sep="\t", index=False)
        logger.info(f"Saved {len(data)} records to: {file_path}")
        return file_path

    def query_df_batched(
        self,
        query: str,
        batch_size: int = 10000,
        client: Optional[clickhouse_connect.driver.Client] = None,
    ) -> pd.DataFrame:
        """Execute query in batches to handle large result sets.

        This method automatically fetches query results in manageable batches
        to prevent memory issues when dealing with large datasets. It fetches
        all available data by default.

        Args:
            query: SQL query to execute.
            batch_size: Number of rows to fetch per batch. Default is 10,000.
            client: ClickHouse client to use (defaults to default_client).

        Returns:
            Combined DataFrame containing all batched results.

        Note:
            To limit the number of rows returned, use SQL LIMIT in your query:
            Example: query_df_batched("SELECT * FROM table LIMIT 50000")
        """
        if client is None:
            client = self.default_client

        from_match = re.search(r"FROM\s+(\S+)", query, re.IGNORECASE)
        if not from_match:
            return client.query_df(query)
        table_name = from_match.group(1)

        where_match = re.search(
            r"WHERE\s+(.*?)(?:ORDER|GROUP|LIMIT|$)", query, re.IGNORECASE | re.DOTALL
        )
        where_clause = f"WHERE {where_match.group(1)}" if where_match else ""

        count_query = f"SELECT COUNT(*) as count FROM {table_name} {where_clause}"
        try:
            count_df = client.query_df(count_query)
            total_count = int(count_df["count"].iloc[0]) if not count_df.empty else 0
        except Exception as e:
            logger.warning(f"Could not get count, running query directly: {e}")
            return client.query_df(query)

        if total_count == 0:
            return pd.DataFrame()

        logger.info(f"Total records: {total_count:,}")

        if total_count <= batch_size:
            return client.query_df(query)

        # Remove existing LIMIT/OFFSET if any
        base_query = re.sub(r"\s+(LIMIT|OFFSET)\s+\d+", "", query, flags=re.IGNORECASE)

        # Fetch in batches
        all_dfs = []
        offset = 0
        batch_num = 0

        while True:
            batch_query = f"{base_query} LIMIT {batch_size} OFFSET {offset}"

            logger.debug(f"Fetching batch {batch_num + 1} (offset: {offset:,})...")
            try:
                batch_df = client.query_df(batch_query)

                # Stop if no more data
                if batch_df.empty:
                    logger.debug("Empty batch received, stopping")
                    break

                logger.debug(f"Fetched {len(batch_df):,} rows")
                all_dfs.append(batch_df)
                offset += batch_size
                batch_num += 1

                # Stop if we received fewer rows than requested (reached end)
                if len(batch_df) < batch_size:
                    logger.debug("Partial batch received, all data fetched")
                    break

            except Exception as e:
                logger.error(f"Error in batch {batch_num + 1}: {e}")
                break

        if not all_dfs:
            return pd.DataFrame()

        logger.info(f"Successfully fetched {batch_num} batches")
        return pd.concat(all_dfs, ignore_index=True)

    def get_events_df(
        self,
        namespaces: List[str] = None,
        save_to_file: bool = True,
        transform: bool = False,
    ) -> pd.DataFrame:
        """Retrieve Kubernetes events from ClickHouse.

        Args:
            namespaces: List of Kubernetes namespaces to filter by.
            save_to_file: Whether to save results to TSV file.
            transform: If True, apply transformations (parse JSON, extract fields).
                      If False (default), export all columns as-is.

        Returns:
            DataFrame containing Kubernetes events.
        """
        if transform:
            query = """
            SELECT
                Timestamp as timestamp,
                Body as body,
                ResourceAttributes['k8s.namespace.name'] as namespace
            FROM kubernetes_events
            WHERE 1=1
            """
        else:
            query = """
            SELECT *
            FROM kubernetes_events
            WHERE 1=1
            """

        if namespaces:
            query += " AND ResourceAttributes['k8s.namespace.name'] IN ({})".format(
                ",".join(f"'{ns}'" for ns in namespaces)
            )

        query += " ORDER BY Timestamp ASC"

        df = self.query_df_batched(query)

        if transform and len(df) > 0:
            try:
                df["event_json"] = df["body"].apply(
                    lambda x: json.loads(x) if x else {}
                )
                df["event_type"] = df["event_json"].apply(lambda x: x.get("type", ""))

                df["reason"] = df["event_json"].apply(
                    lambda x: x.get("object", {}).get("reason", "")
                )
                df["message"] = df["event_json"].apply(
                    lambda x: x.get("object", {}).get("message", "")
                )
                df["event_time"] = df["event_json"].apply(
                    lambda x: x.get("object", {}).get("lastTimestamp", "")
                )
                df["event_count"] = df["event_json"].apply(
                    lambda x: x.get("object", {}).get("count", 1)
                )
                df["event_kind"] = df["event_json"].apply(
                    lambda x: x.get("object", {}).get("type", "")
                )

                df["object_kind"] = df["event_json"].apply(
                    lambda x: x.get("object", {})
                    .get("involvedObject", {})
                    .get("kind", "")
                )
                df["object_name"] = df["event_json"].apply(
                    lambda x: x.get("object", {})
                    .get("involvedObject", {})
                    .get("name", "")
                )
                df["object_namespace"] = df["event_json"].apply(
                    lambda x: x.get("object", {})
                    .get("involvedObject", {})
                    .get("namespace", "")
                )

                df["source_component"] = df["event_json"].apply(
                    lambda x: x.get("object", {}).get("source", {}).get("component", "")
                )

                df = df.drop(columns=["body", "event_json"])

            except Exception as e:
                logger.error(f"Could not parse event body: {e}")

        logger.info(f"Total events loaded: {len(df)}")

        if save_to_file and len(df) > 0:
            prefix = (
                f"k8s_events_{'_'.join(namespaces)}" if namespaces else "k8s_events"
            )
            if not transform:
                prefix += "_raw"
            self._save_to_records(df, prefix, raw=not transform)

        return df

    def get_k8s_objects_df(
        self,
        namespaces: Optional[List[str]] = None,
        resource_types: Optional[List[str]] = None,
        save_to_file: bool = True,
        transform: bool = False,
    ) -> pd.DataFrame:
        """Retrieve Kubernetes object snapshots from ClickHouse.

        Args:
            namespaces: List of Kubernetes namespaces to filter by.
            resource_types: List of Kubernetes resource types to filter by.
            save_to_file: Whether to save results to TSV file.
            transform: If True, apply transformations (parse JSON, extract fields).
                      If False (default), export all columns as-is.

        Returns:
            DataFrame containing Kubernetes object snapshots.
        """
        if transform:
            query = """
            SELECT
                Timestamp as timestamp,
                Body as body,
                ResourceAttributes['k8s.namespace.name'] as namespace,
                LogAttributes['k8s.resource.name'] as resource_type
            FROM kubernetes_objects_snapshot
            WHERE 1=1
            """
        else:
            query = """
            SELECT *
            FROM kubernetes_objects_snapshot
            WHERE 1=1
            """

        if namespaces:
            query += " AND ResourceAttributes['k8s.namespace.name'] IN ({})".format(
                ",".join(f"'{ns}'" for ns in namespaces)
            )

        if resource_types:
            query += " AND LogAttributes['k8s.resource.name'] IN ({})".format(
                ",".join(f"'{rt}'" for rt in resource_types)
            )

        query += " ORDER BY Timestamp ASC"

        df = self.query_df_batched(query)

        if transform and len(df) > 0:
            df["object_json"] = df["body"].apply(lambda x: json.loads(x) if x else {})
            df["object_kind"] = df["object_json"].apply(lambda x: x.get("kind", ""))
            df["object_name"] = df["object_json"].apply(
                lambda x: x.get("metadata", {}).get("name", "")
            )
            df["api_version"] = df["object_json"].apply(
                lambda x: x.get("apiVersion", "")
            )

            df = df.drop(columns=["object_json"])

        logger.info(f"Total K8s objects loaded: {len(df)}")

        if save_to_file and len(df) > 0:
            prefix_parts = ["k8s_objects"]
            if namespaces:
                prefix_parts.append("_".join(namespaces))
            if resource_types:
                prefix_parts.append("_".join(resource_types))
            prefix = "_".join(prefix_parts)
            if not transform:
                prefix += "_raw"
            self._save_to_records(df, prefix, raw=not transform)

        return df

    def get_logs_df(
        self,
        services: Optional[List[str]] = None,
        severity_levels: Optional[List[str]] = None,
        save_to_file: bool = True,
        transform: bool = False,
    ) -> pd.DataFrame:
        """Retrieve OpenTelemetry logs from ClickHouse.

        Args:
            services: List of service names to filter by.
            severity_levels: List of severity levels to filter by.
            save_to_file: Whether to save results to TSV file.
            transform: If True, apply transformations (extract fields, clean data).
                      If False (default), export all columns as-is.

        Returns:
            DataFrame containing OpenTelemetry logs.
        """
        if transform:
            query = """
            SELECT
                Timestamp as timestamp,
                TraceId as trace_id,
                SpanId as span_id,
                TraceFlags as trace_flags,
                SeverityText as severity_text,
                SeverityNumber as severity_number,
                ServiceName as service_name,
                Body as body,
                ResourceAttributes as resource_attributes,
                LogAttributes as log_attributes
            FROM otel_demo_logs
            WHERE 1=1
            """
        else:
            query = """
            SELECT *
            FROM otel_demo_logs
            WHERE 1=1
            """

        if services:
            query += " AND ServiceName IN ({})".format(
                ",".join(f"'{s}'" for s in services)
            )

        if severity_levels:
            # 1-4: TRACE, 5-8: DEBUG, 9-12: INFO, 13-16: WARN, 17-20: ERROR, 21-24: FATAL
            if any(
                level.lower() in ["warning", "warn", "error", "fatal", "critical"]
                for level in severity_levels
            ):
                query += " AND (SeverityText IN ({}) OR SeverityNumber >= 13)".format(
                    ",".join(f"'{s}'" for s in severity_levels)
                )
            else:
                query += " AND SeverityText IN ({})".format(
                    ",".join(f"'{s}'" for s in severity_levels)
                )

        query += " ORDER BY Timestamp ASC"

        df = self.query_df_batched(query)

        if transform and len(df) > 0:
            if (df["severity_text"] == "").all():
                df = df.drop(columns=["severity_text"])
            if (df["severity_number"] == 0).all():
                df = df.drop(columns=["severity_number"])

            df["body"] = df["body"].str.replace("\n", " ", regex=False)

            df["k8s_namespace"] = df["resource_attributes"].apply(
                lambda x: x.get("k8s.namespace.name", "") if isinstance(x, dict) else ""
            )
            df["k8s_pod_name"] = df["resource_attributes"].apply(
                lambda x: x.get("k8s.pod.name", "") if isinstance(x, dict) else ""
            )
            df["url_path"] = df["log_attributes"].apply(
                lambda x: x.get("url.path", "") if isinstance(x, dict) else ""
            )

            df = df.drop(columns=["resource_attributes", "log_attributes"])

        logger.info(f"Total logs loaded: {len(df)}")

        if save_to_file and len(df) > 0:
            prefix = "otel_logs"
            if services:
                prefix += f"_{'_'.join(services)}"
            if severity_levels:
                prefix += f"_{'_'.join(severity_levels)}"
            if not transform:
                prefix += "_raw"
            self._save_to_records(df, prefix, raw=not transform)

        return df

    def get_traces_df(
        self,
        services: Optional[List[str]] = None,
        trace_ids: Optional[List[str]] = None,
        span_kinds: Optional[List[str]] = None,
        status_codes: Optional[List[str]] = None,
        min_duration_ms: Optional[int] = None,
        save_to_file: bool = True,
        transform: bool = False,
    ) -> pd.DataFrame:
        """Retrieve OpenTelemetry traces from ClickHouse.

        Args:
            services: List of service names to filter by.
            trace_ids: List of specific trace IDs to retrieve.
            span_kinds: List of span kinds to filter by.
            status_codes: List of status codes to filter by.
            min_duration_ms: Minimum span duration in milliseconds.
            save_to_file: Whether to save results to TSV file.
            transform: If True, apply transformations (convert duration to ms).
                      If False (default), export all columns as-is.

        Returns:
            DataFrame containing OpenTelemetry traces.
        """
        if transform:
            query = """
            SELECT
                Timestamp as timestamp,
                TraceId as trace_id,
                SpanId as span_id,
                ParentSpanId as parent_span_id,
                TraceState as trace_state,
                SpanName as span_name,
                SpanKind as span_kind,
                ServiceName as service_name,
                ScopeName as scope_name,
                ScopeVersion as scope_version,
                Duration as duration,
                StatusCode as status_code,
                StatusMessage as status_message
            FROM otel_demo_traces
            WHERE 1=1
            """
        else:
            query = """
            SELECT *
            FROM otel_demo_traces
            WHERE 1=1
            """

        if services:
            query += " AND ServiceName IN ({})".format(
                ",".join(f"'{s}'" for s in services)
            )

        if trace_ids:
            query += " AND TraceId IN ({})".format(
                ",".join(f"'{tid}'" for tid in trace_ids)
            )

        if span_kinds:
            query += " AND SpanKind IN ({})".format(
                ",".join(f"'{sk}'" for sk in span_kinds)
            )

        if status_codes:
            query += " AND StatusCode IN ({})".format(
                ",".join(f"'{sc}'" for sc in status_codes)
            )

        if min_duration_ms:
            query += f" AND Duration >= {min_duration_ms * 1000000}"

        query += " ORDER BY Timestamp ASC"

        df = self.query_df_batched(query)

        if transform and len(df) > 0 and "duration" in df.columns:
            df["duration_ms"] = df["duration"] / 1000000

        logger.info(f"Total traces loaded: {len(df)}")

        if save_to_file and len(df) > 0:
            prefix = "otel_traces"
            if services:
                prefix += f"_{'_'.join(services)}"
            if not transform:
                prefix += "_raw"
            self._save_to_records(df, prefix, raw=not transform)

        return df

    def get_trace_by_id(
        self, trace_id: str, save_to_file: bool = True, transform: bool = False
    ) -> pd.DataFrame:
        """Retrieve a specific trace by its ID.

        Args:
            trace_id: The trace ID to retrieve.
            save_to_file: Whether to save results to TSV file.
            transform: If True, apply transformations. If False (default), export as-is.

        Returns:
            DataFrame containing all spans for the specified trace.
        """
        df = self.get_traces_df(
            trace_ids=[trace_id], save_to_file=False, transform=transform
        )

        if len(df) > 0:
            timestamp_col = "timestamp" if "timestamp" in df.columns else "Timestamp"
            df = df.sort_values(timestamp_col)

            if save_to_file:
                prefix = f"trace_{trace_id[:8]}"
                if not transform:
                    prefix += "_raw"
                self._save_to_records(df, prefix, raw=not transform)

        return df

    def get_error_traces(
        self, save_to_file: bool = True, transform: bool = False
    ) -> pd.DataFrame:
        """Retrieve all traces with error status codes.

        Args:
            save_to_file: Whether to save results to TSV file.
            transform: If True, apply transformations. If False (default), export as-is.

        Returns:
            DataFrame containing traces with errors.
        """
        return self.get_traces_df(
            status_codes=["Error"], save_to_file=save_to_file, transform=transform
        )

    def get_metrics_df(
        self,
        metric_names: Optional[List[str]] = None,
        namespace: str = "otel-demo",
        save_to_file: bool = True,
        transform: bool = False,
    ) -> tuple:
        """Retrieve Prometheus metrics from ClickHouse.

        Args:
            metric_names: List of metric names to retrieve. If None, fetches
                all metrics (raw) or CPU/memory related metrics (transformed).
            namespace: Kubernetes namespace to filter by.
            save_to_file: Whether to save results to TSV files.
            transform: If True, apply transformations (drop tags column for service metrics).
                      If False (default), export all columns as-is.

        Returns:
            Tuple of (pod_metrics_df, service_metrics_df).
        """
        table_ids = self._get_metric_table_ids()

        if not table_ids["data"] or not table_ids["tags"]:
            logger.warning(
                "Prometheus metric tables not available, skipping metrics export"
            )
            return pd.DataFrame(), pd.DataFrame()

        if metric_names is None:
            if transform:
                # Lite export: only CPU/memory metrics
                metrics_query = f"""
                SELECT DISTINCT metric_name
                FROM `{table_ids['tags']}`
                WHERE metric_name LIKE '%cpu%'
                   OR metric_name LIKE '%memory%'
                   OR metric_name LIKE '%mem%'
                """
                available_metrics_df = self.prometheus_client.query_df(metrics_query)
                metric_names = available_metrics_df["metric_name"].tolist()
                logger.info(f"Found {len(metric_names)} CPU/memory related metrics")
            else:
                # Raw export: all metrics
                metrics_query = f"""
                SELECT DISTINCT metric_name
                FROM `{table_ids['tags']}`
                """
                available_metrics_df = self.prometheus_client.query_df(metrics_query)
                metric_names = available_metrics_df["metric_name"].tolist()
                logger.info(f"Found {len(metric_names)} total metrics for raw export")

        pod_metrics_df = self._get_pod_metrics(
            table_ids, metric_names, namespace, save_to_file, transform
        )
        service_metrics_df = self._get_service_metrics(
            table_ids, namespace, save_to_file, transform
        )

        return pod_metrics_df, service_metrics_df

    def _get_pod_metrics(
        self,
        table_ids: Dict[str, Optional[str]],
        metric_names: List[str],
        namespace: str,
        save_to_file: bool,
        transform: bool = False,
    ) -> pd.DataFrame:
        """Retrieve pod-level metrics from Prometheus tables.

        Args:
            table_ids: Dictionary of metric table names.
            metric_names: List of metric names to retrieve.
            namespace: Kubernetes namespace to filter by.
            save_to_file: Whether to save results to TSV files.
            transform: If True, apply transformations. If False (default), export as-is.

        Returns:
            DataFrame containing pod-level metrics.
        """
        if not metric_names:
            return pd.DataFrame()

        all_dfs = []
        batch_size = 5

        for i in range(0, len(metric_names), batch_size):
            batch_metrics = metric_names[i : i + batch_size]
            escaped_metrics = [m.replace("'", "''") for m in batch_metrics]

            query = f"""
            SELECT
                t.metric_name,
                d.timestamp,
                d.value,
                t.tags['pod'] as pod_name,
                t.tags['namespace'] as namespace,
                t.tags
            FROM `{table_ids['data']}` d
            JOIN `{table_ids['tags']}` t ON d.id = t.id
            WHERE t.metric_name IN ({','.join(f"'{m}'" for m in escaped_metrics)})
              AND t.tags['namespace'] = '{namespace.replace("'", "''")}'
              AND t.tags['pod'] != ''
            ORDER BY d.timestamp ASC
            """

            batch_num = i // batch_size + 1
            total_batches = (len(metric_names) + batch_size - 1) // batch_size
            logger.info(f"Processing pod metrics batch {batch_num}/{total_batches}")

            try:
                batch_df = self.prometheus_client.query_df(query)
                if not batch_df.empty:
                    all_dfs.append(batch_df)
                    logger.info(f"  Loaded {len(batch_df)} metric points")
            except Exception as e:
                logger.error(f"  Error processing batch: {e}")
                continue

        if all_dfs:
            df = pd.concat(all_dfs, ignore_index=True)
            logger.info(f"Total pod metric points loaded: {len(df)}")

            if save_to_file and len(df) > 0:
                unique_pods = df["pod_name"].unique()
                for pod in unique_pods:
                    pod_df = df[df["pod_name"] == pod].copy()
                    if transform:
                        pod_df = pod_df.drop(columns=["tags"], errors="ignore")
                    safe_pod_name = pod.replace("/", "_").replace(" ", "_")
                    prefix = f"pod_{safe_pod_name}"
                    if not transform:
                        prefix += "_raw"
                    self._save_to_records(
                        pod_df, prefix, subdir="metrics_pod", raw=not transform
                    )
                    logger.debug(f"  Saved {len(pod_df)} metrics for pod: {pod}")

            return df
        else:
            logger.warning("No pod metric data loaded")
            return pd.DataFrame()

    def _get_service_metrics(
        self,
        table_ids: Dict[str, Optional[str]],
        namespace: str,
        save_to_file: bool,
        transform: bool = False,
    ) -> pd.DataFrame:
        """Retrieve service-level metrics from Prometheus tables.

        Args:
            table_ids: Dictionary of metric table names.
            namespace: Kubernetes namespace to filter by.
            save_to_file: Whether to save results to TSV files.
            transform: If True, apply transformations (drop tags column).
                      If False (default), export all columns as-is.

        Returns:
            DataFrame containing service-level metrics.
        """
        duration_query = f"""
        SELECT
            t.metric_name,
            d.timestamp,
            d.value,
            t.tags['service_name'] as service_name,
            t.tags['namespace'] as namespace,
            t.tags['le'] as bucket_le,
            t.tags
        FROM `{table_ids['data']}` d
        JOIN `{table_ids['tags']}` t ON d.id = t.id
        WHERE t.metric_name = 'traces_span_metrics_duration_milliseconds_bucket'
          AND t.tags['namespace'] = '{namespace}'
          AND t.tags['service_name'] NOT IN ('flagd', 'load-generator')
        ORDER BY d.timestamp ASC
        """

        error_query = f"""
        SELECT
            t.metric_name,
            d.timestamp,
            d.value,
            t.tags['service_name'] as service_name,
            t.tags['namespace'] as namespace,
            t.tags['status_code'] as status_code,
            t.tags
        FROM `{table_ids['data']}` d
        JOIN `{table_ids['tags']}` t ON d.id = t.id
        WHERE t.metric_name = 'traces_span_metrics_calls_total'
          AND t.tags['namespace'] = '{namespace}'
          AND t.tags['service_name'] NOT IN ('flagd', 'load-generator')
          AND t.tags['status_code'] = 'STATUS_CODE_ERROR'
        ORDER BY d.timestamp ASC
        """

        logger.info("Fetching service-level metrics...")

        all_service_dfs = []

        try:
            duration_df = self.prometheus_client.query_df(duration_query)
            if not duration_df.empty:
                duration_df["metric_type"] = "duration_p95"
                all_service_dfs.append(duration_df)
                logger.info(f"  Loaded {len(duration_df)} duration metric points")
        except Exception as e:
            logger.error(f"  Error fetching duration metrics: {e}")

        try:
            error_df = self.prometheus_client.query_df(error_query)
            if not error_df.empty:
                error_df["metric_type"] = "error_rate"
                all_service_dfs.append(error_df)
                logger.info(f"  Loaded {len(error_df)} error metric points")
        except Exception as e:
            logger.error(f"  Error fetching error metrics: {e}")

        if all_service_dfs:
            service_df = pd.concat(all_service_dfs, ignore_index=True)

            if save_to_file and len(service_df) > 0:
                unique_services = service_df["service_name"].unique()
                for service in unique_services:
                    svc_df = service_df[service_df["service_name"] == service].copy()
                    if transform:
                        svc_df = svc_df.drop(columns=["tags"], errors="ignore")
                    prefix = f"service_{service}"
                    if not transform:
                        prefix += "_raw"
                    self._save_to_records(
                        svc_df, prefix, subdir="metrics_service", raw=not transform
                    )
                    logger.debug(
                        f"  Saved {len(svc_df)} metrics for service: {service}"
                    )

            return service_df
        else:
            logger.warning("No service metric data loaded")
            return pd.DataFrame()

    def get_available_metrics(self) -> pd.DataFrame:
        """Retrieve list of all available metrics in the prometheus database.

        Returns:
            DataFrame containing metric names and their variation counts.
        """
        table_ids = self._get_metric_table_ids()

        if not table_ids["tags"]:
            raise Exception("Could not find prometheus tags table")

        query = f"""
        SELECT DISTINCT
            metric_name,
            count(*) as variations
        FROM `{table_ids['tags']}`
        GROUP BY metric_name
        ORDER BY metric_name
        """

        df = self.prometheus_client.query_df(query)
        logger.info(f"Found {len(df)} unique metrics")
        return df

    def close(self):
        """Close all ClickHouse client connections."""
        self.default_client.close()
        self.prometheus_client.close()


def main():
    """Main execution function demonstrating usage of ClickHouseEventStreamer."""

    endpoint = os.environ.get("CLICKHOUSE_ENDPOINT")
    username = os.environ.get("CLICKHOUSE_USERNAME", "default")
    password = os.environ.get("CLICKHOUSE_PASSWORD", "")

    # Clean up the endpoint if it has protocol
    endpoint = endpoint.replace("https://", "").replace("http://", "")

    if endpoint is None or username is None or password is None:
        sys.exit(
            "error: CLICKHOUSE_ENDPOINT, USERNAME and PASSWORD environment variables are not set"
        )

    streamer = ClickHouseEventStreamer(
        host=endpoint, username=username, password=password
    )

    try:
        # ===================
        # FULL EXPORT (raw)
        # ===================
        logger.info("=" * 50)
        logger.info("FULL EXPORT (raw)")
        logger.info("=" * 50)

        logger.info("Fetching events (raw)...")
        events_df = streamer.get_events_df(transform=False)

        logger.info("\nFetching K8s objects (raw)...")
        k8s_objects_df = streamer.get_k8s_objects_df(transform=False)

        logger.info("\nFetching logs (raw)...")
        logs_df = streamer.get_logs_df(transform=False)

        logger.info("\nFetching traces (raw)...")
        traces_df = streamer.get_traces_df(transform=False)

        logger.info("\nFetching metrics (raw)...")
        pod_metrics_df, service_metrics_df = streamer.get_metrics_df(transform=False)

        # ===================
        # LITE EXPORT (transformed + filtered)
        # ===================
        logger.info("\n" + "=" * 50)
        logger.info("LITE EXPORT (transformed + filtered)")
        logger.info("=" * 50)

        namespaces = ["chaos-mesh", "otel-demo"]

        logger.info(f"Fetching events (namespaces: {namespaces})...")
        events_lite_df = streamer.get_events_df(namespaces=namespaces, transform=True)

        logger.info(f"\nFetching K8s objects (namespaces: {namespaces})...")
        k8s_objects_lite_df = streamer.get_k8s_objects_df(
            namespaces=namespaces, transform=True
        )

        logger.info("\nFetching logs (severity: WARN, ERROR, FATAL)...")
        logs_lite_df = streamer.get_logs_df(
            severity_levels=["WARN", "ERROR", "FATAL"], transform=True
        )

        logger.info("\nFetching traces (status: Error)...")
        traces_lite_df = streamer.get_traces_df(status_codes=["Error"], transform=True)

        logger.info("\nFetching metrics (namespace: otel-demo)...")
        pod_metrics_lite_df, service_metrics_lite_df = streamer.get_metrics_df(
            namespace="otel-demo", transform=True
        )

    except Exception as e:
        logger.error(f"Error: {e}")
    finally:
        streamer.close()


if __name__ == "__main__":
    main()
