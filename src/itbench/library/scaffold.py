"""Scaffold new scenario and fault index template stubs."""
import logging
from pathlib import Path

import yaml

from itbench.utils.yaml_dumper import IndentedSafeDumper

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def next_scenario_index(scenarios_templates_directory: Path) -> int:
    existing = [
        int(f.name.split(".", 1)[0])
        for f in scenarios_templates_directory.glob("*.yaml.j2")
    ]
    return max(existing) + 1 if existing else 1


def create_scenario_stub(
    description: str,
    index: int,
    scenarios_templates_directory: Path,
) -> Path:
    scenario = {
        "category": "",
        "complexity": "low",
        "description": description,
        "disruptions": [],
        "environment": {"applications": []},
        "id": index,
        "solutionTemplates": [],
    }

    schema_comment = "# yaml-language-server: $schema=../../../../../../schemas/json/library/index/scenario.json\n"
    content = schema_comment + yaml.dump(
        scenario,
        Dumper=IndentedSafeDumper,
        explicit_start=True,
        indent=2,
        default_flow_style=False,
        allow_unicode=True,
    )

    dest = scenarios_templates_directory / f"{index}.yaml.j2"
    dest.write_text(content, encoding="utf-8")
    logger.debug("wrote scenario stub: %s", dest)
    return dest


def next_fault_index(faults_templates_directory: Path) -> int:
    existing = [
        int(f.name.split(".", 1)[0])
        for f in faults_templates_directory.glob("*.yaml.j2")
    ]
    return max(existing) + 1 if existing else 1


def create_fault_stub(
    name: str,
    description: str,
    expectation: str,
    index: int,
    faults_templates_directory: Path,
) -> Path:
    fault = {
        "alerts": {},
        "arguments": {"jsonSchema": {}},
        "name": name,
        "description": description,
        "expectation": expectation,
        "platform": "",
        "resources": [],
        "solutions": {"templates": []},
        "tags": [],
    }

    schema_comment = "# yaml-language-server: $schema=../../../../../../schemas/json/library/index/fault.json\n"
    content = schema_comment + yaml.dump(
        fault,
        Dumper=IndentedSafeDumper,
        explicit_start=True,
        indent=2,
        default_flow_style=False,
        allow_unicode=True,
    )

    dest = faults_templates_directory / f"{index}.yaml.j2"
    dest.write_text(content, encoding="utf-8")
    logger.debug("wrote fault stub: %s", dest)
    return dest
