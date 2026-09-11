import argparse
import json
import logging
import sys

from pathlib import Path
from typing import Any, Dict, List

import yaml

from yaml import SafeDumper


class _IndentedSafeDumper(SafeDumper):
    def increase_indent(self, flow=False, indentless=False):
        return super().increase_indent(flow=flow, indentless=False)


from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def load_scenarios(library_index_directory: Path) -> List[Dict[str, Any]]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in (library_index_directory / "scenarios").glob("*.json")
    ]


def write_yaml_file(file_path: Path, content: str) -> None:
    logger.info(f"writing spec file: {file_path}")
    file_path.write_text(content, encoding="utf-8")


def generate_scenario_specs(
    scenario: Dict[str, Any],
    specs_directory: Path,
    environment: Environment,
) -> None:
    scenario_id = scenario["id"]
    scenario_dir = specs_directory / str(scenario_id)
    scenario_dir.mkdir(parents=True, exist_ok=True)

    for template_name, output_name in [
        ("scenario.yaml.j2", "scenario.yaml"),
        ("groundtruth.yaml.j2", "groundtruth.yaml"),
    ]:
        rendered = yaml.safe_load(environment.get_template(template_name).render(scenario=scenario))
        write_yaml_file(
            scenario_dir / output_name,
            yaml.dump(rendered, Dumper=_IndentedSafeDumper, explicit_start=True, indent=2, width=160),
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate scenario spec files from library indexes")

    parser.add_argument("--templates_directory", type=Path, required=True)
    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--specs_directory", type=Path, required=True)

    args = parser.parse_args()

    env = Environment(
        loader=FileSystemLoader(args.templates_directory),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    scenarios = load_scenarios(args.library_index_directory)
    logger.info(f"generating spec files for {len(scenarios)} scenarios")

    for scenario in scenarios:
        generate_scenario_specs(scenario, args.specs_directory, env)


if __name__ == "__main__":
    sys.exit(main())
