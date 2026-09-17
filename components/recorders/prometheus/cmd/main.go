package main

import (
	"context"
	"log/slog"
	"os"
	"path/filepath"
	"strings"
	"time"

	"github.com/itbench-hub/ITBench/components/recorders/prometheus/internal/recorder"
)

func main() {
	endpoint := os.Getenv("PROMETHEUS_ENDPOINT")
	if endpoint == "" {
		slog.Error("PROMETHEUS_ENDPOINT environment variable is not set")
		os.Exit(1)
	}

	token := os.Getenv("PROMETHEUS_TOKEN")

	homeDir, err := os.UserHomeDir()
	if err != nil {
		slog.Error("could not determine home directory", "err", err)
		os.Exit(1)
	}
	outputDir := filepath.Join(homeDir, "records")

	var timestamps []time.Time
	if rawTimestamps := os.Getenv("SNAPSHOT_TIMESTAMPS"); rawTimestamps != "" {
		for _, raw := range strings.Split(rawTimestamps, ",") {
			raw = strings.TrimSpace(raw)
			if raw == "" {
				continue
			}
			t, err := time.Parse(time.RFC3339, raw)
			if err != nil {
				slog.Warn("could not parse milestone timestamp", "raw", raw, "err", err)
				continue
			}
			timestamps = append(timestamps, t.UTC())
		}
	}

	slog.Info("starting prometheus burst recorder", "snapshots_count", len(timestamps), "output_dir", outputDir)

	if err := recorder.Run(context.Background(), endpoint, token, outputDir, timestamps...); err != nil {
		slog.Error("recorder failed", "err", err)
		os.Exit(1)
	}
	slog.Info("prometheus burst recording completed successfully")
}
