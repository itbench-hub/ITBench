package recorder_test

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/itbench-hub/ITBench/scenarios/sre/tools/prometheus-recorder/internal/recorder"
)

// fakePrometheus returns an httptest.Server that serves the given alert JSON
// under /api/v1/alerts.
func fakePrometheus(t *testing.T, body string) *httptest.Server {
	t.Helper()
	return httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/v1/alerts" {
			http.NotFound(w, r)
			return
		}
		w.Header().Set("Content-Type", "application/json")
		_, _ = w.Write([]byte(body))
	}))
}

const (
	firingAlert = `{
		"status": "success",
		"data": {
			"alerts": [
				{"labels":{"alertname":"TestFiring"},"annotations":{},"state":"firing","activeAt":"2024-01-01T00:00:00Z","value":"1"},
				{"labels":{"alertname":"TestPending"},"annotations":{},"state":"pending","activeAt":"2024-01-01T00:00:00Z","value":"1"}
			]
		}
	}`

	noAlerts = `{"status":"success","data":{"alerts":[]}}`
)

func TestRun_FiringAlertWritten(t *testing.T) {
	srv := fakePrometheus(t, firingAlert)
	defer srv.Close()

	dir := t.TempDir()
	if err := recorder.Run(context.Background(), srv.URL, "", dir); err != nil {
		t.Fatalf("Run: %v", err)
	}

	entries, err := os.ReadDir(dir)
	if err != nil || len(entries) != 1 {
		t.Fatalf("expected 1 output file, got %d", len(entries))
	}

	data, err := os.ReadFile(filepath.Join(dir, entries[0].Name()))
	if err != nil {
		t.Fatalf("read output: %v", err)
	}

	var alerts []map[string]interface{}
	if err := json.Unmarshal(data, &alerts); err != nil {
		t.Fatalf("parse output: %v", err)
	}
	if len(alerts) != 1 {
		t.Errorf("expected 1 firing alert, got %d", len(alerts))
	}
	if alerts[0]["State"] != "firing" {
		t.Errorf("expected State=firing, got %v", alerts[0]["State"])
	}
}

func TestRun_PendingAlertExcluded(t *testing.T) {
	srv := fakePrometheus(t, firingAlert)
	defer srv.Close()

	dir := t.TempDir()
	if err := recorder.Run(context.Background(), srv.URL, "", dir); err != nil {
		t.Fatalf("Run: %v", err)
	}

	data, err := os.ReadFile(filepath.Join(dir, firstFile(t, dir)))
	if err != nil {
		t.Fatalf("read output: %v", err)
	}
	if strings.Contains(string(data), "pending") {
		t.Error("output contains a pending alert — should be excluded")
	}
}

func TestRun_NoAlerts_FileStillWritten(t *testing.T) {
	srv := fakePrometheus(t, noAlerts)
	defer srv.Close()

	dir := t.TempDir()
	if err := recorder.Run(context.Background(), srv.URL, "", dir); err != nil {
		t.Fatalf("Run: %v", err)
	}

	// Python writes even an empty array — Go should match.
	entries, err := os.ReadDir(dir)
	if err != nil || len(entries) != 1 {
		t.Fatalf("expected 1 output file even with no alerts, got %d", len(entries))
	}

	data, _ := os.ReadFile(filepath.Join(dir, entries[0].Name()))
	var alerts []interface{}
	if err := json.Unmarshal(data, &alerts); err != nil {
		t.Fatalf("parse output: %v", err)
	}
	if len(alerts) != 0 {
		t.Errorf("expected empty array, got %d items", len(alerts))
	}
}

func TestRun_HTTP500_ReturnsError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		http.Error(w, "internal error", http.StatusInternalServerError)
	}))
	defer srv.Close()

	dir := t.TempDir()
	if err := recorder.Run(context.Background(), srv.URL, "", dir); err == nil {
		t.Error("expected error on HTTP 500, got nil")
	}
}

func firstFile(t *testing.T, dir string) string {
	t.Helper()
	entries, err := os.ReadDir(dir)
	if err != nil || len(entries) == 0 {
		t.Fatalf("no files in output dir")
	}
	return entries[0].Name()
}
