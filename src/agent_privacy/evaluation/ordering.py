from __future__ import annotations

from itertools import combinations
from typing import Any

from agent_privacy.attacks.pipeline import group_by_label
from agent_privacy.evaluation.clustering import truth_labels
from agent_privacy.features.extract import _shingles, _timestamp_minute, request_text


def evaluate_turn_ordering(
    rows: list[dict[str, Any]],
    session_labels: dict[str, str],
    truth_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    row_by_id = {row["request_id"]: row for row in rows}
    truth_by_id = {
        row["request_id"]: row
        for row in truth_rows
        if row.get("workflow_id") and row.get("turn_id") is not None
    }
    true_session = truth_labels(truth_rows, "session")
    adjacent_total = 0
    adjacent_correct = 0
    context_adjacent_correct = 0
    pair_total = 0
    pair_correct = 0
    context_pair_correct = 0
    pure_clusters = 0
    evaluated_clusters = 0

    for request_ids in group_by_label(session_labels).values():
        usable = [
            request_id
            for request_id in request_ids
            if request_id in row_by_id and request_id in truth_by_id and request_id in true_session
        ]
        if len(usable) < 2:
            continue
        true_ids = {true_session[request_id] for request_id in usable}
        if len(true_ids) != 1:
            continue
        evaluated_clusters += 1
        true_order = sorted(usable, key=lambda request_id: _turn_id(truth_by_id[request_id]))
        predicted_order = sorted(
            usable,
            key=lambda request_id: (
                _timestamp_minute(str(row_by_id[request_id]["timestamp"])),
                request_id,
            ),
        )
        context_order = _context_order(usable, row_by_id)
        predicted_positions = {request_id: idx for idx, request_id in enumerate(predicted_order)}
        context_positions = {request_id: idx for idx, request_id in enumerate(context_order)}
        pure_clusters += 1

        for left, right in zip(true_order, true_order[1:], strict=False):
            adjacent_total += 1
            if predicted_positions[left] < predicted_positions[right]:
                adjacent_correct += 1
            if context_positions[left] < context_positions[right]:
                context_adjacent_correct += 1

        for left, right in combinations(true_order, 2):
            pair_total += 1
            if predicted_positions[left] < predicted_positions[right]:
                pair_correct += 1
            if context_positions[left] < context_positions[right]:
                context_pair_correct += 1

    return {
        "adjacent_pair_accuracy": _ratio(adjacent_correct, adjacent_total),
        "pairwise_order_accuracy": _ratio(pair_correct, pair_total),
        "context_adjacent_pair_accuracy": _ratio(context_adjacent_correct, adjacent_total),
        "context_pairwise_order_accuracy": _ratio(context_pair_correct, pair_total),
        "adjacent_pairs": adjacent_total,
        "ordered_pairs": pair_total,
        "evaluated_clusters": evaluated_clusters,
        "pure_session_clusters": pure_clusters,
    }


def evaluate_ordering_all(
    rows: list[dict[str, Any]],
    predictions: dict[str, dict[str, dict[str, str]]],
    truth_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for method, level_predictions in predictions.items():
        session_labels = level_predictions.get("session")
        if not session_labels:
            continue
        out.append(
            {
                "method": method,
                "level": "session",
                **evaluate_turn_ordering(rows, session_labels, truth_rows),
            }
        )
    return out


def _turn_id(row: dict[str, Any]) -> int:
    return int(row.get("turn_id", 0))


def _context_order(request_ids: list[str], row_by_id: dict[str, dict[str, Any]]) -> list[str]:
    text_by_id = {request_id: request_text(row_by_id[request_id]).lower() for request_id in request_ids}
    shingle_by_id = {
        request_id: _shingles(text, 5, max_shingles=2_000) for request_id, text in text_by_id.items()
    }
    score_by_id: dict[str, int] = {}
    for request_id in request_ids:
        text = text_by_id[request_id]
        shingles = shingle_by_id[request_id]
        predecessors = 0
        for other_id in request_ids:
            if other_id == request_id:
                continue
            other_text = text_by_id[other_id]
            other_shingles = shingle_by_id[other_id]
            if _looks_like_predecessor(other_text, text, other_shingles, shingles):
                predecessors += 1
        score_by_id[request_id] = predecessors
    return sorted(
        request_ids,
        key=lambda request_id: (
            score_by_id[request_id],
            len(text_by_id[request_id]),
            _timestamp_minute(str(row_by_id[request_id]["timestamp"])),
            request_id,
        ),
    )


def _looks_like_predecessor(
    left_text: str,
    right_text: str,
    left_shingles: set[str],
    right_shingles: set[str],
) -> bool:
    if len(left_text) < len(right_text) and left_text[:1_000] and left_text[:1_000] in right_text:
        return True
    if not left_shingles or not right_shingles:
        return False
    overlap = len(left_shingles & right_shingles)
    if overlap == 0:
        return False
    containment = overlap / len(left_shingles)
    size_ratio = len(left_shingles) / max(1, len(right_shingles))
    return containment >= 0.65 and size_ratio <= 1.05


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0
