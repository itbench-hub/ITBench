"""Helpers for reading scenario definitions from the library."""

from collections.abc import Callable
from pathlib import Path
from typing import Any

import yaml


def summarize_scenario(scenario_id: str, data: dict[str, Any]) -> dict[str, Any]:
    """Return the id, domains, applications and fault ids of a parsed scenario."""
    env = data.get("environment") or {}
    return {
        "id": scenario_id,
        "domains": list(env.get("domains") or []),
        "applications": [a.get("id", "?") for a in env.get("applications") or []],
        "faults": [inj.get("id", "?") for fault in data.get("faults") or [] for inj in fault.get("injections") or []],
    }


def known_scenario_ids(scenarios_dir: Path) -> list[str]:
    """Return the ids of all scenario directories in *scenarios_dir*, in numeric order.

    A missing *scenarios_dir* yields an empty list.
    """
    if not scenarios_dir.is_dir():
        return []
    return sorted((d.name for d in scenarios_dir.iterdir() if d.name.isdigit()), key=int)


def load_scenario_docs(
    scenarios_dir: Path,
    on_error: Callable[[str, Exception], None] | None = None,
) -> list[tuple[str, dict[str, Any]]]:
    """Return ``(scenario_id, parsed_yaml)`` for every readable scenario in *scenarios_dir*.

    Scenario directories are named with integers and returned in numeric order. Directories
    without a ``scenario.yaml`` are ignored. Files that cannot be parsed, or whose top level
    is not a mapping, are skipped and reported through *on_error*.
    """
    if not scenarios_dir.is_dir():
        return []

    results: list[tuple[str, dict[str, Any]]] = []
    scenario_dirs = sorted(
        (d for d in scenarios_dir.iterdir() if d.is_dir() and d.name.isdigit()),
        key=lambda d: int(d.name),
    )
    for scenario_dir in scenario_dirs:
        scenario_file = scenario_dir / "scenario.yaml"
        if not scenario_file.is_file():
            continue
        try:
            data = yaml.safe_load(scenario_file.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("top level of scenario.yaml must be a mapping")
        except Exception as exc:
            if on_error is not None:
                on_error(scenario_dir.name, exc)
            continue
        results.append((scenario_dir.name, data))
    return results
