package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"strconv"
	"syscall"
	"time"

	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/writer"
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

	startTS := time.Unix(0, 0).UTC()
	if rawStart := os.Getenv("RECORDING_START_TIMESTAMP"); rawStart != "" {
		if parsed, err := time.Parse(time.RFC3339, rawStart); err == nil {
			startTS = parsed.UTC()
		} else {
			slog.Warn("could not parse RECORDING_START_TIMESTAMP, using epoch zero", "raw", rawStart, "err", err)
		}
	}

	pollInterval := 2 * time.Second
	if rawInterval := os.Getenv("POLL_INTERVAL_SECONDS"); rawInterval != "" {
		if secs, err := strconv.Atoi(rawInterval); err == nil && secs > 0 {
			pollInterval = time.Duration(secs) * time.Second
		}
	}

	ctx, cancel := signal.NotifyContext(context.Background(), os.Interrupt, syscall.SIGTERM)
	defer cancel()

	slog.Info("connecting to clickhouse", "host", host, "username", username)
	conn, err := writer.OpenConnection(ctx, host, username, password, "kubernetes")
	if err != nil {
		slog.Error("failed to connect to clickhouse", "err", err)
		os.Exit(1)
	}
	defer conn.Close()

	tw := writer.NewTopologyWriter(conn, startTS, pollInterval)
	if err := tw.Run(ctx); err != nil {
		slog.Error("topology writer exited with error", "err", err)
		os.Exit(1)
	}
	slog.Info("topology writer exited cleanly")
}
