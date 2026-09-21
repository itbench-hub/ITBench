package recorder

import (
	"context"
	"database/sql"
	"encoding/csv"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
)

const batchSize = 10_000

// openDB opens a *sql.DB via the clickhouse-go/v2 native TCP driver.
// addr must be host:port.
func openDB(addr, username, password, database string) *sql.DB {
	return clickhouse.OpenDB(&clickhouse.Options{
		Protocol: clickhouse.Native,
		Addr:     []string{addr},
		Auth: clickhouse.Auth{ // pragma: allowlist secret
			Database: database,
			Username: username,
			Password: password,
		},
		Compression: &clickhouse.Compression{
			Method: clickhouse.CompressionLZ4,
		},
		DialTimeout:     10 * time.Second,
		ReadTimeout:     120 * time.Second,
		MaxOpenConns:    2,
		MaxIdleConns:    2,
		ConnMaxLifetime: 10 * time.Minute,
	})
}

// Run connects to ClickHouse at host:9000 (TCP) and writes TSV exports to outputDir.
// host must be a bare hostname or IP — no scheme, no port.
func Run(ctx context.Context, host, username, password, outputDir string, timestamps ...time.Time) error {
	return RunWithAddr(ctx, host+":9000", username, password, outputDir, timestamps...)
}

// RunWithAddr is like Run but accepts a pre-built addr (host:port).
// This is useful in tests where testcontainers maps port 9000 to a random host port.
func RunWithAddr(ctx context.Context, addr, username, password, outputDir string, timestamps ...time.Time) error {
	defaultDB := openDB(addr, username, password, "default")
	defer defaultDB.Close()

	jaegerDB := openDB(addr, username, password, "jaeger")
	defer jaegerDB.Close()

	promDB := openDB(addr, username, password, "prometheus")
	defer promDB.Close()

	if err := defaultDB.PingContext(ctx); err != nil {
		return fmt.Errorf("ping default db: %w", err)
	}

	if len(timestamps) == 0 {
		return exportSnapshot(ctx, defaultDB, jaegerDB, promDB, outputDir, nil)
	}

	for _, ts := range timestamps {
		tsVal := ts
		targetDir := filepath.Join(outputDir, fmt.Sprintf("snapshot_at_%s", ts.UTC().Format("2006-01-02T15-04-05.000000")))
		if err := exportSnapshot(ctx, defaultDB, jaegerDB, promDB, targetDir, &tsVal); err != nil {
			return err
		}
	}

	return nil
}

