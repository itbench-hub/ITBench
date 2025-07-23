import json
import networkx as nx
import matplotlib.pyplot as plt
from collections import defaultdict
import logging
from typing import Dict, Set, Tuple
import argparse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TaxonomyVisualizer:
    def __init__(self, topology_data: Dict):
        self.topology_data = topology_data
        self.instance_graph = nx.DiGraph()  # Original instance graph
        self.kind_graph = nx.DiGraph()      # Abstract kind graph
        self._build_instance_graph()
        self._build_kind_graph()

    def _build_instance_graph(self):
        for node in self.topology_data.get("nodes", []):
            self.instance_graph.add_node(node["id"], **node.get("attributes", {}))
        for edge in self.topology_data.get("edges", []):
            self.instance_graph.add_edge(
                edge["source"],
                edge["target"],
                **edge.get("attributes", {})
            )

    def _build_kind_graph(self):
        # Track resource kinds and their properties
        kind_properties = defaultdict(lambda: {
            "count": 0,
            "is_namespaced": False,
            "relationship_counts": defaultdict(lambda: defaultdict(int))
        })

        # Analyze nodes
        for node_id, attrs in self.instance_graph.nodes(data=True):
            kind = attrs.get('kind')
            if kind:
                kind_properties[kind]["count"] += 1
                if attrs.get('namespace'):
                    kind_properties[kind]["is_namespaced"] = True

        # Analyze edges
        for source, target, data in self.instance_graph.edges(data=True):
            source_kind = self.instance_graph.nodes[source].get('kind')
            target_kind = self.instance_graph.nodes[target].get('kind')
            rel_types = data.get('type', 'UNKNOWN')
            # Handle both single string and list of relationship types
            if isinstance(rel_types, str):
                rel_types = [rel_types]

            if source_kind and target_kind:
                for rel_type in rel_types:
                    kind_properties[source_kind]["relationship_counts"][target_kind][rel_type] += 1

        # Build kind graph
        for kind, props in kind_properties.items():
            self.kind_graph.add_node(
                kind,
                count=props["count"],
                is_namespaced=props["is_namespaced"]
            )

        # Add edges with relationship information
        for source_kind, props in kind_properties.items():
            for target_kind, rel_counts in props["relationship_counts"].items():
                # Combine all relationship types and their counts
                rel_info = [f"{rel_type}: {count}"
                           for rel_type, count in rel_counts.items()]
                self.kind_graph.add_edge(
                    source_kind,
                    target_kind,
                    relationship_types=rel_counts.keys(),
                    relationship_counts=rel_counts,
                    label="\n".join(rel_info)
                )

    def create_taxonomy_json(self) -> Dict:
        taxonomy = {
            "resource_kinds": {},
            "relationships": [],
            "statistics": {
                "total_kinds": self.kind_graph.number_of_nodes(),
                "total_relationships": self.kind_graph.number_of_edges(),
                "namespaced_kinds": sum(1 for _, d in self.kind_graph.nodes(data=True) if d["is_namespaced"]),
                "cluster_scoped_kinds": sum(1 for _, d in self.kind_graph.nodes(data=True) if not d["is_namespaced"])
            }
        }

        # Add resource kinds
        for kind, data in self.kind_graph.nodes(data=True):
            taxonomy["resource_kinds"][kind] = {
                "instance_count": data["count"],
                "scope": "Namespaced" if data["is_namespaced"] else "Cluster",
                "outgoing_relationships": defaultdict(list),
                "incoming_relationships": defaultdict(list)
            }

        # Add relationships
        for source, target, data in self.kind_graph.edges(data=True):
            rel_data = {
                "source_kind": source,
                "target_kind": target,
                "relationships": {
                    rel_type: count
                    for rel_type, count in data["relationship_counts"].items()
                }
            }
            taxonomy["relationships"].append(rel_data)

            # Update kind relationship lists
            for rel_type, count in data["relationship_counts"].items():
                taxonomy["resource_kinds"][source]["outgoing_relationships"][target].append({
                    "type": rel_type,
                    "count": count
                })
                taxonomy["resource_kinds"][target]["incoming_relationships"][source].append({
                    "type": rel_type,
                    "count": count
                })

        return taxonomy

    def visualize(self, output_file: str):
        plt.figure(figsize=(20, 20))

        # Use spring layout for node positioning
        pos = nx.spring_layout(self.kind_graph, k=1, iterations=50)

        # Draw nodes
        namespaced_nodes = [n for n, d in self.kind_graph.nodes(data=True) if d["is_namespaced"]]
        cluster_nodes = [n for n, d in self.kind_graph.nodes(data=True) if not d["is_namespaced"]]

        # Draw namespaced nodes in blue
        nx.draw_networkx_nodes(
            self.kind_graph, pos,
            nodelist=namespaced_nodes,
            node_color='lightblue',
            node_size=3000,
            alpha=0.6
        )

        # Draw cluster-scoped nodes in red
        nx.draw_networkx_nodes(
            self.kind_graph, pos,
            nodelist=cluster_nodes,
            node_color='lightcoral',
            node_size=3000,
            alpha=0.6
        )

        # Draw edges
        nx.draw_networkx_edges(
            self.kind_graph, pos,
            edge_color='gray',
            arrows=True,
            arrowsize=20
        )

        # Add node labels with counts
        labels = {
            node: f"{node}\n({data['count']} instances)"
            for node, data in self.kind_graph.nodes(data=True)
        }
        nx.draw_networkx_labels(
            self.kind_graph, pos,
            labels=labels,
            font_size=8
        )

        # Add edge labels
        edge_labels = nx.get_edge_attributes(self.kind_graph, 'label')
        nx.draw_networkx_edge_labels(
            self.kind_graph, pos,
            edge_labels=edge_labels,
            font_size=6
        )

        # Add legend
        plt.plot([], [], 'lightblue', marker='o', markersize=15, label='Namespaced Resources', linestyle='None', alpha=0.6)
        plt.plot([], [], 'lightcoral', marker='o', markersize=15, label='Cluster-Scoped Resources', linestyle='None', alpha=0.6)
        plt.legend(loc='upper left', bbox_to_anchor=(1, 1))

        plt.title("Kubernetes Resource Type Taxonomy\n(Node size based on instance count)")
        plt.axis('off')
        plt.tight_layout()

        # Save the plot
        plt.savefig(output_file, bbox_inches='tight', dpi=300)
        plt.close()
        logger.info(f"Visualization saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(description='Visualize K8s resource type taxonomy')
    parser.add_argument('--topology', required=True,
                      help='Input JSON file containing topology data')
    parser.add_argument('--output-viz', required=True,
                      help='Output PNG file for visualization')
    parser.add_argument('--output-json', required=True,
                      help='Output JSON file for detailed taxonomy')

    args = parser.parse_args()

    try:
        # Load topology data
        with open(args.topology, 'r') as f:
            topology_data = json.load(f)

        # Create visualizer
        visualizer = TaxonomyVisualizer(topology_data)

        # Create and save visualization
        visualizer.visualize(args.output_viz)

        # Create and save JSON taxonomy
        taxonomy = visualizer.create_taxonomy_json()
        with open(args.output_json, 'w') as f:
            json.dump(taxonomy, f, indent=2)
        logger.info(f"Taxonomy JSON saved to {args.output_json}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
