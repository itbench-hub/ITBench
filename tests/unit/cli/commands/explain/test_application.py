"""Tests for the explain application CLI command."""

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


def test_explain_application_unknown_slug() -> None:
    runner = CliRunner()

    result = runner.invoke(explain_application, ["no-such-app"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "itbench list apps" in result.output
