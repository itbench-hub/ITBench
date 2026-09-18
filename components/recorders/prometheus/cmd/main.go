package main

import (
	"context"
	"log/slog"
	"os"
	"path/filepath"
	"strconv"
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

	startRaw := os.Getenv("RECORDING_START_TIMESTAMP")
	if startRaw == "" {
		slog.Error("RECORDING_START_TIMESTAMP environment variable is not set")
		os.Exit(1)
	}

	start, err := time.Parse(time.RFC3339, startRaw)
	if err != nil {
		slog.Error("could not parse RECORDING_START_TIMESTAMP", "raw", startRaw, "err", err)
		os.Exit(1)
	}

	endRaw := os.Getenv("RECORDING_END_TIMESTAMP")
	if endRaw == "" {
		slog.Error("RECORDING_END_TIMESTAMP environment variable is not set")
		os.Exit(1)
	}

	end, err := time.Parse(time.RFC3339, endRaw)
	if err != nil {
		slog.Error("could not parse RECORDING_END_TIMESTAMP", "raw", endRaw, "err", err)
		os.Exit(1)
	}

	intervalRaw := os.Getenv("RECORDING_INTERVAL_SECONDS")
	if intervalRaw == "" {
		slog.Error("RECORDING_INTERVAL_SECONDS environment variable is not set")
		os.Exit(1)
	}

	intervalSeconds, err := strconv.Atoi(intervalRaw)
	if err != nil || intervalSeconds <= 0 {
		slog.Error("RECORDING_INTERVAL_SECONDS must be a positive integer", "raw", intervalRaw, "err", err)
		os.Exit(1)
	}
	interval := time.Duration(intervalSeconds) * time.Second

	var timestamps []time.Time
	for t := start.UTC(); !t.After(end.UTC()); t = t.Add(interval) {
		timestamps = append(timestamps, t)
	}

	slog.Info("starting prometheus burst recorder", "snapshots_count", len(timestamps), "output_dir", outputDir)

	if err := recorder.Run(context.Background(), endpoint, token, outputDir, timestamps...); err != nil {
		slog.Error("recorder failed", "err", err)
		os.Exit(1)
	}
	slog.Info("prometheus burst recording completed successfully")
}
