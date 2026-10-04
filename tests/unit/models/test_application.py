"""Tests for Application model and catalog."""

import pytest

from pydantic import ValidationError

from itbench.models.application import APPLICATION_CATALOG, Application
from itbench.models.platform import Platform


def test_application_id_computation() -> None:
    app = Application(
        name="OpenTelemetry Demo Application",
        description="Demo microservices app",
        authors=["OpenTelemetry Authors"],
        platforms=[Platform.Kubernetes],
        repository="https://github.com/open-telemetry/opentelemetry-demo",
    )
    assert app.id == "opentelemetry-demo-application"
    assert app.aliases == []
    assert app.resources is None


def test_application_aliases_default_factory() -> None:
    app1 = Application(
        name="App One",
        description="App 1",
        authors=["Author 1"],
        platforms=[Platform.Kubernetes],
        repository="https://example.com/1",
    )
    app2 = Application(
        name="App Two",
        description="App 2",
        authors=["Author 2"],
        platforms=[Platform.Kubernetes],
        repository="https://example.com/2",
    )
    app1.aliases.append("alias1")
    assert app2.aliases == []


def test_application_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        Application(
            name="App One",
            description="App 1",
            authors=["Author 1"],
            platforms=[Platform.Kubernetes],
            repository="https://example.com/1",
            extra_field="disallowed",
        )


def test_application_catalog_loaded() -> None:
    assert isinstance(APPLICATION_CATALOG, dict)
    for app_id, app in APPLICATION_CATALOG.items():
        assert app.id == app_id
        assert isinstance(app, Application)
        assert len(app.authors) > 0
        assert len(app.platforms) > 0
        assert app.repository.startswith("http")
