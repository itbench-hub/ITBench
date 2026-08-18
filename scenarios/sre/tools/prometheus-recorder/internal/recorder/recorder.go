package recorder

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"time"

	prometheusapi "github.com/prometheus/client_golang/api"
	prometheusv1 "github.com/prometheus/client_golang/api/prometheus/v1"
)

// Run fetches firing alerts from Prometheus and writes them as JSON to outputDir.
// endpoint is the full HTTP URL of the Prometheus server (e.g. "http://prometheus:9090").
// token is an optional Bearer token; pass empty string if not needed.
func Run(ctx context.Context, endpoint, token, outputDir string) error {
	client, err := prometheusapi.NewClient(prometheusapi.Config{
		Address:      endpoint,
		RoundTripper: newRoundTripper(token),
	})
	if err != nil {
		return fmt.Errorf("create prometheus client: %w", err)
	}

	api := prometheusv1.NewAPI(client)

	result, err := api.Alerts(ctx)
	if err != nil {
		return fmt.Errorf("query alerts: %w", err)
	}

	firing := make([]prometheusv1.Alert, 0)
	for _, a := range result.Alerts {
		if a.State == prometheusv1.AlertStateFiring {
			firing = append(firing, a)
		}
	}

	slog.Info("alerts retrieved", "total", len(result.Alerts), "firing", len(firing))

	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", outputDir, err)
	}

	timestamp := time.Now().UTC().Format("2006-01-02T15-04-05.000000")
	path := filepath.Join(outputDir, fmt.Sprintf("alerts_at_%s.json", timestamp))

	f, err := os.Create(path)
	if err != nil {
		return fmt.Errorf("create %s: %w", path, err)
	}
	defer f.Close()

	enc := json.NewEncoder(f)
	enc.SetIndent("", "    ")
	if err := enc.Encode(firing); err != nil {
		return fmt.Errorf("encode alerts: %w", err)
	}

	slog.Info("wrote alerts", "file", path, "count", len(firing))
	return nil
}

// roundTripper wraps http.DefaultTransport and injects a Bearer token when set.
type roundTripper struct {
	token string
	inner http.RoundTripper
}

func newRoundTripper(token string) http.RoundTripper {
	if token == "" {
		return prometheusapi.DefaultRoundTripper
	}
	return &roundTripper{token: token, inner: prometheusapi.DefaultRoundTripper}
}

func (rt *roundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
	req = req.Clone(req.Context())
	req.Header.Set("Authorization", rt.token)
	return rt.inner.RoundTrip(req)
}
