from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.io import read_jsonl, write_json
from agent_privacy.profiling.semantic_profiler import (
    DEFAULT_MODEL,
    SemanticOptions,
    encode_request_evidence,
    profile_clusters_semantic,
)
from agent_privacy.profiling.structured_profiler import (
    AUDITED_TECHNICAL_FIELDS,
    profile_clusters_structured,
)
from agent_privacy.reporting import write_csv


THRESHOLDS = (0.34, 0.38, 0.42, 0.46, 0.50, 0.54, 0.58)
MIN_SUPPORTS = (1, 2, 3)


def run_semantic_profile_experiment(
    dataset_dir: Path,
    predictions_path: Path,
    output_dir: Path,
    *,
    method: str = "hybrid",
    level: str = "org",
    model_name: str = DEFAULT_MODEL,
    calibration_fraction: float = 0.20,
    seed: int = 7,
) -> dict[str, Any]:
    start = time.perf_counter()
    rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    predicted_labels = predictions[method][level]
    calibration_ids, test_ids = split_request_ids_by_org(
        truth_rows,
        calibration_fraction=calibration_fraction,
        seed=seed,
    )
    calibration_rows = [row for row in rows if row["request_id"] in calibration_ids]
    test_rows = [row for row in rows if row["request_id"] in test_ids]
    calibration_truth = [row for row in truth_rows if row["request_id"] in calibration_ids]
    test_truth = [row for row in truth_rows if row["request_id"] in test_ids]
    calibration_labels = {
        request_id: label
        for request_id, label in predicted_labels.items()
        if request_id in calibration_ids
    }
    test_labels = {
        request_id: label for request_id, label in predicted_labels.items() if request_id in test_ids
    }
    request_candidates, semantic_stats = encode_request_evidence(
        rows,
        options=SemanticOptions(model_name=model_name, batch_size=256),
    )
    calibration_candidates = {
        request_id: values
        for request_id, values in request_candidates.items()
        if request_id in calibration_ids
    }
    test_candidates = {
        request_id: values
        for request_id, values in request_candidates.items()
        if request_id in test_ids
    }

    calibration_rows_out: list[dict[str, Any]] = []
    best: tuple[float, float, float, int] | None = None
    for threshold in THRESHOLDS:
        for min_support in MIN_SUPPORTS:
            profiles = profile_clusters_semantic(
                calibration_rows,
                calibration_labels,
                calibration_candidates,
                threshold=threshold,
                min_request_support=min_support,
            )
            metrics = _audited_metrics(
                evaluate_profiles(profiles, calibration_truth, calibration_labels)
            )
            micro = next(row for row in metrics if row["field"] == "__audited_micro__")
            calibration_rows_out.append(
                {
                    "threshold": threshold,
                    "min_request_support": min_support,
                    "precision": micro["precision"],
                    "recall": micro["recall"],
                    "f1": micro["f1"],
                    "tp": micro["tp"],
                    "fp": micro["fp"],
                    "fn": micro["fn"],
                }
            )
            candidate = (micro["f1"], micro["precision"], threshold, min_support)
            if best is None or candidate > best:
                best = candidate
    assert best is not None
    _, _, selected_threshold, selected_support = best

    structured_profiles = profile_clusters_structured(test_rows, test_labels)
    semantic_profiles = profile_clusters_semantic(
        test_rows,
        test_labels,
        test_candidates,
        threshold=selected_threshold,
        min_request_support=selected_support,
    )
    truth_labels = {row["request_id"]: str(row["org_id"]) for row in test_truth}
    semantic_truth_profiles = profile_clusters_semantic(
        test_rows,
        truth_labels,
        test_candidates,
        threshold=selected_threshold,
        min_request_support=selected_support,
    )
    profile_runs = {
        "structured_predicted_clusters": (structured_profiles, test_labels),
        "semantic_predicted_clusters": (semantic_profiles, test_labels),
        "semantic_truth_clusters": (semantic_truth_profiles, truth_labels),
    }
    comparison_rows: list[dict[str, Any]] = []
    for profiler, (profiles, labels) in profile_runs.items():
        write_json(output_dir / f"{profiler}.json", profiles)
        for row in _audited_metrics(evaluate_profiles(profiles, test_truth, labels)):
            row.update(
                {
                    "profiler": profiler,
                    "cluster_source": (
                        "truth" if profiler.endswith("truth_clusters") else "predicted"
                    ),
                    "split": "test",
                    "model": model_name if profiler.startswith("semantic") else "none",
                    "threshold": selected_threshold if profiler.startswith("semantic") else "",
                    "min_request_support": (
                        selected_support if profiler.startswith("semantic") else ""
                    ),
                }
            )
            comparison_rows.append(row)
    write_csv(output_dir / "semantic_profile_calibration.csv", calibration_rows_out)
    write_csv(output_dir / "semantic_profile_comparison.csv", comparison_rows)
    _write_markdown(output_dir / "semantic_profile_comparison.md", comparison_rows)
    summary = {
        "dataset_dir": str(dataset_dir),
        "predictions": str(predictions_path),
        "method": method,
        "level": level,
        "model": model_name,
        "seed": seed,
        "calibration_fraction": calibration_fraction,
        "calibration_requests": len(calibration_rows),
        "test_requests": len(test_rows),
        "calibration_orgs": len({row["org_id"] for row in calibration_truth}),
        "test_orgs": len({row["org_id"] for row in test_truth}),
        "selected_threshold": selected_threshold,
        "selected_min_request_support": selected_support,
        "semantic_runtime": semantic_stats,
        "total_experiment_seconds": time.perf_counter() - start,
        "max_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
    }
    write_json(output_dir / "semantic_profile_summary.json", summary)
    return summary


