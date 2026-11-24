"""Fault Pydantic models for ITBench."""

import re

from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, computed_field, model_validator

from itbench.models.catalog import LazyCatalog, load_catalog_directory
from itbench.models.kubernetes import KubernetesObjectKind
from itbench.models.platform import Platform
from itbench.paths import repository


class PrometheusAlertNames(StrEnum):
    """Alerts associated with a fault."""

    HighRequestErrorRate = "HighRequestErrorRate"
    HighRequestLatency = "HighRequestLatency"
    KubeContainerWaiting = "KubeContainerWaiting"
    KubeHpaMaxedOut = "KubeHpaMaxedOut"
    KubePodCrashLooping = "KubePodCrashLooping"
    KubePodNotReady = "KubePodNotReady"
    NoRequestsReceived = "NoRequestsReceived"


class PrometheusAlertState(StrEnum):
    """Prometheus alert state a signal expects."""

    Firing = "firing"
    Pending = "pending"
    Inactive = "inactive"


class KyvernoPolicyReportStatus(StrEnum):
    """Result status of a policy report entry (``wgpolicyk8s.io`` ``results[].result``)."""

    Pass = "pass"
    Fail = "fail"
    Warn = "warn"
    Error = "error"
    Skip = "skip"


class PrometheusAlertSignal(BaseModel):
    """A Prometheus alert a fault causes."""

    model_config = ConfigDict(extra="forbid")

    name: PrometheusAlertNames = Field(
        description="Alert identifier.",
    )
    state: PrometheusAlertState = Field(
        default=PrometheusAlertState.Firing,
        description="State the alert is expected to be in while the fault is active.",
    )


class PrometheusSignals(BaseModel):
    """Signals observed through Prometheus."""

    model_config = ConfigDict(extra="forbid")

    alerts: list[PrometheusAlertSignal] = Field(
        default_factory=list,
        description="Alerts caused by the fault.",
        json_schema_extra={"uniqueItems": True},
    )


class KyvernoPolicyReportSignal(BaseModel):
    """A policy report result a fault causes.

    Names a policy and the status expected for it. It does not name the reported object.
    """

    model_config = ConfigDict(extra="forbid")

    policy: str = Field(
        description="Policy the report entry is for, as written in the report's results[].policy.",
    )
    status: KyvernoPolicyReportStatus = Field(
        description="Status expected for the policy (the report's results[].result).",
    )


class KubernetesSignals(BaseModel):
    """Signals observed through the Kubernetes API."""

    model_config = ConfigDict(extra="forbid")

    policy_reports: list[KyvernoPolicyReportSignal] = Field(
        default_factory=list,
        description="Policy report results expected for the fault.",
        json_schema_extra={"uniqueItems": True},
    )


class FaultSignals(BaseModel):
    """Signals a fault causes, grouped by where they are observed."""

    model_config = ConfigDict(extra="forbid")

    kubernetes: KubernetesSignals = Field(
        default_factory=KubernetesSignals,
        description="Signals observed through the Kubernetes API.",
    )
    prometheus: PrometheusSignals = Field(
        default_factory=PrometheusSignals,
        description="Signals observed through Prometheus.",
    )


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
    signals: FaultSignals = Field(
        default_factory=FaultSignals,
        description="Signals this fault causes, such as Prometheus alerts or policy report results.",
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

    @property
    def alert_names(self) -> list[str]:
        """Names of the Prometheus alerts this fault causes."""
        return [str(alert.name) for alert in self.signals.prometheus.alerts]

    @property
    def is_retired(self) -> bool:
        """Whether the fault has been retired."""
        return self.status is not None and self.status.retired is not None

    @property
    def is_converted(self) -> bool:
        """Whether the fault has been converted to a waiter."""
        return self.status is not None and self.status.converted is not None

    @property
    def is_inactive(self) -> bool:
        """Whether the fault is retired or converted and so no longer injected."""
        return self.is_retired or self.is_converted

    @property
    def retired_reason(self) -> str | None:
        """Reason the fault was retired, if it was retired and a reason was given."""
        if self.status is None or self.status.retired is None:
            return None
        return self.status.retired.reason

    @model_validator(mode="after")
    def _require_tags_for_active_faults(self) -> Self:
        """Enforce that at least one tag is defined for non-retired faults."""
        if not self.is_retired and not self.tags:
            raise ValueError("Non-retired faults must define at least one tag in 'tags'.")
        return self

    @model_validator(mode="after")
    def _require_targets_for_active_faults(self) -> Self:
        """Enforce that at least one target is defined for non-retired faults."""
        if not self.is_retired and not self.targets:
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
    return load_catalog_directory(repository.faults, Fault, "fault")


FAULT_CATALOG: LazyCatalog[Fault] = LazyCatalog(_load_fault_catalog)
