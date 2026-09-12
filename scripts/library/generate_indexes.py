import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any

import yaml

from jinja2 import Environment, FileSystemLoader

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def write_json_file(file_path: Path, content: dict[str, Any] | list[dict[str, Any]]) -> None:
    logger.debug("writing index file: %s", file_path)
    file_path.write_text(json.dumps(content, sort_keys=True, indent=4) + "\n", encoding="utf-8")

def extract_index_from_filename(filename: str) -> int:
    return int(filename.split(".", 1)[0])

def generate_id_from_name(name: str) -> str:
    return name.lower().replace(" ", "-")

def load_releases(applications: Path, tools: Path) -> dict[str, Any]:
    applications_releases = yaml.safe_load(applications.read_text(encoding="utf-8"))
    tools_releases = yaml.safe_load(tools.read_text(encoding="utf-8"))

    return {
        "applications": applications_releases["applications_releases"],
        "tools": tools_releases["tools_releases"]
    }

def load_and_write_library_index(library_type: str, templates_directory: Path, index_directory: Path) -> dict[str, Any]:
    logger.info("writing %s library indexes", library_type)

    indexes = []
    faults_lookup = {}

    for template_file in templates_directory.glob("*.yaml.j2"):
        index = yaml.safe_load(template_file.read_text(encoding="utf-8"))
        index_id = generate_id_from_name(index["name"])

        index["id"] = index_id
        index["index"] = extract_index_from_filename(template_file.name)
        index["$schema"] = f"https://raw.githubusercontent.com/itbench-hub/ITBench/refs/heads/main/schemas/library/index/{library_type.removesuffix("s")}.json"

        indexes.append(index)

        # Creating this lookup is an optimisation: the faults data is needed
        # to build scenario indexes, so caching it here avoids reopening files.
        if library_type == "faults":
            faults_lookup[index_id] = index

        write_json_file(index_directory / (Path(template_file.stem).stem + ".json"), index)

    return faults_lookup

def create_scenarios_indexes(templates_directory: Path, index_directory: Path, playbooks_directory: Path, faults: dict[str, Any]) -> None:
    logger.info("writing scenarios library indexes")

    releases = load_releases(
        playbooks_directory / "roles" / "applications" / "vars" / "main" / "releases.yaml",
        playbooks_directory / "roles" / "tools" / "vars" / "main" / "releases.yaml"
    )

    indexes = []
    faults_solution_templates = {}

    env = Environment(loader=FileSystemLoader(templates_directory))

    for template_file in templates_directory.glob("*.yaml.j2"):
        template = env.get_template(template_file.name)
        index = yaml.safe_load(template.render(releases=releases))

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

        write_json_file(index_directory / (Path(template_file.stem).stem + ".json"), index)

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate scenarios schema from library indexes")

    parser.add_argument("--templates_directory", type=Path, required=True)
    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--playbooks_directory", type=Path, required=True)

    args = parser.parse_args()

    _ = load_and_write_library_index(
        "applications",
        args.templates_directory / "applications",
        args.library_index_directory / "applications",
    )

    faults_cache = load_and_write_library_index(
        "faults",
        args.templates_directory / "faults",
        args.library_index_directory / "faults",
    )

    _ = load_and_write_library_index(
        "waiters",
        args.templates_directory / "waiters",
        args.library_index_directory / "waiters",
    )

    create_scenarios_indexes(
        args.templates_directory / "scenarios",
        args.library_index_directory / "scenarios",
        args.playbooks_directory,
        faults_cache
    )

if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.logging import configure_logging
    configure_logging()
    sys.exit(main())
