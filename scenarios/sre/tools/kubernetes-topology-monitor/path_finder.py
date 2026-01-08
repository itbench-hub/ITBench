import networkx as nx
import json
import argparse
import logging
from typing import Set, Dict, Any
from pathlib import Path

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class SubgraphExtractor:
    def __init__(self, topology_data: Dict):
        self.topology_data = topology_data
        self.graph = nx.DiGraph()
        self._build_graph()
        logger.debug(f"Built graph with {len(self.graph.nodes)} nodes and {len(self.graph.edges)} edges")

    def _build_graph(self):
        for node in self.topology_data.get("nodes", []):
            self.graph.add_node(node["id"], **node.get("attributes", {}))
        for edge in self.topology_data.get("edges", []):
            self.graph.add_edge(edge["source"], edge["target"], **edge.get("attributes", {}))

    def _find_paths_to_root(self, start_node: str) -> Set[str]:
        nodes_in_paths = set()
        paths = [[start_node]]
        explored_paths = set()

        while paths:
            current_path = paths.pop(0)
            current_node = current_path[-1]
            path_key = ','.join(current_path)

            if path_key in explored_paths:
                continue

            explored_paths.add(path_key)
            nodes_in_paths.update(current_path)

            # Add paths through all predecessors
            for pred in self.graph.predecessors(current_node):
                if pred not in current_path:  # Avoid cycles
                    new_path = current_path + [pred]
                    paths.append(new_path)

        return nodes_in_paths

    def _find_paths_to_leaves(self, start_node: str) -> Set[str]:
        nodes_in_paths = set()
        paths = [[start_node]]
        explored_paths = set()

        while paths:
            current_path = paths.pop(0)
            current_node = current_path[-1]
            path_key = ','.join(current_path)

            if path_key in explored_paths:
                continue

            explored_paths.add(path_key)
            nodes_in_paths.update(current_path)

            # Add paths through all successors
            successors = list(self.graph.successors(current_node))
            if not successors:  # This is a leaf node
                continue

            for succ in successors:
                if succ not in current_path:  # Avoid cycles
                    new_path = current_path + [succ]
                    paths.append(new_path)

        return nodes_in_paths

    def extract_subgraph(self, node_id: str) -> Dict:
        if node_id not in self.graph:
            raise ValueError(f"Node {node_id} not found in graph")

        # Get all nodes in paths
        nodes_to_root = self._find_paths_to_root(node_id)
        nodes_to_leaves = self._find_paths_to_leaves(node_id)
        all_nodes = nodes_to_root.union(nodes_to_leaves)

        logger.debug(f"Found {len(nodes_to_root)} nodes to root")
        logger.debug(f"Found {len(nodes_to_leaves)} nodes to leaves")
        logger.debug(f"Total unique nodes: {len(all_nodes)}")

        # Create subgraph
        subgraph = self.graph.subgraph(all_nodes)

        # Debug edges
        logger.debug("\nEdges in subgraph:")
        for edge in subgraph.edges(data=True):
            source_kind = subgraph.nodes[edge[0]].get('kind')
            target_kind = subgraph.nodes[edge[1]].get('kind')
            logger.debug(f"  {source_kind} -> {target_kind} ({edge[2]['type']})")

        # Format result
        result = {
            "nodes": [
                {
                    "id": node,
                    "attributes": dict(subgraph.nodes[node]),
                    "position": self._determine_position(node, subgraph)
                }
                for node in subgraph.nodes()
            ],
            "edges": [
                {
                    "source": source,
                    "target": target,
                    "attributes": dict(data)
                }
                for source, target, data in subgraph.edges(data=True)
            ]
        }

        return result

    def _determine_position(self, node: str, graph: nx.DiGraph) -> str:
        """Determine node's position in the hierarchy."""
        if (graph.nodes[node].get('kind') == 'K8Cluster' or
            graph.in_degree(node) == 0):
            return "root"
        elif graph.out_degree(node) == 0:
            return "leaf"
        else:
            return "intermediate"

def main():
    parser = argparse.ArgumentParser(description='Extract subgraph from K8s topology')
    parser.add_argument('--topology', required=True,
                      help='Input JSON file containing topology data')
    parser.add_argument('--output', required=True,
                      help='Output JSON file for subgraph')
    parser.add_argument('--node-id',
                      help='Node ID to extract subgraph from')
    parser.add_argument('--kind',
                      help='Kind of resource to find')
    parser.add_argument('--name',
                      help='Name of resource to find')
    parser.add_argument('--namespace',
                      help='Namespace of resource')

    args = parser.parse_args()

    try:
        # Load topology data
        with open(args.topology, 'r') as f:
            topology_data = json.load(f)

        extractor = SubgraphExtractor(topology_data)

        # Find node ID if not provided directly
        node_id = args.node_id
        if not node_id:
            if not (args.kind and args.name):
                raise ValueError("Must provide either --node-id or both --kind and --name")

            search_attrs = {
                'kind': args.kind,
                'name': args.name
            }
            if args.namespace:
                search_attrs['namespace'] = args.namespace

            node_id = extractor.find_node_by_attributes(**search_attrs)

        # Extract and save subgraph
        subgraph = extractor.extract_subgraph(node_id)

        with open(args.output, 'w') as f:
            json.dump(subgraph, f, indent=2)
            logger.info(f"Subgraph written to {args.output}")

    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise

if __name__ == "__main__":
    main()
