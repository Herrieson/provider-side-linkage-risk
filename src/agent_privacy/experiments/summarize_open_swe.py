from __future__ import annotations

import argparse
import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agent_privacy.io import ensure_dir
from agent_privacy.reporting import write_csv


@dataclass(frozen=True)
class OpenSWEResultCell:
    scaffold: str
    split: str
    sample_size: int
    dataset_dir: str
    audit_path: str
    cumulative_raw: str
    cumulative_no_workspace: str
    turn_delta_dir: str
    turn_delta_audit_path: str
    turn_delta_raw: str
    turn_delta_no_workspace: str


@dataclass(frozen=True)
class OpenSWESweepCell:
    sample_label: str
    sample_size: int
    scaffold: str
    split: str
    dataset_dir: str
    cumulative_raw: str
    cumulative_no_workspace: str
    turn_delta_raw: str
    turn_delta_no_workspace: str


DEFAULT_CELLS = [
    OpenSWEResultCell(
        scaffold="openhands",
        split="minimax_m25",
        sample_size=1000,
        dataset_dir="artifacts/datasets/open_swe_traces_raw_1000",
        audit_path="docs/open-swe-traces-raw-1000-audit.md",
        cumulative_raw="results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast",
        cumulative_no_workspace="results/open_swe_traces_raw_1000_turns_3_6_9_12_no_workspace_fast",
        turn_delta_dir="artifacts/datasets/open_swe_traces_raw_1000_turn_delta_3_6_9_12",
        turn_delta_audit_path="docs/open-swe-traces-raw-1000-turn-delta-3-6-9-12-audit.md",
        turn_delta_raw="results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_m0_fast",
        turn_delta_no_workspace="results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_no_workspace_fast",
    ),
    OpenSWEResultCell(
        scaffold="openhands",
        split="qwen35_122b",
        sample_size=500,
        dataset_dir="artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500",
        audit_path="docs/open-swe-traces-openhands-qwen35-raw-500-audit.md",
        cumulative_raw="results/open_swe_traces_openhands_qwen35_raw_500_turns_3_6_9_12_m0_fast",
        cumulative_no_workspace=(
            "results/open_swe_traces_openhands_qwen35_raw_500_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_dir="artifacts/datasets/open_swe_traces_openhands_qwen35_raw_500_turn_delta_3_6_9_12",
        turn_delta_audit_path=(
            "docs/open-swe-traces-openhands-qwen35-raw-500-turn-delta-3-6-9-12-audit.md"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_openhands_qwen35_raw_500_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_openhands_qwen35_raw_500_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    OpenSWEResultCell(
        scaffold="sweagent",
        split="minimax_m25",
        sample_size=500,
        dataset_dir="artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500",
        audit_path="docs/open-swe-traces-sweagent-minimax-raw-500-audit.md",
        cumulative_raw="results/open_swe_traces_sweagent_minimax_raw_500_turns_3_6_9_12_m0_fast",
        cumulative_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_raw_500_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_dir="artifacts/datasets/open_swe_traces_sweagent_minimax_raw_500_turn_delta_3_6_9_12",
        turn_delta_audit_path=(
            "docs/open-swe-traces-sweagent-minimax-raw-500-turn-delta-3-6-9-12-audit.md"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_sweagent_minimax_raw_500_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_sweagent_minimax_raw_500_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    OpenSWEResultCell(
        scaffold="sweagent",
        split="qwen35_122b",
        sample_size=500,
        dataset_dir="artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500",
        audit_path="docs/open-swe-traces-sweagent-qwen35-raw-500-audit.md",
        cumulative_raw="results/open_swe_traces_sweagent_qwen35_raw_500_turns_3_6_9_12_m0_fast",
        cumulative_no_workspace=(
            "results/open_swe_traces_sweagent_qwen35_raw_500_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_dir="artifacts/datasets/open_swe_traces_sweagent_qwen35_raw_500_turn_delta_3_6_9_12",
        turn_delta_audit_path=(
            "docs/open-swe-traces-sweagent-qwen35-raw-500-turn-delta-3-6-9-12-audit.md"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_sweagent_qwen35_raw_500_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_sweagent_qwen35_raw_500_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
]


OPENHANDS_MINIMAX_SAMPLE_SWEEP = [
    OpenSWESweepCell(
        sample_label="100_hf_reservoir_seed7",
        sample_size=100,
        scaffold="openhands",
        split="minimax_m25",
        dataset_dir="artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf",
        cumulative_raw=(
            "results/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf_turns_3_6_9_12_m0_fast"
        ),
        cumulative_no_workspace=(
            "results/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_openhands_minimax_reservoir_100_seed7_hf_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    OpenSWESweepCell(
        sample_label="250_hf_reservoir_seed7",
        sample_size=250,
        scaffold="openhands",
        split="minimax_m25",
        dataset_dir="artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf",
        cumulative_raw=(
            "results/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf_turns_3_6_9_12_m0_fast"
        ),
        cumulative_no_workspace=(
            "results/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_openhands_minimax_reservoir_250_seed7_hf_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    OpenSWESweepCell(
        sample_label="500_hf_reservoir_seed7",
        sample_size=500,
        scaffold="openhands",
        split="minimax_m25",
        dataset_dir="artifacts/datasets/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf",
        cumulative_raw=(
            "results/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf_turns_3_6_9_12_m0_fast"
        ),
        cumulative_no_workspace=(
            "results/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf_turns_3_6_9_12_no_workspace_fast"
        ),
        turn_delta_raw=(
            "results/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf_turn_delta_3_6_9_12_m0_fast"
        ),
        turn_delta_no_workspace=(
            "results/open_swe_traces_openhands_minimax_reservoir_500_seed7_hf_turn_delta_3_6_9_12_no_workspace_fast"
        ),
    ),
    OpenSWESweepCell(
        sample_label="1000_first_seed7",
        sample_size=1000,
        scaffold="openhands",
        split="minimax_m25",
        dataset_dir="artifacts/datasets/open_swe_traces_raw_1000",
        cumulative_raw="results/open_swe_traces_raw_1000_turns_3_6_9_12_m0_fast",
        cumulative_no_workspace="results/open_swe_traces_raw_1000_turns_3_6_9_12_no_workspace_fast",
        turn_delta_raw="results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_m0_fast",
        turn_delta_no_workspace="results/open_swe_traces_raw_1000_turn_delta_3_6_9_12_no_workspace_fast",
    ),
]


def summarize_open_swe(cells: list[OpenSWEResultCell]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    attack_rows: list[dict[str, Any]] = []
    dataset_rows: list[dict[str, Any]] = []
    for cell in cells:
        base_manifest = _read_manifest(Path(cell.dataset_dir))
        delta_manifest = _read_manifest(Path(cell.turn_delta_dir))
        dataset_rows.append(
            {
                "scaffold": cell.scaffold,
                "split": cell.split,
                "sample_size": cell.sample_size,
                "dataset_dir": cell.dataset_dir,
                "requests": base_manifest.get("requests", ""),
                "workflows": base_manifest.get("trajectories_used", ""),
                "source_rows_seen": base_manifest.get("source_rows_seen", ""),
                "sample_mode": base_manifest.get("sample_mode", base_manifest.get("config", {}).get("sample_mode", "first")),
                "repair_mode": base_manifest.get("config", {}).get("repair_mode", ""),
                "turn_delta_requests": delta_manifest.get("requests", ""),
                "audit_path": cell.audit_path,
                "turn_delta_audit_path": cell.turn_delta_audit_path,
            }
        )
        views = [
            ("cumulative_raw", cell.cumulative_raw),
            ("cumulative_no_workspace", cell.cumulative_no_workspace),
            ("turn_delta_raw", cell.turn_delta_raw),
            ("turn_delta_no_workspace", cell.turn_delta_no_workspace),
        ]
        for view, result_dir in views:
            metrics = _read_metrics(Path(result_dir))
            attack_rows.append(
                {
                    "scaffold": cell.scaffold,
                    "split": cell.split,
                    "sample_size": cell.sample_size,
                    "view": view,
                    "result_dir": result_dir,
                    "hybrid_session_f1": _metric(metrics, "hybrid", "session", "pairwise_f1"),
                    "hybrid_project_f1": _metric(metrics, "hybrid", "project", "pairwise_f1"),
                    "hybrid_org_f1": _metric(metrics, "hybrid", "org", "pairwise_f1"),
                    "rare_project_f1": _metric(metrics, "rare", "project", "pairwise_f1"),
                    "temporal_session_f1": _metric(metrics, "temporal", "session", "pairwise_f1"),
                    "tool_session_f1": _metric(metrics, "tool", "session", "pairwise_f1"),
                }
            )
    return dataset_rows, attack_rows


def summarize_sample_size_sweep(cells: list[OpenSWESweepCell]) -> list[dict[str, Any]]:
    attack_rows: list[dict[str, Any]] = []
    for cell in cells:
        manifest = _read_manifest(Path(cell.dataset_dir))
        config = manifest.get("config", {})
        views = [
            ("cumulative_raw", cell.cumulative_raw),
            ("cumulative_no_workspace", cell.cumulative_no_workspace),
            ("turn_delta_raw", cell.turn_delta_raw),
            ("turn_delta_no_workspace", cell.turn_delta_no_workspace),
        ]
        for view, result_dir in views:
            metrics = _read_metrics(Path(result_dir))
            attack_rows.append(
                {
                    "sample_label": cell.sample_label,
                    "sample_size": cell.sample_size,
                    "scaffold": cell.scaffold,
                    "split": cell.split,
                    "sample_mode": manifest.get("sample_mode", config.get("sample_mode", "first")),
                    "seed": config.get("seed", ""),
                    "max_source_rows": manifest.get("max_source_rows", config.get("max_source_rows", "")),
                    "source_rows_seen": manifest.get("source_rows_seen", ""),
                    "eligible_trajectories": manifest.get("eligible_trajectories", ""),
                    "requests": manifest.get("requests", ""),
                    "view": view,
                    "result_dir": result_dir,
                    "hybrid_session_f1": _metric(metrics, "hybrid", "session", "pairwise_f1"),
                    "hybrid_project_f1": _metric(metrics, "hybrid", "project", "pairwise_f1"),
                    "hybrid_org_f1": _metric(metrics, "hybrid", "org", "pairwise_f1"),
                    "rare_project_f1": _metric(metrics, "rare", "project", "pairwise_f1"),
                    "temporal_session_f1": _metric(metrics, "temporal", "session", "pairwise_f1"),
                    "tool_session_f1": _metric(metrics, "tool", "session", "pairwise_f1"),
                }
            )
    return attack_rows


def write_markdown_table(path: Path, rows: list[dict[str, Any]], columns: list[str]) -> None:
    ensure_dir(path.parent)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join("---" for _ in columns) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(_format_cell(row.get(column, "")) for column in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_manifest(dataset_dir: Path) -> dict[str, Any]:
    return json.loads((dataset_dir / "source_manifest.json").read_text(encoding="utf-8"))


def _read_metrics(result_dir: Path) -> list[dict[str, str]]:
    with (result_dir / "clustering_metrics_all.csv").open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _metric(rows: list[dict[str, str]], method: str, level: str, key: str) -> float | str:
    for row in rows:
        if row.get("method") == method and row.get("level") == level:
            return round(float(row[key]), 3)
    return ""


def _format_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def main() -> None:
    parser = argparse.ArgumentParser(description="Summarize existing Open-SWE 2x2 experiment results.")
    parser.add_argument("--output-dir", type=Path, default=Path("docs/tables"))
    args = parser.parse_args()

    dataset_rows, attack_rows = summarize_open_swe(DEFAULT_CELLS)
    sweep_rows = summarize_sample_size_sweep(OPENHANDS_MINIMAX_SAMPLE_SWEEP)
    write_csv(args.output_dir / "open_swe_2x2_dataset_matrix.csv", dataset_rows)
    write_csv(args.output_dir / "open_swe_2x2_attack_matrix.csv", attack_rows)
    write_csv(args.output_dir / "open_swe_openhands_minimax_sample_size_sweep.csv", sweep_rows)
    write_markdown_table(
        args.output_dir / "open_swe_2x2_attack_matrix.md",
        attack_rows,
        [
            "scaffold",
            "split",
            "sample_size",
            "view",
            "hybrid_session_f1",
            "hybrid_project_f1",
            "hybrid_org_f1",
            "rare_project_f1",
        ],
    )
    write_markdown_table(
        args.output_dir / "open_swe_openhands_minimax_sample_size_sweep.md",
        sweep_rows,
        [
            "sample_label",
            "sample_size",
            "sample_mode",
            "source_rows_seen",
            "view",
            "hybrid_session_f1",
            "hybrid_project_f1",
            "hybrid_org_f1",
            "rare_project_f1",
        ],
    )
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir),
                "dataset_rows": len(dataset_rows),
                "attack_rows": len(attack_rows),
                "sample_size_sweep_rows": len(sweep_rows),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
