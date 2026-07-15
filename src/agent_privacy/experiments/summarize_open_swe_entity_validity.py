from __future__ import annotations

import argparse
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.attacks.cluster import connect_by_bucket, inverted_index
from agent_privacy.evaluation.clustering import (
    clustering_metrics,
    cross_workflow_clustering_metrics,
    truth_labels,
)
from agent_privacy.features.extract import request_text
from agent_privacy.experiments.bootstrap_ci import _weighted_pairwise_metrics
from agent_privacy.io import iter_jsonl, read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_snapshots/first_12000_requests")
DEFAULT_PREDICTIONS = Path(
    "results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns/"
    "M0/feature_no_semantic/predictions.json"
)
DEFAULT_HYBRID_PREDICTIONS = Path(
    "results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast/M0/predictions.json"
)
DEFAULT_DEVELOPMENT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_sample100")
REPOSITORY_FIELD_RE = re.compile(r"\brepository=([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+)\b")
WORKSPACE_RE = re.compile(r"/workspace/([A-Za-z0-9_.-]+)")


def summarize_entity_validity(
    *,
    dataset_dir: Path,
    predictions_path: Path,
    hybrid_predictions_path: Path = DEFAULT_HYBRID_PREDICTIONS,
    development_dataset_dir: Path = DEFAULT_DEVELOPMENT_DATASET,
    iterations: int = 200,
    seed: int = 7,
) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))["provider_lowcost"]
    hybrid_predictions = json.loads(hybrid_predictions_path.read_text(encoding="utf-8"))["hybrid"]
    development_workflows = {
        str(row["workflow_id"])
        for row in read_jsonl(development_dataset_dir / "ground_truth.jsonl")
    }
    selected_ids = set(predictions["project"])
    selected_truth = [
        row
        for row in truth_rows
        if row["request_id"] in selected_ids
        and str(row["workflow_id"]) not in development_workflows
    ]
    selected_ids = {row["request_id"] for row in selected_truth}
    workflows = {row["request_id"]: str(row["workflow_id"]) for row in selected_truth}

    anchors = _read_direct_anchors(dataset_dir / "attack_view.jsonl", selected_ids)
    direct_predictions = _direct_anchor_predictions(anchors)
    workflow_members: dict[str, list[str]] = defaultdict(list)
    for request_id, workflow_id in workflows.items():
        workflow_members[workflow_id].append(request_id)
    workflow_ids = sorted(workflow_members)

    rows: list[dict[str, Any]] = []
    for method, level_predictions, levels in (
        ("carp", predictions, ("session", "project", "org")),
        ("hybrid", hybrid_predictions, ("session", "project", "org")),
        ("direct_workspace_anchor", direct_predictions, ("project", "org")),
    ):
        for level in levels:
            truth = truth_labels(selected_truth, level)
            labels = level_predictions[level]
            standard = clustering_metrics(labels, truth)
            rng = random.Random(seed + len(rows))
            pairwise_samples = []
            cross_samples = []
            request_to_workflow = workflows
            for _ in range(iterations):
                weights = Counter(rng.choices(workflow_ids, k=len(workflow_ids)))
                pairwise_samples.append(
                    _weighted_pairwise_metrics(
                        labels,
                        truth,
                        request_to_workflow,
                        weights,
                    )["pairwise_f1"]
                )
                if level != "session":
                    cross_samples.append(
                        _weighted_cross_workflow_f1(labels, truth, workflows, weights)
                    )
            entity_workflows: dict[str, set[str]] = {}
            field = {
                "session": "workflow_id",
                "project": "project_id",
                "org": "org_id",
            }[level]
            for row in selected_truth:
                entity_workflows.setdefault(str(row[field]), set()).add(str(row["workflow_id"]))
            item: dict[str, Any] = {
                "method": method,
                "level": level,
                "requests": len(selected_ids),
                "development_workflows": len(development_workflows),
                "workflows": len(set(workflows.values())),
                "entities": len(entity_workflows),
                "multi_workflow_entities": sum(
                    len(entity_workflow_ids) > 1
                    for entity_workflow_ids in entity_workflows.values()
                ),
                "pairwise_precision": standard["pairwise_precision"],
                "pairwise_recall": standard["pairwise_recall"],
                "pairwise_f1": standard["pairwise_f1"],
                "pairwise_f1_ci_low": _quantile(pairwise_samples, 0.025),
                "pairwise_f1_ci_high": _quantile(pairwise_samples, 0.975),
                "bootstrap_iterations": iterations,
            }
            if level == "session":
                item["anchor_request_coverage"] = ""
            else:
                anchor_prefix = "repo_full:" if level == "project" else "repo_owner:"
                evidence_requests = sum(
                    any(value.startswith(anchor_prefix) for value in anchors[rid])
                    for rid in selected_ids
                )
                cross = cross_workflow_clustering_metrics(labels, truth, workflows)
                item["anchor_request_coverage"] = evidence_requests / len(selected_ids)
                item.update({key: value for key, value in cross.items() if key != "items"})
                item["cross_workflow_f1_ci_low"] = _quantile(cross_samples, 0.025)
                item["cross_workflow_f1_ci_high"] = _quantile(cross_samples, 0.975)
            rows.append(item)
    return rows


