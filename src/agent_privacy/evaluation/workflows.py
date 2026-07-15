from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Any

from agent_privacy.attacks.pipeline import group_by_label
from agent_privacy.features.extract import _shingles, _timestamp_minute, request_text


def reconstruct_workflows(
    rows: list[dict[str, Any]],
    session_labels: dict[str, str],
    truth_rows: list[dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    row_by_id = {row["request_id"]: row for row in rows}
    truth_by_id = {row["request_id"]: row for row in truth_rows or []}
    out: list[dict[str, Any]] = []
    for cluster_id, request_ids in group_by_label(session_labels).items():
        usable = [request_id for request_id in request_ids if request_id in row_by_id]
        if not usable:
            continue
        ordered = _order_requests(usable, row_by_id)
        item: dict[str, Any] = {
            "predicted_workflow_id": cluster_id,
            "request_ids": ordered,
            "request_count": len(ordered),
            "start_timestamp": row_by_id[ordered[0]].get("timestamp"),
            "end_timestamp": row_by_id[ordered[-1]].get("timestamp"),
        }
        if truth_by_id:
            item.update(_workflow_truth_metrics(ordered, truth_by_id))
        out.append(item)
    return sorted(out, key=lambda row: (-row["request_count"], row["predicted_workflow_id"]))


def workflow_reconstruction_summary(workflows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not workflows:
        return []
    evaluable = [row for row in workflows if "purity" in row]
    return [
        {
            "workflows": len(workflows),
            "evaluable_workflows": len(evaluable),
            "requests": sum(int(row["request_count"]) for row in workflows),
            "mean_purity": _mean([float(row["purity"]) for row in evaluable]),
            "mean_pairwise_order_accuracy": _mean(
                [float(row["pairwise_order_accuracy"]) for row in evaluable]
            ),
            "mean_adjacent_order_accuracy": _mean(
                [float(row["adjacent_order_accuracy"]) for row in evaluable]
            ),
        }
    ]


def _order_requests(request_ids: list[str], row_by_id: dict[str, dict[str, Any]]) -> list[str]:
    text_by_id = {request_id: request_text(row_by_id[request_id]).lower() for request_id in request_ids}
    shingle_by_id = {
        request_id: _shingles(text, 5, max_shingles=2_000) for request_id, text in text_by_id.items()
    }
    predecessor_counts: dict[str, int] = {}
    for request_id in request_ids:
        predecessor_counts[request_id] = sum(
            1
            for other_id in request_ids
            if other_id != request_id
            and _looks_like_predecessor(
                text_by_id[other_id],
                text_by_id[request_id],
                shingle_by_id[other_id],
                shingle_by_id[request_id],
            )
        )
    return sorted(
        request_ids,
        key=lambda request_id: (
            predecessor_counts[request_id],
            _timestamp_minute(str(row_by_id[request_id]["timestamp"])),
            len(text_by_id[request_id]),
            request_id,
        ),
    )


def _workflow_truth_metrics(
    ordered: list[str], truth_by_id: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    truth_workflows = [
        str(truth_by_id[request_id].get("workflow_id"))
        for request_id in ordered
        if request_id in truth_by_id and truth_by_id[request_id].get("workflow_id")
    ]
    counts = Counter(truth_workflows)
    majority_workflow = counts.most_common(1)[0][0] if counts else None
    majority_ids = [
        request_id
        for request_id in ordered
        if request_id in truth_by_id
        and str(truth_by_id[request_id].get("workflow_id")) == majority_workflow
    ]
    truth_positions = {
        request_id: int(truth_by_id[request_id].get("turn_id", 0)) for request_id in majority_ids
    }
    predicted_positions = {request_id: idx for idx, request_id in enumerate(ordered)}
    pair_total = 0
    pair_correct = 0
    for left, right in combinations(sorted(majority_ids, key=lambda rid: truth_positions[rid]), 2):
        pair_total += 1
        if predicted_positions[left] < predicted_positions[right]:
            pair_correct += 1
    adjacent_total = 0
    adjacent_correct = 0
    true_order = sorted(majority_ids, key=lambda rid: truth_positions[rid])
    for left, right in zip(true_order, true_order[1:], strict=False):
        adjacent_total += 1
        if predicted_positions[left] < predicted_positions[right]:
            adjacent_correct += 1
    return {
        "majority_workflow_id": majority_workflow,
        "majority_workflow_requests": len(majority_ids),
        "purity": len(majority_ids) / len(ordered) if ordered else 0.0,
        "pairwise_order_accuracy": pair_correct / pair_total if pair_total else 0.0,
        "adjacent_order_accuracy": adjacent_correct / adjacent_total if adjacent_total else 0.0,
    }


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
    containment = overlap / len(left_shingles) if left_shingles else 0.0
    size_ratio = len(left_shingles) / max(1, len(right_shingles))
    return containment >= 0.65 and size_ratio <= 1.05


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0
