"""Kubernetes object reference models for ITBench."""

from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class KubernetesObjectKind(StrEnum):
    """Supported Kubernetes object model class names for target references."""

    KubernetesGateway = "KubernetesGateway"
    KubernetesHorizontalPodAutoscaler = "KubernetesHorizontalPodAutoscaler"
    KubernetesNamespace = "KubernetesNamespace"
    KubernetesSecret = "KubernetesSecret" # pragma: allowlist secret
    KubernetesService = "KubernetesService"
    KubernetesWorkload = "KubernetesWorkload"


class KubernetesObject(BaseModel):
    """Base model for a Kubernetes object reference."""

    model_config = ConfigDict(extra="forbid")

    api_version: str = Field(
        default="v1",
        alias="apiVersion",
        description="API version of the Kubernetes resource (e.g. v1, apps/v1).",
    )
    kind: str = Field(
        description="Kind of the Kubernetes resource (e.g. Deployment, Service, Node).",
    )
    name: str = Field(
        description="Name of the Kubernetes resource.",
    )
    namespace: str | None = Field(
        default=None,
        description="Namespace of the resource (if namespaced).",
    )


class KubernetesHorizontalPodAutoscaler(KubernetesObject):
    """Reference to a Kubernetes Horizontal Pod Autoscaler."""

    api_version: Literal["autoscaling/v2"] = Field(
        default="autoscaling/v2",
        alias="apiVersion",
        description="API version of the Kubernetes Horizontal Pod Autoscaler resource. Always autoscaling/v2.",
        frozen=True,
    )
    kind: Literal["HorizontalPodAutoscaler"] = Field(
        default="HorizontalPodAutoscaler",
        description="Kind of the Kubernetes resource. Always HorizontalPodAutoscaler.",
        frozen=True,
    )
    namespace: str = Field(
        description="Namespace of the Kubernetes Horizontal Pod Autoscaler.",
    )


class KubernetesGateway(KubernetesObject):
    """Reference to a Kubernetes Gateway (gateway.networking.k8s.io)."""

    api_version: Literal["gateway.networking.k8s.io/v1"] = Field(
        default="gateway.networking.k8s.io/v1",
        alias="apiVersion",
        description="API version of the Kubernetes Gateway resource. Always gateway.networking.k8s.io/v1.",
        frozen=True,
    )
    kind: Literal["Gateway"] = Field(
        default="Gateway",
        description="Kind of the Kubernetes resource. Always Gateway.",
        frozen=True,
    )
    namespace: str = Field(
        description="Namespace of the Gateway.",
    )


class KubernetesNamespace(KubernetesObject):
    """Reference to a Kubernetes Namespace."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="API version of the Kubernetes Namespace resource. Always v1.",
        frozen=True,
    )
    kind: Literal["Namespace"] = Field(
        default="Namespace",
        description="Kind of the Kubernetes resource. Always Namespace.",
        frozen=True,
    )
    namespace: None = Field(
        default=None,
        description="Namespaces are cluster-scoped; this field is always None.",
        frozen=True,
    )


class KubernetesSecret(KubernetesObject):
    """Reference to a Kubernetes Secret."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="API version of the Kubernetes Secret resource. Always v1.",
        frozen=True,
    )
    kind: Literal["Secret"] = Field(
        default="Secret",
        description="Kind of the Kubernetes resource. Always Secret.",
        frozen=True,
    )
    namespace: str = Field(
        description="Namespace of the Secret.",
    )


class KubernetesService(KubernetesObject):
    """Reference to a Kubernetes Service."""

    api_version: Literal["v1"] = Field(
        default="v1",
        alias="apiVersion",
        description="API version of the Kubernetes Service resource. Always v1.",
        frozen=True,
    )
    kind: Literal["Service"] = Field(
        default="Service",
        description="Kind of the Kubernetes resource. Always Service.",
        frozen=True,
    )
    namespace: str = Field(
        description="Namespace of the Service.",
    )


class KubernetesWorkload(KubernetesObject):
    """Reference to a Kubernetes workload (DaemonSet, Deployment, or StatefulSet)."""

    api_version: Literal["apps/v1"] = Field(
        default="apps/v1",
        alias="apiVersion",
        description="API version of the Kubernetes workload resource. Always apps/v1.",
        frozen=True,
    )
    kind: Literal["DaemonSet", "Deployment", "StatefulSet"] = Field(
        default="Deployment",
        description="Kind of the Kubernetes workload. One of DaemonSet, Deployment, or StatefulSet.",
    )
    namespace: str = Field(
        description="Namespace of the workload.",
    )


KubernetesObjects = Annotated[
    KubernetesGateway
    | KubernetesHorizontalPodAutoscaler
    | KubernetesNamespace
    | KubernetesSecret
    | KubernetesService
    | KubernetesWorkload,
    Field(discriminator="kind"),
]
