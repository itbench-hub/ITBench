"""Tests for the library usage statistics helpers."""

from typing import Any

from itbench.utils.statistics import build_report, compute_usage, usage_rows

_SCENARIOS: list[tuple[str, dict[str, Any]]] = [
    (
        "2",
        {
            "environment": {"applications": [{"id": "app-a"}], "domains": ["sre", "finops"]},
            "faults": [
                {"injections": [{"id": "fault-a"}, {"id": "fault-b"}]},
                {
                    "injections": [{"id": "fault-a"}],
                    "waitFor": {"preInjection": [{"id": "wait-a"}], "postInjection": [{"id": "wait-a"}]},
                },
            ],
        },
    ),
    ("10", {"environment": {"applications": [{"id": "app-a"}, {"id": "app-x"}], "domains": ["sre"]}}),
]


def test_uses_count_every_reference_but_scenarios_are_unique() -> None:
    usage = compute_usage("faults", _SCENARIOS)

    assert usage["fault-a"].uses == 2
    assert usage["fault-a"].scenarios == {"2"}
    assert usage["fault-b"].uses == 1


def test_waiters_count_both_phases() -> None:
    usage = compute_usage("waiters", _SCENARIOS)

    assert usage["wait-a"].uses == 2
    assert usage["wait-a"].scenarios == {"2"}


def test_applications_and_domains() -> None:
    assert compute_usage("applications", _SCENARIOS)["app-a"].scenarios == {"2", "10"}
    assert compute_usage("domains", _SCENARIOS)["sre"].uses == 2
    assert compute_usage("domains", _SCENARIOS)["finops"].uses == 1


def test_missing_sections_are_tolerated() -> None:
    scenarios = [("1", {}), ("2", {"environment": None, "faults": None}), ("3", {"faults": [{"waitFor": None}]})]

    for subject in ("faults", "applications", "waiters", "domains"):
        assert compute_usage(subject, scenarios) == {}


def test_usage_rows_sort_ids_and_order_scenarios_numerically() -> None:
    rows = usage_rows(compute_usage("applications", _SCENARIOS))

    assert list(rows) == ["app-a", "app-x"]
    assert rows["app-a"] == {"uses": 2, "scenarios": [2, 10]}


def test_build_report_splits_known_unused_and_unknown() -> None:
    catalogs = {
        "faults": {"fault-a": object(), "fault-unused": object()},
        "applications": {"app-a": object(), "app-x": object()},
        "waiters": {"wait-a": object()},
    }

    report = build_report(_SCENARIOS, catalogs)

    assert report["totals"] == {"scenarios": 2, "faults": 2, "applications": 2, "waiters": 1}
    assert report["faults"] == {"fault-a": {"uses": 2, "scenarios": [2]}}
    assert report["unused"]["faults"] == ["fault-unused"]
    assert report["inactive"]["faults"] == []
    assert report["unknown"]["faults"] == {"fault-b": {"uses": 1, "scenarios": [2]}}
    assert report["unknown"]["applications"] == {}
    assert report["unused"]["waiters"] == []
    assert report["domains"]["sre"] == {"uses": 2, "scenarios": [2, 10]}


def test_build_report_lists_inactive_faults_separately_from_unused() -> None:
    catalogs = {
        "faults": {"fault-a": object(), "fault-unused": object(), "fault-retired": object()},
        "applications": {},
        "waiters": {},
    }

    report = build_report(_SCENARIOS, catalogs, inactive_faults=["fault-retired"])

    assert report["inactive"]["faults"] == ["fault-retired"]
    assert report["unused"]["faults"] == ["fault-unused"]
    assert report["totals"]["faults"] == 3


def test_build_report_inactive_fault_still_reports_usage_if_referenced() -> None:
    catalogs = {"faults": {"fault-a": object()}, "applications": {}, "waiters": {}}

    report = build_report(_SCENARIOS, catalogs, inactive_faults=["fault-a"])

    assert report["faults"]["fault-a"]["uses"] == 2
    assert report["unused"]["faults"] == []
