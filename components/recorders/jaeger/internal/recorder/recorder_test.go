package recorder_test

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"testing"
	"time"

	api_v2 "github.com/jaegertracing/jaeger-idl/proto-gen/api_v2"
	"github.com/testcontainers/testcontainers-go"
	"github.com/testcontainers/testcontainers-go/wait"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"

	"github.com/itbench-hub/ITBench/components/recorders/jaeger/internal/recorder"
)

const (
	// Same image as the live deployment in install_opentelemetry_collectors.yaml.
	image = "quay.io/jaegertracing/jaeger:2.21.0@sha256:3d0ac795ff98aa04d1be04311d2dac6c25b4bfc8322dc02e53bc5b170c5018c3"

	otlpHTTPPort  = "4318/tcp"
	grpcQueryPort = "16685/tcp"

	testService   = "recorder-integration-svc"
	testOperation = "GET /integration"
)

func TestRun(t *testing.T) {
	ctx := context.Background()

	ctr, err := testcontainers.GenericContainer(ctx, testcontainers.GenericContainerRequest{
		ContainerRequest: testcontainers.ContainerRequest{
			Image:        image,
			ExposedPorts: []string{otlpHTTPPort, grpcQueryPort},
			Env: map[string]string{
				"COLLECTOR_OTLP_ENABLED": "true",
			},
			WaitingFor: wait.ForListeningPort(grpcQueryPort).WithStartupTimeout(60 * time.Second),
		},
		Started: true,
	})
	if err != nil {
		t.Fatalf("start jaeger container: %v", err)
	}
	t.Cleanup(func() { _ = ctr.Terminate(ctx) })

	otlpEndpoint, err := ctr.PortEndpoint(ctx, otlpHTTPPort, "http")
	if err != nil {
		t.Fatalf("get otlp endpoint: %v", err)
	}

	grpcEndpoint, err := ctr.PortEndpoint(ctx, grpcQueryPort, "")
	if err != nil {
		t.Fatalf("get grpc endpoint: %v", err)
	}

	seedTime := time.Now().UTC()
	if err := seedSpans(otlpEndpoint); err != nil {
		t.Fatalf("seed spans: %v", err)
	}

	if err := waitForService(ctx, grpcEndpoint, testService, 15*time.Second); err != nil {
		t.Fatalf("service %q did not appear: %v", testService, err)
	}

	outDir := t.TempDir()
	// Both query timestamps are after seedTime, so seedTime falls in [t - 5m, t] for both
	t1 := seedTime.Add(2 * time.Second)
	t2 := seedTime.Add(4 * time.Second)

	if err := recorder.Run(ctx, grpcEndpoint, outDir, t1, t2); err != nil {
		t.Fatalf("recorder.Run: %v", err)
	}

	entries, err := os.ReadDir(outDir)
	if err != nil {
		t.Fatalf("read output dir: %v", err)
	}
	if len(entries) != 2 {
		t.Fatalf("expected 2 output files for 2 snapshots, got %d", len(entries))
	}

	for _, entry := range entries {
		data, err := os.ReadFile(filepath.Join(outDir, entry.Name()))
		if err != nil {
			t.Fatalf("read output file: %v", err)
		}

		var spans []map[string]any
		if err := json.Unmarshal(data, &spans); err != nil {
			t.Fatalf("parse output JSON: %v", err)
		}
		if len(spans) == 0 {
			t.Errorf("expected at least one span in output file %s, got none", entry.Name())
		}

		found := false
		for _, s := range spans {
			if s["operation_name"] == testOperation {
				found = true
				break
			}
		}
		if !found {
			t.Errorf("expected span with operation_name=%q in output file %s", testOperation, entry.Name())
		}
	}
}

// seedSpans sends one OTLP trace to Jaeger via HTTP so the recorder has data
// to collect. Uses stdlib net/http — no extra dependency required.
func seedSpans(otlpEndpoint string) error {
	now := time.Now()
	body := map[string]any{
		"resourceSpans": []any{
			map[string]any{
				"resource": map[string]any{
					"attributes": []any{
						map[string]any{
							"key":   "service.name",
							"value": map[string]any{"stringValue": testService},
						},
					},
				},
				"scopeSpans": []any{
					map[string]any{
						"spans": []any{
							map[string]any{
								"traceId":           "0af7651916cd43dd8448eb211c80319c",
								"spanId":            "b7ad6b7169203331",
								"name":              testOperation,
								"kind":              2,
								"startTimeUnixNano": fmt.Sprintf("%d", now.Add(-time.Second).UnixNano()),
								"endTimeUnixNano":   fmt.Sprintf("%d", now.UnixNano()),
								"status":            map[string]any{"code": 1},
							},
						},
					},
				},
			},
		},
	}

	b, err := json.Marshal(body)
	if err != nil {
		return err
	}

	resp, err := http.Post(otlpEndpoint+"/v1/traces", "application/json", bytes.NewReader(b))
	if err != nil {
		return fmt.Errorf("POST /v1/traces: %w", err)
	}
	defer resp.Body.Close()

	if resp.StatusCode != http.StatusOK {
		return fmt.Errorf("OTLP ingest returned HTTP %d", resp.StatusCode)
	}
	return nil
}

// waitForService polls the Jaeger gRPC QueryService until the given service
// name appears in GetServices, or the timeout is exceeded.
func waitForService(ctx context.Context, grpcEndpoint, service string, timeout time.Duration) error {
	conn, err := grpc.NewClient(grpcEndpoint, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return fmt.Errorf("dial: %w", err)
	}
	defer conn.Close()

	client := api_v2.NewQueryServiceClient(conn)
	deadline := time.Now().Add(timeout)

	for time.Now().Before(deadline) {
		resp, err := client.GetServices(ctx, &api_v2.GetServicesRequest{})
		if err == nil {
			for _, svc := range resp.GetServices() {
				if svc == service {
					return nil
				}
			}
		}
		time.Sleep(500 * time.Millisecond)
	}
	return fmt.Errorf("timed out after %s", timeout)
}
