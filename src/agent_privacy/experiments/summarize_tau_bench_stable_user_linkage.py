from __future__ import annotations

import argparse
import random
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.attacks.cluster import UnionFind
from agent_privacy.attacks.pipeline import run_attacks_from_features
from agent_privacy.evaluation.clustering import (
    clustering_metrics,
    cross_workflow_clustering_metrics,
    truth_labels,
)
from agent_privacy.experiments.bootstrap_ci import _quantile, _weighted_pairwise_metrics
from agent_privacy.experiments.summarize_tau_bench_historical_evidence import _split_rows
from agent_privacy.features.extract import (
    extract_features_from_jsonl,
    extract_stable_content_handles,
)
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "tau_bench_stable_user_linkage"


def summarize_stable_user_linkage(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    seed: int = 7,
    bootstrap_iterations: int = 500,
) -> dict[str, str]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    attack_rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    _, test_truth = _split_rows(truth_rows, seed=seed)
    test_ids = {str(row["request_id"]) for row in test_truth}
    test_attacks = [row for row in attack_rows if str(row["request_id"]) in test_ids]
    features = extract_features_from_jsonl(
        dataset_dir / "attack_view.jsonl",
        request_ids=test_ids,
    )
    provider_labels = run_attacks_from_features(
        features,
        methods=["provider_lowcost"],
    )["provider_lowcost"]["user"]
    handles = {
        str(row["request_id"]): {
            value
            for value in extract_stable_content_handles(row)
            if value.startswith("stable_user:")
        }
        for row in test_attacks
    }
    predictions = {
        "stable_handle_pipeline": provider_labels,
        "user_id_only": _labels_from_handles(
            handles,
            kinds={"user", "username"},
            prefix="uid",
        ),
        "email_only": _labels_from_handles(handles, kinds={"email"}, prefix="email"),
        "no_stable_handle": {
            request_id: f"singleton:{request_id}" for request_id in sorted(test_ids)
        },
    }
    rows = [
        _result_row(
            method=method,
            labels=labels,
            truth_rows=test_truth,
            handles=handles,
            seed=seed,
            bootstrap_iterations=bootstrap_iterations,
        )
        for method, labels in predictions.items()
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _labels_from_handles(
    handles: dict[str, set[str]],
    *,
    kinds: set[str],
    prefix: str,
) -> dict[str, str]:
    request_ids = sorted(handles)
    union_find = UnionFind(request_ids)
    requests_by_handle: dict[str, list[str]] = defaultdict(list)
    for request_id, values in handles.items():
        for value in values:
            parts = value.split(":", 2)
            if len(parts) == 3 and parts[1] in kinds:
                requests_by_handle[value].append(request_id)
    for members in requests_by_handle.values():
        for request_id in members[1:]:
            union_find.union(members[0], request_id)
    return union_find.labels(prefix)


def _result_row(
    *,
    method: str,
    labels: dict[str, str],
    truth_rows: list[dict[str, Any]],
    handles: dict[str, set[str]],
    seed: int,
    bootstrap_iterations: int,
) -> dict[str, Any]:
    truth = truth_labels(truth_rows, "user")
    workflows = {
        str(row["request_id"]): str(row["workflow_id"]) for row in truth_rows
    }
    metrics = clustering_metrics(labels, truth)
    cross = cross_workflow_clustering_metrics(labels, truth, workflows)
    workflow_members: dict[str, list[str]] = defaultdict(list)
    for request_id, workflow in workflows.items():
        workflow_members[workflow].append(request_id)
    request_to_workflow = {
        request_id: workflow
        for workflow, members in workflow_members.items()
        for request_id in members
    }
    workflow_ids = sorted(workflow_members)
    rng = random.Random(seed)
    samples = []
    for _ in range(bootstrap_iterations):
        weights: dict[str, int] = defaultdict(int)
        for _draw in workflow_ids:
            weights[rng.choice(workflow_ids)] += 1
        samples.append(
            _weighted_pairwise_metrics(
                labels,
                truth,
                request_to_workflow,
                weights,
            )["pairwise_f1"]
        )
    covered = sum(bool(handles.get(request_id)) for request_id in truth)
    return {
        "method": method,
        "workflows": len(workflow_ids),
        "requests": len(truth),
        "users": len(set(truth.values())),
        "stable_handle_request_coverage": covered / len(truth) if truth else 0.0,
        "precision": metrics["pairwise_precision"],
        "recall": metrics["pairwise_recall"],
        "f1": metrics["pairwise_f1"],
        "f1_ci_low": _quantile(samples, 0.025),
        "f1_ci_high": _quantile(samples, 0.975),
        "cross_workflow_precision": cross["cross_workflow_precision"],
        "cross_workflow_recall": cross["cross_workflow_recall"],
        "cross_workflow_f1": cross["cross_workflow_f1"],
        "purity": metrics["purity"],
        "split_rate": metrics["split_rate"],
        "merge_rate": metrics["merge_rate"],
    }


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = list(rows[0]) if rows else []
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append(
            "| "
            + " | ".join(
                f"{row[header]:.3f}" if isinstance(row[header], float) else str(row[header])
                for header in headers
            )
            + " |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--bootstrap-iterations", type=int, default=500)
    args = parser.parse_args()
    print(
        summarize_stable_user_linkage(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            seed=args.seed,
            bootstrap_iterations=args.bootstrap_iterations,
        )
    )


if __name__ == "__main__":
    main()
