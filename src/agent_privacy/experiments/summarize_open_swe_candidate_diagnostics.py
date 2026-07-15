from __future__ import annotations

import argparse
import json
from collections import defaultdict
from dataclasses import replace
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

from agent_privacy.attacks.cluster import UnionFind, inverted_index
from agent_privacy.attacks.pipeline import (
    LOWCOST_MAX_PAIRS_PER_REQUEST,
    LOWCOST_SHINGLE_BUCKET_SIZE,
    _informative_identifiers,
    _iter_bounded_candidate_pairs,
)
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.experiments.feature_ablations import feature_options_for_ablation
from agent_privacy.features.extract import RequestFeatures, extract_features_from_jsonl, jaccard
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000")
DEFAULT_DEVELOPMENT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_sample100")
DEFAULT_CARP_PREDICTIONS = Path(
    "results/open_swe_carp_fixed_turns_3_6_9_12/M0/feature_no_semantic/predictions.json"
)
DEFAULT_HYBRID_PREDICTIONS = Path(
    "results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast/M0/predictions.json"
)
OUTPUT_BASE = "open_swe_candidate_diagnostics"
TURN_IDS = {3, 6, 9, 12}
SKETCH_SIZE = 32
SKETCH_BAND_SIZE = 4
SKETCH_MAX_BUCKET_SIZE = 80


def summarize_candidate_diagnostics(
    *,
    dataset_dir: Path = DEFAULT_DATASET,
    development_dataset_dir: Path = DEFAULT_DEVELOPMENT_DATASET,
    carp_predictions_path: Path = DEFAULT_CARP_PREDICTIONS,
    hybrid_predictions_path: Path = DEFAULT_HYBRID_PREDICTIONS,
) -> list[dict[str, Any]]:
    all_truth = [
        row
        for row in read_jsonl(dataset_dir / "ground_truth.jsonl")
        if int(row.get("turn_id", -1)) in TURN_IDS
    ]
    development_workflows = {
        str(row["workflow_id"])
        for row in read_jsonl(development_dataset_dir / "ground_truth.jsonl")
    }
    heldout_truth = [
        row for row in all_truth if str(row["workflow_id"]) not in development_workflows
    ]
    heldout_ids = {str(row["request_id"]) for row in heldout_truth}
    options = feature_options_for_ablation(
        methods=["provider_lowcost"],
        fast_features=True,
        feature_ablation="no_semantic",
    )
    options = replace(
        options,
        text_feature_window_chars=24_000,
        max_shingles=1_200,
        max_words=1_500,
    )
    features = extract_features_from_jsonl(
        dataset_dir / "attack_view.jsonl",
        options=options,
        request_ids=heldout_ids,
    )
    stages = _carp_session_candidates(features)
    truth_pairs = _truth_pairs(heldout_truth)
    rows = [
        _candidate_row(stage, pairs, truth_pairs, heldout_ids)
        for stage, pairs in stages.items()
    ]

    sketch_candidates, sketch_predictions = _bottom_k_shingle_sketch_baseline(features)
    rows.append(
        _candidate_row(
            "bottom_k_shingle_sketch_candidates",
            sketch_candidates,
            truth_pairs,
            heldout_ids,
            sketch_size=SKETCH_SIZE,
            band_size=SKETCH_BAND_SIZE,
        )
    )
    rows.append(
        _prediction_row(
            "bottom_k_shingle_sketch_linkage",
            sketch_predictions,
            heldout_truth,
            candidate_pairs=sketch_candidates,
            truth_pairs=truth_pairs,
            heldout_ids=heldout_ids,
            sketch_size=SKETCH_SIZE,
            band_size=SKETCH_BAND_SIZE,
        )
    )
    carp_predictions = json.loads(carp_predictions_path.read_text(encoding="utf-8"))[
        "provider_lowcost"
    ]["session"]
    hybrid_predictions = json.loads(hybrid_predictions_path.read_text(encoding="utf-8"))[
        "hybrid"
    ]["session"]
    rows.append(
        _prediction_row(
            "carp_final",
            carp_predictions,
            heldout_truth,
            candidate_pairs=stages["candidate_union"],
            truth_pairs=truth_pairs,
            heldout_ids=heldout_ids,
        )
    )
    rows.append(
        _prediction_row(
            "hybrid_final",
            hybrid_predictions,
            heldout_truth,
            candidate_pairs=None,
            truth_pairs=truth_pairs,
            heldout_ids=heldout_ids,
        )
    )
    return rows