func exportSnapshot(ctx context.Context, defaultDB, jaegerDB, promDB *sql.DB, baseDir string, maxTime *time.Time) error {
	rawDir := filepath.Join(baseDir, "raw")
	liteDir := filepath.Join(baseDir, "lite")
	for _, d := range []string{
		rawDir, liteDir,
		filepath.Join(rawDir, "metrics_pod"), filepath.Join(rawDir, "metrics_service"),
		filepath.Join(liteDir, "metrics_pod"), filepath.Join(liteDir, "metrics_service"),
	} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			return fmt.Errorf("mkdir %s: %w", d, err)
		}
	}

	timeFilter := "1=1"
	promTimeFilter := "1=1"
	if maxTime != nil {
		formattedTime := maxTime.UTC().Format("2006-01-02 15:04:05.000000000")
		timeFilter = fmt.Sprintf("Timestamp <= '%s'", formattedTime)
		promTimeFilter = fmt.Sprintf("d.timestamp <= '%s'", formattedTime)
	}

	// ── k8s events ──────────────────────────────────────────────────────────
	slog.Info("fetching k8s events (raw)", "dir", rawDir)
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_events_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.events WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("k8s events raw", "err", err)
	}

	slog.Info("fetching k8s events (lite)", "dir", liteDir)
	if err := exportQuery(ctx, defaultDB, liteDir, "k8s_events",
		fmt.Sprintf(`SELECT
			Timestamp     AS timestamp,
			Body          AS body,
			ResourceAttributes['k8s.namespace.name'] AS namespace
		 FROM kubernetes.events
		 WHERE %s AND ResourceAttributes['k8s.namespace.name'] IN ('chaos-mesh','otel-demo','bookinfo')
		 ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("k8s events lite", "err", err)
	}

	// ── k8s objects snapshot ─────────────────────────────────────────────────
	slog.Info("fetching k8s objects (raw)", "dir", rawDir)
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_objects_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.objects_snapshot WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("k8s objects raw", "err", err)
	}

	slog.Info("fetching k8s objects (lite)", "dir", liteDir)
	if err := exportQuery(ctx, defaultDB, liteDir, "k8s_objects",
		fmt.Sprintf(`SELECT
			Timestamp     AS timestamp,
			Body          AS body,
			ResourceAttributes['k8s.namespace.name'] AS namespace,
			LogAttributes['k8s.resource.name']       AS resource_type
		 FROM kubernetes.objects_snapshot
		 WHERE %s AND ResourceAttributes['k8s.namespace.name'] IN ('chaos-mesh','otel-demo','bookinfo')
		 ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("k8s objects lite", "err", err)
	}

	// ── otel logs ────────────────────────────────────────────────────────────
	slog.Info("fetching otel logs (raw)", "dir", rawDir)
	if err := exportQuery(ctx, defaultDB, rawDir, "otel_logs_raw",
		fmt.Sprintf(`SELECT * FROM otel_demo.logs WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("otel logs raw", "err", err)
	}

	slog.Info("fetching otel logs (lite)", "dir", liteDir)
	if err := exportQuery(ctx, defaultDB, liteDir, "otel_logs",
		fmt.Sprintf(`SELECT
			Timestamp        AS timestamp,
			TraceId          AS trace_id,
			SpanId           AS span_id,
			TraceFlags       AS trace_flags,
			SeverityText     AS severity_text,
			SeverityNumber   AS severity_number,
			ServiceName      AS service_name,
			Body             AS body,
			ResourceAttributes AS resource_attributes,
			LogAttributes    AS log_attributes
		 FROM otel_demo.logs
		 WHERE %s AND (SeverityText IN ('WARN','ERROR','FATAL') OR SeverityNumber >= 13)
		 ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("otel logs lite", "err", err)
	}

	// ── otel traces ──────────────────────────────────────────────────────────
	slog.Info("fetching otel traces (raw)", "dir", rawDir)
	if err := exportQuery(ctx, jaegerDB, rawDir, "otel_traces_raw",
		fmt.Sprintf(`SELECT * FROM jaeger_spans WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("otel traces raw", "err", err)
	}

	slog.Info("fetching otel traces (lite)", "dir", liteDir)
	if err := exportQuery(ctx, jaegerDB, liteDir, "otel_traces",
		fmt.Sprintf(`SELECT
			Timestamp      AS timestamp,
			TraceId        AS trace_id,
			SpanId         AS span_id,
			ParentSpanId   AS parent_span_id,
			TraceState     AS trace_state,
			SpanName       AS span_name,
			SpanKind       AS span_kind,
			ServiceName    AS service_name,
			ScopeName      AS scope_name,
			ScopeVersion   AS scope_version,
			Duration       AS duration,
			StatusCode     AS status_code,
			StatusMessage  AS status_message
		 FROM jaeger_spans
		 WHERE %s AND StatusCode = 'Error'
		 ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("otel traces lite", "err", err)
	}

	// ── prometheus metrics ───────────────────────────────────────────────────
	tableIDs, err := discoverMetricTables(ctx, promDB)
	if err != nil {
		slog.Warn("could not discover prometheus metric tables", "err", err)
	} else if tableIDs.data != "" && tableIDs.tags != "" {
		if err := exportMetrics(ctx, promDB, rawDir, liteDir, tableIDs, promTimeFilter); err != nil {
			slog.Error("metrics export", "err", err)
		}
	}

	return nil
}

// metricTableIDs holds the discovered inner-id table names for the prometheus DB.
type metricTableIDs struct {
	data    string
	tags    string
	metrics string
}

func discoverMetricTables(ctx context.Context, db *sql.DB) (metricTableIDs, error) {
	rows, err := db.QueryContext(ctx,
		`SELECT name FROM system.tables WHERE database = 'prometheus' AND name LIKE '.inner_id%'`)
	if err != nil {
		return metricTableIDs{}, fmt.Errorf("query system.tables: %w", err)
	}
	defer rows.Close()

	var ids metricTableIDs
	for rows.Next() {
		var name string
		if err := rows.Scan(&name); err != nil {
			return ids, err
		}
		switch {
		case strings.Contains(name, ".inner_id.data."):
			ids.data = name
		case strings.Contains(name, ".inner_id.tags."):
			ids.tags = name
		case strings.Contains(name, ".inner_id.metrics."):
			ids.metrics = name
		}
	}
	return ids, rows.Err()
}

// exportMetrics writes per-pod and per-service metric TSV files.
func exportMetrics(ctx context.Context, db *sql.DB, rawDir, liteDir string, ids metricTableIDs, promTimeFilter string) error {
	// Raw: all metrics, otel-demo namespace
	for _, ns := range []string{"otel-demo", "bookinfo"} {
		if err := exportPodMetrics(ctx, db, rawDir, ids, ns, false, promTimeFilter); err != nil {
			slog.Error("pod metrics raw", "namespace", ns, "err", err)
		}
		if err := exportServiceMetrics(ctx, db, rawDir, ids, ns, false, promTimeFilter); err != nil {
			slog.Error("service metrics raw", "namespace", ns, "err", err)
		}
	}
	// Lite: CPU/memory only
	for _, ns := range []string{"otel-demo", "bookinfo"} {
		if err := exportPodMetrics(ctx, db, liteDir, ids, ns, true, promTimeFilter); err != nil {
			slog.Error("pod metrics lite", "namespace", ns, "err", err)
		}
		if err := exportServiceMetrics(ctx, db, liteDir, ids, ns, true, promTimeFilter); err != nil {
			slog.Error("service metrics lite", "namespace", ns, "err", err)
		}
	}
	return nil
}

func exportPodMetrics(ctx context.Context, db *sql.DB, baseDir string, ids metricTableIDs, namespace string, lite bool, promTimeFilter string) error {
	metricFilter := ""
	if lite {
		metricFilter = `AND (t.metric_name LIKE '%cpu%' OR t.metric_name LIKE '%memory%' OR t.metric_name LIKE '%mem%')`
	}
	query := fmt.Sprintf(`
		SELECT
			t.metric_name,
			d.timestamp,
			d.value,
			t.tags['pod']       AS pod_name,
			t.tags['namespace'] AS namespace,
			t.tags
		FROM %q AS d
		JOIN %q AS t ON d.id = t.id
		WHERE t.tags['namespace'] = '%s'
		  AND t.tags['pod'] != ''
		  AND %s
		  %s
		ORDER BY d.timestamp ASC`,
		ids.data, ids.tags, namespace, promTimeFilter, metricFilter,
	)

	colNames, rows, err := queryAll(ctx, db, query)
	if err != nil {
		return err
	}
	if len(rows) == 0 {
		return nil
	}

	// Group by pod and write one file per pod.
	podCol := slices.Index(colNames, "pod_name")
	if podCol < 0 {
		return fmt.Errorf("pod_name column not found")
	}

	tagsCol := slices.Index(colNames, "tags")

	// Build headers — clone to avoid mutating colNames.
	headers := slices.Clone(colNames)
	if lite && tagsCol >= 0 {
		headers = slices.Delete(headers, tagsCol, tagsCol+1)
	}

	byPod := map[string][][]string{}
	for _, row := range rows {
		pod := row[podCol]
		if lite && tagsCol >= 0 {
			// Clone row before mutating to avoid corrupting the backing array.
			row = slices.Delete(slices.Clone(row), tagsCol, tagsCol+1)
		}
		byPod[pod] = append(byPod[pod], row)
	}

	subdir := filepath.Join(baseDir, "metrics_pod")
	for pod, podRows := range byPod {
		suffix := ""
		if !lite {
			suffix = "_raw"
		}
		safePod := strings.NewReplacer("/", "_", " ", "_").Replace(pod)
		fname := fmt.Sprintf("pod_%s%s.tsv", safePod, suffix)
		if err := writeTSV(filepath.Join(subdir, fname), headers, podRows); err != nil {
			slog.Error("write pod tsv", "pod", pod, "err", err)
		}
	}
	return nil
}

func exportServiceMetrics(ctx context.Context, db *sql.DB, baseDir string, ids metricTableIDs, namespace string, lite bool, promTimeFilter string) error {
	queries := []struct {
		q          string
		metricType string
	}{
		{
			fmt.Sprintf(`
			SELECT t.metric_name, d.timestamp, d.value,
			       t.tags['service_name'] AS service_name, t.tags['namespace'] AS namespace,
			       t.tags['le'] AS bucket_le, t.tags
			FROM %q AS d JOIN %q AS t ON d.id = t.id
			WHERE t.metric_name = 'traces_span_metrics_duration_milliseconds_bucket'
			  AND t.tags['namespace'] = '%s'
			  AND t.tags['service_name'] NOT IN ('flagd','load-generator')
			  AND %s
			ORDER BY d.timestamp ASC`, ids.data, ids.tags, namespace, promTimeFilter),
			"duration_p95",
		},
		{
			fmt.Sprintf(`
			SELECT t.metric_name, d.timestamp, d.value,
			       t.tags['service_name'] AS service_name, t.tags['namespace'] AS namespace,
			       t.tags['status_code'] AS status_code, t.tags
			FROM %q AS d JOIN %q AS t ON d.id = t.id
			WHERE t.metric_name = 'traces_span_metrics_calls_total'
			  AND t.tags['namespace'] = '%s'
			  AND t.tags['service_name'] NOT IN ('flagd','load-generator')
			  AND t.tags['status_code'] = 'STATUS_CODE_ERROR'
			  AND %s
			ORDER BY d.timestamp ASC`, ids.data, ids.tags, namespace, promTimeFilter),
			"error_rate",
		},
		{
			fmt.Sprintf(`
			SELECT t.metric_name, d.timestamp, d.value,
			       t.tags['destination_canonical_service'] AS service_name,
			       t.tags['destination_workload_namespace'] AS namespace,
			       t.tags['le'] AS bucket_le, t.tags
			FROM %q AS d JOIN %q AS t ON d.id = t.id
			WHERE t.metric_name = 'istio_request_duration_milliseconds_bucket'
			  AND t.tags['destination_workload_namespace'] = '%s'
			  AND t.tags['destination_canonical_service'] NOT IN ('load-generator')
			  AND %s
			ORDER BY d.timestamp ASC`, ids.data, ids.tags, namespace, promTimeFilter),
			"duration_p95",
		},
		{
			fmt.Sprintf(`
			SELECT t.metric_name, d.timestamp, d.value,
			       t.tags['destination_canonical_service'] AS service_name,
			       t.tags['destination_workload_namespace'] AS namespace,
			       t.tags['response_code'] AS status_code, t.tags
			FROM %q AS d JOIN %q AS t ON d.id = t.id
			WHERE t.metric_name = 'istio_requests_total'
			  AND t.tags['destination_workload_namespace'] = '%s'
			  AND t.tags['destination_canonical_service'] NOT IN ('load-generator')
			  AND t.tags['response_code'] NOT LIKE '2%%'
			  AND %s
			ORDER BY d.timestamp ASC`, ids.data, ids.tags, namespace, promTimeFilter),
			"error_rate",
		},
	}

	// Collect all rows across all service metric queries.
	type serviceRow struct {
		cols []string
		rows [][]string
	}
	bySvc := map[string]*serviceRow{}

	for _, q := range queries {
		colNames, rows, err := queryAll(ctx, db, q.q)
		if err != nil {
			slog.Warn("service metric query failed", "metric_type", q.metricType, "err", err)
			continue
		}
		svcCol := slices.Index(colNames, "service_name")
		if svcCol < 0 {
			continue
		}
		tagsCol := slices.Index(colNames, "tags")
		for _, row := range rows {
			svc := row[svcCol]
			if _, ok := bySvc[svc]; !ok {
				// Note: cols is taken from the first query that produces rows for
				// this service. Rows from subsequent queries may have different
				// columns — this matches the Python pd.concat behaviour where
				// missing columns are filled with NaN.
				bySvc[svc] = &serviceRow{cols: colNames}
			}
			r := slices.Clone(row)
			if lite && tagsCol >= 0 {
				r = slices.Delete(r, tagsCol, tagsCol+1)
			}
			bySvc[svc].rows = append(bySvc[svc].rows, r)
		}
	}

	subdir := filepath.Join(baseDir, "metrics_service")
	for svc, sr := range bySvc {
		// Build headers — clone to avoid mutating sr.cols.
		headers := slices.Clone(sr.cols)
		if lite {
			tagsCol := slices.Index(sr.cols, "tags")
			if tagsCol >= 0 {
				headers = slices.Delete(headers, tagsCol, tagsCol+1)
			}
		}
		suffix := ""
		if !lite {
			suffix = "_raw"
		}
		fname := fmt.Sprintf("service_%s%s.tsv", svc, suffix)
		if err := writeTSV(filepath.Join(subdir, fname), headers, sr.rows); err != nil {
			slog.Error("write service tsv", "service", svc, "err", err)
		}
	}
	return nil
}

// exportQuery runs a SQL query and writes all rows to a TSV file under dir.
// Uses LIMIT/OFFSET batching for large result sets.
func exportQuery(ctx context.Context, db *sql.DB, dir, prefix, query string) error {
	colNames, rows, err := queryAll(ctx, db, query)
	if err != nil {
		return err
	}
	if len(rows) == 0 {
		slog.Info("no rows", "prefix", prefix)
		return nil
	}
	return writeTSV(filepath.Join(dir, prefix+".tsv"), colNames, rows)
}

// queryAll executes query with LIMIT/OFFSET batching and returns all rows as strings.
func queryAll(ctx context.Context, db *sql.DB, query string) ([]string, [][]string, error) {
	// Strip any existing LIMIT/OFFSET so we can add our own.
	base := stripLimitOffset(query)

	var (
		colNames []string
		allRows  [][]string
		offset   int
	)

	for {
		paged := fmt.Sprintf("%s LIMIT %d OFFSET %d", base, batchSize, offset)
		rows, err := db.QueryContext(ctx, paged)
		if err != nil {
			return nil, nil, fmt.Errorf("query: %w", err)
		}

		if colNames == nil {
			cols, err := rows.Columns()
			if err != nil {
				rows.Close()
				return nil, nil, fmt.Errorf("columns: %w", err)
			}
			colNames = cols
		}

		batch, err := scanRows(rows, len(colNames))
		rows.Close()
		if err != nil {
			return nil, nil, err
		}

		allRows = append(allRows, batch...)
		if len(batch) < batchSize {
			break
		}
		offset += batchSize
	}

	return colNames, allRows, nil
}

// scanRows scans all rows from an open *sql.Rows into string slices.
func scanRows(rows *sql.Rows, ncols int) ([][]string, error) {
	vals := make([]any, ncols)
	ptrs := make([]any, ncols)
	for i := range vals {
		ptrs[i] = &vals[i]
	}

	result := make([][]string, 0, batchSize)
	for rows.Next() {
		if err := rows.Scan(ptrs...); err != nil {
			return nil, fmt.Errorf("scan: %w", err)
		}
		row := make([]string, ncols)
		for i, v := range vals {
			if v == nil {
				row[i] = ""
				continue
			}
			switch val := v.(type) {
			case string:
				row[i] = val
			case []byte:
				row[i] = string(val)
			default:
				row[i] = fmt.Sprintf("%v", val)
			}
		}
		result = append(result, row)
	}
	return result, rows.Err()
}

// writeTSV writes headers + rows to path using tab-separated values.
func writeTSV(path string, headers []string, rows [][]string) error {
	f, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	w.Comma = '\t'
	w.UseCRLF = false

	if err := w.Write(headers); err != nil {
		return err
	}
	for _, row := range rows {
		if err := w.Write(row); err != nil {
			return err
		}
	}
	w.Flush()
	slog.Info("wrote", "file", path, "rows", len(rows))
	return w.Error()
}

// stripLimitOffset removes trailing LIMIT n / OFFSET n clauses (case-insensitive).
func stripLimitOffset(q string) string {
	// Work on the query trimmed of trailing whitespace.
	upper := strings.ToUpper(strings.TrimRight(q, " \t\n\r"))
	for _, kw := range []string{"OFFSET", "LIMIT"} {
		if idx := strings.LastIndex(upper, kw); idx >= 0 {
			// Only strip if the token after the keyword is purely numeric.
			rest := strings.TrimSpace(upper[idx+len(kw):])
			isNumeric := true
			for _, c := range rest {
				if c < '0' || c > '9' {
					isNumeric = false
					break
				}
			}
			if isNumeric {
				q = q[:idx]
				upper = upper[:idx]
			}
		}
	}
	return strings.TrimRight(q, " \t\n\r")
}
