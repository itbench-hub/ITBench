package recorder

import (
	"context"
	"database/sql"
	"encoding/csv"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"time"
	"unicode"

	"github.com/ClickHouse/clickhouse-go/v2"
)

const batchSize = 10_000

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

// Run exports the recorded data into outputDir. Namespaced data is restricted to the given namespaces.
func Run(ctx context.Context, addr, username, password, outputDir string, namespaces []string, timestamps ...time.Time) error {
	defaultDB := openDB(addr, username, password, "default")
	defer defaultDB.Close()

	jaegerDB := openDB(addr, username, password, "jaeger")
	defer jaegerDB.Close()

	promDB := openDB(addr, username, password, "prometheus")
	defer promDB.Close()

	if err := defaultDB.PingContext(ctx); err != nil {
		return fmt.Errorf("ping clickhouse: %w", err)
	}

	if len(timestamps) == 0 {
		return exportSnapshot(ctx, defaultDB, jaegerDB, promDB, outputDir, namespaces, nil, nil)
	}

	startTime := timestamps[0]
	for _, ts := range timestamps {
		targetDir := filepath.Join(outputDir, fmt.Sprintf("snapshot_at_%s", ts.UTC().Format("2006-01-02T15-04-05.000000")))
		if err := exportSnapshot(ctx, defaultDB, jaegerDB, promDB, targetDir, namespaces, &ts, &startTime); err != nil {
			return err
		}
	}

	return nil
}

// quoteList converts values into a SQL list of single-quoted strings, e.g. 'a','b'.
func quoteList(values []string) string {
	quoted := make([]string, 0, len(values))
	for _, v := range values {
		quoted = append(quoted, "'"+strings.ReplaceAll(v, "'", "''")+"'")
	}
	return strings.Join(quoted, ",")
}

