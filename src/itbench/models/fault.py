"""Fault Pydantic models for ITBench."""

import re

from enum import StrEnum
from pathlib import Path
from typing import Self

import yaml

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from itbench.models.kubernetes import KubernetesObjectKind
from itbench.models.platform import Platform

_FAULTS_DIR = Path(__file__).parents[3] / "library" / "faults"


class FaultAlerts(StrEnum):
    """Alerts associated with a fault."""

    HighRequestErrorRate = "HighRequestErrorRate"
    HighRequestLatency = "HighRequestLatency"
    KubeContainerWaiting = "KubeContainerWaiting"
    KubeHpaMaxedOut = "KubeHpaMaxedOut"
    KubePodCrashLooping = "KubePodCrashLooping"
    KubePodNotReady = "KubePodNotReady"
    NoRequestsReceived = "NoRequestsReceived"


class FaultTags(StrEnum):
    """Categories/tags for faults."""

    Authentication = "Authentication"
    Code = "Code"
    Deployment = "Deployment"
    Networking = "Networking"
    Performance = "Performance"


class FaultTargetReference(BaseModel):
    """A type reference declaring what kind of Kubernetes object a fault targets.

    Uses the model class name rather than a full object instance — the concrete
    object is supplied in the scenario injection's ``targets`` list.
    """

    model_config = ConfigDict(extra="forbid")

    kubernetes: KubernetesObjectKind = Field(
        description="Name of the Kubernetes object model this fault targets (e.g. KubernetesWorkload, KubernetesService).",
    )


class FaultConvertedStatus(BaseModel):
    """Conversion metadata for a fault that has been converted into a waiter."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        description="Unique slug identifier for the waiter.",
    )
    version: str = Field(
        description="ITBench version in which the fault was converted.",
    )


class FaultRetiredStatus(BaseModel):
    """Retirement metadata for a fault that has been removed from the active catalog."""

    model_config = ConfigDict(extra="forbid")

    reason: str | None = Field(
        default=None,
        description="Reason the fault was retired.",
    )
    version: str = Field(
        description="ITBench version in which the fault was retired.",
    )


class FaultStatus(BaseModel):
    """Lifecycle status for a fault."""

    model_config = ConfigDict(extra="forbid")

    converted: FaultConvertedStatus | None = Field(
        default=None,
        description="Conversion metadata, present only if the fault has been converted to a waiter.",
    )
    retired: FaultRetiredStatus | None = Field(
        default=None,
        description="Retirement metadata, present only if the fault has been retired.",
    )


class FaultSolutionStep(BaseModel):
    """Individual step in a solution procedure."""

    model_config = ConfigDict(extra="forbid")

    command: str | None = Field(
        default=None,
        description="CLI command to execute for this step.",
    )
    text: str = Field(
        description="Human-readable description of the troubleshooting step.",
    )


class FaultSolution(BaseModel):
    """A single recommended solution comprising ordered remediation steps."""

    model_config = ConfigDict(extra="forbid")

    steps: list[FaultSolutionStep] = Field(
        description="Ordered list of steps to resolve the fault.",
    )


class FaultSolutionTemplates(BaseModel):
    """Solution templates for addressing the fault."""

    model_config = ConfigDict(extra="forbid")

    templates: list[FaultSolution] = Field(
        description="One or more recommended solutions for resolving the fault.",
    )


class Fault(BaseModel):
    """A single fault catalog entry."""

    model_config = ConfigDict(extra="forbid")

    alerts: list[FaultAlerts] = Field(
        default_factory=list,
        description="Alerts triggered by this fault.",
        json_schema_extra={"uniqueItems": True},
    )
    description: str = Field(
        description="Description of what the fault does.",
    )
    expectation: str = Field(
        description="Expected behavior or symptoms observed when the fault is injected.",
    )
    name: str = Field(
        description="Name of the fault.",
    )
    platform: Platform = Field(
        description="Target platform.",
    )
    resources: list[str] = Field(
        default_factory=list,
        description="Reference documentation or links.",
        json_schema_extra={"uniqueItems": True},
    )
    solution_templates: FaultSolutionTemplates = Field(
        description="Recommended troubleshooting solutions.",
    )
    status: FaultStatus | None = Field(
        default=None,
        description="Lifecycle status of the fault, including retirement metadata if applicable.",
    )
    tags: list[FaultTags] = Field(
        default_factory=list,
        description="Tags categorizing the fault.",
        json_schema_extra={"uniqueItems": True},
    )
    targets: list[FaultTargetReference] = Field(
        default_factory=list,
        description=(
            "Kubernetes object types this fault targets, by model class name. "
            "Scenario injections must supply a matching concrete object in their own targets list."
        ),
        json_schema_extra={"uniqueItems": True},
    )

    @model_validator(mode="after")
    def _require_alerts_for_active_faults(self) -> Self:
        """Enforce that at least one alert is defined for non-retired faults."""
        if (self.status is None or self.status.retired is None) and not self.alerts:
            raise ValueError("Non-retired faults must define at least one alert in 'alerts'.")
        return self

    @model_validator(mode="after")
    def _require_tags_for_active_faults(self) -> Self:
        """Enforce that at least one tag is defined for non-retired faults."""
        if (self.status is None or self.status.retired is None) and not self.tags:
            raise ValueError("Non-retired faults must define at least one tag in 'tags'.")
        return self

    @model_validator(mode="after")
    def _require_targets_for_active_faults(self) -> Self:
        """Enforce that at least one target is defined for non-retired faults."""
        if (self.status is None or self.status.retired is None) and not self.targets:
            raise ValueError("Non-retired faults must define at least one target in 'targets'.")
        return self

    @computed_field
    @property
    def id(self) -> str:
        """Unique slug identifier derived from the fault name."""
        text = self.name.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        return text.strip("-")


def _load_fault_catalog() -> dict[str, Fault]:
    if not _FAULTS_DIR.exists():
        raise FileNotFoundError(f"Fault library directory not found: {_FAULTS_DIR}")

    catalog: dict[str, Fault] = {}

    for path in _FAULTS_DIR.glob("*.yaml"):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            fault = Fault.model_validate(data)
            catalog[fault.id] = fault
        except Exception:
            continue

    return catalog


FAULT_CATALOG: dict[str, Fault] = _load_fault_catalog()
