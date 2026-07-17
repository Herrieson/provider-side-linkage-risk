from __future__ import annotations

from agent_privacy.agent_state.model import LinkDecision
from agent_privacy.evaluation.selective import (
    false_merge_amplification,
    risk_coverage_curve,
    selective_linkage_metrics,
)


def test_selective_metrics_are_exact_on_hand_computed_edges() -> None:
    truth = {"a1": "a", "a2": "a", "b1": "b", "b2": "b"}
    decisions = [
        _decision("a1", None, "abstain", 0.0),
        _decision("a2", "a1", "accept", 5.0),
        _decision("b1", None, "abstain", 0.0),
        _decision("b2", "a1", "accept", 4.0),
    ]
    metrics = selective_linkage_metrics(decisions, truth)
    assert metrics["accepted_edge_precision"] == 0.5
    assert metrics["true_edge_coverage"] == 0.5
    assert metrics["abstention_rate"] == 0.5
    curve = risk_coverage_curve(decisions, truth, [4.5, 3.5])
    assert curve[0]["precision"] == 1.0
    assert curve[0]["coverage"] == 0.5
    assert curve[1]["precision"] == 0.5


def test_false_bridge_amplification_counts_contamination() -> None:
    truth = {"a1": "a", "a2": "a", "b1": "b", "b2": "b", "b3": "b"}
    pred = {request_id: "joined" for request_id in truth}
    metrics = false_merge_amplification(pred, truth)
    assert metrics["mixed_components"] == 1.0
    assert metrics["contaminated_requests"] == 5.0
    assert metrics["false_positive_pairs"] == 6.0
    assert metrics["minimum_false_bridge_edges"] == 1.0
    assert metrics["false_pairs_per_bridge"] == 6.0


def _decision(
    request_id: str,
    predecessor_id: str | None,
    disposition: str,
    score: float,
) -> LinkDecision:
    return LinkDecision(
        request_id=request_id,
        predecessor_id=predecessor_id,
        disposition=disposition,  # type: ignore[arg-type]
        score=score,
        runner_up_score=0.0,
        margin=score,
        evidence_families=(),
        conflicts=(),
        reason="test",
    )
