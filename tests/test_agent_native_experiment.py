from __future__ import annotations

from pathlib import Path

from agent_privacy.experiments.run_agent_native import (
    run_agent_native_dataset,
    run_scale_gate,
)


def test_agent_native_dataset_report_contains_safety_metrics() -> None:
    report = run_agent_native_dataset(Path("examples/tool_agent_smoke/dataset"))
    assert report["metrics"]["session"]["pairwise_f1"] == 1.0
    assert report["metrics"]["session"]["accepted_edge_precision"] == 1.0
    assert report["metrics"]["session"]["contaminated_requests"] == 0.0
    assert report["decision_counts"] == {"accept": 3, "reject": 0, "abstain": 3}


def test_small_scale_gate_passes_all_bounds() -> None:
    report = run_scale_gate(100)
    assert report["passed"]
    assert all(report["gates"].values())
    assert report["stats"]["requests_processed"] == 100
