"""Tests for Scenario model and nested validation."""

import pytest

from pydantic import ValidationError

from itbench.models.application import APPLICATION_CATALOG
from itbench.models.fault import FAULT_CATALOG
from itbench.models.kubernetes import KubernetesWorkload
from itbench.models.scenario import (
    FaultTarget,
    Scenario,
    ScenarioApplication,
    ScenarioDomain,
    ScenarioEnvironment,
    ScenarioFault,
    ScenarioFaultInjection,
    ScenarioInjectionWaiter,
)
from itbench.models.waiter import WaiterPauseExecution


def test_scenario_valid() -> None:
    first_app_id = next(iter(APPLICATION_CATALOG.keys()))
    first_fault_id = next(iter(FAULT_CATALOG.keys()))

    scenario = Scenario(
        environment=ScenarioEnvironment(
            applications=[
                ScenarioApplication(id=first_app_id, enabled=True),
            ],
            domains=[ScenarioDomain.SiteReliabilityEngineering],
        ),
        faults=[
            ScenarioFault(
                injections=[
                    ScenarioFaultInjection(
                        id=first_fault_id,
                        targets=[
                            FaultTarget(
                                kubernetes=KubernetesWorkload(
                                    kind="Deployment",
                                    name="target-app",
                                    namespace="default",
                                )
                            )
                        ],
                    )
                ],
                wait_for=ScenarioInjectionWaiter(
                    pre_injection=[
                        WaiterPauseExecution(
                            description="Pre-pause",
                            name="Pause",
                            seconds=10,
                        )
                    ]
                ),
            )
        ],
    )
    assert len(scenario.environment.applications) == 1
    assert scenario.environment.applications[0].id == first_app_id
    assert len(scenario.faults) == 1
    assert scenario.faults[0].injections[0].id == first_fault_id


def test_scenario_invalid_application_id() -> None:
    with pytest.raises(ValidationError, match="Unknown application 'non-existent-app'"):
        ScenarioApplication(id="non-existent-app")


def test_scenario_invalid_fault_id() -> None:
    with pytest.raises(ValidationError, match="Unknown fault 'non-existent-fault'"):
        ScenarioFaultInjection(id="non-existent-fault")


def test_scenario_domain_enum_values() -> None:
    assert ScenarioDomain.ComplianceSecurityOperations == "ciso"
    assert ScenarioDomain.FinancialOperations == "finops"
    assert ScenarioDomain.SiteReliabilityEngineering == "sre"


def test_scenario_invalid_domain_value() -> None:
    with pytest.raises(ValueError):
        ScenarioDomain("invalid_domain")
