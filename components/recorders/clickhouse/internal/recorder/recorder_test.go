package recorder_test

import (
	"context"
	"database/sql"
	"encoding/csv"
	"os"
	"path/filepath"
	"testing"
	"time"

	ch "github.com/ClickHouse/clickhouse-go/v2"
	"github.com/testcontainers/testcontainers-go/modules/clickhouse"

	"github.com/itbench-hub/ITBench/components/recorders/clickhouse/internal/recorder"
)

const (
	image        = "docker.io/clickhouse/clickhouse-server:26.8.9@sha256:85ddbad63bd6779d4b3c64af17a0720c85e9dc6e5fa636f80bfdbb6096bdc5ab"
	testPassword = "testpassword" // pragma: allowlist secret
)

func TestRun(t *testing.T) {
	ctx := context.Background()

	ctr, err := clickhouse.Run(ctx, image,
		clickhouse.WithPassword(testPassword),
	)
	if err != nil {
		t.Fatalf("start clickhouse container: %v", err)
	}
	t.Cleanup(func() { _ = ctr.Terminate(ctx) })

	// ConnectionHost returns "host:mappedPort" for the native TCP port (9000).
	addr, err := ctr.ConnectionHost(ctx)
	if err != nil {
		t.Fatalf("get connection host: %v", err)
	}

	if err := seed(ctx, addr, testPassword); err != nil {
		t.Fatalf("seed: %v", err)
	}

	// recorder.Run appends :9000 to the host, so we pass addr directly as the
	// host argument by stripping the port — testcontainers maps 9000 to a
	// random port, so we need to override the addr in Run via a test-only helper.
	outDir := t.TempDir()
	if err := recorder.RunWithAddr(ctx, addr, "default", testPassword, outDir); err != nil {
		t.Fatalf("recorder.Run: %v", err)
	}

	// ── raw files must exist ──────────────────────────────────────────────
	for _, f := range []string{
		"raw/k8s_events_raw.tsv",
		"raw/k8s_objects_raw.tsv",
		"raw/otel_logs_raw.tsv",
		"raw/otel_traces_raw.tsv",
	} {
		assertFile(t, outDir, f)
	}

	// ── lite files must exist ─────────────────────────────────────────────
	for _, f := range []string{
		"lite/k8s_events.tsv",
		"lite/k8s_objects.tsv",
		"lite/otel_logs.tsv",
		"lite/otel_traces.tsv",
	} {
		assertFile(t, outDir, f)
	}

	// ── lite logs must only contain WARN/ERROR/FATAL rows ─────────────────
	assertLiteLogsFiltered(t, outDir)

	// ── test snapshot milestone mode ─────────────────────────────────────
	snapshotDir := t.TempDir()
	t1 := time.Date(2024, 1, 1, 0, 0, 0, 500000000, time.UTC)
	if err := recorder.RunWithAddr(ctx, addr, "default", testPassword, snapshotDir, t1); err != nil {
		t.Fatalf("recorder.Run with snapshot timestamp: %v", err)
	}

	snapSubDir := filepath.Join(snapshotDir, "snapshot_at_2024-01-01T00-00-00.500000")
	for _, f := range []string{
		"raw/k8s_events_raw.tsv",
		"lite/k8s_events.tsv",
	} {
		assertFile(t, snapSubDir, f)
	}
}

// seedDB opens a *sql.DB for DDL/DML seeding — same TCP options as the recorder.
// addr is host:port.
func seedDB(addr, password string) *sql.DB {
	return ch.OpenDB(&ch.Options{
		Protocol: ch.Native,
		Addr:     []string{addr},
		Auth: ch.Auth{
			Database: "default",
			Username: "default",
			Password: password,
		},
		DialTimeout: 10 * time.Second,
		ReadTimeout: 30 * time.Second,
	})
}

