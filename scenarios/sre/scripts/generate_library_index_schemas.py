import argparse
import json
import logging
import sys

from pathlib import Path
from typing import Any, Dict, List

from jinja2 import Environment, FileSystemLoader
from jsonschema import Draft202012Validator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def write_json_schema_file(file_path: Path, schema: Dict[str, Any]) -> None:
    logger.info(f"writing JSON schema: {file_path}")
    file_path.write_text(json.dumps(schema, sort_keys=True, indent=4) + "\n", encoding="utf-8")

def process_library_type(library_type: str, index_dir: Path, schema_dir: Path) -> tuple[List[str], List[Dict[str, Any]]]:
    ids: List[str] = []
    items: List[Dict[str, Any]] = []

    for index_file in index_dir.glob("*.json"):
        index = json.loads(index_file.read_text(encoding="utf-8"))
        index_id = index["id"]

        schema = index["arguments"]["jsonSchema"]
        schema["$schema"] = Draft202012Validator.META_SCHEMA["$id"]

        write_json_schema_file(schema_dir / f"{index_id}.json", schema)

        ids.append(index_id)
        items.append({
            "if": {
                "properties": {
                    "id": {
                        "const": index_id
                    }
                }
            },
            "then": {
                "properties": {
                    "args": {
                        "$ref": f"../../{library_type}/{index_id}.json"
                    }
                }
            }
        })

    return ids, items

def collect_alert_ids(index_dir: Path) -> List[str]:
    alerts: set[str] = set()
    for index_file in (index_dir / "faults").glob("*.json"):
        index = json.loads(index_file.read_text(encoding="utf-8"))
        fault_alerts = index.get("alerts", {})
        alerts.update(fault_alerts.get("application", []))
        alerts.update(fault_alerts.get("goldenSignal", []))
    return sorted(alerts)


def main():
    parser = argparse.ArgumentParser(description="Generate schemas from library indexes")

    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--templates_directory", type=Path, required=True)
    parser.add_argument("--schemas_directory", type=Path, required=True)

    args = parser.parse_args()

    template_ids: Dict[str, List[str]] = {}
    template_items: Dict[str, List[Dict[str, Any]]] = {}

    # Create the JSON schema for each application, fault, and waiter index
    # These types all render the same way due to the same key/value pairings

    for library_type in ["applications", "faults", "waiters"]:
        logger.info(f"writing {library_type} library index JSON schema")

        ids, items = process_library_type(
            library_type,
            args.library_index_directory / library_type,
            args.schemas_directory / library_type
        )

        template_ids[library_type] = ids
        template_items[library_type] = items

    template_ids["alerts"] = collect_alert_ids(args.library_index_directory)

    env = Environment(loader=FileSystemLoader(args.templates_directory / "index"))

    logger.info("writing scenarios library index JSON schema")

    schema = json.loads(env.get_template("scenario.json.j2").render(ids=template_ids, items=template_items))
    schema_dir = args.schemas_directory / "library" / "index"
    write_json_schema_file(schema_dir / "scenario.json", schema)

    logger.info("writing scenarios definition JSON schemas")

    definitions_env = Environment(loader=FileSystemLoader(args.templates_directory / "definitions"))
    definitions_schema_dir = args.schemas_directory / "library" / "definitions"

    for definition_template in ["scenario.json.j2", "groundtruth.json.j2"]:
        schema = json.loads(definitions_env.get_template(definition_template).render(ids=template_ids))
        write_json_schema_file(definitions_schema_dir / definition_template.removesuffix(".j2"), schema)

if __name__ == "__main__":
    sys.exit(main())
