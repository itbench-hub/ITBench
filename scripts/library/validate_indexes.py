import argparse
import json
import logging
import sys

from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def load_and_validate_library_index(registry: Registry, index_directory: Path, schema_file: Path) -> None:
    schema = { "$ref": schema_file.as_uri() }
    validator = Draft202012Validator(schema=schema, registry=registry)

    for index_file in index_directory.glob("*.json"):
        logger.debug("validating index: %s", index_file)

        index = json.loads(index_file.read_text(encoding="utf-8"))

        try:
            validator.validate(index)
        except ValidationError as e:
            logger.error("validation failed for %s: %s", index_file, e.message)
            raise


def main():
    parser = argparse.ArgumentParser(description="Validate library indexes against JSON schemas")

    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--schemas_directory", type=Path, required=True)

    args = parser.parse_args()

    registry = Registry()

    logger.debug("creating registry with JSON schemas")
    for schema_file in args.schemas_directory.rglob("*.json"):
        logger.debug("loading JSON schema: %s", schema_file)

        registry = registry.with_resource(
            uri=schema_file.as_uri(),
            resource=Resource.from_contents(
                json.loads(schema_file.read_text(encoding="utf-8"))
            )
        )

    for library_type in ["applications", "faults", "scenarios", "waiters"]:
        logger.info("validating %s library indexes", library_type)

        schema_name = library_type.removesuffix("s")

        try:
            load_and_validate_library_index(
                registry,
                args.library_index_directory / library_type,
                args.schemas_directory / "library" / "index" / f"{schema_name}.json"
            )
        except ValidationError:
            sys.exit(1)

    logger.info("all indexes valid")


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from utils.logging import configure_logging
    configure_logging()
    main()
