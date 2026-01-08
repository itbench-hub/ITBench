from flask import Flask, jsonify
from datetime import datetime
import os

app = Flask(__name__)

# Global reference to topology manager
topology_manager = None
event_logger = None

@app.route('/healthz')
def healthz():
    """
    Simple health check endpoint for Kubernetes.
    """
    return jsonify({"status": "ok"}), 200

@app.route('/nodes')
def get_nodes():
    topology_manager.refresh_topology()
    return jsonify([{
        'id': node_id,
        **{k: str(v) for k, v in topology_manager.graph.nodes[node_id].items()}  # Convert all values to strings
    } for node_id in topology_manager.graph.nodes])

@app.route('/edges')
def get_edges():
    topology_manager.refresh_topology()  # Ensure latest state
    return jsonify([{
        'source': source,
        'target': target,
        **attrs
    } for source, target, attrs in topology_manager.graph.edges(data=True)])

@app.route('/graph')
def get_graph():
    topology_manager.refresh_topology()  # Ensure latest state
    return jsonify(topology_manager._serialize_graph())

@app.route('/events')
def get_events():
    events = []
    current_date = datetime.now().strftime("%Y-%m-%d")
    log_file = event_logger._get_current_logfile()

    if log_file.exists():
        with open(log_file, 'r') as f:
            events = f.read().split('-' * 80)
            events = [e.strip() for e in events if e.strip()]

    return jsonify(events)


@app.route('/refresh')
def refresh_topology():
    """Endpoint to manually trigger topology refresh"""
    topology_manager.refresh_topology()
    return jsonify({"status": "success"})

def start_server(topology_mgr, evt_logger):
    global topology_manager, event_logger
    topology_manager = topology_mgr
    event_logger = evt_logger
    app.run(host='0.0.0.0', port=8080)
