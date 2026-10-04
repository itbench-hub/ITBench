"""Scenario Pydantic models for ITBench."""

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator

from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.kubernetes import KubernetesObjects
from itbench.models.waiter import Waiters


class ScenarioDomain(StrEnum):
    """Supported domains for scenario configurations."""

    ComplianceSecurityOperations = "ciso"
    FinancialOperations = "finops"
    SiteReliabilityEngineering = "sre"


class FaultTarget(BaseModel):
    """A concrete Kubernetes object target for a scenario fault injection."""

    model_config = ConfigDict(extra="forbid")

    kubernetes: KubernetesObjects = Field(
        description="The Kubernetes object to target for this injection.",
    )


class ScenarioInjectionWaiter(BaseModel):
    """Pre- and post-injection waiter steps for a fault block."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    post_injection: list[Waiters] = Field(
        default_factory=list,
        alias="postInjection",
        description="Waiters to run after fault injection.",
    )
    pre_injection: list[Waiters] = Field(
        default_factory=list,
        alias="preInjection",
        description="Waiters to run before fault injection.",
    )


class ScenarioFaultInjection(BaseModel):
    """A single fault injection within a fault block."""

    model_config = ConfigDict(extra="forbid")

    id: str = Field(
        description="Fault slug identifier.",
    )
    targets: list[FaultTarget] = Field(
        default_factory=list,
        description=(
            "Runtime targets for this injection. "
            "Overrides the template targets defined in the fault catalog entry. "
            "Leave empty only for targetless faults."
        ),
        json_schema_extra={"uniqueItems": True},
    )

    @field_validator("id")
    @classmethod
    def validate_fault_id(cls, v: str) -> str:
        if v not in FAULT_CATALOG:
            valid_ids = ", ".join(sorted(FAULT_CATALOG.keys()))
            raise ValueError(f"Unknown fault '{v}'. Must be one of: {valid_ids}")
        return v


class ScenarioFault(BaseModel):
    """A group of fault injections with optional waiters."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    injections: list[ScenarioFaultInjection] = Field(
        description="One or more fault injections to apply together.",
    )
    wait_for: ScenarioInjectionWaiter | None = Field(
        default=None,
        alias="waitFor",
        description="Waiter steps to run before or after this fault block.",
    )


class ScenarioApplication(BaseModel):
    """An application enablement entry in a scenario."""

    model_config = ConfigDict(extra="forbid")

    enabled: bool = Field(
        default=True,
        description="Whether this application is enabled for the scenario.",
    )
    id: str = Field(
        description="Application slug identifier.",
    )

    @field_validator("id")
    @classmethod
    def validate_application_id(cls, v: str) -> str:
        if v not in APPLICATION_CATALOG:
            valid_ids = ", ".join(sorted(APPLICATION_CATALOG.keys()))
            raise ValueError(f"Unknown application '{v}'. Must be one of: {valid_ids}")
        return v


class ScenarioEnvironment(BaseModel):
    """Environment definition for a scenario."""

    model_config = ConfigDict(extra="forbid")

    applications: list[ScenarioApplication] = Field(
        default_factory=list,
        description="List of applications configured for the scenario.",
        json_schema_extra={"uniqueItems": True},
    )
    domains: list[ScenarioDomain] = Field(
        default_factory=list,
        description="List of domains enabled for the scenario.",
        json_schema_extra={"uniqueItems": True},
    )


class Scenario(BaseModel):
    """A complete benchmark scenario definition."""

    model_config = ConfigDict(extra="forbid")

    environment: ScenarioEnvironment = Field(
        description="Environment configuration for the scenario.",
    )
    faults: list[ScenarioFault] = Field(
        description="Ordered list of fault blocks to inject.",
    )