func exportSnapshot(ctx context.Context, defaultDB, jaegerDB, promDB *sql.DB, baseDir string, namespaces []string, maxTime, minTime *time.Time) error {
	namespaceList := quoteList(namespaces)

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
	tracesTimeFilter := "1=1"
	if maxTime != nil {
		t := maxTime.UTC().Format("2006-01-02 15:04:05.000000000")
		timeFilter = fmt.Sprintf("Timestamp <= '%s'", t)
		// promTimeFilter is used against the bare data table (no alias), so no qualifier.
		promTimeFilter = fmt.Sprintf("timestamp <= '%s'", t)
		tracesTimeFilter = fmt.Sprintf("start_time <= '%s'", t)
	}

	topologyTimeFilter := "1=1"
	if minTime != nil {
		topologyTimeFilter = fmt.Sprintf("Timestamp >= '%s'", minTime.UTC().Format("2006-01-02 15:04:05.000000000"))
	}
	if maxTime != nil {
		topologyTimeFilter += fmt.Sprintf(" AND Timestamp <= '%s'", maxTime.UTC().Format("2006-01-02 15:04:05.000000000"))
	}

	slog.Info("fetching k8s events (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_events_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.events WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("k8s events raw", "err", err)
	}

	slog.Info("fetching k8s events (lite)")
	if err := exportQuery(ctx, defaultDB, liteDir, "k8s_events",
		fmt.Sprintf(`SELECT
			Timestamp     AS timestamp,
			Body          AS body,
			ResourceAttributes['k8s.namespace.name'] AS namespace
		 FROM kubernetes.events
		 WHERE %s AND ResourceAttributes['k8s.namespace.name'] IN (%s)
		 ORDER BY Timestamp ASC`, timeFilter, namespaceList)); err != nil {
		slog.Error("k8s events lite", "err", err)
	}

	slog.Info("fetching k8s topology objects (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_topology_objects_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.topology WHERE %s ORDER BY Timestamp ASC`, topologyTimeFilter)); err != nil {
		slog.Warn("k8s topology objects raw (table may not exist)", "err", err)
	}

	slog.Info("fetching k8s topology graph (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_topology_graph_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.topology_graph WHERE %s ORDER BY Timestamp ASC, Seq ASC`, topologyTimeFilter)); err != nil {
		slog.Warn("k8s topology graph raw (table may not exist)", "err", err)
	}

	slog.Info("fetching k8s objects (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_objects_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.objects_snapshot WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("k8s objects raw", "err", err)
	}

	slog.Info("fetching k8s objects (lite)")
	if err := exportQuery(ctx, defaultDB, liteDir, "k8s_objects",
		fmt.Sprintf(`SELECT
			Timestamp     AS timestamp,
			Body          AS body,
			ResourceAttributes['k8s.namespace.name'] AS namespace,
			LogAttributes['k8s.resource.name']       AS resource_type
		 FROM kubernetes.objects_snapshot
		 WHERE %s AND ResourceAttributes['k8s.namespace.name'] IN (%s)
		 ORDER BY Timestamp ASC`, timeFilter, namespaceList)); err != nil {
		slog.Error("k8s objects lite", "err", err)
	}

	slog.Info("fetching otel logs (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "otel_logs_raw",
		fmt.Sprintf(`SELECT * FROM opentelemetry_demo.logs WHERE %s ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("otel logs raw", "err", err)
	}

	slog.Info("fetching otel logs (lite)")
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
		 FROM opentelemetry_demo.logs
		 WHERE %s AND (SeverityText IN ('WARN','ERROR','FATAL') OR SeverityNumber >= 13)
		 ORDER BY Timestamp ASC`, timeFilter)); err != nil {
		slog.Error("otel logs lite", "err", err)
	}

	slog.Info("fetching jaeger spans (raw)")
	if err := exportQuery(ctx, jaegerDB, rawDir, "jaeger_spans_raw",
		fmt.Sprintf(`SELECT * FROM spans WHERE %s ORDER BY start_time ASC`, tracesTimeFilter)); err != nil {
		slog.Error("jaeger spans raw", "err", err)
	}

	slog.Info("fetching jaeger spans (lite)")
	if err := exportQuery(ctx, jaegerDB, liteDir, "jaeger_spans",
		fmt.Sprintf(`SELECT
			start_time     AS timestamp,
			trace_id       AS trace_id,
			id             AS span_id,
			parent_span_id AS parent_span_id,
			trace_state    AS trace_state,
			name           AS span_name,
			kind           AS span_kind,
			service_name   AS service_name,
			scope_name     AS scope_name,
			scope_version  AS scope_version,
			duration       AS duration,
			status_code    AS status_code,
			status_message AS status_message
		 FROM spans
		 WHERE %s AND (status_code = 'Error' OR status_code = 'STATUS_CODE_ERROR')
		 ORDER BY start_time ASC`, tracesTimeFilter)); err != nil {
		slog.Error("jaeger spans lite", "err", err)
	}

	tableIDs, err := discoverMetricTables(ctx, promDB)
	if err != nil {
		slog.Warn("could not discover prometheus metric tables", "err", err)
	} else if tableIDs.data != "" && tableIDs.tags != "" {
		if err := exportMetrics(ctx, promDB, rawDir, liteDir, tableIDs, namespaces, promTimeFilter); err != nil {
			slog.Error("metrics export", "err", err)
		}
	}

	return nil
}

// metricTableIDs holds the inner-id table names backing the Prometheus materialized view.
type metricTableIDs struct {
	data string
	tags string
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
		}
	}
	return ids, rows.Err()
}

// tagMeta holds the denormalised metadata for one metric series (unique label-set).
type tagMeta struct {
	metricName string
	tags       map[string]string
}

// fetchTagMap loads the tags inner table into memory, filtered by whereClause.
// This is cheap: the tags table has one row per unique label-set, not per data point.
func fetchTagMap(ctx context.Context, db *sql.DB, tagsTable, whereClause string) (map[string]tagMeta, error) {
	query := fmt.Sprintf(`SELECT id, metric_name, tags FROM %q WHERE %s`, tagsTable, whereClause)
	rows, err := db.QueryContext(ctx, query)
	if err != nil {
		return nil, fmt.Errorf("fetch tags: %w", err)
	}
	defer rows.Close()

	result := map[string]tagMeta{}
	for rows.Next() {
		var id, metricName string
		var tags map[string]string
		if err := rows.Scan(&id, &metricName, &tags); err != nil {
			return nil, fmt.Errorf("scan tag: %w", err)
		}
		result[id] = tagMeta{metricName: metricName, tags: tags}
	}
	return result, rows.Err()
}

