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

	if err := defaultDB.PingContext(ctx); err != nil {
		return fmt.Errorf("ping clickhouse: %w", err)
	}

	if len(timestamps) == 0 {
		return exportSnapshot(ctx, defaultDB, jaegerDB, outputDir, namespaces, nil, nil)
	}

	startTime := timestamps[0]
	for _, ts := range timestamps {
		targetDir := filepath.Join(outputDir, fmt.Sprintf("snapshot_at_%s", ts.UTC().Format("2006-01-02T15-04-05.000000")))
		if err := exportSnapshot(ctx, defaultDB, jaegerDB, targetDir, namespaces, &ts, &startTime); err != nil {
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

func exportSnapshot(ctx context.Context, defaultDB, jaegerDB *sql.DB, baseDir string, namespaces []string, maxTime, minTime *time.Time) error {
	namespaceList := quoteList(namespaces)

	rawDir := filepath.Join(baseDir, "raw")
	liteDir := filepath.Join(baseDir, "lite")
	for _, d := range []string{rawDir, liteDir} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			return fmt.Errorf("mkdir %s: %w", d, err)
		}
	}

	timeFilter := "1=1"
	tracesTimeFilter := "1=1"
	if maxTime != nil {
		t := maxTime.UTC().Format("2006-01-02 15:04:05.000000000")
		timeFilter = fmt.Sprintf("Timestamp <= '%s'", t)
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
