package model

import "time"

// Node represents a topology graph node.
type Node struct {
	ID        string            `json:"id"`
	Kind      string            `json:"kind"`
	Name      string            `json:"name"`
	Namespace string            `json:"namespace"`
	Group     string            `json:"group"`
	Version   string            `json:"version"`
	Labels    map[string]string `json:"labels"`
}

// Edge represents a directed relation between two nodes.
type Edge struct {
	Source string `json:"source"`
	Target string `json:"target"`
	Type   string `json:"type"`
}

type edgeKey struct {
	source string
	target string
	typ    string
}

// Graph holds the in-memory directed graph of nodes and unique edges.
type Graph struct {
	Nodes   map[string]Node
	Edges   []Edge
	edgeSet map[edgeKey]struct{}
}

// NewGraph creates an empty Graph.
func NewGraph() *Graph {
	return &Graph{
		Nodes:   make(map[string]Node),
		Edges:   make([]Edge, 0),
		edgeSet: make(map[edgeKey]struct{}),
	}
}

// AddNode adds a node to the graph.
func (g *Graph) AddNode(node Node) {
	g.Nodes[node.ID] = node
}

// AddEdge adds an edge if both source and target nodes exist and the edge is not already present.
func (g *Graph) AddEdge(sourceUID, targetUID, edgeType string) {
	if _, ok := g.Nodes[sourceUID]; !ok {
		return
	}
	if _, ok := g.Nodes[targetUID]; !ok {
		return
	}
	key := edgeKey{source: sourceUID, target: targetUID, typ: edgeType}
	if _, exists := g.edgeSet[key]; !exists {
		g.edgeSet[key] = struct{}{}
		g.Edges = append(g.Edges, Edge{
			Source: sourceUID,
			Target: targetUID,
			Type:   edgeType,
		})
	}
}

// TopologyEvent represents a row streamed from kubernetes.topology.
type TopologyEvent struct {
	Timestamp          time.Time
	Type               string // ADDED, MODIFIED, DELETED
	ResourceAttributes map[string]string
	LogAttributes      map[string]string
	Object             map[string]any
}
