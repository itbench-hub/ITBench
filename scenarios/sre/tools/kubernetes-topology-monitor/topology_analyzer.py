import networkx as nx
import json
import argparse
import sys
from typing import Dict, List
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TopologyAnalyzer:
    def __init__(self, topology_data: Dict):
        """
        Initialize the analyzer with topology data.

        Args:
            topology_data (dict): Dictionary containing nodes and edges information
        """
        self.topology_data = topology_data
        self.graph = nx.DiGraph()
        self._build_graph()

    def _build_graph(self):
        """Build the directed graph from topology data."""
        # Create a set of all node IDs for quick lookup
        node_ids = {node["id"] for node in self.topology_data.get("nodes", [])}

        # Add nodes with their attributes
        for node in self.topology_data.get("nodes", []):
            self.graph.add_node(node["id"], **node.get("attributes", {}))

        # Track missing nodes referenced in edges
        missing_nodes = set()

        # Add edges with their attributes
        for edge in self.topology_data.get("edges", []):
            source = edge["source"]
            target = edge["target"]

            # Check if both source and target nodes exist
            if source not in node_ids:
                missing_nodes.add(source)
                logger.warning(f"Edge references missing source node: {source}")
            if target not in node_ids:
                missing_nodes.add(target)
                logger.warning(f"Edge references missing target node: {target}")

            # Add the edge even if nodes are missing - we'll handle them as placeholder nodes
            if source not in self.graph:
                self.graph.add_node(source, kind="Unknown", name=f"missing-{source}")
            if target not in self.graph:
                self.graph.add_node(target, kind="Unknown", name=f"missing-{target}")

            self.graph.add_edge(source, target, **edge.get("attributes", {}))

        if missing_nodes:
            logger.warning(f"Found {len(missing_nodes)} nodes referenced in edges but not in nodes list")

        logger.info(f"Graph built with {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges")

    def _determine_position(self, node: str, subgraph: nx.DiGraph) -> str:
        in_degree = subgraph.in_degree(node)
        out_degree = subgraph.out_degree(node)

        # Parent: No incoming edges but has outgoing edges, OR isolated node
        if in_degree == 0:
            return "parent"
        # Intermediate: Both incoming and outgoing edges
        elif in_degree > 0 and out_degree > 0:
            return "intermediate"
        # Leaf: Has incoming edges but no outgoing edges
        elif in_degree > 0 and out_degree == 0:
            return "leaf"

        return "parent"  # Default case for any unhandled scenarios

    def analyze(self) -> List[Dict]:
        # Get weakly connected components
        components = list(nx.weakly_connected_components(self.graph))
        result = []

        logger.info(f"Found {len(components)} disconnected components")

        for i, component in enumerate(components, 1):
            # Create subgraph for each component
            subgraph = self.graph.subgraph(component)
            logger.info(f"Processing component {i} with {len(component)} nodes and {subgraph.number_of_edges()} edges")

            # Process nodes with position classification
            nodes = []
            node_positions = {}  # Keep track of positions for debugging
            for node in subgraph.nodes():
                position = self._determine_position(node, subgraph)
                node_positions[position] = node_positions.get(position, 0) + 1

                node_data = {
                    "id": node,
                    "attributes": dict(subgraph.nodes[node]),
                    "position": position
                }
                nodes.append(node_data)

            logger.info(f"Component {i} node positions: {node_positions}")

            # Process edges
            edges = []
            for source, target, data in subgraph.edges(data=True):
                edge_data = {
                    "source": source,
                    "target": target,
                    "attributes": data
                }
                edges.append(edge_data)

            # Create component data
            component_data = {
                "nodes": sorted(nodes, key=lambda x: (
                    {"parent": 0, "intermediate": 1, "leaf": 2}[x["position"]],
                    x["attributes"].get("name", "")
                )),
                "edges": edges
            }

            result.append(component_data)

        return result

    def export_to_json(self, filename: str):
        analysis_results = self.analyze()
        with open(filename, 'w') as f:
            json.dump(analysis_results, f, indent=2)
            logger.info(f"Results written to {filename}")

def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(description='Analyze topology data and identify disconnected components.')
    parser.add_argument('--in', dest='input_file', required=True,
                      help='Input JSON file containing topology data')
    parser.add_argument('--out', dest='output_file', required=True,
                      help='Output JSON file for analyzed results')
    parser.add_argument('--debug', action='store_true',
                      help='Enable debug logging')

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        with open(args.input_file, 'r') as f:
            topology_data = json.load(f)

        analyzer = TopologyAnalyzer(topology_data)

        analyzer.export_to_json(args.output_file)

    except FileNotFoundError as e:
        logger.error(f"Could not find file - {e.filename}")
        sys.exit(1)
    except json.JSONDecodeError:
        logger.error(f"Invalid JSON format in input file - {args.input_file}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred - {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
