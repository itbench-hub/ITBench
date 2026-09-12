import argparse
import json
import logging
import sys

from pathlib import Path

# Ensure `scripts/` is on sys.path for utils imports
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import yaml

from jinja2 import Environment, FileSystemLoader

from utils.yaml import IndentedSafeDumper

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def load_scenarios(library_index_directory: Path) -> list[dict]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in (library_index_directory / "scenarios").glob("*.json")
    ]


def write_yaml_file(file_path: Path, content: str) -> None:
    logger.debug("writing spec file: %s", file_path)
    file_path.write_text(content, encoding="utf-8")


def generate_scenario_specs(
    scenario: dict,
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
            yaml.dump(rendered, Dumper=IndentedSafeDumper, explicit_start=True, indent=2, width=160),
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
    logger.info("generating spec files for %d scenario(s)", len(scenarios))

    for scenario in scenarios:
        generate_scenario_specs(scenario, args.specs_directory, env)


if __name__ == "__main__":
    from utils.logging import configure_logging
    configure_logging()
    sys.exit(main())