// lazyTSV opens and writes a header to a TSV file on the first write call.
type lazyTSV struct {
	path    string
	headers []string
	f       *os.File
	w       *csv.Writer
}

func (l *lazyTSV) write(row []string) error {
	if l.f == nil {
		f, err := os.Create(l.path)
		if err != nil {
			return fmt.Errorf("create %s: %w", l.path, err)
		}
		w := csv.NewWriter(f)
		w.Comma = '\t'
		w.UseCRLF = false
		if err := w.Write(l.headers); err != nil {
			f.Close()
			return err
		}
		l.f = f
		l.w = w
	}
	return l.w.Write(row)
}

func (l *lazyTSV) close() {
	if l.f == nil {
		return
	}
	l.w.Flush()
	if err := l.w.Error(); err != nil {
		slog.Error("flush tsv", "path", l.path, "err", err)
	}
	l.f.Close()
}

// streamDataByIDs pages through the data table for a given set of series IDs
// and calls handle for each row. Avoids a server-side JOIN with the tags table.
func streamDataByIDs(ctx context.Context, db *sql.DB, dataTable, idList, timeFilter string, handle func(id, ts, val string) error) error {
	base := fmt.Sprintf(
		`SELECT id, timestamp, value FROM %q WHERE id IN (%s) AND %s ORDER BY timestamp ASC`,
		dataTable, idList, timeFilter,
	)
	for offset := 0; ; offset += batchSize {
		paged := fmt.Sprintf("%s LIMIT %d OFFSET %d", base, batchSize, offset)
		rows, err := db.QueryContext(ctx, paged)
		if err != nil {
			return fmt.Errorf("query data: %w", err)
		}
		var n int
		for rows.Next() {
			var id, ts, val string
			if err := rows.Scan(&id, &ts, &val); err != nil {
				rows.Close()
				return fmt.Errorf("scan data: %w", err)
			}
			if err := handle(id, ts, val); err != nil {
				rows.Close()
				return err
			}
			n++
		}
		rows.Close()
		if err := rows.Err(); err != nil {
			return err
		}
		if n < batchSize {
			break
		}
	}
	return nil
}

// buildIDList converts tag map keys into a SQL IN list of single-quoted strings.
func buildIDList(m map[string]tagMeta) string {
	ids := make([]string, 0, len(m))
	for id := range m {
		ids = append(ids, "'"+strings.ReplaceAll(id, "'", "''")+"'")
	}
	return strings.Join(ids, ",")
}

func exportMetrics(ctx context.Context, db *sql.DB, rawDir, liteDir string, ids metricTableIDs, namespaces []string, promTimeFilter string) error {
	for _, ns := range namespaces {
		if err := exportPodMetrics(ctx, db, rawDir, liteDir, ids, ns, promTimeFilter); err != nil {
			slog.Error("pod metrics export", "namespace", ns, "err", err)
		}
		if err := exportServiceMetrics(ctx, db, rawDir, liteDir, ids, ns, promTimeFilter); err != nil {
			slog.Error("service metrics export", "namespace", ns, "err", err)
		}
	}
	return nil
}

