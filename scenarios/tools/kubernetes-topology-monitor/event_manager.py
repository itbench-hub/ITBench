# event_manager.py

import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import threading

class EventLogger:
    """
    Responsible for writing events to log files.
    Includes:
      - A lock to prevent race conditions in file I/O (if multiple threads log).
      - Extended logging to capture 'id' and 'uid' from resource_info.
      - Optionally logs all owners in resource_info['owners'] (if present).
    """
    def __init__(self, log_dir: str = "./topology_data"):
        """Initialize event logger with the specified directory."""
        self.logger = logging.getLogger("event_logger")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Lock for concurrency safety in record_event()
        self._write_lock = threading.Lock()

    def _get_current_logfile(self) -> Path:
        """Get the path for today's log file."""
        current_date = datetime.now().strftime("%Y-%m-%d")
        return self.log_dir / f"k8s_events_{current_date}.log"

    def should_record_event(self, event_type: str, resource_info: Dict[str, Any]) -> bool:
        """Filter out high-frequency or noisy events."""
        # Skip lease modifications
        if resource_info.get('kind') == 'Lease' and event_type == 'MODIFIED':
            return False
        # Skip endpoint modifications
        if resource_info.get('kind') == 'Endpoints' and event_type == 'MODIFIED':
            return False
        return True

    def record_event(self, event_type: str, resource_info: Dict[str, Any],
                     owner_info: Optional[Dict[str, Any]] = None,
                     additional_data: Optional[Dict[str, Any]] = None):
        """Record a resource event to the log file, including stable ID, UID, owners, etc."""
        if not self.should_record_event(event_type, resource_info):
            return

        with self._write_lock:
            try:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                log_file = self._get_current_logfile()

                # Prepare relevant fields
                kind = resource_info.get('kind', '')
                group = resource_info.get('group', '')
                version = resource_info.get('version', '')
                namespace = resource_info.get('namespace', '')
                name = resource_info.get('name', '')
                stable_id = resource_info.get('id', '')   # The stable node ID
                uid = resource_info.get('uid', '')        # The Kubernetes UID
                owners = resource_info.get('owners', [])  # All owners (list of dicts)

                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write('-' * 80 + '\n')  # Separator line
                    f.write(f"Timestamp: {timestamp}\n")
                    f.write(f"Event Type: {event_type}\n")
                    f.write(f"Resource:\n")
                    f.write(f"  Kind: {kind}\n")
                    f.write(f"  Group: {group}\n")
                    f.write(f"  Version: {version}\n")
                    f.write(f"  Namespace: {namespace}\n")
                    f.write(f"  Name: {name}\n")
                    # New lines for stable ID and UID
                    f.write(f"  ID: {stable_id}\n")
                    f.write(f"  UID: {uid}\n")

                    # If you’d like to log *all* owners, you can do so here:
                    if owners:
                        f.write(f"Owners:\n")
                        for idx, o in enumerate(owners, start=1):
                            f.write(f"  - Owner #{idx}:\n")
                            f.write(f"      Kind: {o.get('kind', '')}\n")
                            f.write(f"      Name: {o.get('name', '')}\n")
                            f.write(f"      UID: {o.get('uid', '')}\n")

                    # If you want to keep "owner_info" as a special single-owner field
                    # (for backward-compatibility or other reasons), here’s how:
                    if owner_info:
                        f.write("Owner (Primary):\n")
                        f.write(f"  Kind: {owner_info.get('kind', '')}\n")
                        f.write(f"  Name: {owner_info.get('name', '')}\n")
                        # Typically we don’t store 'namespace' here if cluster-scoped,
                        # but you could if it’s relevant. So for example:
                        # f.write(f"  Namespace: {owner_info.get('namespace', '')}\n")
                        # f.write(f"  UID: {owner_info.get('uid', '')}\n")

                    if additional_data:
                        f.write(f"Additional Data:\n")
                        json_str = json.dumps(additional_data, indent=2).replace('\n', '\n  ')
                        f.write(f"  {json_str}\n")
                    f.flush()

            except Exception as e:
                self.logger.error(f"Error recording event: {e}", exc_info=True)

    def cleanup_old_logs(self, days_to_keep: int = 30):
        """Remove log files older than specified days."""
        try:
            cutoff_date = datetime.now().timestamp() - (days_to_keep * 24 * 3600)
            cleaned = 0
            for log_file in self.log_dir.glob("k8s_events_*.log"):
                if log_file.stat().st_mtime < cutoff_date:
                    log_file.unlink()
                    cleaned += 1
            if cleaned > 0:
                self.logger.info(f"Cleaned up {cleaned} old log files")
        except Exception as e:
            self.logger.error(f"Error cleaning up old logs: {e}", exc_info=True)
