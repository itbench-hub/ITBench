package writer_test

import (
	"context"
	"encoding/json"
	"fmt"
	"testing"
	"time"

	"github.com/ClickHouse/clickhouse-go/v2/lib/driver"
	"github.com/testcontainers/testcontainers-go/modules/clickhouse"

	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/writer"
)

const (
	image        = "docker.io/clickhouse/clickhouse-server:26.9.22@sha256:3358498f63c33d60ec1fa3abe9918e63c6b1d86dbad20e5613590a2899d5d872"
	testPassword = "testpassword" // pragma: allowlist secret
)

var viewsDDLs = []string{
	`CREATE OR REPLACE VIEW kubernetes.v_topology_nodes AS
SELECT
    Id,
    argMax(ResourceKind, (Timestamp, Seq)) AS ResourceKind,
    argMax(Name, (Timestamp, Seq)) AS Name,
    argMax(Namespace, (Timestamp, Seq)) AS Namespace,
    argMax(Group, (Timestamp, Seq)) AS Group,
    argMax(Version, (Timestamp, Seq)) AS Version,
    argMax(Labels, (Timestamp, Seq)) AS Labels,
    argMax(Deleted, (Timestamp, Seq)) AS Deleted,
    max(Timestamp) AS LastUpdated
FROM kubernetes.topology_graph
WHERE Kind = 'node'
GROUP BY Id
HAVING Deleted = 0`,

	`CREATE OR REPLACE VIEW kubernetes.v_topology_edges AS
SELECT
    Source,
    Target,
    Type,
    argMax(Deleted, (Timestamp, Seq)) AS Deleted,
    max(Timestamp) AS LastUpdated
FROM kubernetes.topology_graph
WHERE Kind = 'edge'
GROUP BY Source, Target, Type
HAVING Deleted = 0`,

	`CREATE OR REPLACE VIEW kubernetes.v_topology_relationships AS
SELECT
    multiIf(
        Type = 'OWNS', Target,
        Type = 'NODE_RUNS_POD', Target,
        Source
    ) AS Source,
    multiIf(
        Type = 'OWNS', Source,
        Type = 'NODE_RUNS_POD', Source,
        Target
    ) AS Target,
    multiIf(
        Type IN ('SERVICE_OWNS_PORT', 'POD_OWNS_PORT'), 'EXPOSES',
        Type IN ('OWNS', 'NODE_RUNS_POD', 'SERVICE_SELECTS_POD', 'POD_MOUNTS_CONFIGMAP', 'POD_MOUNTS_SECRET', 'POD_MOUNTS_PVC'), 'DEPENDS',
        Type
    ) AS Relationship,
    Type AS OriginalType,
    LastUpdated
FROM kubernetes.v_topology_edges`,
}

