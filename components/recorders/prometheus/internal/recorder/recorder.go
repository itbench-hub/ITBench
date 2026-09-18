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
	"github.com/prometheus/common/model"
)

// Run fetches firing alerts from Prometheus and writes them as JSON to outputDir.
// endpoint is the full HTTP URL of the Prometheus server (e.g. "http://prometheus:9090").
// token is an optional Bearer token; pass empty string if not needed.
// AlertSnapshot represents a point-in-time snapshot of an alert.
type AlertSnapshot struct {
	Labels      map[string]string `json:"labels"`
	Annotations map[string]string `json:"annotations,omitempty"`
	State       string            `json:"state"`
	Value       string            `json:"value"`
}

// Run fetches alerts from Prometheus for the given timestamps and writes them as JSON to outputDir.
// If timestamps is empty, it queries the ALERTS metric at the current time.
func Run(ctx context.Context, endpoint, token, outputDir string, timestamps ...time.Time) error {
	if len(timestamps) == 0 {
		timestamps = []time.Time{time.Now().UTC()}
	}

	client, err := prometheusapi.NewClient(prometheusapi.Config{
		Address:      endpoint,
		RoundTripper: newRoundTripper(token),
	})
	if err != nil {
		return fmt.Errorf("create prometheus client: %w", err)
	}

	api := prometheusv1.NewAPI(client)

	if err := os.MkdirAll(outputDir, 0o755); err != nil {
		return fmt.Errorf("mkdir %s: %w", outputDir, err)
	}

	for _, ts := range timestamps {
		if err := queryAndWriteSnapshot(ctx, api, ts, outputDir); err != nil {
			return err
		}
	}

	return nil
}

func queryAndWriteSnapshot(ctx context.Context, api prometheusv1.API, ts time.Time, outputDir string) error {
	val, warnings, err := api.Query(ctx, `ALERTS{alertstate="firing"}`, ts)
	if err != nil {
		return fmt.Errorf("query alerts at %s: %w", ts.Format(time.RFC3339), err)
	}
	if len(warnings) > 0 {
		slog.Warn("query warnings", "warnings", warnings)
	}

	var firing []AlertSnapshot
	if vec, ok := val.(model.Vector); ok {
		firing = make([]AlertSnapshot, 0, len(vec))
		for _, sample := range vec {
			labels := make(map[string]string, len(sample.Metric))
			for k, v := range sample.Metric {
				labels[string(k)] = string(v)
			}
			firing = append(firing, AlertSnapshot{
				Labels: labels,
				State:  labels["alertstate"],
				Value:  sample.Value.String(),
			})
		}
	} else {
		firing = []AlertSnapshot{}
	}

	formattedTS := ts.UTC().Format("2006-01-02T15-04-05.000000")
	path := filepath.Join(outputDir, fmt.Sprintf("alerts_at_%s.json", formattedTS))

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

	slog.Info("wrote alerts", "timestamp", ts.Format(time.RFC3339), "file", path, "count", len(firing))
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
