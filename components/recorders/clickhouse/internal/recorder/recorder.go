package recorder

import (
	"compress/gzip"
	"context"
	"database/sql"
	"encoding/csv"
	"fmt"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
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

type liteHandler struct {
	dir    string
	prefix string
	header []string
	derive func(colIdx map[string]int, vals []any) ([]string, bool)
}

func exportSnapshot(ctx context.Context, defaultDB, jaegerDB *sql.DB, baseDir string, namespaces []string, maxTime, minTime *time.Time) error {
	nsSet := make(map[string]bool, len(namespaces))
	for _, ns := range namespaces {
		nsSet[ns] = true
	}

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

	slog.Info("fetching k8s events")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_events_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.events WHERE %s ORDER BY Timestamp ASC`, timeFilter),
		&liteHandler{
			dir:    liteDir,
			prefix: "k8s_events",
			header: []string{"timestamp", "body", "namespace"},
			derive: func(colIdx map[string]int, vals []any) ([]string, bool) {
				ns := getMapKey(vals[colIdx["ResourceAttributes"]], "k8s.namespace.name")
				if !nsSet[ns] {
					return nil, false
				}
				return []string{
					formatVal(vals[colIdx["Timestamp"]]),
					formatVal(vals[colIdx["Body"]]),
					ns,
				}, true
			},
		}); err != nil {
		slog.Error("k8s events", "err", err)
	}

	slog.Info("fetching k8s topology objects (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_topology_objects_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.topology WHERE %s ORDER BY Timestamp ASC`, topologyTimeFilter), nil); err != nil {
		slog.Warn("k8s topology objects raw (table may not exist)", "err", err)
	}

	slog.Info("fetching k8s topology graph (raw)")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_topology_graph_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.topology_graph WHERE %s ORDER BY Timestamp ASC, Seq ASC`, topologyTimeFilter), nil); err != nil {
		slog.Warn("k8s topology graph raw (table may not exist)", "err", err)
	}

	slog.Info("fetching k8s infrastructure")
	if err := exportQuery(ctx, defaultDB, rawDir, "k8s_infrastructure_raw",
		fmt.Sprintf(`SELECT * FROM kubernetes.infrastructure WHERE %s ORDER BY Timestamp ASC`, timeFilter),
		&liteHandler{
			dir:    liteDir,
			prefix: "k8s_infrastructure",
			header: []string{"timestamp", "body", "namespace", "resource_type"},
			derive: func(colIdx map[string]int, vals []any) ([]string, bool) {
				ns := getMapKey(vals[colIdx["ResourceAttributes"]], "k8s.namespace.name")
				if !nsSet[ns] {
					return nil, false
				}
				resourceType := getMapKey(vals[colIdx["LogAttributes"]], "k8s.resource.name")
				return []string{
					formatVal(vals[colIdx["Timestamp"]]),
					formatVal(vals[colIdx["Body"]]),
					ns,
					resourceType,
				}, true
			},
		}); err != nil {
		slog.Error("k8s infrastructure", "err", err)
	}

	slog.Info("fetching otel logs")
	if err := exportQuery(ctx, defaultDB, rawDir, "otel_logs_raw",
		fmt.Sprintf(`SELECT * FROM opentelemetry_demo.logs WHERE %s ORDER BY Timestamp ASC`, timeFilter),
		&liteHandler{
			dir:    liteDir,
			prefix: "otel_logs",
			header: []string{
				"timestamp", "trace_id", "span_id", "trace_flags",
				"severity_text", "severity_number", "service_name",
				"body", "resource_attributes", "log_attributes",
			},
			derive: func(colIdx map[string]int, vals []any) ([]string, bool) {
				sevText := formatVal(vals[colIdx["SeverityText"]])
				sevNum := toInt(vals[colIdx["SeverityNumber"]])
				if sevText != "WARN" && sevText != "ERROR" && sevText != "FATAL" && sevNum < 13 {
					return nil, false
				}
				return []string{
					formatVal(vals[colIdx["Timestamp"]]),
					formatVal(vals[colIdx["TraceId"]]),
					formatVal(vals[colIdx["SpanId"]]),
					formatVal(vals[colIdx["TraceFlags"]]),
					sevText,
					formatVal(vals[colIdx["SeverityNumber"]]),
					formatVal(vals[colIdx["ServiceName"]]),
					formatVal(vals[colIdx["Body"]]),
					formatVal(vals[colIdx["ResourceAttributes"]]),
					formatVal(vals[colIdx["LogAttributes"]]),
				}, true
			},
		}); err != nil {
		slog.Error("otel logs", "err", err)
	}

	slog.Info("fetching jaeger spans")
	if err := exportQuery(ctx, jaegerDB, rawDir, "jaeger_spans_raw",
		fmt.Sprintf(`SELECT * FROM spans WHERE %s ORDER BY start_time ASC`, tracesTimeFilter),
		&liteHandler{
			dir:    liteDir,
			prefix: "jaeger_spans",
			header: []string{
				"timestamp", "trace_id", "span_id", "parent_span_id",
				"trace_state", "span_name", "span_kind", "service_name",
				"scope_name", "scope_version", "duration", "status_code", "status_message",
			},
			derive: func(colIdx map[string]int, vals []any) ([]string, bool) {
				statusCode := formatVal(vals[colIdx["status_code"]])
				if statusCode != "Error" && statusCode != "STATUS_CODE_ERROR" {
					return nil, false
				}
				return []string{
					formatVal(vals[colIdx["start_time"]]),
					formatVal(vals[colIdx["trace_id"]]),
					formatVal(vals[colIdx["id"]]),
					formatVal(vals[colIdx["parent_span_id"]]),
					formatVal(vals[colIdx["trace_state"]]),
					formatVal(vals[colIdx["name"]]),
					formatVal(vals[colIdx["kind"]]),
					formatVal(vals[colIdx["service_name"]]),
					formatVal(vals[colIdx["scope_name"]]),
					formatVal(vals[colIdx["scope_version"]]),
					formatVal(vals[colIdx["duration"]]),
					statusCode,
					formatVal(vals[colIdx["status_message"]]),
				}, true
			},
		}); err != nil {
		slog.Error("jaeger spans", "err", err)
	}

	return nil
}

// exportQuery streams a SQL query page-by-page directly into a gzip-compressed TSV file,
// optionally deriving and writing a lite TSV in the same pass.
func exportQuery(ctx context.Context, db *sql.DB, rawDir, rawPrefix, query string, lite *liteHandler) error {
	rawPath := filepath.Join(rawDir, rawPrefix+".tsv.gz")
	base := stripLimitOffset(query)

	rawFile, err := os.Create(rawPath)
	if err != nil {
		return fmt.Errorf("create %s: %w", rawPath, err)
	}
	defer rawFile.Close()

	rawGz := gzip.NewWriter(rawFile)
	defer rawGz.Close()

	rawWriter := csv.NewWriter(rawGz)
	rawWriter.Comma = '\t'
	rawWriter.UseCRLF = false

	var (
		liteGz     *gzip.Writer
		liteWriter *csv.Writer
		litePath   string
		liteTotal  int
	)

	if lite != nil {
		litePath = filepath.Join(lite.dir, lite.prefix+".tsv.gz")
		f, err := os.Create(litePath)
		if err != nil {
			return fmt.Errorf("create %s: %w", litePath, err)
		}
		defer f.Close()

		liteGz = gzip.NewWriter(f)
		defer liteGz.Close()

		liteWriter = csv.NewWriter(liteGz)
		liteWriter.Comma = '\t'
		liteWriter.UseCRLF = false
		if err := liteWriter.Write(lite.header); err != nil {
			return err
		}
	}

	var (
		colNames []string
		colIdx   map[string]int
		rawTotal int
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
			colIdx = make(map[string]int, len(colNames))
			for i, c := range colNames {
				colIdx[c] = i
			}
			if err := rawWriter.Write(colNames); err != nil {
				rows.Close()
				return err
			}
		}

		vals := make([]any, len(colNames))
		ptrs := make([]any, len(colNames))
		for i := range vals {
			ptrs[i] = &vals[i]
		}
		rawRow := make([]string, len(colNames))

		var batchCount int
		for rows.Next() {
			if err := rows.Scan(ptrs...); err != nil {
				rows.Close()
				return fmt.Errorf("scan: %w", err)
			}
			for i, v := range vals {
				rawRow[i] = formatVal(v)
			}
			if err := rawWriter.Write(rawRow); err != nil {
				rows.Close()
				return err
			}
			rawTotal++
			batchCount++

			if lite != nil {
				if liteRow, ok := lite.derive(colIdx, vals); ok {
					if err := liteWriter.Write(liteRow); err != nil {
						rows.Close()
						return err
					}
					liteTotal++
				}
			}
		}
		if err := rows.Err(); err != nil {
			rows.Close()
			return err
		}
		rows.Close()

		if batchCount < batchSize {
			break
		}
	}

	rawWriter.Flush()
	if err := rawWriter.Error(); err != nil {
		return err
	}
	if err := rawGz.Close(); err != nil {
		return fmt.Errorf("close gzip %s: %w", rawPath, err)
	}

	if rawTotal == 0 {
		_ = os.Remove(rawPath)
		slog.Info("no rows", "prefix", rawPrefix)
	} else {
		slog.Info("wrote", "file", rawPath, "rows", rawTotal)
	}

	if lite != nil {
		liteWriter.Flush()
		if err := liteWriter.Error(); err != nil {
			return err
		}
		if err := liteGz.Close(); err != nil {
			return fmt.Errorf("close gzip %s: %w", litePath, err)
		}
		if liteTotal == 0 {
			_ = os.Remove(litePath)
			slog.Info("no rows", "prefix", lite.prefix)
		} else {
			slog.Info("wrote", "file", litePath, "rows", liteTotal)
		}
	}

	return nil
}

func formatVal(v any) string {
	if v == nil {
		return ""
	}
	switch val := v.(type) {
	case string:
		return val
	case []byte:
		return string(val)
	default:
		return fmt.Sprintf("%v", val)
	}
}

func getMapKey(v any, key string) string {
	switch m := v.(type) {
	case map[string]string:
		return m[key]
	case map[string]any:
		if val, ok := m[key]; ok {
			return formatVal(val)
		}
	}
	return ""
}

func toInt(v any) int64 {
	switch val := v.(type) {
	case int:
		return int64(val)
	case int8:
		return int64(val)
	case int16:
		return int64(val)
	case int32:
		return int64(val)
	case int64:
		return val
	case uint:
		return int64(val)
	case uint8:
		return int64(val)
	case uint16:
		return int64(val)
	case uint32:
		return int64(val)
	case uint64:
		return int64(val)
	case string:
		n, _ := strconv.ParseInt(val, 10, 64)
		return n
	default:
		return 0
	}
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