def split_request_ids_by_org(
    truth_rows: list[dict[str, Any]],
    *,
    calibration_fraction: float,
    seed: int,
) -> tuple[set[str], set[str]]:
    orgs = sorted({str(row["org_id"]) for row in truth_rows})
    calibration_orgs = {
        org
        for org in orgs
        if _unit_interval(f"{seed}:{org}") < calibration_fraction
    }
    if not calibration_orgs or calibration_orgs == set(orgs):
        cut = max(1, min(len(orgs) - 1, round(len(orgs) * calibration_fraction)))
        calibration_orgs = set(orgs[:cut])
    calibration_ids = {
        row["request_id"] for row in truth_rows if str(row["org_id"]) in calibration_orgs
    }
    test_ids = {row["request_id"] for row in truth_rows} - calibration_ids
    return calibration_ids, test_ids


def _audited_metrics(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    selected = [row for row in rows if row["field"] in AUDITED_TECHNICAL_FIELDS]
    selected.append(_audited_micro(selected))
    return selected


def _audited_micro(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(int(row.get("tp", 0)) for row in rows)
    fp = sum(int(row.get("fp", 0)) for row in rows)
    fn = sum(int(row.get("fn", 0)) for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    predicted = sum(int(row.get("predicted_values", 0)) for row in rows)
    evidenced = sum(int(row.get("evidenced_values", 0)) for row in rows)
    return {
        "field": "__audited_micro__",
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "predicted_values": predicted,
        "evidenced_values": evidenced,
        "unsupported_predictions": sum(
            int(row.get("unsupported_predictions", 0)) for row in rows
        ),
        "evidence_coverage": evidenced / predicted if predicted else 0.0,
    }


def _unit_interval(value: str) -> float:
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:12]
    return int(digest, 16) / float(16**12)


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "profiler",
        "cluster_source",
        "field",
        "precision",
        "recall",
        "f1",
        "tp",
        "fp",
        "fn",
        "evidence_coverage",
    ]
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        values = [
            f"{row.get(field, ''):.3f}"
            if isinstance(row.get(field), float)
            else str(row.get(field, ""))
            for field in fields
        ]
        lines.append("| " + " | ".join(values) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run calibrated semantic profile reconstruction.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--method", default="hybrid")
    parser.add_argument("--level", default="org", choices=["org"])
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--calibration-fraction", type=float, default=0.20)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    print(
        json.dumps(
            run_semantic_profile_experiment(
                args.dataset_dir,
                args.predictions,
                args.output_dir,
                method=args.method,
                level=args.level,
                model_name=args.model,
                calibration_fraction=args.calibration_fraction,
                seed=args.seed,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
