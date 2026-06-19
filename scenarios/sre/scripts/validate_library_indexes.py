import argparse
import json
import logging
import sys

from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)

def load_and_validate_library_index(registry: Registry, index_directory: Path, schema_file: Path) -> None:
    schema = { "$ref": schema_file.as_uri() }
    validator = Draft202012Validator(schema=schema, registry=registry)

    for index_file in index_directory.glob("*.json"):
        logger.info(f"validating index: {index_file}")

        index = json.loads(index_file.read_text(encoding="utf-8"))

        try:
            validator.validate(index)
        except ValidationError as e:
            logger.exception(f"validation failed: {e}")
            sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Generate schemas from library indexes")

    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--schemas_directory", type=Path, required=True)

    args = parser.parse_args()

    registry = Registry()

    logger.debug("creating registry with JSON schemas")
    for schema_file in args.schemas_directory.rglob("*.json"):
        logger.debug(f"loading JSON schema: {schema_file}")

        registry = registry.with_resource(
            uri=schema_file.as_uri(),
            resource=Resource.from_contents(
                json.loads(schema_file.read_text(encoding="utf-8"))
            )
        )

    for library_type in ["applications", "faults", "scenarios", "waiters"]:
        logger.info(f"validating {library_type} library indexes")

        schema_name = library_type.removesuffix("s")

        load_and_validate_library_index(
            registry,
            args.library_index_directory / library_type,
            args.schemas_directory / "library" / "index" / f"{schema_name}.json"
        )

if __name__ == "__main__":
    main()
