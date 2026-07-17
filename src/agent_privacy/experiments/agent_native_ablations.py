from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from agent_privacy.agent_state.streaming import AgentNativeLinker, LinkerConfig
from agent_privacy.evaluation.clustering import clustering_metrics, truth_labels
from agent_privacy.evaluation.selective import (
    false_merge_amplification,
    selective_linkage_metrics,
)
from agent_privacy.io import iter_jsonl, read_jsonl


VARIANTS: dict[str, LinkerConfig] = {
    "full": LinkerConfig(),
    "replay_only": LinkerConfig(
        enabled_evidence=("state_replay", "initial_task", "ordered_progression"),
        accept_score=3.0,
        min_evidence_families=2,
    ),
    "tool_resource_only": LinkerConfig(
        enabled_evidence=("tool_resource", "resource_root", "ordered_progression"),
        accept_score=4.3,
        min_evidence_families=3,
    ),
    "typed_handle_only": LinkerConfig(
        enabled_evidence=("typed_handle", "ordered_progression"),
        accept_score=1.3,
        min_evidence_families=2,
    ),
    "without_conflicts": LinkerConfig(enforce_conflicts=False),
}


def run_ablations(dataset_dir: Path) -> list[dict[str, Any]]:
    truth_rows = read_jsonl(dataset_dir / "ground_truth.jsonl")
    truth = truth_labels(truth_rows, "session")
    reports: list[dict[str, Any]] = []
    for name, config in VARIANTS.items():
        result = AgentNativeLinker(config).run(iter_jsonl(dataset_dir / "attack_view.jsonl"))
        cluster = clustering_metrics(result.predictions["session"], truth)
        selective = selective_linkage_metrics(result.decisions, truth)
        amplification = false_merge_amplification(result.predictions["session"], truth)
        reports.append(
            {
                "dataset": dataset_dir.name,
                "variant": name,
                "pairwise_precision": cluster["pairwise_precision"],
                "pairwise_recall": cluster["pairwise_recall"],
                "pairwise_f1": cluster["pairwise_f1"],
                "accepted_edge_precision": selective["accepted_edge_precision"],
                "true_edge_coverage": selective["true_edge_coverage"],
                "abstention_rate": selective["abstention_rate"],
                "contaminated_requests": amplification["contaminated_requests"],
                "candidates_per_request": result.stats["candidates_per_request"],
            }
        )
    return reports


def write_reports(reports: list[dict[str, Any]], output_base: Path) -> None:
    output_base.parent.mkdir(parents=True, exist_ok=True)
    fields = list(reports[0]) if reports else []
    with output_base.with_suffix(".csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(reports)
    lines = [
        "# Agent-Native Evidence Ablations",
        "",
        "| Dataset | Variant | Precision | Recall | F1 | Edge precision | Coverage | Abstention | Contaminated requests | Candidates/request |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in reports:
        lines.append(
            f"| {row['dataset']} | {row['variant']} | {row['pairwise_precision']:.3f} | "
            f"{row['pairwise_recall']:.3f} | {row['pairwise_f1']:.3f} | "
            f"{row['accepted_edge_precision']:.3f} | {row['true_edge_coverage']:.3f} | "
            f"{row['abstention_rate']:.3f} | {row['contaminated_requests']:.0f} | "
            f"{row['candidates_per_request']:.2f} |"
        )
    output_base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Agent-native evidence-family ablations.")
    parser.add_argument("--dataset-dir", type=Path, action="append", required=True)
    parser.add_argument("--output-base", type=Path, required=True)
    args = parser.parse_args()
    reports = [row for path in args.dataset_dir for row in run_ablations(path)]
    write_reports(reports, args.output_base)
    print(json.dumps(reports, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