def _read_direct_anchors(path: Path, request_ids: set[str]) -> dict[str, set[str]]:
    anchors = {request_id: set() for request_id in request_ids}
    for row in iter_jsonl(path):
        request_id = str(row.get("request_id"))
        if request_id not in anchors:
            continue
        text = request_text(row).lower()
        for owner, repo in REPOSITORY_FIELD_RE.findall(text):
            anchors[request_id].update(
                {f"repo_owner:{owner}", f"repo_full:{owner}/{repo}"}
            )
        for slug in WORKSPACE_RE.findall(text):
            if "__" not in slug:
                continue
            parts = slug.split("__")
            if len(parts) < 2 or not parts[0] or not parts[1]:
                continue
            owner, repo = parts[0], parts[1]
            anchors[request_id].update(
                {f"repo_owner:{owner}", f"repo_full:{owner}/{repo}"}
            )
    return anchors


def _direct_anchor_predictions(anchors: dict[str, set[str]]) -> dict[str, dict[str, str]]:
    request_ids = list(anchors)
    project_buckets = inverted_index(
        {
            rid: {value for value in values if value.startswith("repo_full:")}
            for rid, values in anchors.items()
        }
    )
    org_buckets = inverted_index(
        {
            rid: {value for value in values if value.startswith("repo_owner:")}
            for rid, values in anchors.items()
        }
    )
    return {
        "project": connect_by_bucket(request_ids, project_buckets, len(request_ids)).labels(
            "direct_project"
        ),
        "org": connect_by_bucket(request_ids, org_buckets, len(request_ids)).labels("direct_org"),
    }


def _weighted_cross_workflow_f1(
    pred: dict[str, str],
    truth: dict[str, str],
    workflows: dict[str, str],
    workflow_weights: dict[str, int],
) -> float:
    pred_counts: Counter[str] = Counter()
    truth_counts: Counter[str] = Counter()
    joint_counts: Counter[tuple[str, str]] = Counter()
    pred_within: Counter[tuple[str, str]] = Counter()
    truth_within: Counter[tuple[str, str]] = Counter()
    joint_within: Counter[tuple[str, str, str]] = Counter()
    for request_id in set(pred) & set(truth) & set(workflows):
        workflow_id = workflows[request_id]
        weight = workflow_weights.get(workflow_id, 0)
        if weight <= 0:
            continue
        pred_label = pred[request_id]
        truth_label = truth[request_id]
        pred_counts[pred_label] += weight
        truth_counts[truth_label] += weight
        joint_counts[(pred_label, truth_label)] += weight
        pred_within[(workflow_id, pred_label)] += weight
        truth_within[(workflow_id, truth_label)] += weight
        joint_within[(workflow_id, pred_label, truth_label)] += weight
    pred_pairs = sum(_choose2(count) for count in pred_counts.values()) - sum(
        _choose2(count) for count in pred_within.values()
    )
    truth_pairs = sum(_choose2(count) for count in truth_counts.values()) - sum(
        _choose2(count) for count in truth_within.values()
    )
    true_positive = sum(_choose2(count) for count in joint_counts.values()) - sum(
        _choose2(count) for count in joint_within.values()
    )
    precision = true_positive / pred_pairs if pred_pairs else 0.0
    recall = true_positive / truth_pairs if truth_pairs else 0.0
    return 2 * precision * recall / (precision + recall) if precision + recall else 0.0


def _choose2(value: int) -> int:
    return value * (value - 1) // 2 if value >= 2 else 0


def _quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "method",
        "level",
        "requests",
        "development_workflows",
        "workflows",
        "entities",
        "multi_workflow_entities",
        "anchor_request_coverage",
        "pairwise_f1",
        "pairwise_f1_ci_low",
        "pairwise_f1_ci_high",
        "cross_workflow_precision",
        "cross_workflow_recall",
        "cross_workflow_f1",
        "cross_workflow_f1_ci_low",
        "cross_workflow_f1_ci_high",
        "cross_workflow_truth_positive_pairs",
        "cross_workflow_false_positive_pairs",
        "cross_workflow_false_negative_pairs",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = []
        for header in headers:
            value = row.get(header, "")
            cells.append(f"{value:.3f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(cells) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Audit Open-SWE entity linkage with cross-workflow-only pairs."
    )
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument(
        "--hybrid-predictions", type=Path, default=DEFAULT_HYBRID_PREDICTIONS
    )
    parser.add_argument(
        "--development-dataset-dir", type=Path, default=DEFAULT_DEVELOPMENT_DATASET
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    rows = summarize_entity_validity(
        dataset_dir=args.dataset_dir,
        predictions_path=args.predictions,
        hybrid_predictions_path=args.hybrid_predictions,
        development_dataset_dir=args.development_dataset_dir,
        iterations=args.iterations,
        seed=args.seed,
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = args.output_dir / "open_swe_cross_workflow_entity_validity.csv"
    md_path = args.output_dir / "open_swe_cross_workflow_entity_validity.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    print({"rows": len(rows), "output": str(md_path)})


if __name__ == "__main__":
    main()
