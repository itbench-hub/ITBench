"""Tests for Platform enum."""

from itbench.models.platform import Platform


def test_platform_values() -> None:
    assert Platform.Kubernetes == "Kubernetes"
    assert Platform.Localhost == "Localhost"
    assert Platform.OpenShift == "OpenShift"
