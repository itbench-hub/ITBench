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
		return exportSnapshot(ctx, defaultDB, jaegerDB, outputDir, namespaces, nil)
	}

	for i, ts := range timestamps {
		targetDir := filepath.Join(outputDir, "snapshots", ts.UTC().Format("2006-01-02T15-04-05.000000"))
		slog.Info("exporting snapshot", "snapshot", ts.UTC().Format(time.RFC3339), "index", i+1, "total", len(timestamps))
		if err := exportSnapshot(ctx, defaultDB, jaegerDB, targetDir, namespaces, &ts); err != nil {
			return err
		}
	}

	return nil
}

type filterHandler struct {
	dir    string
	prefix string
	header []string
	derive func(colIdx map[string]int, vals []any) ([]string, bool)
}

func exportSnapshot(ctx context.Context, defaultDB, jaegerDB *sql.DB, baseDir string, namespaces []string, maxTime *time.Time) error {
	nsSet := make(map[string]bool, len(namespaces))
	for _, ns := range namespaces {
		nsSet[ns] = true
	}

	if err := os.MkdirAll(baseDir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", baseDir, err)
	}

	timeFilter := "1=1"
	tracesTimeFilter := "1=1"
	if maxTime != nil {
		t := maxTime.UTC().Format("2006-01-02 15:04:05.000000000")
		timeFilter = fmt.Sprintf("Timestamp <= '%s'", t)
		tracesTimeFilter = fmt.Sprintf("start_time <= '%s'", t)
	}

	if err := exportQuery(ctx, defaultDB, baseDir, "k8s_events",
		fmt.Sprintf(`SELECT * FROM kubernetes.events WHERE %s ORDER BY Timestamp ASC`, timeFilter),
		&filterHandler{
			dir:    baseDir,
			prefix: "k8s_events_filtered",
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

	if err := exportQuery(ctx, defaultDB, baseDir, "k8s_topology_objects",
		fmt.Sprintf(`SELECT * FROM kubernetes.topology WHERE %s ORDER BY Timestamp ASC`, timeFilter), nil); err != nil {
		slog.Warn("k8s topology objects (table may not exist)", "err", err)
	}

	if err := exportQuery(ctx, defaultDB, baseDir, "k8s_topology_graph",
		fmt.Sprintf(`SELECT * FROM kubernetes.topology_graph WHERE %s ORDER BY Timestamp ASC, Seq ASC`, timeFilter), nil); err != nil {
		slog.Warn("k8s topology graph (table may not exist)", "err", err)
	}

	if err := exportQuery(ctx, defaultDB, baseDir, "k8s_infrastructure",
		fmt.Sprintf(`SELECT * FROM kubernetes.infrastructure WHERE %s ORDER BY Timestamp ASC`, timeFilter),
		&filterHandler{
			dir:    baseDir,
			prefix: "k8s_infrastructure_filtered",
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

	if err := exportQuery(ctx, defaultDB, baseDir, "otel_logs",
		fmt.Sprintf(`SELECT * FROM opentelemetry_demo.logs WHERE %s ORDER BY Timestamp ASC`, timeFilter),
		&filterHandler{
			dir:    baseDir,
			prefix: "otel_logs_filtered",
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

	if err := exportQuery(ctx, jaegerDB, baseDir, "jaeger_spans",
		fmt.Sprintf(`SELECT * FROM spans WHERE %s ORDER BY start_time ASC`, tracesTimeFilter),
		&filterHandler{
			dir:    baseDir,
			prefix: "jaeger_spans_filtered",
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
func exportQuery(ctx context.Context, db *sql.DB, baseDir, rawPrefix, query string, filtered *filterHandler) error {
	rawPath := filepath.Join(baseDir, rawPrefix+".tsv.gz")
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
		filteredGz     *gzip.Writer
		filteredWriter *csv.Writer
		filteredPath   string
		filteredTotal  int
	)

	if filtered != nil {
		filteredPath = filepath.Join(filtered.dir, filtered.prefix+".tsv.gz")
		f, err := os.Create(filteredPath)
		if err != nil {
			return fmt.Errorf("create %s: %w", filteredPath, err)
		}
		defer f.Close()

		filteredGz = gzip.NewWriter(f)
		defer filteredGz.Close()

		filteredWriter = csv.NewWriter(filteredGz)
		filteredWriter.Comma = '\t'
		filteredWriter.UseCRLF = false
		if err := filteredWriter.Write(filtered.header); err != nil {
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

			if filtered != nil {
				if filteredRow, ok := filtered.derive(colIdx, vals); ok {
					if err := filteredWriter.Write(filteredRow); err != nil {
						rows.Close()
						return err
					}
					filteredTotal++
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
		slog.Debug("no rows", "prefix", rawPrefix)
	} else {
		slog.Info("wrote", "file", rawPath, "rows", rawTotal)
	}

	if filtered != nil {
		filteredWriter.Flush()
		if err := filteredWriter.Error(); err != nil {
			return err
		}
		if err := filteredGz.Close(); err != nil {
			return fmt.Errorf("close gzip %s: %w", filteredPath, err)
		}
		if filteredTotal == 0 {
			_ = os.Remove(filteredPath)
			slog.Debug("no rows", "prefix", filtered.prefix)
		} else {
			slog.Info("wrote", "file", filteredPath, "rows", filteredTotal)
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
