"""Tests for itbench.utils.manifests."""

from pathlib import Path
from unittest.mock import patch

import pytest

from itbench.models.kubernetes import KubernetesObject
from itbench.utils.manifests import (
    _extract_targets_from_file,
    _parse_discovery_dir,
    get_application_workloads,
)


def test_extract_targets_deployment(tmp_path: Path) -> None:
    manifest = tmp_path / "deploy.yaml"
    manifest.write_text(
        "apiVersion: apps/v1\nkind: Deployment\nmetadata:\n  name: frontend\n  namespace: default\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert len(targets) == 1
    assert targets[0].kind == "Deployment"
    assert targets[0].name == "frontend"
    assert targets[0].namespace == "default"


def test_extract_targets_statefulset(tmp_path: Path) -> None:
    manifest = tmp_path / "ss.yaml"
    manifest.write_text(
        "kind: StatefulSet\nmetadata:\n  name: db\n  namespace: data\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert len(targets) == 1
    assert targets[0].kind == "StatefulSet"


def test_extract_targets_service(tmp_path: Path) -> None:
    manifest = tmp_path / "svc.yaml"
    manifest.write_text(
        "kind: Service\nmetadata:\n  name: my-svc\n  namespace: default\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert len(targets) == 1
    assert targets[0].kind == "Service"


def test_extract_targets_ignores_unknown_kind(tmp_path: Path) -> None:
    manifest = tmp_path / "cm.yaml"
    manifest.write_text(
        "kind: ConfigMap\nmetadata:\n  name: cfg\n  namespace: default\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert targets == []


def test_extract_targets_skips_resource_without_name(tmp_path: Path) -> None:
    manifest = tmp_path / "nameless.yaml"
    manifest.write_text(
        "kind: Deployment\nmetadata:\n  namespace: default\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert targets == []


def test_extract_targets_handles_multi_document_yaml(tmp_path: Path) -> None:
    manifest = tmp_path / "multi.yaml"
    manifest.write_text(
        "kind: Deployment\nmetadata:\n  name: a\n  namespace: ns\n"
        "---\n"
        "kind: Service\nmetadata:\n  name: b\n  namespace: ns\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert len(targets) == 2
    kinds = {t.kind for t in targets}
    assert kinds == {"Deployment", "Service"}


def test_extract_targets_skips_non_mapping_documents(tmp_path: Path) -> None:
    manifest = tmp_path / "list.yaml"
    manifest.write_text("- item1\n- item2\n", encoding="utf-8")
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert targets == []


def test_extract_targets_handles_unreadable_file(tmp_path: Path) -> None:
    missing = tmp_path / "does_not_exist.yaml"
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(missing, targets)  # must not raise

    assert targets == []


def test_extract_targets_namespace_can_be_none(tmp_path: Path) -> None:
    manifest = tmp_path / "deploy.yaml"
    manifest.write_text(
        "kind: Deployment\nmetadata:\n  name: frontend\n",
        encoding="utf-8",
    )
    targets: list[KubernetesObject] = []
    _extract_targets_from_file(manifest, targets)

    assert targets[0].namespace is None


def test_parse_discovery_dir_returns_empty_when_missing(tmp_path: Path) -> None:
    with patch("itbench.utils.manifests.Path.cwd", return_value=tmp_path / "no-such-dir"):
        result = _parse_discovery_dir()

    assert result == {}


def test_parse_discovery_dir_groups_by_app_slug(tmp_path: Path) -> None:
    discovery = tmp_path / ".itbench" / "discovery"
    app_dir = discovery / "my-app"
    app_dir.mkdir(parents=True)
    (app_dir / "deploy.yaml").write_text(
        "kind: Deployment\nmetadata:\n  name: web\n  namespace: default\n",
        encoding="utf-8",
    )

    with patch("itbench.utils.manifests.Path.cwd", return_value=tmp_path):
        result = _parse_discovery_dir()

    assert "my-app" in result
    assert result["my-app"][0].name == "web"


def test_parse_discovery_dir_filters_to_single_app(tmp_path: Path) -> None:
    discovery = tmp_path / ".itbench" / "discovery"
    for slug in ("app-a", "app-b"):
        app_dir = discovery / slug
        app_dir.mkdir(parents=True)
        (app_dir / "deploy.yaml").write_text(
            f"kind: Deployment\nmetadata:\n  name: {slug}\n  namespace: default\n",
            encoding="utf-8",
        )

    with patch("itbench.utils.manifests.Path.cwd", return_value=tmp_path):
        result = _parse_discovery_dir(app_id="app-a")

    assert list(result.keys()) == ["app-a"]


def test_parse_discovery_dir_nonexistent_app_returns_empty(tmp_path: Path) -> None:
    discovery = tmp_path / ".itbench" / "discovery"
    discovery.mkdir(parents=True)

    with patch("itbench.utils.manifests.Path.cwd", return_value=tmp_path):
        result = _parse_discovery_dir(app_id="missing-app")

    assert result == {}


def test_get_application_workloads_returns_list_for_known_app(tmp_path: Path) -> None:
    discovery = tmp_path / ".itbench" / "discovery"
    app_dir = discovery / "my-app"
    app_dir.mkdir(parents=True)
    (app_dir / "deploy.yaml").write_text(
        "kind: Deployment\nmetadata:\n  name: web\n  namespace: default\n",
        encoding="utf-8",
    )

    with (
        patch("itbench.utils.manifests.run_playbook"),
        patch("itbench.utils.manifests.Path.cwd", return_value=tmp_path),
    ):
        workloads = get_application_workloads("my-app")

    assert len(workloads) == 1
    assert workloads[0].name == "web"


def test_get_application_workloads_returns_empty_for_unknown_app(tmp_path: Path) -> None:
    discovery = tmp_path / ".itbench" / "discovery"
    discovery.mkdir(parents=True)

    with (
        patch("itbench.utils.manifests.run_playbook"),
        patch("itbench.utils.manifests.Path.cwd", return_value=tmp_path),
    ):
        workloads = get_application_workloads("unknown-app")

    assert workloads == []
