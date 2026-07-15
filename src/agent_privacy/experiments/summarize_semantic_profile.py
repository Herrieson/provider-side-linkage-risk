from __future__ import annotations

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from agent_privacy.io import read_jsonl, write_jsonl
from agent_privacy.reporting import write_csv


EXPLICIT_ARTIFACT_PATTERNS = {
    ("build_tools", "go test"): (r"_test\.go\b", r"/testing/testing\.go\b", r"\bgo test\b"),
    ("build_tools", "pytest"): (r"\bpytest\b", r"conftest\.py\b"),
    ("languages", "python"): (r"\.py\b", r"pyproject\.toml\b", r"python traceback"),
    ("languages", "go"): (r"\.go\b", r"go\.mod\b", r"/usr/local/go/"),
}


def summarize_semantic_profile(
    result_dir: Path,
    dataset_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    comparison = _read_csv(result_dir / "semantic_profile_comparison.csv")
    summary = json.loads((result_dir / "semantic_profile_summary.json").read_text(encoding="utf-8"))
    structured = json.loads(
        (result_dir / "structured_predicted_clusters.json").read_text(encoding="utf-8")
    )
    semantic = json.loads(
        (result_dir / "semantic_predicted_clusters.json").read_text(encoding="utf-8")
    )
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    novel = _novel_predictions(structured, semantic, truth_rows)
    micro_rows = [row for row in comparison if row["field"] == "__audited_micro__"]
    for row in micro_rows:
        row.update(
            {
                "model": summary["model"] if row["profiler"].startswith("semantic") else "none",
                "calibration_orgs": summary["calibration_orgs"],
                "test_orgs": summary["test_orgs"],
                "test_requests": summary["test_requests"],
                "threshold": (
                    summary["selected_threshold"]
                    if row["profiler"].startswith("semantic")
                    else ""
                ),
                "min_request_support": (
                    summary["selected_min_request_support"]
                    if row["profiler"].startswith("semantic")
                    else ""
                ),
                "embedding_seconds": (
                    summary["semantic_runtime"]["encode_seconds"]
                    if row["profiler"].startswith("semantic")
                    else ""
                ),
                "semantic_spans": (
                    summary["semantic_runtime"]["spans"]
                    if row["profiler"].startswith("semantic")
                    else ""
                ),
                "max_rss_mb": (
                    summary["max_rss_mb"] if row["profiler"].startswith("semantic") else ""
                ),
            }
        )
    comparison_csv = output_dir / "open_swe_semantic_profile_comparison.csv"
    comparison_md = output_dir / "open_swe_semantic_profile_comparison.md"
    novel_jsonl = output_dir / "open_swe_semantic_profile_novel_evidence.jsonl"
    novel_md = output_dir / "open_swe_semantic_profile_novel_evidence.md"
    write_csv(comparison_csv, micro_rows)
    _write_micro_markdown(comparison_md, micro_rows, summary, novel)
    write_jsonl(novel_jsonl, novel)
    _write_novel_markdown(novel_md, novel)
    return {
        "comparison_csv": str(comparison_csv),
        "comparison_markdown": str(comparison_md),
        "novel_evidence_jsonl": str(novel_jsonl),
        "novel_evidence_markdown": str(novel_md),
        "novel_predictions": len(novel),
        "explicit_artifact_supported": sum(
            row["audit_status"] == "explicit_artifact_support" for row in novel
        ),
    }


def _novel_predictions(
    structured: dict[str, dict[str, Any]],
    semantic: dict[str, dict[str, Any]],
    truth_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    truth_by_request = {row["request_id"]: row for row in truth_rows}
    truth_by_org: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for row in truth_rows:
        for field, values in row.get("profile_truth", {}).items():
            truth_by_org[str(row["org_id"])][field].update(values)
    rows: list[dict[str, Any]] = []
    for cluster_id, semantic_profile in semantic.items():
        structured_fields = structured.get(cluster_id, {}).get("fields", {})
        org_counts = Counter(
            str(truth_by_request[request_id]["org_id"])
            for request_id in semantic_profile.get("request_ids", [])
            if request_id in truth_by_request
        )
        org_id = org_counts.most_common(1)[0][0] if org_counts else ""
        for field, values in semantic_profile.get("fields", {}).items():
            novel_values = set(values) - set(structured_fields.get(field, []))
            for value in sorted(novel_values):
                confidence = semantic_profile.get("confidence", {}).get(field, {}).get(value, {})
                span = str(confidence.get("best_span", ""))
                truth_match = value in truth_by_org[org_id].get(field, set())
                explicit = _has_explicit_artifact(field, value, span)
                rows.append(
                    {
                        "cluster_id": cluster_id,
                        "majority_org": org_id,
                        "field": field,
                        "value": value,
                        "score": confidence.get("score", 0.0),
                        "request_count": confidence.get("request_count", 0),
                        "best_span_role": confidence.get("best_span_role", ""),
                        "best_span": span,
                        "truth_match": truth_match,
                        "audit_status": (
                            "truth_match"
                            if truth_match
                            else "explicit_artifact_support"
                            if explicit
                            else "semantic_only_unverified"
                        ),
                    }
                )
    return rows


def _has_explicit_artifact(field: str, value: str, span: str) -> bool:
    patterns = EXPLICIT_ARTIFACT_PATTERNS.get((field, value), ())
    return any(re.search(pattern, span, re.IGNORECASE) for pattern in patterns)


def _read_csv(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    numeric = {
        "precision",
        "recall",
        "f1",
        "tp",
        "fp",
        "fn",
        "evidence_coverage",
    }
    return [
        {key: float(value) if key in numeric and value else value for key, value in row.items()}
        for row in rows
    ]


def _write_micro_markdown(
    path: Path,
    rows: list[dict[str, Any]],
    summary: dict[str, Any],
    novel: list[dict[str, Any]],
) -> None:
    fields = [
        "profiler",
        "cluster_source",
        "precision",
        "recall",
        "f1",
        "test_requests",
        "threshold",
        "min_request_support",
        "embedding_seconds",
        "max_rss_mb",
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
    explicit = sum(row["audit_status"] == "explicit_artifact_support" for row in novel)
    lines.extend(
        [
            "",
            f"Calibration/test split: {summary['calibration_orgs']} / {summary['test_orgs']} disjoint orgs.",
            f"Evidence spans: {summary['semantic_runtime']['spans']} total, "
            f"{summary['semantic_runtime']['unique_spans']} unique.",
            f"Semantic-only predictions: {len(novel)}; explicit artifact supported: {explicit}.",
            "The fixed benchmark truth does not include these artifact-supported additions, so they "
            "remain false positives in the quantitative table.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_novel_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "majority_org",
        "field",
        "value",
        "score",
        "request_count",
        "truth_match",
        "audit_status",
        "best_span",
    ]
    lines = [
        "| " + " | ".join(fields) + " |",
        "| " + " | ".join("---" for _ in fields) + " |",
    ]
    for row in rows:
        values = []
        for field in fields:
            value = row.get(field, "")
            if isinstance(value, float):
                rendered = f"{value:.3f}"
            else:
                rendered = str(value).replace("|", "\\|").replace("\n", " ")
            values.append(rendered[:240])
        lines.append("| " + " | ".join(values) + " |")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize semantic profile reconstruction.")
    parser.add_argument("--result-dir", type=Path, required=True)
    parser.add_argument("--dataset-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            summarize_semantic_profile(args.result_dir, args.dataset_dir, args.output_dir),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
