package main

import (
	"context"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"time"

	"github.com/itbench-hub/ITBench/components/recorders/clickhouse/internal/recorder"
)

func main() {
	host := os.Getenv("CLICKHOUSE_HOST")
	username := os.Getenv("CLICKHOUSE_USER")
	password := os.Getenv("CLICKHOUSE_PASSWORD")

	if host == "" {
		slog.Error("CLICKHOUSE_HOST environment variable is not set")
		os.Exit(1)
	}
	if username == "" {
		slog.Error("CLICKHOUSE_USER environment variable is not set")
		os.Exit(1)
	}
	if password == "" {
		slog.Error("CLICKHOUSE_PASSWORD environment variable is not set")
		os.Exit(1)
	}

	outputDir := os.Getenv("OUTPUT_DIR")
	if outputDir == "" {
		outputDir = "/records"
	}

	// NAMESPACES is a comma-separated list, e.g. "otel-demo,book-info".
	var namespaces []string
	for _, ns := range strings.Split(os.Getenv("NAMESPACES"), ",") {
		if ns = strings.TrimSpace(ns); ns != "" {
			namespaces = append(namespaces, ns)
		}
	}
	if len(namespaces) == 0 {
		slog.Error("NAMESPACES environment variable is not set or contains no namespaces")
		os.Exit(1)
	}

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

	var timestamps []time.Time
	interval := time.Duration(intervalSeconds) * time.Second
	for t := start.UTC(); !t.After(end.UTC()); t = t.Add(interval) {
		timestamps = append(timestamps, t)
	}

	slog.Info("starting clickhouse burst recorder", "snapshots_count", len(timestamps), "output_dir", outputDir, "namespaces", namespaces)

	if err := recorder.Run(context.Background(), host, username, password, outputDir, namespaces, timestamps...); err != nil {
		slog.Error("recorder failed", "err", err)
		os.Exit(1)
	}
	slog.Info("clickhouse burst recording completed successfully")
}
