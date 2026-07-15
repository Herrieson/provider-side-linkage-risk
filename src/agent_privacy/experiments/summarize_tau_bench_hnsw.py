from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.experiments.semantic_linkage import (
    encode_documents,
    hnsw_cosine_pairs,
    labels_from_scores,
    top_k_cosine_pairs,
    write_markdown,
)
from agent_privacy.experiments.summarize_tau_bench_historical_evidence import _split_rows
from agent_privacy.experiments.summarize_tau_bench_temporal_stress import _semantic_document
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "tau_bench_hnsw_ann_baseline"
TOP_K = 24
LINK_THRESHOLD = 0.98


def summarize_hnsw(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    _, test_truth = _split_rows(truth_rows, seed=7)
    test_ids = {str(row["request_id"]) for row in test_truth}
    attack_rows = [
        row
        for row in read_jsonl(dataset_dir / "attack_view.jsonl")
        if str(row["request_id"]) in test_ids
    ]
    documents = {str(row["request_id"]): _semantic_document(row) for row in attack_rows}
    request_ids, vectors = encode_documents(documents)
    truth_pairs = _truth_pairs(test_truth)
    rows: list[dict[str, Any]] = []

    exact_pairs = top_k_cosine_pairs(request_ids, vectors, top_k=TOP_K)
    rows.append(
        _result_row(
            method="exact_dense_topk",
            request_ids=request_ids,
            pair_scores=exact_pairs,
            truth_pairs=truth_pairs,
            test_truth=test_truth,
            stats={
                "build_seconds": 0.0,
                "query_seconds": 0.0,
                "index_bytes": int(vectors.nbytes),
                "ef_search": "exact",
                "ef_construction": "exact",
                "max_connections": "exact",
                "top_k": TOP_K,
            },
            exact_pairs=exact_pairs,
        )
    )
    for ef_search in (16, 64, 200):
        pairs, stats = hnsw_cosine_pairs(
            request_ids,
            vectors,
            top_k=TOP_K,
            ef_search=ef_search,
        )
        rows.append(
            _result_row(
                method=f"hnsw_ef{ef_search}",
                request_ids=request_ids,
                pair_scores=pairs,
                truth_pairs=truth_pairs,
                test_truth=test_truth,
                stats=stats,
                exact_pairs=exact_pairs,
            )
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _result_row(
    *,
    method: str,
    request_ids: list[str],
    pair_scores: dict[tuple[str, str], float],
    truth_pairs: set[tuple[str, str]],
    test_truth: list[dict[str, Any]],
    stats: dict[str, float | int | str],
    exact_pairs: dict[tuple[str, str], float],
) -> dict[str, Any]:
    true_candidates = len(set(pair_scores) & truth_pairs)
    predictions = labels_from_scores(
        request_ids,
        pair_scores,
        threshold=LINK_THRESHOLD,
        prefix=method,
    )
    metrics = clustering_metrics(predictions, truth_labels(test_truth, "session"))
    exact_overlap = len(set(pair_scores) & set(exact_pairs))
    return {
        "method": method,
        "requests": len(request_ids),
        "candidate_pairs": len(pair_scores),
        "truth_session_pairs": len(truth_pairs),
        "candidate_recall": true_candidates / len(truth_pairs),
        "candidate_precision": true_candidates / len(pair_scores),
        "exact_topk_pair_recall": exact_overlap / len(exact_pairs),
        "session_precision": metrics["pairwise_precision"],
        "session_recall": metrics["pairwise_recall"],
        "session_f1": metrics["pairwise_f1"],
        "purity": metrics["purity"],
        "clusters": int(metrics["clusters"]),
        "link_threshold": LINK_THRESHOLD,
        "top_k": stats["top_k"],
        "ef_search": stats["ef_search"],
        "ef_construction": stats["ef_construction"],
        "max_connections": stats["max_connections"],
        "build_seconds": stats["build_seconds"],
        "query_seconds": stats["query_seconds"],
        "index_bytes": stats["index_bytes"],
    }


def _truth_pairs(truth_rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    by_workflow: dict[str, list[str]] = defaultdict(list)
    for row in truth_rows:
        by_workflow[str(row["workflow_id"])].append(str(row["request_id"]))
    pairs = set()
    for members in by_workflow.values():
        ordered = sorted(members)
        for index, left in enumerate(ordered):
            for right in ordered[index + 1 :]:
                pairs.add((left, right))
    return pairs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(summarize_hnsw(dataset_dir=args.dataset_dir, output_dir=args.output_dir))


if __name__ == "__main__":
    main()
