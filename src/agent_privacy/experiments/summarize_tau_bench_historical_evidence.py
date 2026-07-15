"""Summarize held-out tau-bench historical linkage with calibrated baselines.

The historical tau-bench sample is small enough to materialize features, which lets this
summary keep calibration separate from evaluation.  The semantic operating point is selected
only on a deterministic 20% workflow calibration split; all reported test metrics use the
remaining workflows.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from agent_privacy.attacks.cluster import UnionFind, inverted_index
from agent_privacy.attacks.pipeline import (
    LOWCOST_MAX_PAIRS_PER_REQUEST,
    LOWCOST_SEMANTIC_BUCKET_SIZE,
    _iter_bounded_candidate_pairs,
    run_attacks_from_features,
)
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.experiments.bootstrap_ci import (
    _bootstrap_units,
    _quantile,
    _weighted_pairwise_metrics,
)
from agent_privacy.experiments.run_dataset import control_predictions
from agent_privacy.features.extract import (
    RequestFeatures,
    extract_features_from_jsonl,
    jaccard,
    overlap_count,
)
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET_DIR = Path("artifacts/datasets/tau_bench_historical_sample200")
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "tau_bench_historical_evidence"
OPERATING_BASE = "tau_bench_historical_operating_points"
SPLIT_BASE = "tau_bench_historical_split_manifest"
CALIBRATION_FRACTION = 0.20
BASELINE_METHODS = [
    "temporal",
    "rare",
    "tool",
    "prefix",
    "context_only",
    "hybrid",
    "provider_lowcost",
]
SEMANTIC_OVERLAPS = (2, 3, 4, 5)
SHINGLE_THRESHOLDS = (0.32, 0.50, 0.60, 0.70)
IDENTIFIER_OVERLAPS = (3, 4, 5, 6)
TIME_GAPS = (30, 60, 90)


@dataclass(frozen=True)
class SemanticThresholds:
    semantic_overlap: int
    shingle_jaccard: float
    identifier_overlap: int
    max_time_gap: int


def summarize_tau_bench_evidence(
    *,
    dataset_dir: Path = DEFAULT_DATASET_DIR,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    iterations: int = 200,
    seed: int = 7,
) -> dict[str, str]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    attack_path = dataset_dir / "attack_view.jsonl"
    features = extract_features_from_jsonl(attack_path)
    calibration_rows, test_rows = _split_rows(truth_rows, seed=seed)
    calibration_ids = {row["request_id"] for row in calibration_rows}
    test_ids = {row["request_id"] for row in test_rows}
    calibration_features = {
        request_id: feature for request_id, feature in features.items() if request_id in calibration_ids
    }
    test_features = {
        request_id: feature for request_id, feature in features.items() if request_id in test_ids
    }
    del features

    thresholds, operating_rows = _calibrate_semantic_thresholds(
        calibration_features, calibration_rows
    )
    test_predictions = run_attacks_from_features(test_features, methods=BASELINE_METHODS)
    test_predictions["semantic_high_precision"] = _semantic_labels(test_features, thresholds)

    test_predictions.update(
        control_predictions(
            request_ids=sorted(test_ids),
            truth_rows=test_rows,
            methods=["random", "oracle_size_random"],
            seed=seed,
            levels=["session"],
        )
    )

    metric_rows = _metric_rows(
        predictions=test_predictions,
        truth_rows=test_rows,
        iterations=iterations,
        seed=seed,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    evidence_csv = output_dir / f"{OUTPUT_BASE}.csv"
    evidence_md = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(evidence_csv, metric_rows)
    _write_markdown(evidence_md, metric_rows)

    selected_test = _metric_rows(
        predictions={"semantic_high_precision": test_predictions["semantic_high_precision"]},
        truth_rows=test_rows,
        iterations=iterations,
        seed=seed,
    )
    operating_rows.extend(
        {
            "scope": "held_out_test",
            "semantic_overlap": thresholds.semantic_overlap,
            "shingle_jaccard": thresholds.shingle_jaccard,
            "identifier_overlap": thresholds.identifier_overlap,
            "max_time_gap": thresholds.max_time_gap,
            "precision": row["precision"],
            "recall": row["recall"],
            "f1": row["f1"],
            "precision_ci_low": row["precision_ci_low"],
            "precision_ci_high": row["precision_ci_high"],
            "recall_ci_low": row["recall_ci_low"],
            "recall_ci_high": row["recall_ci_high"],
            "f1_ci_low": row["f1_ci_low"],
            "f1_ci_high": row["f1_ci_high"],
            "workflows": row["workflows"],
            "requests": row["requests"],
        }
        for row in selected_test
        if row["scope"] == "overall"
    )
    operating_csv = output_dir / f"{OPERATING_BASE}.csv"
    operating_md = output_dir / f"{OPERATING_BASE}.md"
    write_csv(operating_csv, operating_rows)
    _write_markdown(operating_md, operating_rows)

    split_manifest = {
        "dataset_dir": str(dataset_dir),
        "seed": seed,
        "calibration_fraction": CALIBRATION_FRACTION,
        "calibration_workflows": sorted({row["workflow_id"] for row in calibration_rows}),
        "test_workflows": sorted({row["workflow_id"] for row in test_rows}),
        "calibration_requests": len(calibration_rows),
        "test_requests": len(test_rows),
        "selected_thresholds": thresholds.__dict__,
        "bootstrap_iterations": iterations,
    }
    split_json = output_dir / f"{SPLIT_BASE}.json"
    split_json.write_text(json.dumps(split_manifest, indent=2) + "\n", encoding="utf-8")
    return {
        "evidence_csv": str(evidence_csv),
        "evidence_md": str(evidence_md),
        "operating_csv": str(operating_csv),
        "operating_md": str(operating_md),
        "split_manifest": str(split_json),
        "selected_thresholds": json.dumps(thresholds.__dict__, sort_keys=True),
    }


def _split_rows(
    rows: list[dict[str, Any]], *, seed: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_domain: dict[str, dict[str, list[dict[str, Any]]]] = defaultdict(lambda: defaultdict(list))
    for row in rows:
        by_domain[str(row.get("org_id", "unknown"))][str(row["workflow_id"])].append(row)
    calibration_workflows: set[str] = set()
    for domain, workflows in sorted(by_domain.items()):
        ordered = sorted(
            workflows,
            key=lambda workflow: hashlib.sha256(f"{seed}:{domain}:{workflow}".encode()).hexdigest(),
        )
        count = max(1, round(len(ordered) * CALIBRATION_FRACTION))
        calibration_workflows.update(ordered[:count])
    calibration = [row for row in rows if row["workflow_id"] in calibration_workflows]
    test = [row for row in rows if row["workflow_id"] not in calibration_workflows]
    return calibration, test


def _calibrate_semantic_thresholds(
    features: dict[str, RequestFeatures], truth_rows: list[dict[str, Any]]
) -> tuple[SemanticThresholds, list[dict[str, Any]]]:
    truth = truth_labels(truth_rows, "session")
    candidates = _semantic_candidates(features)
    rows: list[dict[str, Any]] = []
    for semantic_overlap in SEMANTIC_OVERLAPS:
        for shingle_jaccard in SHINGLE_THRESHOLDS:
            for identifier_overlap in IDENTIFIER_OVERLAPS:
                for max_time_gap in TIME_GAPS:
                    thresholds = SemanticThresholds(
                        semantic_overlap,
                        shingle_jaccard,
                        identifier_overlap,
                        max_time_gap,
                    )
                    prediction = _semantic_labels_from_candidates(
                        features, candidates, thresholds
                    )
                    metrics = clustering_metrics(prediction["session"], truth)
                    rows.append(
                        {
                            "scope": "calibration",
                            "semantic_overlap": semantic_overlap,
                            "shingle_jaccard": shingle_jaccard,
                            "identifier_overlap": identifier_overlap,
                            "max_time_gap": max_time_gap,
                            "precision": metrics["pairwise_precision"],
                            "recall": metrics["pairwise_recall"],
                            "f1": metrics["pairwise_f1"],
                            "precision_ci_low": "",
                            "precision_ci_high": "",
                            "recall_ci_low": "",
                            "recall_ci_high": "",
                            "f1_ci_low": "",
                            "f1_ci_high": "",
                            "workflows": len({row["workflow_id"] for row in truth_rows}),
                            "requests": len(truth_rows),
                        }
                    )
    eligible = [row for row in rows if row["precision"] >= 0.8 and row["recall"] > 0]
    pool = eligible or rows
    selected_row = max(pool, key=lambda row: (row["f1"], row["precision"], row["recall"]))
    selected = SemanticThresholds(
        int(selected_row["semantic_overlap"]),
        float(selected_row["shingle_jaccard"]),
        int(selected_row["identifier_overlap"]),
        int(selected_row["max_time_gap"]),
    )
    rows.append(
        {
            "scope": "selected_calibration",
            "semantic_overlap": selected.semantic_overlap,
            "shingle_jaccard": selected.shingle_jaccard,
            "identifier_overlap": selected.identifier_overlap,
            "max_time_gap": selected.max_time_gap,
            "precision": selected_row["precision"],
            "recall": selected_row["recall"],
            "f1": selected_row["f1"],
            "precision_ci_low": "",
            "precision_ci_high": "",
            "recall_ci_low": "",
            "recall_ci_high": "",
            "f1_ci_low": "",
            "f1_ci_high": "",
            "workflows": len({row["workflow_id"] for row in truth_rows}),
            "requests": len(truth_rows),
        }
    )
    return selected, rows


def _semantic_candidates(
    features: dict[str, RequestFeatures],
) -> list[tuple[str, str, int, float, int, int]]:
    by_cache: dict[str, dict[str, RequestFeatures]] = defaultdict(dict)
    for request_id, feature in features.items():
        by_cache[feature.cache_bucket or "cache_unavailable"][request_id] = feature
    candidates: list[tuple[str, str, int, float, int, int]] = []
    for scoped in by_cache.values():
        buckets = inverted_index({rid: feat.semantic_signatures for rid, feat in scoped.items()})
        pair_counts: dict[str, int] = defaultdict(int)
        for left, right in _iter_bounded_candidate_pairs(
            buckets,
            max_bucket_size=LOWCOST_SEMANTIC_BUCKET_SIZE,
            pair_counts=pair_counts,
            max_pairs_per_item=LOWCOST_MAX_PAIRS_PER_REQUEST,
        ):
            left_feat = scoped[left]
            right_feat = scoped[right]
            candidates.append(
                (
                    left,
                    right,
                    overlap_count(
                        left_feat.semantic_signatures, right_feat.semantic_signatures
                    ),
                    jaccard(left_feat.shingles, right_feat.shingles),
                    overlap_count(left_feat.identifiers, right_feat.identifiers),
                    abs(left_feat.timestamp_minute - right_feat.timestamp_minute),
                )
            )
    return candidates


def _semantic_labels(
    features: dict[str, RequestFeatures], thresholds: SemanticThresholds
) -> dict[str, dict[str, str]]:
    return _semantic_labels_from_candidates(features, _semantic_candidates(features), thresholds)


def _semantic_labels_from_candidates(
    features: dict[str, RequestFeatures],
    candidates: Iterable[tuple[str, str, int, float, int, int]],
    thresholds: SemanticThresholds,
) -> dict[str, dict[str, str]]:
    uf = UnionFind(list(features))
    for left, right, semantic_overlap, shingle_score, identifier_overlap, time_gap in candidates:
        if (
            semantic_overlap >= thresholds.semantic_overlap
            and shingle_score >= thresholds.shingle_jaccard
            and identifier_overlap >= thresholds.identifier_overlap
            and time_gap <= thresholds.max_time_gap
        ):
            uf.union(left, right)
    return {
        "session": uf.labels("semantic_hp_s"),
        "user": UnionFind(list(features)).labels("semantic_hp_u"),
        "project": UnionFind(list(features)).labels("semantic_hp_p"),
        "org": UnionFind(list(features)).labels("semantic_hp_o"),
    }


def _metric_rows(
    *,
    predictions: dict[str, dict[str, dict[str, str]]],
    truth_rows: list[dict[str, Any]],
    iterations: int,
    seed: int,
) -> list[dict[str, Any]]:
    scopes = [("overall", truth_rows)]
    scopes.extend(
        (domain, [row for row in truth_rows if str(row.get("org_id")) == domain])
        for domain in sorted({str(row.get("org_id")) for row in truth_rows})
    )
    rows: list[dict[str, Any]] = []
    for method, level_predictions in predictions.items():
        prediction = level_predictions.get("session", {})
        for scope, scoped_truth_rows in scopes:
            if not scoped_truth_rows:
                continue
            scoped_ids = {row["request_id"] for row in scoped_truth_rows}
            scoped_prediction = {
                request_id: label for request_id, label in prediction.items() if request_id in scoped_ids
            }
            truth = truth_labels(scoped_truth_rows, "session")
            observed = clustering_metrics(scoped_prediction, truth)
            ci = _bootstrap_metrics(
                scoped_prediction,
                scoped_truth_rows,
                iterations=iterations,
                seed=seed,
            )
            rows.append(
                {
                    "scope": scope,
                    "method": method,
                    "precision": round(observed["pairwise_precision"], 3),
                    "recall": round(observed["pairwise_recall"], 3),
                    "f1": round(observed["pairwise_f1"], 3),
                    "precision_ci_low": round(ci["precision_ci_low"], 3),
                    "precision_ci_high": round(ci["precision_ci_high"], 3),
                    "recall_ci_low": round(ci["recall_ci_low"], 3),
                    "recall_ci_high": round(ci["recall_ci_high"], 3),
                    "f1_ci_low": round(ci["f1_ci_low"], 3),
                    "f1_ci_high": round(ci["f1_ci_high"], 3),
                    "workflows": len({row["workflow_id"] for row in scoped_truth_rows}),
                    "requests": len(scoped_truth_rows),
                }
            )
    return rows


def _bootstrap_metrics(
    prediction: dict[str, str],
    truth_rows: list[dict[str, Any]],
    *,
    iterations: int,
    seed: int,
) -> dict[str, float]:
    truth = truth_labels(truth_rows, "session")
    units = _bootstrap_units(truth_rows, "session")
    request_to_unit = {
        request_id: unit_id for unit_id, members in units.items() for request_id in members
    }
    unit_keys = sorted(units)
    rng = random.Random(seed)
    samples = {metric: [] for metric in ("precision", "recall", "f1")}
    for _ in range(iterations):
        weights: dict[str, int] = defaultdict(int)
        for _draw in unit_keys:
            weights[rng.choice(unit_keys)] += 1
        metric = _weighted_pairwise_metrics(prediction, truth, request_to_unit, weights)
        samples["precision"].append(metric["pairwise_precision"])
        samples["recall"].append(metric["pairwise_recall"])
        samples["f1"].append(metric["pairwise_f1"])
    return {
        f"{metric}_ci_low": _quantile(values, 0.025)
        for metric, values in samples.items()
    } | {
        f"{metric}_ci_high": _quantile(values, 0.975)
        for metric, values in samples.items()
    }


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    headers = list(rows[0])
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(str(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(
        summarize_tau_bench_evidence(
            dataset_dir=args.dataset_dir,
            output_dir=args.output_dir,
            iterations=args.iterations,
            seed=args.seed,
        )
    )


if __name__ == "__main__":
    main()
