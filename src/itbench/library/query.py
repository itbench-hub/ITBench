"""Query, search, and inspect ITBench library resources."""
import json
import logging

from pathlib import Path
from typing import Any

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def list_resources(library_index_directory: Path, resource_type: str) -> list[dict[str, Any]]:
    """List all resources of a given type (scenarios, faults, applications, waiters)."""
    target_dir = library_index_directory / resource_type
    if not target_dir.exists():
        return []
    resources = []
    for f in target_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            resources.append(data)
        except json.JSONDecodeError:
            continue
    return sorted(resources, key=lambda r: r.get("id", str(r.get("index", ""))))


def get_resource(library_index_directory: Path, resource_type: str, resource_id: str | int) -> dict[str, Any] | None:
    """Get a single resource by ID or index number."""
    resources = list_resources(library_index_directory, resource_type)
    for r in resources:
        if str(r.get("id")) == str(resource_id) or str(r.get("index")) == str(resource_id):
            return r
    return None


def search_resources(library_index_directory: Path, query: str) -> dict[str, list[dict[str, Any]]]:
    """Search across all library resources for matching text."""
    query_lower = query.lower()
    results: dict[str, list[dict[str, Any]]] = {
        "scenarios": [],
        "faults": [],
        "applications": [],
        "waiters": [],
    }

    for resource_type in results.keys():
        for res in list_resources(library_index_directory, resource_type):
            content_str = json.dumps(res).lower()
            if query_lower in content_str:
                results[resource_type].append(res)

    return results


def get_scenario_statistics(library_index_directory: Path) -> dict[str, dict[str, int]]:
    """Compute distribution statistics for scenarios across applications, categories, and complexities."""
    scenarios = list_resources(library_index_directory, "scenarios")
    stats: dict[str, dict[str, int]] = {
        "applications": {},
        "categories": {},
        "complexities": {},
    }

    for scenario in scenarios:
        for app in scenario.get("environment", {}).get("applications", []):
            app_id = app.get("id", "unknown")
            stats["applications"][app_id] = stats["applications"].get(app_id, 0) + 1

        cat = scenario.get("category", "unknown")
        stats["categories"][cat] = stats["categories"].get(cat, 0) + 1

        comp = scenario.get("complexity", "unknown")
        stats["complexities"][comp] = stats["complexities"].get(comp, 0) + 1

    return stats
