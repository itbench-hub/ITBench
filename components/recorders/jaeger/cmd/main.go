package main

import (
	"context"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/itbench-hub/ITBench/components/recorders/jaeger/internal/recorder"
)

func main() {
	endpoint := os.Getenv("JAEGER_ENDPOINT")
	if endpoint == "" {
		slog.Error("JAEGER_ENDPOINT environment variable is not set")
		os.Exit(1)
	}

	homeDir, err := os.UserHomeDir()
	if err != nil {
		slog.Error("could not determine home directory", "err", err)
		os.Exit(1)
	}
	outputDir := filepath.Join(homeDir, "records")

	if err := recorder.Run(context.Background(), endpoint, outputDir); err != nil {
		slog.Error("recorder failed", "err", err)
		os.Exit(1)
	}
}
