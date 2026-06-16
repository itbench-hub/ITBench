import argparse
import json
import logging
import sys

from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def write_json_file(file_path: Path, content: Union[Dict[str, Any], List[Dict[str, Any]]]) -> None:
    logger.info(f"writing index file: {file_path}")
    file_path.write_text(json.dumps(content, sort_keys=True, indent=4) + "\n", encoding="utf-8")

def extract_index_from_filename(filename: str) -> int:
    return int(filename.split(".", 1)[0])

def generate_id_from_name(name: str) -> str:
    return name.lower().replace(" ", "-")

def load_managers(applications: Path, tools: Path) -> Dict[str, Any]:
    applications_managers = yaml.safe_load(applications.read_text(encoding="utf-8"))
    tools_managers = yaml.safe_load(tools.read_text(encoding="utf-8"))

    return {
        "applications": applications_managers["applications_managers"],
        "tools": tools_managers["tools_managers"]
    }

def load_and_write_library_index(library_type: str, templates_directory: Path, index_directory: Path, generator_directory: Path) -> Dict[str, Any]:
    logger.info(f"writing {library_type} library indexes")

    indexes = []
    faults_lookup = {}

    for template_file in templates_directory.glob("*.json.j2"):
        index = json.loads(template_file.read_text(encoding="utf-8"))
        index_id = generate_id_from_name(index["name"])

        index["id"] = index_id
        index["index"] = extract_index_from_filename(template_file.name)
        index["$schema"] = f"https://raw.githubusercontent.com/itbench-hub/ITBench/refs/heads/main/schemas/library/index/{library_type.removesuffix("s")}.json"

        indexes.append(index)

        """
        Creating this dictionary is mostly for optimization purposes.
        This dictionary will be needed to make the scenarios indexes, so
        initializing it here will save needing to reopen the files later.
        """
        if library_type == "faults":
            faults_lookup[index_id] = index

        write_json_file(index_directory / template_file.stem, index)

    logger.info("writing combined index file")

    write_json_file(
        generator_directory / f"{library_type}.json",
        sorted(indexes, key=itemgetter("name"))
    )

    return faults_lookup

def create_scenarios_indexes(templates_directory: Path, index_directory: Path, playbooks_directory: Path, generator_directory: Path, faults: Dict[str, Any]) -> None:
    logger.info("writing scenarios library indexes")

    managers = load_managers(
        playbooks_directory / "roles" / "applications" / "defaults" / "main" / "managers.yaml",
        playbooks_directory / "roles" / "tools" / "defaults" / "main" / "managers.yaml"
    )

    indexes = []
    faults_solution_templates = {}

    env = Environment(loader=FileSystemLoader(templates_directory))

    for template_file in templates_directory.glob("*.json.j2"):
        template = env.get_template(template_file.name)
        index = json.loads(template.render(managers=managers))

        alerts = set()
        tags = set(index.get("tags", []))
        platforms = set(index.get("platforms", []))
        solutions = []

        solution_templates = index.pop("solutionTemplates", [])

        for solution_template in solution_templates:
            disruption = index["disruptions"][solution_template["disruptionIndex"]]
            injection = disruption["injections"][solution_template["injectionIndex"]]

            fault = faults[injection["id"]]

            fault_alerts = fault.get("alerts", {})
            alerts.update(fault_alerts.get("application", []))
            alerts.update(fault_alerts.get("goldenSignal", []))

            tags.update(fault["tags"])

            platforms.add(fault["platform"])

            if injection["id"] not in faults_solution_templates:
                faults_solution_templates[injection["id"]] = env.from_string(json.dumps(fault["solutions"]["templates"]))

            solutions.append(json.loads(faults_solution_templates[injection["id"]].render(args=injection["args"])))

        # Finalize index map properties natively using fast sorting arrays
        index["index"] = extract_index_from_filename(template_file.name)
        index["alerts"] = sorted(alerts)
        index["platforms"] = sorted(platforms)
        index["solutions"] = solutions
        index["tags"] = sorted(tags)
        index["$schema"] = "https://raw.githubusercontent.com/itbench-hub/ITBench/refs/heads/main/schemas/library/index/scenario.json"

        indexes.append(index)

        write_json_file(index_directory / template_file.stem, index)

    logger.info("writing combined index file")
    write_json_file(generator_directory / "scenarios.json", sorted(indexes, key=itemgetter("index")))

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate scenarios schema from library indexes")

    parser.add_argument("--templates_directory", type=Path, required=True)
    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--playbooks_directory", type=Path, required=True)

    args = parser.parse_args()

    generator_directory = args.playbooks_directory.parent / "project" / "roles" / "generator" / "files" / "library" / "index"

    _ = load_and_write_library_index(
        "applications",
        args.templates_directory / "applications",
        args.library_index_directory / "applications",
        generator_directory
    )

    faults_cache = load_and_write_library_index(
        "faults",
        args.templates_directory / "faults",
        args.library_index_directory / "faults",
        generator_directory
    )

    # Process waiters
    _ = load_and_write_library_index(
        "waiters",
        args.templates_directory / "waiters",
        args.library_index_directory / "waiters",
        generator_directory
    )

    create_scenarios_indexes(
        args.templates_directory / "scenarios",
        args.library_index_directory / "scenarios",
        args.playbooks_directory,
        generator_directory,
        faults_cache
    )

if __name__ == "__main__":
    sys.exit(main())
