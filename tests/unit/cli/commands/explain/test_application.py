"""Tests for the explain application CLI command."""

import json

import yaml

from click.testing import CliRunner

from itbench.cli.commands.explain.application import explain_application
from itbench.models.application import APPLICATION_CATALOG


def test_explain_application_known_slug() -> None:
    runner = CliRunner()
    slug = next(iter(APPLICATION_CATALOG))

    result = runner.invoke(explain_application, [slug])

    assert result.exit_code == 0
    assert APPLICATION_CATALOG[slug].name in result.output


def test_explain_application_shows_sections() -> None:
    runner = CliRunner()
    slug = next(iter(APPLICATION_CATALOG))

    result = runner.invoke(explain_application, [slug])

    assert "DESCRIPTION" in result.output
    assert "REPOSITORY" in result.output
    assert "SCENARIO YAML EXAMPLE" in result.output


def test_explain_application_example_references_slug() -> None:
    slug = next(iter(APPLICATION_CATALOG))

    result = CliRunner().invoke(explain_application, [slug], env={"COLUMNS": "200"})

    assert "environment:" in result.output
    assert f"id: {slug}" in result.output


def test_explain_application_shows_aliases_when_present() -> None:
    slug, entry = next((s, e) for s, e in APPLICATION_CATALOG.items() if e.aliases)

    result = CliRunner().invoke(explain_application, [slug], env={"COLUMNS": "200"})

    assert "ALIASES" in result.output
    assert entry.aliases[0] in result.output


def test_explain_application_json_output() -> None:
    slug = next(iter(APPLICATION_CATALOG))

    result = CliRunner().invoke(explain_application, [slug, "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == slug
    assert data["name"] == APPLICATION_CATALOG[slug].name


def test_explain_application_yaml_output() -> None:
    slug = next(iter(APPLICATION_CATALOG))

    result = CliRunner().invoke(explain_application, [slug, "--format", "yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output)["id"] == slug


def test_explain_application_unknown_slug() -> None:
    runner = CliRunner()

    result = runner.invoke(explain_application, ["no-such-app"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "itbench list applications" in result.output


def test_explain_application_unknown_slug_suggests_close_match() -> None:
    slug = next(iter(APPLICATION_CATALOG))

    result = CliRunner().invoke(explain_application, [slug[:-1]])

    assert result.exit_code == 1
    assert "Did you mean" in result.output
    assert slug in result.output
