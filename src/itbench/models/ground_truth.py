"""Ground truth Pydantic models for ITBench."""

from pydantic import BaseModel, ConfigDict, Field

from itbench.models.fault import FaultAlerts, FaultSolution
from itbench.models.kubernetes import KubernetesObject


class GroundTruthAlert(BaseModel):
    """A single alert entry in a ground truth definition."""

    model_config = ConfigDict(extra="forbid")

    labels: dict[str, str] = Field(
        default_factory=dict,
        description="Key/value label pairs associated with the alert.",
    )
    name: FaultAlerts = Field(
        description="Alert identifier.",
    )


class GroundTruthEntity(BaseModel):
    """A Kubernetes object entity involved in a fault."""

    model_config = ConfigDict(extra="forbid")

    kubernetes: list[KubernetesObject] = Field(
        description="One or more Kubernetes objects involved in this fault.",
        json_schema_extra={"uniqueItems": True},
    )


class GroundTruth(BaseModel):
    """Ground truth definition for a benchmark scenario."""

    model_config = ConfigDict(extra="forbid")

    alerts: list[GroundTruthAlert] = Field(
        default_factory=list,
        description="Alerts expected to fire when the fault is active.",
        json_schema_extra={"uniqueItems": True},
    )
    entities: list[GroundTruthEntity] = Field(
        description="Kubernetes objects directly involved in the fault.",
        json_schema_extra={"uniqueItems": True},
    )
    solutions: list[list[FaultSolution]] = Field(
        description=(
            "One entry per fault injection, each containing one or more alternative "
            "remediation paths (solution templates) for that injection."
        ),
    )
