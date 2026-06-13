import argparse
import json
import logging
import sys

from operator import itemgetter
from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def write_markdown_file(file_path: Path, content: str) -> None:
    logger.info(f"writing markdown file: {file_path}")
    file_path.write_text(content, encoding="utf-8")

def load_library_indexes(index_directory: Path) -> List[Dict[str, Any]]:
    return [
        json.loads(f.read_text(encoding="utf-8")) for f in index_directory.glob("*.json")
    ]

def create_library_readme(
    library_type: str,
    documentation_directory: Path,
    environment: Environment,
    indexes: List[Dict[str, Any]]
) -> None:
    template = environment.get_template(f"{library_type}/README.md.j2")

    write_markdown_file(
        documentation_directory / "README.md",
        template.render({library_type: indexes})
    )

def create_applications_documentation(
    documentation_directory: Path,
    environment: Environment,
    indexes: List[Dict[str, Any]]
) -> None:
    create_library_readme("applications", documentation_directory, environment, indexes)
    template = environment.get_template("applications/application.md.j2")

    for index in indexes:
        index_id = index["id"]

        write_markdown_file(
            documentation_directory / f"{index_id}.md",
            template.render({
                "application": index,
                "source_file_path": f"../../../../scenarios/sre/library/indexes/applications/{index_id}.json",
                "schema_file_path": f"../../../../schemas/json/applications/{index_id}.json"
            })
        )

def create_faults_documentation(
    documentation_directory: Path,
    environment: Environment,
    indexes: List[Dict[str, Any]]
) -> None:
    create_library_readme("faults", documentation_directory, environment, indexes)
    template = environment.get_template("faults/fault.md.j2")

    for index in indexes:
        index_id = index["id"]
        write_markdown_file(
            documentation_directory / f"{index_id}.md",
            template.render({
                "fault": index,
                "source_file_path": f"../../../../scenarios/sre/library/indexes/faults/{index_id}.json",
                "schema_file_path": f"../../../../schemas/json/faults/{index_id}.json",
                "implementation_file_path": f"../../../../scenarios/sre/project/roles/faults/tasks/inject_{index_id.replace('-', '_')}.yaml"
            })
        )

def create_waiters_documentation(
    documentation_directory: Path,
    environment: Environment,
    indexes: List[Dict[str, Any]]
) -> None:
    create_library_readme("waiters", documentation_directory, environment, indexes)
    template = environment.get_template("waiters/waiter.md.j2")

    for index in indexes:
        index_id = index["id"]
        write_markdown_file(
            documentation_directory / f"{index_id}.md",
            template.render({
                "waiter": index,
                "source_file_path": f"../../../../scenarios/sre/library/indexes/waiters/{index_id}.json",
                "schema_file_path": f"../../../../schemas/json/waiters/{index_id}.json"
            })
        )

def create_scenarios_statistics(
    documentation_directory: Path,
    environment: Environment,
    scenarios: List[Dict[str, Any]]
) -> None:
    statistics = {
        "application": {"book_info": 0, "otel_demo": 0},
        "category": {"finops": 0, "sre": 0},
        "complexity": {"low": 0, "medium": 0, "high": 0}
    }

    for scenario in scenarios:
        for app in scenario.get("environment", {}).get("applications", []):
            app_id = app["id"]
            if "book-info" == app_id:
                statistics["application"]["book_info"] += 1
            elif "opentelemetry-demo" == app_id:
                statistics["application"]["otel_demo"] += 1

        category = scenario["category"]
        if category in statistics["category"]:
            statistics["category"][category] += 1

        complexity = scenario["complexity"]
        if complexity in statistics["complexity"]:
            statistics["complexity"][complexity] += 1

    template = environment.get_template("scenarios/statistics.md.j2")

    write_markdown_file(
        documentation_directory / "statistics.md",
        template.render(statistics=statistics)
    )

def create_scenarios_documentation(
    index_directory: Path,
    documentation_directory: Path,
    environment: Environment,
    scenarios_indexes: List[Dict[str, Any]],
    application_indexes: List[Dict[str, Any]],
    faults_indexes: List[Dict[str, Any]]
) -> None:
    create_library_readme("scenarios", documentation_directory, environment, scenarios_indexes)
    create_scenarios_statistics(documentation_directory, environment, scenarios_indexes)

    applications_lookup = { a["id"]: a for a in application_indexes }
    faults_lookup = { f["id"]: f for f in faults_indexes }

    template = environment.get_template("scenarios/scenario.md.j2")

    for index in scenarios_indexes:
        index_id = index["id"]
        write_markdown_file(
            documentation_directory / index["category"] / f"{index_id}.md",
            template.render({
                "scenario": index,
                "source_file_path": f"../../../../scenarios/sre/library/indexes/scenarios/{index_id}.json",
                "schema_file_path": f"../../../../schemas/json/scenarios/{index_id}.json",
                "applications": applications_lookup,
                "faults": faults_lookup
            })
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate library documentation files from indexes")

    parser.add_argument("--templates_directory", type=Path, required=True)
    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--documentation_directory", type=Path, required=True)

    args = parser.parse_args()

    env = Environment(
        loader=FileSystemLoader(args.templates_directory),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True
    )

    application_indexes = load_library_indexes(args.library_index_directory / "applications")
    faults_indexes = load_library_indexes(args.library_index_directory / "faults")
    waiters_indexes = load_library_indexes(args.library_index_directory / "waiters")
    scenarios_indexes = load_library_indexes(args.library_index_directory / "scenarios")

    create_applications_documentation(
        args.documentation_directory / "applications",
        env,
        sorted(application_indexes, key=itemgetter("name"))
    )
    create_faults_documentation(
        args.documentation_directory / "faults",
        env,
        sorted(faults_indexes, key=itemgetter("name"))
    )
    create_waiters_documentation(
        args.documentation_directory / "waiters",
        env,
        sorted(waiters_indexes, key=itemgetter("name"))
    )

    create_scenarios_documentation(
        args.library_index_directory,
        args.documentation_directory / "scenarios",
        env,
        sorted(scenarios_indexes, key=itemgetter("id")),
        application_indexes,
        faults_indexes
    )

if __name__ == "__main__":
    sys.exit(main())
