from __future__ import annotations

import argparse
import time
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

from agent_privacy.attacks.cluster import UnionFind, inverted_index
from agent_privacy.attacks.pipeline import run_attacks_from_features
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.experiments.feature_ablations import feature_options_for_ablation
from agent_privacy.features.extract import RequestFeatures, extract_features_from_jsonl, jaccard, overlap_count
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_CONTAINMENTS = [0.60, 0.70, 0.78, 0.86]
DEFAULT_JACCARDS = [0.12, 0.20, 0.28]
DEFAULT_CANDIDATE_CAPS = [100, 400, 800]


def sweep_thresholds(
    *,
    dataset_dir: Path,
    output: Path,
    turn_ids: list[int] | None = None,
    containments: list[float] | None = None,
    jaccards: list[float] | None = None,
    candidate_caps: list[int] | None = None,
    max_bucket_size: int = 35,
    fast_features: bool = True,
    axis_only: bool = False,
) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    if turn_ids:
        allowed_turns = set(turn_ids)
        truth_rows = [row for row in truth_rows if int(row.get("turn_id", -1)) in allowed_turns]
    request_ids = {row["request_id"] for row in truth_rows}
    feature_options = feature_options_for_ablation(
        methods=["provider_lowcost"],
        fast_features=fast_features,
        feature_ablation="none",
    )
    t0 = time.perf_counter()
    features = extract_features_from_jsonl(
        dataset_dir / "attack_view.jsonl",
        options=feature_options,
        request_ids=request_ids if turn_ids else None,
    )
    feature_seconds = time.perf_counter() - t0
    baseline_t0 = time.perf_counter()
    baseline = run_attacks_from_features(features, methods=["provider_lowcost"])["provider_lowcost"]
    baseline_seconds = time.perf_counter() - baseline_t0
    session_truth = truth_labels(truth_rows, "session")
    project_truth = truth_labels(truth_rows, "project")
    org_truth = truth_labels(truth_rows, "org")
    baseline_session = clustering_metrics(baseline["session"], session_truth)
    caps = candidate_caps or DEFAULT_CANDIDATE_CAPS
    candidate_cache = {
        cap: _bounded_context_candidates(
            features,
            max_pairs_per_request=cap,
            max_bucket_size=max_bucket_size,
        )
        for cap in caps
    }
    rows: list[dict[str, Any]] = [
        {
            "variant": "provider_lowcost_default",
            "containment_threshold": "",
            "jaccard_threshold": "",
            "max_pairs_per_request": "",
            "candidate_pairs": "",
            "linked_pairs": "",
            "feature_seconds": feature_seconds,
            "attack_seconds": baseline_seconds,
            "requests": len(features),
            "session_f1": baseline_session["pairwise_f1"],
            "session_precision": baseline_session["pairwise_precision"],
            "session_recall": baseline_session["pairwise_recall"],
            "project_f1": clustering_metrics(baseline["project"], project_truth)["pairwise_f1"],
            "org_f1": clustering_metrics(baseline["org"], org_truth)["pairwise_f1"],
        }
    ]
    containment_values = containments or DEFAULT_CONTAINMENTS
    jaccard_values = jaccards or DEFAULT_JACCARDS
    configurations = (
        sorted(
            {
                *((value, 0.20, 400) for value in containment_values),
                *((0.78, value, 400) for value in jaccard_values),
                *((0.78, 0.20, value) for value in caps),
            }
        )
        if axis_only
        else [
            (containment, jaccard_threshold, cap)
            for containment in containment_values
            for jaccard_threshold in jaccard_values
            for cap in caps
        ]
    )
    for containment, jaccard_threshold, cap in configurations:
        t1 = time.perf_counter()
        labels, diagnostics = _context_threshold_labels(
            features,
            truth=session_truth,
            candidate_pairs=candidate_cache[cap],
            containment_threshold=containment,
            jaccard_threshold=jaccard_threshold,
            max_pairs_per_request=cap,
            max_bucket_size=max_bucket_size,
        )
        attack_seconds = time.perf_counter() - t1
        metrics = clustering_metrics(labels, session_truth)
        rows.append(
            {
                "variant": "context_sweep",
                "containment_threshold": containment,
                "jaccard_threshold": jaccard_threshold,
                "max_pairs_per_request": cap,
                "candidate_pairs": diagnostics["candidate_pairs"],
                "linked_pairs": diagnostics["linked_pairs"],
                "true_session_pairs_retained": diagnostics[
                    "true_session_pairs_retained"
                ],
                "truth_session_pairs": diagnostics["truth_session_pairs"],
                "candidate_recall": diagnostics["candidate_recall"],
                "candidate_precision": diagnostics["candidate_precision"],
                "feature_seconds": feature_seconds,
                "attack_seconds": attack_seconds,
                "requests": len(features),
                "session_f1": metrics["pairwise_f1"],
                "session_precision": metrics["pairwise_precision"],
                "session_recall": metrics["pairwise_recall"],
                "project_f1": "",
                "org_f1": "",
            }
        )
    write_csv(output, rows)
    _write_markdown(output.with_suffix(".md"), rows)
    return rows


