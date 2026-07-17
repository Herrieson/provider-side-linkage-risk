from __future__ import annotations

from pathlib import Path

from agent_privacy.experiments.agent_native_ablations import run_ablations


def test_agent_native_ablations_are_distinct_and_full_passes_smoke() -> None:
    rows = run_ablations(Path("examples/tool_agent_smoke/dataset"))
    by_name = {row["variant"]: row for row in rows}
    assert by_name["full"]["pairwise_f1"] == 1.0
    assert by_name["full"]["contaminated_requests"] == 0.0
    assert all(0.0 <= row["pairwise_f1"] <= 1.0 for row in rows)
    assert by_name["tool_resource_only"]["abstention_rate"] >= 0.5
    assert set(by_name) == {
        "full",
        "replay_only",
        "tool_resource_only",
        "typed_handle_only",
        "without_conflicts",
    }
