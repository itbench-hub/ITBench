"""Platform definitions for ITBench."""

from enum import StrEnum


class Platform(StrEnum):
    """Supported platforms for ITBench applications, faults, and waiters."""

    Kubernetes = "Kubernetes"
    Localhost = "Localhost"
    OpenShift = "OpenShift"
