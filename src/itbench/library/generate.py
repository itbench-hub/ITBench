"""Generate indexes, schemas, specs, and documentation from library templates."""
import json
import logging

from operator import itemgetter
from pathlib import Path
from typing import Any

import yaml

from jinja2 import Environment, FileSystemLoader
from jsonschema import Draft202012Validator

from itbench.utils.yaml_dumper import IndentedSafeDumper

logging.getLogger(__name__).addHandler(logging.NullHandler())
logger = logging.getLogger(__name__)


def write_json_file(file_path: Path, content: dict[str, Any] | list[dict[str, Any]]) -> None:
    logger.debug("writing index file: %s", file_path)
    file_path.write_text(json.dumps(content, sort_keys=True, indent=4) + "\n", encoding="utf-8")


def write_yaml_file(file_path: Path, content: str) -> None:
    logger.debug("writing spec file: %s", file_path)
    file_path.write_text(content, encoding="utf-8")


def write_markdown_file(file_path: Path, content: str) -> None:
    logger.debug("writing markdown file: %s", file_path)
    file_path.write_text(content, encoding="utf-8")


def extract_index_from_filename(filename: str) -> int:
    return int(filename.split(".", 1)[0])


def generate_id_from_name(name: str) -> str:
    return name.lower().replace(" ", "-")


