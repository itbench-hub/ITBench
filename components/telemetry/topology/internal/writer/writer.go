package writer

import (
	"context"
	"encoding/json"
	"fmt"
	"log/slog"
	"reflect"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2"
	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"
	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/builder"
	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/model"
)

const (
	tableDDL = `
CREATE TABLE IF NOT EXISTS kubernetes.topology_graph (
    Timestamp DateTime64(9),
    Seq UInt64,
    Kind Enum8('node' = 1, 'edge' = 2),
    Deleted UInt8 DEFAULT 0,
    Id String DEFAULT '',
    ResourceKind LowCardinality(String) DEFAULT '',
    Name String DEFAULT '',
    Namespace String DEFAULT '',
    Group LowCardinality(String) DEFAULT '',
    Version LowCardinality(String) DEFAULT '',
    Labels Map(String, String),
    Source String DEFAULT '',
    Target String DEFAULT '',
    Type LowCardinality(String) DEFAULT ''
) ENGINE = MergeTree()
ORDER BY (Timestamp, Seq);`
)

type EventBody struct {
	Type   string         `json:"type"`
	Object map[string]any `json:"object"`
}

type TopologyWriter struct {
	conn             driver.Conn
	builder          *builder.KubernetesGraphBuilder
	state            map[string]map[string]any
	lastNodes        map[string]model.Node
	lastEdges        map[string]model.Edge
	lastSeenTS       time.Time
	pollInterval     time.Duration
	batchSeq         uint64
	minStartTS       time.Time
}

func NewTopologyWriter(conn driver.Conn, minStartTS time.Time, pollInterval time.Duration) *TopologyWriter {
	return &TopologyWriter{
		conn:         conn,
		builder:      builder.NewKubernetesGraphBuilder(),
		state:        make(map[string]map[string]any),
		lastNodes:    make(map[string]model.Node),
		lastEdges:    make(map[string]model.Edge),
		lastSeenTS:   minStartTS,
		pollInterval: pollInterval,
		minStartTS:   minStartTS,
	}
}

// OpenConnection creates a native ClickHouse driver connection.
func OpenConnection(ctx context.Context, addr, username, password, database string) (driver.Conn, error) {
	conn, err := clickhouse.Open(&clickhouse.Options{
		Addr: []string{addr},
		Auth: clickhouse.Auth{
			Database: database,
			Username: username,
			Password: password,
		},
		Protocol: clickhouse.Native,
		Compression: &clickhouse.Compression{
			Method: clickhouse.CompressionLZ4,
		},
		DialTimeout:     10 * time.Second,
		MaxOpenConns:    5,
		MaxIdleConns:    2,
		ConnMaxLifetime: 10 * time.Minute,
	})
	if err != nil {
		return nil, fmt.Errorf("open clickhouse connection: %w", err)
	}
	if err := conn.Ping(ctx); err != nil {
		return nil, fmt.Errorf("ping clickhouse: %w", err)
	}
	return conn, nil
}

// InitSchema ensures the target table exists.
func (w *TopologyWriter) InitSchema(ctx context.Context) error {
	if err := w.conn.Exec(ctx, "CREATE DATABASE IF NOT EXISTS kubernetes"); err != nil {
		return fmt.Errorf("create database kubernetes: %w", err)
	}
	if err := w.conn.Exec(ctx, tableDDL); err != nil {
		return fmt.Errorf("create topology_graph table: %w", err)
	}
	return nil
}

// PollOnce reads new rows from kubernetes.topology, updates state, and flushes graph deltas.
func (w *TopologyWriter) PollOnce(ctx context.Context) (int, error) {
	query := `
		SELECT
			Timestamp,
			Body
		FROM kubernetes.topology
		WHERE Timestamp > ?
		ORDER BY Timestamp ASC
		LIMIT 10000`

	rows, err := w.conn.Query(ctx, query, w.lastSeenTS)
	if err != nil {
		return 0, fmt.Errorf("query kubernetes.topology: %w", err)
	}
	defer rows.Close()

	var eventCount int
	var maxTS time.Time

	for rows.Next() {
		var ts time.Time
		var rawBody string

		if err := rows.Scan(&ts, &rawBody); err != nil {
			slog.Warn("failed to scan topology row", "err", err)
			continue
		}

		var body EventBody
		if err := json.Unmarshal([]byte(rawBody), &body); err != nil {
			slog.Warn("failed to parse topology body JSON", "err", err)
			continue
		}

		uid, cleanObj, ok := builder.SanitizeObject(body.Object)
		if !ok {
			continue
		}

		switch body.Type {
		case "ADDED", "MODIFIED":
			w.state[uid] = cleanObj
		case "DELETED":
			delete(w.state, uid)
		}

		if ts.After(maxTS) {
			maxTS = ts
		}
		eventCount++
	}

	if err := rows.Err(); err != nil {
		return 0, fmt.Errorf("iterating topology rows: %w", err)
	}

	if eventCount == 0 {
		return 0, nil
	}

	w.lastSeenTS = maxTS

	// Rebuild graph
	newGraph := w.builder.Build(w.state)

	// Compute and flush deltas
	insertedCount, err := w.flushDeltas(ctx, newGraph, maxTS)
	if err != nil {
		return 0, fmt.Errorf("flush deltas: %w", err)
	}

	return insertedCount, nil
}

