package builder

import (
	"fmt"
	"strings"

	"github.com/itbench-hub/ITBench/components/telemetry/topology/internal/model"
)

const ClusterUID = "cluster"

var clusterScopedKinds = map[string]struct{}{
	"Node":                           {},
	"Namespace":                      {},
	"PersistentVolume":               {},
	"ClusterRole":                    {},
	"ClusterRoleBinding":             {},
	"StorageClass":                   {},
	"CSIDriver":                      {},
	"CSINode":                        {},
	"PriorityClass":                  {},
	"RuntimeClass":                   {},
	"VolumeAttachment":               {},
	"CustomResourceDefinition":       {},
	"ValidatingWebhookConfiguration": {},
	"MutatingWebhookConfiguration":   {},
}

// KubernetesGraphBuilder constructs a Graph from an ObjectState snapshot.
type KubernetesGraphBuilder struct{}

// NewKubernetesGraphBuilder returns a new KubernetesGraphBuilder.
func NewKubernetesGraphBuilder() *KubernetesGraphBuilder {
	return &KubernetesGraphBuilder{}
}

// Build builds the topology Graph from state.
func (b *KubernetesGraphBuilder) Build(state map[string]map[string]any) *model.Graph {
	g := model.NewGraph()
	b.addClusterRoot(g)
	b.addNodes(g, state)

	idx := b.buildIndex(g)
	b.addOwnershipEdges(g, idx, state)
	b.addRuntimeEdges(g, idx, state)
	b.addServiceEdges(g, idx, state)
	b.addDeclaredPortEdges(g, state)
	b.addEndpointsEdges(g, idx, state)
	b.addMountEdges(g, idx, state)
	b.addVolumeEdges(g, idx, state)
	b.addHPAEdges(g, idx, state)
	b.addHTTPRouteEdges(g, idx, state)

	return g
}

func (b *KubernetesGraphBuilder) addClusterRoot(g *model.Graph) {
	g.AddNode(model.Node{
		ID:        ClusterUID,
		Kind:      "K8Cluster",
		Name:      "cluster",
		Namespace: "",
		Group:     "",
		Version:   "v1",
		Labels:    map[string]string{},
	})
}

func (b *KubernetesGraphBuilder) addNodes(g *model.Graph, state map[string]map[string]any) {
	for uid, obj := range state {
		kind, _ := obj["kind"].(string)
		apiVersion, _ := obj["apiVersion"].(string)
		if apiVersion == "" {
			apiVersion = "v1"
		}

		var group, version string
		if parts := strings.SplitN(apiVersion, "/", 2); len(parts) == 2 {
			group = parts[0]
			version = parts[1]
		} else {
			group = ""
			version = apiVersion
		}

		meta, _ := obj["metadata"].(map[string]any)
		name, _ := meta["name"].(string)
		namespace, _ := meta["namespace"].(string)

		labels := make(map[string]string)
		if rawLabels, ok := meta["labels"].(map[string]any); ok {
			for k, v := range rawLabels {
				if s, ok := v.(string); ok {
					labels[k] = s
				}
			}
		}

		g.AddNode(model.Node{
			ID:        uid,
			Kind:      kind,
			Name:      name,
			Namespace: namespace,
			Group:     group,
			Version:   version,
			Labels:    labels,
		})
	}
}

type lookupKey struct {
	kind      string
	namespace string
	name      string
}

func (b *KubernetesGraphBuilder) buildIndex(g *model.Graph) map[lookupKey]string {
	idx := make(map[lookupKey]string, len(g.Nodes))
	for uid, node := range g.Nodes {
		if uid == ClusterUID {
			continue
		}
		idx[lookupKey{kind: node.Kind, namespace: node.Namespace, name: node.Name}] = uid
	}
	return idx
}

func (b *KubernetesGraphBuilder) lookup(idx map[lookupKey]string, kind, namespace, name string) (string, bool) {
	uid, ok := idx[lookupKey{kind: kind, namespace: namespace, name: name}]
	return uid, ok
}

