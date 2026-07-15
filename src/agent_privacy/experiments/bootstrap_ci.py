from __future__ import annotations

import argparse
import json
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


def bootstrap_clustering_ci(
    *,
    dataset_dir: Path,
    predictions_path: Path,
    output: Path,
    methods: list[str] | None = None,
    levels: list[str] | None = None,
    unit_level: str = "session",
    iterations: int = 200,
    seed: int = 7,
    turn_ids: list[int] | None = None,
) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    if turn_ids:
        allowed_turns = set(turn_ids)
        truth_rows = [row for row in truth_rows if int(row.get("turn_id", -1)) in allowed_turns]
    predictions = _read_predictions(predictions_path)
    selected_methods = methods or sorted(predictions)
    selected_levels = levels or ["session", "project", "org"]
    units = _bootstrap_units(truth_rows, unit_level)
    rng = random.Random(seed)
    rows: list[dict[str, Any]] = []
    for method in selected_methods:
        if method not in predictions:
            continue
        for level in selected_levels:
            pred = predictions[method].get(level)
            if not pred:
                continue
            truth = truth_labels(truth_rows, level)
            observed = clustering_metrics(pred, truth)
            f1_samples: list[float] = []
            precision_samples: list[float] = []
            recall_samples: list[float] = []
            request_to_unit = {
                request_id: unit_id for unit_id, members in units.items() for request_id in members
            }
            unit_keys = sorted(units)
            for _ in range(iterations):
                weights: dict[str, int] = defaultdict(int)
                for _draw in unit_keys:
                    weights[rng.choice(unit_keys)] += 1
                metric = _weighted_pairwise_metrics(pred, truth, request_to_unit, weights)
                f1_samples.append(metric["pairwise_f1"])
                precision_samples.append(metric["pairwise_precision"])
                recall_samples.append(metric["pairwise_recall"])
            rows.append(
                {
                    "method": method,
                    "level": level,
                    "unit_level": unit_level,
                    "iterations": iterations,
                    "observed_precision": observed["pairwise_precision"],
                    "observed_recall": observed["pairwise_recall"],
                    "observed_f1": observed["pairwise_f1"],
                    "precision_mean": _mean(precision_samples),
                    "precision_ci_low": _quantile(precision_samples, 0.025),
                    "precision_ci_high": _quantile(precision_samples, 0.975),
                    "recall_mean": _mean(recall_samples),
                    "recall_ci_low": _quantile(recall_samples, 0.025),
                    "recall_ci_high": _quantile(recall_samples, 0.975),
                    "f1_mean": _mean(f1_samples),
                    "f1_ci_low": _quantile(f1_samples, 0.025),
                    "f1_ci_high": _quantile(f1_samples, 0.975),
                    "units": len(units),
                    "requests": sum(len(members) for members in units.values()),
                }
            )
    write_csv(output, rows)
    _write_markdown(output.with_suffix(".md"), rows)
    return rows


def _read_predictions(path: Path) -> dict[str, dict[str, dict[str, str]]]:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def _bootstrap_units(truth_rows: list[dict[str, Any]], unit_level: str) -> dict[str, list[str]]:
    field = {
        "session": "workflow_id",
        "project": "project_id",
        "org": "org_id",
        "request": "request_id",
    }[unit_level]
    units: dict[str, list[str]] = defaultdict(list)
    for row in truth_rows:
        value = row.get(field)
        if value is None or str(value).lower() in {"", "none", "null", "unknown", "n/a"}:
            continue
        units[str(value)].append(row["request_id"])
    return dict(units)


def _weighted_pairwise_metrics(
    pred: dict[str, str],
    truth: dict[str, str],
    request_to_unit: dict[str, str],
    unit_weights: dict[str, int],
) -> dict[str, float]:
    pred_counts: dict[str, float] = defaultdict(float)
    truth_counts: dict[str, float] = defaultdict(float)
    joint_counts: dict[tuple[str, str], float] = defaultdict(float)
    unit_pred_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unit_truth_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    unit_joint_counts: dict[str, dict[tuple[str, str], int]] = defaultdict(
        lambda: defaultdict(int)
    )
    self_duplicate_pairs = 0.0
    for request_id in sorted(set(pred) & set(truth)):
        unit_id = request_to_unit.get(request_id, "")
        weight = unit_weights.get(unit_id, 0)
        if weight <= 0:
            continue
        pred_label = pred[request_id]
        truth_label = truth[request_id]
        pred_counts[pred_label] += weight
        truth_counts[truth_label] += weight
        joint_counts[(pred_label, truth_label)] += weight
        unit_pred_counts[unit_id][pred_label] += 1
        unit_truth_counts[unit_id][truth_label] += 1
        unit_joint_counts[unit_id][(pred_label, truth_label)] += 1
        self_duplicate_pairs += _choose_two(weight)

    pred_pairs = sum(_choose_two(count) for count in pred_counts.values())
    truth_pairs = sum(_choose_two(count) for count in truth_counts.values())
    true_positive = sum(_choose_two(count) for count in joint_counts.values())
    pred_pairs -= self_duplicate_pairs
    truth_pairs -= self_duplicate_pairs
    true_positive -= self_duplicate_pairs
    for unit_id in unit_pred_counts:
        weight = unit_weights.get(unit_id, 0)
        same_unit_overcount = weight * weight - weight
        if same_unit_overcount <= 0:
            continue
        pred_pairs -= same_unit_overcount * sum(
            _choose_two(count) for count in unit_pred_counts[unit_id].values()
        )
        truth_pairs -= same_unit_overcount * sum(
            _choose_two(count) for count in unit_truth_counts[unit_id].values()
        )
        true_positive -= same_unit_overcount * sum(
            _choose_two(count) for count in unit_joint_counts[unit_id].values()
        )
    precision = true_positive / pred_pairs if pred_pairs else 0.0
    recall = true_positive / truth_pairs if truth_pairs else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {
        "pairwise_precision": precision,
        "pairwise_recall": recall,
        "pairwise_f1": f1,
    }


def _choose_two(count: float) -> float:
    return count * (count - 1) / 2


def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _quantile(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = [
        "method",
        "level",
        "observed_f1",
        "f1_mean",
        "f1_ci_low",
        "f1_ci_high",
        "units",
        "requests",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header)) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Bootstrap clustering confidence intervals.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--methods", nargs="*")
    parser.add_argument("--levels", nargs="*")
    parser.add_argument("--unit-level", choices=["session", "project", "org", "request"], default="session")
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--turn-ids", type=int, nargs="*")
    args = parser.parse_args()
    bootstrap_clustering_ci(
        dataset_dir=args.dataset_dir,
        predictions_path=args.predictions,
        output=args.output,
        methods=args.methods,
        levels=args.levels,
        unit_level=args.unit_level,
        iterations=args.iterations,
        seed=args.seed,
        turn_ids=args.turn_ids,
    )


if __name__ == "__main__":
    main()
