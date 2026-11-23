"""Ground truth Pydantic models for ITBench."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue

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


class GroundTruthField(BaseModel):
    """A single field of an object that must keep an expected value."""

    model_config = ConfigDict(extra="forbid")

    path: str = Field(
        description="JSON key path of the field, e.g. spec.template.spec.containers[0].name.",
    )
    value: JsonValue = Field(
        description="Value the field is expected to hold, e.g. server.",
    )


class GroundTruthUnchangedKubernetesObject(KubernetesObject):
    """A Kubernetes object that the fault does not touch and the agent must not change."""

    fields: list[GroundTruthField] = Field(
        default_factory=list,
        description="Fields that must keep the given value. When empty, the whole object must be unchanged.",
    )


class GroundTruthEntityGroup(BaseModel):
    """Entities of one relationship to the fault, grouped by entity type."""

    model_config = ConfigDict(extra="forbid")

    kubernetes: list[KubernetesObject] = Field(
        default_factory=list,
        description="Kubernetes objects in this group.",
        json_schema_extra={"uniqueItems": True},
    )


class GroundTruthUnchangedEntityGroup(BaseModel):
    """Entities that must stay as they are, grouped by entity type."""

    model_config = ConfigDict(extra="forbid")

    kubernetes: list[GroundTruthUnchangedKubernetesObject] = Field(
        default_factory=list,
        description="Kubernetes objects the fault does not touch and the agent must not change.",
        json_schema_extra={"uniqueItems": True},
    )


class GroundTruthEntities(BaseModel):
    """Entities of a scenario, grouped by their relationship to the fault."""

    model_config = ConfigDict(extra="forbid")

    faulted: GroundTruthEntityGroup = Field(
        description="Entities the fault acts on directly, including objects it creates.",
    )
    impacted: GroundTruthEntityGroup = Field(
        default_factory=GroundTruthEntityGroup,
        description=("Entities affected by cascade from the faulted ones."),
    )
    unchanged: GroundTruthUnchangedEntityGroup = Field(
        default_factory=GroundTruthUnchangedEntityGroup,
        description="Entities that must stay unchanged.",
    )


class GroundTruth(BaseModel):
    """Ground truth definition for a benchmark scenario."""

    model_config = ConfigDict(extra="forbid")

    alerts: list[GroundTruthAlert] = Field(
        default_factory=list,
        description="Alerts expected to fire when the fault is active.",
        json_schema_extra={"uniqueItems": True},
    )
    entities: GroundTruthEntities = Field(
        description="Entities involved in the fault, grouped by their relationship to it.",
    )
    solutions: list[list[FaultSolution]] = Field(
        description=(
            "One entry per fault injection, each containing one or more alternative "
            "remediation paths (solution templates) for that injection."
        ),
    )
