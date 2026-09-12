"""Scaffold a new scenario index stub from user prompts.

Makefile invocation:
  scripts/library/scaffold_scenario.py
    --templates_directory=<path>
"""
import argparse
import logging
import sys

from pathlib import Path

# Ensure `scripts/` is on sys.path for utils imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from utils.yaml import IndentedSafeDumper

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def next_index(scenarios_templates_directory: Path) -> int:
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Scaffold a new scenario index stub")
    parser.add_argument("--templates_directory", type=Path, required=True)
    args = parser.parse_args()

    scenarios_dir = args.templates_directory / "scenarios"

    description = input("Please enter a description for the new scenario: ").strip()

    index = next_index(scenarios_dir)
    dest = create_scenario_stub(description, index, scenarios_dir)

    logger.info("The new scenario has been generated.")
    logger.info("Please edit the file to complete the scenario:")
    logger.info("  %s", dest.resolve())
    logger.info("")
    logger.info("Once done, run `make generate-library` and `make validate-library`.")
    logger.info("Once verified, run `make generate-resource-files` to create implementation file(s).")


if __name__ == "__main__":
    from utils.logging import configure_logging
    configure_logging()
    sys.exit(main())