def _carp_session_candidates(
    features: dict[str, RequestFeatures],
) -> dict[str, set[tuple[str, str]]]:
    rare_pairs: set[tuple[str, str]] = set()
    context_pairs: set[tuple[str, str]] = set()
    refine_pairs: set[tuple[str, str]] = set()
    by_cache: dict[str, dict[str, RequestFeatures]] = defaultdict(dict)
    for request_id, feature in features.items():
        by_cache[feature.cache_bucket or "cache_unavailable"][request_id] = feature
    for scoped in by_cache.values():
        rare_buckets = inverted_index({rid: feat.traces for rid, feat in scoped.items()})
        for members in rare_buckets.values():
            if 1 < len(members) <= 20:
                rare_pairs.update(_pairs(members))

        context_buckets = inverted_index({rid: feat.shingles for rid, feat in scoped.items()})
        pair_counts: dict[str, int] = defaultdict(int)
        context_pairs.update(
            _iter_bounded_candidate_pairs(
                context_buckets,
                max_bucket_size=LOWCOST_SHINGLE_BUCKET_SIZE,
                pair_counts=pair_counts,
                max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
            )
        )

        refine_buckets = inverted_index(
            {
                rid: _informative_identifiers(feat.identifiers) | feat.traces | feat.domains
                for rid, feat in scoped.items()
            }
        )
        pair_counts = defaultdict(int)
        refine_pairs.update(
            _iter_bounded_candidate_pairs(
                refine_buckets,
                max_bucket_size=20,
                pair_counts=pair_counts,
                max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
            )
        )
    return {
        "rare_candidates": rare_pairs,
        "context_candidates": context_pairs,
        "refine_candidates": refine_pairs,
        "candidate_union": rare_pairs | context_pairs | refine_pairs,
    }


def _bottom_k_shingle_sketch_baseline(
    features: dict[str, RequestFeatures],
) -> tuple[set[tuple[str, str]], dict[str, str]]:
    band_buckets: dict[str, set[str]] = defaultdict(set)
    for request_id, feature in features.items():
        signature = sorted(feature.shingles)[:SKETCH_SIZE]
        for band_start in range(
            0,
            len(signature) - SKETCH_BAND_SIZE + 1,
            SKETCH_BAND_SIZE,
        ):
            band = signature[band_start : band_start + SKETCH_BAND_SIZE]
            band_buckets[f"{band_start}:{'|'.join(band)}"].add(request_id)
    pair_counts: dict[str, int] = defaultdict(int)
    candidates = set(
        _iter_bounded_candidate_pairs(
            dict(band_buckets),
            max_bucket_size=SKETCH_MAX_BUCKET_SIZE,
            pair_counts=pair_counts,
            max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
        )
    )
    uf = UnionFind(list(features))
    for left, right in candidates:
        left_feature = features[left]
        right_feature = features[right]
        intersection = len(left_feature.shingles & right_feature.shingles)
        smaller = min(len(left_feature.shingles), len(right_feature.shingles))
        containment = intersection / smaller if smaller else 0.0
        time_gap = abs(left_feature.timestamp_minute - right_feature.timestamp_minute)
        if containment >= 0.78 and jaccard(left_feature.shingles, right_feature.shingles) >= 0.20 and time_gap <= 180:
            uf.union(left, right)
    return candidates, uf.labels("bottom_k_shingle_sketch")


