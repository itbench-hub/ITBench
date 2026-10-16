package builder_test

import (
	"testing"

	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/builder"
	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/model"
)

func simpleState() map[string]map[string]any {
	return map[string]map[string]any{
		"uid-ns": {
			"kind":       "Namespace",
			"apiVersion": "v1",
			"metadata":   map[string]any{"name": "demo", "uid": "uid-ns"},
		},
		"uid-node": {
			"kind":       "Node",
			"apiVersion": "v1",
			"metadata":   map[string]any{"name": "node-1", "uid": "uid-node"},
		},
		"uid-pod-a": {
			"kind":       "Pod",
			"apiVersion": "v1",
			"metadata": map[string]any{
				"name":      "pod-a",
				"namespace": "demo",
				"uid":       "uid-pod-a",
				"labels":    map[string]any{"app": "web"},
			},
			"spec": map[string]any{"nodeName": "node-1"},
		},
		"uid-pod-b": {
			"kind":       "Pod",
			"apiVersion": "v1",
			"metadata": map[string]any{
				"name":      "pod-b",
				"namespace": "demo",
				"uid":       "uid-pod-b",
				"labels":    map[string]any{"app": "web"},
			},
			"spec": map[string]any{"nodeName": "node-1"},
		},
		"uid-svc": {
			"kind":       "Service",
			"apiVersion": "v1",
			"metadata":   map[string]any{"name": "web-svc", "namespace": "demo", "uid": "uid-svc"},
			"spec":       map[string]any{"selector": map[string]any{"app": "web"}},
		},
	}
}

func edgesOfType(g *model.Graph, edgeType string) []model.Edge {
	var result []model.Edge
	for _, e := range g.Edges {
		if e.Type == edgeType {
			result = append(result, e)
		}
	}
	return result
}

func hasEdge(g *model.Graph, source, target, edgeType string) bool {
	for _, e := range g.Edges {
		if e.Source == source && e.Target == target && e.Type == edgeType {
			return true
		}
	}
	return false
}

func TestKubernetesGraphBuilder_Basic(t *testing.T) {
	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(simpleState())

	if _, ok := g.Nodes[builder.ClusterUID]; !ok {
		t.Fatalf("expected cluster root node %s to exist", builder.ClusterUID)
	}

	for uid := range simpleState() {
		if _, ok := g.Nodes[uid]; !ok {
			t.Errorf("missing node %s in graph", uid)
		}
	}

	nodeRunsPod := edgesOfType(g, "NODE_RUNS_POD")
	if len(nodeRunsPod) != 2 {
		t.Errorf("expected 2 NODE_RUNS_POD edges, got %d", len(nodeRunsPod))
	}
	if !hasEdge(g, "uid-node", "uid-pod-a", "NODE_RUNS_POD") || !hasEdge(g, "uid-node", "uid-pod-b", "NODE_RUNS_POD") {
		t.Errorf("expected NODE_RUNS_POD edges to pod-a and pod-b")
	}

	svcSelects := edgesOfType(g, "SERVICE_SELECTS_POD")
	if len(svcSelects) != 2 {
		t.Errorf("expected 2 SERVICE_SELECTS_POD edges, got %d", len(svcSelects))
	}
	if !hasEdge(g, "uid-svc", "uid-pod-a", "SERVICE_SELECTS_POD") || !hasEdge(g, "uid-svc", "uid-pod-b", "SERVICE_SELECTS_POD") {
		t.Errorf("expected SERVICE_SELECTS_POD edges from svc to pod-a and pod-b")
	}

	if !hasEdge(g, builder.ClusterUID, "uid-node", "OWNS") {
		t.Errorf("expected cluster to own node-1")
	}
	if !hasEdge(g, "uid-ns", "uid-pod-a", "OWNS") {
		t.Errorf("expected namespace demo to own pod-a")
	}
}

func TestEndpointsEdges(t *testing.T) {
	state := map[string]map[string]any{
		"uid-ns": {
			"kind": "Namespace", "apiVersion": "v1",
			"metadata": map[string]any{"name": "ns", "uid": "uid-ns"},
		},
		"uid-svc": {
			"kind": "Service", "apiVersion": "v1",
			"metadata": map[string]any{"name": "svc", "namespace": "ns", "uid": "uid-svc"},
			"spec":     map[string]any{},
		},
		"uid-ep": {
			"kind": "Endpoints", "apiVersion": "v1",
			"metadata": map[string]any{"name": "svc", "namespace": "ns", "uid": "uid-ep"},
			"subsets": []any{
				map[string]any{
					"addresses": []any{
						map[string]any{
							"targetRef": map[string]any{"kind": "Pod", "name": "pod-1", "uid": "uid-pod"},
						},
					},
					"ports": []any{
						map[string]any{"port": 8080, "protocol": "TCP"},
					},
				},
			},
		},
		"uid-pod": {
			"kind": "Pod", "apiVersion": "v1",
			"metadata": map[string]any{"name": "pod-1", "namespace": "ns", "uid": "uid-pod"},
		},
	}

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	expectedTypes := []string{
		"SERVICE_HAS_ENDPOINTS",
		"ENDPOINTS_TARGET_POD",
		"POD_OWNS_PORT",
		"SERVICE_OWNS_PORT",
		"SERVICE_TARGETS_PORT",
	}

	for _, et := range expectedTypes {
		if len(edgesOfType(g, et)) == 0 {
			t.Errorf("expected edge type %s in graph, but none found", et)
		}
	}
}