func TestTopologyWriterIntegration(t *testing.T) {
	ctx := context.Background()

	ctr, err := clickhouse.Run(ctx, image,
		clickhouse.WithPassword(testPassword),
	)
	if err != nil {
		t.Fatalf("start clickhouse container: %v", err)
	}
	t.Cleanup(func() { _ = ctr.Terminate(ctx) })

	addr, err := ctr.ConnectionHost(ctx)
	if err != nil {
		t.Fatalf("get connection host: %v", err)
	}

	conn, err := writer.OpenConnection(ctx, addr, "default", testPassword, "default")
	if err != nil {
		t.Fatalf("open connection: %v", err)
	}
	defer conn.Close()

	// 1. Create kubernetes.topology stream table
	if err := conn.Exec(ctx, "CREATE DATABASE IF NOT EXISTS kubernetes"); err != nil {
		t.Fatalf("create database kubernetes: %v", err)
	}
	topologyTableDDL := `
	CREATE TABLE IF NOT EXISTS kubernetes.topology (
		Timestamp DateTime64(9),
		Body String
	) ENGINE = MergeTree()
	ORDER BY Timestamp;`
	if err := conn.Exec(ctx, topologyTableDDL); err != nil {
		t.Fatalf("create kubernetes.topology table: %v", err)
	}

	// 2. Initialize writer and graph schema
	startTime := time.Date(2026, 1, 1, 0, 0, 0, 0, time.UTC)
	w := writer.NewTopologyWriter(conn, startTime, 1*time.Second)
	if err := w.InitSchema(ctx); err != nil {
		t.Fatalf("InitSchema: %v", err)
	}

	// 3. Create views
	for i, ddl := range viewsDDLs {
		if err := conn.Exec(ctx, ddl); err != nil {
			t.Fatalf("create view [%d]: %v", i, err)
		}
	}

	// 4. Seed initial events into kubernetes.topology
	t1 := startTime.Add(1 * time.Second)
	events := []writer.EventBody{
		{
			Type: "ADDED",
			Object: map[string]any{
				"apiVersion": "apps/v1",
				"kind":       "Deployment",
				"metadata": map[string]any{
					"name":      "store-front",
					"namespace": "default",
					"uid":       "uid-deploy-1",
				},
			},
		},
		{
			Type: "ADDED",
			Object: map[string]any{
				"apiVersion": "apps/v1",
				"kind":       "ReplicaSet",
				"metadata": map[string]any{
					"name":      "store-front-rs",
					"namespace": "default",
					"uid":       "uid-rs-1",
					"ownerReferences": []any{
						map[string]any{
							"uid":  "uid-deploy-1",
							"kind": "Deployment",
							"name": "store-front",
						},
					},
				},
			},
		},
		{
			Type: "ADDED",
			Object: map[string]any{
				"apiVersion": "v1",
				"kind":       "Pod",
				"metadata": map[string]any{
					"name":      "store-front-pod",
					"namespace": "default",
					"uid":       "uid-pod-1",
					"labels": map[string]any{
						"app": "store",
					},
					"ownerReferences": []any{
						map[string]any{
							"uid":  "uid-rs-1",
							"kind": "ReplicaSet",
							"name": "store-front-rs",
						},
					},
				},
				"spec": map[string]any{
					"volumes": []any{
						map[string]any{
							"name": "secret-vol",
							"secret": map[string]any{
								"secretName": "store-secret",
							},
						},
					},
				},
			},
		},
		{
			Type: "ADDED",
			Object: map[string]any{
				"apiVersion": "v1",
				"kind":       "Service",
				"metadata": map[string]any{
					"name":      "store-service",
					"namespace": "default",
					"uid":       "uid-svc-1",
				},
				"spec": map[string]any{
					"selector": map[string]any{
						"app": "store",
					},
				},
			},
		},
		{
			Type: "ADDED",
			Object: map[string]any{
				"apiVersion": "v1",
				"kind":       "Secret",
				"metadata": map[string]any{
					"name":      "store-secret",
					"namespace": "default",
					"uid":       "uid-secret-1",
				},
				"data": map[string]any{
					"password": "SUPER_SECRET_VALUE",
				},
			},
		},
	}

	if err := insertTopologyEvents(ctx, conn, t1, events); err != nil {
		t.Fatalf("insert topology events: %v", err)
	}

	// 5. Poll and assert graph deltas
	deltas, err := w.PollOnce(ctx)
	if err != nil {
		t.Fatalf("PollOnce initial sync: %v", err)
	}
	if deltas == 0 {
		t.Fatalf("expected deltas > 0, got %d", deltas)
	}

	// 6. Verify nodes in kubernetes.topology_graph (5 resources + 1 cluster root node)
	var nodeCount uint64
	if err := conn.QueryRow(ctx, "SELECT count() FROM kubernetes.topology_graph WHERE Kind = 'node' AND Deleted = 0").Scan(&nodeCount); err != nil {
		t.Fatalf("count nodes: %v", err)
	}
	if nodeCount != 6 {
		t.Errorf("expected 6 nodes (including cluster root), got %d", nodeCount)
	}

	// 7. Verify edges in kubernetes.topology_graph
	var edgeCount uint64
	if err := conn.QueryRow(ctx, "SELECT count() FROM kubernetes.topology_graph WHERE Kind = 'edge' AND Deleted = 0").Scan(&edgeCount); err != nil {
		t.Fatalf("count edges: %v", err)
	}
	if edgeCount != 4 {
		// Expect: deploy->rs (OWNS), rs->pod (OWNS), svc->pod (SERVICE_SELECTS_POD), pod->secret (POD_MOUNTS_SECRET)
		t.Errorf("expected 4 edges, got %d", edgeCount)
	}

	// 8. Verify relationships view (DEPENDS projection)
	var dependsCount uint64
	if err := conn.QueryRow(ctx, "SELECT count() FROM kubernetes.v_topology_relationships WHERE Relationship = 'DEPENDS'").Scan(&dependsCount); err != nil {
		t.Fatalf("count DEPENDS relationships: %v", err)
	}
	if dependsCount != 4 {
		t.Errorf("expected 4 DEPENDS relationships, got %d", dependsCount)
	}

	// 9. Verify deletion handling
	t2 := t1.Add(1 * time.Second)
	deleteEvents := []writer.EventBody{
		{
			Type: "DELETED",
			Object: map[string]any{
				"apiVersion": "v1",
				"kind":       "Pod",
				"metadata": map[string]any{
					"name":      "store-front-pod",
					"namespace": "default",
					"uid":       "uid-pod-1",
				},
			},
		},
	}
	if err := insertTopologyEvents(ctx, conn, t2, deleteEvents); err != nil {
		t.Fatalf("insert delete event: %v", err)
	}

	delDeltas, err := w.PollOnce(ctx)
	if err != nil {
		t.Fatalf("PollOnce after delete: %v", err)
	}
	if delDeltas == 0 {
		t.Fatalf("expected deltas for deletion, got 0")
	}

	// 10. Verify active view excludes deleted pod (4 resources + 1 cluster root node)
	var activeNodeCount uint64
	if err := conn.QueryRow(ctx, "SELECT count() FROM kubernetes.v_topology_nodes").Scan(&activeNodeCount); err != nil {
		t.Fatalf("count active nodes in view: %v", err)
	}
	if activeNodeCount != 5 {
		t.Errorf("expected 5 active nodes after pod deletion, got %d", activeNodeCount)
	}

	var podInViewCount uint64
	if err := conn.QueryRow(ctx, "SELECT count() FROM kubernetes.v_topology_nodes WHERE Id = 'uid-pod-1'").Scan(&podInViewCount); err != nil {
		t.Fatalf("check pod in view: %v", err)
	}
	if podInViewCount != 0 {
		t.Errorf("deleted pod should not appear in v_topology_nodes")
	}
}

func insertTopologyEvents(ctx context.Context, conn driver.Conn, ts time.Time, events []writer.EventBody) error {
	batch, err := conn.PrepareBatch(ctx, "INSERT INTO kubernetes.topology (Timestamp, Body)")
	if err != nil {
		return fmt.Errorf("prepare batch: %w", err)
	}

	for _, ev := range events {
		bodyBytes, err := json.Marshal(ev)
		if err != nil {
			return fmt.Errorf("marshal event: %w", err)
		}
		if err := batch.Append(ts, string(bodyBytes)); err != nil {
			return fmt.Errorf("append event: %w", err)
		}
	}

	return batch.Send()
}
