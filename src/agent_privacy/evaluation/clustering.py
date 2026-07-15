from __future__ import annotations

from collections import Counter, defaultdict
from math import comb
from typing import Any


def truth_labels(truth_rows: list[dict[str, Any]], level: str) -> dict[str, str]:
    field = {"session": "workflow_id", "user": "user_id", "project": "project_id", "org": "org_id"}[
        level
    ]
    labels: dict[str, str] = {}
    for row in truth_rows:
        value = row.get(field)
        if _missing_label(value):
            continue
        labels[row["request_id"]] = str(value)
    return labels


def clustering_metrics(pred: dict[str, str], truth: dict[str, str]) -> dict[str, float]:
    request_ids = sorted(set(pred) & set(truth))
    pred_clusters = _clusters({rid: pred[rid] for rid in request_ids})
    truth_clusters = _clusters({rid: truth[rid] for rid in request_ids})

    pred_pairs = sum(_choose2(len(members)) for members in pred_clusters.values())
    truth_pairs = sum(_choose2(len(members)) for members in truth_clusters.values())
    true_positive = 0
    purity_hits = 0
    merge_count = 0

    for members in pred_clusters.values():
        counts = Counter(truth[rid] for rid in members)
        true_positive += sum(_choose2(count) for count in counts.values())
        purity_hits += max(counts.values()) if counts else 0
        if len(counts) > 1:
            merge_count += 1

    precision = true_positive / pred_pairs if pred_pairs else 0.0
    recall = true_positive / truth_pairs if truth_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    purity = purity_hits / len(request_ids) if request_ids else 0.0

    true_to_pred: dict[str, set[str]] = defaultdict(set)
    for rid in request_ids:
        true_to_pred[truth[rid]].add(pred[rid])
    split_rate = sum(1 for labels in true_to_pred.values() if len(labels) > 1) / len(true_to_pred) if true_to_pred else 0.0
    merge_rate = merge_count / len(pred_clusters) if pred_clusters else 0.0

    return {
        "pairwise_precision": precision,
        "pairwise_recall": recall,
        "pairwise_f1": f1,
        "purity": purity,
        "split_rate": split_rate,
        "merge_rate": merge_rate,
        "clusters": float(len(pred_clusters)),
        "items": float(len(request_ids)),
    }


def cross_workflow_clustering_metrics(
    pred: dict[str, str],
    truth: dict[str, str],
    workflows: dict[str, str],
) -> dict[str, float]:
    """Evaluate only request pairs drawn from different workflows."""

    request_ids = sorted(set(pred) & set(truth) & set(workflows))
    pred_counts = Counter(pred[rid] for rid in request_ids)
    truth_counts = Counter(truth[rid] for rid in request_ids)
    joint_counts = Counter((pred[rid], truth[rid]) for rid in request_ids)
    pred_workflow_counts = Counter((pred[rid], workflows[rid]) for rid in request_ids)
    truth_workflow_counts = Counter((truth[rid], workflows[rid]) for rid in request_ids)
    joint_workflow_counts = Counter(
        (pred[rid], truth[rid], workflows[rid]) for rid in request_ids
    )

    pred_pairs = sum(_choose2(count) for count in pred_counts.values()) - sum(
        _choose2(count) for count in pred_workflow_counts.values()
    )
    truth_pairs = sum(_choose2(count) for count in truth_counts.values()) - sum(
        _choose2(count) for count in truth_workflow_counts.values()
    )
    true_positive = sum(_choose2(count) for count in joint_counts.values()) - sum(
        _choose2(count) for count in joint_workflow_counts.values()
    )

    precision = true_positive / pred_pairs if pred_pairs else 0.0
    recall = true_positive / truth_pairs if truth_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "cross_workflow_precision": precision,
        "cross_workflow_recall": recall,
        "cross_workflow_f1": f1,
        "cross_workflow_true_positive_pairs": float(true_positive),
        "cross_workflow_predicted_positive_pairs": float(pred_pairs),
        "cross_workflow_truth_positive_pairs": float(truth_pairs),
        "cross_workflow_false_positive_pairs": float(pred_pairs - true_positive),
        "cross_workflow_false_negative_pairs": float(truth_pairs - true_positive),
        "items": float(len(request_ids)),
    }


def evaluate_all(
    predictions: dict[str, dict[str, dict[str, str]]],
    truth_rows: list[dict[str, Any]],
    levels: list[str] | None = None,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    allowed_levels = set(levels) if levels else None
    for method, level_predictions in predictions.items():
        for level, labels in level_predictions.items():
            if allowed_levels is not None and level not in allowed_levels:
                continue
            truth = truth_labels(truth_rows, level)
            if not truth:
                continue
            metrics = clustering_metrics(labels, truth)
            rows.append({"method": method, "level": level, **metrics})
    return rows


def _clusters(labels: dict[str, str]) -> dict[str, list[str]]:
    clusters: dict[str, list[str]] = defaultdict(list)
    for request_id, label in labels.items():
        clusters[label].append(request_id)
    return dict(clusters)


def _choose2(value: int) -> int:
    return comb(value, 2) if value >= 2 else 0


def _missing_label(value: Any) -> bool:
    return value is None or value == "" or str(value).lower() in {"none", "null", "unknown", "n/a"}
