from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from agent_privacy.evaluation.profile import evaluate_profiles
from agent_privacy.io import read_jsonl, write_json
from agent_privacy.profiling.structured_profiler import (
    AUDITED_TECHNICAL_FIELDS,
    profile_clusters_structured,
)
from agent_privacy.reporting import write_csv


def compare_profilers(
    dataset_dir: Path,
    predictions_path: Path,
    output_dir: Path,
    *,
    method: str = "hybrid",
    level: str = "org",
    rule_metrics_path: Path | None = None,
) -> dict[str, Any]:
    rows = read_jsonl(dataset_dir / "attack_view.jsonl")
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    predictions = json.loads(predictions_path.read_text(encoding="utf-8"))
    predicted_labels = predictions[method][level]
    truth_field = {"org": "org_id", "user": "user_id", "project": "project_id", "session": "workflow_id"}[level]
    truth_labels = {
        row["request_id"]: str(row[truth_field])
        for row in truth_rows
        if row.get(truth_field) not in (None, "", "N/A")
    }
    runs = {
        "structured_predicted_clusters": profile_clusters_structured(rows, predicted_labels),
        "structured_truth_clusters": profile_clusters_structured(rows, truth_labels),
    }
    metric_rows: list[dict[str, Any]] = []
    if rule_metrics_path is not None:
        metric_rows.extend(_read_rule_metrics(rule_metrics_path, method=method, level=level))
    for profiler, profiles in runs.items():
        write_json(output_dir / f"{profiler}.json", profiles)
        metrics = evaluate_profiles(profiles, truth_rows, predicted_labels)
        selected = [row for row in metrics if row["field"] in AUDITED_TECHNICAL_FIELDS]
        selected.append(_audited_micro(selected))
        for row in selected:
            row["profiler"] = profiler
            row["cluster_source"] = "truth" if profiler.endswith("truth_clusters") else "predicted"
            row["attack_method"] = method
            row["level"] = level
            metric_rows.append(row)
    write_csv(output_dir / "profile_comparison.csv", metric_rows)
    _write_markdown(output_dir / "profile_comparison.md", metric_rows)
    return {
        "dataset_dir": str(dataset_dir),
        "predictions": str(predictions_path),
        "output_dir": str(output_dir),
        "rows": len(metric_rows),
    }


def _read_rule_metrics(path: Path, *, method: str, level: str) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        raw_rows = [
            row
            for row in csv.DictReader(handle)
            if row.get("method") == method
            and row.get("level") == level
            and row.get("field") in AUDITED_TECHNICAL_FIELDS
        ]
    numeric = {
        "precision",
        "recall",
        "f1",
        "evidence_coverage",
        "tp",
        "fp",
        "fn",
        "predicted_values",
        "evidenced_values",
        "unsupported_predictions",
    }
    rows: list[dict[str, Any]] = []
    for raw in raw_rows:
        row = {
            key: float(value) if key in numeric and value else value
            for key, value in raw.items()
        }
        row.update(
            {
                "profiler": "rule_predicted_clusters",
                "cluster_source": "predicted",
                "attack_method": method,
                "level": level,
            }
        )
        rows.append(row)
    rows.append(
        {
            **_audited_micro(rows),
            "profiler": "rule_predicted_clusters",
            "cluster_source": "predicted",
            "attack_method": method,
            "level": level,
        }
    )
    return rows


def _audited_micro(rows: list[dict[str, Any]]) -> dict[str, Any]:
    tp = sum(float(row.get("tp", 0)) for row in rows)
    fp = sum(float(row.get("fp", 0)) for row in rows)
    fn = sum(float(row.get("fn", 0)) for row in rows)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    predicted = sum(float(row.get("predicted_values", 0)) for row in rows)
    evidenced = sum(float(row.get("evidenced_values", 0)) for row in rows)
    return {
        "field": "__audited_micro__",
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "tp": int(tp),
        "fp": int(fp),
        "fn": int(fn),
        "predicted_values": int(predicted),
        "evidenced_values": int(evidenced),
        "unsupported_predictions": int(
            sum(float(row.get("unsupported_predictions", 0)) for row in rows)
        ),
        "evidence_coverage": evidenced / predicted if predicted else 0.0,
    }


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = ["profiler", "cluster_source", "field", "precision", "recall", "f1", "tp", "fp", "fn", "evidence_coverage"]
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field, "")
            values.append(f"{value:.3f}" if isinstance(value, float) else str(value))
        lines.append("| " + " | ".join(values) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare rule and structured profile reconstruction.")
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--method", default="hybrid")
    parser.add_argument("--level", default="org", choices=["session", "user", "project", "org"])
    parser.add_argument("--rule-metrics", type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            compare_profilers(
                args.dataset_dir,
                args.predictions,
                args.output_dir,
                method=args.method,
                level=args.level,
                rule_metrics_path=args.rule_metrics,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
