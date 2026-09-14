"""CLI handlers for 'library' subcommands."""
import argparse
import sys

from pathlib import Path

from rich.console import Console
from rich.table import Table

from itbench.library.generate import (
    generate_index_schemas,
    generate_indexes,
    generate_readmes,
    generate_specs,
)
from itbench.library.query import (
    get_resource,
    get_scenario_statistics,
    list_resources,
    search_resources,
)
from itbench.library.scaffold import (
    create_fault_stub,
    create_scenario_stub,
    next_fault_index,
    next_scenario_index,
)
from itbench.library.validate import (
    validate_all_indexes
)

console = Console()


def get_default_paths(root: Path | None = None) -> dict[str, Path]:
    if root is None:
        # Search upwards for repo root marker (pyproject.toml)
        cur = Path.cwd()
        for parent in [cur] + list(cur.parents):
            if (parent / "pyproject.toml").exists() and (parent / "library").exists():
                root = parent
                break
        if root is None:
            root = Path.cwd()

    return {
        "root": root,
        "library_index_directory": root / "library" / "indexes",
        "templates_directory": root / "templates" / "library" / "indexes",
        "schemas_directory": root / "schemas" / "json",
        "specs_templates_directory": root / "templates" / "library" / "specs" / "scenarios",
        "specs_directory": root / "library" / "specs" / "scenarios",
        "docs_templates_directory": root / "templates" / "documentation" / "library",
        "documentation_directory": root / "documentation" / "library",
        "schemas_templates_directory": root / "templates" / "schemas" / "json" / "library" / "index",
        "playbooks_directory": root / "scenarios" / "sre" / "project",
    }


