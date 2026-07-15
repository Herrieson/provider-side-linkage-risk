from __future__ import annotations

import argparse
import multiprocessing
import resource
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.attacks.cluster import inverted_index
from agent_privacy.attacks.pipeline import (
    LOWCOST_MAX_PAIRS_PER_REQUEST,
    LOWCOST_SHINGLE_BUCKET_SIZE,
    _iter_bounded_candidate_pairs,
    run_provider_lowcost_from_features_with_stats,
)
from agent_privacy.evaluation.clustering import clustering_metrics
from agent_privacy.experiments.semantic_linkage import write_markdown
from agent_privacy.features.extract import RequestFeatures
from agent_privacy.reporting import write_csv


DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "carp_synthetic_scale"


def summarize_scale(
    *,
    sizes: tuple[int, ...] = (10_000, 50_000, 100_000),
    conditions: tuple[str, ...] = ("clean", "shared_alias_collision"),
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    tasks = [(size, condition) for condition in conditions for size in sizes]
    context = multiprocessing.get_context("spawn")
    with context.Pool(processes=1, maxtasksperchild=1) as pool:
        rows = pool.map(_run_size_task, tasks, chunksize=1)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


def _run_size_task(task: tuple[int, str]) -> dict[str, Any]:
    size, condition = task
    return _run_size(size, condition=condition)


def _run_size(requests: int, *, condition: str) -> dict[str, Any]:
    if requests % 4:
        raise ValueError("scale sizes must be divisible by four requests per workflow")
    feature_start = time.perf_counter()
    features, truth = _synthetic_features(requests, condition=condition)
    feature_seconds = time.perf_counter() - feature_start
    candidate_start = time.perf_counter()
    candidate_stats = _context_candidate_recall(features, truth["session"])
    candidate_seconds = time.perf_counter() - candidate_start
    predictions, stats = run_provider_lowcost_from_features_with_stats(features)
    session_metrics = clustering_metrics(predictions["session"], truth["session"])
    user_metrics = clustering_metrics(predictions["user"], truth["user"])
    project_metrics = clustering_metrics(predictions["project"], truth["project"])
    org_metrics = clustering_metrics(predictions["org"], truth["org"])
    pair_events = int(stats["candidate_pairs_considered"])
    all_pairs = requests * (requests - 1) // 2
    return {
        "condition": condition,
        "requests": requests,
        "workflows": requests // 4,
        "cache_buckets": stats["cache_bucket_count"],
        "max_cache_bucket_requests": stats["max_cache_bucket_requests"],
        "context_candidate_pairs": candidate_stats["candidate_pairs"],
        "context_candidate_recall": candidate_stats["candidate_recall"],
        "context_candidate_precision": candidate_stats["candidate_precision"],
        "pair_comparison_events": pair_events,
        "comparisons_per_request": pair_events / requests,
        "all_pairs": all_pairs,
        "all_pairs_reduction": all_pairs / pair_events if pair_events else 0.0,
        "session_precision": session_metrics["pairwise_precision"],
        "session_recall": session_metrics["pairwise_recall"],
        "session_f1": session_metrics["pairwise_f1"],
        "user_f1": user_metrics["pairwise_f1"],
        "project_f1": project_metrics["pairwise_f1"],
        "org_f1": org_metrics["pairwise_f1"],
        "feature_generation_seconds": feature_seconds,
        "candidate_diagnostic_seconds": candidate_seconds,
        "linkage_seconds": stats["linkage_seconds"],
        "requests_per_second": requests / stats["linkage_seconds"],
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }


def _synthetic_features(
    requests: int,
    *,
    condition: str = "clean",
) -> tuple[dict[str, RequestFeatures], dict[str, dict[str, str]]]:
    if condition not in {"clean", "shared_alias_collision"}:
        raise ValueError(f"unknown scale condition: {condition}")
    features: dict[str, RequestFeatures] = {}
    truth = {level: {} for level in ("session", "user", "project", "org")}
    workflows = requests // 4
    for workflow in range(workflows):
        user = workflow // 5
        project = workflow // 10
        org = project // 20
        cache = workflow // 50
        collision_member = condition == "shared_alias_collision" and workflow % 20 in {18, 19}
        anchor_id = f"collision-{workflow // 20}" if collision_member else f"workflow-{workflow}"
        shared_shingles = {f"{anchor_id}-shared-{index}" for index in range(12)}
        for turn in range(4):
            request_id = f"scale-{workflow:07d}-{turn}"
            shingles = shared_shingles | {
                f"workflow-{workflow}-turn-{prior}-{index}"
                for prior in range(turn + 1)
                for index in range(5)
            }
            identifiers = frozenset(
                {
                    f"repo_full:org-{org}/project-{project}",
                    f"service.{anchor_id}.internal",
                    f"business_user:customer_ref:user-{user}",
                    f"business_project:project_ref:project-{project}",
                    f"business_org:tenant:org-{org}",
                }
            )
            features[request_id] = RequestFeatures(
                request_id=request_id,
                timestamp_minute=workflow * 10 + turn,
                token_count=200 + turn * 40,
                words=frozenset(),
                shingles=frozenset(shingles),
                identifiers=identifiers,
                paths=frozenset(),
                usernames=frozenset(),
                domains=frozenset(),
                traces=frozenset(),
                cache_bucket=f"cache-{cache:06d}",
                semantic_signatures=frozenset(),
                tool_fingerprint=f"tool-{workflow % 8}",
                system_fingerprint="scale-system",
            )
            truth["session"][request_id] = f"workflow-{workflow}"
            truth["user"][request_id] = f"user-{user}"
            truth["project"][request_id] = f"project-{project}"
            truth["org"][request_id] = f"org-{org}"
    return features, truth


def _context_candidate_recall(
    features: dict[str, RequestFeatures], truth: dict[str, str]
) -> dict[str, float | int]:
    cache_groups: dict[str, dict[str, RequestFeatures]] = defaultdict(dict)
    truth_cluster_sizes: dict[str, int] = defaultdict(int)
    for request_id, feature in features.items():
        cache_groups[feature.cache_bucket][request_id] = feature
        truth_cluster_sizes[truth[request_id]] += 1
    candidate_pairs = 0
    retained = 0
    for scoped in cache_groups.values():
        buckets = inverted_index(
            {request_id: feature.shingles for request_id, feature in scoped.items()}
        )
        pair_counts: dict[str, int] = defaultdict(int)
        for left, right in _iter_bounded_candidate_pairs(
            buckets,
            max_bucket_size=LOWCOST_SHINGLE_BUCKET_SIZE,
            pair_counts=pair_counts,
            max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
        ):
            candidate_pairs += 1
            retained += truth[left] == truth[right]
    truth_pairs = sum(size * (size - 1) // 2 for size in truth_cluster_sizes.values())
    return {
        "candidate_pairs": candidate_pairs,
        "true_pairs_retained": retained,
        "truth_pairs": truth_pairs,
        "candidate_recall": retained / truth_pairs if truth_pairs else 0.0,
        "candidate_precision": retained / candidate_pairs if candidate_pairs else 0.0,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sizes", type=int, nargs="+", default=[10_000, 50_000, 100_000])
    parser.add_argument(
        "--conditions",
        nargs="+",
        choices=("clean", "shared_alias_collision"),
        default=["clean", "shared_alias_collision"],
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(
        summarize_scale(
            sizes=tuple(args.sizes),
            conditions=tuple(args.conditions),
            output_dir=args.output_dir,
        )
    )


if __name__ == "__main__":
    main()
