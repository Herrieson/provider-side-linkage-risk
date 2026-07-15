from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_privacy.reporting import write_csv


@dataclass(frozen=True)
class ReservoirCell:
    sample_label: str
    sample_size: int
    dataset_dir: str
    turn_delta_dir: str
    cumulative_raw: str
    cumulative_no_workspace: str
    turn_delta_raw: str
    turn_delta_no_workspace: str


SWEAGENT_MINIMAX_LOCAL_RESERVOIR = [
    ReservoirCell(
        sample_label="100_local_reservoir_seed7",
        sample_size=100,
        dataset_dir="artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_100_seed7_local",
        turn_delta_dir=(
            "artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_100_seed7_local_turn_delta_3_6_9_12"
        ),
        cumulative_raw=(
            "results/open_swe_traces_sweagent_minimax_reservoir_100_seed7_local_turns_3_6_9_12_m0_fast"
        ),
        cumulative_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_reservoir_100_seed7_local_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_sweagent_minimax_reservoir_100_seed7_local_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_reservoir_100_seed7_local_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    ReservoirCell(
        sample_label="250_local_reservoir_seed7",
        sample_size=250,
        dataset_dir="artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_250_seed7_local",
        turn_delta_dir=(
            "artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_250_seed7_local_turn_delta_3_6_9_12"
        ),
        cumulative_raw=(
            "results/open_swe_traces_sweagent_minimax_reservoir_250_seed7_local_turns_3_6_9_12_m0_fast"
        ),
        cumulative_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_reservoir_250_seed7_local_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_sweagent_minimax_reservoir_250_seed7_local_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_reservoir_250_seed7_local_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    ReservoirCell(
        sample_label="500_local_reservoir_seed7",
        sample_size=500,
        dataset_dir="artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_500_seed7_local",
        turn_delta_dir=(
            "artifacts/datasets/open_swe_traces_sweagent_minimax_reservoir_500_seed7_local_turn_delta_3_6_9_12"
        ),
        cumulative_raw=(
            "results/open_swe_traces_sweagent_minimax_reservoir_500_seed7_local_turns_3_6_9_12_m0_fast"
        ),
        cumulative_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_reservoir_500_seed7_local_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_sweagent_minimax_reservoir_500_seed7_local_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_reservoir_500_seed7_local_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
]


def summarize_sweagent_reservoir(output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, Any]] = []
    for cell in SWEAGENT_MINIMAX_LOCAL_RESERVOIR:
        manifest = _read_json(Path(cell.dataset_dir) / "source_manifest.json")
        delta_manifest = _read_json(Path(cell.turn_delta_dir) / "source_manifest.json")
        views = [
            ("cumulative_raw", cell.cumulative_raw),
            ("cumulative_no_workspace", cell.cumulative_no_workspace),
            ("turn_delta_raw", cell.turn_delta_raw),
            ("turn_delta_no_workspace", cell.turn_delta_no_workspace),
        ]
        for view, result_dir in views:
            metrics = _read_metrics(Path(result_dir) / "clustering_metrics_all.csv")
            run_summary = _read_json(Path(result_dir) / "run_summary.json")
            rows.append(
                {
                    "sample_label": cell.sample_label,
                    "sample_size": cell.sample_size,
                    "sample_mode": manifest.get("sample_mode", ""),
                    "sample_scope": "local_from_sweagent_minimax_raw_500",
                    "source_workflows": manifest.get("source_workflows", ""),
                    "source_requests": manifest.get("requests", ""),
                    "evaluated_requests": run_summary.get("requests", ""),
                    "turn_delta_requests": delta_manifest.get("requests", ""),
                    "view": view,
                    "result_dir": result_dir,
                    "hybrid_session_f1": _metric(metrics, "hybrid", "session", "pairwise_f1"),
                    "hybrid_project_f1": _metric(metrics, "hybrid", "project", "pairwise_f1"),
                    "hybrid_org_f1": _metric(metrics, "hybrid", "org", "pairwise_f1"),
                    "rare_project_f1": _metric(metrics, "rare", "project", "pairwise_f1"),
                    "temporal_session_f1": _metric(metrics, "temporal", "session", "pairwise_f1"),
                    "tool_session_f1": _metric(metrics, "tool", "session", "pairwise_f1"),
                    "feature_seconds": _timing(run_summary, "feature_seconds"),
                    "attack_seconds": _timing(run_summary, "attack_seconds"),
                    "evaluation_seconds": _timing(run_summary, "evaluation_seconds"),
                }
            )
    csv_path = output_dir / "open_swe_sweagent_minimax_local_reservoir_sweep.csv"
    md_path = output_dir / "open_swe_sweagent_minimax_local_reservoir_sweep.md"
    write_csv(csv_path, rows)
    _write_markdown(md_path, rows)
    return {"csv": str(csv_path), "md": str(md_path), "rows": str(len(rows))}


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_metrics(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _metric(rows: list[dict[str, str]], method: str, level: str, key: str) -> float | str:
    for row in rows:
        if row.get("method") == method and row.get("level") == level:
            return round(float(row[key]), 3)
    return ""


def _timing(run_summary: dict[str, Any], key: str) -> float | str:
    try:
        feature_summaries = run_summary["defenses"]["M0"]["ablations"]
        first_ablation = next(iter(feature_summaries.values()))
        first_feature = next(iter(first_ablation["feature_ablations"].values()))
        return round(float(first_feature[key]), 3)
    except (KeyError, StopIteration, TypeError, ValueError):
        return ""


def _write_markdown(path: Path, rows: list[dict[str, Any]]) -> None:
    headers = [
        "sample_label",
        "sample_scope",
        "evaluated_requests",
        "view",
        "hybrid_session_f1",
        "hybrid_project_f1",
        "hybrid_org_f1",
        "rare_project_f1",
        "feature_seconds",
        "attack_seconds",
    ]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format(row.get(header, "")) for header in headers) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _format(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize SWE-agent/minimax local reservoir sweep.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()
    print(json.dumps(summarize_sweagent_reservoir(args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
