from __future__ import annotations

from collections import Counter, defaultdict
from typing import Iterable

from agent_privacy.agent_state.model import LinkDecision


def selective_linkage_metrics(
    decisions: Iterable[LinkDecision],
    truth: dict[str, str],
) -> dict[str, float]:
    """Evaluate accepted predecessor edges while treating abstention as an explicit outcome."""

    decision_list = [decision for decision in decisions if decision.request_id in truth]
    accepted = [
        decision
        for decision in decision_list
        if decision.disposition == "accept"
        and decision.predecessor_id is not None
        and decision.predecessor_id in truth
    ]
    true_accepted = sum(
        truth[decision.request_id] == truth[decision.predecessor_id] for decision in accepted
    )
    recoverable_true_edges = sum(max(count - 1, 0) for count in Counter(truth.values()).values())
    return {
        "accepted_edges": float(len(accepted)),
        "true_accepted_edges": float(true_accepted),
        "accepted_edge_precision": true_accepted / len(accepted) if accepted else 0.0,
        "true_edge_coverage": (
            true_accepted / recoverable_true_edges if recoverable_true_edges else 0.0
        ),
        "abstention_rate": (
            sum(decision.disposition == "abstain" for decision in decision_list)
            / len(decision_list)
            if decision_list
            else 0.0
        ),
        "rejection_rate": (
            sum(decision.disposition == "reject" for decision in decision_list)
            / len(decision_list)
            if decision_list
            else 0.0
        ),
    }


def risk_coverage_curve(
    decisions: Iterable[LinkDecision],
    truth: dict[str, str],
    thresholds: Iterable[float],
) -> list[dict[str, float]]:
    candidates = [
        decision
        for decision in decisions
        if decision.predecessor_id is not None
        and decision.request_id in truth
        and decision.predecessor_id in truth
        and not decision.conflicts
    ]
    true_edges = sum(max(count - 1, 0) for count in Counter(truth.values()).values())
    rows: list[dict[str, float]] = []
    for threshold in thresholds:
        accepted = [decision for decision in candidates if decision.score >= threshold]
        correct = sum(
            truth[decision.request_id] == truth[decision.predecessor_id] for decision in accepted
        )
        rows.append(
            {
                "score_threshold": float(threshold),
                "accepted_edges": float(len(accepted)),
                "precision": correct / len(accepted) if accepted else 0.0,
                "coverage": correct / true_edges if true_edges else 0.0,
            }
        )
    return rows


def false_merge_amplification(
    pred: dict[str, str], truth: dict[str, str]
) -> dict[str, float]:
    request_ids = set(pred) & set(truth)
    predicted_components: dict[str, list[str]] = defaultdict(list)
    for request_id in request_ids:
        predicted_components[pred[request_id]].append(request_id)

    mixed_components = 0
    contaminated_requests = 0
    largest_mixed_component = 0
    false_positive_pairs = 0
    minimum_bridge_edges = 0
    for members in predicted_components.values():
        truth_counts = Counter(truth[request_id] for request_id in members)
        if len(truth_counts) <= 1:
            continue
        mixed_components += 1
        contaminated_requests += len(members)
        largest_mixed_component = max(largest_mixed_component, len(members))
        total_pairs = len(members) * (len(members) - 1) // 2
        within_truth = sum(count * (count - 1) // 2 for count in truth_counts.values())
        false_positive_pairs += total_pairs - within_truth
        minimum_bridge_edges += len(truth_counts) - 1
    return {
        "mixed_components": float(mixed_components),
        "contaminated_requests": float(contaminated_requests),
        "largest_mixed_component": float(largest_mixed_component),
        "false_positive_pairs": float(false_positive_pairs),
        "minimum_false_bridge_edges": float(minimum_bridge_edges),
        "contaminated_requests_per_bridge": (
            contaminated_requests / minimum_bridge_edges if minimum_bridge_edges else 0.0
        ),
        "false_pairs_per_bridge": (
            false_positive_pairs / minimum_bridge_edges if minimum_bridge_edges else 0.0
        ),
    }
