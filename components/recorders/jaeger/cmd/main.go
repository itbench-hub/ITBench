package main

import (
	"context"
	"log/slog"
	"os"
	"os/signal"
	"path/filepath"
	"strconv"
	"syscall"
	"time"

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

	intervalSec := 300
	if val := os.Getenv("INTERVAL_SECONDS"); val != "" {
		if parsed, err := strconv.Atoi(val); err == nil && parsed > 0 {
			intervalSec = parsed
		} else {
			slog.Warn("invalid INTERVAL_SECONDS, using default", "value", val, "default", intervalSec)
		}
	}

	ctx, cancel := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer cancel()

	slog.Info("starting jaeger recorder daemon", "interval_seconds", intervalSec, "output_dir", outputDir)

	if err := recorder.Run(ctx, endpoint, outputDir); err != nil {
		slog.Error("initial recorder run failed", "err", err)
	}

	ticker := time.NewTicker(time.Duration(intervalSec) * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			slog.Info("shutting down jaeger recorder daemon")
			return
		case <-ticker.C:
			slog.Info("running scheduled scrape")
			if err := recorder.Run(ctx, endpoint, outputDir); err != nil {
				slog.Error("scheduled recorder run failed", "err", err)
			}
		}
	}
}
