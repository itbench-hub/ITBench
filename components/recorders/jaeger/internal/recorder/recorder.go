package recorder

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"os"
	"path/filepath"
	"slices"
	"sync"
	"time"

	api_v2 "github.com/jaegertracing/jaeger-idl/proto-gen/api_v2"
	model "github.com/jaegertracing/jaeger-idl/model/v1"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

const (
	// lookbackWindow is how far back in time the recorder searches for traces.
	lookbackWindow = 5 * time.Minute

	// maxTracesPerOperation caps the number of traces fetched per service/operation pair.
	maxTracesPerOperation = 1

	// workerCount controls how many service/operation pairs are queried concurrently.
	workerCount = 10
)

// Run connects to Jaeger at endpoint via gRPC, fetches one trace per
// service/operation pair from the last 5 minutes, and writes them as a
// JSON array to outputDir/traces_at_<timestamp>.json.
//
// endpoint must be host:port (e.g. "jaeger-query:16686"). TLS is not
// required — the recorder uses insecure credentials suitable for in-cluster use.
func Run(ctx context.Context, endpoint, outputDir string, timestamps ...time.Time) error {
	conn, err := grpc.NewClient(endpoint, grpc.WithTransportCredentials(insecure.NewCredentials()))
	if err != nil {
		return fmt.Errorf("dial %s: %w", endpoint, err)
	}
	defer conn.Close()

	return run(ctx, api_v2.NewQueryServiceClient(conn), outputDir, timestamps...)
}

// run is the testable core: it accepts a QueryServiceClient so tests can
// inject an in-process server without a real network connection.
func run(ctx context.Context, client api_v2.QueryServiceClient, outputDir string, timestamps ...time.Time) error {
	if len(timestamps) == 0 {
		timestamps = []time.Time{time.Now().UTC()}
	}

	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", outputDir, err)
	}

	for _, ts := range timestamps {
		if err := queryAndWriteSnapshot(ctx, client, ts, outputDir); err != nil {
			return err
		}
	}

	return nil
}

func queryAndWriteSnapshot(ctx context.Context, client api_v2.QueryServiceClient, ts time.Time, outputDir string) error {
	startMax := ts.UTC()
	startMin := startMax.Add(-lookbackWindow)

	// ── 1. Discover services ────────────────────────────────────────────────
	svcResp, err := client.GetServices(ctx, &api_v2.GetServicesRequest{})
	if err != nil {
		return fmt.Errorf("GetServices: %w", err)
	}
	services := svcResp.GetServices()
	slog.Info("retrieved services", "timestamp", ts.Format(time.RFC3339), "count", len(services))

	// ── 2. Discover operations per service ──────────────────────────────────
	type work struct {
		service   string
		operation string
	}
	var jobs []work

	for _, svc := range services {
		opResp, err := client.GetOperations(ctx, &api_v2.GetOperationsRequest{Service: svc})
		if err != nil {
			slog.Warn("GetOperations failed", "service", svc, "err", err)
			continue
		}
		ops := opResp.GetOperations()
		jobs = slices.Grow(jobs, len(ops))
		for _, op := range ops {
			if opName := op.GetName(); opName != "" {
				jobs = append(jobs, work{service: svc, operation: opName})
			}
		}
	}
	slog.Info("operation/service pairs to query", "timestamp", ts.Format(time.RFC3339), "count", len(jobs))

	// ── 3. Fan-out: fetch spans concurrently ────────────────────────────────
	var (
		mu    sync.Mutex
		spans []model.Span
		wg    sync.WaitGroup
		sem   = make(chan struct{}, workerCount)
	)

	for _, j := range jobs {
		wg.Add(1)
		sem <- struct{}{}
		go func(j work) {
			defer wg.Done()
			defer func() { <-sem }()

			chunk, err := fetchSpans(ctx, client, j.service, j.operation, startMin, startMax)
			if err != nil {
				slog.Warn("FindTraces failed", "service", j.service, "operation", j.operation, "err", err)
				return
			}
			if len(chunk) > 0 {
				mu.Lock()
				spans = append(spans, chunk...)
				mu.Unlock()
			}
		}(j)
	}
	wg.Wait()

	slog.Info("total spans collected", "timestamp", ts.Format(time.RFC3339), "count", len(spans))

	// ── 4. Write output ─────────────────────────────────────────────────────
	if len(spans) == 0 {
		slog.Info("no spans found, skipping file write", "timestamp", ts.Format(time.RFC3339))
		return nil
	}

	formattedTS := ts.UTC().Format("2006-01-02T15-04-05.000000")
	path := filepath.Join(outputDir, fmt.Sprintf("traces_at_%s.json", formattedTS))

	f, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "    ")
	if err := enc.Encode(spans); err != nil {
		return fmt.Errorf("encode spans: %w", err)
	}

	slog.Info("wrote traces", "timestamp", ts.Format(time.RFC3339), "file", path, "spans", len(spans))
	return nil
}

// fetchSpans calls FindTraces and collects all spans from all streamed
// SpansResponseChunk messages.
func fetchSpans(
	ctx context.Context,
	client api_v2.QueryServiceClient,
	service, operation string,
	startMin, startMax time.Time,
) ([]model.Span, error) {
	req := &api_v2.FindTracesRequest{
		Query: &api_v2.TraceQueryParameters{
			ServiceName:   service,
			OperationName: operation,
			StartTimeMin:  startMin,
			StartTimeMax:  startMax,
			SearchDepth:   maxTracesPerOperation,
		},
	}

	stream, err := client.FindTraces(ctx, req)
	if err != nil {
		return nil, err
	}

	var result []model.Span
	for {
		chunk, err := stream.Recv()
		if err == io.EOF {
			break
		}
		if err != nil {
			return nil, err
		}
		result = append(result, chunk.GetSpans()...)
	}
	return result, nil
}
