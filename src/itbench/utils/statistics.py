"""Usage statistics for library primitives, derived from the scenarios that reference them."""

from collections import defaultdict
from collections.abc import Collection, Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from typing import Any

SUBJECTS = ("faults", "applications", "waiters")


@dataclass
class Usage:
    """How often one primitive is referenced: total references and the scenarios that make them."""

    uses: int = 0
    scenarios: set[str] = field(default_factory=set)

    def sorted_scenarios(self) -> list[int]:
        """Return the scenario ids as integers in ascending order (scenario directories are numeric)."""
        return sorted(int(scenario_id) for scenario_id in self.scenarios)


def _fault_ids(data: Mapping[str, Any]) -> Iterator[str]:
    for block in data.get("faults") or []:
        for injection in block.get("injections") or []:
            yield str(injection.get("id", "?"))


def _application_ids(data: Mapping[str, Any]) -> Iterator[str]:
    for application in (data.get("environment") or {}).get("applications") or []:
        yield str(application.get("id", "?"))


def _waiter_ids(data: Mapping[str, Any]) -> Iterator[str]:
    for block in data.get("faults") or []:
        wait_for = block.get("waitFor") or {}
        for phase in ("preInjection", "postInjection"):
            for waiter in wait_for.get(phase) or []:
                yield str(waiter.get("id", "?"))


def _domains(data: Mapping[str, Any]) -> Iterator[str]:
    for domain in (data.get("environment") or {}).get("domains") or []:
        yield str(domain)


_EXTRACTORS = {
    "faults": _fault_ids,
    "applications": _application_ids,
    "waiters": _waiter_ids,
    "domains": _domains,
}


def compute_usage(subject: str, scenarios: Iterable[tuple[str, Mapping[str, Any]]]) -> dict[str, Usage]:
    """Count how often each *subject* is referenced across *scenarios*.

    *subject* is one of ``faults``, ``applications``, ``waiters`` or ``domains``. *scenarios* is an
    iterable of ``(scenario_id, parsed_yaml)`` pairs, as returned by ``load_scenario_docs``.
    ``uses`` counts every reference; ``scenarios`` holds each referencing scenario once.
    """
    extract = _EXTRACTORS[subject]
    usage: defaultdict[str, Usage] = defaultdict(Usage)
    for scenario_id, data in scenarios:
        for item_id in extract(data):
            entry = usage[item_id]
            entry.uses += 1
            entry.scenarios.add(scenario_id)
    return dict(usage)


def usage_rows(usage: Mapping[str, Usage]) -> dict[str, dict[str, Any]]:
    """Convert usage into plain ``{"uses": n, "scenarios": [...]}`` dictionaries keyed by id."""
    return {
        item_id: {"uses": entry.uses, "scenarios": entry.sorted_scenarios()} for item_id, entry in sorted(usage.items())
    }


def build_report(
    scenarios: list[tuple[str, Mapping[str, Any]]],
    catalogs: Mapping[str, Mapping[str, Any]],
    inactive_faults: Collection[str] = (),
) -> dict[str, Any]:
    """Build the full statistics report for *scenarios*.

    *catalogs* maps each of :data:`SUBJECTS` to its catalog. Alongside per-primitive usage, the
    report lists catalog entries no scenario references (``unused``) and ids scenarios reference
    that the catalog does not define (``unknown``).

    *inactive_faults* are faults that are retired or converted. They are expected to have no
    usage, so they are listed under ``inactive`` instead of ``unused``.
    """
    report: dict[str, Any] = {
        "totals": {"scenarios": len(scenarios)},
        "unused": {},
        "inactive": {"faults": sorted(inactive_faults)},
        "unknown": {},
    }
    for subject in SUBJECTS:
        usage = compute_usage(subject, scenarios)
        catalog = catalogs[subject]
        expected_unused = set(inactive_faults) if subject == "faults" else set()
        report["totals"][subject] = len(catalog)
        report["unused"][subject] = sorted(set(catalog) - set(usage) - expected_unused)
        report["unknown"][subject] = {
            item_id: entry for item_id, entry in usage_rows(usage).items() if item_id not in catalog
        }
        report[subject] = usage_rows({item_id: entry for item_id, entry in usage.items() if item_id in catalog})

    report["domains"] = usage_rows(compute_usage("domains", scenarios))
    return report
