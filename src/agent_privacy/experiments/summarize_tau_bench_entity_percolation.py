from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


def summarize_entity_percolation(
    baseline_dir: Path,
    improved_dir: Path,
    output_dir: Path,
) -> dict[str, Any]:
    baseline = _metrics(baseline_dir / "clustering_metrics_all.csv")
    improved = _metrics(improved_dir / "clustering_metrics_all.csv")
    stats = _stats(improved_dir / "run_summary.json")
    rows = []
    for level in ("session", "user", "project", "org"):
        before = baseline[level]
        after = improved[level]
        rows.append(
            {
                "level": level,
                "baseline_precision": before["pairwise_precision"],
                "baseline_recall": before["pairwise_recall"],
                "baseline_f1": before["pairwise_f1"],
                "entity_percolation_precision": after["pairwise_precision"],
                "entity_percolation_recall": after["pairwise_recall"],
                "entity_percolation_f1": after["pairwise_f1"],
                "f1_gain": after["pairwise_f1"] - before["pairwise_f1"],
                "global_business_candidate_pairs": stats.get(
                    "global_business_candidate_pairs", 0
                ),
                "global_business_links": stats.get("global_business_links", 0),
                "ambiguous_user_anchors_rejected": stats.get(
                    "global_business_ambiguous_anchors", 0
                ),
            }
        )
    csv_path = output_dir / "tau_bench_t3_entity_percolation.csv"
    md_path = output_dir / "tau_bench_t3_entity_percolation.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "markdown": str(md_path), "rows": len(rows)}


def _metrics(path: Path) -> dict[str, dict[str, float]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        rows = [
            row
            for row in csv.DictReader(handle)
            if row["method"] == "provider_lowcost"
            and row.get("feature_ablation", "none") == "none"
        ]
    return {
        row["level"]: {
            field: float(row[field])
            for field in ("pairwise_precision", "pairwise_recall", "pairwise_f1")
        }
        for row in rows
    }


def _stats(path: Path) -> dict[str, Any]:
    summary = json.loads(path.read_text(encoding="utf-8"))
    feature = summary["defenses"]["M0"]["ablations"]["none"]["feature_ablations"]["none"]
    return feature.get("stream_provider_lowcost_stats", {})


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fields = [
        "level",
        "baseline_precision",
        "baseline_recall",
        "baseline_f1",
        "entity_percolation_precision",
        "entity_percolation_recall",
        "entity_percolation_f1",
        "f1_gain",
    ]
    lines = ["| " + " | ".join(fields) + " |", "| " + " | ".join("---" for _ in fields) + " |"]
    for row in rows:
        values = [f"{row[field]:.3f}" if isinstance(row[field], float) else str(row[field]) for field in fields]
        lines.append("| " + " | ".join(values) + " |")
    lines.extend(
        [
            "",
            f"Global typed-handle candidate edges: {rows[0]['global_business_candidate_pairs']}.",
            f"New cross-cache union operations: {rows[0]['global_business_links']}.",
            f"Ambiguous typed aliases rejected: {rows[0]['ambiguous_user_anchors_rejected']}.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize T3 entity-percolation improvement.")
    parser.add_argument("--baseline-dir", type=Path, required=True)
    parser.add_argument("--improved-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            summarize_entity_percolation(
                args.baseline_dir,
                args.improved_dir,
                args.output_dir,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
