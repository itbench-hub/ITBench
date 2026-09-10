package main

import (
	"context"
	"log/slog"
	"os"
	"path/filepath"

	"github.com/itbench-hub/ITBench/scenarios/sre/tools/clickhouse-recorder/internal/recorder"
)

func main() {
	host := os.Getenv("CLICKHOUSE_HOST")
	username := os.Getenv("CLICKHOUSE_USERNAME")
	password := os.Getenv("CLICKHOUSE_PASSWORD")

	if host == "" {
		slog.Error("CLICKHOUSE_HOST environment variable is not set")
		os.Exit(1)
	}
	if username == "" {
		slog.Error("CLICKHOUSE_USERNAME environment variable is not set")
		os.Exit(1)
	}
	if password == "" {
		slog.Error("CLICKHOUSE_PASSWORD environment variable is not set")
		os.Exit(1)
	}

	homeDir, err := os.UserHomeDir()
	if err != nil {
		slog.Error("could not determine home directory", "err", err)
		os.Exit(1)
	}
	outputDir := filepath.Join(homeDir, "records")

	if err := recorder.Run(context.Background(), host, username, password, outputDir); err != nil {
		slog.Error("recorder failed", "err", err)
		os.Exit(1)
	}
}
