package main

import (
	"context"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/itbench-hub/ITBench/scenarios/sre/tools/prometheus-recorder/internal/recorder"
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

	if err := recorder.Run(context.Background(), endpoint, token, outputDir); err != nil {
		slog.Error("recorder failed", "err", err)
		os.Exit(1)
	}
}