def handle_validate(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    index_dir = args.library_index_directory or paths["library_index_directory"]
    schemas_dir = args.schemas_directory or paths["schemas_directory"]

    console.print(f"[bold blue]Validating library indexes against schemas...[/bold blue]")
    try:
        validate_all_indexes(index_dir, schemas_dir)
        console.print("[bold green]✓ All library indexes are valid![/bold green]")
        return 0
    except Exception as e:
        console.print(f"[bold red]✗ Validation failed:[/bold red] {e}")
        return 1


def handle_generate(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    target = args.target

    try:
        if target in ["all", "indexes"]:
            console.print("[blue]Generating library indexes...[/blue]")
            generate_indexes(
                paths["templates_directory"],
                paths["library_index_directory"],
                paths["playbooks_directory"],
            )
        if target in ["all", "schemas"]:
            console.print("[blue]Generating index schemas...[/blue]")
            generate_index_schemas(
                paths["library_index_directory"],
                paths["schemas_templates_directory"],
                paths["schemas_directory"],
            )
        if target in ["all", "specs"]:
            console.print("[blue]Generating scenario specs...[/blue]")
            generate_specs(
                paths["specs_templates_directory"],
                paths["library_index_directory"],
                paths["specs_directory"],
            )
        if target in ["all", "readmes"]:
            console.print("[blue]Generating documentation readmes...[/blue]")
            generate_readmes(
                paths["docs_templates_directory"],
                paths["library_index_directory"],
                paths["documentation_directory"],
            )
    except Exception as e:
        console.print(f"[bold red]✗ Generation failed:[/bold red] {e}")
        return 1

    console.print("[bold green]✓ Generation complete![/bold green]")
    return 0


def handle_scaffold(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    item_type = args.item_type

    if item_type == "scenario":
        scenarios_dir = paths["templates_directory"] / "scenarios"
        description = args.description or input("Enter description for new scenario: ").strip()
        idx = next_scenario_index(scenarios_dir)
        dest = create_scenario_stub(description, idx, scenarios_dir)
        console.print(f"[bold green]✓ Scenario stub created:[/bold green] {dest.resolve()}")
    elif item_type == "fault":
        faults_dir = paths["templates_directory"] / "faults"
        name = args.name or input("Enter fault name: ").strip()
        description = args.description or input("Enter fault description: ").strip()
        expectation = args.expectation or input("Enter fault expectation: ").strip()
        idx = next_fault_index(faults_dir)
        dest = create_fault_stub(name, description, expectation, idx, faults_dir)
        console.print(f"[bold green]✓ Fault stub created:[/bold green] {dest.resolve()}")
    return 0


def handle_list(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    res_type = args.resource_type
    items = list_resources(paths["library_index_directory"], res_type)

    if not items:
        console.print(f"[yellow]No {res_type} found.[/yellow]")
        return 0

    table = Table(title=f"ITBench Library: {res_type.capitalize()}")
    if res_type == "scenarios":
        table.add_column("ID / Index", style="cyan", justify="right")
        table.add_column("Category", style="magenta")
        table.add_column("Complexity", style="green")
        table.add_column("Description", style="white")
        for sc in items:
            table.add_row(
                str(sc.get("id", sc.get("index", ""))),
                sc.get("category", "-"),
                sc.get("complexity", "-"),
                sc.get("description", "")[:80] + ("..." if len(sc.get("description", "")) > 80 else ""),
            )
    elif res_type == "faults":
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Platform", style="green")
        table.add_column("Description", style="white")
        for f in items:
            table.add_row(
                str(f.get("id", "")),
                str(f.get("name", "")),
                str(f.get("platform", "-")),
                str(f.get("description", ""))[:70],
            )
    else:
        table.add_column("ID", style="cyan")
        table.add_column("Name", style="magenta")
        table.add_column("Description", style="white")
        for item in items:
            table.add_row(
                str(item.get("id", "")),
                str(item.get("name", "")),
                str(item.get("description", ""))[:70],
            )

    console.print(table)
    return 0


def handle_show(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    res_type = args.resource_type
    res_id = args.id
    item = get_resource(paths["library_index_directory"], res_type, res_id)

    if not item:
        console.print(f"[bold red]Resource not found:[/bold red] {res_type} with ID/index '{res_id}'")
        return 1

    console.print_json(data=item)
    return 0


def handle_search(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    query = args.query
    results = search_resources(paths["library_index_directory"], query)

    total_found = sum(len(v) for v in results.values())
    if total_found == 0:
        console.print(f"[yellow]No results found matching '{query}'.[/yellow]")
        return 0

    console.print(f"[bold green]Found {total_found} matching result(s):[/bold green]\n")
    for res_type, items in results.items():
        if not items:
            continue
        table = Table(title=f"Matches in {res_type.capitalize()} ({len(items)})")
        table.add_column("ID", style="cyan")
        table.add_column("Name / Category", style="magenta")
        table.add_column("Description", style="white")
        for it in items:
            table.add_row(
                str(it.get("id", it.get("index", ""))),
                str(it.get("name", it.get("category", ""))),
                str(it.get("description", ""))[:80],
            )
        console.print(table)
        console.print()

    return 0


def handle_stats(args: argparse.Namespace) -> int:
    paths = get_default_paths(args.root)
    stats = get_scenario_statistics(paths["library_index_directory"])

    console.print("[bold blue]ITBench Scenario Distribution Statistics[/bold blue]\n")

    # Categories
    cat_table = Table(title="Categories")
    cat_table.add_column("Category", style="cyan")
    cat_table.add_column("Count", justify="right", style="green")
    for cat, count in sorted(stats["categories"].items()):
        cat_table.add_row(cat, str(count))
    console.print(cat_table)
    console.print()

    # Applications
    app_table = Table(title="Applications")
    app_table.add_column("Application", style="magenta")
    app_table.add_column("Count", justify="right", style="green")
    for app, count in sorted(stats["applications"].items()):
        app_table.add_row(app, str(count))
    console.print(app_table)
    console.print()

    # Complexities
    comp_table = Table(title="Complexities")
    comp_table.add_column("Complexity", style="yellow")
    comp_table.add_column("Count", justify="right", style="green")
    for comp, count in sorted(stats["complexities"].items()):
        comp_table.add_row(comp, str(count))
    console.print(comp_table)

    return 0


def register_library_subparsers(subparsers: argparse._SubParsersAction) -> None:
    # validate
    val_p = subparsers.add_parser("validate", help="Validate library indexes against JSON schemas")
    val_p.add_argument("--library_index_directory", type=Path, default=None)
    val_p.add_argument("--schemas_directory", type=Path, default=None)
    val_p.set_defaults(func=handle_validate)

    # generate
    gen_p = subparsers.add_parser("generate", help="Generate indexes, schemas, specs, or readmes")
    gen_p.add_argument("target", choices=["all", "indexes", "schemas", "specs", "readmes"], default="all", nargs="?")
    gen_p.set_defaults(func=handle_generate)

    # scaffold
    scaf_p = subparsers.add_parser("scaffold", help="Scaffold a new scenario or fault stub")
    scaf_p.add_argument("item_type", choices=["scenario", "fault"])
    scaf_p.add_argument("--description", type=str, default=None)
    scaf_p.add_argument("--name", type=str, default=None)
    scaf_p.add_argument("--expectation", type=str, default=None)
    scaf_p.set_defaults(func=handle_scaffold)

    # list
    list_p = subparsers.add_parser("list", help="List library resources")
    list_p.add_argument("resource_type", choices=["scenarios", "faults", "applications", "waiters"])
    list_p.set_defaults(func=handle_list)

    # show
    show_p = subparsers.add_parser("show", help="Show full JSON definition of a library resource")
    show_p.add_argument("resource_type", choices=["scenarios", "faults", "applications", "waiters"])
    show_p.add_argument("id", type=str, help="Resource ID or scenario number")
    show_p.set_defaults(func=handle_show)

    # search
    search_p = subparsers.add_parser("search", help="Search across library items")
    search_p.add_argument("query", type=str, help="Search terms")
    search_p.set_defaults(func=handle_search)

    # stats
    stats_p = subparsers.add_parser("stats", help="Show scenario distribution statistics")
    stats_p.set_defaults(func=handle_stats)