def load_releases(applications: Path, tools: Path) -> dict[str, Any]:
    applications_releases = yaml.safe_load(applications.read_text(encoding="utf-8"))
    tools_releases = yaml.safe_load(tools.read_text(encoding="utf-8"))
    return {
        "applications": applications_releases["applications_releases"],
        "tools": tools_releases["tools_releases"],
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
        index["$schema"] = f"https://raw.githubusercontent.com/itbench-hub/ITBench/refs/heads/main/schemas/library/index/{library_type.removesuffix('s')}.json"

        indexes.append(index)
        if library_type == "faults":
            faults_lookup[index_id] = index

        filename = template_file.name.removesuffix(".yaml.j2") + ".json"
        write_json_file(index_directory / filename, index)

    return faults_lookup


def create_scenarios_indexes(
    templates_directory: Path,
    index_directory: Path,
    playbooks_directory: Path,
    faults: dict[str, Any],
) -> None:
    logger.info("writing scenarios library indexes")
    releases = load_releases(
        playbooks_directory / "roles" / "applications" / "vars" / "main" / "releases.yaml",
        playbooks_directory / "roles" / "tools" / "vars" / "main" / "releases.yaml",
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

        index["index"] = extract_index_from_filename(template_file.name)
        index["alerts"] = sorted(alerts)
        index["platforms"] = sorted(platforms)
        index["solutions"] = solutions
        index["tags"] = sorted(tags)
        index["$schema"] = "https://raw.githubusercontent.com/itbench-hub/ITBench/refs/heads/main/schemas/library/index/scenario.json"

        indexes.append(index)
        filename = template_file.name.removesuffix(".yaml.j2") + ".json"
        write_json_file(index_directory / filename, index)


def generate_indexes(templates_directory: Path, library_index_directory: Path, playbooks_directory: Path) -> None:
    """Generate all JSON index files from YAML templates."""
    _ = load_and_write_library_index(
        "applications",
        templates_directory / "applications",
        library_index_directory / "applications",
    )
    faults_cache = load_and_write_library_index(
        "faults",
        templates_directory / "faults",
        library_index_directory / "faults",
    )
    _ = load_and_write_library_index(
        "waiters",
        templates_directory / "waiters",
        library_index_directory / "waiters",
    )
    create_scenarios_indexes(
        templates_directory / "scenarios",
        library_index_directory / "scenarios",
        playbooks_directory,
        faults_cache,
    )


def process_library_type(library_type: str, index_dir: Path, schema_dir: Path) -> tuple[list[str], list[dict[str, Any]]]:
    ids: list[str] = []
    items: list[dict[str, Any]] = []

    for index_file in index_dir.glob("*.json"):
        index = json.loads(index_file.read_text(encoding="utf-8"))
        index_id = index["id"]

        schema = index["arguments"]["jsonSchema"]
        schema["$schema"] = Draft202012Validator.META_SCHEMA["$id"]
        write_json_file(schema_dir / f"{index_id}.json", schema)

        ids.append(index_id)
        items.append({
            "if": {"properties": {"id": {"const": index_id}}},
            "then": {"properties": {"args": {"$ref": f"../../{library_type}/{index_id}.json"}}},
        })

    return ids, items


def generate_index_schemas(library_index_directory: Path, templates_directory: Path, schemas_directory: Path) -> None:
    """Generate JSON schemas from index files."""
    template_ids: dict[str, list[str]] = {}
    template_items: dict[str, list[dict[str, Any]]] = {}

    for library_type in ["applications", "faults", "waiters"]:
        logger.info("writing %s library index JSON schema", library_type)
        ids, items = process_library_type(
            library_type,
            library_index_directory / library_type,
            schemas_directory / library_type,
        )
        template_ids[library_type] = ids
        template_items[library_type] = items

    logger.info("writing scenarios library index JSON schema")
    env = Environment(loader=FileSystemLoader(templates_directory))
    template = env.get_template("scenario.json.j2")
    schema = json.loads(template.render(ids=template_ids, items=template_items))

    schema_dir = schemas_directory / "library" / "index"
    write_json_file(schema_dir / "scenario.json", schema)


def load_scenarios(library_index_directory: Path) -> list[dict]:
    return [
        json.loads(f.read_text(encoding="utf-8"))
        for f in (library_index_directory / "scenarios").glob("*.json")
    ]


def generate_scenario_specs(scenario: dict, specs_directory: Path, environment: Environment) -> None:
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


def generate_specs(templates_directory: Path, library_index_directory: Path, specs_directory: Path) -> None:
    """Generate scenario.yaml and groundtruth.yaml specs."""
    env = Environment(
        loader=FileSystemLoader(templates_directory),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    scenarios = load_scenarios(library_index_directory)
    logger.info("generating spec files for %d scenario(s)", len(scenarios))
    for scenario in scenarios:
        generate_scenario_specs(scenario, specs_directory, env)


def load_library_indexes(index_directory: Path) -> list[dict[str, Any]]:
    return [
        json.loads(f.read_text(encoding="utf-8")) for f in index_directory.glob("*.json")
    ]


def generate_readmes(templates_directory: Path, library_index_directory: Path, documentation_directory: Path) -> None:
    """Generate documentation markdown files for all library indexes."""
    env = Environment(
        loader=FileSystemLoader(templates_directory),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )

    application_indexes = load_library_indexes(library_index_directory / "applications")
    faults_indexes = load_library_indexes(library_index_directory / "faults")
    waiters_indexes = load_library_indexes(library_index_directory / "waiters")
    scenarios_indexes = load_library_indexes(library_index_directory / "scenarios")

    # Applications
    logger.info("creating documentation for %d application(s)", len(application_indexes))
    write_markdown_file(
        documentation_directory / "applications" / "README.md",
        env.get_template("applications/README.md.j2").render({"applications": sorted(application_indexes, key=itemgetter("name"))}),
    )
    app_tmpl = env.get_template("applications/application.md.j2")
    for app in application_indexes:
        app_id = app["id"]
        write_markdown_file(
            documentation_directory / "applications" / f"{app_id}.md",
            app_tmpl.render({
                "application": app,
                "source_file_path": f"../../../library/indexes/applications/{app_id}.json",
                "schema_file_path": f"../../../schemas/json/applications/{app_id}.json",
            }),
        )

    # Faults
    logger.info("creating documentation for %d fault(s)", len(faults_indexes))
    write_markdown_file(
        documentation_directory / "faults" / "README.md",
        env.get_template("faults/README.md.j2").render({"faults": sorted(faults_indexes, key=itemgetter("name"))}),
    )
    fault_tmpl = env.get_template("faults/fault.md.j2")
    for fault in faults_indexes:
        fault_id = fault["id"]
        write_markdown_file(
            documentation_directory / "faults" / f"{fault_id}.md",
            fault_tmpl.render({
                "fault": fault,
                "source_file_path": f"../../../library/indexes/faults/{fault_id}.json",
                "schema_file_path": f"../../../schemas/json/faults/{fault_id}.json",
                "implementation_file_path": f"../../../scenarios/sre/project/roles/faults/tasks/inject_{fault_id.replace('-', '_')}.yaml",
            }),
        )

    # Waiters
    logger.info("creating documentation for %d waiter(s)", len(waiters_indexes))
    write_markdown_file(
        documentation_directory / "waiters" / "README.md",
        env.get_template("waiters/README.md.j2").render({"waiters": sorted(waiters_indexes, key=itemgetter("name"))}),
    )
    waiter_tmpl = env.get_template("waiters/waiter.md.j2")
    for waiter in waiters_indexes:
        waiter_id = waiter["id"]
        write_markdown_file(
            documentation_directory / "waiters" / f"{waiter_id}.md",
            waiter_tmpl.render({
                "waiter": waiter,
                "source_file_path": f"../../../library/indexes/waiters/{waiter_id}.json",
                "schema_file_path": f"../../../schemas/json/waiters/{waiter_id}.json",
            }),
        )

    # Scenarios
    logger.info("creating documentation for %d scenario(s)", len(scenarios_indexes))
    write_markdown_file(
        documentation_directory / "scenarios" / "README.md",
        env.get_template("scenarios/README.md.j2").render({"scenarios": sorted(scenarios_indexes, key=itemgetter("id"))}),
    )

    applications_lookup = {a["id"]: a for a in application_indexes}
    faults_lookup = {f["id"]: f for f in faults_indexes}
    scenario_tmpl = env.get_template("scenarios/scenario.md.j2")

    for sc in scenarios_indexes:
        sc_id = sc["id"]
        sc_cat = sc.get("category", "sre")
        cat_dir = documentation_directory / "scenarios" / sc_cat
        cat_dir.mkdir(parents=True, exist_ok=True)
        write_markdown_file(
            cat_dir / f"{sc_id}.md",
            scenario_tmpl.render({
                "scenario": sc,
                "source_file_path": f"../../../../library/indexes/scenarios/{sc_id}.json",
                "schema_file_path": f"../../../../schemas/json/scenarios/{sc_id}.json",
                "applications": applications_lookup,
                "faults": faults_lookup,
            }),
        )