func exportPodMetrics(ctx context.Context, db *sql.DB, rawDir, liteDir string, ids metricTableIDs, namespace, promTimeFilter string) error {
	tagMap, err := fetchTagMap(ctx, db, ids.tags,
		fmt.Sprintf(`tags['namespace'] = '%s' AND tags['pod'] != ''`, namespace))
	if err != nil {
		return err
	}
	if len(tagMap) == 0 {
		return nil
	}

	rawWriters := map[string]*lazyTSV{}
	liteWriters := map[string]*lazyTSV{}
	defer func() {
		for _, l := range rawWriters {
			l.close()
		}
		for _, l := range liteWriters {
			l.close()
		}
	}()

	rawHeaders := []string{"metric_name", "timestamp", "value", "pod_name", "namespace", "tags"}
	liteHeaders := []string{"metric_name", "timestamp", "value", "pod_name", "namespace"}
	safeReplacer := strings.NewReplacer("/", "_", " ", "_")

	return streamDataByIDs(ctx, db, ids.data, buildIDList(tagMap), promTimeFilter, func(id, ts, val string) error {
		meta, ok := tagMap[id]
		if !ok {
			return nil
		}
		pod := meta.tags["pod"]
		safePod := safeReplacer.Replace(pod)

		if _, ok := rawWriters[pod]; !ok {
			rawWriters[pod] = &lazyTSV{
				path:    filepath.Join(rawDir, "metrics_pod", fmt.Sprintf("pod_%s_raw.tsv", safePod)),
				headers: rawHeaders,
			}
		}
		if err := rawWriters[pod].write([]string{
			meta.metricName, ts, val, pod, meta.tags["namespace"], fmt.Sprintf("%v", meta.tags),
		}); err != nil {
			return err
		}

		if strings.Contains(meta.metricName, "cpu") ||
			strings.Contains(meta.metricName, "memory") ||
			strings.Contains(meta.metricName, "mem") {
			if _, ok := liteWriters[pod]; !ok {
				liteWriters[pod] = &lazyTSV{
					path:    filepath.Join(liteDir, "metrics_pod", fmt.Sprintf("pod_%s.tsv", safePod)),
					headers: liteHeaders,
				}
			}
			if err := liteWriters[pod].write([]string{
				meta.metricName, ts, val, pod, meta.tags["namespace"],
			}); err != nil {
				return err
			}
		}
		return nil
	})
}

func exportServiceMetrics(ctx context.Context, db *sql.DB, rawDir, liteDir string, ids metricTableIDs, namespace, promTimeFilter string) error {
	type svcQueryDef struct {
		metricName  string
		nsTagKey    string
		svcTagKey   string
		extraFilter string
	}
	queryDefs := []svcQueryDef{
		{
			metricName:  "traces_span_metrics_duration_milliseconds_bucket",
			nsTagKey:    "namespace",
			svcTagKey:   "service_name",
			extraFilter: `tags['service_name'] NOT IN ('flagd','load-generator')`,
		},
		{
			metricName:  "traces_span_metrics_calls_total",
			nsTagKey:    "namespace",
			svcTagKey:   "service_name",
			extraFilter: `tags['service_name'] NOT IN ('flagd','load-generator') AND tags['status_code'] = 'STATUS_CODE_ERROR'`,
		},
		{
			metricName:  "istio_request_duration_milliseconds_bucket",
			nsTagKey:    "destination_workload_namespace",
			svcTagKey:   "destination_canonical_service",
			extraFilter: `tags['destination_canonical_service'] NOT IN ('load-generator')`,
		},
		{
			metricName:  "istio_requests_total",
			nsTagKey:    "destination_workload_namespace",
			svcTagKey:   "destination_canonical_service",
			extraFilter: `tags['destination_canonical_service'] NOT IN ('load-generator') AND tags['response_code'] NOT LIKE '2%'`,
		},
	}

	rawHeaders := []string{"metric_name", "timestamp", "value", "service_name", "namespace", "tags"}
	liteHeaders := []string{"metric_name", "timestamp", "value", "service_name", "namespace"}

	rawWriters := map[string]*lazyTSV{}
	liteWriters := map[string]*lazyTSV{}
	defer func() {
		for _, l := range rawWriters {
			l.close()
		}
		for _, l := range liteWriters {
			l.close()
		}
	}()

	for _, qd := range queryDefs {
		tagMap, err := fetchTagMap(ctx, db, ids.tags, fmt.Sprintf(
			`metric_name = '%s' AND tags['%s'] = '%s' AND %s`,
			qd.metricName, qd.nsTagKey, namespace, qd.extraFilter,
		))
		if err != nil {
			slog.Warn("fetch service tags failed", "metric", qd.metricName, "err", err)
			continue
		}
		if len(tagMap) == 0 {
			continue
		}

		err = streamDataByIDs(ctx, db, ids.data, buildIDList(tagMap), promTimeFilter, func(id, ts, val string) error {
			meta, ok := tagMap[id]
			if !ok {
				return nil
			}
			svc := meta.tags[qd.svcTagKey]

			if _, ok := rawWriters[svc]; !ok {
				rawWriters[svc] = &lazyTSV{
					path:    filepath.Join(rawDir, "metrics_service", fmt.Sprintf("service_%s_raw.tsv", svc)),
					headers: rawHeaders,
				}
			}
			if err := rawWriters[svc].write([]string{
				meta.metricName, ts, val, svc, meta.tags[qd.nsTagKey], fmt.Sprintf("%v", meta.tags),
			}); err != nil {
				return err
			}

			if _, ok := liteWriters[svc]; !ok {
				liteWriters[svc] = &lazyTSV{
					path:    filepath.Join(liteDir, "metrics_service", fmt.Sprintf("service_%s.tsv", svc)),
					headers: liteHeaders,
				}
			}
			return liteWriters[svc].write([]string{
				meta.metricName, ts, val, svc, meta.tags[qd.nsTagKey],
			})
		})
		if err != nil {
			slog.Error("stream service data failed", "metric", qd.metricName, "err", err)
		}
	}
	return nil
}

