package recorder

import (
	"context"
	"encoding/csv"
	"encoding/json"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"path/filepath"
	"strings"
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
// For every timestamp after the first, it also writes the pod and service metrics of namespaces
// recorded since the first timestamp into outputDir/snapshot_at_<timestamp>.
func Run(ctx context.Context, endpoint, token, outputDir string, namespaces []string, timestamps ...time.Time) error {
	if len(timestamps) == 0 {
		timestamps = []time.Time{time.Now().UTC()}
	}
	startTime := timestamps[0]

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
		snapshotDir := filepath.Join(outputDir, fmt.Sprintf("snapshot_at_%s", ts.UTC().Format("2006-01-02T15-04-05.000000")))
		if err := exportMetrics(ctx, api, snapshotDir, namespaces, startTime, ts); err != nil {
			return err
		}
	}

	return nil
}

func queryAndWriteSnapshot(ctx context.Context, api prometheusv1.API, ts time.Time, outputDir string) error {
	val, warnings, infos, err := api.Query(ctx, `ALERTS{alertstate="firing"}`, ts)
	if err != nil {
		return fmt.Errorf("query alerts at %s: %w", ts.Format(time.RFC3339), err)
	}
	if len(warnings) > 0 {
		slog.Warn("query warnings", "warnings", warnings)
	}
	if len(infos) > 0 {
		slog.Info("query infos", "infos", infos)
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

const sampleTimeFormat = "2006-01-02 15:04:05.000"

// serviceQuery selects one family of service series for a namespace.
type serviceQuery struct {
	selector     string // format string with one %q verb for the namespace
	namespaceKey string
	serviceKey   string
}

var serviceQueries = []serviceQuery{
	{
		selector:     `traces_span_metrics_duration_milliseconds_bucket{namespace=%q,service_name!~"flagd|load-generator"}`,
		namespaceKey: "namespace",
		serviceKey:   "service_name",
	},
	{
		selector:     `traces_span_metrics_calls_total{namespace=%q,service_name!~"flagd|load-generator",status_code="STATUS_CODE_ERROR"}`,
		namespaceKey: "namespace",
		serviceKey:   "service_name",
	},
	{
		selector:     `istio_request_duration_milliseconds_bucket{destination_workload_namespace=%q,destination_canonical_service!="load-generator"}`,
		namespaceKey: "destination_workload_namespace",
		serviceKey:   "destination_canonical_service",
	},
	{
		selector:     `istio_requests_total{destination_workload_namespace=%q,destination_canonical_service!="load-generator",response_code!~"2.*"}`,
		namespaceKey: "destination_workload_namespace",
		serviceKey:   "destination_canonical_service",
	},
}

// exportMetrics writes the pod and service metrics of the given namespaces for the window
// (start, ts] into baseDir. The files are written lazily, so series without samples create no file.
func exportMetrics(ctx context.Context, api prometheusv1.API, baseDir string, namespaces []string, start, ts time.Time) error {
	window := ts.Sub(start)
	if window <= 0 {
		slog.Info("skipping metrics, snapshot is not after the recording start", "timestamp", ts.Format(time.RFC3339))
		return nil
	}

	rawDir := filepath.Join(baseDir, "raw")
	liteDir := filepath.Join(baseDir, "lite")
	for _, d := range []string{
		filepath.Join(rawDir, "metrics_pod"), filepath.Join(rawDir, "metrics_service"),
		filepath.Join(liteDir, "metrics_pod"), filepath.Join(liteDir, "metrics_service"),
	} {
		if err := os.MkdirAll(d, 0o755); err != nil {
			return fmt.Errorf("mkdir %s: %w", d, err)
		}
	}

	rawPods, litePods := tsvSet{}, tsvSet{}
	rawServices, liteServices := tsvSet{}, tsvSet{}
	defer func() {
		rawPods.close()
		litePods.close()
		rawServices.close()
		liteServices.close()
	}()

	safeReplacer := strings.NewReplacer("/", "_", " ", "_")

	for _, ns := range namespaces {
		matrix, err := queryMatrix(ctx, api, fmt.Sprintf(`{namespace=%q,pod!=""}`, ns), window, ts)
		if err != nil {
			slog.Error("pod metrics export", "namespace", ns, "err", err)
		}
		for _, series := range matrix {
			name, tags := splitMetric(series.Metric)
			pod := tags["pod"]
			safePod := safeReplacer.Replace(pod)
			isLite := strings.Contains(name, "cpu") || strings.Contains(name, "memory") || strings.Contains(name, "mem")

			for _, sample := range series.Values {
				sampleTime := sample.Timestamp.Time().UTC().Format(sampleTimeFormat)
				if err := rawPods.write(
					filepath.Join(rawDir, "metrics_pod", fmt.Sprintf("pod_%s_raw.tsv", safePod)),
					[]string{"metric_name", "timestamp", "value", "pod_name", "namespace", "tags"},
					[]string{name, sampleTime, sample.Value.String(), pod, tags["namespace"], fmt.Sprintf("%v", tags)},
				); err != nil {
					return err
				}
				if !isLite {
					continue
				}
				if err := litePods.write(
					filepath.Join(liteDir, "metrics_pod", fmt.Sprintf("pod_%s.tsv", safePod)),
					[]string{"metric_name", "timestamp", "value", "pod_name", "namespace"},
					[]string{name, sampleTime, sample.Value.String(), pod, tags["namespace"]},
				); err != nil {
					return err
				}
			}
		}

		for _, query := range serviceQueries {
			matrix, err := queryMatrix(ctx, api, fmt.Sprintf(query.selector, ns), window, ts)
			if err != nil {
				slog.Warn("service metrics export", "namespace", ns, "selector", query.selector, "err", err)
				continue
			}
			for _, series := range matrix {
				name, tags := splitMetric(series.Metric)
				service := tags[query.serviceKey]

				for _, sample := range series.Values {
					sampleTime := sample.Timestamp.Time().UTC().Format(sampleTimeFormat)
					if err := rawServices.write(
						filepath.Join(rawDir, "metrics_service", fmt.Sprintf("service_%s_raw.tsv", service)),
						[]string{"metric_name", "timestamp", "value", "service_name", "namespace", "tags"},
						[]string{name, sampleTime, sample.Value.String(), service, tags[query.namespaceKey], fmt.Sprintf("%v", tags)},
					); err != nil {
						return err
					}
					if err := liteServices.write(
						filepath.Join(liteDir, "metrics_service", fmt.Sprintf("service_%s.tsv", service)),
						[]string{"metric_name", "timestamp", "value", "service_name", "namespace"},
						[]string{name, sampleTime, sample.Value.String(), service, tags[query.namespaceKey]},
					); err != nil {
						return err
					}
				}
			}
		}
	}

	return nil
}

// queryMatrix evaluates selector[window] at ts, which returns every raw sample in the window.
func queryMatrix(ctx context.Context, api prometheusv1.API, selector string, window time.Duration, ts time.Time) (model.Matrix, error) {
	query := fmt.Sprintf("%s[%s]", selector, model.Duration(window))
	val, warnings, infos, err := api.Query(ctx, query, ts)
	if err != nil {
		return nil, fmt.Errorf("query %s at %s: %w", query, ts.Format(time.RFC3339), err)
	}
	if len(warnings) > 0 {
		slog.Warn("query warnings", "query", query, "warnings", warnings)
	}
	if len(infos) > 0 {
		slog.Info("query infos", "query", query, "infos", infos)
	}
	matrix, ok := val.(model.Matrix)
	if !ok {
		return nil, fmt.Errorf("query %s returned %s, expected a matrix", query, val.Type())
	}
	return matrix, nil
}

// splitMetric returns the metric name and the remaining labels of a series.
func splitMetric(metric model.Metric) (string, map[string]string) {
	tags := make(map[string]string, len(metric))
	for k, v := range metric {
		if k == model.MetricNameLabel {
			continue
		}
		tags[string(k)] = string(v)
	}
	return string(metric[model.MetricNameLabel]), tags
}

// tsvSet holds TSV files by path. A file is created, with its header, on the first write.
type tsvSet map[string]*lazyTSV

func (s tsvSet) write(path string, headers, row []string) error {
	l, ok := s[path]
	if !ok {
		l = &lazyTSV{path: path, headers: headers}
		s[path] = l
	}
	return l.write(row)
}

func (s tsvSet) close() {
	for _, l := range s {
		l.close()
	}
}

// lazyTSV opens and writes a header to a TSV file on the first write call.
type lazyTSV struct {
	path    string
	headers []string
	f       *os.File
	w       *csv.Writer
}

func (l *lazyTSV) write(row []string) error {
	if l.f == nil {
		f, err := os.Create(l.path)
		if err != nil {
			return fmt.Errorf("create %s: %w", l.path, err)
		}
		w := csv.NewWriter(f)
		w.Comma = '\t'
		w.UseCRLF = false
		if err := w.Write(l.headers); err != nil {
			f.Close()
			return err
		}
		l.f = f
		l.w = w
	}
	return l.w.Write(row)
}

func (l *lazyTSV) close() {
	if l.f == nil {
		return
	}
	l.w.Flush()
	if err := l.w.Error(); err != nil {
		slog.Error("flush tsv", "path", l.path, "err", err)
	}
	l.f.Close()
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
	req.Header.Set("Authorization", "Bearer "+rt.token)
	return rt.inner.RoundTrip(req)
}