def _context_threshold_labels(
    features: dict[str, RequestFeatures],
    *,
    truth: dict[str, str] | None = None,
    candidate_pairs: list[tuple[str, str]] | None = None,
    containment_threshold: float,
    jaccard_threshold: float,
    max_pairs_per_request: int,
    max_bucket_size: int,
) -> tuple[dict[str, str], dict[str, int]]:
    uf = UnionFind(sorted(features))
    candidates = candidate_pairs or _bounded_context_candidates(
        features,
        max_pairs_per_request=max_pairs_per_request,
        max_bucket_size=max_bucket_size,
    )
    candidate_pair_count = 0
    linked_pairs = 0
    true_session_pairs_retained = 0
    for left, right in candidates:
        candidate_pair_count += 1
        if truth is not None and truth.get(left) == truth.get(right):
            true_session_pairs_retained += 1
        if _threshold_link(
            features[left],
            features[right],
            containment_threshold=containment_threshold,
            jaccard_threshold=jaccard_threshold,
        ):
            uf.union(left, right)
            linked_pairs += 1
    truth_counts = Counter(truth.values()) if truth is not None else Counter()
    truth_session_pairs = sum(count * (count - 1) // 2 for count in truth_counts.values())
    return uf.labels("threshold_s"), {
        "candidate_pairs": candidate_pair_count,
        "linked_pairs": linked_pairs,
        "true_session_pairs_retained": true_session_pairs_retained,
        "truth_session_pairs": truth_session_pairs,
        "candidate_recall": true_session_pairs_retained / truth_session_pairs
        if truth_session_pairs
        else 0.0,
        "candidate_precision": true_session_pairs_retained / candidate_pair_count
        if candidate_pair_count
        else 0.0,
    }


def _bounded_context_candidates(
    features: dict[str, RequestFeatures],
    *,
    max_pairs_per_request: int,
    max_bucket_size: int,
) -> list[tuple[str, str]]:
    buckets = inverted_index({rid: feat.shingles for rid, feat in features.items()})
    pair_counts: dict[str, int] = defaultdict(int)
    candidates = []
    seen: set[tuple[str, str]] = set()
    for members in sorted(
        buckets.values(), key=lambda values: (len(values), sorted(values)[0])
    ):
        if not (1 < len(members) <= max_bucket_size):
            continue
        for left, right in combinations(sorted(members), 2):
            if (
                pair_counts[left] >= max_pairs_per_request
                or pair_counts[right] >= max_pairs_per_request
            ):
                continue
            pair = (left, right)
            if pair in seen:
                continue
            seen.add(pair)
            pair_counts[left] += 1
            pair_counts[right] += 1
            candidates.append(pair)
    return candidates


def _threshold_link(
    left: RequestFeatures,
    right: RequestFeatures,
    *,
    containment_threshold: float,
    jaccard_threshold: float,
) -> bool:
    if not left.shingles or not right.shingles:
        return False
    time_gap = abs(left.timestamp_minute - right.timestamp_minute)
    if time_gap > 180:
        return False
    small, large = (left.shingles, right.shingles) if len(left.shingles) <= len(right.shingles) else (right.shingles, left.shingles)
    overlap = len(small & large)
    if not overlap:
        return False
    containment = overlap / len(small)
    repo_overlap = overlap_count(_repo_full_ids(left.identifiers), _repo_full_ids(right.identifiers))
    return (
        containment >= containment_threshold
        and jaccard(left.shingles, right.shingles) >= jaccard_threshold
        and overlap_count(left.identifiers, right.identifiers) >= 2
        and repo_overlap >= 1
    )


def _repo_full_ids(identifiers: frozenset[str]) -> set[str]:
    return {value for value in identifiers if value.startswith("repo_full:")}


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "variant",
        "containment_threshold",
        "jaccard_threshold",
        "max_pairs_per_request",
        "candidate_pairs",
        "linked_pairs",
        "candidate_recall",
        "candidate_precision",
        "attack_seconds",
        "session_f1",
        "session_precision",
        "session_recall",
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
    parser = argparse.ArgumentParser(description="Sweep provider-lowcost context thresholds.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--turn-ids", type=int, nargs="*")
    parser.add_argument("--containments", type=float, nargs="*")
    parser.add_argument("--jaccards", type=float, nargs="*")
    parser.add_argument("--candidate-caps", type=int, nargs="*")
    parser.add_argument("--max-bucket-size", type=int, default=35)
    parser.add_argument("--full-features", action="store_true")
    parser.add_argument("--axis-only", action="store_true")
    args = parser.parse_args()
    sweep_thresholds(
        dataset_dir=args.dataset_dir,
        output=args.output,
        turn_ids=args.turn_ids,
        containments=args.containments,
        jaccards=args.jaccards,
        candidate_caps=args.candidate_caps,
        max_bucket_size=args.max_bucket_size,
        fast_features=not args.full_features,
        axis_only=args.axis_only,
    )


if __name__ == "__main__":
    main()