func (b *KubernetesGraphBuilder) addOwnershipEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		if uid == ClusterUID {
			continue
		}

		obj := state[uid]
		meta, _ := obj["metadata"].(map[string]any)
		ownerRefs, _ := meta["ownerReferences"].([]any)

		linked := false
		for _, refItem := range ownerRefs {
			ref, ok := refItem.(map[string]any)
			if !ok {
				continue
			}
			ownerUID, _ := ref["uid"].(string)
			if ownerUID != "" {
				if _, exists := g.Nodes[ownerUID]; exists {
					g.AddEdge(ownerUID, uid, "OWNS")
					linked = true
				}
			}
		}

		if !linked {
			if _, isClusterScoped := clusterScopedKinds[node.Kind]; isClusterScoped || node.Namespace == "" {
				g.AddEdge(ClusterUID, uid, "OWNS")
			} else if node.Kind != "Endpoints" && node.Kind != "EndpointSlice" {
				if nsUID, ok := b.lookup(idx, "Namespace", "", node.Namespace); ok {
					g.AddEdge(nsUID, uid, "OWNS")
				}
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addRuntimeEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		if node.Kind != "Pod" {
			continue
		}
		obj := state[uid]
		spec, _ := obj["spec"].(map[string]any)
		nodeName, _ := spec["nodeName"].(string)
		if nodeName != "" {
			if nodeUID, ok := b.lookup(idx, "Node", "", nodeName); ok {
				g.AddEdge(nodeUID, uid, "NODE_RUNS_POD")
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addServiceEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for svcUID, svc := range g.Nodes {
		if svc.Kind != "Service" {
			continue
		}
		obj := state[svcUID]
		spec, _ := obj["spec"].(map[string]any)
		rawSelector, _ := spec["selector"].(map[string]any)
		if len(rawSelector) == 0 {
			continue
		}

		selector := make(map[string]string, len(rawSelector))
		for k, v := range rawSelector {
			if s, ok := v.(string); ok {
				selector[k] = s
			}
		}

		for podUID, pod := range g.Nodes {
			if pod.Kind == "Pod" && pod.Namespace == svc.Namespace {
				match := true
				for k, v := range selector {
					if pod.Labels[k] != v {
						match = false
						break
					}
				}
				if match {
					g.AddEdge(svcUID, podUID, "SERVICE_SELECTS_POD")
				}
			}
		}
	}
}

func (b *KubernetesGraphBuilder) ensurePort(g *model.Graph, namespace, ownerName, port, proto string) string {
	if proto == "" {
		proto = "TCP"
	}
	portUID := fmt.Sprintf("port:%s:%s:%s:%s", namespace, ownerName, port, proto)
	if _, exists := g.Nodes[portUID]; !exists {
		g.AddNode(model.Node{
			ID:        portUID,
			Kind:      "Port",
			Name:      fmt.Sprintf("%s:%s/%s", ownerName, port, proto),
			Namespace: namespace,
			Group:     "",
			Version:   "v1",
			Labels:    map[string]string{},
		})
	}
	return portUID
}

func (b *KubernetesGraphBuilder) addDeclaredPortEdges(g *model.Graph, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		obj := state[uid]
		spec, _ := obj["spec"].(map[string]any)
		if spec == nil {
			continue
		}

		if node.Kind == "Service" {
			ports, _ := spec["ports"].([]any)
			for _, item := range ports {
				p, ok := item.(map[string]any)
				if !ok || p["port"] == nil {
					continue
				}
				portStr := fmt.Sprintf("%v", p["port"])
				proto, _ := p["protocol"].(string)
				portUID := b.ensurePort(g, node.Namespace, node.Name, portStr, proto)
				g.AddEdge(uid, portUID, "SERVICE_OWNS_PORT")
			}
		} else if node.Kind == "Pod" {
			containers, _ := spec["containers"].([]any)
			for _, cItem := range containers {
				c, ok := cItem.(map[string]any)
				if !ok {
					continue
				}
				ports, _ := c["ports"].([]any)
				for _, pItem := range ports {
					p, ok := pItem.(map[string]any)
					if !ok || p["containerPort"] == nil {
						continue
					}
					portStr := fmt.Sprintf("%v", p["containerPort"])
					proto, _ := p["protocol"].(string)
					portUID := b.ensurePort(g, node.Namespace, node.Name, portStr, proto)
					g.AddEdge(uid, portUID, "POD_OWNS_PORT")
				}
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addEndpointsEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for epUID, ep := range g.Nodes {
		if ep.Kind != "Endpoints" {
			continue
		}
		obj := state[epUID]

		svcUID, hasSvc := b.lookup(idx, "Service", ep.Namespace, ep.Name)
		if hasSvc {
			g.AddEdge(svcUID, epUID, "SERVICE_HAS_ENDPOINTS")
		}

		subsets, _ := obj["subsets"].([]any)
		for _, sItem := range subsets {
			subset, ok := sItem.(map[string]any)
			if !ok {
				continue
			}

			addresses, _ := subset["addresses"].([]any)
			for _, aItem := range addresses {
				addr, ok := aItem.(map[string]any)
				if !ok {
					continue
				}
				targetRef, _ := addr["targetRef"].(map[string]any)
				if targetRef == nil || targetRef["kind"] != "Pod" {
					continue
				}

				podName, _ := targetRef["name"].(string)
				podUID, _ := targetRef["uid"].(string)
				if podUID == "" {
					podUID, _ = b.lookup(idx, "Pod", ep.Namespace, podName)
				}
				if podUID == "" {
					continue
				}
				if _, exists := g.Nodes[podUID]; !exists {
					continue
				}

				g.AddEdge(epUID, podUID, "ENDPOINTS_TARGET_POD")

				ports, _ := subset["ports"].([]any)
				for _, pItem := range ports {
					p, ok := pItem.(map[string]any)
					if !ok || p["port"] == nil {
						continue
					}
					portNum := fmt.Sprintf("%v", p["port"])
					proto, _ := p["protocol"].(string)

					podPortUID := b.ensurePort(g, ep.Namespace, podName, portNum, proto)
					svcPortUID := b.ensurePort(g, ep.Namespace, ep.Name, portNum, proto)

					g.AddEdge(podUID, podPortUID, "POD_OWNS_PORT")
					if hasSvc {
						g.AddEdge(svcUID, svcPortUID, "SERVICE_OWNS_PORT")
						g.AddEdge(svcPortUID, podPortUID, "SERVICE_TARGETS_PORT")
					}
				}
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addMountEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		if node.Kind != "Pod" {
			continue
		}
		obj := state[uid]
		spec, _ := obj["spec"].(map[string]any)
		volumes, _ := spec["volumes"].([]any)

		for _, vItem := range volumes {
			vol, ok := vItem.(map[string]any)
			if !ok {
				continue
			}

			if cm, ok := vol["configMap"].(map[string]any); ok {
				if cmName, ok := cm["name"].(string); ok && cmName != "" {
					if cmUID, ok := b.lookup(idx, "ConfigMap", node.Namespace, cmName); ok {
						g.AddEdge(uid, cmUID, "POD_MOUNTS_CONFIGMAP")
					}
				}
			}

			if sec, ok := vol["secret"].(map[string]any); ok {
				if secName, ok := sec["secretName"].(string); ok && secName != "" {
					if secUID, ok := b.lookup(idx, "Secret", node.Namespace, secName); ok {
						g.AddEdge(uid, secUID, "POD_MOUNTS_SECRET")
					}
				}
			}

			if pvc, ok := vol["persistentVolumeClaim"].(map[string]any); ok {
				if pvcName, ok := pvc["claimName"].(string); ok && pvcName != "" {
					if pvcUID, ok := b.lookup(idx, "PersistentVolumeClaim", node.Namespace, pvcName); ok {
						g.AddEdge(uid, pvcUID, "POD_MOUNTS_PVC")
					}
				}
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addVolumeEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		if node.Kind != "PersistentVolume" {
			continue
		}
		obj := state[uid]
		spec, _ := obj["spec"].(map[string]any)
		claimRef, _ := spec["claimRef"].(map[string]any)
		if claimRef == nil {
			continue
		}

		claimNamespace, _ := claimRef["namespace"].(string)
		claimName, _ := claimRef["name"].(string)
		if claimName != "" {
			if pvcUID, ok := b.lookup(idx, "PersistentVolumeClaim", claimNamespace, claimName); ok {
				g.AddEdge(uid, pvcUID, "PV_BOUND_TO_PVC")
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addHPAEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		if node.Kind != "HorizontalPodAutoscaler" {
			continue
		}
		obj := state[uid]
		spec, _ := obj["spec"].(map[string]any)
		ref, _ := spec["scaleTargetRef"].(map[string]any)
		if ref == nil {
			continue
		}

		targetKind, _ := ref["kind"].(string)
		targetName, _ := ref["name"].(string)
		if targetKind != "" && targetName != "" {
			if targetUID, ok := b.lookup(idx, targetKind, node.Namespace, targetName); ok {
				g.AddEdge(uid, targetUID, "HPA_SCALES")
			}
		}
	}
}

func (b *KubernetesGraphBuilder) addHTTPRouteEdges(g *model.Graph, idx map[lookupKey]string, state map[string]map[string]any) {
	for uid, node := range g.Nodes {
		if node.Kind != "HTTPRoute" {
			continue
		}
		obj := state[uid]
		spec, _ := obj["spec"].(map[string]any)
		if spec == nil {
			continue
		}

		// parentRefs
		if parentRefs, ok := spec["parentRefs"].([]any); ok {
			for _, pItem := range parentRefs {
				ref, ok := pItem.(map[string]any)
				if !ok {
					continue
				}
				gwKind, _ := ref["kind"].(string)
				if gwKind != "" && gwKind != "Gateway" {
					continue
				}
				gwNS, _ := ref["namespace"].(string)
				if gwNS == "" {
					gwNS = node.Namespace
				}
				gwName, _ := ref["name"].(string)
				if gwName != "" {
					if gwUID, ok := b.lookup(idx, "Gateway", gwNS, gwName); ok {
						g.AddEdge(uid, gwUID, "HTTPROUTE_ATTACHES_GATEWAY")
					}
				}
			}
		}

		// rules
		if rules, ok := spec["rules"].([]any); ok {
			for _, rItem := range rules {
				rule, ok := rItem.(map[string]any)
				if !ok {
					continue
				}
				backendRefs, _ := rule["backendRefs"].([]any)
				for _, bItem := range backendRefs {
					backend, ok := bItem.(map[string]any)
					if !ok {
						continue
					}
					svcKind, _ := backend["kind"].(string)
					if svcKind != "" && svcKind != "Service" {
						continue
					}
					svcNS, _ := backend["namespace"].(string)
					if svcNS == "" {
						svcNS = node.Namespace
					}
					svcName, _ := backend["name"].(string)
					if svcName != "" {
						if svcUID, ok := b.lookup(idx, "Service", svcNS, svcName); ok {
							g.AddEdge(uid, svcUID, "HTTPROUTE_ROUTES_SERVICE")
						}
					}
				}
			}
		}
	}
}

// SanitizeObject extracts the object UID and strips sensitive and high-cardinality metadata fields.
func SanitizeObject(obj map[string]any) (string, map[string]any, bool) {
	meta, ok := obj["metadata"].(map[string]any)
	if !ok {
		return "", nil, false
	}
	uid, _ := meta["uid"].(string)
	if uid == "" {
		return "", nil, false
	}

	delete(obj, "data")
	delete(obj, "stringData")
	delete(meta, "managedFields")

	return uid, obj, true
}
