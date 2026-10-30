package recorder_test

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"

	"github.com/itbench-hub/ITBench/components/recorders/prometheus/internal/recorder"
)

const image = "quay.io/prometheus/prometheus:v3.15.1@sha256:fa3302279710be2f21a8301ec17a8b4f2301fd829bd113839b3b6b02b6f191a2"

// prometheusConfig is a minimal Prometheus configuration that defines one
// alerting rule which fires immediately (expr: 1 == 1), and scrapes itself with
// pod and namespace labels so that the metrics export has a pod series to find.
const prometheusConfig = `
global:
  scrape_interval: 1s
  evaluation_interval: 1s

rule_files:
  - /etc/prometheus/rules.yml

scrape_configs:
  - job_name: self
    static_configs:
      - targets: ["localhost:9090"]
        labels:
          namespace: test-ns
          pod: test-pod
`

const prometheusRules = `
groups:
  - name: integration
    rules:
      - alert: AlwaysFiring
        expr: vector(1)
        labels:
          severity: critical
        annotations:
          summary: "Integration test alert"
`

func TestRun(t *testing.T) {
	ctx := context.Background()

	// Write config and rules to temp files so testcontainers can mount them.
	cfgFile := writeTempFile(t, "prometheus.yml", prometheusConfig)
	rulesFile := writeTempFile(t, "rules.yml", prometheusRules)

	ctr, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
		ContainerRequest: testcontainers.ContainerRequest{
			Image:        image,
			ExposedPorts: []string{"9090/tcp"},
			Files: []testcontainers.ContainerFile{
				{HostFilePath: cfgFile, ContainerFilePath: "/etc/prometheus/prometheus.yml", FileMode: 0o444},
				{HostFilePath: rulesFile, ContainerFilePath: "/etc/prometheus/rules.yml", FileMode: 0o444},
			},
			Cmd: []string{
				"--config.file=/etc/prometheus/prometheus.yml",
				"--storage.tsdb.path=/prometheus",
			},
			WaitingFor: wait.ForHTTP("/-/ready").WithPort("9090/tcp").WithStartupTimeout(60 * time.Second),
		},
		Started: true,
	})
	if err != nil {
		t.Fatalf("start prometheus container: %v", err)
	}
	t.Cleanup(func() { _ = ctr.Terminate(ctx) })

	endpoint, err := ctr.PortEndpoint(ctx, "9090/tcp", "http")
	if err != nil {
		t.Fatalf("get endpoint: %v", err)
	}

	// Wait for AlwaysFiring to transition to firing state.
	if err := waitForFiringAlert(ctx, endpoint, "AlwaysFiring", 30*time.Second); err != nil {
		t.Fatalf("alert did not fire: %v", err)
	}

	outDir := t.TempDir()
	now := time.Now().UTC()
	t1 := now
	t2 := now.Add(3 * time.Second)

	// Wait until both snapshot timestamps are in the past, so that the ALERTS series
	// and the scraped samples between them have been recorded.
	time.Sleep(time.Until(t2) + 2*time.Second)

	namespaces := []string{"test-ns"}
	if err := recorder.Run(ctx, endpoint, "", outDir, namespaces, t1, t2); err != nil {
		t.Fatalf("recorder.Run: %v", err)
	}

	// The metrics of a snapshot are written to the snapshot_at_<timestamp> directory.
	// The first snapshot is the recording start, so only the second one has a window.
	assertFileNotEmpty(t, filepath.Join(outDir, "snapshot_at_"+t2.Format("2006-01-02T15-04-05.000000"), "raw", "metrics_pod", "pod_test-pod_raw.tsv"))

	entries, err := os.ReadDir(outDir)
	if err != nil {
		t.Fatalf("read output dir: %v", err)
	}
	var alertFiles []os.DirEntry
	for _, entry := range entries {
		if !entry.IsDir() {
			alertFiles = append(alertFiles, entry)
		}
	}
	if len(alertFiles) != 2 {
		t.Fatalf("expected 2 alert files for 2 snapshots, got %d", len(alertFiles))
	}

	for _, entry := range alertFiles {
		data, err := os.ReadFile(filepath.Join(outDir, entry.Name()))
		if err != nil {
			t.Fatalf("read output: %v", err)
		}

		var alerts []recorder.AlertSnapshot
		if err := json.Unmarshal(data, &alerts); err != nil {
			t.Fatalf("parse output JSON: %v", err)
		}
		if len(alerts) == 0 {
			t.Fatalf("expected at least one firing alert in output file %s, got none", entry.Name())
		}

		found := false
		for _, a := range alerts {
			if a.Labels["alertname"] == "AlwaysFiring" {
				found = true
				if a.State != "firing" {
					t.Errorf("expected state to be firing, got %s", a.State)
				}
				break
			}
		}
		if !found {
			t.Errorf("expected AlwaysFiring alert in output file %s, got: %s", entry.Name(), string(data))
		}
	}
}

// waitForFiringAlert polls Prometheus /api/v1/alerts directly (not via the
// recorder) until the named alert reaches firing state or the timeout expires.
// This is purely a test setup barrier — it ensures data is available before
// recorder.Run is called.
func waitForFiringAlert(ctx context.Context, endpoint, alertName string, timeout time.Duration) error {
	type response struct {
		Data struct {
			Alerts []struct {
				Labels map[string]string `json:"labels"`
				State  string            `json:"state"`
			} `json:"alerts"`
		} `json:"data"`
	}

	client := &http.Client{Timeout: 5 * time.Second}
	deadline := time.Now().Add(timeout)
	for time.Now().Before(deadline) {
		req, _ := http.NewRequestWithContext(ctx, http.MethodGet, endpoint+"/api/v1/alerts", nil)
		resp, err := client.Do(req)
		if err == nil {
			body, _ := io.ReadAll(resp.Body)
			resp.Body.Close()
			var ar response
			if json.Unmarshal(body, &ar) == nil {
				for _, a := range ar.Data.Alerts {
					if a.Labels["alertname"] == alertName && a.State == "firing" {
						return nil
					}
				}
			}
		}
		time.Sleep(500 * time.Millisecond)
	}
	return fmt.Errorf("alert %q did not reach firing state within %s", alertName, timeout)
}

func assertFileNotEmpty(t *testing.T, path string) {
	t.Helper()
	info, err := os.Stat(path)
	if err != nil {
		t.Errorf("expected file %s: %v", path, err)
		return
	}
	if info.Size() == 0 {
		t.Errorf("file %s is empty", path)
	}
}

func writeTempFile(t *testing.T, name, content string) string {
	t.Helper()
	dir := t.TempDir()
	path := filepath.Join(dir, name)
	if err := os.WriteFile(path, []byte(content), 0o644); err != nil {
		t.Fatalf("write temp file %s: %v", name, err)
	}
	return path
}
