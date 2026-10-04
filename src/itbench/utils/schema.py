"""Schema generation and export utilities."""

import copy
import json

from pathlib import Path
from typing import Any, get_args

from jsonschema import Draft202012Validator
from pydantic import BaseModel


def export_json_schema(model: type[BaseModel], output_path: Path) -> dict[str, Any]:
    """Export a Pydantic model's JSON Schema (Draft 2020-12) to a file.

    Args:
        model: Pydantic model class.
        output_path: Destination path for the schema JSON file.

    Returns:
        The generated schema dictionary.
    """
    schema = model.model_json_schema()
    schema["$schema"] = Draft202012Validator.META_SCHEMA["$id"]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=4, sort_keys=True) + "\n", encoding="utf-8")

    return schema


def export_fault_schema(fault: Any, output_path: Path) -> None:
    """Export a per-fault JSON Schema for a ``faults/*.yaml`` file.

    Builds on the base ``Fault`` schema with two additions:

    1. ``FaultTargetReference.kubernetes`` enum is constrained to only the
       class name(s) this fault declares in its ``targets`` list.

    2. The concrete ``KubernetesObject`` subtype definitions for those class
       names are merged into ``$defs``, so readers of the schema (and tooling)
       can see exactly what shape ``KubernetesWorkload``, ``KubernetesService``
       etc. have — without leaving the fault schema file.

    Args:
        fault: A ``Fault`` model instance from the fault catalog.
        output_path: Destination path for the schema JSON file.
    """
    # Deferred to avoid circular imports between models and utils.
    from itbench.models.fault import Fault
    from itbench.models.kubernetes import KubernetesObject, KubernetesObjects

    schema = copy.deepcopy(Fault.model_json_schema())
    schema["$schema"] = Draft202012Validator.META_SCHEMA["$id"]
    schema["title"] = fault.name
    schema["description"] = fault.description

    kinds = [t.kubernetes for t in fault.targets]
    if kinds:
        schema["$defs"]["FaultTargetReference"]["properties"]["kubernetes"]["enum"] = kinds

    # KubernetesObjects is Annotated[Union[...], Field(...)]; unwrap to get the Union members.
    kube_classes: dict[str, type[KubernetesObject]] = {
        cls.__name__: cls
        for cls in get_args(get_args(KubernetesObjects)[0])
    }

    for class_name in kinds or list(kube_classes.keys()):
        cls = kube_classes.get(class_name)
        if cls is None:
            continue
        kube_schema = cls.model_json_schema()
        kube_schema.pop("$schema", None)
        schema["$defs"][class_name] = kube_schema

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(schema, indent=4, sort_keys=True) + "\n", encoding="utf-8")
