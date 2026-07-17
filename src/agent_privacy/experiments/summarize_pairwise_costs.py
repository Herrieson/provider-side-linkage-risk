from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.clustering import (
    clustering_metrics,
    pairwise_confusion_counts,
    truth_labels,
)
from agent_privacy.io import read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000")
DEFAULT_DEVELOPMENT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_sample100")
DEFAULT_BASELINES = Path(
    "results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast/M0/predictions.json"
)
DEFAULT_CARP = Path(
    "results/open_swe_provider_lowcost_longitudinal_full_first_12000_turns/"
    "M0/feature_no_semantic/predictions.json"
)
DEFAULT_OUTPUT_DIR = Path("docs/tables")
OUTPUT_BASE = "open_swe_pairwise_cost_audit"
TURN_IDS = {3, 6, 9, 12}
COST_RATIOS = (0.1, 1.0, 10.0, 100.0)


def summarize_pairwise_costs(
    *,
    dataset_dir: Path = DEFAULT_DATASET,
    development_dataset_dir: Path = DEFAULT_DEVELOPMENT_DATASET,
    baseline_predictions_path: Path = DEFAULT_BASELINES,
    carp_predictions_path: Path = DEFAULT_CARP,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, str]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    development_workflows = {
        str(row["workflow_id"])
        for row in read_jsonl(development_dataset_dir / "ground_truth.jsonl")
    }
    truth_rows = [
        row
        for row in truth_rows
        if int(row.get("turn_id", -1)) in TURN_IDS
        and str(row["workflow_id"]) not in development_workflows
    ]
    truth = truth_labels(truth_rows, "session")
    baselines = json.loads(baseline_predictions_path.read_text(encoding="utf-8"))
    carp = json.loads(carp_predictions_path.read_text(encoding="utf-8"))
    predictions = {
        "singleton": {request_id: request_id for request_id in truth},
        "temporal": baselines["temporal"]["session"],
        "hybrid": baselines["hybrid"]["session"],
        "carp": carp["provider_lowcost"]["session"],
        "all_in_one": {request_id: "all" for request_id in truth},
    }
    rows = [_audit_row(method, labels, truth) for method, labels in predictions.items()]
    cost_rows = [
        _cost_row(row, false_positive_cost=ratio, false_negative_cost=1.0)
        for ratio in COST_RATIOS
        for row in rows
    ]
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    cost_csv_path = output_dir / f"{OUTPUT_BASE}_cost_ratios.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    write_csv(cost_csv_path, cost_rows)
    _write_markdown(md_path, rows, cost_rows)
    return {
        "audit_csv": str(csv_path),
        "cost_csv": str(cost_csv_path),
        "markdown": str(md_path),
    }


def _audit_row(method: str, pred: dict[str, str], truth: dict[str, str]) -> dict[str, Any]:
    counts = pairwise_confusion_counts(pred, truth)
    metrics = clustering_metrics(pred, truth)
    negative_pairs = counts["actual_negative_pairs"]
    total_pairs = counts["total_pairs"]
    return {
        "method": method,
        **counts,
        "positive_pair_prevalence": counts["actual_positive_pairs"] / total_pairs,
        "pairwise_precision": metrics["pairwise_precision"],
        "pairwise_recall": metrics["pairwise_recall"],
        "pairwise_f1": metrics["pairwise_f1"],
        "false_positive_rate": counts["false_positive_pairs"] / negative_pairs,
        "false_links_per_million_negative_pairs": (
            counts["false_positive_pairs"] / negative_pairs * 1_000_000
        ),
        "pairwise_accuracy": (
            counts["true_positive_pairs"] + counts["true_negative_pairs"]
        )
        / total_pairs,
    }


def _cost_row(
    row: dict[str, Any],
    *,
    false_positive_cost: float,
    false_negative_cost: float,
) -> dict[str, Any]:
    fp = int(row["false_positive_pairs"])
    fn = int(row["false_negative_pairs"])
    positives = int(row["actual_positive_pairs"])
    weighted_cost = false_positive_cost * fp + false_negative_cost * fn
    return {
        "false_positive_cost": false_positive_cost,
        "false_negative_cost": false_negative_cost,
        "method": row["method"],
        "false_positive_pairs": fp,
        "false_negative_pairs": fn,
        "weighted_pair_error": weighted_cost,
        "weighted_error_per_true_pair": weighted_cost / positives,
    }


def _write_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    cost_rows: list[dict[str, Any]],
) -> None:
    headers = [
        "method",
        "actual_positive_pairs",
        "actual_negative_pairs",
        "positive_pair_prevalence",
        "true_positive_pairs",
        "false_positive_pairs",
        "false_negative_pairs",
        "pairwise_precision",
        "pairwise_recall",
        "pairwise_f1",
        "false_links_per_million_negative_pairs",
        "pairwise_accuracy",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row[key]) for key in headers) + " |")
    lines.extend(
        [
            "",
            "Pairwise accuracy is dominated by true-negative request pairs: the singleton baseline ",
            "can exceed 99.9% accuracy while recovering no true link. Pairwise precision instead ",
            "asks what fraction of predicted links are correct, and recall asks what fraction of ",
            "true links are recovered.",
            "",
            "| false_positive_cost / false_negative_cost | method | weighted_error_per_true_pair |",
            "| --- | --- | --- |",
        ]
    )
    for row in cost_rows:
        lines.append(
            "| "
            + " | ".join(
                [
                    _format(row["false_positive_cost"]),
                    str(row["method"]),
                    _format(row["weighted_error_per_true_pair"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "The cost ratio is intentionally reported as a sensitivity parameter. False positives ",
            "contaminate a pseudonymous profile or watchlist with unrelated traffic; false negatives ",
            "understate the provider's aggregation reach. No single ratio is universal.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}" if abs(value) < 0.01 else f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-dir", type=Path, default=DEFAULT_DATASET)
    parser.add_argument(
        "--development-dataset-dir", type=Path, default=DEFAULT_DEVELOPMENT_DATASET
    )
    parser.add_argument("--baseline-predictions", type=Path, default=DEFAULT_BASELINES)
    parser.add_argument("--carp-predictions", type=Path, default=DEFAULT_CARP)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    print(
        summarize_pairwise_costs(
            dataset_dir=args.dataset_dir,
            development_dataset_dir=args.development_dataset_dir,
            baseline_predictions_path=args.baseline_predictions,
            carp_predictions_path=args.carp_predictions,
            output_dir=args.output_dir,
        )
    )


if __name__ == "__main__":
    main()
