"""Tests for the explain waiter CLI command."""

import json

import yaml

from click.testing import CliRunner

from itbench.cli.commands.explain.waiter import explain_waiter
from itbench.models.waiter import WAITER_CATALOG


def test_explain_waiter_known_id() -> None:
    runner = CliRunner()
    waiter_id = next(iter(WAITER_CATALOG))

    result = runner.invoke(explain_waiter, [waiter_id])

    assert result.exit_code == 0
    assert WAITER_CATALOG[waiter_id].name in result.output


def test_explain_waiter_shows_sections() -> None:
    runner = CliRunner()
    waiter_id = next(iter(WAITER_CATALOG))

    result = runner.invoke(explain_waiter, [waiter_id])

    assert "DESCRIPTION" in result.output
    assert "SCENARIO YAML EXAMPLE" in result.output


def test_explain_waiter_fields_show_description_and_default() -> None:
    result = CliRunner().invoke(explain_waiter, ["pause-execution"])

    assert result.exit_code == 0
    assert "FIELDS" in result.output
    assert "seconds" in result.output
    assert "default: 30" in result.output
    assert "Number of seconds to pause execution." in result.output


def test_explain_waiter_required_field_marked_required() -> None:
    result = CliRunner().invoke(explain_waiter, ["scale-kubernetes-workload"])

    assert result.exit_code == 0
    assert "workload" in result.output
    assert "required" in result.output


def test_explain_waiter_example_uses_real_values_and_aliases() -> None:
    result = CliRunner().invoke(explain_waiter, ["scale-kubernetes-workload"], env={"COLUMNS": "200"})

    assert result.exit_code == 0
    assert "postInjection" in result.output
    assert "id: scale-kubernetes-workload" in result.output
    assert "replicas: 1" in result.output
    assert "apiVersion: apps/v1" in result.output
    assert "<fault-id>" in result.output


def test_explain_waiter_json_output() -> None:
    result = CliRunner().invoke(explain_waiter, ["pause-execution", "--format", "json"])

    assert result.exit_code == 0
    data = json.loads(result.output)
    assert data["id"] == "pause-execution"
    assert data["seconds"] == 30


def test_explain_waiter_yaml_output() -> None:
    result = CliRunner().invoke(explain_waiter, ["pause-execution", "--format", "yaml"])

    assert result.exit_code == 0
    assert yaml.safe_load(result.output)["id"] == "pause-execution"


def test_explain_waiter_unknown_id() -> None:
    runner = CliRunner()

    result = runner.invoke(explain_waiter, ["no-such-waiter"])

    assert result.exit_code == 1
    assert "not found" in result.output
    assert "itbench list waiters" in result.output


def test_explain_waiter_unknown_id_suggests_close_match() -> None:
    result = CliRunner().invoke(explain_waiter, ["pause-executon"])

    assert result.exit_code == 1
    assert "Did you mean" in result.output
    assert "pause-execution" in result.output
