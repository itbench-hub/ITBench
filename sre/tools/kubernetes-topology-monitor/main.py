import logging
import time
import argparse
import os
from pathlib import Path
from typing import Optional

from topology_manager import K8sTopologyManager
from topology_manager import K8sClient
from resource_watcher import K8sResourceWatcher
from event_manager import EventLogger
import threading

def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

def run_snapshot_thread(topology, interval, logger):
    """Periodically save topology snapshots."""
    while True:
        try:
            topology.save_snapshot()
            topology.cleanup_old_snapshots()
            time.sleep(interval)
        except Exception as e:
            logger.error(f"Error in snapshot thread: {e}", exc_info=True)
            time.sleep(60)

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Kubernetes Topology Monitor')
    parser.add_argument('--kubeconfig',
                       help='Path to kubeconfig file. If not specified, uses default ~/.kube/config. '
                            'The current-context from the kubeconfig will be used.')
    parser.add_argument('--data-dir', default='./topology_data',
                       help='Directory for storing topology data')
    parser.add_argument('--interval', type=int, default=300,
                       help='Collection interval in seconds')
    parser.add_argument('--max-snapshots', type=int, default=10,
                       help='Maximum number of snapshots to keep')
    parser.add_argument('--log-level', default='INFO',
                       choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Logging level')
    return parser.parse_args()


def main():
    args = parse_args()
    setup_logging(args.log_level)

    try:
        k8s_client = K8sClient(kubeconfig_path=args.kubeconfig)
        topology = K8sTopologyManager(k8s_client, persistence_dir=args.data_dir)
        event_logger = EventLogger(log_dir=args.data_dir)
        logger = logging.getLogger("k8s_client")
        # Load existing topology if available
        latest_snapshot = topology.get_latest_snapshot()
        if latest_snapshot:
            topology.load_snapshot(latest_snapshot)
        else:
            # Initial topology build
            topology.refresh_topology()

        # Start the watcher
        watcher = K8sResourceWatcher(k8s_client, topology, event_logger)
        watcher.start()

        # Start snapshot thread
        def run_snapshots():
            while True:
                try:
                    topology.save_snapshot()
                    topology.cleanup_old_snapshots(args.max_snapshots)
                    topology.cleanup_old_nodes(max_age_seconds=3600)
                    time.sleep(args.interval)
                except Exception as e:
                    logger.error(f"Snapshot error: {e}")
                    time.sleep(60)

        snapshot_thread = threading.Thread(
            target=run_snapshots,
            daemon=True
        )
        snapshot_thread.start()

        # Start API server
        from app import start_server
        start_server(topology, event_logger)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
