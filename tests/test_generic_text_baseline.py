from __future__ import annotations

from pathlib import Path

from agent_privacy.experiments.generic_text_baseline import run_generic_text_baseline


def test_generic_text_baseline_is_bounded_and_runs_on_smoke() -> None:
    report = run_generic_text_baseline(
        Path("examples/tool_agent_smoke/dataset"), max_active_requests=3
    )
    assert report["requests"] == 6
    assert report["peak_active_requests"] <= 3
    assert report["comparisons"] <= 6 * 3
    assert 0.0 <= report["metrics"]["pairwise_f1"] <= 1.0