func (w *TopologyWriter) flushDeltas(ctx context.Context, g *model.Graph, batchTS time.Time) (int, error) {
	currentEdgesMap := make(map[string]model.Edge, len(g.Edges))
	for _, e := range g.Edges {
		key := fmt.Sprintf("%s|%s|%s", e.Source, e.Target, e.Type)
		currentEdgesMap[key] = e
	}

	// Identify Node deltas
	var nodeInserts []model.Node
	var nodeDeletes []model.Node

	for uid, node := range g.Nodes {
		lastNode, exists := w.lastNodes[uid]
		if !exists || !reflect.DeepEqual(lastNode, node) {
			nodeInserts = append(nodeInserts, node)
		}
	}

	for uid, lastNode := range w.lastNodes {
		if _, exists := g.Nodes[uid]; !exists {
			nodeDeletes = append(nodeDeletes, lastNode)
		}
	}

	// Identify Edge deltas
	var edgeInserts []model.Edge
	var edgeDeletes []model.Edge

	for key, edge := range currentEdgesMap {
		if _, exists := w.lastEdges[key]; !exists {
			edgeInserts = append(edgeInserts, edge)
		}
	}

	for key, lastEdge := range w.lastEdges {
		if _, exists := currentEdgesMap[key]; !exists {
			edgeDeletes = append(edgeDeletes, lastEdge)
		}
	}

	totalDeltas := len(nodeInserts) + len(nodeDeletes) + len(edgeInserts) + len(edgeDeletes)
	if totalDeltas == 0 {
		return 0, nil
	}

	batch, err := w.conn.PrepareBatch(ctx, "INSERT INTO kubernetes.topology_graph")
	if err != nil {
		return 0, fmt.Errorf("prepare batch: %w", err)
	}

	for _, n := range nodeInserts {
		w.batchSeq++
		if err := batch.Append(
			batchTS, w.batchSeq, "node", uint8(0),
			n.ID, n.Kind, n.Name, n.Namespace, n.Group, n.Version, n.Labels,
			"", "", "",
		); err != nil {
			return 0, fmt.Errorf("append node insert: %w", err)
		}
	}

	for _, n := range nodeDeletes {
		w.batchSeq++
		if err := batch.Append(
			batchTS, w.batchSeq, "node", uint8(1),
			n.ID, n.Kind, n.Name, n.Namespace, n.Group, n.Version, n.Labels,
			"", "", "",
		); err != nil {
			return 0, fmt.Errorf("append node delete: %w", err)
		}
	}

	for _, e := range edgeInserts {
		w.batchSeq++
		if err := batch.Append(
			batchTS, w.batchSeq, "edge", uint8(0),
			"", "", "", "", "", "", map[string]string{},
			e.Source, e.Target, e.Type,
		); err != nil {
			return 0, fmt.Errorf("append edge insert: %w", err)
		}
	}

	for _, e := range edgeDeletes {
		w.batchSeq++
		if err := batch.Append(
			batchTS, w.batchSeq, "edge", uint8(1),
			"", "", "", "", "", "", map[string]string{},
			e.Source, e.Target, e.Type,
		); err != nil {
			return 0, fmt.Errorf("append edge delete: %w", err)
		}
	}

	if err := batch.Send(); err != nil {
		return 0, fmt.Errorf("send batch: %w", err)
	}

	w.lastNodes = g.Nodes
	w.lastEdges = currentEdgesMap

	return totalDeltas, nil
}

// Run starts the continuous polling and sync loop until ctx is cancelled.
func (w *TopologyWriter) Run(ctx context.Context) error {
	if err := w.InitSchema(ctx); err != nil {
		return err
	}

	ticker := time.NewTicker(w.pollInterval)
	defer ticker.Stop()

	slog.Info("topology writer started", "poll_interval", w.pollInterval, "min_start_ts", w.minStartTS)

	for {
		select {
		case <-ctx.Done():
			slog.Info("topology writer stopping")
			return nil
		case <-ticker.C:
			deltas, err := w.PollOnce(ctx)
			if err != nil {
				slog.Error("error during topology sync", "err", err)
			} else if deltas > 0 {
				slog.Info("synced topology deltas", "deltas_written", deltas)
			}
		}
	}
}