func declaredPortState() map[string]map[string]any {
	return map[string]map[string]any{
		"uid-ns": {
			"kind": "Namespace", "apiVersion": "v1",
			"metadata": map[string]any{"name": "ns", "uid": "uid-ns"},
		},
		"uid-svc": {
			"kind": "Service", "apiVersion": "v1",
			"metadata": map[string]any{"name": "svc", "namespace": "ns", "uid": "uid-svc"},
			"spec": map[string]any{
				"ports": []any{
					map[string]any{"port": 80, "protocol": "TCP", "targetPort": 8080},
				},
			},
		},
		"uid-pod": {
			"kind": "Pod", "apiVersion": "v1",
			"metadata": map[string]any{"name": "pod-1", "namespace": "ns", "uid": "uid-pod"},
			"spec": map[string]any{
				"containers": []any{
					map[string]any{
						"name":  "c",
						"ports": []any{map[string]any{"containerPort": 8080}},
					},
				},
			},
		},
	}
}

func TestDeclaredPortEdges(t *testing.T) {
	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(declaredPortState())

	if !hasEdge(g, "uid-svc", "port:ns:svc:80:TCP", "SERVICE_OWNS_PORT") {
		t.Errorf("missing SERVICE_OWNS_PORT edge")
	}
	if !hasEdge(g, "uid-pod", "port:ns:pod-1:8080:TCP", "POD_OWNS_PORT") {
		t.Errorf("missing POD_OWNS_PORT edge")
	}
	if pNode, ok := g.Nodes["port:ns:svc:80:TCP"]; !ok || pNode.Kind != "Port" {
		t.Errorf("expected port node port:ns:svc:80:TCP with kind Port")
	}
}

func TestProtocolDefaultsToTCPAndRespectsUDP(t *testing.T) {
	state := declaredPortState()
	spec := state["uid-svc"]["spec"].(map[string]any)
	ports := spec["ports"].([]any)
	spec["ports"] = append(ports, map[string]any{"port": 53, "protocol": "UDP"})

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	if _, ok := g.Nodes["port:ns:svc:53:UDP"]; !ok {
		t.Errorf("expected UDP port node port:ns:svc:53:UDP")
	}
}

func TestDeclaredAndEndpointPortShareOneNode(t *testing.T) {
	state := declaredPortState()
	state["uid-ep"] = map[string]any{
		"kind": "Endpoints", "apiVersion": "v1",
		"metadata": map[string]any{"name": "svc", "namespace": "ns", "uid": "uid-ep"},
		"subsets": []any{
			map[string]any{
				"addresses": []any{
					map[string]any{
						"targetRef": map[string]any{"kind": "Pod", "name": "pod-1", "uid": "uid-pod"},
					},
				},
				"ports": []any{map[string]any{"port": 8080, "protocol": "TCP"}},
			},
		},
	}

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	podOwns := 0
	for _, e := range g.Edges {
		if e.Type == "POD_OWNS_PORT" && e.Target == "port:ns:pod-1:8080:TCP" {
			podOwns++
		}
	}
	if podOwns != 1 {
		t.Errorf("expected exactly 1 POD_OWNS_PORT edge, got %d", podOwns)
	}
}

func TestMountEdges(t *testing.T) {
	state := map[string]map[string]any{
		"uid-ns": {
			"kind": "Namespace", "apiVersion": "v1", "metadata": map[string]any{"name": "ns", "uid": "uid-ns"},
		},
		"uid-cm": {
			"kind": "ConfigMap", "apiVersion": "v1", "metadata": map[string]any{"name": "cfg", "namespace": "ns", "uid": "uid-cm"},
		},
		"uid-sec": {
			"kind": "Secret", "apiVersion": "v1", "metadata": map[string]any{"name": "sec", "namespace": "ns", "uid": "uid-sec"},
		},
		"uid-pvc": {
			"kind": "PersistentVolumeClaim", "apiVersion": "v1", "metadata": map[string]any{"name": "claim", "namespace": "ns", "uid": "uid-pvc"},
		},
		"uid-pod": {
			"kind": "Pod", "apiVersion": "v1",
			"metadata": map[string]any{"name": "p", "namespace": "ns", "uid": "uid-pod"},
			"spec": map[string]any{
				"volumes": []any{
					map[string]any{"name": "v1", "configMap": map[string]any{"name": "cfg"}},
					map[string]any{"name": "v2", "secret": map[string]any{"secretName": "sec"}},
					map[string]any{"name": "v3", "persistentVolumeClaim": map[string]any{"claimName": "claim"}},
				},
			},
		},
	}

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	if !hasEdge(g, "uid-pod", "uid-cm", "POD_MOUNTS_CONFIGMAP") {
		t.Errorf("missing POD_MOUNTS_CONFIGMAP edge")
	}
	if !hasEdge(g, "uid-pod", "uid-sec", "POD_MOUNTS_SECRET") {
		t.Errorf("missing POD_MOUNTS_SECRET edge")
	}
	if !hasEdge(g, "uid-pod", "uid-pvc", "POD_MOUNTS_PVC") {
		t.Errorf("missing POD_MOUNTS_PVC edge")
	}
}

