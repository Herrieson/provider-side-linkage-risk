from __future__ import annotations

import argparse
import csv
import json
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
from scipy.sparse import csr_matrix
from sklearn.feature_extraction.text import HashingVectorizer

from agent_privacy.attacks.cluster import UnionFind
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.evaluation.selective import false_merge_amplification
from agent_privacy.features.extract import request_text
from agent_privacy.io import iter_jsonl, read_jsonl


def run_generic_text_baseline(
    dataset_dir: Path,
    *,
    active_window_seconds: int = 90 * 60,
    similarity_threshold: float = 0.72,
    min_margin: float = 0.04,
    max_active_requests: int = 2048,
) -> dict[str, Any]:
    vectorizer = HashingVectorizer(
        n_features=2**15,
        alternate_sign=False,
        norm="l2",
        ngram_range=(1, 2),
        stop_words="english",
    )
    rows = list(iter_jsonl(dataset_dir / "attack_view.jsonl"))
    request_ids = [str(row["request_id"]) for row in rows]
    uf = UnionFind(request_ids)
    active: deque[tuple[str, int, csr_matrix]] = deque()
    accepted = 0
    abstained = 0
    comparisons = 0
    peak_active = 0
    for row in rows:
        request_id = str(row["request_id"])
        timestamp = _timestamp(str(row["timestamp"]))
        while active and timestamp - active[0][1] > active_window_seconds:
            active.popleft()
        while len(active) >= max_active_requests:
            active.popleft()
        vector = vectorizer.transform([request_text(row)]).tocsr()
        scored: list[tuple[float, str]] = []
        for candidate_id, _candidate_time, candidate_vector in active:
            similarity = float((vector @ candidate_vector.T).toarray()[0, 0])
            scored.append((similarity, candidate_id))
        comparisons += len(scored)
        scored.sort(reverse=True)
        best_score, best_id = scored[0] if scored else (0.0, "")
        runner_up = scored[1][0] if len(scored) > 1 else 0.0
        if best_id and best_score >= similarity_threshold and best_score - runner_up >= min_margin:
            uf.union(best_id, request_id)
            accepted += 1
        else:
            abstained += 1
        active.append((request_id, timestamp, vector))
        peak_active = max(peak_active, len(active))
    pred = uf.labels("txt")
    truth = truth_labels(read_jsonl(dataset_dir / "ground_truth.jsonl"), "session")
    metrics = clustering_metrics(pred, truth)
    metrics.update(false_merge_amplification(pred, truth))
    metrics.update(
        {
            "accepted_edges": float(accepted),
            "abstention_rate": abstained / len(rows) if rows else 0.0,
        }
    )
    return {
        "dataset": dataset_dir.name,
        "method": "generic_hashed_text_nearest_neighbor",
        "metrics": metrics,
        "requests": len(rows),
        "comparisons": comparisons,
        "comparisons_per_request": comparisons / len(rows) if rows else 0.0,
        "peak_active_requests": peak_active,
        "max_active_requests": max_active_requests,
        "hash_dimensions": int(np.prod(vector.shape)) if rows else 2**15,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a generic non-Agent text-linkage baseline.")
    parser.add_argument("--dataset-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-base", type=Path, required=True)
    args = parser.parse_args()
    reports = [run_generic_text_baseline(path) for path in args.dataset_dir]
    args.output_base.parent.mkdir(parents=True, exist_ok=True)
    with args.output_base.with_suffix(".json").open("w", encoding="utf-8") as handle:
        json.dump(reports, handle, indent=2, sort_keys=True)
        handle.write("\n")
    fields = [
        "dataset",
        "pairwise_precision",
        "pairwise_recall",
        "pairwise_f1",
        "abstention_rate",
        "contaminated_requests",
        "comparisons_per_request",
        "peak_active_requests",
    ]
    with args.output_base.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for report in reports:
            writer.writerow(
                {
                    "dataset": report["dataset"],
                    **{field: report["metrics"][field] for field in fields[1:6]},
                    "comparisons_per_request": report["comparisons_per_request"],
                    "peak_active_requests": report["peak_active_requests"],
                }
            )
    print(json.dumps(reports, indent=2, sort_keys=True))


def _timestamp(value: str) -> int:
    return int(datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp())


if __name__ == "__main__":
    main()
