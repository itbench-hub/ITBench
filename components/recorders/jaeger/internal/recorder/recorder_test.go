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
	image = "quay.io/jaegertracing/jaeger:2.20.0"

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

	if err := seedSpans(otlpEndpoint); err != nil {
		t.Fatalf("seed spans: %v", err)
	}

	if err := waitForService(ctx, grpcEndpoint, testService, 15*time.Second); err != nil {
		t.Fatalf("service %q did not appear: %v", testService, err)
	}

	outDir := t.TempDir()
	if err := recorder.Run(ctx, grpcEndpoint, outDir); err != nil {
		t.Fatalf("recorder.Run: %v", err)
	}

	entries, err := os.ReadDir(outDir)
	if err != nil {
		t.Fatalf("read output dir: %v", err)
	}
	if len(entries) != 1 {
		t.Fatalf("expected 1 output file, got %d", len(entries))
	}

	data, err := os.ReadFile(filepath.Join(outDir, entries[0].Name()))
	if err != nil {
		t.Fatalf("read output file: %v", err)
	}

	var spans []map[string]any
	if err := json.Unmarshal(data, &spans); err != nil {
		t.Fatalf("parse output JSON: %v", err)
	}
	if len(spans) == 0 {
		t.Error("expected at least one span in output, got none")
	}

	// Verify the seeded operation name is present in at least one span.
	// model.Span serialises as "operation_name" per its protobuf JSON tag.
	found := false
	for _, s := range spans {
		if s["operation_name"] == testOperation {
			found = true
			break
		}
	}
	if !found {
		t.Errorf("expected span with operation_name=%q in output", testOperation)
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
