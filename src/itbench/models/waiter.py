"""Waiter Pydantic models and built-in catalog for ITBench engine primitives."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field

from itbench.models.kubernetes import KubernetesWorkload
from itbench.models.platform import Platform


class Waiter(BaseModel):
    """Shared base for all waiter catalog entries."""

    model_config = ConfigDict(extra="forbid")

    description: str | None = Field(
        default=None,
        description="Description of what the waiter does.",
    )
    id: str = Field(
        description="Unique slug identifier for the waiter.",
    )
    name: str | None = Field(
        default=None,
        description="Human-readable name of the waiter.",
    )
    platforms: list[Platform] = Field(
        default_factory=list,
        description="Target platforms this waiter applies to.",
        json_schema_extra={"uniqueItems": True},
    )


class WaiterDeleteWorkloadPods(Waiter):
    """Waiter that deletes all pods associated with a Kubernetes workload."""

    id: Literal["delete-workload-pods"] = Field(
        default="delete-workload-pods",
        description="Unique slug identifier for the waiter.",
        frozen=True,
    )
    platforms: list[Platform] = Field(
        default=[Platform.Kubernetes, Platform.OpenShift],
        description="Target platforms this waiter applies to.",
        frozen=True,
        json_schema_extra={"uniqueItems": True},
    )
    workload: KubernetesWorkload = Field(
        description="Target workload whose pods will be deleted.",
    )


class WaiterPauseExecution(Waiter):
    """Waiter that pauses execution for a fixed number of seconds."""

    id: Literal["pause-execution"] = Field(
        default="pause-execution",
        description="Unique slug identifier for the waiter.",
        frozen=True,
    )
    platforms: list[Platform] = Field(
        default=[Platform.Localhost],
        description="Target platforms this waiter applies to.",
        frozen=True,
        json_schema_extra={"uniqueItems": True},
    )
    seconds: int = Field(
        default=30,
        description="Number of seconds to pause execution.",
        gt=0,
    )


class WaiterRestartKubernetesWorkload(Waiter):
    """Waiter that restarts a Kubernetes workload and waits for it to become ready."""

    id: Literal["restart-kubernetes-workload"] = Field(
        default="restart-kubernetes-workload",
        description="Unique slug identifier for the waiter.",
        frozen=True,
    )
    platforms: list[Platform] = Field(
        default=[Platform.Kubernetes, Platform.OpenShift],
        description="Target platforms this waiter applies to.",
        frozen=True,
        json_schema_extra={"uniqueItems": True},
    )
    workload: KubernetesWorkload = Field(
        description="Target workload to restart.",
    )


class WaiterScaleKubernetesWorkload(Waiter):
    """Waiter that scales a Kubernetes workload to a desired replica count."""

    id: Literal["scale-kubernetes-workload"] = Field(
        default="scale-kubernetes-workload",
        description="Unique slug identifier for the waiter.",
        frozen=True,
    )
    platforms: list[Platform] = Field(
        default=[Platform.Kubernetes, Platform.OpenShift],
        description="Target platforms this waiter applies to.",
        frozen=True,
        json_schema_extra={"uniqueItems": True},
    )
    replicas: int = Field(
        default=1,
        description="Desired number of replicas to scale the workload to.",
        gt=0,
    )
    workload: KubernetesWorkload = Field(
        description="Target workload to scale.",
    )


class WaiterUnassignWorkloadContainerResourceLimits(Waiter):
    """Waiter that removes the resource limits of a container in a Kubernetes workload."""

    id: Literal["unassign-workload-container-resource-limits"] = Field(
        default="unassign-workload-container-resource-limits",
        description="Unique slug identifier for the waiter.",
        frozen=True,
    )
    platforms: list[Platform] = Field(
        default=[Platform.Kubernetes, Platform.OpenShift],
        description="Target platforms this waiter applies to.",
        frozen=True,
        json_schema_extra={"uniqueItems": True},
    )
    container: str = Field(
        description="Name of the container whose resource limits will be removed.",
    )
    workload: KubernetesWorkload = Field(
        description="Target workload containing the container.",
    )


Waiters = Annotated[
    WaiterDeleteWorkloadPods
    | WaiterPauseExecution
    | WaiterRestartKubernetesWorkload
    | WaiterScaleKubernetesWorkload
    | WaiterUnassignWorkloadContainerResourceLimits,
    Field(discriminator="id"),
]

WAITER_CATALOG: dict[str, Waiter] = {
    "delete-workload-pods": WaiterDeleteWorkloadPods(
        description="Deletes all the pods associated with a Kubernetes workload.",
        name="Delete Workload Pods",
        workload=KubernetesWorkload(
            kind="Deployment",
            name="<workload-name>",
            namespace="<namespace>",
        ),
    ),
    "pause-execution": WaiterPauseExecution(
        description="Pauses for the requested number of seconds.",
        name="Pause Execution",
    ),
    "restart-kubernetes-workload": WaiterRestartKubernetesWorkload(
        description="Waits for a Kubernetes workload to be restarted.",
        name="Restart Kubernetes Workload",
        workload=KubernetesWorkload(
            kind="Deployment",
            name="<workload-name>",
            namespace="<namespace>",
        ),
    ),
    "scale-kubernetes-workload": WaiterScaleKubernetesWorkload(
        description="Waits for a Kubernetes workload to scale to the requested number of replicas.",
        name="Scale Kubernetes Workload",
        workload=KubernetesWorkload(
            kind="Deployment",
            name="<workload-name>",
            namespace="<namespace>",
        ),
    ),
    "unassign-workload-container-resource-limits": WaiterUnassignWorkloadContainerResourceLimits(
        description="Removes the resource limits of a container in a Kubernetes workload.",
        name="Unassign Workload Container Resource Limits",
        container="<container-name>",
        workload=KubernetesWorkload(
            kind="Deployment",
            name="<workload-name>",
            namespace="<namespace>",
        ),
    ),
}
