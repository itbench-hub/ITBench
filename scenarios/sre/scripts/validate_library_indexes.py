import argparse
import json

from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

def load_and_validate_library_index(registry: Registry, index_directory: Path, schema_file: Path) -> None:
    schema = { "$ref": schema_file.as_uri() }
    validator = Draft202012Validator(schema=schema, registry=registry)

    for index_file in index_directory.glob("*.json"):
        index = json.loads(index_file.read_text(encoding="utf-8"))

        try:
            validator.validate(index)
            print("Success: The local object matches the local schema copy perfectly!")
        except ValidationError as e:
            print(f"Validation failed: {e.message}")

def main():
    parser = argparse.ArgumentParser(description="Generate schemas from library indexes")

    parser.add_argument("--library_index_directory", type=Path, required=True)
    parser.add_argument("--schemas_directory", type=Path, required=True)

    args = parser.parse_args()

    registry = Registry()

    for schema_file in args.schemas_directory.rglob("*.json"):
        registry = registry.with_resource(
            uri=schema_file.as_uri(),
            resource=Resource.from_contents(
                json.loads(schema_file.read_text(encoding="utf-8"))
            )
        )

    for library_type in ["applications", "faults", "scenarios", "waiters"]:
        schema_file_name = f"{library_type.removesuffix("s")}.json"

        load_and_validate_library_index(
            registry,
            args.library_index_directory / library_type,
            args.schemas_directory / "library" / "index" / schema_file_name
        )

if __name__ == "__main__":
    main()