// seed creates the required tables and inserts representative rows.
// addr is host:port.
func seed(ctx context.Context, addr, password string) error {
	db := seedDB(addr, password)
	defer db.Close()

	ddl := []string{
		`CREATE DATABASE IF NOT EXISTS jaeger`,
		`CREATE DATABASE IF NOT EXISTS kubernetes`,
		`CREATE DATABASE IF NOT EXISTS otel_demo`,

		`CREATE TABLE IF NOT EXISTS kubernetes.events (
			Timestamp DateTime64(9),
			Body String,
			ResourceAttributes Map(String, String),
			LogAttributes Map(String, String)
		) ENGINE = MergeTree() ORDER BY Timestamp`,

		`CREATE TABLE IF NOT EXISTS kubernetes.objects_snapshot (
			Timestamp DateTime64(9),
			Body String,
			ResourceAttributes Map(String, String),
			LogAttributes Map(String, String)
		) ENGINE = MergeTree() ORDER BY Timestamp`,

		`CREATE TABLE IF NOT EXISTS otel_demo.logs (
			Timestamp DateTime64(9),
			TraceId String,
			SpanId String,
			TraceFlags UInt8,
			SeverityText String,
			SeverityNumber UInt8,
			ServiceName String,
			Body String,
			ResourceAttributes Map(String, String),
			LogAttributes Map(String, String)
		) ENGINE = MergeTree() ORDER BY Timestamp`,

		`CREATE TABLE IF NOT EXISTS jaeger.jaeger_spans (
			Timestamp DateTime64(9),
			TraceId String,
			SpanId String,
			ParentSpanId String,
			TraceState String,
			SpanName String,
			SpanKind String,
			ServiceName String,
			ScopeName String,
			ScopeVersion String,
			Duration UInt64,
			StatusCode String,
			StatusMessage String
		) ENGINE = MergeTree() ORDER BY Timestamp`,
	}

	for _, stmt := range ddl {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			return err
		}
	}

	dml := []string{
		`INSERT INTO kubernetes.events VALUES
			('2024-01-01 00:00:00', '{"type":"Normal"}', {'k8s.namespace.name': 'otel-demo'}, {})`,

		`INSERT INTO kubernetes.objects_snapshot VALUES
			('2024-01-01 00:00:00', '{"kind":"Pod"}', {'k8s.namespace.name': 'otel-demo'}, {'k8s.resource.name': 'Pod'})`,

		// INFO row — must NOT appear in lite export
		`INSERT INTO otel_demo.logs VALUES
			('2024-01-01 00:00:00', '', '', 0, 'INFO', 9, 'svc-a', 'info message', {}, {})`,
		// ERROR row — must appear in lite export
		`INSERT INTO otel_demo.logs VALUES
			('2024-01-01 00:00:01', '', '', 0, 'ERROR', 17, 'svc-a', 'error message', {}, {})`,

		// OK trace — must NOT appear in lite export
		`INSERT INTO jaeger.jaeger_spans VALUES
			('2024-01-01 00:00:00', 'tid1', 'sid1', '', '', 'op', 'SERVER', 'svc-a', '', '', 1000000, 'Ok', '')`,
		// Error trace — must appear in lite export
		`INSERT INTO jaeger.jaeger_spans VALUES
			('2024-01-01 00:00:01', 'tid2', 'sid2', '', '', 'op', 'SERVER', 'svc-a', '', '', 2000000, 'Error', 'failed')`,
	}

	for _, stmt := range dml {
		if _, err := db.ExecContext(ctx, stmt); err != nil {
			return err
		}
	}
	return nil
}

func assertFile(t *testing.T, outDir, rel string) {
	t.Helper()
	path := filepath.Join(outDir, rel)
	info, err := os.Stat(path)
	if err != nil {
		t.Errorf("expected file %s: %v", rel, err)
		return
	}
	if info.Size() == 0 {
		t.Errorf("file %s is empty", rel)
	}
}

// assertLiteLogsFiltered checks that lite/otel_logs.tsv contains only
// WARN/ERROR/FATAL rows and not INFO.
func assertLiteLogsFiltered(t *testing.T, outDir string) {
	t.Helper()
	path := filepath.Join(outDir, "lite", "otel_logs.tsv")
	f, err := os.Open(path)
	if err != nil {
		t.Fatalf("open lite logs: %v", err)
	}
	defer f.Close()

	r := csv.NewReader(f)
	r.Comma = '\t'
	records, err := r.ReadAll()
	if err != nil {
		t.Fatalf("parse lite logs tsv: %v", err)
	}

	// Find severity_text column index from header.
	if len(records) < 2 {
		t.Fatalf("lite logs tsv has fewer than 2 rows (header + data)")
	}
	sevCol := -1
	for i, h := range records[0] {
		if h == "severity_text" {
			sevCol = i
			break
		}
	}
	if sevCol < 0 {
		t.Fatalf("severity_text column not found in lite logs header")
	}

	for _, row := range records[1:] {
		sev := row[sevCol]
		if sev == "INFO" || sev == "DEBUG" || sev == "TRACE" {
			t.Errorf("lite logs contains unexpected severity %q", sev)
		}
	}
}