func TestPVBoundToPVC(t *testing.T) {
	state := map[string]map[string]any{
		"uid-pv": {
			"kind": "PersistentVolume", "apiVersion": "v1",
			"metadata": map[string]any{"name": "pv-1", "uid": "uid-pv"},
			"spec":     map[string]any{"claimRef": map[string]any{"namespace": "ns", "name": "claim"}},
		},
		"uid-pvc": {
			"kind": "PersistentVolumeClaim", "apiVersion": "v1",
			"metadata": map[string]any{"name": "claim", "namespace": "ns", "uid": "uid-pvc"},
		},
	}

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	if !hasEdge(g, "uid-pv", "uid-pvc", "PV_BOUND_TO_PVC") {
		t.Errorf("missing PV_BOUND_TO_PVC edge")
	}
}

func TestHPAEdges(t *testing.T) {
	state := map[string]map[string]any{
		"uid-ns": {
			"kind": "Namespace", "apiVersion": "v1", "metadata": map[string]any{"name": "ns", "uid": "uid-ns"},
		},
		"uid-dep": {
			"kind": "Deployment", "apiVersion": "apps/v1",
			"metadata": map[string]any{"name": "web", "namespace": "ns", "uid": "uid-dep"},
		},
		"uid-hpa": {
			"kind": "HorizontalPodAutoscaler", "apiVersion": "autoscaling/v2",
			"metadata": map[string]any{"name": "web-hpa", "namespace": "ns", "uid": "uid-hpa"},
			"spec": map[string]any{
				"scaleTargetRef": map[string]any{"kind": "Deployment", "name": "web"},
			},
		},
	}

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	if !hasEdge(g, "uid-hpa", "uid-dep", "HPA_SCALES") {
		t.Errorf("missing HPA_SCALES edge")
	}
}

func TestHTTPRouteEdges(t *testing.T) {
	state := map[string]map[string]any{
		"uid-ns": {
			"kind": "Namespace", "apiVersion": "v1", "metadata": map[string]any{"name": "ns", "uid": "uid-ns"},
		},
		"uid-gw": {
			"kind": "Gateway", "apiVersion": "gateway.networking.k8s.io/v1",
			"metadata": map[string]any{"name": "my-gateway", "namespace": "ns", "uid": "uid-gw"},
		},
		"uid-svc": {
			"kind": "Service", "apiVersion": "v1",
			"metadata": map[string]any{"name": "backend", "namespace": "ns", "uid": "uid-svc"},
		},
		"uid-route": {
			"kind": "HTTPRoute", "apiVersion": "gateway.networking.k8s.io/v1",
			"metadata": map[string]any{"name": "my-route", "namespace": "ns", "uid": "uid-route"},
			"spec": map[string]any{
				"parentRefs": []any{
					map[string]any{"kind": "Gateway", "name": "my-gateway"},
				},
				"rules": []any{
					map[string]any{
						"backendRefs": []any{
							map[string]any{"kind": "Service", "name": "backend", "port": 80},
						},
					},
				},
			},
		},
	}

	b := builder.NewKubernetesGraphBuilder()
	g := b.Build(state)

	if !hasEdge(g, "uid-route", "uid-gw", "HTTPROUTE_ATTACHES_GATEWAY") {
		t.Errorf("missing HTTPROUTE_ATTACHES_GATEWAY edge")
	}
	if !hasEdge(g, "uid-route", "uid-svc", "HTTPROUTE_ROUTES_SERVICE") {
		t.Errorf("missing HTTPROUTE_ROUTES_SERVICE edge")
	}
}

func TestGraphDeduplication(t *testing.T) {
	g := model.NewGraph()
	g.AddNode(model.Node{ID: "a", Kind: "Pod", Name: "a", Namespace: "ns"})
	g.AddNode(model.Node{ID: "b", Kind: "Pod", Name: "b", Namespace: "ns"})

	g.AddEdge("a", "b", "OWNS")
	g.AddEdge("a", "b", "OWNS")

	if len(g.Edges) != 1 {
		t.Errorf("expected 1 deduplicated edge, got %d", len(g.Edges))
	}
}
