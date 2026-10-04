"""Workload discovery utilities for ITBench applications.

Invokes the ``discover_applications.yaml`` Ansible playbook (via ansible-runner)
which renders each application's Helm chart / manifests into
``.itbench/discovery/<app-id>/`` directories. The parser then walks those
directories and extracts every ``Deployment``, ``StatefulSet``, and ``Service``
resource as a :class:`~itbench.models.kubernetes.KubernetesObject`.
"""

from pathlib import Path

import yaml

from itbench.models.kubernetes import KubernetesObject
from itbench.utils.runner import run_playbook

_TARGET_KINDS = {"Deployment", "StatefulSet", "Service"}


def discover_workloads(app_id: str | None = None) -> dict[str, list[KubernetesObject]]:
    """Run the discovery playbook and return workloads grouped by application id."""
    run_playbook(
        playbook="discover_applications.yaml",
        tags=["discover_applications"],
    )
    return _parse_discovery_dir(app_id=app_id)


def get_application_workloads(app_id: str) -> list[KubernetesObject]:
    """Return the targetable workloads for a single application slug."""
    return discover_workloads(app_id=app_id).get(app_id, [])


def _parse_discovery_dir(app_id: str | None = None) -> dict[str, list[KubernetesObject]]:
    results: dict[str, list[KubernetesObject]] = {}
    discovery_dir = Path.cwd() / ".itbench" / "discovery"

    if not discovery_dir.exists():
        return results

    app_dirs = (
        [discovery_dir / app_id]
        if app_id
        else [p for p in discovery_dir.iterdir() if p.is_dir()]
    )

    for app_dir in app_dirs:
        if not app_dir.is_dir():
            continue

        slug = app_dir.name
        workloads: list[KubernetesObject] = []

        for yaml_file in sorted(app_dir.rglob("*.yaml")):
            _extract_targets_from_file(yaml_file, workloads)

        results[slug] = workloads

    return results


def _extract_targets_from_file(path: Path, targets: list[KubernetesObject]) -> None:
    """Parse a YAML manifest file and append matching workload targets.

    Handles multi-document YAML (``---`` separated). Skips documents that are
    not mappings, have an unrecognised kind, or lack a name.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return

    for doc in yaml.safe_load_all(text):
        if not isinstance(doc, dict):
            continue

        kind = doc.get("kind")
        if kind not in _TARGET_KINDS:
            continue

        metadata = doc.get("metadata", {})
        name = metadata.get("name")
        namespace = metadata.get("namespace")

        if not name:
            continue

        targets.append(KubernetesObject(kind=kind, name=name, namespace=namespace))
