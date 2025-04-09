import logging
import threading
import queue
import time
from typing import Optional, Dict, Any, List
from kubernetes.client.rest import ApiException
from datetime import datetime, timedelta
from event_manager import EventLogger
import sys

def LINE():
    return sys._getframe(1).f_lineno

CLUSTER_SCOPED_RESOURCES = {
    'Node', 'Namespace', 'PersistentVolume', 'ClusterRole', 'ClusterRoleBinding',
    'StorageClass', 'CSIDriver', 'CSINode', 'PriorityClass', 'RuntimeClass',
    'VolumeAttachment', 'PodSecurityPolicy', 'CustomResourceDefinition',
    'ValidatingWebhookConfiguration', 'MutatingWebhookConfiguration',
    'PodPreset', 'InitializerConfiguration'
}

class K8sResourceWatcher:
    """
    Watches resources in the cluster and queues events for processing,
    then processes them in batches to reduce lock contention and overhead.
    Also includes stable node ID, UID, and owner info in each event log.
    """

    def __init__(self, k8s_client, topology_manager, event_logger):
        self.logger = logging.getLogger("resource_watcher")
        self.k8s_client = k8s_client
        self.topology = topology_manager
        self.event_logger = event_logger

        self.watch_threads: Dict[str, threading.Thread] = {}
        self.resource_versions: Dict[str, str] = {}

        self.stop_event = threading.Event()

        # Bounded queue to prevent unbounded growth
        self.event_queue = queue.Queue(maxsize=10000)

        self.processor_thread = None

        # Tuning parameters for batch refresh:
        self.REFRESH_EVENT_COUNT = 100   # e.g., refresh after 100 relevant events
        self.REFRESH_TIME_LIMIT = 30.0   # or 30 seconds

    def start(self):
        """Start the watch threads and event processor."""
        self.stop_event.clear()

        # Start consumer thread to process queued events
        self.processor_thread = threading.Thread(
            target=self._process_events,
            daemon=True,
            name="event-processor"
        )
        self.processor_thread.start()

        # Start watches for each resource type
        self._start_resource_watches()

    def stop(self):
        """Stop all watch threads and gracefully shut down the processor."""
        self.logger.info("Stopping resource watcher...")
        self.stop_event.set()

        # Put sentinel in the queue so _process_events will exit
        self.event_queue.put(None)

        # Join the processor thread
        if self.processor_thread:
            self.processor_thread.join(timeout=5)

        # Then stop each watch thread
        for thread in self.watch_threads.values():
            thread.join()

        # (Optional) final refresh to capture last changes
        try:
            self.logger.info("Performing final topology refresh before exit...")
            self.topology.refresh_topology()
        except Exception as e:
            self.logger.error(f"Error during final refresh_topology: {e}", exc_info=True)

        self.logger.info("Resource watcher stopped.")

    def _start_resource_watches(self):
        """Start watch threads for all supported resources."""
        core_resources = {
            'Pod', 'Service', 'ConfigMap', 'Secret', 'PersistentVolumeClaim',
            'PersistentVolume', 'Node', 'Namespace', 'ServiceAccount', 'Endpoints'
        }

        # Start core resources first
        for kind in core_resources:
            self._start_watch("v1", kind)
            time.sleep(0.5)  # small delay to avoid spamming the API

        # Then watch API group resources
        for api_version, kind in self.k8s_client.get_api_resources():
            if kind not in core_resources:
                self._start_watch(api_version, kind)
                time.sleep(0.5)

    def _start_watch(self, api_version: str, kind: str):
        """Start a watch thread for a specific resource type."""
        watch_key = f"{api_version}/{kind}"

        # Avoid duplicates
        if watch_key in self.watch_threads:
            if self.watch_threads[watch_key].is_alive():
                return
            else:
                self.logger.info(f"Restarting dead watch thread for {kind}")

        self.logger.info(f"Starting watch for {kind}")
        thread = threading.Thread(
            target=self._watch_resource,
            args=(api_version, kind),
            name=f"watch-{kind.lower()}",
            daemon=True
        )
        thread.start()
        self.watch_threads[watch_key] = thread

    def _watch_resource(self, api_version: str, kind: str):
        """Watch a specific resource type and queue events."""
        try:
            resource = self.k8s_client.dynamic_client.resources.get(
                api_version=api_version,
                kind=kind
            )
            if not hasattr(resource, 'watch') or 'watch' not in resource.verbs:
                self.logger.debug(f"Resource {kind} does not support watch operation")
                return

            while not self.stop_event.is_set():
                try:
                    list_response = resource.get()
                    resource_version = list_response.metadata.resourceVersion

                    watch_iter = resource.watch(resource_version=resource_version)
                    start_time = time.time()
                    for event in watch_iter:
                        if self.stop_event.is_set() or (time.time() - start_time > 3600):
                            break

                        event_type = event['type']
                        obj = event['object']

                        # If queue is full, this blocks
                        self.event_queue.put({
                            'type': event_type,
                            'api_version': api_version,
                            'kind': kind,
                            'object': obj
                        })

                except ApiException as e:
                    if e.status == 410:  # resourceVersion too old
                        continue
                    self.logger.error(f"API error watching {kind}: {str(e)}")
                    time.sleep(5)
                except Exception as e:
                    self.logger.error(f"Error watching {kind}: {str(e)}", exc_info=True)
                    time.sleep(5)

        except Exception as e:
            self.logger.error(f"Error setting up watch for {kind}: {e}", exc_info=True)

    def _get_resource_info(self, obj) -> Dict[str, Any]:
        """
        Extract resource info from a k8s object, including:
          - group, version, kind, namespace, name
          - stable node ID from the topology
          - the K8s UID
          - list of owner references (each with kind, name, uid)
        """
        api_version = obj.apiVersion
        if '/' in api_version:
            group, version = api_version.split('/')
        else:
            group, version = "", api_version

        namespace = getattr(obj.metadata, 'namespace', '')
        name = getattr(obj.metadata, 'name', '')

        # Use the TopologyManager to get a stable ID (pre-existing function)
        stable_id = self.topology._get_stable_node_id(group, version, obj.kind, namespace, name)

        # Extract owners
        owners = []
        if getattr(obj.metadata, 'ownerReferences', None):
            for ref in obj.metadata.ownerReferences:
                owners.append({
                    'kind': ref.kind,
                    'name': ref.name,
                    'uid': ref.uid
                })

        return {
            'kind': obj.kind,
            'group': group,
            'version': version,
            'namespace': namespace,
            'name': name,
            'id': stable_id,  # stable node ID from topology
            'uid': getattr(obj.metadata, 'uid', ''),
            'owners': owners
        }

    def _process_events(self):
        """
        Main loop: pop events from the queue, log them (with ID/UID/owners),
        and occasionally refresh topology.
        """
        self.logger.info("Event processing thread started.")

        last_refresh_time = time.time()
        events_since_last_refresh = 0

        while True:
            # If stop requested AND queue is empty, exit
            if self.stop_event.is_set() and self.event_queue.empty():
                break

            try:
                event = self.event_queue.get(timeout=1.0)
            except queue.Empty:
                continue

            if event is None:
                # Sentinel for shutdown
                break

            try:
                # Build resource_info dict with ID, UID, owners
                resource_info = self._get_resource_info(event['object'])

                # For the event logger "owner_info", we can pass the first owner (if any)
                # You could also pass the entire list if needed by your design
                owner_info = resource_info['owners'][0] if resource_info['owners'] else None

                # Record the event
                self.event_logger.record_event(
                    event['type'],
                    resource_info,
                    owner_info=owner_info
                )

                # If relevant event, schedule a topology refresh
                if event['type'] in ('ADDED', 'MODIFIED', 'DELETED'):
                    events_since_last_refresh += 1

                    now = time.time()
                    elapsed = now - last_refresh_time
                    if (events_since_last_refresh >= self.REFRESH_EVENT_COUNT) or \
                       (elapsed >= self.REFRESH_TIME_LIMIT):
                        # Perform one refresh
                        self.logger.debug(f"Triggering refresh_topology() after "
                                          f"{events_since_last_refresh} events or {int(elapsed)}s elapsed.")
                        self.topology.refresh_topology()

                        # Reset counters
                        last_refresh_time = now
                        events_since_last_refresh = 0

            except Exception as e:
                self.logger.error(f"Error processing event: {e}", exc_info=True)
            finally:
                self.event_queue.task_done()

        self.logger.info("Event processing thread exiting.")