// exportQuery streams a SQL query page-by-page directly into a TSV file,
// so the full result set is never held in memory.
func exportQuery(ctx context.Context, db *sql.DB, dir, prefix, query string) error {
	path := filepath.Join(dir, prefix+".tsv")
	base := stripLimitOffset(query)

	f, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer f.Close()

	w := csv.NewWriter(f)
	w.Comma = '\t'
	w.UseCRLF = false

	var (
		colNames []string
		total    int
	)

	for offset := 0; ; offset += batchSize {
		paged := fmt.Sprintf("%s LIMIT %d OFFSET %d", base, batchSize, offset)
		rows, err := db.QueryContext(ctx, paged)
		if err != nil {
			return fmt.Errorf("query: %w", err)
		}

		if colNames == nil {
			cols, err := rows.Columns()
			if err != nil {
				rows.Close()
				return fmt.Errorf("columns: %w", err)
			}
			colNames = cols
			if err := w.Write(colNames); err != nil {
				rows.Close()
				return err
			}
		}

		n, err := streamRows(rows, len(colNames), w)
		rows.Close()
		if err != nil {
			return err
		}

		total += n
		if n < batchSize {
			break
		}
	}

	w.Flush()
	if err := w.Error(); err != nil {
		return err
	}

	if total == 0 {
		_ = os.Remove(path)
		slog.Info("no rows", "prefix", prefix)
		return nil
	}

	slog.Info("wrote", "file", path, "rows", total)
	return nil
}

func streamRows(rows *sql.Rows, ncols int, w *csv.Writer) (int, error) {
	vals := make([]any, ncols)
	ptrs := make([]any, ncols)
	for i := range vals {
		ptrs[i] = &vals[i]
	}
	row := make([]string, ncols)

	var n int
	for rows.Next() {
		if err := rows.Scan(ptrs...); err != nil {
			return n, fmt.Errorf("scan: %w", err)
		}
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
		if err := w.Write(row); err != nil {
			return n, err
		}
		n++
	}
	return n, rows.Err()
}

// stripLimitOffset removes a trailing LIMIT [n] OFFSET [n] or LIMIT [n] clause.
// Only strips clauses where the argument is a plain integer, so subquery limits are safe.
func stripLimitOffset(q string) string {
	upper := strings.ToUpper(strings.TrimRight(q, " \t\n\r"))
	for _, kw := range []string{"OFFSET", "LIMIT"} {
		if idx := strings.LastIndex(upper, kw); idx >= 0 {
			rest := strings.TrimSpace(upper[idx+len(kw):])
			if rest != "" && strings.IndexFunc(rest, func(r rune) bool { return !unicode.IsDigit(r) }) == -1 {
				q = strings.TrimRight(q[:idx], " \t\n\r")
				upper = upper[:idx]
			}
		}
	}
	return strings.TrimRight(q, " \t\n\r")
}