def _candidate_row(
    stage: str,
    pairs: set[tuple[str, str]],
    truth_pairs: set[tuple[str, str]],
    heldout_ids: set[str],
    *,
    sketch_size: int | str = "",
    band_size: int | str = "",
) -> dict[str, Any]:
    scoped = {pair for pair in pairs if pair[0] in heldout_ids and pair[1] in heldout_ids}
    true_candidates = len(scoped & truth_pairs)
    return {
        "stage": stage,
        "candidate_pairs": len(scoped),
        "true_session_pairs_retained": true_candidates,
        "truth_session_pairs": len(truth_pairs),
        "candidate_recall": true_candidates / len(truth_pairs) if truth_pairs else 0.0,
        "candidate_precision": true_candidates / len(scoped) if scoped else 0.0,
        "feature_window_chars": 24000,
        "max_shingles": 1200,
        "max_words": 1500,
        "sketch_size": sketch_size,
        "band_size": band_size,
        "session_precision": "",
        "session_recall": "",
        "session_f1": "",
        "purity": "",
        "split_rate": "",
        "merge_rate": "",
        "clusters": "",
    }


def _prediction_row(
    stage: str,
    predictions: dict[str, str],
    truth_rows: list[dict[str, Any]],
    *,
    candidate_pairs: set[tuple[str, str]] | None,
    truth_pairs: set[tuple[str, str]],
    heldout_ids: set[str],
    sketch_size: int | str = "",
    band_size: int | str = "",
) -> dict[str, Any]:
    metrics = clustering_metrics(predictions, truth_labels(truth_rows, "session"))
    candidate = (
        _candidate_row(
            stage,
            candidate_pairs,
            truth_pairs,
            heldout_ids,
            sketch_size=sketch_size,
            band_size=band_size,
        )
        if candidate_pairs is not None
        else {
            "stage": stage,
            "candidate_pairs": "",
            "true_session_pairs_retained": "",
            "truth_session_pairs": len(truth_pairs),
            "candidate_recall": "",
            "candidate_precision": "",
            "feature_window_chars": 24000,
            "max_shingles": 1200,
            "max_words": 1500,
            "sketch_size": sketch_size,
            "band_size": band_size,
        }
    )
    candidate.update(
        {
            "session_precision": metrics["pairwise_precision"],
            "session_recall": metrics["pairwise_recall"],
            "session_f1": metrics["pairwise_f1"],
            "purity": metrics["purity"],
            "split_rate": metrics["split_rate"],
            "merge_rate": metrics["merge_rate"],
            "clusters": int(metrics["clusters"]),
        }
    )
    return candidate


def _truth_pairs(truth_rows: list[dict[str, Any]]) -> set[tuple[str, str]]:
    by_workflow: dict[str, list[str]] = defaultdict(list)
    for row in truth_rows:
        by_workflow[str(row["workflow_id"])].append(str(row["request_id"]))
    pairs: set[tuple[str, str]] = set()
    for members in by_workflow.values():
        pairs.update(_pairs(members))
    return pairs


def _pairs(members: Iterable[str]) -> set[tuple[str, str]]:
    return {tuple(sorted(pair)) for pair in combinations(sorted(members), 2)}


def write_candidate_diagnostics(
    output_dir: Path,
    **kwargs: Any,
) -> dict[str, str]:
    rows = summarize_candidate_diagnostics(**kwargs)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
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
    md_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return {"csv": str(csv_path), "markdown": str(md_path)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize Open-SWE candidate-stage recall.")
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--development-dataset-dir", type=Path, default=DEFAULT_DEVELOPMENT_DATASET
    )
    parser.add_argument("--carp-predictions", type=Path, default=DEFAULT_CARP_PREDICTIONS)
    parser.add_argument("--hybrid-predictions", type=Path, default=DEFAULT_HYBRID_PREDICTIONS)
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(
        write_candidate_diagnostics(
            args.output_dir,
            dataset_dir=args.dataset_dir,
            development_dataset_dir=args.development_dataset_dir,
            carp_predictions_path=args.carp_predictions,
            hybrid_predictions_path=args.hybrid_predictions,
        )
    )


if __name__ == "__main__":
    main()
