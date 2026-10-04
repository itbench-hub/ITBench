"""Application Pydantic models and catalog for ITBench."""

import re

from pathlib import Path

import yaml

from pydantic import BaseModel, ConfigDict, Field, computed_field

from itbench.models.platform import Platform

_APPLICATIONS_DIR = Path(__file__).parents[3] / "library" / "applications"


class Application(BaseModel):
    """A single entry in the application catalog."""

    model_config = ConfigDict(extra="forbid")

    aliases: list[str] = Field(
        default_factory=list,
        description="Alternate names for the application.",
        json_schema_extra={"uniqueItems": True},
    )
    authors: list[str] = Field(
        description="Authors of the application.",
        json_schema_extra={"uniqueItems": True},
    )
    description: str = Field(
        description="Description of the application.",
    )
    name: str = Field(
        description="Name of the application.",
    )
    platforms: list[Platform] = Field(
        description="Supported platforms for the application.",
        json_schema_extra={"uniqueItems": True},
    )
    repository: str = Field(
        description="Repository URL of the application.",
    )
    resources: list[str] | None = Field(
        default=None,
        description="Related documentation or resource URLs.",
        json_schema_extra={"uniqueItems": True},
    )

    @computed_field
    @property
    def id(self) -> str:
        """Unique slug identifier derived from the application name."""
        text = self.name.lower().strip()
        text = re.sub(r"[^\w\s-]", "", text)
        text = re.sub(r"[\s_]+", "-", text)
        return text.strip("-")


def _load_application_catalog() -> dict[str, Application]:
    if not _APPLICATIONS_DIR.exists():
        raise FileNotFoundError(f"Application library directory not found: {_APPLICATIONS_DIR}")

    catalog: dict[str, Application] = {}

    for path in sorted(_APPLICATIONS_DIR.glob("*.yaml")):
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8"))
            application = Application.model_validate(data)
            catalog[application.id] = application
        except Exception:
            continue

    return catalog


APPLICATION_CATALOG: dict[str, Application] = _load_application_catalog()
