from __future__ import annotations

import argparse
import gc
import re
from dataclasses import replace
from pathlib import Path
from typing import Any

from agent_privacy.attacks.pipeline import run_attacks_from_features
from agent_privacy.evaluation.clustering import (
    clustering_metrics,
    cross_workflow_clustering_metrics,
    truth_labels,
)
from agent_privacy.experiments.feature_ablations import feature_options_for_ablation
from agent_privacy.experiments.summarize_open_swe_main_session import (
    _exact_message_nesting_labels,
)
from agent_privacy.features.extract import extract_features_from_rows
from agent_privacy.io import iter_jsonl, read_jsonl
from agent_privacy.reporting import write_csv


DEFAULT_CUMULATIVE_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000")
DEFAULT_TURN_DELTA_DATASET = Path(
    "artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12"
)
DEFAULT_DEVELOPMENT_DATASET = Path("artifacts/datasets/open_swe_traces_raw_1000_sample100")
OUTPUT_BASE = "open_swe_strict_signal_removal"
TURN_IDS = {3, 6, 9, 12}
WORKSPACE_PATH_RE = re.compile(r"/(?:workspace|home|srv|opt|tmp)/[A-Za-z0-9_./-]+")
REPOSITORY_FIELD_RE = re.compile(
    r"\brepository=[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\b", re.IGNORECASE
)
INTERNAL_DOMAIN_RE = re.compile(
    r"\b(?:[a-z0-9-]+\.)+(?:internal|local|prod|corp)\b", re.IGNORECASE
)
OWNER_REPO_RE = re.compile(r"\b[A-Za-z0-9_.-]{2,}/[A-Za-z0-9_.-]{2,}\b")


def summarize_strict_removal(
    *,
    cumulative_dataset_dir: Path = DEFAULT_CUMULATIVE_DATASET,
    turn_delta_dataset_dir: Path = DEFAULT_TURN_DELTA_DATASET,
    development_dataset_dir: Path = DEFAULT_DEVELOPMENT_DATASET,
) -> list[dict[str, Any]]:
    development_workflows = {
        str(row["workflow_id"])
        for row in read_jsonl(development_dataset_dir / "ground_truth.jsonl")
    }
    rows: list[dict[str, Any]] = []
    for view, dataset_dir in (
        ("cumulative", cumulative_dataset_dir),
        ("turn_delta", turn_delta_dataset_dir),
    ):
        rows.extend(
            _summarize_view(
                view=view,
                dataset_dir=dataset_dir,
                development_workflows=development_workflows,
            )
        )
        gc.collect()
    return rows


def _summarize_view(
    *, view: str, dataset_dir: Path, development_workflows: set[str]
) -> list[dict[str, Any]]:
    truth_rows = [
        row
        for row in read_jsonl(dataset_dir / "ground_truth.jsonl")
        if int(row.get("turn_id", -1)) in TURN_IDS
        and str(row["workflow_id"]) not in development_workflows
    ]
    request_ids = {str(row["request_id"]) for row in truth_rows}
    attack_rows = [
        _strict_sanitize(row)
        for row in iter_jsonl(dataset_dir / "attack_view.jsonl")
        if str(row.get("request_id")) in request_ids
    ]
    options = feature_options_for_ablation(
        methods=["hybrid", "provider_lowcost"],
        fast_features=True,
        feature_ablation="no_semantic",
    )
    options = replace(
        options,
        text_feature_window_chars=24_000,
        max_shingles=1_200,
        max_words=1_500,
    )
    features = extract_features_from_rows(attack_rows, options=options)
    predictions = run_attacks_from_features(features, methods=["hybrid", "provider_lowcost"])
    predictions["exact_message_nesting"] = {
        "session": _exact_message_nesting_labels(attack_rows)
    }
    workflows = {str(row["request_id"]): str(row["workflow_id"]) for row in truth_rows}
    rows: list[dict[str, Any]] = []
    for method, level_predictions in predictions.items():
        for level in ("session", "project", "org"):
            if level not in level_predictions:
                continue
            truth = truth_labels(truth_rows, level)
            metrics = clustering_metrics(level_predictions[level], truth)
            row = {
                "view": view,
                "method": method,
                "level": level,
                "requests": len(truth_rows),
                "precision": metrics["pairwise_precision"],
                "recall": metrics["pairwise_recall"],
                "f1": metrics["pairwise_f1"],
                "purity": metrics["purity"],
                "split_rate": metrics["split_rate"],
                "merge_rate": metrics["merge_rate"],
                "clusters": int(metrics["clusters"]),
                "cross_workflow_precision": "",
                "cross_workflow_recall": "",
                "cross_workflow_f1": "",
                "feature_window_chars": 24000,
                "max_shingles": 1200,
                "max_words": 1500,
            }
            if level != "session":
                cross = cross_workflow_clustering_metrics(
                    level_predictions[level], truth, workflows
                )
                row.update(
                    {
                        "cross_workflow_precision": cross["cross_workflow_precision"],
                        "cross_workflow_recall": cross["cross_workflow_recall"],
                        "cross_workflow_f1": cross["cross_workflow_f1"],
                    }
                )
            rows.append(row)
    return rows


def _strict_sanitize(row: dict[str, Any]) -> dict[str, Any]:
    for message in row.get("messages", []):
        text = str(message.get("content", ""))
        text = REPOSITORY_FIELD_RE.sub("repository=[REPOSITORY]", text)
        text = WORKSPACE_PATH_RE.sub("[PATH]", text)
        text = INTERNAL_DOMAIN_RE.sub("[INTERNAL_DOMAIN]", text)
        text = OWNER_REPO_RE.sub("[OWNER_REPOSITORY]", text)
        message["content"] = text
    return row


def write_strict_removal(output_dir: Path, **kwargs: Any) -> dict[str, str]:
    rows = summarize_strict_removal(**kwargs)
    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / f"{OUTPUT_BASE}.csv"
    md_path = output_dir / f"{OUTPUT_BASE}.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path)}


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
    parser = argparse.ArgumentParser(description="Evaluate strict Open-SWE signal removal.")
    parser.add_argument(
        "--cumulative-dataset-dir", type=Path, default=DEFAULT_CUMULATIVE_DATASET
    )
    parser.add_argument(
        "--turn-delta-dataset-dir", type=Path, default=DEFAULT_TURN_DELTA_DATASET
    )
    parser.add_argument(
        "--development-dataset-dir", type=Path, default=DEFAULT_DEVELOPMENT_DATASET
    )
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(
        write_strict_removal(
            args.output_dir,
            cumulative_dataset_dir=args.cumulative_dataset_dir,
            turn_delta_dataset_dir=args.turn_delta_dataset_dir,
            development_dataset_dir=args.development_dataset_dir,
        )
    )


if __name__ == "__main__":
    main()
